from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import FraudAlert, NetworkEvent
from .ml_service import predict_fraud_30  # if needed

# Existing prediction view (keep as is)
@api_view(['POST'])
def predict_transaction(request):
    # Your existing prediction logic
    # (Make sure it uses the correct model functions)
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
    alerts = FraudAlert.objects.select_related('transaction').order_by('-created_at')
    return render(request, 'prediction/alerts.html', {'alerts': alerts})

@login_required
def acknowledge_alert(request, alert_id):
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
    events = NetworkEvent.objects.all().order_by('-timestamp')[:50]
    return render(request, 'prediction/network_security.html', {'events': events})