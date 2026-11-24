import json
import os

data = json.load(open('tests/chunk038_local_matches.json', encoding='utf-8'))

# Check raw_sites and settlement_sources/raw for exact coordinate matches
raw_files = [
    'histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw/nso_colombia/divipola_centros_poblados.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw/nso_peru/inei_ccpp_2017_nacional.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw/nso_peru/peru_censos_2007_2025.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw/nso_ecuador/inec_towns_1990_2022.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw/nso_argentina/georef_localidades_censales.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw/nso_venezuela/esriven_parroquias_2011.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/raw_argentina_idacor_ariadne.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/raw_chile_cmn_acreditado.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/raw_chile_arkg.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/raw_colombia_icanh_sitios.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/raw_colombia_col14.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/raw_peru_sigda.json',
    'histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/raw_ecuador_radiocarbon_syntheses.json',
]

targets = [(d['key'], d['ll'][0], d['ll'][1], d['n']) for d in data]
hits = {k: [] for k, _, _, _ in targets}

def extract_records(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ['features', 'records', 'sites', 'data', 'items', 'rows', 'settlements']:
            if k in obj and isinstance(obj[k], list):
                return obj[k]
        if all(isinstance(v, dict) for v in list(obj.values())[:5]):
            return list(obj.values())
    return []

for rf in raw_files:
    if not os.path.exists(rf):
        continue
    try:
        obj = json.load(open(rf, encoding='utf-8'))
    except Exception as e:
        print('ERR', rf, e)
        continue
    recs = extract_records(obj)
    for r in recs:
        if not isinstance(r, dict):
            continue
        props = r.get('properties', r)
        geom = r.get('geometry') or {}
        lat = lng = None
        if isinstance(geom, dict) and geom.get('type') == 'Point' and isinstance(geom.get('coordinates'), list) and len(geom['coordinates']) >= 2:
            lng, lat = geom['coordinates'][0], geom['coordinates'][1]
        elif 'coords' in props and isinstance(props['coords'], list) and len(props['coords']) == 2:
            lat, lng = props['coords'][0], props['coords'][1]
        elif 'lat' in props and 'lng' in props:
            lat, lng = props['lat'], props['lng']
        elif 'lat' in props and 'lon' in props:
            lat, lng = props['lat'], props['lon']
        elif 'latitude' in props and 'longitude' in props:
            lat, lng = props['latitude'], props['longitude']
        elif 'latitud' in props and 'longitud' in props:
            lat, lng = props['latitud'], props['longitud']
        if lat is None or lng is None:
            continue
        try:
            lat, lng = float(lat), float(lng)
        except:
            continue
        for k, ilat, ilng, iname in targets:
            if abs(lat - ilat) < 0.008 and abs(lng - ilng) < 0.008:
                hits[k].append((os.path.basename(rf), {kk: vv for kk, vv in props.items() if kk not in ('population', 'geometry', 'polygon') and vv not in (None, '', [])}))

with open('tests/chunk038_raw_hits.json', 'w', encoding='utf-8') as f:
    json.dump(hits, f, ensure_ascii=False, indent=2)
print('Raw hits keys:', sum(1 for v in hits.values() if v), '/', len(targets))
