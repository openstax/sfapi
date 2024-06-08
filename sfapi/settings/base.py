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

# Override this in local.py to use an easier way to locally authenticate with Salesforce
# Be sure SALESFORCE_USERNAME is set to your SF username
USE_SFDX_AUTH = False

# Determine environment based on command line arguments
# These set various things throughout the settings file like, DEBUG, ALLOWED_HOSTS, CACHE, SENTRY, etc.
# You can override things in your local.py file to better reflect a production environment
TEST = 'test' in sys.argv
LOCAL = 'runserver' in sys.argv or 'runserver_plus' in sys.argv

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

# Set Accounts URL and environment for /info/
ACCOUNTS_URL = os.getenv('ACCOUNTS_URL', 'https://accounts.openstax.org')
ACCOUNTS_ENVIRONMENT = 'production'
if 'dev' in ACCOUNTS_URL:
    ACCOUNTS_ENVIRONMENT = 'dev'
elif 'staging' in ACCOUNTS_URL:
    ACCOUNTS_ENVIRONMENT = 'staging'

if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    # All non-local and non-prod environments
    ALLOWED_HOSTS = [f"{ENVIRONMENT}.salesforce.openstax.org", f"{ENVIRONMENT}.salesforce.sandbox.openstax.org"]
    if ENVIRONMENT == 'prod':
        # Prod only
        ALLOWED_HOSTS = ['salesforce.openstax.org']


ADMINS = ('SF Admin', 'sfadmin@openstax.org')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # contrib
    'corsheaders',  # for allowing cross-origin requests
    'salesforce',  # to generate models for Salesforce objects
    'redisboard',  # a django admin page for redis status
    'ninja',  # the django-ninja api framework
    'ninja_extra',  # extends ninja with more features
    # local apps
    'db',  # models for the local database storage of Salesforce data (to both cache and store data before upload to SF)
    'sf',  # logic for interacting with Salesforce
    'api',  # views and schemas for the API
    'users',  # custom user model and interactions with OpenStax Accounts
]

AUTH_USER_MODEL = 'users.User'
LOGIN_URL = '/admin/login/'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
if ENVIRONMENT not in ('local', 'test'):
    MIDDLEWARE.insert(2, 'healthcheck.middleware.HealthCheckMiddleware')  # after session, before common

CORS_ORIGIN_ALLOW_ALL = True

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
        'USER': os.getenv('DATABASE_USER', 'postgres'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'postgres'),
        'HOST': os.getenv('DATABASE_HOST', 'localhost'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
    },
    'salesforce': {
        'ENGINE': 'salesforce.backend',
        'AUTH': 'salesforce.auth.SalesforcePasswordAuth',
        'CONSUMER_KEY': os.getenv('SALESFORCE_CLIENT_ID', 'replaceme'),
        'CONSUMER_SECRET': os.getenv('SALESFORCE_CLIENT_SECRET', 'replaceme'),
        'USER': os.getenv('SALESFORCE_USERNAME', 'replaceme'),
        'PASSWORD': os.getenv('SALESFORCE_PASSWORD', 'replaceme') + os.getenv('SALESFORCE_SECURITY_TOKEN', 'replaceme'),
        'HOST': os.getenv('SALESFORCE_HOST', 'https://test.salesforce.com'),
    }
}

# Set Salesforce environment based on the host for /info/
SALESFORCE_ENVIRONMENT = DATABASES['salesforce']['HOST'].split('//')[1].split('.')[0]

# Salesforce API rate limiting
SALESFORCE_API_RATE_LIMIT = os.getenv('SALESFORCE_API_RATE_LIMIT', '20/min')  # x/sec x/min x/hour
SALESFORCE_API_USE_ALERT_THRESHOLD = os.getenv('SALESFORCE_API_USE_ALERT_THRESHOLD', 0.5)  # 50% of the limit

# Make sure to have sfdx/sf cli installed, you will be prompted to authenticate if you aren't
if USE_SFDX_AUTH:
    DATABASES['salesforce']['AUTH'] = 'salesforce.auth.SfdxOrgWebAuth'
    DATABASES['salesforce'].pop('CONSUMER_KEY')
    DATABASES['salesforce'].pop('CONSUMER_SECRET')
    DATABASES['salesforce'].pop('PASSWORD')

DATABASE_ROUTERS = [
    "salesforce.router.ModelRouter"
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cache settings
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_DB = os.getenv('REDIS_DB', '0')
REDIS_PROTOCOL = 'rediss' if REDIS_PASSWORD else 'redis'
REDIS_URL = f'{REDIS_PROTOCOL}://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": REDIS_PASSWORD,
            "IGNORE_EXCEPTIONS": True,  # this works without redis, so don't kill app if redis is down
        },
        "KEY_PREFIX": "sfapi",
        "TIMEOUT": 60*15  # default to a 15-min cache unless specified
    }
}

# If running locally, use a dummy cache to avoid having to spin up a redis server
if LOCAL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, 'public', 'static')
STATIC_URL = 'static/'

# OpenStax SSO cookie settings
SSO_COOKIE_NAME = os.getenv('SSO_COOKIE_NAME', 'oxa')
SIGNATURE_PUBLIC_KEY = os.getenv('SSO_SIGNATURE_PUBLIC_KEY')
ENCRYPTION_PRIVATE_KEY = os.getenv('SSO_ENCRYPTION_PRIVATE_KEY')

# This list of uuids use the auth decorator has_super_auth, use this to restrict access to certain endpoints
# during integrations with other systems
# TODO: This should be replaced with something like oauth before going to production with these endpoints
SUPER_USERS = os.getenv('SUPER_USERS', [
    'f8a6b8b8-32f7-4b4d-b6f9-054ab6fb5623',  # MiVo(local)
    '92e2c837-2cfa-4c42-bc0f-486d4ef19b2d',  # MiVo
    '85ea80ef-afdf-40cd-8803-fa84ad5a867e',  # DeMo
    'c8635454-1e4b-4205-944f-a054aeb9a41c',  # RoJo
    '1a01d1d7-6551-42ff-9400-23bfeeea4452',  # BrEa
])

# Sentry settings
if ENVIRONMENT not in('local', 'test'):
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.2,  # 20% of transactions will be sent to sentry
        send_default_pii=True,  # this will send the user id of admin users only to sentry to help with debugging
        environment=ENVIRONMENT
    )


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
