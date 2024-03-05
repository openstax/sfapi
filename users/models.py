from django.db import models
from django.contrib.auth.models import AbstractUser

from .managers import OpenStaxUserManager

# Placeholder for future custom user model
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    account_uuid = models.UUIDField(unique=True, null=True, blank=True)
    is_admin = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = OpenStaxUserManager()

    def __str__(self):
        return self.email
