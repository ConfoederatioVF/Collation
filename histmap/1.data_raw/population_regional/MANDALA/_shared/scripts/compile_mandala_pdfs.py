"""Parallel RMarkdown -> XeLaTeX PDF compiler for Operation Viscount Project MANDALA."""

import concurrent.futures
import glob
import os
import subprocess
import sys
import time

RSCRIPT = r"C:\Program Files\R\R-4.5.0\bin\Rscript.exe"
MANDALA = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MANDALA"


def compile_one(rmd_path, force=False):
  pdf_path = os.path.splitext(rmd_path)[0] + ".pdf"
  rel = os.path.relpath(rmd_path, MANDALA)
  if not force and os.path.isfile(pdf_path):
    bibs = glob.glob(os.path.join(os.path.dirname(rmd_path), "*.bib"))
    max_bib = max((os.path.getmtime(b) for b in bibs), default=0.0)
    if os.path.getmtime(pdf_path) >= max(os.path.getmtime(rmd_path), max_bib):
      fig_dir = os.path.join(os.path.dirname(rmd_path), "figures")
      pngs = glob.glob(os.path.join(fig_dir, "*.png")) if os.path.isdir(fig_dir) else []
      max_fig = max((os.path.getmtime(p) for p in pngs), default=0.0)
      if os.path.getmtime(pdf_path) >= max_fig:
        return (rel, True, 0.0, "up-to-date")
  t0 = time.time()
  rmd_fwd = rmd_path.replace("\\", "/")
  cmd = [
    RSCRIPT, "-e",
    f"rmarkdown::render('{rmd_fwd}', output_format = 'pdf_document', quiet = TRUE)"
  ]
  res = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(rmd_path))
  dt = time.time() - t0
  ok = (res.returncode == 0 and os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 10000)
  msg = "OK" if ok else (res.stderr or res.stdout)[-600:]
  return (rel, ok, dt, msg)


def main():
  force = "--force" in sys.argv
  only_filter = None
  for a in sys.argv[1:]:
    if a.startswith("--only="):
      only_filter = a.split("=", 1)[1].lower()

  rmds = [os.path.join(MANDALA, "studies_on_population.Rmd")]
  rmds.extend(sorted(glob.glob(os.path.join(MANDALA, "*", "*", "*.Rmd"))))
  rmds = [p for p in rmds if os.path.isfile(p)]
  if only_filter:
    rmds = [p for p in rmds if only_filter in p.lower()]

  print(f"=== COMPILING {len(rmds)} MANDALA RMD FILES TO PDF (concurrency=4) ===", flush=True)
  ok_cnt = 0
  fails = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    futs = {ex.submit(compile_one, p, force): p for p in rmds}
    for fut in concurrent.futures.as_completed(futs):
      rel, ok, dt, msg = fut.result()
      if ok:
        ok_cnt += 1
        print(f"  [OK  {ok_cnt:02d}/{len(rmds):02d}] {rel} ({dt:.1f}s) {msg if msg != 'OK' else ''}", flush=True)
      else:
        fails.append((rel, msg))
        print(f"  [FAIL] {rel} ({dt:.1f}s):\n{msg}", flush=True)

  print(f"=== FINISHED: {ok_cnt}/{len(rmds)} OK, {len(fails)} FAILED ===", flush=True)
  sys.exit(1 if fails else 0)


if __name__ == "__main__":
  main()
