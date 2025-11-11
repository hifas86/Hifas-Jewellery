from django.contrib import admin
from django.urls import path, include
from goldtrade import views as app_views
from goldtrade import views_auth as auth_views
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static
from goldtrade import views, views_auth


# Temporary stub so the sidebar link doesn't crash
def reports_placeholder(request):
    return HttpResponse("Reports page coming soon.")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('goldtrade.urls')),
    path('', app_views.dashboard, name='dashboard'),

    path('buy/', app_views.buy_gold, name='buy_gold'),
    path('sell/', app_views.sell_gold, name='sell_gold'),
    path('transactions/', app_views.transactions, name='transactions'),
    path('update-rate/', app_views.update_gold_rate, name='update_rate'),
    path('refresh-rates/', app_views.refresh_rates, name='refresh_rates'),

    path('login/', views_auth.login_view, name='login'),
    path('logout/', views_auth.logout_view, name='logout'),
    path('register/', views_auth.register_view, name='register'),
    path('forgot-password/', views_auth.forgot_password, name='forgot_password'),
    path('reset-confirm/', views_auth.reset_confirm, name='reset_confirm'),

    # keep the base.html link happy
    path('reports/', reports_placeholder, name='reports'),
    path('gold-history/', app_views.gold_price_history, name='gold_history'),
    path('add-money/', app_views.add_money, name='add_money'),
    path('withdraw/', app_views.withdraw_money, name='withdraw_money'),
    path('withdraw/confirm/<int:tx_id>/', app_views.withdraw_confirm, name='withdraw_confirm'),
    path('deposits/', app_views.my_deposits, name='my_deposits'),
    path('switch-wallet/<str:mode>/', app_views.switch_wallet, name='switch_wallet'),

    # Staff actions
    path('staff/deposits/', app_views.staff_deposits, name='staff_deposits'),
    path('staff/deposits/<int:pk>/approve/', app_views.approve_deposit, name='approve_deposit'),
    path('staff/deposits/<int:pk>/reject/', app_views.reject_deposit, name='reject_deposit'),

    # Withdrawals (Admin)
    path('staff/withdrawals/', app_views.staff_withdrawals, name='staff_withdrawals'),
    path('staff/withdrawals/<int:pk>/approve/', app_views.approve_withdrawal, name='approve_withdrawal'),
    path('staff/withdrawals/<int:pk>/reject/', app_views.reject_withdrawal, name='reject_withdrawal'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
