"""Commits Gemini 3.8 Flash master historical toponymy records (`INDUS` V2 + `CASTLE`)
into Dataview `data/stadester/stadester_2.0/city_metadata.json` with:
- Unconditional purging of ALL monument/temple/religious/building/non-settlement entries & stale monument historical_names,
- Authoritative V2 `foundation_year`-aligned `historical_names` overwrites (fixing Besnagar->Bhilsa, Nohta Temple->Nohta, Indore->1715, etc.),
- Signature A/B terminal modern name anchoring (`max_year >= 1950`),
- Local script purity (South Asian scripts + Latin for INDUS; CJK/Kana/Hangul + Latin for CASTLE).
"""

import json
import math
import os
import re
import sys


SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
META_PATH = r"F:\Active Projects\Project 1436 - Dataview\data\stadester\stadester_2.0\city_metadata.json"
CACHE_DIR = r"F:\Active Projects\Project 1436 - Dataview\data\stadester\cache"

sys.path.insert(0, os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "scripts"))
sys.path.insert(0, os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "_gis_cache"))
import resolve_indus_toponymy as ri
import resolve_castle_toponymy as rc

DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")
SAFE_TOWNS = {
  "dharamshala", "mandir hasaud", "haveli", "ali masjid", "chhatri", "niwas",
  "koteshwar", "dalsingh sarai", "kheta sarai", "sarai mir", "sarai khas", "ekangar sarai"
}
MON_BAN_RE = re.compile(
  r"(\b(temple|temples|mandir|masjid|mosque|tomb|tombs|haveli|gadhi|durg|marhia|matha|gunti|wall|fortification|cave|caves|rock\s+cut|rock-cut|stupa|pillar|slab|fresco|statue|stature|effigy|pagoda|stele|shrine|monastery|vihara|chaitya|church|chapel|cathedral|bridge|baoli|stepwell|chhatri|palace|gate|gateway|ruins|ruined|monument|memorial|raslilaghar|chauburji|ordnance\s+factory|power\s+plant|housing\s+society|fertilizer|heavy\s+electricals|reliance\s+complex|aeronautics\s+limited|rest\s+house|iseki\s+site|seoktap|seokdeung|sunsubi|buljwasang|ipsang|sajeokbi)\b)",
  re.I,
)


def is_monument_str(s):
  t = str(s or "").strip()
  if not t:
    return False
  if t.lower() in SAFE_TOWNS:
    return False
  return bool(MON_BAN_RE.search(t)) or len(t) > 42


def haversine_km(la1, lo1, la2, lo2):
  d1 = math.radians(la2 - la1)
  d2 = math.radians(lo2 - lo1)
  a = math.sin(d1 / 2) ** 2 + math.cos(math.radians(la1)) * math.cos(math.radians(la2)) * math.sin(d2 / 2) ** 2
  return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def date_tuple(ds):
  p = str(ds or "").split(".")
  if len(p) != 3:
    return (0, 1, 1)
  try:
    return (int(p[0]), int(p[1]), int(p[2]))
  except Exception:
    return (0, 1, 1)


def sort_dedup_hist(entries, mod):
  seen = set()
  clean = []
  for e in entries:
    if not isinstance(e, dict):
      continue
    ds = str(e.get("date") or "").strip()
    nm = mod.strip_parens(e.get("name") or "")
    if not DATE_RE.match(ds) or not mod.is_clean_name(nm):
      continue
    sig = f"{ds}|{nm.lower()}"
    if sig not in seen:
      seen.add(sig)
      clean.append({"date": ds, "name": nm})
  clean.sort(key=lambda x: date_tuple(x["date"]))
  dedup = []
  for e in clean:
    if dedup and dedup[-1]["name"].lower() == e["name"].lower():
      continue
    dedup.append(e)
  return dedup


def main():
  projs = [a.upper() for a in sys.argv[1:]] if len(sys.argv) > 1 else ["INDUS"]
  meta = json.load(open(META_PATH, "r", encoding="utf-8"))
  orig_total = len(meta)

  masters = {}
  drop_coords_names = []
  for proj in projs:
    v2_p = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", proj, "_shared", "flash_toponymy_master_v2.json")
    v1_p = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", proj, "_shared", "flash_toponymy_master.json")
    mp = v2_p if os.path.exists(v2_p) else v1_p
    masters[proj] = json.load(open(mp, "r", encoding="utf-8")).get("settlements", {})
    mod = ri if proj == "INDUS" else rc
    for v in masters[proj].values():
      if v.get("action") in ("DROP_MONUMENT", "DROP_NON_SETTLEMENT"):
        c = v.get("coords") or []
        if len(c) >= 2:
          drop_coords_names.append((float(c[0]), float(c[1]), mod.norm_key(v.get("orig_name") or ""), mod.norm_key(v.get("canonical_name") or "")))

  drop_grid = {}
  for dla, dlo, dnk1, dnk2 in drop_coords_names:
    gx, gy = int(round(dla * 4)), int(round(dlo * 4))
    drop_grid.setdefault((gx, gy), []).append((dla, dlo, dnk1, dnk2))

  # Step 1: Purge ALL dropped monument/non-settlement entries AND any entry whose name is a monument/religious building inside target bboxes
  kept_meta = []
  purged = 0
  scrubbed_hist = 0
  for e in meta:
    c = e.get("coords") or []
    if len(c) < 2:
      kept_meta.append(e)
      continue
    lng, lat = float(c[0]), float(c[1])
    in_ind = ("INDUS" in projs) and (60.0 <= lng <= 98.5 and -2.0 <= lat <= 38.5)
    in_cas = ("CASTLE" in projs) and (122.5 <= lng <= 147.0 and 23.5 <= lat <= 46.5)
    if not (in_ind or in_cas):
      kept_meta.append(e)
      continue
    nm = str(e.get("name") or "").strip()
    mod = ri if in_ind else rc
    nk = mod.norm_key(nm)
    if e.get("capital"):
      kept_meta.append(e)
      continue

    should_purge = False
    if is_monument_str(nm):
      should_purge = True
    else:
      gx, gy = int(round(lat * 4)), int(round(lng * 4))
      for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
          for dla, dlo, dnk1, dnk2 in drop_grid.get((gx + dx, gy + dy), []):
            if (nk == dnk1 or nk == dnk2) and haversine_km(lat, lng, dla, dlo) <= 2.0:
              should_purge = True
              break
          if should_purge:
            break
        if should_purge:
          break
    if should_purge:
      purged += 1
      continue

    # Also scrub any stale monument label inside historical_names of surviving entries (e.g. "Nohta Temple" -> "Nohta")
    hn = e.get("historical_names") or []
    if any(is_monument_str(h.get("name")) for h in hn if isinstance(h, dict)):
      new_hn = []
      for h in hn:
        if not isinstance(h, dict): continue
        hnm = str(h.get("name") or "")
        if is_monument_str(hnm):
          new_hn.append({"date": h["date"], "name": nm})
          scrubbed_hist += 1
        else:
          new_hn.append(h)
      e["historical_names"] = sort_dedup_hist(new_hn, mod)
    kept_meta.append(e)

  meta = kept_meta

  grid = {}
  for idx, e in enumerate(meta):
    c = e.get("coords") or []
    if len(c) < 2: continue
    lng, lat = float(c[0]), float(c[1])
    gx, gy = int(round(lat * 4)), int(round(lng * 4))
    grid.setdefault((gx, gy), []).append((idx, lat, lng))

  stats = {"updated": 0, "inserted": 0, "purged": purged, "scrubbed_hist": scrubbed_hist}

  # Step 2: Merge all kept/renamed Flash V2 settlements authoritatively
  for proj in projs:
    mod = ri if proj == "INDUS" else rc
    for v in masters[proj].values():
      if v.get("action") in ("DROP_MONUMENT", "DROP_NON_SETTLEMENT"):
        continue
      c = v.get("coords") or []
      if len(c) < 2: continue
      lat, lng = float(c[0]), float(c[1])
      canon = mod.strip_parens(v.get("canonical_name") or "")
      orig_nm = mod.strip_parens(v.get("orig_name") or "")
      if not mod.is_clean_name(canon) or is_monument_str(canon):
        continue
      nk_canon = mod.norm_key(canon)
      nk_orig = mod.norm_key(orig_nm)
      flash_hist = sort_dedup_hist(v.get("historical_names") or [], mod)
      fyr = int(v.get("foundation_year") if v.get("foundation_year") is not None else v.get("min_year", 1800))
      if not flash_hist:
        flash_hist = [{"date": f"{fyr}.1.1", "name": canon}]
      max_y = int(v.get("max_year") if v.get("max_year") is not None else 2025)

      if max_y >= 1950 and flash_hist:
        ln = flash_hist[-1]["name"]
        ly = date_tuple(flash_hist[-1]["date"])[0]
        if mod.norm_key(ln) != nk_canon:
          if ly < 1950:
            flash_hist.append({"date": f"{max(1950, ly + 1)}.1.1", "name": canon})
          else:
            canon = ln
            nk_canon = mod.norm_key(canon)

      gx, gy = int(round(lat * 4)), int(round(lng * 4))
      best_idx = None
      best_score = 999999.0
      for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
          for idx, mla, mlo in grid.get((gx + dx, gy + dy), []):
            d = haversine_km(lat, lng, mla, mlo)
            if d > 10.0: continue
            enm = mod.strip_parens(meta[idx].get("name") or "")
            enk = mod.norm_key(enm)
            name_match = (enk == nk_canon or (nk_orig and enk == nk_orig))
            if name_match and d < best_score:
              best_score = d
              best_idx = idx
            elif d <= 1.0 and (d + 5.0) < best_score:
              if not meta[idx].get("capital") or name_match:
                best_score = d + 5.0
                best_idx = idx

      flash_other = [o for o in (v.get("other_names") or []) if mod.is_clean_name(o) and not is_monument_str(o) and o.lower() != canon.lower()]

      if best_idx is not None:
        target = meta[best_idx]
        ex_hist = sort_dedup_hist(target.get("historical_names") or [], mod)
        ex_has_mon = any(is_monument_str(h["name"]) for h in ex_hist)
        ex_name = mod.strip_parens(target.get("name") or "")

        if mod.norm_key(ex_name) == nk_orig and nk_canon != nk_orig:
          target["name"] = canon
        elif is_monument_str(ex_name):
          target["name"] = canon

        t_canon = mod.strip_parens(target.get("name") or canon)
        # Authoritative overwrite: ALWAYS prefer Flash V2 when ex_has_mon OR len(ex_hist) <= 1 OR len(flash_hist) >= len(ex_hist)
        # Preserve strictly richer valid curated non-monument chains (e.g. Delhi 5-step, Chennai 5-step, Chattogram 5-step)
        if ex_has_mon or len(ex_hist) <= 1 or len(flash_hist) >= len(ex_hist):
          chosen = flash_hist
        else:
          # Preserve strictly richer curated chain ONLY if its earliest year doesn't wildly predate a post-1600 founded town
          ex_first_y = date_tuple(ex_hist[0]["date"])[0]
          if fyr >= 1600 and ex_first_y < fyr - 200:
            chosen = flash_hist
          else:
            chosen = ex_hist

        if max_y >= 1950 and chosen:
          ln = chosen[-1]["name"]
          ly = date_tuple(chosen[-1]["date"])[0]
          if mod.norm_key(ln) != mod.norm_key(t_canon):
            if ly < 1950:
              chosen.append({"date": f"{max(1950, ly + 1)}.1.1", "name": t_canon})
            else:
              target["name"] = ln
              t_canon = ln
        target["historical_names"] = sort_dedup_hist(chosen, mod)

        prev_o = [mod.strip_parens(o) for o in (target.get("other_names") or []) if mod.is_clean_name(mod.strip_parens(o)) and not is_monument_str(o)]
        merged_o = []
        seen_o = {t_canon.lower()}
        for o in prev_o + flash_other + [h["name"] for h in target["historical_names"]]:
          if o and len(o) <= 38 and mod.is_clean_name(o) and not is_monument_str(o) and o.lower() not in seen_o:
            seen_o.add(o.lower())
            merged_o.append(o)
        if merged_o:
          target["other_names"] = merged_o[:14]
        stats["updated"] += 1
      else:
        new_entry = {
          "coords": [round(lng, 5), round(lat, 5)],
          "historical_names": flash_hist,
          "name": canon,
        }
        if flash_other:
          new_entry["other_names"] = flash_other[:12]
        new_idx = len(meta)
        meta.append(new_entry)
        grid.setdefault((gx, gy), []).append((new_idx, lat, lng))
        stats["inserted"] += 1

  with open(META_PATH, "w", encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=2)

  removed_caches = 0
  for fn in ("stadester_2.0_indexed.json", "stadester_2.0_lite.json", "stadester_city_cache.json"):
    fp = os.path.join(CACHE_DIR, fn)
    if os.path.exists(fp):
      os.remove(fp)
      removed_caches += 1

  ind_m, ind_multi, ind_mon_left = 0, 0, 0
  for e in meta:
    c = e.get("coords") or []
    if len(c) < 2: continue
    lng, lat = float(c[0]), float(c[1])
    if 60.0 <= lng <= 98.5 and -2.0 <= lat <= 38.5:
      ind_m += 1
      hn = e.get("historical_names") or []
      if len(hn) >= 2: ind_multi += 1
      if is_monument_str(e.get("name")) or any(is_monument_str(h.get("name")) for h in hn if isinstance(h, dict)):
        ind_mon_left += 1

  print(f"[commit_flash_city_metadata V2] {orig_total:,} -> {len(meta):,} entries (purged={stats['purged']:,}, scrubbed_hist={stats['scrubbed_hist']:,}, updated={stats['updated']:,}, inserted={stats['inserted']:,}, removed_caches={removed_caches})")
  print(f"  INDUS bbox: {ind_m:,} entries, multi_hist(>=2)={ind_multi:,}, residual_monument_strings={ind_mon_left}")


if __name__ == "__main__":
  main()
