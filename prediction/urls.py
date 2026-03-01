from django.urls import path
from . import views

urlpatterns = [
    path('predict/', views.predict_transaction, name='predict'),
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/acknowledge/<int:alert_id>/', views.acknowledge_alert, name='acknowledge_alert'),
    path('network/', views.network_security, name='network_security'),
]