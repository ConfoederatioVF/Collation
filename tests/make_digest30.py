import json
from chunk030_local import INPUT

lh = json.load(open('tests/chunk030_local_hits.json', encoding='utf-8'))
wk = json.load(open('tests/chunk030_wiki.json', encoding='utf-8'))

lines = []
for idx, item in enumerate(INPUT):
    k = item['key']
    n = item['n']
    c = item['c']
    r = item['r']
    ll = item['ll']
    ey = item['ey']
    ly = item['ly']
    al = item.get('al')
    ex = item.get('ex')
    lines.append(f'### [{idx+1}] {k} | n={n} | c={c} | r={r} | ll={ll} | ey={ey} | ly={ly} | al={al} | ex={ex}')
    L = lh.get(k, {})
    for ls in L.get('local_setts', []):
        slim = {kk: vv for kk, vv in ls.items() if kk not in ('coords', 'll') and vv not in (None, [], '', {})}
        lines.append('  LOCAL: ' + json.dumps(slim, ensure_ascii=False))
    for rs in L.get('raw_sites', [])[:4]:
        slim = {kk: vv for kk, vv in rs.items() if vv not in (None, [], '', {})}
        lines.append('  SITE: ' + json.dumps(slim, ensure_ascii=False)[:400])
    for hg in L.get('hgis', [])[:3]:
        lines.append('  HGIS: ' + json.dumps(hg, ensure_ascii=False)[:300])
    W = wk.get(k, {})
    geos = [(g['title'], g['dist']) for g in W.get('geo_es', [])[:3]]
    if geos:
        lines.append('  GEO_ES: ' + str(geos))
    for ext in W.get('extracts_es', []):
        txt = ext['extract'].replace('\n', ' ')
        lines.append(f'  WIKI[{ext["title"]}]: {txt[:1000]}')
    lines.append('')

with open('tests/chunk030_digest.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('Total lines:', len(lines))
