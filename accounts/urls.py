from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('post_login/', views.post_login_redirect, name='post_login'),
]