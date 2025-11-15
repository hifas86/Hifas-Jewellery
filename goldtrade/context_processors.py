from .models import BankDeposit, Transaction

def pending_counts(request):
    if not request.user.is_authenticated:
        return {}

    if not request.user.is_staff:
        return {}

    deposit_count = BankDeposit.objects.filter(status="pending").count()
    withdraw_count = Transaction.objects.filter(transaction_type="WITHDRAW", status="pending").count()

    return {
        "pending_deposits_count": deposit_count,
        "pending_withdrawals_count": withdraw_count,
    }
