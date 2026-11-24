import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request

SETTLEMENTS = [
  ('1.Las Lajas-CO', 1.58273, -78.70609, '"Las Lajas" "Cajapí" Tumaco Nariño'),
  ('2.Tarapoa-EC', -0.1247, -76.34551, '"Tarapoa" Sucumbíos parroquia creación historia'),
  ('3.Choquecancha-PE', -13.0397, -72.036, '"Choquecancha" OR "Chuquicancha" Lares Calca historia'),
  ('4.La Libertad-PE', -9.63306, -77.74139, '"La Libertad" "Cajamarquilla" Huaraz Ancash creación distrito'),
  ('5.Moretecocha-EC', -1.61, -77.35, '"Moretecocha" Pastaza Ecuador'),
  ('6.Alto Jahuel-CL', -33.73753, -70.68519, '"Alto Jahuel" Buin historia hacienda'),
  ('7.Toro-PE', -15.26444, -72.92833, 'distrito de "Toro" "La Unión" Arequipa creación historia'),
  ('8.Tumbabarreto-CO', 5.43811, -75.70027, '"Tumbabarreto" OR "Quiebralomo" Riosucio Caldas historia'),
  ('9.Maucallacta-PE', -13.5601, -73.4934, '"Maucallacta" OR "Ataccara" Apurímac'),
  ('10.Tocmoche-PE', -6.41278, -79.36083, '"Tocmoche" Chota Cajamarca creación distrito historia'),
  ('11.Andajes-PE', -10.79278, -76.90917, '"Andajes" Oyón Lima historia reducción creación'),
  ('12.Quipama-CO', 5.52055, -74.18003, '"Quípama" Boyacá historia fundación municipio'),
  ('13.La Punta-CL', -34.01085, -70.64988, '"La Punta" Mostazal historia hacienda'),
  ('14.Otoca-PE', -14.49, -74.68667, '"Otoca" Lucanas Ayacucho historia creación distrito'),
  ('15.Tangui-PE', -12.383, -76.383, '"Tanqui" OR "Tangui" Calango OR Huarochirí OR Yauyos OR Lima'),
]

HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept-Language': 'es,en;q=0.9',
}

def bing_search(q):
  url = 'https://www.bing.com/search?q=' + urllib.parse.quote(q)
  req = urllib.request.Request(url, headers=HEADERS)
  body = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'ignore')
  results = []
  for m in re.finditer(r'<li class="b_algo"[^>]*>(.*?)</li>', body, re.S):
    blk = m.group(1)
    t = re.sub(r'<[^>]+>', ' ', blk)
    t = html.unescape(re.sub(r'\s+', ' ', t)).strip()
    href = re.search(r'href="(https?://[^"]+)"', blk)
    results.append((t[:350], href.group(1) if href else ''))
  return results

def photon_rev(lat, lon):
  url = f'https://photon.komoot.io/reverse?lat={lat}&lon={lon}'
  req = urllib.request.Request(url, headers={'User-Agent': 'SVEA-Research/1.0'})
  data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
  feats = data.get('features', [])
  if not feats:
    return 'none'
  props = feats[0].get('properties', {})
  return {k: props.get(k) for k in ('name', 'city', 'county', 'state', 'country', 'osm_value') if props.get(k)}

idx_start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
idx_end = int(sys.argv[2]) if len(sys.argv) > 2 else len(SETTLEMENTS)

for label, lat, lon, q in SETTLEMENTS[idx_start:idx_end]:
  print(f'\n================ {label} ({lat}, {lon}) ================')
  try:
    print('GEO:', photon_rev(lat, lon))
  except Exception as e:
    print('GEO ERR:', e)
  try:
    res = bing_search(q)
    for txt, link in res[:5]:
      print(' -', txt, '|', link)
    if not res:
      print(' (no b_algo results)')
  except Exception as e:
    print('BING ERR:', e)
  time.sleep(0.5)
