import json
import time
import urllib.request
import urllib.parse
import re

HEADERS = {'User-Agent': 'SVEA-Toponymy/1.0 (https://confoederatio.org; research@confoederatio.org)'}

def api_get(lang, params):
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if '429' in str(e) or '503' in str(e):
                time.sleep(1.5 * (attempt + 1))
            else:
                raise
    return {}

def clean_wikitext(text):
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.S)
    text = re.sub(r'<ref[^/>]*/?>', '', text)
    return text

with open('tests/wiki_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

updated = 0
for idx, res in enumerate(results):
    if not res.get('geo_err') and not res.get('sr_err') and (res.get('geo') or res.get('search')):
        continue
    lat, lng = res['ll']
    n = res['n']
    c = res['c']
    res.pop('geo_err', None)
    res.pop('sr_err', None)
    res.pop('pg_err', None)

    try:
        gs = api_get('es', {
            'action': 'query', 'list': 'geosearch',
            'gscoord': f'{lat}|{lng}', 'gsradius': 10000, 'gslimit': 5, 'format': 'json'
        })
        res['geo'] = gs.get('query', {}).get('geosearch', [])
    except Exception as e:
        res['geo_err'] = str(e)

    try:
        sr = api_get('es', {
            'action': 'query', 'list': 'search',
            'srsearch': f'"{n}" {c}', 'srlimit': 3, 'format': 'json'
        })
        res['search'] = [x['title'] for x in sr.get('query', {}).get('search', [])]
    except Exception as e:
        res['sr_err'] = str(e)

    titles = []
    for g in res['geo'][:2]:
        if g['title'] not in titles:
            titles.append(g['title'])
    for t in res['search'][:2]:
        if t not in titles:
            titles.append(t)

    res['pages'] = {}
    if titles:
        try:
            pg = api_get('es', {
                'action': 'query', 'prop': 'revisions', 'rvprop': 'content',
                'rvslots': 'main', 'titles': '|'.join(titles[:3]), 'format': 'json', 'redirects': 1
            })
            pages = pg.get('query', {}).get('pages', {})
            for pid, pdata in pages.items():
                if 'revisions' in pdata:
                    content = clean_wikitext(pdata['revisions'][0]['slots']['main']['*'])
                    snippet = content[:2500]
                    hist_txt = ''
                    for m in re.finditer(r'(==+\s*(?:Historia|Toponimia|Etimolog[ií]a|Antecedentes|Fundaci[oó]n|Creaci[oó]n|Or[ií]genes|Rese[ñn]a hist[oó]rica)[^=]*==+.*?(?=\n==[^=]|\Z))', content, flags=re.S|re.I):
                        hist_txt += '\n' + m.group(1)[:2500]
                    res['pages'][pdata['title']] = {
                        'lead': snippet,
                        'hist': hist_txt[:4000]
                    }
        except Exception as e:
            res['pg_err'] = str(e)
    updated += 1
    time.sleep(0.15)

with open('tests/wiki_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Updated {updated} items")
