from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLES = (
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Pro'),
    )
    role = models.CharField(max_length=10, choices=ROLES, default='free')
    created_at = models.DateTimeField(auto_now_add=True)