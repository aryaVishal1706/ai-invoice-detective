"""Export vendor stats to JSON for ML Lambda to use."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.anomaly.detector import build_vendor_stats

stats = build_vendor_stats()
# Convert numpy types to native Python
clean = {k: {kk: float(vv) for kk, vv in v.items()} for k, v in stats.items()}
with open("data/raw/vendor_stats.json", "w") as f:
    json.dump(clean, f)
print(f"Exported {len(clean)} vendor stats → data/raw/vendor_stats.json")
