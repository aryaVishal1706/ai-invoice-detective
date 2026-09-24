"""
Evaluate IsolationForest on the synthetic labeled dataset.
Measures how well the ML model detects anomalies.
"""
import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from core.anomaly.detector import load_model, build_vendor_stats, score_invoice

DATASET_PATH = "data/raw/invoice_dataset.csv"
SCORE_THRESHOLD = 60   # score >= 60 → predicted anomaly


def evaluate():
    df = pd.read_csv(DATASET_PATH)
    model = load_model()
    stats = build_vendor_stats()

    y_true, y_pred = [], []

    for _, row in df.iterrows():
        invoice = row.to_dict()
        score = score_invoice(invoice, model, stats)
        y_true.append(int(row["is_anomaly"]))
        y_pred.append(1 if score >= SCORE_THRESHOLD else 0)

    print("=" * 50)
    print("ISOLATION FOREST — EVALUATION REPORT")
    print(f"Dataset : {len(df)} invoices | Threshold: {SCORE_THRESHOLD}/100")
    print("=" * 50)
    print(classification_report(y_true, y_pred, target_names=["Normal", "Anomaly"]))

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    print(f"True Positives  (caught fraud)    : {tp}")
    print(f"False Positives (false alarms)    : {fp}")
    print(f"False Negatives (missed fraud)    : {fn}")
    print(f"True Negatives  (correct clears)  : {tn}")
    print()

    # Per anomaly type breakdown
    anomaly_df = df[df["is_anomaly"] == 1].copy()
    scores = []
    for _, row in anomaly_df.iterrows():
        s = score_invoice(row.to_dict(), model, stats)
        scores.append({"anomaly_type": row["anomaly_type"], "score": s, "detected": 1 if s >= SCORE_THRESHOLD else 0})

    result = pd.DataFrame(scores)
    summary = result.groupby("anomaly_type").agg(
        total=("detected", "count"),
        detected=("detected", "sum"),
        avg_score=("score", "mean")
    )
    summary["detection_rate"] = (summary["detected"] / summary["total"] * 100).round(1)
    summary = summary.sort_values("detection_rate", ascending=False)

    print("PER ANOMALY TYPE DETECTION RATE:")
    print(summary[["total", "detected", "avg_score", "detection_rate"]].to_string())


if __name__ == "__main__":
    evaluate()
