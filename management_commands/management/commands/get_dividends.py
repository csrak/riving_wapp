import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from django.utils import timezone
import logging
from typing import Dict, List
from fin_data_cl.models import Security, Exchange, DividendData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dividend_imports.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DividendImporter:
    """Handles the processing and importing of dividend data"""

    def __init__(self):
        # Get Santiago Stock Exchange instance
        self.exchange = Exchange.objects.get(code='SCL')
        self.data_folder = Path(settings.MEDIA_ROOT) / 'Data' / 'Chile'

    def process_row(self, row: Dict) -> DividendData:
        """
        Process a single row of dividend data.
        Now includes security validation and proper model creation.
        """
        try:
            ticker = row['Ticker']
            # Get or create security
            security, created = Security.objects.get_or_create(
                ticker=ticker,
                exchange=self.exchange,
                defaults={'name': f"{ticker} Security"}
            )

            if created:
                logger.info(f"Created new security entry for {ticker}")

            current_time = timezone.now()

            return DividendData(
                security=security,
                date=row['Date'],
                amount=Decimal(row['Dividend']),
                dividend_type=int(float(row['DividendType'])),
                created_at=current_time,
                updated_at=current_time
            )
        except (InvalidOperation, KeyError, ValueError) as e:
            raise ValueError(f"Invalid data in row {row}: {e}")

    def read_csv_file(self, file_path: Path) -> List[DividendData]:
        """Read and process the CSV file"""
        dividend_data = []
        with open(file_path, mode='r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    dividend = self.process_row(row)
                    dividend_data.append(dividend)
                except ValueError as e:
                    logger.warning(f'Skipping row due to error: {e}')
        return dividend_data

    @transaction.atomic
    def save_dividend_data(self, dividend_data: List[DividendData]):
        """Save processed dividend data to database"""
        updates = 0
        creates = 0

        for dividend in dividend_data:
            try:
                # Try to find existing record
                existing = DividendData.objects.filter(
                    security=dividend.security,
                    date=dividend.date
                ).first()

                if existing:
                    # Update existing record
                    existing.amount = dividend.amount
                    existing.dividend_type = dividend.dividend_type
                    existing.updated_at = timezone.now()
                    existing.save()
                    updates += 1
                else:
                    # Create new record
                    dividend.save()
                    creates += 1

            except Exception as e:
                logger.error(
                    f"Error saving dividend for {dividend.security.ticker} "
                    f"on {dividend.date}: {str(e)}"
                )

        return creates, updates


class Command(BaseCommand):
    help = 'Import dividend data from CSV file and save to the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Specific CSV file to import (optional)',
            default='Dividends/Dividends_2013_2024.csv',  # Set the default value here
        )

    def handle(self, *args, **options):
        start_time = timezone.now()

        self.stdout.write("Synchronizing exchanges...")
        created, updated = Exchange.sync_from_registry()
        self.stdout.write(f"Exchanges synchronized: {created} created, {updated} updated.")

        importer = DividendImporter()


        # Determine input file path
        file_name = options.get('file')
        input_file_path = importer.data_folder / file_name

        if not input_file_path.exists():
            logger.error(f'Error: File {input_file_path} does not exist.')
            return

        try:
            logger.info('Reading and importing dividend data from CSV...')
            dividend_data = importer.read_csv_file(input_file_path)

            creates, updates = importer.save_dividend_data(dividend_data)

            duration = timezone.now() - start_time
            logger.info(
                f'Import completed in {duration.total_seconds():.1f} seconds. '
                f'Created: {creates}, Updated: {updates}'
            )

        except Exception as e:
            logger.error(f'Error during dividend import: {str(e)}')
