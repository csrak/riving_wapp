import time
import schedule
from datetime import datetime
import logging
from django.core.management.base import BaseCommand
from django.core import management
from django.conf import settings
from django.utils import timezone
import pytz
from fin_data_cl.models import Exchange, Security
from typing import Dict, Optional

# Configure logging with more detailed formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('price_updates.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ExchangeUpdateTracker:
    """
    Tracks the last successful update for each exchange to prevent
    redundant updates and help with error recovery
    """

    def __init__(self):
        self.last_updates: Dict[str, datetime] = {}
        self.failed_attempts: Dict[str, int] = {}

    def record_update(self, exchange_code: str, success: bool):
        """Record an update attempt and its result"""
        if success:
            self.last_updates[exchange_code] = timezone.now()
            self.failed_attempts[exchange_code] = 0
        else:
            self.failed_attempts[exchange_code] = (
                    self.failed_attempts.get(exchange_code, 0) + 1
            )

    def get_last_update(self, exchange_code: str) -> Optional[datetime]:
        """Get the last successful update time for an exchange"""
        return self.last_updates.get(exchange_code)

    def should_retry(self, exchange_code: str) -> bool:
        """Determine if we should retry updates for an exchange"""
        max_attempts = getattr(settings, 'MAX_UPDATE_ATTEMPTS', 3)
        return self.failed_attempts.get(exchange_code, 0) < max_attempts


class PriceUpdateScheduler:
    """
    Handles scheduling of price updates across multiple exchanges
    with improved tracking and error handling
    """

    def __init__(self):
        self.update_interval = getattr(settings, 'PRICE_UPDATE_INTERVAL', 30)
        self.min_update_spacing = getattr(settings, 'MIN_UPDATE_SPACING', 5)
        self.tracker = ExchangeUpdateTracker()

        # Load active exchanges that have securities
        self.exchanges = Exchange.objects.filter(
            security__is_active=True
        ).distinct()

        if not self.exchanges.exists():
            logger.warning("No active exchanges found with securities")

    def should_update_exchange(self, exchange: Exchange) -> bool:
        """
        Determine if an exchange should be updated based on trading hours
        and last update time
        """
        current_time = timezone.now()
        exchange_time = current_time.astimezone(pytz.timezone(exchange.timezone))

        # Check if we're in trading hours
        if not exchange.is_trading_time(exchange_time.time()):
            logger.debug(f"{exchange.name} - Outside trading hours")
            return False

        # Check minimum time between updates
        last_update = self.tracker.get_last_update(exchange.code)
        if last_update:
            minutes_since_update = (current_time - last_update).total_seconds() / 60
            if minutes_since_update < self.min_update_spacing:
                logger.debug(
                    f"{exchange.name} - Too soon to update "
                    f"({minutes_since_update:.1f} minutes since last update)"
                )
                return False

        return True

    def update_exchange(self, exchange: Exchange):
        """
        Execute price update for a specific exchange with error handling
        and update tracking
        """
        if not self.should_update_exchange(exchange):
            return

        try:
            logger.info(f"Starting scheduled price update for {exchange.name}")

            # Count active securities for this exchange
            security_count = Security.objects.filter(
                exchange=exchange,
                is_active=True
            ).count()

            if security_count == 0:
                logger.warning(f"No active securities found for {exchange.name}")
                return

            logger.info(f"Updating {security_count} securities for {exchange.name}")

            # Call the update command
            management.call_command(
                'update_price_data',
                exchange=exchange.code
            )

            self.tracker.record_update(exchange.code, success=True)
            logger.info(f"Completed scheduled update for {exchange.name}")

        except Exception as e:
            logger.error(f"Error updating {exchange.name}: {str(e)}")
            self.tracker.record_update(exchange.code, success=False)

            # Handle retry logic
            if self.tracker.should_retry(exchange.code):
                logger.info(f"Will retry update for {exchange.name} later")
            else:
                logger.error(
                    f"Exceeded maximum retry attempts for {exchange.name}. "
                    "Manual intervention may be required."
                )

    def schedule_all_exchanges(self):
        """Schedule updates for all active exchanges"""
        for exchange in self.exchanges:
            schedule.every(self.update_interval).minutes.do(
                self.update_exchange, exchange
            )
            logger.info(
                f"Scheduled {exchange.name} updates every {self.update_interval} minutes"
            )

    def run_scheduler(self):
        """Run the scheduler with enhanced error handling and monitoring"""
        logger.info("Starting price update scheduler")
        self.schedule_all_exchanges()

        consecutive_errors = 0
        max_consecutive_errors = getattr(settings, 'MAX_CONSECUTIVE_ERRORS', 5)

        while True:
            try:
                schedule.run_pending()
                consecutive_errors = 0
                time.sleep(60)  # Check every minute

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Scheduler error: {str(e)}")

                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(
                        f"Too many consecutive errors ({consecutive_errors}). "
                        "Scheduler needs attention!"
                    )
                    # You might want to add notification logic here

                time.sleep(300)  # Wait 5 minutes before retrying


class Command(BaseCommand):
    help = 'Start the automated multi-exchange price update scheduler'

    def handle(self, *args, **options):
        scheduler = PriceUpdateScheduler()
        self.stdout.write(
            self.style.SUCCESS('Starting multi-exchange price update scheduler...')
        )
        scheduler.run_scheduler()