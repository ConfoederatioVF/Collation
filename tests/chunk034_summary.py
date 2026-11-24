import json, glob, os

d = json.load(open('tests/chunk034_dossier.json', encoding='utf-8'))

# Check hgis_indias_colonial_raw.json
hgis = json.load(open('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json', encoding='utf-8'))
hgis_setts = hgis.get('settlements', {})

# Check all *_source_ledger.json5
ledgers = glob.glob('histmap/1.data_raw/population_regional/QUIPU/**/*_source_ledger.json5', recursive=True)
ledger_txt = {os.path.basename(f): open(f, encoding='utf-8', errors='ignore').read() for f in ledgers}

lines = []
for i, (k, v) in enumerate(d.items(), 1):
    inp = v['input']
    locs = v['local']
    wds = v['wd']
    lines.append(f"{i:02d}. {k} | n={inp['n']} | c={inp['c']} | r={inp['r']} | ll={inp['ll']} | ey={inp['ey']}..{inp['ly']} | ex={inp.get('ex')} | al={inp.get('al')}")
    for fn, rec in locs:
        keep = {kk: vv for kk, vv in rec.items() if kk not in ('coords', 'country', 'key', 'region_id', 'region')}
        lines.append(f"    LOCAL[{fn}]: {json.dumps(keep, ensure_ascii=False)}")
    if isinstance(wds, list) and wds:
        for w in wds[:4]:
            if w['lbl'] or w['P571'] or w['eswiki']:
                lines.append(f"    WD: {w['qid']} ({int(w['dist_m'])}m) lbl={w['lbl']!r} [{w['desc']}] P571={w['P571']} P1448={w['P1448']} es={w['eswiki']!r} en={w['enwiki']!r}")
    # Also check raw HGIS by key or name
    if isinstance(hgis_setts, dict) and k in hgis_setts:
        lines.append(f"    HGIS: {json.dumps(hgis_setts[k], ensure_ascii=False)}")

open('tests/chunk034_summary.txt', 'w', encoding='utf-8').write('\n'.join(lines))
print('Lines written:', len(lines))
