import os, json, sys

# Read all settlement JSONs in QUIPU chapters
records = {}
quipu_dir = "histmap/1.data_raw/population_regional/QUIPU"
for root, dirs, files in os.walk(quipu_dir):
  for f in files:
    if f.endswith("_settlements.json"):
      p = os.path.join(root, f)
      data = json.load(open(p, "r", encoding="utf-8"))
      for k, v in data.items():
        if isinstance(v, dict):
          records[k] = (f, v)

keys_file = sys.argv[1]
target_keys = json.load(open(keys_file, "r", encoding="utf-8"))
for tk in target_keys:
  key = tk["key"]
  if key in records:
    fn, v = records[key]
    prov = v.get("provenance_source", "")
    years = sorted([str(y) for y in v.get("population", {}).keys()], key=lambda x: int(x) if x.lstrip('-').isdigit() else 9999)
    print(f"{key} || file={fn} || prov={prov} || years={years[:4]}..{years[-2:] if len(years)>4 else ''} || aliases={v.get('other_names', [])} || notes={v.get('notes', '')}")
  else:
    print(f"{key} || NOT FOUND IN CHAPTER SETTLEMENTS")
