import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "AntigravityResearchBot/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def wiki_search_and_extract(query, lang="es"):
  s_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&srlimit=1&format=json"
  req = urllib.request.Request(s_url, headers=UA)
  data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
  hits = data.get("query", {}).get("search", [])
  if not hits:
    return None
  title = hits[0]["title"]
  e_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts|revisions&rvprop=content&rvslots=main&explaintext=1&exintro=1&titles={urllib.parse.quote(title)}&format=json"
  req2 = urllib.request.Request(e_url, headers=UA)
  data2 = json.loads(urllib.request.urlopen(req2, timeout=15).read().decode("utf-8"))
  pages = data2.get("query", {}).get("pages", {})
  for pid, p in pages.items():
    extract = p.get("extract", "")[:500].replace("\n", " ")
    wikitext = ""
    revs = p.get("revisions", [])
    if revs:
      wikitext = revs[0].get("slots", {}).get("main", {}).get("*", "")[:2500]
    # extract founding/creation/history lines from wikitext
    hist_lines = []
    for line in wikitext.splitlines():
      if any(k in line.lower() for k in ["fundac", "creac", "erig", "fecha", "nombre", "coord", "lat", "lon", "departamento", "provincia", "cantón", "municipio", "distrito", "parroquia", "antiguo"]):
        hist_lines.append(line.strip()[:140])
    return {"title": title, "extract": extract, "infobox": hist_lines[:10]}
  return None

queries = [
  ("Conima-Peru", "Distrito de Conima"),
  ("Villa Ibáñez-Argentina", "Villa Ibáñez"),
  ("Matituy-Colombia", "Matituy"),
  ("Songo-Bolivia", "Zongo Bolivia"),
  ("Pilaló-Ecuador", "Pilaló"),
  ("Pampa Hermosa (per_san_martin)-Peru", "Pampa Hermosa San Martín Alianza Peru"),
  ("Chacra de La Merced-Argentina", "Chacra de la Merced"),
  ("Santos de Abelgas-Venezuela", "Santos de Abelgas"),
  ("Santa Rosa de Pilaguin-Ecuador", "Santa Rosa Ambato Ecuador"),
  ("Ventanillas de Apan-Peru", "Ventanillas de Apán"),
  ("Alejandra-Argentina", "Alejandra Santa Fe"),
  ("Pueblo Nuevo (per_huanuco)-Peru", "Distrito de Pueblo Nuevo Leoncio Prado"),
  ("San José De Morona-Ecuador", "San José de Morona"),
  ("Cumbaya-Ecuador", "Cumbayá"),
  ("Huaviña-Chile", "Huaviña"),
  ("Villa del Rosario (arg_entre_rios)-Argentina", "Villa del Rosario Entre Ríos"),
  ("Cotacachi-Ecuador_2", "Cotacachi"),
  ("La Escondida-Argentina", "La Escondida Chaco"),
  ("Poroto-Peru", "Distrito de Poroto"),
  ("Nueva Troncal-Ecuador", "Cascales Ecuador"),
  ("Tongod-Peru", "Distrito de Tongod"),
  ("Gaira-Colombia", "Gaira"),
  ("Chinchihuasi-Peru", "Distrito de Chinchihuasi"),
  ("Isla Verde-Argentina", "Isla Verde Córdoba"),
  ("Cochamarca-Peru", "Distrito de Cochamarca"),
  ("Sanipaya-Bolivia", "Sanipaya"),
  ("Los Encuentros-Ecuador", "Los Encuentros Yantzaza"),
  ("Curaray-Ecuador", "Curaray"),
  ("Kuntur Was-Peru", "Kuntur Wasi"),
  ("San José (ven_trujillo_2)-Venezuela", "San José de Tostós"),
  ("Piedra Grande-Venezuela", "Parroquia Piedra Grande"),
  ("Santander-Peru", "Alpamarca"),
  ("Rinconada-Argentina", "Rinconada Jujuy"),
  ("Madre Tierra-Ecuador", "Madre Tierra Pastaza"),
  ("Vista Flores-Argentina", "Vista Flores Mendoza"),
  ("Izcuchaca-Peru_2", "Zurite Anta"),
  ("San Hilarión-Peru", "Distrito de San Hilarión"),
  ("Cojata-Peru", "Distrito de Cojata"),
  ("San José de Tiznados-Venezuela", "San José de Tiznados"),
  ("Las Pirias-Peru", "Distrito de Las Pirias"),
  ("Constantino Fernández-Ecuador", "Constantino Fernández Ecuador"),
  ("San Antonio (per_lima_2)-Peru", "Distrito de San Antonio Cañete"),
  ("Cumbemayo-Peru", "Cumbemayo"),
  ("Complejo Miculla - Pachia Sector: C-Peru", "Miculla"),
  ("La Para-Argentina", "La Para"),
  ("Pocpo-Bolivia", "Pocpo"),
  ("Guanazán-Ecuador", "Guanazán"),
  ("Relave-Peru", "Relave Ayacucho"),
  ("Pansaleo-Ecuador", "Panzaleo Cotopaxi"),
  ("Usmagama-Chile", "Usmagama"),
  ("Santa Isabel (col_cordoba)-Colombia", "Santa Isabel Montería"),
  ("Pílamo-Colombia", "Pílamo"),
  ("Solor-Chile", "Ayllu de Solor"),
  ("Amaicha del Valle-Argentina", "Amaicha del Valle"),
  ("San Ignacio Miní-Argentina", "San Ignacio Miní"),
]

out = {}
for k, q in queries:
  try:
    out[k] = wiki_search_and_extract(q)
  except Exception as e:
    out[k] = {"error": str(e)}

with open("f:/Active Projects/Project 1509 - SVEA/tests/tmp_wiki_out.json", "w", encoding="utf-8") as fh:
  json.dump(out, fh, ensure_ascii=False, indent=2)
print("Done:", len(out))
