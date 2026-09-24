from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class InvoiceInput(BaseModel):
    """Incoming invoice data for validation and analysis."""
    invoice_id: str
    vendor_name: str
    vendor_gstin: Optional[str] = None
    amount: float
    tax_amount: float
    tax_rate: float = 0.18
    invoice_date: str           # YYYY-MM-DD
    submission_date: str        # YYYY-MM-DD
    po_number: Optional[str] = None
    bank_account: str
    payment_terms: Optional[str] = None


class Flag(BaseModel):
    """A single detected violation or anomaly."""
    check: str
    detail: str
    severity: RiskLevel


class RiskReport(BaseModel):
    """Full risk report returned after analysis."""
    invoice_id: str
    vendor: str
    amount: float
    risk_score: int                  # 0–100
    risk_level: RiskLevel
    flags: List[Flag]
    explanation: str                 # Groq-generated plain English summary
    recommendation: str              # APPROVE / REVIEW / HOLD
