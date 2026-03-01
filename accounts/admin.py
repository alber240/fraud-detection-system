from django.contrib import admin
from django.contrib import messages
from django.core.mail import send_mail
from .models import Customer, Account

class CustomerAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'kyc_status', 'image_approved']
    list_filter = ['kyc_status', 'image_approved']
    actions = ['approve_customers']

    def approve_customers(self, request, queryset):
        for customer in queryset:
            if customer.kyc_status != 'verified':
                customer.kyc_status = 'verified'
                customer.save()
                # Send email
                account = customer.accounts.first()
                if account:
                    send_mail(
                        'Account Approved',
                        f'Your account has been approved. Your account number is {account.account_number}.',
                        'admin@securebank.com',
                        [customer.user.email],
                        fail_silently=False,
                    )
        self.message_user(request, f"{queryset.count()} customers approved.")
    approve_customers.short_description = "Approve selected customers"

admin.site.register(Customer, CustomerAdmin)
admin.site.register(Account)