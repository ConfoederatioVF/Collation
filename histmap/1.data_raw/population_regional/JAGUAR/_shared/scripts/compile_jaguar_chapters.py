"""Compiles Project JAGUAR RMarkdown documents (.pdf and .md) with <= 2 concurrent directory workers.

Strictly serialises `_literature_review.Rmd` and `_settlements.Rmd` within the same
chapter directory so XeLaTeX auxiliary files never collide, and compiles both
`pdf_document` and `github_document` outputs via `rmarkdown::render(..., output_format = 'all')`.
"""

import argparse
import concurrent.futures
import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import time

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JAGUAR_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR")
RSCRIPT_CANDIDATES = [
  r"C:\Program Files\R\R-4.6.1\bin\Rscript.exe",
  r"C:\Program Files\R\R-4.5.0\bin\Rscript.exe",
]
TINYTEX_BIN = r"C:/Users/htmlp/AppData/Roaming/TinyTeX/bin/windows"


def find_rscript ():
  """Locates the preferred Rscript executable with full RMarkdown + kableExtra support."""
  for cand in RSCRIPT_CANDIDATES:
    if os.path.isfile(cand):
      return cand
  found = shutil.which("Rscript")
  if found:
    return found
  raise FileNotFoundError("Could not locate Rscript.exe on this system.")


def win_short_path (arg0_path):
  """Returns Windows 8.3 short path to stay safely below Win32 260-char MAX_PATH in XeTeX."""
  buf = ctypes.create_unicode_buffer(512)
  n = ctypes.windll.kernel32.GetShortPathNameW(os.path.abspath(arg0_path), buf, 512)
  return buf.value.replace("\\", "/") if n > 0 else os.path.abspath(arg0_path).replace("\\", "/")


def load_itinerary ():
  """Parses `jaguar_itinerary.json5` into a Python dictionary."""
  itin_path = os.path.join(JAGUAR_DIR, "jaguar_itinerary.json5")
  with open(itin_path, "r", encoding="utf-8") as fh:
    raw = fh.read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def build_directory_jobs (arg0_args, arg1_itinerary):
  """Builds directory-grouped compilation jobs so sibling Rmds are always serialised."""
  jobs_by_dir = {}

  def add_job (arg0_label, arg1_dir, arg2_rmd_name):
    abs_dir = os.path.abspath(arg1_dir)
    if abs_dir not in jobs_by_dir:
      jobs_by_dir[abs_dir] = {"dir": abs_dir, "label": arg0_label, "rmds": []}
    if arg2_rmd_name not in jobs_by_dir[abs_dir]["rmds"]:
      jobs_by_dir[abs_dir]["rmds"].append(arg2_rmd_name)

  if arg0_args.files:
    all_known = {"studies_on_population.Rmd": ("ROOT", JAGUAR_DIR)}
    for ch in arg1_itinerary["chapters"]:
      ch_dir = os.path.join(JAGUAR_DIR, ch["group"], ch["folder"])
      stem = ch["stem"]
      lbl = f"CH {ch['index']:02d} {stem}"
      all_known[f"{stem}_literature_review.Rmd"] = (lbl, ch_dir)
      all_known[f"{stem}_settlements.Rmd"] = (lbl, ch_dir)

    for raw_f in arg0_args.files:
      if os.path.isfile(raw_f):
        abs_f = os.path.abspath(raw_f)
        add_job(os.path.basename(os.path.dirname(abs_f)), os.path.dirname(abs_f), os.path.basename(abs_f))
      else:
        rel_try = os.path.join(JAGUAR_DIR, raw_f)
        if os.path.isfile(rel_try):
          abs_f = os.path.abspath(rel_try)
          add_job(os.path.basename(os.path.dirname(abs_f)), os.path.dirname(abs_f), os.path.basename(abs_f))
        else:
          bn = os.path.basename(raw_f)
          if bn in all_known:
            lbl, cdir = all_known[bn]
            add_job(lbl, cdir, bn)
          else:
            raise FileNotFoundError(f"Could not resolve target Rmd file: {raw_f}")
    return list(jobs_by_dir.values())

  if arg0_args.root_only:
    add_job("ROOT", JAGUAR_DIR, "studies_on_population.Rmd")
    return list(jobs_by_dir.values())

  selected_chapters = [
    ch for ch in arg1_itinerary["chapters"]
    if not arg0_args.chapters or ch["index"] in arg0_args.chapters
  ]
  for ch in selected_chapters:
    ch_dir = os.path.join(JAGUAR_DIR, ch["group"], ch["folder"])
    stem = ch["stem"]
    lbl = f"CH {ch['index']:02d} {stem}"
    add_job(lbl, ch_dir, f"{stem}_literature_review.Rmd")
    add_job(lbl, ch_dir, f"{stem}_settlements.Rmd")

  if (not arg0_args.chapters and not arg0_args.no_root) or arg0_args.include_root:
    add_job("ROOT", JAGUAR_DIR, "studies_on_population.Rmd")

  return list(jobs_by_dir.values())


def compile_directory_job (arg0_job, arg1_rscript):
  """Compiles all target Rmd files inside a single directory strictly serially."""
  label = arg0_job["label"]
  dir_raw = arg0_job["dir"]
  rmds = arg0_job["rmds"]
  dir_tex = win_short_path(dir_raw) if len(dir_raw) > 110 else dir_raw.replace("\\", "/")

  errs = []
  compiled_count = 0
  t0 = time.time()

  for rmd in rmds:
    rmd_path = os.path.join(dir_raw, rmd)
    if not os.path.isfile(rmd_path):
      errs.append(f"Missing {rmd}")
      continue

    r_code = (
      f"Sys.setenv(PATH=paste('{TINYTEX_BIN}', Sys.getenv('PATH'), sep=';')); "
      f"setwd('{dir_tex}'); "
      f"rmarkdown::render('{rmd}', output_format='all', quiet=TRUE)"
    )
    res = subprocess.run([arg1_rscript, "-e", r_code], capture_output=True, text=True)
    if res.returncode != 0:
      tail = "\n".join((res.stderr + "\n" + res.stdout).splitlines()[-18:])
      errs.append(f"{rmd} FAILED (rc={res.returncode}):\n{tail}")
      continue

    stem = os.path.splitext(rmd)[0]
    pdf_path = os.path.join(dir_raw, f"{stem}.pdf")
    md_path = os.path.join(dir_raw, f"{stem}.md")
    if not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) <= 0:
      errs.append(f"{rmd} produced missing/empty {stem}.pdf")
      continue
    if not os.path.isfile(md_path) or os.path.getsize(md_path) <= 0:
      errs.append(f"{rmd} produced missing/empty {stem}.md")
      continue
    compiled_count += 1

  elapsed = time.time() - t0
  if errs:
    print(f"  [FAIL] [{label}] ({elapsed:.1f}s): {' | '.join(errs)}", flush=True)
    return label, False, compiled_count, len(rmds), errs

  print(f"  [PASS] [{label}] ({elapsed:.1f}s): {compiled_count}/{len(rmds)} PDF + MD compiled cleanly", flush=True)
  return label, True, compiled_count, len(rmds), []


def main ():
  parser = argparse.ArgumentParser(description="Compile Project JAGUAR RMarkdown chapters and root paper.")
  parser.add_argument("--chapters", nargs="*", type=int, default=[], help="Optional chapter indices (1-14)")
  parser.add_argument("--files", nargs="*", default=[], help="Optional specific .Rmd file paths or basenames")
  parser.add_argument("--include-root", action="store_true", help="Include root studies_on_population.Rmd with --chapters")
  parser.add_argument("--no-root", action="store_true", help="Skip root studies_on_population.Rmd")
  parser.add_argument("--root-only", action="store_true", help="Compile only root studies_on_population.Rmd")
  parser.add_argument("--workers", type=int, default=2, help="Max concurrent directory workers (capped at 2)")
  args = parser.parse_args()

  rscript = find_rscript()
  workers = max(1, min(2, int(args.workers)))
  itinerary = load_itinerary()
  jobs = build_directory_jobs(args, itinerary)
  total_rmds = sum(len(j["rmds"]) for j in jobs)

  print(
    f"[JAGUAR COMPILE] Starting {total_rmds} Rmd file(s) across {len(jobs)} director(y/ies) "
    f"with max_workers={workers} using {rscript}...",
    flush=True,
  )
  t_start = time.time()

  ok_jobs = 0
  fail_jobs = 0
  ok_rmds = 0
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
    futs = [ex.submit(compile_directory_job, job, rscript) for job in jobs]
    for fut in concurrent.futures.as_completed(futs):
      _, ok, n_ok, _, _ = fut.result()
      ok_rmds += n_ok
      if ok:
        ok_jobs += 1
      else:
        fail_jobs += 1

  total_elapsed = time.time() - t_start
  print(
    f"\n[JAGUAR COMPILE SUMMARY] Jobs passed: {ok_jobs}/{len(jobs)} | "
    f"Rmds compiled (PDF+MD): {ok_rmds}/{total_rmds} | Failed jobs: {fail_jobs} | "
    f"Elapsed: {total_elapsed:.1f}s",
    flush=True,
  )
  sys.exit(1 if fail_jobs else 0)


if __name__ == "__main__":
  main()
