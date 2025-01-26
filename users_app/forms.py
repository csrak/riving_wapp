# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

class SignUpForm(UserCreationForm):
   email = forms.EmailField(required=True)
   first_name = forms.CharField(max_length=30, required=True)
   last_name = forms.CharField(max_length=30, required=True)
   phone_number = forms.CharField(max_length=15, required=False)

   class Meta:
       model = User
       fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2')

   def clean_password1(self):
       password = self.cleaned_data.get('password1')
       validate_password(password)
       return password

   def clean_email(self):
       email = self.cleaned_data.get('email')
       if User.objects.filter(email=email).exists():
           raise forms.ValidationError("Email already exists")
       return email