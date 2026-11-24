import urllib.request, urllib.parse, json

# Query Wikidata SPARQL for settlements in our chunk by Spanish/English labels
names = [
  "Presidencia Roca", "Jovita", "El Sacrificio", "San Roque", "Puesto Viejo",
  "Azara", "Lucas González", "Santa Catalina", "Misión Tacaaglé", "Acheral",
  "La Reducción", "Colonia Dora", "Huanguelén", "Ingeniero Luiggi", "María Juana",
  "Huatajata", "Potobamba", "Quioma", "Chuquichambi", "Las Carreras", "Eterazama",
  "Entre Lagos", "Laraquete", "Maullín", "El Playón", "Curbatí", "Acacías",
  "Servitá", "Durania", "Tipacoque", "Quinamayó", "Charapotó", "Jenaro Herrera",
  "Congas", "Lalaquiz", "Phara", "Quivilla", "Samanco", "El Algarrobal",
  "Cáceres del Perú", "Juan Guerra", "Río Grande", "Huarautambo", "Chontay",
  "Cochapata", "La Villegas", "Chumundé", "Guale", "General Leonidas Plaza Gutiérrez",
  "Supte San Jorge", "Tres Tomas", "Ulapes", "Rotinet", "Murca", "Tambo Quemado",
  "Chinchipe", "San Fernando", "Iquipi", "Jimbe"
]

filter_str = ", ".join(f'"{n}"@es' for n in names)
sparql = f"""
SELECT ?item ?itemLabel ?coord ?inception ?countryLabel WHERE {{
  ?item wdt:P625 ?coord .
  ?item wdt:P31/wdt:P279* wd:Q486972 .
  ?item rdfs:label ?l .
  FILTER(?l IN ({filter_str}))
  OPTIONAL {{ ?item wdt:P571 ?inception . }}
  OPTIONAL {{ ?item wdt:P17 ?country . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
}} LIMIT 200
"""

url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(sparql)
req = urllib.request.Request(url, headers={"User-Agent": "ViscountToponymyBot/1.0"})
d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
for r in d["results"]["bindings"]:
  lbl = r.get("itemLabel", {}).get("value", "")
  coord = r.get("coord", {}).get("value", "")
  inc = r.get("inception", {}).get("value", "")
  ctry = r.get("countryLabel", {}).get("value", "")
  qid = r.get("item", {}).get("value", "").split("/")[-1]
  print(f"{lbl} ({qid}) | {ctry} | {coord} | inception={inc}")
