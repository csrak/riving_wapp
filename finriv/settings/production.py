from .base import *
from datetime import timedelta
# Use environment variables for sensitive information
from decouple import config
SECRET_KEY = config('DJANGO_SECRET_KEY', default='None')
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = ['rivingwapp-production.up.railway.app']
CSRF_TRUSTED_ORIGINS = ['https://rivingwapp-production.up.railway.app']
# Example: Using PostgreSQL in production
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///db.sqlite3'), conn_max_age=600, ssl_require=True
    )
}
PORT = int(config('PORT',  default=8080))
# Security settings
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# # Celery (Optional in production)
# CELERY_BROKER_URL = 'redis://redis:6379/0'
# CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'UTC'
#
# CELERY_BEAT_SCHEDULE = {
#     'process_data_and_ratios_every_day': {
#         'task': 'myapp.tasks.process_data_and_ratios',
#         'schedule': timedelta(days=1),
#     },
# }
# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'WARNING',
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
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')  # Set in environment variables
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')  # Set in environment variables