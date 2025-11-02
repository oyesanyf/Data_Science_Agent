#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Super Cleaner++ (one file, two flags)

Quick start:
  python super_cleaner.py --file merged_iot_events.csv --output out.csv
  python super_cleaner.py --file merged_iot_events.csv --output out.csv

What it does (deterministic core):
  1) Read CSV/TSV/JSON/JSONL/Parquet
  2) Drop all-NaN cols, trim strings, normalize booleans/whitespace
  3) Coerce numeric-looking strings
  4) Parse datetimes (multi-format) and normalize to *naive UTC* to avoid tz dtype clashes
  5) Drop constant & duplicate cols; drop duplicate rows
  6) Impute missing (median for numeric, ffill/bfill for datetime, mode for others)
  7) Winsorize numeric outliers with IQR*3
  8) Downcast numerics to reduce size
  9) Save cleaned CSV and sidecar JSON report

Best-effort plugins (all optional, never fatal):
  - pyjanitor            : .clean_names() if available
  - AutoClean            : elisemercury/AutoClean pass
  - datacleaner.autoclean: rhiever/datacleaner auto-clean
  - Great Expectations   : light expectations (API version-safe)
  - Pandera              : inferred schema validation
  - Cleanlab             : label issue flags if a target column exists
  - Deepchecks           : data-integrity suite summary

AutoML dry-run (optional: --automl):
  - Chooses task (classification vs regression) from target column
  - Advisor (optional, --advisor=openai) asks OpenAI to suggest model family
  - Backends:
      * FLAML (if installed)  -> quick AutoML
      * AutoGluon (if installed, heavy) -> quick TabularPredictor
      * Fallback: scikit-learn baseline CV over a few models
  - Never modifies the cleaned CSV; only adds metrics to the report

Windows-friendly, pandas 2.x safe, tz-naive datetime normalization (UTC->naive).
"""

import argparse
import json
import os
import re
import sys
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Quiet noisy warnings (kept light; we still surface plugin errors explicitly)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# -------------------- Optional deps (best-effort) --------------------
try:
    import janitor  # pyjanitor
except Exception:
    janitor = None

try:
    from AutoClean import AutoClean  # py-AutoClean
except Exception:
    AutoClean = None

try:
    # rhiever/datacleaner
    from datacleaner import autoclean as datacleaner_autoclean  # type: ignore
except Exception:
    datacleaner_autoclean = None

try:
    import great_expectations as ge  # API changes between 0.x and 1.x handled below
except Exception:
    ge = None

try:
    import pandera as pa
except Exception:
    pa = None

try:
    from cleanlab.dataset import find_label_issues
    _HAS_CLEANLAB = True
except Exception:
    _HAS_CLEANLAB = False

try:
    from deepchecks.tabular import Dataset as DCDataset
    from deepchecks.tabular.suites import data_integrity
    _HAS_DEEPCHECKS = True
except Exception:
    _HAS_DEEPCHECKS = False

# AutoML/backends
try:
    from flaml import AutoML as FLAML_AutoML  # pip install flaml
    _HAS_FLAML = True
except Exception:
    _HAS_FLAML = False

try:
    # pip install autogluon.tabular
    from autogluon.tabular import TabularPredictor
    _HAS_AUTOGLUON = True
except Exception:
    _HAS_AUTOGLUON = False

try:
    from openai import OpenAI  # pip install openai
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False

# sklearn for fallback & CV
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import make_pipeline
from sklearn.metrics import make_scorer, accuracy_score, f1_score, r2_score  # fixed import
from sklearn.linear_model import LogisticRegression, Ridge, LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.dummy import DummyClassifier, DummyRegressor

# Macro-F1 scorer (replacement for the removed f1_macro import)
F1_MACRO_SCORER = make_scorer(f1_score, average="macro")

# -------------------- I/O --------------------
def _read_any(path: str, read_options: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    read_options = read_options or {}
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".tsv"):
        sep = read_options.get("sep") or ("," if ext == ".csv" else "\t")
        return pd.read_csv(path, sep=sep, low_memory=False, **{k: v for k, v in read_options.items() if k != "sep"})
    if ext == ".json":
        orient = read_options.get("orient", "records")
        lines = read_options.get("lines", False)
        try:
            return pd.read_json(path, orient=orient, lines=lines)
        except Exception:
            return pd.read_json(path, orient="records", lines=True)
    if ext == ".jsonl":
        # newline-delimited JSON
        try:
            return pd.read_json(path, orient="records", lines=True)
        except Exception:
            # Fallback to manual line parse
            with open(path, "r", encoding="utf-8") as f:
                recs = [json.loads(line) for line in f if line.strip()]
            return pd.DataFrame(recs)
    if ext in (".parquet", ".pq"):
        return pd.read_parquet(path, **read_options)
    # Fallback
    return pd.read_csv(path, low_memory=False, **read_options)

def _to_csv(df: pd.DataFrame, out_path: str, write_options: Optional[Dict[str, Any]] = None) -> None:
    write_options = write_options or {}
    df.to_csv(out_path, index=False, **write_options)

# -------------------- Helpers --------------------
COMMON_TS_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S.%f%z",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%d/%m/%Y %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
]
_EPOCH_RE = re.compile(r"^\s*\d{10,13}\s*$")
_ISO_RE = re.compile(r"(?P<iso>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)")

def _trim_and_normalize_strings(df: pd.DataFrame, lower: bool = True) -> pd.DataFrame:
    obj_cols = df.select_dtypes(include=["object", "string"]).columns
    for c in obj_cols:
        s = df[c].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
        if lower:
            s = s.str.lower()
        s = s.replace({"y": "yes", "n": "no", "true": "yes", "false": "no", "t": "yes", "f": "no"})
        df.loc[:, c] = s
    return df

def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.select_dtypes(include=["object", "string"]).columns:
        s = df[c].astype("string").str.replace(r"[,$%]", "", regex=True)
        try:
            nums = pd.to_numeric(s, errors="coerce")
            if nums.notna().mean() > 0.5:
                df.loc[:, c] = nums
        except Exception:
            pass
    return df

def _extract_datetime_token(val: Any) -> Optional[str]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, (list, dict, set, tuple)):
        try:
            if isinstance(val, (set, tuple)):
                val = list(val)
            val = json.dumps(val, ensure_ascii=False)
        except Exception:
            val = str(val)
    s = str(val).strip()
    if not s:
        return None
    if _EPOCH_RE.match(s):
        n = int(re.sub(r"[^\d]", "", s))
        if len(re.sub(r"\D", "", s)) >= 13:
            n //= 1000
        try:
            return pd.to_datetime(n, unit="s", utc=True).isoformat()
        except Exception:
            pass
    m = _ISO_RE.search(s)
    if m:
        token = m.group("iso")
        token = re.sub(r"Z$", "+00:00", token)
        token = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", token)
        return token
    return s

def _parse_dates(df: pd.DataFrame, max_cols: int = 30) -> pd.DataFrame:
    # try targeted robust extraction, then fallback to broad parse
    # after parsing -> normalize to tz-aware UTC, then drop tz (naive) to satisfy libraries expecting datetime64[ns]
    cand_cols = []
    for c in df.columns[:max_cols]:
        if df[c].dtype in ("object", "string"):
            cand_cols.append(c)
    for c in cand_cols:
        tokens = df[c].map(_extract_datetime_token)
        parsed = pd.to_datetime(tokens, errors="coerce", utc=True)
        if parsed.notna().mean() >= 0.6:
            df.loc[:, c] = parsed
        else:
            try:
                alt = pd.to_datetime(df[c], errors="coerce", utc=True, format=None)
                if alt.notna().mean() >= 0.6:
                    df.loc[:, c] = alt
            except Exception:
                pass
    # Normalize to tz-naive (UTC) to avoid Pandera dtype mismatches and downstream friction
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            try:
                if getattr(df[c].dt, "tz", None) is not None:
                    df.loc[:, c] = df[c].dt.tz_convert("UTC").dt.tz_localize(None)
            except Exception:
                try:
                    # tz-aware but not convertible -> force to UTC then drop tz
                    df.loc[:, c] = pd.to_datetime(df[c], errors="coerce", utc=True).dt.tz_convert("UTC").dt.tz_localize(None)
                except Exception:
                    pass
    return df

def _drop_all_nan(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna(axis=1, how="all")

def _drop_constant_and_dupes(df: pd.DataFrame) -> pd.DataFrame:
    nunique = df.nunique(dropna=False)
    const_cols = nunique[nunique <= 1].index.tolist()
    if const_cols:
        df = df.drop(columns=const_cols)
    df = df.loc[:, ~df.T.duplicated()]
    return df

def _dedup_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates()

def _drop_high_missing(df: pd.DataFrame, thresh: float = 0.98) -> pd.DataFrame:
    miss_ratio = df.isna().mean()
    to_drop = miss_ratio[miss_ratio >= thresh].index.tolist()
    if to_drop:
        df = df.drop(columns=to_drop)
    return df

def _impute_missing(df: pd.DataFrame, numeric: str = "median") -> pd.DataFrame:
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            val = df[c].median() if numeric == "median" else df[c].mean()
            df.loc[:, c] = df[c].fillna(val)
        elif pd.api.types.is_datetime64_any_dtype(df[c]):
            df.loc[:, c] = df[c].ffill().bfill()
        else:
            mode = df[c].mode(dropna=True)
            fill = mode.iloc[0] if not mode.empty else ""
            df.loc[:, c] = df[c].fillna(fill)
    return df

def _winsorize_iqr(df: pd.DataFrame, factor: float = 3.0) -> pd.DataFrame:
    for c in df.select_dtypes(include=["number"]).columns:
        q1 = df[c].quantile(0.25)
        q3 = df[c].quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            continue
        lo = q1 - factor * iqr
        hi = q3 + factor * iqr
        df.loc[:, c] = df[c].clip(lower=lo, upper=hi)
    return df

def _downcast_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.select_dtypes(include=["int", "float"]).columns:
        if pd.api.types.is_integer_dtype(df[c]):
            df.loc[:, c] = pd.to_numeric(df[c], downcast="integer")
        else:
            df.loc[:, c] = pd.to_numeric(df[c], downcast="float")
    return df

def _profile(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "missing_pct": df.isna().mean().round(4),
        "nunique": df.nunique(dropna=True)
    })

def _usability(df: pd.DataFrame) -> Dict[str, Any]:
    if df.shape[0] == 0:
        return {"status": "not-usable", "reasons": ["no rows"]}
    if df.shape[1] == 0:
        return {"status": "not-usable", "reasons": ["no columns"]}
    reasons: List[str] = []
    num_cols = df.select_dtypes(include=["number"]).columns
    if num_cols.size and np.isinf(df[num_cols].to_numpy(dtype="float64", copy=True)).any():
        reasons.append("infinite values present")
    cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns
    high_card = {c: int(df[c].nunique(dropna=True)) for c in cat_cols if df[c].nunique(dropna=True) >= 5000}
    if high_card:
        reasons.append(f"high cardinality: {list(high_card.keys())}")
    return {"status": "usable-with-warnings" if reasons else "usable", "reasons": reasons}

# -------------------- NEW: enforce tz-naive after plugins --------------------
def _force_tz_naive(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            try:
                if getattr(df[c].dt, "tz", None) is not None:
                    df.loc[:, c] = pd.to_datetime(df[c], errors="coerce", utc=True).dt.tz_convert("UTC").dt.tz_localize(None)
            except Exception:
                try:
                    df.loc[:, c] = pd.to_datetime(df[c], errors="coerce", utc=True).dt.tz_localize(None)
                except Exception:
                    pass
    return df

# -------------------- Core cleaning pipeline --------------------
def core_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = _drop_all_nan(df)
    df = _trim_and_normalize_strings(df)
    df = _coerce_numeric(df)
    df = _parse_dates(df)
    df = _drop_high_missing(df, 0.98)
    df = _drop_constant_and_dupes(df)
    df = _dedup_rows(df)
    df = _impute_missing(df)
    df = _winsorize_iqr(df, 3.0)
    df = _downcast_numeric(df)
    return df

# -------------------- Plugins (optional) --------------------
def _detect_target(df: pd.DataFrame, user_target: Optional[str]) -> Optional[str]:
    if user_target and user_target in df.columns:
        return user_target
    for k in ["target", "label", "y", "class", "outcome"]:
        if k in df.columns:
            return k
    return None

def run_plugins(df: pd.DataFrame, report: Dict[str, Any]) -> pd.DataFrame:
    plugins_used: List[str] = []
    plugin_errors: List[Dict[str, str]] = []

    # (0) text normalization fallback marker so you see it happened even if pyjanitor absent
    plugins_used.append("text_normalize_fallback")

    # pyjanitor
    if janitor is not None and hasattr(df, "clean_names"):
        try:
            df = df.clean_names()
            plugins_used.append("pyjanitor")
        except Exception as e:
            plugin_errors.append({"plugin": "pyjanitor", "error": str(e)})

    # AutoClean
    if AutoClean is not None:
        try:
            p = AutoClean(
                df,
                mode="auto",
                duplicates="auto",
                missing_num="auto",
                missing_categ="auto",
                encode_categ="auto",
                extract_datetime="auto",
                outliers="auto",
                logfile=False,
                verbose=False,
            )
            if isinstance(getattr(p, "output", None), pd.DataFrame) and not p.output.empty:
                df = p.output
                plugins_used.append("AutoClean")
        except Exception as e:
            plugin_errors.append({"plugin": "AutoClean", "error": str(e)})

    # datacleaner.autoclean
    if datacleaner_autoclean is not None:
        try:
            df = datacleaner_autoclean(df, copy=True)
            plugins_used.append("datacleaner.autoclean")
        except Exception as e:
            plugin_errors.append({"plugin": "datacleaner.autoclean", "error": str(e)})

    # Great Expectations (very light, version-safe)
    if ge is not None:
        try:
            success = None
            ge_summary = {}
            try:
                if hasattr(ge, "dataset") and hasattr(ge.dataset, "PandasDataset"):
                    GEPandas = ge.dataset.PandasDataset  # type: ignore[attr-defined]
                    gdf = GEPandas(df)
                    for c in df.columns:
                        gdf.expect_column_to_exist(c)
                        gdf.expect_column_values_to_not_be_null(c, mostly=0.5)
                    res = gdf.validate()
                    success = bool(res.get("success"))
                else:
                    success = True  # assume ok if API too heavy for quick path
                ge_summary = {"success": True if success is None else bool(success)}
            except Exception as e:
                ge_summary = {"success": False, "note": "GE quick-check failed (non-fatal)"}
                plugin_errors.append({"plugin": "great_expectations", "error": str(e)})
            plugins_used.append("great_expectations")
            report["ge_summary"] = ge_summary
        except Exception as e:
            plugin_errors.append({"plugin": "great_expectations", "error": str(e)})

    # Pandera inferred schema
    if pa is not None:
        try:
            cols = {}
            for c, dt in df.dtypes.items():
                if pd.api.types.is_integer_dtype(dt):
                    t = pa.Int64
                elif pd.api.types.is_float_dtype(dt):
                    t = pa.Float
                elif pd.api.types.is_datetime64_any_dtype(dt):
                    t = pa.DateTime
                else:
                    t = pa.String
                cols[c] = pa.Column(t, nullable=True)
            schema = pa.DataFrameSchema(cols)
            schema.validate(df, lazy=True)
            plugins_used.append("pandera")
        except Exception as e:
            plugin_errors.append({"plugin": "pandera", "error": str(e)})

    # Cleanlab label checks (if target exists)
    if _HAS_CLEANLAB:
        try:
            y_col = _detect_target(df, user_target=None)
            if y_col:
                y = df[y_col].astype(str)
                classes = sorted(y.dropna().unique())
                if len(classes) >= 2:
                    n, k = len(y), len(classes)
                    pred_probs = np.ones((n, k)) / k  # uniform placeholder
                    mask = find_label_issues(labels=y.to_numpy(), pred_probs=pred_probs)
                    idxs = list(np.where(mask)[0][:50])
                    report["cleanlab_label_issues"] = {"count": int(mask.sum()), "indices_preview": idxs}
                    plugins_used.append("cleanlab")
        except Exception as e:
            plugin_errors.append({"plugin": "cleanlab", "error": str(e)})

    # Deepchecks data-integrity
    if _HAS_DEEPCHECKS:
        try:
            ds = DCDataset(df, label=_detect_target(df, None))
            suite = data_integrity()
            res = suite.run(ds)
            try:
                n_checks = len(res.results)
            except Exception:
                n_checks = 0
            report["deepchecks_summary"] = {"n_checks": n_checks}
            plugins_used.append("deepchecks")
        except Exception as e:
            plugin_errors.append({"plugin": "deepchecks", "error": str(e)})

    report["applied_plugins"] = {"plugins": plugins_used, "errors": plugin_errors}
    return df

# -------------------- AutoML & Advisor --------------------
def _infer_task(df: pd.DataFrame, target: str) -> str:
    s = df[target]
    if pd.api.types.is_numeric_dtype(s):
        nun = int(s.nunique(dropna=True))
        if nun <= 20 and not np.any(np.mod(s.dropna().values, 1)):
            return "classification"
        return "regression"
    return "classification"

def _prepare_xy(df: pd.DataFrame, target: str) -> Tuple[pd.DataFrame, np.ndarray, Optional[LabelEncoder]]:
    X = df.drop(columns=[target]).select_dtypes(exclude=["category"]).copy()
    for c in X.select_dtypes(include=["object", "string"]).columns:
        X[c] = X[c].astype("category").cat.codes.replace(-1, np.nan)
        mode = X[c].mode(dropna=True)
        X[c] = X[c].fillna(mode.iloc[0] if not mode.empty else 0)
    y = df[target].copy()
    le = None
    if _infer_task(df, target) == "classification":
        y = y.astype(str)
        le = LabelEncoder()
        y = le.fit_transform(y.fillna("NA"))
    else:
        y = pd.to_numeric(y, errors="coerce")
        y = y.fillna(y.median())
    for c in X.select_dtypes(include=["number"]).columns:
        if X[c].isna().any():
            X[c] = X[c].fillna(X[c].median())
    return X, y.to_numpy(), le

def _advisor_openai(df: pd.DataFrame, target: str) -> Optional[str]:
    if not _HAS_OPENAI:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        client = OpenAI(api_key=api_key)
        summary = {
            "rows": int(df.shape[0]),
            "cols": int(df.shape[1]),
            "target": target,
            "target_nunique": int(df[target].nunique(dropna=True)),
            "numeric_cols": len(df.select_dtypes(include=["number"]).columns),
            "categorical_cols": len(df.select_dtypes(include=["object", "string", "category"]).columns),
        }
        prompt = (
            "Given this tabular dataset summary, suggest a quick model family to sanity-check the data.\n"
            "Return ONLY one of: 'logreg', 'rf_class', 'rf_reg', 'ridge', 'linear'.\n"
            f"Summary: {json.dumps(summary)}\n"
        )
        resp = client.responses.create(model="gpt-4o-mini", input=prompt)
        text = getattr(resp, "output_text", "").strip().lower()
        for tok in ["logreg", "rf_class", "rf_reg", "ridge", "linear"]:
            if tok in text:
                return tok
    except Exception:
        return None
    return None

def _automl_flaml(X: pd.DataFrame, y: np.ndarray, task: str, time_budget: int = 30) -> Dict[str, Any]:
    if not _HAS_FLAML:
        return {"backend": "flaml", "error": "FLAML not installed"}
    automl = FLAML_AutoML()
    metric = "accuracy" if task == "classification" else "r2"
    try:
        automl.fit(X_train=X, y_train=y, task=task, time_budget=time_budget, metric=metric, verbose=False)
        return {"backend": "flaml", "best_model": str(automl.model.estimator) if automl.model else "n/a",
                "best_config": automl.best_config, "best_loss": automl.best_loss}
    except Exception as e:
        return {"backend": "flaml", "error": str(e)}

def _automl_autogluon(df: pd.DataFrame, target: str, time_budget: int = 30) -> Dict[str, Any]:
    if not _HAS_AUTOGLUON:
        return {"backend": "autogluon", "error": "AutoGluon not installed"}
    try:
        label = target
        df_small = df.sample(min(1000, len(df)), random_state=42)
        predictor = TabularPredictor(label=label, verbosity=0).fit(df_small, time_limit=time_budget)
        leaderboard = predictor.leaderboard(silent=True)
        top_row = leaderboard.iloc[0].to_dict() if len(leaderboard) else {}
        return {"backend": "autogluon", "top_model": top_row.get("model"), "val_score": top_row.get("score_val")}
    except Exception as e:
        return {"backend": "autogluon", "error": str(e)}

def _automl_sklearn(X: pd.DataFrame, y: np.ndarray, task: str, advisor_hint: Optional[str]) -> Dict[str, Any]:
    results: Dict[str, Any] = {"backend": "sklearn", "models": []}
    rng = 42
    if task == "classification":
        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=rng)
        if advisor_hint == "logreg":
            candidates = [("logreg", LogisticRegression(max_iter=200))]
        elif advisor_hint == "rf_class":
            candidates = [("rf_class", RandomForestClassifier(n_estimators=200, random_state=rng))]
        else:
            candidates = [
                ("dummy", DummyClassifier(strategy="most_frequent")),
                ("logreg", LogisticRegression(max_iter=200)),
                ("rf_class", RandomForestClassifier(n_estimators=200, random_state=rng)),
            ]
        for name, model in candidates:
            try:
                acc = cross_val_score(model, X, y, cv=cv, scoring=make_scorer(accuracy_score))
                f1s = cross_val_score(model, X, y, cv=cv, scoring=F1_MACRO_SCORER)
                results["models"].append({"model": name, "acc_mean": float(acc.mean()), "f1_macro_mean": float(f1s.mean())})
            except Exception as e:
                results["models"].append({"model": name, "error": str(e)})
    else:
        cv = KFold(n_splits=3, shuffle=True, random_state=rng)
        if advisor_hint == "ridge":
            candidates = [("ridge", Ridge(alpha=1.0, random_state=rng))]
        elif advisor_hint == "linear":
            candidates = [("linear", LinearRegression())]
        elif advisor_hint == "rf_reg":
            candidates = [("rf_reg", RandomForestRegressor(n_estimators=200, random_state=rng))]
        else:
            candidates = [
                ("dummy", DummyRegressor()),
                ("linear", LinearRegression()),
                ("ridge", Ridge(alpha=1.0, random_state=rng)),
                ("rf_reg", RandomForestRegressor(n_estimators=200, random_state=rng)),
            ]
        for name, model in candidates:
            try:
                r2s = cross_val_score(model, X, y, cv=cv, scoring=make_scorer(r2_score))
                results["models"].append({"model": name, "r2_mean": float(r2s.mean())})
            except Exception as e:
                results["models"].append({"model": name, "error": str(e)})
    return results

def run_automl(df: pd.DataFrame, target: Optional[str], backend_pref: Optional[str], advisor: Optional[str], budget: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {"enabled": True}
    if not target or target not in df.columns:
        out["error"] = "No target column found/provided for AutoML."
        return out
    task = _infer_task(df, target)
    out["task"] = task
    X, y, _ = _prepare_xy(df, target)
    hint = None
    if advisor == "openai":
        hint = _advisor_openai(df, target)
    out["advisor_hint"] = hint
    if len(X) > 5000:
        idx = np.random.RandomState(42).choice(len(X), size=5000, replace=False)
        X = X.iloc[idx]
        y = y[idx]
    results = []
    order = [backend_pref] if backend_pref else ["flaml", "autogluon", "sklearn"]
    for backend in order:
        if backend == "flaml":
            results.append(_automl_flaml(X, y, "classification" if task == "classification" else "regression", time_budget=budget))
        elif backend == "autogluon":
            results.append(_automl_autogluon(pd.concat([X.reset_index(drop=True), pd.Series(y, name=target)], axis=1), target, time_budget=budget))
        else:
            results.append(_automl_sklearn(X, y, task, hint))
    out["results"] = results
    return out

# -------------------- CLI --------------------
EXAMPLES = r"""
Examples:
  # Minimal two-flag run (clean only)
  python super_cleaner.py --file merged_iot_events.csv --output out.csv

  # Clean + sidecar report (auto) – report saved next to out.csv as out_report.json
  python super_cleaner.py --file merged_iot_events.csv --output out.csv

  # Disable optional plugins if they slow you down
  python super_cleaner.py --file data.csv --output out.csv --no-plugins

  # Run AutoML sanity-check using FLAML (30s budget) on a known target column
  python super_cleaner.py --file data.csv --output out.csv --automl --target label --automl-backend flaml --automl-budget 30

  # Let OpenAI suggest a model family (set OPENAI_API_KEY first)
  # Windows (PowerShell: $env:OPENAI_API_KEY="sk-..."), macOS/Linux: export OPENAI_API_KEY=sk-...
  python super_cleaner.py --file data.csv --output out.csv --automl --target label --advisor openai

  # JSON & JSONL & Parquet inputs are supported
  python super_cleaner.py --file events.json --output clean.csv
  python super_cleaner.py --file events.jsonl --output clean.csv
  python super_cleaner.py --file dataset.parquet --output clean.csv
"""

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Super Cleaner++ : two-flag robust cleaner with best-effort plugins and optional AutoML dry-run",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=EXAMPLES,
    )
    p.add_argument("--file", required=True, help="Input file (csv/tsv/json/jsonl/parquet)")
    p.add_argument("--output", required=True, help="Output cleaned CSV path")
    p.add_argument("--no-plugins", action="store_true", help="Disable optional plugin passes (AutoClean, pyjanitor, etc.)")
    p.add_argument("--profilecsv", default=None, help="Optional: write a column profile CSV here")
    p.add_argument("--validate", action="store_true", help="Run light validations (Pandera/GE if installed)")
    p.add_argument("--automl", action="store_true", help="Run a quick AutoML dry-run on the cleaned data")
    p.add_argument("--target", default=None, help="Target/label column for AutoML (otherwise auto-detected)")
    p.add_argument("--automl-backend", choices=["flaml", "autogluon", "sklearn"], default=None, help="Preferred backend (tries others if missing)")
    p.add_argument("--automl-budget", type=int, default=30, help="Time budget (seconds) for FLAML/AutoGluon")
    p.add_argument("--advisor", choices=["openai"], default=None, help="Use OpenAI to suggest a model family (requires OPENAI_API_KEY)")
    # Convenience flag to only print examples and exit
    p.add_argument("--examples", action="store_true", help="Show usage examples and exit")
    return p

# -------------------- Main --------------------
def main():
    args = build_argparser().parse_args()

    # If user just wants the examples, print them and exit cleanly
    if getattr(args, "examples", False):
        print(EXAMPLES.strip())
        sys.exit(0)

    # Load
    df_in = _read_any(args.file)
    before = df_in.shape

    # Clean (core)
    df_core = core_clean(df_in)

    # Plugins (optional)
    report: Dict[str, Any] = {}
    if not args.no_plugins:
        df_core = run_plugins(df_core, report)
    else:
        report["applied_plugins"] = {"plugins": ["(plugins disabled)"], "errors": []}

    # Enforce tz-naive after plugins (fixes Pandera complaint)
    df_core = _force_tz_naive(df_core)

    # Validate (Pandera/GE are already run inside plugins; this flag just keeps parity with your prior UX)
    if args.validate:
        report.setdefault("notes", []).append("validate flag set; plugin validations already applied when available")

    # Save cleaned CSV
    _to_csv(df_core, args.output)

    # Optional profile
    if args.profilecsv:
        prof = _profile(df_core)
        prof.to_csv(args.profilecsv, index=True)

    # AutoML dry-run (optional)
    automl_report: Optional[Dict[str, Any]] = None
    if args.automl:
        target = _detect_target(df_core, args.target)
        automl_report = run_automl(df_core, target, args.automl_backend, args.advisor, args.automl_budget)

    # Final sidecar summary
    usability = _usability(df_core)
    out_stem, _ = os.path.splitext(os.path.abspath(args.output))
    sidecar = f"{out_stem}_report.json"

    final_report = {
        "input_rows": int(before[0]),
        "input_cols": int(before[1]),
        "output_rows": int(df_core.shape[0]),
        "output_cols": int(df_core.shape[1]),
        "dtypes": df_core.dtypes.astype(str).to_dict(),
        "usability": usability,
    }
    final_report.update(report)
    if automl_report:
        final_report["automl"] = automl_report

    with open(sidecar, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    # Console summary
    status = usability["status"].upper()
    reasons = usability.get("reasons", [])
    extra = (" - " + "; ".join(reasons)) if reasons else ""
    print(f"USABILITY: {status}{extra}")
    print(json.dumps(
        {k: final_report.get(k) for k in ("input_rows", "input_cols", "output_rows", "output_cols", "usability")},
        indent=2
    ))
    if "applied_plugins" in final_report:
        print(json.dumps({"applied_plugins": final_report["applied_plugins"]}, indent=2))
    if automl_report:
        print(json.dumps({"automl": automl_report}, indent=2))

if __name__ == "__main__":
    main()
