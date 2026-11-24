import json, pathlib

raw_dir = pathlib.Path('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources')
sites_dir = pathlib.Path('histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites')

targets = [
  ('Las Lajas-Colombia', [1.58273, -78.70609]),
  ('Tarapoa-Ecuador', [-0.1247, -76.34551]),
  ('La Libertad-Peru', [-9.63306, -77.74139]),
  ('Moretecocha-Ecuador_2', [-1.61, -77.35]),
  ('Alto Jahuel-Chile', [-33.73753, -70.68519]),
  ('Tumbabarreto-Colombia', [5.43811, -75.70027]),
  ('Maucallacta-Peru', [-13.5601, -73.4934]),
  ('Andajes-Peru', [-10.79278, -76.90917]),
  ('Quípama-Colombia', [5.52055, -74.18003]),
  ('Chibunga-Ecuador', [-0.03782, -79.74084]),
  ('Páez (ven_barinas)-Venezuela', [8.03111, -70.00667]),
  ('Condormarca-Peru', [-7.54667, -77.59972]),
  ('Buena Vista (ven_lara)-Venezuela', [9.88667, -69.48111]),
  ('Cantagallo-Venezuela', [9.78852, -67.43191]),
  ('Juan Pablo Peñaloza-Venezuela', [8.03722, -71.85444]),
  ('Puncurin-Peru', [-9.80468, -76.79086]),
  ('Sabaneta (ven_falcon)-Venezuela', [11.26, -69.98944]),
  ('Mercedes Díaz-Venezuela', [9.30027, -70.63088]),
  ('Huambacho Nueva (la Huaca)-Peru', [-9.2589, -78.4352]),
  ('Jorobamba-Peru', [-5.8533, -78.6166]),
  ('Nonogasta-Argentina', [-29.30222, -67.50633]),
  ('Lampa (per_ayacucho)-Peru', [-15.185, -73.34917]),
  ('Coronado-Colombia', [3.552, -76.318]),
  ('Choquekancha-Peru', [-13.03601, -72.03543]),
  ('Mamara-Peru', [-14.22861, -72.59083]),
  ('Cotaruse-Peru', [-14.41583, -73.205]),
]

print("--- RAW SETTS ---")
for fn in sorted(raw_dir.glob('raw_setts_*.json')):
    data = json.load(open(fn, encoding='utf8'))
    items = data if isinstance(data, list) else data.get('settlements', data.get('records', []))
    for it in items:
        if not isinstance(it, dict): continue
        lat = it.get('lat') or (it.get('coords')[0] if isinstance(it.get('coords'), list) and len(it.get('coords'))>=2 else None)
        lng = it.get('lng') or (it.get('coords')[1] if isinstance(it.get('coords'), list) and len(it.get('coords'))>=2 else None)
        if lat is None or lng is None: continue
        for k, (tlat, tlng) in targets:
            if abs(float(lat)-tlat)<0.02 and abs(float(lng)-tlng)<0.02:
                print(fn.name, "|", k, "|", {kk: it[kk] for kk in it if kk not in ('population','populations','yearly_pop')})

print("--- RAW ARCH SITES ---")
for fn in sorted(sites_dir.glob('*.json')):
    if 'summary' in fn.name: continue
    data = json.load(open(fn, encoding='utf8'))
    items = data if isinstance(data, list) else data.get('sites', data.get('features', data.get('records', [])))
    if not isinstance(items, list): continue
    for it in items:
        if not isinstance(it, dict): continue
        props = it.get('properties', it)
        geom = it.get('geometry') or {}
        coords = geom.get('coordinates') if isinstance(geom, dict) else None
        lat = props.get('lat') or props.get('latitude') or (coords[1] if coords and len(coords)>=2 else (props.get('coords')[0] if isinstance(props.get('coords'), list) else None))
        lng = props.get('lng') or props.get('lon') or props.get('longitude') or (coords[0] if coords and len(coords)>=2 else (props.get('coords')[1] if isinstance(props.get('coords'), list) else None))
        if lat is None or lng is None: continue
        try:
            lat, lng = float(lat), float(lng)
        except: continue
        for k, (tlat, tlng) in targets:
            if abs(lat-tlat)<0.02 and abs(lng-tlng)<0.02:
                print(fn.name, "|", k, "|", str(props)[:260])
