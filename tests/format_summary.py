import json

data = json.load(open("tests/wiki_chunk016.json", encoding="utf-8"))
lines = []
for k, v in data.items():
  geo = v.get("geo", [])
  sr = v.get("search", [])
  lines.append(f"=== {k} ===")
  lines.append(f"  GEO: {[(g['title'], int(g['dist'])) for g in geo[:4]]}")
  lines.append(f"  SR : {sr[:3]}")
  for t, ext in v.get("extracts", {}).items():
    lines.append(f"  --- [{t}] ---")
    lines.append("  " + ext.replace("\n", "\n  "))
  lines.append("")

with open("tests/summary_chunk016.txt", "w", encoding="utf-8") as f:
  f.write("\n".join(lines))
print("Lines:", len(lines))
