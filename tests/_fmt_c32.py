import json

items = json.load(open('tests/_chunk032_input.json', encoding='utf-8'))
res = json.load(open('tests/_chunk032_research.json', encoding='utf-8'))
for p_idx in range(3):
    lines = []
    for idx in range(p_idx*30, (p_idx+1)*30):
        it = items[idx]
        k = it['key']
        loc = res['local'].get(k, {})
        wk = res['wiki'].get(k, {})
        lines.append(f"=== [{idx}] {k} | n={it['n']} | c={it['c']} | r={it['r']} | ll={it['ll']} | ey={it['ey']} ly={it['ly']} | al={it.get('al')} | ex={it.get('ex')} ===")
        if loc.get('raw_sett'):
            rs = loc['raw_sett']
            sub = {x: rs.get(x) for x in ('name','other_names','admin1','admin2','sources','coord_source','notes','foundation_year','earliest_year') if rs.get(x) is not None}
            lines.append('  RAW_SETT: ' + json.dumps(sub, ensure_ascii=False))
        if loc.get('hgis'):
            for d, h in loc['hgis'][:3]:
                obs = str(h.get('observaciones', ''))[:120]
                lines.append(f"  HGIS ({d}km): name={h.get('name')} mod={h.get('modern_name')} var={h.get('variants')} {h.get('start_year')}..{h.get('end_year')} cat={h.get('categoria')} prov={h.get('colonial_province')} part={h.get('colonial_partido')} obs={obs}")
        if loc.get('arch'):
            for d, src, a in loc['arch'][:3]:
                lines.append(f"  ARCH ({d}km, {src}): {json.dumps(a, ensure_ascii=False)[:220]}")
        if wk.get('es_geo'):
            geo_str = ', '.join(f"{g['title']}({g['dist']}m)" for g in wk['es_geo'][:4])
            lines.append('  ES_GEO: ' + geo_str)
        if wk.get('es_search'):
            sr_str = ', '.join(s['title'] for s in wk['es_search'][:3])
            lines.append('  ES_SEARCH: ' + sr_str)
        for t, txt in (wk.get('es_extracts') or {}).items():
            clean = ' '.join(txt.split())[:1200]
            lines.append(f"  ES_TXT [{t}]: {clean}")
        for t, txt in (wk.get('en_extracts') or {}).items():
            if not wk.get('es_extracts'):
                clean = ' '.join(txt.split())[:800]
                lines.append(f"  EN_TXT [{t}]: {clean}")
        lines.append('')
    with open(f'tests/_c32_part{p_idx+1}.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
print('Wrote 3 digest files')
