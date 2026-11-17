import json5
import os
import subprocess
import sys

SVEA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../.."))
MANIFEST = os.path.join(SVEA_ROOT, "histmap/1.data_raw/population_regional/CENTAUR/centaur_gazetteers.json5")
VERIFIER = os.path.join(SVEA_ROOT, ".agents/skills/population-regional-study/scripts/verify_gazetteer_exhaustiveness.py")

data = json5.load(open(MANIFEST, "r", encoding="utf-8"))
gazs = data["gazetteers"]
failures = 0
for g in gazs:
    s_abs = os.path.join(SVEA_ROOT, g["path"])
    l_abs = s_abs.replace("_settlements.json", "_source_ledger.json5")
    cmd = [sys.executable, VERIFIER, s_abs, "--ledger", l_abs, "--require-sources", "--mode", "regional", "--check-close-pairs"]
    if g["key"] == "canada_post_confederation":
        cmd.extend(["--require-saturation", "--modern-census-year", "1867"])
    elif g["key"] == "united_states_post_independence":
        cmd.extend(["--require-saturation", "--modern-census-year", "1850"])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    status = "PASS" if proc.returncode == 0 else "FAIL"
    print(f"[{status}] {g['key']:36s} | {proc.stdout.strip()}")
    if proc.returncode != 0:
        print("  STDERR:", proc.stderr.strip())
        failures += 1

print(f"\nGatekeeper A Summary: {len(gazs) - failures}/{len(gazs)} passed, {failures} failures.")
sys.exit(1 if failures else 0)
