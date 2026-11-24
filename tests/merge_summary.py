import json

with open("tests/chunk023_wiki.json", encoding="utf-8") as f:
    wiki = json.load(f)
with open("tests/chunk023_local.json", encoding="utf-8") as f:
    loc = json.load(f)

lines = []
for i, (k, v) in enumerate(wiki.items(), 1):
    n = v.get("n")
    c = v.get("c")
    ll = v.get("ll")
    lines.append(f"=== {i}. {k} | n={n} | c={c} | ll={ll} ===")
    if k in loc:
        for fn, meta in loc[k]:
            lines.append("  LOCAL [" + fn + "]: " + json.dumps(meta, ensure_ascii=False))
    if v.get("es_geo"):
        lines.append("  GEO: " + ", ".join(f"{g['title']} ({g['dist']}m)" for g in v["es_geo"]))
    if v.get("es_search"):
        lines.append("  SEARCH: " + ", ".join(v["es_search"]))
    for t, ex in v.get("es_extracts", {}).items():
        clean_ex = ex.replace("\n", " ")[:900]
        lines.append(f"  [{t}]: {clean_ex}")
    lines.append("")

with open("tests/chunk023_merged.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Lines written:", len(lines))
