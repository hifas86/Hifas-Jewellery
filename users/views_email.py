from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import EmailVerification

def verify_email(request, token):
    try:
        verification = EmailVerification.objects.get(token=token)
    except EmailVerification.DoesNotExist:
        messages.error(request, "Invalid verification link.")
        return redirect("login")

    if verification.is_expired():
        messages.error(request, "Verification link expired. Please request again.")
        return redirect("resend_verification")

    user = verification.user
    user.is_active = True
    user.save()

    verification.delete()

    messages.success(request, "Your email has been verified! You can now log in.")
    return redirect("login")

@login_required
def resend_verification(request):
    from .utils import send_verification_email

    if request.user.is_active:
        messages.info(request, "Your email is already verified.")
        return redirect("dashboard")

    send_verification_email(request.user)
    messages.success(request, "Verification email sent again. Check your inbox.")
    return redirect("dashboard")
