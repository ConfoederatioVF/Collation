import glob
import json
import os
import re
import unicodedata

DATAVIEW_ROOT = r"F:\Active Projects\Project 1436 - Dataview"
SHARD_DIR = os.path.join(DATAVIEW_ROOT, r"data\stadester\stadester_2.0")
META_PATH = os.path.join(SHARD_DIR, "city_metadata.json")

centaur_shard = {}
for sp in sorted(glob.glob(os.path.join(SHARD_DIR, "01_centaur_*.json"))):
    centaur_shard.update(json.load(open(sp, encoding="utf-8")))

meta = json.load(open(META_PATH, encoding="utf-8"))

def norm(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", s)

nd_sd = []
for e in meta:
    k = e.get("key")
    if not k or k not in centaur_shard:
        continue
    raw = centaur_shard[k]
    ctry = raw.get("country", "")
    if ctry not in {"North Dakota", "South Dakota"}:
        continue
    pop = raw.get("population") or {}
    yrs = [int(y) for y, v in pop.items() if str(y).lstrip("-").isdigit() and float(v or 0) > 0]
    mn = min(yrs) if yrs else 0
    mx = max(yrs) if yrs else 0
    if mn >= 1800:
        hn = e.get("historical_names") or []
        fn = hn[0]["name"] if hn else ""
        if norm(fn) != norm(raw.get("name", "")):
            nd_sd.append((k, raw.get("name"), mn, mx, hn))

print(f"ND/SD post-1800 changed entries: {len(nd_sd)}")
for x in nd_sd[:50]:
    print(" ", x)
