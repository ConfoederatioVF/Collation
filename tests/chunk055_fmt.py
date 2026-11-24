import json

items = json.load(open("tests/chunk055_input.json", encoding="utf-8"))
loc = json.load(open("tests/chunk055_local.json", encoding="utf-8"))
wiki = json.load(open("tests/chunk055_wiki.json", encoding="utf-8"))

for part_idx in range(3):
    chunk = items[part_idx * 30 : (part_idx + 1) * 30]
    lines = []
    for i, it in enumerate(chunk, part_idx * 30 + 1):
        k = it["key"]
        al = it.get("al")
        lines.append(f"=== [{i}] {k} | n={it['n']} | c={it['c']} | r={it['r']} | ll={it['ll']} | ey={it['ey']} | ly={it['ly']} | al={al} ===")
        for lh in loc.get(k, [])[:4]:
            lines.append("  LOCAL(" + lh["file"] + "): " + json.dumps(lh["data"], ensure_ascii=False))
        w = wiki.get(k, {})
        if w.get("es_geo"):
            lines.append("  ES_GEO: " + ", ".join(f"{g['title']} ({int(g['dist'])}m)" for g in w["es_geo"][:4]))
        if w.get("en_geo"):
            lines.append("  EN_GEO: " + ", ".join(f"{g['title']} ({int(g['dist'])}m)" for g in w["en_geo"][:3]))
        if w.get("es_search"):
            lines.append("  ES_SEARCH: " + ", ".join(s["title"] for s in w["es_search"][:4]))
        for t, ex in w.get("extracts", {}).items():
            txt = ex["extract"].replace("\n", " ")[:1500]
            lines.append(f"  EXT[{t}] coords={ex.get('coords')}: {txt}")
        lines.append("")
    with open(f"tests/chunk055_part{part_idx + 1}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
print("Wrote 3 parts")
