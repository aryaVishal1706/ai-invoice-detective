from datetime import datetime, date
from typing import Optional
from models.schemas import Flag, RiskLevel

GST_RATE = 0.18
GST_TOLERANCE = 0.01          # 1% tolerance on GST calculation
LATE_SUBMISSION_DAYS = 90
HIGH_AMOUNT_NEW_VENDOR = 500000   # ₹5L threshold for new vendor flag

# In-memory stores — replaced by DB in production
_seen_invoices: dict = {}         # invoice_id → invoice data
_vendor_bank_accounts: dict = {}  # vendor_name → last known bank account
_vendor_first_seen: set = set()   # vendor names seen before
_po_registry: set = set()         # known valid PO numbers
_expired_pos: set = set()         # expired PO numbers


def load_po_registry(valid_pos: list, expired_pos: list):
    """Pre-load PO registry from client data."""
    _po_registry.update(valid_pos)
    _expired_pos.update(expired_pos)


def run_all_checks(invoice: dict) -> list[Flag]:
    """
    Run all 14 rule-based checks on an invoice.
    Returns a list of Flag objects for each violation found.
    """
    flags = []
    inv_id      = invoice["invoice_id"]
    vendor      = invoice["vendor_name"]
    amount      = invoice["amount"]
    tax         = invoice["tax_amount"]
    gstin       = invoice.get("vendor_gstin")
    po          = invoice.get("po_number")
    bank        = invoice["bank_account"]
    inv_date    = invoice["invoice_date"]
    sub_date    = invoice["submission_date"]

    # 1. Exact Duplicate
    key = f"{inv_id}_{vendor}_{amount}"
    if key in _seen_invoices:
        flags.append(Flag(
            check="Exact Duplicate",
            detail=f"Invoice {inv_id} from {vendor} for ₹{amount:,.0f} already exists.",
            severity=RiskLevel.HIGH
        ))

    # 2. Near-Duplicate (same vendor + amount ±1%, different invoice_id)
    for seen_key, seen in _seen_invoices.items():
        if (seen["vendor_name"] == vendor and
                seen["invoice_id"] != inv_id and
                abs(seen["amount"] - amount) / max(amount, 1) <= 0.01):
            flags.append(Flag(
                check="Near-Duplicate",
                detail=f"Amount ₹{amount:,.0f} is within 1% of invoice {seen['invoice_id']} from same vendor.",
                severity=RiskLevel.HIGH
            ))
            break

    # 3. Split Invoice (same PO, amount ~50% of another invoice on same PO)
    if po:
        for seen in _seen_invoices.values():
            if (seen.get("po_number") == po and
                    seen["vendor_name"] == vendor and
                    abs(seen["amount"] - amount) / max(amount, 1) <= 0.05):
                flags.append(Flag(
                    check="Split Invoice",
                    detail=f"Two similar-amount invoices found against PO {po}. Possible invoice splitting.",
                    severity=RiskLevel.HIGH
                ))
                break

    # 4. Missing PO Number
    if not po:
        flags.append(Flag(
            check="Missing PO Number",
            detail="No purchase order reference found on this invoice.",
            severity=RiskLevel.HIGH
        ))

    # 5. PO Mismatch (PO not in known registry)
    if po and _po_registry and po not in _po_registry and po not in _expired_pos:
        flags.append(Flag(
            check="PO Mismatch",
            detail=f"PO number {po} does not exist in the system.",
            severity=RiskLevel.HIGH
        ))

    # 6. Expired PO
    if po and po in _expired_pos:
        flags.append(Flag(
            check="Expired PO",
            detail=f"PO number {po} has expired.",
            severity=RiskLevel.HIGH
        ))

    # 7. GST Mismatch
    expected_gst = round(amount * GST_RATE, 2)
    if abs(tax - expected_gst) / max(expected_gst, 1) > GST_TOLERANCE:
        flags.append(Flag(
            check="GST Mismatch",
            detail=f"Stated GST ₹{tax:,.2f} does not match expected 18% = ₹{expected_gst:,.2f}.",
            severity=RiskLevel.HIGH
        ))

    # 8. Missing GSTIN
    if not gstin:
        flags.append(Flag(
            check="Missing GSTIN",
            detail="Vendor GST Identification Number is missing.",
            severity=RiskLevel.MEDIUM
        ))

    # 9. Changed Bank Account
    if vendor in _vendor_bank_accounts and _vendor_bank_accounts[vendor] != bank:
        flags.append(Flag(
            check="Changed Bank Account",
            detail=f"Bank account for {vendor} has changed since last payment.",
            severity=RiskLevel.HIGH
        ))

    # 10. New Vendor + High Amount
    if vendor not in _vendor_first_seen and amount >= HIGH_AMOUNT_NEW_VENDOR:
        flags.append(Flag(
            check="New Vendor High Amount",
            detail=f"First invoice from {vendor} is ₹{amount:,.0f} — above ₹{HIGH_AMOUNT_NEW_VENDOR:,.0f} threshold.",
            severity=RiskLevel.HIGH
        ))

    # 11. Weekend Invoice
    try:
        d = datetime.strptime(inv_date, "%Y-%m-%d").date()
        if d.weekday() >= 5:
            flags.append(Flag(
                check="Weekend Invoice",
                detail=f"Invoice is dated {inv_date} ({d.strftime('%A')}).",
                severity=RiskLevel.MEDIUM
            ))
    except ValueError:
        pass

    # 12. Future-Dated Invoice
    try:
        d = datetime.strptime(inv_date, "%Y-%m-%d").date()
        if d > date.today():
            flags.append(Flag(
                check="Future-Dated Invoice",
                detail=f"Invoice date {inv_date} is in the future.",
                severity=RiskLevel.HIGH
            ))
    except ValueError:
        pass

    # 13. Late Submission
    try:
        inv_dt = datetime.strptime(inv_date, "%Y-%m-%d").date()
        sub_dt = datetime.strptime(sub_date, "%Y-%m-%d").date()
        gap = (sub_dt - inv_dt).days
        if gap > LATE_SUBMISSION_DAYS:
            flags.append(Flag(
                check="Late Submission",
                detail=f"Invoice submitted {gap} days after invoice date (threshold: {LATE_SUBMISSION_DAYS} days).",
                severity=RiskLevel.MEDIUM
            ))
    except ValueError:
        pass

    # 14. Amount Below PO (underbilling — kickback signal)
    # Requires PO amount context; flagged only when PO amount is known
    # Handled in API layer when PO amount is available

    # Register invoice after checks
    _seen_invoices[key] = invoice
    _vendor_bank_accounts[vendor] = bank
    _vendor_first_seen.add(vendor)

    return flags
