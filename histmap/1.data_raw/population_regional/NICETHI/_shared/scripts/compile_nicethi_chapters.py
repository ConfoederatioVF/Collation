"""Compiles all Project NICETHI RMarkdown manuscripts (root + 23 chapter pairs = 47 PDFs) with <= 2 concurrent directory builds."""
import argparse
import concurrent.futures
import ctypes
import glob
import os
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NICETHI_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
TEMPLATE_DIR = os.path.join(NICETHI_DIR, "_shared", "template")
TINYTEX_BIN = r"C:/Users/htmlp/AppData/Roaming/TinyTeX/bin/windows"
AUX_EXTENSIONS = (".aux", ".log", ".toc", ".out", ".fls", ".fdb_latexmk", ".synctex.gz", ".bbl", ".blg")


def find_rscript ():
  """Locates Rscript.exe, preferring R-4.5.0 then newest installed R."""
  preferred = r"C:\Program Files\R\R-4.5.0\bin\Rscript.exe"
  if os.path.isfile(preferred):
    return preferred
  candidates = sorted(glob.glob(r"C:\Program Files\R\R-*\bin\Rscript.exe"), reverse=True)
  if candidates:
    return candidates[0]
  found = shutil.which("Rscript")
  if found:
    return found
  raise FileNotFoundError("Could not locate Rscript.exe on PATH or under C:\\Program Files\\R")


def win_short_path (arg0_path):
  """Returns Windows 8.3 short path to stay safely below Win32 260-char MAX_PATH in XeTeX."""
  buf = ctypes.create_unicode_buffer(512)
  n = ctypes.windll.kernel32.GetShortPathNameW(os.path.abspath(arg0_path), buf, 512)
  return buf.value.replace("\\", "/") if n > 0 else arg0_path.replace("\\", "/")


def discover_units ():
  """Discovers root + all 23 chapter directory units so no two workers ever touch the same folder."""
  units = []
  root_rmd = os.path.join(NICETHI_DIR, "studies_on_population.Rmd")
  if os.path.isfile(root_rmd):
    units.append({"dir": NICETHI_DIR, "label": "00_root", "rmds": ["studies_on_population.Rmd"]})

  era_dirs = sorted(
    d for d in os.listdir(NICETHI_DIR)
    if os.path.isdir(os.path.join(NICETHI_DIR, d)) and d[0].isdigit() and "." in d
  )
  ch_idx = 0
  for era in era_dirs:
    era_path = os.path.join(NICETHI_DIR, era)
    ch_dirs = sorted(
      d for d in os.listdir(era_path)
      if os.path.isdir(os.path.join(era_path, d)) and d[0].isdigit() and "." in d
    )
    for ch in ch_dirs:
      ch_idx += 1
      ch_path = os.path.join(era_path, ch)
      rmds = sorted(f for f in os.listdir(ch_path) if f.endswith(".Rmd"))
      if rmds:
        units.append({"dir": ch_path, "label": f"CH{ch_idx:02d}_{ch}", "rmds": rmds})
  return units


def cleanup_aux (arg0_dir, arg1_rmd):
  """Removes intermediate LaTeX build files for the rendered RMarkdown stem."""
  stem = os.path.splitext(arg1_rmd)[0]
  for ext in AUX_EXTENSIONS:
    cand = os.path.join(arg0_dir, stem + ext)
    if os.path.isfile(cand):
      try:
        os.remove(cand)
      except OSError:
        pass


def compile_unit (arg0_unit, arg1_rscript):
  """Compiles all Rmd files inside a single directory sequentially."""
  label = arg0_unit["label"]
  raw_dir = arg0_unit["dir"]
  work_dir = win_short_path(raw_dir) if len(raw_dir) > 110 else raw_dir.replace("\\", "/")
  tpl_dir = win_short_path(TEMPLATE_DIR) if len(TEMPLATE_DIR) > 110 else TEMPLATE_DIR.replace("\\", "/")

  env = os.environ.copy()
  if os.path.isdir(TINYTEX_BIN):
    env["PATH"] = TINYTEX_BIN.replace("/", "\\") + ";" + env.get("PATH", "")
  existing_texinputs = env.get("TEXINPUTS", "")
  env["TEXINPUTS"] = f".;{tpl_dir.replace('/', os.sep)};{existing_texinputs};"

  errs = []
  ok_rmds = []
  for rmd in arg0_unit["rmds"]:
    rp = os.path.join(raw_dir, rmd)
    if not os.path.isfile(rp):
      errs.append(f"Missing {rmd}")
      continue
    r_code = (
      f"Sys.setenv(PATH=paste('{TINYTEX_BIN}', Sys.getenv('PATH'), sep=';')); "
      f"setwd('{work_dir}'); "
      f"rmarkdown::render('{rmd}', output_format='all', quiet=TRUE)"
    )
    res = subprocess.run([arg1_rscript, "-e", r_code], capture_output=True, text=True, env=env)
    cleanup_aux(raw_dir, rmd)
    if res.returncode != 0:
      combined = (res.stderr or "") + "\n" + (res.stdout or "")
      tail = "\n".join(line for line in combined.splitlines() if line.strip())
      tail_lines = tail.splitlines()[-15:]
      errs.append(f"{rmd} FAILED (rc={res.returncode}):\n" + "\n".join(tail_lines))
    else:
      pdf_path = os.path.join(raw_dir, os.path.splitext(rmd)[0] + ".pdf")
      if not os.path.isfile(pdf_path):
        errs.append(f"{rmd} exited 0 but PDF missing: {pdf_path}")
      else:
        ok_rmds.append(rmd)

  if errs:
    print(f"  [FAIL] [{label}] ({len(ok_rmds)}/{len(arg0_unit['rmds'])}): " + " | ".join(errs), flush=True)
    return label, False, len(ok_rmds), len(arg0_unit["rmds"]), errs
  print(f"  [PASS] [{label}] ({len(ok_rmds)}/{len(arg0_unit['rmds'])}): " + ", ".join(ok_rmds), flush=True)
  return label, True, len(ok_rmds), len(arg0_unit["rmds"]), []


def main ():
  ap = argparse.ArgumentParser(description="Compile NICETHI RMarkdown manuscripts with <= 2 concurrent directory builds.")
  ap.add_argument("--only", nargs="*", default=[], help="Substring filter(s) matching directory label or Rmd filename")
  args = ap.parse_args()

  rscript = find_rscript()
  units = discover_units()

  if args.only:
    needles = [s.lower() for s in args.only]
    filtered = []
    for u in units:
      if any(n in u["label"].lower() for n in needles):
        filtered.append(u)
      else:
        matched_rmds = [r for r in u["rmds"] if any(n in r.lower() for n in needles)]
        if matched_rmds:
          filtered.append({"dir": u["dir"], "label": u["label"], "rmds": matched_rmds})
    units = filtered

  total_rmds = sum(len(u["rmds"]) for u in units)
  print(f"[COMPILE] Rscript={rscript}", flush=True)
  print(f"[COMPILE] Compiling {total_rmds} Rmd(s) across {len(units)} directory unit(s) with max_workers=2...", flush=True)

  ok_pdfs = 0
  fail_units = 0
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    futures = [ex.submit(compile_unit, u, rscript) for u in units]
    for fut in concurrent.futures.as_completed(futures):
      label, ok, n_ok, n_tot, _ = fut.result()
      ok_pdfs += n_ok
      if not ok:
        fail_units += 1

  print(f"\n[COMPILE SUMMARY] PDFs compiled: {ok_pdfs}/{total_rmds} | Failed units: {fail_units}/{len(units)}", flush=True)
  sys.exit(1 if fail_units or ok_pdfs != total_rmds else 0)


if __name__ == "__main__":
  main()
