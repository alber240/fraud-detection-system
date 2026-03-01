from django import forms
from .models import Transaction

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['transaction_id', 'account_number', 'amount', 'merchant', 'location', 'device_id']
        widgets = {
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'TXN001'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ACC123'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'merchant': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Store Name'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'device_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Device ID (optional)'}),
        }