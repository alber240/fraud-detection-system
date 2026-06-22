from django.db import models
from django.conf import settings


class FraudAlert(models.Model):
    """Fraud Alert Model - Can link to both BankingTransaction and Transaction"""
    
    banking_transaction = models.ForeignKey(
        'banking.BankingTransaction', 
        on_delete=models.CASCADE, 
        related_name='alerts',
        null=True, 
        blank=True
    )
    demo_transaction = models.ForeignKey(
        'transactions.Transaction', 
        on_delete=models.CASCADE, 
        related_name='alerts',
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        'auth.User', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    def __str__(self):
        if self.banking_transaction:
            return f"Alert for {self.banking_transaction.transaction_id}"
        elif self.demo_transaction:
            return f"Alert for {self.demo_transaction.transaction_id}"
        return f"Alert {self.id}"


class NetworkEvent(models.Model):
    """Network Security Events for monitoring"""
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    event_type = models.CharField(max_length=50)
    source_ip = models.GenericIPAddressField()
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='low')

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp'], name='idx_network_timestamp'),
            models.Index(fields=['severity'], name='idx_network_severity'),
        ]

    def __str__(self):
        return f"{self.event_type} from {self.source_ip} at {self.timestamp}"