"""Gatekeeper B: Audits `.Rmd` reports for anti-AI tortured prose, US spelling,
malformed European/semantic numbers, inline `render_table_template` redefinitions,
and style regressions before Intellte publishing.
"""

import argparse
import re
import sys


BANNED_PHRASES = [
  r"\bdelve(?:s|d|ing)?\b",
  r"\btapestry\b",
  r"\bserve(?:s|d)? as a testament\b",
  r"\bpivotal role\b",
  r"\bcomplex interplay\b",
  r"\brobust framework\b",
  r"\bholistic approach\b",
  r"\bbeacon of\b",
  r"\bunparalleled\b",
  r"\bburgeoning\b",
  r"\bspearhead(?:s|ed|ing)?\b",
  r"\bit is worth noting that\b",
  r"\bpaints a vivid picture\b",
  r"\bsheds light on\b",
  r"\brichest tapestry\b",
  r"\bnot only\b.{1,80}\bbut also\b",
]

WARN_PHRASES = [
  r"\bshowcase(?:s|d|ing)?\b",
  r"\bunderscore(?:s|d|ing)?\b",
  r"\bparamount\b",
  r"\bmultifaceted\b",
  r"\bseamless(?:ly)?\b",
  r"\bin conclusion\b",
  r"\bin summary\b",
  r"\bmeticulous(?:ly)?\b",
  r"\bvibrant\b",
]

US_ENGLISH_PATTERNS = [
  r"\banalyz(?:e|ed|es|ing)\b",
  r"\bsynthesiz(?:e|ed|es|ing)\b",
  r"\bstandardiz(?:e|ed|es|ing)\b",
  r"\bnormaliz(?:e|ed|es|ing)\b",
  r"\bsynchroniz(?:e|ed|es|ing)\b",
  r"\bneighbor(?:s|ing|hood)?\b",
  r"\bbehavior(?:s|al)?\b",
  r"\bfavor(?:s|ed|able)?\b",
]


def strip_non_prose(arg0_text):
  """Strips YAML frontmatter, R code chunks and inline LaTeX math for prose scanning."""
  lines = arg0_text.splitlines()
  prose_lines = []
  in_yaml = False
  in_code = False

  for idx, line in enumerate(lines, start=1):
    stripped = line.strip()
    if idx == 1 and stripped == "---":
      in_yaml = True
      continue
    if in_yaml:
      if stripped == "---":
        in_yaml = False
      continue
    if stripped.startswith("```"):
      in_code = not in_code
      continue
    if in_code:
      continue

    cleaned = re.sub(r"\$\$?.*?\$\$?", " MATH ", line)
    cleaned = re.sub(r"`[^`]+`", " CODE ", cleaned)
    cleaned = re.sub(r"\[@[^\]]+\]", " CITE ", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", " TEX ", cleaned)
    prose_lines.append((idx, cleaned))

  return prose_lines


def audit_rmd_file(arg0_rmd_path, arg1_strict_prose=True):
  """Audits an Rmd file and returns `(errors, warnings)`."""
  errors = []
  warnings = []

  with open(arg0_rmd_path, "r", encoding="utf-8") as fh:
    raw = fh.read()

  # Check code chunks for banned 260-line inline render_table_template overrides
  if re.search(r"render_table_template\s*<-\s*function", raw):
    errors.append(
      "Inline `render_table_template <- function` override detected; use shared `viscount_rmd_helpers.R` and Intellte framework instead."
    )

  prose_lines = strip_non_prose(raw)

  for line_no, text in prose_lines:
    if not text.strip() or text.lstrip().startswith("#") or text.lstrip().startswith("<") or text.lstrip().startswith("|"):
      continue

    for pat in BANNED_PHRASES:
      m = re.search(pat, text, flags=re.IGNORECASE)
      if m:
        msg = f"Line {line_no}: AI cliché / anti-human pattern {m.group(0)!r}"
        if arg1_strict_prose:
          errors.append(msg)
        else:
          warnings.append(msg)

    for pat in WARN_PHRASES:
      m = re.search(pat, text, flags=re.IGNORECASE)
      if m:
        warnings.append(f"Line {line_no}: Stylistic warning phrase {m.group(0)!r}")

    for pat in US_ENGLISH_PATTERNS:
      m = re.search(pat, text, flags=re.IGNORECASE)
      if m:
        errors.append(f"Line {line_no}: Non-British (US) spelling {m.group(0)!r}")

    # English decimal dots before % or semantic k/M/B/T suffixes (excluding bibliographic refs/version strings like v1.0)
    for m in re.finditer(r"(?<![a-zA-Z0-9\.])(\d+\.\d+)(?=\s*%|(?:\s*(?:k|M|B|T)\b))", text):
      errors.append(f"Line {line_no}: English decimal dot {m.group(1)!r}; use European comma (e.g. {m.group(1).replace('.', ',')!r}).")

    # Spelled-out large number words where semantic suffix belongs
    for m in re.finditer(r"\b\d+(?:,\d+)?\s+(?:thousand|million|billion|trillion)\b", text, flags=re.IGNORECASE):
      warnings.append(f"Line {line_no}: Spelled-out magnitude {m.group(0)!r}; prefer semantic suffix (k/M/B/T).")

    # Oxford serial comma check
    for m in re.finditer(r"\b[A-Za-z0-9\-]+,\s+[A-Za-z0-9\-]+,\s+and\s+[A-Za-z0-9\-]+\b", text):
      warnings.append(f"Line {line_no}: Possible Oxford serial comma {m.group(0)!r}.")

  return errors, warnings


def main():
  parser = argparse.ArgumentParser(description="Audit Operation Viscount .Rmd reports for academic EN-GB style.")
  parser.add_argument("rmd_path", help="Path to the .Rmd file")
  parser.add_argument("--warn-only-cliches", action="store_true", help="Treat banned clichés as warnings")
  parsed = parser.parse_args()

  errors, warnings = audit_rmd_file(parsed.rmd_path, arg1_strict_prose=not parsed.warn_only_cliches)
  for w in warnings[:40]:
    print(f"[WARN] {w}")
  if len(warnings) > 40:
    print(f"[WARN] ... and {len(warnings) - 40} additional warnings")

  for e in errors[:40]:
    print(f"[FAIL] {e}", file=sys.stderr)
  if len(errors) > 40:
    print(f"[FAIL] ... and {len(errors) - 40} additional errors", file=sys.stderr)

  print(f"[audit_academic_prose] {parsed.rmd_path}: {len(errors)} error(s), {len(warnings)} warning(s)")
  sys.exit(1 if errors else 0)


if __name__ == "__main__":
  main()
