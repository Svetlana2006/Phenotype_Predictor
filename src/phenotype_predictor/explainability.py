import joblib
import numpy as np
from pathlib import Path
from typing import Dict

def get_feature_importances(model, feature_names: list[str]) -> Dict[str, float]:
    """
    Extracts mathematical feature importances from a trained scikit-learn model.
    Works for both RandomForest (feature_importances_) and LogisticRegression (coef_).
    Handles Pipeline objects automatically.
    """
    importances = {}
    
    # Extract the actual classifier if it's wrapped in a Pipeline
    if hasattr(model, 'steps'):
        model = model.steps[-1][1]
        
    if hasattr(model, 'feature_importances_'):
        # Random Forest or Gradient Boosting
        weights = model.feature_importances_
        for name, weight in zip(feature_names, weights):
            importances[name] = float(weight)
            
    elif hasattr(model, 'coef_'):
        # Logistic Regression or Linear Models
        # Coef shape can be (n_classes, n_features) or (1, n_features)
        weights = np.mean(np.abs(model.coef_), axis=0)
        
        # Normalize weights so they sum to 1.0 (to match Random Forest behavior)
        total_weight = np.sum(weights)
        if total_weight > 0:
            weights = weights / total_weight
            
        for name, weight in zip(feature_names, weights):
            importances[name] = float(weight)
    else:
        # Fallback if the model is not supported
        return {}

    # Sort descending
    importances = {k: round(v, 4) for k, v in sorted(importances.items(), key=lambda item: item[1], reverse=True) if v > 0}
    return importances

def explain_predictions(predictor_instance, X_vectors: dict) -> dict:
    """
    Given a PhenotypePredictor instance and the input feature vectors,
    calculates which specific SNPs had the highest mathematical weight for each model.
    """
    explanations = {}
    
    # Ancestry (Sparse Model or Full Model)
    # We dynamically check which one was used by checking the length of the input vector
    if 'ancestry' in X_vectors:
        anc_features = X_vectors['ancestry'].columns.tolist()
        anc_model = predictor_instance._sparse_ancestry if len(anc_features) < 100 else predictor_instance._ancestry
        explanations['ancestry'] = get_feature_importances(anc_model, anc_features)
        
    # Pigmentation
    if 'pigmentation' in X_vectors:
        pig_features = X_vectors['pigmentation'].columns.tolist()
        explanations['eye_color'] = get_feature_importances(predictor_instance._eye, pig_features)
        explanations['hair_color'] = get_feature_importances(predictor_instance._hair, pig_features)
        explanations['skin_color'] = get_feature_importances(predictor_instance._skin, pig_features)
        
    return explanations
