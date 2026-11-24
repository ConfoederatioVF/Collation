import json, glob, os, urllib.request, urllib.parse, time

items = json.load(open('tests/chunk034_input.json', encoding='utf-8'))
keys = {x['key']: x for x in items}

# 1. Inspect local QUIPU settlement files
local_hits = {k: [] for k in keys}
files = glob.glob('histmap/1.data_raw/population_regional/QUIPU/**/*_settlements.json', recursive=True) + \
        glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json', recursive=True)

for fp in files:
    try:
        d = json.load(open(fp, encoding='utf-8'))
        if isinstance(d, dict) and 'settlements' in d and isinstance(d['settlements'], dict):
            d = d['settlements']
        if isinstance(d, dict):
            for k in keys:
                if k in d:
                    rec = d[k]
                    slim = {kk: vv for kk, vv in rec.items() if kk != 'population'}
                    local_hits[k].append((os.path.basename(fp), slim))
    except Exception as e:
        pass

# Also check sites_quipu_andes_cone CSV/JSON if any
for fp in glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/*'):
    if fp.endswith('.json') or fp.endswith('.geojson'):
        try:
            txt = open(fp, encoding='utf-8', errors='ignore').read()
            for x in items:
                if x['n'] in txt:
                    pass
        except Exception:
            pass

# 2. Query Wikidata geosearch + wbgetentities
def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'SVEA-Research/1.0 (viscount)'})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode('utf-8'))

wd_results = {}
qids_to_fetch = {}
for x in items:
    lat, lng = x['ll']
    url = f"https://www.wikidata.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
    try:
        res = fetch_json(url)
        hits = res.get('query', {}).get('geosearch', [])
        wd_results[x['key']] = hits
        for h in hits:
            qids_to_fetch[h['title']] = True
    except Exception as e:
        wd_results[x['key']] = {'error': str(e)}
    time.sleep(0.05)

all_qids = list(qids_to_fetch.keys())
entities = {}
for i in range(0, len(all_qids), 50):
    batch = '|'.join(all_qids[i:i+50])
    url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={batch}&props=labels|descriptions|claims|sitelinks&languages=es|en&format=json"
    try:
        res = fetch_json(url)
        entities.update(res.get('entities', {}))
    except Exception as e:
        print('wbgetentities err:', e)
    time.sleep(0.1)

out = {}
for x in items:
    k = x['key']
    cands = []
    hits = wd_results.get(k, [])
    if isinstance(hits, list):
        for h in hits:
            qid = h['title']
            ent = entities.get(qid, {})
            lbl_es = ent.get('labels', {}).get('es', {}).get('value', '')
            lbl_en = ent.get('labels', {}).get('en', {}).get('value', '')
            desc_es = ent.get('descriptions', {}).get('es', {}).get('value', '')
            desc_en = ent.get('descriptions', {}).get('en', {}).get('value', '')
            claims = ent.get('claims', {})
            p571 = []
            for c in claims.get('P571', []):
                v = c.get('mainsnak', {}).get('datavalue', {}).get('value', {})
                if isinstance(v, dict) and 'time' in v:
                    p571.append(v['time'])
            p1448 = []
            for c in claims.get('P1448', []):
                v = c.get('mainsnak', {}).get('datavalue', {}).get('value', {})
                if isinstance(v, dict) and 'text' in v:
                    p1448.append(v['text'])
            eswiki = ent.get('sitelinks', {}).get('eswiki', {}).get('title', '')
            enwiki = ent.get('sitelinks', {}).get('enwiki', {}).get('title', '')
            cands.append({
                'qid': qid, 'dist_m': h['dist'],
                'lbl': lbl_es or lbl_en, 'desc': desc_es or desc_en,
                'P571': p571, 'P1448': p1448,
                'eswiki': eswiki, 'enwiki': enwiki
            })
    out[k] = {
        'input': x,
        'local': local_hits[k],
        'wd': cands
    }

json.dump(out, open('tests/chunk034_dossier.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('Wrote tests/chunk034_dossier.json for', len(out), 'settlements')
