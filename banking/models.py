from django.db import models
from accounts.models import Account
import uuid

class BankingTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
    ]
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    from_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='outgoing_transactions', null=True, blank=True)
    to_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='incoming_transactions', null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200, blank=True)

    # Fraud detection fields
    fraud_prediction = models.BooleanField(null=True, blank=True)
    fraud_probability = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"