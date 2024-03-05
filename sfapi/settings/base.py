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

ENVIRONMENT = os.getenv('ENVIRONMENT', 'local')
RELEASE_VERSION = os.getenv('RELEASE_VERSION')
DEPLOYMENT_VERSION = os.getenv('DEPLOYMENT_VERSION')
IS_TESTING = os.getenv('IS_TESTING', 'False')

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')

SECRET_KEY = os.environ.get('SECRET_KEY')

# check if running local dev server - else default to DEBUG=False
if len(sys.argv) > 1:
    DEBUG = (sys.argv[1] == 'runserver')
else:
    DEBUG = False

if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    if ENVIRONMENT == 'prod':
        # Prod only
        ALLOWED_HOSTS = ['salesforce.openstax.org']
        ACCOUNTS_URL = os.getenv('ACCOUNTS_URL', 'https://accounts.openstax.org')
    else:
        # All non-local and non-prod environments
        ALLOWED_HOSTS = [f"{ENVIRONMENT}.salesforce.openstax.org", f"{ENVIRONMENT}.salesforce.sandbox.openstax.org"]
        ACCOUNTS_URL = os.getenv('ACCOUNTS_URL', f"https://{ENVIRONMENT}.accounts.openstax.org")

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
    # 'users.middleware.OpenAPIOpenStaxAuthenticationMiddleware',
]
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True
# SECURE_SSL_REDIRECT = not DEBUG
#
# SECURE_HSTS_PRELOAD = True
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_SECONDS = 31536000  # 1 year

if DEBUG:
    MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://\w+\.openstax\.org$",
    ]
    CORS_ALLOW_CREDENTIALS = True
    SESSION_COOKIE_SAMESITE = None
    SESSION_COOKIE_DOMAIN = ".openstax.org"
    SESSION_COOKIE_NAME = 'oxa_dev'

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

# Account Engagement Form Handlers
ACCOUNT_ENGAGEMENT_FORM_HANDLERS = {
    'renewal': os.getenv('RENEWAL_FORM_HANDLER', 'https://www2.openstax.org/l/218812/2022-06-14/zldbyb'),
    'adoption': os.getenv('ADOPTION_FORM_HANDLER', 'https://www2.openstax.org/l/218812/2021-10-21/tdphnv'),
    'interest': os.getenv('INTEREST_FORM_HANDLER', 'https://www2.openstax.org/l/218812/2021-10-21/tdphmz'),
}

DATABASE_ROUTERS = [
    "salesforce.router.ModelRouter"
]


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

if ENVIRONMENT == 'prod':
    ACCOUNTS_URL = os.getenv('ACCOUNTS_URL', 'https://accounts.openstax.org')
elif ENVIRONMENT == 'local':
    ACCOUNTS_URL = os.getenv('ACCOUNTS_URL', 'http://localhost:2999')
    OAUTHLIB_INSECURE_TRANSPORT = 1
else:
    ACCOUNTS_URL = os.getenv('ACCOUNTS_URL', f"https://{ENVIRONMENT}.accounts.openstax.org")

AUTHORIZATION_URL = os.getenv('ACCOUNTS_AUTHORIZATION_URL', f'{ACCOUNTS_URL}/oauth/authorize')
ACCESS_TOKEN_URL = os.getenv('ACCOUNTS_ACCESS_TOKEN_URL', f'{ACCOUNTS_URL}/oauth/token')
USER_QUERY = os.getenv('ACCOUNTS_USER_QUERY', f'{ACCOUNTS_URL}/api/user?')
USERS_QUERY = os.getenv('ACCOUNTS_USERS_QUERY', f'{ACCOUNTS_URL}/api/users?')
SOCIAL_AUTH_OPENSTAX_KEY = os.getenv('SOCIAL_AUTH_OPENSTAX_KEY')
SOCIAL_AUTH_OPENSTAX_SECRET = os.getenv('SOCIAL_AUTH_OPENSTAX_SECRET')

if not LOCAL or TEST:
    # Sentry settings - disabled for local and testing
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.2, # 20% of transactions will be sent to sentry
        send_default_pii=True,  # this will send the user id of admin users only to sentry to help with debugging
        environment=ENVIRONMENT,
        release=RELEASE_VERSION,
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
