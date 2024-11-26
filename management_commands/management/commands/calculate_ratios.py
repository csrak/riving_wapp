import math
from django.core.management.base import BaseCommand
from fin_data_cl.models import FinancialData, FinancialRatio, PriceData, Dividend, FinancialReport
from decimal import Decimal
import datetime
from datetime import date, timedelta
from django.db.models import Sum, Max

def get_latest_dividend_total(ticker, last_update_date):
    """
    Calculate the total dividend paid for the given ticker in the last 365 days
    since the last update in the Dividend model, and in the 365 days before that.
    Returns None on each if there is insufficient data.

    Args:
        ticker (str): The ticker symbol for the company

    Returns:
        tuple: (total_last_365_days, total_previous_365_days)
    """
    # Get the most recent date from the Dividend model for the given ticker, this is not exactly latest day downloaded but still valid


    # Define the date ranges based on the last update date
    last_year_end = last_update_date
    last_year_start = last_update_date - timedelta(days=365)

    previous_year_end = last_year_start - timedelta(days=1)
    previous_year_start = previous_year_end - timedelta(days=365)

    # Calculate the total dividend for the last 365 days since the last update
    total_last_365_days = (
        Dividend.objects.filter(
            ticker=ticker,
            date__range=(last_year_start, last_year_end)
        ).aggregate(total=Sum('amount'))['total']
    )

    # Calculate the total dividend for the 365 days before the last year
    total_previous_365_days = (
        Dividend.objects.filter(
            ticker=ticker,
            date__range=(previous_year_start, previous_year_end)
        ).aggregate(total=Sum('amount'))['total']
    )

    return total_last_365_days, total_previous_365_days
def calculate_ratios(ticker, date):
    # try:
    last_div_update_date = Dividend.objects.aggregate(max_date=Max('date'))['max_date']

    # Get the latest available date for balance sheet data
    latest_financial_data = FinancialData.objects.filter(ticker=ticker, date=date).first()
    try:
        latest_divs, before_divs = get_latest_dividend_total(ticker,last_div_update_date)
    except Exception as e:
        div_year = None
        latest_divs = None
        before_divs = None
        print(f"Problem obtaining dividends for {ticker}")


    # Fetch the last four quarters for income statement data to annualize
    last_4_quarters = FinancialData.objects.filter(ticker=ticker).order_by('-date')[:4]

    # If we have fewer than 4 quarters, we can't annualize properly
    if not (len(last_4_quarters) < 4):
        # Aggregate data for the last 4 quarters
        aggregated_data = {
            'revenue': sum([d.revenue for d in last_4_quarters if d.revenue is not None]),
            'net_profit': sum([d.net_profit for d in last_4_quarters if d.net_profit is not None]),
            'operating_profit': sum([d.operating_profit for d in last_4_quarters if d.operating_profit is not None]),
            'eps': sum([d.eps for d in last_4_quarters if d.eps is not None]),
            'cost_of_sales': sum([d.cost_of_sales for d in last_4_quarters if d.cost_of_sales is not None]),
            'ebit': sum([d.ebit for d in last_4_quarters if d.ebit is not None]),
            'depreciation': sum([d.depreciation for d in last_4_quarters if d.depreciation is not None]),
            'interest': sum([d.interest for d in last_4_quarters if d.interest is not None]),
        }

        # Use the latest balance sheet data for these metrics
        balance_sheet_data = {
            'equity': latest_financial_data.equity,
            'assets': latest_financial_data.assets,
            'liabilities': latest_financial_data.liabilities,
            'current_assets': latest_financial_data.current_assets,
            'current_liabilities': latest_financial_data.current_liabilities,
            'inventories': latest_financial_data.inventories,
            'cash': latest_financial_data.cash,
            'shares': latest_financial_data.shares,
        }
    else:
        print("Not enough quarters for {ticker}")
        aggregated_data = {
            'revenue': None,
            'net_profit': None,
            'operating_profit': None,
            'eps': None,
            'cost_of_sales': None,
            'ebit': None,
            'depreciation': None,
            'interest': None,
        }
        balance_sheet_data = {
            'equity': None,
            'assets': None,
            'liabilities': None,
            'current_assets': None,
            'current_liabilities': None,
            'inventories': None,
            'cash': None,
            'shares': None
        }

    # Fetch the most recent price and market cap data
    price_data = PriceData.objects.filter(ticker=ticker).order_by('-date').first()
    peg_ratio = 0

    if not price_data:
        print(f"No price data for {ticker}")
        return None
    else:
        # Calculate ratios with robust handling for None and zero values price_data.market_cap
        if aggregated_data['eps']:
            pe_ratio = to_decimal(price_data.price) / to_decimal(aggregated_data['eps'])
        elif price_data.market_cap and aggregated_data['net_profit']:
            pe_ratio = to_decimal(price_data.market_cap) / to_decimal(aggregated_data['net_profit'])
        else:
            pe_ratio = None

        if price_data.market_cap:
            pb_ratio = to_decimal(price_data.market_cap) / to_decimal(balance_sheet_data['equity'] ) if balance_sheet_data['equity']  else None
            ps_ratio = to_decimal(price_data.market_cap) / to_decimal(aggregated_data['revenue'] ) if aggregated_data['revenue'] else None
        elif balance_sheet_data['shares']:
            pb_ratio = to_decimal(price_data.price) / to_decimal(balance_sheet_data['equity'] / balance_sheet_data['shares']) if balance_sheet_data['equity'] else None
            ps_ratio = to_decimal(price_data.price) / to_decimal(aggregated_data['revenue'] / balance_sheet_data['shares']) if aggregated_data['revenue']  else None
        else:
            pb_ratio = None
            ps_ratio = None

        # Enterprise Value calculation using market cap if available
        enterprise_value = to_decimal(price_data.market_cap) + to_decimal(balance_sheet_data['liabilities']) - to_decimal(balance_sheet_data['cash']) if (price_data.market_cap and balance_sheet_data['liabilities'] and balance_sheet_data['cash']) else None
        ev_ebit = to_decimal(enterprise_value) / to_decimal(aggregated_data['ebit']) if (enterprise_value and aggregated_data['ebit']) else None

        gross_profit_margin = to_decimal((aggregated_data['revenue'] - aggregated_data['cost_of_sales']) / aggregated_data['revenue']) if (aggregated_data['revenue'] and aggregated_data['cost_of_sales']) else None
        operating_profit_margin = to_decimal(aggregated_data['operating_profit'] / aggregated_data['revenue']) if (aggregated_data['revenue'] and aggregated_data['operating_profit']) else None
        net_profit_margin = to_decimal(aggregated_data['net_profit'] / aggregated_data['revenue']) if (aggregated_data['revenue'] and aggregated_data['net_profit'] )else None
        return_on_assets = to_decimal(aggregated_data['net_profit'] / balance_sheet_data['assets']) if (balance_sheet_data['assets'] and aggregated_data['net_profit'] ) else None
        return_on_equity = to_decimal(aggregated_data['net_profit'] / balance_sheet_data['equity']) if(balance_sheet_data['equity'] and aggregated_data['net_profit'] ) else None
        debt_to_equity = to_decimal(balance_sheet_data['liabilities'] / balance_sheet_data['equity']) if (balance_sheet_data['equity'] and balance_sheet_data['liabilities'] ) else None
        current_ratio = to_decimal(balance_sheet_data['current_assets'] / balance_sheet_data['current_liabilities']) if (balance_sheet_data['current_liabilities'] and balance_sheet_data['current_assets']) else None
        quick_ratio = to_decimal((balance_sheet_data['current_assets'] - balance_sheet_data['inventories']) / balance_sheet_data['current_liabilities']) if (balance_sheet_data['current_liabilities'] and balance_sheet_data['current_assets'] and balance_sheet_data['inventories']) else None

        dividend_yield = to_decimal(latest_divs / price_data.price *100)  if latest_divs else None
        before_dividend_yield = to_decimal(before_divs/ price_data.price*100)  if before_divs else None
    # Create or update the financial ratio record
    if date is None:
        date = last_div_update_date

    financial_ratio, created = FinancialRatio.objects.update_or_create(
        ticker=ticker,
        date=date,
        defaults={
            'pe_ratio': pe_ratio,
            'pb_ratio': pb_ratio,
            'ps_ratio': ps_ratio,
            'peg_ratio': peg_ratio,
            'ev_ebitda': ev_ebit,
            'gross_profit_margin': gross_profit_margin,
            'operating_profit_margin': operating_profit_margin,
            'net_profit_margin': net_profit_margin,
            'return_on_assets': return_on_assets,
            'return_on_equity': return_on_equity,
            'debt_to_equity': debt_to_equity,
            'current_ratio': current_ratio,
            'quick_ratio': quick_ratio,
            'dividend_yield':dividend_yield,
            'before_dividend_yield':before_dividend_yield
        }
    )

    # except FinancialData.DoesNotExist:
    #     print(f"Financial data for ticker {ticker} on {date} not found.")
    #     return None
    # except Exception as e:
    #     print(f"Error calculating ratios for ticker {ticker} on {date}: {str(e)}")
    #     return None

def to_decimal(value):
    try:
        return Decimal(str(value)) if value is not None and not math.isnan(value) else None
    except (InvalidOperation, ValueError):
        return None

class Command(BaseCommand):
    help = 'Calculate and store financial ratios for all tickers'

    def handle(self, *args, **kwargs):
        # Get unique tickers and dates from FinancialData
        tickers = FinancialReport.objects.values_list('ticker', flat=True).distinct()

        for ticker in tickers:
            dates = FinancialData.objects.filter(ticker=ticker).values_list('date', flat=True).distinct()
            if dates:
                for date in dates:
                    calculate_ratios(ticker, date)
                    print(f"Ratios calculated for {ticker} on {date}.")
            else:
                calculate_ratios(ticker, None)
                print(f"Only dividend Ratios calculated for {ticker} on {date}.")
