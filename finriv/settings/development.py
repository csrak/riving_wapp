from .base import *
from datetime import timedelta
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-q(f&!^own^%p_a2_gt)ekepz$jj(axiv*3ba8@cwz2^p*0$a1o"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# SQLite for local development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_moved.sqlite3",
    }
}

# Celery (Optional in development)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

CELERY_BEAT_SCHEDULE = {
    'process_data_and_ratios_every_day': {
        'task': 'myapp.tasks.process_data_and_ratios',
        'schedule': timedelta(days=1),
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'fin_data_cl': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}