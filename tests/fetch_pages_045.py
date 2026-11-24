import json
import urllib.parse
import urllib.request
import time

with open(r'f:\Active Projects\Project 1509 - SVEA\tests\settlements_045.json', encoding='utf-8') as f:
    SETTLEMENTS = json.load(f)
with open(r'f:\Active Projects\Project 1509 - SVEA\tests\chunk045_wd.json', encoding='utf-8') as f:
    WD = json.load(f)

HEADERS = {'User-Agent': 'OperationViscountBot/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)'}

def api_get(lang, params):
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))

# Match best WD item per settlement
matched = {}
unmatched = []
for s in SETTLEMENTS:
    k = s['key']
    n = s['n'].lower()
    rows = WD.get(k, [])
    best = []
    for r in rows:
        lbl = (r.get('label') or '').lower()
        desc = (r.get('desc') or '').lower()
        # Keep items with matching name or settlement/arch description or wikipedia article
        if n in lbl or any(a.lower() in lbl for a in s.get('al', [])):
            best.append(r)
    if not best:
        # keep any row with an es/en wikipedia article and non-trivial description
        for r in rows:
            if r.get('es') or r.get('en'):
                best.append(r)
    matched[k] = best
    if not best:
        unmatched.append(s)

print(f"WD matched: {90 - len(unmatched)}/90, unmatched: {len(unmatched)}")

# Collect unique es.wikipedia and en.wikipedia titles
es_titles = set()
en_titles = set()
for k, rows in matched.items():
    for r in rows[:3]:
        if r.get('es'):
            t = urllib.parse.unquote(r['es'].split('/wiki/')[-1]).replace('_', ' ')
            es_titles.add(t)
        if r.get('en'):
            t = urllib.parse.unquote(r['en'].split('/wiki/')[-1]).replace('_', ' ')
            en_titles.add(t)

print(f"Unique es titles: {len(es_titles)}, en titles: {len(en_titles)}")

def fetch_batch(lang, titles_list):
    out = {}
    for i in range(0, len(titles_list), 20):
        chunk = titles_list[i:i+20]
        try:
            data = api_get(lang, {
                'action': 'query',
                'titles': '|'.join(chunk),
                'prop': 'extracts',
                'exintro': 'false',
                'explaintext': 'true',
                'exchars': '5000',
                'exlimit': '20',
                'format': 'json',
                'redirects': '1'
            })
            for pid, p in data.get('query', {}).get('pages', {}).items():
                if pid != '-1':
                    out[p['title']] = p.get('extract', '')
        except Exception as e:
            print(f"Err {lang} batch {i}: {e}", flush=True)
        time.sleep(0.5)
    return out

es_pages = fetch_batch('es', sorted(es_titles))
en_pages = fetch_batch('en', sorted(en_titles))

with open(r'f:\Active Projects\Project 1509 - SVEA\tests\chunk045_pages.json', 'w', encoding='utf-8') as f:
    json.dump({'matched': matched, 'es_pages': es_pages, 'en_pages': en_pages}, f, ensure_ascii=False, indent=2)
print("Saved pages:", len(es_pages), len(en_pages))
