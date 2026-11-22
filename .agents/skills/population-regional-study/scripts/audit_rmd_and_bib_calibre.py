"""Gatekeeper D2: Audits Viscount chapter & project Rmd/bib calibre, archival PDFs,
anti-fallback provenance rules, Zipf sample-size floors and compiled PDF geometry.

Thresholds enforced here are anti-stub guardrails, never target stopping quotas.
"""

import argparse
import glob
import hashlib
import json
import os
import re
import sys

try:
  import json5
except ImportError:
  json5 = None

try:
  import pymupdf
except ImportError:
  import fitz as pymupdf

ZENODO_BIB_RE = re.compile(r"zenodo\.org|10\.5281/zenodo|\bzenodo\b", re.IGNORECASE)
CROWD_BIB_RE = re.compile(r"wikidata\.org|openstreetmap\.org|overpass-api|geonames\.org|wikipedia\.org", re.IGNORECASE)
URL_HOST_RE = re.compile(r"https?://(?:www\.)?([A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.IGNORECASE)
PUBLISHER_FIELD_RE = re.compile(r"(?i)\b(?:journal|publisher|institution|booktitle)\s*=\s*[\{\"]([^\}\"]+)")


def _load_skill_profiles():
  """Loads `.agents/skills/population-regional-study/config/viscount_skill_profiles.json5`."""
  p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config/viscount_skill_profiles.json5")
  if not os.path.isfile(p):
    return {}
  raw = open(p, "r", encoding="utf-8", errors="replace").read()
  try:
    return json5.loads(raw) if json5 else json.loads(re.sub(r"//.*?$", "", raw, flags=re.MULTILINE))
  except Exception:
    return {}


def _audit_pdf_deadspace(arg0_doc, arg1_pdf_path, arg2_label, arg3_errors, arg4_warnings=None):
  """Measures interior page vertical ink/content occupancy via PyMuPDF to catch excessive PDF deadspace."""
  pages = len(arg0_doc)
  if pages < 3:
    return 0
  pdf_name = os.path.basename(arg1_pdf_path)
  deadspace_pages = 0
  in_sources_section = False

  for page_idx in range(1, pages - 1):
    page = arg0_doc[page_idx]
    txt = page.get_text("text") or ""
    if re.search(r"(?m)^\s*(?:Sources|Footnotes|Appendix)\s*$", txt):
      in_sources_section = True
      continue
    if in_sources_section:
      continue
    # Skip page immediately before a Sources/Appendix heading if it ends a section cleanly
    next_txt = arg0_doc[page_idx + 1].get_text("text") or ""
    if re.search(r"^\s*(?:Sources|Appendix)\b", next_txt.lstrip()):
      continue

    page_h = float(page.rect.height)
    top_m = 68.0
    bot_m = page_h - 68.0
    printable_h = max(1.0, bot_m - top_m)

    intervals = []
    for blk in page.get_text("blocks"):
      if len(blk) >= 4:
        y0 = max(top_m, min(bot_m, float(blk[1])))
        y1 = max(top_m, min(bot_m, float(blk[3])))
        if y1 - y0 >= 3.0:
          intervals.append((y0, y1))
    for img_info in page.get_image_info(xrefs=False):
      bb = img_info.get("bbox")
      if bb and len(bb) >= 4:
        y0 = max(top_m, min(bot_m, float(bb[1])))
        y1 = max(top_m, min(bot_m, float(bb[3])))
        if y1 - y0 >= 8.0:
          intervals.append((y0, y1))
    for drw in page.get_drawings():
      rect = drw.get("rect")
      if rect is not None:
        y0 = max(top_m, min(bot_m, float(rect.y0)))
        y1 = max(top_m, min(bot_m, float(rect.y1)))
        if y1 - y0 >= 4.0 and (float(rect.x1) - float(rect.x0)) >= 20.0:
          intervals.append((y0, y1))

    if not intervals:
      deadspace_pages += 1
      arg3_errors.append(f"[{arg2_label}] {pdf_name} p.{page_idx + 1}: [DEADSPACE] blank interior page (0% vertical occupancy).")
      continue

    intervals.sort()
    merged = [intervals[0]]
    for y0, y1 in intervals[1:]:
      py0, py1 = merged[-1]
      if y0 <= py1 + 6.0:
        merged[-1] = (py0, max(py1, y1))
      else:
        merged.append((y0, y1))

    occupied_pt = sum(y1 - y0 for y0, y1 in merged)
    occ_ratio = occupied_pt / printable_h

    gaps = [merged[0][0] - top_m, bot_m - merged[-1][1]]
    for i in range(len(merged) - 1):
      gaps.append(merged[i + 1][0] - merged[i][1])
    max_gap_ratio = max(gaps) / printable_h if gaps else 0.0

    if occ_ratio < 0.35 or max_gap_ratio > 0.55:
      deadspace_pages += 1
      arg3_errors.append(
        f"[{arg2_label}] {pdf_name} p.{page_idx + 1}: [DEADSPACE] excessive interior page whitespace "
        f"(occupancy={occ_ratio*100:.1f}% < 35% or max_gap={max_gap_ratio*100:.1f}% > 55%); tune float heights (<= 0,42\\textheight) and LaTeX float fractions."
      )
    elif occ_ratio < 0.48 and arg4_warnings is not None:
      arg4_warnings.append(
        f"[{arg2_label}] {pdf_name} p.{page_idx + 1}: elevated interior page deadspace (occupancy={occ_ratio*100:.1f}% < 48%)."
      )

  return deadspace_pages


BANNED_FALLBACK_PATTERNS = [
  ("mcevedy", re.compile(r"\bmcevedy\b", re.IGNORECASE)),
  ("kleingoldewijk", re.compile(r"\bklein\s*goldewijk\b", re.IGNORECASE)),
  ("populstat", re.compile(r"\bpopulstat\b", re.IGNORECASE)),
  ("chandler1987", re.compile(r"\bchandler\s*1987\b", re.IGNORECASE)),
  ("modelski2003", re.compile(r"\bmodelski\s*2003\b", re.IGNORECASE)),
  ("maddison", re.compile(r"\bmaddison\b", re.IGNORECASE))
]

SKIP_DIRS = {"_shared", "archive", "diagnostics_visual", "papers", ".git", ".Rproj.user", "figures"}

MONO_FONT_SUBSTRINGS = (
  "lmmono",
  "courier",
  "consolas",
  "inconsolata",
  "dejavusansmono",
  "cmtt",
  "lmtt",
  "firacode",
  "jetbrainsmono"
)


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


def rmd_has_visible_code_blocks(arg0_pdf_path):
  """Returns True if the sibling Rmd intentionally displays fenced code or echo=TRUE chunks."""
  stem = os.path.splitext(arg0_pdf_path)[0]
  rmd_path = None
  for ext in (".Rmd", ".rmd"):
    cand = stem + ext
    if os.path.isfile(cand):
      rmd_path = cand
      break
  if not rmd_path:
    return False

  try:
    with open(rmd_path, "r", encoding="utf-8", errors="replace") as fh:
      lines = fh.read().splitlines()
  except OSError:
    return False

  idx = 0
  if lines and lines[0].strip() == "---":
    for y_idx in range(1, len(lines)):
      if lines[y_idx].strip() == "---":
        idx = y_idx + 1
        break

  global_echo_false = False
  in_fence = False
  fence_header = ""
  chunk_body = []

  while idx < len(lines):
    stripped = lines[idx].strip()
    if stripped.startswith("```"):
      if not in_fence:
        in_fence = True
        fence_header = stripped[3:].strip()
        chunk_body = []
      else:
        body_text = "\n".join(chunk_body)
        if "opts_chunk$set" in body_text and re.search(r"echo\s*=\s*(?:FALSE|F)\b", body_text):
          global_echo_false = True
        if "viscount_rmd_helpers.R" in body_text:
          global_echo_false = True

        has_nonempty_body = any(ln.strip() for ln in chunk_body)
        if not fence_header.startswith("{="):
          knitr_m = re.match(r"^\{\s*(?:r|python|bash|sh|stan|sql)\b([^}]*)\}", fence_header, flags=re.IGNORECASE)
          if knitr_m:
            opts_str = knitr_m.group(1) or ""
            is_hidden = bool(re.search(r"\b(?:include|echo)\s*=\s*(?:FALSE|F)\b", opts_str))
            is_explicit_echo = bool(re.search(r"\becho\s*=\s*(?:TRUE|T)\b", opts_str))
            if is_explicit_echo and has_nonempty_body:
              return True
            if not is_hidden and not global_echo_false and has_nonempty_body:
              return True
          elif has_nonempty_body:
            return True
        in_fence = False
        fence_header = ""
        chunk_body = []
    elif in_fence:
      chunk_body.append(lines[idx])
    idx += 1

  return False


def _audit_page1_orphaned_headings(arg0_page, arg1_pdf_path, arg2_label, arg3_errors, arg4_warnings=None):
  """Flags Page-1 bottom Jost-Bold / Abstract headings stranded with fewer than 2 body prose lines beneath them."""
  page_dict = arg0_page.get_text("dict")
  page_h = float(arg0_page.rect.height)
  visual_lines = []

  for blk in page_dict.get("blocks", []):
    if blk.get("type", 0) != 0:
      continue
    for line in blk.get("lines", []):
      spans = line.get("spans", [])
      line_text = "".join(sp.get("text", "") for sp in spans).strip()
      if not line_text:
        continue
      y0 = float(line["bbox"][1])
      y1 = float(line["bbox"][3])
      if y0 > page_h - 45.0 and (re.fullmatch(r"\d+", line_text) or len(line_text) < 40):
        continue
      max_size = max((float(sp.get("size", 0.0)) for sp in spans), default=0.0)
      is_jost_bold = any(
        "jost" in sp.get("font", "").lower() and "bold" in sp.get("font", "").lower() and float(sp.get("size", 0.0)) >= 10.3
        for sp in spans
      )
      is_caption = bool(re.match(r"^(?:Figure|Fig\.?|Table|Note|Source)\s*\d*\s*[:.]", line_text, re.IGNORECASE))
      visual_lines.append({
        "is_caption": is_caption,
        "is_jost_bold": is_jost_bold,
        "max_size": max_size,
        "text": line_text,
        "y0": y0,
        "y1": y1
      })

  pdf_name = os.path.basename(arg1_pdf_path)
  for line_info in visual_lines:
    if line_info["is_caption"]:
      continue
    is_abstract_hdr = (
      bool(re.fullmatch(r"(?:\d+(?:\.\d+)*\.?\s+)?abstract", line_info["text"], re.IGNORECASE))
      and line_info["max_size"] >= 10.3
    )
    is_bottom_section_hdr = (
      line_info["is_jost_bold"]
      and line_info["max_size"] <= 14.5
      and line_info["y0"] >= page_h * 0.52
    )
    if not (is_abstract_hdr or is_bottom_section_hdr):
      continue

    body_lines_below = 0
    for below in visual_lines:
      if below is line_info or below["y0"] <= line_info["y1"] - 1.0:
        continue
      if below["is_caption"] or below["is_jost_bold"]:
        continue
      if len(below["text"]) >= 25:
        body_lines_below += 1

    if body_lines_below < 2:
      arg3_errors.append(
        f"[{arg2_label}] {pdf_name} p.1: Orphaned Page-1 heading `{line_info['text']}` (y={line_info['y0']:.1f} pt) "
        f"with only {body_lines_below} prose line(s) beneath it; push heading to Page 2 with its paragraph and forbid sub-headings inside Abstract."
      )
    elif body_lines_below == 2 and arg4_warnings is not None:
      arg4_warnings.append(
        f"[{arg2_label}] {pdf_name} p.1: Shallow Page-1 heading `{line_info['text']}` (y={line_info['y0']:.1f} pt) "
        f"with only 2 prose lines beneath it; consider moving to Page 2."
      )


def audit_compiled_pdf(arg0_pdf_path, arg1_label, arg2_errors, arg3_warnings=None):
  """Inspects a compiled Viscount PDF via PyMuPDF for overflow (`max_x1 > 540.5` pt), blank Page 1, orphaned Page-1 headings, unintended monospace fonts, repeated headers, replacement/.notdef glyphs and `??` tokens."""
  try:
    doc = pymupdf.open(arg0_pdf_path)
  except Exception as exc:
    arg2_errors.append(f"[{arg1_label}] Failed to open compiled PDF {os.path.basename(arg0_pdf_path)}: {exc}")
    return {"max_x1": None, "pages": 0, "qq_hits": 0, "mono_pages": 0}

  max_x1 = 0.0
  qq_hits = 0
  pages = len(doc)
  qq_pattern = re.compile(r"(?:Table|Figure|Fig\.|Section|Eq\.|\[\s*)\?\?|\?\?\s*\]|(?<![A-Za-z0-9?])\?\?(?![A-Za-z0-9?])")
  repeated_header_hits = 0
  tofu_chars = 0
  mono_pages = []
  has_code_blocks = rmd_has_visible_code_blocks(arg0_pdf_path)

  try:
    if pages >= 1:
      p1_text = doc[0].get_text("text").strip()
      if len(p1_text) < 80:
        arg2_errors.append(
          f"[{arg1_label}] {os.path.basename(arg0_pdf_path)} p.1: Page 1 appears nearly blank ({len(p1_text)} chars); rescale hero figure <= 0,52\\textheight."
        )
      _audit_page1_orphaned_headings(doc[0], arg0_pdf_path, arg1_label, arg2_errors, arg3_warnings)

    for page_idx, page in enumerate(doc):
      for blk in page.get_text("blocks"):
        if blk[2] > max_x1:
          max_x1 = float(blk[2])
      if not has_code_blocks:
        page_fonts = doc.get_page_fonts(page_idx)
        if any(any(sub in str(f_info[3]).lower() for sub in MONO_FONT_SUBSTRINGS) for f_info in page_fonts):
          mono_pages.append(page_idx + 1)
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

    if mono_pages and not has_code_blocks:
      pdf_name = os.path.basename(arg0_pdf_path)
      is_legacy_settlements = pdf_name.lower().endswith("_settlements.pdf")
      single_page_spans = 0
      if is_legacy_settlements and len(mono_pages) == 1:
        mono_page_dict = doc[mono_pages[0] - 1].get_text("dict")
        for blk in mono_page_dict.get("blocks", []):
          if blk.get("type", 0) != 0:
            continue
          for line in blk.get("lines", []):
            for sp in line.get("spans", []):
              if sp.get("text", "").strip() and any(sub in sp.get("font", "").lower() for sub in MONO_FONT_SUBSTRINGS):
                single_page_spans += 1
      if is_legacy_settlements and len(mono_pages) == 1 and single_page_spans <= 2:
        if arg3_warnings is not None:
          arg3_warnings.append(
            f"[{arg1_label}] {pdf_name} p.{mono_pages[0]}: minor legacy monospace font usage ({single_page_spans} span(s)); strip non-code backticks on regeneration."
          )
      else:
        arg2_errors.append(
          f"[{arg1_label}] {pdf_name}: unexpected monospace font on page(s) {mono_pages} "
          f"(monospace is reserved strictly for code; strip non-code backticks/\\texttt from captions, headings, prose and tables)."
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
    deadspace_pages = _audit_pdf_deadspace(doc, arg0_pdf_path, arg1_label, arg2_errors, arg3_warnings)
  finally:
    doc.close()

  return {"deadspace_pages": deadspace_pages, "max_x1": round(max_x1, 2), "pages": pages, "qq_hits": qq_hits, "mono_pages": len(mono_pages)}


def count_unique_bib_keys(arg0_chapter_dir, arg1_bib_names=None):
  """Returns sorted unique BibTeX entry keys, `.bib` paths, DOI/URL count, total entries and source-diversity telemetry."""
  keys = set()
  linked = 0
  total_entries = 0
  zenodo_entries = 0
  crowd_entries = 0
  publisher_domains = set()
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
        if ZENODO_BIB_RE.search(ent):
          zenodo_entries += 1
        if CROWD_BIB_RE.search(ent):
          crowd_entries += 1
        pm = PUBLISHER_FIELD_RE.search(ent)
        if pm:
          publisher_domains.add(pm.group(1).strip().lower()[:40])
        else:
          um = URL_HOST_RE.search(ent)
          if um:
            publisher_domains.add(um.group(1).strip().lower())
      for match in key_re.findall(content):
        keys.add(match.strip())
    except OSError:
      continue
  diversity = {
    "crowd_entries": crowd_entries,
    "publisher_domains": len(publisher_domains),
    "zenodo_entries": zenodo_entries,
  }
  return sorted(keys), bib_files, linked, total_entries, diversity


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


def audit_figure_and_pdf_freshness(arg0_dir, arg1_root_dir, arg2_label, arg3_require_visual_check, arg4_errors, arg5_warnings):
  """Verifies mask/GeoJSON -> figure PNG -> compiled PDF mtime synchronisation."""
  fig_dir = os.path.join(arg0_dir, "figures")
  pngs = sorted(glob.glob(os.path.join(fig_dir, "*.png"))) if os.path.isdir(fig_dir) else []
  pdfs = sorted(glob.glob(os.path.join(arg0_dir, "*.pdf")))
  if not pngs:
    return

  newest_png_m = max(os.path.getmtime(p) for p in pngs)
  if pdfs:
    oldest_pdf_m = min(os.path.getmtime(p) for p in pdfs)
    if oldest_pdf_m + 2.0 < newest_png_m:
      arg4_errors.append(
        f"[{arg2_label}] Compiled PDF is older than regenerated figure PNG(s) in figures/; recompile RMarkdown so PDFs reflect current figures and masks."
      )

  spatial_re = re.compile(r"(?:^fig1_|spatial|map|hero|zones)", re.IGNORECASE)
  spatial_pngs = [p for p in pngs if spatial_re.search(os.path.basename(p))]
  if not spatial_pngs:
    return

  source_paths = sorted(glob.glob(os.path.join(arg0_dir, "*_areal_mask.png")))
  subreg_dir = os.path.join(arg1_root_dir, "_shared", "_gis_cache", "chapter_subregions")
  for mask_p in list(source_paths):
    stem = re.sub(r"_areal_mask\.png$", "", os.path.basename(mask_p), flags=re.IGNORECASE)
    vec_p = os.path.join(subreg_dir, f"{stem}_subregions.geojson")
    if os.path.isfile(vec_p):
      source_paths.append(vec_p)
  if os.path.abspath(arg0_dir) == os.path.abspath(arg1_root_dir):
    source_paths.extend(sorted(glob.glob(os.path.join(arg1_root_dir, "_shared", "_gis_cache", "*_polygons.geojson"))))

  if not source_paths:
    return

  oldest_spatial_m = min(os.path.getmtime(p) for p in spatial_pngs)
  newest_src_m = max(os.path.getmtime(s) for s in source_paths)
  if oldest_spatial_m + 2.0 < newest_src_m:
    msg = (
      f"[{arg2_label}] Spatial figure PNG(s) are older than updated areal mask/GeoJSON sources; "
      "regenerate figures and recompile PDF."
    )
    if arg3_require_visual_check:
      arg4_errors.append(msg)
    else:
      arg5_warnings.append(msg)


def audit_visual_check_manifest(arg0_chapter_dir, arg1_label, arg2_require_visual_check, arg3_errors, arg4_warnings):
  """Verifies `figures/visual_check.json` exists, is fresh, covers all PNGs and contains genuine non-duplicated per-figure notes."""
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

  top_dict = data if isinstance(data, dict) else {}
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

  if arg2_require_visual_check and pngs:
    recorded_names = set()
    dict_entries = []
    for ent in entries:
      if isinstance(ent, dict):
        dict_entries.append(ent)
        fn_e = str(ent.get("file") or ent.get("panel") or "").strip()
        if fn_e:
          recorded_names.add(os.path.basename(fn_e))
      elif isinstance(ent, str) and ent.strip():
        recorded_names.add(os.path.basename(ent.strip()))

    missing_pngs = [os.path.basename(p) for p in pngs if os.path.basename(p) not in recorded_names]
    if missing_pngs:
      arg3_errors.append(
        f"[{arg1_label}] figures/visual_check.json omits rendered PNG(s): {missing_pngs[:5]}."
      )

    if len(dict_entries) < len(pngs):
      arg3_errors.append(
        f"[{arg1_label}] figures/visual_check.json must contain one dict entry per PNG (`{len(dict_entries)}`/`{len(pngs)}`) with unique figure-specific notes."
      )
    else:
      notes_list = [str(e.get("notes") or "").strip() for e in dict_entries]
      short_notes = [str(e.get("file", "?")) for e, n in zip(dict_entries, notes_list) if len(n) < 50]
      if short_notes:
        arg3_errors.append(
          f"[{arg1_label}] figures/visual_check.json entries lack >= 50-char figure-specific visual notes: {short_notes[:5]}."
        )
      elif len(set(notes_list)) < len(notes_list) and len(notes_list) >= 2:
        arg3_errors.append(
          f"[{arg1_label}] figures/visual_check.json contains duplicate boilerplate `notes` across figures; write unique observations per PNG via `read_file`."
        )

      top_zero = top_dict.get("zero_occlusion_and_in_panel_bounds") is True
      top_parity = top_dict.get("polaris_visual_parity") is True
      missing_att = []
      for ent in dict_entries:
        fn_e = str(ent.get("file") or ent.get("panel") or "?")
        if not (top_zero or ent.get("zero_occlusion_and_in_panel_bounds") is True):
          missing_att.append(f"{fn_e}:zero_occlusion_and_in_panel_bounds")
        if not (top_parity or ent.get("polaris_visual_parity") is True):
          missing_att.append(f"{fn_e}:polaris_visual_parity")
      if missing_att:
        arg3_errors.append(
          f"[{arg1_label}] figures/visual_check.json missing required true attestation(s): {missing_att[:5]}."
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

  # Archival PDFs in ./papers/ (validity + SHA-256 uniqueness)
  papers_dir = os.path.join(arg0_chapter_dir, "papers")
  valid_pdfs = []
  seen_pdf_hashes = {}
  if not os.path.isdir(papers_dir):
    errors.append(f"[{rel_label}] Missing ./papers/ directory (anti-stub guardrail requires >= 15 valid archival PDFs).")
  else:
    for pdf_path in sorted(glob.glob(os.path.join(papers_dir, "*.pdf"))):
      if is_valid_pdf_file(pdf_path):
        h_val = hashlib.sha256(open(pdf_path, "rb").read()).hexdigest()
        if h_val in seen_pdf_hashes:
          errors.append(
            f"[{rel_label}] Duplicate archival PDF in ./papers/: `{os.path.basename(pdf_path)}` is identical to `{seen_pdf_hashes[h_val]}`."
          )
        else:
          seen_pdf_hashes[h_val] = os.path.basename(pdf_path)
          valid_pdfs.append(os.path.basename(pdf_path))
      else:
        errors.append(
          f"[{rel_label}] Corrupt/stub archival file papers/{os.path.basename(pdf_path)} (failed > 10 KB + `%PDF-` magic check)."
        )
    if len(valid_pdfs) < 15:
      errors.append(
        f"[{rel_label}] Only {len(valid_pdfs)} unique valid PDFs in ./papers/ (anti-stub guardrail requires >= 15 valid `%PDF-` files)."
      )

  # Unique .bib entries, DOI/URL coverage & source diversity (anti-Zenodo / anti-Wikidata-only)
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

  profiles = _load_skill_profiles()
  caps = profiles.get("provenance_caps") or {}
  max_zen_ch = float(caps.get("max_zenodo_bib_ratio_chapter", 0.15))
  max_crowd_bib = float(caps.get("max_crowd_bib_ratio", 0.10))
  min_pub_doms = int(caps.get("min_bib_publisher_domains", 5))

  bib_keys, bib_files, linked_entries, total_bib_entries, bib_div = count_unique_bib_keys(arg0_chapter_dir, ref_bibs or None)
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
    zen_ratio = float(bib_div["zenodo_entries"]) / total_bib_entries
    if zen_ratio > max_zen_ch:
      errors.append(
        f"[{rel_label}] [BIB_DIVERSITY] Excessive Zenodo reliance: {bib_div['zenodo_entries']}/{total_bib_entries} "
        f"({zen_ratio*100:.1f}% > {max_zen_ch*100:.0f}% chapter cap); cite diverse peer-reviewed journals, university presses and national statistical sources."
      )
    crowd_ratio = float(bib_div["crowd_entries"]) / total_bib_entries
    if crowd_ratio > max_crowd_bib:
      errors.append(
        f"[{rel_label}] [BIB_DIVERSITY] Excessive Wikidata/OSM/GeoNames/Wikipedia citations: {bib_div['crowd_entries']}/{total_bib_entries} "
        f"({crowd_ratio*100:.1f}% > {max_crowd_bib*100:.0f}% cap)."
      )
    if total_bib_entries >= 10 and bib_div["publisher_domains"] < min_pub_doms:
      errors.append(
        f"[{rel_label}] [BIB_DIVERSITY] Bibliography cites only {bib_div['publisher_domains']} distinct publisher/journal/domain(s) (< {min_pub_doms} minimum)."
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

  audit_figure_and_pdf_freshness(arg0_chapter_dir, arg1_root_dir, rel_label, require_visual, errors, warnings)
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
    require_vis_root = bool(opts.get("require_visual_check", False))
    audit_figure_and_pdf_freshness(target_abs, target_abs, "root", require_vis_root, all_errors, all_warnings)
    if glob.glob(os.path.join(target_abs, "figures", "*.png")):
      audit_visual_check_manifest(target_abs, "root", require_vis_root, all_errors, all_warnings)

  if not chapter_dirs:
    all_errors.append(f"No Viscount chapter directories containing .Rmd files found under {arg0_target_path}.")

  for chap_dir in chapter_dirs:
    metrics, errs, warns = audit_chapter_dir(chap_dir, target_abs, opts)
    chapter_reports.append(metrics)
    all_errors.extend(errs)
    all_warnings.extend(warns)

  # Project-level Zenodo cap & per-jurisdiction historical demography literature check
  if chapter_dirs != [target_abs] and chapter_dirs:
    profiles = _load_skill_profiles()
    caps = profiles.get("provenance_caps") or {}
    max_zen_proj = float(caps.get("max_zenodo_bib_ratio_project", 0.10))
    proj_bib_text = []
    proj_paper_names = []
    total_proj_bib = 0
    total_proj_zen = 0
    for b_p in [os.path.join(target_abs, "studies_on_population.bib")] + [
      b for c_d in chapter_dirs for b in sorted(glob.glob(os.path.join(c_d, "*.bib")))
      if os.path.basename(b).lower() != "intellte-sample.bib"
    ]:
      if os.path.isfile(b_p):
        b_txt = open(b_p, "r", encoding="utf-8", errors="replace").read()
        proj_bib_text.append(b_txt)
        if os.path.basename(b_p).lower() == "studies_on_population.bib":
          ents = re.split(r"(?m)^\s*@[A-Za-z]+\s*\{", b_txt)[1:]
          total_proj_bib = len(ents)
          total_proj_zen = sum(1 for e in ents if ZENODO_BIB_RE.search(e))
    for c_d in chapter_dirs:
      p_d = os.path.join(c_d, "papers")
      if os.path.isdir(p_d):
        proj_paper_names.extend(os.listdir(p_d))
    if total_proj_bib > 0 and (float(total_proj_zen) / total_proj_bib) > max_zen_proj:
      all_errors.append(
        f"[root] [BIB_DIVERSITY] Project-wide Zenodo citation share is {total_proj_zen}/{total_proj_bib} "
        f"({100.0 * total_proj_zen / total_proj_bib:.1f}% > {max_zen_proj*100:.0f}% ceiling)."
      )
    proj_key = os.path.basename(target_abs).upper()
    j_matrix = (profiles.get("jurisdiction_source_matrix") or {}).get(proj_key)
    if isinstance(j_matrix, dict):
      corpus_blob = ("\n".join(proj_bib_text) + "\n" + "\n".join(proj_paper_names)).lower()
      for j_item in j_matrix.get("required_jurisdictions") or []:
        if not isinstance(j_item, dict):
          continue
        label_tokens = [
          t for t in re.split(r"[^a-z]+", str(j_item.get("label") or "").lower())
          if len(t) >= 4 and t not in {"incl", "excl", "main", "south", "north", "east", "west", "associated", "territories", "provinces", "archipelago"}
        ]
        if label_tokens and not any(tok in corpus_blob for tok in label_tokens):
          all_errors.append(
            f"[root] [JURISDICTION_LIT] Required jurisdiction `{j_item.get('id')}` ({j_item.get('label')}) has 0 matching historical demography references across project `.bib` / `./papers/`."
          )

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
