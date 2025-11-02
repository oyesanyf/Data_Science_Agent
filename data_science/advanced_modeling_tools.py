"""
Advanced modeling tools: GBM family, explainability, imbalance handling, NLP, etc.
20+ tools with safe fallbacks for missing dependencies.
"""
import logging
from typing import Dict, Any, List, Optional
from .ds_tools import ensure_display_fields

logger = logging.getLogger(__name__)

def _lib_missing(name: str) -> dict:
    return {
        "status": "failed",
        "error": f"Optional dependency '{name}' is not installed.",
        "hint": f"pip install {name}  (or its extras) to enable this tool."
    }

# ---------- MODELING (GBM family) ----------
@ensure_display_fields
async def train_lightgbm_classifier(**kwargs) -> dict:
    try:
        import lightgbm as lgb  # noqa
    except Exception:
        return _lib_missing("lightgbm")
    # Delegate to your generic train_classifier if available
    try:
        from .ds_tools import train_classifier
        kwargs.setdefault("estimator", "LightGBM")
        return await train_classifier(**kwargs)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def train_xgboost_classifier(**kwargs) -> dict:
    try:
        import xgboost as xgb  # noqa
    except Exception:
        return _lib_missing("xgboost")
    try:
        from .ds_tools import train_classifier
        kwargs.setdefault("estimator", "XGBoost")
        return await train_classifier(**kwargs)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def train_catboost_classifier(**kwargs) -> dict:
    try:
        import catboost  # noqa
    except Exception:
        return _lib_missing("catboost")
    try:
        from .ds_tools import train_classifier
        kwargs.setdefault("estimator", "CatBoost")
        kwargs.setdefault("allow_categorical", True)
        return await train_classifier(**kwargs)
    except Exception as e:
        return {"status":"failed","error":str(e)}

# ---------- EXPLAINABILITY ----------
@ensure_display_fields
async def permutation_importance_tool(model_name: Optional[str]=None, n_repeats: int=10) -> dict:
    try:
        from sklearn.inspection import permutation_importance
    except Exception:
        return _lib_missing("scikit-learn")
    try:
        from .ds_tools import explain_model
        return await explain_model(method="permutation_importance", model_name=model_name, n_repeats=n_repeats)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def partial_dependence_tool(model_name: Optional[str]=None, features: Optional[List[str]]=None) -> dict:
    try:
        from sklearn.inspection import PartialDependenceDisplay  # noqa
    except Exception:
        return _lib_missing("scikit-learn")
    try:
        from .ds_tools import explain_model
        return await explain_model(method="partial_dependence", model_name=model_name, features=features)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def ice_plot_tool(model_name: Optional[str]=None, feature: Optional[str]=None) -> dict:
    try:
        from sklearn.inspection import PartialDependenceDisplay  # noqa
    except Exception:
        return _lib_missing("scikit-learn")
    try:
        from .ds_tools import explain_model
        return await explain_model(method="ice_plot", model_name=model_name, features=[feature] if feature else None)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def shap_interaction_values_tool(model_name: Optional[str]=None) -> dict:
    try:
        import shap  # noqa
    except Exception:
        return _lib_missing("shap")
    try:
        from .ds_tools import explain_model
        return await explain_model(method="shap_interaction", model_name=model_name)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def lime_explain_tool(model_name: Optional[str]=None, num_features: int=10) -> dict:
    try:
        import lime  # noqa
    except Exception:
        return _lib_missing("lime")
    try:
        from .ds_tools import explain_model
        return await explain_model(method="lime", model_name=model_name, num_features=num_features)
    except Exception as e:
        return {"status":"failed","error":str(e)}

# ---------- IMBALANCE / THRESHOLD ----------
@ensure_display_fields
async def smote_rebalance_tool(strategy: str = "smote", random_state: int = 42) -> dict:
    try:
        from imblearn.over_sampling import SMOTE  # noqa
    except Exception:
        return _lib_missing("imbalanced-learn")
    try:
        from .ds_tools import rebalance_fit
        return await rebalance_fit(method=strategy, random_state=random_state)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def threshold_tune_tool(model_name: Optional[str]=None, metric: str="f1") -> dict:
    try:
        from .ds_tools import evaluate
        return await evaluate(model_name=model_name, optimize_threshold_for=metric)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def cost_sensitive_learning_tool(cost_matrix: Optional[List[List[float]]]=None) -> dict:
    try:
        from .ds_tools import train_classifier
        return await train_classifier(cost_matrix=cost_matrix or [[0,1],[5,0]])
    except Exception as e:
        return {"status":"failed","error":str(e)}

# ---------- FEATURE ENCODING / LEAKAGE ----------
@ensure_display_fields
async def target_encode_tool(columns: Optional[List[str]]=None, smoothing: float=0.3) -> dict:
    try:
        import category_encoders as ce  # noqa
    except Exception:
        return _lib_missing("category-encoders")
    try:
        from .ds_tools import encode_data
        return await encode_data(method="target", columns=columns, smoothing=smoothing)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def leakage_check_tool() -> dict:
    try:
        from .ds_tools import stats
        return await stats(mode="leakage_check")
    except Exception as e:
        return {"status":"failed","error":str(e)}

# ---------- ANOMALY ----------
@ensure_display_fields
async def lof_anomaly_tool(**kwargs) -> dict:
    try:
        from sklearn.neighbors import LocalOutlierFactor  # noqa
    except Exception:
        return _lib_missing("scikit-learn")
    try:
        from .ds_tools import anomaly
        return await anomaly(method="lof", **kwargs)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def oneclass_svm_anomaly_tool(**kwargs) -> dict:
    try:
        from sklearn.svm import OneClassSVM  # noqa
    except Exception:
        return _lib_missing("scikit-learn")
    try:
        from .ds_tools import anomaly
        return await anomaly(method="oneclass_svm", **kwargs)
    except Exception as e:
        return {"status":"failed","error":str(e)}

# ---------- TIME SERIES ----------
@ensure_display_fields
async def arima_forecast_tool(target: str, order: Optional[List[int]] = None, steps: int = 12) -> dict:
    try:
        import statsmodels  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .extended_tools import ts_prophet_forecast
        return await ts_prophet_forecast(target=target, backend="arima", order=order or [1,1,1], steps=steps)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def sarimax_forecast_tool(target: str, order: Optional[List[int]] = None, seasonal_order: Optional[List[int]] = None, steps: int = 12) -> dict:
    try:
        import statsmodels  # noqa
    except Exception:
        return _lib_missing("statsmodels")
    try:
        from .extended_tools import ts_prophet_forecast
        return await ts_prophet_forecast(target=target, backend="sarimax", order=order or [1,1,1], seasonal_order=seasonal_order or [0,0,0,0], steps=steps)
    except Exception as e:
        return {"status":"failed","error":str(e)}

# ---------- NLP ----------
@ensure_display_fields
async def lda_topic_model_tool(text_column: str, n_topics: int=10) -> dict:
    try:
        import gensim  # noqa
    except Exception:
        return _lib_missing("gensim")
    try:
        from .ds_tools import text_to_features
        return await text_to_features(method="lda", text_column=text_column, n_topics=n_topics)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def spacy_ner_tool(text_column: str, model: str="en_core_web_sm") -> dict:
    try:
        import spacy  # noqa
    except Exception:
        return _lib_missing("spacy")
    try:
        from .ds_tools import text_to_features
        return await text_to_features(method="spacy_ner", text_column=text_column, model=model)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def sentiment_vader_tool(text_column: str) -> dict:
    try:
        import nltk  # noqa
    except Exception:
        return _lib_missing("nltk")
    try:
        from .ds_tools import text_to_features
        return await text_to_features(method="vader", text_column=text_column)
    except Exception as e:
        return {"status":"failed","error":str(e)}

# ---------- ASSOCIATION RULES ----------
@ensure_display_fields
async def association_rules_tool(transaction_col: str, min_support: float=0.01, min_conf: float=0.2) -> dict:
    try:
        from mlxtend.frequent_patterns import apriori, association_rules  # noqa
    except Exception:
        return _lib_missing("mlxtend")
    try:
        from .ds_tools import stats
        return await stats(mode="association_rules", transaction_col=transaction_col, min_support=min_support, min_conf=min_conf)
    except Exception as e:
        return {"status":"failed","error":str(e)}

# ---------- EXPORT / RUNTIME ----------
@ensure_display_fields
async def export_onnx_tool(model_name: Optional[str]=None) -> dict:
    try:
        import skl2onnx  # noqa
    except Exception:
        return _lib_missing("skl2onnx")
    try:
        from .ds_tools import export
        return await export(format="onnx", model_name=model_name)
    except Exception as e:
        return {"status":"failed","error":str(e)}

@ensure_display_fields
async def onnx_runtime_infer_tool(model_path: str, **kwargs) -> dict:
    try:
        import onnxruntime as ort  # noqa
    except Exception:
        return _lib_missing("onnxruntime")
    try:
        from .ds_tools import predict
        return await predict(runtime="onnxruntime", model_path=model_path, **kwargs)
    except Exception as e:
        return {"status":"failed","error":str(e)}
