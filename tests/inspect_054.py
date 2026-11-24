import json

with open("tests/quipu_054_lookup.json", "r", encoding="utf-8") as f:
    out = json.load(f)

lines = []
for i, (k, entries) in enumerate(out.items(), 1):
    lines.append(f"=== {i}. {k} ===")
    for fn, v in entries:
        srcs = v.get("sources", [])
        pop = v.get("population", {})
        yrs = sorted(pop.keys(), key=lambda x: int(x)) if isinstance(pop, dict) else []
        yr_range = f"{yrs[0]}..{yrs[-1]} ({len(yrs)} pts)" if yrs else ""
        extra = {
            kk: vv for kk, vv in v.items()
            if kk not in ("population", "sources", "coords", "key", "name", "country", "region_id", "region", "population_scope")
        }
        reg = v.get("region")
        coords = v.get("coords")
        lines.append(f"  [{fn}] reg={reg} coords={coords} yrs={yr_range} srcs={srcs} extra={json.dumps(extra, ensure_ascii=False)}")

with open("tests/quipu_054_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Wrote", len(lines), "lines")
