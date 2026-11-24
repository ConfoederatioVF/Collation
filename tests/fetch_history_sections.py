import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

with open('tests/chunk030_wiki.json', 'r', encoding='utf-8') as f:
  DATA = json.load(f)

HEADERS = {'User-Agent': 'OperationViscountToponymy/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)'}

def fetch_json(url, retries=4):
  for attempt in range(retries):
    time.sleep(1.1)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
      with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
      if e.code == 429:
        wait = int(e.headers.get('Retry-After', 5)) + attempt * 2
        print(f"429 hit, sleeping {wait}s...")
        time.sleep(wait)
      else:
        raise
  raise RuntimeError(f"Failed after {retries} retries: {url}")

# First fix the 3 missing geo_es/sr_es
for it in DATA:
  if 'geo_es_err' in it or 'sr_es_err' in it:
    lat, lng = it['ll']
    it.pop('geo_es_err', None)
    it.pop('sr_es_err', None)
    geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
    geo = fetch_json(geo_url).get('query', {}).get('geosearch', [])
    it['geo_es'] = [(g['title'], round(g['dist'])) for g in geo]
    q = urllib.parse.quote(f"{it['n']} {it['c']}")
    sr_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
    sr = fetch_json(sr_url).get('query', {}).get('search', [])
    it['sr_es'] = [s['title'] for s in sr]

with open('tests/chunk030_wiki.json', 'w', encoding='utf-8') as f:
  json.dump(DATA, f, ensure_ascii=False, indent=2)

# Pick candidate titles
def pick_titles(item):
  n_low = item['n'].lower()
  cands = []
  for t, d in item.get('geo_es', []):
    if d <= 5000 or n_low in t.lower() or any(w in t.lower() for w in n_low.split() if len(w) > 3):
      cands.append(t)
  for t in item.get('sr_es', []):
    if n_low in t.lower() or any(w in t.lower() for w in n_low.split() if len(w) > 3):
      if t not in cands:
        cands.append(t)
  return cands[:2]

all_titles = []
item_titles = {}
for it in DATA:
  ts = pick_titles(it)
  item_titles[it['key']] = ts
  for t in ts:
    if t not in all_titles:
      all_titles.append(t)

print(f"Fetching wikitext/history for {len(all_titles)} unique titles in batches of 20...")
page_info = {}
for i in range(0, len(all_titles), 20):
  batch = all_titles[i:i+20]
  ts = urllib.parse.quote('|'.join(batch))
  url = f"https://es.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&rvslots=main&titles={ts}&format=json"
  pages = fetch_json(url).get('query', {}).get('pages', {})
  for pid, pdata in pages.items():
    title = pdata.get('title', '')
    revs = pdata.get('revisions', [])
    if not revs:
      continue
    wikitext = revs[0].get('slots', {}).get('main', {}).get('*', '')
    lines = wikitext.splitlines()
    infobox_hits = []
    for ln in lines[:140]:
      if any(k in ln.lower() for k in ['fundac', 'creac', 'erecc', 'nombre', 'antiguo', 'otros_nombres', 'fecha', 'etimo', 'establec', 'patrono', 'topon']):
        infobox_hits.append(ln.strip())
    sec_text = []
    in_sec = False
    for ln in lines:
      if re.match(r'^==+\s*(historia|toponimia|etimolog|origen|fundaci|reseña hist|antecedentes)', ln, re.I):
        in_sec = True
        sec_text.append(ln)
        continue
      elif re.match(r'^==[^=]', ln) and in_sec:
        in_sec = False
      elif in_sec:
        sec_text.append(ln)
    # Also grab first 500 chars of intro
    intro = '\n'.join([l for l in lines if not l.startswith('|') and not l.startswith('{{') and not l.startswith('}}') and not l.startswith('[[Categor')][:15])[:600]
    page_info[title] = {
      'infobox': infobox_hits[:15],
      'intro': intro,
      'history': '\n'.join(sec_text)[:2500]
    }

out = []
for it in DATA:
  entry = {'key': it['key'], 'n': it['n'], 'c': it['c'], 'r': it['r'], 'll': it['ll'], 'ey': it['ey'], 'ly': it['ly']}
  if 'ex' in it: entry['ex'] = it['ex']
  if 'al' in it: entry['al'] = it['al']
  entry['geo_es'] = it.get('geo_es', [])
  entry['sr_es'] = it.get('sr_es', [])
  entry['pages'] = {t: page_info[t] for t in item_titles[it['key']] if t in page_info}
  out.append(entry)

with open('tests/chunk030_history.json', 'w', encoding='utf-8') as f:
  json.dump(out, f, ensure_ascii=False, indent=2)
print("Saved tests/chunk030_history.json successfully")
