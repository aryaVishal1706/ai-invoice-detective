"""
Integration tests — Full API pipeline via FastAPI TestClient
Tests the complete flow: input → rules → ML → Groq → risk report
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from dotenv import load_dotenv
load_dotenv()

from main import app
from core.rules.validator import _seen_invoices, _vendor_bank_accounts, _vendor_first_seen

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_state():
    _seen_invoices.clear()
    _vendor_bank_accounts.clear()
    _vendor_first_seen.clear()
    yield

CLEAN_INVOICE = {
    "invoice_id"      : "INV-INT-001",
    "vendor_name"     : "Wipro Technologies",
    "vendor_gstin"    : "27AABCT1332L1ZN",
    "amount"          : 500000.0,
    "tax_amount"      : 90000.0,
    "tax_rate"        : 0.18,
    "invoice_date"    : "2024-03-15",
    "submission_date" : "2024-03-20",
    "po_number"       : "PO-1234-ABCD",
    "bank_account"    : "ACC-WIPRO-001",
    "payment_terms"   : "Net 30"
}

FRAUD_INVOICE = {
    "invoice_id"      : "INV-INT-002",
    "vendor_name"     : "SuspiciousVendor-999",
    "vendor_gstin"    : None,
    "amount"          : 9500000.0,
    "tax_amount"      : 100000.0,   # wrong GST
    "tax_rate"        : 0.18,
    "invoice_date"    : "2024-01-10",
    "submission_date" : "2024-07-01",  # late
    "po_number"       : None,          # missing PO
    "bank_account"    : "NEW-BANK-999",
    "payment_terms"   : "Net 30"
}


# ── /invoice/validate ─────────────────────────────────────────────────────────
def test_validate_clean_invoice():
    # amount 100,000 — below ₹5L new vendor threshold, correct GST, has PO
    inv = {**CLEAN_INVOICE, "invoice_id": "INV-CLEAN-UNIQUE",
           "vendor_name": "CleanVendorUnique123", "amount": 100000.0, "tax_amount": 18000.0}
    r = client.post("/invoice/validate", json=inv)
    assert r.status_code == 200
    assert r.json()["violations"] == 0

def test_validate_fraud_invoice_has_flags():
    r = client.post("/invoice/validate", json=FRAUD_INVOICE)
    assert r.status_code == 200
    assert r.json()["violations"] > 0

def test_validate_missing_po_flagged():
    inv = dict(CLEAN_INVOICE, invoice_id="INV-INT-003", po_number=None)
    r = client.post("/invoice/validate", json=inv)
    checks = [f["check"] for f in r.json()["flags"]]
    assert "Missing PO Number" in checks

def test_validate_gst_mismatch_flagged():
    inv = dict(CLEAN_INVOICE, invoice_id="INV-INT-004", tax_amount=5000.0)
    r = client.post("/invoice/validate", json=inv)
    checks = [f["check"] for f in r.json()["flags"]]
    assert "GST Mismatch" in checks


# ── /invoice/analyze ──────────────────────────────────────────────────────────
def test_analyze_returns_risk_report():
    """Mock Groq to avoid API call in tests."""
    with patch("core.anomaly.explainer.explain_risk",
               return_value=("Test explanation.", "HOLD")):
        r = client.post("/invoice/analyze", json=FRAUD_INVOICE)
    assert r.status_code == 200
    body = r.json()
    assert "risk_score"      in body
    assert "risk_level"      in body
    assert "flags"           in body
    assert "explanation"     in body
    assert "recommendation"  in body

def test_analyze_fraud_invoice_high_risk():
    with patch("core.anomaly.explainer.explain_risk",
               return_value=("High risk detected.", "HOLD")):
        r = client.post("/invoice/analyze", json=FRAUD_INVOICE)
    assert r.json()["risk_level"] == "HIGH"
    assert r.json()["risk_score"] >= 70

def test_analyze_recommendation_hold_for_high_risk():
    with patch("core.anomaly.explainer.explain_risk",
               return_value=("Suspicious invoice.", "HOLD")):
        r = client.post("/invoice/analyze", json=FRAUD_INVOICE)
    assert r.json()["recommendation"] == "HOLD"


# ── /invoice/report/{id} ──────────────────────────────────────────────────────
def test_report_retrieval_after_analyze():
    inv = dict(FRAUD_INVOICE, invoice_id="INV-INT-REPORT-001")
    with patch("core.anomaly.explainer.explain_risk",
               return_value=("Test.", "HOLD")):
        client.post("/invoice/analyze", json=inv)
    r = client.get("/invoice/report/INV-INT-REPORT-001")
    assert r.status_code == 200
    assert r.json()["invoice_id"] == "INV-INT-REPORT-001"

def test_report_not_found():
    r = client.get("/invoice/report/INV-DOES-NOT-EXIST")
    assert r.status_code == 404


# ── Edge Cases ────────────────────────────────────────────────────────────────
def test_invalid_payload_returns_422():
    r = client.post("/invoice/validate", json={"invoice_id": "only-this"})
    assert r.status_code == 422

def test_root_endpoint():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "running"
