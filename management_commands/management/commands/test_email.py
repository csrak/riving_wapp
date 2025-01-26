# management/commands/test_email.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users_app.views import send_verification_email
from django.test.client import RequestFactory
from django.conf import settings


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        test_user = User.objects.create_user(
            username='testuser_temp',
            email='pokemon10.11.12@gmail.com',
            password='test123'
        )

        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_HOST'] = settings.ALLOWED_HOSTS[0]  # Use first allowed host

        email_sent = send_verification_email(request, test_user)
        print(f"Using email backend: {settings.EMAIL_BACKEND}")

        if email_sent:
            self.stdout.write(self.style.SUCCESS('Email sent successfully'))
        else:
            self.stdout.write(self.style.ERROR('Email sending failed'))

        test_user.delete()