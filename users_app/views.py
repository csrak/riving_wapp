# users_app/views.py
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from .models import UserProfile
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from .tokens import email_verification_token


class SignUpView(CreateView):
    def form_valid(self, form):
        user = form.save()
        current_site = get_current_site(self.request)

        email_subject = 'Activate Your Account'
        email_body = render_to_string('users_app/email_verification.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': email_verification_token.make_token(user),
        })

        email = EmailMessage(email_subject, email_body, to=[user.email])
        email.send()

        messages.success(self.request, 'Please check your email to complete registration.')
        return redirect('users:login')


def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user and email_verification_token.check_token(user, token):
        user.userprofile.email_confirmed = True
        user.userprofile.save()
        messages.success(request, 'Email verified! You can now login.')
    else:
        messages.error(request, 'Invalid activation link!')

    return redirect('users:login')
class CustomLoginView(LoginView):
    template_name = 'users_app/login.html'
    redirect_authenticated_user = True

class CustomLogoutView(LogoutView):
    next_page = 'fin_data:index'

def privacy_policy(request):
    return render(request, 'users_app/privacy_policy.html')

def terms(request):
    return render(request, 'users_app/terms.html')

