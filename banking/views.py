from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import DepositForm, WithdrawalForm, TransferForm
from .models import BankingTransaction
from accounts.models import Account
from prediction.ml_service import combined_risk
from prediction.models import FraudAlert
from django_ratelimit.decorators import ratelimit

@login_required
@ratelimit(key='ip', rate='5/m', method='POST')
def deposit(request):
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']

            # Ensure the account belongs to the logged-in user
            if account.customer.user != request.user:
                messages.error(request, "You can only deposit into your own accounts.")
                return redirect('deposit')

            # Update balance
            account.balance += amount
            account.save()

            # Create transaction record
            transaction = BankingTransaction.objects.create(
                to_account=account,
                transaction_type='deposit',
                amount=amount,
                description=description
            )

            # Fraud detection – risk is now a Python float
            risk = combined_risk(transaction)
            transaction.fraud_probability = risk
            transaction.fraud_prediction = risk > 0.5
            transaction.save()

            # Create alert if high risk
            if risk > 0.8:
                FraudAlert.objects.get_or_create(transaction=transaction)

            messages.success(request, f"Deposited ${amount} to account {account.account_number}")
            return redirect('customer_dashboard')
    else:
        form = DepositForm()
    return render(request, 'banking/deposit.html', {'form': form})


@login_required
@ratelimit(key='ip', rate='5/m', method='POST')
def withdraw(request):
    if request.method == 'POST':
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']

            if account.customer.user != request.user:
                messages.error(request, "You can only withdraw from your own accounts.")
                return redirect('withdraw')

            if account.balance < amount:
                messages.error(request, "Insufficient funds.")
                return redirect('withdraw')

            account.balance -= amount
            account.save()

            transaction = BankingTransaction.objects.create(
                from_account=account,
                transaction_type='withdrawal',
                amount=amount,
                description=description
            )

            risk = combined_risk(transaction)
            transaction.fraud_probability = risk
            transaction.fraud_prediction = risk > 0.5
            transaction.save()

            if risk > 0.8:
                FraudAlert.objects.get_or_create(transaction=transaction)

            messages.success(request, f"Withdrew ${amount} from account {account.account_number}")
            return redirect('customer_dashboard')
    else:
        form = WithdrawalForm()
    return render(request, 'banking/withdraw.html', {'form': form})


@login_required
@ratelimit(key='ip', rate='5/m', method='POST')
def transfer(request):
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            from_account = form.cleaned_data['from_account']
            to_account = form.cleaned_data['to_account']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']

            if from_account.customer.user != request.user:
                messages.error(request, "You can only transfer from your own accounts.")
                return redirect('transfer')

            if from_account.balance < amount:
                messages.error(request, "Insufficient funds.")
                return redirect('transfer')

            from_account.balance -= amount
            to_account.balance += amount
            from_account.save()
            to_account.save()

            transaction = BankingTransaction.objects.create(
                from_account=from_account,
                to_account=to_account,
                transaction_type='transfer',
                amount=amount,
                description=description
            )

            risk = combined_risk(transaction)
            transaction.fraud_probability = risk
            transaction.fraud_prediction = risk > 0.5
            transaction.save()

            if risk > 0.8:
                FraudAlert.objects.get_or_create(transaction=transaction)

            messages.success(request, f"Transferred ${amount} from {from_account.account_number} to {to_account.account_number}")
            return redirect('customer_dashboard')
    else:
        form = TransferForm()
    return render(request, 'banking/transfer.html', {'form': form})