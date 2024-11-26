import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from fin_data_cl.models import Dividend
from django.db import transaction
from pathlib import Path
from finriv.settings import BASE_DIR, MEDIA_ROOT

import os

G_datafold = Path(MEDIA_ROOT) / 'Data' / 'Chile'
G_root_dir = Path(BASE_DIR)

class Command(BaseCommand):
    help = 'Import dividend data from CSV file and save to the database.'

    def handle(self, *args, **kwargs):
        # Define the input CSV file path
        input_file_path = G_datafold / Path('Dividends/Dividends_2013_2024.csv')

        # Read and process the CSV file
        if not input_file_path.exists():
            self.stdout.write(self.style.ERROR(f'Error: File {input_file_path} does not exist.'))
            return

        self.stdout.write('Reading and importing dividend data from CSV...')
        try:
            dividend_data = self.read_csv_file(input_file_path)
            self.save_dividend_data(dividend_data)
            self.stdout.write(self.style.SUCCESS('Successfully imported dividend data.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error while importing dividend data: {e}'))

    def read_csv_file(self, file_path):
        """Reads the CSV file and processes the data."""
        dividend_data = []
        with open(file_path, mode='r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    dividend = self.process_row(row)
                    dividend_data.append(dividend)
                except ValueError as e:
                    self.stdout.write(self.style.WARNING(f'Skipping row due to error: {e}'))
        return dividend_data
    @staticmethod
    def process_row(row):
        """Processes a single row of CSV data."""
        try:
            date = row['Date']
            ticker = row['Ticker']
            amount = Decimal(row['Dividend'])
            dividend_type = int(float(row['DividendType']))  # Cast to float first, then to int

            return Dividend(
                date=date,
                ticker=ticker,
                amount=amount,
                dividend_type=dividend_type
            )
        except (InvalidOperation, KeyError, ValueError) as e:
            raise ValueError(f"Invalid data in row {row}: {e}")

    @transaction.atomic #Not sure if we need it to be atomic but for now is okay
    def save_dividend_data(self, dividend_data):
        """Saves the processed dividend data into the database."""
        for dividend in dividend_data:
            # Using `get_or_create` to avoid duplication of entries based on unique fields
            obj, created = Dividend.objects.get_or_create(
                date=dividend.date,
                ticker=dividend.ticker,
                defaults={
                    'amount': dividend.amount,
                    'dividend_type': dividend.dividend_type
                }
            )
            if not created:
                # If the entry already exists, update the data
                obj.amount = dividend.amount
                obj.dividend_type = dividend.dividend_type
                obj.save()

            self.stdout.write(self.style.SUCCESS(f'{"Created" if created else "Updated"} dividend entry for {dividend.ticker} on {dividend.date}'))

