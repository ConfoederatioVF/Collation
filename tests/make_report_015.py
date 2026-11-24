import json, glob

hgis = json.load(open('tests/chunk015_hgis.json', encoding='utf-8'))
wiki = json.load(open('tests/chunk015_wiki.json', encoding='utf-8'))

raw_map = {}
for fp in glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw_setts_*.json'):
    d = json.load(open(fp, encoding='utf-8'))
    setts = d.get('settlements', d) if isinstance(d, dict) else d
    if isinstance(setts, dict):
        for k, v in setts.items():
            raw_map[k] = v
    elif isinstance(setts, list):
        for v in setts:
            if isinstance(v, dict) and 'key' in v:
                raw_map[v['key']] = v

lines = []
for i, (k, w) in enumerate(wiki.items(), 1):
    lines.append(f"=== {i}. {k} | n={w['n']} | c={w['c']} | r={w['r']} | ll={w['ll']} | ey={w['ey']} | ly={w['ly']} ===")
    if k in raw_map:
        rm = {rk: rv for rk, rv in raw_map[k].items() if rk not in ('population', 'pop', 'geometry')}
        lines.append("  RAW: " + json.dumps(rm, ensure_ascii=False)[:400])
    if k in hgis:
        for h in hgis[k]:
            lines.append("  HGIS: " + json.dumps(h, ensure_ascii=False))
    if w.get('geo_es'):
        lines.append("  GEO_ES: " + str(w['geo_es']))
    if w.get('sr_es'):
        lines.append("  SR_ES: " + str(w['sr_es']))
    for title, ext in w.get('extracts', {}).items():
        clean_ext = ext.replace('\n', ' ')
        lines.append(f"  WIKI[{title}]: {clean_ext[:1100]}")
    lines.append('')

open('tests/chunk015_report.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('Lines:', len(lines))
