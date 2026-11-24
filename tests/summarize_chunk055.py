import glob
import json
import math
import sys

sys.path.insert(0, "tests")
import lookup_chunk055

items = lookup_chunk055.INPUT_DATA
wiki = json.load(open("tests/chunk055_wiki.json", encoding="utf-8"))
hgis = json.load(open("histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json", encoding="utf-8"))["settlements"]

raw_files = glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw_setts_*.json")
raw_rows = []
for rf in raw_files:
    d = json.load(open(rf, encoding="utf-8"))
    rows = d.get("settlements", d) if isinstance(d, dict) else d
    if isinstance(rows, dict):
        rows = list(rows.values())
    for r in rows:
        if isinstance(r, dict):
            raw_rows.append(r)

def dist_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    return 2 * R * math.asin(math.sqrt(math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2))

lines = []
for idx, it in enumerate(items, 1):
    k = it["key"]
    lat, lon = it["ll"]
    lines.append(f"[{idx}] {k} | n={it['n']} | c={it['c']} | r={it['r']} | ll=({lat},{lon}) | ey={it['ey']} ly={it['ly']} | al={it.get('al',[])}")
    # Raw match
    for r in raw_rows:
        rlat = r.get("lat") or (r.get("coords")[0] if isinstance(r.get("coords"), list) else None)
        rlon = r.get("lon") or r.get("lng") or (r.get("coords")[1] if isinstance(r.get("coords"), list) else None)
        if rlat is not None and rlon is not None:
            if dist_km(lat, lon, float(rlat), float(rlon)) < 2.0:
                nm = r.get("name", "")
                if it["n"].split()[0].lower() in nm.lower() or r.get("key") == k:
                    meta = {kk: vv for kk, vv in r.items() if kk not in ("pop", "population", "populations", "years", "urban_population")}
                    lines.append(f"  RAW: {meta}")
                    break
    # HGIS match
    for hk, hv in hgis.items():
        c = hv.get("coords")
        if c and c[0] is not None and dist_km(lat, lon, c[0], c[1]) < 3.0:
            lines.append(f"  HGIS({hk}): name={hv.get('name')} mod={hv.get('modern_name')} var={hv.get('variants')} prov={hv.get('colonial_province')} part={hv.get('colonial_partido')} sy={hv.get('start_year')} ey={hv.get('end_year')} src={hv.get('sources')}")
    # Wiki match
    w = wiki.get(k, {})
    for g in w.get("geosearch", [])[:2]:
        lines.append(f"  WIKI_GEO: {g['title']} ({g['dist_m']}m)")
    for t, ex in w.get("extracts", {}).items():
        txt = (ex.get("extract") or "").replace("\n", " ")
        lines.append(f"  WIKI_EX[{t}] (d={ex.get('dist_km')}km): {txt[:500]}")
    lines.append("")

with open("tests/chunk055_dossier.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Lines:", len(lines))
