import json
import re
import time
import urllib.parse
import urllib.request

with open("tests/chunk055_wiki_hits.json", "r", encoding="utf-8") as f:
  HITS = json.load(f)

UA = {"User-Agent": "SVEA-Toponymy-Bot/1.0 (https://confoederatio.org; polite-sequential)"}

def fetch_json(url):
  req = urllib.request.Request(url, headers=UA)
  with urllib.request.urlopen(req, timeout=20) as r:
    return json.loads(r.read().decode("utf-8"))

# Select relevant titles only (filter obvious noise from search)
relevant_titles = set()
noise = {
  "Piper PA-31 Navajo", "Juana Azurduy", "Gastronomía del Perú", "Mate (infusión)",
  "Frito pie", "Escopeta antidisturbios", "Sobras", "Unión Argentina de Rugby",
  "Unión Democrática (Argentina)", "Unión Cívica (Argentina)", "Guaguas de pan",
  "Pan de molde", "Ricardo Arjona", "Pouteria caimito", "Chrysophyllum cainito",
  "Vitaly Novich", "Diosa Canales", "Fortuna (cigarrillo)", "Manuel Fortuna",
  "Chepe Fortuna", "Perímetro", "Mediatriz", "Alfonso Leyva", "Hillary Wolf",
  "Sunisa Lee", "Vara", "Caduceo", "Psittacoidea", "Amazona (animal)",
  "Carlos Concha Torres", "Guerra de Concha", "Eloy Linares Málaga",
  "Comercio global de plata entre los siglos XVI y XIX"
}

for h in HITS:
  for t in h.get("geo", []):
    if t not in noise:
      relevant_titles.add(t)
  for t in h.get("search", [])[:2]:
    if t not in noise:
      relevant_titles.add(t)

title_list = sorted(relevant_titles)
print("Fetching", len(title_list), "eswiki pages sequentially...")

es_pages = {}
for i in range(0, len(title_list), 15):
  batch = title_list[i:i+15]
  url = "https://es.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
    "action": "query",
    "prop": "revisions|coordinates",
    "rvprop": "content",
    "rvslots": "main",
    "titles": "|".join(batch),
    "format": "json",
    "redirects": "1"
  })
  try:
    d = fetch_json(url)
    pages = d.get("query", {}).get("pages", {})
    for pid, p in pages.items():
      if "missing" not in p:
        revs = p.get("revisions", [])
        txt = revs[0]["slots"]["main"]["*"] if revs else ""
        # Keep infobox + first 3000 chars + Historia section if present
        hist_idx = txt.lower().find("== historia")
        hist_snip = txt[hist_idx:hist_idx+2500] if hist_idx != -1 else ""
        es_pages[p["title"]] = {
          "coords": p.get("coordinates", []),
          "head": txt[:2500],
          "historia": hist_snip
        }
  except Exception as e:
    print("Batch err", i, e)
  time.sleep(0.3)

with open("tests/chunk055_es_pages.json", "w", encoding="utf-8") as f:
  json.dump(es_pages, f, ensure_ascii=False, indent=2)
print("Saved es_pages:", len(es_pages))
