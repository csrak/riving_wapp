# management_commands/management/commands/migrate_to_railway.py

import json
import logging
from pathlib import Path
from datetime import datetime
import psycopg2
from urllib.parse import urlparse
from decouple import config

from django.core.management.base import BaseCommand, CommandError
from django.core import management


class Command(BaseCommand):
    help = 'Safely dump data from Django and load to Railway PostgreSQL'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_apps = [
            'fin_data_cl',
        ]

    def add_arguments(self, parser):
        default_output = f"railway_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        parser.add_argument(
            '-o', '--output',
            type=str,
            default=default_output,
            help=f'Output JSON file path (default: {default_output})'
        )
        parser.add_argument(
            '-a', '--action',
            type=str,
            choices=['dump', 'load', 'both'],
            default='both',
            help='Action to perform (default: both)'
        )
        parser.add_argument(
            '--railway-url',
            type=str,
            help='Railway PostgreSQL URL (defaults to DATABASE_URL from .env)'
        )

    def setup_logging(self):
        """Configure logging for the migration process."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('railway_migration.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def dump_data(self, output_file: Path) -> bool:
        """Dump data from Django using dumpdata."""
        try:
            self.logger.info(f"Starting data dump to {output_file}")
            combined_data = {}

            for app_name in self.target_apps:
                self.logger.info(f"Dumping {app_name}...")
                temp_file = f"{app_name}_temp.json"

                try:
                    # Use dumpdata with natural keys for better compatibility
                    management.call_command(
                        'dumpdata',
                        app_name,
                        natural_foreign=True,
                        natural_primary=True,
                        indent=2,
                        output=temp_file
                    )

                    if Path(temp_file).exists() and Path(temp_file).stat().st_size > 2:
                        with open(temp_file, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for item in data:
                                    model = item['model']
                                    if model not in combined_data:
                                        combined_data[model] = []
                                    combined_data[model].append(item)
                    else:
                        self.logger.warning(f"No data found for {app_name}")

                finally:
                    # Clean up temp file
                    Path(temp_file).unlink(missing_ok=True)

            if combined_data:
                with open(output_file, 'w') as f:
                    json.dump(combined_data, f, indent=2)

                total_records = sum(len(records) for records in combined_data.values())
                self.logger.info(
                    f"Saved {total_records} records from "
                    f"{len(combined_data)} models to {output_file}"
                )
                return True

            self.logger.error("No data was dumped")
            return False

        except Exception as e:
            self.logger.error(f"Failed to dump data: {str(e)}")
            return False

    def load_to_railway(self, input_file: Path, railway_url: str) -> bool:
        """Load data directly to Railway PostgreSQL."""
        try:
            self.logger.info("Starting load to Railway PostgreSQL")

            if not input_file.exists():
                raise CommandError(f"Input file not found: {input_file}")

            # Parse the Railway URL and connect
            url = urlparse(railway_url)
            conn = psycopg2.connect(
                dbname=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
            )

            with open(input_file, 'r') as f:
                data = json.load(f)

            total_processed = 0
            total_errors = 0

            with conn:
                with conn.cursor() as cur:
                    # Process each model's data
                    for model_name, records in data.items():
                        table_name = model_name.replace('.', '_')
                        self.logger.info(f"\nProcessing {len(records)} records for {table_name}")

                        for record in records:
                            try:
                                fields = record['fields']
                                pk = record.get('pk')

                                if pk:
                                    fields['id'] = pk

                                # Filter out None values
                                fields = {k: v for k, v in fields.items() if v is not None}

                                columns = list(fields.keys())
                                values = list(fields.values())

                                sql = f"""
                                    INSERT INTO {table_name} ({', '.join(columns)})
                                    VALUES ({', '.join(['%s'] * len(columns))})
                                    ON CONFLICT (id) 
                                    DO UPDATE SET {
                                ', '.join(f"{col} = EXCLUDED.{col}"
                                          for col in columns)
                                }
                                """

                                cur.execute(sql, values)
                                total_processed += 1

                                if total_processed % 1000 == 0:
                                    conn.commit()
                                    self.logger.info(f"Processed {total_processed} records")

                            except Exception as e:
                                total_errors += 1
                                conn.rollback()
                                self.logger.error(
                                    f"Error loading record into {table_name}: {str(e)}"
                                )
                                continue

            conn.close()
            self.logger.info(
                f"Loading completed: "
                f"Processed {total_processed} records, "
                f"Encountered {total_errors} errors"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to load to Railway: {str(e)}")
            return False

    def handle(self, *args, **options):
        self.logger = self.setup_logging()

        output_file = Path(options['output'])
        action = options['action']

        # Get Railway URL from command line or environment
        railway_url = options['railway_url'] or config('DATABASE_URL', default=None)

        if not railway_url and action in ['load', 'both']:
            raise CommandError(
                "Railway URL must be provided either via --railway-url or "
                "DATABASE_URL in .env"
            )

        try:
            if action in ['dump', 'both']:
                self.stdout.write("Starting data dump...")
                if not self.dump_data(output_file):
                    raise CommandError("Data dump failed")
                self.stdout.write(self.style.SUCCESS("Data dump completed"))

            if action in ['load', 'both']:
                self.stdout.write("Starting data load to Railway...")
                if not self.load_to_railway(output_file, railway_url):
                    raise CommandError("Data load failed")
                self.stdout.write(self.style.SUCCESS("Data load completed"))

        except Exception as e:
            raise CommandError(f"Migration failed: {str(e)}")