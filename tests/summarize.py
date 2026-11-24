import json, re

data = json.load(open('tests/chunk016_research.json', encoding='utf-8'))
lines = []
for idx, d in enumerate(data):
    lines.append(f"=== [{idx+1}] {d['key']} | n={d['n']} | c={d['c']} | r={d['r']} | ll={d['ll']} | ey={d['ey']} | ly={d['ly']} | al={d['al']} | ex={d['ex']} ===")
    for loc in d.get('local', []):
        ld = dict(loc['data'])
        for drop in ('pop', 'populations', 'series', 'p', 'yearly_populations', 'hist_pop'):
            ld.pop(drop, None)
        lines.append(f"  LOCAL({loc['file']}): {json.dumps(ld, ensure_ascii=False)[:600]}")
    if d.get('es_geo'):
        lines.append('  ES_GEO: ' + ', '.join(f"{h['title']} ({h['dist']}m)" for h in d['es_geo']))
    if d.get('es_search'):
        lines.append('  ES_SEARCH: ' + ', '.join(h['title'] for h in d['es_search']))
    for title, ext in d.get('extracts', {}).items():
        clean = re.sub(r'\s+', ' ', ext)[:1100]
        lines.append(f"  EXT[{title}]: {clean}")
with open('tests/chunk016_summary.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('Lines written:', len(lines))
