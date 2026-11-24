import json, os, glob, math

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\_c046_research.json", "r", encoding="utf-8") as f:
    data = json.load(f)

raw_sites_dir = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\QUIPU\_shared\sites_quipu_andes_cone\0.raw_sites"
print("raw_sites files:", [os.path.basename(x) for x in glob.glob(os.path.join(raw_sites_dir, "*"))])

for idx, start in enumerate([0, 30, 60], 1):
    out = []
    for i, r in enumerate(data[start:start+30], start+1):
        out.append(f'=== {i}. {r["key"]} | n={r["n"]} | c={r["c"]} | ll={r["ll"]} | ey={r["ey"]} | ly={r["ly"]} | al={r["al"]} | ex={r["ex"]} ===')
        if r["local"]:
            for loc in r["local"]:
                out.append("  [LOCAL] " + json.dumps(loc, ensure_ascii=False)[:500])
        if r["geo"].get("es") or r["geo"].get("en"):
            out.append("  [GEO_ES] " + ", ".join(f'{g["title"]} ({g["dist"]}m)' for g in r["geo"].get("es", [])))
            out.append("  [GEO_EN] " + ", ".join(f'{g["title"]} ({g["dist"]}m)' for g in r["geo"].get("en", [])))
        for lang in ("es", "en"):
            for p in r["wiki"].get(lang, []):
                ext = p.get("extract", "").replace("\n", " ")
                out.append(f'  [WIKI_{lang.upper()}: {p["title"]} coords={p.get("coords")}] {ext[:1200]}')
        out.append("")
    with open(rf"f:\Active Projects\Project 1509 - SVEA\tests\_c046_part{idx}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
print("Wrote parts 1-3")
