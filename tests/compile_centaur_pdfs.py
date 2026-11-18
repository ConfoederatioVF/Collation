import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import shutil
import subprocess
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[1]
CENTAUR_DIR = (
  REPO_ROOT / "histmap" / "1.data_raw" / "population_regional" / "CENTAUR"
)


def resolve_rscript ():
  """Locate Rscript executable with rmarkdown/kableExtra installed."""
  preferred = Path(r"C:\Program Files\R\R-4.6.1\bin\Rscript.exe")
  if preferred.is_file():
    return str(preferred)
  for candidate in sorted(Path(r"C:\Program Files\R").glob("R-*/bin/Rscript.exe"), reverse=True):
    if candidate.is_file():
      return str(candidate)
  on_path = shutil.which("Rscript")
  if on_path:
    return on_path
  raise FileNotFoundError("Could not locate Rscript executable.")


def collect_compile_batches (arg0_centaur_dir):
  """Collect directory-grouped Rmd compile batches for CENTAUR."""
  centaur_dir = Path(arg0_centaur_dir)
  batches = []
  root_rmd = centaur_dir / "studies_on_population.Rmd"
  chapter_dirs = []

  if not root_rmd.is_file():
    raise FileNotFoundError(f"Missing root Rmd: {root_rmd}")
  batches.append((centaur_dir, [root_rmd]))

  for group_dir in sorted(centaur_dir.iterdir()):
    if not group_dir.is_dir():
      continue
    if group_dir.name.startswith("_") or group_dir.name == "figures":
      continue
    for chapter_dir in sorted(group_dir.iterdir()):
      if not chapter_dir.is_dir():
        continue
      rmds = sorted(chapter_dir.glob("*.Rmd"))
      if rmds:
        chapter_dirs.append((chapter_dir, rmds))

  batches.extend(chapter_dirs)

  #Return statement
  return batches


def compile_directory_batch (arg0_batch, arg1_rscript):
  """Compile all Rmd files inside a single directory sequentially."""
  target_dir, rmd_files = arg0_batch
  results = []
  t0 = time.time()

  for rmd_path in rmd_files:
    pdf_path = rmd_path.with_suffix(".pdf")
    cmd = [
      arg1_rscript,
      "-e",
      f"rmarkdown::render('{rmd_path.name}', quiet=TRUE)",
    ]
    proc = subprocess.run(
      cmd,
      cwd=str(target_dir),
      capture_output=True,
      text=True,
      encoding="utf-8",
      errors="replace",
    )
    ok = (proc.returncode == 0) and pdf_path.is_file()
    results.append({
      "rmd": str(rmd_path.relative_to(CENTAUR_DIR)),
      "pdf": str(pdf_path.relative_to(CENTAUR_DIR)),
      "ok": ok,
      "returncode": proc.returncode,
      "stderr": proc.stderr[-1200:] if not ok else "",
      "stdout": proc.stdout[-800:] if not ok else "",
    })

  elapsed = time.time() - t0

  #Return statement
  return str(target_dir.relative_to(CENTAUR_DIR)), elapsed, results


def main ():
  """CLI entrypoint to compile all CENTAUR Rmd files into PDFs."""
  parser = argparse.ArgumentParser(description="Compile CENTAUR Rmd monographs.")
  parser.add_argument("--workers", type=int, default=4)
  parser.add_argument("--dry-run", action="store_true")
  args = parser.parse_args()

  batches = collect_compile_batches(CENTAUR_DIR)
  total_rmds = sum(len(b[1]) for b in batches)
  print(f"Discovered {len(batches)} directory batches ({total_rmds} Rmd files).")

  if total_rmds != 63:
    print(f"ERROR: expected 63 Rmd files, found {total_rmds}", file=sys.stderr)
    sys.exit(1)

  if args.dry_run:
    for target_dir, rmd_files in batches:
      names = ", ".join(p.name for p in rmd_files)
      print(f"  {target_dir.relative_to(CENTAUR_DIR)}: {names}")
    sys.exit(0)

  rscript_exe = resolve_rscript()
  print(f"Using Rscript: {rscript_exe}")
  failures = []
  completed_rmds = 0
  t_start = time.time()

  with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
    futures = {
      pool.submit(compile_directory_batch, batch, rscript_exe): batch[0]
      for batch in batches
    }
    for future in as_completed(futures):
      rel_dir, elapsed, results = future.result()
      dir_ok = all(r["ok"] for r in results)
      completed_rmds += len(results)
      status = "OK" if dir_ok else "FAIL"
      print(
        f"[{completed_rmds}/{total_rmds}] {status} {rel_dir} ({elapsed:.1f}s)"
      )
      for res in results:
        if not res["ok"]:
          failures.append(res)
          print(f"  FAILED: {res['rmd']} (rc={res['returncode']})")
          if res["stdout"]:
            print(f"  STDOUT:\n{res['stdout']}")
          if res["stderr"]:
            print(f"  STDERR:\n{res['stderr']}")

  total_elapsed = time.time() - t_start
  print(
    f"Finished {total_rmds - len(failures)}/{total_rmds} PDFs in {total_elapsed:.1f}s."
  )

  if failures:
    sys.exit(1)


if __name__ == "__main__":
  main()
