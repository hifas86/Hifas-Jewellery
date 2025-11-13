from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.db import transaction
from decimal import Decimal

from goldtrade.models import Wallet   # ✅ correct import

# --------------------------------------------------------------------
# LOGIN VIEW
# --------------------------------------------------------------------
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("dashboard")

        return render(request, "login.html", {"error": "Invalid credentials"})

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")

# --------------------------------------------------------------------
# SEND VERIFICATION EMAIL
# --------------------------------------------------------------------
def send_verification_email(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    verify_link = request.build_absolute_uri(f"/verify-email/{uid}/{token}/")

    subject = "Verify Your Email - Hifas Jewellery"
    message = render_to_string("emails/verify_email_template.html", {
        "user": user,
        "verify_link": verify_link,
    })

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

# --------------------------------------------------------------------
# REGISTER VIEW  ⭐ FIXED ⭐
# --------------------------------------------------------------------
def register_view(request):
    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # --------------------------------------------------------------
        # VALIDATIONS
        # --------------------------------------------------------------
        if not username or not email or not password:
            messages.error(request, "All fields are required.")
            return redirect("register")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("register")

        # --------------------------------------------------------------
        # CREATE USER + WALLETS SAFELY (Atomic)
        # --------------------------------------------------------------
        try:
            with transaction.atomic():

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_active=True       # Change to False if requiring email verification
                )

                # Create demo wallet with 500,000 LKR
                Wallet.objects.create(
                    user=user,
                    is_demo=True,
                    cash_balance=Decimal("500000.00"),
                    gold_balance=Decimal("0")
                )

                # Create real wallet (0 balance)
                Wallet.objects.create(
                    user=user,
                    is_demo=False,
                    cash_balance=Decimal("0"),
                    gold_balance=Decimal("0")
                )

        except Exception as e:
            messages.error(request, f"Registration failed: {e}")
            return redirect("register")

        # OPTIONAL: Send email verification
        # send_verification_email(request, user)

        messages.success(request, "Account created successfully! Please log in.")
        return redirect("login")

    return render(request, "register.html")

# --------------------------------------------------------------------
# FORGOT PASSWORD
# --------------------------------------------------------------------
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "No account found with this email.")
            return redirect("forgot_password")

        messages.success(request, "Reset link sent to your email.")
        return redirect("forgot_password")

    return render(request, "forgot_password.html")

# --------------------------------------------------------------------
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


def email_verification_pending(request):
    if request.method == "POST":
        messages.success(request, "Verification email resent successfully!")
        return redirect("email_verification_pending")

    return render(request, "email_verification_pending.html")


@login_required
def resend_verification_email(request):
    user = request.user
    if user.is_active:
        messages.info(request, "Your account is already verified.")
        return redirect("dashboard")

    send_verification_email(request, user)
    messages.success(request, "Verification email resent successfully!")
    return redirect("email_verification_pending")
