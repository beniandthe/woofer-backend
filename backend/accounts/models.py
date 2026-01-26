from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # External auth provider subject / user id (Auth0, Clerk, etc.)
    auth_provider_id = models.CharField(max_length=255, blank=True, null=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
