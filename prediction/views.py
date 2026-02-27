from rest_framework.decorators import api_view
from rest_framework.response import Response
from .ml_service import predict_fraud

@api_view(['POST'])
def predict_transaction(request):
    # Expect JSON with feature list (order must match training)
    features = request.data.get('features')
    if not features:
        return Response({'error': 'No features provided'}, status=400)
    
    prediction, probability = predict_fraud(features)
    return Response({
        'prediction': int(prediction),
        'probability': float(probability),
        'is_fraud': bool(prediction)
    })