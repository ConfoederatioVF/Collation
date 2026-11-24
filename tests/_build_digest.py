import json
import re

inp = json.load(open('tests/quipu_021_input.json', encoding='utf-8'))
geo = json.load(open('tests/quipu_021_geo.json', encoding='utf-8'))
wiki = json.load(open('tests/_c021_wikitext.json', encoding='utf-8'))
local = json.load(open('tests/_c021_local_hits.json', encoding='utf-8'))

missing_wiki = []
lines = []
for i, item in enumerate(inp, 1):
  k = item['key']
  n = item['n']
  c = item['c']
  r = item['r']
  ey = item['ey']
  ly = item['ly']
  al = item.get('al', [])
  ex = item.get('ex', [])
  loc = local.get(k, {}).get('data', {})
  src = loc.get('sources', [])
  fy = loc.get('foundation_year')
  g_list = geo.get(k, []) if isinstance(geo.get(k), list) else []
  g_titles = [g['title'] for g in g_list]

  matched = []
  for t in g_titles[:3]:
    if t in wiki:
      matched.append((t, wiki[t]))
  n_low = n.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
  for wt in wiki:
    wt_low = wt.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    if n_low in wt_low and wt not in [m[0] for m in matched]:
      matched.append((wt, wiki[wt]))

  lines.append(f"=== [{i}] {k} | n={n} | c={c} | r={r} | ll={item['ll']} | ey={ey}..{ly} | fy={fy} | al={al} | ex={ex} ===")
  if src:
    lines.append("  SRC: " + " ; ".join(src))
  if g_list:
    geo_str = ", ".join(f"{g['title']} ({g['dist']}m)" for g in g_list[:4])
    lines.append("  GEO: " + geo_str)
  if not matched:
    missing_wiki.append((k, n, c, r))
  for mt, mtxt in matched[:2]:
    clean = re.sub(r'<ref[^>]*>.*?</ref>', '', mtxt, flags=re.S)
    clean = re.sub(r'<ref[^>]*/>', '', clean)
    clean = re.sub(r'\[\[([^|\]]+\|)?([^\]]+)\]\]', r'\2', clean)
    clean = re.sub(r'\s+', ' ', clean)
    lines.append(f"  WIKI [{mt}]: {clean[:1400]}")

with open('tests/_c021_digest.txt', 'w', encoding='utf-8') as f:
  f.write('\n'.join(lines))

print("Total:", len(inp), "Missing direct wiki:", len(missing_wiki))
for m in missing_wiki:
  print("  MISSING:", m)
