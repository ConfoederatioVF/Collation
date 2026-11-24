import json, urllib.request, urllib.parse, time

with open('tests/tmp_wiki_028.py', 'r', encoding='utf-8') as f:
  src = f.read()

# Extract ITEMS
ns = {}
exec(src.split('def wiki_get')[0], ns)
ITEMS = ns['ITEMS']

HEADERS = {'User-Agent': 'ViscountHistoricalToponymy/1.0 (https://confoederatio.org; contact@confoederatio.org)'}

def wiki_get(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=15) as r:
    return json.loads(r.read().decode('utf-8'))

out = []
for idx, item in enumerate(ITEMS):
  lat, lng = item['ll']
  res = {'key': item['key'], 'n': item['n'], 'c': item['c'], 'r': item['r'], 'll': item['ll'], 'ey': item['ey'], 'ly': item['ly'], 'al': item.get('al', [])}
  try:
    geo = wiki_get(f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=3&format=json")
    hits = geo.get('query', {}).get('geosearch', [])
    res['es_geo'] = [h['title'] + f" ({h['dist']}m)" for h in hits]
    time.sleep(0.2)
    q = urllib.parse.quote(f"{item['n']} {item['c']}")
    sr = wiki_get(f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=2&format=json")
    shits = sr.get('query', {}).get('search', [])
    res['es_search'] = [h['title'] for h in shits]
    titles = []
    if hits: titles.append(hits[0]['title'])
    if shits and shits[0]['title'] not in titles: titles.append(shits[0]['title'])
    if titles:
      time.sleep(0.2)
      tparam = urllib.parse.quote("|".join(titles))
      ext = wiki_get(f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={tparam}&format=json")
      res['extracts'] = {}
      for p in ext.get('query', {}).get('pages', {}).values():
        res['extracts'][p.get('title','')] = p.get('extract', '')[:800]
  except Exception as e:
    res['err'] = str(e)
  out.append(res)
  time.sleep(0.25)

with open('tests/tmp_wiki_028.json', 'w', encoding='utf-8') as f:
  json.dump(out, f, ensure_ascii=False, indent=2)
print("Done polite:", len(out))
