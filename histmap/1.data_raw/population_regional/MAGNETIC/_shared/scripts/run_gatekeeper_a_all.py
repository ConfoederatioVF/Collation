"""Runs Gatekeeper A (`verify_gazetteer_exhaustiveness.py`) across all 21 MAGNETIC chapters (4-worker parallel)."""
import concurrent.futures
import json
import os
import re
import subprocess
import sys

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
VERIFIER = os.path.join(SVEA_ROOT, ".agents", "skills", "population-regional-study", "scripts", "verify_gazetteer_exhaustiveness.py")

raw = open(os.path.join(MAG_DIR, "magnetic_itinerary.json5"), encoding="utf-8").read()
raw = re.sub(r"//.*", "", raw)
raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
itin = json.loads(raw)


def verify_one (arg0_ch):
  key = arg0_ch["key"]
  ch_dir = os.path.join(MAG_DIR, arg0_ch["folder"])
  sett = os.path.join(ch_dir, f"{key}_settlements.json")
  ledg = os.path.join(ch_dir, f"{key}_source_ledger.json5")
  cmd = [
    sys.executable, VERIFIER, sett,
    "--require-sources", "--require-saturation",
    "--audit-temporal-density", "--audit-spatial-bounds",
    "--ledger", ledg,
  ]
  res = subprocess.run(cmd, capture_output=True, text=True)
  if res.returncode == 0:
    return arg0_ch["index"], key, True, []
  errs = [l for l in (res.stderr + "\n" + res.stdout).splitlines() if "[FAIL]" in l][:6]
  return arg0_ch["index"], key, False, errs


def main ():
  passed = 0
  failed = 0
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    results = list(ex.map(verify_one, itin["chapters"]))
  for idx, key, ok, errs in sorted(results):
    if ok:
      passed += 1
      print(f"  [PASS] [CH {idx:02d}] {key}", flush=True)
    else:
      failed += 1
      print(f"  [FAIL] [CH {idx:02d}] {key}: {errs}", flush=True)
  print(f"\n[GATEKEEPER A SUMMARY] Passed: {passed}/21 | Failed: {failed}/21", flush=True)
  sys.exit(1 if failed else 0)


if __name__ == "__main__":
  main()
