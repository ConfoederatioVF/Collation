import json
import time
import urllib.parse
import urllib.request

# Import INPUT from research_chunk030.py
with open('f:/Active Projects/Project 1509 - SVEA/tests/research_chunk030.py', 'r', encoding='utf-8') as f:
  code = f.read().split('HEADERS =')[0]
ns = {}
exec(code, ns)
INPUT = ns['INPUT']

HEADERS = {'User-Agent': 'SVEA-Toponymy-Research/1.0 (https://confoederatio.org; research@confoederatio.org)'}

def fetch_json(url, data=None):
  req = urllib.request.Request(url, data=data, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=30) as resp:
    return json.loads(resp.read().decode('utf-8'))

# 1. Query Wikidata SPARQL using wikibase:around in batches of 10
wd_hits = {it['key']: [] for it in INPUT}
for b in range(0, len(INPUT), 10):
  batch = INPUT[b:b+10]
  blocks = []
  for idx, it in enumerate(batch):
    lat, lon = it['ll']
    key_esc = it['key'].replace('"', '\\"')
    blocks.append(f'''
    {{
      BIND("{key_esc}" AS ?inputKey)
      SERVICE wikibase:around {{
        ?item wdt:P625 ?loc .
        bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral .
        bd:serviceParam wikibase:radius "8" .
        bd:serviceParam wikibase:distance ?dist .
      }}
    }}''')
  query = f'''
  SELECT ?inputKey ?item ?itemLabel ?itemDescription ?inception ?eswiki ?enwiki ?dist WHERE {{
    {" UNION ".join(blocks)}
    OPTIONAL {{ ?item wdt:P571 ?inception . }}
    OPTIONAL {{ ?eswiki schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> . }}
    OPTIONAL {{ ?enwiki schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }}
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . }}
  }}
  '''
  try:
    url = "https://query.wikidata.org/sparql"
    body = urllib.parse.urlencode({'query': query, 'format': 'json'}).encode('utf-8')
    res = fetch_json(url, data=body)
    for row in res.get('results', {}).get('bindings', []):
      k = row['inputKey']['value']
      wd_hits[k].append({
        'qid': row['item']['value'].split('/')[-1],
        'label': row.get('itemLabel', {}).get('value', ''),
        'desc': row.get('itemDescription', {}).get('value', ''),
        'inception': row.get('inception', {}).get('value', ''),
        'eswiki': urllib.parse.unquote(row['eswiki']['value'].split('/wiki/')[-1]) if 'eswiki' in row else '',
        'enwiki': urllib.parse.unquote(row['enwiki']['value'].split('/wiki/')[-1]) if 'enwiki' in row else '',
        'dist': float(row.get('dist', {}).get('value', 999))
      })
  except Exception as e:
    print(f"Batch {b} SPARQL error: {e}")
  time.sleep(0.5)

# Deduplicate and sort by distance + name match
for k, hits in wd_hits.items():
  by_q = {}
  for h in hits:
    q = h['qid']
    if q not in by_q:
      by_q[q] = h
  wd_hits[k] = sorted(by_q.values(), key=lambda x: x['dist'])[:5]

# Collect all eswiki titles to fetch in batches of 30 (sequential, polite)
titles_to_fetch = []
for k, hits in wd_hits.items():
  for h in hits:
    if h['eswiki'] and h['eswiki'] not in titles_to_fetch:
      titles_to_fetch.append(h['eswiki'])

# Also add direct clean names for items with no eswiki hit yet
for it in INPUT:
  if not any(h['eswiki'] for h in wd_hits[it['key']]):
    if it['n'] not in titles_to_fetch:
      titles_to_fetch.append(it['n'])

wiki_articles = {}
for b in range(0, len(titles_to_fetch), 25):
  batch_t = titles_to_fetch[b:b+25]
  t_str = urllib.parse.quote('|'.join(batch_t))
  url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|revisions&exintro=1&explaintext=1&rvprop=content&redirects=1&titles={t_str}&format=json"
  try:
    data = fetch_json(url)
    pages = data.get('query', {}).get('pages', {})
    for pid, p in pages.items():
      if int(pid) < 0:
        continue
      title = p.get('title', '')
      extract = p.get('extract', '')[:1500]
      wt = ''
      revs = p.get('revisions', [])
      if revs:
        txt = revs[0].get('*', '')
        # grab infobox + historia section snippet
        lines = []
        for line in txt.splitlines()[:100]:
          if any(w in line.lower() for w in ['fundaci', 'creaci', 'nombre', 'fecha', 'erecci', 'antiguo', 'otros_nombres', 'historia', 'pueblo', 'municipio', 'distrito', 'parroquia', 'localidad', 'departamento', 'provincia', 'cantón', 'región']):
            lines.append(line.strip())
        # also find == Historia ==
        hist_idx = txt.lower().find('historia')
        hist_snip = ''
        if hist_idx != -1:
          hist_snip = txt[hist_idx:hist_idx+1200].replace('\n', ' ')
        wt = ' | '.join(lines[:15]) + ('\nHIST: ' + hist_snip if hist_snip else '')
      wiki_articles[title] = {'extract': extract, 'wt': wt}
  except Exception as e:
    print(f"Wiki batch {b} error: {e}")
  time.sleep(0.5)

out = {'wd': wd_hits, 'wiki': wiki_articles}
with open('f:/Active Projects/Project 1509 - SVEA/tests/chunk030_wd_wiki.json', 'w', encoding='utf-8') as f:
  json.dump(out, f, ensure_ascii=False, indent=2)

print(f"Done! WD items with hits: {sum(1 for v in wd_hits.values() if v)}, Wiki articles: {len(wiki_articles)}")
