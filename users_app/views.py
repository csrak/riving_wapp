from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from .forms import SignUpForm
from .models import UserProfile
from .tokens import email_confirmation_token
from django.utils.encoding import force_str, force_bytes
import logging

logger = logging.getLogger(__name__)


def send_verification_email(request, user):
    try:
        current_site = get_current_site(request)
        subject = 'Verify your email'
        message = render_to_string('users_app/email_verification.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': email_confirmation_token.make_token(user),
        })

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        email = Mail(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=user.email,
            subject=subject,
            html_content=message
        )
        sg.send(email)
        return True
    except Exception as e:
        logger.error(f"Email sending failed: {str(e)}")
        return False


@method_decorator(sensitive_post_parameters(), name='dispatch')
class CustomLoginView(LoginView):
    template_name = 'users_app/login.html'
    redirect_authenticated_user = True
    next_page = '/'  # or any other URL name like 'fin_data:index'
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password')
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    next_page = 'fin_data:index'


@sensitive_post_parameters()
@require_http_methods(["GET", "POST"])
def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                if send_verification_email(request, user):
                    messages.success(request, 'Account created successfully. Please check your email.')
                    return redirect('users:login')
                else:
                    messages.warning(request, 'Account created but verification email failed.')
                    return redirect('users:login')
            except Exception as e:
                logger.error(f"Signup error: {str(e)}")
                messages.error(request, 'Error creating account. Please try again.')
                return redirect('users:signup')
    else:
        form = SignUpForm()

    return render(request, 'users_app/signup.html', {'form': form})


@require_http_methods(["GET"])
def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)

        # Add debug prints
        print(f"Attempting to activate user: {user.username}")
        print(f"Token valid: {email_confirmation_token.check_token(user, token)}")

        if not email_confirmation_token.check_token(user, token):
            print("Token validation failed")  # Debug print
            messages.error(request, 'Activation link is invalid or expired.')
            return redirect('users:login')

        profile = UserProfile.objects.get_or_create(user=user)[0]
        if profile.email_confirmed:
            messages.info(request, 'Email already verified.')
        else:
            profile.email_confirmed = True
            profile.save()
            messages.success(request, 'Email verified successfully!')

    except Exception as e:
        print(f"Activation error: {str(e)}")  # Debug print
        messages.error(request, 'Activation link is invalid.')

    return redirect('users:login')


def privacy_policy(request):
    return render(request, 'users_app/privacy_policy.html')


def terms(request):
    return render(request, 'users_app/terms.html')