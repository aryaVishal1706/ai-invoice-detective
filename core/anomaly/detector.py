import pickle
import os
import json

MODEL_PATH = "models/trained/isolation_forest.pkl"
DATASET_PATH = "data/raw/invoice_dataset.csv"


def _build_features(df):
    """Extract numeric features from invoice dataframe for IsolationForest."""
    import pandas as pd
    df = df.copy()
    df["invoice_date"]    = pd.to_datetime(df["invoice_date"])
    df["submission_date"] = pd.to_datetime(df["submission_date"])

    df["submission_lag"]       = (df["submission_date"] - df["invoice_date"]).dt.days
    vendor_avg                 = df.groupby("vendor_name")["amount"].transform("mean")
    vendor_std                 = df.groupby("vendor_name")["amount"].transform("std").fillna(1)
    df["amount_vs_vendor_avg"] = df["amount"] / vendor_avg.replace(0, 1)
    df["amount_zscore"]        = (df["amount"] - vendor_avg) / vendor_std.replace(0, 1)
    df["month"]                = df["invoice_date"].dt.to_period("M").astype(str)
    df["vendor_monthly_freq"]  = df.groupby(["vendor_name", "month"])["invoice_id"].transform("count")
    df["tax_deviation"]        = abs(df["tax_amount"] - df["amount"] * 0.18) / (df["amount"] * 0.18).replace(0, 1)
    df["is_weekend"]           = df["invoice_date"].dt.weekday.ge(5).astype(int)
    df["is_future"]            = (df["invoice_date"] > pd.Timestamp.today()).astype(int)
    df["missing_po"]           = df["po_number"].isna().astype(int)
    df["missing_gstin"]        = df["vendor_gstin"].isna().astype(int)
    df["is_round"]             = (df["amount"] % 10000 == 0).astype(int)

    return df[["amount", "submission_lag", "amount_vs_vendor_avg", "amount_zscore",
               "vendor_monthly_freq", "tax_deviation", "is_weekend", "is_future",
               "missing_po", "missing_gstin", "is_round"]]


def train_model():
    """Train IsolationForest on normal invoices from synthetic dataset and save model."""
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import IsolationForest
    os.makedirs("models/trained", exist_ok=True)

    df = pd.read_csv(DATASET_PATH)
    normal_df = df[df["is_anomaly"] == 0].copy()

    features = _build_features(normal_df)

    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(features)

    # Compute score bounds from full dataset for normalization
    all_features = _build_features(df)
    all_scores   = model.decision_function(all_features)
    score_min, score_max = float(all_scores.min()), float(all_scores.max())

    artifact = {"model": model, "score_min": score_min, "score_max": score_max}
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(artifact, f)

    print(f"Model trained on {len(normal_df)} normal invoices → saved to {MODEL_PATH}")
    print(f"Score range: [{score_min:.4f}, {score_max:.4f}]")
    return artifact


def load_model() -> dict:
    """Load trained model artifact — from S3 on Lambda, from disk locally."""
    import os
    model_bucket = os.environ.get("MODEL_BUCKET")

    if model_bucket:
        # Running on Lambda — download from S3 to /tmp
        import boto3
        tmp_path = "/tmp/isolation_forest.pkl"
        if not os.path.exists(tmp_path):
            boto3.client("s3").download_file(
                model_bucket, os.environ.get("MODEL_KEY", "isolation_forest.pkl"), tmp_path
            )
        with open(tmp_path, "rb") as f:
            return pickle.load(f)

    # Running locally
    if not os.path.exists(MODEL_PATH):
        return train_model()
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def score_invoice(invoice: dict, artifact: dict, vendor_stats: dict) -> int:
    """
    Score invoice — calls ML Lambda if running on AWS, runs locally otherwise.
    Returns anomaly score 0–100.
    """
    ml_function = os.environ.get("ML_LAMBDA_FUNCTION")

    if ml_function:
        import boto3, json
        client   = boto3.client("lambda", region_name="ap-south-1")
        response = client.invoke(
            FunctionName=ml_function,
            InvocationType="RequestResponse",
            Payload=json.dumps({"invoice": invoice})
        )
        result = json.loads(response["Payload"].read())
        return result.get("score", 50)

    # Running locally — use pandas/numpy directly
    import pandas as pd
    import numpy as np

    vendor         = invoice["vendor_name"]
    amount         = invoice["amount"]
    vendor_avg_amt = vendor_stats.get(vendor, {}).get("avg_amount", amount)
    vendor_std_amt = vendor_stats.get(vendor, {}).get("std_amount", 1) or 1
    amount_vs_avg  = amount / vendor_avg_amt if vendor_avg_amt > 0 else 1.0
    amount_zscore  = (amount - vendor_avg_amt) / vendor_std_amt

    try:
        inv_dt = pd.to_datetime(invoice["invoice_date"])
        sub_dt = pd.to_datetime(invoice["submission_date"])
        submission_lag = (sub_dt - inv_dt).days
        is_weekend = 1 if inv_dt.weekday() >= 5 else 0
        is_future  = 1 if inv_dt > pd.Timestamp.today() else 0
    except Exception:
        submission_lag = is_weekend = is_future = 0

    expected_tax  = amount * 0.18
    tax_deviation = abs(invoice.get("tax_amount", expected_tax) - expected_tax) / max(expected_tax, 1)
    missing_po    = 1 if not invoice.get("po_number") else 0
    missing_gstin = 1 if not invoice.get("vendor_gstin") else 0
    is_round      = 1 if amount % 10000 == 0 else 0

    model       = artifact["model"]
    score_min   = artifact["score_min"]
    score_max   = artifact["score_max"]
    score_range = score_max - score_min if score_max != score_min else 1

    features = pd.DataFrame([[
        amount, submission_lag, amount_vs_avg, amount_zscore,
        vendor_stats.get(vendor, {}).get("monthly_freq", 1),
        tax_deviation, is_weekend, is_future, missing_po, missing_gstin, is_round
    ]], columns=["amount", "submission_lag", "amount_vs_vendor_avg", "amount_zscore",
                 "vendor_monthly_freq", "tax_deviation", "is_weekend", "is_future",
                 "missing_po", "missing_gstin", "is_round"])

    raw_score = model.decision_function(features)[0]
    return int(np.clip((1 - (raw_score - score_min) / score_range) * 100, 0, 100))


def build_vendor_stats(csv_path: str = DATASET_PATH) -> dict:
    """Build per-vendor baseline stats from historical invoice data."""
    import pandas as pd
    df = pd.read_csv(csv_path)
    normal = df[df["is_anomaly"] == 0]

    stats = {}
    for vendor, group in normal.groupby("vendor_name"):
        group["month"] = pd.to_datetime(group["invoice_date"]).dt.to_period("M").astype(str)
        stats[vendor] = {
            "avg_amount":   group["amount"].mean(),
            "std_amount":   group["amount"].std(),
            "monthly_freq": group.groupby("month").size().mean()
        }
    return stats
