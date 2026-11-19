"""
Systematically detect ALL duplicate Indigenous/pre-contact names across CENTAUR-II
in Dataview's stadester_2.0/city_metadata.json (grouping by diacritic/apostrophe-normalised
stem so 'Sahnish' == 'Sáhniš' and "Kitikiti'sh" == "Kitikitiʼsh").
"""

import glob
import json
import os
import re
import unicodedata
from collections import defaultdict

DATAVIEW_ROOT = r"F:\Active Projects\Project 1436 - Dataview"
SHARD_DIR = os.path.join(DATAVIEW_ROOT, r"data\stadester\stadester_2.0")
META_PATH = os.path.join(SHARD_DIR, "city_metadata.json")

# Load CENTAUR shard keys + metadata
centaur_shard = {}
for sp in sorted(glob.glob(os.path.join(SHARD_DIR, "01_centaur_*.json"))):
    centaur_shard.update(json.load(open(sp, encoding="utf-8")))

meta = json.load(open(META_PATH, encoding="utf-8"))

def norm_indig(s):
    s = str(s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    for a, b in [("ł", "l"), ("ɬ", "l"), ("đ", "d"), ("ø", "o"), ("ŋ", "n"), ("ʔ", ""), ("ʷ", "w"), ("š", "s"), ("č", "c"), ("ž", "z")]:
        s = s.replace(a, b)
    s = re.sub(r"['’‘ʼʻ`´\-_\s.,]+", "", s)
    return s

# Collect all keyed CENTAUR entries
centaur_meta = []
for e in meta:
    k = e.get("key")
    if k and k in centaur_shard:
        raw = centaur_shard[k]
        hn = e.get("historical_names") or []
        if not hn:
            continue
        hn_sorted = sorted(hn, key=lambda x: [int(p) for p in str(x["date"]).split(".")])
        first_y = int(str(hn_sorted[0]["date"]).split(".")[0])
        first_n = str(hn_sorted[0]["name"]).strip()
        pop = raw.get("population") or {}
        yrs = [int(y) for y, v in pop.items() if str(y).lstrip("-").isdigit() and float(v or 0) > 0]
        mn = min(yrs) if yrs else first_y
        mx = max(yrs) if yrs else first_y
        centaur_meta.append({
            "key": k,
            "shard_name": raw.get("name", ""),
            "other_names": raw.get("other_names", []),
            "country": raw.get("country", ""),
            "region": raw.get("region", ""),
            "coords": raw.get("coords", []),
            "min_year": mn,
            "max_year": mx,
            "first_year": first_y,
            "first_name": first_n,
            "first_norm": norm_indig(first_n),
            "historical_names": hn_sorted,
        })

# Group by first_norm (and also check all historical_names active <= 1650!)
by_norm = defaultdict(list)
for item in centaur_meta:
    by_norm[item["first_norm"]].append(item)

dups = {nm: lst for nm, lst in by_norm.items() if len(lst) >= 2}
total_dup_settlements = sum(len(lst) for lst in dups.values())

# Also check how many duplicate groups have count >= 2, >= 3, >= 5, >= 10
c2 = sum(1 for lst in dups.values() if len(lst) == 2)
c3_4 = sum(1 for lst in dups.values() if 3 <= len(lst) <= 4)
c5_9 = sum(1 for lst in dups.values() if 5 <= len(lst) <= 9)
c10p = sum(1 for lst in dups.values() if len(lst) >= 10)

print(f"Total keyed CENTAUR entries: {len(centaur_meta)}")
print(f"Duplicate normalised first-names (>= 2 settlements): {len(dups)} groups covering {total_dup_settlements} settlements")
print(f"  Size 2: {c2} groups ({c2*2} settlements)")
print(f"  Size 3-4: {c3_4} groups ({sum(len(l) for l in dups.values() if 3 <= len(l) <= 4)} settlements)")
print(f"  Size 5-9: {c5_9} groups ({sum(len(l) for l in dups.values() if 5 <= len(l) <= 9)} settlements)")
print(f"  Size 10+: {c10p} groups ({sum(len(l) for l in dups.values() if len(l) >= 10)} settlements)")

print("\n=== TOP 60 DUPLICATE NAME GROUPS ===")
for nm, lst in sorted(dups.items(), key=lambda x: -len(x[1]))[:60]:
    display_forms = sorted(set(i["first_name"] for i in lst))
    ctries = sorted(set(i["country"] for i in lst))
    print(f"  [{len(lst):3d}] {display_forms[:3]} | countries={ctries[:5]}")

print("\n=== DETAILED INSPECTION OF SAHNISH + MNISOSE + MATA (IMAGE 1 AREA) ===")
for target in ["sahnish", "mnisose", "mata"]:
    lst = by_norm.get(target, [])
    print(f"\n--- {target} ({len(lst)} entries) ---")
    for x in sorted(lst, key=lambda i: (i["country"], -(i["coords"][0] if i["coords"] else 0))):
        print(f"  key={x['key']!r:45} | shard={x['shard_name']!r:25} | {x['min_year']}..{x['max_year']} | first={x['first_name']!r} | other={x['other_names'][:4]}")
