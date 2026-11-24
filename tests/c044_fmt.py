import json

with open("tests/c044_dossier.json", "r", encoding="utf-8") as f:
  d = json.load(f)

keys = list(d.keys())
for p in range(3):
  chunk = keys[p * 30:(p + 1) * 30]
  lines = []
  for i, k in enumerate(chunk, p * 30 + 1):
    it = d[k]["input"]
    lines.append(f"=== {i}. {k} | n={it['n']} | c={it['c']} | r={it['r']} | ll={it['ll']} | ey={it['ey']} | ly={it['ly']} | al={it.get('al')} ===")
    if d[k]["local"]:
      lines.append("LOCAL: " + json.dumps(d[k]["local"], ensure_ascii=False)[:1500])
    if d[k]["es_geo"]:
      lines.append("ES_GEO: " + ", ".join(f"{x['title']} ({x['dist']}m)" for x in d[k]["es_geo"]))
    if d[k]["es_search"]:
      lines.append("ES_SEARCH: " + ", ".join(d[k]["es_search"]))
    if d[k]["en_geo"]:
      lines.append("EN_GEO: " + ", ".join(f"{x['title']} ({x['dist']}m)" for x in d[k]["en_geo"]))
    for title, info in d[k]["extracts"].items():
      ext = info["extract"].replace("\n", " ")[:1800]
      lines.append(f"  [{title}]: {ext}")
    lines.append("")
  with open(f"tests/c044_part{p + 1}.txt", "w", encoding="utf-8") as out:
    out.write("\n".join(lines))
print("Wrote 3 parts")
