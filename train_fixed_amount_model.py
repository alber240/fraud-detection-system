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
print("Training Fixed Amount-Only Fraud Detection Model")
print("="*60)

# Load dataset
print("\n1. Loading dataset...")
df = pd.read_csv('ml_model/creditcard.csv')
print(f"   Dataset shape: {df.shape}")
print(f"   Fraud cases: {df['Class'].sum()} / {len(df)} ({df['Class'].mean()*100:.4f}%)")

# Use Amount as the only feature
X = df[['Amount']].values  # Use numpy array directly
y = df['Class'].values

# Scale the amount feature
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n2. Training set: {len(X_train)} transactions")
print(f"   Test set: {len(X_test)} transactions")

# Train Random Forest
print("\n3. Training Random Forest Classifier...")
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print("\n" + "="*60)
print("MODEL PERFORMANCE")
print("="*60)
print(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
print(f"Precision: {precision_score(y_test, y_pred):.4f}")
print(f"Recall:    {recall_score(y_test, y_pred):.4f}")
print(f"F1-Score:  {f1_score(y_test, y_pred):.4f}")

# Save models
joblib.dump(model, 'prediction/ml_models/amount_fraud_model_v2.pkl')
joblib.dump(scaler, 'prediction/ml_models/amount_scaler_v2.pkl')
print("\n✅ Models saved to:")
print("   - prediction/ml_models/amount_fraud_model_v2.pkl")
print("   - prediction/ml_models/amount_scaler_v2.pkl")

# Test predictions for different amounts
print("\n" + "="*60)
print("SAMPLE PREDICTIONS")
print("="*60)
test_amounts = [10, 50, 100, 500, 1000, 5000, 10000, 25000, 50000]
for amt in test_amounts:
    features = np.array([[amt]])
    features_scaled = scaler.transform(features)
    prob = model.predict_proba(features_scaled)[0][1]
    pred = "FRAUD" if prob > 0.5 else "LEGIT"
    print(f"Amount: ${amt:6} -> {pred} (Risk: {prob:.2%})")