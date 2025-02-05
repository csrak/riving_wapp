from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from rest_framework import status
import json


class ContactAPITests(TestCase):
    """Test suite for contact form functionality."""

    def setUp(self):
        self.client = Client()
        self.url = reverse('contacts:contact-api')
        self.valid_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'message': 'This is a test message with proper length.'
        }

    def test_valid_submission(self):
        """Test successful form submission."""
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            f"New Contact Form Message from {self.valid_data['name']}"
        )

    def test_invalid_email(self):
        """Test submission with invalid email."""
        invalid_data = self.valid_data.copy()
        invalid_data['email'] = 'invalid-email'
        response = self.client.post(
            self.url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_short_message(self):
        """Test submission with too short message."""
        invalid_data = self.valid_data.copy()
        invalid_data['message'] = 'Short'
        response = self.client.post(
            self.url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_fields(self):
        """Test submission with missing fields."""
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)