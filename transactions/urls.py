from django.urls import path
from . import views

urlpatterns = [
    #path('', views.TransactionListCreate.as_view(), name='transaction-list'),
    path('dashboard/', views.dashboard, name='dashboard'),  # for the dashboard
    path('new/', views.transaction_create, name='transaction-create'),
]