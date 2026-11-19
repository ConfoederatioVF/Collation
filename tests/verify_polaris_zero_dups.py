# -*- coding: utf-8 -*-
"""Post-repair exhaustive duplicate-name audit across rebuilt POLARIS Stadestér 2.0
shards and Dataview stadester_2.0/city_metadata.json.
"""

import json
import math
import os
import re
import unicodedata
from collections import defaultdict

DV = r"F:\Active Projects\Project 1436 - Dataview"
SHARD_DIR = os.path.join(DV, "data", "stadester", "stadester_2.0")
META_PATH = os.path.join(SHARD_DIR, "city_metadata.json")


def hav_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp * 0.5) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl * 0.5) ** 2
    return 2.0 * r * math.asin(min(1.0, math.sqrt(a)))


def norm_name(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower().strip()
    return re.sub(r"\s+", " ", s)


def stem(s):
    return re.sub(r"[^a-z0-9]", "", norm_name(s))


def main():
    polaris = {}
    for fn in ["02_polaris_1.json", "02_polaris_2.json"]:
        polaris.update(json.load(open(os.path.join(SHARD_DIR, fn), "r", encoding="utf-8")))

    all_shard_keys = set(polaris.keys())
    for fn in os.listdir(SHARD_DIR):
        if not fn.endswith(".json") or fn in ("city_metadata.json", "stadester_manifest.json", "02_polaris_1.json", "02_polaris_2.json"):
            continue
        try:
            d = json.load(open(os.path.join(SHARD_DIR, fn), "r", encoding="utf-8"))
            if isinstance(d, dict):
                all_shard_keys.update(d.keys())
        except Exception:
            pass

    meta = json.load(open(META_PATH, "r", encoding="utf-8"))
    print(f"Rebuilt POLARIS shard entries: {len(polaris)}")
    print(f"Repaired city_metadata.json total: {len(meta)}")

    # 1. Duplicate explicit keys globally
    exp_keys = defaultdict(list)
    for i, r in enumerate(meta):
        if isinstance(r, dict) and r.get("key"):
            exp_keys[r["key"]].append(i)
    dup_exp = {k: v for k, v in exp_keys.items() if len(v) > 1}
    print(f"Duplicate explicit keys globally: {len(dup_exp)}")

    # 2. Orphaned explicit POLARIS keys
    pol_ctries = {"Belarus", "Estonia", "Finland", "Kazakhstan", "Latvia", "Lithuania", "Moldova", "Poland", "Russia", "Ukraine"}
    orphans = []
    for i, r in enumerate(meta):
        k = r.get("key") if isinstance(r, dict) else None
        if not k or k in all_shard_keys:
            continue
        for c in pol_ctries:
            if k.endswith("-" + c) or ("-" + c + "_") in k or k.startswith("Category:"):
                orphans.append((i, k, r.get("name")))
                break
    print(f"Orphaned explicit POLARIS keys: {len(orphans)}")
    for o in orphans[:10]:
        print("  ORPHAN:", o)

    # 3. Endirey check
    print("\n=== ENDIREY CHECK ===")
    for k, v in polaris.items():
        if "endirey" in k.lower() or "andreyaul" in k.lower() or "enderi" in k.lower():
            ys = sorted(int(y) for y, val in (v.get("population") or {}).items() if float(val) > 0)
            print(f"  SHARD: {k} [{ys[0]}..{ys[-1]}] @{v['coords']}")
    for i, r in enumerate(meta):
        if not isinstance(r, dict):
            continue
        s = f"{r.get('key') or ''} {r.get('name') or ''}".lower()
        if "endirey" in s or "andreyaul" in s or "enderi" in s:
            print(f"  META idx={i}: key={r.get('key')} name={r.get('name')} coords={r.get('coords')} hnames={r.get('historical_names')}")

    # 4. Bind all metadata to POLARIS shards & check remaining close duplicates
    pol_grid = defaultdict(list)
    for k, v in polaris.items():
        co = v.get("coords")
        if isinstance(co, list) and len(co) >= 2:
            pol_grid[(int(math.floor(co[0])), int(math.floor(co[1])))].append((k, float(co[0]), float(co[1]), v))

    sk_to_metas = defaultdict(list)
    for i, r in enumerate(meta):
        if not isinstance(r, dict):
            continue
        k = r.get("key")
        if k:
            if k in polaris:
                sk_to_metas[k].append((i, r, 0.0, "key"))
            continue
        co = r.get("coords")
        if not isinstance(co, list) or len(co) < 2:
            continue
        lat, lon = float(co[1]), float(co[0])
        ms = {stem(r.get("name", ""))} | {stem(x) for x in (r.get("other_names") or [])}
        ms.discard("")
        m_prim = stem(r.get("name", ""))
        best = None
        best_d = 15.0
        for dl in (-1, 0, 1):
            for dn in (-1, 0, 1):
                for sk, plat, plon, v in pol_grid.get((int(math.floor(lat)) + dl, int(math.floor(lon)) + dn), ()):
                    d = hav_km(lat, lon, plat, plon)
                    if d < best_d:
                        ss = {stem(v.get("name", ""))} | {stem(x) for x in (v.get("other_names") or [])}
                        ss.discard("")
                        if d <= 0.1 or (m_prim and m_prim == stem(v.get("name", ""))) or (ms & ss):
                            best_d = d
                            best = (sk, d, "spatial")
        if best:
            sk_to_metas[best[0]].append((i, r, best[1], best[2]))

    multi_same = 0
    multi_diff = 0
    multi_samples = []
    for sk, lst in sk_to_metas.items():
        if len(lst) > 1:
            nms = {norm_name(r.get("name", "")) for _, r, _, _ in lst}
            if len(nms) == 1:
                multi_same += 1
                multi_samples.append((sk, [(i, r.get("key"), r.get("name"), round(d, 2)) for i, r, d, _ in lst]))
            else:
                multi_diff += 1
    print(f"\nMulti-meta per single POLARIS shard: same-name={multi_same}, diff-name={multi_diff}")
    for x in multi_samples[:15]:
        print("  MULTI-SAME:", x)

    # Resolved display name per POLARIS shard city
    sk_disp = {}
    for sk, v in polaris.items():
        lst = sk_to_metas.get(sk)
        if lst:
            lst_s = sorted(lst, key=lambda t: (0 if t[3] == "key" else 1, t[2]))
            sk_disp[sk] = lst_s[0][1].get("name") or v.get("name") or sk
        else:
            sk_disp[sk] = v.get("name") or sk

    by_disp = defaultdict(list)
    for sk, disp in sk_disp.items():
        by_disp[norm_name(disp)].append(sk)

    rem_ovlp = []
    rem_gap_le250 = []
    rem_gap_gt250 = []
    for disp, sks in by_disp.items():
        if len(sks) < 2 or not disp:
            continue
        for a in range(len(sks)):
            ka = sks[a]
            va = polaris[ka]
            ya = {int(y) for y, val in (va.get("population") or {}).items() if float(val) > 0}
            for b in range(a + 1, len(sks)):
                kb = sks[b]
                vb = polaris[kb]
                d = hav_km(va["coords"][0], va["coords"][1], vb["coords"][0], vb["coords"][1])
                if d > 30.0:
                    continue
                yb = {int(y) for y, val in (vb.get("population") or {}).items() if float(val) > 0}
                ovlp = len(ya & yb)
                if ovlp > 0:
                    rem_ovlp.append((disp, round(d, 2), ovlp, ka, min(ya), max(ya), kb, min(yb), max(yb)))
                else:
                    gap = max(min(ya) - max(yb), min(yb) - max(ya)) if (ya and yb) else 99999
                    if gap <= 250:
                        rem_gap_le250.append((disp, round(d, 2), gap, ka, min(ya) if ya else None, max(ya) if ya else None, kb, min(yb) if yb else None, max(yb) if yb else None))
                    else:
                        rem_gap_gt250.append((disp, round(d, 2), gap, ka, min(ya) if ya else None, max(ya) if ya else None, kb, min(yb) if yb else None, max(yb) if yb else None))

    print(f"\nRemaining POLARIS <= 30 km same-display-name pairs:")
    print(f"  Overlapping:        {len(rem_ovlp)} (was 386)")
    print(f"  Non-ovlp gap<=250y: {len(rem_gap_le250)} (was 145)")
    print(f"  Non-ovlp gap>250y:  {len(rem_gap_gt250)} (was 1002)")
    print("\n--- Remaining overlapping pairs (all up to 40) ---")
    for x in sorted(rem_ovlp, key=lambda t: t[1])[:40]:
        print(f"  [{x[0]}] d={x[1]}km ovlp={x[2]}y: {x[3]}[{x[4]}..{x[5]}] vs {x[6]}[{x[7]}..{x[8]}]")
    print("\n--- Remaining gap<=250y pairs (up to 20) ---")
    for x in sorted(rem_gap_le250, key=lambda t: t[1])[:20]:
        print(f"  [{x[0]}] d={x[1]}km gap={x[2]}y: {x[3]}[{x[4]}..{x[5]}] vs {x[6]}[{x[7]}..{x[8]}]")
    print("\n--- Remaining gap>250y pairs (up to 20) ---")
    for x in sorted(rem_gap_gt250, key=lambda t: t[1])[:20]:
        print(f"  [{x[0]}] d={x[1]}km gap={x[2]}y: {x[3]}[{x[4]}..{x[5]}] vs {x[6]}[{x[7]}..{x[8]}]")


if __name__ == "__main__":
    main()
