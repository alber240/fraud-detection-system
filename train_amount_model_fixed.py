"""
Train a pure ML model using ONLY transaction amount as feature
Simplified version - guaranteed to complete
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("TRAINING PURE ML MODEL ON AMOUNT ONLY")
print("="*60)

# Load dataset
print("\n1. Loading credit card dataset...")
df = pd.read_csv('ml_model/creditcard.csv')
print(f"   Total transactions: {len(df):,}")
print(f"   Fraud cases: {df['Class'].sum():,} ({df['Class'].mean()*100:.4f}%)")

# Use ONLY Amount as feature
X = df[['Amount']].values
y = df['Class'].values

# Scale the feature
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.3, random_state=42, stratify=y
)

print(f"\n2. Training set: {len(X_train):,} transactions")
print(f"   Test set: {len(X_test):,} transactions")

# Train Random Forest (simpler, faster)
print("\n3. Training Random Forest Classifier on Amount only...")
model = RandomForestClassifier(
    n_estimators=100,  # Reduced from 200 for faster training
    max_depth=8,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print("\n" + "="*60)
print("MODEL PERFORMANCE (Amount-only Random Forest)")
print("="*60)
print(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
print(f"Precision: {precision_score(y_test, y_pred):.4f}")
print(f"Recall:    {recall_score(y_test, y_pred):.4f}")
print(f"F1-Score:  {f1_score(y_test, y_pred):.4f}")

# Save model and scaler
joblib.dump(model, 'prediction/ml_models/amount_only_model.pkl')
joblib.dump(scaler, 'prediction/ml_models/amount_only_scaler.pkl')
print("\n✅ Model saved to: prediction/ml_models/amount_only_model.pkl")
print("✅ Scaler saved to: prediction/ml_models/amount_only_scaler.pkl")

# Test predictions
print("\n" + "="*60)
print("SAMPLE PREDICTIONS (Pure ML Model)")
print("="*60)
test_amounts = [10, 50, 100, 500, 1000, 5000, 10000, 25000, 50000]
for amt in test_amounts:
    features = np.array([[amt]])
    features_scaled = scaler.transform(features)
    prob = model.predict_proba(features_scaled)[0][1]
    pred = "FRAUD" if prob > 0.5 else "LEGIT"
    print(f"Amount: ${amt:6} -> {pred} (Risk: {prob:.2%})")