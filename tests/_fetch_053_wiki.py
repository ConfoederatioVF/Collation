import json, time, urllib.request, urllib.parse, urllib.error

inp = json.load(open('tests/c053_input.json', encoding='utf-8'))
headers = {'User-Agent': 'SVEA-Toponymy-Research/1.0 (contact: research@example.org)'}

def api_get(lang, params):
    url = f'https://{lang}.wikipedia.org/w/api.php?' + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(3 * (attempt + 1))
            else:
                return {'error': str(e)}
        except Exception as e:
            time.sleep(1)
    return {'error': 'max_retries'}

def fetch_best(item):
    lat, lon = item['ll']
    n = item['n']
    c = item['c']
    # Geosearch on es.wikipedia first (10km radius)
    geo = api_get('es', {
        'action': 'query', 'list': 'geosearch',
        'gscoord': f'{lat}|{lon}', 'gsradius': 10000, 'gslimit': 5, 'format': 'json'
    })
    time.sleep(0.2)
    titles = [g['title'] for g in geo.get('query', {}).get('geosearch', [])]
    # Also text search on es.wikipedia
    sr = api_get('es', {
        'action': 'query', 'list': 'search',
        'srsearch': f'"{n}" {c}', 'srlimit': 3, 'format': 'json'
    })
    time.sleep(0.2)
    for s in sr.get('query', {}).get('search', []):
        if s['title'] not in titles:
            titles.append(s['title'])
    extracts = {}
    if titles:
        batch = titles[:4]
        ext = api_get('es', {
            'action': 'query', 'prop': 'extracts|coordinates',
            'exintro': 1, 'explaintext': 1, 'exchars': 1500,
            'titles': '|'.join(batch), 'format': 'json'
        })
        time.sleep(0.2)
        for pid, pdata in ext.get('query', {}).get('pages', {}).items():
            if int(pid) > 0:
                extracts[pdata['title']] = {
                    'coords': pdata.get('coordinates', []),
                    'extract': pdata.get('extract', '')
                }
    return {'geo_titles': [g['title'] for g in geo.get('query', {}).get('geosearch', [])], 'extracts': extracts}

out = {}
# Filter to non-generic archaeological sites + all colonial/modern
skip_pure_arch = {'Caja-Colombia', 'La Filomena-Colombia', 'Alto Checua-Colombia', 'Embarcadero-Colombia',
    'Playa Las Lisas-Argentina', 'Ruyrupata-Peru', 'Alero Sin designacion-Argentina', 'Shashatambo-Peru',
    'Panul-Chile', 'Muestreo RS-Colombia', 'Arajuno-Ecuador_2', 'Reconocimiento superficial-Colombia',
    'Machosillota o Pucara Sillocota-Peru', 'Cerro Pariaque-Peru', 'Apu Timan-Peru', 'Punta Entrada-Chile',
    'Carr-Colombia', 'La Esperanza-Peru_2', 'Jiguales-Colombia', 'Laguna Tromen-Co-Argentina',
    'Mocoa Piedmont-Colombia', 'Cerro Pueblo-Peru', 'Piedra Blancas-Colombia', 'Las Mulas-Argentina'}

for idx, item in enumerate(inp):
    k = item['key']
    if k in skip_pure_arch:
        continue
    out[k] = fetch_best(item)
    if len(out) % 10 == 0:
        print(f'Fetched {len(out)}...', flush=True)

json.dump(out, open('tests/_wiki_053_clean.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Done, total:', len(out))
