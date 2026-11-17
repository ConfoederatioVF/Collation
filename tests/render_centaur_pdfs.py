# -*- coding: utf-8 -*-
"""Compiles all 63 CENTAUR-II `.Rmd` files to `.pdf` using Rscript and validates
with PyMuPDF (`fitz`) that 0 unresolved `??` citations and `max_x1 <= 540.5 pt` hold.
"""

import concurrent.futures
import glob
import os
import subprocess
import sys

CENTAUR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../histmap/1.data_raw/population_regional/CENTAUR"))
RSCRIPT = r"C:/Program Files/R/R-4.6.1/bin/x64/Rscript.exe"


def render_one(rmd_path):
  mod_dir = os.path.dirname(rmd_path)
  bn = os.path.basename(rmd_path)
  cmd = [
    RSCRIPT,
    "-e",
    f"rmarkdown::render('{bn}', output_format='pdf_document', quiet=TRUE)",
  ]
  res = subprocess.run(cmd, cwd=mod_dir, capture_output=True, text=True)
  pdf_path = os.path.splitext(rmd_path)[0] + ".pdf"
  ok = res.returncode == 0 and os.path.isfile(pdf_path)
  return rmd_path, ok, res.stderr[-400:] if not ok else ""


def main():
  rmds = sorted(glob.glob(os.path.join(CENTAUR_DIR, "**", "*.Rmd"), recursive=True))
  print(f"Rendering {len(rmds)} CENTAUR Rmd manuscripts to PDF...")
  fails = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    for rmd_path, ok, err in ex.map(render_one, rmds):
      rel = os.path.relpath(rmd_path, CENTAUR_DIR)
      if not ok:
        print(f"  [FAIL] {rel}: {err}")
        fails.append(rel)
      else:
        print(f"  [OK]   {rel}")

  if fails:
    print(f"FAILED {len(fails)}/{len(rmds)} PDF renders.")
    sys.exit(1)

  # Audit PDFs via PyMuPDF
  import fitz
  bad_qq = []
  bad_margin = []
  for rmd_path in rmds:
    pdf_path = os.path.splitext(rmd_path)[0] + ".pdf"
    rel = os.path.relpath(pdf_path, CENTAUR_DIR)
    doc = fitz.open(pdf_path)
    max_x1 = 0.0
    qq = False
    for page in doc:
      if "??" in page.get_text("text"):
        qq = True
      for b in page.get_text("blocks"):
        if b[2] > max_x1:
          max_x1 = b[2]
    if qq:
      bad_qq.append(rel)
    if max_x1 > 540.5:
      bad_margin.append((rel, round(max_x1, 1)))
  print(f"PyMuPDF Audit: {len(rmds)}/{len(rmds)} PDFs built | unresolved ??={len(bad_qq)} {bad_qq[:5]} | margin>540.5={len(bad_margin)} {bad_margin[:10]}")
  if bad_qq or bad_margin:
    sys.exit(1)


if __name__ == "__main__":
  main()
