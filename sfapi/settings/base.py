import os
import sys

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from pathlib import Path
from dotenv import load_dotenv

import logging.config
from django.utils.log import DEFAULT_LOGGING

# Load environment variables from .env file
load_dotenv()

# Determine environment based on command line arguments
TEST = 'test' in sys.argv
LOCAL = 'runserver' in sys.argv

ENVIRONMENT = os.getenv('ENVIRONMENT', 'test' if TEST else 'local')
RELEASE_VERSION = os.getenv('RELEASE_VERSION')
DEPLOYMENT_VERSION = os.getenv('DEPLOYMENT_VERSION')
IS_TESTING = os.getenv('IS_TESTING', 'False')

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')

SECRET_KEY = os.environ.get('SECRET_KEY')

# check if running local dev server - else default to DEBUG=False
if LOCAL:
    DEBUG = True
else:
    DEBUG = False

if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    if ENVIRONMENT == 'prod':
        # Prod only
        ALLOWED_HOSTS = ['salesforce.openstax.org']
    else:
        # All non-local and non-prod environments
        ALLOWED_HOSTS = [f"{ENVIRONMENT}.salesforce.openstax.org", f"{ENVIRONMENT}.salesforce.sandbox.openstax.org"]

ADMINS = ('SF Admin', 'sfadmin@openstax.org')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'ninja',
    'ninja_extra',
    'sf',
    'api',
    'users',
    'salesforce',
    'cacheops',
]

AUTH_USER_MODEL = 'users.User'
LOGIN_URL = '/admin/login/'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'healthcheck.middleware.HealthCheckMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True
# SECURE_SSL_REDIRECT = not DEBUG
#
# SECURE_HSTS_PRELOAD = True
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_SECONDS = 31536000  # 1 year

if DEBUG:
    CORS_ORIGIN_ALLOW_ALL = True
    MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')

ROOT_URLCONF = 'sfapi.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sfapi.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DATABASE_NAME', 'sfapi'),
        'USER': os.getenv('DATABASE_USER'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'HOST': os.getenv('DATABASE_HOST', 'localhost'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
    },
    'salesforce': {
        'ENGINE': 'salesforce.backend',
        'CONSUMER_KEY': os.getenv('SALESFORCE_CLIENT_ID', 'replaceme'),
        'CONSUMER_SECRET': os.getenv('SALESFORCE_CLIENT_SECRET', 'replaceme'),
        'USER': os.getenv('SALESFORCE_USERNAME', 'replaceme'),
        'PASSWORD': os.getenv('SALESFORCE_PASSWORD', 'replaceme') + os.getenv('SALESFORCE_SECURITY_TOKEN', 'replaceme'),
        'HOST': os.getenv('SALESFORCE_HOST', 'https://test.salesforce.com'),
    }
}

DATABASE_ROUTERS = [
    "salesforce.router.ModelRouter"
]

# Cache settings
# REDIS_USER = os.getenv('REDIS_USER')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_DB = os.getenv('REDIS_DB', '0')
REDIS_PROTOCOL = 'rediss' if REDIS_PASSWORD else 'redis'
REDIS_URL = os.getenv('REDIS_URL', f'{REDIS_PROTOCOL}://{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}')

if REDIS_PASSWORD:
    CACHEOPS_REDIS = f'{REDIS_PROTOCOL}://{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
else:
    CACHEOPS_REDIS = f'{REDIS_PROTOCOL}://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": REDIS_URL,
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#             "PASSWORD": REDIS_PASSWORD,
#             "IGNORE_EXCEPTIONS": True,  # this works without redis, so don't kill app if redis is down
#         },
#         "KEY_PREFIX": "sfapi",
#         "TIMEOUT": 60*15  # default to a 15-min cache unless specified
#     }
# }

CACHEOPS = {
    # Automatically cache any Adoption.objects.get() calls for 5 minutes
    'sf.adoption': {'ops': 'all', 'timeout': 60*5},

    # Automatically cache any Contact.objects.get() calls for 1 week, since contacts don't change often
    'sf.contact': {'ops': 'all', 'timeout': 60*60*24*7},
}
CACHEOPS_DEGRADE_ON_FAILURE = True


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'public', 'static')
STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# OpenStax SSO cookie settings
SSO_COOKIE_NAME = os.getenv('SSO_COOKIE_NAME', 'oxa')
SIGNATURE_PUBLIC_KEY = os.getenv('SSO_SIGNATURE_PUBLIC_KEY')
ENCRYPTION_PRIVATE_KEY = os.getenv('SSO_ENCRYPTION_PRIVATE_KEY')

# Sentry settings
sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.2, # 20% of transactions will be sent to sentry
    send_default_pii=True,  # this will send the user id of admin users only to sentry to help with debugging
    environment=ENVIRONMENT
)


# Cronjobs (when needed)
CRONTAB_COMMAND_PREFIX = os.getenv('CRONTAB_COMMAND_PREFIX', '')
CRONTAB_COMMAND_SUFFIX = os.getenv('CRONTAB_COMMAND_SUFFIX', '')
CRONTAB_LOCK_JOBS = os.getenv('CRONTAB_LOCK_JOBS') != 'False'


# Logging
LOGGING_CONFIG = None
LOGLEVEL = os.getenv('LOGLEVEL', 'error').upper()
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'healthcheck_filter': {
            '()': 'healthcheck.filter.HealthCheckFilter'
        },
    },
    'formatters': {
        'default': {
            # exact format is not important, this is the minimum information
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        },
        'django.server': DEFAULT_LOGGING['formatters']['django.server'],
    },
    'handlers': {
        # disable logs set with null handler
        'null': {
            'class': 'logging.NullHandler',
        },
        # console logs to stderr
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'django.server': {
            **DEFAULT_LOGGING['handlers']['django.server'],
            'filters': ['healthcheck_filter']
        },
    },
    'loggers': {
        # default for all undefined Python modules
        '': {
            'level': 'ERROR',
            'handlers': ['console'],
        },
        # Our application code
        'openstax': {
            'level': LOGLEVEL,
            'handlers': ['console'],
            'propagate': False,
        },
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        },
        'django.request': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        # Default runserver request logging
        'django.server': DEFAULT_LOGGING['loggers']['django.server'],
    },
})

# this is used by the deployment to override settings
# you can use it locally, but don't check it in
try:
    from .local import *
except ImportError:
    pass
