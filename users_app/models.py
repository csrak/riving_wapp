# users_app/models.py
from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    email_confirmed = models.BooleanField(default=False)


class PaymentInfo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card_last4 = models.CharField(max_length=4)
    card_brand = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)