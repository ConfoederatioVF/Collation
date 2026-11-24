import json

inp = json.load(open("tests/_c030_input.json", encoding="utf-8"))
res = json.load(open("tests/_c030_research.json", encoding="utf-8"))

for idx, start in enumerate([0, 30, 60], 1):
  lines = []
  for i in range(start, start + 30):
    it = inp[i]
    k = it["key"]
    r = res[k]
    lines.append(
      f"=== [{i}] {k} | n={it['n']} | c={it['c']} | r={it['r']} | ll={it['ll']} | ey={it['ey']} | ly={it['ly']} | al={it.get('al')} | ex={it.get('ex')} ==="
    )
    if r.get("local"):
      lines.append("  LOCAL: " + " || ".join(r["local"][:3]))
    for w in r.get("es", [])[:2]:
      txt = w["extract"].replace("\n", " ")[:1200]
      lines.append(f"  ES [{w['title']} ({w['how']})]: {txt}")
    for w in r.get("en", [])[:1]:
      txt = w["extract"].replace("\n", " ")[:600]
      lines.append(f"  EN [{w['title']} ({w['how']})]: {txt}")
    lines.append("")
  with open(f"tests/_c030_part{idx}.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Wrote 3 parts")
