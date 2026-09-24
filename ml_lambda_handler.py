"""
ML Lambda — runs IsolationForest scoring.
Invoked by the main API Lambda when anomaly score is needed.
Heavy dependencies (scikit-learn, pandas) live here only.
"""
import json
import os
import pickle
import boto3
import pandas as pd
import numpy as np

MODEL_BUCKET = os.environ.get("MODEL_BUCKET")
MODEL_KEY    = os.environ.get("MODEL_KEY", "isolation_forest.pkl")
STATS_KEY    = os.environ.get("STATS_KEY", "vendor_stats.json")

_artifact     = None
_vendor_stats = None


def _load_artifact():
    global _artifact
    if _artifact is None:
        tmp = "/tmp/isolation_forest.pkl"
        if not os.path.exists(tmp):
            boto3.client("s3").download_file(MODEL_BUCKET, MODEL_KEY, tmp)
        with open(tmp, "rb") as f:
            _artifact = pickle.load(f)
    return _artifact


def _load_vendor_stats():
    global _vendor_stats
    if _vendor_stats is None:
        tmp = "/tmp/vendor_stats.json"
        if not os.path.exists(tmp):
            boto3.client("s3").download_file(MODEL_BUCKET, STATS_KEY, tmp)
        with open(tmp) as f:
            _vendor_stats = json.load(f)
    return _vendor_stats


def _score(invoice: dict, artifact: dict, stats: dict) -> int:
    vendor        = invoice.get("vendor_name", "")
    amount        = float(invoice.get("amount", 0))
    vendor_data   = stats.get(vendor, {})
    vendor_avg    = vendor_data.get("avg_amount", amount)
    vendor_std    = vendor_data.get("std_amount", 1) or 1
    amount_vs_avg = amount / vendor_avg if vendor_avg > 0 else 1.0
    amount_zscore = (amount - vendor_avg) / vendor_std

    try:
        inv_dt = pd.to_datetime(invoice.get("invoice_date"))
        sub_dt = pd.to_datetime(invoice.get("submission_date"))
        submission_lag = (sub_dt - inv_dt).days
        is_weekend     = 1 if inv_dt.weekday() >= 5 else 0
        is_future      = 1 if inv_dt > pd.Timestamp.today() else 0
    except Exception:
        submission_lag = is_weekend = is_future = 0

    expected_tax  = amount * 0.18
    tax_deviation = abs(invoice.get("tax_amount", expected_tax) - expected_tax) / max(expected_tax, 1)
    missing_po    = 1 if not invoice.get("po_number") else 0
    missing_gstin = 1 if not invoice.get("vendor_gstin") else 0
    is_round      = 1 if amount % 10000 == 0 else 0

    features = pd.DataFrame([[
        amount, submission_lag, amount_vs_avg, amount_zscore,
        vendor_data.get("monthly_freq", 1),
        tax_deviation, is_weekend, is_future, missing_po, missing_gstin, is_round
    ]], columns=["amount", "submission_lag", "amount_vs_vendor_avg", "amount_zscore",
                 "vendor_monthly_freq", "tax_deviation", "is_weekend", "is_future",
                 "missing_po", "missing_gstin", "is_round"])

    model      = artifact["model"]
    score_min  = artifact["score_min"]
    score_max  = artifact["score_max"]
    raw        = model.decision_function(features)[0]
    score_range = score_max - score_min if score_max != score_min else 1
    return int(np.clip((1 - (raw - score_min) / score_range) * 100, 0, 100))


def handler(event, context):
    """
    Expects event: { invoice: { ...invoice fields... } }
    Returns: { score: int }
    """
    try:
        invoice  = event.get("invoice", event)
        artifact = _load_artifact()
        stats    = _load_vendor_stats()
        score    = _score(invoice, artifact, stats)
        return {"statusCode": 200, "score": score}
    except Exception as e:
        return {"statusCode": 500, "error": str(e), "score": 50}
