from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Transaction(models.Model):
    transaction_id = models.CharField(max_length=100, unique=True)
    account_number = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    merchant = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    device_id = models.CharField(max_length=100, blank=True)
    is_fraud = models.BooleanField(default=False)          # ground truth
    prediction = models.BooleanField(null=True, blank=True) # model output
    probability = models.FloatField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.amount}"