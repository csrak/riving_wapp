import time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
import logging
from fin_data_cl.models import Exchange, Security, PriceData
from tqdm import tqdm  # Import tqdm --
logger = logging.getLogger(__name__)
from fin_data_cl.utils.Price_Update_manager import PriceDataFetcher  # Import the fetcher

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
        exchange_code = options['exchange'].upper()
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
            for security in tqdm(securities, desc="Updating securities"):
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