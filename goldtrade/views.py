# goldtrade/views.py
from decimal import Decimal, ROUND_DOWN
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.utils.timezone import localtime, now, timedelta
from django.db import transaction as db_tx
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, send_mail
from django.conf import settings
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.views.decorators.cache import cache_page

from .models import BankDeposit, Wallet, Transaction, GoldRate

# ------------------------- Email Helper --------------------------
def notify_user_email(to_email: str, subject: str, html_body: str):
    """
    Sends both HTML and plain-text fallback. Never raises to users.
    """
    try:
        text_body = strip_tags(html_body)
        msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [to_email])
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        # Keep silent in production paths to avoid breaking user flow
        pass

# ------------------------- Gold Price Helper ---------------------
def get_gold_price():
    gold = GoldRate.objects.order_by('-last_updated').first()
    if gold:
        return {
            'buy_rate': Decimal(gold.buy_rate),
            'sell_rate': Decimal(gold.sell_rate),
            'last_updated': gold.last_updated
        }
    return {'buy_rate': Decimal('0'), 'sell_rate': Decimal('0'), 'last_updated': None}
    
# --- wallet mode helper (session) --------------------------------------------
def _get_current_mode(request) -> bool:
    """Return True if DEMO, False if REAL."""
    return request.session.get("wallet_mode", "real") == "demo"

def _ensure_both_wallets(request):
    """Always ensure both wallets exist for the user."""
    Wallet.objects.get_or_create(user=request.user, is_demo=False)
    Wallet.objects.get_or_create(user=request.user, is_demo=True)

def _get_selected_wallet(request):
    is_demo = _get_current_mode(request)
    wallet, _ = Wallet.objects.get_or_create(user=request.user, is_demo=is_demo)
    _ensure_both_wallets(request)
    return wallet, is_demo

# --- switch wallet (Demo/Real) -----------------------------------------------
@login_required
def switch_wallet(request, mode):
    request.session["wallet_mode"] = "demo" if mode == "demo" else "real"
    nxt = request.GET.get("next") or "dashboard"
    return redirect(nxt)


# --- dashboard ---------------------------------------------------------------
@login_required
def dashboard(request):
    _ensure_both_wallets(request)
    demo_wallet = Wallet.objects.get(user=request.user, is_demo=True)
    real_wallet = Wallet.objects.get(user=request.user, is_demo=False)
    selected_wallet, is_demo = _get_selected_wallet(request)
    gold_rate = GoldRate.objects.order_by('-last_updated').first()

    context = {
        "selected_wallet": selected_wallet,
        "is_demo": is_demo,
        "demo_wallet": demo_wallet,
        "real_wallet": real_wallet,
        "demo_transactions": Transaction.objects.filter(wallet=demo_wallet).order_by("-timestamp")[:5],
        "real_transactions": Transaction.objects.filter(wallet=real_wallet).order_by("-timestamp")[:5],
        "buy_rate": gold_rate.buy_rate if gold_rate else 0,
        "sell_rate": gold_rate.sell_rate if gold_rate else 0,
        "last_updated": gold_rate.last_updated if gold_rate else None,
    }
    return render(request, "goldtrade/dashboard.html", context)

# ------------------------- BUY GOLD -------------------------------
@login_required
def buy_gold(request):
    rates = get_gold_price()

    if request.method == "POST":
        try:
            amount = Decimal(request.POST.get("amount", "0"))
            if amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return redirect("buy_gold")
        except Exception:
            messages.error(request, "Invalid amount.")
            return redirect("buy_gold")

        if rates["sell_rate"] <= 0:
            messages.error(request, "Sell rate not available.")
            return redirect("buy_gold")

        grams = (amount / rates["sell_rate"]).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
        try:
            with db_tx.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user, is_demo=_get_current_mode(request))

                if wallet.cash_balance < amount:
                    messages.error(request, "Insufficient balance!")
                    return redirect("buy_gold")

            wallet.cash_balance -= amount
            wallet.gold_balance += grams
            wallet.save(update_fields=["cash_balance", "gold_balance"])

            Transaction.objects.create(
                wallet=wallet,
                transaction_type="BUY",
                gold_amount=grams,
                price_per_gram=rates["sell_rate"],
                total_amount=amount,
            )

        messages.success(request, f"Bought {grams} g of gold.")
    except Exception:
        messages.error(request, "A database error occurred during the transaction.")
        # Log the error 'e' here if this were production code
    return redirect("buy_gold")

wallet, _ = _get_selected_wallet(request)
return render(request, "goldtrade/buy_gold.html", {
    "wallet": wallet,
    "buy_rate": rates["buy_rate"],
    "sell_rate": rates["sell_rate"],
})

# ------------------------- SELL GOLD ------------------------------
@login_required
def sell_gold(request):
    rates = get_gold_price()

    if request.method == "POST":
        try:
            grams = Decimal(request.POST.get("grams", "0"))
            if grams <= 0:
                messages.error(request, "Gold amount must be greater than zero.")
                return redirect("sell_gold")
        except Exception:
            messages.error(request, "Invalid grams.")
            return redirect("sell_gold")

        if rates["buy_rate"] <= 0:
            messages.error(request, "Buy rate not available.")
            return redirect("sell_gold")

        total = (grams * rates["buy_rate"]).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        try:
            with db_tx.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user, is_demo=_get_current_mode(request))

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
         except Exception as e:
            messages.error(request, "A database error occurred during the transaction.")
         return redirect("sell_gold")
    
    wallet, _ = _get_selected_wallet(request)
    return render(request, "goldtrade/sell_gold.html", {
        "wallet": wallet,
        "buy_rate": rates["buy_rate"],
        "sell_rate": rates["sell_rate"],
    })

# ------------------------- ADD MONEY ------------------------------
@login_required
def add_money(request):
    wallet = Wallet.objects.get(user=request.user, is_demo=False)

       if request.method == "POST":
        raw_amount = request.POST.get("amount") # Get raw string
        reference_no = request.POST.get("reference_no")
        slip = request.FILES.get("slip")
        
        try:
            # Safely convert and validate amount
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

        BankDeposit.objects.create(
            user=request.user,
            amount=amount,
            reference_no=reference_no,
            slip=slip,
            status="pending"
        )

        messages.success(request, "Deposit submitted ✅ Awaiting admin approval.")
        return redirect("add_money")

    return render(request, "goldtrade/add_money.html", {
        "wallet": wallet
    })

@login_required
def withdraw_money(request):
    wallet = Wallet.objects.get(user=request.user, is_demo=False)

    if request.method == "POST":
        amount = Decimal(request.POST.get("amount") or "0")
        bank_name = request.POST.get("bank_name")
        account_name = request.POST.get("account_name")
        account_number = request.POST.get("account_number")
        branch = request.POST.get("branch")

        if not all([amount, bank_name, account_name, account_number, branch]):
            messages.error(request, "Please fill in all fields.")
            return redirect("withdraw_money")

        if amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect("withdraw_money")

        if wallet.cash_balance < amount:
            messages.error(request, "Insufficient funds.")
            return redirect("withdraw_money")
        if Transaction.objects.filter(wallet=wallet, transaction_type="WITHDRAW", status="pending").exists():
            messages.warning(request, "You already have a pending withdrawal request.")
            return redirect("transactions")

        # ✅ create withdrawal request (not deducted yet)
        tx = Transaction.objects.create(
            wallet=wallet,
            transaction_type="WITHDRAW",
            total_amount=amount,
            remarks=f"{bank_name} - {branch} | {account_name} ({account_number})",
            status="pending"
        )

        # ✉️ Notify user instantly
        user = request.user
        if user.email:
            notify_user_email(
                user.email,
                "Withdrawal Request Received – Hifas Jewellery",
                f"""
                <p>Hi {user.username},</p>
                <p>We have received your withdrawal request and it's now <b>pending review</b>.</p>
                <p><b>Amount:</b> Rs. {amount:,.2f}<br>
                   <b>Bank Details:</b> {bank_name} - {branch} | {account_name} ({account_number})</p>
                <p>We'll notify you once it's approved or if we need more information.</p>
                <p>— Hifas Jewellery</p>
                """
            )

        messages.success(request, "Withdrawal request submitted ✅ Awaiting admin approval.")
        return redirect("withdraw_confirm", tx_id=tx.id)

    return render(request, "goldtrade/withdraw.html", {"wallet": wallet})


@login_required
def withdraw_confirm(request, tx_id):
    tx = get_object_or_404(
        Transaction,
        id=tx_id,
        wallet__user=request.user,
        transaction_type="WITHDRAW"
    )
    return render(request, "goldtrade/withdraw_confirm.html", {"tx": tx})

# --- transactions page (for currently selected wallet) -----------------------
@login_required
def transactions(request):
    wallet, _is_demo = _get_selected_wallet(request)
    tx = Transaction.objects.filter(wallet=wallet).order_by("-timestamp")
    return render(request, "goldtrade/transactions.html", {"transactions": tx})

# --- rates refresh / history (unchanged except imports) ----------------------
@cache_page(60)  # cache for 1 minute
def refresh_rates(request):
    try:
        gold = GoldRate.objects.latest('last_updated')
        data = {
            'buy_rate': float(gold.buy_rate),
            'sell_rate': float(gold.sell_rate),
            'last_updated': localtime(gold.last_updated).strftime("%Y-%m-%d %H:%M")
        }
    except GoldRate.DoesNotExist:
        data = {'buy_rate': 0, 'sell_rate': 0, 'last_updated': None}
    return JsonResponse(data)

def gold_price_history(request):
    last_30_days = now() - timedelta(days=30)
    history = GoldRate.objects.filter(last_updated__gte=last_30_days).order_by('last_updated')
    data = {
        "timestamps": [g.last_updated.isoformat() for g in history],  # send ISO 8601 UTC times
        "buy_rates": [float(g.buy_rate) for g in history],
        "sell_rates": [float(g.sell_rate) for g in history],
    }
    return JsonResponse(data)

@user_passes_test(lambda u: u.is_staff)
def update_gold_rate(request):
    latest = GoldRate.objects.order_by('-last_updated').first()

    if request.method == "POST":
        try:
            buy_rate = Decimal(request.POST.get("buy_rate", "0").replace(",", "").strip())
            sell_rate = Decimal(request.POST.get("sell_rate", "0").replace(",", "").strip())

            if buy_rate <= 0 or sell_rate <= 0:
                messages.error(request, "⚠️ Please enter valid positive rates.")
                return redirect("update_rate")

            GoldRate.objects.create(buy_rate=buy_rate, sell_rate=sell_rate)
            messages.success(request, "✅ Gold rates updated successfully!")
            return redirect("update_rate")

        except Exception as e:
            messages.error(request, f"⚠️ Price Update Error: {e}")
            return redirect("update_rate")

    return render(request, "goldtrade/update_rate.html", {
        "buy_rate": latest.buy_rate if latest else 0,
        "sell_rate": latest.sell_rate if latest else 0,
        "last_updated": latest.last_updated if latest else None
    })

@login_required
def my_deposits(request):
    deposits = BankDeposit.objects.filter(user=request.user).order_by('-created_at')
    wallet, _is_demo = _get_selected_wallet(request)
    return render(request, "goldtrade/my_deposits.html", {"deposits": deposits, "wallet": wallet})

@staff_member_required
def staff_deposits(request):
    q = request.GET.get("q", "").strip()
    qs = BankDeposit.objects.select_related("user").order_by(
        "-created_at"
    )
    if q:
        qs = qs.filter(reference_no__icontains=q)
    status = request.GET.get("status")
    if status in {"pending", "approved", "rejected"}:
        qs = qs.filter(status=status)
    return render(request, "goldtrade/staff_deposits.html", {"deposits": qs, "q": q, "status": status})

@staff_member_required
def staff_withdrawals(request):
    q = request.GET.get("q", "").strip()
    qs = Transaction.objects.filter(transaction_type="WITHDRAW").select_related("wallet__user").order_by("-timestamp")
    if q:
        qs = qs.filter(wallet__user__username__icontains=q)
    status = request.GET.get("status")
    if status in {"pending", "approved", "rejected"}:
        qs = qs.filter(status=status)
    return render(request, "goldtrade/staff_withdrawals.html", {"withdrawals": qs, "q": q, "status": status})

@staff_member_required
@db_tx.atomic
def approve_withdrawal(request, pk):
    # 1. Lock the transaction row
    # Use get_object_or_404 for proper error handling
    tx = get_object_or_404(
        Transaction.objects.select_for_update(), 
        id=pk, 
        transaction_type="WITHDRAW"
    )

    if tx.status != "pending":
        messages.warning(request, "Already processed.")
        return redirect("staff_withdrawals")

    # 2. Lock the associated wallet row
    # Use tx.wallet.pk to get the correct wallet ID for locking
    wallet = Wallet.objects.select_for_update().get(pk=tx.wallet.pk)

    if wallet.cash_balance < tx.total_amount:
        messages.error(request, "User wallet has insufficient balance.")
        return redirect("staff_withdrawals")

    # Deduct safely
    wallet.cash_balance -= tx.total_amount
    wallet.save(update_fields=['cash_balance'])

    tx.status = "approved"
    tx.processed_by = request.user
    tx.save(update_fields=['status', 'processed_by'])

    # Log a mirrored withdrawal for consistency
    Transaction.objects.create(
        wallet=wallet,
        transaction_type="WITHDRAW",
        total_amount=tx.total_amount,
        remarks=f"Admin approved withdrawal ({request.user.username})",
        status="approved"
    )

    # Notify user
    user = wallet.user
    if user.email:
        subject = "Withdrawal Approved – Hifas Jewellery"
        html = render_to_string("emails/withdrawal_approved.html", {
            "username": user.username,
            "amount": tx.total_amount,
            "bank_details": tx.remarks,
            "date": localtime(tx.timestamp).strftime("%Y-%m-%d %H:%M"),
            "site_url": "https://hifas-jewellery.onrender.com",
            "year": now().year,
        })
        notify_user_email(user.email, subject, html)

    messages.success(request, f"Withdrawal of Rs. {tx.total_amount:,.2f} approved ✅")
    return redirect("staff_withdrawals")

@staff_member_required
def reject_withdrawal(request, pk):
    tx = get_object_or_404(Transaction, id=pk, transaction_type="WITHDRAW")
    if tx.status != "pending":
        messages.warning(request, "Already processed.")
        return redirect("staff_withdrawals")

    tx.status = "rejected"
    tx.processed_by = request.user
    tx.save()

    # ✉️ Email user
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

@staff_member_required
@db_tx.atomic
def approve_deposit(request, pk):
    deposit = get_object_or_404(BankDeposit.objects.select_for_update(), id=pk)

    if deposit.status != "pending":
        messages.warning(request, "⚠️ This deposit is already processed.")
        return redirect("staff_deposits")

    # ✅ Credit amount to REAL wallet
    wallet = Wallet.objects.select_for_update().get(user=deposit.user, is_demo=False)
    wallet.cash_balance += Decimal(deposit.amount)
    wallet.save(update_fields=['cash_balance'])

    Transaction.objects.create(
    wallet=wallet,
    transaction_type="DEPOSIT",
    total_amount=deposit.amount,
    remarks=f"Bank deposit ref: {deposit.reference_no}",
    status="approved"
    )

    # ✅ Update deposit status
    deposit.status = "approved"
    deposit.save(update_fields=["status"])

    # ✅ Send email notification
    if deposit.user.email:
        html = render_to_string("emails/deposit_approved.html", {
            "username": deposit.user.username,
            "amount": f"{deposit.amount:,.2f}",
            "reference_no": deposit.reference_no,
            "date": localtime(deposit.created_at).strftime("%Y-%m-%d %H:%M"),
            "site_url": "https://hifas-jewellery.onrender.com",
            "year": now().year,
        })
        notify_user_email(deposit.user.email, "Deposit Approved – Hifas Jewellery", html)

    messages.success(request, f"✅ Deposit approved. Rs. {deposit.amount:,.2f} credited to {deposit.user.username}.")
    return redirect("staff_deposits")
    
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
            """
        )

    messages.info(request, "❌ Deposit rejected.")
    return redirect("staff_deposits")

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')
        try:
            with db_tx.atomic():

        user = User.objects.create_user(username=username, email=email, password=password)
        # Use defaults to set initial balance only on creation
        Wallet.objects.create(user=user, is_demo=True, cash_balance=Decimal('500000.00'))
        Wallet.objects.create(user=user, is_demo=False) # Cash balance defaults to 0
        messages.success(request, "Account created successfully! Please log in.")
        return redirect('login')
        except Exception as e:
            messages.error(request, f"Registration failed due to an error.")
            # Log error 'e' here.
            return redirect('register')
  return render(request, 'register.html')
    
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "No account found with this email.")
            return redirect("forgot_password")

        # send dummy link (you’ll replace with secure token later)
        send_mail(
            "Reset your Digital Gold account password",
            "Click here to reset your password: http://127.0.0.1:8000/reset-confirm/",
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )

        messages.success(request, "Reset link sent to your email ✅")
        return redirect("forgot_password")

    return render(request, "forgot_password.html")

