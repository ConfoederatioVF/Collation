import json, urllib.request, urllib.parse, time, re

titles_to_fetch = [
  # Already matched or candidate exact titles on es.wikipedia.org
  "Santa Isabel (Santa Fe)", "Cantón Santa Clara", "Pica (Chile)", "Distrito de Saisa",
  "Caá Catí", "Villa Sarmiento (General Roca)", "Fray Luis Beltrán (Mendoza)",
  "Santa Ana de los Guácaras", "Duna Grande", "Departamento Paclín", "Paccha (Morropón)",
  "Chimpay", "Distrito de La Ramada", "Villa de Pomán", "Pozo Hondo", "Coronel Juan Solá",
  "Distrito de Abelardo Pardo Lezameta", "Sama Grande", "Guantajaya", "Huasco Bajo",
  "Puerto Rondón", "Copequén", "La Capuera", "Distrito de Chiguirip",
  "General Manuel Belgrano (Formosa)", "Villa Dos Trece", "Loma de Arena", "Mutiscua",
  "Viviate", "Distrito de Tres Unidos", "Taganga", "Santa Cruz (Alto Amazonas)",
  "Distrito de Santa Cruz (Alto Amazonas)", "San Genaro Norte", "Simbilá", "Los Antiguos",
  "Cantón Quilanga", "Gobernador Juan E. Martínez", "Catavi", "Puan",
  "Distrito de Inambari", "Inzá", "San Andrés de Pisimbalá", "Guanacas",
  "Campo Elías (Trujillo)", "Municipio Juan Vicente Campo Elías", "Parroquia Agua Santa",
  "Parroquia Chura", "Parroquia San Simón", "Parroquia Bachillero", "Parroquia El Retiro",
  "Parroquia Chontaduro", "Parroquia Abdón Calderón", "El Chical", "Cavari",
  "Santa Clara (Loreto)", "Santa Clara de Nanay", "Chanavaya", "Sipisa", "Sapse",
  "Villa de Pasco", "Tinyahuarco", "Distrito de Tinyahuarco", "Chairama", "Pueblito Chairama",
  "Punta Laguna", "Yavi", "La Cueva (Jujuy)", "Santa Bárbara (Cueva)"
]

#Wait: let's also search eswiki for specific titles that might have slightly different page names
search_queries = [
  ("La Cueva de Ya", "La Cueva Jujuy arqueología"),
  ("La Milagrosa", "Guanacas Inzá Cauca"),
  ("Santa Clara Peru", "Santa Clara Nanay Iquitos"),
  ("Puan", "Puan Buenos Aires"),
  ("Paclin", "La Merced Paclín Catamarca"),
  ("Abdon Calderon", "Abdón Calderón Azuay"),
  ("El Chical", "El Chical Carchi"),
  ("Chura", "Chura Quinindé"),
  ("San Simon", "San Simón Guaranda Bolívar"),
  ("Bachillero", "Bachillero Tosagua"),
  ("El Retiro", "El Retiro Machala"),
  ("Chontaduro", "Chontaduro Rioverde"),
  ("Simon Bolivar", "Simón Bolívar Julio Moreno Santa Elena"),
  ("Campo Elias", "Campo Elías Trujillo Venezuela"),
  ("Agua Santa", "Agua Santa Trujillo Venezuela"),
  ("Taganga", "Taganga"),
  ("Cavari", "Cavari Inquisivi"),
  ("Guantajaya", "Huantajaya"),
  ("Chanabaya", "Chanavaya"),
  ("Sipisa", "Sipiza"),
  ("Inambari", "Inambari Carabaya Puno"),
  ("Villa Pasco", "Villa de Pasco"),
  ("Chairama", "Chairama Pueblito Tayrona"),
  ("Sapse", "Sapse Bolivia"),
  ("San Juan de Oro", "San Juan de Oro Jujuy"),
  ("Santiago de Vado", "Santiago de Vado Ayacucho"),
  ("La Lagunita", "Nirgua Yaracuy"),
  ("Buenavista", "Buenavista Ocaña"),
  ("Pueblo Nuevo", "Pueblo Nuevo Arauca"),
  ("Las Piedras", "Las Piedras Bolívar Colombia"),
  ("Gallipavo", "Gallipavo Chile"),
  ("Ayallaqta", "Ayallaqta"),
  ("Altarani", "Altarani Puno"),
  ("Campos Elevados", "Campos Elevados Casma"),
  ("Jaiva", "Jaiva Barranca arqueología"),
  ("Siswa", "Siswa Huánuco"),
  ("Cerro Chillin", "Cerro Chillin")
]

def api_get(params):
  url = "https://es.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
  req = urllib.request.Request(url, headers={"User-Agent": "ViscountResearch/1.0 (https://confoederatio.org)"})
  with urllib.request.urlopen(req, timeout=30) as r:
    return json.loads(r.read().decode("utf-8"))

found_titles = list(dict.fromkeys(titles_to_fetch))
search_map = {}
for k, q in search_queries:
  try:
    res = api_get({"action": "query", "list": "search", "srsearch": q, "srlimit": 3, "format": "json"})
    hits = [x["title"] for x in res.get("query", {}).get("search", [])]
    search_map[k] = hits
    for h in hits[:2]:
      if h not in found_titles:
        found_titles.append(h)
  except Exception as e:
    search_map[k] = [str(e)]
  time.sleep(0.2)

extracts = {}
for i in range(0, len(found_titles), 10):
  batch = found_titles[i:i+10]
  try:
    data = api_get({
      "action": "query",
      "prop": "extracts",
      "explaintext": "1",
      "titles": "|".join(batch),
      "format": "json"
    })
    for pid, page in data.get("query", {}).get("pages", {}).items():
      if "extract" in page:
        extracts[page["title"]] = page["extract"]
  except Exception as e:
    print("Err batch:", e)
  time.sleep(0.3)

with open("tests/wiki_full_data.json", "w", encoding="utf-8") as f:
  json.dump({"search_map": search_map, "extracts": extracts}, f, ensure_ascii=False, indent=2)
print("Done! Extracts:", len(extracts))
