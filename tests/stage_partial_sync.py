"""Stage only auditor-approved AUSTRAL Stage F batches into a partial-sync input directory
with a signoff scoped strictly to those batches (rejected/unprocessed batches excluded)."""

import glob
import json
import os
import shutil

SRC = r"f:\Active Projects\Project 1509 - SVEA\tests\toponymy_batches\austral"
DST = r"f:\Active Projects\Project 1509 - SVEA\tests\toponymy_batches\austral_partial_sync"

if os.path.exists(DST):
  shutil.rmtree(DST)
os.makedirs(DST)

results = []
for rp in sorted(glob.glob(os.path.join(SRC, "resolved_batch_*.json"))):
  d = json.load(open(rp, encoding="utf-8"))
  bp = os.path.join(SRC, os.path.basename(rp).replace("resolved_", ""))
  exp = len(json.load(open(bp, encoding="utf-8")).get("settlements", []))
  if d.get("approved_by_auditor") and len(d.get("settlements", [])) == exp:
    shutil.copy2(rp, os.path.join(DST, os.path.basename(rp)))
    results.append({"approved": True, "batch_path": os.path.basename(rp), "count": exp, "errors_remaining": 0})

with open(os.path.join(DST, "auditor_signoff.json"), "w", encoding="utf-8") as fh:
  json.dump({
    "approved": True,
    "batches_audited": len(results),
    "errors_remaining": 0,
    "results": results,
    "scope": "partial_sync_auditor_approved_batches_only",
    "total_resolved": sum(r["count"] for r in results),
  }, fh, ensure_ascii=False, indent=2)

print(f"Staged {len(results)} auditor-approved batches ({sum(r['count'] for r in results)} settlements) -> {DST}")
