import json

data = json.load(open("tests/tmp_chunk037_research.json", encoding="utf-8"))
for idx_batch, start in enumerate([0, 30, 60], 1):
  lines = []
  for i, it in enumerate(data[start:start + 30], start):
    lines.append(
      f"=== [{i}] {it['key']} | n={it['n']} | c={it['c']} | r={it['r']} | ll={it['ll']} | ey={it['ey']} ly={it['ly']} | al={it['al']} | ex={it['ex']} ==="
    )
    if it["local"]:
      for loc in it["local"][:6]:
        lines.append(
          f"  LOCAL({loc.get('file')}): key={loc.get('key')} name={loc.get('name')} other={loc.get('other_names')} fy={loc.get('foundation_year')} notes={str(loc.get('notes'))[:220]} src={loc.get('sources')}"
        )
    lines.append(f"  ES_GEO: {it.get('es_geo')}")
    lines.append(
      f"  ES_SEARCH: {[(s['title'], s['snippet'][:120]) for s in it.get('es_search', [])]}"
    )
    for t, ex in it.get("es_extracts", {}).items():
      txt = " ".join(ex.get("extract", "").split())
      lines.append(f"  ES_EX[{t}] {ex.get('coords')}: {txt[:1100]}")
    lines.append(f"  EN_GEO: {it.get('en_geo')}")
    for t, ex in it.get("en_extracts", {}).items():
      txt = " ".join(ex.get("extract", "").split())
      lines.append(f"  EN_EX[{t}] {ex.get('coords')}: {txt[:600]}")
    lines.append("")
  open(f"tests/tmp_digest_{idx_batch}.txt", "w", encoding="utf-8").write(
    "\n".join(lines)
  )
print("Wrote 3 digest files")
