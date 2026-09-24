# AI Invoice Detective — Complete Project Documentation
**Corporate IT Accounts Payable Fraud Detection**
**Stack:** Python · FastAPI · IsolationForest · Groq API · React · AWS Lambda · DynamoDB · CodePipeline
**Last Updated:** September 2026

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Detection Approach](#3-detection-approach)
4. [Dataset](#4-dataset)
5. [Project Structure](#5-project-structure)
6. [Backend — API Reference](#6-backend--api-reference)
7. [Frontend](#7-frontend)
8. [AWS Infrastructure](#8-aws-infrastructure)
9. [CI/CD — AWS CodePipeline](#9-cicd--aws-codepipeline)
10. [Local Setup](#10-local-setup)
11. [Deploy to AWS](#11-deploy-to-aws)
12. [Test Results](#12-test-results)
13. [Limitations](#13-limitations)
14. [Pitch](#14-pitch)
15. [Technical Defense](#15-technical-defense)

---

## 1. Project Overview

Corporate IT companies receive hundreds of invoices monthly from vendors like Infosys, Wipro, TCS, HCL.
Manual review misses fraud patterns that cost companies an average of 5% of annual revenue.

**This system automatically:**
- Runs 14 rule-based checks on every invoice
- Scores statistical anomalies using IsolationForest ML
- Generates a plain-language explanation using Groq LLM
- Returns a risk report with score, flags, and recommendation

**Target users:** Finance / Accounts Payable teams in corporate IT companies.

---

## 2. System Architecture

### Local / Development
```
React Frontend (Vite, port 5173)
        ↓ proxy
FastAPI Backend (uvicorn, port 8000)
        ↓
Rule Engine + IsolationForest + Groq API
        ↓
In-memory store (local dev)
```

### Production (AWS)
```
Browser
   ↓
S3 Static Website          ← React frontend
   ↓
API Gateway (HTTP API)     ← HTTPS endpoint
   ↓
Lambda (Python 3.11)       ← FastAPI via Mangum adapter
   ↓
DynamoDB                   ← Persistent report storage
S3 (model bucket)          ← isolation_forest.pkl
```

### CI/CD
```
GitHub push (main branch)
   ↓
AWS CodePipeline triggers
   ↓
CodeBuild
   → pip install + zip backend → upload to S3 → update Lambda
   → npm build frontend → sync to S3 website bucket
```

---

## 3. Detection Approach

Three layers work together. Each has a specific job:

```
Invoice Input
      ↓
[Rule Engine]       → finds violations (facts, binary)
      ↓
[IsolationForest]   → scores statistical abnormality (0–100)
      ↓
[Groq LLM]          → explains risk in plain English
      ↓
Risk Report
```

### Layer 1 — Rule Engine (14 Checks)

| # | Check | Logic | Confidence |
|---|---|---|---|
| 1 | Exact Duplicate | Same invoice_no + vendor + amount already exists | 100% |
| 2 | Near-Duplicate | Same vendor + amount ±1%, invoice_no slightly altered | High |
| 3 | Split Invoice | Same PO, two invoices each ~50% of PO value | High |
| 4 | Missing PO Number | PO field is empty or null | 100% |
| 5 | PO Mismatch | Invoice references non-existent or wrong vendor PO | High |
| 6 | Amount Above PO | Invoice amount exceeds approved PO value | 100% |
| 7 | GST Mismatch | Stated GST ≠ 18% of taxable amount | High |
| 8 | Missing GSTIN | Vendor GST number absent | High |
| 9 | Changed Bank Account | Bank account differs from vendor's last payment | High |
| 10 | New Vendor + High Amount | First invoice from vendor AND amount > ₹5L | High |
| 11 | Weekend Invoice | Invoice dated Saturday or Sunday | Medium |
| 12 | Future-Dated Invoice | Invoice date is in the future | High |
| 13 | Expired PO | Invoice references a PO past its validity date | High |
| 14 | Late Submission | Invoice submitted 90+ days after invoice date | Medium |

### Layer 2 — IsolationForest (ML)

- **Algorithm:** scikit-learn IsolationForest (unsupervised)
- **Trained on:** 8,500 normal invoices from synthetic dataset
- **Features:** amount, submission_lag, amount_vs_vendor_avg, amount_zscore, vendor_monthly_freq, tax_deviation, is_weekend, is_future, missing_po, missing_gstin, is_round
- **Output:** anomaly score 0–100 (higher = more anomalous)
- **Why unsupervised:** No labeled corporate fraud data exists publicly. This is the same approach used by AppZen, Oversight Systems, and SAP Fraud Management.

**Model evaluation results:**

| Anomaly Type | Detection Rate |
|---|---|
| tax_mismatch | 96.4% |
| amount_spike | 83.1% |
| amount_above_po | 54.2% |
| round_number | 51.8% |
| Others (missing_po, duplicate, etc.) | Caught by Rule Engine |

### Layer 3 — Groq LLM Explanation

- **Model:** `qwen/qwen3.8-27b` via Groq API
- **Input:** invoice details + flags + risk score
- **Output:** 3–4 sentence plain-language explanation + recommendation (APPROVE / REVIEW / HOLD)
- **Why Groq:** Fast inference, free tier, sufficient for structured explanation tasks

### Risk Score Calculation
```
risk_score = min(ml_score + (num_flags × 8), 100)

risk_level:
  score >= 70  → HIGH
  score >= 40  → MEDIUM
  score < 40   → LOW
```

### Vendor Blacklist (Optional)
- Client uploads their own blocked vendor list
- Fuzzy name matching via rapidfuzz (handles typos/abbreviations)
- If no list provided → check is skipped automatically

---

## 4. Dataset

### Synthetic Invoice Dataset
| Property | Value |
|---|---|
| File | `data/raw/invoice_dataset.csv` |
| Total records | 9,994 |
| Normal invoices | 8,500 (85%) |
| Anomalous invoices | 1,494 (15%) |
| Anomaly types | 18 (83 records each) |
| Currency | INR |
| Industry | IT Corporate |
| Vendors | 50 real IT company names |

**18 Anomaly types:**
`exact_duplicate` · `near_duplicate` · `split_invoice` · `amount_spike` · `round_number` ·
`amount_below_po` · `amount_above_po` · `new_vendor_high_amount` · `changed_bank_account` ·
`blacklisted_vendor` · `missing_po` · `po_mismatch` · `tax_mismatch` · `missing_gst_number` ·
`weekend_invoice` · `future_dated` · `expired_po` · `late_submission`

To regenerate: `python3 scripts/generate_dataset.py`

### World Bank Sanctions List
| Property | Value |
|---|---|
| File | `data/raw/wb_sanctioned_firms_clean.csv` |
| Records | 1,521 debarred firms |
| Use | Optional vendor blacklist reference |
| Note | Not wired into pipeline by default |

---

## 5. Project Structure

```
ai_invoice_detective/
│
├── main.py                          ← FastAPI app entry point
├── lambda_handler.py                ← Mangum wrapper for AWS Lambda
├── requirements.txt                 ← Python dependencies
├── buildspec.yml                    ← AWS CodeBuild instructions
├── Dockerfile                       ← Local development only
├── .env.example                     ← Environment variable template
├── .gitignore
│
├── api/
│   └── invoice.py                   ← Routes: /validate, /analyze, /report/{id}
│
├── core/
│   ├── rules/
│   │   └── validator.py             ← 14 rule-based checks
│   ├── anomaly/
│   │   ├── detector.py              ← IsolationForest train/load/score
│   │   ├── explainer.py             ← Groq LLM explanation generator
│   │   └── blacklist.py             ← Optional fuzzy vendor blacklist
│   └── ocr/                         ← Phase 2 (PDF/image parsing)
│
├── models/
│   ├── schemas.py                   ← Pydantic: InvoiceInput, Flag, RiskReport
│   └── trained/
│       └── isolation_forest.pkl     ← Trained model (gitignored)
│
├── data/
│   └── raw/
│       ├── invoice_dataset.csv      ← 9,994 synthetic invoices
│       └── wb_sanctioned_firms_clean.csv
│
├── scripts/
│   ├── generate_dataset.py          ← Regenerate synthetic dataset
│   └── evaluate_model.py            ← Model evaluation report
│
├── frontend/frontend/               ← React + Vite app
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── Sidebar.jsx
│       │   └── RiskReport.jsx
│       └── pages/
│           ├── Analyze.jsx          ← Invoice form + result
│           └── History.jsx          ← Past analyses table
│
├── terraform/                       ← AWS infrastructure
│   ├── main.tf                      ← Provider config
│   ├── variables.tf                 ← Region, project, GitHub config
│   ├── s3.tf                        ← 4 S3 buckets
│   ├── dynamodb.tf                  ← Reports table
│   ├── lambda.tf                    ← Lambda function + IAM
│   ├── api_gateway.tf               ← HTTP API Gateway
│   └── codepipeline.tf              ← CodePipeline + CodeBuild + GitHub
│
└── docs/
    ├── AI_Invoice_Detective_Approach.md
    └── project_idea.txt
```

---

## 6. Backend — API Reference

Base URL (local): `http://localhost:8000`
Base URL (AWS): `https://{api-id}.execute-api.ap-south-1.amazonaws.com`

### POST /invoice/validate
Run 14 rule-based checks. Returns violations list.

**Request:**
```json
{
  "invoice_id": "INV-2024-001",
  "vendor_name": "Wipro Technologies",
  "vendor_gstin": "27AABCT1332L1ZN",
  "amount": 500000.0,
  "tax_amount": 90000.0,
  "tax_rate": 0.18,
  "invoice_date": "2024-03-15",
  "submission_date": "2024-03-20",
  "po_number": "PO-1234-ABCD",
  "bank_account": "ACC123456789",
  "payment_terms": "Net 30"
}
```

**Response:**
```json
{
  "invoice_id": "INV-2024-001",
  "violations": 2,
  "flags": [
    { "check": "GST Mismatch", "detail": "...", "severity": "HIGH" }
  ]
}
```

---

### POST /invoice/analyze
Full pipeline: rules + ML score + Groq explanation. Returns complete risk report.

**Response:**
```json
{
  "invoice_id": "INV-2024-001",
  "vendor": "Wipro Technologies",
  "amount": 500000.0,
  "risk_score": 91,
  "risk_level": "HIGH",
  "flags": [...],
  "explanation": "This invoice presents significant risk because...",
  "recommendation": "HOLD"
}
```

---

### GET /invoice/report/{invoice_id}
Retrieve a previously analyzed invoice report from DynamoDB (AWS) or memory (local).

---

## 7. Frontend

**Tech:** React + Vite
**Local URL:** `http://localhost:5173`
**AWS URL:** S3 static website endpoint (output after `terraform apply`)

### Pages

**Analyze Invoice**
- Form with all invoice fields
- Submit → calls `/invoice/analyze`
- Displays risk score ring, flags list, Groq explanation, recommendation badge

**History**
- Table of all analyzed invoices in current session
- Click View → expands full risk report inline

### Run Frontend
```bash
cd frontend/frontend
npm run dev
```

---

## 8. AWS Infrastructure

All resources created by Terraform in `ap-south-1` (Mumbai).

| Resource | Name | Purpose |
|---|---|---|
| S3 | `ai-invoice-detective-lambda-{account}` | Lambda zip deployments |
| S3 | `ai-invoice-detective-models-{account}` | ML model + dataset |
| S3 | `ai-invoice-detective-frontend-{account}` | React static website |
| DynamoDB | `ai-invoice-detective-reports` | Invoice risk reports (pay-per-request) |
| Lambda | `ai-invoice-detective-api` | FastAPI backend (Python 3.11, 512MB, 60s) |
| API Gateway | `ai-invoice-detective-api` | HTTP API → Lambda |

**Cost estimate (low usage):**
- Lambda: ~$0 (1M free requests/month — always free)
- DynamoDB: ~$0 (pay-per-request, 25GB free — always free)
- API Gateway: ~$0 (1M free requests/month — free until March 2027)
- S3: ~$0.02/month
- CodePipeline: **Not used** — costs $1/month, not in free tier

---

## 9. Deployment — Manual

No CI/CD pipeline (CodePipeline costs $1/month — not in free tier after 30 days).
Deploy manually when needed using AWS CLI.

### Deploy Backend (Lambda)
```cmd
pip install -r requirements.txt -t package/
xcopy api package\api\ /E /I /Q
xcopy core package\core\ /E /I /Q
xcopy models package\models\ /E /I /Q
copy main.py package\ && copy lambda_handler.py package\
cd package && zip -r ../lambda.zip . && cd ..
aws s3 cp lambda.zip s3://ai-invoice-detective-lambda-{account}/lambda.zip
aws lambda update-function-code --function-name ai-invoice-detective-api --s3-bucket ai-invoice-detective-lambda-{account} --s3-key lambda.zip
```

### Deploy Frontend (S3)
```cmd
cd frontend\frontend
npm run build
aws s3 sync dist/ s3://ai-invoice-detective-frontend-{account} --delete
```

### Upload ML Model
```cmd
aws s3 cp models/trained/isolation_forest.pkl s3://ai-invoice-detective-models-{account}/isolation_forest.pkl
```

---

## 10. Local Setup

```bash
# 1. Clone repo
git clone https://github.com/aryaVishal1706/ai-invoice-detective.git
cd ai_invoice_detective

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — add your Groq API key
# Get free key at: console.groq.com

# 4. Train the model
PYTHONPATH=. python3 -c "from core.anomaly.detector import train_model; train_model()"

# 5. Start backend
uvicorn main:app --reload --port 8000

# 6. Start frontend (new terminal)
cd frontend/frontend
npm install
npm run dev

# 7. Open
# Backend API docs: http://localhost:8000/docs
# Frontend:         http://localhost:5173
```

---

## 11. Deploy to AWS

```bash
# Prerequisites: AWS CLI configured, Terraform installed

# 1. Deploy infrastructure
cd terraform
terraform init
terraform apply -var="groq_api_key=your_groq_key_here"

# Note the outputs:
#   api_url      → paste into frontend/.env or vite.config.js
#   frontend_url → your app URL

# 2. Authorize GitHub connection (one time)
# AWS Console → CodePipeline → Connections → Click Authorize

# 3. Upload model to S3
aws s3 cp models/trained/isolation_forest.pkl \
  s3://ai-invoice-detective-models-{account}/isolation_forest.pkl

# 4. Push code → pipeline triggers automatically
git add .
git commit -m "deploy"
git push origin main

# 5. Monitor pipeline
# AWS Console → CodePipeline → ai-invoice-detective-pipeline
```

---

## 12. Test Results

### How to Run Tests

```cmd
# Activate venv first
venv\Scripts\activate

# Run all tests (unit + integration)
venv\Scripts\pytest tests/test_rules.py tests/test_anomaly.py tests/test_api.py -v

# Run AI quality tests (uses real Groq API)
venv\Scripts\pytest tests/test_ai_quality.py -v

# Run everything
venv\Scripts\pytest tests/ -v
```

### Test Files

| File | Tests | What it covers |
|---|---|---|
| `tests/test_rules.py` | 10 | Each rule check individually (missing PO, GST mismatch, duplicate, etc.) |
| `tests/test_anomaly.py` | 5 | IsolationForest scoring — normal vs anomalous invoices |
| `tests/test_api.py` | 11 | Full API pipeline, edge cases, 404, 422 validation |
| `tests/test_ai_quality.py` | 4 | Groq LLM output quality — recommendation correctness, no hallucination |

### Results — Unit + Integration Tests (26 tests)

```
26 passed in 93s — platform win32, Python 3.13.3
```

| Test | Result |
|---|---|
| test_missing_po | ✅ PASSED |
| test_gst_mismatch | ✅ PASSED |
| test_missing_gstin | ✅ PASSED |
| test_future_dated | ✅ PASSED |
| test_weekend_invoice | ✅ PASSED |
| test_late_submission | ✅ PASSED |
| test_changed_bank_account | ✅ PASSED |
| test_new_vendor_high_amount | ✅ PASSED |
| test_exact_duplicate | ✅ PASSED |
| test_normal_invoice_no_flags | ✅ PASSED |
| test_normal_invoice_low_score | ✅ PASSED |
| test_amount_spike_high_score | ✅ PASSED |
| test_tax_mismatch_high_score | ✅ PASSED |
| test_score_range | ✅ PASSED |
| test_missing_vendor_stats | ✅ PASSED |
| test_validate_clean_invoice | ✅ PASSED |
| test_validate_fraud_invoice_has_flags | ✅ PASSED |
| test_validate_missing_po_flagged | ✅ PASSED |
| test_validate_gst_mismatch_flagged | ✅ PASSED |
| test_analyze_returns_risk_report | ✅ PASSED |
| test_analyze_fraud_invoice_high_risk | ✅ PASSED |
| test_analyze_recommendation_hold_for_high_risk | ✅ PASSED |
| test_report_retrieval_after_analyze | ✅ PASSED |
| test_report_not_found | ✅ PASSED |
| test_invalid_payload_returns_422 | ✅ PASSED |
| test_root_endpoint | ✅ PASSED |

### Results — AI Quality Tests (4 tests, real Groq API)

```
4 passed in 2.25s
```

| Test | Result | What was verified |
|---|---|---|
| test_explanation_contains_recommendation | ✅ PASSED | Groq output always contains APPROVE/REVIEW/HOLD |
| test_high_risk_gets_hold_recommendation | ✅ PASSED | Score 95 + 4 HIGH flags → HOLD |
| test_no_flags_returns_approve | ✅ PASSED | No flags → APPROVE without calling Groq |
| test_explanation_mentions_vendor | ✅ PASSED | Explanation references the vendor name |

### Model Evaluation (9,994 invoices)

```
PYTHONPATH=. python3 scripts/evaluate_model.py
```

| Metric | Value |
|---|---|
| Overall Accuracy | 87% |
| Anomaly Precision | 71% |
| Anomaly Recall | 19% (ML alone — rules cover the rest) |
| tax_mismatch detection | 96.4% |
| amount_spike detection | 83.1% |
| amount_above_po detection | 54.2% |

Note: Low ML recall is by design — structural anomalies (missing PO, duplicate, weekend) are caught by the rule engine with 100% accuracy. ML handles statistical outliers the rules can't define.

---

## 13. Limitations

- IsolationForest trained on synthetic data — accuracy improves with real client AP history
- Vendor blacklist is optional — skipped if not provided
- OCR is Phase 2 — Phase 1 accepts structured JSON input only
- Lambda cold start ~2–3 seconds on first request (warms up after)
- Does not detect internal staff collusion (requires ERP integration)
- Groq API dependency — if Groq is down, explanation fails (flags + score still work)

---

## 14. Pitch (30 Seconds)

> "Your AP team manually reviews hundreds of invoices every month.
> This system checks every invoice automatically — duplicates, inflated amounts,
> missing approvals, changed bank details — in seconds, before payment goes out.
> It then explains exactly why an invoice is suspicious in plain English.
> Your team only reviews what's actually risky."

---

## 15. Technical Defense

| Question | Answer |
|---|---|
| Why IsolationForest not supervised? | No labeled corporate fraud data exists publicly. Unsupervised is industry standard — AppZen, SAP, Oversight all use this approach. |
| Why Groq and not OpenAI? | Groq is faster, has a free tier, and qwen3.8-27b is sufficient for structured explanation tasks. |
| What if client has no blacklist? | Blacklist check is skipped. System runs fully on rules + ML. |
| False positive rate? | Near zero for hard rules (binary). ML threshold is tunable per client risk tolerance. |
| Why synthetic dataset? | No public labeled corporate AP fraud dataset exists. Synthetic data gives clean labeled ground truth for MVP. Replaced by client data in production. |
| Why Lambda not EC2? | Pay-per-use — near zero cost for low usage. No server management. Scales automatically. |
| Why DynamoDB not RDS? | Serverless, no VPC required, pay-per-request, native AWS Lambda integration. |
| Why CodePipeline not GitHub Actions? | Fully AWS-native, no external credentials needed, integrates directly with Lambda and S3. |

---

*AI Invoice Detective · Corporate IT AP Fraud Detection · v1.0*
*GitHub: github.com/aryaVishal1706/ai-invoice-detective*
