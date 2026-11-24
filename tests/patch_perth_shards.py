import glob, json, os

DIRS = [
  r"f:\Active Projects\Project 1509 - SVEA\histmap\3.data_transform\population_Stadester.transform\stadester",
  r"f:\Active Projects\Project 1509 - SVEA\histmap\5.data_visualisation\stadester\stadester_2.0",
  r"f:\Active Projects\Project 1436 - Dataview\data\stadester\stadester_2.0",
]

for d in DIRS:
  for fp in sorted(glob.glob(os.path.join(d, "13_austral*.json"))):
    data = json.load(open(fp, encoding="utf-8"))
    changed = False
    for k, v in data.items():
      if "perth" in k.lower() and isinstance(v, dict):
        co = v.get("coords") or []
        if len(co) >= 2 and float(co[0]) < -38.0:
          pop = v.get("population") or {}
          new_pop = {y: p for y, p in pop.items() if float(p) <= 20000}
          if len(new_pop) != len(pop):
            print(f"Patched {k} in {fp}: {len(pop)} -> {len(new_pop)} years (max {max(new_pop.values()) if new_pop else 0})")
            v["population"] = new_pop
            changed = True
    if changed:
      with open(fp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
