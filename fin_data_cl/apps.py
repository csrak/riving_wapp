# fin_data_cl/apps.py

from django.apps import AppConfig


class FinDataClConfig(AppConfig):
    name = 'fin_data_cl'

    def ready(self):
        # Import here to avoid AppRegistryNotReady exception
        from .schedulers import initialize_price_update_schedule

        # Initialize scheduled tasks
        initialize_price_update_schedule()