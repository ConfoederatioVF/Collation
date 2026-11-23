"""Compiles Project MAGNETIC chapter RMarkdown pairs (.pdf and .md) with <= 2 concurrent directory builds."""
import argparse
import concurrent.futures
import ctypes
import json
import os
import re
import subprocess
import sys

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
RSCRIPT = r"C:\Program Files\R\R-4.5.0\bin\Rscript.exe"
TINYTEX_BIN = r"C:/Users/htmlp/AppData/Roaming/TinyTeX/bin/windows"


def win_short_path (arg0_path):
  """Returns Windows 8.3 short path to stay safely below Win32 260-char MAX_PATH in XeTeX."""
  buf = ctypes.create_unicode_buffer(512)
  n = ctypes.windll.kernel32.GetShortPathNameW(os.path.abspath(arg0_path), buf, 512)
  return buf.value.replace("\\", "/") if n > 0 else arg0_path.replace("\\", "/")


def load_itinerary ():
  raw = open(os.path.join(MAG_DIR, "magnetic_itinerary.json5"), encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def compile_chapter (arg0_ch):
  idx = arg0_ch["index"]
  key = arg0_ch["key"]
  ch_dir_raw = os.path.join(MAG_DIR, arg0_ch["folder"])
  ch_dir = win_short_path(ch_dir_raw) if len(ch_dir_raw) > 110 else ch_dir_raw.replace("\\", "/")
  rmds = [f"{key}_literature_review.Rmd", f"{key}_settlements.Rmd"]
  errs = []
  for rmd in rmds:
    rp = os.path.join(ch_dir, rmd)
    if not os.path.isfile(rp):
      errs.append(f"Missing {rmd}")
      continue
    r_code = (
      f"Sys.setenv(PATH=paste('{TINYTEX_BIN}', Sys.getenv('PATH'), sep=';')); "
      f"setwd('{ch_dir}'); "
      f"rmarkdown::render('{rmd}', output_format='all', quiet=TRUE)"
    )
    res = subprocess.run([RSCRIPT, "-e", r_code], capture_output=True, text=True)
    if res.returncode != 0:
      tail = "\n".join((res.stderr + "\n" + res.stdout).splitlines()[-12:])
      errs.append(f"{rmd} FAILED:\n{tail}")
  if errs:
    print(f"  [FAIL] [CH {idx:02d}] {key}: {' | '.join(errs)}", flush=True)
    return idx, key, False, errs
  print(f"  [PASS] [CH {idx:02d}] {key}: PDF + MD compiled cleanly", flush=True)
  return idx, key, True, []


def main ():
  ap = argparse.ArgumentParser()
  ap.add_argument("--chapters", nargs="*", type=int, default=[])
  args = ap.parse_args()
  itin = load_itinerary()
  targets = [c for c in itin["chapters"] if not args.chapters or c["index"] in args.chapters]
  print(f"[COMPILE] Compiling {len(targets)} chapter(s) with max_workers=2...", flush=True)
  ok_n, fail_n = 0, 0
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    for idx, key, ok, _ in ex.map(compile_chapter, targets):
      if ok:
        ok_n += 1
      else:
        fail_n += 1
  print(f"\n[COMPILE SUMMARY] Passed: {ok_n}/{len(targets)} | Failed: {fail_n}/{len(targets)}", flush=True)
  sys.exit(1 if fail_n else 0)


if __name__ == "__main__":
  main()
