"""
Ensemble model builders for regression and classification.
"""
from sklearn.ensemble import VotingRegressor, VotingClassifier, StackingRegressor, StackingClassifier
from typing import Dict, Any, Optional

def build_voting_regressor(models: Dict[str, Any]) -> VotingRegressor:
    """Build a voting regressor from trained models."""
    items = sorted(models.items())
    return VotingRegressor(estimators=items)

def build_voting_classifier(models: Dict[str, Any], voting: str = "soft") -> VotingClassifier:
    """Build a voting classifier from trained models."""
    items = sorted(models.items())
    return VotingClassifier(estimators=items, voting=voting)

def build_stacking_regressor(models: Dict[str, Any], final_estimator=None) -> StackingRegressor:
    """Build a stacking regressor from trained models."""
    items = sorted(models.items())
    return StackingRegressor(estimators=items, final_estimator=final_estimator)

def build_stacking_classifier(models: Dict[str, Any], final_estimator=None) -> StackingClassifier:
    """Build a stacking classifier from trained models."""
    items = sorted(models.items())
    return StackingClassifier(estimators=items, final_estimator=final_estimator)
