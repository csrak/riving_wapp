# fin_data_cl/apps.py

from django.apps import AppConfig


class FinDataClConfig(AppConfig):
    name = 'fin_data_cl'

    # fin_data_cl/apps.py

    def ready(self):
        """
        Initialize the application when Django starts.
        """
        # Only run scheduler initialization in the main process
        import sys
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            try:
                from django_q.models import Schedule
                from django.utils import timezone
                import json
                import logging

                logger = logging.getLogger(__name__)

                # Check if the SCL price update schedule exists
                if not Schedule.objects.filter(
                        func='fin_data_cl.tasks.update_price_data',  # Use the new function
                ).exists():
                    # Create a new schedule with a valid next_run value
                    Schedule.objects.create(
                        name='Daily SCL Price Update',
                        func='fin_data_cl.tasks.update_price_data',  # Update this
                        kwargs=json.dumps({"exchange": "SCL"}),  # This is simpler now
                        schedule_type=Schedule.DAILY,
                        repeats=-1,
                        next_run=timezone.now() + timezone.timedelta(minutes=5)
                    )
                    logger.info("Created daily SCL price update schedule")
            except Exception as e:
                logger.error(f"Failed to schedule price updates: {str(e)}")