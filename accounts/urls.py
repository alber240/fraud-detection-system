from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('post_login/', views.post_login_redirect, name='post_login'),
    
    path('pending-kyc/', views.pending_kyc, name='pending_kyc'),
path('approve-kyc/<int:customer_id>/', views.approve_kyc, name='approve_kyc'),
path('reject-kyc/<int:customer_id>/', views.reject_kyc, name='reject_kyc'),
]