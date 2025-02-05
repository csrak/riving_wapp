from django.urls import path
from .views import ContactView, ContactAPIView

app_name = 'contacts'

urlpatterns = [
    path('contact/', ContactView.as_view(), name='contact-page'),
    path('api/contact/', ContactAPIView.as_view(), name='contact-api'),
]
