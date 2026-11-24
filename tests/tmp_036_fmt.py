import json

data = json.load(open("tests/tmp_036_data.json", encoding="utf-8"))
for chunk_idx in range(3):
    sub = data[chunk_idx*30:(chunk_idx+1)*30]
    lines = []
    for i, d in enumerate(sub):
        lines.append(f'=== [{chunk_idx*30+i}] {d["key"]} | n={d["n"]} | c={d["c"]} | r={d["r"]} | ll={d["ll"]} | ey={d["ey"]} | ly={d["ly"]} | al={d["al"]} ===')
        for l in d.get("local", []):
            lines.append(f"  LOCAL: {l}")
        lines.append(f'  GEO: {d.get("es_geo", [])}')
        lines.append(f'  SRCH: {d.get("es_search", [])}')
        for t, ex in d.get("es_extracts", {}).items():
            txt = ex["extract"].replace("\n", " ")
            lines.append(f'  WIKI[{t}] coords={ex.get("coords")}: {txt[:1200]}')
    with open(f"tests/tmp_036_part{chunk_idx}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
print("Wrote 3 parts")
