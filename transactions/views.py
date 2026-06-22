from django.shortcuts import render, redirect
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta
import json
from .models import Transaction
from .forms import TransactionForm
from banking.models import BankingTransaction
from prediction.ml_service import predict_fraud_amount_only
from django.contrib.auth.decorators import login_required
from prediction.models import FraudAlert
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from accounts.decorators import staff_required


@staff_required
@login_required
def dashboard(request):
    """
    Staff dashboard showing combined demo and banking transactions.
    """
    # Get demo and banking transactions
    demo_transactions = Transaction.objects.all()
    banking_transactions = BankingTransaction.objects.all()
    
    # Combine and sort
    all_transactions = list(demo_transactions) + list(banking_transactions)
    all_transactions.sort(key=lambda x: x.timestamp, reverse=True)
    
    # KPIs
    total_count = demo_transactions.count() + banking_transactions.count()
    fraud_count = demo_transactions.filter(prediction=True).count() + banking_transactions.filter(fraud_prediction=True).count()
    fraud_rate = (fraud_count / total_count * 100) if total_count > 0 else 0
    
    demo_avg = demo_transactions.aggregate(Avg('amount'))['amount__avg'] or 0
    banking_avg = banking_transactions.aggregate(Avg('amount'))['amount__avg'] or 0
    avg_amount = (demo_avg + banking_avg) / 2 if (demo_avg + banking_avg) > 0 else 0
    
    # Daily transactions
    last_week = timezone.now() - timedelta(days=7)
    
    demo_daily = demo_transactions.filter(timestamp__gte=last_week) \
        .annotate(date=TruncDate('timestamp')) \
        .values('date') \
        .annotate(total=Count('id'), fraud=Count('id', filter=Q(prediction=True))) \
        .order_by('date')
    
    banking_daily = banking_transactions.filter(timestamp__gte=last_week) \
        .annotate(date=TruncDate('timestamp')) \
        .values('date') \
        .annotate(total=Count('id'), fraud=Count('id', filter=Q(fraud_prediction=True))) \
        .order_by('date')
    
    # Merge daily data
    daily_dates = set()
    for d in demo_daily:
        daily_dates.add(d['date'].strftime('%Y-%m-%d'))
    for d in banking_daily:
        daily_dates.add(d['date'].strftime('%Y-%m-%d'))
    
    daily_labels = sorted(list(daily_dates))
    daily_totals = []
    daily_frauds = []
    
    for date_str in daily_labels:
        total = 0
        fraud = 0
        for d in demo_daily:
            if d['date'].strftime('%Y-%m-%d') == date_str:
                total += d['total']
                fraud += d['fraud']
        for d in banking_daily:
            if d['date'].strftime('%Y-%m-%d') == date_str:
                total += d['total']
                fraud += d['fraud']
        daily_totals.append(total)
        daily_frauds.append(fraud)
    
    # Hourly transactions
    last_24h = timezone.now() - timedelta(hours=24)
    
    demo_hourly = demo_transactions.filter(timestamp__gte=last_24h) \
        .annotate(hour=TruncHour('timestamp')) \
        .values('hour') \
        .annotate(count=Count('id')) \
        .order_by('hour')
    
    banking_hourly = banking_transactions.filter(timestamp__gte=last_24h) \
        .annotate(hour=TruncHour('timestamp')) \
        .values('hour') \
        .annotate(count=Count('id')) \
        .order_by('hour')
    
    hourly_dict = {}
    for h in demo_hourly:
        hour_key = h['hour'].strftime('%H:00')
        hourly_dict[hour_key] = hourly_dict.get(hour_key, 0) + h['count']
    for h in banking_hourly:
        hour_key = h['hour'].strftime('%H:00')
        hourly_dict[hour_key] = hourly_dict.get(hour_key, 0) + h['count']
    
    hourly_labels = sorted(hourly_dict.keys())
    hourly_counts = [hourly_dict[h] for h in hourly_labels]
    
    # Recent transactions formatted for template
    recent = all_transactions[:100]
    formatted_transactions = []
    for t in recent:
        if hasattr(t, 'prediction'):
            formatted_transactions.append({
                'transaction_id': t.transaction_id,
                'amount': t.amount,
                'timestamp': t.timestamp,
                'prediction': t.prediction,
                'probability': t.probability,
            })
        else:
            formatted_transactions.append({
                'transaction_id': str(t.transaction_id)[:8],
                'amount': t.amount,
                'timestamp': t.timestamp,
                'prediction': t.fraud_prediction,
                'probability': t.fraud_probability,
            })
    
    context = {
        'total_count': total_count,
        'fraud_count': fraud_count,
        'fraud_rate': round(fraud_rate, 2),
        'avg_amount': round(avg_amount, 2),
        'daily_labels': json.dumps(daily_labels),
        'daily_totals': json.dumps(daily_totals),
        'daily_frauds': json.dumps(daily_frauds),
        'hourly_labels': json.dumps(hourly_labels),
        'hourly_counts': json.dumps(hourly_counts),
        'transactions': formatted_transactions,
    }
    return render(request, 'transactions/dashboard.html', context)


@login_required
def transaction_create(request):
    """
    Create a demo transaction with ML fraud detection and WebSocket broadcast.
    """
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            amount = float(transaction.amount)
            pred, prob = predict_fraud_amount_only(amount)
            transaction.prediction = pred
            transaction.probability = prob
            transaction.save()

            if prob > 0.8:
                FraudAlert.objects.get_or_create(demo_transaction=transaction) # WebSocket broadcast
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    'transactions_group',
                    {
                        'type': 'transaction_update',
                        'transaction': {
                            'id': transaction.id,
                            'transaction_id': transaction.transaction_id,
                            'amount': str(transaction.amount),
                            'timestamp': transaction.timestamp.isoformat(),
                            'prediction': transaction.prediction,
                            'probability': transaction.probability,
                        }
                    }
                )
            except Exception as e:
                print(f"WebSocket error: {e}")

            return redirect('dashboard')
    else:
        form = TransactionForm()
    return render(request, 'transactions/transaction_form.html', {'form': form})