from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.views.generic import TemplateView
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.utils.translation import gettext as _
import logging
import re

logger = logging.getLogger(__name__)


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


class ContactView(TemplateView):
    """View for rendering the contact form page."""
    template_name = 'contacts/contact.html'


class ContactAPIView(APIView):
    """API endpoint for handling contact form submissions."""
    permission_classes = [AllowAny]

    def post(self, request):
        # Get and clean data
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip().lower()
        message = request.data.get('message', '').strip()

        # Validate inputs
        if not all([name, email, message]):
            return Response({
                'status': 'error',
                'message': _('All fields are required.')
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(name) < 2:
            return Response({
                'status': 'error',
                'message': _('Name must be at least 2 characters long.')
            }, status=status.HTTP_400_BAD_REQUEST)

        if not validate_email(email):
            return Response({
                'status': 'error',
                'message': _('Please enter a valid email address.')
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(message) < 10:
            return Response({
                'status': 'error',
                'message': _('Message must be at least 10 characters long.')
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Prepare email content
            subject = f"New Contact Form Message from {name}"
            email_body = (
                f"Name: {name}\n"
                f"Email: {email}\n\n"
                f"Message:\n{message}\n\n"
                f"IP Address: {request.META.get('REMOTE_ADDR')}"
            )

            # Send email
            send_mail(
                subject=subject,
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False
            )

            # Log success
            logger.info(f"Contact form submission successful from {email}")

            return Response({
                'status': 'success',
                'message': _('Your message has been sent successfully!')
            }, status=status.HTTP_200_OK)

        except BadHeaderError:
            logger.error(f"Invalid header found in contact form submission from {email}")
            return Response({
                'status': 'error',
                'message': _('Invalid header found.')
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error processing contact form from {email}: {str(e)}")
            return Response({
                'status': 'error',
                'message': _('An error occurred while sending your message. Please try again later.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)