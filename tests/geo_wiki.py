import urllib.request, urllib.parse, json, time

# Check exact coordinates via Wikidata SPARQL or Wikipedia geosearch for settlements that are tricky
coords_check = [
  ("Culluay-Peru", -11.317, -76.55),
  ("Santiago Berenguela-Bolivia", -17.891, -66.418),
  ("Cruce San Martin de Porres (el Cruce)-Peru", -7.3327, -79.4829),
  ("Villcabamba-Bolivia", -17.86966, -66.19085),
  ("Carijana-Bolivia", -15.22234, -68.76965),
  ("Tiquirpaya-Bolivia", -17.115, -66.73),
  ("Buenos Aires (per_san_martin_2)-Peru", -5.9163, -77.0797),
  ("Cueros-Peru", -13.279, -71.198),
  ("San Rafael de Las Guasduas-Venezuela", 9.14889, -69.605),
  ("Trinidad de la Capilla-Venezuela", 8.71842, -68.85795),
  ("Las Piedras-Venezuela", 10.09241, -69.06641),
  ("Quinimari-Venezuela", 7.50152, -72.34368),
  ("Padre Barral-Venezuela", 9.01832, -60.89492),
  ("Pueblo Nuevo (col_magdalena)-Colombia", 9.90571, -74.10156),
  ("Media Luna-Colombia", 10.24429, -73.14473),
  ("Río Grande-Colombia", 7.92901, -76.62431),
  ("Ten-Colombia", 5.94, -72.096),
  ("Yambe-Ecuador", -0.091, -78.924),
  ("El Triunfo (ecu_orellana)-Ecuador", -0.70033, -77.31268),
  ("Chilcal-Ecuador", 0.939, -78.185),
  ("Las Conchitas-Argentina", -31.731, -60.309),
  ("Cayastá Chaná-Timbú-Argentina", -31.202, -60.163),
  ("Huito-Chile", -41.70916, -73.15443),
  ("Puerto Nuevo-Chile_2", -40.22357, -72.59706),
  ("Perinao-Ecuador", -1.3, -80.0),
]

out = []
for key, lat, lon in coords_check:
  time.sleep(0.35)
  url = f'https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json'
  try:
    req = urllib.request.Request(url, headers={'User-Agent':'SVEA-Research/1.0 (contact@example.org)'})
    data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    hits = [(x['title'], int(x['dist'])) for x in data.get('query', {}).get('geosearch', [])]
    out.append(f"{key} ({lat},{lon}): {hits}")
  except Exception as e:
    out.append(f"{key}: ERR {e}")

with open('tests/geo_out.txt', 'w', encoding='utf-8') as f:
  f.write('\n'.join(out))
print('GEO DONE', len(out))
