from django import forms
from accounts.models import Account

class DepositForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.filter(is_active=True), label="Account")
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    description = forms.CharField(max_length=200, required=False, widget=forms.Textarea(attrs={'rows': 2}))

class WithdrawalForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.filter(is_active=True), label="Account")
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    description = forms.CharField(max_length=200, required=False, widget=forms.Textarea(attrs={'rows': 2}))

class TransferForm(forms.Form):
    from_account = forms.ModelChoiceField(queryset=Account.objects.filter(is_active=True), label="From Account")
    to_account = forms.ModelChoiceField(queryset=Account.objects.filter(is_active=True), label="To Account")
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    description = forms.CharField(max_length=200, required=False, widget=forms.Textarea(attrs={'rows': 2}))