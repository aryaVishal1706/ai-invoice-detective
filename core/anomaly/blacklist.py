from rapidfuzz import process, fuzz

_blacklist: list[str] = []


def load_blacklist(csv_path: str):
    """Load vendor names from client-provided CSV or default WB sanctions list."""
    global _blacklist
    try:
        import pandas as pd
        df  = pd.read_csv(csv_path)
        col = "SUPP_NAME" if "SUPP_NAME" in df.columns else df.columns[0]
        _blacklist = df[col].dropna().str.upper().tolist()
        print(f"Blacklist loaded: {len(_blacklist)} vendors from {csv_path}")
    except Exception as e:
        print(f"Blacklist not loaded: {e}")
        _blacklist = []


def check_blacklist(vendor_name: str, threshold: int = 90) -> dict | None:
    """
    Fuzzy match vendor name against blacklist.
    Returns match details if score >= threshold, else None.
    Skipped automatically if blacklist is empty.
    """
    if not _blacklist:
        return None

    match, score, _ = process.extractOne(
        vendor_name.upper(), _blacklist, scorer=fuzz.token_sort_ratio
    )

    if score >= threshold:
        return {"matched": match, "score": score}
    return None
