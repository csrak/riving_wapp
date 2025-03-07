# utils/Price_Update_manager.py
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
from fin_data_cl.models import Exchange, Security, PriceData
import requests

# Import the fetcher from your command file

# Configure logging
logger = logging.getLogger(__name__)

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})

class PriceDataFetcher:
    """Handles fetching and processing of price data from Yahoo Finance"""

    def __init__(self, exchange: Exchange, max_retries: int = 3, retry_delay: int = 5):
        self.exchange = exchange
        self.max_retries = max_retries  # Default max retries
        self.retry_delay = retry_delay  # Default delay in seconds
        self.manual_retry_mode = False  # Flag for manual retry mode

    def old_decimal(self, value) -> Optional[Decimal]:
        """Convert value to Decimal, handling None and invalid values"""
        try:
            return Decimal(str(value)) if value is not None else None
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def to_decimal(value):
        if str(value) in [None, 'NaN', 'nan', '']:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    def fetch_history_with_retry(self, stock, start_date, end_date) -> tuple:
        """
        Fetch history data with automatic retry logic

        Returns:
            Tuple: (DataFrame, success_status)
        """
        attempts = 0
        delay = self.retry_delay

        while attempts < self.max_retries:
            try:
                hist = stock.history(
                    start=start_date,
                    end=end_date + timedelta(days=1)  # Include end_date
                )

                return hist, True

            except Exception as e:
                attempts += 1
                retry_msg = f"Rate limit or API error on attempt {attempts}/{self.max_retries}: {str(e)}"

                if "Too Many Requests" in str(e):
                    logger.warning(f"{retry_msg} - Rate limiting detected")
                else:
                    logger.warning(f"{retry_msg}")

                if attempts < self.max_retries:
                    logger.info(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Max retries ({self.max_retries}) exceeded")
                    return None, False

        return None, False  # Should never reach here, but just in case

    def fetch_info_with_retry(self, stock) -> tuple:
        """
        Fetch stock info with automatic retry logic

        Returns:
            Tuple: (market_cap, success_status)
        """
        attempts = 0
        delay = self.retry_delay

        while attempts < self.max_retries:
            try:
                market_cap = self.to_decimal(stock.info.get('marketCap'))
                return market_cap, True

            except Exception as e:
                attempts += 1
                retry_msg = f"Error fetching market cap on attempt {attempts}/{self.max_retries}: {str(e)}"

                if "Too Many Requests" in str(e):
                    logger.warning(f"{retry_msg} - Rate limiting detected")
                else:
                    logger.warning(retry_msg)

                if attempts < self.max_retries:
                    logger.info(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Max retries ({self.max_retries}) exceeded when fetching market cap")
                    return None, False

        return None, False

    def fetch_data(self, security: Security, use_previous_day: bool = False) -> List[Dict]:
        """
        Fetch price data for a single security starting from the appropriate date
        Args:
            security: Security object to fetch data for
            use_previous_day: If True, fetch data up to previous trading day instead of today
        """
        price_data_list = []
        full_symbol = f"{security.ticker}.{self.exchange.suffix}"

        try:
            start_date = PriceData.get_start_date(security)
            today = timezone.now().date()

            if use_previous_day:
                end_date = today - timedelta(days=1)
            else:
                end_date = today

            if start_date >= end_date:
                logger.info(f"Data already up to date for {full_symbol}")
                return []

            logger.info(
                f"Fetching {full_symbol} data from {start_date} to {end_date}"
            )

            stock = yf.Ticker(full_symbol, session = session )

            # Fetch history with retries
            hist, hist_success = self.fetch_history_with_retry(stock, start_date, end_date)

            if not hist_success:
                if self.manual_retry_mode:
                    user_input = input(f"Failed to fetch data for {full_symbol}. Retry? (y/n): ")
                    if user_input.lower() == 'y':
                        logger.info(f"Manual retry for {full_symbol}...")
                        hist, hist_success = self.fetch_history_with_retry(stock, start_date, end_date)
                    else:
                        logger.info(f"Manual skip for {full_symbol}")
                        return []
                else:
                    logger.error(f"Failed to fetch history data for {full_symbol} after {self.max_retries} attempts")
                    return []

            # Handle empty DataFrame
            if hist is None or hist.empty:
                logger.warning(f"No new data returned for {full_symbol}")
                # Add diagnostic info
                logger.info(f"Diagnostic info for {full_symbol}: start_date={start_date}, end_date={end_date}")

                # Try with a wider date range for diagnostics
                try:
                    wider_start = start_date - timedelta(days=30)
                    logger.info(f"Trying wider date range for diagnostics: {wider_start} to {end_date}")
                    wider_hist, _ = self.fetch_history_with_retry(stock, wider_start, end_date)

                    if wider_hist is not None and not wider_hist.empty:
                        logger.info(
                            f"Found data with wider range: {len(wider_hist)} days from {wider_hist.index.min().date()} to {wider_hist.index.max().date()}")
                    else:
                        logger.warning(f"No data found even with wider date range for {full_symbol}")
                except Exception as diag_err:
                    logger.warning(f"Error during diagnostic check: {str(diag_err)}")

                return []

            # Fetch market cap with retries
            market_cap, _ = self.fetch_info_with_retry(stock)

            current_time = timezone.now()
            for date, row in hist.iterrows():
                try:
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
                except Exception as row_err:
                    logger.warning(f"Error processing row for {full_symbol} on {date}: {str(row_err)}")
                    # Continue with next row instead of failing entire security

            return price_data_list

        except Exception as e:
            logger.error(f"Error fetching data for {full_symbol}: {str(e)}")
            return []


class PriceUpdateManager:
    """
    Coordinates between the scheduler and price update command,
    providing enhanced monitoring and control
    """

    def __init__(self, exchange: Exchange, max_retries: int = 3, retry_delay: int = 5):
        self.exchange = exchange
        self.fetcher = PriceDataFetcher(exchange, max_retries, retry_delay)
        self.total_records_updated = 0
        self.last_update_stats = {}

    def set_manual_retry_mode(self, enabled: bool = True):
        """Enable or disable manual retry mode"""
        self.fetcher.manual_retry_mode = enabled
        logger.info(f"Manual retry mode {'enabled' if enabled else 'disabled'}")

    def execute_update(self, use_previous_day: bool = False) -> bool:
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
                            price_data_list = self.fetcher.fetch_data(security, use_previous_day)

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

                    # Respect API rate limits - increased delay to avoid rate limiting
                    time.sleep(1.0)  # Increased from 0.5 to 1.0 second

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