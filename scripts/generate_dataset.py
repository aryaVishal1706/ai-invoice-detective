import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker('en_IN')
np.random.seed(42)
random.seed(42)

# ── Config ────────────────────────────────────────────────────────────────────
TOTAL_INVOICES   = 10000
ANOMALY_RATIO    = 0.15          # 15% anomalous
NUM_VENDORS      = 50
GST_RATE         = 0.18          # 18% GST for IT services
START_DATE       = datetime(2023, 1, 1)
END_DATE         = datetime(2024, 12, 31)

# ── Vendor Master ─────────────────────────────────────────────────────────────
IT_VENDORS = [
    "Infosys BPM Ltd", "Wipro Technologies", "HCL Services Pvt Ltd",
    "TCS Digital Solutions", "Tech Mahindra Ltd", "Mphasis Corp",
    "Hexaware Technologies", "Mindtree Solutions", "NIIT Technologies",
    "Zensar IT Services", "Persistent Systems", "Cyient Ltd",
    "Mastech Digital", "Sonata Software", "Kellton Tech",
    "Saksoft Ltd", "Trigent Software", "Cigniti Technologies",
    "Infostretch Corp", "Happiest Minds", "Birlasoft Ltd",
    "KPIT Technologies", "Tata Elxsi", "Sasken Technologies",
    "Geometric Ltd", "Cybage Software", "Nihilent Ltd",
    "Datamatics Global", "Ramsol Pvt Ltd", "Xoriant Solutions",
    "Softcell Technologies", "Nucleus Software", "Newgen Software",
    "Intellect Design", "Majesco Ltd", "3i Infotech",
    "Tanla Platforms", "Subex Ltd", "Onward Technologies",
    "Saksoft Ltd", "Accelya Solutions", "KALS Info Systems",
    "Dynacons Systems", "Compuage Infocom", "Rashi Peripherals",
    "Redington India", "Ingram Micro India", "Supertron Electronics",
    "Iris Computers", "Savex Technologies"
]

# Each vendor has a baseline monthly billing amount (realistic IT ranges)
vendor_baselines = {v: random.randint(50000, 2000000) for v in IT_VENDORS}
vendor_bank_accounts = {v: fake.bban() for v in IT_VENDORS}
vendor_gstins = {v: fake.bothify("##?????####?#?#").upper() for v in IT_VENDORS}
vendor_first_invoice = {v: True for v in IT_VENDORS}  # track new vendors

# PO pool
po_pool = [f"PO-{fake.bothify('####-????').upper()}" for _ in range(300)]
expired_po_pool = [f"PO-EXP-{fake.bothify('####').upper()}" for _ in range(20)]

# ── Helpers ───────────────────────────────────────────────────────────────────
def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

def business_date(start, end):
    d = random_date(start, end)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d

def weekend_date(start, end):
    d = random_date(start, end)
    while d.weekday() < 5:
        d += timedelta(days=1)
    return d

def format_inr(amount):
    return round(amount, 2)

# ── Normal Invoice Generator ──────────────────────────────────────────────────
def make_normal_invoice(idx, vendor):
    base = vendor_baselines[vendor]
    amount = format_inr(random.uniform(base * 0.7, base * 1.3))
    tax    = format_inr(amount * GST_RATE)
    inv_date = business_date(START_DATE, END_DATE)
    sub_date = inv_date + timedelta(days=random.randint(1, 15))
    return {
        "invoice_id"       : f"INV-{idx:05d}",
        "vendor_name"      : vendor,
        "vendor_gstin"     : vendor_gstins[vendor],
        "amount"           : amount,
        "tax_amount"       : tax,
        "tax_rate"         : GST_RATE,
        "invoice_date"     : inv_date.strftime("%Y-%m-%d"),
        "submission_date"  : sub_date.strftime("%Y-%m-%d"),
        "po_number"        : random.choice(po_pool),
        "bank_account"     : vendor_bank_accounts[vendor],
        "payment_terms"    : random.choice(["Net 30", "Net 45", "Net 60"]),
        "is_anomaly"       : 0,
        "anomaly_type"     : "none"
    }

# ── Anomaly Injectors ─────────────────────────────────────────────────────────
def inject_exact_duplicate(base):
    r = base.copy()
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "exact_duplicate"
    return r

def inject_near_duplicate(base, idx):
    r = base.copy()
    r["invoice_id"]   = f"INV-{idx:05d}"
    r["invoice_id"]   = base["invoice_id"].replace("1","l").replace("0","O")
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "near_duplicate"
    return r

def inject_split_invoice(base, idx):
    r = base.copy()
    r["invoice_id"]   = f"INV-{idx:05d}"
    r["amount"]       = format_inr(base["amount"] / 2)
    r["tax_amount"]   = format_inr(r["amount"] * GST_RATE)
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "split_invoice"
    return r

def inject_amount_spike(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    r["amount"]       = format_inr(vendor_baselines[vendor] * random.uniform(4, 8))
    r["tax_amount"]   = format_inr(r["amount"] * GST_RATE)
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "amount_spike"
    return r

def inject_round_number(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    base_amt = vendor_baselines[vendor]
    magnitude = 10 ** (len(str(int(base_amt))) - 1)
    r["amount"]       = float(round(random.randint(1, 20) * magnitude))
    r["tax_amount"]   = format_inr(r["amount"] * GST_RATE)
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "round_number"
    return r

def inject_amount_below_po(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    r["amount"]       = format_inr(vendor_baselines[vendor] * random.uniform(0.1, 0.4))
    r["tax_amount"]   = format_inr(r["amount"] * GST_RATE)
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "amount_below_po"
    return r

def inject_amount_above_po(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    r["amount"]       = format_inr(vendor_baselines[vendor] * random.uniform(2, 3))
    r["tax_amount"]   = format_inr(r["amount"] * GST_RATE)
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "amount_above_po"
    return r

def inject_new_vendor_high_amount(idx):
    vendor = f"NewVendor_{idx} IT Solutions Pvt Ltd"
    amount = format_inr(random.uniform(1500000, 5000000))
    tax    = format_inr(amount * GST_RATE)
    inv_date = business_date(START_DATE, END_DATE)
    return {
        "invoice_id"       : f"INV-{idx:05d}",
        "vendor_name"      : vendor,
        "vendor_gstin"     : fake.bothify("##?????####?#?#").upper(),
        "amount"           : amount,
        "tax_amount"       : tax,
        "tax_rate"         : GST_RATE,
        "invoice_date"     : inv_date.strftime("%Y-%m-%d"),
        "submission_date"  : (inv_date + timedelta(days=2)).strftime("%Y-%m-%d"),
        "po_number"        : random.choice(po_pool),
        "bank_account"     : fake.bban(),
        "payment_terms"    : "Net 30",
        "is_anomaly"       : 1,
        "anomaly_type"     : "new_vendor_high_amount"
    }

def inject_changed_bank(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    r["bank_account"] = fake.bban()   # different from vendor master
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "changed_bank_account"
    return r

def inject_blacklisted_vendor(idx):
    # Use actual name from WB sanctions list
    blacklisted = [
        "BMR CONSULTORIA Y CONSTRUCCIÓN S.A.C.",
        "ASTRA BIOPHARMACEUTICALS LIMITED",
        "PSL ENGINEERING PRIVATE LIMITED",
        "SOFTWARE DEVELOPMENT & IT SOLUTION JOINT STOCK COMPANY"
    ]
    vendor = random.choice(blacklisted)
    amount = format_inr(random.uniform(100000, 1000000))
    tax    = format_inr(amount * GST_RATE)
    inv_date = business_date(START_DATE, END_DATE)
    return {
        "invoice_id"       : f"INV-{idx:05d}",
        "vendor_name"      : vendor,
        "vendor_gstin"     : fake.bothify("##?????####?#?#").upper(),
        "amount"           : amount,
        "tax_amount"       : tax,
        "tax_rate"         : GST_RATE,
        "invoice_date"     : inv_date.strftime("%Y-%m-%d"),
        "submission_date"  : (inv_date + timedelta(days=3)).strftime("%Y-%m-%d"),
        "po_number"        : random.choice(po_pool),
        "bank_account"     : fake.bban(),
        "payment_terms"    : "Net 30",
        "is_anomaly"       : 1,
        "anomaly_type"     : "blacklisted_vendor"
    }

def inject_missing_po(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    r["po_number"]    = None
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "missing_po"
    return r

def inject_po_mismatch(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    r["po_number"]    = f"PO-FAKE-{random.randint(9000,9999)}"
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "po_mismatch"
    return r

def inject_tax_mismatch(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    r["tax_amount"]   = format_inr(r["amount"] * random.choice([0.05, 0.12, 0.28]))
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "tax_mismatch"
    return r

def inject_missing_gstin(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    r["vendor_gstin"] = None
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "missing_gst_number"
    return r

def inject_weekend_invoice(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    wdate = weekend_date(START_DATE, END_DATE)
    r["invoice_date"] = wdate.strftime("%Y-%m-%d")
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "weekend_invoice"
    return r

def inject_future_dated(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    future = datetime(2025, random.randint(1,12), random.randint(1,28))
    r["invoice_date"] = future.strftime("%Y-%m-%d")
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "future_dated"
    return r

def inject_expired_po(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    r["po_number"]    = random.choice(expired_po_pool)
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "expired_po"
    return r

def inject_late_submission(base, idx, vendor):
    r = make_normal_invoice(idx, vendor)
    inv_date = datetime.strptime(r["invoice_date"], "%Y-%m-%d")
    r["submission_date"] = (inv_date + timedelta(days=random.randint(95, 180))).strftime("%Y-%m-%d")
    r["is_anomaly"]   = 1
    r["anomaly_type"] = "late_submission"
    return r

# ── All 18 anomaly injectors mapped ──────────────────────────────────────────
ANOMALY_INJECTORS = [
    "exact_duplicate", "near_duplicate", "split_invoice",
    "amount_spike", "round_number", "amount_below_po", "amount_above_po",
    "new_vendor_high_amount", "changed_bank_account", "blacklisted_vendor",
    "missing_po", "po_mismatch", "tax_mismatch", "missing_gst_number",
    "weekend_invoice", "future_dated", "expired_po", "late_submission"
]

# ── Generate Dataset ──────────────────────────────────────────────────────────
records = []
idx = 1
normal_count  = int(TOTAL_INVOICES * (1 - ANOMALY_RATIO))
anomaly_count = TOTAL_INVOICES - normal_count
anomalies_per_type = anomaly_count // len(ANOMALY_INJECTORS)

# Normal invoices
for _ in range(normal_count):
    vendor = random.choice(IT_VENDORS)
    records.append(make_normal_invoice(idx, vendor))
    idx += 1

# Anomalous invoices — equal distribution across all 18 types
for atype in ANOMALY_INJECTORS:
    for _ in range(anomalies_per_type):
        vendor = random.choice(IT_VENDORS)
        base   = make_normal_invoice(idx, vendor)

        if atype == "exact_duplicate":
            r = inject_exact_duplicate(base); r["invoice_id"] = f"INV-{idx:05d}"
        elif atype == "near_duplicate":
            r = inject_near_duplicate(base, idx)
        elif atype == "split_invoice":
            r = inject_split_invoice(base, idx)
        elif atype == "amount_spike":
            r = inject_amount_spike(base, idx, vendor)
        elif atype == "round_number":
            r = inject_round_number(base, idx, vendor)
        elif atype == "amount_below_po":
            r = inject_amount_below_po(base, idx, vendor)
        elif atype == "amount_above_po":
            r = inject_amount_above_po(base, idx, vendor)
        elif atype == "new_vendor_high_amount":
            r = inject_new_vendor_high_amount(idx)
        elif atype == "changed_bank_account":
            r = inject_changed_bank(base, idx, vendor)
        elif atype == "blacklisted_vendor":
            r = inject_blacklisted_vendor(idx)
        elif atype == "missing_po":
            r = inject_missing_po(base, idx, vendor)
        elif atype == "po_mismatch":
            r = inject_po_mismatch(base, idx, vendor)
        elif atype == "tax_mismatch":
            r = inject_tax_mismatch(base, idx, vendor)
        elif atype == "missing_gst_number":
            r = inject_missing_gstin(base, idx, vendor)
        elif atype == "weekend_invoice":
            r = inject_weekend_invoice(base, idx, vendor)
        elif atype == "future_dated":
            r = inject_future_dated(base, idx, vendor)
        elif atype == "expired_po":
            r = inject_expired_po(base, idx, vendor)
        elif atype == "late_submission":
            r = inject_late_submission(base, idx, vendor)

        records.append(r)
        idx += 1

# Shuffle
random.shuffle(records)

df = pd.DataFrame(records)
df.to_csv("/mnt/c/Coder/temp/Automation/datasets/invoice_dataset.csv", index=False)

# Summary
print(f"Total records    : {len(df)}")
print(f"Normal invoices  : {len(df[df['is_anomaly']==0])}")
print(f"Anomalous        : {len(df[df['is_anomaly']==1])}")
print(f"\nAnomaly breakdown:")
print(df[df['is_anomaly']==1]['anomaly_type'].value_counts().to_string())
print(f"\nFile saved: invoice_dataset.csv")
