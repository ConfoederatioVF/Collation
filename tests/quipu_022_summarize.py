import json

d = json.load(open(r"f:\Active Projects\Project 1509 - SVEA\tests\quipu_022_wiki.json", encoding="utf-8"))
lines = []
for i, x in enumerate(d):
    geo = ", ".join(f"{g['title']}({int(g['dist'])}m)" for g in x["geo_es"][:3])
    srch = ", ".join(x["search_es"][:3])
    lines.append(f"=== [{i}] {x['key']} | n={x['n']} | c={x['c']} | r={x['r']} | ll={x['ll']} | ey={x['ey']}..{x['ly']} | al={x['al']} ===")
    lines.append(f"  GEO: {geo}")
    lines.append(f"  SRC: {srch}")
    for t, ex in x["extracts"].items():
        ex1 = ex.replace("\n", " ")[:450]
        lines.append(f"  EXT[{t}]: {ex1}")

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\quipu_022_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Lines:", len(lines))
