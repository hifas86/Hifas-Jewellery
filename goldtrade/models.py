from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Wallet

class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_demo = models.BooleanField(default=False, db_index=True)  # False = Real, True = Demo
    cash_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gold_balance = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "is_demo"], name="uniq_user_demo_flag")
        ]

    def __str__(self):
        return f"{self.user.username} - {'DEMO' if self.is_demo else 'REAL'}"
@receiver(post_save, sender=User)
def create_demo_wallet(sender, instance, created, **kwargs):
    if created:
        # Create wallet if it doesn’t exist yet
        Wallet.objects.get_or_create(
            user=instance,
            mode='demo',              # or your wallet type field
            defaults={'balance': 500000.00}  # LKR 500,000.00
        )

class BankDeposit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference_no = models.CharField(max_length=100)
    slip = models.ImageField(upload_to='bank_slips/')

    STATUS_CHOICES = (
        ('pending', 'Pending Verification'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} LKR"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("BUY", "Buy"),
        ("SELL", "Sell"),
        ("DEPOSIT", "Deposit"),
        ("WITHDRAW", "Withdraw"),
    ]
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    gold_amount = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    price_per_gram = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remarks = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # ✅ new fields
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending",
    )
    processed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_withdrawals"
    )

    def __str__(self):
        return f"{self.transaction_type} - {self.total_amount} ({self.status})"


class GoldRate(models.Model):
    buy_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Buy rate per gram in LKR")
    sell_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Sell rate per gram in LKR")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Buy: {self.buy_rate} | Sell: {self.sell_rate} (Updated {self.last_updated.strftime('%Y-%m-%d %H:%M')})"
