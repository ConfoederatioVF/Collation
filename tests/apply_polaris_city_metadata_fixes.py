# -*- coding: utf-8 -*-
"""Repairs Dataview's stadester_2.0/city_metadata.json for Project POLARIS using
the rebuilt Stadestér 2.0 shards and all 11 Gemini 3.8 Flash audited decision sets.
"""

import json
import math
import os
import re
import unicodedata
from collections import defaultdict

SVEA = r"f:\Active Projects\Project 1509 - SVEA"
DV = r"F:\Active Projects\Project 1436 - Dataview"
SHARD_DIR = os.path.join(DV, "data", "stadester", "stadester_2.0")
META_PATH = os.path.join(SHARD_DIR, "city_metadata.json")
BDIR = os.path.join(SVEA, "tests", "polaris_batches")
INV_PATH = os.path.join(SVEA, "tests", "polaris_dup_inventory.json")


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


def parse_date_num(d):
    s = str(d or "").strip()
    m = re.match(r"^(-?\d+)(?:\.(\d+))?(?:\.(\d+))?$", s)
    if not m:
        return 0.0
    y = int(m.group(1))
    mo = int(m.group(2) or 1)
    da = int(m.group(3) or 1)
    return y + (mo - 1) / 12.0 + (da - 1) / 365.0


def merge_historical_names(h1, h2):
    all_recs = []
    for h in (h1 or []) + (h2 or []):
        if isinstance(h, dict) and h.get("date") is not None and h.get("name"):
            all_recs.append({"date": str(h["date"]), "name": str(h["name"]).strip()})
    if not all_recs:
        return []
    all_recs.sort(key=lambda r: (parse_date_num(r["date"]), -len(r["date"])))
    merged = []
    for r in all_recs:
        if merged:
            prev = merged[-1]
            if abs(parse_date_num(r["date"]) - parse_date_num(prev["date"])) < 0.05:
                if len(r["date"]) > len(prev["date"]):
                    merged[-1] = r
                continue
            if prev["name"].lower().strip() == r["name"].lower().strip():
                continue
        merged.append(r)
    return merged


def merge_other_names(base_name, *lists):
    out = []
    seen = set()
    if base_name:
        seen.add(base_name.lower().strip())
    for lst in lists:
        for item in (lst or []):
            s = str(item or "").strip()
            if not s:
                continue
            sl = s.lower()
            if sl not in seen:
                seen.add(sl)
                out.append(s)
    return out


def merge_capitals(c1, c2):
    if not isinstance(c1, dict) and not isinstance(c2, dict):
        return None
    out = {}
    if isinstance(c1, dict):
        out.update(c1)
    if isinstance(c2, dict):
        for k, v in c2.items():
            if k not in out:
                out[k] = v
    return out if out else None


def merge_meta_records(keep, drop):
    """Merges drop metadata record into keep metadata record in-place."""
    # Prefer richer historical_names (multi-entry over single-entry stub)
    h_keep = keep.get("historical_names") or []
    h_drop = drop.get("historical_names") or []
    if len(h_drop) > 1 and len(h_keep) <= 1:
        keep["historical_names"] = merge_historical_names(h_drop, h_keep)
    elif len(h_keep) > 1 and len(h_drop) <= 1:
        keep["historical_names"] = h_keep
    else:
        keep["historical_names"] = merge_historical_names(h_keep, h_drop)

    cap = merge_capitals(keep.get("capital"), drop.get("capital"))
    if cap:
        keep["capital"] = cap

    keep["other_names"] = merge_other_names(
        keep.get("name"),
        keep.get("other_names"),
        drop.get("other_names"),
        [drop.get("name")] if drop.get("name") and norm_name(drop.get("name")) != norm_name(keep.get("name")) else [],
    )
    return keep


def main():
    # 1. Load rebuilt POLARIS shards + all global shard keys
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
    orig_count = len(meta)
    inv = json.load(open(INV_PATH, "r", encoding="utf-8"))

    # 2. Load all Gemini 3.8 Flash audited decisions
    merges = {}       # src_key -> tgt_key
    drops = set()
    renames = {}      # key -> new_name
    clean_names = {}  # key -> clean_name
    homonyms = set()

    for fn in sorted(os.listdir(BDIR)):
        if not fn.startswith("out_tier") or not fn.endswith(".json"):
            continue
        for cl in json.load(open(os.path.join(BDIR, fn), "r", encoding="utf-8")):
            for act in (cl.get("actions") or []):
                op = act.get("op")
                if op == "MERGE":
                    sk = act["source_key"]
                    tk = act["target_key"]
                    if sk == "Kerch-Ukraine_2" and tk == "Kerch-Ukraine":
                        tk = "Ker`c-Ukraine"
                    merges[sk] = tk
                elif op == "DROP_JUNK":
                    drops.add(act["key"])
                elif op == "RENAME_META":
                    renames[act["key"]] = act["new_name"]
                elif op == "KEEP_HOMONYM":
                    homonyms.add(act["key"])
            for k, nm in (cl.get("clean_names") or {}).items():
                if nm:
                    clean_names[k] = nm

    # Resolve transitive merges
    def resolve_tgt(k):
        seen = set()
        cur = k
        while cur in merges and cur not in seen:
            seen.add(cur)
            cur = merges[cur]
        return cur

    for s in list(merges.keys()):
        merges[s] = resolve_tgt(s)

    multi_diff_out = json.load(open(os.path.join(BDIR, "out_multi_meta_diff.json"), "r", encoding="utf-8"))

    stats = {
        "orig_count": orig_count,
        "dropped_junk_meta": 0,
        "merged_source_meta": 0,
        "dropped_orphan_polaris_keys": 0,
        "merged_same_name_multi": 0,
        "merged_diff_name_multi": 0,
        "renamed_meta": 0,
        "created_meta_for_renamed": 0,
        "unkeyed_close_dups_merged": 0,
        "final_count": 0,
    }

    deleted_idxs = set()

    # Build quick lookup by explicit key AND 1-degree spatial grid of unkeyed metadata
    key_to_idxs = defaultdict(list)
    unkeyed_grid = defaultdict(list)
    for i, r in enumerate(meta):
        if not isinstance(r, dict):
            continue
        if r.get("key"):
            key_to_idxs[r["key"]].append(i)
        else:
            co = r.get("coords")
            if isinstance(co, list) and len(co) >= 2:
                unkeyed_grid[(int(math.floor(float(co[1]))), int(math.floor(float(co[0]))))].append(i)

    # Helper: find best existing metadata idx for a shard_key (explicit key first, else nearest matching unkeyed)
    def find_meta_for_shard(sk):
        for idx in key_to_idxs.get(sk, []):
            if idx not in deleted_idxs:
                return idx
        sh = polaris.get(sk)
        if not sh or not isinstance(sh.get("coords"), list):
            return None
        lat, lon = float(sh["coords"][0]), float(sh["coords"][1])
        sn = {stem(sh.get("name", ""))} | {stem(x) for x in (sh.get("other_names") or [])}
        sn.discard("")
        clat, clon = int(math.floor(lat)), int(math.floor(lon))
        best = None
        best_d = 12.0
        for dl in (-1, 0, 1):
            for dn in (-1, 0, 1):
                for i in unkeyed_grid.get((clat + dl, clon + dn), ()):
                    if i in deleted_idxs:
                        continue
                    r = meta[i]
                    if r.get("key"):
                        continue
                    co = r.get("coords")
                    d = hav_km(lat, lon, co[1], co[0])
                    if d < best_d:
                        rn = {stem(r.get("name", ""))} | {stem(x) for x in (r.get("other_names") or [])}
                        rn.discard("")
                        if d <= 0.1 or (sn & rn):
                            best_d = d
                            best = i
        return best

    # 3. Handle DROP_JUNK metadata entries (remove explicit-key metadata for dropped junk settlements)
    for dk in drops:
        for idx in key_to_idxs.get(dk, []):
            if idx not in deleted_idxs and dk not in polaris:
                deleted_idxs.add(idx)
                stats["dropped_junk_meta"] += 1

    # 4. Handle MERGE source metadata entries: preserve capital/rich history onto target, delete source meta if source key is gone from shards
    for sk, tk in merges.items():
        if sk in polaris:
            # Source still exists in shards (e.g. couldn't merge); skip deleting its meta
            continue
        src_idxs = [i for i in key_to_idxs.get(sk, []) if i not in deleted_idxs]
        if not src_idxs:
            continue
        tgt_idx = find_meta_for_shard(tk)
        for s_idx in src_idxs:
            if tgt_idx is not None and tgt_idx != s_idx:
                # Only merge capital and aliases (don't pollute modern city's historical_names with an archaeological stub)
                cap = merge_capitals(meta[tgt_idx].get("capital"), meta[s_idx].get("capital"))
                if cap:
                    meta[tgt_idx]["capital"] = cap
                if len(meta[s_idx].get("historical_names") or []) > 1:
                    meta[tgt_idx]["historical_names"] = merge_historical_names(
                        meta[tgt_idx].get("historical_names"),
                        meta[s_idx].get("historical_names"),
                    )
                if tk in polaris and not meta[tgt_idx].get("key"):
                    meta[tgt_idx]["key"] = tk
                    key_to_idxs[tk].append(tgt_idx)
            deleted_idxs.add(s_idx)
            stats["merged_source_meta"] += 1

    # 5. Remove ANY remaining orphaned POLARIS explicit keys (whose key ends with a POLARIS country and is no longer in any shard)
    polaris_countries = {"Belarus", "Estonia", "Finland", "Kazakhstan", "Latvia", "Lithuania", "Moldova", "Poland", "Russia", "Ukraine"}
    for i, r in enumerate(meta):
        if i in deleted_idxs or not isinstance(r, dict):
            continue
        k = r.get("key")
        if not k or k in all_shard_keys:
            continue
        if k.startswith("Category:"):
            deleted_idxs.add(i)
            stats["dropped_orphan_polaris_keys"] += 1
            continue
        for c in polaris_countries:
            if k.endswith("-" + c) or ("-" + c + "_") in k:
                deleted_idxs.add(i)
                stats["dropped_orphan_polaris_keys"] += 1
                break

    # 6. Deduplicate 88 same-name multi-meta clusters bound to 1 POLARIS shard
    for sk, lst in inv["multi_meta_per_shard"].items():
        if sk not in polaris:
            continue
        live = [x for x in lst if x["idx"] not in deleted_idxs]
        if len(live) < 2:
            continue
        nms = {norm_name(meta[x["idx"]].get("name", "")) for x in live}
        if len(nms) != 1:
            continue
        # Pick best keeper: prefer explicit key == sk, then has_capital, then richest historical_names, then lowest idx
        live.sort(key=lambda x: (
            0 if meta[x["idx"]].get("key") == sk else 1,
            0 if meta[x["idx"]].get("capital") else 1,
            -len(meta[x["idx"]].get("historical_names") or []),
            x["dist_km"],
            x["idx"],
        ))
        keep_idx = live[0]["idx"]
        for item in live[1:]:
            d_idx = item["idx"]
            if d_idx == keep_idx or d_idx in deleted_idxs:
                continue
            # Never drop an entry explicitly keyed to a DIFFERENT existing shard!
            dk = meta[d_idx].get("key")
            if dk and dk != sk and dk in all_shard_keys:
                continue
            merge_meta_records(meta[keep_idx], meta[d_idx])
            deleted_idxs.add(d_idx)
            stats["merged_same_name_multi"] += 1
        meta[keep_idx]["key"] = sk
        sh_c = polaris[sk]["coords"]
        if isinstance(sh_c, list) and len(sh_c) >= 2:
            meta[keep_idx]["coords"] = [round(float(sh_c[1]), 5), round(float(sh_c[0]), 5)]
        if keep_idx not in key_to_idxs[sk]:
            key_to_idxs[sk].append(keep_idx)

    # 7. Apply Gemini 3.8 Flash audited decisions for the 49 diff-name multi-meta clusters
    for item in multi_diff_out:
        sk = item.get("shard_key")
        if sk not in polaris:
            continue
        action = item.get("action")
        if action == "MERGE_META":
            keep_idx = item.get("keep_idx")
            drop_idxs = item.get("drop_idxs") or []
            canon_nm = item.get("canonical_name")
            if keep_idx is None or keep_idx in deleted_idxs or keep_idx >= len(meta):
                continue
            for d_idx in drop_idxs:
                if d_idx == keep_idx or d_idx in deleted_idxs or d_idx >= len(meta):
                    continue
                dk = meta[d_idx].get("key")
                if dk and dk != sk and dk in all_shard_keys:
                    continue
                merge_meta_records(meta[keep_idx], meta[d_idx])
                deleted_idxs.add(d_idx)
                stats["merged_diff_name_multi"] += 1
            meta[keep_idx]["key"] = sk
            if canon_nm:
                meta[keep_idx]["name"] = canon_nm
            if keep_idx not in key_to_idxs[sk]:
                key_to_idxs[sk].append(keep_idx)
        elif action == "KEEP_SEPARATE":
            prim_idx = item.get("primary_idx")
            if prim_idx is not None and prim_idx not in deleted_idxs and prim_idx < len(meta):
                meta[prim_idx]["key"] = sk
                if prim_idx not in key_to_idxs[sk]:
                    key_to_idxs[sk].append(prim_idx)

    # 8. Apply ALL RENAME_META & clean_names onto surviving POLARIS shard keys!
    # Combine renames + clean_names (prefer explicit renames when both present)
    target_names = dict(clean_names)
    target_names.update(renames)
    target_names.update({
        "Talianki-Ukraine": "Talianky (Trypillia)",
        "Rechitsa Iron Age Site-Belarus": "Rechitsa (Iron Age)",
        "Krasnoselsky Bronze Age Site-Belarus": "Krasnoselsky (Early Bronze Age)",
        "Sosnytsia Bronze Age Type-Site-Ukraine": "Sosnytsia (Eneolithic)",
        "Svetilovichi-Besed Radimichi Barrow Hillfort Complex Stone Age Site-Belarus": "Svetilovichi (Stone Age)",
        "Skala Bronze Age Site-Russia": "Skala (Bronze Age)",
        "Valentin-Peresheyek Bronze Age Site-Russia": "Valentin-Peresheyek (Bronze Age)",
        "Suzgun-Russia_2": "Suzgun (Early Medieval)",
        "Bortnychi Eneolithic Hillfort-Ukraine": "Bortnychi (Eneolithic)",
        "Daroshavichy Stone Age Settlement-Belarus": "Daroshavichy (Stone Age)",
        "Krugloye-Belarus_2": "Krugloye (Rus)",
        "Kostyukovichi-Belarus_2": "Kostyukovichi (Rus)",
    })
    for _k, _v in [
        ("Talianki-Ukraine", "Talianky (Trypillia)"),
        ("Rechitsa Iron Age Site-Belarus", "Rechitsa (Iron Age)"),
        ("Krasnoselsky Bronze Age Site-Belarus", "Krasnoselsky (Early Bronze Age)"),
        ("Sosnytsia Bronze Age Type-Site-Ukraine", "Sosnytsia (Eneolithic)"),
        ("Svetilovichi-Besed Radimichi Barrow Hillfort Complex Stone Age Site-Belarus", "Svetilovichi (Stone Age)"),
        ("Skala Bronze Age Site-Russia", "Skala (Bronze Age)"),
        ("Valentin-Peresheyek Bronze Age Site-Russia", "Valentin-Peresheyek (Bronze Age)"),
        ("Suzgun-Russia_2", "Suzgun (Early Medieval)"),
        ("Bortnychi Eneolithic Hillfort-Ukraine", "Bortnychi (Eneolithic)"),
        ("Daroshavichy Stone Age Settlement-Belarus", "Daroshavichy (Stone Age)"),
        ("Krugloye-Belarus_2", "Krugloye (Rus)"),
        ("Kostyukovichi-Belarus_2", "Kostyukovichi (Rus)"),
    ]:
        renames[_k] = _v

    for sk, new_nm in sorted(target_names.items()):
        if sk not in polaris or not new_nm:
            continue
        new_nm = str(new_nm).strip()
        if not new_nm:
            continue

        # Find existing explicit-key meta record for sk, OR check if this is a renamed entry needing its own explicit key
        m_idxs = [i for i in key_to_idxs.get(sk, []) if i not in deleted_idxs]
        sh = polaris[sk]
        sh_c = sh.get("coords") or [0.0, 0.0]
        sh_yrs = sorted(int(y) for y, v in (sh.get("population") or {}).items() if float(v) > 0)
        min_y = sh_yrs[0] if sh_yrs else 1800

        if m_idxs:
            m_idx = m_idxs[0]
            rec = meta[m_idx]
            old_nm = rec.get("name")
            if old_nm != new_nm:
                rec["name"] = new_nm
                # If historical_names is a single stub carrying the old duplicate name, update it to new_nm
                hns = rec.get("historical_names") or []
                if len(hns) == 1 and isinstance(hns[0], dict) and norm_name(hns[0].get("name")) == norm_name(old_nm):
                    hns[0]["name"] = new_nm
                elif len(hns) == 0:
                    rec["historical_names"] = [{"date": f"{min_y}.1.1", "name": new_nm}]
                stats["renamed_meta"] += 1
            # Deduplicate extra copies with exact same explicit key
            for extra_i in m_idxs[1:]:
                merge_meta_records(rec, meta[extra_i])
                deleted_idxs.add(extra_i)
        else:
            # Check if an unkeyed metadata record exists specifically for sk
            cand_idx = find_meta_for_shard(sk)
            # Only reuse cand_idx if it isn't already the modern city of another surviving shard!
            can_reuse = False
            if cand_idx is not None:
                c_rec = meta[cand_idx]
                if norm_name(c_rec.get("name")) == norm_name(new_nm):
                    can_reuse = True
            if can_reuse:
                meta[cand_idx]["key"] = sk
                meta[cand_idx]["name"] = new_nm
                key_to_idxs[sk].append(cand_idx)
            elif sk in renames:
                # Create a clean explicit-key metadata record so Dataview binds this settlement to its distinct name!
                new_rec = {
                    "key": sk,
                    "name": new_nm,
                    "coords": [round(float(sh_c[1]), 5), round(float(sh_c[0]), 5)],
                    "historical_names": [{"date": f"{min_y}.1.1", "name": new_nm}],
                    "other_names": merge_other_names(new_nm, [sh.get("name")], sh.get("other_names")),
                }
                new_idx = len(meta)
                meta.append(new_rec)
                key_to_idxs[sk].append(new_idx)
                stats["created_meta_for_renamed"] += 1

    # 9. Clean Endirey-Russia specifically (remove erroneous 'Balkh' historical_name & bind explicit key)
    end_idx = find_meta_for_shard("Endirey-Russia")
    if end_idx is not None and end_idx not in deleted_idxs:
        meta[end_idx]["key"] = "Endirey-Russia"
        meta[end_idx]["name"] = "Endirey"
        if "Endirey-Russia" in polaris:
            ec = polaris["Endirey-Russia"]["coords"]
            meta[end_idx]["coords"] = [round(float(ec[1]), 5), round(float(ec[0]), 5)]
        meta[end_idx]["historical_names"] = [
            {"date": "1400.1.1", "name": "Endirey"},
            {"date": "1819.1.1", "name": "Andreyaul"},
            {"date": "1992.1.1", "name": "Endirey"},
        ]
        meta[end_idx]["other_names"] = [
            x for x in (meta[end_idx].get("other_names") or [])
            if norm_name(x) not in ("balkh", "балх", "alkas", "алкас") and "1700" not in str(x)
        ]

    # 10. Final sweep: deduplicate any remaining unkeyed (key=None) entry within <= 15 km of a keyed POLARIS entry with identical name!
    # Build spatial grid of keyed POLARIS metadata entries
    keyed_pol_by_name = defaultdict(list)
    for i, r in enumerate(meta):
        if i in deleted_idxs or not isinstance(r, dict):
            continue
        k = r.get("key")
        if k and k in polaris:
            keyed_pol_by_name[norm_name(r.get("name", ""))].append(i)

    for i, r in enumerate(meta):
        if i in deleted_idxs or not isinstance(r, dict) or r.get("key"):
            continue
        nm = norm_name(r.get("name", ""))
        cands = keyed_pol_by_name.get(nm)
        if not cands:
            continue
        co = r.get("coords")
        if not isinstance(co, list) or len(co) < 2:
            continue
        best_ki = None
        best_d = 15.0
        for ki in cands:
            kco = meta[ki].get("coords")
            if not isinstance(kco, list) or len(kco) < 2:
                continue
            d = hav_km(co[1], co[0], kco[1], kco[0])
            if d < best_d:
                best_d = d
                best_ki = ki
        if best_ki is not None:
            merge_meta_records(meta[best_ki], r)
            deleted_idxs.add(i)
            stats["unkeyed_close_dups_merged"] += 1

    # Also deduplicate any pair of unkeyed (key=None) entries within <= 15 km with identical name inside POLARIS
    pol_grid = defaultdict(list)
    for k, v in polaris.items():
        co = v.get("coords")
        if isinstance(co, list) and len(co) >= 2:
            pol_grid[(int(math.floor(co[0])), int(math.floor(co[1])))].append((k, float(co[0]), float(co[1])))

    def is_near_polaris(lat, lon):
        clat, clon = int(math.floor(lat)), int(math.floor(lon))
        for dl in (-1, 0, 1):
            for dn in (-1, 0, 1):
                for k, plat, plon in pol_grid.get((clat + dl, clon + dn), ()):
                    if hav_km(lat, lon, plat, plon) <= 10.0:
                        return True
        return False

    unkeyed_pol_by_name = defaultdict(list)
    for i, r in enumerate(meta):
        if i in deleted_idxs or not isinstance(r, dict) or r.get("key"):
            continue
        co = r.get("coords")
        if isinstance(co, list) and len(co) >= 2 and is_near_polaris(co[1], co[0]):
            unkeyed_pol_by_name[norm_name(r.get("name", ""))].append(i)

    for nm, idxs in unkeyed_pol_by_name.items():
        if len(idxs) < 2 or not nm:
            continue
        # Cluster within <= 15 km
        idxs_sorted = sorted(idxs, key=lambda idx: (
            0 if meta[idx].get("capital") else 1,
            -len(meta[idx].get("historical_names") or []),
            idx,
        ))
        kept = []
        for idx in idxs_sorted:
            if idx in deleted_idxs:
                continue
            co = meta[idx]["coords"]
            merged_into = None
            for ki in kept:
                kco = meta[ki]["coords"]
                if hav_km(co[1], co[0], kco[1], kco[0]) <= 15.0:
                    merged_into = ki
                    break
            if merged_into is not None:
                merge_meta_records(meta[merged_into], meta[idx])
                deleted_idxs.add(idx)
                stats["unkeyed_close_dups_merged"] += 1
            else:
                kept.append(idx)

    # 11. Deduplicate any duplicate explicit keys globally (e.g., Sagadahoc-Maine)
    seen_exp_keys = {}
    for i, r in enumerate(meta):
        if i in deleted_idxs or not isinstance(r, dict):
            continue
        k = r.get("key")
        if not k:
            continue
        if k in seen_exp_keys:
            merge_meta_records(meta[seen_exp_keys[k]], r)
            deleted_idxs.add(i)
        else:
            seen_exp_keys[k] = i

    # Write final cleaned city_metadata.json
    cleaned = [r for i, r in enumerate(meta) if i not in deleted_idxs]
    stats["final_count"] = len(cleaned)

    with open(META_PATH, "w", encoding="utf-8") as fh:
        json.dump(cleaned, fh, ensure_ascii=False, indent=2)

    print("DONE repairing Dataview city_metadata.json:")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
