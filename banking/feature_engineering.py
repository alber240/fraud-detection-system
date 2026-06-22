"""
Feature Engineering Module for Fraud Detection
Creates time-based, amount-based, cumulative, and recency features
"""

from django.utils import timezone
from django.db import models  # ADD THIS IMPORT
from datetime import timedelta
from decimal import Decimal
import numpy as np
from django.db.models import Sum, Count, Avg, StdDev, Q  # ADD Q import
from accounts.models import Customer, Account
from .models import BankingTransaction


class FeatureEngineer:
    """
    Generates features for fraud detection as required by supervisor:
    - Time-based features (hour, days since last transaction)
    - Amount-based features (ratio to average, deviation)
    - Cumulative features (24-hour count and value)
    - Recency features (last login, password change, profile update)
    """
    
    @staticmethod
    def get_transaction_hour(timestamp):
        """Extract hour of transaction (0-23)"""
        return timestamp.hour
    
    @staticmethod
    def get_transaction_day_of_week(timestamp):
        """Extract day of week (0=Monday, 6=Sunday)"""
        return timestamp.weekday()
    
    @staticmethod
    def get_days_since_last_transaction(account, current_timestamp):
        """
        Calculate days since last transaction for this account
        """
        last_transaction = BankingTransaction.objects.filter(
            models.Q(from_account=account) | models.Q(to_account=account)
        ).exclude(timestamp__gte=current_timestamp).order_by('-timestamp').first()
        
        if last_transaction:
            delta = current_timestamp - last_transaction.timestamp
            return delta.total_seconds() / (24 * 3600)  # Convert to days
        return None
    
    @staticmethod
    def get_amount_ratio_to_avg(account, current_amount, current_timestamp):
        """
        Calculate ratio of current amount to user's average transaction amount
        """
        # Get all previous transactions for this account
        previous_transactions = BankingTransaction.objects.filter(
            models.Q(from_account=account) | models.Q(to_account=account)
        ).exclude(timestamp__gte=current_timestamp)
        
        amounts = [float(t.amount) for t in previous_transactions]
        
        if amounts:
            avg_amount = np.mean(amounts)
            if avg_amount > 0:
                return float(current_amount) / avg_amount
        return None
    
    @staticmethod
    def get_amount_deviation_std(account, current_amount, current_timestamp):
        """
        Calculate how many standard deviations from user's average
        """
        previous_transactions = BankingTransaction.objects.filter(
            models.Q(from_account=account) | models.Q(to_account=account)
        ).exclude(timestamp__gte=current_timestamp)
        
        amounts = [float(t.amount) for t in previous_transactions]
        
        if len(amounts) > 1:
            avg_amount = np.mean(amounts)
            std_amount = np.std(amounts)
            if std_amount > 0:
                return (float(current_amount) - avg_amount) / std_amount
        return None
    
    @staticmethod
    def get_transaction_count_last_24h(account, current_timestamp):
        """
        Count number of transactions in last 24 hours for this account
        """
        last_24h = current_timestamp - timedelta(hours=24)
        count = BankingTransaction.objects.filter(
            models.Q(from_account=account) | models.Q(to_account=account),
            timestamp__gte=last_24h,
            timestamp__lt=current_timestamp
        ).count()
        return count
    
    @staticmethod
    def get_transaction_value_last_24h(account, current_timestamp):
        """
        Total value of transactions in last 24 hours for this account
        """
        last_24h = current_timestamp - timedelta(hours=24)
        transactions = BankingTransaction.objects.filter(
            models.Q(from_account=account) | models.Q(to_account=account),
            timestamp__gte=last_24h,
            timestamp__lt=current_timestamp
        )
        
        total = sum(float(t.amount) for t in transactions)
        return total
    
    @staticmethod
    def get_hours_since_last_login(customer, current_timestamp):
        """
        Calculate hours since customer's last login
        """
        if customer.user.last_login:
            delta = current_timestamp - customer.user.last_login
            return delta.total_seconds() / 3600  # Convert to hours
        return None
    
    @staticmethod
    def get_days_since_last_password_change(customer, current_timestamp):
        """
        Calculate days since customer's last password change
        """
        if customer.user.last_login:  # Using last_login as proxy for password change
            delta = current_timestamp - customer.user.last_login
            return delta.total_seconds() / (24 * 3600)
        return None
    
    @staticmethod
    def get_days_since_profile_update(customer, current_timestamp):
        """
        Calculate days since customer's profile was last updated
        """
        if customer.updated_at:
            delta = current_timestamp - customer.updated_at
            return delta.total_seconds() / (24 * 3600)
        return None
    
    @classmethod
    def engineer_features_for_transaction(cls, transaction):
        """
        Generate all features for a given transaction
        """
        # Determine which account is involved
        if transaction.transaction_type == 'deposit':
            account = transaction.to_account
        else:
            account = transaction.from_account
        
        if not account:
            return
        
        customer = account.customer
        current_timestamp = transaction.timestamp
        
        # Time-Based Features
        transaction.transaction_hour = cls.get_transaction_hour(current_timestamp)
        transaction.transaction_day_of_week = cls.get_transaction_day_of_week(current_timestamp)
        transaction.days_since_last_transaction = cls.get_days_since_last_transaction(
            account, current_timestamp
        )
        
        # Amount-Based Features
        transaction.amount_ratio_to_avg = cls.get_amount_ratio_to_avg(
            account, transaction.amount, current_timestamp
        )
        transaction.amount_deviation_std = cls.get_amount_deviation_std(
            account, transaction.amount, current_timestamp
        )
        
        # Cumulative Features
        transaction.transaction_count_last_24h = cls.get_transaction_count_last_24h(
            account, current_timestamp
        )
        transaction.transaction_value_last_24h = cls.get_transaction_value_last_24h(
            account, current_timestamp
        )
        
        # Recency Features
        transaction.hours_since_last_login = cls.get_hours_since_last_login(
            customer, current_timestamp
        )
        transaction.days_since_last_password_change = cls.get_days_since_last_password_change(
            customer, current_timestamp
        )
        transaction.days_since_profile_update = cls.get_days_since_profile_update(
            customer, current_timestamp
        )
        
        transaction.save()