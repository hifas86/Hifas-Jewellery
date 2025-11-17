# goldtrade/views_auth.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

import random

# ------------------------------
# LOGIN
# ------------------------------
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('login')

    return render(request, 'login.html')


# ------------------------------
# LOGOUT
# ------------------------------
def logout_view(request):
    logout(request)
    return redirect('login')


# ------------------------------
# REGISTER (NO EMAIL VERIFICATION)
# ------------------------------
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")                   # matches your form
        confirm_password = request.POST.get("confirm_password")   # matches your form

        # --- VALIDATE ---
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")

        # --- CREATE USER (ACTIVE IMMEDIATELY) ---
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True
        )

        # --- AUTO-CREATE DEMO & REAL WALLETS ---
        from goldtrade.models import Wallet
        Wallet.objects.get_or_create(user=user, is_demo=True, defaults={"cash_balance": 500000})
        Wallet.objects.get_or_create(user=user, is_demo=False)

        messages.success(request, "Account created successfully! Please log in.")
        return redirect("login")

    return render(request, "register.html")


# ------------------------------
# FORGOT PASSWORD (Dummy)
# ------------------------------
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "No account found with this email.")
            return redirect("forgot_password")

        # Fake reset link (no SMTP)
        messages.success(request, "A password reset link has been sent to your email (demo mode).")
        return redirect("forgot_password")

    return render(request, "forgot_password.html")

# ------------------------------
# RESET PASSWORD (Dummy)
# ------------------------------
def reset_confirm(request):
    if request.method == "POST":
        pw1 = request.POST.get("password1")
        pw2 = request.POST.get("password2")

        if pw1 != pw2:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_confirm")

        messages.success(request, "Your password has been reset successfully.")
        return redirect("reset_success")

    return render(request, "reset_confirm.html")

def reset_success(request):
    return render(request, "reset_success.html")

# ------------------------------
# Change PASSWORD
# ------------------------------
@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Password changed successfully!")
            return redirect("profile")
        else:
            messages.error(request, "Please fix the errors.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "goldtrade/change_password.html", {"form": form})

# ------------------------------
# Save OTP in Session
# ------------------------------
@login_required
def email_change_request(request):
    new_email = request.POST.get("new_email")

    if User.objects.filter(email=new_email).exists():
        messages.error(request, "Email already in use.")
        return redirect("profile")

    otp = random.randint(100000, 999999)
    request.session["email_otp"] = otp
    request.session["new_email"] = new_email

    notify_user_email(
        new_email,
        "Email Verification Code – Hifas Jewellery",
        f"<p>Your verification code is: <b>{otp}</b></p>"
    )

    messages.info(request, "Verification code sent. Enter OTP to confirm.")
    return redirect("email_verify_page")

# ------------------------------
# Verify OTP & Update Email
# ------------------------------
@login_required
def email_verify(request):
    if request.method == "POST":
        otp = request.POST.get("otp")

        if str(otp) == str(request.session.get("email_otp")):
            request.user.email = request.session.get("new_email")
            request.user.save()

            del request.session["email_otp"]
            del request.session["new_email"]

            messages.success(request, "Email updated successfully!")
            return redirect("profile")

        messages.error(request, "Invalid OTP.")
        return redirect("email_verify_page")

    return render(request, "goldtrade/email_verify.html")
