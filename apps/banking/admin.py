# apps/banking/admin.py
from django.contrib import admin
from .models import Account, TransactionHistory

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "bank_code", "account_number", "account_type", "balance", "created_at")
    list_filter = ("bank_code", "account_type", "created_at")
    search_fields = ("account_number", "user__email")
    autocomplete_fields = ("user",)

@admin.register(TransactionHistory)
class TransactionHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "io_type", "method", "amount", "balance_after", "created_at", "description")
    list_filter = ("io_type", "method", "created_at")
    search_fields = ("account__account_number", "description")
    autocomplete_fields = ("account",)
