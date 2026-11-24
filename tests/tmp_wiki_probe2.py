import json
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "AntigravityResearchBot/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def wiki_fetch(title, lang="es"):
  e_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts|revisions&rvprop=content&rvslots=main&explaintext=1&exintro=1&titles={urllib.parse.quote(title)}&format=json"
  req = urllib.request.Request(e_url, headers=UA)
  data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
  pages = data.get("query", {}).get("pages", {})
  for pid, p in pages.items():
    if pid == "-1":
      return None
    extract = p.get("extract", "")[:600].replace("\n", " ")
    wikitext = ""
    revs = p.get("revisions", [])
    if revs:
      wikitext = revs[0].get("slots", {}).get("main", {}).get("*", "")[:3500]
    hist_lines = []
    for line in wikitext.splitlines():
      if any(k in line.lower() for k in ["fundac", "creac", "erig", "fecha", "nombre", "antiguo", "denominac", "historia", "15", "16", "17", "18", "19"]):
        if not line.strip().startswith("|imagen") and not line.strip().startswith("|mapa"):
          hist_lines.append(line.strip()[:160])
    return {"title": p.get("title"), "extract": extract, "lines": hist_lines[:12]}
  return None

def wiki_search(query, lang="es"):
  s_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&srlimit=3&format=json"
  req = urllib.request.Request(s_url, headers=UA)
  data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
  hits = data.get("query", {}).get("search", [])
  return [h["title"] for h in hits]

targets = [
  ("Villa Ibáñez-Argentina", ["Villa Ibáñez", "Departamento Ullum"]),
  ("Matituy-Colombia", ["Matituy", "La Florida (Nariño)"]),
  ("Pilaló-Ecuador", ["Pilaló", "Cantón Pujilí"]),
  ("Pampa Hermosa (per_san_martin)-Peru", ["Distrito de Pampa Hermosa (Ucayali)", "Distrito de Caynarachi"]),
  ("Santa Rosa de Pilaguin-Ecuador", ["Santa Rosa (Tungurahua)", "Pilahuín"]),
  ("San José De Morona-Ecuador", ["Cantón Tiwintza"]),
  ("Cumbaya-Ecuador", ["Cumbayá (parroquia)"]),
  ("Huaviña-Chile", ["Huaviña", "Quebrada de Tarapacá"]),
  ("Villa del Rosario (arg_entre_rios)-Argentina", ["Villa del Rosario (Entre Ríos)"]),
  ("La Escondida-Argentina", ["La Escondida (Argentina)"]),
  ("Nueva Troncal-Ecuador", ["Cantón Cascales"]),
  ("San José (ven_trujillo_2)-Venezuela", ["Tostós", "Municipio Boconó"]),
  ("Piedra Grande-Venezuela", ["Municipio Democracia (Falcón)"]),
  ("Santander-Peru", ["Distrito de Santa Bárbara de Carhuacayán", "Alpamarca"]),
  ("Rinconada-Argentina", ["Rinconada (Argentina)", "Departamento Rinconada"]),
  ("Madre Tierra-Ecuador", ["Madre Tierra (Pastaza)", "Cantón Mera"]),
  ("Vista Flores-Argentina", ["Vista Flores"]),
  ("Cojata-Peru", ["Distrito de Cojata"]),
  ("Constantino Fernández-Ecuador", ["Constantino Fernández (Tungurahua)", "Constantino Fernández"]),
  ("Guanazán-Ecuador", ["Guanazán"]),
  ("Relave-Peru", ["Distrito de Pullo", "Relave"]),
  ("Pansaleo-Ecuador", ["Panzaleo", "Cantón Salcedo"]),
  ("Santa Isabel (col_cordoba)-Colombia", ["Montería"]),
  ("Pílamo-Colombia", ["Guachené", "Pílamo"]),
  ("Solor-Chile", ["San Pedro de Atacama", "Aldea de Tulor"]),
  ("Amaicha del Valle-Argentina", ["Amaicha del Valle"]),
  ("San Ignacio Miní-Argentina", ["San Ignacio Miní"]),
  ("Villa del Rosario-2", ["Villa del Rosario (Entre Ríos)"]),
  ("Santos de Abelgas-Venezuela", ["Municipio Antonio Díaz (Delta Amacuro)"]),
  ("Conima-Peru", ["Conima", "Distrito de Conima"]),
  ("Songo-Bolivia", ["Zongo", "Valle de Zongo"]),
  ("Pocpo-Bolivia", ["Poroma"]),
  ("Sanipaya-Bolivia", ["Cocapata", "Ayopaya"]),
  ("Chiacani-Bolivia", ["Guanay", "Tipuani"]),
  ("Gaira-Colombia", ["Gaira", "Santa Marta"]),
  ("Kuntur Was-Peru", ["Kuntur Wasi"]),
]

out = {}
for k, candidates in targets:
  res = None
  for c in candidates:
    time.sleep(0.25)
    try:
      res = wiki_fetch(c)
      if res:
        break
    except Exception as e:
      res = {"error": str(e)}
  if not res:
    time.sleep(0.25)
    try:
      hits = wiki_search(candidates[0])
      if hits:
        time.sleep(0.25)
        res = wiki_fetch(hits[0])
    except Exception as e:
      res = {"error": str(e)}
  out[k] = res

with open("f:/Active Projects/Project 1509 - SVEA/tests/tmp_wiki_out2.json", "w", encoding="utf-8") as fh:
  json.dump(out, fh, ensure_ascii=False, indent=2)
print("Done:", len(out))
