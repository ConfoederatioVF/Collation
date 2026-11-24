import json
import time
import urllib.parse
import urllib.request

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; SVEAResearch/1.0; +mailto:research@confoederatio.org)'}


def fetch_json(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=12) as resp:
    return json.loads(resp.read().decode('utf-8'))


def wiki_geosearch(lat, lng, lang='es', radius=10000):
  url = (
      f'https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch'
      f'&gscoord={lat}|{lng}&gsradius={radius}&gslimit=5&format=json'
  )
  try:
    data = fetch_json(url)
    return data.get('query', {}).get('geosearch', [])
  except Exception as e:
    return [{'error': str(e)}]


def wiki_extract_full(title, lang='es'):
  url = (
      f'https://{lang}.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}'
      f'&prop=extracts&explaintext=1&format=json'
  )
  try:
    data = fetch_json(url)
    pages = data.get('query', {}).get('pages', {})
    for p in pages.values():
      return p.get('extract', '')
  except Exception as e:
    return f'ERROR: {e}'
  return ''


def wiki_search(q, lang='es'):
  url = f'https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=3&format=json'
  try:
    data = fetch_json(url)
    return [x['title'] for x in data.get('query', {}).get('search', [])]
  except Exception:
    return []


# Items to investigate deeply (history, founding, colonial name, renames)
TARGETS = [
    ('Sinsacate-Argentina', -30.94285, -64.09397, 'Sinsacate'),
    ('Barabara-Venezuela', 11.342, -68.975, 'Barabara Falcón Venezuela'),
    ('Pacocha-Peru', -17.61083, -71.34028, 'Distrito de Pacocha'),
    ('Vichuquén-Chile', -34.82954, -72.00987, 'Vichuquén'),
    ('Paraíso de San José-Venezuela', 9.80517, -69.50698, 'Paraíso de San José Lara'),
    ('Cochamó-Chile', -41.75191, -72.19424, 'Cochamó'),
    ('La Gabarra-Colombia', 8.99726, -72.89728, 'La Gabarra'),
    ('Charape-Peru', -5.3274, -79.1215, 'Charape San Ignacio Cajamarca'),
    ('San Lucas-Ecuador', -3.75305, -79.24415, 'San Lucas Loja'),
    ('Camarones-Chile_2', -19.015, -69.861, 'Camarones (comuna)'),
    ('Mucuchies-Venezuela', 8.748, -70.921, 'Mucuchíes'),
    ('Colonia El Simbolar-Argentina', -27.72481, -63.86288, 'Colonia El Simbolar'),
    ('Nelson-Argentina', -31.2677, -60.76206, 'Nelson (Santa Fe)'),
    ('Soledad-Argentina', -30.61953, -60.91457, 'Soledad (Santa Fe)'),
    ('Colaisaca-Ecuador', -4.244, -79.68256, 'Colaisaca'),
    ('Pacobamba-Peru', -13.61528, -73.08389, 'Distrito de Pacobamba'),
    ('Isinlivi-Ecuador', -0.78143, -78.85611, 'Isinliví'),
    ('Cayastá-Argentina', -31.19867, -60.15938, 'Cayastá'),
    ('Enciso-Colombia', 6.66803, -72.69965, 'Enciso (Santander)'),
    ('Pomacancha-Peru_2', -11.736, -76.27, 'Pomacancha'),
    ('Santa Rosa del Rio Primero-Argentina', -31.153, -63.399, 'Santa Rosa de Río Primero'),
    ('Ocros (per_ancash)-Peru', -10.40333, -77.39667, 'Ocros (Áncash)'),
    ('Pantoño-Venezuela', 10.51556, -63.575, 'Pantoño Sucre'),
    ('Bowen-Argentina', -35.00042, -67.51046, 'Bowen'),
    ('Calzada-Peru', -6.03028, -77.06667, 'Distrito de Calzada'),
    ('Sauce (ury_rio_negro)-Uruguay', -32.90179, -57.73823, 'Sauce Río Negro Uruguay'),
    ('Costa Rica-Colombia', 3.75178, -76.23411, 'Costa Rica Ginebra'),
    ('Villa Unión-Argentina', -29.31776, -68.22776, 'Villa Unión (La Rioja)'),
    ('Cocaniguas-Ecuador', -0.115, -78.953, 'Cocaniguas'),
    ('Santa Ana (col_bolivar)-Colombia', 10.2389, -75.55575, 'Santa Ana Barú'),
    ('Garmendia-Argentina', -26.57412, -64.55867, 'Gobernador Garmendia'),
    ('San Fernando Chile-Chile', -34.584, -70.989, 'San Fernando (Chile)'),
    ('Santa Maria de Los Lagos-Chile', -39.85319, -72.72986, 'Los Lagos (Chile)'),
    ('Pampa Blanca-Argentina', -24.53522, -65.07181, 'Pampa Blanca'),
    ('Chivor-Colombia', 4.88817, -73.3684, 'Chivor'),
    ('Santo Tomas de Pata-Peru', -13.11306, -74.41889, 'Distrito de Santo Tomás de Pata'),
    ('Alcalá-Bolivia', -19.36753, -64.39105, 'Villa Alcalá'),
    ('Margarita-Argentina', -29.69249, -60.25222, 'Margarita (Santa Fe)'),
    ('Pacarní-Colombia', 2.60843, -75.69836, 'Pacarní'),
    ('Puerto Cayo-Ecuador', -1.32359, -80.70451, 'Puerto Cayo'),
    ('Umamac-Argentina', -28.677, -63.597, 'Umamac'),
    ('Charapaya-Bolivia', -17.369, -66.755, 'Charapaya'),
    ('San Roque Cañaverales-Colombia', 7.55, -73.544, 'San Roque Cañaverales'),
    ('Chalán-Colombia', 9.54535, -75.3127, 'Chalán'),
    ('Corpus-Argentina', -27.1278, -55.50942, 'Corpus Christi (Misiones)'),
    ('San Diego de Alcala-Venezuela', 10.115, -66.778, 'Ocumare del Tuy'),
    ('Carlos Julio Arosemena Tola-Ecuador', -1.16859, -77.93139, 'Carlos Julio Arosemena Tola'),
    ('El Maitén-Argentina', -42.05031, -71.16779, 'El Maitén'),
    ('Sotoca-Chile', -19.583, -69.201, 'Sotoca'),
    ('Pulan-Peru', -6.73889, -78.92028, 'Distrito de Pulán'),
    ('Boyacá-Ecuador', -0.53787, -80.16201, 'Boyacá Manabí'),
    ('La Dormida-Argentina_2', -30.354, -63.949, 'San José de la Dormida'),
    ('La Luz-Venezuela', 8.39556, -69.82389, 'La Luz Barinas'),
    ('Pulido Méndez-Venezuela', 8.62389, -71.61944, 'Parroquia Pulido Méndez'),
    ('Páez (col_boyaca)-Colombia', 5.09732, -73.05274, 'Páez (Boyacá)'),
    ('Membrillo-Ecuador', -0.8715, -79.95263, 'Membrillo Manabí'),
    ('General Lavalle-Argentina', -36.40635, -56.94324, 'General Lavalle (Buenos Aires)'),
]

out = {}
for key, lat, lng, q in TARGETS:
  geo = wiki_geosearch(lat, lng, 'es', 8000)
  sr = wiki_search(q, 'es')
  best_title = sr[0] if sr else (geo[0]['title'] if geo and 'title' in geo[0] else None)
  txt = wiki_extract_full(best_title, 'es') if best_title else ''
  out[key] = {
      'geo': [g.get('title') for g in geo if isinstance(g, dict)],
      'search': sr,
      'title': best_title,
      'extract': txt[:2500]
  }
  time.sleep(0.08)

with open('tests/chunk033_wiki.json', 'w', encoding='utf-8') as f:
  json.dump(out, f, ensure_ascii=False, indent=2)
print('DONE', len(out))
