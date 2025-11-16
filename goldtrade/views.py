# goldtrade/views.py
from decimal import Decimal, ROUND_DOWN

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.timezone import localtime, now, timedelta
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.db import transaction as db_tx  # alias for clarity

from .models import BankDeposit, GoldRate, Transaction, Wallet
from .models import KYC

from .forms import KYCForm

# =========================
# Email Helper
# =========================
def notify_user_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Sends multi-part (HTML + plain-text) email.
    Fail-safe: never raises to the user path (fail_silently).
    """
    try:
        text_body = strip_tags(html_body)
        msg = EmailMultiAlternatives(
            subject, text_body, settings.DEFAULT_FROM_EMAIL, [to_email]
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        # Intentionally silent: do not break user flows if SMTP has issues.
        pass

# =========================
# Gold Price Helper
# =========================
def get_gold_price():
    """
    Returns the latest buy/sell rates as Decimals.
    If none available, returns zeros to protect arithmetic.
    """
    gold = GoldRate.objects.order_by("-last_updated").first()
    if gold:
        return {
            "buy_rate": Decimal(gold.buy_rate),
            "sell_rate": Decimal(gold.sell_rate),
            "last_updated": gold.last_updated,
        }
    return {"buy_rate": Decimal("0"), "sell_rate": Decimal("0"), "last_updated": None}

# =========================
# Wallet Helpers (Session)
# =========================
def _get_current_mode(request) -> bool:
    """
    Returns True if DEMO, False if REAL.
    Stored in session to let user switch without changing DB.
    """
    return request.session.get("wallet_mode", "real") == "demo"


def _ensure_both_wallets(request) -> None:
    """
    Ensure both demo and real wallets exist for the authenticated user.
    Idempotent: uses get_or_create.
    """
    Wallet.objects.get_or_create(user=request.user, is_demo=False)
    Wallet.objects.get_or_create(user=request.user, is_demo=True)


def _get_selected_wallet(request):
    """
    Returns (wallet, is_demo) for the currently selected mode.
    Also guarantees both wallets exist.
    """
    is_demo = _get_current_mode(request)
    wallet, _ = Wallet.objects.get_or_create(user=request.user, is_demo=is_demo)
    _ensure_both_wallets(request)
    return wallet, is_demo

# =========================
# Mode Switch
# =========================
@login_required
def switch_wallet(request, mode):
    request.session["wallet_mode"] = "demo" if mode == "demo" else "real"
    nxt = request.GET.get("next") or "dashboard"
    return redirect(nxt)

# =========================
# Dashboard
# =========================
@login_required
def dashboard(request):
    _ensure_both_wallets(request)
    demo_wallet = Wallet.objects.get(user=request.user, is_demo=True)
    real_wallet = Wallet.objects.get(user=request.user, is_demo=False)
    selected_wallet, is_demo = _get_selected_wallet(request)
    gold_rate = GoldRate.objects.order_by("-last_updated").first()

    context = {
        "selected_wallet": selected_wallet,
        "is_demo": is_demo,
        "demo_wallet": demo_wallet,
        "real_wallet": real_wallet,
        "demo_transactions": Transaction.objects.filter(wallet=demo_wallet)
        .order_by("-timestamp")[:5],
        "real_transactions": Transaction.objects.filter(wallet=real_wallet)
        .order_by("-timestamp")[:5],
        "buy_rate": gold_rate.buy_rate if gold_rate else 0,
        "sell_rate": gold_rate.sell_rate if gold_rate else 0,
        "last_updated": gold_rate.last_updated if gold_rate else None,
    }
    return render(request, "goldtrade/dashboard.html", context)

# =========================
# BUY GOLD
# =========================
@login_required
def buy_gold(request):
    if not kyc_required(request.user):
        messages.error(request, "KYC approval is required to buy gold.")
        return redirect("kyc_form")
    rates = get_gold_price()

    if request.method == "POST":
        # Basic validation before DB work
        try:
            amount = Decimal(request.POST.get("amount", "0"))
        except Exception:
            messages.error(request, "Invalid amount.")
            return redirect("buy_gold")

        if amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect("buy_gold")

        if rates["sell_rate"] <= 0:
            messages.error(request, "Sell rate not available.")
            return redirect("buy_gold")

        # Calculate grams at the current sell rate
        grams = (amount / rates["sell_rate"]).quantize(
            Decimal("0.0001"), rounding=ROUND_DOWN
        )

        try:
            # --- RACE CONDITION PROTECTION ---
            # 1) Wrap the mutation in a single database transaction to ensure all-or-nothing.
            # 2) SELECT ... FOR UPDATE on the wallet row to acquire a row-level lock,
            #    preventing concurrent requests from reading/updating stale balances.
            with db_tx.atomic():
                wallet = (
                    Wallet.objects.select_for_update()
                    .get(user=request.user, is_demo=_get_current_mode(request))
                )

                if wallet.cash_balance < amount:
                    messages.error(request, "Insufficient balance!")
                    return redirect("buy_gold")

                # Perform the state change while the row is locked
                wallet.cash_balance -= amount
                wallet.gold_balance += grams
                wallet.save(update_fields=["cash_balance", "gold_balance"])

                # Persist transaction record within the same atomic block
                Transaction.objects.create(
                    wallet=wallet,
                    transaction_type="BUY",
                    gold_amount=grams,
                    price_per_gram=rates["sell_rate"],
                    total_amount=amount,
                )

            messages.success(request, f"Bought {grams} g of gold.")
        except Exception:
            messages.error(
                request, "A database error occurred during the transaction."
            )
        return redirect("buy_gold")

    # GET: show form with the selected wallet
    wallet, _ = _get_selected_wallet(request)
    return render(
        request,
        "goldtrade/buy_gold.html",
        {"wallet": wallet, "buy_rate": rates["buy_rate"], "sell_rate": rates["sell_rate"]},
    )

# =========================
# SELL GOLD
# =========================
@login_required
def sell_gold(request):
    if not kyc_required(request.user):
        messages.error(request, "KYC approval is required to sell gold.")
        return redirect("kyc_form")
    rates = get_gold_price()

    if request.method == "POST":
        # Basic validation before DB work
        try:
            grams = Decimal(request.POST.get("grams", "0"))
        except Exception:
            messages.error(request, "Invalid gold amount.")
            return redirect("sell_gold")

        if grams <= 0:
            messages.error(request, "Gold amount must be greater than zero.")
            return redirect("sell_gold")

        if rates["buy_rate"] <= 0:
            messages.error(request, "Buy rate not available.")
            return redirect("sell_gold")

        total = (grams * rates["buy_rate"]).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )

        try:
            # --- RACE CONDITION PROTECTION ---
            # Same pattern as buy: single atomic block + row-level lock on wallet.
            with db_tx.atomic():
                wallet = (
                    Wallet.objects.select_for_update()
                    .get(user=request.user, is_demo=_get_current_mode(request))
                )

                if wallet.gold_balance < grams:
                    messages.error(request, "Not enough gold to sell.")
                    return redirect("sell_gold")

                wallet.gold_balance -= grams
                wallet.cash_balance += total
                wallet.save(update_fields=["cash_balance", "gold_balance"])

                Transaction.objects.create(
                    wallet=wallet,
                    transaction_type="SELL",
                    gold_amount=grams,
                    price_per_gram=rates["buy_rate"],
                    total_amount=total,
                )

            messages.success(request, f"Sold {grams} g for {total}")
        except Exception:
            messages.error(
                request, "A database error occurred during the transaction."
            )
        return redirect("sell_gold")

    # GET: show form with the selected wallet
    wallet, _ = _get_selected_wallet(request)
    return render(
        request,
        "goldtrade/sell_gold.html",
        {"wallet": wallet, "buy_rate": rates["buy_rate"], "sell_rate": rates["sell_rate"]},
    )

# =========================
# ADD MONEY (submit deposit slip)
# =========================
@login_required
def add_money(request):
    wallet = Wallet.objects.get(user=request.user, is_demo=False)

    if request.method == "POST":
        raw_amount = request.POST.get("amount")
        reference_no = request.POST.get("reference_no")
        slip = request.FILES.get("slip")

        # Parse & validate the amount safely
        try:
            if not raw_amount:
                raise ValueError("Amount is required.")
            amount = Decimal(raw_amount)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
        except Exception:
            messages.error(request, "Invalid amount.")
            return redirect("add_money")

        if not reference_no or not slip:
            messages.error(request, "All fields are required. Please fill & upload slip.")
            return redirect("add_money")

        # Create a pending deposit (funds credited only on admin approval)
        BankDeposit.objects.create(
            user=request.user,
            amount=amount,
            reference_no=reference_no,
            slip=slip,
            status="pending",
        )

        messages.success(request, "Deposit submitted ✅ Awaiting admin approval.")
        return redirect("add_money")

    return render(request, "goldtrade/add_money.html", {"wallet": wallet})

# =========================
# WITHDRAW MONEY (user request)
# =========================
@login_required
def withdraw_money(request):
    # Require KYC approval
    if not kyc_required(request.user):
        messages.error(request, "KYC approval is required before withdrawing money.")
        return redirect("kyc_form")

    # Retrieve wallet safely
    try:
        wallet = Wallet.objects.get(user=request.user, is_demo=False)
    except Wallet.DoesNotExist:
        messages.error(request, "Wallet not found.")
        return redirect("dashboard")

    if request.method == "POST":
        # Basic validation
        try:
            amount = Decimal(request.POST.get("amount") or "0")
        except Exception:
            messages.error(request, "Invalid amount.")
            return redirect("withdraw_money")

        bank_name = request.POST.get("bank_name")
        account_name = request.POST.get("account_name")
        account_number = request.POST.get("account_number")
        branch = request.POST.get("branch")

        if amount <= 0 or not all([bank_name, account_name, account_number, branch]):
            messages.error(request, "Please fill in all fields with valid values.")
            return redirect("withdraw_money")

        # -------------------------------
        # ATOMIC BLOCK + LOCKING
        # -------------------------------
        try:
            with db_tx.atomic():

                # 1. LOCK the wallet row
                locked_wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

                # 2. Check sufficient balance
                if amount > locked_wallet.cash_balance:
                    messages.error(request, "Insufficient wallet balance.")
                    return redirect("withdraw_money")

                # 3. Pending withdrawal guard
                if Transaction.objects.filter(
                    wallet=locked_wallet,
                    transaction_type="WITHDRAW",
                    status="pending"
                ).exists():
                    messages.warning(request, "You already have a pending withdrawal request.")
                    return redirect("transactions")

                # 4. Create pending withdrawal (DEDUCTION happens on admin approval)
                tx = Transaction.objects.create(
                    wallet=locked_wallet,
                    transaction_type="WITHDRAW",
                    total_amount=amount,
                    remarks=f"{bank_name} - {branch} | {account_name} ({account_number})",
                    status="pending",
                )

        except Exception:
            messages.error(request, "A temporary error occurred. Please try again.")
            return redirect("withdraw_money")

        # Email notification
        user = request.user
        if user.email:
            notify_user_email(
                user.email,
                "Withdrawal Request Received – Hifas Jewellery",
                f"""
                <p>Hi {user.username},</p>
                <p>Your withdrawal request has been submitted and is now <b>pending review</b>.</p>
                <p><b>Amount:</b> Rs. {amount:,.2f}</p>
                <p><b>Bank:</b> {bank_name} - {branch}</p>
                <p><b>Account:</b> {account_name} ({account_number})</p>
                <p>We will notify you once it is processed.</p>
                <p>— Hifas Jewellery</p>
                """
            )

        messages.success(request, "Withdrawal request submitted 🎉 Awaiting admin approval.")
        return redirect("withdraw_confirm", tx_id=tx.id)

    return render(request, "goldtrade/withdraw.html", {"wallet": wallet})

@login_required
def withdraw_confirm(request, tx_id):
    tx = get_object_or_404(
        Transaction,
        id=tx_id,
        wallet__user=request.user,
        transaction_type="WITHDRAW",
    )
    return render(request, "goldtrade/withdraw_confirm.html", {"tx": tx})

# =========================
# Transactions (selected wallet)
# =========================
@login_required
def transactions(request):
    wallet, _is_demo = _get_selected_wallet(request)
    tx = Transaction.objects.filter(wallet=wallet).order_by("-timestamp")
    return render(request, "goldtrade/transactions.html", {"transactions": tx})

# =========================
# Rates: Refresh + History
# =========================
@cache_page(60)
def refresh_rates(request):
    try:
        gold = GoldRate.objects.latest("last_updated")
        data = {
            "buy_rate": float(gold.buy_rate),
            "sell_rate": float(gold.sell_rate),
            "last_updated": localtime(gold.last_updated).strftime("%Y-%m-%d %H:%M"),
        }
    except GoldRate.DoesNotExist:
        data = {"buy_rate": 0, "sell_rate": 0, "last_updated": None}
    return JsonResponse(data)

def gold_price_history(request):
    last_30_days = now() - timedelta(days=30)
    history = GoldRate.objects.filter(
        last_updated__gte=last_30_days
    ).order_by("last_updated")
    data = {
        "timestamps": [g.last_updated.isoformat() for g in history],
        "buy_rates": [float(g.buy_rate) for g in history],
        "sell_rates": [float(g.sell_rate) for g in history],
    }
    return JsonResponse(data)

# =========================
# Staff: Update Gold Rate
# =========================
@user_passes_test(lambda u: u.is_staff)
def update_gold_rate(request):
    latest = GoldRate.objects.order_by("-last_updated").first()

    if request.method == "POST":
        try:
            buy_rate = Decimal(request.POST.get("buy_rate", "0").replace(",", "").strip())
            sell_rate = Decimal(request.POST.get("sell_rate", "0").replace(",", "").strip())
        except Exception:
            messages.error(request, "Please enter numeric rates.")
            return redirect("update_rate")

        if buy_rate <= 0 or sell_rate <= 0:
            messages.error(request, "⚠️ Please enter valid positive rates.")
            return redirect("update_rate")

        GoldRate.objects.create(buy_rate=buy_rate, sell_rate=sell_rate)
        messages.success(request, "✅ Gold rates updated successfully!")
        return redirect("update_rate")

    return render(
        request,
        "goldtrade/update_rate.html",
        {
            "buy_rate": latest.buy_rate if latest else 0,
            "sell_rate": latest.sell_rate if latest else 0,
            "last_updated": latest.last_updated if latest else None,
        },
    )

# =========================
# My Deposits (user)
# =========================
@login_required
def my_deposits(request):
    deposits = BankDeposit.objects.filter(user=request.user).order_by("-created_at")
    wallet, _is_demo = _get_selected_wallet(request)
    return render(
        request, "goldtrade/my_deposits.html", {"deposits": deposits, "wallet": wallet}
    )

# =========================
# Staff: Deposits list
# =========================
@staff_member_required
def staff_deposits(request):
    q = request.GET.get("q", "").strip()
    qs = BankDeposit.objects.select_related("user").order_by("-created_at")
    if q:
        qs = qs.filter(reference_no__icontains=q)
    status = request.GET.get("status")
    if status in {"pending", "approved", "rejected"}:
        qs = qs.filter(status=status)
    return render(
        request, "goldtrade/staff_deposits.html", {"deposits": qs, "q": q, "status": status}
    )

# =========================
# My Withdrawals (user)
# =========================
@login_required
def my_withdrawals(request):
    withdrawals = Transaction.objects.filter(
        wallet__user=request.user,
        transaction_type="WITHDRAW"
    ).order_by("-timestamp")

    return render(request, "goldtrade/my_withdrawals.html", {
        "withdrawals": withdrawals
    })

# =========================
# Staff: Withdrawals list
# =========================
@staff_member_required
def staff_withdrawals(request):
    q = request.GET.get("q", "").strip()
    qs = (
        Transaction.objects.filter(transaction_type="WITHDRAW")
        .select_related("wallet__user")
        .order_by("-timestamp")
    )
    if q:
        qs = qs.filter(wallet__user__username__icontains=q)
    status = request.GET.get("status")
    if status in {"pending", "approved", "rejected"}:
        qs = qs.filter(status=status)
    return render(
        request,
        "goldtrade/staff_withdrawals.html",
        {"withdrawals": qs, "q": q, "status": status},
    )

# =========================
# Staff: Approve Withdrawal
# =========================
@staff_member_required
@db_tx.atomic
def approve_withdrawal(request, pk):
    # --- RACE CONDITION PROTECTION ---
    # Lock order: (1) withdrawal transaction row, (2) wallet row.
    # Consistent lock order prevents deadlocks if multiple admins process in parallel.

    # 1) Lock the transaction row for update.
    tx = get_object_or_404(
        Transaction.objects.select_for_update(), id=pk, transaction_type="WITHDRAW"
    )

    if tx.status != "pending":
        messages.warning(request, "Already processed.")
        return redirect("staff_withdrawals")

    # 2) Lock the associated wallet row for update.
    wallet = Wallet.objects.select_for_update().get(pk=tx.wallet.pk)

    # Ensure sufficient funds at the exact approval moment.
    if wallet.cash_balance < tx.total_amount:
        messages.error(request, "User wallet has insufficient balance.")
        return redirect("staff_withdrawals")

    # Deduct and finalize while both rows are locked inside the same transaction.
    wallet.cash_balance -= tx.total_amount
    wallet.save(update_fields=["cash_balance"])

    tx.status = "approved"
    tx.processed_by = request.user
    tx.save(update_fields=["status", "processed_by"])

    # Email notify user
    user = wallet.user
    if user.email:
        html = render_to_string(
            "emails/withdrawal_approved.html",
            {
                "username": user.username,
                "amount": tx.total_amount,
                "bank_details": tx.remarks,
                "date": localtime(tx.timestamp).strftime("%Y-%m-%d %H:%M"),
                "site_url": "https://hifas-jewellery.onrender.com",
                "year": now().year,
            },
        )
        notify_user_email(user.email, "Withdrawal Approved – Hifas Jewellery", html)

    messages.success(
        request, f"Withdrawal of Rs. {tx.total_amount:,.2f} approved ✅"
    )
    return redirect("staff_withdrawals")

# =========================
# Staff: Reject Withdrawal
# =========================
@staff_member_required
def reject_withdrawal(request, pk):
    tx = get_object_or_404(Transaction, id=pk, transaction_type="WITHDRAW")
    if tx.status != "pending":
        messages.warning(request, "Already processed.")
        return redirect("staff_withdrawals")

    tx.status = "rejected"
    tx.processed_by = request.user
    tx.save(update_fields=["status", "processed_by"])

    user = tx.wallet.user
    if user.email:
        subject = "Withdrawal Rejected – Hifas Jewellery"
        html = f"""
        <p>Hi {user.username},</p>
        <p>Your withdrawal request has been <b>rejected</b>.</p>
        <p><b>Amount:</b> Rs. {tx.total_amount:,.2f}<br>
           <b>Requested on:</b> {tx.timestamp.strftime('%Y-%m-%d %H:%M')}<br>
           <b>Bank Details:</b> {tx.remarks or '—'}</p>
        <p>If you believe this is an error, please reply to this email.</p>
        <p>— Hifas Jewellery</p>
        """
        notify_user_email(user.email, subject, html)

    messages.info(request, "Withdrawal rejected ❌")
    return redirect("staff_withdrawals")

# =========================
# Staff: Approve Deposit
# =========================
@staff_member_required
@db_tx.atomic
def approve_deposit(request, pk):
    # --- RACE CONDITION PROTECTION ---
    # Lock order: (1) deposit row, (2) wallet row.
    deposit = get_object_or_404(BankDeposit.objects.select_for_update(), id=pk)

    if deposit.status != "pending":
        messages.warning(request, "⚠️ This deposit is already processed.")
        return redirect("staff_deposits")

    wallet = Wallet.objects.select_for_update().get(user=deposit.user, is_demo=False)

    # Credit funds while locked and within the same transaction
    wallet.cash_balance += Decimal(deposit.amount)
    wallet.save(update_fields=["cash_balance"])

    # Record the accounting transaction
    Transaction.objects.create(
        wallet=wallet,
        transaction_type="DEPOSIT",
        total_amount=deposit.amount,
        remarks=f"Bank deposit ref: {deposit.reference_no}",
        status="approved",
    )

    # Mark deposit approved
    deposit.status = "approved"
    deposit.save(update_fields=["status"])

    # Email notify user
    if deposit.user.email:
        html = render_to_string(
            "emails/deposit_approved.html",
            {
                "username": deposit.user.username,
                "amount": f"{deposit.amount:,.2f}",
                "reference_no": deposit.reference_no,
                "date": localtime(deposit.created_at).strftime("%Y-%m-%d %H:%M"),
                "site_url": "https://hifas-jewellery.onrender.com",
                "year": now().year,
            },
        )
        notify_user_email(deposit.user.email, "Deposit Approved – Hifas Jewellery", html)

    messages.success(
        request, f"✅ Deposit approved. Rs. {deposit.amount:,.2f} credited to {deposit.user.username}."
    )
    return redirect("staff_deposits")

# =========================
# Staff: Reject Deposit
# =========================
@staff_member_required
def reject_deposit(request, pk):
    deposit = get_object_or_404(BankDeposit, id=pk)

    if deposit.status != "pending":
        messages.warning(request, "⚠️ This deposit has already been processed.")
        return redirect("staff_deposits")

    deposit.status = "rejected"
    deposit.save(update_fields=["status"])

    if deposit.user.email:
        notify_user_email(
            deposit.user.email,
            "Deposit Rejected – Hifas Jewellery",
            f"""
            <p>Hi {deposit.user.username},</p>
            <p>Your bank deposit (Ref: {deposit.reference_no}) has been <b>rejected</b>.</p>
            <p>Amount: Rs. {deposit.amount:,.2f}</p>
            <p>If you believe this is an error, please contact support.</p>
            <p>— Hifas Jewellery</p>
            """,
        )

    messages.info(request, "❌ Deposit rejected.")
    return redirect("staff_deposits")

# =========================
# Staff: Notifications alert
# =========================
@staff_member_required
def live_notifications(request):
    deposit_count = BankDeposit.objects.filter(status="pending").count()
    withdraw_count = Transaction.objects.filter(
        transaction_type="WITHDRAW", status="pending"
    ).count()

    return JsonResponse({
        "deposits": deposit_count,
        "withdrawals": withdraw_count
    })

# =========================
# My KYC
# =========================
@login_required
def kyc_form(request):
    try:
        kyc = KYC.objects.get(user=request.user)
        is_edit = True
    except KYC.DoesNotExist:
        kyc = None
        is_edit = False

    if request.method == "POST":
        form = KYCForm(request.POST, request.FILES, instance=kyc)
        
        if form.is_valid():
            k = form.save(commit=False)
            k.user = request.user
            k.status = "pending"
            k.save()
            messages.success(request, "KYC submitted successfully! 📝")
            return redirect("kyc_form")
        else:
            messages.error(request, "Please correct the errors and try again.")
    else:
        form = KYCForm(instance=kyc)

    return render(request, "goldtrade/kyc_form.html", {
        "form": form,
        "kyc": kyc,
        "is_edit": is_edit,
    })

# =========================
# KYC Helper
# =========================
def kyc_required(user):
    from .models import KYC
    try:
        kyc = KYC.objects.get(user=user)
        return kyc.status == "approved"
    except KYC.DoesNotExist:
        return False
        
# =========================
# My KYC Status
# =========================
@login_required
def kyc_status(request):
    try:
        kyc = KYC.objects.get(user=request.user)
    except KYC.DoesNotExist:
        return redirect("kyc_form")

    return render(request, "goldtrade/kyc_status.html", {"kyc": kyc})

# =========================
# KYC ADMIN BACKEND
# =========================

# ---- List All KYC ----
@staff_member_required
def kyc_admin_list(request):
    status = request.GET.get("status", "pending")

    if status == "all":
        kycs = KYC.objects.select_related("user").order_by("-created_at")
    else:
        kycs = KYC.objects.filter(status=status).select_related("user").order_by("-created_at")

    return render(request, "goldtrade/kyc_admin_list.html", {
        "kycs": kycs,
        "status": status,
    })


# ---- Review Single KYC ----
@staff_member_required
def kyc_admin_review(request, pk):
    kyc = get_object_or_404(KYC, id=pk)
    return render(request, "goldtrade/kyc_admin_review.html", {"kyc": kyc})


# ---- Approve KYC ----
@staff_member_required
def kyc_admin_approve(request, pk):
    kyc = get_object_or_404(KYC, id=pk)

    if kyc.status == "approved":
        messages.info(request, "KYC already approved.")
        return redirect("kyc_admin_review", pk=pk)

    kyc.status = "approved"
    kyc.save(update_fields=["status"])

    # Email user after approval
    if kyc.user.email:
        html = f"""
        <p>Hi {kyc.user.username},</p>
        <p>Your KYC verification has been <b style='color:green;'>APPROVED ✔</b>.</p>
        <p>Thank you for verifying your identity.</p>
        <p>— Hifas Jewellery</p>
        """
        notify_user_email(kyc.user.email, "KYC Approved – Hifas Jewellery", html)

    messages.success(request, "KYC approved successfully.")
    return redirect("kyc_admin_review", pk=pk)


# ---- Reject KYC ----
@staff_member_required
def kyc_admin_reject(request, pk):
    kyc = get_object_or_404(KYC, id=pk)

    if kyc.status == "rejected":
        messages.info(request, "KYC already rejected.")
        return redirect("kyc_admin_review", pk=pk)

    kyc.status = "rejected"
    kyc.save(update_fields=["status"])

    # Email user after rejection
    if kyc.user.email:
        html = f"""
        <p>Hi {kyc.user.username},</p>
        <p>Your KYC verification has been <b style='color:red;'>REJECTED ❌</b>.</p>
        <p>Please resubmit your details correctly.</p>
        <p>— Hifas Jewellery</p>
        """
        notify_user_email(kyc.user.email, "KYC Rejected – Hifas Jewellery", html)

    messages.warning(request, "KYC rejected.")
    return redirect("kyc_admin_review", pk=pk)
