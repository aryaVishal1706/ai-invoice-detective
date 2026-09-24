"""
Unit tests — IsolationForest anomaly scorer
Tests that the model scores anomalous invoices higher than normal ones.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from core.anomaly.detector import load_model, build_vendor_stats, score_invoice

@pytest.fixture(scope="module")
def model_and_stats():
    return load_model(), build_vendor_stats()


def normal_invoice():
    return {
        "invoice_id"      : "INV-NORM-001",
        "vendor_name"     : "Infosys BPM Ltd",
        "vendor_gstin"    : "27AABCT1332L1ZN",
        "amount"          : 800000.0,
        "tax_amount"      : 144000.0,
        "invoice_date"    : "2024-03-15",
        "submission_date" : "2024-03-20",
        "po_number"       : "PO-1234-ABCD",
        "bank_account"    : "ACC-STABLE-001",
    }


def test_normal_invoice_low_score(model_and_stats):
    """Normal invoice should score below 60."""
    model, stats = model_and_stats
    score = score_invoice(normal_invoice(), model, stats)
    assert score < 60, f"Expected score < 60 for normal invoice, got {score}"


def test_amount_spike_high_score(model_and_stats):
    """Invoice with 10x vendor average should score higher than normal."""
    model, stats = model_and_stats
    normal_score  = score_invoice(normal_invoice(), model, stats)
    spike = dict(normal_invoice())
    spike["amount"]     = 8000000.0   # 10x normal
    spike["tax_amount"] = 1440000.0
    spike_score = score_invoice(spike, model, stats)
    assert spike_score > normal_score, f"Spike score {spike_score} should > normal {normal_score}"


def test_tax_mismatch_high_score(model_and_stats):
    """Invoice with wrong GST should score higher than normal."""
    model, stats = model_and_stats
    normal_score = score_invoice(normal_invoice(), model, stats)
    bad_tax = dict(normal_invoice())
    bad_tax["tax_amount"] = 10000.0   # far below 18%
    bad_score = score_invoice(bad_tax, model, stats)
    assert bad_score > normal_score, f"Bad tax score {bad_score} should > normal {normal_score}"


def test_score_range(model_and_stats):
    """Score must always be between 0 and 100."""
    model, stats = model_and_stats
    score = score_invoice(normal_invoice(), model, stats)
    assert 0 <= score <= 100


def test_missing_vendor_stats(model_and_stats):
    """Unknown vendor should not crash — uses fallback."""
    model, stats = model_and_stats
    inv = dict(normal_invoice())
    inv["vendor_name"] = "CompletelyUnknownVendorXYZ"
    score = score_invoice(inv, model, stats)
    assert 0 <= score <= 100
