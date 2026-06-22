from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import random
import string


def generate_account_number():
    """Generate a random 12-digit account number."""
    return ''.join(random.choices(string.digits, k=12))


class Customer(models.Model):
    """
    Customer Model - Extends Django User with KYC and compliance fields.
    """
    KYC_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    RISK_TIER_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    # Core fields
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    phone = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    date_of_birth = models.DateField()
    id_number = models.CharField(max_length=50, unique=True)
    
    # KYC/Compliance fields
    kyc_status = models.CharField(max_length=10, choices=KYC_STATUS_CHOICES, default='pending')
    risk_tier = models.CharField(max_length=10, choices=RISK_TIER_CHOICES, default='low')
    aml_flagged = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Profile image
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    image_approved = models.BooleanField(default=False)
    
    # KYC Documents
    id_proof = models.ImageField(upload_to='kyc_docs/', null=True, blank=True)
    address_proof = models.ImageField(upload_to='kyc_docs/', null=True, blank=True)
    
    # Approval workflow
    kyc_submitted_at = models.DateTimeField(null=True, blank=True)
    kyc_reviewed_at = models.DateTimeField(null=True, blank=True)
    kyc_reviewed_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_customers')
    kyc_rejection_reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            # Index for KYC status filtering (admin/approval dashboard)
            models.Index(fields=['kyc_status'], name='idx_customer_kyc'),
            
            # Unique fields already have indexes, but explicit for clarity
            models.Index(fields=['phone'], name='idx_customer_phone'),
            models.Index(fields=['id_number'], name='idx_customer_id'),
            
            # Index for risk tier analysis
            models.Index(fields=['risk_tier'], name='idx_customer_risk'),
            
            # Index for AML flagged customers
            models.Index(fields=['aml_flagged'], name='idx_customer_aml'),
            
            # Composite index for dashboard queries
            models.Index(fields=['kyc_status', 'risk_tier'], name='idx_customer_kyc_risk'),
            
            # Index for created_at date range queries
            models.Index(fields=['-created_at'], name='idx_customer_created'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.kyc_status}"


class Account(models.Model):
    """
    Bank Account Model - Linked to Customer.
    Supports checking and savings accounts.
    """
    ACCOUNT_TYPES = [
        ('checking', 'Checking'),
        ('savings', 'Savings'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=20, unique=True, default=generate_account_number)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default='checking')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # Index for account number lookups (most common query)
            models.Index(fields=['account_number'], name='idx_account_number'),
            
            # Index for customer account list queries
            models.Index(fields=['customer', 'account_type'], name='idx_account_customer_type'),
            
            # Index for active accounts filter
            models.Index(fields=['is_active'], name='idx_account_active'),
            
            # Composite index for customer dashboard queries
            models.Index(fields=['customer', '-opened_at'], name='idx_account_customer_opened'),
        ]
        ordering = ['customer', 'account_type']

    def __str__(self):
        return f"{self.account_number} ({self.account_type})"
    

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('checking', 'Checking'),
        ('savings', 'Savings'),
    ]
    CURRENCY_CHOICES = [
        ('RWF', 'Rwandan Franc'),
        ('USD', 'US Dollar'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=20, unique=True, default=generate_account_number)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default='checking')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='RWF')  # NEW
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account_number} ({self.currency}) - {self.balance} {self.currency}"