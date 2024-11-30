import time
import yfinance as yf
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
import logging
from typing import Optional, List, Dict
from fin_data_cl.models import Exchange, Security, PriceData

logger = logging.getLogger(__name__)


class PriceDataFetcher:
    """Handles fetching and processing of price data from Yahoo Finance"""

    def __init__(self, exchange: Exchange):
        self.exchange = exchange

    def to_decimal(self, value) -> Optional[Decimal]:
        """Convert value to Decimal, handling None and invalid values"""
        try:
            return Decimal(str(value)) if value is not None else None
        except (InvalidOperation, ValueError):
            return None

    def fetch_data(self, security: Security) -> List[Dict]:
        """
        Fetch price data for a single security starting from the appropriate date
        """
        price_data_list = []
        full_symbol = f"{security.ticker}.{self.exchange.suffix}"

        try:
            # Determine the start date
            start_date = PriceData.get_start_date(security)
            today = timezone.now().date()

            if start_date >= today:
                logger.info(f"Data already up to date for {full_symbol}")
                return []

            logger.info(
                f"Fetching {full_symbol} data from {start_date} to {today}"
            )

            # Fetch data from Yahoo Finance
            stock = yf.Ticker(full_symbol)
            hist = stock.history(
                start=start_date,
                end=today + timedelta(days=1)  # Include today
            )

            if hist.empty:
                logger.warning(f"No new data returned for {full_symbol}")
                return []

            # Try to get market cap once
            try:
                market_cap = self.to_decimal(stock.info.get('marketCap'))
            except Exception:
                market_cap = None
                logger.warning(f"Failed to fetch market cap for {full_symbol}")

            # Process each day's data
            current_time = timezone.now()
            for date, row in hist.iterrows():
                price_data = {
                    'security': security,
                    'date': date.date(),
                    'price': self.to_decimal(row.get('Close')),
                    'market_cap': market_cap,
                    'open_price': self.to_decimal(row.get('Open')),
                    'high_price': self.to_decimal(row.get('High')),
                    'low_price': self.to_decimal(row.get('Low')),
                    'close_price': self.to_decimal(row.get('Close')),
                    'adj_close': self.to_decimal(row.get('Close')),
                    'volume': row.get('Volume') or 0,
                    'created_at': current_time,
                    'updated_at': current_time
                }
                price_data_list.append(price_data)

            return price_data_list

        except Exception as e:
            logger.error(f"Error fetching data for {full_symbol}: {str(e)}")
            return []


class Command(BaseCommand):
    help = 'Update price data for securities in specified exchange'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exchange',
            type=str,
            required=True,
            help='Exchange code to update (e.g., NYSE)'
        )
        parser.add_argument(
            '--security',
            type=str,
            help='Specific security ticker to update (optional)'
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        exchange_code = options['exchange']
        specific_security = options.get('security')

        try:
            # Get exchange and securities
            exchange = Exchange.objects.get(code=exchange_code)
            securities = Security.objects.filter(
                exchange=exchange,
                is_active=True
            )
            if specific_security:
                securities = securities.filter(ticker=specific_security)

            if not securities.exists():
                logger.warning(f"No active securities found for {exchange.name}")
                return

            # Initialize fetcher
            fetcher = PriceDataFetcher(exchange)
            total_records = 0

            # Process each security
            for security in securities:
                try:
                    with transaction.atomic():
                        price_data_list = fetcher.fetch_data(security)

                        if price_data_list:
                            PriceData.objects.bulk_create([
                                PriceData(**data) for data in price_data_list
                            ], ignore_conflicts=True)

                            total_records += len(price_data_list)
                            logger.info(
                                f"Added {len(price_data_list)} records for {security.ticker}"
                            )

                        # Respect API rate limits
                        time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error processing {security.ticker}: {str(e)}")

            # Log summary
            duration = timezone.now() - start_time
            logger.info(
                f"Update completed for {exchange.name}. "
                f"Added {total_records} records in {duration.total_seconds():.1f} seconds"
            )

        except Exchange.DoesNotExist:
            logger.error(f"Exchange {exchange_code} not found")
        except Exception as e:
            logger.error(f"Command failed: {str(e)}")