import json, urllib.request, urllib.parse, time

with open('tests/lookup_chunk026.py', encoding='utf-8') as f:
    src = f.read()
ns = {}
exec(src.split('def wp_geo')[0], ns)
inp = ns['INPUT']

results = {}
for i, item in enumerate(inp):
    k = item['key']
    lat, lng = item['ll']
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'SVEA-Toponymy-Bot/1.0 (https://confoederatio.org)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode())
            results[k] = [f"{x['title']} ({int(x['dist'])}m)" for x in d.get('query', {}).get('geosearch', [])]
    except Exception as e:
        results[k] = [f"ERR:{e}"]
    time.sleep(0.2)

with open('tests/chunk026_wp_seq.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
ok = sum(1 for v in results.values() if v and not str(v[0]).startswith('ERR'))
print(f"Done WP seq: {ok}/{len(inp)} have geosearch hits")
