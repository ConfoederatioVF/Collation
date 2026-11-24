"""Compiles Project AUSTRAL chapter RMarkdown pairs and root synthesis (.pdf and .md) with <= 2 concurrent directory builds."""
import argparse
import concurrent.futures
import ctypes
import json
import os
import re
import subprocess
import sys

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
AUSTRAL_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "AUSTRAL")
RSCRIPT = r"C:\Program Files\R\R-4.5.0\bin\Rscript.exe"
TINYTEX_BIN = r"C:/Users/htmlp/AppData/Roaming/TinyTeX/bin/windows"


def win_short_path (arg0_path):
  """Returns Windows 8.3 short path to stay safely below Win32 260-char MAX_PATH in XeTeX."""
  buf = ctypes.create_unicode_buffer(512)
  n = ctypes.windll.kernel32.GetShortPathNameW(os.path.abspath(arg0_path), buf, 512)
  return buf.value.replace("\\", "/") if n > 0 else arg0_path.replace("\\", "/")


def load_itinerary ():
  raw = open(os.path.join(AUSTRAL_DIR, "austral_itinerary.json5"), encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def render_rmd (arg0_dir_raw, arg1_rmd_name):
  """Renders a single Rmd file to all configured output formats (.pdf and .md)."""
  work_dir = win_short_path(arg0_dir_raw) if len(arg0_dir_raw) > 105 else arg0_dir_raw.replace("\\", "/")
  rmd_path = os.path.join(arg0_dir_raw, arg1_rmd_name)
  if not os.path.isfile(rmd_path):
    return False, f"Missing {arg1_rmd_name}"
  r_code = (
    f"Sys.setenv(PATH=paste('{TINYTEX_BIN}', Sys.getenv('PATH'), sep=';')); "
    f"setwd('{work_dir}'); "
    f"rmarkdown::render('{arg1_rmd_name}', output_format='all', quiet=TRUE)"
  )
  res = subprocess.run([RSCRIPT, "-e", r_code], capture_output=True, text=True)
  if res.returncode != 0:
    tail = "\n".join((res.stderr + "\n" + res.stdout).splitlines()[-18:])
    return False, f"{arg1_rmd_name} FAILED:\n{tail}"
  return True, ""


def compile_chapter (arg0_ch):
  idx = arg0_ch["index"]
  key = arg0_ch["key"]
  ch_dir_raw = os.path.join(AUSTRAL_DIR, arg0_ch["folder"])
  rmds = [f"{key}_literature_review.Rmd", f"{key}_settlements.Rmd"]
  errs = []
  for rmd in rmds:
    ok, msg = render_rmd(ch_dir_raw, rmd)
    if not ok:
      errs.append(msg)
  if errs:
    print(f"  [FAIL] [CH {idx:02d}] {key}: {' | '.join(errs)}", flush=True)
    return idx, key, False, errs
  print(f"  [PASS] [CH {idx:02d}] {key}: PDF + MD compiled cleanly (2/2)", flush=True)
  return idx, key, True, []


def compile_root ():
  ok, msg = render_rmd(AUSTRAL_DIR, "studies_on_population.Rmd")
  if not ok:
    print(f"  [FAIL] [ROOT] studies_on_population.Rmd: {msg}", flush=True)
    return False
  print("  [PASS] [ROOT] studies_on_population.Rmd: PDF + MD compiled cleanly (1/1)", flush=True)
  return True


def main ():
  ap = argparse.ArgumentParser()
  ap.add_argument("--chapters", nargs="*", type=int, default=[])
  ap.add_argument("--root-only", action="store_true")
  ap.add_argument("--skip-root", action="store_true")
  args = ap.parse_args()

  itin = load_itinerary()
  targets = [] if args.root_only else [
    c for c in itin["chapters"] if not args.chapters or c["index"] in args.chapters
  ]
  do_root = args.root_only or (not args.skip_root and not args.chapters)

  total_rmds = len(targets)*2 + (1 if do_root else 0)
  print(f"[COMPILE] Compiling {len(targets)} chapter(s) + {'1 root' if do_root else '0 root'} ({total_rmds} Rmd files) with max_workers=2...", flush=True)

  ok_n, fail_n = 0, 0
  if targets:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
      for idx, key, ok, _ in ex.map(compile_chapter, targets):
        if ok:
          ok_n += 2
        else:
          fail_n += 1

  if do_root:
    if compile_root():
      ok_n += 1
    else:
      fail_n += 1

  print(f"\n[COMPILE SUMMARY] Compiled Rmd files OK: {ok_n}/{total_rmds} | Failed targets: {fail_n}", flush=True)
  sys.exit(1 if fail_n else 0)


if __name__ == "__main__":
  main()
