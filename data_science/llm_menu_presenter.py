"""
LLM-driven tool menu presenter for EDA-first workflow.
Makes EDA Step 1 and provides comprehensive, stage-aware tool recommendations.
"""
import logging
from typing import Dict, Any, List, Optional
from google.adk.agents.callback_context import CallbackContext

logger = logging.getLogger(__name__)

def _get_llm_model():
    """Get the LLM model for menu generation."""
    try:
        from google.genai import types as gen_types
        from google.genai import Client
        return Client()
    except Exception:
        return None

def _llm_present_tool_menu(llm, stage: str, dataset_profile: dict, available_tools: list[str]) -> str:
    """
    Use LLM to render a comprehensive, stage-aware menu of ALL tools grouped by steps.
    EDA is Step 1. The LLM explains why each bucket matters and suggests top picks.
    """
    # Compact inventory by category (kept explicit for clarity & control)
    tool_buckets = {
        "1⃣ EDA (Step 1)": [
            "analyze_dataset", "describe", "plot", "stats", "anomaly", "anova", "inference",
            "polars_profile", "duckdb_query", "ttest_ind_tool", "ttest_rel_tool", "mannwhitney_tool",
            "pearson_corr_tool", "spearman_corr_tool", "shapiro_normality_tool"
        ],
        "2⃣ Data Cleaning / Preprocessing": [
            "robust_auto_clean_file", "auto_clean_data", "impute_simple", "impute_knn", "impute_iterative",
            "ge_auto_profile", "ge_validate", "data_quality_report", "scale_data", "encode_data",
            "auto_impute_orchestrator_adk"
        ],
        "3⃣ Feature Engineering": [
            "auto_feature_synthesis", "expand_features", "select_features", "recursive_select", "sequential_select",
            "apply_pca", "feature_importance_stability", "text_to_features", "embed_text_column",
            "target_encode_tool", "leakage_check_tool"
        ],
        "4⃣ Splitting": ["split_data"],
        "5⃣ Modeling (Classic + AutoML)": [
            "recommend_model", "train_baseline_model", "train_classifier", "train_regressor",
            "train_decision_tree", "train_knn", "train_naive_bayes", "train_svm",
            "smart_autogluon_automl", "auto_sklearn_classify", "auto_sklearn_regress", "ensemble",
            "train_lightgbm_classifier", "train_xgboost_classifier", "train_catboost_classifier"
        ],
        "6⃣ Evaluation, Explainability, Fairness & Drift": [
            "accuracy", "evaluate", "explain_model", "fairness_report", "fairness_mitigation_grid",
            "drift_profile", "data_quality_report", "permutation_importance_tool", "partial_dependence_tool",
            "ice_plot_tool", "shap_interaction_values_tool", "lime_explain_tool", "threshold_tune_tool"
        ],
        "7⃣ Optimization": [
            "optuna_tune", "grid_search", "rebalance_fit", "calibrate_probabilities",
            "smote_rebalance_tool", "cost_sensitive_learning_tool"
        ],
        "8⃣ Reporting, Cards & Governance": [
            "export_executive_report", "export", "export_model_card"
        ],
        "9⃣ Production, Monitoring & Versioning": [
            "mlflow_start_run", "mlflow_log_metrics", "mlflow_end_run",
            "monitor_drift_fit", "monitor_drift_score", "dvc_init_local", "dvc_track",
            "export_onnx_tool", "onnx_runtime_infer_tool"
        ],
        " Unstructured / Text / Email": [
            "extract_text", "chunk_text", "embed_and_index", "semantic_search",
            "summarize_chunks", "classify_text", "ingest_mailbox", "vector_search",
            "lda_topic_model_tool", "spacy_ner_tool", "sentiment_vader_tool"
        ],
        " Advanced / Time Series / Fast EDA": [
            "ts_prophet_forecast", "ts_backtest", "duckdb_query", "polars_profile", "smart_autogluon_timeseries",
            "smart_cluster", "kmeans_cluster", "dbscan_cluster", "hierarchical_cluster", "isolation_forest_train",
            "arima_forecast_tool", "sarimax_forecast_tool", "adf_stationarity_tool", "kpss_stationarity_tool"
        ],
        " Statistical Inference & ANOVA": [
            "anova_oneway_tool", "anova_twoway_tool", "tukey_hsd_tool", "wilcoxon_tool", "kruskal_wallis_tool",
            "chisq_independence_tool", "proportions_ztest_tool", "mcnemar_tool", "cochran_q_tool",
            "kendall_corr_tool", "anderson_darling_tool", "jarque_bera_tool", "levene_homoskedasticity_tool",
            "bartlett_homoskedasticity_tool", "cohens_d_tool", "hedges_g_tool", "eta_squared_tool",
            "omega_squared_tool", "cliffs_delta_tool", "ci_mean_tool", "power_ttest_tool", "power_anova_tool",
            "vif_tool", "breusch_pagan_tool", "white_test_tool", "durbin_watson_tool",
            "bonferroni_correction_tool", "benjamini_hochberg_fdr_tool"
        ],
        "[ALERT] Anomaly Detection": [
            "lof_anomaly_tool", "oneclass_svm_anomaly_tool"
        ],
        " Association Rules": [
            "association_rules_tool"
        ],
        "ℹ Utilities": [
            "list_data_files", "discover_datasets", "list_available_models", "help"
        ]
    }

    # Filter by actually registered tools (defensive)
    available_set = set(available_tools)
    for k in list(tool_buckets.keys()):
        tool_buckets[k] = [t for t in tool_buckets[k] if t in available_set]
        if not tool_buckets[k]:
            del tool_buckets[k]

    # Build prompt
    prompt = f"""
You are a senior data-science guide. EDA is **Step 1**.
Render a concise, numbered, stage-aware menu of ALL available tools grouped by steps.
Use the dataset profile (if any) and the current stage to recommend top picks.
Always show:
- What each bucket is for
- When to use it
- 3–5 recommended next actions with exact tool calls and suggested parameters

Current stage: {stage}
Dataset profile (may be empty): {dataset_profile}

Available tool buckets and members:
{ {k: v for k, v in tool_buckets.items()} }

Output format:
- A short intro stating that Step 1 is File Discovery (list_data_files), Step 2 is EDA (analyze_dataset)
- For each bucket: title line + one-sentence purpose + comma-separated tools
- A "Recommended Next Actions" section (numbered) with concrete calls
- Keep it compact and execution-oriented
    """.strip()

    try:
        if llm:
            return llm.generate_content(prompt).text
    except Exception:
        pass
    
    # Fallback: a simple deterministic text if LLM is unavailable
    lines = ["Step 1 = File Discovery (list_data_files), Step 2 = EDA (analyze_dataset). Full tool menu:"]
    for k, v in tool_buckets.items():
        lines.append(f"- {k}: {', '.join(v)}")
    lines.append("\nRecommended Next Actions:\n1. list_data_files()\n2. analyze_dataset()\n2. describe()\n3. plot(kind='correlation')")
    return "\n".join(lines)

def present_full_tool_menu(callback_context: CallbackContext = None) -> dict:
    """
    Presents the LLM-rendered full-stage tool menu. Makes EDA the first step.
    Uses context to include dataset profile (shape, target guess, etc.) when available.
    """
    try:
        llm = _get_llm_model()
        stage = (callback_context.state.get("current_stage") if callback_context and hasattr(callback_context, "state") else None) or "EDA"
        profile = (callback_context.state.get("dataset_profile") if callback_context and hasattr(callback_context, "state") else None) or {}
        
        # Discover actually-registered tools on this agent
        available = []
        try:
            from .agent import root_agent
            available = [t.func.__name__ for t in getattr(root_agent, "tools", [])]
        except Exception:
            pass
            
        rendered = _llm_present_tool_menu(llm, stage, profile, available)
        return {"status": "success", "menu": rendered}
    except Exception as e:
        return {"status": "failed", "error": str(e), "menu": "Menu unavailable. Try again."}

def _bootstrap_step1_and_menu(callback_context: CallbackContext):
    """
    Runs Step 1 (EDA) automatically when we can (dataset present) and then presents the full tool menu.
    Saves a compact profile in state for better LLM recommendations.
    """
    try:
        # Only run once per session
        if callback_context.state.get("_bootstrapped"):
            return
        callback_context.state["_bootstrapped"] = True

        # If a CSV was uploaded, prepare for analysis (but don't auto-run to avoid timing issues)
        # Instead, suggest it as the next step in the UI
        try:
            # Check if a file was uploaded
            default_csv_path = callback_context.state.get("default_csv_path")
            if default_csv_path:
                # File uploaded - set stage and suggest next action
                callback_context.state["current_stage"] = "EDA"
                callback_context.state["suggested_next_action"] = "list_data_files"
                callback_context.state["dataset_profile"] = {}
                
                # Log the suggestion
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[BOOTSTRAP] File uploaded: {default_csv_path}. Suggesting list_data_files as Step 1, then analyze_dataset as Step 2.")
            else:
                # No dataset yet, we still show a global menu
                callback_context.state.setdefault("dataset_profile", {})
                callback_context.state.setdefault("current_stage", "EDA")
        except Exception:
            # Even if there is no dataset yet, we still show a global menu
            callback_context.state.setdefault("dataset_profile", {})
            callback_context.state.setdefault("current_stage", "EDA")

        # Show the LLM-composed full menu
        try:
            menu_payload = present_full_tool_menu(callback_context)
            # Surface to UI as an artifact so users see it immediately
            if hasattr(callback_context, "save_artifact") and menu_payload.get("menu"):
                from google.genai import types as gen_types
                callback_context.save_artifact("full_tool_menu.txt", gen_types.Part.from_text(menu_payload["menu"]))
        except Exception:
            pass
    except Exception:
        pass

def route_user_intent(action: str = "", params: dict = None, callback_context: CallbackContext = None) -> dict:
    """
    Execute a requested tool from the menu with smart defaults.
    Example: {"action": "train_classifier", "params": {"target": "label"}}
    """
    try:
        params = params or {}
        # Get registered tools
        try:
            from .agent import root_agent
            registered = {t.func.__name__: t for t in getattr(root_agent, "tools", [])}
        except Exception:
            return {"status": "failed", "error": "Could not access registered tools"}
            
        if action not in registered:
            return {"status": "failed", "error": f"Unknown action: {action}"}

        # Smart defaults per category (extend as needed)
        if action in ("plot",):
            params.setdefault("kind", "correlation")
        if action in ("smart_autogluon_automl",):
            params.setdefault("time_limit", 60)
            params.setdefault("presets", "medium_quality")
        if action in ("optuna_tune",):
            params.setdefault("n_trials", 25)
        if action in ("split_data",):
            params.setdefault("test_size", 0.2)
            params.setdefault("random_state", 42)
        if action in ("train_lightgbm_classifier","train_xgboost_classifier","train_catboost_classifier"):
            params.setdefault("target", params.get("target"))  # user still needs target; keep strict
        if action == "smote_rebalance_tool":
            params.setdefault("strategy", "smote")
        if action == "threshold_tune_tool":
            params.setdefault("metric", "f1")
        if action == "partial_dependence_tool":
            params.setdefault("features", params.get("features") or [])
        if action == "ice_plot_tool":
            if "feature" not in params: return {"status":"failed","error":"Provide 'feature' for ICE"}
        if action in ("arima_forecast_tool","sarimax_forecast_tool"):
            if "target" not in params: return {"status":"failed","error":"Provide 'target' (time series column)"}
            params.setdefault("steps", 12)
        if action == "lda_topic_model_tool":
            if "text_column" not in params: return {"status":"failed","error":"Provide 'text_column'"}
            params.setdefault("n_topics", 10)
        if action == "spacy_ner_tool":
            if "text_column" not in params: return {"status":"failed","error":"Provide 'text_column'"}
            params.setdefault("model", "en_core_web_sm")
        if action == "sentiment_vader_tool":
            if "text_column" not in params: return {"status":"failed","error":"Provide 'text_column'"}
        if action == "association_rules_tool":
            if "transaction_col" not in params: return {"status":"failed","error":"Provide 'transaction_col'"}
            params.setdefault("min_support", 0.01)
            params.setdefault("min_conf", 0.2)
        if action == "export_onnx_tool":
            params.setdefault("model_name", params.get("model_name"))
        if action == "onnx_runtime_infer_tool":
            if "model_path" not in params: return {"status":"failed","error":"Provide 'model_path' (onnx file)"}

        # Execute
        tool = registered[action]
        result = tool.func(**params)  # call the raw function to avoid nested wrappers
        return {"status": "success", "action": action, "result": result}
    except Exception as e:
        return {"status": "failed", "error": str(e), "action": action}


