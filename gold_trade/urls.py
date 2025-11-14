from django.urls import path
from . import views, views_auth

urlpatterns = [
    # 🔐 Authentication routes
    path('login/', views_auth.login_view, name='login'),
    path('logout/', views_auth.logout_view, name='logout'),
    path('register/', views_auth.register_view, name='register'),
    path('forgot-password/', views_auth.forgot_password, name='forgot_password'),
    path('reset-confirm/', views_auth.reset_confirm, name='reset_confirm'),
    path('reset-success/', views_auth.reset_success, name='reset_success'),

    # 💰 Core App routes
    path('', views.dashboard, name='dashboard'),
    path('update-rate/', views.update_gold_rate, name='update_rate'),
    path('buy-gold/', views.buy_gold, name='buy_gold'),
    path('sell-gold/', views.sell_gold, name='sell_gold'),
    path('transactions/', views.transactions, name='transactions'),
    path('refresh-rates/', views.refresh_rates, name='refresh_rates'),
    path('gold-history/', views.gold_price_history, name='gold_history'),

    path('add-money/', views.add_money, name='add_money'),
    path('withdraw/', views.withdraw_money, name='withdraw_money'),
    path('withdraw/confirm/<int:tx_id>/', views.withdraw_confirm, name='withdraw_confirm'),

    path('my-deposits/', views.my_deposits, name='my_deposits'),

    # Staff actions
    path('staff/deposits/', views.staff_deposits, name='staff_deposits'),
    path('staff/deposits/<int:pk>/approve/', views.approve_deposit, name='approve_deposit'),
    path('staff/deposits/<int:pk>/reject/', views.reject_deposit, name='reject_deposit'),

    path('staff/withdrawals/', views.staff_withdrawals, name='staff_withdrawals'),
    path('staff/withdrawals/<int:pk>/approve/', views.approve_withdrawal, name='approve_withdrawal'),
    path('staff/withdrawals/<int:pk>/reject/', views.reject_withdrawal, name='reject_withdrawal'),
]
