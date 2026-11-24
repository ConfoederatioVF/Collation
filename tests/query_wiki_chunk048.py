import json, urllib.request, urllib.parse, time

with open('tests/chunk048_input.json', 'r', encoding='utf-8') as f:
  items = json.load(f)

HEADERS = {'User-Agent': 'AntigravityBot/1.0 (https://confoederatio.org; research@confoederatio.org)'}

def fetch_json(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=15) as r:
    return json.loads(r.read().decode('utf-8'))

# 1. Batch Wikidata SPARQL query by coordinates (in batches of 30)
wd_results = {}
for i in range(0, len(items), 30):
  batch = items[i:i+30]
  values = " ".join(f'("{it["key"]}" "Point({it["ll"][1]} {it["ll"][0]})"^^geo:wktLiteral)' for it in batch)
  query = f"""
  SELECT ?k ?item ?itemLabel ?esTitle ?enTitle ?inception ?dist WHERE {{
    VALUES (?k ?pt) {{ {values} }}
    SERVICE wikibase:around {{
      ?item wdt:P625 ?loc .
      bd:serviceParam wikibase:center ?pt .
      bd:serviceParam wikibase:radius "5" .
      bd:serviceParam wikibase:distance ?dist .
    }}
    OPTIONAL {{ ?item wdt:P571 ?inception . }}
    OPTIONAL {{ ?esArticle schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> ; schema:name ?esTitle . }}
    OPTIONAL {{ ?enArticle schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?enTitle . }}
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
  }}
  """
  url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(query)
  try:
    res = fetch_json(url)
    for b in res.get('results', {}).get('bindings', []):
      k = b['k']['value']
      wd_results.setdefault(k, []).append({
        'qid': b['item']['value'].split('/')[-1],
        'label': b.get('itemLabel', {}).get('value'),
        'esTitle': b.get('esTitle', {}).get('value'),
        'enTitle': b.get('enTitle', {}).get('value'),
        'inception': b.get('inception', {}).get('value'),
        'dist_km': float(b.get('dist', {}).get('value', 99))
      })
  except Exception as e:
    print("SPARQL err batch", i, e)
  time.sleep(0.5)

# Sort each by dist_km
for k in wd_results:
  wd_results[k].sort(key=lambda x: x['dist_km'])

# 2. Fetch es.wikipedia extracts for top matched esTitle (or search for modern/colonial items with no esTitle)
titles_to_fetch = set()
for it in items:
  k = it['key']
  matches = wd_results.get(k, [])
  for m in matches[:2]:
    if m.get('esTitle'):
      titles_to_fetch.add(m['esTitle'])

wiki_extracts = {}
title_list = list(titles_to_fetch)
for i in range(0, len(title_list), 20):
  sub = title_list[i:i+20]
  url = "https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&redirects=1&format=json&titles=" + urllib.parse.quote("|".join(sub))
  try:
    res = fetch_json(url)
    for pid, page in res.get('query', {}).get('pages', {}).items():
      if 'title' in page and 'extract' in page:
        wiki_extracts[page['title']] = page['extract'][:1000]
  except Exception as e:
    print("Wiki batch err", i, e)
  time.sleep(0.3)

with open('tests/chunk048_wiki.json', 'w', encoding='utf-8') as f:
  json.dump({'wikidata': wd_results, 'extracts': wiki_extracts}, f, ensure_ascii=False, indent=2)

print("Wikidata keys matched:", len(wd_results), "Extracts fetched:", len(wiki_extracts))
