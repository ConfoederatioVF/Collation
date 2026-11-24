import json

fp = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\_shared\settlement_sources\aus_official_ucl_lga_timeseries.json"
d = json.load(open(fp, encoding="utf-8"))
box = d["settlements"] if "settlements" in d else d
rec = box["Perth_(Tas.)-Tasmania-UCL-Australia"]
print("BEFORE:", rec["population"])
clean_pop = {y: v for y, v in rec["population"].items() if int(v) <= 20000}
rec["population"] = clean_pop
print("AFTER:", rec["population"])
with open(fp, "w", encoding="utf-8") as fh:
  json.dump(d, fh, ensure_ascii=False, indent=2)
print("Saved clean Perth (Tas.) record.")
