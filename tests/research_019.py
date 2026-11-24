import json
import urllib.parse
import urllib.request

HEADERS = {'User-Agent': 'ResearchBot/1.0 (mailto:research@confoederatio.org)'}


def fetch_json(arg0_url):
  req = urllib.request.Request(arg0_url, headers=HEADERS)
  try:
    with urllib.request.urlopen(req, timeout=8) as r:
      return json.loads(r.read().decode('utf-8'))
  except Exception as e:
    return {'_error': str(e)}


def wiki_geo(arg0_lang, arg1_lat, arg2_lng, arg3_radius=10000):
  url = (
    f'https://{arg0_lang}.wikipedia.org/w/api.php?action=query&list=geosearch'
    f'&gscoord={arg1_lat}|{arg2_lng}&gsradius={arg3_radius}&gslimit=5&format=json'
  )
  data = fetch_json(url)
  return data.get('query', {}).get('geosearch', [])


def wiki_search(arg0_lang, arg1_query):
  q = urllib.parse.quote(arg1_query)
  url = (
    f'https://{arg0_lang}.wikipedia.org/w/api.php?action=query&list=search'
    f'&srsearch={q}&srlimit=3&format=json'
  )
  data = fetch_json(url)
  return data.get('query', {}).get('search', [])


def wiki_extracts(arg0_lang, arg1_titles):
  if not arg1_titles:
    return {}
  titles = urllib.parse.quote('|'.join(arg1_titles[:6]))
  url = (
    f'https://{arg0_lang}.wikipedia.org/w/api.php?action=query&titles={titles}'
    f'&prop=extracts|coordinates&exintro=0&explaintext=1&exchars=2200&format=json'
  )
  data = fetch_json(url)
  pages = data.get('query', {}).get('pages', {})
  out = {}
  for p in pages.values():
    if 'title' in p and 'missing' not in p:
      out[p['title']] = {
        'extract': p.get('extract', ''),
        'coords': p.get('coordinates', [])
      }
  return out


with open('tests/chunk_019_input.json', encoding='utf-8') as f:
  settlements = json.load(f)

with open('tests/toponymy_batches/quipu_approved_cache.json', encoding='utf-8') as f:
  cache = json.load(f)

results = []
for idx, s in enumerate(settlements):
  lat, lng = s['ll']
  geo_es = wiki_geo('es', lat, lng, 10000)
  geo_titles = [g['title'] for g in geo_es[:3]]
  sr_es = wiki_search('es', f"{s['n']} {s['c']}")
  sr_titles = [x['title'] for x in sr_es[:2]]
  all_titles = list(dict.fromkeys(geo_titles + sr_titles))
  extracts = wiki_extracts('es', all_titles[:4])

  cache_hits = {}
  if s.get('ex'):
    for ex_item in s['ex']:
      for ck, cv in cache.items():
        if cv.get('canonical_name') == ex_item['name'] or ck.startswith(ex_item['name'] + '-'):
          cache_hits[ck] = cv

  results.append({
    'idx': idx,
    'key': s['key'],
    'n': s['n'],
    'c': s['c'],
    'r': s['r'],
    'll': s['ll'],
    'ey': s['ey'],
    'ly': s['ly'],
    'al': s.get('al', []),
    'ex': s.get('ex', []),
    'geo_es': [{'title': g['title'], 'dist': g['dist']} for g in geo_es[:3]],
    'sr_es': sr_titles,
    'extracts': extracts,
    'cache_hits': cache_hits,
  })
  if idx % 15 == 14:
    print(f'Processed {idx+1}/90', flush=True)

with open('tests/chunk_019_research.json', 'w', encoding='utf-8') as f:
  json.dump(results, f, ensure_ascii=False, indent=2)

print('Done! Saved tests/chunk_019_research.json')
