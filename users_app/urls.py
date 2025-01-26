from django.urls import path
from . import views

app_name = 'users'
urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('terms/', views.terms, name='terms'),
]