"""Single-invocation batched PyMuPDF geometry & typography probe for Gatekeeper D3.

Invoked once per Viscount project by `audit_rmd_and_bib_calibre.js` so Python CV
inspects every compiled PDF in a single process startup (~0.3s total).
"""

import argparse
import json
import os
import re
import sys

try:
  import pymupdf
except ImportError:
  import fitz as pymupdf


MONO_FONT_SUBSTRINGS = (
  "lmmono",
  "courier",
  "consolas",
  "inconsolata",
  "dejavusansmono",
  "cmtt",
  "lmtt",
  "firacode",
  "jetbrainsmono",
)

QQ_PATTERN = re.compile(
  r"(?:Table|Figure|Fig\.|Section|Eq\.|\[\s*)\?\?|\?\?\s*\]|(?<![A-Za-z0-9?])\?\?(?![A-Za-z0-9?])"
)


def probe_page1_orphaned_headings (arg0_page):
  """Returns `(orphaned_list, shallow_list)` for Page-1 bottom Jost-Bold / Abstract headings."""
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
        "jost" in sp.get("font", "").lower()
        and "bold" in sp.get("font", "").lower()
        and float(sp.get("size", 0.0)) >= 10.3
        for sp in spans
      )
      is_caption = bool(re.match(r"^(?:Figure|Fig\.?|Table|Note|Source)\s*\d*\s*[:.]", line_text, re.IGNORECASE))
      visual_lines.append({
        "is_caption": is_caption,
        "is_jost_bold": is_jost_bold,
        "max_size": max_size,
        "text": line_text,
        "y0": y0,
        "y1": y1,
      })

  orphaned = []
  shallow = []
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

    rec = {
      "body_lines_below": body_lines_below,
      "text": line_info["text"],
      "y0": round(line_info["y0"], 1),
    }
    if body_lines_below < 2:
      orphaned.append(rec)
    elif body_lines_below == 2:
      shallow.append(rec)

  return orphaned, shallow


def probe_deadspace (arg0_doc):
  """Measures interior vertical ink occupancy across body pages (excluding title/final/Sources pages)."""
  pages = len(arg0_doc)
  if pages < 3:
    return [], []

  deadspace_errors = []
  deadspace_warnings = []
  in_sources_section = False

  for page_idx in range(1, pages - 1):
    page = arg0_doc[page_idx]
    txt = page.get_text("text") or ""
    if re.search(r"(?m)^\s*(?:Sources|Footnotes|Appendix)\s*$", txt):
      in_sources_section = True
      continue
    if in_sources_section:
      continue
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
      deadspace_errors.append({"blank": True, "max_gap_pct": 100.0, "occ_pct": 0.0, "page": page_idx + 1})
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
      deadspace_errors.append({
        "blank": False,
        "max_gap_pct": round(max_gap_ratio * 100.0, 1),
        "occ_pct": round(occ_ratio * 100.0, 1),
        "page": page_idx + 1,
      })
    elif occ_ratio < 0.48:
      deadspace_warnings.append({
        "occ_pct": round(occ_ratio * 100.0, 1),
        "page": page_idx + 1,
      })

  return deadspace_errors, deadspace_warnings


def probe_single_pdf (arg0_pdf_path):
  """Inspects one compiled PDF and returns structured geometry/typography metrics."""
  try:
    doc = pymupdf.open(arg0_pdf_path)
  except Exception as exc:
    return {"error": str(exc), "pages": 0}

  max_x1 = 0.0
  pages = len(doc)
  qq_pages = []
  continued_banners = 0
  tofu_chars = 0
  mono_pages = []
  mono_single_page_spans = 0
  p1_chars = 0
  p1_orphaned = []
  p1_shallow = []

  try:
    if pages >= 1:
      p1_chars = len((doc[0].get_text("text") or "").strip())
      p1_orphaned, p1_shallow = probe_page1_orphaned_headings(doc[0])

    for page_idx, page in enumerate(doc):
      for blk in page.get_text("blocks"):
        if blk[2] > max_x1:
          max_x1 = float(blk[2])
      page_fonts = doc.get_page_fonts(page_idx)
      if any(any(sub in str(f_info[3]).lower() for sub in MONO_FONT_SUBSTRINGS) for f_info in page_fonts):
        mono_pages.append(page_idx + 1)
      page_text = page.get_text("text") or ""
      if "(Continued from previous page)" in page_text:
        continued_banners += 1
      tofu_chars += page_text.count("\ufffd") + page_text.count("\x00")
      matches = QQ_PATTERN.findall(page_text)
      if matches:
        qq_pages.append({"count": len(matches), "page": page_idx + 1})

    if len(mono_pages) == 1:
      mono_dict = doc[mono_pages[0] - 1].get_text("dict")
      for blk in mono_dict.get("blocks", []):
        if blk.get("type", 0) != 0:
          continue
        for line in blk.get("lines", []):
          for sp in line.get("spans", []):
            if sp.get("text", "").strip() and any(sub in sp.get("font", "").lower() for sub in MONO_FONT_SUBSTRINGS):
              mono_single_page_spans += 1

    deadspace_errors, deadspace_warnings = probe_deadspace(doc)
  finally:
    doc.close()

  return {
    "continued_banners": continued_banners,
    "deadspace_errors": deadspace_errors,
    "deadspace_warnings": deadspace_warnings,
    "error": None,
    "is_blank_page1": pages >= 1 and p1_chars < 80,
    "max_x1": round(max_x1, 2),
    "mono_pages": mono_pages,
    "mono_single_page_spans": mono_single_page_spans,
    "p1_chars": p1_chars,
    "page1_orphaned_headings": p1_orphaned,
    "page1_shallow_headings": p1_shallow,
    "pages": pages,
    "qq_hits": sum(item["count"] for item in qq_pages),
    "qq_pages": qq_pages,
    "tofu_chars": tofu_chars,
  }


def main ():
  parser = argparse.ArgumentParser(description="Batched PyMuPDF geometry/font probe for Viscount PDFs.")
  parser.add_argument("--manifest", default=None, help="JSON file containing an array of PDF paths to probe")
  parser.add_argument("pdfs", nargs="*", help="One or more PDF paths to probe")
  parsed = parser.parse_args()

  pdf_list = list(parsed.pdfs or [])
  if parsed.manifest and os.path.isfile(parsed.manifest):
    with open(parsed.manifest, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    if isinstance(data, list):
      pdf_list.extend(str(p) for p in data)

  results = {}
  for pdf_path in pdf_list:
    abs_p = os.path.abspath(pdf_path)
    results[abs_p] = probe_single_pdf(abs_p)

  print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
  main()
