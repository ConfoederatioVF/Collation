# Intellte R Markdown Setup Block and Audit Scripts (`/draft-report`)

This reference file provides:
1. The verified R Markdown YAML frontmatter and `{r setup, include=FALSE}` chunk for `<report_stem>.Rmd`.
2. General-purpose R helper functions for loading on-disk CSV/JSON datasets and formatting European decimals (`58,88`), semantic abbreviations (`k`, `M`, `B`, `T`), coordinates and compact dates (`10000BC`, `2000AD`).
3. The automated Python compilation and `pymupdf` verification script for auditing compiled PDFs and archived `./papers/` PDFs.

---

## 1. Standard YAML Frontmatter & `{r setup, include=FALSE}` Block

Use this exact setup block at the top of `<report_stem>.Rmd`. It enforces:
- Inline `10pt` (`10pt/14pt`) `longtable` rendering (never `\resizebox` or isolated float pages).
- Top-aligned table headers (`valign=top`) with zero `\parindent` cell indentation, empty continuation `\endhead` (headers emitted once via `\endfirsthead`), `rownames(df) <- NULL` and captions strictly below tables (`<= 3` lines adding context).
- Compact `10000BC` / `1897AD` year formatting without dot separators or modern month-year `AD` suffixes.
- Plain hyphens (`-`) in place of em/en-dashes.
- Non-overlapping `!htbp` figure placement capped at `0.42\textheight`, and Page 1 hero height `<= 0.52\textheight` so Page 1 is never blank.
- **No Orphaned Page-1 `Abstract` or Sub-Heading Splits**: Keep `# Abstract` as an undivided prose block (zero `##` sub-headings inside `# Abstract`, which force a premature `needspace` break before the opening paragraph) and add the `\AtBeginDocument` `\crdneedspace{135pt}` + `\abscontent` `\nopagebreak[4]` guard below so `# Abstract` either prints with at least 3 opening lines on Page 1 or moves cleanly onto Page 2 with its paragraph.
- **Strict Code-Only Monospace**: Never use inline Markdown backticks (outside evaluated knitr `` `r ...` `` calls), `\texttt{}`, `\verb` or `<code>` in YAML captions/titles, headings, prose or table cells.

*(Note: If the report is a pure on-disk exploratory data analysis with no external `.bib` citations, omit the `bibliography:`, `csl:` and `link-citations:` fields from the YAML frontmatter and omit the `# Sources` / `::: {#refs}` block at the end of the document.)*

````markdown
---
title: "<REPORT TITLE IN UPPERCASE>."
subtitle: "<Clear Descriptive Subtitle Summarising Scope, Data Sources and Analytical Focus>."
date: "<Day Month Year>"
authors_line: "Aust Kätzchen"
emails:
  - austkaeztchen@confoederatio.org
hero_figure: "figures/<report_stem>_hero.png"
hero_caption: "<Caption describing the hero figure or cartographic basemap>."
hero_label: "fig:hero"
bibliography: <report_stem>.bib
csl: crd-mla-numeric.csl
link-citations: true
header-includes:
  - |
    \AtBeginDocument{%
      \makeatletter
      \ifdefined\crdneedspace
        \pretocmd{\section}{\crdneedspace{135pt}}{}{}%
        \ifdefined\abscontent
          \pretocmd{\abscontent}{\crdneedspace{90pt}\nopagebreak[4]}{}{}%
        \fi
      \fi
      \makeatother
    }
output:
  pdf_document:
    template: template.tex
    latex_engine: xelatex
    keep_tex: false
---

```{r setup, include=FALSE}
Sys.setenv(VELKSCALA_ROOT = "E:/Active Projects/Project 1746 - Intellte/papers/velkscala")
source("E:/Active Projects/Project 1746 - Intellte/core/framework/R/framework_init.R")

# Ensure all tables render inline at 10pt body font size without horizontal overflow or float page isolation,
# and replace em/en-dashes with plain hyphens (-).
sanitize_latex_text <- function (arg0_text, arg1_in_table = FALSE) {
  text <- as.character(arg0_text)
  if (length(text) == 0 || is.na(text) || !nzchar(text)) return("")
  text <- gsub("`", "", text, fixed = TRUE)
  parts <- strsplit(text, "(?<=\\$)|(?=\\$)", perl = TRUE)[[1]]
  in_math <- FALSE
  out_parts <- character(length(parts))
  for (i in seq_along(parts)) {
    p <- parts[i]
    if (identical(p, "$")) {
      in_math <- !in_math
      out_parts[i] <- "$"
    } else if (in_math) {
      p <- gsub("\u2192", " \\rightarrow ", p, fixed = TRUE)
      p <- gsub("\u00d7", " \\times ", p, fixed = TRUE)
      p <- gsub("\u0394", "\\Delta ", p, fixed = TRUE)
      p <- gsub("\u00b2", "^2", p, fixed = TRUE)
      p <- gsub("\u2013", "-", p, fixed = TRUE)
      p <- gsub("\u2014", "-", p, fixed = TRUE)
      p <- gsub("---", "-", p, fixed = TRUE)
      p <- gsub("--", "-", p, fixed = TRUE)
      p <- gsub("(?<!\\\\)%", "\\\\%", p, perl = TRUE)
      out_parts[i] <- p
    } else {
      p <- gsub("\u2192", "->", p, fixed = TRUE)
      p <- gsub("\u00d7", "x", p, fixed = TRUE)
      p <- gsub("\u0394", "$\\Delta$", p, fixed = TRUE)
      p <- gsub("km\u00b2", "km\\textsuperscript{2}", p, fixed = TRUE)
      p <- gsub("m\u00b2", "m\\textsuperscript{2}", p, fixed = TRUE)
      p <- gsub("R\u00b2", "R\\textsuperscript{2}", p, fixed = TRUE)
      p <- gsub("\u00b2", "\\textsuperscript{2}", p, fixed = TRUE)
      p <- gsub("\u2013", "-", p, fixed = TRUE)
      p <- gsub("\u2014", " - ", p, fixed = TRUE)
      p <- gsub("---", " - ", p, fixed = TRUE)
      p <- gsub("--", "-", p, fixed = TRUE)
      p <- gsub("(?<!\\\\)&", "\\\\&", p, perl = TRUE)
      p <- gsub("(?<!\\\\)%", "\\\\%", p, perl = TRUE)
      p <- gsub("(?<!\\\\)_", "\\\\_", p, perl = TRUE)
      if (isTRUE(arg1_in_table)) {
        p <- gsub("\\_", "\\_\\allowbreak{}", p, fixed = TRUE)
        p <- gsub("/", "/\\allowbreak{}", p, fixed = TRUE)
        # Keep thousands-separated numbers and BC/AD dates on a single line inside table cells
        p <- gsub("([0-9]) ([0-9]{3}\\b)", "\\1~\\2", p, perl = TRUE)
        p <- gsub("([0-9]) ([0-9]{3}\\b)", "\\1~\\2", p, perl = TRUE)
        p <- gsub("([0-9])\\s*(BC|AD)\\b", "\\1\\2", p, perl = TRUE)
        # Prevent line breaks immediately after a leading negative sign (e.g. -10000)
        p <- gsub("(^|\\s|\\()-([0-9])", "\\1\\\\mbox{-}\\2", p, perl = TRUE)
      }
      out_parts[i] <- p
    }
  }
  return(paste(out_parts, collapse = ""))
}

sanitize_prose_unicode_for_latex <- function (arg0_line) {
  line_str <- as.character(arg0_line)
  if (length(line_str) == 0 || is.na(line_str) || !nzchar(line_str)) return(line_str)
  parts <- strsplit(line_str, "(?<=\\$)|(?=\\$)", perl = TRUE)[[1]]
  in_math <- FALSE
  for (i in seq_along(parts)) {
    p <- parts[i]
    if (identical(p, "$")) {
      in_math <- !in_math
    } else if (in_math) {
      p <- gsub("\u2192", " \\rightarrow ", p, fixed = TRUE)
      p <- gsub("\u00d7", " \\times ", p, fixed = TRUE)
      p <- gsub("\u0394", "\\Delta ", p, fixed = TRUE)
      p <- gsub("\u2248", " \\approx ", p, fixed = TRUE)
      p <- gsub("\u2013", "-", p, fixed = TRUE)
      p <- gsub("\u2014", "-", p, fixed = TRUE)
      parts[i] <- p
    } else {
      p <- gsub(
        "\\b(Figures?|Figs?\\.|Tables?|Tabs?\\.|Images?|Definitions?|Sections?|Appendix)(?:\\s+|~)\\\\ref\\{([^}]+)\\}",
        "\\\\crdxref{\\1}{\\2}",
        p,
        perl = TRUE
      )
      p <- gsub("\u2192", "->", p, fixed = TRUE)
      p <- gsub("\u00d7", "x", p, fixed = TRUE)
      p <- gsub("\u0394", "$\\Delta$", p, fixed = TRUE)
      p <- gsub("\u2248", "~", p, fixed = TRUE)
      p <- gsub("km\u00b2", "km\\textsuperscript{2}", p, fixed = TRUE)
      p <- gsub("m\u00b2", "m\\textsuperscript{2}", p, fixed = TRUE)
      p <- gsub("R\u00b2", "R\\textsuperscript{2}", p, fixed = TRUE)
      p <- gsub("\u00b2", "\\textsuperscript{2}", p, fixed = TRUE)
      p <- gsub("\u2013", "-", p, fixed = TRUE)
      p <- gsub("\u2014", " - ", p, fixed = TRUE)
      p <- gsub("---", " - ", p, fixed = TRUE)
      p <- gsub("--", "-", p, fixed = TRUE)
      parts[i] <- p
    }
  }
  return(paste(parts, collapse = ""))
}

render_table_template <- function (arg0_df, arg1_options = NULL) {
  df <- as.data.frame(arg0_df, stringsAsFactors = FALSE)
  rownames(df) <- NULL
  options <- if (!is.null(arg1_options)) arg1_options else list()

  caption_str <- if (!is.null(options$caption)) as.character(options$caption) else ""
  col_names <- if (!is.null(options$col_names)) as.character(options$col_names) else colnames(df)
  euro_decimals <- if (!is.null(options$euro_decimals)) isTRUE(options$euro_decimals) else TRUE
  is_latex <- if (requireNamespace("knitr", quietly = TRUE)) knitr::is_latex_output() else FALSE
  label_str <- if (!is.null(options$label)) as.character(options$label) else ""

  n_cols <- ncol(df)
  n_rows <- nrow(df)
  if (n_rows == 0 || n_cols == 0) return(invisible(NULL))

  if (length(col_names) != n_cols) {
    col_names <- colnames(df)
  }
  col_names <- gsub("`", "", col_names, fixed = TRUE)
  col_names <- gsub("\n", " ", col_names, fixed = TRUE)
  col_names <- gsub("([0-9])\\s+(BC|AD)\\b", "\\1\\2", col_names, perl = TRUE)
  col_names <- gsub("\u2014", " - ", col_names, fixed = TRUE)
  col_names <- gsub("\u2013", "-", col_names, fixed = TRUE)
  for (c_i in seq_len(n_cols)) {
    df[[c_i]] <- gsub("`", "", as.character(df[[c_i]]), fixed = TRUE)
    df[[c_i]] <- gsub("\\*\\*", "", as.character(df[[c_i]]))
    df[[c_i]] <- gsub("\u2014", " - ", as.character(df[[c_i]]), fixed = TRUE)
    df[[c_i]] <- gsub("\u2013", "-", as.character(df[[c_i]]), fixed = TRUE)
    df[[c_i]] <- gsub("---", " - ", as.character(df[[c_i]]), fixed = TRUE)
    df[[c_i]] <- gsub("--", "-", as.character(df[[c_i]]), fixed = TRUE)
    df[[c_i]] <- gsub("([0-9])\\s+(BC|AD)\\b", "\\1\\2", as.character(df[[c_i]]), perl = TRUE)
  }

  if (!is_latex) {
    disp_df <- df
    colnames(disp_df) <- col_names
    for (c_idx in seq_len(n_cols)) {
      disp_df[[c_idx]] <- vapply(
        disp_df[[c_idx]],
        function (v) format_table_cell(v, c_idx, list(bold_first_col = FALSE, euro_decimals = euro_decimals, is_latex = FALSE)),
        character(1)
      )
    }
    kb <- knitr::kable(disp_df, format = "markdown", caption = if (nzchar(caption_str)) caption_str else NULL)
    return(knitr::asis_output(paste(as.character(kb), collapse = "\n")))
  }

  # Calculate safe usable fraction of \textwidth accounting for (n_cols - 1) inter-column gaps
  usable_frac <- max(0.78, 0.962 - 0.0132 * (n_cols - 1L))

  min_frac <- numeric(n_cols)
  col_weights <- numeric(n_cols)
  for (c_idx in seq_len(n_cols)) {
    hdr_str <- col_names[c_idx]
    hdr_words <- unlist(strsplit(hdr_str, "[\\s/\\-]+", perl = TRUE))
    hdr_max_w <- min(11L, max(nchar(hdr_words), 3L))

    cell_vec <- as.character(df[[c_idx]])
    # Treat thousands-separated numbers (1 280,0k) and dates (10000BC) as single unbreakable tokens
    cell_vec_joined <- gsub("([0-9]) ([0-9]{3}\\b)", "\\1_\\2", cell_vec, perl = TRUE)
    cell_vec_joined <- gsub("([0-9])\\s*(BC|AD)\\b", "\\1\\2", cell_vec_joined, perl = TRUE)
    cell_words <- unlist(strsplit(paste(cell_vec_joined, collapse = " "), "[\\s/]+", perl = TRUE))
    cell_max_w <- min(11L, max(nchar(cell_words), 3L))

    # Word-fit floor in fraction of 468pt textwidth
    req_pts <- max(hdr_max_w * 5.1 + 4.0, cell_max_w * 4.7 + 4.0, 30.0)
    min_frac[c_idx] <- req_pts / 468.0

    cell_lens <- nchar(cell_vec)
    cell_q85 <- as.numeric(quantile(cell_lens, probs = 0.85, na.rm = TRUE))
    cell_max <- max(cell_lens, nchar(hdr_str), na.rm = TRUE)
    eff_len <- max(nchar(hdr_str) * 0.42, min(cell_max, max(cell_q85, 6.0)))
    col_weights[c_idx] <- max(3.5, eff_len ^ 0.65)
  }

  if (sum(min_frac) > usable_frac * 0.94) {
    min_frac <- min_frac * ((usable_frac * 0.94) / sum(min_frac))
  }
  rem_frac <- max(0.0, usable_frac - sum(min_frac))
  col_fracs <- min_frac + rem_frac * (col_weights / sum(col_weights))

  # IMPORTANT: Do NOT put \hspace{0pt} in col_specs, so header cells never break before the first word (keeping valign=top)
  col_specs <- vapply(
    col_fracs,
    function (fr) sprintf(">{\\raggedright\\arraybackslash\\hyphenpenalty=50\\exhyphenpenalty=50}p{%.4f\\textwidth}", fr),
    character(1)
  )
  align_str <- paste(col_specs, collapse = "")

  header_cells <- vapply(
    seq_len(n_cols),
    function (c_idx) {
      clean_h <- sanitize_latex_text(col_names[c_idx], TRUE)
      paste0("{\\karlabold\\lefthyphenmin=5\\righthyphenmin=5 ", clean_h, "}")
    },
    character(1)
  )
  header_line <- paste0(paste(header_cells, collapse = " & "), " \\\\*[4pt]")

  cap_tex <- sanitize_latex_text(caption_str, FALSE)
  lbl_tex <- if (nzchar(label_str)) paste0("\\label{", label_str, "}") else ""
  row_pt <- if (n_rows >= 14L) "1pt" else "2pt"
  arr_str <- if (n_rows >= 14L) "1.0" else "1.08"

  block_lines <- c(
    paste0(strrep("\x60", 3), "{=latex}"),
    "\\par\\vspace{4pt}",
    "\\begingroup\\fontsize{10pt}{14pt}\\selectfont\\normalfont\\rmfamily\\mdseries",
    "\\setlength{\\tabcolsep}{3pt}",
    paste0("\\renewcommand{\\arraystretch}{", arr_str, "}"),
    "\\setlength{\\LTpre}{4pt}",
    "\\setlength{\\LTpost}{4pt}",
    "\\setlength{\\LTcapwidth}{\\textwidth}",
    paste0("\\begin{longtable}[l]{@{}", align_str, "@{}}"),
    header_line,
    "\\endfirsthead",
    "\\endhead"
  )

  for (r_idx in seq_len(n_rows)) {
    row_cells <- vapply(
      seq_len(n_cols),
      function (c_idx) {
        raw_v <- df[r_idx, c_idx]
        val_str <- if (is.null(raw_v) || is.na(raw_v)) "-" else as.character(raw_v)
        val_str <- trimws(gsub("\\*\\*", "", val_str))
        if (euro_decimals) {
          val_str <- convert_euro_decimals_in_text(val_str)
        }
        clean_v <- sanitize_latex_text(val_str, TRUE)
        paste0("{\\normalfont\\rmfamily\\mdseries\\lefthyphenmin=4\\righthyphenmin=4\\hspace{0pt} ", clean_v, "}")
      },
      character(1)
    )
    row_end <- paste0("\\\\[", row_pt, "]")
    if (r_idx == n_rows && (nzchar(cap_tex) || nzchar(lbl_tex))) {
      row_end <- "\\\\*[5pt]"
    }
    block_lines <- c(block_lines, paste0(paste(row_cells, collapse = " & "), " ", row_end))
  }

  if (nzchar(cap_tex) || nzchar(lbl_tex)) {
    block_lines <- c(block_lines, paste0("\\caption{", cap_tex, "}", lbl_tex, "\\\\"))
  }
  block_lines <- c(
    block_lines,
    "\\end{longtable}\\endgroup",
    "\\vspace{4pt}\\par",
    strrep("\x60", 3)
  )

  return(knitr::asis_output(paste(block_lines, collapse = "\n")))
}

orig_render_figure_template <- render_figure_template
render_figure_template <- function (arg0_file_path, arg1_options = NULL) {
  options <- if (!is.null(arg1_options)) arg1_options else list()
  options$placement <- "!htbp"
  if (is.null(options$max_height) || identical(options$max_height, "none")) {
    options$max_height <- "0.52\\textheight"
  }
  return(orig_render_figure_template(arg0_file_path, options))
}
```

```{r fig1-hero-dom, results='asis'}
if (!knitr::is_latex_output()) {
  render_figure_template(
    "figures/<report_stem>_hero.png",
    list(
      caption = "<Caption describing the hero figure or cartographic basemap>.",
      label = "fig:hero",
      span_columns = TRUE
    )
  )
}
```
````

---

## 2. Optional R Data Loader & Formatting Helpers for On-Disk Datasets

Use these helper functions inside `<report_stem>.Rmd` when dynamically formatting on-disk JSON, CSV or summary statistics into tables:

````markdown
```{r data-helpers, include=FALSE}
fmt_num_eu <- function (arg0_val, arg1_digits = 2L, arg2_semantic = TRUE) {
  if (is.null(arg0_val) || is.na(arg0_val)) return("-")
  v <- as.numeric(arg0_val)
  abs_v <- abs(v)
  fmt_clean <- function (val, suffix) {
    s <- sprintf(paste0("%.", arg1_digits, "f"), val)
    s <- sub("0+$", "", s)
    s <- sub("\\.$", "", s)
    paste0(gsub("\\.", ",", s), suffix)
  }
  if (isTRUE(arg2_semantic)) {
    if (abs_v >= 1e12) return(fmt_clean(v / 1e12, "T"))
    if (abs_v >= 1e9) return(fmt_clean(v / 1e9, "B"))
    if (abs_v >= 1e6) return(fmt_clean(v / 1e6, "M"))
    if (abs_v >= 1e3) return(fmt_clean(v / 1e3, "k"))
  }
  if (abs_v == round(abs_v)) {
    return(format(round(v), big.mark = ".", scientific = FALSE, trim = TRUE))
  }
  return(fmt_clean(v, ""))
}

fmt_year_lbl <- function (arg0_y) {
  y <- as.numeric(arg0_y)
  if (y < 0) return(paste0(abs(round(y)), "BC"))
  return(paste0(round(y), "AD"))
}

fmt_coord_pair <- function (arg0_coords) {
  lat <- as.numeric(arg0_coords[[1]])
  lon <- as.numeric(arg0_coords[[2]])
  lat_s <- paste0(gsub("\\.", ",", sprintf("%.2f", abs(lat))), if (lat >= 0) "°N" else "°S")
  lon_s <- paste0(gsub("\\.", ",", sprintf("%.2f", abs(lon))), if (lon >= 0) "°E" else "°W")
  return(paste0(lat_s, ", ", lon_s))
}
```
````

And at the end of `<report_stem>.Rmd`, include the bibliography (if external sources are cited) and the footnotes hook:

````markdown
# Sources

::: {#refs}
:::

```{r crd_footnotes, echo=FALSE, results='asis'}
emit_crd_footnotes()
```
````

---

## 3. Automated Compilation, Figure Audit & Verification Script (`pymupdf` + PDF Archive Validator)

Run `python .agents/skills/population-regional-study/scripts/audit_figure_scripts.py <report_dir>` before compiling figures and prose to ensure every figure script preserves default Matplotlib styling (`plt.rcdefaults(); plt.style.use("default")`, `DejaVu Sans`, 4-sided spines, rendered `$...$` MathText with `{,}` decimals, `FuncFormatter` comma ticks, zero `$10^k$` / `1e4` scientific notation on counts or densities via `apply_human_log_ticks()` / `euro_log_formatter()`), renders smooth vector GeoJSON polygons with `set_aspect("equal")` instead of pixelated categorical mask `imshow()` calls, splits distant non-contiguous exclaves into dedicated insets and verifies zero panel-spine bleeds or text overlaps via `verify_panel_bounds_and_overlaps()` before saving (`pdf.mtime >= max(fig.mtime)`):

```python
import math
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

def init_default_matplotlib ():
  mpl.rcdefaults()
  plt.style.use("default")
  mpl.rcParams["savefig.dpi"] = 300

def fmt_mathtext_eu (val, digits=2):
  s = f"{float(val):.{digits}f}".replace(".", ",")
  if "," in s:
    s = s.rstrip("0").rstrip(",")
  return s.replace(",", "{,}")

def euro_tick_formatter (digits=2):
  return mticker.FuncFormatter(
    lambda x, _pos: (f"{x:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".").rstrip("0").rstrip(",") if digits > 0 else f"{x:,.0f}".replace(",", "."))
  )

def euro_log_formatter (semantic=True, digits=2):
  def _fmt (x, _pos):
    v = float(x)
    if not math.isfinite(v) or v <= 0.0:
      return ""
    if v >= 1e6 and semantic:
      return f"{v / 1e6:.2f}".rstrip("0").rstrip(".").replace(".", ",") + "M"
    if v >= 1e3 and semantic:
      return f"{v / 1e3:.1f}".rstrip("0").rstrip(".").replace(".", ",") + "k"
    if v >= 1.0:
      return str(int(round(v))) if abs(v - round(v)) < 1e-6 else f"{v:.{digits}f}".rstrip("0").rstrip(".").replace(".", ",")
    d = max(digits, 4 if v < 1e-3 else (3 if v < 1e-2 else digits))
    return f"{v:.{d}f}".rstrip("0").rstrip(".").replace(".", ",")
  return mticker.FuncFormatter(_fmt)

def apply_human_log_ticks (ax, axes="both", semantic=True):
  fmt = euro_log_formatter(semantic)
  for axis_obj in ([ax.xaxis] if axes == "x" else ([ax.yaxis] if axes == "y" else [ax.xaxis, ax.yaxis])):
    axis_obj.set_major_formatter(fmt)
    axis_obj.set_minor_formatter(mticker.NullFormatter())
```

Then run this check after compiling `<report_stem>.Rmd` to verify that `.pdf` and `.md` outputs build cleanly (and were recompiled after every figure PNG update), every page satisfies `max_x1 <= 540.1 pt` (zero right-margin overflow), `0` unresolved `??` tokens appear and any archived PDFs in `./papers/` are valid `%PDF` documents `> 10 KB`:

```python
import pathlib
import subprocess
import pymupdf

RSCRIPT = r"C:\Program Files\R\R-4.5.0\bin\Rscript.exe"

def compile_and_verify_report(rmd_path):
  p = pathlib.Path(rmd_path).resolve()
  workdir = str(p.parent).replace("\\", "/")
  r_expr = (
    f"setwd('{workdir}'); "
    f"rmarkdown::render('{p.name}', output_format='pdf_document', quiet=TRUE); "
    f"knitr::knit('{p.name}', output='{p.with_suffix('.md').name}', quiet=TRUE)"
  )
  subprocess.run([RSCRIPT, "-e", r_expr], check=True)
  pdf_path = p.with_suffix(".pdf")
  fig_dir = p.parent / "figures"
  if fig_dir.is_dir():
    pngs = list(fig_dir.glob("*.png"))
    if pngs:
      assert pdf_path.stat().st_mtime + 2.0 >= max(x.stat().st_mtime for x in pngs), f"Stale PDF older than PNG in {p.parent}"
  doc = pymupdf.open(str(pdf_path))
  assert len(doc) >= 1 and len(doc[0].get_text("text").strip()) >= 80, f"Blank Page 1 in {pdf_path.name}"
  # Guard against orphaned Page-1 Abstract/section headings and non-code monospace fonts
  p1_dict = doc[0].get_text("dict")
  p1_lines = []
  for blk in p1_dict.get("blocks", []):
    if blk.get("type", 0) != 0:
      continue
    for ln in blk.get("lines", []):
      sp_list = ln.get("spans", [])
      txt = "".join(sp.get("text", "") for sp in sp_list).strip()
      if txt:
        max_sz = max((float(sp.get("size", 0.0)) for sp in sp_list), default=0.0)
        is_jb = any("jost" in sp.get("font", "").lower() and "bold" in sp.get("font", "").lower() and sp.get("size", 0) >= 10.3 for sp in sp_list)
        p1_lines.append((float(ln["bbox"][1]), float(ln["bbox"][3]), max_sz, is_jb, txt))
  for y0, y1, max_sz, is_jb, txt in p1_lines:
    if (txt.lower() == "abstract" and max_sz >= 10.3) or (is_jb and max_sz <= 14.5 and y0 >= float(doc[0].rect.height) * 0.52):
      body_below = sum(1 for by0, _, _, b_jb, b_txt in p1_lines if by0 > y1 - 1.0 and not b_jb and len(b_txt) >= 25)
      assert body_below >= 2, f"Orphaned Page-1 heading {txt!r} in {pdf_path.name} ({body_below} prose lines below)"

  mono_subs = ("lmmono", "courier", "consolas", "inconsolata", "dejavusansmono", "cmtt", "lmtt", "firacode", "jetbrainsmono")
  mono_pages = [
    i + 1 for i in range(len(doc))
    if any(any(sub in str(f[3]).lower() for sub in mono_subs) for f in doc.get_page_fonts(i))
  ]
  # When a prose/editorial report displays zero intentional code blocks, forbid embedded monospace fonts
  assert len(mono_pages) == 0 or "echo=TRUE" in p.read_text(encoding="utf-8", errors="ignore"), (
    f"Unintended monospace font on pages {mono_pages} in {pdf_path.name}"
  )

  max_x1 = 0.0
  qmarks = []
  for i, page in enumerate(doc):
    pg_txt = page.get_text("text")
    assert "(Continued from previous page)" not in pg_txt, f"Repeated header in {pdf_path.name} p.{i + 1}"
    assert "\ufffd" not in pg_txt, f"Replacement glyph U+FFFD in {pdf_path.name} p.{i + 1}"
    for w in page.get_text("words"):
      if w[2] > max_x1:
        max_x1 = w[2]
      if "??" in w[4]:
        qmarks.append((i + 1, w[4]))
  assert max_x1 <= 540.1, f"Right margin overflow in {pdf_path.name}: max_x1={max_x1:.2f}"
  assert len(qmarks) == 0, f"Unresolved ?? in {pdf_path.name}: {qmarks}"
  doc.close()

  papers_dir = p.parent / "papers"
  if papers_dir.is_dir():
    for pdf_file in sorted(papers_dir.glob("*.pdf")):
      size_b = pdf_file.stat().st_size
      assert size_b > 10240, f"Archived PDF too small ({size_b} bytes): {pdf_file.name}"
      with pdf_file.open("rb") as fh:
        hdr = fh.read(5)
      assert hdr == b"%PDF-", f"Invalid PDF header ({hdr!r}) in {pdf_file.name}"
```
