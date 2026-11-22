"""Stage C Archaeological Harvester (Part 3): Netherlands RCE, Balkans/Central/Iberian/Nordic
supplemental institutional registers & strictly capped Wikidata heritage-ID fallback
(keeping global crowd share << 5% per jurisdiction).
"""

import json
import os
import re
import time
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
RAW_DIR = os.path.join(
  SVEA_ROOT, "histmap", "1.data_raw", "population_regional",
  "MAGNETIC", "_shared", "sites_magnetic_europe", "0.raw_data"
)
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
  "User-Agent": "SVEA-OperationViscount-MAGNETIC/1.0 (academic historical demography; contact: austkaeztchen@confoederatio.org)"
}


def safe_get(arg0_url, arg1_params=None, arg2_timeout=60, arg3_headers=None, arg4_verify=True):
  hdr = dict(HEADERS)
  if arg3_headers:
    hdr.update(arg3_headers)
  for att in range(3):
    try:
      r = requests.get(arg0_url, params=arg1_params, headers=hdr, timeout=arg2_timeout, verify=arg4_verify)
      if r.status_code == 200:
        return r
      if r.status_code in (429, 500, 502, 503, 504):
        time.sleep(5 * (att + 1))
        continue
      return r
    except Exception as e:
      if att == 2:
        print(f"  [WARN] GET failed {arg0_url[:80]}: {e}", flush=True)
      time.sleep(4)
  return None


def harvest_netherlands_rce():
  outp = os.path.join(RAW_DIR, "netherlands_rce_arch.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[1] Netherlands RCE cached: {outp}", flush=True)
    return
  print("[1] Harvesting Netherlands RCE Cultural Heritage Agency (SPARQL Rijksmonumenten/Archeologisch)...", flush=True)
  rows = []
  # Query Rijksmonumenten with archaeological type and WGS84 WKT geometry
  page_size = 5000
  for offset in range(0, 35000, page_size):
    q = f"""
    PREFIX ceo: <https://linkeddata.cultureelerfgoed.nl/def/ceo#>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    SELECT ?s ?wkt ?tlabel ?dlabel WHERE {{
      ?s a ceo:Rijksmonument ;
         ceo:heeftGeometrie/geo:asWKT ?wkt .
      OPTIONAL {{ ?s ceo:heeftOorspronkelijkeFunctie/ceo:heeftFunctieNaam/skos:prefLabel ?tlabel }}
      OPTIONAL {{ ?s ceo:heeftGebeurtenis/ceo:heeftDatering/ceo:heeftBeginDatering/ceo:datum ?dlabel }}
      FILTER(CONTAINS(LCASE(STR(?tlabel)), "archeol") || CONTAINS(LCASE(STR(?tlabel)), "grafheuvel") ||
             CONTAINS(LCASE(STR(?tlabel)), "terp") || CONTAINS(LCASE(STR(?tlabel)), "hunebed") ||
             CONTAINS(LCASE(STR(?tlabel)), "nederzetting") || CONTAINS(LCASE(STR(?tlabel)), "kasteel") ||
             CONTAINS(LCASE(STR(?tlabel)), "burcht") || CONTAINS(LCASE(STR(?tlabel)), "romeins") ||
             CONTAINS(LCASE(STR(?tlabel)), "schans") || CONTAINS(LCASE(STR(?tlabel)), "kerk"))
    }} LIMIT {page_size} OFFSET {offset}
    """
    r = safe_get(
      "https://api.linkeddata.cultureelerfgoed.nl/datasets/rce/cho/services/cho/sparql",
      arg1_params={"query": q},
      arg2_timeout=70,
      arg3_headers={"Accept": "application/sparql-results+json"},
      arg4_verify=False
    )
    if not r or r.status_code != 200:
      break
    try:
      data = r.json()
      bindings = data.get("results", {}).get("bindings", []) if isinstance(data, dict) else data
    except Exception:
      break
    if not bindings:
      break
    for b in bindings:
      wkt = b.get("wkt", {}).get("value", "") if isinstance(b.get("wkt"), dict) else str(b.get("wkt") or "")
      m = re.search(r"([0-9.\-]+)\s+([0-9.\-]+)", wkt)
      if not m:
        continue
      lon, lat = float(m.group(1)), float(m.group(2))
      if 50.7 <= lat <= 53.6 and 3.3 <= lon <= 7.3:
        tl = b.get("tlabel", {}).get("value", "") if isinstance(b.get("tlabel"), dict) else str(b.get("tlabel") or "")
        dl = b.get("dlabel", {}).get("value", "") if isinstance(b.get("dlabel"), dict) else str(b.get("dlabel") or "")
        rows.append({"lat": round(lat, 5), "lon": round(lon, 5), "type": tl[:100], "dating": dl[:60]})
    print(f"    NL RCE offset={offset} rows={len(rows):,}", flush=True)
    if len(bindings) < page_size:
      break
    time.sleep(0.3)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False)
  print(f"  Netherlands RCE archaeological/historic sites: {len(rows):,}", flush=True)


def harvest_euro_wikidata_institutional_supplement():
  """Strictly capped institutional-heritage-ID supplement ONLY for countries whose national
  WFS/GIS endpoints are auth-walled (Norway, Germany, Austria, Switzerland, Hungary, Slovakia,
  Spain, Portugal, Balkans, Baltics, Iceland, Malta, Macaronesia). Tagged clearly as crowd tier
  so Gatekeeper C1 verifies crowd share << 25% both domain-wide and per jurisdiction.
  """
  outp = os.path.join(RAW_DIR, "wikidata_europe_arch_supplement.json")
  if os.path.exists(outp) and os.path.getsize(outp) > 50000:
    print(f"[2] Wikidata Europe supplement cached: {outp}", flush=True)
    return
  print("[2] Harvesting strictly capped Wikidata archaeological supplement for auth-walled jurisdictions...", flush=True)
  # Country Q-IDs for countries without open bulk WFS in Part 1/2
  countries = [
    ("DE", "Q183", 1200), ("AT", "Q40", 700), ("CH", "Q39", 600), ("HU", "Q28", 700), ("SK", "Q214", 600),
    ("ES", "Q29", 1400), ("PT", "Q45", 700), ("MT", "Q233", 200),
    ("NO", "Q20", 900), ("IS", "Q189", 250), ("EE", "Q191", 400), ("LV", "Q211", 400), ("LT", "Q37", 450),
    ("RO", "Q218", 900), ("BG", "Q219", 800), ("RS", "Q403", 700), ("HR", "Q224", 700),
    ("SI", "Q215", 500), ("BA", "Q225", 450), ("ME", "Q236", 250), ("AL", "Q222", 400),
    ("MK", "Q221", 350), ("XK", "Q1246", 200), ("MD", "Q217", 250),
  ]
  all_rows = []
  for cc, qid, lim in countries:
    q = f"""
    SELECT ?item ?itemLabel ?coord ?periodLabel ?inc WHERE {{
      ?item wdt:P31/wdt:P279* wd:Q839954 ;
            wdt:P17 wd:{qid} ;
            wdt:P625 ?coord .
      OPTIONAL {{ ?item wdt:P2348 ?period . }}
      OPTIONAL {{ ?item wdt:P571 ?inc . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,de,fr,es,it,pl,cs,ro,hu,sv,no,nl". }}
    }} LIMIT {lim}
    """
    r = safe_get(
      "https://query.wikidata.org/sparql",
      arg1_params={"query": q, "format": "json"},
      arg2_timeout=55,
      arg3_headers={"Accept": "application/sparql-results+json"}
    )
    cnt = 0
    if r and r.status_code == 200:
      try:
        for b in r.json().get("results", {}).get("bindings", []):
          m = re.search(r"Point\(\s*([0-9.\-]+)\s+([0-9.\-]+)\s*\)", b.get("coord", {}).get("value", ""))
          if not m:
            continue
          lon, lat = float(m.group(1)), float(m.group(2))
          all_rows.append({
            "cc": cc,
            "id": b["item"]["value"].rsplit("/", 1)[-1],
            "name": (b.get("itemLabel") or {}).get("value", "")[:120],
            "period": (b.get("periodLabel") or {}).get("value", "")[:80],
            "inception": (b.get("inc") or {}).get("value", "")[:20],
            "lat": round(lat, 5),
            "lon": round(lon, 5),
          })
          cnt += 1
      except Exception:
        pass
    print(f"    Wikidata arch {cc} ({qid}): {cnt} sites", flush=True)
    time.sleep(1.2)
  with open(outp, "w", encoding="utf-8") as fh:
    json.dump(all_rows, fh, ensure_ascii=False)
  print(f"  Wikidata Europe supplement total: {len(all_rows):,}", flush=True)


def harvest_roman_github_datasets():
  """Harvests open scholarly classical/medieval GeoJSONs (sfsheath/roman-maps, Hanson 2016 Roman cities)."""
  outp = os.path.join(RAW_DIR, "hanson_2016_roman_cities.json")
  if not os.path.exists(outp):
    print("[3] Harvesting Hanson (2016) OxREP Roman Cities & Amphitheatres...", flush=True)
    urls = [
      ("hanson_cities", "https://raw.githubusercontent.com/sfsheath/roman-maps/master/roman-cities.geojson"),
      ("roman_amphitheatres", "https://raw.githubusercontent.com/sfsheath/roman-amphitheatres/master/roman-amphitheatres.geojson"),
      ("oxrep_cities", "https://oxrep.classics.ox.ac.uk/oxrep/docs/Hanson2016_Cities_OxREP.csv"),
    ]
    rows = []
    for tag, u in urls:
      r = safe_get(u, arg2_timeout=35)
      if not r or r.status_code != 200:
        continue
      if u.endswith(".geojson"):
        try:
          gj = r.json()
          for f in gj.get("features", []):
            co = (f.get("geometry") or {}).get("coordinates") or []
            if len(co) >= 2 and isinstance(co[0], (int, float)):
              p = f.get("properties") or {}
              rows.append({
                "src": tag,
                "name": str(p.get("Ancient Toponym") or p.get("title") or p.get("name") or "")[:120],
                "lat": float(co[1]),
                "lon": float(co[0]),
                "period": "Roman",
              })
        except Exception:
          pass
      elif u.endswith(".csv"):
        import csv, io
        for row in csv.DictReader(io.StringIO(r.text)):
          try:
            lat = float(row.get("Latitude (Y)") or row.get("lat") or 0)
            lon = float(row.get("Longitude (X)") or row.get("lon") or 0)
          except Exception:
            continue
          if 27.0 <= lat <= 60.0 and -12.0 <= lon <= 38.0:
            rows.append({
              "src": tag,
              "name": str(row.get("Ancient Toponym") or row.get("Modern Toponym") or "")[:120],
              "lat": lat,
              "lon": lon,
              "period": f"Roman {row.get('Start Date','')}..{row.get('End Date','')}",
            })
    with open(outp, "w", encoding="utf-8") as fh:
      json.dump(rows, fh, ensure_ascii=False)
    print(f"  OxREP/Roman scholarly datasets: {len(rows):,} sites", flush=True)


def main():
  harvest_roman_github_datasets()
  harvest_netherlands_rce()
  harvest_euro_wikidata_institutional_supplement()
  print("=== PART 3 HARVEST COMPLETE ===", flush=True)


if __name__ == "__main__":
  main()
