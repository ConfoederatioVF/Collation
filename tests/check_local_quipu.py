import json
import os
import time
import urllib.parse
import urllib.request

# 1. Check local QUIPU files for any source/provenance/notes on our 90 keys
with open("tests/lookup_chunk051.py", "r", encoding="utf-8") as f:
  src = f.read()
start = src.index("SETTLEMENTS = [")
end = src.index("\ndef wiki_search")
ns = {}
exec(src[start:end], ns)
SETTLEMENTS = ns["SETTLEMENTS"]
keys_set = {s["key"] for s in SETTLEMENTS}

local_info = {}
for fn in ["histmap/5.data_visualisation/stadester/stadester_2.0/11_quipu_1.json",
           "histmap/5.data_visualisation/stadester/stadester_2.0/11_quipu_2.json"]:
  if os.path.exists(fn):
    with open(fn, "r", encoding="utf-8") as f:
      data = json.load(f)
    if isinstance(data, dict):
      for k, v in data.items():
        if k in keys_set:
          local_info[k] = {
            "name": v.get("name"),
            "other_names": v.get("other_names"),
            "country": v.get("country"),
            "coords": v.get("coords"),
            "pop_years": sorted([str(y) for y in (v.get("population") or {}).keys()])[:5] + ["..."] + sorted([str(y) for y in (v.get("population") or {}).keys()])[-3:] if isinstance(v.get("population"), dict) else None,
            "sources": v.get("sources") or v.get("source")
          }

with open("tests/chunk051_local.json", "w", encoding="utf-8") as f:
  json.dump(local_info, f, ensure_ascii=False, indent=2)
print(f"Found {len(local_info)} local entries")
