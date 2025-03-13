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
    'users_app',
    'portfolios',
    'metrics_an',
    'widget_tweaks',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    'django.contrib.staticfiles',
    'contacts',
    'django_extensions',
    'management_commands',
    'rest_framework',
    'django_filters',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    #'users_app.middleware.LoginRequiredMiddleware',
]

ROOT_URLCONF = "finriv.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'finriv.context_processors.google_analytics',  # Add this line
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
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Directory where collectstatic will collect files
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


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

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Changed from IsAuthenticated
    ],
}
API_BASE_URL = '/api/v1/' #To save time writign api calls

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
DEFAULT_FROM_EMAIL = 'finriv.app@gmail.com'  # Your verified Gmail

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'your.actual@email.com')
