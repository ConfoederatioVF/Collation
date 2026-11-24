import json
import time
import urllib.parse
import urllib.request

with open('tests/chunk030_wiki.json', 'r', encoding='utf-8') as f:
  DATA = json.load(f)

HEADERS = {'User-Agent': 'OperationViscountResearch/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)'}

def fetch_json(url):
  time.sleep(0.18)
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=20) as r:
    return json.loads(r.read().decode('utf-8'))

for item in DATA:
  need_geo = 'geo_es_err' in item
  need_sr = 'sr_es_err' in item
  need_ex = 'ex_err' in item or (not item.get('extracts') and (item.get('geo_es') or item.get('sr_es')))
  lat, lng = item['ll']
  name = item['n']
  country = item['c']

  if need_geo:
    item.pop('geo_es_err', None)
    try:
      geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
      geo = fetch_json(geo_url).get('query', {}).get('geosearch', [])
      item['geo_es'] = [(g['title'], round(g['dist'])) for g in geo]
    except Exception as e:
      item['geo_es_err'] = str(e)

  if need_sr:
    item.pop('sr_es_err', None)
    try:
      q = urllib.parse.quote(f"{name} {country}")
      sr_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
      sr = fetch_json(sr_url).get('query', {}).get('search', [])
      item['sr_es'] = [s['title'] for s in sr]
    except Exception as e:
      item['sr_es_err'] = str(e)

  if need_ex or 'ex_err' in item:
    item.pop('ex_err', None)
    titles = []
    for t, d in item.get('geo_es', [])[:2]:
      if t not in titles:
        titles.append(t)
    for t in item.get('sr_es', [])[:2]:
      if t not in titles:
        titles.append(t)
    if titles:
      try:
        ts = urllib.parse.quote('|'.join(titles[:3]))
        ex_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=false&explaintext=true&exchars=3500&titles={ts}&format=json"
        pages = fetch_json(ex_url).get('query', {}).get('pages', {})
        extracts = item.get('extracts', {})
        for pid, pdata in pages.items():
          if 'extract' in pdata:
            extracts[pdata['title']] = pdata['extract'][:2500]
        item['extracts'] = extracts
      except Exception as e:
        item['ex_err'] = str(e)

with open('tests/chunk030_wiki.json', 'w', encoding='utf-8') as f:
  json.dump(DATA, f, ensure_ascii=False, indent=2)
print("Completed retry pass.")
