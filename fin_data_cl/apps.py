# fin_data_cl/apps.py

from django.apps import AppConfig


class FinDataClConfig(AppConfig):
    name = 'fin_data_cl'

    def ready(self):
        """
        Initialize the application when Django starts.
        """
        # Only run scheduler initialization in the main process
        import sys
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            try:
                # Import and initialize the scheduler
                from django_q.models import Schedule
                from django.utils import timezone
                import json
                import logging

                logger = logging.getLogger(__name__)

                # Check if the SCL price update schedule exists
                if not Schedule.objects.filter(
                        func='django.core.management.call_command',
                        kwargs__contains='"exchange": "SCL"'
                ).exists():
                    # Create a new schedule with a valid next_run value
                    # The key fix is here - ensuring next_run has a valid timezone-aware datetime
                    Schedule.objects.create(
                        name='Daily SCL Price Update',
                        func='django.core.management.call_command',
                        args='price_update',
                        kwargs=json.dumps({"exchange": "SCL"}),
                        schedule_type=Schedule.DAILY,
                        repeats=-1,
                        next_run=timezone.now() + timezone.timedelta(minutes=5)  # Start in 5 minutes
                    )
                    logger.info("Created daily SCL price update schedule")
            except Exception as e:
                logger.error(f"Failed to schedule price updates: {str(e)}")