from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Transaction(models.Model):
    """
    Demo Transaction Model for 30-feature ML model demonstration.
    This is separate from banking transactions to showcase real ML.
    """
    transaction_id = models.CharField(max_length=100, unique=True)
    account_number = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    merchant = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    device_id = models.CharField(max_length=100, blank=True)
    is_fraud = models.BooleanField(default=False)           # Ground truth
    prediction = models.BooleanField(null=True, blank=True)  # ML model output
    probability = models.FloatField(null=True, blank=True)   # ML probability
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            # Index for sorting by timestamp
            models.Index(fields=['-timestamp'], name='idx_demo_timestamp'),
            
            # Index for filtering by ML prediction
            models.Index(fields=['prediction'], name='idx_demo_prediction'),
            
            # Index for account-based lookups
            models.Index(fields=['account_number'], name='idx_demo_account'),
            
            # Composite index for dashboard queries
            models.Index(fields=['-timestamp', 'prediction'], name='idx_demo_timestamp_pred'),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.amount}"