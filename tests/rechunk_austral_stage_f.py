"""Re-chunk AUSTRAL Stage F candidates into larger, tiered batches (Tier 1: 150/chunk, Tier 2: 250/chunk)
so the Gemini 3.8 Flash + read-only Auditor swarm runs cleanly without resource exhaustion."""

import glob
import json
import os

BDIR = r"f:\Active Projects\Project 1509 - SVEA\tests\toponymy_batches\austral"
MAN_PATH = os.path.join(BDIR, "manifest.json")

man = json.load(open(MAN_PATH, encoding="utf-8"))
all_items = []
for bp in sorted(glob.glob(os.path.join(BDIR, "batch_*.json"))):
  d = json.load(open(bp, encoding="utf-8"))
  all_items.extend(d.get("settlements", []))

print(f"Loaded {len(all_items)} total candidates from {len(glob.glob(os.path.join(BDIR, 'batch_*.json')))} raw batches.")

tier1 = []
tier2 = []
for it in all_items:
  is_t1 = (
    bool(it.get("is_capital"))
    or it.get("reason") != "missing_entry"
    or (it.get("max_pop") or 0) >= 5000
    or (it.get("earliest_year") is not None and int(it["earliest_year"]) < 1850)
  )
  if is_t1:
    tier1.append(it)
  else:
    tier2.append(it)

# Sort Tier 1: capitals first, then under_covered/audit reasons, then descending max_pop
tier1.sort(key=lambda x: (
  0 if x.get("is_capital") else 1,
  0 if x.get("reason") != "missing_entry" else 1,
  -(x.get("max_pop") or 0),
  str(x.get("country", "")),
  str(x.get("name", "")),
))

# Sort Tier 2: geographically by country + region + descending max_pop so workers share regional context!
tier2.sort(key=lambda x: (
  str(x.get("country", "")),
  str(x.get("region", "")),
  -(x.get("max_pop") or 0),
  str(x.get("name", "")),
))

print(f"Tier 1 (capitals / pre-1850 / >=5k / existing-history updates): {len(tier1)}")
print(f"Tier 2 (post-1850 rural/modern towns <5k): {len(tier2)}")

# Clean old batch_*.json and resolved_batch_*.json before writing large chunks
for old_p in glob.glob(os.path.join(BDIR, "batch_*.json")) + glob.glob(os.path.join(BDIR, "resolved_batch_*.json")):
  os.remove(old_p)
if os.path.exists(os.path.join(BDIR, "auditor_signoff.json")):
  os.remove(os.path.join(BDIR, "auditor_signoff.json"))

batches = []
T1_SIZE = 150
T2_SIZE = 250

for i in range(0, len(tier1), T1_SIZE):
  batches.append(("tier1", tier1[i:i + T1_SIZE]))
for i in range(0, len(tier2), T2_SIZE):
  batches.append(("tier2", tier2[i:i + T2_SIZE]))

batch_files = []
for idx, (tier_lbl, sl) in enumerate(batches, start=1):
  bname = f"batch_{idx:03d}.json"
  bpath = os.path.join(BDIR, bname)
  with open(bpath, "w", encoding="utf-8") as fh:
    json.dump({
      "batch_index": idx,
      "count": len(sl),
      "is_indigenous_region": True,
      "project": "AUSTRAL",
      "tier": tier_lbl,
      "settlements": sl,
    }, fh, ensure_ascii=False, indent=2)
  batch_files.append(bpath)

man["batch_count"] = len(batch_files)
man["batch_files"] = batch_files
man["batch_size"] = T2_SIZE
man["rechunked_tiers"] = {"tier1_size": T1_SIZE, "tier1_count": len(tier1), "tier2_size": T2_SIZE, "tier2_count": len(tier2)}
with open(MAN_PATH, "w", encoding="utf-8") as fh:
  json.dump(man, fh, ensure_ascii=False, indent=2)

t1_b = sum(1 for t, _ in batches if t == "tier1")
t2_b = sum(1 for t, _ in batches if t == "tier2")
print(f"Wrote {len(batch_files)} large chunks ({t1_b} Tier-1 @ <={T1_SIZE}, {t2_b} Tier-2 @ <={T2_SIZE}).")
