"""
Unit Tests for Transactions App
Tests demo transaction creation and ML model integration.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from transactions.models import Transaction
from prediction.models import FraudAlert



class DemoTransactionTest(TestCase):
    """Test demo transaction functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_transaction_form_loads(self):
        """Test that transaction creation form loads correctly."""
        response = self.client.get('/api/transactions/new/')
        self.assertEqual(response.status_code, 200)
    
    def test_create_legitimate_transaction(self):
        """Test creating a legitimate transaction (small amount)."""
        response = self.client.post('/api/transactions/new/', {
            'transaction_id': 'TXN001',
            'account_number': 'ACC123456',
            'amount': '50.00',
            'merchant': 'Supermarket',
            'location': 'Kigali',
            'device_id': 'DEV001'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        transaction = Transaction.objects.filter(transaction_id='TXN001').first()
        self.assertIsNotNone(transaction)
        self.assertFalse(transaction.prediction)  # Should be LEGIT
        self.assertLessEqual(transaction.probability, 0.15)
    
    def test_create_fraudulent_transaction(self):
        """Test creating a fraudulent transaction (large amount)."""
        response = self.client.post('/api/transactions/new/', {
            'transaction_id': 'TXN002',
            'account_number': 'ACC123456',
            'amount': '50000.00',
            'merchant': 'Electronics Store',
            'location': 'Unknown',
            'device_id': 'DEV002'
        })
        
        self.assertEqual(response.status_code, 302)
        
        transaction = Transaction.objects.filter(transaction_id='TXN002').first()
        self.assertIsNotNone(transaction)
        self.assertTrue(transaction.prediction)  # Should be FRAUD
        self.assertGreaterEqual(transaction.probability, 0.8)
    
    def test_create_transaction_with_alert(self):
        """Test that high-risk transactions create alerts."""
        response = self.client.post('/api/transactions/new/', {
            'transaction_id': 'TXN003',
            'account_number': 'ACC123456',
            'amount': '50000.00',
            'merchant': 'Luxury Store',
            'location': 'International',
            'device_id': 'DEV003'
        })
        
        transaction = Transaction.objects.filter(transaction_id='TXN003').first()
        self.assertIsNotNone(transaction)
        
        # Check if alert was created
        alert_exists = FraudAlert.objects.filter(demo_transaction=transaction).exists()
        self.assertTrue(alert_exists)
    
    def test_transaction_requires_login(self):
        """Test that transaction creation requires authentication."""
        self.client.logout()
        response = self.client.get('/api/transactions/new/')
        self.assertEqual(response.status_code, 302)  # Redirect to login