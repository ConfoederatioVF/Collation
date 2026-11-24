import urllib.request, urllib.parse, json, time

searches = [
  ("Queros", "es", "Queros Paucartambo Cusco"),
  ("Villcabamba", "es", "Vilcabamba Cochabamba Arque"),
  ("Carijana", "es", "Carijana Charazani"),
  ("Tiquirpaya", "es", "Tiquirpaya Cochabamba"),
  ("Churuguara", "es", "Churuguara"),
  ("San Rafael de Las Guasduas", "es", "San Rafael de Las Guasduas"),
  ("Las Piedras", "es", "Las Piedras Yaracuy Peña"),
  ("Pueblo Nuevo Magd", "es", "Pueblo Nuevo Ariguaní Magdalena"),
  ("Bocachica", "es", "Bocachica Cartagena"),
  ("Yascual", "es", "Yascual Túquerres"),
  ("Ten", "es", "Ten Casanare"),
  ("Chaltura", "es", "Chaltura Imbabura"),
  ("Loreto Orellana", "es", "Cantón Loreto Orellana"),
  ("Taracoa", "es", "Taracoa Orellana"),
  ("Santo Domingo de Onzole", "es", "Santo Domingo de Onzole"),
  ("Cayasta", "es", "Cayastá"),
  ("Mantagua", "es", "Mantagua Quintero"),
  ("Huito", "es", "Fuerte Huito Calbuco"),
  ("Puerto Nuevo", "es", "Puerto Nuevo La Unión Chile"),
  ("Cruce San Martin", "es", "Cruce San Martín de Porres Pacasmayo"),
  ("Buenos Aires San Martin", "es", "Buenos Aires Rioja San Martín Avisado"),
  ("Trinidad de la Capilla", "es", "Trinidad de la Capilla Guanarito"),
  ("Quinimari", "es", "Quinimarí Táchira"),
  ("Padre Barral", "es", "Padre Barral Delta Amacuro"),
  ("Rio Grande Turbo", "es", "Río Grande Turbo Antioquia"),
  ("Yambe", "es", "Yambe Pichincha Ecuador"),
  ("Chilcal", "es", "Chilcal Carchi Ecuador"),
  ("Perinao", "es", "Perinao Manabí Ecuador")
]

out = []
for key, lang, q in searches:
  time.sleep(0.35)
  url = f'https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch=' + urllib.parse.quote(q) + '&srlimit=3&format=json'
  try:
    req = urllib.request.Request(url, headers={'User-Agent':'SVEA-Research/1.0 (contact@example.org)'})
    data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    hits = [(x['title'], x['snippet'][:120]) for x in data.get('query', {}).get('search', [])]
    out.append(f"{key} ({q}): {hits}")
  except Exception as e:
    out.append(f"{key}: ERR {e}")

with open('tests/search_out.txt', 'w', encoding='utf-8') as f:
  f.write('\n'.join(out))
print('SEARCH DONE', len(out))
