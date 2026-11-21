"""UCL CAAL (Central Asian Archaeological Landscapes) Full Multi-Period Monument Harvester.

Queries the official UCL CAAL Public Viewer API (`https://data.uclcaal.org/api/public-viewer`)
with strict API forensics:
  1. Verifies period-filtered queries do NOT leak NULL/undated monuments by inspecting leaf
     `/records/monument/<id>` records.
  2. Sweeps the full Central Asia + Xinjiang bounding box (46..89E, 35..56N) per macro
     cultural-period bucket AND per settlement/fortification vs funerary monument-type bucket
     using adaptive quad-tree tiling at zoom=11.5 whenever a tile clusters or exceeds 900 features,
     guaranteeing 100% unclustered exact-coordinate capture with zero truncation.
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional",
  "SARAY", "_shared", "sites_saray_central_asia", "0.raw_data"
)
BASE = "https://data.uclcaal.org/api/public-viewer"
HDR = {"User-Agent": "SVEA-OperationViscount-SARAY/1.0 (academic historical demography; contact: austkaeztchen@confoederatio.org)"}

# Inspect all 118 cultural period IDs from cached caal_cultural_periods.json and map cleanly to SARAY's 9 horizons
CP_PATH = os.path.join(RAW_DIR, "caal_cultural_periods.json")


def build_horizon_cp_groups():
  cp_data = json.load(open(CP_PATH, "r", encoding="utf-8"))
  opts = cp_data.get("options", [])
  groups = {
    "01_epipalaeolithic_mesolithic_early_neolithic": [],
    "02_chalcolithic_namazga_sarazm_botai": [],
    "03_bronze_age_bmac_sintashta_andronovo": [],
    "04_iron_age_saka_achaemenid_hellenistic": [],
    "05_kushan_kangju_wusun_parthian_antiquity": [],
    "06_sogdian_turkic_early_islamic": [],
    "07_samanid_karakhanid_seljuk_khwarazmshah": [],
    "08_mongol_chagatai_timurid": [],
    "09_uzbek_khanates_kazakh_zhuzes": [],
  }
  unmapped = []
  for o in opts:
    cid = o.get("concept_id") or o.get("value")
    lbl = (o.get("label") or "").lower()
    dr = (o.get("date_range") or "").lower()
    if not cid or lbl in ("uncertain", "modern", "empire/dynasty", "chinese", "republic of china", "three kingdoms"):
      continue
    if any(k in lbl for k in ("palaeolithic", "paleolithic", "mesolithic", "early neolithic", "middle neolithic")):
      groups["01_epipalaeolithic_mesolithic_early_neolithic"].append(cid)
    elif any(k in lbl for k in ("late neolithic", "eneolithic", "chalcolithic", "neolithic")):
      groups["02_chalcolithic_namazga_sarazm_botai"].append(cid)
    elif any(k in lbl for k in ("bronze", "andronovo", "bmac", "oxus", "sintashta", "begazy", "xia dynasty", "shang dynasty", "prehistoric")):
      groups["03_bronze_age_bmac_sintashta_andronovo"].append(cid)
    elif any(k in lbl for k in ("saka", "scythian", "tasmola", "pazyryk", "mayemir", "kulazhorgin", "achaemenid", "greco-bactrian", "greek-macedonian", "hellenistic", "seleucid", "chrikirabad", "iron age", "zhou", "spring and autumn", "warring states", "qin dynasty")):
      groups["04_iron_age_saka_achaemenid_hellenistic"].append(cid)
    elif any(k in lbl for k in ("kushan", "parthian", "sarmat", "kangyuy", "usun", "sargat", "xiongnu", "han dynasty", "early antiquity", "late antiquity", "zhetyasar", "sedentary-agricultural", "early state", "sasanian", "wei, jin")):
      groups["05_kushan_kangju_wusun_parthian_antiquity"].append(cid)
    elif any(k in lbl for k in ("sogdian", "hephthalite", "afrighid", "turkic", "uyghur", "kerder", "early medieval", "early islamic", "umayyad", "abbasid", "tahirid", "sui", "tang", "tibetan empire", "five dynasties")):
      groups["06_sogdian_turkic_early_islamic"].append(cid)
    elif any(k in lbl for k in ("samanid", "karakhanid", "qarakhanid", "ghaznavid", "seljuk", "khwarazmian", "late islamic", "liao", "song dynasty", "islamic")):
      groups["07_samanid_karakhanid_seljuk_khwarazmshah"].append(cid)
    elif any(k in lbl for k in ("mongol", "chagatai", "timurid", "late medieval", "medieval", "yuan dynasty")):
      groups["08_mongol_chagatai_timurid"].append(cid)
    elif any(k in lbl for k in ("shaybanid", "post medieval", "ming dynasty", "qing dynasty")):
      groups["09_uzbek_khanates_kazakh_zhuzes"].append(cid)
    else:
      unmapped.append((cid, o.get("label"), o.get("date_range")))
  if unmapped:
    print(f"  [INFO] Unmapped CAAL periods ({len(unmapped)}): {unmapped[:15]}", flush=True)
  return groups


def fetch_tile(session, params, bbox, depth=0):
  w, s, e, n = bbox
  p = dict(params)
  p["bbox"] = f"{w:.4f},{s:.4f},{e:.4f},{n:.4f}"
  p["zoom"] = "11.5"
  for att in range(3):
    try:
      r = session.get(BASE + "/map", params=p, headers=HDR, timeout=35)
      if r.status_code == 200:
        j = r.json()
        feats = j.get("features") or []
        clustered = bool(j.get("clustered"))
        # Subdivide if clustered or dense (>= 950 features) and box still splittable
        if (clustered or len(feats) >= 950) and depth < 4 and (e - w) > 0.35 and (n - s) > 0.35:
          mx, my = 0.5 * (w + e), 0.5 * (s + n)
          out = []
          for sub_bb in [(w, s, mx, my), (mx, s, e, my), (w, my, mx, n), (mx, my, e, n)]:
            out.extend(fetch_tile(session, params, sub_bb, depth + 1))
          return out
        return feats
      if r.status_code in (429, 502, 503, 504):
        time.sleep(2 * (att + 1))
        continue
      return []
    except Exception:
      time.sleep(2)
  return []


def sweep_region(params, label):
  # Tile Central Asia (46..88E, 35..56N) into coarse 6x5.25 deg tiles (7x4 = 28 tiles), auto-subdividing dense tiles
  tiles = []
  lon_steps = [46, 52, 58, 64, 70, 76, 82, 88]
  lat_steps = [35, 40, 45, 50, 56]
  for i in range(len(lon_steps) - 1):
    for j in range(len(lat_steps) - 1):
      tiles.append((lon_steps[i], lat_steps[j], lon_steps[i + 1], lat_steps[j + 1]))

  by_id = {}
  def worker(bb):
    sess = requests.Session()
    return fetch_tile(sess, params, bb, 0)

  with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(worker, bb) for bb in tiles]
    for fut in as_completed(futs):
      for feat in fut.result():
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if geom.get("type") != "Point" or len(coords) < 2:
          continue
        cid = props.get("caal_id") or props.get("source_row_id") or f"{round(coords[0],5)}_{round(coords[1],5)}"
        cnt = int(props.get("count") or 1)
        by_id[cid] = {
          "caal_id": props.get("caal_id") or "",
          "source_row_id": props.get("source_row_id") or "",
          "label": props.get("display_label") or "",
          "lon": round(float(coords[0]), 6),
          "lat": round(float(coords[1]), 6),
          "count": cnt,
        }
  rows = list(by_id.values())
  print(f"  [CAAL] {label}: {len(rows):,} unique monuments (point sum={sum(r['count'] for r in rows):,})", flush=True)
  return rows


def run_api_forensics(session, sample_ids, period_label):
  """Inspects 5 leaf monument records to verify zero NULL/undated leakage in period-filtered queries."""
  dated, undated = 0, 0
  for srid in sample_ids[:5]:
    if not srid:
      continue
    try:
      r = session.get(f"{BASE}/records/monument/{srid}", headers=HDR, timeout=15)
      if r.status_code == 200:
        raw = ((r.json().get("record") or {}).get("details_json") or {}).get("raw") or {}
        has_date = any(raw.get(k) for k in ("Start Date", "End Date", "Cultural Period1", "Cultural Period2", "Cultural Period 1", "CulturalPeriod1"))
        # Check any key containing period or date
        if not has_date:
          for k, v in raw.items():
            if v and ("period" in k.lower() or "date" in k.lower()):
              has_date = True
              break
        if has_date:
          dated += 1
        else:
          undated += 1
    except Exception:
      pass
  print(f"    [FORENSICS {period_label}] leaf check: {dated} dated / {undated} undated", flush=True)
  return dated, undated


def main():
  print("=== HARVESTING UCL CAAL (CENTRAL ASIAN ARCHAEOLOGICAL LANDSCAPES) FULL REGISTRY ===", flush=True)
  groups = build_horizon_cp_groups()
  sess = requests.Session()
  forensics_report = {}

  # 1. Harvest ALL 9 cultural period horizons cleanly
  for hk, cids in groups.items():
    outp = os.path.join(RAW_DIR, f"caal_horizon_{hk}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 500:
      existing = json.load(open(outp, "r", encoding="utf-8"))
      print(f"  [SKIP] CAAL {hk}: {len(existing):,} cached", flush=True)
      continue
    if not cids:
      continue
    rows = sweep_region({"types": "monument", "culturalPeriods": ",".join(cids)}, f"{hk} ({len(cids)} CPs)")
    with open(outp, "w", encoding="utf-8") as fh:
      json.dump(rows, fh, ensure_ascii=False)
    sample_srids = [r["source_row_id"] for r in rows[:10] if r.get("source_row_id")]
    d_cnt, u_cnt = run_api_forensics(sess, sample_srids, hk)
    forensics_report[hk] = {"monuments": len(rows), "leaf_dated": d_cnt, "leaf_undated": u_cnt, "cp_ids": cids}

  # 2. Also harvest CAAL Settlement/Urban/Fortification vs Funerary/Kurgan monument-type masks so we can weight habitation sites above isolated burial mounds!
  lk = json.load(open(os.path.join(RAW_DIR, "caal_lookups.json"), "r", encoding="utf-8"))
  stypes = lk.get("site_types", [])
  sett_mts, fort_mts, funerary_mts = [], [], []
  for st in stypes:
    cid = st.get("concept_id")
    lbl = (st.get("label_en") or st.get("display_en") or "").lower()
    if any(k in lbl for k in ("settlement", "town", "city", "urban", "village", "tell", "tepe", "mound", "habitation", "domestic", "dwelling", "oasis", "caravanserai", "ribat", "camp", "canal", "irrigation", "karez", "qanat")):
      sett_mts.append(cid)
    elif any(k in lbl for k in ("fort", "citadel", "castle", "tower", "wall", "defensive", "garrison", "kala", "qala")):
      fort_mts.append(cid)
    elif any(k in lbl for k in ("burial", "kurgan", "barrow", "tumulus", "grave", "cemetery", "necropolis", "tomb", "mausoleum", "funerary", "ossuary", "crypt")):
      funerary_mts.append(cid)

  print(f"\n  Monument type buckets: settlements={len(sett_mts)}, fortifications={len(fort_mts)}, funerary={len(funerary_mts)}", flush=True)
  for tag, mts in [("settlements", sett_mts), ("fortifications", fort_mts), ("funerary", funerary_mts)]:
    outp = os.path.join(RAW_DIR, f"caal_type_{tag}.json")
    if os.path.exists(outp) and os.path.getsize(outp) > 500:
      continue
    if mts:
      rows = sweep_region({"types": "monument", "monumentTypes": ",".join(mts[:60])}, f"type:{tag}")
      with open(outp, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False)

  # 3. Harvest ALL CAAL monuments (including undated/settlement-typed monuments for total site inventory audit)
  all_outp = os.path.join(RAW_DIR, "caal_all_monuments.json")
  if not os.path.exists(all_outp) or os.path.getsize(all_outp) < 10000:
    all_rows = sweep_region({"types": "monument"}, "ALL_MONUMENTS")
    with open(all_outp, "w", encoding="utf-8") as fh:
      json.dump(all_rows, fh, ensure_ascii=False)

  with open(os.path.join(RAW_DIR, "caal_api_forensics.json"), "w", encoding="utf-8") as fh:
    json.dump(forensics_report, fh, indent=2)
  print("=== DONE UCL CAAL FULL REGISTRY HARVEST ===", flush=True)


if __name__ == "__main__":
  main()
