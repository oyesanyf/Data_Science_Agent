"""
Task detection and model recommendations.
"""
import numpy as np
import pandas as pd
from typing import Literal, List

Task = Literal["regression", "classification"]

def detect_task(y: pd.Series, cls_threshold: int = 20) -> Task:
    """Detect if the target variable is for classification or regression."""
    if y.dtype.kind in "ifu":  # int/float/unsigned
        nunique = y.dropna().nunique()
        return "classification" if (y.dtype.kind in "iu" and nunique <= cls_threshold) else "regression"
    return "classification"

def recommend_models(task: Task) -> List[str]:
    """Recommend appropriate models based on task type."""
    if task == "regression":
        return ["RandomForestRegressor", "GradientBoostingRegressor", "ElasticNet", "Ridge", "SVR"]
    else:
        return ["RandomForestClassifier", "GradientBoostingClassifier", "LogisticRegression", "SVC", "KNeighborsClassifier"]

def get_ensemble_models(task: Task) -> List[str]:
    """Get models suitable for ensemble based on task type."""
    if task == "regression":
        return ["RandomForestRegressor", "GradientBoostingRegressor", "ElasticNet"]
    else:
        return ["RandomForestClassifier", "GradientBoostingClassifier", "LogisticRegression"]
