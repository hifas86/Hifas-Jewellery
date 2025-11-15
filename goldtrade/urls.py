from django.urls import path
from . import views, views_auth

urlpatterns = [
    # Django admin (must exist to avoid NoReverseMatch: 'admin')
    path("admin/", admin.site.urls),
    
    # Authentication
    path('login/', views_auth.login_view, name='login'),
    path('logout/', views_auth.logout_view, name='logout'),
    path('register/', views_auth.register_view, name='register'),
    path('forgot-password/', views_auth.forgot_password, name='forgot_password'),

    # Live notifications
    path("live-notifications/", views.live_notifications, name="live_notifications"),  # ✅ Now works
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Wallet switch
    path('switch-wallet/<str:mode>/', views.switch_wallet, name='switch_wallet'),

    # Gold Trading
    path('buy-gold/', views.buy_gold, name='buy_gold'),
    path('sell-gold/', views.sell_gold, name='sell_gold'),
    path('transactions/', views.transactions, name='transactions'),

    # Rates
    path('update-rate/', views.update_gold_rate, name='update_rate'),
    path('refresh-rates/', views.refresh_rates, name='refresh_rates'),
    path('gold-history/', views.gold_price_history, name='gold_history'),

    # Deposits / Withdrawals
    path('add-money/', views.add_money, name='add_money'),
    path('my-deposits/', views.my_deposits, name='my_deposits'),
    path('withdraw/', views.withdraw_money, name='withdraw_money'),
    path('withdraw/confirm/<int:tx_id>/', views.withdraw_confirm, name='withdraw_confirm'),

    # Staff
    path('staff/deposits/', views.staff_deposits, name='staff_deposits'),
    path('staff/deposits/<int:pk>/approve/', views.approve_deposit, name='approve_deposit'),
    path('staff/deposits/<int:pk>/reject/', views.reject_deposit, name='reject_deposit'),

    path('staff/withdrawals/', views.staff_withdrawals, name='staff_withdrawals'),
    path('staff/withdrawals/<int:pk>/approve/', views.approve_withdrawal, name='approve_withdrawal'),
    path('staff/withdrawals/<int:pk>/reject/', views.reject_withdrawal, name='reject_withdrawal'),
]
