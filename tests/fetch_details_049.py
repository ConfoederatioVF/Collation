import json
import time
import urllib.request
import urllib.parse

HEADERS = {"User-Agent": "SVEA-QUIPU-Research/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def fetch_json(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=20) as resp:
    return json.loads(resp.read().decode("utf-8"))

with open("tests/lookup_chunk049.py", "r", encoding="utf-8") as f:
  src = f.read()

# Extract SETTLEMENTS
ns = {}
exec(src.split("HEADERS =")[0], ns)
SETTLEMENTS = ns["SETTLEMENTS"]

with open("tests/wiki_lookup_049.json", "r", encoding="utf-8") as f:
  existing = {x["key"]: x for x in json.load(f)}

# Retry any that had errors
for s in SETTLEMENTS:
  cur = existing.get(s["key"], {})
  if cur.get("geo_err") or cur.get("search_err"):
    lat, lon = s["ll"]
    if cur.get("geo_err") or not cur.get("geo"):
      try:
        url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=3&format=json"
        data = fetch_json(url)
        cur["geo"] = [{"title": g["title"], "dist": g["dist"]} for g in data.get("query", {}).get("geosearch", [])]
        cur.pop("geo_err", None)
      except Exception as e:
        cur["geo_err"] = str(e)
      time.sleep(0.15)
    if cur.get("search_err"):
      try:
        q = urllib.parse.quote(f'{s["n"]} {s["c"]}')
        url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=2&format=json"
        data = fetch_json(url)
        cur["search"] = [item["title"] for item in data.get("query", {}).get("search", [])]
        cur.pop("search_err", None)
      except Exception as e:
        cur["search_err"] = str(e)
      time.sleep(0.15)
    existing[s["key"]] = cur

with open("tests/wiki_lookup_049.json", "w", encoding="utf-8") as f:
  json.dump([existing[s["key"]] for s in SETTLEMENTS], f, ensure_ascii=False, indent=2)

# Collect relevant candidate titles for all settlements
titles = set()
for s in SETTLEMENTS:
  cur = existing[s["key"]]
  for g in cur.get("geo", []):
    titles.add(g["title"])
  for t in cur.get("search", []):
    titles.add(t)

# Also add direct name guesses for known towns
extra_titles = [
  "Serrano (Córdoba)", "Barreal", "Villa Pituil", "Villa Santa Rosa (San Juan)", "Santa Rosa (San Juan)",
  "Arteaga (Santa Fe)", "Mincha", "Iglesia de Mincha", "Villa Alfredo Fortabat", "Loma Negra",
  "San Juan Bautista de Hualqui", "Hualqui", "Hersilia (Santa Fe)", "Hersilia",
  "San Mateo (Anzoátegui)", "Buta Ranquil", "Máximo Paz (Santa Fe)", "Chavarría",
  "Hilario Ascasubi (Buenos Aires)", "San Juan de Ojiba", "Santiago de Huata",
  "Río Blanco (Morona Santiago)", "Laguna El Peral", "Esmeralda (Chile)", "Yopal",
  "Khonkho Wankane", "El Palo (Caloto)", "Parán", "Llanquera", "Suesca", "Rocas de Suesca",
  "Gualmatán", "Catambuco", "Otón (Ecuador)", "Guarumo", "Guacamayas (Colombia)",
  "Jenesano", "Villa Marina (Venezuela)", "Juan Bautista Alberdi (Buenos Aires)", "Diego de Alvear (Santa Fe)",
  "9 de Julio (Corrientes)", "Nueve de Julio (Corrientes)", "Sacanta", "Elena (Córdoba)",
  "Veracruz (Táchira)", "Distrito de Río Grande (Palpa)", "Distrito de Sina", "Sina (Puno)",
  "Ocobaya", "San Félix (Falcón)", "Puente de Piedra (Cundinamarca)", "Presidente Urbina",
  "Los Cóndores (Córdoba)", "San Sebastián de los Reyes (Venezuela)", "Yatay Ti Calle",
  "Cueva Lago Sofía", "Areo (Venezuela)", "Areo", "Distrito de Quiñota", "Distrito de Esquena",
  "Distrito de Coasa", "Distrito de Miraflores (Huamalíes)", "Distrito de Levanto",
  "Antihuala", "Atuncela", "Sepulturas (Oruro)", "Antavilque", "Portillo (Tarija)", "Anchayacu"
]
for t in extra_titles:
  titles.add(t)

title_list = sorted(titles)
extracts = {}
for i in range(0, len(title_list), 20):
  batch = title_list[i:i+20]
  t_param = urllib.parse.quote("|".join(batch))
  url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&exintro=false&explaintext=true&exsectionformat=plain&exchars=3500&redirects=1&titles={t_param}&format=json"
  try:
    data = fetch_json(url)
    pages = data.get("query", {}).get("pages", {})
    for pid, pdata in pages.items():
      if int(pid) > 0:
        extracts[pdata["title"]] = {
          "extract": pdata.get("extract", ""),
          "coords": pdata.get("coordinates", [])
        }
  except Exception as e:
    print("Batch error:", i, e)
  time.sleep(0.2)

with open("tests/wiki_extracts_049.json", "w", encoding="utf-8") as f:
  json.dump(extracts, f, ensure_ascii=False, indent=2)
print(f"Fetched {len(extracts)} Wikipedia extracts")
