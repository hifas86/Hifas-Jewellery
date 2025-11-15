# goldtrade/views_auth.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

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
