import json
d = json.load(open("tests/wp_chunk44.json", encoding="utf-8"))
lines = []
for i, r in enumerate(d, 1):
    lines.append(f"=== {i:02d}. {r['key']} | chosen={r.get('chosen')} | final={r.get('title_final')}")
    lines.append("  hits: " + str(r["hits"][:4]))
    lines.append("  intro: " + (r.get("intro") or "")[:400].replace("\n", " "))
    if r.get("infobox"):
        lines.append("  box: " + " || ".join(r["infobox"][:6]))
open("tests/wp_summary.txt", "w", encoding="utf-8").write("\n".join(lines))
print("lines:", len(lines))
