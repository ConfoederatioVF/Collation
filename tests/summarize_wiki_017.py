import json
import re

with open("tests/chunk017_wiki.json", "r", encoding="utf-8") as f:
    data = json.load(f)

lines = []
missing_geo = []
for idx, it in enumerate(data):
    lines.append(f"=== [{idx+1}/90] {it['key']} | n={it['n']} | c={it['c']} | r={it['r']} | ll={it['ll']} | ey={it['ey']}..{it['ly']} | al={it['al']} | ex={it['ex']} ===")
    geo = it.get("es_geo", [])
    if geo:
        lines.append("  GEO: " + ", ".join(f"{g['title']} ({round(g['dist'])}m)" for g in geo[:3]))
    else:
        lines.append("  GEO: NONE")
        missing_geo.append(it["key"])
    sr = it.get("es_sr", [])
    lines.append("  SR: " + ", ".join(sr[:3]))
    for title, pinfo in it.get("es_pages", {}).items():
        ext = (pinfo.get("extract") or "").replace("\n", " ")
        inf = pinfo.get("infobox") or ""
        # Extract infobox lines matching useful fields
        inf_hits = []
        for l in inf.splitlines():
            if re.search(r"(fundaci|creaci|nombre|apodo|lema|entidad|departamento|provincia|estado|cant[oó]n|distrito|municipio|parroquia|cultura|periodo|cronolog|antiguo)", l, re.I):
                inf_hits.append(l.strip()[:120])
        lines.append(f"  PAGE [{title}]:")
        if inf_hits:
            lines.append("    INFOBOX: " + " | ".join(inf_hits[:8]))
        lines.append("    EXTRACT: " + ext[:700])
    lines.append("")

with open("tests/chunk017_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Wrote summary. Missing geo count: {len(missing_geo)}")
print("Missing geo keys:", missing_geo)
