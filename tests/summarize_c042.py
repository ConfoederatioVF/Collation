import json

with open("tests/tmp_c042_wiki.json", "r", encoding="utf-8") as f:
    w = json.load(f)
with open("tests/tmp_c042_local.json", "r", encoding="utf-8") as f:
    l = json.load(f)

lines = []
for i, (k, v) in enumerate(w.items(), 1):
    inp = v["input"]
    geo = [(g["title"], round(g["dist"])) for g in v.get("es_geo", [])[:2]]
    srch = v.get("es_search", [])[:2]
    loc = l.get(k, [])
    lines.append(f"{i:2d}. {k} | ey={inp['ey']} ly={inp['ly']} | r={inp['r']} | ll={inp['ll']} | al={inp.get('al', [])} | ex={inp.get('ex', [])}")
    if loc:
        for h in loc[:3]:
            lines.append(f"    LOCAL[{h.get('_file')} d={h.get('_dist_km')}km]: " + json.dumps({kk: vv for kk, vv in h.items() if not kk.startswith('_')}, ensure_ascii=False)[:300])
    if geo or srch:
        lines.append(f"    WIKI geo={geo} | srch={srch}")
    for t, ex in v.get("extracts", {}).items():
        lines.append(f"    EX[{t}]: {ex[:250].replace(chr(10), ' ')}")

with open("tests/tmp_c042_digest.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Wrote {len(lines)} lines to tests/tmp_c042_digest.txt")
