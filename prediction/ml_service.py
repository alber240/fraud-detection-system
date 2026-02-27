import joblib
import os
from django.conf import settings

# Load the model once when Django starts
model_path = os.path.join(settings.BASE_DIR, 'prediction', 'ml_models', 'fraud_detection_model.pkl')
model = joblib.load(model_path)

def predict_fraud(transaction_features):
    """
    Expects a list or array of features matching the model's input.
    Returns prediction (0/1) and probability.
    """
    prediction = model.predict([transaction_features])[0]
    probability = model.predict_proba([transaction_features])[0][1]  # probability of class 1 (fraud)
    return prediction, probability