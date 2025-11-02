import os
import io
import json
import glob
import time
import joblib
import pickle
import logging
import warnings
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

import numpy as np
import pandas as pd

try:
    import onnxruntime as ort
    HAS_ONNXRUNTIME = True
except Exception:
    HAS_ONNXRUNTIME = False

from .artifact_manager import ensure_workspace, register_artifact
from .large_data_config import UPLOAD_ROOT

logger = logging.getLogger(__name__)


def _now_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _get_active_run_dir(state: Dict[str, Any]) -> Tuple[str, str]:
    """Return (workspace_root, run_dir).

    In this project, state["workspace_root"] points to the active run directory
    (…/_workspaces/<dataset>/<YYYYMMDD_HHMMSS>). We honor that and avoid any
    hard-coded bases.
    """
    ensure_workspace(state, UPLOAD_ROOT)
    run_dir = state.get("workspace_root")
    if not run_dir or not os.path.isdir(run_dir):
        raise RuntimeError("Workspace not initialized; upload a dataset first.")
    return run_dir, run_dir


def _find_latest_model_path(run_dir: str) -> Optional[str]:
    models_dir = os.path.join(run_dir, "models")
    if not os.path.isdir(models_dir):
        return None
    patterns = ["*.joblib", "*.pkl", "*.pickle", "*.onnx"]
    files: list[str] = []
    for pat in patterns:
        files.extend(glob.glob(os.path.join(models_dir, pat)))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _load_model(model_path: str):
    ext = os.path.splitext(model_path)[1].lower()
    if ext == ".joblib":
        return joblib.load(model_path), "sk"
    if ext in (".pkl", ".pickle"):
        with open(model_path, "rb") as f:
            return pickle.load(f), "sk"
    if ext == ".onnx":
        if not HAS_ONNXRUNTIME:
            raise RuntimeError("onnxruntime is not installed; cannot load .onnx model.")
        sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        return sess, "onnx"
    with open(model_path, "rb") as f:
        return pickle.load(f), "sk"


def _load_current_dataframe(state: Dict[str, Any]) -> pd.DataFrame:
    path = state.get("default_csv_path") or state.get("default_parquet_path")
    if not path or not os.path.exists(path):
        raise RuntimeError("No active dataset in session; upload a dataset first.")
    if path.lower().endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _ensure_reports_dir(run_dir: str) -> str:
    reports_dir = os.path.join(run_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


def _save_csv_report(df: pd.DataFrame, run_dir: str, stem: str) -> str:
    out = os.path.join(run_dir, "reports", f"{stem}_{_now_slug()}.csv")
    df.to_csv(out, index=False)
    return out


def _simple_pdf(summary_text: str, run_dir: str, stem: str) -> str:
    pdf_path = os.path.join(run_dir, "reports", f"{stem}_{_now_slug()}.pdf")
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch

        c = canvas.Canvas(pdf_path, pagesize=LETTER)
        width, height = LETTER
        y = height - 1 * inch
        for line in summary_text.splitlines():
            c.drawString(1 * inch, y, line[:110])
            y -= 14
            if y < 1 * inch:
                c.showPage()
                y = height - 1 * inch
        c.save()
        return pdf_path
    except Exception:
        txt_path = pdf_path.replace(".pdf", ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
        return txt_path


def _infer_task(action: str) -> str:
    a = (action or "").strip().lower()
    if a in {"predict", "regress", "estimate", "estimate values"}:
        return "predict"
    if a in {"classify", "classification"}:
        return "classify"
    if a in {"rank"}:
        return "rank"
    if a in {"forecast"}:
        return "forecast"
    if a in {"anomaly", "detect anomalies", "anomaly detection"}:
        return "anomaly"
    if a in {"cluster", "clustering"}:
        return "cluster"
    return "predict"


def _split_X_y(df: pd.DataFrame, target: Optional[str]) -> tuple[pd.DataFrame, Optional[pd.Series]]:
    y = None
    if target and target in df.columns:
        y = df[target]
        X = df.drop(columns=[target])
    else:
        X = df.copy()
    for col in list(X.columns):
        if str(col).lower() in {"id", "uuid", "index", "_id"}:
            X = X.drop(columns=[col])
    return X, y


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def load_model_universal_tool(action: str = "", target: Optional[str] = None, params_json: str = "", **kwargs) -> Dict[str, Any]:
    """Load latest model in active workspace and run quick inference on current dataset.

    - Finds run dir from state (no hard-coded paths)
    - Supports .joblib/.pkl/.onnx
    - Writes outputs + a small PDF summary to run/reports/
    - Registers artifacts
    """
    t0 = time.time()
    state = (kwargs.get("tool_context").state if kwargs.get("tool_context") else {}) or {}

    try:
        run_dir, _ = _get_active_run_dir(state)
        _ensure_reports_dir(run_dir)
        model_path = _find_latest_model_path(run_dir)
        if not model_path:
            raise FileNotFoundError(f"No model files found under: {os.path.join(run_dir, 'models')}")

        try:
            extra = json.loads(params_json) if params_json else {}
        except Exception:
            extra = {}

        df = _load_current_dataframe(state)
        X, y = _split_X_y(df, target)
        model, kind = _load_model(model_path)

        canonical = _infer_task(action)
        summary = [
            f"Action: {canonical}",
            f"Run dir: {run_dir}",
            f"Model: {os.path.basename(model_path)} ({kind})",
            f"Rows: {len(X):,}, Cols: {X.shape[1]}",
        ]

        artifacts: list[str] = []
        preview_head = None

        if canonical in {"predict", "classify", "rank"} and kind == "sk":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                y_pred = model.predict(X) if hasattr(model, "predict") else None
                y_proba = None
                if canonical == "rank":
                    if hasattr(model, "predict_proba"):
                        y_proba = model.predict_proba(X)
                    elif hasattr(model, "decision_function"):
                        scores = model.decision_function(X)
                        y_proba = np.vstack([1 - _sigmoid(scores), _sigmoid(scores)]).T if scores.ndim == 1 else scores

                out_df = pd.DataFrame(index=X.index)
                if y_pred is not None:
                    out_df["prediction"] = y_pred
                if y_proba is not None:
                    if y_proba.ndim == 1:
                        out_df["score"] = y_proba
                    else:
                        for j in range(y_proba.shape[1]):
                            out_df[f"proba_{j}"] = y_proba[:, j]
                        if "proba_1" in out_df.columns:
                            out_df["rank_score"] = out_df["proba_1"]
                        else:
                            proba_cols = [c for c in out_df.columns if c.startswith("proba_")]
                            if proba_cols:
                                out_df["rank_score"] = out_df[proba_cols].max(axis=1)

                id_like = [c for c in df.columns if str(c).lower() in {"id", "uuid", "index"}]
                for c in id_like:
                    out_df[c] = df[c]

                out_path = _save_csv_report(out_df.reset_index(drop=True), run_dir, stem=f"{canonical}_output")
                register_artifact(state, out_path, kind="report", label=f"{canonical}_output")
                artifacts.append(out_path)

                head_preview = out_df.head(10).to_string(index=False)
                preview_head = head_preview
                pdf_path = _simple_pdf("\n".join(summary + ["", "Preview:", head_preview]), run_dir, stem=f"{canonical}_summary")
                register_artifact(state, pdf_path, kind="report", label=f"{canonical}_summary")
                artifacts.append(pdf_path)

        elif canonical == "forecast":
            horizon = int(extra.get("forecast_horizon", 24))
            if kind == "sk" and hasattr(model, "predict"):
                last_row = X.tail(1).to_numpy()
                preds = []
                for _ in range(horizon):
                    preds.append(float(model.predict(last_row)[0]))
                out_df = pd.DataFrame({"t": np.arange(1, horizon + 1), "forecast": preds})
                out_path = _save_csv_report(out_df, run_dir, stem="forecast_output")
                register_artifact(state, out_path, kind="report", label="forecast_output")
                artifacts.append(out_path)
                head_preview = out_df.head(10).to_string(index=False)
                pdf_path = _simple_pdf("\n".join(summary + [f"Horizon: {horizon}", "", "Preview:", head_preview]), run_dir, stem="forecast_summary")
                register_artifact(state, pdf_path, kind="report", label="forecast_summary")
                artifacts.append(pdf_path)
            else:
                msg = "Loaded model is not a sklearn regressor; use ts_* tools for time series."
                pdf_path = _simple_pdf("\n".join(summary + ["", msg]), run_dir, stem="forecast_summary")
                register_artifact(state, pdf_path, kind="report", label="forecast_summary")
                artifacts.append(pdf_path)

        elif canonical == "anomaly" and kind == "sk":
            flagged = None
            if hasattr(model, "decision_function"):
                scores = model.decision_function(X)
                thr = float(np.percentile(scores, 2.0))
                flagged = scores < thr
                out_df = pd.DataFrame({"score": scores, "is_anomaly": flagged})
            elif hasattr(model, "score_samples"):
                scores = model.score_samples(X)
                thr = float(np.percentile(scores, 2.0))
                flagged = scores < thr
                out_df = pd.DataFrame({"score": scores, "is_anomaly": flagged})
            if flagged is None:
                msg = "Model does not expose anomaly scoring; consider lof/oneclass_svm."
                pdf_path = _simple_pdf("\n".join(summary + ["", msg]), run_dir, stem="anomaly_summary")
                register_artifact(state, pdf_path, kind="report", label="anomaly_summary")
                artifacts.append(pdf_path)
            else:
                out_path = _save_csv_report(out_df, run_dir, stem="anomaly_output")
                register_artifact(state, out_path, kind="report", label="anomaly_output")
                artifacts.append(out_path)
                head_preview = out_df.head(10).to_string(index=False)
                pdf_path = _simple_pdf("\n".join(summary + ["", "Preview:", head_preview]), run_dir, stem="anomaly_summary")
                register_artifact(state, pdf_path, kind="report", label="anomaly_summary")
                artifacts.append(pdf_path)

        elif canonical == "cluster" and kind == "sk":
            try:
                labels = model.predict(X) if hasattr(model, "predict") else model.fit_predict(X)
                out_df = pd.DataFrame({"cluster": labels})
                out_path = _save_csv_report(out_df, run_dir, stem="cluster_output")
                register_artifact(state, out_path, kind="report", label="cluster_output")
                artifacts.append(out_path)
                head_preview = out_df.head(10).to_string(index=False)
                pdf_path = _simple_pdf("\n".join(summary + ["", "Preview:", head_preview]), run_dir, stem="cluster_summary")
                register_artifact(state, pdf_path, kind="report", label="cluster_summary")
                artifacts.append(pdf_path)
            except Exception as e:
                msg = f"Clustering inference failed: {e}"
                pdf_path = _simple_pdf("\n".join(summary + ["", msg]), run_dir, stem="cluster_summary")
                register_artifact(state, pdf_path, kind="report", label="cluster_summary")
                artifacts.append(pdf_path)

        elif kind == "onnx":
            sess = model
            input_name = sess.get_inputs()[0].name
            out_name = sess.get_outputs()[0].name
            Xn = X.select_dtypes(include=[np.number]).to_numpy().astype(np.float32, copy=False)
            yhat = sess.run([out_name], {input_name: Xn})[0]
            out_df = pd.DataFrame({"output": np.asarray(yhat).ravel()})
            out_path = _save_csv_report(out_df, run_dir, stem=f"{canonical or 'inference'}_onnx_output")
            register_artifact(state, out_path, kind="report", label="onnx_output")
            artifacts.append(out_path)
            head_preview = out_df.head(10).to_string(index=False)
            pdf_path = _simple_pdf("\n".join(summary + ["", "Preview:", head_preview]), run_dir, stem="onnx_summary")
            register_artifact(state, pdf_path, kind="report", label="onnx_summary")
            artifacts.append(pdf_path)

        else:
            msg = (
                "Universal loader covers tabular predict/classify/rank/forecast/anomaly/cluster. "
                "Use specialized pipelines for recommend/generate/optimize."
            )
            pdf_path = _simple_pdf("\n".join(summary + ["", msg]), run_dir, stem="note_universal_loader")
            register_artifact(state, pdf_path, kind="report", label="note_universal_loader")
            artifacts.append(pdf_path)

        dt = time.time() - t0
        logger.info(f"load_model_universal_tool completed in {dt:.2f}s")
        return {
            "status": "success",
            "action": canonical,
            "model_path": model_path,
            "artifacts": artifacts,
            "message": f"Completed in {dt:.2f}s. Saved under reports/ and registered as artifacts.",
            "preview": (preview_head[:1000] if preview_head else "")
        }

    except Exception as e:
        logger.exception("load_model_universal_tool failed")
        return {
            "status": "failed",
            "error": str(e),
            "message": "Could not load model or execute the requested action.",
            "suggestion": "Ensure a model exists under models/ and a dataset is uploaded."
        }


