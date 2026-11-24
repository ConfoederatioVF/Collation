import json
import re

with open("tests/chunk037_research.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("tests/chunk037_digest.txt", "w", encoding="utf-8") as out:
    for i, s in enumerate(data):
        out.write(f"=== [{i+1}] {s['key']} | n={s['n']} | c={s['c']} | r={s['r']} | ll={s['ll']} | ey={s['ey']} | ly={s['ly']} ===\n")
        geos = [(g["title"], round(g["dist"])) for g in s.get("es_geo", [])]
        out.write(f"  geo: {geos}\n")
        out.write(f"  search: {s.get('es_search', [])}\n")
        for k, v in s.get("extracts", {}).items():
            txt = v.get("extract", "").replace("\n", " ")
            coords = v.get("coords")
            out.write(f"  [{k}] coords={coords}\n    {txt[:600]}\n")
            hits = re.findall(r"[^.]*(?:\b1[4-9]\d{2}\b|\b20[0-2]\d\b|fundad|cread|denomin|llamad|originalmente|antiguamente|nombre)[^.]*\.", txt, re.I)
            if hits:
                out.write("    HITS: " + " | ".join(hits[:6])[:900] + "\n")
        out.write("\n")
print("Wrote digest")
