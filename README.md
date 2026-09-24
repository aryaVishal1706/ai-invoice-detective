# AI Invoice Detective
**Corporate Accounts Payable Fraud Detection System**  
Stack: Python · FastAPI · scikit-learn · pdfplumber · pytesseract

---

## Project Goal
Automatically detect suspicious invoices in corporate IT billing before payment is approved.
Targets duplicate invoices, inflated amounts, ghost vendors, missing POs, tax mismatches, and 14 other anomaly types.

---

## Repository Structure

```
ai_invoice_detective/
│
├── api/                        # FastAPI routes
│   ├── __init__.py
│   ├── invoice.py              # POST /invoice/upload, /validate, /analyze
│   └── report.py               # GET /invoice/{id}/report
│
├── core/                       # Business logic
│   ├── rules/
│   │   ├── __init__.py
│   │   └── validator.py        # 10 rule-based checks
│   ├── anomaly/
│   │   ├── __init__.py
│   │   ├── detector.py         # IsolationForest anomaly scorer
│   │   └── benford.py          # Benford's Law amount analysis
│   └── ocr/
│       ├── __init__.py
│       └── extractor.py        # PDF/Image → structured JSON (Phase 2)
│
├── models/
│   ├── __init__.py
│   ├── schemas.py              # Pydantic request/response models
│   └── trained/                # Saved ML model artifacts (.pkl)
│
├── data/
│   ├── raw/
│   │   ├── invoice_dataset.csv         # Synthetic dataset (9,994 invoices, 18 anomaly types)
│   │   └── wb_sanctioned_firms_clean.csv  # World Bank sanctioned vendors (1,521 records)
│   └── processed/              # Cleaned/feature-engineered data
│
├── scripts/
│   └── generate_dataset.py     # Synthetic dataset generator (re-run to regenerate)
│
├── tests/                      # Unit tests
│
├── docs/
│   ├── AI_Invoice_Detective_Approach.md   # Full approach, pitch guide, technical defense
│   └── project_idea.txt                   # Original project requirement
│
├── main.py                     # FastAPI app entry point
├── requirements.txt            # Python dependencies
├── Dockerfile
└── .env.example
```

---

## Build Phases

**Phase 1 (Current)**
- Synthetic dataset ✅
- Rule-based validation engine
- Benford's Law scorer
- Vendor blacklist lookup (World Bank data)
- FastAPI endpoints
- Risk report generator

**Phase 2**
- IsolationForest model training on client historical data
- OCR invoice parser (PDF + image)
- Model retraining pipeline

---

## Detection Methods

| Method | Anomalies Covered | Dataset Needed |
|---|---|---|
| Rule engine | duplicate, missing PO, tax mismatch, changed bank, round number | None |
| Benford's Law | fabricated/manipulated amounts | None (math) |
| Vendor blacklist | blacklisted vendors | WB sanctions CSV |
| IsolationForest | amount spike, frequency anomaly | Client historical data |

---

## API Endpoints

```
POST /invoice/upload      →  OCR → structured invoice JSON
POST /invoice/validate    →  rule checks → violations list
POST /invoice/analyze     →  anomaly score + blacklist → risk report
GET  /invoice/{id}/report →  full risk report
```

---

## Dataset Summary

| File | Records | Description |
|---|---|---|
| invoice_dataset.csv | 9,994 | Synthetic IT corporate invoices (INR), 18 labeled anomaly types |
| wb_sanctioned_firms_clean.csv | 1,521 | World Bank debarred firms for vendor blacklist lookup |

---

## Quick Start
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Docs
See `docs/AI_Invoice_Detective_Approach.md` for full approach, pitch guide, and technical Q&A.
"# ai-invoice-detective" 
