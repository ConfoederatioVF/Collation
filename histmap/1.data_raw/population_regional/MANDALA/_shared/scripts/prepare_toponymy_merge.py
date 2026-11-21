"""Enriches verified Gemini 3.8 Flash resolved_batch_01..20.json with coords_lat_lng, country, and latest_year
from batch_01..20.json (and filters out any scrubbed non-settlement entities) so merge_city_metadata.js accepts 100% cleanly."""

import glob
import json
import os
import re

MANDALA = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MANDALA"
IN_DIR = os.path.join(MANDALA, "_shared", "toponymy_batches")
OUT_DIR = os.path.join(MANDALA, "_shared", "toponymy_merge_ready")
os.makedirs(OUT_DIR, exist_ok=True)

NON_SETT_RE = re.compile(
  r"\b(diocese|archdiocese|vicariate|prelature|eparchy|metropolis|apostolic|"
  r"dynasty|kingdom|empire|sultanate|republic|federation|colony|protectorate|"
  r"province|region|regency|kabupaten|changwat|island|islands|archipelago|"
  r"greater|portuguese timor|east timor|timor-leste)\b",
  flags=re.I
)
BLOCKED_EXACT = {"laos", "thailand", "vietnam", "cambodia", "myanmar", "burma", "malaysia", "indonesia", "philippines", "brunei", "sabah", "sarawak", "bali", "timor", "java", "sumatra", "borneo", "sulawesi"}

# Load active valid settlement keys from all 22 cleaned chapter gazetteers
valid_keys = {}
for sf in glob.glob(os.path.join(MANDALA, "*", "*", "*_settlements.json")):
  d = json.load(open(sf, encoding="utf-8"))
  for k, s in d.items():
    pops = s.get("population") or {}
    ly = max((int(y) for y in pops.keys()), default=2020)
    if k not in valid_keys or ly > valid_keys[k]["latest_year"]:
      valid_keys[k] = {"coords": s["coords"], "country": s["country"], "latest_year": ly, "name": s["name"]}

total_in = 0
total_out = 0
total_skipped = 0

for idx in range(1, 21):
  bf = os.path.join(IN_DIR, f"batch_{idx:02d}.json")
  rf = os.path.join(IN_DIR, f"resolved_batch_{idx:02d}.json")
  bdata = json.load(open(bf, encoding="utf-8"))
  rdata = json.load(open(rf, encoding="utf-8"))
  b_map = {s["key"]: s for s in (bdata.get("settlements") if isinstance(bdata, dict) else bdata)}
  out_list = []
  for rec in rdata.get("settlements", []):
    total_in += 1
    k = rec["key"]
    canon = str(rec.get("canonical_name") or "").strip()
    if NON_SETT_RE.search(canon) or canon.lower() in BLOCKED_EXACT:
      total_skipped += 1
      continue
    b = b_map.get(k) or {}
    vk = valid_keys.get(k)
    coords = (vk["coords"] if vk else b.get("coords"))
    country = (vk["country"] if vk else b.get("country") or (k.rsplit("-", 1)[-1] if "-" in k else ""))
    latest_yr = (vk["latest_year"] if vk else b.get("latest_year") or 2025)
    if not coords or len(coords) < 2:
      total_skipped += 1
      continue
    merged = dict(rec)
    merged["coords_lat_lng"] = [float(coords[0]), float(coords[1])]
    merged["country"] = country
    merged["latest_year"] = int(latest_yr)
    out_list.append(merged)
    total_out += 1
  out_p = os.path.join(OUT_DIR, f"resolved_batch_{idx:02d}.json")
  with open(out_p, "w", encoding="utf-8") as fh:
    json.dump({"batch_index": idx, "settlements": out_list}, fh, indent=2, ensure_ascii=False)

print(f"Prepared {total_out}/{total_in} verified Flash toponymy records in {OUT_DIR} (skipped {total_skipped} scrubbed non-settlements).")
