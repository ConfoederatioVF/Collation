import json, os, math

digest = json.load(open("tests/quipu_023_digest.json", encoding="utf-8"))
wiki_full = json.load(open("tests/quipu_023_wiki_full.json", encoding="utf-8"))

quipu_dir = "histmap/1.data_raw/population_regional/QUIPU"
all_recs = []
for root, dirs, files in os.walk(quipu_dir):
    for fn in files:
        if fn.endswith("_settlements.json"):
            fp = os.path.join(root, fn)
            data = json.load(open(fp, encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    c = v.get("coords")
                    if isinstance(c, list) and len(c) == 2:
                        all_recs.append((k, os.path.relpath(fp, quipu_dir), v))

def hav(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin(math.radians(lat2-lat1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2
    return 2*R*math.asin(math.sqrt(a))

for d in digest:
    if d["local"].get("missing_in_settlements_json"):
        lat, lng = d["input"]["ll"]
        near = []
        for k, fp, v in all_recs:
            c = v["coords"]
            dkm1 = hav(lat, lng, c[0], c[1])
            dkm2 = hav(lat, lng, c[1], c[0])
            dkm = min(dkm1, dkm2)
            if dkm < 5.0:
                near.append((round(dkm, 2), k, fp, v.get("notes"), v.get("source"), v.get("other_names"), v.get("earliest_year"), v.get("latest_year")))
        d["local_near"] = near

for b_idx, (s, e) in enumerate([(0,30), (30,60), (60,90)], 1):
    lines = []
    for idx in range(s, e):
        d = digest[idx]
        it = d["input"]
        lines.append(f'=== [{idx+1}] {it["key"]} | n={it["n"]} | c={it["c"]} | r={it["r"]} | ll={it["ll"]} | ey={it["ey"]} | ly={it["ly"]} | p={it["p"]} | al={it.get("al",[])}')
        lines.append("  LOCAL: " + json.dumps(d.get("local_near") or d["local"], ensure_ascii=False))
        lines.append("  ES_GEO: " + json.dumps(d.get("es_geo", []), ensure_ascii=False))
        wf = wiki_full.get(it["key"], {})
        for title, info in wf.items():
            if isinstance(info, dict):
                txt = info.get("text", "").replace("\n", " ")
                lines.append(f'  WIKI [{title}] coords={info.get("coords")}: {txt[:2000]}')
        lines.append("")
    open(f"tests/batch{b_idx}.txt", "w", encoding="utf-8").write("\n".join(lines))
print("Wrote batch1.txt, batch2.txt, batch3.txt")
