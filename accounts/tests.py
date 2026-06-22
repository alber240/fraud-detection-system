"""
Unit Tests for Accounts App
Tests user registration, customer creation, account management, and KYC.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from accounts.models import Customer, Account


class RegistrationTest(TestCase):
    """Test user registration functionality."""
    
    def setUp(self):
        self.client = Client()
    
    def test_registration_page_loads(self):
        """Test that registration page loads correctly."""
        response = self.client.get('/accounts/register/')
        self.assertEqual(response.status_code, 200)
    
    def test_successful_registration(self):
        """Test that a user can register successfully."""
        response = self.client.post('/accounts/register/', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'phone': '0788112233',
            'address': '456 New Street, Kigali',
            'date_of_birth': '1992-06-15',
            'id_number': '9876543210987654'
        })
        
        # Should redirect after successful registration
        self.assertEqual(response.status_code, 302)
        
        # Check user was created
        user_exists = User.objects.filter(username='newuser').exists()
        self.assertTrue(user_exists)
        
        # Check customer was created
        customer_exists = Customer.objects.filter(user__username='newuser').exists()
        self.assertTrue(customer_exists)
        
        # Check account was created with initial balance
        account_exists = Account.objects.filter(customer__user__username='newuser').exists()
        self.assertTrue(account_exists)
    
    def test_registration_with_existing_username(self):
        """Test that registration fails with existing username."""
        # Create existing user
        User.objects.create_user(username='existinguser', password='pass123')
        
        response = self.client.post('/accounts/register/', {
            'username': 'existinguser',
            'email': 'new@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'phone': '0788112233',
            'address': 'Test Address',
            'date_of_birth': '1990-01-01',
            'id_number': '1111111111111111'
        })
        
        # Should return to registration page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
    
    def test_registration_with_password_mismatch(self):
        """Test that registration fails when passwords don't match."""
        response = self.client.post('/accounts/register/', {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'Password123!',
            'password2': 'DifferentPassword456!',
            'phone': '0788112233',
            'address': 'Test Address',
            'date_of_birth': '1990-01-01',
            'id_number': '1111111111111111'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'password')
    
    def test_registration_with_missing_fields(self):
        """Test that registration fails when required fields are missing."""
        response = self.client.post('/accounts/register/', {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'Password123!',
            'password2': 'Password123!'
            # Missing phone, address, date_of_birth, id_number
        })
        
        self.assertEqual(response.status_code, 200)
        # Form should show errors for missing fields


class CustomerDashboardTest(TestCase):
    """Test customer dashboard functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testcustomer',
            password='testpass123'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            phone='0788000000',
            address='Test Address',
            date_of_birth='1990-01-01',
            id_number='1234567890123456'
        )
        self.account = Account.objects.create(
            customer=self.customer,
            account_type='checking',
            balance=Decimal('500.00')
        )
        self.client.login(username='testcustomer', password='testpass123')
    
    def test_dashboard_loads(self):
        """Test that customer dashboard loads correctly."""
        response = self.client.get('/accounts/dashboard/')
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_shows_account_info(self):
        """Test that dashboard displays account information."""
        response = self.client.get('/accounts/dashboard/')
        
        self.assertContains(response, self.account.account_number)
        self.assertContains(response, '500.00')
        self.assertContains(response, 'Checking')
    
    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication."""
        self.client.logout()
        response = self.client.get('/accounts/dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_dashboard_shows_kyc_status(self):
        """Test that dashboard displays KYC status."""
        response = self.client.get('/accounts/dashboard/')
        self.assertContains(response, 'Pending')  # Default KYC status


class LoginTest(TestCase):
    """Test login functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
    
    def test_login_page_loads(self):
        """Test that login page loads correctly."""
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)
    
    def test_successful_login(self):
        """Test that user can login successfully."""
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login
    
    def test_failed_login_wrong_password(self):
        """Test that login fails with wrong password."""
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Stays on login page
        self.assertContains(response, 'Invalid username or password')
    
    def test_failed_login_nonexistent_user(self):
        """Test that login fails with non-existent username."""
        response = self.client.post('/accounts/login/', {
            'username': 'nonexistent',
            'password': 'somepass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')