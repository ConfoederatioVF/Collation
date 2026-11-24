import json

data = json.load(open("tests/quipu_wiki_cache.json", encoding="utf-8"))
keys = list(data.keys())

for part, sl in [(1, slice(0, 45)), (2, slice(45, 90))]:
  lines = []
  for idx, k in enumerate(keys[sl], start=(0 if part == 1 else 45)):
    d = data[k]
    inp = d["input"]
    lines.append(f"## [{idx}] {k}")
    lines.append(f"- n: `{inp['n']}` | c: `{inp['c']}` | r: `{inp['r']}` | ll: `{inp['ll']}` | ey: `{inp['ey']}` | ly: `{inp['ly']}` | al: `{inp.get('al')}` | ex: `{inp.get('ex')}`")
    lines.append(f"- geo_es: {[(g.get('title'), g.get('dist')) for g in d['geo_es'][:3]]}")
    lines.append(f"- search_es: {d['search_es'][:3]}")
    for ek, ev in d["extracts"].items():
      txt = ev["extract"].replace("\n", " ")[:1200]
      lines.append(f"  - **{ek}** (coords={ev.get('coords')}): {txt}")
    lines.append("")
  with open(f"tests/summary_{part}.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Wrote summary_1.md and summary_2.md")
