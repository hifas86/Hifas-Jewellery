from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import PasswordChangeForm

from .models import KYC
from .models import UserProfile

class CustomUserCreationForm(UserCreationForm):
    """Custom registration form with email field."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class KYCForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = [
            "full_name", "dob", "nic_number",
            "address", "phone", "nic_front",
            "nic_back", "selfie"
        ]
        widgets = {
            "dob": forms.DateInput(attrs={'type': 'date'}),
            "address": forms.Textarea(attrs={'rows': 3}),
        }

class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["profile_picture"]

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["full_name", "phone", "dob", "address", "nic_passport", "bio"]

