# goldtrade/views_auth.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail

from goldtrade.models import Wallet
from users.utils import send_verification_email

import random


# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            if not user.is_active:
                messages.error(request, "Email not verified. Please check your inbox.")
                return redirect("login")

            login(request, user)
            return redirect('dashboard')

        messages.error(request, "Invalid username or password.")
        return redirect('login')

    return render(request, 'login.html')


# ---------------------------------------------------
# LOGOUT
# ---------------------------------------------------
def logout_view(request):
    logout(request)
    return redirect('login')


# ---------------------------------------------------
# REGISTER (WITH EMAIL VERIFICATION)
# ---------------------------------------------------
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # validations
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")

        # user created but NOT ACTIVE
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=False
        )

        # create wallets
        Wallet.objects.get_or_create(user=user, is_demo=True, defaults={"cash_balance": 500000})
        Wallet.objects.get_or_create(user=user, is_demo=False)

        # send email verification
        send_verification_email(user)

        messages.success(request, "Registration successful! Please verify your email.")
        return redirect("login")

    return render(request, "register.html")


# ---------------------------------------------------
# FORGOT PASSWORD (DEMO)
# ---------------------------------------------------
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "No account found with this email.")
            return redirect("forgot_password")

        messages.success(request, "A password reset link has been sent to your email (demo).")
        return redirect("forgot_password")

    return render(request, "forgot_password.html")


# ---------------------------------------------------
# RESET PASSWORD (DEMO)
# ---------------------------------------------------
def reset_confirm(request):
    if request.method == "POST":
        pw1 = request.POST.get("password1")
        pw2 = request.POST.get("password2")

        if pw1 != pw2:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_confirm")

        messages.success(request, "Password reset successful.")
        return redirect("reset_success")

    return render(request, "reset_confirm.html")


def reset_success(request):
    return render(request, "reset_success.html")


# ---------------------------------------------------
# CHANGE PASSWORD
# ---------------------------------------------------
@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password changed successfully!")
            return redirect("profile")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "goldtrade/change_password.html", {"form": form})


# ---------------------------------------------------
# REQUEST EMAIL CHANGE (OTP)
# ---------------------------------------------------
@login_required
def email_change_request(request):
    new_email = request.POST.get("new_email")

    if User.objects.filter(email=new_email).exists():
        messages.error(request, "Email already in use.")
        return redirect("profile")

    otp = random.randint(100000, 999999)

    request.session["email_otp"] = otp
    request.session["new_email"] = new_email

    send_mail(
        subject="Email Verification Code – Hifas Jewellery",
        message=f"Your verification code is: {otp}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[new_email],
        fail_silently=True,
    )

    messages.info(request, "Verification code sent. Enter OTP to confirm.")
    return redirect("email_verify_page")


# ---------------------------------------------------
# VERIFY EMAIL CHANGE (OTP)
# ---------------------------------------------------
@login_required
def email_verify(request):
    if request.method == "POST":
        otp = request.POST.get("otp")

        if str(otp) == str(request.session.get("email_otp")):
            request.user.email = request.session.get("new_email")
            request.user.save()

            # cleanup session
            del request.session["email_otp"]
            del request.session["new_email"]

            messages.success(request, "Email updated successfully!")
            return redirect("profile")

        messages.error(request, "Invalid OTP.")
        return redirect("email_verify_page")

    return render(request, "goldtrade/email_verify.html")

