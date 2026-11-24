import json

with open("tests/_c055_research.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def fmt_list(lst, out):
    for idx, item in lst:
        out.append(f"=== [{idx}] {item['key']} | n={item['n']} | c={item['c']} | r={item['r']} | ll={item['ll']} | ey={item['ey']} | ly={item['ly']} | al={item['al']} ===")
        for lang in ("es", "en"):
            for src in ("geosearch", "search"):
                entries = item[lang].get(src, [])
                if entries:
                    out.append(f"  [{lang}.{src}]")
                    for e in entries[:3]:
                        ext = (e.get("extract") or "").replace("\n", " ")[:450]
                        coords = e.get("coords")
                        out.append(f"    - {e.get('title')} {coords}: {ext}")

for part, rng in [(1, range(0, 30)), (2, range(30, 60)), (3, range(60, 90))]:
    out = []
    fmt_list([(i, data[i]) for i in rng], out)
    with open(f"tests/_c055_part{part}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
print("Formatted 3 parts")
