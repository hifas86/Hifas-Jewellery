from django.urls import reverse
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import EmailVerification

SENDGRID_SENDER = settings.DEFAULT_FROM_EMAIL

def send_verification_email(user):
    # Create or refresh token
    verification, _ = EmailVerification.objects.get_or_create(user=user)
    verification.token = uuid.uuid4()
    verification.save()

    url = f"https://hifas-jewellery.onrender.com/verify-email/{verification.token}/"

    subject = "Verify Your Email - Hifas Jewellery"
    html_content = render_to_string("email/verify_email.html", {"user": user, "url": url})
    text_content = f"Please verify your email: {url}"

    email = EmailMultiAlternatives(subject, text_content, SENDGRID_SENDER, [user.email])
    email.attach_alternative(html_content, "text/html")
    email.send()
