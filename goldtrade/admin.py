from django.contrib import admin
from .models import Wallet, Transaction, GoldRate, BankDeposit

@admin.register(BankDeposit)
class BankDepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'reference_no', 'created_at', 'slip_preview')
    list_filter = ('status',)
    search_fields = ('user__username', 'reference_no')
    readonly_fields = ('slip_preview',)

    # ✅ Show image preview in admin panel
    def slip_preview(self, obj):
        if obj.slip:
            return f'<img src="{obj.slip.url}" style="height:80px;" />'
        return "No slip"
    slip_preview.allow_tags = True
    slip_preview.short_description = "Slip Preview"


@admin.register(GoldRate)
class GoldRateAdmin(admin.ModelAdmin):
    list_display = ('buy_rate', 'sell_rate', 'last_updated')
    readonly_fields = ('last_updated',)


admin.site.register(Wallet)
admin.site.register(Transaction)
admin.site.site_header = "Hifas Jewellery Admin Panel 💎"
admin.site.site_title = "Hifas Jewellery Admin"
admin.site.index_title = "Welcome to Hifas Jewellery Dashboard"
