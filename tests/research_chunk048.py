import json, math, os, glob

def haversine(lat1, lon1, lat2, lon2):
  R = 6371.0
  p1, p2 = math.radians(lat1), math.radians(lat2)
  dp = math.radians(lat2 - lat1)
  dl = math.radians(lon2 - lon1)
  a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
  return 2 * R * math.asin(math.sqrt(a))

with open('tests/chunk048_input.json', 'r', encoding='utf-8') as f:
  items = json.load(f)

base = 'histmap/1.data_raw/population_regional/QUIPU/_shared'
with open(os.path.join(base, 'settlement_sources/hgis_indias_colonial_raw.json'), 'r', encoding='utf-8') as f:
  hgis = json.load(f)['settlements']

hgis_list = list(hgis.values()) if isinstance(hgis, dict) else hgis

raw_setts = []
for fn in glob.glob(os.path.join(base, 'settlement_sources/raw_setts_*.json')):
  with open(fn, 'r', encoding='utf-8') as f:
    d = json.load(f)
    if isinstance(d, dict):
      for k, v in d.items():
        if isinstance(v, list): raw_setts.extend(v)
        elif isinstance(v, dict): raw_setts.append(v)
    elif isinstance(d, list):
      raw_setts.extend(d)

sites = []
for fn in glob.glob(os.path.join(base, 'sites_quipu_andes_cone/0.raw_sites/*.json')):
  if 'summary_' in fn: continue
  with open(fn, 'r', encoding='utf-8') as f:
    try:
      d = json.load(f)
    except Exception:
      continue
    arr = d if isinstance(d, list) else (d.get('sites') or d.get('features') or d.get('records') or [])
    bname = os.path.basename(fn)
    for row in arr:
      if not isinstance(row, dict): continue
      lat = row.get('lat') or row.get('latitude') or row.get('y')
      lon = row.get('lng') or row.get('lon') or row.get('longitude') or row.get('x')
      if lat is None and isinstance(row.get('geometry'), dict):
        c = row['geometry'].get('coordinates') or []
        if len(c) >= 2: lon, lat = c[0], c[1]
      if lat is None or lon is None: continue
      try:
        sites.append((float(lat), float(lon), bname, row))
      except Exception:
        pass

out = []
for it in items:
  lat, lon = it['ll']
  rec = {'key': it['key'], 'n': it['n'], 'c': it['c'], 'r': it['r'], 'ey': it['ey'], 'ly': it['ly'], 'hgis': [], 'raw_setts': [], 'sites': []}
  for h in hgis_list:
    hc = h.get('coords') or []
    if len(hc) == 2 and haversine(lat, lon, hc[0], hc[1]) <= 3.0:
      rec['hgis'].append({k: h.get(k) for k in ['name', 'modern_name', 'variants', 'colonial_province', 'colonial_partido', 'categoria', 'start_year', 'end_year', 'coords']})
  for r in raw_setts:
    rc = r.get('coords') or r.get('ll')
    rlat = rc[0] if isinstance(rc, list) and len(rc) == 2 else (r.get('lat') or r.get('latitude'))
    rlon = rc[1] if isinstance(rc, list) and len(rc) == 2 else (r.get('lng') or r.get('lon') or r.get('longitude'))
    if rlat is not None and rlon is not None:
      try:
        if haversine(lat, lon, float(rlat), float(rlon)) <= 1.5:
          rec['raw_setts'].append({k: r.get(k) for k in ['name', 'modern_name', 'source', 'admin1', 'admin2', 'subregion', 'founding_year', 'start_year', 'notes'] if r.get(k) is not None})
      except Exception:
        pass
  for slat, slon, bname, row in sites:
    if haversine(lat, lon, slat, slon) <= 1.5:
      props = row.get('properties') if isinstance(row.get('properties'), dict) else row
      keep = {k: props.get(k) for k in ['name', 'site_name', 'nombre', 'sitio', 'culture', 'period', 'periodo', 'cultura', 'cronologia', 'start_year', 'end_year', 'age_bp', 'cal_bp', 'year_bc_ad', 'category', 'tipo', 'departamento', 'provincia', 'municipio', 'distrito', 'region', 'description', 'observaciones', 'source'] if props.get(k) is not None}
      keep['_file'] = bname
      keep['_dist_km'] = round(haversine(lat, lon, slat, slon), 2)
      rec['sites'].append(keep)
      if len(rec['sites']) >= 5: break
  out.append(rec)

with open('tests/chunk048_local_matches.json', 'w', encoding='utf-8') as f:
  json.dump(out, f, ensure_ascii=False, indent=2)

print('Matched HGIS:', sum(1 for x in out if x['hgis']), 'raw_setts:', sum(1 for x in out if x['raw_setts']), 'sites:', sum(1 for x in out if x['sites']))
