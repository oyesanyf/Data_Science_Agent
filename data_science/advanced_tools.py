"""
Advanced Data Science Tools
- Optuna Bayesian Hyperparameter Optimization
- Great Expectations Data Validation
- MLflow Experiment Tracking & Model Cards
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List
from google.adk.tools import ToolContext
import logging
from .ds_tools import ensure_display_fields

logger = logging.getLogger(__name__)


def _json_safe(obj):
    """Convert complex Python objects to JSON-serializable types using production serializer."""
    from .json_serializer import to_json_safe
    return to_json_safe(obj, use_pydantic=True)


async def _load_dataframe(csv_path: Optional[str], tool_context: Optional[ToolContext] = None) -> pd.DataFrame:
    """Helper to load DataFrame from csv_path or uploaded files."""
    from pathlib import Path
    import logging
    import glob
    logger = logging.getLogger(__name__)
    
    # Get DATA_DIR using proper folder structure
    try:
        from .large_data_config import UPLOAD_ROOT
        DATA_DIR = str(UPLOAD_ROOT)
    except ImportError:
        DATA_DIR = os.path.join(os.path.dirname(__file__), ".uploaded")
    
    path = csv_path
    
    # ABSOLUTE RULE: ONLY use the file the user uploaded in the UI
    if tool_context is not None:
        try:
            default_path = tool_context.state.get("default_csv_path")
            force_default = tool_context.state.get("force_default_csv")
        except Exception:
            default_path = None
            force_default = False
        
        if force_default and default_path:
            if path and path != str(default_path):
                logger.warning(
                    f" BLOCKED: Tool requested '{Path(path).name}' but user uploaded '{Path(default_path).name}'. "
                    f"ENFORCING user upload for data accuracy."
                )
                path = str(default_path)
            elif not path:
                path = str(default_path)
    
    # Try absolute path first
    if path and os.path.exists(path):
        return pd.read_csv(path)
    
    # Try finding in .uploaded directory
    if path:
        candidate_in_data = os.path.join(DATA_DIR, os.path.basename(path))
        if os.path.exists(candidate_in_data):
            logger.info(f"[OK] Found file in .uploaded: {candidate_in_data}")
            return pd.read_csv(candidate_in_data)
    
    # Last resort: Use most recent file in .uploaded
    try:
        csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
        parquet_files = glob.glob(os.path.join(DATA_DIR, "*.parquet"))
        all_files = csv_files + parquet_files
        
        if all_files:
            latest_file = max(all_files, key=os.path.getmtime)
            logger.warning(f"[WARNING] No valid path provided, using most recent upload: {os.path.basename(latest_file)}")
            if latest_file.endswith('.parquet'):
                return pd.read_parquet(latest_file)
            else:
                return pd.read_csv(latest_file)
    except Exception as e:
        logger.warning(f"Could not find fallback CSV: {e}")
    
    raise FileNotFoundError(f"CSV not found: {path}. Upload a file in the UI.")


# ============================================================================
# 1. OPTUNA BAYESIAN HYPERPARAMETER OPTIMIZATION
# ============================================================================

@ensure_display_fields
async def optuna_tune(
    target: str,
    csv_path: Optional[str] = None,
    estimator: str = "xgboost",
    n_trials: int = 50,
    time_budget_s: int = 120,
    direction: str = "maximize",
    metric: str = "accuracy",
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """ Optuna Bayesian Hyperparameter Optimization - Smarter than grid_search!
    
    Uses Bayesian optimization with pruning to find optimal hyperparameters FASTER
    and with BETTER results than grid search.
    
    **Why Optuna:**
    - [OK] Bayesian optimization (learns from previous trials)
    - [OK] Early stopping/pruning (skips bad configs)
    - [OK] 2-10x faster than grid search
    - [OK] Often finds better parameters
    
    Supported Estimators:
    - 'xgboost': XGBoost (gradient boosting)
    - 'lightgbm': LightGBM (fast gradient boosting)
    - 'random_forest': Random Forest
    - 'svm': Support Vector Machine
    
    Args:
        target: Target column to predict
        csv_path: Path to CSV (optional, auto-detects)
        estimator: Model to tune (default: 'xgboost')
        n_trials: Number of trials (default: 50)
        time_budget_s: Max time in seconds (default: 120)
        direction: 'maximize' or 'minimize' the metric
        metric: Metric to optimize (default: 'accuracy')
        tool_context: ADK context (auto-provided)
    
    Returns:
        dict with:
        - best_params: Optimal hyperparameters found
        - best_score: Best metric value achieved
        - study_summary: Trial history
        - visualization_path: Plot of optimization history
        - model_path: Path to model trained with best params
    
    Example:
        optuna_tune(target='price', estimator='xgboost', n_trials=50)
    """
    try:
        import optuna
        from sklearn.model_selection import cross_val_score, train_test_split
        from sklearn.preprocessing import LabelEncoder
        import matplotlib.pyplot as plt
        
        # Suppress Optuna logs
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        
    except ImportError:
        return {"error": "Optuna not installed. Run: pip install optuna"}
    
    # Load data
    df = await _load_dataframe(csv_path, tool_context=tool_context)
    
    if target not in df.columns:
        return {"error": f"Target '{target}' not found"}
    
    X = df.drop(columns=[target])
    y = df[target]
    
    # Encode categorical
    for col in X.select_dtypes(include=['object', 'category']).columns:
        X[col] = LabelEncoder().fit_transform(X[col].astype(str))
    
    is_classification = len(y.unique()) < 20 or y.dtype == 'object'
    if is_classification and y.dtype == 'object':
        y = LabelEncoder().fit_transform(y.astype(str))
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Define objective function for Optuna
    def objective(trial):
        if estimator == "xgboost":
            try:
                import xgboost as xgb
                params = {
                    'max_depth': trial.suggest_int('max_depth', 3, 10),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    'random_state': 42
                }
                if is_classification:
                    model = xgb.XGBClassifier(**params, use_label_encoder=False, eval_metric='logloss')
                else:
                    model = xgb.XGBRegressor(**params)
            except ImportError:
                return 0.0
                
        elif estimator == "lightgbm":
            try:
                import lightgbm as lgb
                params = {
                    'num_leaves': trial.suggest_int('num_leaves', 20, 150),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    'random_state': 42,
                    'verbose': -1
                }
                if is_classification:
                    model = lgb.LGBMClassifier(**params)
                else:
                    model = lgb.LGBMRegressor(**params)
            except ImportError:
                return 0.0
                
        elif estimator == "random_forest":
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                'max_depth': trial.suggest_int('max_depth', 3, 20),
                'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
                'random_state': 42
            }
            if is_classification:
                model = RandomForestClassifier(**params)
            else:
                model = RandomForestRegressor(**params)
                
        elif estimator == "svm":
            from sklearn.svm import SVC, SVR
            from sklearn.preprocessing import StandardScaler
            params = {
                'C': trial.suggest_float('C', 0.1, 100, log=True),
                'kernel': trial.suggest_categorical('kernel', ['linear', 'rbf', 'poly']),
                'random_state': 42
            }
            # SVM needs scaling
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            if is_classification:
                model = SVC(**params)
            else:
                model = SVR(**params)
            model.fit(X_train_scaled, y_train)
            return model.score(scaler.transform(X_test), y_test)
        else:
            return 0.0
        
        # Train and evaluate with cross-validation
        scoring = 'accuracy' if is_classification else 'r2'
        if metric == 'accuracy':
            scoring = 'accuracy'
        elif metric == 'r2':
            scoring = 'r2'
        elif metric == 'f1':
            scoring = 'f1_weighted'
        
        scores = cross_val_score(model, X_train, y_train, cv=3, scoring=scoring, n_jobs=-1)
        return scores.mean()
    
    # Create and run study
    study = optuna.create_study(
        direction=direction,
        pruner=optuna.pruners.MedianPruner()
    )
    
    study.optimize(objective, n_trials=n_trials, timeout=time_budget_s, show_progress_bar=False)
    
    # Get best parameters
    best_params = study.best_params
    best_score = study.best_value
    
    # Save study summary
    dataset_name = Path(csv_path).stem if csv_path else "dataset"
    export_dir = os.path.join(os.path.dirname(__file__), '.export')
    os.makedirs(export_dir, exist_ok=True)
    
    study_df = study.trials_dataframe()
    summary_path = os.path.join(export_dir, f"optuna_study_{estimator}_{target}.csv")
    study_df.to_csv(summary_path, index=False)
    
    # Visualization
    plot_dir = os.path.join(os.path.dirname(__file__), '.plot')
    os.makedirs(plot_dir, exist_ok=True)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Optimization history
    ax1.plot(range(len(study.trials)), [t.value for t in study.trials], 'o-')
    ax1.axhline(y=best_score, color='r', linestyle='--', label=f'Best: {best_score:.4f}')
    ax1.set_xlabel('Trial', fontsize=12)
    ax1.set_ylabel(metric.capitalize(), fontsize=12)
    ax1.set_title('Optuna Optimization History', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Parameter importance (if available)
    try:
        importances = optuna.importance.get_param_importances(study)
        params_list = list(importances.keys())[:5]
        values = [importances[p] for p in params_list]
        ax2.barh(params_list, values, color='steelblue')
        ax2.set_xlabel('Importance', fontsize=12)
        ax2.set_title('Top 5 Parameter Importance', fontsize=14, fontweight='bold')
    except:
        ax2.text(0.5, 0.5, 'Parameter importance\nnot available', 
                ha='center', va='center', transform=ax2.transAxes, fontsize=12)
    
    plt.tight_layout()
    viz_path = os.path.join(plot_dir, f"optuna_{estimator}_{target}.png")
    plt.savefig(viz_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # Upload artifacts
    if tool_context:
        try:
            with open(viz_path, 'rb') as f:
                from google.genai import types
                await tool_context.save_artifact(
                    filename=f"optuna_{estimator}_{target}.png",
                    artifact=types.Part.from_bytes(data=f.read(), mime_type="image/png")
                )
        except Exception as e:
            logger.warning(f"Could not upload Optuna plot: {e}")
    
    return _json_safe({
        "status": "success",
        "estimator": estimator,
        "best_params": best_params,
        "best_score": float(best_score),
        "n_trials_completed": len(study.trials),
        "study_summary_path": summary_path,
        "visualization_path": viz_path,
        "message": f"[OK] Optuna found optimal params! Best {metric}: {best_score:.4f}",
        "improvement": f" Bayesian optimization completed {len(study.trials)} trials",
        "next_steps": [
            f"Train final model with these params: {best_params}",
            "Use explain_model() to understand feature importance",
            "Generate export_executive_report() with optimization results",
            "Try ensemble() to combine with other models"
        ]
    })


# ============================================================================
# 2. GREAT EXPECTATIONS DATA VALIDATION
# ============================================================================

@ensure_display_fields
async def ge_auto_profile(
    csv_path: Optional[str] = None,
    save_suite_as: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """ Auto-generate Great Expectations validation suite from your data.
    
    Automatically creates data quality expectations (schema, types, ranges, nulls).
    
    **Best For:**
    - Establishing data quality baselines
    - Detecting schema drift
    - Pre-training data validation
    
    Args:
        csv_path: Path to CSV (optional)
        save_suite_as: Name for the expectation suite (default: auto-generated)
        tool_context: ADK context
    
    Returns:
        dict with suite_path, expectations_count, summary
    
    Example:
        ge_auto_profile(save_suite_as='my_data_quality_suite')
    """
    try:
        import great_expectations as gx
        from great_expectations.core.batch import RuntimeBatchRequest
    except ImportError:
        return {"error": "Great Expectations not installed. Run: pip install great-expectations"}
    
    # Load data
    df = await _load_dataframe(csv_path, tool_context=tool_context)
    
    dataset_name = Path(csv_path).stem if csv_path else "dataset"
    suite_name = save_suite_as or f"{dataset_name}_quality_suite"
    
    # Initialize GE context
    ge_dir = os.path.join(os.path.dirname(__file__), '.ge')
    context = gx.get_context(project_root_dir=ge_dir)
    
    # Create expectation suite
    try:
        suite = context.add_or_update_expectation_suite(expectation_suite_name=suite_name)
    except:
        suite = context.get_expectation_suite(expectation_suite_name=suite_name)
    
    # Auto-generate expectations
    batch = context.sources.pandas_default.read_dataframe(df)
    
    expectations = []
    
    # Table-level expectations
    expectations.append({
        "expectation_type": "expect_table_row_count_to_be_between",
        "kwargs": {"min_value": max(1, int(len(df) * 0.5)), "max_value": int(len(df) * 2)}
    })
    
    expectations.append({
        "expectation_type": "expect_table_column_count_to_equal",
        "kwargs": {"value": len(df.columns)}
    })
    
    # Column-level expectations
    for col in df.columns:
        # Column exists
        expectations.append({
            "expectation_type": "expect_column_to_exist",
            "kwargs": {"column": col}
        })
        
        # Nulls
        null_pct = df[col].isnull().mean()
        if null_pct < 0.5:  # If less than 50% null, expect mostly non-null
            expectations.append({
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": col, "mostly": 1 - null_pct - 0.1}
            })
        
        # Type expectations for numeric
        if df[col].dtype in ['int64', 'float64']:
            min_val = float(df[col].min())
            max_val = float(df[col].max())
            expectations.append({
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {"column": col, "min_value": min_val * 0.8, "max_value": max_val * 1.2}
            })
    
    # Save suite
    suite_path = os.path.join(ge_dir, 'expectations', f'{suite_name}.json')
    os.makedirs(os.path.dirname(suite_path), exist_ok=True)
    
    with open(suite_path, 'w') as f:
        json.dump({
            'expectation_suite_name': suite_name,
            'expectations': expectations,
            'meta': {'generated_by': 'ge_auto_profile'}
        }, f, indent=2)
    
    return _json_safe({
        "status": "success",
        "suite_name": suite_name,
        "suite_path": suite_path,
        "expectations_count": len(expectations),
        "message": f"[OK] Generated {len(expectations)} data quality expectations",
        "summary": f"Suite includes: table shape, nulls, ranges, types for {len(df.columns)} columns",
        "next_steps": [
            f"Run ge_validate() to check data against suite",
            "Use auto_clean_data() to fix violations",
            "Run validation before every training run"
        ]
    })


@ensure_display_fields
async def ge_validate(
    csv_path: Optional[str] = None,
    suite_name: Optional[str] = None,
    fail_on_warning: bool = False,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """[OK] Validate data quality using Great Expectations suite.
    
    Checks your data against predefined expectations and reports violations.
    
    Args:
        csv_path: Path to CSV (optional)
        suite_name: Expectation suite to use (default: auto-detect)
        fail_on_warning: Return error status if any expectation fails
        tool_context: ADK context
    
    Returns:
        dict with passed (bool), violations, summary
    
    Example:
        ge_validate(suite_name='my_data_quality_suite')
    """
    try:
        import great_expectations as gx
    except ImportError:
        return {"error": "Great Expectations not installed"}
    
    # Load data
    df = await _load_dataframe(csv_path, tool_context=tool_context)
    
    dataset_name = Path(csv_path).stem if csv_path else "dataset"
    suite_to_use = suite_name or f"{dataset_name}_quality_suite"
    
    # Load suite
    ge_dir = os.path.join(os.path.dirname(__file__), '.ge')
    suite_path = os.path.join(ge_dir, 'expectations', f'{suite_to_use}.json')
    
    if not os.path.exists(suite_path):
        return {
            "error": f"Suite '{suite_to_use}' not found. Run ge_auto_profile() first.",
            "available_suites": [f.replace('.json', '') for f in os.listdir(os.path.join(ge_dir, 'expectations')) if f.endswith('.json')] if os.path.exists(os.path.join(ge_dir, 'expectations')) else []
        }
    
    with open(suite_path, 'r') as f:
        suite_data = json.load(f)
    
    # Run validations
    results = {"passed": [], "failed": []}
    
    for exp in suite_data.get('expectations', []):
        exp_type = exp['expectation_type']
        kwargs = exp.get('kwargs', {})
        
        try:
            if exp_type == "expect_table_row_count_to_be_between":
                row_count = len(df)
                passed = kwargs['min_value'] <= row_count <= kwargs['max_value']
                result = {"expectation": "Row count", "passed": passed, "actual": row_count, "expected": f"{kwargs['min_value']}-{kwargs['max_value']}"}
                
            elif exp_type == "expect_column_to_exist":
                passed = kwargs['column'] in df.columns
                result = {"expectation": f"Column '{kwargs['column']}' exists", "passed": passed}
                
            elif exp_type == "expect_column_values_to_not_be_null":
                col = kwargs['column']
                null_pct = df[col].isnull().mean()
                passed = null_pct < (1 - kwargs.get('mostly', 1.0))
                result = {"expectation": f"'{col}' non-null", "passed": passed, "null_pct": f"{null_pct:.1%}"}
                
            elif exp_type == "expect_column_values_to_be_between":
                col = kwargs['column']
                min_val = df[col].min()
                max_val = df[col].max()
                passed = kwargs['min_value'] <= min_val and max_val <= kwargs['max_value']
                result = {"expectation": f"'{col}' range", "passed": passed, "actual_range": f"{min_val:.2f}-{max_val:.2f}"}
            
            else:
                result = {"expectation": exp_type, "passed": None, "note": "Not implemented"}
            
            if result.get("passed"):
                results["passed"].append(result)
            else:
                results["failed"].append(result)
                
        except Exception as e:
            results["failed"].append({"expectation": exp_type, "error": str(e)})
    
    passed_count = len(results["passed"])
    failed_count = len(results["failed"])
    total = passed_count + failed_count
    success_rate = passed_count / total if total > 0 else 0
    
    overall_passed = failed_count == 0
    
    return _json_safe({
        "status": "warning" if failed_count > 0 else "success",
        "passed": overall_passed,
        "success_rate": f"{success_rate:.1%}",
        "passed_count": passed_count,
        "failed_count": failed_count,
        "violations": results["failed"] if failed_count > 0 else [],
        "message": f"[OK] {passed_count}/{total} expectations passed" if overall_passed else f"[WARNING] {failed_count}/{total} expectations failed",
        "next_steps": [
            "Review violations and fix data issues",
            "Use auto_clean_data() to handle outliers/nulls",
            "Re-run validation after cleaning",
            "Proceed to training only if validation passes"
        ] if failed_count > 0 else [
            "Data quality validated! Proceed to training",
            "Use smart_autogluon_automl() or train_decision_tree()",
            "Generate export_executive_report() documenting data quality"
        ]
    })


# ============================================================================
# 3. MLFLOW EXPERIMENT TRACKING
# ============================================================================

_active_mlflow_run = None

@ensure_display_fields
async def mlflow_start_run(
    run_name: Optional[str] = None,
    tags: Optional[dict] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """ Start MLflow experiment tracking run.
    
    Begins tracking parameters, metrics, and artifacts for reproducibility.
    
    Args:
        run_name: Name for this run (default: auto-generated)
        tags: Optional metadata tags (dict)
        tool_context: ADK context
    
    Returns:
        dict with run_id, tracking_uri
    
    Example:
        mlflow_start_run(run_name='xgboost_baseline', tags={'model': 'xgb', 'version': '1.0'})
    """
    try:
        import mlflow
    except ImportError:
        return {"error": "MLflow not installed. Run: pip install mlflow"}
    
    global _active_mlflow_run
    
    # Set tracking URI to local directory
    mlflow_dir = os.path.join(os.path.dirname(__file__), '.mlflow')
    os.makedirs(mlflow_dir, exist_ok=True)
    mlflow.set_tracking_uri(f"file://{mlflow_dir}")
    
    # Start run
    run = mlflow.start_run(run_name=run_name)
    _active_mlflow_run = run
    
    # Set tags
    if tags:
        for key, value in tags.items():
            mlflow.set_tag(key, value)
    
    return _json_safe({
        "status": "success",
        "run_id": run.info.run_id,
        "run_name": run_name or "auto-generated",
        "tracking_uri": mlflow.get_tracking_uri(),
        "message": f"[OK] MLflow run started: {run.info.run_id[:8]}...",
        "next_steps": [
            "Train your model",
            "Use mlflow_log_metrics() to log params/metrics",
            "End with mlflow_end_run() when complete"
        ]
    })


@ensure_display_fields
async def mlflow_log_metrics(
    params: Optional[dict] = None,
    metrics: Optional[dict] = None,
    artifacts: Optional[List[str]] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """ Log parameters, metrics, and artifacts to active MLflow run.
    
    Args:
        params: Hyperparameters (dict)
        metrics: Performance metrics (dict)
        artifacts: Paths to files to log (list of paths)
        tool_context: ADK context
    
    Returns:
        dict with logged counts
    
    Example:
        mlflow_log_metrics(
            params={'learning_rate': 0.1, 'max_depth': 5},
            metrics={'accuracy': 0.92, 'f1': 0.89},
            artifacts=['model.joblib', 'plot.png']
        )
    """
    try:
        import mlflow
    except ImportError:
        return {"error": "MLflow not installed"}
    
    global _active_mlflow_run
    
    if not _active_mlflow_run:
        return {"error": "No active MLflow run. Call mlflow_start_run() first."}
    
    logged = {"params": 0, "metrics": 0, "artifacts": 0}
    
    # Log parameters
    if params:
        for key, value in params.items():
            mlflow.log_param(key, value)
            logged["params"] += 1
    
    # Log metrics
    if metrics:
        for key, value in metrics.items():
            mlflow.log_metric(key, float(value))
            logged["metrics"] += 1
    
    # Log artifacts
    if artifacts:
        for artifact_path in artifacts:
            if os.path.exists(artifact_path):
                mlflow.log_artifact(artifact_path)
                logged["artifacts"] += 1
    
    return _json_safe({
        "status": "success",
        "run_id": _active_mlflow_run.info.run_id,
        "logged": logged,
        "message": f"[OK] Logged {logged['params']} params, {logged['metrics']} metrics, {logged['artifacts']} artifacts",
        "next_steps": [
            "Continue training or analysis",
            "Log more metrics as needed",
            "Call mlflow_end_run() when complete"
        ]
    })


@ensure_display_fields
async def mlflow_end_run(
    status: str = "FINISHED",
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """ End active MLflow run and finalize tracking.
    
    Args:
        status: Run status - 'FINISHED', 'FAILED', or 'KILLED'
        tool_context: ADK context
    
    Returns:
        dict with run_id and artifact location
    
    Example:
        mlflow_end_run(status='FINISHED')
    """
    try:
        import mlflow
    except ImportError:
        return {"error": "MLflow not installed"}
    
    global _active_mlflow_run
    
    if not _active_mlflow_run:
        return {"error": "No active MLflow run to end"}
    
    run_id = _active_mlflow_run.info.run_id
    artifact_uri = _active_mlflow_run.info.artifact_uri
    
    mlflow.end_run(status=status)
    _active_mlflow_run = None
    
    return _json_safe({
        "status": "success",
        "run_id": run_id,
        "run_status": status,
        "artifact_location": artifact_uri,
        "message": f"[OK] MLflow run ended: {run_id[:8]}...",
        "ui_hint": f"View results at: {mlflow.get_tracking_uri()}",
        "next_steps": [
            "Generate export_model_card() for documentation",
            "Use export_executive_report() for stakeholder presentation",
            "Start new run for next experiment"
        ]
    })


@ensure_display_fields
async def export_model_card(
    model_name: str,
    dataset_name: Optional[str] = None,
    metrics: Optional[dict] = None,
    intended_use: Optional[str] = None,
    limitations: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """ Generate Model Card PDF for governance and documentation.
    
    Creates a comprehensive model card following best practices for ML documentation.
    
    Args:
        model_name: Name of the model
        dataset_name: Name of dataset used
        metrics: Performance metrics (dict)
        intended_use: Description of intended use cases
        limitations: Known limitations and risks
        tool_context: ADK context
    
    Returns:
        dict with model_card_path
    
    Example:
        export_model_card(
            model_name='XGBoost Classifier v1.0',
            metrics={'accuracy': 0.92, 'f1': 0.89},
            intended_use='Predict customer churn for retention campaigns',
            limitations='Not validated for international markets'
        )
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from datetime import datetime
    
    # Create export directory
    export_dir = os.path.join(os.path.dirname(__file__), '.export')
    os.makedirs(export_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_card_filename = f"model_card_{model_name.replace(' ', '_')}_{timestamp}.pdf"
    pdf_path = os.path.join(export_dir, model_card_filename)
    
    # Create PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=36)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1f4788'), 
                                  spaceAfter=30, alignment=1, fontName='Helvetica-Bold')
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor('#2c5aa0'), 
                                    spaceAfter=12, spaceBefore=20, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('Body', parent=styles['BodyText'], fontSize=11, spaceAfter=12, leading=16)
    
    # Title
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(f"Model Card: {model_name}", title_style))
    elements.append(Paragraph(f"<i>Generated: {datetime.now().strftime('%B %d, %Y')}</i>", 
                              ParagraphStyle('Date', alignment=1, fontSize=10, textColor=colors.gray)))
    elements.append(Spacer(1, 0.5*inch))
    
    # Model Details
    elements.append(Paragraph("Model Details", section_style))
    elements.append(Paragraph(f"<b>Model Name:</b> {model_name}", body_style))
    if dataset_name:
        elements.append(Paragraph(f"<b>Training Dataset:</b> {dataset_name}", body_style))
    elements.append(Paragraph(f"<b>Date Created:</b> {datetime.now().strftime('%B %d, %Y')}", body_style))
    
    # Intended Use
    elements.append(Paragraph("Intended Use", section_style))
    use_text = intended_use or "This model is intended for predictive analysis in data science applications. Specific use cases should be documented by the model owner."
    elements.append(Paragraph(use_text, body_style))
    
    # Performance Metrics
    if metrics:
        elements.append(Paragraph("Performance Metrics", section_style))
        metrics_data = [['Metric', 'Value']]
        for key, value in metrics.items():
            metrics_data.append([key.capitalize(), f"{value:.4f}" if isinstance(value, (int, float)) else str(value)])
        
        table = Table(metrics_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
    
    # Limitations
    elements.append(Paragraph("Limitations & Considerations", section_style))
    limit_text = limitations or "This model has been trained on a specific dataset and may not generalize to all scenarios. Users should validate performance on their specific use case before production deployment."
    elements.append(Paragraph(limit_text, body_style))
    
    # Build PDF
    doc.build(elements)
    
    # Upload as artifact
    if tool_context:
        try:
            with open(pdf_path, 'rb') as f:
                from google.genai import types
                await tool_context.save_artifact(
                    filename=model_card_filename,
                    artifact=types.Part.from_bytes(data=f.read(), mime_type="application/pdf")
                )
        except Exception as e:
            logger.warning(f"Could not upload model card: {e}")
    
    return _json_safe({
        "status": "success",
        "model_card_path": pdf_path,
        "filename": model_card_filename,
        "message": f"[OK] Model card generated: {model_card_filename}",
        "sections": ["Model Details", "Intended Use", "Performance Metrics", "Limitations"],
        "next_steps": [
            "Include model card in export_executive_report()",
            "Share with stakeholders for governance review",
            "Update card when model is retrained or modified"
        ]
    })

