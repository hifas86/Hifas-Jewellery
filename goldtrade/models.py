from django.db import models
from django.contrib.auth.models import User

# -------------------------
# WALLET MODEL
# -------------------------
class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wallets")
    is_demo = models.BooleanField(default=False, db_index=True)
    cash_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gold_balance = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "is_demo"], name="uniq_user_demo_flag")
        ]

    def __str__(self):
        return f"{self.user.username} - {'DEMO' if self.is_demo else 'REAL'}"


# -------------------------
# BANK DEPOSITS
# -------------------------
class BankDeposit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bank_deposits")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference_no = models.CharField(max_length=100)
    slip = models.ImageField(upload_to='bank_slips/')

    STATUS_CHOICES = (
        ('pending', 'Pending Verification'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} LKR"


# -------------------------
# TRANSACTIONS
# -------------------------
class Transaction(models.Model):

    TRANSACTION_TYPES = [
        ("BUY", "Buy"),
        ("SELL", "Sell"),
        ("DEPOSIT", "Deposit"),
        ("WITHDRAW", "Withdraw"),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)

    gold_amount = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    price_per_gram = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    remarks = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # new approval fields (for withdraw only)
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending",
    )

    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_transactions",
    )

    def __str__(self):
        return f"{self.transaction_type} - {self.total_amount} ({self.status})"


# -------------------------
# GOLD RATE
# -------------------------
class GoldRate(models.Model):
    buy_rate = models.DecimalField(max_digits=10, decimal_places=2)
    sell_rate = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Buy: {self.buy_rate} | Sell: {self.sell_rate}"


# -------------------------
# KYC MODEL
# -------------------------
class KYC(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    full_name = models.CharField(max_length=150)
    dob = models.DateField()
    nic_number = models.CharField(max_length=12)
    address = models.TextField()
    phone = models.CharField(max_length=10)

    nic_front = models.ImageField(upload_to='kyc/')
    nic_back = models.ImageField(upload_to='kyc/')
    selfie = models.ImageField(upload_to='kyc/')

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending"
    )

    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"KYC - {self.user.username}"
