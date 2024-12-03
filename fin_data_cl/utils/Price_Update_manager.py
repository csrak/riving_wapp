from typing import List, Optional
import logging
import time
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.core import management
from tqdm import tqdm
from typing import Optional, List, Dict
import yfinance as yf
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
# Import your models
from fin_data_cl.models import Exchange, Security, PriceData
# Import the fetcher from your command file


# Configure logging
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

class PriceUpdateManager:
    """
    Coordinates between the scheduler and price update command,
    providing enhanced monitoring and control
    """

    def __init__(self, exchange: Exchange):
        self.exchange = exchange
        self.fetcher = PriceDataFetcher(exchange)
        self.total_records_updated = 0
        self.last_update_stats = {}

    def execute_update(self) -> bool:
        """
        Executes the price update process with enhanced monitoring
        Returns: True if update was successful
        """
        start_time = timezone.now()
        success = True

        try:
            # Get active securities count before update
            securities = Security.objects.filter(
                exchange=self.exchange,
                is_active=True
            )

            if not securities.exists():
                logger.warning(f"No active securities found for {self.exchange.name}")
                return False

            total_records = 0
            failed_securities = []

            # Process each security with progress tracking
            with tqdm(securities, desc=f"Updating {self.exchange.name}") as pbar:
                for security in pbar:
                    try:
                        with transaction.atomic():
                            price_data_list = self.fetcher.fetch_data(security)

                            if price_data_list:
                                PriceData.objects.bulk_create(
                                    [PriceData(**data) for data in price_data_list],
                                    ignore_conflicts=True
                                )
                                total_records += len(price_data_list)

                            pbar.set_postfix(
                                records=total_records,
                                current=security.ticker
                            )

                    except Exception as e:
                        failed_securities.append(security.ticker)
                        logger.error(f"Error processing {security.ticker}: {str(e)}")
                        success = False

                    # Respect API rate limits
                    time.sleep(0.5)

            # Update statistics
            duration = timezone.now() - start_time
            self.last_update_stats = {
                'timestamp': timezone.now(),
                'duration': duration,
                'total_records': total_records,
                'securities_processed': securities.count(),
                'failed_securities': failed_securities,
                'success_rate': (securities.count() - len(failed_securities)) / securities.count()
            }

            self.total_records_updated += total_records

            logger.info(
                f"Update completed for {self.exchange.name}. "
                f"Added {total_records} records in {duration.total_seconds():.1f} seconds. "
                f"Failed securities: {', '.join(failed_securities) if failed_securities else 'None'}"
            )

            return success

        except Exception as e:
            logger.error(f"Update failed for {self.exchange.name}: {str(e)}")
            return False

    def get_update_statistics(self) -> dict:
        """Returns the statistics from the last update"""
        return self.last_update_stats

    @property
    def total_updates(self) -> int:
        """Returns the total number of records updated since instantiation"""
        return self.total_records_updated