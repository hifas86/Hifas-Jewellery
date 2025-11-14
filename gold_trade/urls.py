# gold_trade/urls.py

from django.contrib import admin
from django.urls import path
from . import views,
from . import views_auth as auth_views,

urlpatterns = [

    # ------------------------------
    # AUTH ROUTES
    # ------------------------------
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('register/', auth_views.register_view, name='register'),
    path('forgot-password/', auth_views.forgot_password, name='forgot_password'),
    path('reset-confirm/', auth_views.reset_confirm, name='reset_confirm'),
    path('reset-success/', auth_views.reset_success, name='reset_success'),

    # ------------------------------
    # GOLD TRADE APP ROUTES
    # ------------------------------
    path('', app_views.dashboard, name='dashboard'),
    path('switch-wallet/<str:mode>/', app_views.switch_wallet, name='switch_wallet'),

    # ---- GOLD BUY / SELL ----
    path('buy-gold/', app_views.buy_gold, name='buy_gold'),
    path('sell-gold/', app_views.sell_gold, name='sell_gold'),

    # ---- MONEY OPERATIONS ----
    path('my-deposits/', views.my_deposits, name='my_deposits'),
    path('add-money/', app_views.add_money, name='add_money'),
    path('withdraw-money/', app_views.withdraw_money, name='withdraw_money'),
    path('withdraw-confirm/<int:tx_id>/', app_views.withdraw_confirm, name='withdraw_confirm'),

    # ---- USER TRANSACTIONS ----
    path('transactions/', app_views.transactions, name='transactions'),

    # ---- GOLD PRICE ----
    path('refresh-rates/', app_views.refresh_rates, name='refresh_rates'),
    path('gold-history/', app_views.gold_price_history, name='gold_price_history'),

    # ------------------------------
    # ADMIN PANEL – DEPOSITS & WITHDRAWALS
    # ------------------------------
    path('staff/deposits/', app_views.staff_deposits, name='staff_deposits'),
    path('staff/withdrawals/', app_views.staff_withdrawals, name='staff_withdrawals'),

    path('staff/deposits/approve/<int:pk>/', app_views.approve_deposit, name='approve_deposit'),
    path('staff/deposits/reject/<int:pk>/', app_views.reject_deposit, name='reject_deposit'),

    path('staff/withdrawals/approve/<int:pk>/', app_views.approve_withdrawal, name='approve_withdrawal'),
    path('staff/withdrawals/reject/<int:pk>/', app_views.reject_withdrawal, name='reject_withdrawal'),
    path('update-rate/', views.update_gold_rate, name='update_rate'),


    # ------------------------------
    # DJANGO ADMIN
    # ------------------------------
    path('admin/', admin.site.urls),
]
