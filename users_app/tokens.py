# tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator

from django.contrib.auth import get_user_model

class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Use password field instead of email_confirmed since it changes after verification
        return f"{user.pk}{user.password}{timestamp}"

    def check_token(self, user, token):
        """
        Add timeout validation (default 3 days)
        """
        timestamp = token.split("-")[0]
        return super().check_token(user, token) and \
            (self._num_seconds(self._now()) - int(timestamp)) < 259200  # 3 days

email_confirmation_token = EmailConfirmationTokenGenerator()