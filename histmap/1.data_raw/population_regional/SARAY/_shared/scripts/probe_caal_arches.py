"""Dumps UCL CAAL full controls, cultural periods, and tests period-filtered /map forensics."""
import json, os, re, requests
HDR = {"User-Agent": "SVEA-OperationViscount-SARAY/1.0 (academic research; contact: austkaeztchen@confoederatio.org)"}
BASE = "https://data.uclcaal.org/api/public-viewer"
RAW_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\SARAY\_shared\sites_saray_central_asia\0.raw_data"

rf = requests.get("https://data.uclcaal.org/js/publicViewerFiltersUI.js?v=filters-2", headers=HDR, timeout=20).text
idx = rf.find("const controls=")
print("CONTROLS FULL:", rf[idx:idx + 550])

cp = requests.get(BASE + "/cultural-periods", headers=HDR, timeout=25).json()
with open(os.path.join(RAW_DIR, "caal_cultural_periods.json"), "w", encoding="utf-8") as fh:
  json.dump(cp, fh, ensure_ascii=False, indent=2)
opts = cp.get("options", [])
print(f"\nTotal cultural periods: {len(opts)}")
for o in opts[:60]:
  print(f"  {o.get('concept_id')}: {o.get('label')} ({o.get('date_range')}) [parent={o.get('parent_id')}]")
if len(opts) > 60:
  print(f"  ... ({len(opts) - 60} more)")
  for o in opts[60:]:
    print(f"  {o.get('concept_id')}: {o.get('label')} ({o.get('date_range')}) [parent={o.get('parent_id')}]")

lk = requests.get(BASE + "/lookups", headers=HDR, timeout=25).json()
with open(os.path.join(RAW_DIR, "caal_lookups.json"), "w", encoding="utf-8") as fh:
  json.dump(lk, fh, ensure_ascii=False, indent=2)

# Check ussr-historic-partial links
uh_p = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\SARAY\_shared\_census_cache\popstat_ussr-historic-partial_index.htm"
if os.path.exists(uh_p):
  ut = open(uh_p, encoding="utf-8", errors="replace").read()
  print("\nUSSR HISTORIC PARTIAL LINKS:", sorted(set(re.findall(r'href=["\']([^"\']+\.htm)["\']', ut, re.I)))[:40])
