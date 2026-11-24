import json
import urllib.request
import urllib.parse
import concurrent.futures
import math

HEADERS = {'User-Agent': 'HistoricalToponymyResearch/1.0 (https://example.org)'}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode('utf-8'))

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

data = json.load(open("tests/quipu_results.json", encoding="utf-8"))

def process(d):
    lat, lng = d['ll']
    out = {
        'key': d['key'],
        'n': d['n'],
        'c': d['c'],
        'r': d['r'],
        'll': d['ll'],
        'ey': d['ey'],
        'ly': d['ly'],
        'geo': d.get('geo', []),
        'sr': d.get('sr', []),
        'articles': []
    }
    # Gather candidate titles from geo (all) and sr (top 3)
    cand_titles = []
    for g in d.get('geo', []):
        if g['title'] not in cand_titles:
            cand_titles.append(g['title'])
    for s in d.get('sr', []):
        if s not in cand_titles:
            cand_titles.append(s)
    if cand_titles:
        try:
            t_param = urllib.parse.quote('|'.join(cand_titles[:5]))
            url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=1&exchars=4000&titles={t_param}&format=json"
            pages = fetch_json(url).get('query', {}).get('pages', {})
            for pid, p in pages.items():
                if 'missing' in p:
                    continue
                coords = p.get('coordinates', [])
                dist_km = None
                if coords:
                    dist_km = round(haversine(lat, lng, coords[0]['lat'], coords[0]['lon']), 2)
                out['articles'].append({
                    'lang': 'es',
                    'title': p.get('title'),
                    'dist_km': dist_km,
                    'extract': p.get('extract', '')
                })
        except Exception as e:
            out['es_err'] = str(e)
    
    # Also check enwiki geosearch if no es article within 5km
    has_close = any(a.get('dist_km') is not None and a['dist_km'] <= 5.0 for a in out['articles'])
    if not has_close:
        try:
            geo_url = f"https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=3&format=json"
            en_geo = fetch_json(geo_url).get('query', {}).get('geosearch', [])
            if en_geo:
                t_param = urllib.parse.quote('|'.join([g['title'] for g in en_geo]))
                url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=1&exchars=3000&titles={t_param}&format=json"
                pages = fetch_json(url).get('query', {}).get('pages', {})
                for pid, p in pages.items():
                    if 'missing' in p:
                        continue
                    coords = p.get('coordinates', [])
                    dist_km = round(haversine(lat, lng, coords[0]['lat'], coords[0]['lon']), 2) if coords else None
                    out['articles'].append({
                        'lang': 'en',
                        'title': p.get('title'),
                        'dist_km': dist_km,
                        'extract': p.get('extract', '')
                    })
        except Exception as e:
            out['en_err'] = str(e)
    return out

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    detailed = list(ex.map(process, data))

with open('tests/quipu_detailed.json', 'w', encoding='utf-8') as f:
    json.dump(detailed, f, ensure_ascii=False, indent=2)

for i, d in enumerate(detailed):
    arts = [f"{a['lang']}:{a['title']}({a['dist_km']}km)" for a in d['articles']]
    print(f"{i+1:02d}. {d['key']} -> {arts[:4]}")
