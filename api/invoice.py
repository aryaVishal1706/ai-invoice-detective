import os, json
from fastapi import APIRouter, HTTPException
from models.schemas import InvoiceInput, RiskReport, RiskLevel, Flag
from core.rules.validator import run_all_checks
from core.anomaly.detector import score_invoice, load_model, build_vendor_stats
from core.anomaly.explainer import explain_risk
from core.anomaly.blacklist import load_blacklist, check_blacklist

router = APIRouter(prefix="/invoice", tags=["Invoice"])

# On Lambda, ML scoring is delegated to ML Lambda — skip local model load
_IS_LAMBDA    = bool(os.environ.get("ML_LAMBDA_FUNCTION"))
_artifact     = None if _IS_LAMBDA else load_model()
_vendor_stats = {} if _IS_LAMBDA else build_vendor_stats()
load_blacklist(os.getenv("BLACKLIST_PATH", ""))

# DynamoDB client (only on Lambda)
_dynamodb = None
def _get_table():
    global _dynamodb
    table_name = os.environ.get("DYNAMODB_TABLE")
    if not table_name:
        return None
    if _dynamodb is None:
        import boto3
        _dynamodb = boto3.resource("dynamodb", region_name="ap-south-1").Table(table_name)
    return _dynamodb

# In-memory fallback for local dev
_reports: dict = {}


@router.post("/validate")
def validate_invoice(invoice: InvoiceInput):
    """Run 14 rule-based checks. Returns list of violations."""
    flags = run_all_checks(invoice.model_dump())
    return {
        "invoice_id": invoice.invoice_id,
        "violations": len(flags),
        "flags": flags
    }


@router.post("/analyze", response_model=RiskReport)
def analyze_invoice(invoice: InvoiceInput):
    """
    Full analysis pipeline:
    1. Run rule-based checks
    2. Score with IsolationForest
    3. Generate Groq explanation
    4. Return risk report
    """
    data = invoice.model_dump()

    # Layer 1 — Rules
    flags = run_all_checks(data)

    # Blacklist check (optional — skipped if no list loaded)
    bl_match = check_blacklist(invoice.vendor_name)
    if bl_match:
        flags.append(Flag(
            check="Blacklisted Vendor",
            detail=f"Vendor matches blacklist entry '{bl_match['matched']}' (score: {bl_match['score']}%)",
            severity=RiskLevel.HIGH
        ))

    # Layer 2 — ML anomaly score
    ml_score = score_invoice(data, _artifact, _vendor_stats)

    # Combine: rule violations boost the score
    rule_boost = min(len(flags) * 8, 40)
    risk_score = min(ml_score + rule_boost, 100)

    # Risk level thresholds
    if risk_score >= 70:
        risk_level = RiskLevel.HIGH
    elif risk_score >= 40:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    # Layer 3 — Groq explanation
    explanation, recommendation = explain_risk(
        invoice.invoice_id, invoice.vendor_name,
        invoice.amount, risk_score, flags
    )

    report = RiskReport(
        invoice_id=invoice.invoice_id,
        vendor=invoice.vendor_name,
        amount=invoice.amount,
        risk_score=risk_score,
        risk_level=risk_level,
        flags=flags,
        explanation=explanation,
        recommendation=recommendation
    )

    # Save to DynamoDB (Lambda) or in-memory (local)
    table = _get_table()
    if table:
        from decimal import Decimal
        import json
        # Convert floats to Decimal for DynamoDB
        item = json.loads(report.model_dump_json(), parse_float=Decimal)
        table.put_item(Item=item)
    else:
        _reports[invoice.invoice_id] = report

    return report


@router.get("/report/{invoice_id}", response_model=RiskReport)
def get_report(invoice_id: str):
    """Retrieve a previously analyzed invoice report."""
    table = _get_table()
    if table:
        resp = table.get_item(Key={"invoice_id": invoice_id})
        item = resp.get("Item")
        if not item:
            raise HTTPException(status_code=404, detail="Report not found.")
        return item
    if invoice_id not in _reports:
        raise HTTPException(status_code=404, detail="Report not found.")
    return _reports[invoice_id]
