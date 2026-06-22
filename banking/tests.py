from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from accounts.models import Customer, Account
from banking.models import BankingTransaction, ComplianceFlag
from prediction.models import FraudAlert


class BankingTestCase(TestCase):
    """Base test case with common setup for banking tests."""
    
    def setUp(self):
        """Set up test data before each test."""
        # Create a test client that doesn't check CSRF
        self.client = Client(enforce_csrf_checks=False)
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Create test customer
        self.customer = Customer.objects.create(
            user=self.user,
            phone='0788123456',
            address='123 Test Street, Kigali',
            date_of_birth='1990-01-01',
            id_number='1234567890123456',
            kyc_status='verified'
        )
        
        # Create test checking account
        self.checking_account = Account.objects.create(
            customer=self.customer,
            account_type='checking',
            balance=Decimal('1000.00')
        )
        
        # Create test savings account
        self.savings_account = Account.objects.create(
            customer=self.customer,
            account_type='savings',
            balance=Decimal('500.00')
        )
        
        # Login the client
        self.client.login(username='testuser', password='testpass123')


class FraudDetectionTest(BankingTestCase):
    """Test fraud detection functionality."""
    
    def test_large_transaction_flagged(self):
        """Test that large transaction (>$25,000) is flagged as fraud."""
        # Use a POST request with follow=True to see the actual response
        response = self.client.post('/banking/deposit/', {
            'account': self.checking_account.id,
            'amount': '30000.00',
            'description': 'Large deposit'
        }, follow=True)
        
        # Should be successful (200 OK after redirect)
        self.assertEqual(response.status_code, 200)
        
        # Find the transaction
        transaction = BankingTransaction.objects.filter(
            to_account=self.checking_account,
            amount=Decimal('30000.00')
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertTrue(transaction.fraud_prediction)
        self.assertGreaterEqual(transaction.fraud_probability, 0.8)
    
    def test_small_transaction_not_flagged(self):
        """Test that small transaction (<$500) is not flagged as fraud."""
        response = self.client.post('/banking/deposit/', {
            'account': self.checking_account.id,
            'amount': '50.00',
            'description': 'Small deposit'
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        
        transaction = BankingTransaction.objects.filter(
            to_account=self.checking_account,
            amount=Decimal('50.00')
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertFalse(transaction.fraud_prediction)
        self.assertLessEqual(transaction.fraud_probability, 0.15)