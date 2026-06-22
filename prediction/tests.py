"""
Unit Tests for Prediction App
Tests ML model loading, fraud prediction, and alert generation.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from accounts.models import Customer, Account
from banking.models import BankingTransaction
from prediction.models import FraudAlert
from prediction.ml_service import predict_fraud_amount_only, predict_fraud_30, get_model_info


class MLModelTest(TestCase):
    """Test machine learning model functionality."""
    
    def test_amount_only_prediction(self):
        """Test that amount-only prediction returns valid values."""
        # Small amount should be LEGIT
        pred, prob = predict_fraud_amount_only(100)
        self.assertEqual(pred, 0)  # LEGIT
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 0.3)
        
        # Large amount should be FRAUD
        pred, prob = predict_fraud_amount_only(50000)
        self.assertEqual(pred, 1)  # FRAUD
        self.assertGreaterEqual(prob, 0.8)
        
        # Medium amount should be LEGIT but monitored
        pred, prob = predict_fraud_amount_only(15000)
        self.assertEqual(pred, 0)  # LEGIT
        self.assertGreaterEqual(prob, 0.5)
    
    def test_threshold_boundaries(self):
        """Test that thresholds work correctly at boundary values."""
        # Test $10,000 threshold
        pred, prob = predict_fraud_amount_only(10000)
        self.assertEqual(pred, 0)
        self.assertEqual(prob, 0.70)
        
        # Test $25,000 threshold
        pred, prob = predict_fraud_amount_only(25000)
        self.assertEqual(pred, 1)
        self.assertEqual(prob, 0.85)
        
        # Test $50,000 threshold
        pred, prob = predict_fraud_amount_only(50000)
        self.assertEqual(pred, 1)
        self.assertEqual(prob, 0.95)
    
    def test_model_info_returns_valid_data(self):
        """Test that get_model_info returns expected structure."""
        info = get_model_info()
        
        self.assertIn('banking_detection', info)
        self.assertIn('transaction_demo_ml_model', info)
        self.assertIn('thresholds', info['banking_detection'])
        self.assertIn('accuracy', info['transaction_demo_ml_model'])


class FraudAlertTest(TestCase):
    """Test fraud alert functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            phone='0788000000',
            address='Test Address',
            date_of_birth='1990-01-01',
            id_number='1234567890'
        )
        self.account = Account.objects.create(
            customer=self.customer,
            account_type='checking',
            balance=Decimal('1000.00')
        )
    
    def test_fraud_alert_creation(self):
        """Test that a fraud alert can be created."""
        transaction = BankingTransaction.objects.create(
            to_account=self.account,
            transaction_type='deposit',
            amount=Decimal('50000.00')
        )
        
        alert = FraudAlert.objects.create(banking_transaction=transaction)
        
        self.assertIsNotNone(alert)
        self.assertFalse(alert.acknowledged)
        self.assertIsNone(alert.acknowledged_by)
    
    def test_fraud_alert_acknowledgment(self):
        """Test that a fraud alert can be acknowledged."""
        transaction = BankingTransaction.objects.create(
            to_account=self.account,
            transaction_type='deposit',
            amount=Decimal('50000.00')
        )
        
        alert = FraudAlert.objects.create(banking_transaction=transaction)
        
        # Acknowledge the alert
        staff_user = User.objects.create_user(
            username='staff',
            password='staffpass',
            is_staff=True
        )
        alert.acknowledged = True
        alert.acknowledged_by = staff_user
        alert.acknowledged_at = timezone.now()
        alert.resolution_notes = "Reviewed - legitimate large transaction"
        alert.save()
        
        alert.refresh_from_db()
        self.assertTrue(alert.acknowledged)
        self.assertEqual(alert.acknowledged_by, staff_user)
        self.assertEqual(alert.resolution_notes, "Reviewed - legitimate large transaction")