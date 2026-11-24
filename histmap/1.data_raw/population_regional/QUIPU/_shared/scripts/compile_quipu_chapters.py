"""Compiles Project QUIPU root and chapter RMarkdown pairs (.pdf and .md) with <= 2 concurrent directory builds."""
import argparse
import concurrent.futures
import ctypes
import json
import os
import re
import subprocess
import sys

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
QUIPU_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "QUIPU")
RSCRIPT = r"C:\Program Files\R\R-4.5.0\bin\Rscript.exe"
TINYTEX_BIN = r"C:/Users/htmlp/AppData/Roaming/TinyTeX/bin/windows"


def win_short_path (arg0_path):
  """Returns Windows 8.3 short path to stay safely below Win32 260-char MAX_PATH in XeTeX."""
  buf = ctypes.create_unicode_buffer(512)
  n = ctypes.windll.kernel32.GetShortPathNameW(os.path.abspath(arg0_path), buf, 512)
  return buf.value.replace("\\", "/") if n > 0 else arg0_path.replace("\\", "/")


def load_itinerary ():
  raw = open(os.path.join(QUIPU_DIR, "quipu_itinerary.json5"), encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def compile_root ():
  r_dir = QUIPU_DIR.replace("\\", "/")
  r_code = (
    f"Sys.setenv(PATH=paste('{TINYTEX_BIN}', Sys.getenv('PATH'), sep=';')); "
    f"setwd('{r_dir}'); "
    f"rmarkdown::render('studies_on_population.Rmd', output_format='all', quiet=TRUE)"
  )
  res = subprocess.run([RSCRIPT, "-e", r_code], capture_output=True, text=True)
  if res.returncode != 0:
    tail = "\n".join((res.stderr + "\n" + res.stdout).splitlines()[-15:])
    print(f"  [FAIL] [ROOT] studies_on_population.Rmd:\n{tail}", flush=True)
    return False
  print("  [PASS] [ROOT] studies_on_population.Rmd: PDF + MD compiled cleanly", flush=True)
  return True


def compile_chapter (arg0_ch):
  idx = arg0_ch["index"]
  key = arg0_ch["key"]
  ch_dir_raw = os.path.join(QUIPU_DIR, arg0_ch["folder"])
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
  print(f"  [PASS] [CH {idx:02d}] {key}: PDFs compiled cleanly", flush=True)
  return idx, key, True, []


def main ():
  ap = argparse.ArgumentParser()
  ap.add_argument("--chapters", nargs="*", type=int, default=[])
  ap.add_argument("--skip-root", action="store_true")
  args = ap.parse_args()
  itin = load_itinerary()
  targets = [c for c in itin["chapters"] if not args.chapters or c["index"] in args.chapters]
  ok_n, fail_n = 0, 0
  if not args.skip_root and not args.chapters:
    print("[COMPILE] Compiling root studies_on_population.Rmd...", flush=True)
    if not compile_root():
      fail_n += 1
    else:
      ok_n += 1
  print(f"[COMPILE] Compiling {len(targets)} chapter(s) with max_workers=2...", flush=True)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    for idx, key, ok, _ in ex.map(compile_chapter, targets):
      if ok:
        ok_n += 1
      else:
        fail_n += 1
  total = len(targets) + (0 if (args.skip_root or args.chapters) else 1)
  print(f"\n[COMPILE SUMMARY] Passed: {ok_n}/{total} | Failed: {fail_n}/{total}", flush=True)
  sys.exit(1 if fail_n else 0)


if __name__ == "__main__":
  main()
