from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

# ✅ After successful registration, send verification email
def send_verification_email(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    verify_link = request.build_absolute_uri(f"/verify-email/{uid}/{token}/")

    subject = "Verify Your Email - Hifas Jewellery Digital Gold Trade"
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

# ✅ Registration view (updated to include email verification)
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")

        user = User.objects.create_user(username=username, email=email, password=password1)
        user = form.save(commit=False)
        user.is_active = True  # Directly activate user
        user.save()
        login(request, user)
        return redirect('dashboard')

    return render(request, "register.html")


# ✅ Email verification handler
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, "verify_success.html")
    else:
        return render(request, "verify_failed.html")


def register_success(request):
    return render(request, "register_success.html")
    return redirect("register_success")

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "No account found with this email.")
            return redirect("forgot_password")

        messages.success(request, "✅ Reset link sent to your email.")
        return redirect("forgot_password")

    return render(request, "forgot_password.html")


def reset_confirm(request):
    if request.method == "POST":
        pw1 = request.POST.get("password1")
        pw2 = request.POST.get("password2")
        if pw1 != pw2:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_confirm")

        messages.success(request, "✅ Your password has been reset successfully.")
        return redirect("reset_success")  # 👈 redirect to success page

    return render(request, "reset_confirm.html")


def reset_success(request):
    return render(request, "reset_success.html")


def email_verification_pending(request):
    if request.method == "POST":
        # Logic to resend verification email
        messages.success(request, "✅ Verification email resent successfully!")
        return redirect("email_verification_pending")
    return render(request, "email_verification_pending.html")

from django.contrib.auth.decorators import login_required

@login_required
def resend_verification_email(request):
    user = request.user
    if user.is_active:
        messages.info(request, "✅ Your account is already verified.")
        return redirect("dashboard")

    send_verification_email(request, user)
    messages.success(request, "📨 Verification email resent successfully!")
    return redirect("email_verification_pending")

