from django.urls import path
from . import views

urlpatterns = [
    path('predict/', views.predict_transaction, name='predict'),
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/acknowledge/<int:alert_id>/', views.acknowledge_alert, name='acknowledge_alert'),
    path('network/', views.network_security, name='network_security'),
    
    # NEW: Dataset upload routes
    path('upload/', views.upload_dataset, name='upload_dataset'),
    path('preview/', views.dataset_preview, name='dataset_preview'),
    
    path('smote-results/', views.smote_results, name='smote_results'),
    path('model-performance/', views.model_performance, name='model_performance'),
    
    path('feature-importance/', views.feature_importance, name='feature_importance'),
path('generate-shap/', views.generate_shap, name='generate_shap'),
]