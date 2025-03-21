"""finriv URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# main project urls.py (at the root level)
from django.contrib import admin
from django.urls import path, include
from fin_data_cl import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('fin_data_cl.urls')),
    #path('api/v1/', include('fin_data_cl.api_urls', namespace='api')),
    path('', include('price_plots.urls')),
    path('portfolios/', include('portfolios.urls')),
    #path('plots/', include('price_plots.urls', namespace='plots')),
    path('metrics/', include('metrics_an.urls', namespace='metrics')),
    path('about/', views.about, name='about'),
    #path('contact/', views.contact, name='contact'),
    path('users/', include('users_app.urls')),
    path('', include('contacts.urls')),
]
