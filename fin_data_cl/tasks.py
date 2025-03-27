# fin_data_cl/tasks.py

from django.core.management import call_command
from django.db import connection
from django_q.models import Schedule, Task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def reset_django_q_database():
    """
    Completely reset the Django-Q database tables and create a fresh price update schedule.
    This function is meant to be called during application startup to ensure a clean state.
    """
    try:
        # First, delete all existing schedules and tasks
        Schedule.objects.all().delete()
        Task.objects.all().delete()

        logger.info("Successfully cleared all Django-Q schedules and tasks")

        # Create a fresh price update schedule
        Schedule.objects.create(
            name='Daily SCL Price Update',
            func='fin_data_cl.tasks.update_price_data',
            kwargs='{"exchange": "SCL"}',  # Make sure this is a string, not a dict
            schedule_type=Schedule.DAILY,
            repeats=-1,
            next_run=timezone.now() + timezone.timedelta(minutes=10)
        )

        logger.info("Successfully created new price update schedule")
        return True
    except Exception as e:
        logger.error(f"Error resetting Django-Q database: {str(e)}")
        return False


def update_price_data(exchange='SCL'):
    """
    Run the price update command for the specified exchange.
    This function is designed to be called by Django-Q.
    """
    try:
        logger.info(f"Starting price update for exchange: {exchange}")
        call_command('price_update', exchange=exchange)
        logger.info(f"Successfully updated prices for {exchange}")
        return f"Successfully updated prices for {exchange}"
    except Exception as e:
        logger.error(f"Error updating prices for {exchange}: {str(e)}")
        return f"Error updating prices for {exchange}: {str(e)}"