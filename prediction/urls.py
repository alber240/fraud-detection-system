from django.urls import path
from .views import predict_transaction

urlpatterns = [
    path('predict/', predict_transaction, name='predict'),
]