import glob, json, math, os, re, urllib.parse

with open("tests/q018_local_and_wd.json", encoding="utf-8") as f:
    data = json.load(f)
with open("tests/q018_wiki_ext.json", encoding="utf-8") as f:
    wiki = json.load(f)

# Load raw_setts for admin1/admin2 context
raw_by_country = {}
for fn in glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/raw_setts_*.json"):
    d = json.load(open(fn, encoding="utf-8"))
    setts = d.get("settlements", d)
    if isinstance(setts, dict):
        for k, v in setts.items():
            if isinstance(v, dict):
                raw_by_country[k] = v

# Also load arch raw sites for any pre-columbian / archaeological settlements
raw_arch_hits = {}
arch_files = glob.glob("histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites/*.json")
items_list = list(data.items())
for afn in arch_files:
    try:
        ad = json.load(open(afn, encoding="utf-8"))
    except Exception:
        continue
    rows = ad if isinstance(ad, list) else ad.get("features", ad.get("sites", ad.get("data", [])))
    if not isinstance(rows, list):
        continue
    bname = os.path.basename(afn)
    for row in rows:
        if not isinstance(row, dict):
            continue
        geom = row.get("geometry") or {}
        coords = geom.get("coordinates") if isinstance(geom, dict) else None
        props = row.get("properties") if isinstance(row.get("properties"), dict) else row
        rlat = props.get("lat") or props.get("latitude") or (coords[1] if coords and len(coords) >= 2 else None)
        rlon = props.get("lng") or props.get("lon") or props.get("longitude") or (coords[0] if coords and len(coords) >= 2 else None)
        if rlat is None or rlon is None:
            continue
        try:
            rlat, rlon = float(rlat), float(rlon)
        except Exception:
            continue
        for k, rec in items_list:
            ilat, ilon = rec["input"]["ll"]
            if abs(ilat - rlat) < 0.02 and abs(ilon - rlon) < 0.02:
                summary = {kk: vv for kk, vv in props.items() if kk in ("name", "sitio", "site_name", "nombre", "period", "periodo", "culture", "cultura", "chronology", "cronologia", "date", "age", "bp", "type", "tipo", "municipio", "departamento", "provincia")}
                if summary:
                    raw_arch_hits.setdefault(k, []).append((bname, summary))

missing_wiki = []
lines_all = []
for idx, (k, rec) in enumerate(items_list):
    inp = rec["input"]
    buf = []
    buf.append(f"=== [{idx+1}] {k} ===")
    buf.append(f"INPUT: n={inp['n']} | c={inp['c']} | r={inp['r']} | ll={inp['ll']} | ey={inp['ey']} | ly={inp['ly']} | al={inp.get('al')}")
    if k in raw_by_country:
        rv = raw_by_country[k]
        buf.append(f"RAW_SETT: admin1={rv.get('admin1')} | admin2={rv.get('admin2')} | other={rv.get('other_names')} | src={rv.get('sources')}")
    for g in rec["gaz_matches"][:3]:
        buf.append(f"GAZ({g['dist']}): {g['gaz']} | k={g['k']} | name={g['name']} | sub={g['subregion']} | alt={g['alt']} | src={g['source']} | notes={g['notes']} | desc={g['desc']} | pops={g['pop_keys']}")
    for h in rec["hgis_matches"][:4]:
        buf.append(f"HGIS: {h.get('name')} (mod={h.get('modern_name')}) | var={h.get('variants')} | cat={h.get('categoria')} | prov={h.get('colonial_province')} | part={h.get('colonial_partido')} | yrs={h.get('start_year')}-{h.get('end_year')} | coords={h.get('coords')}")
    for a in rec["arch_matches"][:3]:
        buf.append(f"ARCH_DOC: {json.dumps(a, ensure_ascii=False)[:300]}")
    for fn, sm in raw_arch_hits.get(k, [])[:3]:
        buf.append(f"ARCH_RAW({fn}): {json.dumps(sm, ensure_ascii=False)[:250]}")

    n_low = inp["n"].lower().split("(")[0].strip()
    wd_shown = []
    ext_shown = set()
    for w in rec["wd"]:
        lbl = w.get("placeLabel", "")
        es = w.get("eswiki", "")
        en = w.get("enwiki", "")
        inc = w.get("inception", "")
        adm = w.get("adminLabel", "")
        desc = w.get("placeDesc", "")
        if es or en or inc or (n_low in lbl.lower()):
            wd_shown.append(f"WD: {lbl} ({desc}) | adm={adm} | inc={inc} | es={es} | en={en}")
            if es:
                t = urllib.parse.unquote(es.split("/wiki/")[-1]).replace("_", " ")
                if t in wiki["es"] and t not in ext_shown:
                    ext_shown.add(t)
                    txt = re.sub(r"\s+", " ", wiki["es"][t])[:1100]
                    wd_shown.append(f"  ESWIKI[{t}]: {txt}")
            if en:
                t = urllib.parse.unquote(en.split("/wiki/")[-1]).replace("_", " ")
                if t in wiki["en"] and t not in ext_shown:
                    ext_shown.add(t)
                    txt = re.sub(r"\s+", " ", wiki["en"][t])[:900]
                    wd_shown.append(f"  ENWIKI[{t}]: {txt}")
    if not ext_shown:
        missing_wiki.append(k)
    buf.extend(wd_shown[:8])
    buf.append("")
    lines_all.append("\n".join(buf))

for part in range(3):
    fn = f"tests/q018_dossier_{part+1}.txt"
    with open(fn, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_all[part*30:(part+1)*30]))
    print(f"Wrote {fn}")
print(f"Missing wiki extracts ({len(missing_wiki)}):", missing_wiki)
