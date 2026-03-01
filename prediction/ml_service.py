import joblib
import os
import numpy as np
from django.conf import settings
from django.db.models import Q
from banking.models import BankingTransaction
from accounts.models import Customer

# Paths
BASE_DIR = settings.BASE_DIR
MODEL_30_PATH = os.path.join(BASE_DIR, 'prediction', 'ml_models', 'fraud_detection_model.pkl')
SIMPLE_MODEL_PATH = os.path.join(BASE_DIR, 'prediction', 'ml_models', 'simple_fraud_model.pkl')
SCALER_PATH = os.path.join(BASE_DIR, 'prediction', 'ml_models', 'simple_scaler.pkl')

# Load models
model_30 = joblib.load(MODEL_30_PATH)
simple_model = joblib.load(SIMPLE_MODEL_PATH)
simple_scaler = joblib.load(SCALER_PATH)

def predict_fraud_30(features):
    """Predict using 30 features (list of 30 numbers)."""
    pred = model_30.predict([features])[0]
    prob = model_30.predict_proba([features])[0][1]
    return int(pred), float(prob)          # convert to native Python types

def predict_fraud_simple(amount, time_value=50000):
    """
    Predict using amount only (time fixed).
    Returns probability only (0–1) as Python float.
    """
    features = np.array([[amount, time_value]])
    features_scaled = simple_scaler.transform(features)
    prob = simple_model.predict_proba(features_scaled)[0][1]
    return float(prob)                     # ensure Python float

def get_behavioral_risk(transaction):
    """
    transaction is a BankingTransaction instance.
    Returns risk score 0–1 as Python float.
    """
    # Determine which customer owns the transaction
    if transaction.transaction_type == 'deposit':
        account = transaction.to_account
    else:
        account = transaction.from_account
    if not account:
        return 0.0
    customer = account.customer

    # Get all previous transactions for this customer (exclude current)
    transactions = BankingTransaction.objects.filter(
        Q(from_account__customer=customer) | Q(to_account__customer=customer)
    ).exclude(id=transaction.id)

    amounts = [float(t.amount) for t in transactions]
    if not amounts:
        return 0.0

    mean = np.mean(amounts)
    std = np.std(amounts)
    if std == 0:
        std = mean * 0.1 if mean > 0 else 1.0

    z_score = (float(transaction.amount) - mean) / std
    # Sigmoid shifted so that z_score=2 gives 0.5 risk, >2 higher risk
    risk = 1 / (1 + np.exp(-(z_score - 2)))
    return float(min(risk, 1.0))            # convert to Python float

def combined_risk(transaction):
    """
    Combine ML probability and behavioral risk.
    Returns max of both (simple fusion) as Python float.
    """
    ml_prob = predict_fraud_simple(float(transaction.amount))
    behavioral = get_behavioral_risk(transaction)
    return float(max(ml_prob, behavioral))  # ensure Python float