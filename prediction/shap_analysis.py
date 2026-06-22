"""
SHAP (SHapley Additive exPlanations) for Feature Importance
Shows which features most influence fraud predictions
"""

import joblib
import pandas as pd
import numpy as np
import shap
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid tkinter issues
import matplotlib.pyplot as plt
import os
from django.conf import settings


class SHAPAnalyzer:
    """Generate SHAP feature importance visualizations"""
    
    def __init__(self):
        self.model = None
        self.feature_names = None
        self.background_data = None
        
    def load_model(self, model_path='prediction/ml_models/random_forest_with_smote.pkl'):
        """Load trained model"""
        full_path = os.path.join(settings.BASE_DIR, model_path)
        try:
            self.model = joblib.load(full_path)
            print(f"✅ Model loaded from {full_path}")
            return True
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False
    
    def load_sample_data(self, csv_path='ml_model/creditcard.csv'):
        """Load sample data for SHAP analysis"""
        full_path = os.path.join(settings.BASE_DIR, csv_path)
        try:
            df = pd.read_csv(full_path)
            # Use first 500 rows for faster computation
            X_sample = df.drop('Class', axis=1).head(500)
            self.feature_names = X_sample.columns.tolist()
            self.background_data = X_sample
            print(f"✅ Loaded {len(X_sample)} samples for SHAP analysis")
            return X_sample
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return None
    
    def calculate_shap_values(self, X_sample=None):
        """Calculate SHAP values for feature importance"""
        if X_sample is None:
            X_sample = self.background_data
        
        if X_sample is None:
            return None, None
        
        # Create explainer
        explainer = shap.TreeExplainer(self.model)
        
        # Calculate SHAP values (use subset for performance)
        X_subset = X_sample.head(200)
        shap_values = explainer.shap_values(X_subset)
        
        # For binary classification, shap_values is a list - take class 1 (fraud)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        
        return shap_values, X_subset
    
    def generate_bar_chart(self, shap_values, X_sample, save_path=None):
        """Generate bar chart of feature importance"""
        if save_path is None:
            save_path = os.path.join(settings.BASE_DIR, 'prediction', 'ml_models', 'shap_feature_importance.png')
        
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, X_sample, feature_names=self.feature_names, show=False, plot_type="bar", max_display=20)
        plt.title('Feature Importance (SHAP) - Top 20 Features', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"✅ Bar chart saved to {save_path}")
        return save_path
    
    def generate_summary_plot(self, shap_values, X_sample, save_path=None):
        """Generate summary dot plot of feature importance"""
        if save_path is None:
            save_path = os.path.join(settings.BASE_DIR, 'prediction', 'ml_models', 'shap_summary.png')
        
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, X_sample, feature_names=self.feature_names, show=False, max_display=20)
        plt.title('SHAP Summary Plot - Feature Impact on Fraud Prediction', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"✅ Summary plot saved to {save_path}")
        return save_path
    
    def get_top_features(self, shap_values, top_n=10):
        """Get top N most important features"""
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        # Convert to list of tuples
        feature_importance = []
        for i, name in enumerate(self.feature_names):
            if i < len(mean_abs_shap):
                feature_importance.append((name, float(mean_abs_shap[i])))
        
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        return feature_importance[:top_n]
    
    def generate_all(self):
        """Generate all SHAP visualizations"""
        if not self.load_model():
            return None
        
        X_sample = self.load_sample_data()
        if X_sample is None:
            return None
        
        shap_values, X_subset = self.calculate_shap_values(X_sample)
        if shap_values is None:
            return None
        
        bar_path = self.generate_bar_chart(shap_values, X_subset)
        summary_path = self.generate_summary_plot(shap_values, X_subset)
        top_features = self.get_top_features(shap_values)
        
        return {
            'bar_chart': bar_path,
            'summary_plot': summary_path,
            'top_features': top_features,
            'feature_names': self.feature_names[:10]
        }


def run_shap_analysis():
    """Run SHAP analysis and return results"""
    try:
        analyzer = SHAPAnalyzer()
        return analyzer.generate_all()
    except Exception as e:
        print(f"SHAP analysis error: {e}")
        return None


if __name__ == "__main__":
    run_shap_analysis()