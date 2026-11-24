import urllib.request
import urllib.parse
import json
import re
import time
import html as htmllib

pts = [
  (46, 'Casiri-Peru', 'Casiri', -15.33, -73.34, 'Ayacucho Peru'),
  (47, 'Tinta (per_lima)-Peru', 'Tinta', -10.6802, -76.8228, 'Lima Oyon Peru'),
  (48, 'Huataca-Peru', 'Huataca', -15.076, -73.331, 'Ayacucho Peru'),
  (49, 'Atiquipa-Peru', 'Atiquipa', -15.79611, -74.36361, 'Caraveli Arequipa Peru'),
  (50, 'Pariamarca (per_lima)-Peru', 'Pariamarca', -11.4919, -76.6295, 'Canta Lima Peru'),
  (51, 'San Pedro de Laraos-Peru', 'San Pedro de Laraos', -11.66444, -76.53944, 'Huarochiri Lima Peru'),
  (52, 'San Jose (vp_intendencia_lima)-Peru', 'San Jose', -11.505, -76.675, 'Canta Lima Peru'),
  (53, 'Yamor-Peru', 'Yamor', -10.199, -77.483, 'Ancash Bolognesi Peru'),
  (54, 'La Sierra (col_boyaca)-Colombia', 'La Sierra', 6.22731, -74.56735, 'Puerto Boyaca Carare Colombia'),
  (55, 'Quintero-Colombia_2', 'Quintero', 4.472, -76.095, 'Valle del Cauca Colombia'),
  (56, 'Sabaneta (ven_falcon)-Venezuela', 'Sabaneta', 11.26, -69.98944, 'Falcon Miranda Venezuela'),
  (57, 'Huanangui-Peru', 'Huanangui', -11.1328, -77.0363, 'Huaura Lima Peru'),
  (58, 'Santiago Apostol-Colombia', 'Santiago Apostol', 9.0069, -74.92686, 'Sucre San Benito Abad Colombia'),
  (59, 'Anton Moreno-Colombia', 'Anton Moreno', 2.41, -76.62, 'Popayan Cauca Colombia'),
  (60, 'Nanis-Peru', 'Nanis', -10.383, -77.15, 'Ancash Bolognesi Ocros Peru'),
]

wiki_headers = {'User-Agent': 'HistoricalGazetteerResearch/1.0 (https://confoederatio.org; research@confoederatio.org)'}
browser_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def get_json(url, headers):
  req = urllib.request.Request(url, headers=headers)
  return json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))

for idx, key, name, lat, lon, hint in pts:
  print(f'=== {idx}. {key} ({lat}, {lon}) ===')
  # 1. Photon reverse
  try:
    p_url = f'https://photon.komoot.io/reverse?lat={lat}&lon={lon}&limit=3'
    pdata = get_json(p_url, browser_headers)
    feats = pdata.get('features', [])
    for f in feats[:2]:
      pr = f.get('properties', {})
      print('  Photon:', {k: pr.get(k) for k in ['name','city','town','village','county','state','country','osm_value'] if pr.get(k)})
  except Exception as e:
    print('  Photon ERR:', e)

  # 2. es.wiki geosearch
  try:
    g_url = f'https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json'
    gdata = get_json(g_url, wiki_headers)
    gs = gdata.get('query', {}).get('geosearch', [])
    print('  WikiGeo:', [(x['title'], round(x['dist'])) for x in gs])
  except Exception as e:
    print('  WikiGeo ERR:', e)
  time.sleep(0.3)
