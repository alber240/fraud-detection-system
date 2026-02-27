from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'amount', 'timestamp', 'prediction', 'probability')
    list_filter = ('prediction',)
    search_fields = ('transaction_id', 'account_number')