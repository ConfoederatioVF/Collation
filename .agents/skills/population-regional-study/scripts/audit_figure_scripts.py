"""Gatekeeper D2/Figure Audit: Audits Python/R/Rmd figure scripts for default
Matplotlib theme compliance (DejaVu Sans, 4-sided boxed axes, no serif/seaborn
overrides), rendered Matplotlib MathText (`$...$`) on mathematical variables and
exponents, explicit human category labels (no `.replace('_', ' ').title()`
mangling) and non-technobabble figure titles.
"""

import argparse
import ast
import json
import os
import re
import sys


BAD_FONT_VALUES = (
  "serif",
  "times",
  "times new roman",
  "georgia",
  "palatino",
  "garamond",
  "bookman",
  "computer modern",
  "cmr",
  "courier",
  "monospace",
)

FRACTIONAL_LIMIT_METHODS = {"set_xlim", "set_ylim", "xlim", "ylim"}

MANGLED_ROMAN_RE = re.compile(
  r"\b(?:Ii|Iii|Iv|Vii|Viii|Ix|Xii|Xiii|Xiv|Xvi|Xvii|Xviii|Xix)\b"
)

MATPLOTLIB_IMPORT_RE = re.compile(r"\b(?:matplotlib|pyplot|mpl_toolkits|seaborn)\b")

MATH_TEXT_SINKS = {
  "annotate",
  "figtext",
  "legend",
  "set_label",
  "set_title",
  "set_xlabel",
  "set_xticklabels",
  "set_ylabel",
  "set_yticklabels",
  "suptitle",
  "text",
  "title",
  "xlabel",
  "xticklabels",
  "ylabel",
  "yticklabels",
}

PLOT_CALLS_WITH_LABEL_KW = {
  "Patch",
  "Line2D",
  "bar",
  "barh",
  "colorbar",
  "errorbar",
  "fill_between",
  "hist",
  "imshow",
  "plot",
  "scatter",
  "stackplot",
  "step",
}

RAW_GREEK_PARAM_RE = re.compile(
  r"\b(?:nu|tau_?[0-9]*|sigma_?[0-9]*|gamma|alpha|beta|lambda|kappa|rho|theta|chi|mu)\s*(?:=|[<>~])"
  r"|\b(?:tau1|tau2|sigma2)\b"
  r"|\bc0\s*/\s*sill\b"
)

RAW_CARET_MATH_RE = re.compile(r"(?<![A-Za-z0-9])\^|[A-Za-z0-9]\^(?:\{?-?[0-9A-Za-z]+\}?)")
RAW_LOG_SQRT_RE = re.compile(r"\b(?:log_?10|log2|ln|sqrt)\s*\(|\|\s*grad\b")
RAW_RSQUARED_RE = re.compile(r"\b(?:r-squared|r\^2|chi-squared|chi\^2)\b", re.IGNORECASE)

SKIP_DIRS = {
  ".git",
  ".Rproj.user",
  "__pycache__",
  "archive",
  "diagnostics_visual",
  "node_modules",
  "papers",
}

TECHNOBABBLE_TITLE_RE = re.compile(
  r"\b(?:Fit Summary|Complete Secular|Carrying-Capacity Envelope|Spatiotemporal Paleodemographic|Empirical Validation)\b"
)

UNESCAPED_DOLLAR_RE = re.compile(r"(?<!\\)\$")
US_SHORT_DECIMAL_RE = re.compile(r"(?<!\d)\d+\.\d{1,2}(?!\d)")
BARE_COMMA_DECIMAL_RE = re.compile(r"\d,\d")


def audit_math_string_literal (arg0_text, arg1_label, arg2_line, arg3_is_title, arg4_errors, arg5_warnings):
  """Checks a plot title/label string for balanced `$...$` MathText, unrendered ASCII math, Roman numeral mangling and technobabble."""
  text = str(arg0_text or "")
  if not text.strip():
    return

  if MANGLED_ROMAN_RE.search(text):
    arg4_errors.append(
      f"[{arg1_label}] line {arg2_line}: mangled Title-Cased Roman numeral in plot label `{text}` (use explicit display dictionary preserving `II`/`III`/`IV`)."
    )

  if arg3_is_title and TECHNOBABBLE_TITLE_RE.search(text):
    arg4_errors.append(
      f"[{arg1_label}] line {arg2_line}: technobabble plot title `{text}` violates `/humanise` plain academic naming."
    )

  dollars = UNESCAPED_DOLLAR_RE.findall(text)
  if len(dollars) % 2 != 0:
    arg4_errors.append(
      f"[{arg1_label}] line {arg2_line}: unbalanced `$` MathText delimiter in `{text}`."
    )
    return

  #Check formatting inside rendered `$...$` MathText spans
  spans = UNESCAPED_DOLLAR_RE.split(text)
  plain_parts = []
  for idx, part in enumerate(spans):
    if idx % 2 == 1:
      if BARE_COMMA_DECIMAL_RE.search(part):
        arg5_warnings.append(
          f"[{arg1_label}] line {arg2_line}: bare decimal comma inside MathText `${part}$` adds TeX spacing; write `{{,}}` instead."
        )
      if US_SHORT_DECIMAL_RE.search(part):
        arg5_warnings.append(
          f"[{arg1_label}] line {arg2_line}: US decimal dot inside MathText `${part}$`; use European `{{,}}` decimal."
        )
    else:
      plain_parts.append(part)

  outside = " ".join(plain_parts)
  if RAW_GREEK_PARAM_RE.search(outside):
    arg4_errors.append(
      f"[{arg1_label}] line {arg2_line}: unrendered ASCII Greek/parameter math outside `$...$` in `{text}` (render e.g. `$\\nu = 3/2$`, `$\\tau_1 = 1{{,}}41$`)."
    )
  if RAW_RSQUARED_RE.search(outside):
    arg4_errors.append(
      f"[{arg1_label}] line {arg2_line}: unrendered `R-squared`/`R^2` outside `$...$` in `{text}` (render via `$R^2$`)."
    )
  if RAW_LOG_SQRT_RE.search(outside):
    arg4_errors.append(
      f"[{arg1_label}] line {arg2_line}: unrendered `log10`/`sqrt`/`grad` outside `$...$` in `{text}` (render via `$\\log_{{10}}(...)$` or `$|\\nabla ...|$`)."
    )
  if RAW_CARET_MATH_RE.search(outside):
    arg4_errors.append(
      f"[{arg1_label}] line {arg2_line}: raw caret exponent outside `$...$` in `{text}` (use Unicode `km²`/`m²` or MathText `$...$`)."
    )


def audit_python_source (arg0_source, arg1_label):
  """Audits Python Matplotlib source code via AST + line rules and returns `(errors, warnings)`."""
  errors = []
  warnings = []
  try:
    tree = ast.parse(arg0_source)
  except SyntaxError as exc:
    return [f"[{arg1_label}] SyntaxError prevents figure audit: {exc}"], []

  has_default_style_reset = "apply_viscount_style" in arg0_source
  has_tick_formatter = (
    "FuncFormatter" in arg0_source
    or "euro_tick_formatter" in arg0_source
    or "set_xticklabels" in arg0_source
    or "set_yticklabels" in arg0_source
  )
  has_subplot_creation = False
  has_fractional_axis_lim = False

  #Track whether explicit style reset or custom spine stripping appears in AST
  for node in ast.walk(tree):
    if isinstance(node, ast.Call):
      fn_name = get_attr_name(node.func)
      base_chain = get_full_call_chain(node.func)

      if base_chain == "rcdefaults" or base_chain.endswith(".rcdefaults"):
        has_default_style_reset = True
      elif base_chain == "style.use" or base_chain.endswith(".style.use"):
        if node.args:
          s_arg = extract_ast_text(node.args[0])
          if s_arg is not None and s_arg != "default":
            errors.append(
              f"[{arg1_label}] line {node.lineno}: non-default Matplotlib style `{s_arg}` is forbidden; use `plt.rcdefaults(); plt.style.use('default')`."
            )
          elif s_arg == "default":
            has_default_style_reset = True

      if base_chain.startswith(("sns.", "seaborn.")) and fn_name in {"set_theme", "set_style", "set", "despine"}:
        errors.append(
          f"[{arg1_label}] line {node.lineno}: Seaborn theme/despine `{base_chain}` overrides default Matplotlib styling."
        )

      if fn_name in {"subplots", "figure"}:
        has_subplot_creation = True

      #Ban `.replace("_", " ").title()` mechanical label mangling
      if fn_name == "title" and isinstance(node.func, ast.Attribute) and not node.args:
        val_src = ast.get_source_segment(arg0_source, node.func.value) or ""
        if ".replace" in val_src and "_" in val_src:
          errors.append(
            f"[{arg1_label}] line {node.lineno}: mechanical `.replace('_', ' ').title()` mangles Roman numerals and acronyms; use an explicit display dictionary."
          )

      #Ban top/right spine stripping (`spines["top"].set_visible(False)`)
      if fn_name == "set_visible" and node.args:
        if isinstance(node.args[0], ast.Constant) and node.args[0].value is False:
          val_src = ast.get_source_segment(arg0_source, node.func.value) or ""
          if "spines" in val_src and ("top" in val_src or "right" in val_src):
            errors.append(
              f"[{arg1_label}] line {node.lineno}: stripping `{val_src}` violates Matplotlib default 4-sided axes frame."
            )

      #Ban non-default `font.family` / `family=` kwargs on Matplotlib rc or text calls
      for kw in node.keywords:
        if kw.arg in {"family", "fontfamily"}:
          fval = extract_ast_text(kw.value)
          if fval and is_banned_font_name(fval):
            errors.append(
              f"[{arg1_label}] line {node.lineno}: forbidden custom font `{fval}`; keep Matplotlib default `DejaVu Sans` (`sans-serif`)."
            )
        if kw.arg == "label" and (fn_name in PLOT_CALLS_WITH_LABEL_KW or fn_name in MATH_TEXT_SINKS):
          ltxt = extract_ast_text(kw.value)
          if ltxt:
            audit_math_string_literal(ltxt, arg1_label, node.lineno, False, errors, warnings)

      if fn_name == "rc" or base_chain.endswith("rcParams.update"):
        first_arg = extract_ast_text(node.args[0]) if node.args else ""
        if fn_name == "rc" and first_arg == "font":
          for kw in node.keywords:
            if kw.arg == "family":
              fval = extract_ast_text(kw.value)
              if fval and is_banned_font_name(fval):
                errors.append(
                  f"[{arg1_label}] line {node.lineno}: `rc('font', family='{fval}')` violates default `DejaVu Sans` theme."
                )

      #Inspect positional string arguments to plot text sinks
      if fn_name in MATH_TEXT_SINKS:
        is_title_call = fn_name in {"suptitle", "set_title", "title"}
        arg_texts = []
        if fn_name in {"text", "figtext"} and len(node.args) >= 3:
          arg_texts.append(extract_ast_text(node.args[2]))
        elif fn_name == "annotate" and node.args:
          arg_texts.append(extract_ast_text(node.args[0]))
        elif fn_name in {"set_title", "title", "suptitle", "set_xlabel", "xlabel", "set_ylabel", "ylabel", "set_label"} and node.args:
          arg_texts.append(extract_ast_text(node.args[0]))
        elif fn_name in {"set_xticklabels", "xticklabels", "set_yticklabels", "yticklabels"} and node.args:
          if isinstance(node.args[0], (ast.List, ast.Tuple)):
            for elt in node.args[0].elts:
              arg_texts.append(extract_ast_text(elt))
        for txt in arg_texts:
          if txt:
            audit_math_string_literal(txt, arg1_label, node.lineno, is_title_call, errors, warnings)

      if fn_name in FRACTIONAL_LIMIT_METHODS and len(node.args) >= 2:
        lo = extract_ast_number(node.args[0])
        hi = extract_ast_number(node.args[1])
        if lo is not None and hi is not None and 0.0 <= lo < hi <= 1.05:
          has_fractional_axis_lim = True

    elif isinstance(node, ast.Dict):
      for k_node, v_node in zip(node.keys, node.values):
        k_str = extract_ast_text(k_node)
        if k_str in {"font.family", "font.serif"}:
          v_str = extract_ast_text(v_node)
          if k_str == "font.serif" or (v_str and is_banned_font_name(v_str)):
            errors.append(
              f"[{arg1_label}] line {node.lineno}: forbidden `{k_str}` override `{v_str}`; preserve default `sans-serif` (`DejaVu Sans`)."
            )
        if k_str in {"axes.spines.top", "axes.spines.right"}:
          if isinstance(v_node, ast.Constant) and v_node.value is False:
            errors.append(
              f"[{arg1_label}] line {node.lineno}: disabling `{k_str}` breaks default Matplotlib 4-sided frame."
            )

    elif isinstance(node, ast.Assign):
      for tgt in node.targets:
        t_src = ast.get_source_segment(arg0_source, tgt) or ""
        if "rcParams" in t_src and ("font.family" in t_src or "font.serif" in t_src):
          v_str = extract_ast_text(node.value)
          if "font.serif" in t_src or (v_str and is_banned_font_name(v_str)):
            errors.append(
              f"[{arg1_label}] line {node.lineno}: forbidden rcParams font override `{t_src} = {v_str}`."
            )
        if "rcParams" in t_src and ("axes.spines.top" in t_src or "axes.spines.right" in t_src):
          if isinstance(node.value, ast.Constant) and node.value.value is False:
            errors.append(
              f"[{arg1_label}] line {node.lineno}: disabling `{t_src}` violates default Matplotlib 4-sided axes frame."
            )

  if has_subplot_creation and not has_default_style_reset:
    warnings.append(
      f"[{arg1_label}] script creates Matplotlib figures without explicit `plt.rcdefaults()` / `plt.style.use('default')` reset."
    )
  if has_fractional_axis_lim and not has_tick_formatter:
    warnings.append(
      f"[{arg1_label}] fractional [0, 1] axis limits set without European `FuncFormatter` / tick formatting (risks US `0.75` dots)."
    )

  #Return statement
  return errors, warnings


def audit_r_or_rmd_source (arg0_source, arg1_label, arg2_is_rmd):
  """Checks R figure scripts or R/Python chunks inside `.Rmd` files for figure compliance."""
  errors = []
  warnings = []

  if arg2_is_rmd:
    chunk_re = re.compile(r"```\{([A-Za-z]+)[^}]*\}\r?\n(.*?)```", re.DOTALL)
    for idx, match in enumerate(chunk_re.finditer(arg0_source)):
      lang = match.group(1).strip().lower()
      body = match.group(2)
      chunk_label = f"{arg1_label}#chunk{idx + 1}({lang})"
      if lang == "python" and MATPLOTLIB_IMPORT_RE.search(body):
        c_errs, c_warns = audit_python_source(body, chunk_label)
        errors.extend(c_errs)
        warnings.extend(c_warns)
      elif lang == "r" and re.search(r"\b(?:ggplot|plot)\s*\(", body):
        c_errs, c_warns = audit_r_plot_chunk(body, chunk_label)
        errors.extend(c_errs)
        warnings.extend(c_warns)
    return errors, warnings

  if re.search(r"\b(?:ggplot|plot)\s*\(", arg0_source):
    return audit_r_plot_chunk(arg0_source, arg1_label)

  #Return statement
  return errors, warnings


def audit_r_plot_chunk (arg0_code, arg1_label):
  """Performs static hygiene checks on R plotting code."""
  errors = []
  warnings = []
  if re.search(r'family\s*=\s*["\'](?:serif|Times|Georgia|Palatino|Garamond)["\']', arg0_code, re.IGNORECASE):
    errors.append(f"[{arg1_label}] forbidden serif font override in R plot.")
  if re.search(r"\b(?:theme_classic|panel\.border\s*=\s*element_blank)\b", arg0_code):
    warnings.append(f"[{arg1_label}] R plot removes top/right panel border.")
  for m in re.finditer(
    r'(?:ggtitle|xlab|ylab)\s*\(\s*["\']([^"\']+)["\']|(?:main|title|subtitle|x|y)\s*=\s*["\']([^"\']+)["\']',
    arg0_code,
  ):
    txt = m.group(1) or m.group(2)
    if txt:
      audit_math_string_literal(txt, arg1_label, 1, True, errors, warnings)

  #Return statement
  return errors, warnings


def audit_target (arg0_target_path):
  """Discovers and audits all relevant figure scripts under a file or directory."""
  abs_target = os.path.abspath(arg0_target_path)
  if not os.path.exists(abs_target):
    return {"errors": [f"Target path does not exist: {arg0_target_path}"], "files_checked": 0, "success": False, "warnings": []}

  base_root = abs_target if os.path.isdir(abs_target) else os.path.dirname(abs_target)
  files = collect_figure_scripts(abs_target)
  all_errors = []
  all_warnings = []

  for fpath in files:
    rel = os.path.relpath(fpath, base_root).replace("\\", "/")
    if rel == ".":
      rel = os.path.basename(fpath)
    try:
      with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    except OSError as exc:
      all_errors.append(f"[{rel}] Failed to read file: {exc}")
      continue

    ext = os.path.splitext(fpath)[1].lower()
    if ext == ".py":
      errs, warns = audit_python_source(content, rel)
    elif ext == ".r":
      errs, warns = audit_r_or_rmd_source(content, rel, False)
    else:
      errs, warns = audit_r_or_rmd_source(content, rel, True)
    all_errors.extend(errs)
    all_warnings.extend(warns)

  #Return statement
  return {
    "errors": all_errors,
    "files_checked": len(files),
    "success": len(all_errors) == 0,
    "warnings": all_warnings,
  }


def collect_figure_scripts (arg0_target_path):
  """Collects Matplotlib Python scripts, R plotting scripts and `.Rmd` files with plot chunks."""
  if os.path.isfile(arg0_target_path):
    return [os.path.abspath(arg0_target_path)]

  collected = []
  abs_root = os.path.abspath(arg0_target_path)
  for cur_dir, dir_names, file_names in os.walk(abs_root):
    dir_names[:] = sorted([d for d in dir_names if d not in SKIP_DIRS])
    for fn in sorted(file_names):
      fpath = os.path.join(cur_dir, fn)
      low = fn.lower()
      if low.endswith(".py"):
        try:
          src = open(fpath, "r", encoding="utf-8", errors="replace").read()
        except OSError:
          continue
        if MATPLOTLIB_IMPORT_RE.search(src):
          collected.append(fpath)
      elif low.endswith(".r") or low.endswith(".rmd"):
        try:
          src = open(fpath, "r", encoding="utf-8", errors="replace").read()
        except OSError:
          continue
        if re.search(r"\b(?:ggplot|matplotlib|pyplot)\b", src):
          collected.append(fpath)

  #Return statement
  return collected


def extract_ast_number (arg0_node):
  """Extracts a float from a literal `ast.Constant` or unary minus node, or returns None."""
  if isinstance(arg0_node, ast.Constant) and isinstance(arg0_node.value, (int, float)):
    return float(arg0_node.value)
  if isinstance(arg0_node, ast.UnaryOp) and isinstance(arg0_node.op, ast.USub):
    inner = extract_ast_number(arg0_node.operand)
    return -inner if inner is not None else None

  #Return statement
  return None


def extract_ast_text (arg0_node):
  """Extracts flat string text from an AST Constant, JoinedStr (`f"..."`), or simple `+` concatenation."""
  if arg0_node is None:
    return None
  if isinstance(arg0_node, ast.Constant) and isinstance(arg0_node.value, str):
    return arg0_node.value
  if isinstance(arg0_node, ast.JoinedStr):
    parts = []
    for v in arg0_node.values:
      if isinstance(v, ast.Constant) and isinstance(v.value, str):
        parts.append(v.value)
      else:
        parts.append("XVAL")
    return "".join(parts)
  if isinstance(arg0_node, ast.BinOp) and isinstance(arg0_node.op, ast.Add):
    left = extract_ast_text(arg0_node.left)
    right = extract_ast_text(arg0_node.right)
    if left is not None and right is not None:
      return left + right

  #Return statement
  return None


def get_attr_name (arg0_node):
  """Returns the leaf identifier or dotted method name for an AST call target."""
  if isinstance(arg0_node, ast.Name):
    return arg0_node.id
  if isinstance(arg0_node, ast.Attribute):
    return arg0_node.attr

  #Return statement
  return ""


def get_full_call_chain (arg0_node):
  """Reconstructs dotted attribute chain like `plt.style.use` from an AST call target."""
  parts = []
  cur = arg0_node
  while isinstance(cur, ast.Attribute):
    parts.append(cur.attr)
    cur = cur.value
  if isinstance(cur, ast.Name):
    parts.append(cur.id)

  #Return statement
  return ".".join(reversed(parts))


def is_banned_font_name (arg0_font_value):
  """Returns True when a font-family specifier overrides default `DejaVu Sans` / `sans-serif`."""
  low = str(arg0_font_value or "").strip().lower()
  if not low or low in {"sans-serif", "dejavu sans", "sans"}:
    return False
  for tok in BAD_FONT_VALUES:
    if tok in low:
      return True

  #Return statement
  return False


def main ():
  parser = argparse.ArgumentParser(
    description="Audit Viscount figure scripts for default Matplotlib theme, MathText (`$...$`) and clean labels."
  )
  parser.add_argument("target", help="Path to a figure script, chapter dir or Viscount project dir.")
  parser.add_argument("--json", action="store_true")
  parsed = parser.parse_args()

  res = audit_target(parsed.target)
  if parsed.json:
    print(json.dumps(res, indent=2, ensure_ascii=False))
  else:
    for err in res["errors"][:50]:
      print(f"[FAIL] {err}")
    if len(res["errors"]) > 50:
      print(f"[FAIL] ... and {len(res['errors']) - 50} additional error(s).")
    for warn in res["warnings"][:30]:
      print(f"[WARN] {warn}")
    if len(res["warnings"]) > 30:
      print(f"[WARN] ... and {len(res['warnings']) - 30} additional warning(s).")
    print(
      f"[audit_figure_scripts] {parsed.target}: {res['files_checked']} file(s), "
      f"{len(res['errors'])} error(s), {len(res['warnings'])} warning(s)."
    )

  sys.exit(0 if res["success"] else 1)


if __name__ == "__main__":
  main()
