import json

data = json.load(open("tests/chunk026_research.json", encoding="utf-8"))
lines = []
for i, d in enumerate(data):
    lines.append(f"=== {i+1}. {d['key']} | n={d['n']} | c={d['c']} | r={d['r']} | ll={d['ll']} | ey={d['ey']} | ly={d['ly']} ===")
    if d.get("geo_es"):
        lines.append("GEO_ES: " + "; ".join(f"{g['title']} ({g['dist']}m)" for g in d["geo_es"]))
    if d.get("search_es"):
        lines.append("SEARCH_ES: " + "; ".join(f"{s['title']}: {s['snippet'][:120]}" for s in d["search_es"]))
    for t, ex in d.get("extracts", {}).items():
        clean = ex.replace("\n", " ")
        lines.append(f"EXTRACT [{t}]: {clean[:800]}")
    lines.append("")

with open("tests/chunk026_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Total lines:", len(lines))
