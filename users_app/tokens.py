# tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six  # Add this import

class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Add UserProfile state to hash for proper validation
        return (
            six.text_type(user.pk) + six.text_type(timestamp) +
            six.text_type(user.userprofile.email_confirmed)
        )

email_confirmation_token = EmailConfirmationTokenGenerator()