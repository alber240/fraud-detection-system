from django.shortcuts import render
from .models import Transaction

def dashboard(request):
    transactions = Transaction.objects.all().order_by('-timestamp')[:100]  # latest 100
    fraud_count = Transaction.objects.filter(prediction=True).count()
    total_count = Transaction.objects.count()
    context = {
        'transactions': transactions,
        'fraud_count': fraud_count,
        'total_count': total_count,
    }
    return render(request, 'transactions/dashboard.html', context)