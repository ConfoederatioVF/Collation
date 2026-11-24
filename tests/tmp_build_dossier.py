import json, os, math

items = json.load(open('tests/tmp_input_029.json', encoding='utf-8'))
ctx = {x['key']: x for x in json.load(open('tests/tmp_local_context.json', encoding='utf-8'))}
wiki = {x['key']: x for x in json.load(open('tests/tmp_wiki_029.json', encoding='utf-8'))}
root = 'histmap/1.data_raw/population_regional/QUIPU'

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

# Load HGIS raw records
hgis_p = os.path.join(root, '_shared/settlement_sources/hgis_indias_colonial_raw.json')
hgis_recs = []
if os.path.exists(hgis_p):
    hd = json.load(open(hgis_p, encoding='utf-8'))
    for k, v in hd.items():
        if k != 'metadata' and isinstance(v, list):
            hgis_recs = v
        elif k != 'metadata' and isinstance(v, dict):
            hgis_recs = list(v.values())

# Load documented_arch_sites.json
doc_arch = []
da_p = os.path.join(root, '_shared/sites_quipu_andes_cone/config/documented_arch_sites.json')
if os.path.exists(da_p):
    dd = json.load(open(da_p, encoding='utf-8'))
    doc_arch = dd if isinstance(dd, list) else dd.get('sites', list(dd.values()) if isinstance(dd, dict) else [])

# Load ICANH, SIGDA, CMN
def load_sites(rel_path):
    p = os.path.join(root, rel_path)
    if not os.path.exists(p): return []
    d = json.load(open(p, encoding='utf-8'))
    if isinstance(d, list): return d
    if isinstance(d, dict):
        for k in ('features', 'sites', 'records', 'data', 'settlements'):
            if k in d and isinstance(d[k], list): return d[k]
    return []

icanh = load_sites('_shared/sites_quipu_andes_cone/0.raw_sites/raw_colombia_icanh_sitios.json')
sigda = load_sites('_shared/sites_quipu_andes_cone/0.raw_sites/raw_peru_sigda.json')
cmn1 = load_sites('_shared/sites_quipu_andes_cone/0.raw_sites/raw_chile_cmn_acreditado.json')
cmn2 = load_sites('_shared/sites_quipu_andes_cone/0.raw_sites/raw_chile_cmn_registros_complementarios.json')

def match_raw(arr, lat, lng, rad=2.0):
    hits = []
    for r in arr:
        if not isinstance(r, dict): continue
        props = r.get('properties', r)
        geom = r.get('geometry', {})
        rlat = props.get('lat') or props.get('latitude') or props.get('LAT') or props.get('y')
        rlng = props.get('lng') or props.get('lon') or props.get('longitude') or props.get('LON') or props.get('x')
        if rlat is None and isinstance(props.get('coords'), list) and len(props['coords'])>=2:
            rlat, rlng = props['coords'][0], props['coords'][1]
        if rlat is None and isinstance(geom.get('coordinates'), list) and len(geom['coordinates'])>=2:
            rlng, rlat = geom['coordinates'][0], geom['coordinates'][1]
        if rlat is not None and rlng is not None:
            try:
                rlat, rlng = float(rlat), float(rlng)
                if abs(rlat-lat)<0.05 and abs(rlng-lng)<0.05:
                    d = haversine(lat, lng, rlat, rlng)
                    if d <= rad:
                        clean = {k:v for k,v in props.items() if v not in (None, '', []) and k not in ('geometry',)}
                        hits.append((round(d,2), clean))
            except: pass
    return hits[:3]

lines = []
for idx, it in enumerate(items, 1):
    k = it['key']
    lat, lng = it['ll']
    c = ctx.get(k, {})
    w = wiki.get(k, {})
    lines.append(f"=== [{idx}] {k} | n={it['n']} | c={it['c']} | r={it['r']} | ll={it['ll']} | ey={it['ey']} ly={it['ly']} ===")
    if it.get('al'): lines.append(f"  al: {it['al']}")
    if it.get('ex'): lines.append(f"  ex: {it['ex']}")
    for m in c.get('local_matches', []):
        tag = 'KEY' if m.get('key_match') else f"NEAR({m.get('dist_km')}km:{m.get('other_key')})"
        lines.append(f"  [{tag}] {m['file']}: name={m['name']} | other={m.get('other_names')} | src={m.get('sources')} | fy={m.get('foundation_year')} | period={m.get('period')} | yrs={m.get('pop_years')[:4]}..{m.get('pop_years')[-2:] if m.get('pop_years') else []}")
    for d, h in match_raw(hgis_recs, lat, lng, 5.0):
        lines.append(f"  [HGIS {d}km] {str(h)[:300]}")
    for d, h in match_raw(icanh, lat, lng, 2.0):
        lines.append(f"  [ICANH {d}km] {str(h)[:300]}")
    for d, h in match_raw(sigda, lat, lng, 2.0):
        lines.append(f"  [SIGDA {d}km] {str(h)[:300]}")
    for d, h in match_raw(cmn1+cmn2, lat, lng, 2.0):
        lines.append(f"  [CMN {d}km] {str(h)[:300]}")
    if w.get('es_geo'):
        lines.append(f"  [WIKI_GEO] {w['es_geo'][:3]}")
    if w.get('es_search'):
        lines.append(f"  [WIKI_SEARCH] {w['es_search'][:3]}")
    for wt, ex_txt in (w.get('extracts') or {}).items():
        clean_ex = ex_txt.replace('\n', ' ')[:450]
        lines.append(f"  [EXTRACT {wt}] {clean_ex}")
    lines.append("")

open('tests/tmp_dossier_029.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('Wrote tests/tmp_dossier_029.txt, total lines:', len(lines))
