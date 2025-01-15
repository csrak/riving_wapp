# myproject/celery.py

from __future__ import absolute_import, unicode_literals
import os
from celery_app import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finriv.settings.development')

app = Celery('finriv')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
