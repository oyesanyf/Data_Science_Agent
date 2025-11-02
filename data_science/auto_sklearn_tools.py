"""
Auto-sklearn-like AutoML tools built on scikit-learn.

Provides automated algorithm selection, hyperparameter optimization,
feature preprocessing, and ensemble construction - cross-platform compatible.
"""
from __future__ import annotations
from .ds_tools import ensure_display_fields

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Any
from io import BytesIO

from sklearn.model_selection import RandomizedSearchCV, cross_val_score, train_test_split
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    VotingClassifier,
    VotingRegressor,
    StackingClassifier,
    StackingRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge, Lasso
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.svm import SVC, SVR
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, r2_score, mean_squared_error
from scipy.stats import randint, uniform

from google.adk.tools import ToolContext


def _json_safe(obj: Any) -> Any:
    """Convert complex Python objects to JSON-serializable types using production serializer."""
    from .json_serializer import to_json_safe
    return to_json_safe(obj, use_pydantic=True)


def _can_stratify(y, min_samples_per_class=2):
    """Check if stratification is safe for train_test_split.
    
    Stratification requires at least min_samples_per_class samples per class.
    
    Args:
        y: Target variable (pandas Series or numpy array)
        min_samples_per_class: Minimum samples required per class (default: 2)
    
    Returns:
        bool: True if stratification is safe, False otherwise
    """
    try:
        # Convert to pandas Series if needed for easier handling
        if isinstance(y, np.ndarray):
            y_series = pd.Series(y)
        else:
            y_series = y
        
        # Check if there are multiple classes
        unique_classes = y_series.nunique(dropna=True)
        if unique_classes < 2:
            return False
        
        # Check if each class has at least min_samples_per_class samples
        class_counts = y_series.value_counts()
        min_count = class_counts.min()
        
        return min_count >= min_samples_per_class
    except Exception:
        return False


def _get_classification_models():
    """Get candidate classification models with hyperparameter spaces."""
    return {
        "RandomForest": {
            "model": RandomForestClassifier(random_state=42),
            "params": {
                "n_estimators": randint(50, 300),
                "max_depth": [None, 10, 20, 30],
                "min_samples_split": randint(2, 11),
                "min_samples_leaf": randint(1, 5),
            }
        },
        "GradientBoosting": {
            "model": GradientBoostingClassifier(random_state=42),
            "params": {
                "n_estimators": randint(50, 200),
                "learning_rate": uniform(0.01, 0.3),
                "max_depth": randint(3, 10),
                "min_samples_split": randint(2, 11),
            }
        },
        "LogisticRegression": {
            "model": LogisticRegression(random_state=42, max_iter=1000),
            "params": {
                "C": uniform(0.01, 10),
                "penalty": ["l1", "l2"],
                "solver": ["liblinear", "saga"],
            }
        },
        "SVM": {
            "model": SVC(random_state=42, probability=True),
            "params": {
                "C": uniform(0.1, 10),
                "kernel": ["rbf", "linear"],
                "gamma": ["scale", "auto"],
            }
        },
        "KNN": {
            "model": KNeighborsClassifier(),
            "params": {
                "n_neighbors": randint(3, 15),
                "weights": ["uniform", "distance"],
                "metric": ["euclidean", "manhattan"],
            }
        },
    }


def _get_regression_models():
    """Get candidate regression models with hyperparameter spaces."""
    return {
        "RandomForest": {
            "model": RandomForestRegressor(random_state=42),
            "params": {
                "n_estimators": randint(50, 300),
                "max_depth": [None, 10, 20, 30],
                "min_samples_split": randint(2, 11),
                "min_samples_leaf": randint(1, 5),
            }
        },
        "GradientBoosting": {
            "model": GradientBoostingRegressor(random_state=42),
            "params": {
                "n_estimators": randint(50, 200),
                "learning_rate": uniform(0.01, 0.3),
                "max_depth": randint(3, 10),
                "min_samples_split": randint(2, 11),
            }
        },
        "Ridge": {
            "model": Ridge(random_state=42),
            "params": {
                "alpha": uniform(0.01, 10),
                "solver": ["auto", "svd", "cholesky"],
            }
        },
        "Lasso": {
            "model": Lasso(random_state=42, max_iter=2000),
            "params": {
                "alpha": uniform(0.01, 10),
                "selection": ["cyclic", "random"],
            }
        },
        "SVR": {
            "model": SVR(),
            "params": {
                "C": uniform(0.1, 10),
                "kernel": ["rbf", "linear"],
                "gamma": ["scale", "auto"],
            }
        },
        "KNN": {
            "model": KNeighborsRegressor(),
            "params": {
                "n_neighbors": randint(3, 15),
                "weights": ["uniform", "distance"],
                "metric": ["euclidean", "manhattan"],
            }
        },
    }


@ensure_display_fields
async def auto_sklearn_classify(
    csv_path: str,
    target: str,
    time_budget: int = 60,
    n_iter: int = 20,
    build_ensemble: bool = True,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """Auto-sklearn style classification with algorithm selection and hyperparameter optimization.
    
    Automatically:
    1. Preprocesses features (scaling, encoding)
    2. Tries multiple classification algorithms
    3. Optimizes hyperparameters for each
    4. Builds an ensemble of top models
    5. Returns best model and leaderboard
    
    Args:
        csv_path: Path to CSV file
        target: Target column name
        time_budget: Time limit in seconds (approximate)
        n_iter: Number of hyperparameter combinations to try per model
        build_ensemble: Whether to build voting ensemble of top models
        tool_context: ADK tool context for artifacts
    
    Returns:
        dict with best model, leaderboard, and ensemble info
    """
    # Load data
    df = pd.read_csv(csv_path)
    
    # Separate features and target
    X = df.drop(columns=[target])
    y = df[target]
    
    # Encode categorical target if needed
    if y.dtype == 'object' or y.dtype.name == 'category':
        le = LabelEncoder()
        y = le.fit_transform(y)
        classes = le.classes_.tolist()
    else:
        classes = sorted(y.unique().tolist())
    
    # Preprocess features
    # Encode categorical features
    X_processed = X.copy()
    categorical_cols = X.select_dtypes(include=['object', 'category']).columns
    for col in categorical_cols:
        le = LabelEncoder()
        X_processed[col] = le.fit_transform(X[col].astype(str))
    
    # Fill missing values
    X_processed = X_processed.fillna(X_processed.median())
    
    # [OK] Split into train/test BEFORE any training (80/20 split)
    X_train, X_test, y_train, y_test = train_test_split(
        X_processed, y, test_size=0.2, random_state=42, 
        stratify=y if _can_stratify(y) else None
    )
    
    # Scale features (fit on training only, transform both)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Try multiple models with hyperparameter optimization
    models = _get_classification_models()
    results = []
    trained_models = []
    
    for model_name, config in models.items():
        try:
            # Randomized search for hyperparameter optimization (on training set only)
            search = RandomizedSearchCV(
                config["model"],
                config["params"],
                n_iter=n_iter,
                cv=min(3, len(y_train) // 2),
                scoring='accuracy',
                random_state=42,
                n_jobs=-1
            )
            search.fit(X_train_scaled, y_train)
            
            # [OK] Evaluate on held-out test set
            test_accuracy = accuracy_score(y_test, search.best_estimator_.predict(X_test_scaled))
            
            # Cross-validation score (for comparison)
            cv_scores = cross_val_score(search.best_estimator_, X_train_scaled, y_train, cv=3, scoring='accuracy')
            
            results.append({
                "model": model_name,
                "cv_accuracy": float(search.best_score_),
                "test_accuracy": float(test_accuracy),  # [OK] NEW: Held-out test score
                "cv_mean": float(cv_scores.mean()),
                "cv_std": float(cv_scores.std()),
                "best_params": _json_safe(search.best_params_)
            })
            
            trained_models.append((model_name, search.best_estimator_, test_accuracy))
            
        except Exception as e:
            results.append({
                "model": model_name,
                "error": str(e)
            })
    
    # Sort by test performance (most reliable metric)
    results_sorted = sorted([r for r in results if 'test_accuracy' in r], 
                           key=lambda x: x['test_accuracy'], reverse=True)
    
    best_model_name = results_sorted[0]['model']
    best_model = next(m[1] for m in trained_models if m[0] == best_model_name)
    
    # Build ensemble if requested
    ensemble_info = None
    if build_ensemble and len(trained_models) >= 3:
        # Use top 3 models for voting ensemble
        top_models = sorted(trained_models, key=lambda x: x[2], reverse=True)[:3]
        estimators = [(name, model) for name, model, _ in top_models]
        
        ensemble = VotingClassifier(estimators=estimators, voting='soft')
        ensemble.fit(X_train_scaled, y_train)  # [OK] Fit on training set only
        
        # [OK] Evaluate ensemble on test set
        ensemble_test_score = accuracy_score(y_test, ensemble.predict(X_test_scaled))
        
        ensemble_info = {
            "type": "VotingClassifier",
            "models": [name for name, _, _ in top_models],
            "test_accuracy": float(ensemble_test_score),  # [OK] Test set performance
            "improvement": float(ensemble_test_score - results_sorted[0]['test_accuracy'])
        }
    
    # Prepare result
    result = {
        "status": "success",
        "task": "classification",
        "target": target,
        "n_samples_total": len(y),
        "n_samples_train": len(y_train),  # [OK] NEW
        "n_samples_test": len(y_test),    # [OK] NEW
        "test_split": "80/20",             # [OK] NEW
        "n_features": X.shape[1],
        "n_classes": len(classes),
        "classes": [str(c) for c in classes],
        "best_model": best_model_name,
        "best_test_accuracy": results_sorted[0]['test_accuracy'],  # [OK] Test set performance
        "best_cv_accuracy": results_sorted[0]['cv_accuracy'],       # [OK] CV performance (for comparison)
        "best_params": results_sorted[0]['best_params'],
        "leaderboard": results_sorted,
        "ensemble": ensemble_info,
        "models_tried": len(results),
        "message": f"Best model: {best_model_name} (test accuracy: {results_sorted[0]['test_accuracy']:.4f}, CV: {results_sorted[0]['cv_accuracy']:.4f})"
    }
    
    # Save leaderboard as artifact
    if tool_context is not None:
        from google.genai import types
        buf = BytesIO()
        buf.write(str(result).encode('utf-8'))
        await tool_context.save_artifact(
            filename="auto_sklearn_results.json",
            artifact=types.Part.from_bytes(
                data=buf.getvalue(),
                mime_type="application/json"
            )
        )
    
    return _json_safe(result)


@ensure_display_fields
async def auto_sklearn_regress(
    csv_path: str,
    target: str,
    time_budget: int = 60,
    n_iter: int = 20,
    build_ensemble: bool = True,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """Auto-sklearn style regression with algorithm selection and hyperparameter optimization.
    
    Automatically:
    1. Preprocesses features (scaling, encoding)
    2. Tries multiple regression algorithms
    3. Optimizes hyperparameters for each
    4. Builds an ensemble of top models
    5. Returns best model and leaderboard
    
    Args:
        csv_path: Path to CSV file
        target: Target column name
        time_budget: Time limit in seconds (approximate)
        n_iter: Number of hyperparameter combinations to try per model
        build_ensemble: Whether to build stacking ensemble of top models
        tool_context: ADK tool context for artifacts
    
    Returns:
        dict with best model, leaderboard, and ensemble info
    """
    # Load data
    df = pd.read_csv(csv_path)
    
    # Separate features and target
    X = df.drop(columns=[target])
    y = df[target]
    
    # Preprocess features
    X_processed = X.copy()
    categorical_cols = X.select_dtypes(include=['object', 'category']).columns
    for col in categorical_cols:
        le = LabelEncoder()
        X_processed[col] = le.fit_transform(X[col].astype(str))
    
    # Fill missing values
    X_processed = X_processed.fillna(X_processed.median())
    
    # [OK] Split into train/test BEFORE any training (80/20 split)
    X_train, X_test, y_train, y_test = train_test_split(
        X_processed, y, test_size=0.2, random_state=42
    )
    
    # Scale features (fit on training only, transform both)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Try multiple models with hyperparameter optimization
    models = _get_regression_models()
    results = []
    trained_models = []
    
    for model_name, config in models.items():
        try:
            # Randomized search for hyperparameter optimization (on training set only)
            search = RandomizedSearchCV(
                config["model"],
                config["params"],
                n_iter=n_iter,
                cv=min(3, len(y_train) // 2),
                scoring='r2',
                random_state=42,
                n_jobs=-1
            )
            search.fit(X_train_scaled, y_train)
            
            # [OK] Evaluate on held-out test set
            y_test_pred = search.best_estimator_.predict(X_test_scaled)
            test_r2 = r2_score(y_test, y_test_pred)
            test_rmse = float(np.sqrt(mean_squared_error(y_test, y_test_pred)))
            
            # Cross-validation score (for comparison)
            cv_scores = cross_val_score(search.best_estimator_, X_train_scaled, y_train, cv=3, scoring='r2')
            
            results.append({
                "model": model_name,
                "cv_r2": float(search.best_score_),
                "test_r2": float(test_r2),      # [OK] NEW: Held-out test R²
                "test_rmse": test_rmse,          # [OK] NEW: Held-out test RMSE
                "cv_mean": float(cv_scores.mean()),
                "cv_std": float(cv_scores.std()),
                "best_params": _json_safe(search.best_params_)
            })
            
            trained_models.append((model_name, search.best_estimator_, test_r2))
            
        except Exception as e:
            results.append({
                "model": model_name,
                "error": str(e)
            })
    
    # Sort by test performance (most reliable metric)
    results_sorted = sorted([r for r in results if 'test_r2' in r], 
                           key=lambda x: x['test_r2'], reverse=True)
    
    best_model_name = results_sorted[0]['model']
    best_model = next(m[1] for m in trained_models if m[0] == best_model_name)
    
    # Build ensemble if requested
    ensemble_info = None
    if build_ensemble and len(trained_models) >= 3:
        # Use top 3 models for stacking ensemble
        top_models = sorted(trained_models, key=lambda x: x[2], reverse=True)[:3]
        estimators = [(name, model) for name, model, _ in top_models]
        
        # Use Ridge as meta-learner
        ensemble = StackingRegressor(
            estimators=estimators,
            final_estimator=Ridge(),
            cv=3
        )
        ensemble.fit(X_train_scaled, y_train)  # [OK] Fit on training set only
        
        # [OK] Evaluate ensemble on test set
        y_ensemble_pred = ensemble.predict(X_test_scaled)
        ensemble_test_r2 = r2_score(y_test, y_ensemble_pred)
        ensemble_test_rmse = float(np.sqrt(mean_squared_error(y_test, y_ensemble_pred)))
        
        ensemble_info = {
            "type": "StackingRegressor",
            "models": [name for name, _, _ in top_models],
            "test_r2": float(ensemble_test_r2),      # [OK] Test set R²
            "test_rmse": ensemble_test_rmse,         # [OK] Test set RMSE
            "improvement": float(ensemble_test_r2 - results_sorted[0]['test_r2'])
        }
    
    # Prepare result
    result = {
        "status": "success",
        "task": "regression",
        "target": target,
        "n_samples_total": len(y),
        "n_samples_train": len(y_train),  # [OK] NEW
        "n_samples_test": len(y_test),    # [OK] NEW
        "test_split": "80/20",             # [OK] NEW
        "n_features": X.shape[1],
        "best_model": best_model_name,
        "best_test_r2": results_sorted[0]['test_r2'],      # [OK] Test set R²
        "best_test_rmse": results_sorted[0]['test_rmse'],  # [OK] Test set RMSE
        "best_cv_r2": results_sorted[0]['cv_r2'],          # [OK] CV R² (for comparison)
        "best_params": results_sorted[0]['best_params'],
        "leaderboard": results_sorted,
        "ensemble": ensemble_info,
        "models_tried": len(results),
        "message": f"Best model: {best_model_name} (test R² = {results_sorted[0]['test_r2']:.4f}, test RMSE = {results_sorted[0]['test_rmse']:.4f})"
    }
    
    # Save leaderboard as artifact
    if tool_context is not None:
        from google.genai import types
        buf = BytesIO()
        buf.write(str(result).encode('utf-8'))
        await tool_context.save_artifact(
            filename="auto_sklearn_results.json",
            artifact=types.Part.from_bytes(
                data=buf.getvalue(),
                mime_type="application/json"
            )
        )
    
    return _json_safe(result)

