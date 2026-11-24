import json

with open("tests/chunk015_wd_sparql.json", encoding="utf-8") as f:
  wd = json.load(f)
with open("tests/chunk015_wiki.json", encoding="utf-8") as f:
  inp = json.load(f)

lines = []
for idx, (k, meta) in enumerate(inp.items(), 1):
  n = meta["n"]
  ey = meta["ey"]
  rows = wd.get(k, [])
  by_item = {}
  for r in rows:
    it = r.get("item", "")
    rec = by_item.setdefault(
      it,
      {
        "label": r.get("itemLabel", ""),
        "desc": r.get("itemDesc", ""),
        "inc": set(),
        "admins": set(),
        "eswiki": r.get("eswiki", ""),
        "enwiki": r.get("enwiki", ""),
      },
    )
    if r.get("inception"):
      rec["inc"].add(r["inception"][:10])
    if r.get("adminLabel"):
      rec["admins"].add(r["adminLabel"])

  nl = n.lower()
  scored = []
  for it, rec in by_item.items():
    lbl = rec["label"].lower()
    score = 0
    if nl == lbl:
      score += 10
    elif nl in lbl:
      score += 5
    if rec["inc"]:
      score += 3
    if rec["eswiki"] or rec["enwiki"]:
      score += 2
    scored.append((score, it, rec))
  scored.sort(key=lambda x: -x[0])

  lines.append(f"{idx}. {k} | n={n} | ey={ey}")
  for score, it, rec in scored[:4]:
    qid = it.split("/")[-1]
    inc = sorted(rec["inc"])
    adm = sorted(rec["admins"])[:3]
    es = rec["eswiki"].split("/")[-1] if rec["eswiki"] else ""
    en = rec["enwiki"].split("/")[-1] if rec["enwiki"] else ""
    lines.append(
      f"   [{qid}] {rec['label']} ({rec['desc']}) | inc={inc} | adm={adm} | es={es} | en={en}"
    )

with open("tests/chunk015_wd_summary.txt", "w", encoding="utf-8") as f:
  f.write("\n".join(lines))
print("Wrote tests/chunk015_wd_summary.txt, lines:", len(lines))
