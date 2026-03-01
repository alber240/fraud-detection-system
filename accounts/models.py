from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import random
import string

def generate_account_number():
    return ''.join(random.choices(string.digits, k=12))

class Customer(models.Model):
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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    phone = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    date_of_birth = models.DateField()
    id_number = models.CharField(max_length=50, unique=True)  # National ID
    kyc_status = models.CharField(max_length=10, choices=KYC_STATUS_CHOICES, default='pending')
    risk_tier = models.CharField(max_length=10, choices=RISK_TIER_CHOICES, default='low')
    aml_flagged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    image_approved = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.user.username} - {self.kyc_status}"

class Account(models.Model):
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

    def __str__(self):
        return f"{self.account_number} ({self.account_type})"