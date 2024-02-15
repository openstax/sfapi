import os
import json
import sys

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from pathlib import Path
from dotenv import load_dotenv

import logging.config
from django.utils.log import DEFAULT_LOGGING

load_dotenv()

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'local')
RELEASE_VERSION = os.environ.get('RELEASE_VERSION')
DEPLOYMENT_VERSION = os.environ.get('DEPLOYMENT_VERSION')

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

ALLOWED_HOSTS = json.loads(os.getenv('ALLOWED_HOSTS', '[]'))


SECRET_KEY = os.environ.get('SECRET_KEY')

# check if running local dev server - else default to DEBUG=False
if len(sys.argv) > 1:
    DEBUG = (sys.argv[1] == 'runserver')
else:
    DEBUG = False

ADMINS = ('Michael Volo', 'volo@rice.edu')

if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = ['*salesforce.openstax.org']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'oauth2_provider',
    'corsheaders',
    'ninja',
    'aws',
    'sf',
    'api',
    'users',
    'accounts',
    'salesforce',
]

AUTH_USER_MODEL = 'users.User'
LOGIN_URL = '/admin/login/'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = not DEBUG

SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000  # 1 year

if DEBUG:
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
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

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
        'CONSUMER_KEY': os.getenv('SALESFORCE_CLIENT_ID'),
        'CONSUMER_SECRET': os.getenv('SALESFORCE_CLIENT_SECRET'),
        'USER': os.getenv('SALESFORCE_USERNAME'),
        'PASSWORD': os.getenv('SALESFORCE_PASSWORD', 'replaceme') + os.getenv('SALESFORCE_SECURITY_TOKEN', 'replaceme'),
        'HOST': os.getenv('SALESFORCE_HOST', 'https://test.salesforce.com'),
    }
}

DATABASE_ROUTERS = [
    "salesforce.router.ModelRouter"
]


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'public', 'static')
STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# OpenStax SSO cookie settings
SSO_COOKIE_NAME = os.getenv('SSO_COOKIE_NAME', 'oxa')
SIGNATURE_PUBLIC_KEY = os.getenv('SSO_SIGNATURE_PUBLIC_KEY')
ENCRYPTION_PRIVATE_KEY = os.getenv('SSO_ENCRYPTION_PRIVATE_KEY')

# Sentry
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

BASE_URL = os.getenv('BASE_URL')
if BASE_URL is None:
    APPLICATION_DOMAIN = os.getenv('APPLICATION_DOMAIN')
    if APPLICATION_DOMAIN is None:
        if ENVIRONMENT == 'prod':
            APPLICATION_DOMAIN = 'openstax.org'
        else:
            APPLICATION_DOMAIN = f'{ENVIRONMENT}.openstax.org'
    BASE_URL = f'https://{APPLICATION_DOMAIN}'
