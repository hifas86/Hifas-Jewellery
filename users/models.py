import uuid
import os

from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save


class EmailVerification(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(hours=24)

    def __str__(self):
        return f"Verification for {self.user.email}"

# ---------------------------------------------
#  📌 Generate Upload Path for Profile Pictures
# ---------------------------------------------
def profile_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"profile_{instance.user.id}_{uuid.uuid4()}.{ext}"
    return os.path.join("profiles", filename)


# ---------------------------------------------
#  📌 User Profile Model
# ---------------------------------------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Profile picture
    profile_picture = models.ImageField(
        upload_to=profile_upload_path,
        blank=True,
        null=True
    )

    # Personal Details
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    dob = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True)
    nic_passport = models.CharField(max_length=50, blank=True)  # NIC or Passport
    bio = models.TextField(blank=True)

    # Email verification flag (IMPORTANT!)
    email_verified = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    # Return picture URL or fallback
    def picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return "/static/images/default_profile.png"

# ------------------------------------------------
#  🔄 Auto-create UserProfile for new users
# ------------------------------------------------
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.userprofile.save()
