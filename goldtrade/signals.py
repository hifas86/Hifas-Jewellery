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
        from .models import Wallet  # 👈 import inside function to prevent circular import
        Wallet.objects.get_or_create(
            user=instance,
            mode='demo',
            defaults={'balance': 500000.00}
        )
