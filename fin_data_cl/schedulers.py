# fin_data_cl/schedulers.py

from django_q.tasks import schedule
from django_q.models import Schedule
import logging

logger = logging.getLogger(__name__)


def initialize_price_update_schedule():
    """
    Initialize scheduled tasks for price updates.
    This should be called during application startup.
    """
    try:
        # Check if the schedule already exists to avoid duplicates
        if not Schedule.objects.filter(func='django.core.management.call_command',
                                       args='price_update',
                                       kwargs='{"exchange": "SCL"}').exists():
            # Schedule daily price updates for SCL exchange
            schedule('django.core.management.call_command',
                     'price_update',
                     kwargs={'exchange': 'SCL'},
                     schedule_type=Schedule.DAILY,
                     repeats=-1,  # Repeat indefinitely
                     next_run=None,  # Start on next scheduler cycle
                     name='Daily SCL Price Update')

            logger.info("Scheduled daily price updates for SCL exchange")
    except Exception as e:
        logger.error(f"Failed to schedule price updates: {str(e)}")