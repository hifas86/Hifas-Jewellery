from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from users.views_email import verify_email, resend_verification

from . import views, views_auth

urlpatterns = [
    # Live notifications
    path("live-notifications/", views.live_notifications, name="live_notifications"),  # ✅ Now works

    # KYC
    path("kyc/", views.kyc_form, name="kyc_form"),
    path("kyc/status/", views.kyc_status, name="kyc_status"),

    # Profile
    path("profile/", views.profile_view, name="profile"),
    path("profile/upload/", views.profile_picture_upload, name="profile_picture_upload"),
    path("profile/remove/", views.profile_picture_remove, name="profile_picture_remove"),
    path("profile/update/", views.profile_update, name="profile_update"),
    path("profile/change-password/", views_auth.change_password, name="change_password"),

    # Authentication
    path('login/', views_auth.login_view, name='login'),
    path('logout/', views_auth.logout_view, name='logout'),
    path('register/', views_auth.register_view, name='register'),
    path('forgot-password/', views_auth.forgot_password, name='forgot_password'),

    # Email verification
    path("verify-email/<uuid:token>/", verify_email, name="verify_email"),
    path("resend-verification/", resend_verification, name="resend_verification"),

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
    path("my-withdrawals/", views.my_withdrawals, name="my_withdrawals"),

    # Django admin (must exist to avoid NoReverseMatch: 'admin')
    path("admin/", admin.site.urls),
    
    # Staff
    path('staff/deposits/', views.staff_deposits, name='staff_deposits'),
    path('staff/deposits/<int:pk>/approve/', views.approve_deposit, name='approve_deposit'),
    path('staff/deposits/<int:pk>/reject/', views.reject_deposit, name='reject_deposit'),

    path('staff/withdrawals/', views.staff_withdrawals, name='staff_withdrawals'),
    path('staff/withdrawals/<int:pk>/approve/', views.approve_withdrawal, name='approve_withdrawal'),
    path('staff/withdrawals/<int:pk>/reject/', views.reject_withdrawal, name='reject_withdrawal'),

    # Admin KYC approval
    path("staff/kyc/", views.kyc_admin_list, name="kyc_admin_list"),
    path("staff/kyc/<int:pk>/review/", views.kyc_admin_review, name="kyc_admin_review"),
    path("staff/kyc/<int:pk>/approve/", views.kyc_admin_approve, name="kyc_admin_approve"),
    path("staff/kyc/<int:pk>/reject/", views.kyc_admin_reject, name="kyc_admin_reject"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
