import time
import pandas as pd
from tqdm import tqdm
from django.core.management.base import BaseCommand
from fin_data_cl.models import PriceData, FinancialData
import datetime
from decimal import Decimal, InvalidOperation
import yfinance as yf  # Yahoo Finance API
from django.db import transaction

# Function to ensure values are compatible with Django DecimalField
def to_decimal(value):
    try:
        return Decimal(str(value)) if value is not None else None
    except (InvalidOperation, ValueError):
        return None


def fetch_stock_data(ticker, period="1mo"):
    """
    Fetch historical stock data for a given ticker
    Returns a list of PriceData objects
    """
    ticker_sn = ticker + '.SN'
    price_data_objects = []

    try:
        stock = yf.Ticker(ticker_sn)
        hist = stock.history(period=period)

        if hist.empty:
            print(f"Warning: No data returned for ticker {ticker_sn}")
            return []

        # Get market cap from stock info
        stock_info = stock.info
        market_cap = to_decimal(stock_info.get('marketCap'))

        # Process each day's data
        for date, row in hist.iterrows():
            # Ensure all values are valid before creating the object
            price_data = PriceData(
                ticker=ticker,
                date=date.date(),
                price=to_decimal(row.get('Close')) or Decimal(0),  # Default to 0 if invalid
                market_cap=market_cap,
                open_price=to_decimal(row.get('Open')),
                high_price=to_decimal(row.get('High')),
                low_price=to_decimal(row.get('Low')),
                close_price=to_decimal(row.get('Close')),
                adj_close=to_decimal(row.get('Close')),
                volume=row.get('Volume') or 0  # Default to 0 if volume is missing
            )
            price_data_objects.append(price_data)

        return price_data_objects

    except Exception as e:
        print(f"Error fetching data for ticker {ticker_sn}: {str(e)}")
        return []


class Command(BaseCommand):
    help = 'Populate historical price data for each ticker using the Yahoo Finance API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period',
            type=str,
            default='1mo',
            help='Period to fetch (e.g., 1mo, 3mo, 6mo, 1y, 2y, 5y, max)'
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Replace existing data for the period'
        )

    def handle(self, *args, **kwargs):
        period = kwargs['period']
        replace = kwargs['replace']

        # Get list of unique tickers from FinancialData
        tickers = FinancialData.objects.values_list('ticker', flat=True).distinct()
        if replace:
            PriceData.objects.all().delete()
            print("All existing PriceData entries have been deleted.")

        # Initialize progress bar
        with tqdm(total=len(tickers), desc="Fetching Historical Data") as pbar:
            for ticker in tickers:
                try:
                    # Fetch historical data
                    price_data_objects = fetch_stock_data(ticker, period=period)

                    if price_data_objects:
                        with transaction.atomic():
                            # If replace flag is set, delete existing data for this period
                            if replace:
                                earliest_date = min(obj.date for obj in price_data_objects)
                                latest_date = max(obj.date for obj in price_data_objects)
                                PriceData.objects.filter(
                                    ticker=ticker,
                                    date__range=(earliest_date, latest_date)
                                ).delete()

                            # Bulk create new records
                            PriceData.objects.bulk_create(
                                price_data_objects,
                                ignore_conflicts=True  # Skip if record already exists
                            )

                        print(f"Successfully saved {len(price_data_objects)} records for {ticker}")

                    # Add small delay to avoid hitting API limits
                    time.sleep(0.5)

                except Exception as e:
                    print(f"Error processing {ticker}: {str(e)}")

                finally:
                    pbar.update(1)

        self.stdout.write(self.style.SUCCESS('Data import completed'))