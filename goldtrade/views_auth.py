# goldtrade/views_auth.py
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


# ------------------------------------------
# LOGIN
# ------------------------------------------
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            # If not verified but email verification is required
            if not user.is_active:
                messages.warning(request, "Please verify your email before login.")
                return redirect("email_verification_pending")

            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid username or password.")
        return redirect("login")

    return render(request, "login.html")


# ------------------------------------------
# LOGOUT
# ------------------------------------------
def logout_view(request):
    logout(request)
    return redirect("login")


# ------------------------------------------
# SEND VERIFICATION EMAIL (Reusable function)
# ------------------------------------------
def send_verification_email(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    verify_link = request.build_absolute_uri(f"/verify-email/{uid}/{token}/")

    subject = "Verify Your Email - Hifas Jewellery Digital Gold Trade"
    html_message = render_to_string("emails/verify_email_template.html", {
        "user": user,
        "verify_link": verify_link,
    })

    send_mail(
        subject,
        html_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False, # <-- change it to True
    )
    return True # <-- Remove it
   
except Exception as e:
        print("EMAIL ERROR:", e)  # Shows in Render logs
        return False

# ------------------------------------------
# REGISTER USER
# ------------------------------------------
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")              # <-- MATCHES YOUR FORM
        confirm_password = request.POST.get("confirm_password")  # <-- MATCHES YOUR FORM

        # --- VALIDATIONS ---
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")

        # --- CREATE USER (inactive until email verified) ---
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,   # <-- password stored correctly
            is_active=False,     # User must verify email first
        )

        # Send email verification link
        ok = send_verification_email(request, user)

        if not ok:
        messages.warning(request,
        "Account created, but verification email could not be sent (mail server not configured).")

messages.success(request, "Account created successfully! You can now log in.")
return redirect("login")

    return render(request, "register.html")

# ------------------------------------------
# VERIFY EMAIL
# ------------------------------------------
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()

        messages.success(request, "🎉 Email verified successfully! You can now log in.")
        return redirect("login")
    else:
        messages.error(request, "Invalid or expired verification link.")
        return redirect("login")


# ------------------------------------------
# EMAIL VERIFICATION PENDING SCREEN
# ------------------------------------------
def email_verification_pending(request):
    return render(request, "email_verification_pending.html")


# ------------------------------------------
# RESEND VERIFICATION EMAIL
# ------------------------------------------
@login_required
def resend_verification_email(request):
    user = request.user

    if user.is_active:
        messages.info(request, "Your account is already verified.")
        return redirect("dashboard")

    send_verification_email(request, user)
    messages.success(request, "📨 Verification email resent successfully!")
    return redirect("email_verification_pending")


# ------------------------------------------
# FORGOT PASSWORD
# (You will implement token email reset later)
# ------------------------------------------
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "No account found with this email.")
            return redirect("forgot_password")

        # FYI: FULL PASSWORD RESET LOGIC COMING LATER (using tokens)
        messages.success(request, "A password reset link has been sent to your email.")
        return redirect("forgot_password")

    return render(request, "forgot_password.html")


# ------------------------------------------
# RESET PASSWORD (STATIC PAGE FOR NOW)
# ------------------------------------------
def reset_confirm(request, uidb64=None, token=None):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if request.method == "POST":
        pw1 = request.POST.get("password1")
        pw2 = request.POST.get("password2")

        # Passwords must match
        if pw1 != pw2:
            messages.error(request, "Passwords do not match.")
            return redirect(request.path)

        if user is not None and default_token_generator.check_token(user, token):
            # Save new password
            user.set_password(pw1)
            user.save()

            messages.success(request, "Your password has been reset successfully.")
            return redirect("reset_success")
        else:
            messages.error(request, "Invalid or expired reset link.")
            return redirect("forgot_password")

    # GET request: show form
    if user is not None and default_token_generator.check_token(user, token):
        return render(request, "reset_confirm.html", {"uidb64": uidb64, "token": token})
    else:
        messages.error(request, "This reset link is invalid or expired.")
        return redirect("forgot_password")


def reset_success(request):
    return render(request, "reset_success.html")
