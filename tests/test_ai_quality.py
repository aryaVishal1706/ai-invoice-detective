"""
AI Output Quality tests — Groq explanation validation
Tests that the LLM output is coherent, relevant, and not hallucinating.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
load_dotenv()

from models.schemas import Flag, RiskLevel


def make_flags(*checks):
    return [Flag(check=c, detail=f"{c} detected", severity=RiskLevel.HIGH) for c in checks]


# ── Test with real Groq call ──────────────────────────────────────────────────
def test_explanation_contains_recommendation():
    """Groq output must contain a recommendation line."""
    from core.anomaly.explainer import explain_risk
    flags = make_flags("Missing PO Number", "GST Mismatch")
    explanation, recommendation = explain_risk(
        "INV-AI-001", "Test Vendor", 500000.0, 85, flags
    )
    assert recommendation in ("APPROVE", "REVIEW", "HOLD")
    assert len(explanation) > 50


def test_high_risk_gets_hold_recommendation():
    """Score 90+ with multiple HIGH flags should result in HOLD."""
    from core.anomaly.explainer import explain_risk
    flags = make_flags("Missing PO Number", "GST Mismatch", "Changed Bank Account", "New Vendor High Amount")
    _, recommendation = explain_risk(
        "INV-AI-002", "Suspicious Vendor", 9500000.0, 95, flags
    )
    assert recommendation == "HOLD"


def test_no_flags_returns_approve():
    """Invoice with no flags should return APPROVE without calling Groq."""
    from core.anomaly.explainer import explain_risk
    explanation, recommendation = explain_risk(
        "INV-AI-003", "Clean Vendor", 100000.0, 10, []
    )
    assert recommendation == "APPROVE"
    assert "No anomalies" in explanation


def test_explanation_mentions_vendor():
    """Groq explanation should reference the vendor name."""
    from core.anomaly.explainer import explain_risk
    flags = make_flags("Missing PO Number")
    explanation, _ = explain_risk(
        "INV-AI-004", "Infosys BPM Ltd", 500000.0, 75, flags
    )
    assert "Infosys" in explanation or "vendor" in explanation.lower()
