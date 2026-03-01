from django.shortcuts import render, redirect
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta
import json
from .models import Transaction
from .forms import TransactionForm
from prediction.ml_service import predict_fraud_simple
from django.contrib.auth.decorators import login_required
from prediction.models import FraudAlert
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from accounts.decorators import staff_required

@staff_required
@login_required
def dashboard(request):
    # All transactions
    transactions = Transaction.objects.all()

    # --- KPIs ---
    total_count = transactions.count()
    fraud_count = transactions.filter(prediction=True).count()
    fraud_rate = (fraud_count / total_count * 100) if total_count > 0 else 0
    avg_amount = transactions.aggregate(Avg('amount'))['amount__avg'] or 0

    # --- Daily transactions (last 7 days) ---
    last_week = timezone.now() - timedelta(days=7)
    daily = transactions.filter(timestamp__gte=last_week) \
        .annotate(date=TruncDate('timestamp')) \
        .values('date') \
        .annotate(
            total=Count('id'),
            fraud=Count('id', filter=Q(prediction=True))
        ) \
        .order_by('date')

    daily_labels = [d['date'].strftime('%Y-%m-%d') for d in daily]
    daily_totals = [d['total'] for d in daily]
    daily_frauds = [d['fraud'] for d in daily]

    # --- Hourly transactions (last 24 hours) ---
    last_24h = timezone.now() - timedelta(hours=24)
    hourly = transactions.filter(timestamp__gte=last_24h) \
        .annotate(hour=TruncHour('timestamp')) \
        .values('hour') \
        .annotate(count=Count('id')) \
        .order_by('hour')

    hourly_labels = [h['hour'].strftime('%H:00') for h in hourly]
    hourly_counts = [h['count'] for h in hourly]

    # --- Recent 100 transactions for table ---
    recent = transactions.order_by('-timestamp')[:100]

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
        'transactions': recent,
    }
    return render(request, 'transactions/dashboard.html', context)


@login_required
def transaction_create(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            # Call simple model (using amount only)
            amount = float(transaction.amount)
            pred, prob = predict_fraud_simple(amount)
            transaction.prediction = pred
            transaction.probability = prob
            transaction.save()

            # Create alert only if probability is high (e.g., > 0.8)
            if prob > 0.8:
                FraudAlert.objects.create(transaction=transaction)

            # WebSocket broadcast (if you have Channels set up)
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    'transactions',
                    {
                        'type': 'transaction_update',
                        'data': {
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
                # If Channels is not configured, fail silently (or log)
                print(f"WebSocket error: {e}")

            return redirect('dashboard')
    else:
        form = TransactionForm()
    return render(request, 'transactions/transaction_form.html', {'form': form})