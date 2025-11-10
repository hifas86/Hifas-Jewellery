import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gold_trade.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser(
        username="admin",
        email="hifas86@gmail.com",
        password="Admin@123"
    )
    print("✅ Superuser 'admin' created successfully.")
else:
    print("ℹ️ Superuser 'admin' already exists.")
