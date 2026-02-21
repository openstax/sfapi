from .base import *

# We want to run our tests using a local database, not the Salesforce database which would result in ungodly slow tests
# and a depletion of our Salesforce API calls very quickly.

# We also want to avoid using the Salesforce database because we don't want to accidentally create or modify any Salesforce
# records while running our tests.

DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "sfapi",
    "USER": "sfapi",
    "PASSWORD": "sfapi",
    "HOST": "localhost",
    "PORT": 5432,
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

SALESFORCE_DB_ALIAS = "default"

# Disable production security settings for tests
SECURE_SSL_REDIRECT = False
