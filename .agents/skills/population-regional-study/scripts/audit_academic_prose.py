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


SCHEMA_LEAK_PAT = re.compile(r"\b(?:other_names|positive integer population series|JSON archive|Stadest[eé]r format)\b")
SNAKE_LEAK_PAT = re.compile(r"\b(?:sites_[A-Za-z0-9_]+|\d+\.[a-z]+_[a-z_]+)\b")
THE_PROJ_PAT = re.compile(r"\b[Tt]he\s+[A-Z]{4,12}\s+(?:synthesis|framework|model|paradigm|architecture)\b")
WORD_N_EQ_PAT = re.compile(
  r"\b(?:ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[-\sA-Za-z]{0,24}\(\s*n\s*=\s*\d+\s*\)",
  flags=re.IGNORECASE,
)
UNPROMOTED_K_PAT = re.compile(r"(?<![A-Za-z0-9.,])\d+\.\d{3}\s*k\b")
DECORATOR_COLOUR_PAT = re.compile(r"\b(?:warm gold|emerald teal|muted slate|crisp azure|vibrant coral)\b", flags=re.IGNORECASE)
EUPHEMISM_PAT = re.compile(r"\b(?:Contemporary Warfare|Regional Unrest|Growth Hub|Demographic Powerhouse)\b", flags=re.IGNORECASE)
INTERNAL_CIRC_PAT = re.compile(r"\b(?:histmap/|population_Substrata|population_Velkscala)\b")
SAFE_HTML_TAG_PAT = re.compile(r"</?(?:br|sup|sub|em|strong|a|div|span|p|img|code|kbd)(?:\s[^>]*)?>", flags=re.IGNORECASE)
VUE_ANGLE_PAT = re.compile(r"<[A-Za-z][^>\n]*>")
MONTH_YEAR_AD_PAT = re.compile(
  r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2}\s*AD\b"
)
KNITR_INLINE_R_PAT = re.compile(r"`r\s+[^`\n]+`")
INLINE_BACKTICK_PAT = re.compile(r"`([^`\n]+)`")
EXPLICIT_MONO_PAT = re.compile(r"\\texttt\s*\{|\\verb(?![A-Za-z])|<code>", flags=re.IGNORECASE)


def _check_no_monospace(arg0_line_no, arg1_text, arg2_errors, arg3_warnings, arg4_legacy_baseline=False):
  """Rejects non-code inline backticks and explicit LaTeX/HTML monospace spans outside code blocks."""
  without_r = KNITR_INLINE_R_PAT.sub(" ", arg1_text)
  backtick_hits = [m.group(1) for m in INLINE_BACKTICK_PAT.finditer(without_r)]
  explicit_hits = EXPLICIT_MONO_PAT.findall(without_r)

  for token in backtick_hits:
    msg = (
      f"Line {arg0_line_no}: Monospace backtick span `{token}` outside code blocks "
      f"(reserve monospace strictly for code; use plain text or italics in prose/captions/tables)."
    )
    if arg4_legacy_baseline and len(token.strip()) <= 3:
      arg3_warnings.append(msg)
    else:
      arg2_errors.append(msg)

  for token in explicit_hits:
    arg2_errors.append(
      f"Line {arg0_line_no}: Explicit monospace markup '{token}' outside code blocks "
      f"(reserve monospace strictly for code)."
    )


def strip_non_prose_spans(arg0_line):
  """Removes knitr inline R calls, inline LaTeX math, markdown link targets, safe HTML tags and URLs while unwrapping stray prose backticks."""
  text = KNITR_INLINE_R_PAT.sub(" ", arg0_line)
  text = INLINE_BACKTICK_PAT.sub(r"\1", text)
  text = re.sub(r"\$\$[^$]+\$\$|\$[^$\n]+\$", " ", text)
  text = re.sub(r"\\\[.*?\\\]|\\\(.*?\\\)", " ", text)
  text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
  text = re.sub(r"https?://\S+", " ", text)
  text = re.sub(r"<[^>]+>", " ", text)
  return text


def audit_humanise_structure(arg0_rmd_path, arg1_legacy_baseline=False):
  """Enforces /humanise rules across YAML metadata, Markdown headings, prose and captions."""
  import os
  errors = []
  warnings = []
  try:
    with open(arg0_rmd_path, "r", encoding="utf-8", errors="replace") as f:
      raw_text = f.read()
  except OSError as exc:
    return [f"Could not read Rmd file for humanise audit: {exc}"], warnings

  basename = os.path.basename(arg0_rmd_path)
  is_settlements_file = basename.endswith("_settlements.Rmd")
  lines = raw_text.splitlines()

  yaml_end_idx = 0
  if lines and lines[0].strip() == "---":
    for idx in range(1, len(lines)):
      if lines[idx].strip() == "---":
        yaml_end_idx = idx
        break

  # 1. Audit YAML frontmatter caption fields
  for idx in range(1, yaml_end_idx):
    line_no = idx + 1
    stripped_yaml = lines[idx].strip()
    m = re.match(r"^(hero_caption|subtitle)\s*:\s*(.+)$", stripped_yaml)
    if m:
      field_name = m.group(1)
      val = m.group(2).strip().strip("\"'")
      _check_no_monospace(line_no, val, errors, warnings, arg1_legacy_baseline)
      clean_val = strip_non_prose_spans(val)
      for kw in ("verified", "validated", "empirical", "complete"):
        if re.search(rf"\b{kw}\b", clean_val, re.IGNORECASE):
          errors.append(f"Line {line_no}: YAML `{field_name}` contains banned badge/hyperbole word `{kw}`.")
      _check_formatting_tokens(line_no, clean_val, errors, warnings, arg1_legacy_baseline)
      continue
    title_m = re.match(r"^title\s*:\s*(.+)$", stripped_yaml)
    if title_m:
      val = title_m.group(1).strip().strip("\"'")
      _check_no_monospace(line_no, val, errors, warnings, arg1_legacy_baseline)

  # 2. Scan body outside YAML: separate R code chunks from prose/headings
  in_code = False
  in_display_math = False
  current_h1 = None
  for idx in range(yaml_end_idx + (1 if yaml_end_idx > 0 else 0), len(lines)):
    line_no = idx + 1
    raw_line = lines[idx]
    stripped = raw_line.strip()

    if stripped.startswith("```"):
      in_code = not in_code
      continue

    if in_code:
      # Check viscount_table / viscount_figure caption arguments inside R chunks
      for cap_m in re.finditer(r"(?:viscount_table|viscount_figure|render_table_template)\s*\([^)]*(?:caption\s*=\s*|,\s*)([\"'])((?:\\.|(?!\1).)*)\1", raw_line):
        cap_text = cap_m.group(2)
        _check_no_monospace(line_no, cap_text, errors, warnings, arg1_legacy_baseline)
        clean_cap = strip_non_prose_spans(cap_text)
        for kw in ("verified", "validated", "empirical", "complete"):
          if re.search(rf"\b{kw}\b", clean_cap, re.IGNORECASE):
            if kw == "complete" and is_settlements_file and re.search(r"\bcomplete\s+settlement\b", clean_cap, re.IGNORECASE):
              warnings.append(f"Line {line_no}: Caption contains `Complete Settlement` wording; consider concise noun phrasing.")
            else:
              errors.append(f"Line {line_no}: Figure/table caption contains banned badge/hyperbole word `{kw}`.")
        _check_formatting_tokens(line_no, clean_cap, errors, warnings, arg1_legacy_baseline)
      continue

    if stripped.startswith("$$") or stripped.startswith("\\["):
      if stripped in ("$$", "\\[", "\\]") or stripped.count("$$") == 1 or ("\\[" in stripped and "\\]" not in stripped) or ("\\]" in stripped and "\\[" not in stripped):
        in_display_math = not in_display_math
      continue
    if in_display_math:
      continue

    # Headings check
    if stripped.startswith("#"):
      level_m = re.match(r"^(#+)\s*(.*)$", stripped)
      heading_level = len(level_m.group(1)) if level_m else 1
      heading_text = level_m.group(2) if level_m else stripped.lstrip("#").strip()
      _check_no_monospace(line_no, heading_text, errors, warnings, arg1_legacy_baseline)
      clean_heading = strip_non_prose_spans(heading_text)
      if heading_level == 1:
        current_h1 = clean_heading.strip().lower()
      elif heading_level >= 2 and current_h1 == "abstract":
        errors.append(
          f"Line {line_no}: Sub-heading `{heading_text}` inside `# Abstract` is forbidden "
          f"(keep `# Abstract` as an undivided prose block so Page 1 never strands an orphaned heading)."
        )
      for kw in ("verified", "validated", "empirical", "complete"):
        if re.search(rf"\b{kw}\b", clean_heading, re.IGNORECASE):
          if kw == "complete" and is_settlements_file and re.search(r"\bcomplete\s+settlement\b", clean_heading, re.IGNORECASE):
            warnings.append(f"Line {line_no}: Heading contains `Complete Settlement` in `_settlements.Rmd`; avoid elsewhere.")
          else:
            errors.append(f"Line {line_no}: Markdown heading contains banned hyperbole/badge word `{kw}` ({heading_text!r}).")
      _check_formatting_tokens(line_no, clean_heading, errors, warnings, arg1_legacy_baseline)
      continue

    # Prose / table / HTML caption lines
    if not stripped or stripped.startswith("<!--"):
      continue
    _check_no_monospace(line_no, raw_line, errors, warnings, arg1_legacy_baseline)
    raw_no_code = re.sub(r"`[^`]+`|<!--.*?-->|<https?://[^>]+>", " ", raw_line)
    raw_no_code = SAFE_HTML_TAG_PAT.sub(" ", raw_no_code)
    for vm in VUE_ANGLE_PAT.finditer(raw_no_code):
      errors.append(f"Line {line_no}: Unescaped angle-bracket token {vm.group(0)!r} breaks VitePress Vue builds.")
    clean_prose = strip_non_prose_spans(raw_line)
    _check_formatting_tokens(line_no, clean_prose, errors, warnings, arg1_legacy_baseline)

  return errors, warnings


def _check_formatting_tokens(arg0_line_no, arg1_clean_text, arg2_errors, arg3_warnings, arg4_legacy_baseline=False):
  """Checks malformed BC/AD dates, ASCII km2/m2, prose '->' arrows, spaced slashes and AI schema leaks."""
  # Malformed dotted + attached era markers e.g. 10.000BC
  for m in re.finditer(r"(?<![A-Za-z0-9_])\d+(?:\.\d+)+(?:BC|BCE|AD|CE)\b", arg1_clean_text):
    arg2_errors.append(f"Line {arg0_line_no}: Malformed dotted/attached era date {m.group(0)!r} (drop dots, e.g. `10000BC` or `10000 BC`).")
  # Trailing AD after modern Month Year e.g. March 1953AD
  for m in MONTH_YEAR_AD_PAT.finditer(arg1_clean_text):
    arg3_warnings.append(f"Line {arg0_line_no}: Modern month-year date {m.group(0)!r} should omit `AD`.")
  # Trailing AD after spaced year e.g. 1600 AD (harmonised: attached `1600AD` or prefix `AD 1600` are valid)
  for m in re.finditer(r"(?<![A-Za-z0-9_])\d[\d.,]*\s+AD\b", arg1_clean_text):
    arg2_errors.append(f"Line {arg0_line_no}: Spaced trailing `AD` in date {m.group(0)!r} (write `1600AD` or `AD 1600`).")
  # ASCII km2 / m2 units outside math/code
  for m in re.finditer(r"\b(?:km2|m2|km\^2|m\^2)\b", arg1_clean_text):
    msg = f"Line {arg0_line_no}: Malformed ASCII area unit {m.group(0)!r} (use Unicode `km²` or `m²`)."
    if arg4_legacy_baseline:
      arg3_warnings.append(msg)
    else:
      arg2_errors.append(msg)
  # Prose arrow -> outside code/math/comments
  for m in re.finditer(r"(?:^|\s)->(?:\s|$)", arg1_clean_text):
    arg2_errors.append(f"Line {arg0_line_no}: Prose ASCII arrow `->` detected (replace with `to` or proper wording).")
  # Space-padded slash ' / ' in prose/headings (ignore markdown tables pipes and LaTeX)
  if not arg1_clean_text.lstrip().startswith("|"):
    for m in re.finditer(r"[A-Za-z0-9)]\s+/\s+[A-Za-z0-9(]", arg1_clean_text):
      msg = f"Line {arg0_line_no}: Space-padded slash {m.group(0)!r} detected (use `or`, `to` or unspaced slash)."
      if arg4_legacy_baseline:
        arg3_warnings.append(msg)
      else:
        arg2_errors.append(msg)
  for pat, label in (
    (SCHEMA_LEAK_PAT, "leaked database/JSON schema term"),
    (SNAKE_LEAK_PAT, "leaked snake_case folder/code identifier"),
    (THE_PROJ_PAT, "verbose 'the <PROJECT> <noun>' wrapper (use bare `<PROJECT>`)"),
    (WORD_N_EQ_PAT, "redundant spelled-out number paired with `(n=...)`"),
    (UNPROMOTED_K_PAT, "unpromoted magnitude >= 1.000k (promote to `M`)"),
    (DECORATOR_COLOUR_PAT, "compound decorator colour adjective"),
    (EUPHEMISM_PAT, "vague demographic/conflict euphemism"),
  ):
    m = pat.search(arg1_clean_text)
    if m:
      msg = f"Line {arg0_line_no}: Forbidden {label}: {m.group(0)!r}."
      if arg4_legacy_baseline and pat is SNAKE_LEAK_PAT:
        arg3_warnings.append(msg)
      else:
        arg2_errors.append(msg)
  # US 'medieval' -> British 'mediaeval'
  for m in re.finditer(r"\bmedieval\b", arg1_clean_text, flags=re.IGNORECASE):
    arg3_warnings.append(f"Line {arg0_line_no}: Use non-Oxford British spelling `mediaeval` rather than {m.group(0)!r}.")


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
    cleaned = KNITR_INLINE_R_PAT.sub(" CODE ", cleaned)
    cleaned = INLINE_BACKTICK_PAT.sub(r"\1", cleaned)
    cleaned = re.sub(r"\[@[^\]]+\]", " CITE ", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", " TEX ", cleaned)
    prose_lines.append((idx, cleaned))

  return prose_lines


def audit_rmd_file(arg0_rmd_path, arg1_strict_prose=True, arg2_legacy_baseline=False):
  """Audits an Rmd file (or recursively all Rmd files in a directory) and returns `(errors, warnings)`."""
  import os
  errors = []
  warnings = []
  if os.path.isdir(arg0_rmd_path):
    rmd_paths = []
    for root_dir, dir_names, file_names in os.walk(arg0_rmd_path):
      dir_names[:] = sorted([d for d in dir_names if d not in ("_shared", "archive", "diagnostics_visual", ".git", ".Rproj.user")])
      for fn in sorted(file_names):
        if fn.lower().endswith(".rmd"):
          rmd_paths.append(os.path.join(root_dir, fn))
    if not rmd_paths:
      return [f"No .Rmd files found under directory {arg0_rmd_path}"], warnings
    for rmd_path in rmd_paths:
      rel = os.path.relpath(rmd_path, arg0_rmd_path).replace("\\", "/")
      sub_errs, sub_warns = audit_rmd_file(rmd_path, arg1_strict_prose=arg1_strict_prose, arg2_legacy_baseline=arg2_legacy_baseline)
      errors.extend([f"[{rel}] {e}" for e in sub_errs])
      warnings.extend([f"[{rel}] {w}" for w in sub_warns])
    return errors, warnings

  with open(arg0_rmd_path, "r", encoding="utf-8") as fh:
    raw = fh.read()
  is_root_synthesis = os.path.basename(arg0_rmd_path).lower() == "studies_on_population.rmd"

  # Check code chunks for banned 260-line inline render_table_template overrides
  if re.search(r"render_table_template\s*<-\s*function", raw):
    errors.append(
      "Inline `render_table_template <- function` override detected; use shared `viscount_rmd_helpers.R` and Intellte framework instead."
    )

  prose_lines = strip_non_prose(raw)

  for line_no, text in prose_lines:
    if not text.strip() or text.lstrip().startswith("#") or text.lstrip().startswith("<") or text.lstrip().startswith("|"):
      continue

    if not is_root_synthesis:
      cm = INTERNAL_CIRC_PAT.search(text)
      if cm:
        msg = f"Line {line_no}: Sub-chapter circular reference to internal SVEA dataset/path {cm.group(0)!r}."
        if arg2_legacy_baseline:
          warnings.append(msg)
        else:
          errors.append(msg)

    for m_sp in re.finditer(r"(?<![A-Za-z0-9.,])\b\d{1,3}(?: \d{3})+\b", text):
      warnings.append(f"Line {line_no}: Space-delimited thousands {m_sp.group(0)!r}; use DE full-stop separator.")

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

  humanise_errors, humanise_warnings = audit_humanise_structure(arg0_rmd_path, arg1_legacy_baseline=arg2_legacy_baseline)
  errors.extend(humanise_errors)
  warnings.extend(humanise_warnings)

  return errors, warnings


def main():
  parser = argparse.ArgumentParser(description="Audit Operation Viscount .Rmd reports for academic EN-GB style.")
  parser.add_argument("rmd_path", help="Path to the .Rmd file")
  parser.add_argument("--warn-only-cliches", action="store_true", help="Treat banned clichés as warnings")
  parser.add_argument("--legacy-baseline", action="store_true", help="Downgrade legacy baseline ASCII km2/m2 hits to warnings")
  parsed = parser.parse_args()

  errors, warnings = audit_rmd_file(
    parsed.rmd_path,
    arg1_strict_prose=not parsed.warn_only_cliches,
    arg2_legacy_baseline=parsed.legacy_baseline,
  )
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
