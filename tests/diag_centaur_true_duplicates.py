"""
Classify all duplicate names in CENTAUR-II city_metadata.json into:
1. Legitimate same-location multi-epoch counterparts (<= 15 km apart, non-overlapping or continuation epochs, e.g. Yaanga for Los Angeles & Los Angeles_2).
2. False-positive post-1800 settler towns swept in by the 'Dakota'/'Woodland'/etc. keyword regex.
3. True duplicate names in DIFFERENT places (> 15 km apart, OR co-active overlapping settlements) that MUST be recoded to unique, accurate names!
"""

import glob
import json
import math
import os
import re
import unicodedata
from collections import defaultdict, Counter

DATAVIEW_ROOT = r"F:\Active Projects\Project 1436 - Dataview"
SHARD_DIR = os.path.join(DATAVIEW_ROOT, r"data\stadester\stadester_2.0")
META_PATH = os.path.join(SHARD_DIR, "city_metadata.json")

centaur_shard = {}
for sp in sorted(glob.glob(os.path.join(SHARD_DIR, "01_centaur_*.json"))):
    centaur_shard.update(json.load(open(sp, encoding="utf-8")))

meta = json.load(open(META_PATH, encoding="utf-8"))


def norm_indig(s):
    s = str(s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    for a, b in [("ł", "l"), ("ɬ", "l"), ("đ", "d"), ("ø", "o"), ("ŋ", "n"), ("ʔ", ""), ("ʷ", "w"), ("š", "s"), ("č", "c"), ("ž", "z"), ("ȟ", "h"), ("ǧ", "g"), ("ʼ", ""), ("ʻ", "")]:
        s = s.replace(a, b)
    s = re.sub(r"['’‘ʼʻ`´\-_\s.,]+", "", s)
    return s


def haversine_km(lat1, lon1, lat2, lon2):
    rad = math.pi / 180.0
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


# Check EVERY keyed CENTAUR entry
entries = []
for e in meta:
    k = e.get("key")
    if not k or k not in centaur_shard:
        continue
    raw = centaur_shard[k]
    hn = e.get("historical_names") or []
    if not hn:
        continue
    hn_sorted = sorted(hn, key=lambda x: [int(p) for p in str(x["date"]).split(".")])
    pop = raw.get("population") or {}
    yrs = [int(y) for y, v in pop.items() if str(y).lstrip("-").isdigit() and float(v or 0) > 0]
    mn = min(yrs) if yrs else int(str(hn_sorted[0]["date"]).split(".")[0])
    mx = max(yrs) if yrs else mn
    coords = raw.get("coords") or [0.0, 0.0]
    first_n = str(hn_sorted[0]["name"]).strip()
    entries.append({
        "key": k,
        "shard_name": str(raw.get("name") or ""),
        "other_names": raw.get("other_names") or [],
        "country": str(raw.get("country") or ""),
        "region": str(raw.get("region") or ""),
        "lat": float(coords[0]),
        "lng": float(coords[1]),
        "min_year": mn,
        "max_year": mx,
        "first_name": first_n,
        "first_norm": norm_indig(first_n),
        "hn": hn_sorted,
    })

# 1. Check post-1800 ND/SD/modern settler towns that got indigenised by the Dakota/etc. regex bug!
nd_sd_post1800 = [e for e in entries if e["country"] in {"North Dakota", "South Dakota"} and e["min_year"] >= 1800]
other_post1800_changed = [
    e for e in entries
    if e["country"] not in {"North Dakota", "South Dakota", "Alaska", "Hawaii", "American Samoa", "Greenland"}
    and e["min_year"] >= 1800
    and norm_indig(e["first_name"]) != norm_indig(e["shard_name"])
]
print(f"Post-1800 ND/SD entries in keyed CENTAUR meta: {len(nd_sd_post1800)}")
print(f"  of which first_name != shard_name: {sum(1 for e in nd_sd_post1800 if norm_indig(e['first_name']) != norm_indig(e['shard_name']))}")
print(f"Post-1800 non-ND/SD/AK/HI/GL entries with first_name != shard_name: {len(other_post1800_changed)}")
for x in other_post1800_changed[:20]:
    print("  POST1800_OTHER:", x["key"], x["min_year"], x["max_year"], "->", x["hn"][:2])

# 2. Group ALL entries (and separately pre-1800 entries) by first_norm
by_norm = defaultdict(list)
for e in entries:
    by_norm[e["first_norm"]].append(e)

# Classify each duplicate group
same_place_only = []
true_diff_place = []
true_diff_place_pre1800_only = []

for nm, lst in by_norm.items():
    if len(lst) < 2:
        continue
    # Compute max pairwise distance and whether any pair overlaps in time
    max_dist = 0.0
    any_overlap = False
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            d = haversine_km(lst[i]["lat"], lst[i]["lng"], lst[j]["lat"], lst[j]["lng"])
            if d > max_dist:
                max_dist = d
            # overlap in active time?
            if not (lst[i]["max_year"] < lst[j]["min_year"] or lst[j]["max_year"] < lst[i]["min_year"]):
                any_overlap = True
    if max_dist <= 15.0 and not any_overlap and len(lst) == 2:
        same_place_only.append((nm, lst, max_dist))
    else:
        true_diff_place.append((nm, lst, max_dist, any_overlap))
        pre_lst = [x for x in lst if x["min_year"] < 1800 or x["country"] in {"Alaska", "Hawaii", "American Samoa", "Greenland"}]
        if len(pre_lst) >= 2:
            true_diff_place_pre1800_only.append((nm, pre_lst))

print(f"\n=== DUPLICATE CLASSIFICATION (across all {len(entries)} keyed entries) ===")
print(f"Legitimate same-place non-overlapping multi-epoch pairs (<=15 km): {len(same_place_only)} groups ({sum(len(l) for _,l,_ in same_place_only)} entries)")
print(f"TRUE duplicate names in different places / overlapping: {len(true_diff_place)} groups ({sum(len(l) for _,l,_,_ in true_diff_place)} entries)")
print(f"  of which among pre-1800 / AK / HI / GL entries: {len(true_diff_place_pre1800_only)} groups ({sum(len(l) for _,l in true_diff_place_pre1800_only)} entries)")

# Break down true_diff_place_pre1800_only by country
ctry_counts = Counter()
for nm, lst in true_diff_place_pre1800_only:
    for x in lst:
        ctry_counts[x["country"]] += 1
print("\nTop 25 states/provinces with pre-1800 true duplicate names:")
for c, cnt in ctry_counts.most_common(25):
    print(f"  {c:28}: {cnt}")

print("\nTop 40 pre-1800 true duplicate groups (excluding post-1800 ND/SD noise):")
for nm, lst in sorted(true_diff_place_pre1800_only, key=lambda x: -len(x[1]))[:40]:
    forms = sorted(set(i["first_name"] for i in lst))
    ctries = sorted(set(i["country"] for i in lst))
    print(f"  [{len(lst):2d}] {forms[:3]} | {ctries[:4]}")
