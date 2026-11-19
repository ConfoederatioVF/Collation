"""
Stage 1 & 2 of CENTAUR-II Duplicate Name Remediation:
1. Identify false-positive post-1800 North/South Dakota Euro-American railroad/settler towns
   (accidentally swept in by state-name matching on 'Dakota') while preserving genuine ND/SD
   Indigenous reservations/communities.
2. Extract ALL remaining true cross-location duplicate & near-duplicate Indigenous name clusters
   across the entire CENTAUR-II dataset (US, Canada, Alaska, Hawaii, American Samoa, Greenland)
   into cluster-coherent batches (<= 25 settlements/batch) with regional forbidden-name blocklists
   for Gemini 3.8 Flash recoding.
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
OUT_DIR = os.path.join("tests", "toponymy_batches", "centaur_dedup")
MAX_BATCH = 25

# Genuine ND/SD Native American reservations, agencies, and Indigenous communities (keep Indigenous names!)
ND_SD_INDIG_COMMUNITIES = {
    "agency village", "allen", "antelope", "batesland", "belcourt", "bullhead", "cannon ball",
    "cherry creek", "crow creek", "dunseith", "eagle butte", "east dunseith", "fort thompson",
    "fort totten", "fort yates", "four bears village", "green grass", "kyle", "la plant",
    "lake andes", "little eagle", "lower brule", "mandaree", "manderson", "marty", "mclaughlin",
    "mission", "new town", "norris", "oglala", "okreek", "parmelee", "parshall", "pine ridge",
    "porcupine", "rosebud", "selfridge", "shell valley", "sisseton", "soldier creek", "solen",
    "spring creek", "st. francis", "standing rock", "swift bird", "timber lake", "wagner",
    "wakpala", "wanblee", "white horse", "white shield", "wounded knee", "dupree", "rosebud",
    "toki", "st. michael", "crow hill", "wood lake", "belcourt", "rolette", "saint michael",
    "twin buttes", "white river", "rosebud", "wood", "corn creek", "he dog", "ideal", "ring thunder",
    "two strike", "upper cut meat", "blackpipe", "bridger", "howes", "iron lightning", "lantry",
    "promise", "red scaffold", "ridgeview", "takini", "thunder butte", "whitehorse",
}


def strip_paren(s):
    return re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", str(s or "")).strip()


def norm_exact(s):
    s = strip_paren(s).lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", s)


def norm_phonetic(s):
    """Aggressive phonetic key so Sahnish==Sáhniš, Kitikiti'sh==Kitikitiʼsh, Chikasha==Chikashsha."""
    s = strip_paren(s).lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    for a, b in [
        ("ł", "l"), ("ɬ", "l"), ("đ", "d"), ("ø", "o"), ("ŋ", "n"),
        ("ʔ", ""), ("ʷ", "w"), ("š", "s"), ("č", "c"), ("ž", "z"),
        ("ȟ", "h"), ("ǧ", "g"), ("ʼ", ""), ("ʻ", ""),
        ("sh", "s"), ("ch", "c"), ("zh", "z"), ("kh", "k"), ("th", "t"), ("gh", "g"),
    ]:
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "", s)
    # Collapse consecutive duplicate letters (Chikasha == Chikashsha, Waabiganoojii == Waawaabiganoojii partially)
    s = re.sub(r"(.)\1+", r"\1", s)
    return s


def haversine_km(lat1, lon1, lat2, lon2):
    rad = math.pi / 180.0
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def is_same_place_pair(lst):
    """True ONLY when exactly 2 entries are <= 15 km apart and represent non-overlapping epochs of the same place."""
    if len(lst) != 2:
        return False
    a, b = lst[0], lst[1]
    d = haversine_km(a["lat"], a["lng"], b["lat"], b["lng"])
    if d > 15.0:
        return False
    # Non-overlapping (or touching at exact splice year, e.g. 500..1783 & 1781..2026)
    overlap_yrs = min(a["max_year"], b["max_year"]) - max(a["min_year"], b["min_year"])
    return overlap_yrs <= 10


def main():
    centaur_shard = {}
    for sp in sorted(glob.glob(os.path.join(SHARD_DIR, "01_centaur_*.json"))):
        centaur_shard.update(json.load(open(sp, encoding="utf-8")))

    meta = json.load(open(META_PATH, encoding="utf-8"))

    # 1. Inspect ALL keyed CENTAUR entries
    centaur_entries = []
    nd_sd_settler_reverts = {}

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
        shard_name = strip_paren(raw.get("name") or k)
        ctry = str(raw.get("country") or "")

        # Step 1: Identify ND/SD post-1800 Euro-American railroad/homestead towns
        if ctry in {"North Dakota", "South Dakota"} and mn >= 1800:
            if shard_name.lower() not in ND_SD_INDIG_COMMUNITIES and len(hn_sorted) >= 2:
                first_n = str(hn_sorted[0]["name"]).strip()
                second_y = int(str(hn_sorted[1]["date"]).split(".")[0])
                if norm_exact(first_n) != norm_exact(shard_name) and second_y >= 1850:
                    # Drop the synthetic 1850 generic tribal/river prefix; keep authentic settler history!
                    # (Wait: ensure first date <= mn by using the settler founding name from mn onward,
                    #  or if second entry is an authentic earlier settler name like Edwinton / Fort Abercrombie / Nordland, start it at mn!)
                    cleaned_hn = [dict(h) for h in hn_sorted[1:]]
                    # Keep original founding dates, Dataview falls back to cleaned_hn[0] before founding
                    nd_sd_settler_reverts[k] = {
                        "key": k,
                        "name": shard_name,
                        "country": ctry,
                        "old_hn": hn_sorted,
                        "new_hn": cleaned_hn,
                    }
                    hn_sorted = cleaned_hn

        first_n = str(hn_sorted[0]["name"]).strip()
        centaur_entries.append({
            "key": k,
            "name": shard_name,
            "country": ctry,
            "region": str(raw.get("region") or ""),
            "lat": round(float(coords[0]), 5),
            "lng": round(float(coords[1]), 5),
            "min_year": mn,
            "max_year": mx,
            "other_names": (raw.get("other_names") or [])[:10],
            "current_hn": hn_sorted,
            "first_name": first_n,
            "first_phon": norm_phonetic(first_n),
            "was_nd_sd_reverted": k in nd_sd_settler_reverts,
        })

    print(f"ND/SD post-1800 Euro-American towns cleaned of synthetic 1850 prefixes: {len(nd_sd_settler_reverts)}")

    # 2. Cluster by phonetic first_name (excluding purely modern settler English/French towns >= 1800 that share modern names like 'Woodland' or 'Springfield'!)
    #    Wait: ALSO check ALL historical names active <= 1780 across all entries!
    by_phon = defaultdict(list)
    used_names_by_country = defaultdict(set)

    for item in centaur_entries:
        used_names_by_country[item["country"]].add(item["first_name"])
        # Only deduplicate Indigenous/pre-colonial names (skip purely modern post-1800 towns whose first_name == shard_name, like two modern towns named 'Springfield' or 'Woodland')
        is_modern_settler_same = (
            item["min_year"] >= 1750
            and item["country"] not in {"Alaska", "Hawaii", "American Samoa", "Greenland"}
            and norm_exact(item["first_name"]) == norm_exact(item["name"])
            and not re.search(r"(first nation|indian|reserve|pueblo|rancheria)", item["key"], re.I)
        )
        if not is_modern_settler_same:
            by_phon[item["first_phon"]].append(item)

    true_dup_clusters = []
    skipped_same_place = 0
    for phon, lst in by_phon.items():
        if len(lst) < 2:
            continue
        if is_same_place_pair(lst):
            skipped_same_place += 1
            continue
        # Sort cluster north-to-south, west-to-east for geographic clarity
        lst_sorted = sorted(lst, key=lambda x: (x["country"], -x["lat"], x["lng"], x["key"]))
        true_dup_clusters.append((phon, lst_sorted))

    true_dup_clusters.sort(key=lambda x: (-len(x[1]), x[0]))
    total_dup_items = sum(len(lst) for _, lst in true_dup_clusters)

    print(f"Skipped legitimate same-place multi-epoch pairs (<=15 km): {skipped_same_place}")
    print(f"TRUE cross-location duplicate/near-duplicate clusters: {len(true_dup_clusters)} clusters covering {total_dup_items} settlements!")
    for phon, lst in true_dup_clusters[:35]:
        forms = sorted(set(x["first_name"] for x in lst))
        ctries = sorted(set(x["country"] for x in lst))
        print(f"  [{len(lst):2d}] {phon:24} {forms[:3]} | {ctries[:4]}")

    # 3. Pack clusters into batches (<= MAX_BATCH per batch), keeping entire clusters together whenever <= MAX_BATCH!
    os.makedirs(OUT_DIR, exist_ok=True)
    for fn in os.listdir(OUT_DIR):
        if fn.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, fn))

    # Save deterministic ND/SD reverts
    with open(os.path.join(OUT_DIR, "nd_sd_settler_reverts.json"), "w", encoding="utf-8") as fh:
        json.dump(nd_sd_settler_reverts, fh, ensure_ascii=False, indent=2)

    batches = []
    current_batch = []
    current_clusters = []

    for phon, lst in true_dup_clusters:
        if len(lst) > MAX_BATCH:
            # Flush current batch first
            if current_batch:
                batches.append((current_clusters, current_batch))
                current_batch = []
                current_clusters = []
            # Split large cluster by sub-slices of MAX_BATCH (keeping geographically contiguous slices!)
            for i in range(0, len(lst), MAX_BATCH):
                sub = lst[i : i + MAX_BATCH]
                batches.append(([f"{phon} (part {i // MAX_BATCH + 1})"], sub))
        else:
            if len(current_batch) + len(lst) > MAX_BATCH:
                batches.append((current_clusters, current_batch))
                current_batch = []
                current_clusters = []
            current_batch.extend(lst)
            current_clusters.append(phon)

    if current_batch:
        batches.append((current_clusters, current_batch))

    # Write batches with regional forbidden names blocklist
    for idx, (cl_names, items) in enumerate(batches, start=1):
        ctries = sorted(set(x["country"] for x in items))
        # Include other already-used names in those countries (capped at 120 most frequent/relevant so prompt stays compact)
        cluster_set = {x["first_name"] for x in items}
        other_used = sorted({n for c in ctries for n in used_names_by_country[c]} - cluster_set)
        # Keep top 100 nearby/same-country names to warn Flash not to collide with them
        payload_items = []
        for x in items:
            payload_items.append({
                "key": x["key"],
                "shard_name": x["name"],
                "country": x["country"],
                "region": x["region"],
                "coords_lat_lng": [x["lat"], x["lng"]],
                "min_year": x["min_year"],
                "max_year": x["max_year"],
                "other_names": x["other_names"],
                "current_historical_names": x["current_hn"],
                "duplicate_name_flagged": x["first_name"],
            })
        bpath = os.path.join(OUT_DIR, f"batch_{idx:04d}.json")
        with open(bpath, "w", encoding="utf-8") as fh:
            json.dump({
                "batch_index": idx,
                "clusters": cl_names,
                "countries": ctries,
                "count": len(payload_items),
                "forbidden_already_used_in_region": other_used[:120],
                "settlements": payload_items,
            }, fh, ensure_ascii=False, indent=2)

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "nd_sd_settler_reverts": len(nd_sd_settler_reverts),
            "true_duplicate_clusters": len(true_dup_clusters),
            "true_duplicate_settlements": total_dup_items,
            "batch_count": len(batches),
            "max_batch_size": MAX_BATCH,
        }, fh, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(batches)} cluster-coherent dedup batches ({total_dup_items} settlements) -> {OUT_DIR}")


if __name__ == "__main__":
    main()
