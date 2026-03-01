from django.db import models
from transactions.models import Transaction
from django.conf import settings
class FraudAlert(models.Model):
    transaction = models.OneToOneField('banking.BankingTransaction', on_delete=models.CASCADE, related_name='alert')
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Alert for {self.transaction.transaction_id}"
    
class NetworkEvent(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    event_type = models.CharField(max_length=50)  # e.g., 'Failed Login', 'Port Scan', 'DDoS Attempt'
    source_ip = models.GenericIPAddressField()
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='low')

    def __str__(self):
        return f"{self.event_type} from {self.source_ip} at {self.timestamp}"