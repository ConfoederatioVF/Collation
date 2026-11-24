import json, csv, glob, math

with open('tests/c053_input.json', encoding='utf-8') as f:
    items = json.load(f)
with open('tests/c053_local_hits.json', encoding='utf-8') as f:
    hits = json.load(f)

def hav(a, b):
    R = 6371.0
    l1, o1, l2, o2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    return 2 * R * math.asin(min(1, math.sqrt(math.sin((l2 - l1) / 2) ** 2 + math.cos(l1) * math.cos(l2) * math.sin((o2 - o1) / 2) ** 2)))

csvs = glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/**/*.csv', recursive=True)
csv_hits = {it['key']: [] for it in items}
for cf in csvs:
    try:
        with open(cf, encoding='utf-8', errors='replace') as f:
            rd = csv.DictReader(f)
            for row in rd:
                lat = row.get('lat') or row.get('latitude') or row.get('Lat') or row.get('LAT')
                lon = row.get('lon') or row.get('lng') or row.get('longitude') or row.get('Lon') or row.get('LONG')
                try:
                    la, lo = float(lat), float(lon)
                except Exception:
                    continue
                for it in items:
                    d = hav(it['ll'], [la, lo])
                    if d <= 2.5:
                        csv_hits[it['key']].append({'file': cf.replace('\\', '/').split('/')[-1], 'd': round(d, 3), 'row': {k: v for k, v in row.items() if v}})
    except Exception:
        pass

# Also check hgis_indias_colonial_raw.json by radius 15 km or name match!
with open('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json', encoding='utf-8') as f:
    hgis = json.load(f)
hgis_recs = hgis if isinstance(hgis, list) else (hgis.get('features') or hgis.get('records') or hgis.get('settlements') or list(hgis.values()))

hgis_hits = {it['key']: [] for it in items}
for rec in hgis_recs:
    if not isinstance(rec, dict):
        continue
    props = rec.get('properties', rec)
    geom = rec.get('geometry') or {}
    coords = geom.get('coordinates') if isinstance(geom, dict) else None
    la = props.get('lat') or props.get('latitude') or (coords[1] if coords and len(coords) >= 2 else None)
    lo = props.get('lon') or props.get('lng') or props.get('longitude') or (coords[0] if coords and len(coords) >= 2 else None)
    try:
        la, lo = float(la), float(lo)
    except Exception:
        continue
    for it in items:
        d = hav(it['ll'], [la, lo])
        if d <= 10.0:
            hgis_hits[it['key']].append({'d': round(d, 3), 'props': {k: v for k, v in props.items() if v not in (None, '', [], {})}})

lines = []
for it in items:
    k = it['key']
    lh = hits.get(k, [])
    ch = csv_hits.get(k, [])
    hh = hgis_hits.get(k, [])
    if lh or ch or hh:
        seen = set()
        lines.append(f"=== {k} ({it['n']}, {it['c']}, r={it['r']}, {it['ey']}..{it['ly']}) ===")
        for h in lh:
            r = h['rec']
            sig = (h['file'], r.get('name') or r.get('site_name') or r.get('tramnomb'), r.get('period') or r.get('classification'))
            if sig in seen:
                continue
            seen.add(sig)
            sub = {kk: r.get(kk) for kk in ('name', 'site_name', 'period', 'culture', 'classification', 'province', 'department', 'municipality', 'district', 'county', 'date', 'age', 'c14_age', 'cal_bp', 'foundation_year', 'year', 'source', 'citation', 'tramnomb', 'stranomb', 'camdesc') if r.get(kk) is not None}
            lines.append(f"  JSON: {h['file']} {h['dist_km']}km | {sub}")
        for h in ch[:8]:
            sub = {kk: vv for kk, vv in h['row'].items() if any(t in kk.lower() for t in ('site', 'name', 'period', 'cult', 'age', 'bp', 'date', 'dept', 'prov', 'loc', 'cal'))}
            lines.append(f"  CSV: {h['file']} {h['d']}km | {sub}")
        for h in hh[:5]:
            lines.append(f"  HGIS: {h['d']}km | {h['props']}")

with open('tests/c053_local_summary.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f"Wrote {len(lines)} lines to tests/c053_local_summary.txt")
