import csv
import json
import math
import re
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "SVEA-Toponymy/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def api_get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if "429" in str(e):
                time.sleep(2.0 * (attempt + 1))
            else:
                return {"error": str(e)}
    return {"error": "rate_limited"}

with open("tests/chunk048_lookup.json", encoding="utf-8") as f:
    items = json.load(f)

from lookup_chunk048 import ITEMS
item_by_key = {it["key"]: it for it in ITEMS}

# 1. Retry es_geo_err items politely
for entry in items:
    if "es_geo_err" in entry:
        it = item_by_key[entry["key"]]
        lat, lon = it["ll"]
        url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
        d = api_get(url)
        gs = d.get("query", {}).get("geosearch", [])
        entry["es_geo"] = [(g["title"], round(g["dist"])) for g in gs]
        time.sleep(0.25)
        q = urllib.parse.quote(f'{it["n"]} {it["c"]}')
        url2 = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        d2 = api_get(url2)
        sr = d2.get("query", {}).get("search", [])
        entry["es_sr"] = [s["title"] for s in sr]
        entry.pop("es_geo_err", None)
        time.sleep(0.25)

with open("tests/chunk048_lookup.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

# 2. Collect candidate titles to fetch extracts/content
titles = set()
extra_titles = [
    "Capacho Viejo", "Capacho Nuevo", "Independencia (Táchira)",
    "Cazorla (Guárico)", "Loreto (Corrientes)", "Valle Sacta",
    "Distrito de Pucacaca", "Casigua", "Municipio Mauroa",
    "Pucará de Lasana", "Lasana", "Distrito de Yungar",
    "Sunchales", "Apillapampa", "Fortín Olmos", "Lobos (ciudad)",
    "El Carmen de Bolívar", "Cantón Sucumbíos", "Santa Bárbara (Sucumbíos)",
    "Distrito de Cuenca (Huancavelica)", "Milagro (La Rioja)",
    "San Marcos Sierras", "Guachipas", "Villa Valeria",
    "Pedregal Grande", "San Marcos Sud", "Distrito de Rinconada-Llícuar",
    "Cerro Trinidad (sitio arqueológico)", "Choromoro", "Cultura de la Aguada",
    "Cerro Narrío", "Chancayllo", "Garagay", "Catuaro",
    "Pueblo Búho", "El Calvario (Meta)", "El Calvario (Cundinamarca)",
    "Santiago de Méndez", "Distrito de Pontó", "San Antonio de Pereira",
    "Puerto El Carmen de Putumayo", "El Salado (Dagua)", "Apiay",
    "Mateo Gómez", "Parroquia Carolina", "Parroquia San Gerardo",
    "Parroquia El Lucero", "Parroquia Uvencio Antonio Velásquez",
    "Parroquia Agua Larga", "Campo Dos (Tibú)", "Tomayrica"
]
for t in extra_titles:
    titles.add(t)

for entry in items:
    for t, dist in entry.get("es_geo", []):
        if dist < 3500 or any(w.lower() in t.lower() for w in entry["n"].split() if len(w) > 3):
            titles.add(t)
    for t in entry.get("es_sr", [])[:1]:
        if any(w.lower() in t.lower() for w in entry["n"].split() if len(w) > 3):
            titles.add(t)

titles_list = sorted(titles)
print("Fetching es.wiki pages:", len(titles_list))
wiki_pages = {}
for i in range(0, len(titles_list), 20):
    batch = titles_list[i:i+20]
    tparam = urllib.parse.quote("|".join(batch))
    url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|revisions&exintro=false&explaintext=true&exchars=3500&rvprop=content&rvslots=main&redirects=1&titles={tparam}&format=json"
    d = api_get(url)
    pages = d.get("query", {}).get("pages", {})
    for pid, pdata in pages.items():
        if int(pid) > 0:
            title = pdata.get("title")
            ext = pdata.get("extract", "")
            rev = ""
            revs = pdata.get("revisions", [])
            if revs:
                rev = revs[0].get("slots", {}).get("main", {}).get("*", "")[:4000]
            wiki_pages[title] = {"extract": ext, "wikitext_head": rev}
    time.sleep(0.3)

with open("tests/chunk048_wiki.json", "w", encoding="utf-8") as f:
    json.dump(wiki_pages, f, ensure_ascii=False, indent=2)

print("Saved wiki pages:", len(wiki_pages))
