from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from .models import BankDeposit, Wallet
from django.contrib.auth.models import User

@receiver(post_save, sender=BankDeposit)
def credit_wallet_on_approval(sender, instance, created, **kwargs):
    # Only credit when status changes to approved
    if instance.status == "approved" and not created:

        wallet, _ = Wallet.objects.get_or_create(user=instance.user, is_demo=False)

        # Prevent double credit
        if getattr(instance, "_credited", False):
            return

        wallet.cash_balance += Decimal(instance.amount)
        wallet.save()

        # Mark so we don't re-credit
        instance._credited = True


@receiver(post_save, sender=User)
def create_demo_wallet(sender, instance, created, **kwargs):
    if created:
        # Create demo wallet with 500,000.00 LKR
        Wallet.objects.get_or_create(
            user=instance,
            is_demo=True,  # ✅ Correct field name
            defaults={'cash_balance': Decimal('500000.00')}
        )
        # Create real wallet starting at 0
        Wallet.objects.get_or_create(
            user=instance,
            is_demo=False,
            defaults={'cash_balance': Decimal('0.00')}
        )
