import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Media Files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Application definition
INSTALLED_APPS = [
    'price_plots',
    'fin_data_cl',
    'django_q',
    'metrics_an',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    'django.contrib.staticfiles',
    'django_extensions',
    'management_commands',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "finriv.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "finriv.wsgi.application"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",  # Ensure this points to your static directory
]# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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
Q_CLUSTER = {
    'name': 'DjangoQ',
    'workers': 4,
    'timeout': 60,
    'retry': 120,
    'orm': 'default',  # Use Django ORM as the broker
}

# settings.py
PRICE_UPDATE_INTERVAL = int(os.getenv('PRICE_UPDATE_INTERVAL', 7200))  # minutes between updates
MIN_UPDATE_SPACING = int(os.getenv('MIN_UPDATE_SPACING', 3000))  # minimum minutes between updates
MAX_UPDATE_ATTEMPTS = int(os.getenv('MAX_UPDATE_ATTEMPTS', 3))  # max retry attempts per exchange
MAX_CONSECUTIVE_ERRORS = int(os.getenv('MAX_CONSECUTIVE_ERRORS', 5))  # max errors before critical alert

# Logging configuration for scheduler

ANALYSIS_CACHE_TIMEOUT = 60 * 15  # 15 minutes