"""
Unit tests — Rule Engine (14 checks)
Each test feeds a specific violation and asserts the correct flag is raised.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from core.rules.validator import run_all_checks, _seen_invoices, _vendor_bank_accounts, _vendor_first_seen

@pytest.fixture(autouse=True)
def clear_validator_state():
    """Reset in-memory state before each test to prevent cross-test contamination."""
    _seen_invoices.clear()
    _vendor_bank_accounts.clear()
    _vendor_first_seen.clear()
    yield

def fresh_invoice(**overrides):
    """Base valid invoice — override fields to inject specific violations."""
    import uuid
    base = {
        "invoice_id"      : f"INV-{uuid.uuid4().hex[:6].upper()}",
        "vendor_name"     : f"Vendor-{uuid.uuid4().hex[:4]}",
        "vendor_gstin"    : "27AABCT1332L1ZN",
        "amount"          : 100000.0,
        "tax_amount"      : 18000.0,
        "tax_rate"        : 0.18,
        "invoice_date"    : "2024-03-15",
        "submission_date" : "2024-03-20",
        "po_number"       : "PO-TEST-0001",
        "bank_account"    : "ACC-STABLE-001",
        "payment_terms"   : "Net 30"
    }
    base.update(overrides)
    return base


def flag_names(invoice):
    return [f.check for f in run_all_checks(invoice)]


# ── 1. Missing PO ─────────────────────────────────────────────────────────────
def test_missing_po():
    inv = fresh_invoice(po_number=None)
    assert "Missing PO Number" in flag_names(inv)

# ── 2. GST Mismatch ───────────────────────────────────────────────────────────
def test_gst_mismatch():
    inv = fresh_invoice(amount=100000.0, tax_amount=5000.0)  # should be 18000
    assert "GST Mismatch" in flag_names(inv)

# ── 3. Missing GSTIN ──────────────────────────────────────────────────────────
def test_missing_gstin():
    inv = fresh_invoice(vendor_gstin=None)
    assert "Missing GSTIN" in flag_names(inv)

# ── 4. Future-Dated Invoice ───────────────────────────────────────────────────
def test_future_dated():
    inv = fresh_invoice(invoice_date="2099-01-01", submission_date="2099-01-05")
    assert "Future-Dated Invoice" in flag_names(inv)

# ── 5. Weekend Invoice ────────────────────────────────────────────────────────
def test_weekend_invoice():
    inv = fresh_invoice(invoice_date="2024-03-16")  # Saturday
    assert "Weekend Invoice" in flag_names(inv)

# ── 6. Late Submission ────────────────────────────────────────────────────────
def test_late_submission():
    inv = fresh_invoice(invoice_date="2024-01-01", submission_date="2024-06-01")  # 152 days
    assert "Late Submission" in flag_names(inv)

# ── 7. Changed Bank Account ───────────────────────────────────────────────────
def test_changed_bank_account():
    vendor = "BankChangeVendor-XYZ"
    # First invoice — registers bank account
    first = fresh_invoice(vendor_name=vendor, bank_account="BANK-ORIGINAL")
    run_all_checks(first)
    # Second invoice — different bank account
    second = fresh_invoice(vendor_name=vendor, bank_account="BANK-NEW-999")
    assert "Changed Bank Account" in flag_names(second)

# ── 8. New Vendor High Amount ─────────────────────────────────────────────────
def test_new_vendor_high_amount():
    inv = fresh_invoice(vendor_name="BrandNewVendor-ABC", amount=1000000.0)
    assert "New Vendor High Amount" in flag_names(inv)

# ── 9. Exact Duplicate ────────────────────────────────────────────────────────
def test_exact_duplicate():
    inv = fresh_invoice(invoice_id="INV-DUP-001", vendor_name="DupVendor", amount=50000.0)
    run_all_checks(inv)   # first submission
    dup = dict(inv)       # exact same invoice again
    assert "Exact Duplicate" in flag_names(dup)

# ── 10. Normal Invoice — No Flags ─────────────────────────────────────────────
def test_normal_invoice_no_flags():
    """A clean invoice submitted for the first time should have no HIGH flags."""
    from models.schemas import RiskLevel
    inv = fresh_invoice()
    high_flags = [f for f in run_all_checks(inv) if f.severity == RiskLevel.HIGH]
    assert len(high_flags) == 0
