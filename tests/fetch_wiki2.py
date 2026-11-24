import urllib.request, urllib.parse, json, time

titles = [
  'Municipio Federación', 'Parroquia Padre Barral', 'Cantón Loreto',
  'Castillo de San Luis de Bocachica', 'Castillo de San Fernando de Bocachica',
  'La Piedra (Venezuela)', 'Yaritagua', 'Cantón Antonio Ante',
  'Cantón Eloy Alfaro', 'Departamento de Casanare (Boyacá)',
  'Santo Domingo (Ecuador)', 'Cayastá', 'San José (Pacasmayo)',
  'Quero (Paucartambo)', 'Distrito de Kosñipata', 'Mamatoco (Santa Marta)',
  'Churuguara', 'Pueblo Nuevo (Colombia)', 'Punta de Piedras',
  'Provincia de Moyobamba', 'Distrito de Jepelacio', 'Distrito de Calzada',
  'Distrito deSoritor', 'Distrito de Soritor', 'Distrito de Yantaló'
]

def fetch_json(url):
  for attempt in range(3):
    try:
      req = urllib.request.Request(url, headers={'User-Agent':'SVEA-Research/1.0 (contact@example.org)'})
      return json.loads(urllib.request.urlopen(req, timeout=20).read().decode('utf-8'))
    except Exception as e:
      if attempt == 2: raise
      time.sleep(2.0)

out = []
for i in range(0, len(titles), 20):
  if i > 0: time.sleep(1.5)
  batch = titles[i:i+20]
  url = 'https://es.wikipedia.org/w/api.php?action=query&prop=revisions|coordinates&rvprop=content&rvslots=main&redirects=1&format=json&titles=' + urllib.parse.quote('|'.join(batch))
  data = fetch_json(url)
  pages = data.get('query', {}).get('pages', {})
  for pid, p in pages.items():
    if 'missing' in p:
      out.append(f"MISSING: {p.get('title')}")
      continue
    title = p.get('title')
    coords = p.get('coordinates')
    revs = p.get('revisions', [])
    txt = revs[0]['slots']['main']['*'] if revs else ''
    lines = [l.strip() for l in txt.split('\n') if l.strip() and not l.strip().startswith('[[Categoría') and not l.strip().startswith('{{cita')]
    out.append(f"=== {title} | coords={coords}")
    # keep infobox + first 25 lines + any Historia/Fundación lines
    kept = []
    in_hist = False
    for l in lines:
      low = l.lower()
      if '== historia' in low or '== reseña' in low or '== top' in low or '== etim' in low or '== orígenes' in low:
        in_hist = True
      elif l.startswith('== ') and in_hist:
        in_hist = False
      if in_hist or any(k in low for k in ['fundac', 'creac', 'fecha', 'nombre', 'erecc', 'establec', 'poblad', 'siglo', 'ley ', 'decreto', 'reducc', 'misión', 'cacique', 'encomienda', 'yambe', 'avisado', 'mamatoco', 'chaltura', 'barral', 'ten ', 'bocachica']):
        kept.append('   ' + l[:240])
    for l in kept[:25]:
      out.append(l)
    out.append('')

# Also search for "Avisado" "Buenos Aires" "San Martín" and "Yambe" and "Ten" Casanare and "Santiago Berenguela" and "Mamatoco"
searches = [
  ("Avisado Moyobamba", "es", "Avisado Buenos Aires Moyobamba"),
  ("Carijana Bolivia", "es", "Carijana"),
  ("Santiago Berenguela", "es", "Berenguela Bolivia"),
  ("Chilcal Carchi", "es", "Chilcal Carchi"),
  ("San Rafael de Las Guasduas", "es", "Guasduas Portuguesa"),
  ("Ten Casanare", "es", "Ten Casanare"),
  ("Cayasta", "en", "Cayastá"),
  ("Lomas de Ilo", "es", "Lomas de Ilo"),
  ("Alero Lipiche", "es", "Lipiche"),
  ("Casa de Piedra de Ortega", "es", "Casa de Piedra Ortega")
]
for label, lang, q in searches:
  time.sleep(0.5)
  url = f'https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch=' + urllib.parse.quote(q) + '&srlimit=3&format=json'
  try:
    data = fetch_json(url)
    hits = [(x['title'], x['snippet'][:140]) for x in data.get('query', {}).get('search', [])]
    out.append(f"SEARCH {label}: {hits}")
  except Exception as e:
    out.append(f"SEARCH {label}: ERR {e}")

with open('tests/wiki_out2.txt', 'w', encoding='utf-8') as f:
  f.write('\n'.join(out))
print('DONE2', len(out))
