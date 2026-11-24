import urllib.request, urllib.parse, json, re, time

HEADERS = {'User-Agent': 'SVEA-Historical-Research/1.0 (https://confoederatio.org; research@confoederatio.org)'}

def fetch_wikitext_batch(titles):
    url = 'https://es.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&rvslots=main&redirects=1&titles=' + urllib.parse.quote('|'.join(titles)) + '&format=json'
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode('utf-8'))
    pages = d.get('query', {}).get('pages', {})
    res = {}
    for p in pages.values():
        if 'missing' in p:
            continue
        t = p.get('title', '')
        revs = p.get('revisions', [])
        if not revs:
            continue
        txt = revs[0].get('slots', {}).get('main', {}).get('*', '')
        # Extract infobox (first 2500 chars) + Historia / Toponimia sections
        infobox = txt[:2500]
        hist_m = re.search(r'(==\s*(?:Historia|Toponimia|Etimología|Reseña histórica|Fundación).*?)(?=\n==[^=]|$)', txt, re.S | re.I)
        hist = hist_m.group(1)[:2500] if hist_m else ''
        res[t] = {'infobox': infobox, 'history': hist}
    return res

batch1 = [
  'Distrito de Capaya', 'Distrito de Santa Cruz de Andamarca', 'Distrito de Pisuquía', 'Zetaquira',
  'Distrito de Hongos', 'Distrito de Pampamarca (La Unión)', 'Valencia de Jesús', 'Manugasta',
  'Distrito de Congalla', 'Playa Unión', 'Puerto Caldas', 'Distrito de Cochapeti',
  'Cotahuasi', 'Distrito de Huangalá', 'Cantón San Pedro de Huaca', 'Distrito de Huancaya',
  'Distrito de Santiago de Tuna', 'Distrito de Chapimarca', 'Distrito de Huáñec', 'Villa Salavina',
  'General Daniel Cerri', 'Distrito de Leoncio Prado (Huaura)', 'Distrito de San Pedro de Huacarpana',
  'Distrito de Vitis', 'Pecaya', 'Distrito de Chipao', 'Malchinguí', 'Distrito de Ocoyo',
  'Freirina', 'Distrito de Huanza', 'Distrito de Juan Espinoza Medrano', 'Obrajillo',
  'Tupigachi', 'Distrito de Santiago de Chocorvos', 'Distrito de Ihuarí', 'Huamantanga',
  'Distrito de Andabamba (Acobamba)', 'Ticnamar', 'La Salina', 'Distrito de Pachaconas',
  'Distrito de Tapairihua', 'Distrito de Colonia', 'Distrito de Huanchay', 'Mariscal Sucre (Ecuador)',
  'Uyumbicho', 'Luis Cordero (Ecuador)', 'Distrito de Huántar', 'Distrito de Lares',
  'Río Caguán', 'Cartago (Colombia)'
]

batch2 = [
  'San Pedro de Huaca', 'Puracé (Cauca)', 'El Pedral', 'Rocafuerte (Esmeraldas)',
  'Ignacio Briceño', 'Juan Millán', 'El Hato (Falcón)', 'Parroquia Pecaya',
  'Parroquia El Hato', 'Parroquia Ignacio Briceño', 'Parroquia Juan Millán',
  'Parroquia Mariscal Sucre (Guayas)', 'Parroquia Uyumbicho', 'Parroquia Malchinguí',
  'Parroquia Tupigachi', 'Parroquia Luis Cordero', 'Parroquia Rocafuerte (Esmeraldas)',
  'San Juan de Talagá', 'Talagá', 'Santa Bárbara (Páez)', 'Caloto',
  'Distrito de Chota', 'Distrito de Pacaraos', 'Distrito de Carampoma',
  'Distrito de Cacra', 'Distrito de Quinches', 'Distrito de Antabamba',
  'Distrito de Canta', 'Distrito de Colca (Cotabambas)', 'Distrito de Colca (Huancayo)',
  'Salavina', 'Departamento Salavina', 'Huangalá', 'Vila Vila (Tacna)',
  'Distrito de Atavillos Bajo', 'Distrito de Yauyos', 'Distrito de Huaura',
  'San Vicente de Cañete', 'El Overo', 'Bugalagrande', 'Buga',
  'San Agustín de Huayopampa', 'Distrito de Santa Rosa de Quives',
  'Puerto Wilches', 'San Vicente del Caguán', 'Caguán (Neiva)'
]

all_res = {}
all_res.update(fetch_wikitext_batch(batch1))
time.sleep(1.2)
all_res.update(fetch_wikitext_batch(batch2))

with open('tests/wiki_full_020.json', 'w', encoding='utf-8') as f:
    json.dump(all_res, f, ensure_ascii=False, indent=2)
print('Saved wiki_full_020.json with', len(all_res), 'pages')
