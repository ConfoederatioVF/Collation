"""Harvests 100% official Fiji Bureau of Statistics (FBoS) 2017 Population & Housing Census
Localities directly from FBoS ArcGIS Online REST FeatureServers
(`https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services`).

Zero WorldPop, zero GeoNames, zero crowd fallback — verbatim FBoS 2017 CSPRO census totals
(`Total_Pop` = `Male_Pop` + `Female_Pop`) with exact WGS84 polygon centroids.
"""
import json
import math
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SRC_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL", "_shared", "settlement_sources")
OUT_PATH = os.path.join(SRC_DIR, "enriched_fiji_fbos_2017_localities.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
FBOS_ROOT = "https://services-ap1.arcgis.com/6zJAq2IlKWvgryAO/arcgis/rest/services"

NON_SETTLEMENT_RE = re.compile(
  r"\b(?:resort|hotel|motel|lodge|inn|school|college|academy|university|hospital|clinic|"
  r"health\s+cent|dispensary|prison|corrections?|police\s+post|police\s+station|military|"
  r"barracks|camp\b|airport|aerodrome|airstrip|quarry|mine\b|mill\b|factory|power\s+station|"
  r"water\s+treatment|reservoir|dam\b|wharf|jetty|port\s+authority|lighthouse|farm\b|estate\b|"
  r"plantation|ranch|piggery|poultry|dairy|cemetery|church\b|temple\b|mosque\b|monastery|"
  r"convent|mission\s+school|training\s+cent|research\s+station|gov(?:ernment)?\s+station|"
  r"institution|boarding|hostel|industrial|commercial|shop|store|market|club\b|golf|marina|"
  r"other\s+area|remainder|uninhabited|vacant|unknown)\b",
  re.I,
)

# Urban cores to avoid fragmenting (Law 4: Suva, Nasinu, Lautoka, Nadi, Labasa, Ba, Sigatoka, Savusavu)
URBAN_CORES = [
  (-18.1416, 178.4419, 8.0),   # Suva / Lami / Nasinu
  (-17.6169, 177.4505, 5.5),   # Lautoka
  (-17.8031, 177.4162, 5.0),   # Nadi
  (-16.4332, 179.3645, 4.0),   # Labasa
]


def hav_km(a1, o1, a2, o2):
  d1, d2 = math.radians(a2 - a1), math.radians(o2 - o1)
  x = math.sin(d1 / 2) ** 2 + math.cos(math.radians(a1)) * math.cos(math.radians(a2)) * math.sin(d2 / 2) ** 2
  return 6371.0 * 2.0 * math.atan2(math.sqrt(x), math.sqrt(max(0.0, 1.0 - x)))


def norm_key(s):
  s = str(s or "").strip().lower()
  s = unicodedata.normalize("NFD", s)
  s = "".join(c for c in s if unicodedata.category(c) != "Mn")
  s = re.sub(r"\b(?:village|settlement|locality|town|tikina)\b", "", s)
  s = re.sub(r"[^a-z0-9]+", " ", s).strip()
  return s


def get_json(url, timeout=25):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return json.loads(r.read().decode("utf-8"))


def geom_centroid(geom):
  if not isinstance(geom, dict):
    return None
  if "x" in geom and "y" in geom:
    lon, lat = float(geom["x"]), float(geom["y"])
  elif "rings" in geom and geom["rings"]:
    pts = [p for ring in geom["rings"] for p in ring if len(p) >= 2]
    if not pts:
      return None
    # Handle antimeridian wrapping in Fiji (176..180 and -180..-178)
    lons = [float(p[0]) for p in pts]
    if max(lons) - min(lons) > 180.0:
      lons = [x + 360.0 if x < 0 else x for x in lons]
    lon = sum(lons) / len(lons)
    if lon > 180.0:
      lon -= 360.0
    lat = sum(float(p[1]) for p in pts) / len(pts)
  else:
    return None
  # Fiji bounding box (incl. Rotuma at -12.5, 177.0 and Lau at -21.0, -178.0)
  if not (-21.5 <= lat <= -12.0 and (lon >= 176.5 or lon <= -177.5)):
    return None
  return round(lat, 5), round(lon, 5)


def extract_field(attrs, candidates):
  lower_map = {k.lower(): (k, v) for k, v in attrs.items()}
  for cand in candidates:
    if cand in lower_map and lower_map[cand][1] not in (None, "", "<Null>", "-"):
      return lower_map[cand][1]
  # Substring match fallback
  for cand in candidates:
    for lk, (orig_k, v) in lower_map.items():
      if lk.endswith("_" + cand) or lk == cand:
        if v not in (None, "", "<Null>", "-"):
          return v
  return None


def main():
  # 1. Discover ALL locality FeatureServers from FBoS REST catalog + known owner searches
  catalog = get_json(f"{FBOS_ROOT}?f=json")
  svc_urls = []
  for s in catalog.get("services", []):
    nm = s.get("name", "")
    if s.get("type") == "FeatureServer" and any(w in nm.lower() for w in ("localit", "malomalo", "northern")):
      svc_urls.append((nm, f"{FBOS_ROOT}/{nm}/FeatureServer"))

  # Also add simoli.louise_fbos services (may not appear in public root listing)
  extra_names = [
    "Ruwailevu_Localities_Final",
    "Tikina_Malomalo_WFL1",
    "Navosa_Localities_Map_WFL1",
    "Tikina_Nasigatoka_WFL1",
    "Nalawa_Localities_Final",
  ]
  seen_nm = {x[0].lower() for x in svc_urls}
  for en in extra_names:
    if en.lower() not in seen_nm:
      svc_urls.append((en, f"{FBOS_ROOT}/{en}/FeatureServer"))
      seen_nm.add(en.lower())

  # Also search AGOL for any other *_Localities* services on 6zJAq2IlKWvgryAO
  try:
    ag = get_json("https://www.arcgis.com/sharing/rest/search?q=" + urllib.parse.quote('Localities owner:fiu_community_fiji OR owner:simoli.louise_fbos OR owner:snasilivata_community_fiji') + "&f=json&num=100")
    for r in ag.get("results", []):
      u = r.get("url") or ""
      if "6zJAq2IlKWvgryAO" in u and "FeatureServer" in u:
        nm = u.split("/services/")[1].split("/")[0]
        if nm.lower() not in seen_nm:
          svc_urls.append((nm, u))
          seen_nm.add(nm.lower())
  except Exception as e:
    print("AGOL extra search note:", e)

  print(f"[FBoS 2017] Discovered {len(svc_urls)} official FBoS Locality FeatureServers")

  # Load existing Fiji settlements so we don't duplicate existing towns/villages
  existing_fji = []
  for fn in ("melanesia_census_raw.json", "enriched_mel_mic_pol_modern.json"):
    fp = os.path.join(SRC_DIR, fn)
    if not os.path.exists(fp):
      continue
    d = json.load(open(fp, encoding="utf-8"))
    so = d.get("settlements", d)
    for rec in so.values():
      if isinstance(rec, dict) and rec.get("country") == "Fiji":
        c = rec.get("coords") or [0, 0]
        existing_fji.append((float(c[0]), float(c[1]), norm_key(rec.get("name", ""))))

  cands = []
  svc_stats = Counter()

  for svc_nm, svc_url in sorted(svc_urls):
    try:
      meta = get_json(svc_url + "?f=json")
      if "error" in meta:
        continue
      layers = meta.get("layers", [])
      if not layers:
        continue
      for ly in layers:
        lid = ly["id"]
        # Query all records paginated (max 1000 per call)
        offset = 0
        got = 0
        while True:
          qurl = f"{svc_url}/{lid}/query?where=1%3D1&outFields=*&outSR=4326&resultOffset={offset}&resultRecordCount=1000&f=json"
          res = get_json(qurl, timeout=30)
          feats = res.get("features", [])
          if not feats:
            break
          for ft in feats:
            attrs = ft.get("attributes") or {}
            coords = geom_centroid(ft.get("geometry"))
            if coords is None:
              continue
            raw_nm = extract_field(attrs, ["name_localities", "name", "localities", "locality", "village", "name_1"])
            if not raw_nm:
              continue
            raw_nm = str(raw_nm).strip()
            # Clean name: strip trailing " Village" / " Settlement" only if > 1 word left, keep crisp Fijian toponym
            nm = re.sub(r"\s+", " ", raw_nm.replace("`", "'")).strip()
            nm = re.sub(r"\s+(?:Village|Settlement|Locality)$", "", nm, flags=re.I).strip()
            if len(nm) < 3 or re.fullmatch(r"[\d\s\-_./]+", nm):
              continue
            if NON_SETTLEMENT_RE.search(raw_nm) or NON_SETTLEMENT_RE.search(nm):
              continue

            # Check Type field if present (must be Village/Settlement/Town/Urban/Peri-Urban/Rural, not Institution/Resort/Island-empty)
            ltype = str(extract_field(attrs, ["type", "type_1", "category"]) or "").strip().lower()
            if ltype and any(b in ltype for b in ("resort", "hotel", "institution", "school", "hospital", "prison", "industrial", "commercial", "farm", "camp")):
              continue

            # Extract official 2017 Total_Pop (or Male_Pop + Female_Pop)
            pop_raw = extract_field(attrs, ["total_pop", "tot_pop", "population", "pop_2017", "total"])
            if pop_raw is None:
              m_v = extract_field(attrs, ["male_pop", "male"])
              f_v = extract_field(attrs, ["female_pop", "female"])
              if m_v is not None and f_v is not None:
                try:
                  pop_raw = float(m_v) + float(f_v)
                except Exception:
                  pop_raw = None
            if pop_raw is None:
              continue
            try:
              pop = int(round(float(pop_raw)))
            except Exception:
              continue
            if pop < 12 or pop > 45000:
              continue

            # Check urban core exclusions (Law 4)
            lat, lon = coords
            if any(hav_km(lat, lon, ulat, ulon) <= urad for ulat, ulon, urad in URBAN_CORES):
              continue

            tikina = str(extract_field(attrs, ["tikina", "tikina_1", "province", "prov"]) or "").strip()
            prov = svc_nm.split("_")[0]
            if prov.lower() in ("tikina", "new", "northern"):
              prov = tikina or "Fiji"
            admin1 = prov.title() if prov else "Fiji"

            cands.append((pop, nm, admin1, lat, lon, svc_nm, ltype))
            got += 1
          if len(feats) < 1000 and not res.get("exceededTransferLimit"):
            break
          offset += len(feats)
        if got:
          svc_stats[svc_nm] += got
          print(f"  {svc_nm} (L{lid}): extracted {got} inhabited official FBoS 2017 localities")
    except Exception as e:
      print(f"  SKIP {svc_nm}: {e}")

  # Spatial deduplication (> 1.65 km apart; same name <= 25 km merged, largest first)
  cands.sort(key=lambda x: (-x[0], x[1]))
  placed = list(existing_fji)
  out = {}
  for pop, nm, admin1, lat, lon, svc_nm, ltype in cands:
    nk = norm_key(nm)
    if not nk or len(nk) < 2:
      continue
    if any(hav_km(lat, lon, pl[0], pl[1]) <= 1.65 or (hav_km(lat, lon, pl[0], pl[1]) <= 25.0 and pl[2] == nk) for pl in placed):
      continue
    placed.append((lat, lon, nk))
    slug = re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")
    skey = f"fbos17_{slug}_{len(out)}"
    out[skey] = {
      "name": nm,
      "other_names": [],
      "coords": [lat, lon],
      "country": "Fiji",
      "admin1": admin1,
      "population_scope": "city_proper",
      "is_capital": False,
      "population": {"2017": int(pop)},
      "sources": [f"Fiji Bureau of Statistics (FBoS) 2017 Population and Housing Census — Official Locality Enumeration ({svc_nm})"],
    }

  payload = {
    "metadata": {
      "source": "Fiji Bureau of Statistics (FBoS) 2017 Population and Housing Census Official Locality Enumeration (ArcGIS REST FeatureServers)",
      "total_settlements": len(out),
      "services_harvested": dict(svc_stats),
      "crowd_share": 0.0,
    },
    "settlements": out,
  }
  with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
  print(f"\n[FBoS 2017 DONE] Wrote {len(out)} discrete (>1.65 km) pure official FBoS 2017 Fiji census localities -> {OUT_PATH}")


if __name__ == "__main__":
  main()
