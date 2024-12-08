from django.core.management.base import BaseCommand
from django.db import transaction
from fin_data_cl.models import Security, FinancialRatio
from .calculate_ratios import FinancialRatioCalculationService


class Command(BaseCommand):
    help = 'Clean up old financial ratios and recalculate them with consistent dates'

    def handle(self, *args, **options):
        calculator = FinancialRatioCalculationService()

        # Get count of existing records for reporting
        old_count = FinancialRatio.objects.count()
        self.stdout.write(f"Found {old_count} existing ratio records")

        try:
            with transaction.atomic():
                # Delete all existing ratios
                self.stdout.write("Deleting all existing ratio records...")
                FinancialRatio.objects.all().delete()

                # Get active securities
                securities = Security.objects.filter(is_active=True)
                self.stdout.write(f"Processing {securities.count()} active securities")

                success_count = 0
                error_count = 0

                # Recalculate for each security
                for security in securities:
                    try:
                        self.stdout.write(f"Processing {security.ticker}...")
                        result = calculator.calculate_ratios(security, None)
                        if result:
                            success_count += 1
                        else:
                            error_count += 1
                            self.stdout.write(self.style.WARNING(
                                f"No ratios calculated for {security.ticker}"
                            ))
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(
                            f"Error processing {security.ticker}: {str(e)}"
                        ))

                # Report results
                new_count = FinancialRatio.objects.count()
                self.stdout.write(self.style.SUCCESS(
                    f"\nCleanup complete:"
                    f"\n- Deleted {old_count} old records"
                    f"\n- Successfully processed {success_count} securities"
                    f"\n- Encountered {error_count} errors"
                    f"\n- Created {new_count} new ratio records"
                ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Transaction failed, no changes made: {str(e)}"
            ))