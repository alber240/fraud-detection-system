from pyexpat.errors import messages

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import FraudAlert, NetworkEvent
from .ml_service import predict_fraud_30
import os
from django.conf import settings


@api_view(['POST'])
def predict_transaction(request):
    """API endpoint for fraud prediction"""
    features = request.data.get('features')
    if not features:
        return Response({'error': 'No features provided'}, status=400)
    pred, prob = predict_fraud_30(features)
    return Response({
        'prediction': int(pred),
        'probability': float(prob),
        'is_fraud': bool(pred)
    })


@login_required
def alert_list(request):
    """View all fraud alerts"""
    alerts = FraudAlert.objects.all().order_by('-created_at')
    return render(request, 'prediction/alerts.html', {'alerts': alerts})


@login_required
def acknowledge_alert(request, alert_id):
    """Acknowledge a fraud alert"""
    alert = get_object_or_404(FraudAlert, id=alert_id)
    if request.method == 'POST':
        alert.acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.resolution_notes = request.POST.get('notes', '')
        alert.save()
        return redirect('alert_list')
    return render(request, 'prediction/acknowledge_alert.html', {'alert': alert})


@login_required
def network_security(request):
    """View network security events"""
    events = NetworkEvent.objects.all().order_by('-timestamp')[:50]
    return render(request, 'prediction/network_security.html', {'events': events})


import pandas as pd
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .forms import DatasetUploadForm
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def upload_dataset(request):
    """
    Upload CSV/Excel dataset for fraud detection training
    """
    if request.method == 'POST':
        form = DatasetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            dataset_file = request.FILES['dataset_file']
            dataset_name = form.cleaned_data['dataset_name']
            has_header = form.cleaned_data['has_header']
            
            # Create upload directory if not exists
            upload_dir = os.path.join(settings.BASE_DIR, 'uploads', 'datasets')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            file_path = default_storage.save(
                os.path.join('uploads/datasets', dataset_file.name),
                ContentFile(dataset_file.read())
            )
            full_path = os.path.join(settings.BASE_DIR, file_path)
            
            # Process the file based on extension
            file_ext = dataset_file.name.split('.')[-1].lower()
            
            try:
                if file_ext == 'csv':
                    df = pd.read_csv(full_path, header=0 if has_header else None)
                elif file_ext in ['xlsx', 'xls']:
                    df = pd.read_excel(full_path, header=0 if has_header else None)
                else:
                    messages.error(request, "Unsupported file format. Please upload CSV or Excel file.")
                    return redirect('upload_dataset')
                
                # Store in session for preview
                request.session['uploaded_dataset'] = {
                    'name': dataset_name,
                    'path': file_path,
                    'shape': df.shape,
                    'columns': list(df.columns[:10]),  # First 10 columns
                    'preview': df.head(5).to_html(classes='table table-sm')
                }
                
                messages.success(
                    request, 
                    f"Dataset '{dataset_name}' uploaded successfully! "
                    f"Shape: {df.shape[0]} rows, {df.shape[1]} columns"
                )
                return redirect('dataset_preview')
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                return redirect('upload_dataset')
    else:
        form = DatasetUploadForm()
    
    return render(request, 'prediction/upload_dataset.html', {'form': form})


@staff_member_required
def dataset_preview(request):
    """
    Preview uploaded dataset before training
    """
    dataset_info = request.session.get('uploaded_dataset')
    
    if not dataset_info:
        messages.warning(request, "No dataset uploaded. Please upload a dataset first.")
        return redirect('upload_dataset')
    
    return render(request, 'prediction/dataset_preview.html', {'dataset': dataset_info})


import json
import os
from django.conf import settings

@staff_member_required
def smote_results(request):
    """Display SMOTE training results"""
    results_path = os.path.join(settings.BASE_DIR, 'prediction', 'ml_models', 'training_results.json')
    
    results = {}
    if os.path.exists(results_path):
        with open(results_path, 'r') as f:
            results = json.load(f)
    
    # Get the best model
    best_model = None
    best_score = 0
    for name, metrics in results.items():
        if metrics.get('f1_score', 0) > best_score:
            best_score = metrics['f1_score']
            best_model = name
    
    context = {
        'results': results,
        'best_model': best_model,
        'has_results': len(results) > 0
    }
    
    return render(request, 'prediction/smote_results.html', context)

import json
import os
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
import pandas as pd
import numpy as np
from sklearn.metrics import roc_curve, auc

@staff_member_required
def model_performance(request):
    """
    Model Performance Dashboard showing accuracy, precision, recall, F1, ROC-AUC
    """
    # Load training results from SMOTE
    results_path = os.path.join(settings.BASE_DIR, 'prediction', 'ml_models', 'training_results.json')
    
    results = {}
    if os.path.exists(results_path):
        with open(results_path, 'r') as f:
            results = json.load(f)
    
    # Prepare data for charts
    chart_data = {}
    roc_data = {}
    
    for model_name, metrics in results.items():
        chart_data[model_name] = {
            'accuracy': metrics.get('accuracy', 0) * 100,
            'precision': metrics.get('precision', 0) * 100,
            'recall': metrics.get('recall', 0) * 100,
            'f1_score': metrics.get('f1_score', 0) * 100,
            'roc_auc': metrics.get('roc_auc', 0) * 100,
        }
        
        # ROC curve data (simulated for now - can be enhanced with actual predictions)
        if 'confusion_matrix' in metrics:
            tn, fp, fn, tp = metrics['confusion_matrix'][0][0], metrics['confusion_matrix'][0][1], metrics['confusion_matrix'][1][0], metrics['confusion_matrix'][1][1]
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            roc_data[model_name] = {
                'fpr': [0, fpr, 1],
                'tpr': [0, tpr, 1],
                'auc': metrics.get('roc_auc', 0)
            }
    
    # Get best model
    best_model = None
    best_score = 0
    for name, metrics in results.items():
        score = metrics.get('f1_score', 0)
        if score > best_score:
            best_score = score
            best_model = name
    
    context = {
        'results': results,
        'chart_data': json.dumps(chart_data),
        'roc_data': json.dumps(roc_data),
        'best_model': best_model,
        'has_results': len(results) > 0
    }
    
    return render(request, 'prediction/model_performance.html', context)

import os
import json
from django.conf import settings
from .shap_analysis import run_shap_analysis

@staff_member_required
def feature_importance(request):
    """
    Display SHAP feature importance visualizations
    """
    # Check if SHAP images already exist
    shap_bar_path = os.path.join(settings.BASE_DIR, 'prediction', 'ml_models', 'shap_feature_importance.png')
    shap_summary_path = os.path.join(settings.BASE_DIR, 'prediction', 'ml_models', 'shap_summary.png')
    
    has_images = os.path.exists(shap_bar_path) and os.path.exists(shap_summary_path)
    
    context = {
        'has_images': has_images,
        'shap_bar_url': '/static/shap_feature_importance.png' if has_images else None,
        'shap_summary_url': '/static/shap_summary.png' if has_images else None,
    }
    
    return render(request, 'prediction/feature_importance.html', context)


@staff_member_required
def generate_shap(request):
    """
    Generate SHAP visualizations on demand
    """
    import traceback
    import shutil
    
    if request.method == 'POST':
        try:
            from .shap_analysis import run_shap_analysis
            
            results = run_shap_analysis()
            
            if results and results.get('bar_chart') and results.get('summary_plot'):
                # Copy images to static folder for serving
                static_dir = os.path.join(settings.BASE_DIR, 'static')
                os.makedirs(static_dir, exist_ok=True)
                
                if results.get('bar_chart') and os.path.exists(results['bar_chart']):
                    dest_bar = os.path.join(static_dir, 'shap_feature_importance.png')
                    shutil.copy(results['bar_chart'], dest_bar)
                    print(f"✅ Copied bar chart to {dest_bar}")
                
                if results.get('summary_plot') and os.path.exists(results['summary_plot']):
                    dest_summary = os.path.join(static_dir, 'shap_summary.png')
                    shutil.copy(results['summary_plot'], dest_summary)
                    print(f"✅ Copied summary plot to {dest_summary}")
                
                # Use print instead of messages to avoid errors
                print("SHAP analysis completed successfully!")
            else:
                print("SHAP analysis failed. Please check model and data.")
                
        except Exception as e:
            print(f"SHAP generation error: {traceback.format_exc()}")
        
        return redirect('feature_importance')
    
    return redirect('feature_importance')