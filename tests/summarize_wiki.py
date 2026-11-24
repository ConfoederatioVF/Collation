import json

with open('tests/wiki_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

lines = []
for i, d in enumerate(data):
    geos = [f"{g['title']} ({int(g['dist'])}m)" for g in d.get('geo', [])[:3]]
    srs = d.get('search', [])[:3]
    lines.append(f"{i:02d} | {d['key']} | c={d['c']} | r={d['r']} | ll={d['ll']} | ey={d['ey']}..{d['ly']} | geo={geos} | sr={srs}")

with open('tests/wiki_overview.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"Wrote {len(lines)} lines")
