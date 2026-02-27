from django.db import models
from django.contrib.auth import get_user_model
from prediction.ml_service import predict_fraud   # <-- import the function

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

    def save(self, *args, **kwargs):
        # Only predict if this is a new transaction (no primary key yet)
        # and prediction is not already set
        if not self.pk and self.prediction is None:
            # Build the feature vector from transaction fields
            # IMPORTANT: The order and values must match the model's training features.
            # For now, we'll use dummy values; you'll need to map real fields.
            # In a real system, you'd engineer features like transaction amount,
            # time of day, location risk score, etc.
            features = [
                float(self.amount),               # replace with actual feature engineering
                # ... you need 30 features total ...
            ]
            # If you don't have 30 features, you can't use the creditcard model directly.
            # For this project, we'll assume you have the same 30 features.
            # One approach: create a new model trained on your available fields.
            # For now, let's just use a placeholder and skip prediction.
            # Better: generate synthetic features or use a simpler model.
            # But for demonstration, we'll comment out prediction.
            # prediction, probability = predict_fraud(features)
            # self.prediction = prediction
            # self.probability = probability
            pass   # remove this when you have real features
        super().save(*args, **kwargs)