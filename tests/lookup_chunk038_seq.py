import json
import time
import urllib.parse
import urllib.request

with open('tests/lookup_chunk038.py', 'r', encoding='utf-8') as f:
  src = f.read()

# Extract SETTLEMENTS from existing script
ns = {}
exec(src.split('HEADERS =')[0], ns)
SETTLEMENTS = ns['SETTLEMENTS']

HEADERS = {'User-Agent': 'ViscountToponymyAudit/1.0 (https://confoederatio.org; research@confoederatio.org)'}

def wiki_get(lang, params):
  url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
  for attempt in range(4):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
      with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
      if e.code == 429:
        time.sleep(2.0 * (attempt + 1))
        continue
      raise
  raise RuntimeError("429 retries exhausted")

# First do search+geosearch sequentially with small delay, or skip geosearch if search finds it
results = []
for idx, s in enumerate(SETTLEMENTS):
  key = s['key']
  lat, lon = s['ll']
  res = {'key': key, 'n': s['n'], 'c': s['c'], 'r': s['r'], 'll': s['ll'], 'ey': s['ey'], 'ly': s['ly']}
  try:
    geo = wiki_get('es', {'action': 'query', 'list': 'geosearch', 'gscoord': f'{lat}|{lon}', 'gsradius': 8000, 'gslimit': 3, 'format': 'json'})
    res['geo_es'] = [g['title'] for g in geo.get('query', {}).get('geosearch', [])]
  except Exception as e:
    res['geo_es_err'] = str(e)
  time.sleep(0.12)
  try:
    sr = wiki_get('es', {'action': 'query', 'list': 'search', 'srsearch': f'"{s["n"]}" {s["c"]}', 'srlimit': 2, 'format': 'json'})
    res['search_es'] = [x['title'] for x in sr.get('query', {}).get('search', [])]
  except Exception as e:
    res['search_es_err'] = str(e)
  time.sleep(0.12)
  results.append(res)

# Batch fetch extracts in groups of 20 titles
all_titles = []
for r in results:
  for t in r.get('geo_es', [])[:2] + r.get('search_es', [])[:2]:
    if t not in all_titles:
      all_titles.append(t)

extracts = {}
for i in range(0, len(all_titles), 20):
  batch = all_titles[i:i+20]
  try:
    ex = wiki_get('es', {'action': 'query', 'prop': 'extracts', 'exintro': 1, 'explaintext': 1, 'titles': '|'.join(batch), 'format': 'json'})
    for p in ex.get('query', {}).get('pages', {}).values():
      if 'title' in p and 'extract' in p:
        extracts[p['title']] = p['extract'][:1500]
  except Exception as e:
    print("Batch error:", e)
  time.sleep(0.2)

for r in results:
  r['extracts'] = {}
  for t in r.get('geo_es', [])[:2] + r.get('search_es', [])[:2]:
    if t in extracts:
      r['extracts'][t] = extracts[t]

with open('tests/wiki_results.json', 'w', encoding='utf-8') as f:
  json.dump(results, f, ensure_ascii=False, indent=2)
print(f"Done {len(results)}, extracts: {len(extracts)}")
