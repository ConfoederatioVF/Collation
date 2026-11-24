import json, urllib.parse, urllib.request, re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SVEA-Research/1.0'}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode('utf-8', errors='replace')

titles = [
    "Distrito de La Peca",
    "Cantón Rioverde",
    "Distrito de Pilpichaca",
    "Cantón Mira",
    "Cantón Bolívar (Carchi)",
    "Bolívar (Carchi)",
    "Santiago de Callapa",
    "Iglesia de Santiago de Callapa",
    "Distrito de Llacllín",
    "Distrito de Parcoy",
    "Distrito de Choco",
    "Distrito de Llauta",
    "Entrerríos (Antioquia)",
    "Municipio Independencia (Yaracuy)",
    "Puerto Morín",
    "Guañape",
    "Distrito de Andoas",
    "Cantón Chordeleg",
    "Cantón Gualaceo",
]

url = "https://es.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exlimit=20&redirects=1&format=json&titles=" + urllib.parse.quote("|".join(titles))
data = json.loads(fetch(url))
pages = data.get("query", {}).get("pages", {})
out = {}
for pid, p in pages.items():
    t = p.get("title")
    ext = p.get("extract", "")
    print(f"=== {t} (len={len(ext)}) ===")
    print(ext[:1200])
    out[t] = ext

with open("tests/wiki_pages.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
