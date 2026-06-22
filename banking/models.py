from django.db import models
from accounts.models import Account
import uuid


class BankingTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
    ]
    
    REVIEW_STATUS = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('blocked', 'Blocked'),
        ('investigating', 'Under Investigation'),
    ]
    
    # Core fields
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    from_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='outgoing_transactions', null=True, blank=True)
    to_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='incoming_transactions', null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200, blank=True)

    # Fraud detection fields
    fraud_prediction = models.BooleanField(null=True, blank=True)
    fraud_probability = models.FloatField(null=True, blank=True)
    
    # ============================================================
    # FEATURE ENGINEERING FIELDS (Supervisor Requirements)
    # ============================================================
    
    # Time-Based Features
    transaction_hour = models.IntegerField(null=True, blank=True)
    transaction_day_of_week = models.IntegerField(null=True, blank=True)
    days_since_last_transaction = models.FloatField(null=True, blank=True)
    
    # Amount-Based Features
    amount_ratio_to_avg = models.FloatField(null=True, blank=True)
    amount_deviation_std = models.FloatField(null=True, blank=True)
    
    # Cumulative Features (last 24 hours)
    transaction_count_last_24h = models.IntegerField(null=True, blank=True)
    transaction_value_last_24h = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Recency Features
    hours_since_last_login = models.FloatField(null=True, blank=True)
    days_since_last_password_change = models.FloatField(null=True, blank=True)
    days_since_profile_update = models.FloatField(null=True, blank=True)
    
    # Review Queue Fields
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='pending')
    reviewed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    block_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['-timestamp'], name='idx_banking_timestamp'),
            models.Index(fields=['fraud_prediction'], name='idx_banking_fraud_pred'),
            models.Index(fields=['transaction_type'], name='idx_banking_tx_type'),
            models.Index(fields=['from_account', '-timestamp'], name='idx_banking_from_account'),
            models.Index(fields=['to_account', '-timestamp'], name='idx_banking_to_account'),
            models.Index(fields=['transaction_hour'], name='idx_banking_hour'),
            models.Index(fields=['amount_ratio_to_avg'], name='idx_banking_ratio'),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"


class ComplianceFlag(models.Model):
    """
    Compliance Flag Model for AML (Anti-Money Laundering) alerts.
    Flags suspicious transactions and customer activities.
    """
    FLAG_REASONS = [
        ('large_tx', 'Large Transaction'),
        ('rapid_tx', 'Rapid Transactions'),
        ('cross_border', 'Cross-Border Transfer'),
        ('high_risk_country', 'High-Risk Country'),
        ('unusual_pattern', 'Unusual Pattern'),
        ('kyc_pending', 'KYC Pending'),
    ]
    
    transaction = models.ForeignKey('BankingTransaction', on_delete=models.CASCADE, related_name='compliance_flags', null=True, blank=True)
    customer = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE, related_name='compliance_flags')
    reason = models.CharField(max_length=50, choices=FLAG_REASONS)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['resolved', '-created_at'], name='idx_compliance_unresolved'),
            models.Index(fields=['customer'], name='idx_compliance_customer'),
            models.Index(fields=['reason'], name='idx_compliance_reason'),
            models.Index(fields=['-created_at'], name='idx_compliance_created'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Flag for {self.customer.user.username} - {self.reason}"