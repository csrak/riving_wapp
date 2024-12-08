from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db.models import Sum, Max
from datetime import timedelta, datetime
import math
from fin_data_cl.models import Security, DividendData, FinancialData, FinancialRatio, PriceData

class FinancialRatioCalculationService:
    """
    Service class to handle financial ratio calculations
    """

    @staticmethod
    def to_decimal(value):
        """Convert a value to Decimal, handling None and NaN"""
        try:
            return Decimal(str(value)) if value is not None and not math.isnan(float(value)) else None
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def get_latest_dividend_total(security, date):
        """
        Calculate dividend totals for current and previous year periods
        """
        last_year_end = date
        last_year_start = date - timedelta(days=365)
        previous_year_end = last_year_start - timedelta(days=1)
        previous_year_start = previous_year_end - timedelta(days=365)

        # Calculate totals for both periods
        total_last_365_days = (
            DividendData.objects.filter(
                security=security,
                date__range=(last_year_start, last_year_end)
            ).aggregate(total=Sum('amount'))['total']
        )

        total_previous_365_days = (
            DividendData.objects.filter(
                security=security,
                date__range=(previous_year_start, previous_year_end)
            ).aggregate(total=Sum('amount'))['total']
        )

        return total_last_365_days, total_previous_365_days

    @staticmethod
    def get_aggregated_quarterly_data(security, date):
        """
        Aggregate last 4 quarters of financial data
        """
        last_4_quarters = FinancialData.objects.filter(
            security=security,
            date__lte=date
        ).order_by('-date')[:4]

        if len(last_4_quarters) < 4:
            return None

        return {
            'revenue': sum(q.revenue or 0 for q in last_4_quarters),
            'net_profit': sum(q.net_profit or 0 for q in last_4_quarters),
            'operating_profit': sum(q.operating_profit or 0 for q in last_4_quarters),
            'eps': sum(q.eps or 0 for q in last_4_quarters),
            'cost_of_sales': sum(q.cost_of_sales or 0 for q in last_4_quarters),
            'ebit': sum(q.ebit or 0 for q in last_4_quarters),
            'depreciation': sum(q.depreciation or 0 for q in last_4_quarters),
            'interest': sum(q.interest or 0 for q in last_4_quarters),
        }

    def calculate_ratios(self, security, date):
        """
        Calculate financial ratios for a security at a given date
        """
        try:
            # Get the most recent price data
            price_data = PriceData.objects.filter(
                security=security
            ).order_by('-date').first()

            if not price_data:
                print(f"No price data for {security.ticker}")
                return None

            # If no specific date provided, use the price data date
            if not date:
                date = price_data.date

            # Get latest financial data as of this date
            latest_financial_data = FinancialData.objects.filter(
                security=security,
                date__lte=date  # Get latest data up to this date
            ).order_by('-date').first()

            if not latest_financial_data:
                print(f"No financial data for {security.ticker} as of {date}")
                return None

            # Always use the financial data date for consistency
            calculation_date = latest_financial_data.date

            # Get dividend data
            try:
                latest_divs, before_divs = self.get_latest_dividend_total(security, calculation_date)
            except Exception as e:
                print(f"Problem obtaining dividends for {security.ticker}: {e}")
                latest_divs = None
                before_divs = None

            # Initialize ratios with dividend calculations
            ratios = self._calculate_dividend_ratios(latest_divs, before_divs, price_data.price)

            # Get quarterly data and calculate other ratios
            quarterly_data = self.get_aggregated_quarterly_data(security, calculation_date)
            if quarterly_data:
                ratios.update(self._calculate_market_ratios(price_data, quarterly_data, latest_financial_data))
                ratios.update(self._calculate_profitability_ratios(quarterly_data))
                ratios.update(self._calculate_efficiency_ratios(quarterly_data, latest_financial_data))

            # Always create/update using the financial data date
            financial_ratio, created = FinancialRatio.objects.update_or_create(
                security=security,
                date=calculation_date,
                defaults={
                    'price': price_data.price,
                    **ratios
                }
            )

            return financial_ratio

        except Exception as e:
            print(f"Error calculating ratios for {security.ticker}: {e}")
            return None

    def _calculate_market_ratios(self, price_data, quarterly_data, balance_data):
        """Calculate market-based ratios"""
        market_cap = self.to_decimal(price_data.market_cap)
        price = self.to_decimal(price_data.price)

        return {
            'pe_ratio': self.to_decimal(market_cap / quarterly_data['net_profit']) if market_cap and quarterly_data[
                'net_profit'] else None,
            'pb_ratio': self.to_decimal(
                market_cap / balance_data.equity) if market_cap and balance_data.equity else None,
            'ps_ratio': self.to_decimal(market_cap / quarterly_data['revenue']) if market_cap and quarterly_data[
                'revenue'] else None,
            'peg_ratio': Decimal('0'),  # Placeholder for future calculation
            'ev_ebitda': self.to_decimal(
                (market_cap + balance_data.liabilities - balance_data.cash) / quarterly_data['ebit']
            ) if all([market_cap, balance_data.liabilities, balance_data.cash, quarterly_data['ebit']]) else None
        }

    def _calculate_profitability_ratios(self, quarterly_data):
        """Calculate profitability ratios"""
        return {
            'gross_profit_margin': self.to_decimal(
                (quarterly_data['revenue'] - quarterly_data['cost_of_sales']) / quarterly_data['revenue']
            ) if quarterly_data['revenue'] and quarterly_data['cost_of_sales'] else None,
            'operating_profit_margin': self.to_decimal(
                quarterly_data['operating_profit'] / quarterly_data['revenue']
            ) if quarterly_data['operating_profit'] and quarterly_data['revenue'] else None,
            'net_profit_margin': self.to_decimal(
                quarterly_data['net_profit'] / quarterly_data['revenue']
            ) if quarterly_data['net_profit'] and quarterly_data['revenue'] else None
        }

    def _calculate_efficiency_ratios(self, quarterly_data, balance_data):
        """Calculate efficiency ratios"""
        return {
            'return_on_assets': self.to_decimal(
                quarterly_data['net_profit'] / balance_data.assets
            ) if quarterly_data['net_profit'] and balance_data.assets else None,
            'return_on_equity': self.to_decimal(
                quarterly_data['net_profit'] / balance_data.equity
            ) if quarterly_data['net_profit'] and balance_data.equity else None,
            'debt_to_equity': self.to_decimal(
                balance_data.liabilities / balance_data.equity
            ) if balance_data.liabilities and balance_data.equity else None,
            'current_ratio': self.to_decimal(
                balance_data.current_assets / balance_data.current_liabilities
            ) if balance_data.current_assets and balance_data.current_liabilities else None,
            'quick_ratio': self.to_decimal(
                (balance_data.current_assets - balance_data.inventories) / balance_data.current_liabilities
            ) if all(
                [balance_data.current_assets, balance_data.inventories, balance_data.current_liabilities]) else None
        }

    def _calculate_dividend_ratios(self, latest_divs, before_divs, price):
        """Calculate dividend ratios"""
        price = self.to_decimal(price)
        return {
            'dividend_yield': self.to_decimal(latest_divs / price * 100) if latest_divs and price else None,
            'before_dividend_yield': self.to_decimal(before_divs / price * 100) if before_divs and price else None
        }


class Command(BaseCommand):
    help = 'Calculate and store financial ratios for all securities'

    def handle(self, *args, **kwargs):
        calculator = FinancialRatioCalculationService()
        securities = Security.objects.filter(is_active=True)

        for security in securities:
            # Get unique dates for this security
            date = FinancialData.objects.filter(
                security=security
            ).order_by('-date').values_list('date', flat=True).first()

            if date:
                result = calculator.calculate_ratios(security, date)
                if result:
                    print(f"Ratios calculated for {security.ticker} on {date}")
            else:
                result = calculator.calculate_ratios(security, None)
                if result:
                    print(f"Only dividend ratios calculated for {security.ticker}")