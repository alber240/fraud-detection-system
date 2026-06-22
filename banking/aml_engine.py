from .models import BankingTransaction, ComplianceFlag
from accounts.models import Customer
from datetime import timedelta
from django.utils import timezone

def check_aml_rules(transaction):
    """
    Check a transaction against AML rules and create flags if needed.
    """
    flags = []

    # Determine the customer
    if transaction.transaction_type == 'deposit':
        customer = transaction.to_account.customer
    else:
        customer = transaction.from_account.customer

    # Rule 1: Large transaction (over $10,000)
    if transaction.amount > 10000:
        flags.append({
            'customer': customer,
            'transaction': transaction,
            'reason': 'large_tx',
            'description': f"Large transaction of ${transaction.amount}."
        })

    # Rule 2: Rapid transactions – more than 3 in 1 hour
    one_hour_ago = timezone.now() - timedelta(hours=1)
    recent_txs = BankingTransaction.objects.filter(
        from_account__customer=customer,
        timestamp__gte=one_hour_ago
    ).count()
    if recent_txs >= 3:
        flags.append({
            'customer': customer,
            'transaction': transaction,
            'reason': 'rapid_tx',
            'description': f"{recent_txs} transactions in the last hour."
        })

    # Rule 3: Cross-border transfer (simulate by location field – if location differs from customer's address country)
    # For simplicity, we'll skip or implement later.

    # Create flags in database
    for flag_data in flags:
        ComplianceFlag.objects.create(**flag_data)

    return flags