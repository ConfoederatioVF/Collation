import glob
import json
import os
from collections import defaultdict

BASE = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional"
STADESTER_DIR = r"F:\Active Projects\Project 1436 - Dataview\data\stadester\stadester_2.0"

BENCHMARK_BUCKETS = [
    ("<=0 BCE/CE", -10000, 0),
    ("1-500", 1, 500),
    ("501-1000", 501, 1000),
    ("1001-1400", 1001, 1400),
    ("1401-1524", 1401, 1524),
    ("1525-1650", 1525, 1650),
    ("1651-1750", 1651, 1750),
    ("1751-1829", 1751, 1829),
    ("1830-1899", 1830, 1899),
    ("1900-1949", 1900, 1949),
    ("1950-1989", 1950, 1989),
    ("1990-2009", 1990, 2009),
    ("2010-2026", 2010, 2026),
]

def load_settlements(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return []
    if isinstance(d, list):
        return [x for x in d if isinstance(x, dict)]
    if isinstance(d, dict):
        if isinstance(d.get("settlements"), list):
            return [x for x in d["settlements"] if isinstance(x, dict)]
        if isinstance(d.get("cities"), list):
            return [x for x in d["cities"] if isinstance(x, dict)]
        return [v for v in d.values() if isinstance(v, dict) and ("population" in v or "populations" in v or "coords" in v)]
    return []

def extract_years(item):
    pop = item.get("population") or item.get("populations") or {}
    yrs = set()
    if isinstance(pop, dict):
        for k, v in pop.items():
            if v is None:
                continue
            try:
                if float(v) <= 0:
                    continue
            except Exception:
                continue
            try:
                y = int(float(str(k).split(".")[0]))
                yrs.add(y)
            except Exception:
                pass
    return yrs

print("=== 1. PEER VISCOUNT REGIONS (SVEA GAZETTEERS) ===")
regions = sorted([d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d)) and not d.startswith("_")])
for reg in regions:
    rdir = os.path.join(BASE, reg)
    files = sorted(glob.glob(os.path.join(rdir, "**", "*_settlements.json"), recursive=True))
    files = [f for f in files if "_shared" not in f and "backup" not in f.lower()]
    if not files:
        continue
    total_rows = 0
    unique_keys = set()
    bucket_counts = defaultdict(set)
    for fp in files:
        items = load_settlements(fp)
        total_rows += len(items)
        for idx, it in enumerate(items):
            nm = str(it.get("name") or it.get("settlement_name") or f"row_{idx}").strip().lower()
            co = str(it.get("country") or "").strip().lower()
            k = (nm, co, os.path.basename(fp))
            unique_keys.add((nm, co))
            yrs = extract_years(it)
            for label, y0, y1 in BENCHMARK_BUCKETS:
                if any(y0 <= y <= y1 for y in yrs):
                    bucket_counts[label].add((nm, co))
    b_str = " | ".join(f"{lbl}:{len(bucket_counts[lbl])}" for lbl, _, _ in BENCHMARK_BUCKETS)
    print(f"{reg:10s} ch={len(files):2d} rows={total_rows:6d} uniq={len(unique_keys):6d} || {b_str}")

print("\n=== 2. STADESTER 2.0 SHARDS IN DATAVIEW ===")
if os.path.exists(STADESTER_DIR):
    for fp in sorted(glob.glob(os.path.join(STADESTER_DIR, "*.json"))):
        bn = os.path.basename(fp)
        if "manifest" in bn:
            continue
        try:
            d = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        n = len(d)
        by_b = defaultdict(int)
        for k, v in d.items():
            if not isinstance(v, dict):
                continue
            yrs = extract_years(v)
            for label, y0, y1 in BENCHMARK_BUCKETS:
                if any(y0 <= y <= y1 for y in yrs):
                    by_b[label] += 1
        b_str = " | ".join(f"{lbl}:{by_b[lbl]}" for lbl, _, _ in BENCHMARK_BUCKETS)
        print(f"{bn:20s} cities={n:6d} || {b_str}")

print("\n=== 3. QUIPU CHAPTER-BY-CHAPTER SETTLEMENT DETAIL ===")
qdir = os.path.join(BASE, "QUIPU")
qfiles = sorted(glob.glob(os.path.join(qdir, "**", "*_settlements.json"), recursive=True))
qfiles = [f for f in qfiles if "_shared" not in f]
for fp in qfiles:
    rel = os.path.relpath(fp, qdir)
    items = load_settlements(fp)
    yc = defaultdict(int)
    min_pop = 10**9
    max_pop = 0
    for it in items:
        pop = it.get("population") or {}
        if isinstance(pop, dict):
            for k, v in pop.items():
                try:
                    fv = float(v)
                    if fv > 0:
                        y = int(float(str(k).split(".")[0]))
                        yc[y] += 1
                        if fv < min_pop: min_pop = fv
                        if fv > max_pop: max_pop = fv
                except Exception:
                    pass
    yrs_sorted = sorted(yc.items())
    yr_str = ", ".join(f"{y}:{c}" for y, c in yrs_sorted[:10])
    if len(yrs_sorted) > 10:
        yr_str += f" ... ({len(yrs_sorted)} yrs, last 5: " + ", ".join(f"{y}:{c}" for y, c in yrs_sorted[-5:]) + ")"
    print(f"{rel:62s} | n={len(items):5d} | pop=[{min_pop if min_pop<10**9 else 0:.0f}..{max_pop:.0f}] | {yr_str}")

print("\n=== 4. QUIPU HARVESTED RAW SOURCES INVENTORY ===")
shared = os.path.join(qdir, "_shared")
for root, dirs, files in os.walk(shared):
    for fn in sorted(files):
        if fn.endswith((".json", ".geojson", ".gpkg", ".csv", ".xlsx", ".parquet", ".zip")):
            p = os.path.join(root, fn)
            sz_mb = os.path.getsize(p) / (1024 * 1024)
            if sz_mb >= 0.05:
                print(f"  {os.path.relpath(p, shared):75s} {sz_mb:7.2f} MB")
