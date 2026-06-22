"""
Views for the accounts app.
Handles user registration, customer dashboard, and post-login redirection.
"""

from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q

from .forms import CustomerRegistrationForm
from .models import Customer, Account
from banking.models import BankingTransaction
from .decorators import customer_required
from django.utils import timezone


def register(request):
    """
    Handle new customer registration.
    - Validates the registration form (including optional image uploads).
    - Creates a User and associated Customer profile.
    - Creates a default checking account with an initial balance.
    - Logs the user in.
    - Sends a notification email to the admin about the new KYC submission.
    """
    if request.method == 'POST':
        # Include request.FILES to handle profile image and document uploads
        form = CustomerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()                     # also creates the Customer

            # Send email notification to admin (using settings.ADMIN_EMAIL)
            send_mail(
                   'New KYC Submission',
                   f'A new customer {user.username} has registered and submitted KYC documents.',
                   settings.DEFAULT_FROM_EMAIL,
                   [settings.ADMIN_EMAIL],          # <-- use settings.ADMIN_EMAIL
                   fail_silently=True,
                       )
            
            

            # Create a default checking account with $100 opening balance
            Account.objects.create(
                customer=user.customer,
                account_type='checking',
                balance=100.00
            )

            # Log the user in immediately after registration
            login(request, user)

            messages.success(request, "Registration successful. Welcome!")
            return redirect('customer_dashboard')
        else:
            # If form is invalid, print errors to the console and show a generic message
            print(form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
@customer_required
def customer_dashboard(request):
    """
    Display the customer's dashboard showing their accounts and recent transactions.
    - Requires the user to be logged in and have a Customer profile.
    """
    try:
        customer = request.user.customer
        accounts = customer.accounts.all()
        # Fetch transactions where this customer's accounts are involved
        transactions = BankingTransaction.objects.filter(
            Q(from_account__in=accounts) | Q(to_account__in=accounts)
        ).order_by('-timestamp')[:50]
    except Customer.DoesNotExist:
        # In case the user somehow doesn't have a Customer profile
        customer = None
        accounts = []
        transactions = []

    return render(request, 'accounts/customer_dashboard.html', {
        'customer': customer,
        'accounts': accounts,
        'transactions': transactions,
    })


@login_required
def post_login_redirect(request):
    """
    Redirect users after login based on their role:
    - Customers go to their dashboard.
    - Staff members go to the fraud dashboard.
    - Everyone else (should not happen) goes to the home page.
    """
    if hasattr(request.user, 'customer'):
        return redirect('customer_dashboard')
    elif request.user.is_staff or request.user.groups.filter(name='Staff').exists():
        return redirect('dashboard')
    else:
        return redirect('home')
    
from django.contrib.admin.views.decorators import staff_member_required
from .models import Customer

@staff_member_required
def pending_kyc(request):
    """View pending KYC applications for admin approval"""
    pending_customers = Customer.objects.filter(kyc_status='pending')
    return render(request, 'accounts/pending_kyc.html', {
        'pending_customers': pending_customers
    })


@staff_member_required
def approve_kyc(request, customer_id):
    """Approve a customer's KYC application"""
    customer = get_object_or_404(Customer, id=customer_id)
    if request.method == 'POST':
        customer.kyc_status = 'verified'
        customer.save()
        
        # Send email notification
        try:
            send_mail(
                'KYC Approved',
                f'Your KYC has been approved. You can now perform banking operations.',
                settings.DEFAULT_FROM_EMAIL,
                [customer.user.email],
                fail_silently=True,
            )
        except:
            pass
        
        messages.success(request, f'KYC for {customer.user.username} approved!')
        return redirect('pending_kyc')
    
    return render(request, 'accounts/approve_kyc.html', {'customer': customer})


@staff_member_required
def reject_kyc(request, customer_id):
    """Reject a customer's KYC application"""
    customer = get_object_or_404(Customer, id=customer_id)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        customer.kyc_status = 'rejected'
        customer.kyc_rejection_reason = reason
        customer.save()
        messages.warning(request, f'KYC for {customer.user.username} rejected!')
        return redirect('pending_kyc')
    
    return render(request, 'accounts/reject_kyc.html', {'customer': customer})