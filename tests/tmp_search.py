import urllib.request
import urllib.parse
import json
import re
import html
import sys

def bing_search(query):
  url = 'https://www.bing.com/search?' + urllib.parse.urlencode({'q': query, 'setlang': 'es'})
  req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
  })
  body = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'ignore')
  items = re.findall(r'<li class="b_algo".*?</li>', body, re.S)
  results = []
  for item in items[:6]:
    link_m = re.search(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', item, re.S)
    snip_m = re.search(r'<p[^>]*>(.*?)</p>', item, re.S)
    title = html.unescape(re.sub(r'<[^>]+>', ' ', link_m.group(2))).strip() if link_m else ''
    href = html.unescape(link_m.group(1)) if link_m else ''
    snip = html.unescape(re.sub(r'<[^>]+>', ' ', snip_m.group(1))).strip() if snip_m else html.unescape(re.sub(r'<[^>]+>', ' ', item)).strip()
    snip = re.sub(r'\s+', ' ', snip)
    results.append({'title': title, 'url': href, 'snippet': snip[:450]})
  return results

def wikidata_around(lat, lon, radius_km=15):
  q = f'''SELECT ?place ?placeLabel ?placeDescription ?dist WHERE {{
  SERVICE wikibase:around {{
    ?place wdt:P625 ?loc .
    bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral .
    bd:serviceParam wikibase:radius "{radius_km}" .
    bd:serviceParam wikibase:distance ?dist .
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
}} ORDER BY ?dist LIMIT 8'''
  url = 'https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(q)
  req = urllib.request.Request(url, headers={'User-Agent': 'SVEA-Research/1.0 (https://confoederatio.org)'})
  data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode('utf-8'))
  return [{
    'id': r['place']['value'].split('/')[-1],
    'label': r.get('placeLabel', {}).get('value', ''),
    'desc': r.get('placeDescription', {}).get('value', ''),
    'dist': r.get('dist', {}).get('value', '')
  } for r in data['results']['bindings']]

if __name__ == '__main__':
  mode = sys.argv[1]
  if mode == 'bing':
    print(json.dumps(bing_search(sys.argv[2]), ensure_ascii=False, indent=2))
  elif mode == 'wd':
    print(json.dumps(wikidata_around(float(sys.argv[2]), float(sys.argv[3])), ensure_ascii=False, indent=2))
