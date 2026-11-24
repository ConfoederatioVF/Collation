import json, time, urllib.request, urllib.parse
from fetch_wiki_info import INPUT_DATA

HEADERS = {'User-Agent': 'OperationViscountResearch/1.0 (https://example.org; mailto:research@example.org)'}

def fetch_json(url):
  for attempt in range(4):
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
      if e.code == 429:
        time.sleep(2.0 * (attempt + 1))
      else:
        raise
  raise RuntimeError("429 retries exhausted")

results = []
for i, item in enumerate(INPUT_DATA):
  key = item['key']
  name = item['n']
  country = item['c']
  lat, lon = item['ll']
  res = {'key': key, 'wiki_geo': [], 'wiki_search': []}
  # Only do geosearch + search politely with 0.35s sleep
  try:
    geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=3&format=json"
    geo_data = fetch_json(geo_url)
    for g in geo_data.get('query', {}).get('geosearch', []):
      res['wiki_geo'].append({'title': g['title'], 'dist': g['dist']})
  except Exception as e:
    res['geo_err'] = str(e)
  time.sleep(0.25)

  try:
    q = urllib.parse.quote(f"{name} {country}")
    s_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=2&format=json"
    s_data = fetch_json(s_url)
    titles = [x['title'] for x in s_data.get('query', {}).get('search', [])]
    if res['wiki_geo']:
      titles = list(dict.fromkeys([g['title'] for g in res['wiki_geo'][:2]] + titles[:1]))
    if titles:
      t_param = urllib.parse.quote('|'.join(titles))
      ex_url = f"https://es.wikipedia.org/w/api.php?action=query&titles={t_param}&prop=extracts&explaintext=1&exchars=1500&format=json"
      time.sleep(0.25)
      ex_data = fetch_json(ex_url)
      for pid, pinfo in ex_data.get('query', {}).get('pages', {}).items():
        if int(pid) > 0:
          res['wiki_search'].append({
            'title': pinfo.get('title'),
            'extract': pinfo.get('extract', '')[:1200]
          })
  except Exception as e:
    res['search_err'] = str(e)
  time.sleep(0.25)
  results.append(res)

with open('tests/chunk040_wiki.json', 'w', encoding='utf-8') as f:
  json.dump(results, f, ensure_ascii=False, indent=2)
print(f"Done: {len(results)}")
