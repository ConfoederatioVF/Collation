import json
import urllib.request

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get_json(u, timeout=15):
  req = urllib.request.Request(u, headers=H)
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return json.loads(r.read().decode("utf-8"))

# 1. Inspect FeatureServer roots & layers
svcs = [
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Lau_Localities_Final/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Bua_Final_Localities/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Cakaudrove_Localities/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Lomaiviti_Localities_Final/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Kadavu_Final_Localities1/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Taveuni_Final_Localities/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Ruwailevu_Localities_Final/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Navosa_Localities_Map_WFL1/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Rotuma_Localities_2017_MOH/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Yasawa_Group_Final_Localities_/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Cuvu_Localities_Final_070525/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Beqa_Final_Localities/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Malolo_Final_Localities/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Rabi_Localities_Final/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Vatulele_Final_Localities/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Cikobia_Localities_Final/FeatureServer",
  "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services/Tikina_Malomalo_WFL1/FeatureServer",
  "https://services6.arcgis.com/OO2s4OoyCZkYJ6oE/arcgis/rest/services/2017_Fiji_Enumerated_Areas/FeatureServer",
  "https://services.arcgis.com/XTtANUDT8Va4DLwI/arcgis/rest/services/Fiji_EnumerationZones/FeatureServer",
  "https://services6.arcgis.com/ZVM1rEuVZjtC1Wwk/arcgis/rest/services/Fiji_Villages/FeatureServer",
  "https://services6.arcgis.com/hhQx3hz8DjeO4X82/arcgis/rest/services/VillageinFiji/FeatureServer",
  "https://services.arcgis.com/0YblSxHvGTe2blEi/arcgis/rest/services/Census_Village/FeatureServer",
]

for s in svcs:
  name = s.split("/services/")[1].split("/")[0]
  try:
    d = get_json(s + "?f=json")
    if "error" in d:
      print(f"ERR {name}: {d['error']}")
      continue
    layers = [(ly["id"], ly["name"]) for ly in d.get("layers", [])]
    print(f"SVC {name}: layers={layers}")
    if layers:
      lid = layers[0][0]
      cnt = get_json(f"{s}/{lid}/query?where=1%3D1&returnCountOnly=true&f=json").get("count")
      smp = get_json(f"{s}/{lid}/query?where=1%3D1&outFields=*&resultRecordCount=2&outSR=4326&f=json")
      feats = smp.get("features", [])
      attrs = feats[0].get("attributes") if feats else None
      geom = feats[0].get("geometry") if feats else None
      print(f"   L{lid} count={cnt} | sample_attrs={attrs} | geom_keys={list(geom.keys()) if isinstance(geom, dict) else geom}")
  except Exception as e:
    print(f"EXC {name}: {e}")

# 2. Check SPC SDMX dataflows for Fiji/Vanuatu/Solomon/Samoa/Tonga/Kiribati/NC
try:
  sdmx = get_json("https://stats-nsi-stable.pacificdata.org/rest/dataflow/SPC?references=none")
  dfs = sdmx.get("data", {}).get("dataflows", [])
  print(f"\n=== SPC SDMX dataflows total={len(dfs)} ===")
  for df in dfs:
    did = df.get("id", "")
    nm = df.get("name", "")
    if any(w in (did + " " + nm).lower() for w in ("pop", "cens", "vill", "fji", "vut", "slb", "ncl", "wsm", "ton", "kir", "fsm")):
      print(f"  {did:35s} | {nm[:80]}")
except Exception as e:
  print("ERR SDMX:", e)

# 3. Check data.gouv.nc catalog (no bad where clause)
try:
  dnc = get_json("https://data.gouv.nc/api/explore/v2.1/catalog/datasets?limit=40&order_by=records_count+desc")
  print(f"\n=== data.gouv.nc top datasets (total={dnc.get('total_count')}) ===")
  for r in dnc.get("results", []):
    ds = r.get("dataset_id", "")
    meta = (r.get("metas") or {}).get("default") or {}
    t = meta.get("title", "")
    if any(w in (ds + " " + t).lower() for w in ("pop", "recens", "tribu", "commune", "quartier", "localit", "village")):
      print(f"  {ds:45s} | {t[:60]} | n={meta.get('records_count')}")
except Exception as e:
  print("ERR data.gouv.nc:", e)
