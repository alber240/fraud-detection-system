from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import CustomerRegistrationForm
from .models import Account

def register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()  # this also creates Customer
            # Create a checking account with initial balance
            Account.objects.create(
                customer=user.customer,
                account_type='checking',
                balance=100.00
            )
            login(request, user)
            messages.success(request, "Registration successful. Welcome!")
            return redirect('customer_dashboard')
        else:
            # Print errors to console for debugging
            print(form.errors)
            # Pass form with errors back to template
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Customer
from banking.models import BankingTransaction
from django.db.models import Q

from .decorators import customer_required
@login_required
@customer_required
def customer_dashboard(request):
    try:
        customer = request.user.customer
        accounts = customer.accounts.all()
        transactions = BankingTransaction.objects.filter(
            Q(from_account__in=accounts) | Q(to_account__in=accounts)
        ).order_by('-timestamp')[:50]
    except Customer.DoesNotExist:
        customer = None
        accounts = []
        transactions = []
    return render(request, 'accounts/customer_dashboard.html', {
        'customer': customer,
        'accounts': accounts,
        'transactions': transactions,
    })
    

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def post_login_redirect(request):
    if hasattr(request.user, 'customer'):
        return redirect('customer_dashboard')
    elif request.user.is_staff or request.user.groups.filter(name='Staff').exists():
        return redirect('dashboard')
    else:
        return redirect('home')