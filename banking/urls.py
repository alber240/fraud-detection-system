from django.urls import path
from . import views

urlpatterns = [
    path('deposit/', views.deposit, name='deposit'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('transfer/', views.transfer, name='transfer'),
    path('compliance/', views.compliance_dashboard, name='compliance_dashboard'),
path('compliance/resolve/<int:flag_id>/', views.resolve_flag, name='resolve_flag'),
path('feature-analytics/', views.feature_analytics, name='feature_analytics'),

path('review-queue/', views.review_queue, name='review_queue'),
path('review/<int:transaction_id>/', views.review_transaction, name='review_transaction'),
path('export-flagged/', views.export_flagged_transactions, name='export_flagged'),
path('export/', views.export_page, name='export_page'),

path('live-demo/', views.live_demo, name='live_demo'),
path('start-simulation/', views.start_simulation, name='start_simulation'),
path('stop-simulation/', views.stop_simulation, name='stop_simulation'),
path('get-transactions-ajax/', views.get_transactions_ajax, name='get_transactions_ajax'),

path('alert-simulation/', views.alert_simulation, name='alert_simulation'),
path('send-test-alert/', views.send_test_alert, name='send_test_alert'),
path('clear-alert-logs/', views.clear_alert_logs, name='clear_alert_logs'),
path('trigger-alert/<int:transaction_id>/', views.trigger_alert_for_transaction, name='trigger_alert_for_transaction'),
path('get-network-events-ajax/', views.get_network_events_ajax, name='get_network_events_ajax'),
]