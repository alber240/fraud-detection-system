"""
Banking Views for Fraud Detection System
Handles deposits, withdrawals, transfers, AML compliance, and fraud alerts.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction as db_transaction
from .forms import DepositForm, WithdrawalForm, TransferForm
from .models import BankingTransaction, ComplianceFlag
from accounts.models import Account
from prediction.ml_service import predict_fraud_combined, get_model_info
from prediction.models import FraudAlert
from django_ratelimit.decorators import ratelimit
from .aml_engine import check_aml_rules
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .feature_engineering import FeatureEngineer
# Set up logging
logger = logging.getLogger(__name__)
from django.db import models
from django.conf import settings
import time
from prediction.models import NetworkEvent


# ============================================================
# DEPOSIT VIEW
# ============================================================

@login_required
@ratelimit(key='ip', rate='5/m', method='POST')
def deposit(request):
    try:
        if request.method == 'POST':
            form = DepositForm(request.POST)
            if form.is_valid():
                account = form.cleaned_data['account']
                amount = form.cleaned_data['amount']
                description = form.cleaned_data['description']

                # ============================================================
                # KYC CHECK - ADD THIS HERE (After form validation)
                # ============================================================
                if account.customer.kyc_status != 'verified':
                    messages.error(request, "Your KYC is pending approval. You cannot perform transactions.")
                    return redirect('customer_dashboard')
                # ============================================================

                if account.customer.user != request.user:
                    messages.error(request, "You can only deposit into your own accounts.")
                    return redirect('deposit')

                account.balance += amount
                account.save()

                transaction = BankingTransaction.objects.create(
                    to_account=account,
                    transaction_type='deposit',
                    amount=amount,
                    description=description
                )

                prediction, risk = predict_fraud_combined(float(amount))
                transaction.fraud_prediction = prediction
                transaction.fraud_probability = risk
                transaction.save()

                # ============================================================
                # ADD FEATURE ENGINEERING HERE - AFTER transaction.save()
                # ============================================================
                from .feature_engineering import FeatureEngineer
                FeatureEngineer.engineer_features_for_transaction(transaction)
                # ============================================================

                check_aml_rules(transaction)

                if risk > 0.8:
                    FraudAlert.objects.get_or_create(banking_transaction=transaction)

                # WebSocket broadcast
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        'transactions_group',
                        {
                            'type': 'transaction_update',
                            'transaction': {
                                'id': str(transaction.transaction_id)[:8],
                                'amount': str(transaction.amount),
                                'timestamp': transaction.timestamp.isoformat(),
                                'prediction': transaction.fraud_prediction,
                                'probability': transaction.fraud_probability,
                                'type': transaction.transaction_type
                            }
                        }
                    )
                except Exception as e:
                    print(f"WebSocket broadcast error: {e}")

                messages.success(request, f"Deposited ${amount} to account {account.account_number}")
                return redirect('customer_dashboard')
        else:
            form = DepositForm()

        return render(request, 'banking/deposit.html', {'form': form})

    except Exception as e:
        logger.error(f"Deposit error: {e}")
        messages.error(request, "An error occurred. Please try again.")
        return redirect('customer_dashboard')

# ============================================================
# WITHDRAWAL VIEW
# ============================================================

@login_required
@ratelimit(key='ip', rate='5/m', method='POST')
def withdraw(request):
    try:
        if request.method == 'POST':
            form = WithdrawalForm(request.POST)
            if form.is_valid():
                account = form.cleaned_data['account']
                amount = form.cleaned_data['amount']
                description = form.cleaned_data['description']

                # ============================================================
                # KYC CHECK - ADD THIS HERE
                # ============================================================
                if account.customer.kyc_status != 'verified':
                    messages.error(request, "Your KYC is pending approval. You cannot perform transactions.")
                    return redirect('customer_dashboard')
                # ============================================================

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

                prediction, risk = predict_fraud_combined(float(amount))
                transaction.fraud_prediction = prediction
                transaction.fraud_probability = risk
                transaction.save()

                from .feature_engineering import FeatureEngineer
                FeatureEngineer.engineer_features_for_transaction(transaction)

                check_aml_rules(transaction)

                if risk > 0.8:
                    FraudAlert.objects.get_or_create(banking_transaction=transaction)

                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        'transactions_group',
                        {
                            'type': 'transaction_update',
                            'transaction': {
                                'id': str(transaction.transaction_id)[:8],
                                'amount': str(transaction.amount),
                                'timestamp': transaction.timestamp.isoformat(),
                                'prediction': transaction.fraud_prediction,
                                'probability': transaction.fraud_probability,
                                'type': transaction.transaction_type
                            }
                        }
                    )
                except Exception as e:
                    print(f"WebSocket broadcast error: {e}")

                messages.success(request, f"Withdrew ${amount} from account {account.account_number}")
                return redirect('customer_dashboard')
        else:
            form = WithdrawalForm()

        return render(request, 'banking/withdraw.html', {'form': form})

    except Exception as e:
        logger.error(f"Withdrawal error: {e}")
        messages.error(request, "An error occurred. Please try again.")
        return redirect('customer_dashboard')
# ============================================================
# TRANSFER VIEW
# ============================================================

@login_required
@ratelimit(key='ip', rate='5/m', method='POST')
def transfer(request):
    try:
        if request.method == 'POST':
            form = TransferForm(request.POST)
            if form.is_valid():
                from_account = form.cleaned_data['from_account']
                to_account = form.cleaned_data['to_account']
                amount = form.cleaned_data['amount']
                description = form.cleaned_data['description']

                # ============================================================
                # KYC CHECK - ADD THIS HERE (Check source account owner)
                # ============================================================
                if from_account.customer.kyc_status != 'verified':
                    messages.error(request, "Your KYC is pending approval. You cannot perform transactions.")
                    return redirect('customer_dashboard')
                # ============================================================

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

                prediction, risk = predict_fraud_combined(float(amount))
                transaction.fraud_prediction = prediction
                transaction.fraud_probability = risk
                transaction.save()

                from .feature_engineering import FeatureEngineer
                FeatureEngineer.engineer_features_for_transaction(transaction)

                check_aml_rules(transaction)

                if risk > 0.8:
                    FraudAlert.objects.get_or_create(banking_transaction=transaction)

                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        'transactions_group',
                        {
                            'type': 'transaction_update',
                            'transaction': {
                                'id': str(transaction.transaction_id)[:8],
                                'amount': str(transaction.amount),
                                'timestamp': transaction.timestamp.isoformat(),
                                'prediction': transaction.fraud_prediction,
                                'probability': transaction.fraud_probability,
                                'type': transaction.transaction_type
                            }
                        }
                    )
                except Exception as e:
                    print(f"WebSocket broadcast error: {e}")

                messages.success(request, f"Transferred ${amount} from {from_account.account_number} to {to_account.account_number}")
                return redirect('customer_dashboard')
        else:
            form = TransferForm()

        return render(request, 'banking/transfer.html', {'form': form})

    except Exception as e:
        logger.error(f"Transfer error: {e}")
        messages.error(request, "An error occurred. Please try again.")
        return redirect('customer_dashboard')

# ============================================================
# COMPLIANCE DASHBOARD (STAFF ONLY)
# ============================================================

@staff_member_required
def compliance_dashboard(request):
    """
    Display unresolved compliance flags for staff review.
    """
    try:
        flags = ComplianceFlag.objects.filter(resolved=False).select_related(
            'customer__user', 'transaction'
        ).order_by('-created_at')
        return render(request, 'banking/compliance_dashboard.html', {'flags': flags})
    except Exception as e:
        logger.error(f"Compliance dashboard error: {e}")
        messages.error(request, "Unable to load compliance dashboard.")
        return redirect('dashboard')


# ============================================================
# RESOLVE COMPLIANCE FLAG (STAFF ONLY)
# ============================================================

@staff_member_required
def resolve_flag(request, flag_id):
    """
    Handle resolution of a compliance flag.
    """
    try:
        flag = get_object_or_404(ComplianceFlag, id=flag_id)

        if request.method == 'POST':
            flag.resolved = True
            flag.resolved_at = timezone.now()
            flag.resolved_by = request.user
            flag.resolution_notes = request.POST.get('notes', '')
            flag.save()

            messages.success(request, f"Flag for {flag.customer.user.username} has been resolved.")
            return redirect('compliance_dashboard')

        return render(request, 'banking/resolve_flag.html', {'flag': flag})
    except Exception as e:
        logger.error(f"Resolve flag error: {e}")
        messages.error(request, "Unable to resolve flag.")
        return redirect('compliance_dashboard')


# ============================================================
# HEALTH CHECK / DEBUG VIEW (OPTIONAL)
# ============================================================

@staff_member_required
def model_info(request):
    """
    Debug view to check which ML models are loaded.
    """
    try:
        info = get_model_info()
        return render(request, 'banking/model_info.html', {'info': info})
    except Exception as e:
        logger.error(f"Model info error: {e}")
        return render(request, 'banking/model_info.html', {'info': {'error': str(e)}})
    
    
from django.db.models import Count, Avg, StdDev, Sum
from decimal import Decimal

@staff_member_required
def feature_analytics(request):
    """
    Dashboard showing feature engineering analytics
    """
    # Get feature statistics
    stats = {
        'avg_ratio': BankingTransaction.objects.filter(
            amount_ratio_to_avg__isnull=False
        ).aggregate(Avg('amount_ratio_to_avg'))['amount_ratio_to_avg__avg'] or 0,
        
        'avg_hour': BankingTransaction.objects.filter(
            transaction_hour__isnull=False
        ).aggregate(Avg('transaction_hour'))['transaction_hour__avg'] or 0,
        
        'avg_daily_count': BankingTransaction.objects.filter(
            transaction_count_last_24h__isnull=False
        ).aggregate(Avg('transaction_count_last_24h'))['transaction_count_last_24h__avg'] or 0,
        
        'fraud_ratio_high': BankingTransaction.objects.filter(
            fraud_prediction=True,
            amount_ratio_to_avg__gt=3
        ).count(),
        
        'total_transactions': BankingTransaction.objects.count(),
    }
    
    return render(request, 'banking/feature_analytics.html', {'stats': stats})


from django.db.models import Q
from django.utils import timezone

@staff_member_required
def review_queue(request):
    """
    Manual review queue for suspicious transactions
    Analyst can approve, block, or mark for investigation
    """
    # Get transactions that need review
    pending_transactions = BankingTransaction.objects.filter(
        Q(review_status='pending') | 
        Q(fraud_prediction=True, review_status='pending') |
        Q(fraud_probability__gt=0.5, review_status='pending')
    ).order_by('-timestamp')
    
    # Get statistics
    stats = {
        'pending_count': pending_transactions.count(),
        'approved_count': BankingTransaction.objects.filter(review_status='approved').count(),
        'blocked_count': BankingTransaction.objects.filter(review_status='blocked').count(),
        'investigating_count': BankingTransaction.objects.filter(review_status='investigating').count(),
        'high_risk_pending': pending_transactions.filter(fraud_probability__gt=0.8).count(),
        'medium_risk_pending': pending_transactions.filter(fraud_probability__gt=0.5, fraud_probability__lte=0.8).count(),
    }
    
    return render(request, 'banking/review_queue.html', {
        'transactions': pending_transactions,
        'stats': stats
    })


@staff_member_required
def review_transaction(request, transaction_id):
    """
    Review a specific transaction - approve, block, or investigate
    """
    transaction = get_object_or_404(BankingTransaction, id=transaction_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        block_reason = request.POST.get('block_reason', '')
        
        if action == 'approve':
            transaction.review_status = 'approved'
            transaction.fraud_prediction = False  # Override as legitimate
            transaction.fraud_probability = 0.05
            messages.success(request, f'Transaction {transaction.transaction_id} has been approved.')
            
        elif action == 'block':
            transaction.review_status = 'blocked'
            transaction.block_reason = block_reason
            messages.warning(request, f'Transaction {transaction.transaction_id} has been blocked.')
            
        elif action == 'investigate':
            transaction.review_status = 'investigating'
            messages.info(request, f'Transaction {transaction.transaction_id} marked for investigation.')
        
        transaction.reviewed_by = request.user
        transaction.reviewed_at = timezone.now()
        transaction.review_notes = notes
        transaction.save()
        
        return redirect('review_queue')
    
    # Get similar transactions for this account
    similar_transactions = BankingTransaction.objects.filter(
        Q(from_account=transaction.from_account) | Q(to_account=transaction.to_account)
    ).exclude(id=transaction.id).order_by('-timestamp')[:5]
    
    context = {
        'transaction': transaction,
        'similar_transactions': similar_transactions,
        'risk_level': 'High' if transaction.fraud_probability > 0.8 else 'Medium' if transaction.fraud_probability > 0.5 else 'Low'
    }
    
    return render(request, 'banking/review_transaction.html', context)

import csv
from django.http import HttpResponse
from django.utils import timezone

@staff_member_required
def export_flagged_transactions(request):
    """
    Export flagged/suspicious transactions as CSV file
    """
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    transactions = BankingTransaction.objects.filter(
        models.Q(fraud_prediction=True) | models.Q(fraud_probability__gt=0.5)
    )
    
    # Apply filters
    if status_filter == 'pending':
        transactions = transactions.filter(review_status='pending')
    elif status_filter == 'approved':
        transactions = transactions.filter(review_status='approved')
    elif status_filter == 'blocked':
        transactions = transactions.filter(review_status='blocked')
    
    if date_from:
        transactions = transactions.filter(timestamp__gte=date_from)
    if date_to:
        transactions = transactions.filter(timestamp__lte=date_to)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="flagged_transactions_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'Transaction ID', 'Type', 'Amount', 'Date', 'From Account', 'To Account',
        'Fraud Prediction', 'Fraud Probability', 'Risk Level', 'Review Status',
        'Review Notes', 'Block Reason', 'Transaction Hour', 'Days Since Last TX',
        'Amount Ratio to Avg', 'TX Count Last 24h', 'Hours Since Last Login'
    ])
    
    # Write data rows
    for t in transactions:
        # Determine risk level
        if t.fraud_probability and t.fraud_probability > 0.8:
            risk_level = 'High'
        elif t.fraud_probability and t.fraud_probability > 0.5:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        writer.writerow([
            str(t.transaction_id),
            t.transaction_type,
            f"{t.amount:.2f}",
            t.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            t.from_account.account_number if t.from_account else '-',
            t.to_account.account_number if t.to_account else '-',
            'Yes' if t.fraud_prediction else 'No',
            f"{t.fraud_probability:.2%}" if t.fraud_probability else '0%',
            risk_level,
            t.get_review_status_display(),
            t.review_notes[:100] if t.review_notes else '-',
            t.block_reason if t.block_reason else '-',
            t.transaction_hour if t.transaction_hour else '-',
            f"{t.days_since_last_transaction:.1f}" if t.days_since_last_transaction else '-',
            f"{t.amount_ratio_to_avg:.2f}x" if t.amount_ratio_to_avg else '-',
            t.transaction_count_last_24h if t.transaction_count_last_24h else '-',
            f"{t.hours_since_last_login:.1f}" if t.hours_since_last_login else '-',
        ])
    
    return response


@staff_member_required
def export_page(request):
    """Export page with filters"""
    return render(request, 'banking/export_page.html')

import random
import threading
import time
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from accounts.models import Account, Customer
from .models import BankingTransaction
from prediction.ml_service import predict_fraud_combined

# Store simulation state
simulation_active = False
simulation_thread = None
simulation_transactions = []

@staff_member_required
def live_demo(request):
    """Live demo mode page"""
    return render(request, 'banking/live_demo.html')


@staff_member_required
def start_simulation(request):
    """Start live transaction simulation"""
    global simulation_active, simulation_thread
    
    if request.method == 'POST':
        simulation_active = True
        
        # Start simulation in background thread
        simulation_thread = threading.Thread(target=run_simulation, daemon=True)
        simulation_thread.start()
        
        return JsonResponse({'status': 'started', 'message': 'Live demo simulation started!'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@staff_member_required
def stop_simulation(request):
    """Stop live transaction simulation"""
    global simulation_active
    
    if request.method == 'POST':
        simulation_active = False
        return JsonResponse({'status': 'stopped', 'message': 'Live demo simulation stopped!'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@staff_member_required
def get_transactions_ajax(request):
    """Get recent simulated transactions for AJAX polling"""
    global simulation_transactions
    
    # Return last 20 transactions
    return JsonResponse({
        'transactions': simulation_transactions[-20:],
        'count': len(simulation_transactions)
    })


def run_simulation():
    """Background thread to generate simulated transactions"""
    global simulation_active, simulation_transactions
    
    # Sample transaction types
    transaction_types = ['deposit', 'withdrawal', 'transfer']
    merchants = ['Amazon', 'Walmart', 'Target', 'Best Buy', 'Starbucks', 'Uber', 'Netflix', 'Spotify']
    locations = ['Kigali', 'Musanze', 'Rubavu', 'Huye', 'Nyagatare', 'International']
    
    # Sample amounts (some normal, some suspicious)
    amounts = [10, 25, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000, 5000, 10000, 25000, 50000, 75000, 100000]
    
    while simulation_active:
        try:
            # Generate random transaction
            amount = random.choice(amounts)
            tx_type = random.choice(transaction_types)
            
            # Higher chance of high-risk for large amounts
            is_high_risk = amount > 50000 or (amount > 10000 and random.random() > 0.7)
            
            # Get fraud prediction
            pred, prob = predict_fraud_combined(float(amount))
            
            # Create transaction record
            transaction = {
                'id': int(time.time() * 1000),
                'amount': float(amount),
                'type': tx_type,
                'merchant': random.choice(merchants),
                'location': random.choice(locations),
                'timestamp': time.time(),
                'prediction': pred,
                'probability': prob,
                'risk_level': 'High' if prob > 0.8 else 'Medium' if prob > 0.5 else 'Low'
            }
            
            # Add to list
            simulation_transactions.append(transaction)
            
            # Keep only last 100 transactions
            if len(simulation_transactions) > 100:
                simulation_transactions = simulation_transactions[-100:]
            
            # Print to console
            print(f"🔴 LIVE DEMO: {tx_type.upper()} of ${amount} - {'FRAUD' if pred else 'LEGIT'} ({prob:.1%} risk)")
            
            # Wait between 2-5 seconds
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            print(f"Simulation error: {e}")
            time.sleep(5)
            
            

from django.core.mail import send_mail
from django.template.loader import render_to_string

@staff_member_required
def alert_simulation(request):
    """Email/SMS Alert Simulation page"""
    # Get recent high-risk transactions for display
    high_risk_transactions = BankingTransaction.objects.filter(
        fraud_prediction=True,
        fraud_probability__gt=0.8
    ).order_by('-timestamp')[:20]
    
    # Get alert logs
    alert_logs = request.session.get('alert_logs', [])
    
    context = {
        'high_risk_transactions': high_risk_transactions,
        'alert_logs': alert_logs[:20],
    }
    return render(request, 'banking/alert_simulation.html', context)


@staff_member_required
def send_test_alert(request):
    """Send a test email/SMS alert"""
    if request.method == 'POST':
        transaction_id = request.POST.get('transaction_id', '').strip()
        alert_type = request.POST.get('alert_type', 'email')
        customer_email = request.POST.get('customer_email', 'customer@securebank.com')
        customer_phone = request.POST.get('customer_phone', '+250788123456')
        
        transaction = None
        
        # Only try to get transaction if transaction_id is provided and not empty
        if transaction_id and transaction_id.isdigit():
            try:
                transaction = BankingTransaction.objects.get(id=int(transaction_id))
            except BankingTransaction.DoesNotExist:
                pass
        
        # Prepare alert data
        if transaction:
            alert_data = {
                'transaction_id': str(transaction.transaction_id)[:8],
                'amount': float(transaction.amount),
                'probability': float(transaction.fraud_probability) if transaction.fraud_probability else 0.5,
                'timestamp': transaction.timestamp,
                'customer_name': request.user.username,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
            }
        else:
            # Create simulated transaction data for test
            alert_data = {
                'transaction_id': 'TEST' + str(int(time.time()))[-6:],
                'amount': 50000.00,
                'probability': 0.95,
                'timestamp': timezone.now(),
                'customer_name': request.user.username,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
            }
        
        # Send email alert
        if alert_type == 'email' or alert_type == 'both':
            send_alert_email(alert_data)
        
        # Simulate SMS alert
        if alert_type == 'sms' or alert_type == 'both':
            simulate_sms_alert(alert_data)
        
        # Log the alert
        alert_log = {
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': alert_type,
            'transaction_id': alert_data['transaction_id'],
            'amount': alert_data['amount'],
            'risk': f"{alert_data['probability']*100:.1f}%",
            'recipient': customer_email if alert_type == 'email' else customer_phone,
            'status': 'Sent'
        }
        
        # Store in session
        alert_logs = request.session.get('alert_logs', [])
        alert_logs.insert(0, alert_log)
        request.session['alert_logs'] = alert_logs[:50]
        
        messages.success(request, f'Alert sent successfully via {alert_type.upper()}!')
        return redirect('alert_simulation')
    
    return redirect('alert_simulation')

def send_alert_email(alert_data):
    """Send email alert for high-risk transaction"""
    from django.conf import settings
    from django.core.mail import send_mail
    
    subject = f'🚨 FRAUD ALERT: Suspicious Transaction Detected'
    
    message = f"""
    SECUREBANK FRAUD ALERT SYSTEM
    ================================
    
    Dear {alert_data['customer_name']},
    
    A potentially fraudulent transaction has been detected on your account.
    
    Transaction Details:
    --------------------
    Transaction ID: {alert_data['transaction_id']}
    Amount: ${alert_data['amount']:,.2f}
    Risk Score: {alert_data['probability']*100:.1f}%
    Time: {alert_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
    
    Risk Level: HIGH
    
    Action Required:
    ----------------
    If you recognize this transaction, please login to your account to approve it.
    If you do NOT recognize this transaction, please contact our fraud department immediately.
    
    Contact Fraud Department:
    Phone: +250 788 123 456
    Email: fraud@securebank.com
    
    Stay safe,
    SecureBank Fraud Detection Team
    """
    
    # Send email (prints to console in development)
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [alert_data['customer_email']],
        fail_silently=False,
    )
    
    print(f"\n📧 EMAIL ALERT SENT TO: {alert_data['customer_email']}")
    print(f"   Subject: {subject}")
    print(f"   Transaction: {alert_data['transaction_id']} - ${alert_data['amount']:,.2f}")
    print("="*60)

def simulate_sms_alert(alert_data):
    """Simulate SMS alert for high-risk transaction"""
    sms_message = f"""
    🚨 SECUREBANK FRAUD ALERT
    Transaction: ${alert_data['amount']:,.2f}
    Risk: {alert_data['probability']*100:.1f}%
    Reply YES if this was you, or NO to block.
    """
    
    print(f"\n📱 SMS ALERT SIMULATED TO: {alert_data['customer_phone']}")
    print(f"   Message: {sms_message.strip()}")
    print("="*60)


@staff_member_required
def clear_alert_logs(request):
    """Clear alert simulation logs"""
    if request.method == 'POST':
        request.session['alert_logs'] = []
        messages.success(request, 'Alert logs cleared!')
    return redirect('alert_simulation')


@staff_member_required
def trigger_alert_for_transaction(request, transaction_id):
    """Trigger alert for a specific existing transaction"""
    transaction = get_object_or_404(BankingTransaction, id=transaction_id)
    
    if request.method == 'POST':
        alert_type = request.POST.get('alert_type', 'email')
        
        alert_data = {
            'transaction_id': str(transaction.transaction_id)[:8],
            'amount': float(transaction.amount),
            'probability': float(transaction.fraud_probability) if transaction.fraud_probability else 0.5,
            'timestamp': transaction.timestamp,
            'customer_name': transaction.from_account.customer.user.username if transaction.from_account else 'Customer',
            'customer_email': 'customer@securebank.com',
            'customer_phone': '+250788123456',
        }
        
        if alert_type == 'email' or alert_type == 'both':
            send_alert_email(alert_data)
        
        if alert_type == 'sms' or alert_type == 'both':
            simulate_sms_alert(alert_data)
        
        alert_log = {
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': alert_type,
            'transaction_id': alert_data['transaction_id'],
            'amount': alert_data['amount'],
            'risk': f"{alert_data['probability']*100:.1f}%",
            'recipient': alert_data['customer_email'] if alert_type == 'email' else alert_data['customer_phone'],
            'status': 'Sent'
        }
        
        alert_logs = request.session.get('alert_logs', [])
        alert_logs.insert(0, alert_log)
        request.session['alert_logs'] = alert_logs[:50]
        
        messages.success(request, f'Alert triggered for transaction {alert_data["transaction_id"]}!')
    
    return redirect('alert_simulation')


# Add these imports at the top
 

# Add network event types
NETWORK_EVENT_TYPES = [
    'DDoS Attempt', 'Port Scan', 'Malware Detected', 
    'Unusual Outbound Traffic', 'Failed Login Attempt', 
    'Brute Force Attack', 'SQL Injection Attempt'
]

SEVERITY_LEVELS = {
    'DDoS Attempt': 'high',
    'Port Scan': 'medium',
    'Malware Detected': 'high',
    'Unusual Outbound Traffic': 'medium',
    'Failed Login Attempt': 'low',
    'Brute Force Attack': 'high',
    'SQL Injection Attempt': 'high'
}

# Add to run_simulation() function - generate network events alongside transactions
def run_simulation():
    """Background thread to generate simulated transactions and network events"""
    global simulation_active, simulation_transactions
    
    # Sample data
    transaction_types = ['deposit', 'withdrawal', 'transfer']
    merchants = ['Amazon', 'Walmart', 'Target', 'Best Buy', 'Starbucks', 'Uber', 'Netflix', 'Spotify']
    locations = ['Kigali', 'Musanze', 'Rubavu', 'Huye', 'Nyagatare', 'International']
    amounts = [10, 25, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000, 5000, 10000, 25000, 50000, 75000, 100000]
    
    last_network_event = time.time()
    network_event_interval = 10  # Generate network event every 10 seconds
    
    while simulation_active:
        try:
            current_time = time.time()
            
            # Generate transaction (every 2-5 seconds)
            amount = random.choice(amounts)
            tx_type = random.choice(transaction_types)
            
            pred, prob = predict_fraud_combined(float(amount))
            
            transaction = {
                'id': int(current_time * 1000),
                'amount': float(amount),
                'type': tx_type,
                'merchant': random.choice(merchants),
                'location': random.choice(locations),
                'timestamp': current_time,
                'prediction': pred,
                'probability': prob,
                'risk_level': 'High' if prob > 0.8 else 'Medium' if prob > 0.5 else 'Low'
            }
            
            simulation_transactions.append(transaction)
            
            if len(simulation_transactions) > 100:
                simulation_transactions = simulation_transactions[-100:]
            
            print(f"🔴 LIVE DEMO: {tx_type.upper()} of ${amount} - {'FRAUD' if pred else 'LEGIT'} ({prob:.1%} risk)")
            
            # Generate network event every 10 seconds
            if current_time - last_network_event >= network_event_interval:
                generate_network_event()
                last_network_event = current_time
            
            time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            print(f"Simulation error: {e}")
            time.sleep(5)


def generate_network_event():
    """Generate a simulated network security event"""
    event_type = random.choice(NETWORK_EVENT_TYPES)
    severity = SEVERITY_LEVELS.get(event_type, 'medium')
    
    # Generate realistic random IP address
    source_ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"
    
    # Generate realistic descriptions
    descriptions = {
        'DDoS Attempt': f"Distributed denial of service attack detected from {random.randint(10, 1000)} sources",
        'Port Scan': f"Port scanning activity detected on ports {random.randint(1, 100)}-{random.randint(101, 1000)}",
        'Malware Detected': f"Malware signature matched: Trojan.{random.choice(['Generic', 'Banker', 'Agent', 'Downloader'])}",
        'Unusual Outbound Traffic': f"Data exfiltration attempt: {random.randint(10, 500)}MB to unknown destination",
        'Failed Login Attempt': f"Multiple failed login attempts from {source_ip}",
        'Brute Force Attack': f"Brute force attack detected on SSH/RDP services",
        'SQL Injection Attempt': f"SQL injection attempt detected in web traffic"
    }
    
    description = descriptions.get(event_type, f"Suspicious network activity detected")
    
    # Save to database
    try:
        NetworkEvent.objects.create(
            event_type=event_type,
            source_ip=source_ip,
            description=description,
            severity=severity,
            timestamp=timezone.now()
        )
        print(f"🛡️ NETWORK EVENT: {event_type} (Severity: {severity.upper()}) from {source_ip}")
    except Exception as e:
        print(f"Network event error: {e}")
        
        
@staff_member_required
def get_network_events_ajax(request):
    """Get recent network events for AJAX polling"""
    events = NetworkEvent.objects.all().order_by('-timestamp')[:50]
    
    events_data = []
    for event in events:
        events_data.append({
            'timestamp': event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': event.event_type,
            'source_ip': event.source_ip,
            'description': event.description,
            'severity': event.severity
        })
    
    return JsonResponse({'events': events_data})