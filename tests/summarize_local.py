import json

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\chunk016_local_matches.json", encoding="utf-8") as f:
    data = json.load(f)

lines = []
for idx, x in enumerate(data):
    lat, lng = x["ll"]
    h_exact = [h for h in x["hgis"] if abs(h["coords"][0] - lat) < 0.015 and abs(h["coords"][1] - lng) < 0.015]
    h_str = "; ".join(f"{h['name']}(mod:{h['modern_name']},v:{h['variants']},prov:{h['prov']}/{h['partido']},st:{h['start']})" for h in h_exact)
    r_exact = [r for r in x["raw"] if abs(r["coords"][0] - lat) < 0.01 and abs(r["coords"][1] - lng) < 0.01]
    r_str = "; ".join(f"{r['name']}({r['admin1']}/{r['admin2']},alt:{r['other_names']})" for r in r_exact)
    c_str = "; ".join(f"{c['file'].split('_')[0]}:{c['name']}(alt:{c['other_names']})" for c in x["chap"])
    lines.append(f"{idx+1:02d}. {x['input_key']} [{x['ey']}..{x['ly']}] ll={x['ll']}")
    if h_str:
        lines.append(f"   HGIS: {h_str}")
    if r_str:
        lines.append(f"   RAW:  {r_str}")
    if c_str:
        lines.append(f"   CHAP: {c_str}")

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\chunk016_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Wrote", len(lines), "lines")
