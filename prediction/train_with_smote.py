"""
Model Training with SMOTE for Class Imbalance
Handles the extreme fraud imbalance (0.17% fraud cases)
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from imblearn.over_sampling import SMOTE
import joblib
import os
from django.conf import settings
import warnings
warnings.filterwarnings('ignore')


class FraudModelTrainer:
    """Train fraud detection models with SMOTE balancing"""
    
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.models = {}
        self.scaler = None
        self.results = {}
        
    def load_data(self):
        """Load and prepare the dataset"""
        print("📂 Loading dataset...")
        df = pd.read_csv(self.csv_path)
        
        # Separate features and target
        X = df.drop('Class', axis=1)
        y = df['Class']
        
        print(f"   Dataset shape: {X.shape}")
        print(f"   Fraud cases: {y.sum()} / {len(y)} ({y.mean()*100:.4f}%)")
        print(f"   Class imbalance ratio: {y.value_counts()[0] / y.value_counts()[1]:.1f}:1")
        
        return X, y
    
    def apply_smote(self, X_train, y_train):
        """Apply SMOTE to balance the training data"""
        print("\n🔄 Applying SMOTE for class balancing...")
        
        smote = SMOTE(random_state=42, sampling_strategy='auto')
        X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
        
        print(f"   Original training size: {len(X_train)}")
        print(f"   Resampled training size: {len(X_train_resampled)}")
        print(f"   New fraud cases: {y_train_resampled.sum()}")
        print(f"   New class balance ratio: {y_train_resampled.value_counts()[0] / y_train_resampled.value_counts()[1]:.1f}:1")
        
        return X_train_resampled, y_train_resampled
    
    def train_models(self, X_train, y_train, X_test, y_test):
        """Train multiple models and compare performance"""
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Model 1: Logistic Regression
        print("\n📊 Training Logistic Regression...")
        lr = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
        lr.fit(X_train_scaled, y_train)
        self.models['logistic_regression'] = lr
        self._evaluate_model(lr, X_test_scaled, y_test, 'Logistic Regression')
        
        # Model 2: Random Forest
        print("\n📊 Training Random Forest...")
        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        rf.fit(X_train_scaled, y_train)
        self.models['random_forest'] = rf
        self._evaluate_model(rf, X_test_scaled, y_test, 'Random Forest')
        
        # Model 3: XGBoost (if available)
        try:
            import xgboost as xgb
            print("\n📊 Training XGBoost...")
            xgb_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                scale_pos_weight=len(y_train[y_train==0]) / len(y_train[y_train==1]),
                eval_metric='logloss',
                use_label_encoder=False
            )
            xgb_model.fit(X_train_scaled, y_train)
            self.models['xgboost'] = xgb_model
            self._evaluate_model(xgb_model, X_test_scaled, y_test, 'XGBoost')
        except ImportError:
            print("⚠️ XGBoost not installed, skipping...")
        
        return self.models
    
    def _evaluate_model(self, model, X_test, y_test, name):
        """Evaluate model performance"""
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        
        self.results[name] = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1_score': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_proba),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
        }
        
        print(f"   ✅ {name}:")
        print(f"      Accuracy: {self.results[name]['accuracy']:.4f}")
        print(f"      Precision: {self.results[name]['precision']:.4f}")
        print(f"      Recall: {self.results[name]['recall']:.4f}")
        print(f"      F1-Score: {self.results[name]['f1_score']:.4f}")
        print(f"      ROC-AUC: {self.results[name]['roc_auc']:.4f}")
    
    def save_models(self):
        """Save trained models and scaler"""
        model_dir = os.path.join(settings.BASE_DIR, 'prediction', 'ml_models')
        os.makedirs(model_dir, exist_ok=True)
        
        for name, model in self.models.items():
            path = os.path.join(model_dir, f'{name}_with_smote.pkl')
            joblib.dump(model, path)
            print(f"💾 Saved {name} to {path}")
        
        # Save scaler
        scaler_path = os.path.join(model_dir, 'smote_scaler.pkl')
        joblib.dump(self.scaler, scaler_path)
        print(f"💾 Saved scaler to {scaler_path}")
        
        # Save results
        results_path = os.path.join(model_dir, 'training_results.json')
        import json
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"💾 Saved training results to {results_path}")
    
    def get_best_model(self):
        """Return the best model based on F1-score"""
        best_name = max(self.results, key=lambda x: self.results[x]['f1_score'])
        return best_name, self.models[best_name], self.results[best_name]


def train_with_smote(csv_path='ml_model/creditcard.csv'):
    """Main training function"""
    print("="*60)
    print("🚀 FRAUD DETECTION MODEL TRAINING WITH SMOTE")
    print("="*60)
    
    trainer = FraudModelTrainer(csv_path)
    X, y = trainer.load_data()
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Apply SMOTE
    X_train_balanced, y_train_balanced = trainer.apply_smote(X_train, y_train)
    
    # Train models
    trainer.train_models(X_train_balanced, y_train_balanced, X_test, y_test)
    
    # Save models
    trainer.save_models()
    
    # Display best model
    best_name, best_model, best_results = trainer.get_best_model()
    
    print("\n" + "="*60)
    print("🏆 BEST MODEL")
    print("="*60)
    print(f"Model: {best_name}")
    print(f"F1-Score: {best_results['f1_score']:.4f}")
    print(f"ROC-AUC: {best_results['roc_auc']:.4f}")
    
    return trainer


if __name__ == "__main__":
    train_with_smote()