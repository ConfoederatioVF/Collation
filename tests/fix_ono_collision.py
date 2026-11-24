"""Consolidate the three duplicate Ono (Futuna, Wallis and Futuna) records in Dataview city_metadata/13_austral.json."""

import json
import os

PART = r"f:\Active Projects\Project 1436 - Dataview\data\stadester\stadester_2.0\city_metadata"
SHARD = os.path.join(PART, "13_austral.json")
MAN = os.path.join(PART, "city_metadata_manifest.json")

arr = json.load(open(SHARD, encoding="utf-8"))
ono_idx = [i for i, r in enumerate(arr) if r.get("name") == "Ono" and r.get("country") == "Wallis and Futuna"]
print("Ono records:", ono_idx)

# Keep the auditor-approved record with the earliest attested timeline and fullest aliases
keep_i = min(ono_idx, key=lambda i: int(str(arr[i]["historical_names"][0]["date"]).split(".")[0]))
seen = {"ono"}
aliases = []
for i in ono_idx:
  for al in (arr[i].get("other_names") or []):
    if al and al.lower() not in seen:
      seen.add(al.lower())
      aliases.append(al)
arr[keep_i]["other_names"] = aliases

drop = set(ono_idx) - {keep_i}
arr = [r for i, r in enumerate(arr) if i not in drop]
with open(SHARD, "w", encoding="utf-8") as fh:
  json.dump(arr, fh, ensure_ascii=False, indent=2)

man = json.load(open(MAN, encoding="utf-8"))
for sh in man.get("shards", []):
  if sh.get("file") == "13_austral.json":
    for ck in ("count", "records"):
      if ck in sh:
        sh[ck] = len(arr)
with open(MAN, "w", encoding="utf-8") as fh:
  json.dump(man, fh, ensure_ascii=False, indent=2)

print(f"Kept index {keep_i}, dropped {sorted(drop)}; aliases={aliases}; shard now {len(arr)} records.")
