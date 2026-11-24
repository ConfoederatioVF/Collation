"""Preserve already auditor-approved resolved_batch_001..006 and re-chunk remaining
20.527 AUSTRAL Stage F settlements into larger chunks (Tier 1: 250/chunk, Tier 2: 450/chunk)
to eliminate 429 RESOURCE_EXHAUSTED."""

import glob
import json
import os

BDIR = r"f:\Active Projects\Project 1509 - SVEA\tests\toponymy_batches\austral"
MAN_PATH = os.path.join(BDIR, "manifest.json")

man = json.load(open(MAN_PATH, encoding="utf-8"))

approved_batches = []
remaining_t1 = []
remaining_t2 = []

for bp in sorted(glob.glob(os.path.join(BDIR, "batch_*.json"))):
  bn = os.path.basename(bp)
  rp = os.path.join(BDIR, "resolved_" + bn)
  d = json.load(open(bp, encoding="utf-8"))
  if os.path.exists(rp):
    rd = json.load(open(rp, encoding="utf-8"))
    if rd.get("approved_by_auditor") and len(rd.get("settlements", [])) == len(d.get("settlements", [])):
      approved_batches.append((bp, rp, d))
      continue
  tier = d.get("tier", "tier2")
  if tier == "tier1":
    remaining_t1.extend(d.get("settlements", []))
  else:
    remaining_t2.extend(d.get("settlements", []))

print(f"Preserving {len(approved_batches)} already auditor-approved batches ({sum(len(d['settlements']) for _, _, d in approved_batches)} settlements).")
print(f"Re-chunking remaining: Tier 1={len(remaining_t1)} (@ <=250), Tier 2={len(remaining_t2)} (@ <=450).")

keep_bps = {bp for bp, _, _ in approved_batches}
keep_rps = {rp for _, rp, _ in approved_batches}

for bp in glob.glob(os.path.join(BDIR, "batch_*.json")):
  if bp not in keep_bps:
    os.remove(bp)
for rp in glob.glob(os.path.join(BDIR, "resolved_batch_*.json")):
  if rp not in keep_rps:
    os.remove(rp)

next_idx = len(approved_batches) + 1
new_batches = []
for i in range(0, len(remaining_t1), 250):
  new_batches.append(("tier1", remaining_t1[i:i + 250]))
for i in range(0, len(remaining_t2), 450):
  new_batches.append(("tier2", remaining_t2[i:i + 450]))

all_batch_files = [bp for bp, _, _ in approved_batches]
for tier_lbl, sl in new_batches:
  bname = f"batch_{next_idx:03d}.json"
  bpath = os.path.join(BDIR, bname)
  with open(bpath, "w", encoding="utf-8") as fh:
    json.dump({
      "batch_index": next_idx,
      "count": len(sl),
      "is_indigenous_region": True,
      "project": "AUSTRAL",
      "tier": tier_lbl,
      "settlements": sl,
    }, fh, ensure_ascii=False, indent=2)
  all_batch_files.append(bpath)
  next_idx += 1

man["batch_count"] = len(all_batch_files)
man["batch_files"] = all_batch_files
man["batch_size"] = 450
man["rechunked_tiers"] = {
  "preserved_approved_batches": len(approved_batches),
  "remaining_t1_size": 250,
  "remaining_t1_count": len(remaining_t1),
  "remaining_t2_size": 450,
  "remaining_t2_count": len(remaining_t2),
}
with open(MAN_PATH, "w", encoding="utf-8") as fh:
  json.dump(man, fh, ensure_ascii=False, indent=2)

print(f"Done! Total batches now: {len(all_batch_files)} ({len(approved_batches)} approved + {len(new_batches)} remaining).")
