import time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
import logging
from fin_data_cl.models import Exchange, Security, PriceData
from tqdm import tqdm  # Import tqdm --
logger = logging.getLogger(__name__)
from fin_data_cl.utils.Price_Update_manager import PriceDataFetcher  # Import the fetcher
from datetime import timedelta

class Command(BaseCommand):
    help = 'Update price data for securities in specified exchange with optional cleanup'

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
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean existing price data before updating'
        )

    def cleanup_price_data(self, securities):
        """
        Carefully clean up price data for the specified securities.
        Returns the number of records deleted.
        """
        try:
            with transaction.atomic():
                # Get count before deletion for reporting
                initial_count = PriceData.objects.filter(
                    security__in=securities
                ).count()

                logger.info(f"Found {initial_count} price records to delete")

                # Delete the price data
                deleted = PriceData.objects.filter(
                    security__in=securities
                ).delete()

                logger.info(f"Successfully deleted {deleted[0]} price records")
                return deleted[0]

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise

    def handle(self, *args, **options):
        start_time = timezone.now()
        exchange_code = options['exchange'].upper()
        specific_security = options.get('security')
        should_cleanup = options.get('cleanup', False)

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

            deleted_count = 0
            if should_cleanup:
                logger.info("Starting price data cleanup...")
                try:
                    deleted_count = self.cleanup_price_data(securities)
                    logger.info(f"Cleanup completed. Deleted {deleted_count} records.")
                except Exception as e:
                    logger.error(f"Cleanup failed: {str(e)}")
                    return

            # Initialize fetcher
            fetcher = PriceDataFetcher(exchange)
            total_records = 0
            failed_securities = []

            # Always fetch previous day's data first to ensure consistency
            target_date = timezone.now().date() - timedelta(days=1)

            # Process each security
            for security in tqdm(securities, desc="Updating securities"):
                try:
                    with transaction.atomic():
                        # First ensure we have yesterday's data
                        price_data_list = fetcher.fetch_data(
                            security,
                            use_previous_day=True
                        )

                        if price_data_list:
                            # Ensure we don't have any future dates
                            valid_data = [
                                data for data in price_data_list
                                if data['date'] <= target_date
                            ]

                            if valid_data:
                                PriceData.objects.bulk_create([
                                    PriceData(**data) for data in valid_data
                                ], ignore_conflicts=True)

                                total_records += len(valid_data)
                                logger.info(
                                    f"Added {len(valid_data)} records for {security.ticker}"
                                )

                                # Now check if today's data is available (market is closed)
                                if timezone.now().time() > exchange.trading_end:
                                    today_data = fetcher.fetch_data(
                                        security,
                                        use_previous_day=False
                                    )
                                    if today_data:
                                        PriceData.objects.bulk_create([
                                            PriceData(**data) for data in today_data
                                        ], ignore_conflicts=True)
                                        total_records += len(today_data)
                        else:
                            failed_securities.append(security.ticker)

                        # Respect API rate limits
                        time.sleep(0.5)

                except Exception as e:
                    failed_securities.append(security.ticker)
                    logger.error(f"Error processing {security.ticker}: {str(e)}")

            # Log summary
            duration = timezone.now() - start_time
            logger.info(
                f"\nUpdate completed for {exchange.name}:"
                f"\n- Cleaned up {deleted_count} old records"
                f"\n- Added {total_records} new records"
                f"\n- Duration: {duration.total_seconds():.1f} seconds"
                f"\n- Failed securities: {', '.join(failed_securities) if failed_securities else 'None'}"
            )

        except Exchange.DoesNotExist:
            logger.error(f"Exchange {exchange_code} not found")
        except Exception as e:
            logger.error(f"Command failed: {str(e)}")