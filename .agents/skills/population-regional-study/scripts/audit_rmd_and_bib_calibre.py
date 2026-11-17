"""Gatekeeper D2: Audits Viscount chapter & project Rmd/bib calibre, archival PDFs,
anti-fallback provenance rules, Zipf sample-size floors and compiled PDF geometry.

Thresholds enforced here are anti-stub guardrails, never target stopping quotas.
"""

import argparse
import glob
import json
import os
import re
import sys

try:
  import pymupdf
except ImportError:
  import fitz as pymupdf


BANNED_FALLBACK_PATTERNS = [
  ("mcevedy", re.compile(r"\bmcevedy\b", re.IGNORECASE)),
  ("kleingoldewijk", re.compile(r"\bklein\s*goldewijk\b", re.IGNORECASE)),
  ("populstat", re.compile(r"\bpopulstat\b", re.IGNORECASE)),
  ("chandler1987", re.compile(r"\bchandler\s*1987\b", re.IGNORECASE)),
  ("modelski2003", re.compile(r"\bmodelski\s*2003\b", re.IGNORECASE)),
  ("maddison", re.compile(r"\bmaddison\b", re.IGNORECASE))
]

SKIP_DIRS = {"_shared", "archive", "diagnostics_visual", "papers", ".git", ".Rproj.user", "figures"}


def is_valid_pdf_file(arg0_pdf_path):
  """Returns True when the file exceeds 10240 bytes and begins with a `%PDF-` header."""
  try:
    if os.path.getsize(arg0_pdf_path) <= 10240:
      return False
    with open(arg0_pdf_path, "rb") as fh:
      head = fh.read(1024)
    return b"%PDF-" in head
  except OSError:
    return False


def audit_compiled_pdf(arg0_pdf_path, arg1_label, arg2_errors, arg3_warnings=None):
  """Inspects a compiled Viscount PDF via PyMuPDF for overflow (`max_x1 > 540.5` pt), blank Page 1, repeated headers, replacement/.notdef glyphs and `??` tokens."""
  try:
    doc = pymupdf.open(arg0_pdf_path)
  except Exception as exc:
    arg2_errors.append(f"[{arg1_label}] Failed to open compiled PDF {os.path.basename(arg0_pdf_path)}: {exc}")
    return {"max_x1": None, "pages": 0, "qq_hits": 0}

  max_x1 = 0.0
  qq_hits = 0
  pages = len(doc)
  qq_pattern = re.compile(r"(?:Table|Figure|Fig\.|Section|Eq\.|\[\s*)\?\?|\?\?\s*\]|(?<![A-Za-z0-9?])\?\?(?![A-Za-z0-9?])")
  repeated_header_hits = 0
  tofu_chars = 0

  if pages >= 1:
    p1_text = doc[0].get_text("text").strip()
    if len(p1_text) < 80:
      arg2_errors.append(
        f"[{arg1_label}] {os.path.basename(arg0_pdf_path)} p.1: Page 1 appears nearly blank ({len(p1_text)} chars); rescale hero figure <= 0,52\\textheight."
      )

  for page_idx, page in enumerate(doc):
    for blk in page.get_text("blocks"):
      if blk[2] > max_x1:
        max_x1 = float(blk[2])
    page_text = page.get_text("text")
    if "(Continued from previous page)" in page_text:
      repeated_header_hits += 1
    tofu_chars += page_text.count("\ufffd") + page_text.count("\x00")
    matches = qq_pattern.findall(page_text)
    if matches:
      qq_hits += len(matches)
      arg2_errors.append(
        f"[{arg1_label}] {os.path.basename(arg0_pdf_path)} p.{page_idx + 1}: unresolved `??` token(s) ({len(matches)})."
      )

  if repeated_header_hits > 0:
    arg2_errors.append(
      f"[{arg1_label}] {os.path.basename(arg0_pdf_path)}: found `(Continued from previous page)` on {repeated_header_hits} page(s); leave \\endhead empty."
    )
  if tofu_chars >= 2:
    arg2_errors.append(
      f"[{arg1_label}] {os.path.basename(arg0_pdf_path)}: found {tofu_chars} missing-glyph/replacement (U+FFFD / .notdef) char(s); transliterate scripts cleanly."
    )
  elif tofu_chars == 1 and arg3_warnings is not None:
    arg3_warnings.append(
      f"[{arg1_label}] {os.path.basename(arg0_pdf_path)}: found 1 .notdef glyph character; verify script romanisation."
    )
  if max_x1 > 540.5:
    arg2_errors.append(
      f"[{arg1_label}] {os.path.basename(arg0_pdf_path)}: horizontal margin overflow max_x1={max_x1:.2f} pt (> 540.5 pt)."
    )

  return {"max_x1": round(max_x1, 2), "pages": pages, "qq_hits": qq_hits}


def count_unique_bib_keys(arg0_chapter_dir, arg1_bib_names=None):
  """Returns sorted unique BibTeX entry keys, `.bib` paths, and count of entries carrying DOI or external URL."""
  keys = set()
  linked = 0
  total_entries = 0
  if arg1_bib_names:
    bib_files = [
      os.path.join(arg0_chapter_dir, b)
      for b in arg1_bib_names
      if os.path.isfile(os.path.join(arg0_chapter_dir, b))
    ]
  else:
    bib_files = [
      b for b in sorted(glob.glob(os.path.join(arg0_chapter_dir, "*.bib")))
      if os.path.basename(b).lower() != "intellte-sample.bib"
    ]
  key_re = re.compile(r"(?m)^\s*@[A-Za-z]+\s*\{\s*([^,\s]+)")
  link_re = re.compile(r"(?i)\b(?:doi|url)\s*=\s*[\{\"](?:10\.|https?://)")
  for bib_path in bib_files:
    try:
      with open(bib_path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
      entries = re.split(r"(?m)^\s*@[A-Za-z]+\s*\{", content)[1:]
      for ent in entries:
        total_entries += 1
        if link_re.search(ent):
          linked += 1
      for match in key_re.findall(content):
        keys.add(match.strip())
    except OSError:
      continue
  return sorted(keys), bib_files, linked, total_entries


def audit_zipf_sample_floor(arg0_chapter_dir, arg1_label, arg2_errors):
  """Rejects Zipf / rank-size regressions or plots constructed on `n < 25` settlements."""
  zipf_re = re.compile(r"\b(?:zipf|rank[-_\s]*size)\b", re.IGNORECASE)
  n_re = re.compile(r"(?:\bn\s*=\s*|nrow\s*\([^)]*\)\s*[<=-]*\s*|sample\s+of\s+)(\d+)\b|\b(\d+)\s+settlements?\b", re.IGNORECASE)

  scan_files = sorted(
    glob.glob(os.path.join(arg0_chapter_dir, "*.Rmd")) +
    glob.glob(os.path.join(arg0_chapter_dir, "*.R"))
  )
  for fp in scan_files:
    try:
      with open(fp, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    except OSError:
      continue

    for idx, line in enumerate(lines):
      if zipf_re.search(line):
        window_start = max(0, idx - 4)
        window_end = min(len(lines), idx + 5)
        window_text = " ".join(lines[window_start:window_end])
        for match in n_re.finditer(window_text):
          num_str = match.group(1) or match.group(2)
          if num_str:
            n_val = int(num_str)
            if n_val < 25:
              arg2_errors.append(
                f"[{arg1_label}] {os.path.basename(fp)} line {idx + 1}: banned rank-size/Zipf analysis on small sample n={n_val} (< 25)."
              )


def audit_visual_check_manifest(arg0_chapter_dir, arg1_label, arg2_require_visual_check, arg3_errors, arg4_warnings):
  """Verifies `figures/visual_check.json` exists and is newer than all PNGs in `figures/`."""
  fig_dir = os.path.join(arg0_chapter_dir, "figures")
  pngs = sorted(glob.glob(os.path.join(fig_dir, "*.png"))) if os.path.isdir(fig_dir) else []
  manifest_path = os.path.join(fig_dir, "visual_check.json")

  if not os.path.isfile(manifest_path):
    msg = f"[{arg1_label}] Missing figures/visual_check.json inspection manifest."
    if arg2_require_visual_check:
      arg3_errors.append(msg)
    elif pngs:
      arg4_warnings.append(msg)
    return

  try:
    with open(manifest_path, "r", encoding="utf-8") as fh:
      data = json.load(fh)
  except Exception as exc:
    arg3_errors.append(f"[{arg1_label}] Invalid figures/visual_check.json: {exc}")
    return

  if isinstance(data, dict):
    entries = data.get("figures") or data.get("panels") or data.get("checked") or []
    approved = data.get("approved", True)
    if approved is False:
      arg3_errors.append(f"[{arg1_label}] figures/visual_check.json marks figures as not approved.")
  elif isinstance(data, list):
    entries = data
  else:
    entries = []

  if not entries:
    arg3_errors.append(f"[{arg1_label}] figures/visual_check.json contains no inspected figure entries.")

  if pngs:
    newest_png_mtime = max(os.path.getmtime(p) for p in pngs)
    manifest_mtime = os.path.getmtime(manifest_path)
    if manifest_mtime < newest_png_mtime:
      arg3_errors.append(
        f"[{arg1_label}] figures/visual_check.json is stale (older than newest PNG in figures/); re-inspect rendered figures."
      )


def audit_chapter_dir(arg0_chapter_dir, arg1_root_dir, arg2_options=None):
  """Audits one Viscount sub-chapter folder and returns `(metrics, errors, warnings)`."""
  opts = arg2_options if isinstance(arg2_options, dict) else {}
  require_visual = bool(opts.get("require_visual_check", False))
  require_pdfs = bool(opts.get("require_compiled_pdfs", False))
  rel_label = os.path.relpath(arg0_chapter_dir, arg1_root_dir).replace("\\", "/")
  if rel_label == ".":
    rel_label = os.path.basename(os.path.abspath(arg0_chapter_dir))

  errors = []
  warnings = []

  files = sorted(os.listdir(arg0_chapter_dir))
  rmds = [f for f in files if f.lower().endswith(".rmd")]
  settlement_stems = {
    re.sub(r"_settlements\.Rmd$", "", f, flags=re.IGNORECASE): f
    for f in rmds if f.lower().endswith("_settlements.rmd")
  }
  review_stems = {
    re.sub(r"_(?:literature_review|areal_masks_and_bins)\.Rmd$", "", f, flags=re.IGNORECASE): f
    for f in rmds if f.lower().endswith("_literature_review.rmd") or f.lower().endswith("_areal_masks_and_bins.rmd")
  }
  paired_stems = sorted(set(settlement_stems.keys()) & set(review_stems.keys()))

  if not paired_stems:
    errors.append(
      f"[{rel_label}] Missing paired `<stem>_settlements.Rmd` and `<stem>_literature_review.Rmd` (or `*_areal_masks_and_bins.Rmd`). Found: {rmds}"
    )

  review_lines = 0
  review_words = 0
  for stem in paired_stems:
    rev_path = os.path.join(arg0_chapter_dir, review_stems[stem])
    sett_path = os.path.join(arg0_chapter_dir, settlement_stems[stem])
    with open(rev_path, "r", encoding="utf-8", errors="replace") as fh:
      rev_text = fh.read()
    with open(sett_path, "r", encoding="utf-8", errors="replace") as fh:
      sett_text = fh.read()

    l_cnt = len(rev_text.splitlines())
    w_cnt = len(re.findall(r"\S+", rev_text))
    review_lines = max(review_lines, l_cnt)
    review_words = max(review_words, w_cnt)

    if l_cnt < 350:
      errors.append(
        f"[{rel_label}] {review_stems[stem]}: {l_cnt} lines below anti-stub guardrail (>= 350 lines)."
      )
    if w_cnt < 2500:
      errors.append(
        f"[{rel_label}] {review_stems[stem]}: {w_cnt} words below anti-stub guardrail (>= 2500 words)."
      )
    if len(sett_text.splitlines()) < 30:
      errors.append(f"[{rel_label}] {settlement_stems[stem]} appears stubbed (< 30 lines).")

    if require_pdfs:
      for rmd_fn in (review_stems[stem], settlement_stems[stem]):
        expected_pdf = os.path.join(arg0_chapter_dir, re.sub(r"\.Rmd$", ".pdf", rmd_fn, flags=re.IGNORECASE))
        if not os.path.isfile(expected_pdf):
          errors.append(f"[{rel_label}] Missing compiled PDF {os.path.basename(expected_pdf)}.")

  # Archival PDFs in ./papers/
  papers_dir = os.path.join(arg0_chapter_dir, "papers")
  valid_pdfs = []
  if not os.path.isdir(papers_dir):
    errors.append(f"[{rel_label}] Missing ./papers/ directory (anti-stub guardrail requires >= 15 valid archival PDFs).")
  else:
    for pdf_path in sorted(glob.glob(os.path.join(papers_dir, "*.pdf"))):
      if is_valid_pdf_file(pdf_path):
        valid_pdfs.append(os.path.basename(pdf_path))
      else:
        errors.append(
          f"[{rel_label}] Corrupt/stub archival file papers/{os.path.basename(pdf_path)} (failed > 10 KB + `%PDF-` magic check)."
        )
    if len(valid_pdfs) < 15:
      errors.append(
        f"[{rel_label}] Only {len(valid_pdfs)} valid PDFs in ./papers/ (anti-stub guardrail requires >= 15 valid `%PDF-` files)."
      )

  # Unique .bib entries & DOI/URL verification coverage
  ref_bibs = []
  for stem in paired_stems:
    for p_rmd in (os.path.join(arg0_chapter_dir, review_stems[stem]), os.path.join(arg0_chapter_dir, settlement_stems[stem])):
      try:
        rmd_hdr = open(p_rmd, "r", encoding="utf-8", errors="replace").read()
        bm = re.search(r"(?m)^bibliography\s*:\s*([^\r\n#]+)", rmd_hdr)
        if bm:
          bname = bm.group(1).strip().strip("\"'")
          if bname not in ref_bibs:
            ref_bibs.append(bname)
      except OSError:
        pass

  bib_keys, bib_files, linked_entries, total_bib_entries = count_unique_bib_keys(arg0_chapter_dir, ref_bibs or None)
  if len(bib_keys) < 20:
    errors.append(
      f"[{rel_label}] Only {len(bib_keys)} unique .bib entries across {[os.path.basename(b) for b in bib_files]} (anti-stub guardrail requires >= 20)."
    )
  if total_bib_entries > 0:
    doi_ratio = float(linked_entries) / total_bib_entries
    if doi_ratio < 0.85:
      errors.append(
        f"[{rel_label}] Referenced bibliography DOI/URL coverage is {linked_entries}/{total_bib_entries} ({doi_ratio*100:.1f}% < 85.0% floor)."
      )

  # Banned fallback datasets check, `# References` ban and wide-table check in sub-chapter .Rmd & .bib
  for fn in sorted(files):
    if fn.lower().endswith((".rmd", ".bib")):
      fp = os.path.join(arg0_chapter_dir, fn)
      with open(fp, "r", encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
      for label_kw, pat in BANNED_FALLBACK_PATTERNS:
        if pat.search(txt):
          errors.append(
            f"[{rel_label}] {fn}: banned global fallback reference `{label_kw}` found in sub-chapter source/bibliography."
          )
      if fn.lower().endswith(".rmd"):
        if re.search(r"(?m)^#\s+References\s*$", txt):
          errors.append(f"[{rel_label}] {fn}: use `# Sources` rather than `# References`.")
        for tm in re.finditer(r"col_names\s*=\s*c\(([^)]+)\)", txt):
          ncols = len(re.findall(r"[\"'][^\"']+[\"']", tm.group(1)))
          if ncols > 14:
            errors.append(f"[{rel_label}] {fn}: table defines {ncols} columns (> 14 max); split across multiple compact tables.")
          elif ncols > 10:
            warnings.append(f"[{rel_label}] {fn}: wide table has {ncols} columns (> 10); consider splitting for portrait readability.")

  audit_zipf_sample_floor(arg0_chapter_dir, rel_label, errors)

  compiled_pdfs = sorted(glob.glob(os.path.join(arg0_chapter_dir, "*.pdf")))
  pdf_metrics = {}
  for pdf_path in compiled_pdfs:
    pdf_metrics[os.path.basename(pdf_path)] = audit_compiled_pdf(pdf_path, rel_label, errors, warnings)

  audit_visual_check_manifest(arg0_chapter_dir, rel_label, require_visual, errors, warnings)

  metrics = {
    "bib_entries": len(bib_keys),
    "bib_linked_entries": linked_entries,
    "bib_total_entries": total_bib_entries,
    "chapter": rel_label,
    "compiled_pdfs": pdf_metrics,
    "review_lines": review_lines,
    "review_words": review_words,
    "valid_paper_pdfs": len(valid_pdfs)
  }
  return metrics, errors, warnings


def detect_chapter_dirs(arg0_root_dir, arg1_mode="auto"):
  """Discovers Viscount sub-chapter directories inside `arg0_root_dir`."""
  if arg1_mode == "chapter":
    return [arg0_root_dir]

  if arg1_mode == "auto":
    direct_rmds = [f for f in os.listdir(arg0_root_dir) if f.lower().endswith(".rmd")]
    has_paired_rmd = any(
      f.lower().endswith(("_settlements.rmd", "_literature_review.rmd", "_areal_masks_and_bins.rmd"))
      for f in direct_rmds
    )
    if has_paired_rmd:
      return [arg0_root_dir]

  chapter_dirs = []
  abs_root = os.path.abspath(arg0_root_dir)
  for cur_dir, dir_names, file_names in os.walk(abs_root):
    dir_names[:] = sorted([d for d in dir_names if d not in SKIP_DIRS])
    if os.path.abspath(cur_dir) == abs_root:
      continue
    if any(f.lower().endswith(".rmd") for f in file_names):
      chapter_dirs.append(cur_dir)
  return sorted(chapter_dirs)


def audit_target(arg0_target_path, arg1_options=None):
  """Audits a chapter directory or an entire Viscount macro-project directory."""
  opts = arg1_options if isinstance(arg1_options, dict) else {}
  mode = opts.get("mode", "auto")
  target_abs = os.path.abspath(arg0_target_path)

  if not os.path.isdir(target_abs):
    return {"errors": [f"Target directory does not exist: {arg0_target_path}"], "warnings": [], "chapters": []}

  chapter_dirs = detect_chapter_dirs(target_abs, mode)
  all_errors = []
  all_warnings = []
  chapter_reports = []

  # Root project overview check if project mode (multiple chapters or studies_on_population.Rmd present)
  root_rmd = os.path.join(target_abs, "studies_on_population.Rmd")
  root_metrics = None
  if chapter_dirs != [target_abs] and os.path.isfile(root_rmd):
    with open(root_rmd, "r", encoding="utf-8", errors="replace") as fh:
      root_lines = len(fh.read().splitlines())
    if root_lines < 450:
      all_errors.append(
        f"[root] studies_on_population.Rmd has {root_lines} lines (< 450 anti-stub line floor)."
      )
    root_pdf = os.path.join(target_abs, "studies_on_population.pdf")
    root_pdf_info = audit_compiled_pdf(root_pdf, "root", all_errors, all_warnings) if os.path.isfile(root_pdf) else None
    root_metrics = {"lines": root_lines, "pdf": root_pdf_info}

  if not chapter_dirs:
    all_errors.append(f"No Viscount chapter directories containing .Rmd files found under {arg0_target_path}.")

  for chap_dir in chapter_dirs:
    metrics, errs, warns = audit_chapter_dir(chap_dir, target_abs, opts)
    chapter_reports.append(metrics)
    all_errors.extend(errs)
    all_warnings.extend(warns)

  # Enforce figure-script theme, MathText and label hygiene across chapter/project scripts
  try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
      sys.path.insert(0, script_dir)
    import audit_figure_scripts
    fig_res = audit_figure_scripts.audit_target(target_abs)
    all_errors.extend(fig_res.get("errors") or [])
    all_warnings.extend(fig_res.get("warnings") or [])
  except Exception as exc:
    all_warnings.append(f"[figures] Figure script audit skipped: {exc}")

  return {
    "chapters": chapter_reports,
    "errors": all_errors,
    "root": root_metrics,
    "success": len(all_errors) == 0,
    "warnings": all_warnings
  }


def main():
  parser = argparse.ArgumentParser(description="Audit Viscount chapter/project Rmd, bibliography, archival PDF and compiled PDF calibre.")
  parser.add_argument("target_dir", help="Path to a Viscount chapter folder or macro-region project folder.")
  parser.add_argument("--mode", choices=["auto", "chapter", "project"], default="auto")
  parser.add_argument("--require-visual-check", action="store_true")
  parser.add_argument("--require-compiled-pdfs", action="store_true")
  parser.add_argument("--json", action="store_true")
  parsed = parser.parse_args()

  result = audit_target(
    parsed.target_dir,
    {
      "mode": parsed.mode,
      "require_compiled_pdfs": parsed.require_compiled_pdfs,
      "require_visual_check": parsed.require_visual_check
    }
  )

  if parsed.json:
    print(json.dumps(result, indent=2, ensure_ascii=False))
  else:
    for err in result["errors"][:50]:
      print(f"[FAIL] {err}")
    if len(result["errors"]) > 50:
      print(f"[FAIL] ... and {len(result['errors']) - 50} additional error(s).")
    for warn in result["warnings"][:30]:
      print(f"[WARN] {warn}")
    if len(result["warnings"]) > 30:
      print(f"[WARN] ... and {len(result['warnings']) - 30} additional warning(s).")
    print(
      f"[audit_rmd_and_bib_calibre] {parsed.target_dir}: {len(result['chapters'])} chapter(s), "
      f"{len(result['errors'])} error(s), {len(result['warnings'])} warning(s)."
    )

  sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
  main()
