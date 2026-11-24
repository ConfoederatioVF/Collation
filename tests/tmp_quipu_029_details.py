import glob
import json
import time
import urllib.parse
import urllib.request

from tmp_quipu_029_lookup import ITEMS, HEADERS, fetch_json

with open("tests/tmp_quipu_029_wiki.json", "r", encoding="utf-8") as f:
  wiki = json.load(f)

# Retry the few remaining 429s gently
for idx, it in enumerate(ITEMS):
  w = wiki[idx]
  if "geo_err" in w or "search_err" in w:
    lat, lng = it["ll"]
    if "geo_err" in w:
      w.pop("geo_err", None)
      try:
        gd = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}%7C{lng}&gsradius=10000&gslimit=5&format=json")
        w["geo"] = [{"title": g["title"], "dist": g["dist"]} for g in gd.get("query", {}).get("geosearch", [])]
      except Exception as e:
        w["geo_err"] = str(e)
      time.sleep(0.5)
    if "search_err" in w:
      w.pop("search_err", None)
      try:
        q = urllib.parse.quote(f"{it['n']} {it['c']}")
        sd = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json")
        w["search"] = [{"title": s["title"], "snippet": s["snippet"]} for s in sd.get("query", {}).get("search", [])]
      except Exception as e:
        w["search_err"] = str(e)
      time.sleep(0.5)

with open("tests/tmp_quipu_029_wiki.json", "w", encoding="utf-8") as f:
  json.dump(wiki, f, ensure_ascii=False, indent=2)

# Collect unique candidate titles to fetch extracts for
titles = set()
extra_titles = [
  "Las Cruces (Chile)", "Obando (Valle del Cauca)", "El Espinal (Tolima)",
  "Santa Rosa (Barquisimeto)", "Santa Rosa (Lara)", "Distrito de Choros",
  "Chacas", "Yacimientos arqueológicos del valle de Upano", "Huapula",
  "Guatraché", "Distrito de Santo Domingo de la Capilla", "Pinto (Santiago del Estero)",
  "Vallenar", "San Sebastián (Manabí)", "Pichincha (Manabí)", "Cantón Pichincha",
  "La Palma (Cundinamarca)", "El Peñón (Cundinamarca)", "Tarqui (Huila)", "Suaza",
  "Wilfrido Loor Moreira", "Cantón El Carmen", "Distrito de Huasahuasi",
  "Distrito de Llapa", "Ingeniero Forres", "Distrito de Tirapata", "Pucará (Lampa)",
  "Curarigua", "Distrito de Yacus", "Valle de Huentata", "Mendoza (Argentina)",
  "Castro (Chile)", "Los Choros", "Santa Ana del Táchira", "Municipio Torbes",
  "Badillo", "Cantón Sozoranga", "Distrito de Huaros", "Distrito de Pítipo",
  "Los Paredones (sitio arqueológico)", "Nazca", "Distrito de Mañazo", "Panao",
  "Calabozo (Venezuela)", "San Luis Robles", "Distrito de Huayllay Grande",
  "Distrito de Copani", "Chañar Ladeado", "Pampán", "Distrito de Santa Ana de Tusi",
  "Longaví", "Santa Victoria Oeste", "Acoyte", "Cantón Colimes", "Colimes",
  "Montebello (Antioquia)", "Santa Bárbara (Antioquia)", "Concepción (Zulia)",
  "Sastre y Ortiz", "Las Toscas (Canelones)", "Gultro", "Maullín",
  "Chaclacayo", "El Tambo (Cauca)", "Suárez (Tolima)", "Distrito de Acas",
  "Distrito de Chilcayoc", "Cruz del Eje", "Cantón Saquisilí", "Canchagua",
  "Los Juríes", "San Faustino (Colombia)", "Distrito de Lucanas",
  "San Gregorio (Santa Fe)", "Pilar (Santa Fe)", "Matará (Santiago del Estero)",
  "Humboldt (Argentina)", "Quípama", "Itoco", "Villa Caro", "San Carlos (Corrientes)",
  "Misiones jesuíticas guaraníes", "Distrito de Ascope", "Casa Grande (Ascope)",
  "Itá Ibaté", "Distrito de Alto Saposoa", "Distrito de Huancarani",
  "Gobernador Gregores", "Tumusla", "Batalla de Tumusla", "Payogasta",
  "Incas en Argentina", "Quindén Bajo", "San Juan de Pózul", "Las Perdices",
  "Catentoa", "Linares (Chile)", "San Ambrosio de Ballenary"
]
titles.update(extra_titles)
for w in wiki:
  for g in w.get("geo", []):
    if g["dist"] < 5000:
      titles.add(g["title"])

title_list = sorted(titles)
extracts = {}
for i in range(0, len(title_list), 20):
  batch = title_list[i:i+20]
  tparam = urllib.parse.quote("|".join(batch))
  url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exchars=3500&exlimit=20&redirects=1&titles={tparam}&format=json"
  try:
    d = fetch_json(url)
    for pid, pinfo in d.get("query", {}).get("pages", {}).items():
      if "title" in pinfo and "extract" in pinfo:
        extracts[pinfo["title"]] = pinfo["extract"]
  except Exception as e:
    print("Extract error:", e)
  time.sleep(0.5)

with open("tests/tmp_quipu_029_extracts.json", "w", encoding="utf-8") as f:
  json.dump(extracts, f, ensure_ascii=False, indent=2)

# Check local settlement_sources + c14 + sites_quipu_andes_cone + batch_029
local_hits = {it["key"]: [] for it in ITEMS}
def check_obj(bn, obj):
  if not isinstance(obj, dict):
    return
  rlat = obj.get("lat") if obj.get("lat") is not None else obj.get("latitude")
  rlng = obj.get("lng") if obj.get("lng") is not None else (obj.get("lon") if obj.get("lon") is not None else obj.get("longitude"))
  if rlat is None and isinstance(obj.get("coords"), list) and len(obj["coords"]) == 2:
    rlng, rlat = obj["coords"][0], obj["coords"][1]
  if rlat is None and isinstance(obj.get("ll"), list) and len(obj["ll"]) == 2:
    rlat, rlng = obj["ll"][0], obj["ll"][1]
  if rlat is None or rlng is None:
    return
  try:
    rlat, rlng = float(rlat), float(rlng)
  except Exception:
    return
  for it in ITEMS:
    if abs(rlat - it["ll"][0]) < 0.005 and abs(rlng - it["ll"][1]) < 0.005:
      clean = {k: v for k, v in obj.items() if k not in ("geometry", "populations", "pop_by_year")}
      local_hits[it["key"]].append({"file": bn, "rec": clean})

for pat in [
  "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json",
  "histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/*.json",
  "histmap/1.data_raw/population_regional/QUIPU/*/*.json",
]:
  for fp in sorted(glob.glob(pat)):
    try:
      data = json.load(open(fp, encoding="utf-8"))
    except Exception:
      continue
    bn = fp.replace("\\", "/").split("QUIPU/")[-1]
    if isinstance(data, dict):
      if isinstance(data.get("settlements"), dict):
        for k, v in data["settlements"].items():
          if isinstance(v, dict):
            v2 = dict(v); v2["_dict_key"] = k
            check_obj(bn, v2)
      elif isinstance(data.get("settlements"), list):
        for v in data["settlements"]:
          check_obj(bn, v)
      elif isinstance(data.get("features"), list):
        for feat in data["features"]:
          if isinstance(feat, dict):
            props = dict(feat.get("properties") or {})
            geom = feat.get("geometry") or {}
            if geom.get("type") == "Point" and isinstance(geom.get("coordinates"), list):
              props["coords"] = geom["coordinates"]
            check_obj(bn, props)
    elif isinstance(data, list):
      for v in data:
        check_obj(bn, v)

with open("tests/tmp_quipu_029_local.json", "w", encoding="utf-8") as f:
  json.dump(local_hits, f, ensure_ascii=False, indent=2)

print("Extracts:", len(extracts), "Local hits items:", sum(1 for v in local_hits.values() if v))
