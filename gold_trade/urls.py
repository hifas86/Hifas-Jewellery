from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('goldtrade.urls')),   # include app-level routes
    path("live-notifications/", views.live_notifications, name="live_notifications"),
]
