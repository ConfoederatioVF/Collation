"""Fixes the 2 priority-override regressions + 3 tail stragglers identified in Round-3 Hydrogen Audit:
  1. Guam: removes military bases/hospitals (Naval Hospital, Nimitz Hill Annex, Finegayan Station, etc.),
     removes CDP duplicates that share a name with Guam's 19 official Municipalities (so Dededo 44.908,
     Tamuning 18.489, Mangilao 13.476, Barrigada 7.956, Yona 6.298, Asan, Piti stay 100% intact!),
     and ensures is_capital=true belongs exclusively to Hagåtña (not Agana Heights).
  2. Samoa: tags Apia (35.974) as population_scope='metro' (Apia (Metro), is_capital=true) so individual
     SBS villages never swallow the national capital, and fixes Le'auva'a's 2021 split crash (999 vs 3.457).
  3. Stragglers: purges Kiribati 'Phoenix Islands (41)' aggregate (keeping Kanton Village), unifies Fiji
     Lomaloma & Nausori coords so tail duplicates merge cleanly, and renames 'Mu'a Nf' -> 'Mu'a (Niuafo'ou)'.
"""
import json
import os
import re
import unicodedata
from collections import Counter

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")


def norm_key(s):
  s = str(s or "").strip().lower()
  s = unicodedata.normalize("NFD", s)
  s = "".join(c for c in s if unicodedata.category(c) != "Mn")
  s = s.replace("'", "").replace("’", "").replace("`", "")
  s = re.sub(r"\([^)]*\)", "", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


GUAM_19_MUNIS = {
  "agana heights", "agat", "asan", "asan maina", "barrigada", "chalan pago ordot", "chalan pago",
  "dededo", "hagatna", "agana", "inarajan", "inalahan", "mangilao", "merizo", "malesso",
  "mongmong toto maite", "piti", "santa rita", "sumay", "sinajana", "talofofo", "talo fo fo",
  "tamuning", "umatac", "humatak", "yigo", "yona",
}
GUAM_MILITARY_RE = re.compile(
  r"\b(?:naval\s+hospital|nimitz\s+hill\s+annex|finegayan\s+station|andersen\s+afb|"
  r"apra\s+harbor|naval\s+base|naval\s+station|naval\s+computer|air\s+force\s+base|"
  r"ordnance|magazine|camp\s+blaz)\b",
  re.I,
)


def main():
  stats = Counter()

  for fn in sorted(os.listdir(SRC_DIR)):
    if not fn.endswith(".json"):
      continue
    fp = os.path.join(SRC_DIR, fn)
    d = json.load(open(fp, encoding="utf-8"))
    wrapped = isinstance(d, dict) and "settlements" in d and isinstance(d["settlements"], dict)
    so = d["settlements"] if wrapped else d
    if not isinstance(so, dict):
      continue

    changed = False
    new_so = {}
    for k, rec in so.items():
      if not isinstance(rec, dict):
        new_so[k] = rec
        continue
      ctry = str(rec.get("country") or "").strip()
      nm = str(rec.get("name") or "").strip()
      nk = norm_key(nm)
      pops = dict(rec.get("population") or {})

      # 1. Guam fixes
      if ctry == "Guam":
        # Remove military facilities/hospitals across ALL files
        if GUAM_MILITARY_RE.search(nm):
          stats["guam_military_purged"] += 1
          changed = True
          continue
        # Remove CDP overrides matching any of Guam's 19 Municipalities from enriched_mic_pol_official_nso.json
        if fn == "enriched_mic_pol_official_nso.json" and nk in GUAM_19_MUNIS:
          stats["guam_cdp_muni_dup_purged"] += 1
          changed = True
          continue
        # Ensure Agana Heights is NOT capital & does NOT carry Hagåtña's 1960/1970 capital series
        if nk == "agana heights" and rec.get("is_capital"):
          rec = dict(rec)
          rec["is_capital"] = False
          stats["guam_agana_heights_fixed"] += 1
          changed = True
        if nk == "hagatna" and not rec.get("is_capital"):
          rec = dict(rec)
          rec["is_capital"] = True
          changed = True
        # Ensure Dededo/Tamuning/Mangilao/Barrigada/Yona/Asan/Piti never carry small CDP numbers in enriched_mel_mic_pol_modern.json
        if fn != "micronesia_census_raw.json" and nk in GUAM_19_MUNIS and fn != "pacific_precolonial_colonial_evidence.json":
          if fn in ("enriched_mel_mic_pol_modern.json", "enriched_mic_pol_modern_gap.json"):
            stats["guam_enriched_muni_dup_purged"] += 1
            changed = True
            continue

      # 2. Samoa fixes: Apia (Metro) + Le'auva'a 2021 split crash
      if ctry == "Samoa":
        if nk == "apia" and any(float(v) >= 25000 for v in pops.values()):
          rec = dict(rec)
          rec["name"] = "Apia (Metro)"
          rec["population_scope"] = "metro"
          rec["is_capital"] = True
          stats["samoa_apia_metro_fixed"] += 1
          changed = True
        if nk in ("leauvaa", "le auva a", "leauva a", "le auvaa"):
          # Drop mismatched 2021 sub-village split (999 vs 2016: 3.457!)
          if "2021" in pops and float(pops["2021"]) < 1500:
            pops.pop("2021", None)
            rec = dict(rec)
            rec["population"] = pops
            stats["samoa_leauvaa_2021_fixed"] += 1
            changed = True
            if not pops:
              continue

      # 3a. Kiribati: purge 'Phoenix Islands' regional aggregate (keep Kanton Village)
      if ctry == "Kiribati" and nk == "phoenix islands":
        stats["kir_phoenix_purged"] += 1
        changed = True
        continue

      # 3b. Fiji: unify Lomaloma & Nausori distant coordinates so tail records merge cleanly
      if ctry == "Fiji":
        if nk == "lomaloma":
          rec = dict(rec)
          rec["coords"] = [-17.2950, -178.9830]
          stats["fiji_lomaloma_unified"] += 1
          changed = True
        elif nk == "nausori":
          rec = dict(rec)
          rec["coords"] = [-18.0244, 178.5508]
          stats["fiji_nausori_unified"] += 1
          changed = True

      # 3c. Tonga: rename 'Mu'a Nf' -> 'Mu'a (Niuafo'ou)'
      if ctry == "Tonga" and nm.lower() in ("mu'a nf", "mua nf"):
        rec = dict(rec)
        rec["name"] = "Mu'a (Niuafo'ou)"
        stats["tonga_mua_nf_renamed"] += 1
        changed = True

      new_so[k] = rec

    if changed:
      if wrapped:
        d["settlements"] = new_so
        if "metadata" in d and isinstance(d["metadata"], dict):
          d["metadata"]["total_settlements"] = len(new_so)
        out_obj = d
      else:
        out_obj = new_so
      with open(fp, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

  print("[Round-4 Regression Fixes COMPLETE]", dict(stats))


if __name__ == "__main__":
  main()
