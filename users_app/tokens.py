# users_app/tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.userprofile.email_confirmed}"


email_verification_token = EmailVerificationTokenGenerator()