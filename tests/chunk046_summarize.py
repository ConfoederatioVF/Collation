import json
import os
import re

with open("tests/chunk046_input.json", "r", encoding="utf-8") as f:
    items = json.load(f)
with open("tests/chunk046_local.json", "r", encoding="utf-8") as f:
    local_hits = json.load(f)
with open("tests/chunk046_wiki.json", "r", encoding="utf-8") as f:
    wiki = json.load(f)

# Check if any chapter gazetteers/raw files mention these keys or names
extra_hits = {it["key"]: [] for it in items}
for root, dirs, files in os.walk("histmap/1.data_raw/population_regional/QUIPU"):
    for fn in files:
        if fn.endswith(".json") or fn.endswith(".json5"):
            if "gazetteer" in fn.lower() or "hgis" in fn.lower() or "raw_setts" in fn.lower():
                p = os.path.join(root, fn)
                try:
                    txt = open(p, "r", encoding="utf-8").read()
                except Exception:
                    continue
                for it in items:
                    n = it["n"]
                    if n and n != "None" and len(n) >= 4:
                        if n in txt:
                            # extract snippet around first occurrence
                            idx = txt.find(n)
                            snip = txt[max(0, idx-120):min(len(txt), idx+280)].replace("\n", " ")
                            extra_hits[it["key"]].append({"file": fn, "snip": snip})

lines = []
for idx, it in enumerate(items, 1):
    k = it["key"]
    lines.append(f"=== {idx}. {k} | n={it['n']} | c={it['c']} | r={it['r']} | ll={it['ll']} | ey={it['ey']} ly={it['ly']} | al={it.get('al')} | ex={it.get('ex')} ===")
    if local_hits.get(k):
        lines.append("  [LOCAL]: " + json.dumps(local_hits[k], ensure_ascii=False)[:800])
    if extra_hits.get(k):
        for eh in extra_hits[k][:3]:
            lines.append(f"  [EXTRA {eh['file']}]: {eh['snip']}")
    w = wiki.get(k, {})
    es_geo = [(g.get("title"), g.get("dist")) for g in w.get("es_geo", []) if isinstance(g, dict)]
    en_geo = [(g.get("title"), g.get("dist")) for g in w.get("en_geo", []) if isinstance(g, dict)]
    es_sr = [s.get("title") for s in w.get("es_search", []) if isinstance(s, dict)]
    en_sr = [s.get("title") for s in w.get("en_search", []) if isinstance(s, dict)]
    lines.append(f"  [ES_GEO]: {es_geo}")
    lines.append(f"  [EN_GEO]: {en_geo}")
    lines.append(f"  [ES_SR]: {es_sr} | [EN_SR]: {en_sr}")
    for pg in w.get("es_pages", []):
        title = pg.get("title", "")
        coords = pg.get("coordinates", [])
        ext = (pg.get("extract") or "").replace("\n", " ")[:1200]
        lines.append(f"  [PAGE {title} coords={coords}]: {ext}")
    lines.append("")

with open("tests/chunk046_digest.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Wrote tests/chunk046_digest.txt, lines:", len(lines))
