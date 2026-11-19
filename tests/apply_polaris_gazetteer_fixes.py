# -*- coding: utf-8 -*-
"""Applies all Gemini 3.8 Flash audited MERGE and DROP_JUNK resolutions across
all 23 raw POLARIS *_settlements.json gazetteers and synchronises every
corresponding *_source_ledger.json5 file.
"""

import json
import math
import os
import re
import unicodedata
from collections import defaultdict
import json5

SVEA = r"f:\Active Projects\Project 1509 - SVEA"
DV = r"F:\Active Projects\Project 1436 - Dataview"
POLARIS_RAW = os.path.join(SVEA, "histmap", "1.data_raw", "population_regional", "POLARIS")
SHARD_DIR = os.path.join(DV, "data", "stadester", "stadester_2.0")
BDIR = os.path.join(SVEA, "tests", "polaris_batches")


def hav_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp * 0.5) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl * 0.5) ** 2
    return 2.0 * r * math.asin(min(1.0, math.sqrt(a)))


def norm_stem(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"_[a-z]{2}_\d+$", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def slavic_stem(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"_[a-z]{2}_\d+$", "", s)
    s = re.sub(r"['’`´\-.,\s]", "", s)
    s = s.replace("shch", "sc").replace("szcz", "sc")
    s = s.replace("zh", "z").replace("sh", "s").replace("sz", "s")
    s = s.replace("kh", "c").replace("ch", "c").replace("cz", "c").replace("ts", "c")
    s = s.replace("h", "c").replace("j", "y").replace("y", "i")
    s = re.sub(r"(.)\1+", r"\1", s)
    return re.sub(r"[^a-z0-9]", "", s)


def pos_years(pop):
    if not isinstance(pop, dict):
        return []
    out = []
    for yk, yv in pop.items():
        try:
            yi = int(yk)
            if float(yv) > 0:
                out.append(yi)
        except Exception:
            pass
    return sorted(out)


def is_junk_alias(name):
    s = str(name or "").strip()
    if not s or len(s) > 48:
        return True
    if re.search(
        r"\b(gorodishche|garadzishcha|hillfort|iron age|bronze age|stone age|neolithic|eneolithic|"
        r"palaeolithic|paleolithic|mesolithic|mediaeval|medieval|site\s*\d*|sinagoga|tserkov|"
        r"kulturnyy|dostoprimechatelnoe|ruiny|kremlin|kreml|fortress|castle|nekropol|selishche|"
        r"stayanka|poselenie|poselennya|historical quarter|guardian lions|category:|17001900)\b",
        s,
        re.I,
    ):
        return True
    return False


def main():
    # 1. Load compiled POLARIS shards (for reference coords, years, countries)
    polaris = {}
    for fn in ["02_polaris_1.json", "02_polaris_2.json"]:
        polaris.update(json.load(open(os.path.join(SHARD_DIR, fn), "r", encoding="utf-8")))

    # 2. Load all 23 raw POLARIS gazetteer files
    manifest = json5.load(open(os.path.join(POLARIS_RAW, "polaris_gazetteers.json5"), "r", encoding="utf-8"))
    gaz_files = []  # list of dicts: {key, path, abs_path, priority, domain, data, ledger_path, exclusions}
    for g in manifest["gazetteers"]:
        rel = g["path"]
        abs_p = os.path.join(SVEA, rel)
        data = json.load(open(abs_p, "r", encoding="utf-8"))
        ledger_p = re.sub(r"_settlements\.json$", "_source_ledger.json5", abs_p)
        gaz_files.append({
            "id": g["key"],
            "rel": rel,
            "abs_path": abs_p,
            "priority": g.get("priority", 1),
            "domain": g.get("domain", [-10000, 2026]),
            "data": data,
            "ledger_path": ledger_p,
            "exclusions": {},  # removed_key -> (reason_code, justification)
            "modified": False,
        })

    # Build quick lookup: raw_key -> list of gaz_idx
    def build_raw_index():
        idx = defaultdict(list)
        for gi, gf in enumerate(gaz_files):
            for k in gf["data"].keys():
                idx[k].append(gi)
        return idx

    raw_index = build_raw_index()

    # 3. Aggregate Gemini 3.8 Flash audited decisions
    merges = {}  # src_shard_key -> (tgt_shard_key, reason)
    drops = {}   # shard_key -> reason
    for fn in sorted(os.listdir(BDIR)):
        if not fn.startswith("out_tier") or not fn.endswith(".json"):
            continue
        arr = json.load(open(os.path.join(BDIR, fn), "r", encoding="utf-8"))
        for cl in arr:
            for act in (cl.get("actions") or []):
                op = act.get("op")
                if op == "MERGE":
                    sk = act["source_key"]
                    tk = act["target_key"]
                    if sk == "Kerch-Ukraine_2" and tk == "Kerch-Ukraine":
                        tk = "Ker`c-Ukraine"
                    merges[sk] = (tk, act.get("reason", "Duplicate settlement consolidated"))
                elif op == "DROP_JUNK":
                    drops[act["key"]] = act.get("reason", "Heritage monument or anachronistic scrape artefact removed")

    # Resolve transitive merge chains
    def resolve_tgt(k):
        seen = set()
        cur = k
        while cur in merges and cur not in seen:
            seen.add(cur)
            cur = merges[cur][0]
        return cur

    for s in list(merges.keys()):
        ft = resolve_tgt(s)
        if ft != merges[s][0]:
            merges[s] = (ft, merges[s][1])

    # Helper: locate exact raw (gaz_idx, raw_key) occurrences of a compiled shard key
    def locate_raw_occurrences(shard_key):
        sh = polaris.get(shard_key)
        hits = []
        # Exact key match first
        if shard_key in raw_index:
            for gi in raw_index[shard_key]:
                v = gaz_files[gi]["data"].get(shard_key)
                if not v:
                    continue
                if sh and isinstance(sh.get("coords"), list) and isinstance(v.get("coords"), list):
                    d = hav_km(sh["coords"][0], sh["coords"][1], v["coords"][0], v["coords"][1])
                    # Only take exact-key occurrences reasonably close to this shard entry
                    # (if a suffixed _2 twin exists, base key might be in two places!)
                    sh_yrs = set(pos_years(sh.get("population")))
                    v_yrs = set(pos_years(v.get("population")))
                    if d <= 15.0 or (sh_yrs and v_yrs and (sh_yrs & v_yrs) and d <= 30.0):
                        hits.append((gi, shard_key))
                else:
                    hits.append((gi, shard_key))
            if hits:
                return hits

        # Suffixed key (e.g., Tomsk-Russia_2 -> base Tomsk-Russia)
        m = re.match(r"^(.+)_(\d+)$", shard_key)
        if m and sh:
            base = m.group(1)
            sh_c = sh.get("coords")
            sh_yrs = set(pos_years(sh.get("population")))
            if base in raw_index and isinstance(sh_c, list) and len(sh_c) >= 2:
                scored = []
                for gi in raw_index[base]:
                    v = gaz_files[gi]["data"].get(base)
                    if not v or not isinstance(v.get("coords"), list):
                        continue
                    d = hav_km(sh_c[0], sh_c[1], v["coords"][0], v["coords"][1])
                    v_yrs = set(pos_years(v.get("population")))
                    ovlp = len(sh_yrs & v_yrs)
                    if d <= 2.5 and (ovlp > 0 or not sh_yrs):
                        scored.append((gi, base, d, ovlp))
                if not scored:
                    # Slightly wider tolerance if coords shifted marginally during merge
                    for gi in raw_index[base]:
                        v = gaz_files[gi]["data"].get(base)
                        if not v or not isinstance(v.get("coords"), list):
                            continue
                        d = hav_km(sh_c[0], sh_c[1], v["coords"][0], v["coords"][1])
                        v_yrs = set(pos_years(v.get("population")))
                        ovlp = len(sh_yrs & v_yrs)
                        if d <= 8.0 and ovlp > 0 and v_yrs.issubset(sh_yrs | set(range(min(sh_yrs)-5, max(sh_yrs)+6))):
                            scored.append((gi, base, d, ovlp))
                if scored:
                    return [(gi, bk) for gi, bk, _, _ in scored]
        return hits

    # Helper: locate canonical raw POLARIS key for a target_key (handles Populstat keys like Kyjiv-Ukraine -> Kyiv-Ukraine)
    def locate_target_raw_occurrences(target_key):
        exact = locate_raw_occurrences(target_key)
        if exact:
            return exact
        sh = polaris.get(target_key)
        if not sh or not isinstance(sh.get("coords"), list):
            return []
        t_lat, t_lon = float(sh["coords"][0]), float(sh["coords"][1])
        t_ctry = str(sh.get("country") or "").lower().strip()
        t_stems = {slavic_stem(sh.get("name", ""))}
        for on in (sh.get("other_names") or []):
            t_stems.add(slavic_stem(on))
        # Strip country suffix from target_key too
        tk_base = re.sub(r"-[^-]+$", "", target_key)
        t_stems.add(slavic_stem(tk_base))
        t_stems.discard("")

        cand_by_raw_key = defaultdict(list)
        for gi, gf in enumerate(gaz_files):
            for rk, rv in gf["data"].items():
                if not isinstance(rv, dict) or not isinstance(rv.get("coords"), list):
                    continue
                if str(rv.get("country") or "").lower().strip() != t_ctry:
                    continue
                d = hav_km(t_lat, t_lon, rv["coords"][0], rv["coords"][1])
                if d > 15.0:
                    continue
                r_stems = {slavic_stem(rv.get("name", "")), slavic_stem(re.sub(r"-[^-]+$", "", rk))}
                for on in (rv.get("other_names") or []):
                    r_stems.add(slavic_stem(on))
                r_stems.discard("")
                if (t_stems & r_stems) or d <= 1.0:
                    cand_by_raw_key[rk].append((gi, d, gf["priority"]))
        if not cand_by_raw_key:
            return []
        # Pick raw_key with highest max priority, most files, smallest min dist
        best_rk = max(
            cand_by_raw_key.keys(),
            key=lambda rk: (
                max(x[2] for x in cand_by_raw_key[rk]),
                len(cand_by_raw_key[rk]),
                -min(x[1] for x in cand_by_raw_key[rk]),
            ),
        )
        return [(gi, best_rk) for gi, _, _ in cand_by_raw_key[best_rk]]

    stats = {
        "drops_applied_entries": 0,
        "drops_keys_found": 0,
        "drops_keys_missed": [],
        "merges_applied_entries": 0,
        "merges_keys_found": 0,
        "merges_keys_missed": [],
        "backfilled_years": 0,
        "coord_alignments": 0,
        "category_prefix_cleaned": 0,
    }

    # 4. Apply DROP_JUNK across raw POLARIS gazetteers
    for dk, reason in sorted(drops.items()):
        occs = locate_raw_occurrences(dk)
        if not occs:
            stats["drops_keys_missed"].append(dk)
            continue
        stats["drops_keys_found"] += 1
        for gi, rk in occs:
            if rk in gaz_files[gi]["data"]:
                del gaz_files[gi]["data"][rk]
                gaz_files[gi]["exclusions"][rk] = ("heritage_monument_or_anachronism", reason)
                gaz_files[gi]["modified"] = True
                stats["drops_applied_entries"] += 1

    # Also drop any Category:* keys in raw POLARIS if present
    for gi, gf in enumerate(gaz_files):
        cat_keys = [k for k in list(gf["data"].keys()) if k.startswith("Category:")]
        for ck in cat_keys:
            del gf["data"][ck]
            gf["exclusions"][ck] = ("wikipedia_category_artefact", "Removed Wikipedia Category: prefix scrape artefact.")
            gf["modified"] = True
            stats["category_prefix_cleaned"] += 1

    # Rebuild raw index after drops
    raw_index = build_raw_index()

    # 5. Special coord-alignment bridge cases (legacy Populstat/Chandler/Buringh twins whose target isn't in raw POLARIS)
    bridge_coord_fixes = {
        "Tushino-Russia": ([55.83333, 37.46667], ["Tu'sino"]),
        "Babushkin_RU_48-Russia": ([55.86667, 37.66667], ["Babu'skin", "Babushkin"]),
        "Perovo-Russia": ([55.75, 37.78333], []),
        "Pochinki-Russia": ([54.70146, 44.85762], ["Pochinki, Pochinkovsky District, Nizhny Novgorod Oblast"]),
    }

    # 6. Apply MERGE across raw POLARIS gazetteers
    for sk, (tk, reason) in sorted(merges.items()):
        # Special case: Tushino / Babushkin_RU_48 / Perovo_2 merging into Populstat-only twin
        if sk in ("Tushino-Russia", "Babushkin_RU_48-Russia", "Perovo-Russia_2"):
            raw_k = "Perovo-Russia" if sk == "Perovo-Russia_2" else sk
            new_coords, extra_aliases = bridge_coord_fixes[raw_k]
            occs = locate_raw_occurrences(sk)
            for gi, rk in occs:
                entry = gaz_files[gi]["data"].get(rk)
                if entry:
                    entry["coords"] = list(new_coords)
                    ons = list(entry.get("other_names") or [])
                    for ea in extra_aliases:
                        if ea not in ons:
                            ons.append(ea)
                    entry["other_names"] = ons
                    gaz_files[gi]["modified"] = True
                    stats["coord_alignments"] += 1
            stats["merges_keys_found"] += 1
            continue

        # Special case: Talianki-Ukraine (Chandler -2000) -> align Talianky-Ukraine_2 (-3600..-2000 in kiev_and_pereyaslavl)
        if sk == "Talianki-Ukraine" or tk == "Talianki-Ukraine":
            other_k = tk if sk == "Talianki-Ukraine" else sk
            occs = locate_raw_occurrences(other_k)
            sh_ch = polaris.get("Talianki-Ukraine")
            if sh_ch and occs:
                for gi, rk in occs:
                    entry = gaz_files[gi]["data"].get(rk)
                    if entry:
                        entry["coords"] = [float(sh_ch["coords"][0]), float(sh_ch["coords"][1])]
                        ons = list(entry.get("other_names") or [])
                        for ea in ["Talianki", "Talyanki"]:
                            if ea not in ons:
                                ons.append(ea)
                        entry["other_names"] = ons
                        gaz_files[gi]["modified"] = True
                        stats["coord_alignments"] += 1
            stats["merges_keys_found"] += 1
            continue

        # Special case: Pochinki, Pochinkovsky District... (Buringh) -> handled via alias + coord align on Pochinki-Russia
        if sk == "Pochinki, Pochinkovsky District, Nizhny Novgorod Oblast-Russia":
            sh_b = polaris.get(sk)
            occs = locate_target_raw_occurrences(tk)
            for gi, rk in occs:
                entry = gaz_files[gi]["data"].get(rk)
                if entry and sh_b:
                    ons = list(entry.get("other_names") or [])
                    for ea in ["Pochinki, Pochinkovsky District, Nizhny Novgorod Oblast"]:
                        if ea not in ons:
                            ons.append(ea)
                    entry["other_names"] = ons
                    gaz_files[gi]["modified"] = True
            stats["merges_keys_found"] += 1
            continue

        src_occs = locate_raw_occurrences(sk)
        if not src_occs:
            stats["merges_keys_missed"].append((sk, tk))
            continue

        tgt_occs = locate_target_raw_occurrences(tk)
        stats["merges_keys_found"] += 1

        # Collect source years and aliases before removing source entries
        src_pop_all = {}
        src_aliases = []
        src_found = None
        for gi, rk in src_occs:
            sv = gaz_files[gi]["data"].get(rk)
            if not sv:
                continue
            for yk, yv in (sv.get("population") or {}).items():
                try:
                    yi = int(yk)
                    vf = float(yv)
                    if vf > 0 and yi not in src_pop_all:
                        src_pop_all[yi] = int(round(vf))
                except Exception:
                    pass
            if not is_junk_alias(sv.get("name")):
                src_aliases.append(sv["name"])
            for on in (sv.get("other_names") or []):
                if not is_junk_alias(on):
                    src_aliases.append(on)
            fy = sv.get("found.yr", sv.get("foundation_year"))
            try:
                if fy is not None and math.isfinite(float(fy)):
                    fyi = int(float(fy))
                    if src_found is None or fyi < src_found:
                        src_found = fyi
            except Exception:
                pass

        # Backfill non-overlapping earlier/missing years onto target raw occurrences if target exists in raw
        if tgt_occs:
            # Find all years already covered by target across its raw files
            tgt_existing_yrs = set()
            for tgi, trk in tgt_occs:
                tv = gaz_files[tgi]["data"].get(trk)
                if tv:
                    tgt_existing_yrs.update(pos_years(tv.get("population")))
            tgt_min_yr = min(tgt_existing_yrs) if tgt_existing_yrs else 99999

            # Pick the best raw target file for alias attachment (highest priority, then earliest)
            tgt_occs_sorted = sorted(tgt_occs, key=lambda pair: (-gaz_files[pair[0]]["priority"], gaz_files[pair[0]]["domain"][0]))
            primary_tgi, primary_trk = tgt_occs_sorted[0]
            primary_tv = gaz_files[primary_tgi]["data"].get(primary_trk)
            if primary_tv:
                ons = list(primary_tv.get("other_names") or [])
                seen_on = {primary_tv.get("name")} | set(ons)
                for a in src_aliases:
                    if a and a not in seen_on:
                        ons.append(a)
                        seen_on.add(a)
                primary_tv["other_names"] = ons
                gaz_files[primary_tgi]["modified"] = True

            # Only backfill years strictly earlier than tgt_min_yr (or missing years inside a matching domain)
            # when the source is NOT a tiny monument/fortress (< 0.2x target peak) and connects within <= 200 yrs
            # Check gap between src_pop_all and tgt_existing_yrs
            src_yrs_sorted = sorted(src_pop_all.keys())
            if src_yrs_sorted and tgt_existing_yrs:
                # Find any strictly earlier years from source that connect continuously (gap <= 200y) to target
                earlier_yrs = [y for y in src_yrs_sorted if y < tgt_min_yr]
                if earlier_yrs and (tgt_min_yr - earlier_yrs[-1]) <= 200:
                    # Place earlier years into the earliest target file whose domain covers them,
                    # or if none, into the earliest target file with priority <= 2 (or earliest target file)
                    for yr in earlier_yrs:
                        placed = False
                        for tgi, trk in sorted(tgt_occs, key=lambda pair: (gaz_files[pair[0]]["priority"], gaz_files[pair[0]]["domain"][0])):
                            dom = gaz_files[tgi]["domain"]
                            if dom[0] <= yr <= dom[1]:
                                tv = gaz_files[tgi]["data"].get(trk)
                                if tv is not None:
                                    tv.setdefault("population", {})[str(yr)] = src_pop_all[yr]
                                    # Keep foundation_year consistent
                                    fy = tv.get("found.yr", tv.get("foundation_year"))
                                    if fy is not None:
                                        try:
                                            if yr < int(float(fy)):
                                                if "found.yr" in tv:
                                                    tv["found.yr"] = yr
                                                if "foundation_year" in tv:
                                                    tv["foundation_year"] = yr
                                        except Exception:
                                            pass
                                    gaz_files[tgi]["modified"] = True
                                    stats["backfilled_years"] += 1
                                    placed = True
                                    break
                        if not placed:
                            # Put into earliest target file if within reason (e.g. pre-1400 on p3 tsardom or earliest p2)
                            tgi, trk = sorted(tgt_occs, key=lambda pair: (gaz_files[pair[0]]["domain"][0], gaz_files[pair[0]]["priority"]))[0]
                            tv = gaz_files[tgi]["data"].get(trk)
                            if tv is not None:
                                tv.setdefault("population", {})[str(yr)] = src_pop_all[yr]
                                fy = tv.get("found.yr", tv.get("foundation_year"))
                                if fy is not None:
                                    try:
                                        if yr < int(float(fy)):
                                            if "found.yr" in tv:
                                                tv["found.yr"] = yr
                                            if "foundation_year" in tv:
                                                tv["foundation_year"] = yr
                                    except Exception:
                                        pass
                                gaz_files[tgi]["modified"] = True
                                stats["backfilled_years"] += 1

        # Remove duplicate source entries (making sure we NEVER delete a (gi, rk) that is ALSO in tgt_occs!)
        tgt_occ_set = set(tgt_occs)
        for gi, rk in src_occs:
            if (gi, rk) in tgt_occ_set:
                continue
            if rk in gaz_files[gi]["data"]:
                del gaz_files[gi]["data"][rk]
                gaz_files[gi]["exclusions"][rk] = ("duplicate_consolidated", f"Consolidated into {tk}: {reason}")
                gaz_files[gi]["modified"] = True
                stats["merges_applied_entries"] += 1

    # 7. Also specifically check Endirey in dagestan & migration_period to guarantee zero residual overlap!
    # Check Andreyaul (17001900)-Russia in migration_period and Enderi-Russia in dagestan
    for gf in gaz_files:
        if gf["id"] == "migration_period":
            if "Andreyaul (17001900)-Russia" in gf["data"]:
                del gf["data"]["Andreyaul (17001900)-Russia"]
                gf["exclusions"]["Andreyaul (17001900)-Russia"] = ("duplicate_consolidated", "Consolidated into Endirey-Russia.")
                gf["modified"] = True
                stats["merges_applied_entries"] += 1

    # 8. Sort population dicts & write modified raw gazetteer files + sync ALL *_source_ledger.json5
    modified_files = 0
    ledgers_synced = 0
    for gf in gaz_files:
        if gf["modified"]:
            # Sort population keys ascending inside every modified file
            for k, v in gf["data"].items():
                if isinstance(v, dict) and isinstance(v.get("population"), dict):
                    v["population"] = {
                        str(y): v["population"][str(y)]
                        for y in sorted(int(yk) for yk in v["population"].keys())
                    }
            with open(gf["abs_path"], "w", encoding="utf-8") as fh:
                json.dump(gf["data"], fh, ensure_ascii=False, indent=2)
            modified_files += 1

        # Sync source ledger whenever modified OR out of sync with settlements.json
        lp = gf["ledger_path"]
        if os.path.isfile(lp):
            with open(lp, "r", encoding="utf-8") as fh:
                raw_txt = fh.read()
            try:
                ledger = json.loads(raw_txt)
            except ValueError:
                ledger = json5.loads(raw_txt)
            cands = ledger.get("candidates") or []
            inc_keys_ledger = {str(c.get("settlement_key") or "").strip() for c in cands if c.get("status") == "included"}
            if not gf["modified"] and inc_keys_ledger == set(gf["data"].keys()) and ledger.get("total_included") == len(gf["data"]):
                continue
            seen_keys = set()
            new_cands = []
            for c in cands:
                ck = str(c.get("settlement_key") or "").strip()
                if ck in gf["exclusions"]:
                    rc, justif = gf["exclusions"][ck]
                    c["status"] = "excluded"
                    c["reason"] = rc
                    c["justification"] = justif
                    seen_keys.add(ck)
                    new_cands.append(c)
                elif ck in gf["data"]:
                    c["status"] = "included"
                    seen_keys.add(ck)
                    new_cands.append(c)
                else:
                    # Keep existing excluded records; mark vanished included records excluded
                    if c.get("status") == "included":
                        c["status"] = "excluded"
                        c["reason"] = "duplicate_consolidated"
                        c["justification"] = "Consolidated during POLARIS duplicate-name resolution."
                    if ck:
                        seen_keys.add(ck)
                    new_cands.append(c)
            # Append any exclusion not previously in ledger
            for ek, (rc, justif) in gf["exclusions"].items():
                if ek not in seen_keys:
                    new_cands.append({
                        "settlement_key": ek,
                        "name": re.sub(r"-[^-]+$", "", ek),
                        "country": ek.split("-")[-1] if "-" in ek else "Russia",
                        "status": "excluded",
                        "reason": rc,
                        "justification": justif,
                    })
            ledger["candidates"] = new_cands
            ledger["total_included"] = sum(1 for c in new_cands if c.get("status") == "included")
            ledger["total_excluded"] = sum(1 for c in new_cands if c.get("status") == "excluded")
            with open(lp, "w", encoding="utf-8") as fh:
                json.dump(ledger, fh, ensure_ascii=False, indent=2)
            ledgers_synced += 1

    print(f"Modified raw POLARIS gazetteers: {modified_files} / {len(gaz_files)}")
    print(f"Synchronised source ledgers:     {ledgers_synced}")
    print(f"Stats: {json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in stats.items()}, indent=2)}")
    if stats["drops_keys_missed"]:
        print("Missed drop keys:", stats["drops_keys_missed"][:15])
    if stats["merges_keys_missed"]:
        print("Missed merge keys:", stats["merges_keys_missed"][:15])


if __name__ == "__main__":
    main()
