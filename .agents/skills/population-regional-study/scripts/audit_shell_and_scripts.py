"""Gatekeeper S: Static audit of ad-hoc Python and Node.js regional scripts for host-starving
CPU/GPU/RAM anti-patterns, unclosed headless browsers, orphaned detached spawns and unguarded
Stadestér/Velkscala invocations.
"""

import argparse
import ast
import json
import os
import re
import sys


SKIP_DIRS = {
  ".git",
  ".Rproj.user",
  "__pycache__",
  "_gis_cache",
  "archive",
  "diagnostics_visual",
  "figures",
  "node_modules",
  "papers",
}

UNBOUNDED_NODE_HEAP_RE = re.compile(r"--max-old-space-size\s*=\s*(\d+)")
JS_DETACHED_RE = re.compile(r"\bdetached\s*:\s*true\b")
JS_PUPPETEER_LAUNCH_RE = re.compile(r"\bpuppeteer\s*\.\s*launch\s*\(")
JS_BROWSER_CLOSE_RE = re.compile(r"\b(?:browser|page)\s*\.\s*close\s*\(")
JS_FINALLY_RE = re.compile(r"\bfinally\s*\{")
JS_DIRECT_STADESTER_RE = re.compile(r"\b(?:population_Stadester|population_Velkscala)\.js\b")
PY_BROWSER_LAUNCH_RE = re.compile(r"\bwebdriver\.(?:Chrome|Edge|Firefox)\s*\(|\basync_playwright\s*\(|\bsync_playwright\s*\(")
PY_BROWSER_CLOSE_RE = re.compile(r"\.(?:quit|close)\s*\(")


def extract_int_constant (arg0_node):
  """Extracts an integer literal from an AST node or returns None."""
  if isinstance(arg0_node, ast.Constant) and isinstance(arg0_node.value, int):
    return int(arg0_node.value)
  return None


def audit_python_script (arg0_source, arg1_label):
  """Audits an ad-hoc Python script for uncapped worker pools, detached spawns and unclosed browsers."""
  errors = []
  warnings = []
  try:
    tree = ast.parse(arg0_source)
  except SyntaxError as exc:
    return [f"[{arg1_label}] SyntaxError prevents shell resource audit: {exc}"], warnings

  has_browser_launch = bool(PY_BROWSER_LAUNCH_RE.search(arg0_source))
  has_browser_close = bool(PY_BROWSER_CLOSE_RE.search(arg0_source))
  has_try_finally = any(isinstance(n, ast.Try) and len(n.finalbody) > 0 for n in ast.walk(tree))
  has_with_stmt = any(isinstance(n, (ast.With, ast.AsyncWith)) for n in ast.walk(tree))

  if has_browser_launch and not (has_browser_close and (has_try_finally or has_with_stmt)):
    errors.append(
      f"[{arg1_label}] Launches Selenium/Playwright browser without `try...finally` (or `with`) teardown calling `.quit()`/`.close()`; risks orphaned browser processes."
    )

  for m in UNBOUNDED_NODE_HEAP_RE.finditer(arg0_source):
    mb = int(m.group(1))
    if mb > 8192:
      errors.append(
        f"[{arg1_label}] Spawns Node with `--max-old-space-size={mb}` (> 8.192 MiB cap; align with `geopng_compute.json5`)."
      )

  for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
      continue
    fn_name = ""
    if isinstance(node.func, ast.Name):
      fn_name = node.func.id
    elif isinstance(node.func, ast.Attribute):
      fn_name = node.func.attr

    if fn_name in {"ProcessPoolExecutor", "ThreadPoolExecutor"}:
      mw_node = None
      if node.args:
        mw_node = node.args[0]
      for kw in node.keywords:
        if kw.arg == "max_workers":
          mw_node = kw.value
      if mw_node is None:
        errors.append(
          f"[{arg1_label}] line {node.lineno}: `{fn_name}()` without explicit `max_workers <= 4` defaults to saturating all CPU threads."
        )
      else:
        mw_val = extract_int_constant(mw_node)
        if mw_val is not None and mw_val > 4:
          errors.append(
            f"[{arg1_label}] line {node.lineno}: `{fn_name}(max_workers={mw_val})` exceeds `geopng_compute.json5` cap (<= 4)."
          )
        elif mw_val is None:
          src_seg = ast.get_source_segment(arg0_source, mw_node) or ""
          if "cpu_count" in src_seg and "min(" not in src_seg:
            errors.append(
              f"[{arg1_label}] line {node.lineno}: `{fn_name}` derives workers from uncapped `cpu_count()` (`{src_seg}`); wrap with `min(4, ...)`."
            )

    elif fn_name == "Pool":
      p_node = node.args[0] if node.args else None
      for kw in node.keywords:
        if kw.arg == "processes":
          p_node = kw.value
      if p_node is None:
        errors.append(
          f"[{arg1_label}] line {node.lineno}: `multiprocessing.Pool()` without explicit `processes <= 4` saturates all CPU cores."
        )
      else:
        p_val = extract_int_constant(p_node)
        if p_val is not None and p_val > 4:
          errors.append(
            f"[{arg1_label}] line {node.lineno}: `Pool(processes={p_val})` exceeds cap (<= 4)."
          )

    elif fn_name == "Popen":
      for kw in node.keywords:
        if kw.arg == "creationflags":
          seg = ast.get_source_segment(arg0_source, kw.value) or ""
          if "DETACHED_PROCESS" in seg:
            errors.append(
              f"[{arg1_label}] line {node.lineno}: `subprocess.Popen(..., DETACHED_PROCESS)` creates unmanageable orphan processes."
            )
      if not any(tok in arg0_source for tok in (".wait(", ".communicate(", ".terminate(", ".kill(")):
        warnings.append(
          f"[{arg1_label}] line {node.lineno}: `subprocess.Popen` called without visible `.wait()`/`.communicate()`/`.terminate()` cleanup."
        )

  if JS_DIRECT_STADESTER_RE.search(arg0_source) and "run_bounded.py" not in arg0_source:
    errors.append(
      f"[{arg1_label}] Invokes `population_Stadester.js`/`population_Velkscala.js` directly without `run_bounded.py --lock stadester_velkscala` mutex."
    )

  #Return statement
  return errors, warnings


def audit_js_script (arg0_source, arg1_label):
  """Audits an ad-hoc Node.js script for detached spawns, unclosed Puppeteer browsers, heap bloat and unguarded pipeline calls."""
  errors = []
  warnings = []

  if JS_DETACHED_RE.search(arg0_source):
    errors.append(
      f"[{arg1_label}] Uses `detached: true` in child process spawn; risks orphaned background processes."
    )

  if JS_PUPPETEER_LAUNCH_RE.search(arg0_source):
    if not (JS_BROWSER_CLOSE_RE.search(arg0_source) and JS_FINALLY_RE.search(arg0_source)):
      errors.append(
        f"[{arg1_label}] Calls `puppeteer.launch()` without a `finally {{ ... browser.close() }}` block; risks orphaned Chrome processes."
      )

  for m in UNBOUNDED_NODE_HEAP_RE.finditer(arg0_source):
    mb = int(m.group(1))
    if mb > 8192:
      errors.append(
        f"[{arg1_label}] Spawns Node with `--max-old-space-size={mb}` (> 8.192 MiB ceiling)."
      )

  if re.search(r"os\.cpus\(\)\.length", arg0_source) and not re.search(r"Math\.min\s*\([^)]*os\.cpus\(\)\.length", arg0_source):
    errors.append(
      f"[{arg1_label}] Uses uncapped `os.cpus().length` for worker concurrency; clamp via `Math.min(4, os.cpus().length)`."
    )

  base = os.path.basename(arg1_label).lower()
  if base not in {"population_stadester.js", "population_velkscala.js"}:
    if JS_DIRECT_STADESTER_RE.search(arg0_source) and "spawn" in arg0_source and "run_bounded.py" not in arg0_source:
      errors.append(
        f"[{arg1_label}] Spawns `population_Stadester.js`/`population_Velkscala.js` without `run_bounded.py --lock stadester_velkscala`."
      )

  #Return statement
  return errors, warnings


def audit_target (arg0_target_path):
  """Scans a file or directory of regional/test `.py` and `.js` scripts for shell resource anti-patterns."""
  abs_target = os.path.abspath(arg0_target_path)
  if not os.path.exists(abs_target):
    return {"errors": [f"Target path not found: {arg0_target_path}"], "files_checked": 0, "success": False, "warnings": []}

  files = []
  if os.path.isfile(abs_target):
    files = [abs_target]
    base_root = os.path.dirname(abs_target)
  else:
    base_root = abs_target
    for cur_dir, dirs, fnames in os.walk(abs_target):
      dirs[:] = sorted([d for d in dirs if d not in SKIP_DIRS])
      for fn in sorted(fnames):
        if fn.lower().endswith((".py", ".js")):
          files.append(os.path.join(cur_dir, fn))

  all_errors = []
  all_warnings = []
  for fpath in files:
    rel = os.path.relpath(fpath, base_root).replace("\\", "/")
    try:
      src = open(fpath, "r", encoding="utf-8", errors="replace").read()
    except OSError:
      continue
    if fpath.lower().endswith(".py"):
      errs, warns = audit_python_script(src, rel)
    else:
      errs, warns = audit_js_script(src, rel)
    all_errors.extend(errs)
    all_warnings.extend(warns)

  #Return statement
  return {
    "errors": all_errors,
    "files_checked": len(files),
    "success": len(all_errors) == 0,
    "warnings": all_warnings,
  }


def main ():
  parser = argparse.ArgumentParser(description="Gatekeeper S: Audit ad-hoc Python/JS scripts for CPU/GPU/RAM & orphan hazards.")
  parser.add_argument("target", help="Path to a script, regional project directory or tests/ directory")
  parser.add_argument("--json", action="store_true")
  parsed = parser.parse_args()

  res = audit_target(parsed.target)
  if parsed.json:
    print(json.dumps(res, indent=2, ensure_ascii=False))
  else:
    for w in res["warnings"][:30]:
      print(f"[WARN] {w}")
    for e in res["errors"][:50]:
      print(f"[FAIL] {e}", file=sys.stderr)
    print(
      f"[audit_shell_and_scripts] {parsed.target}: {res['files_checked']} file(s), "
      f"{len(res['errors'])} error(s), {len(res['warnings'])} warning(s)."
    )

  sys.exit(0 if res["success"] else 1)


if __name__ == "__main__":
  main()
