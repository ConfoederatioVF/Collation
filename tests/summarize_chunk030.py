import json
import os
import glob

with open('f:/Active Projects/Project 1509 - SVEA/tests/chunk030_wiki.json', 'r', encoding='utf-8') as f:
  wiki_data = json.load(f)

# Search local QUIPU settlement_sources and sites_quipu_andes_cone for exact matches on names/coords
targets = {item['key']: item for item in wiki_data}
local_hits = {k: [] for k in targets}

search_dirs = [
  'f:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone',
  'f:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources',
]

# Also check chapter gazetteer json5/json/csv files
for sub in ['1.pre_columbian', '2.colonial', '3.post_independence']:
  p = f'f:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_regional/QUIPU/{sub}'
  if os.path.exists(p):
    search_dirs.append(p)

# Collect text-like files under 20MB
files = []
for d in search_dirs:
  for root, _, fns in os.walk(d):
    if 'raw' in root.split(os.sep) and 'raw_sources' not in root:
      continue
    for fn in fns:
      if fn.endswith(('.json', '.json5', '.csv', '.tsv', '.geojson')):
        fp = os.path.join(root, fn)
        if os.path.getsize(fp) < 25 * 1024 * 1024:
          files.append(fp)

needles = {}
for item in wiki_data:
  n = item['n']
  if len(n) >= 5:
    needles[item['key']] = n

for fp in files:
  try:
    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
      txt = f.read()
  except Exception:
    continue
  rel = os.path.relpath(fp, 'f:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_regional/QUIPU')
  for key, needle in needles.items():
    idx = txt.find(needle)
    if idx != -1:
      snippet = txt[max(0, idx-120):min(len(txt), idx+280)].replace('\n', ' ')
      local_hits[key].append({'file': rel, 'snippet': snippet})

with open('f:/Active Projects/Project 1509 - SVEA/tests/chunk030_summary.txt', 'w', encoding='utf-8') as out:
  for i, item in enumerate(wiki_data):
    out.write(f"=== [{i}] {item['key']} | n={item['n']} | c={item['c']} | r={item['r']} | ey={item['ey']}..{item['ly']} | al={item['al']} | ex={item['ex']} ===\n")
    for w in item['wiki']:
      out.write(f"  [WIKI] {w['title']}\n")
      if w['infobox']:
        out.write("    INFOBOX: " + w['infobox'].replace('\n', ' || ') + "\n")
      out.write("    EXTRACT: " + w['extract'].replace('\n', ' ')[:700] + "\n")
    for lh in local_hits[item['key']][:3]:
      out.write(f"  [LOCAL:{lh['file']}] {lh['snippet']}\n")
    out.write("\n")

print(f"Scanned {len(files)} files, wrote summary.")
