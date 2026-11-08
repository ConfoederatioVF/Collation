# Intellte R Markdown Setup Block and Audit Scripts

This reference file provides the verified R Markdown `{r setup, include=FALSE}` chunk, the dynamic `population_Stadester` JSON loader chunk for `<region>_settlements.Rmd`, and the Python verification script for auditing compiled PDFs and JSON gazetteers.

---

## 1. Standard YAML Frontmatter & `{r setup, include=FALSE}` Block

Use this exact setup block at the top of both `<region>_literature_review.Rmd` and `<region>_settlements.Rmd`. It enforces:
- Inline `10pt` (`10pt/14pt`) `longtable` rendering (never `\resizebox` or isolated float pages).
- Top-aligned table headers (`valign=top`) by omitting `\hspace{0pt}` from `col_specs` and placing `\hspace{0pt}` only inside body cells.
- Compact `10000BC` / `1897AD` year formatting without spaces.
- Plain hyphens (`-`) in place of em/en-dashes.
- Non-overlapping `!htbp` figure placement capped at `0.42\textheight`.

```markdown
---
title: "DEMOGRAPHIC AND SETTLEMENT HISTORY OF <REGION UPPERCASE>."
subtitle: "Regional Boundaries, Archaeological Synthesis, and Population Estimates (<START_YEAR, default 10000BC> - <END_YEAR, default 2000AD>)."
date: "<Day Month Year>"
authors_line: "Aust Kätzchen"
emails:
  - austkaeztchen@confoederatio.org
hero_figure: "figures/<region>_regional_map.png"
hero_caption: "Cartographic basemap of <Region>, showing hydrological basins, administrative boundaries, and principal settlements."
hero_label: "fig:hero"
bibliography: <region>_literature_review.bib
csl: crd-mla-numeric.csl
link-citations: true
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
    paste0("\\multicolumn{", n_cols, "}{@{}l@{}}{\\normalfont\\karlalight\\fontsize{9pt}{12pt}\\selectfont (Continued from previous page)} \\\\*[3pt]"),
    header_line,
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
    options$max_height <- "0.42\\textheight"
  }
  return(orig_render_figure_template(arg0_file_path, options))
}
```
````

---

## 2. Dynamic `population_Stadester` JSON Loader Chunk for `<region>_settlements.Rmd`

Include this chunk after `{r setup, include=FALSE}` in `<region>_settlements.Rmd` to dynamically parse `<region>_settlements.json`:

````markdown
```{r load-stadester-json, include=FALSE}
GAZETTEER_JSON_FILE <- "<region>_settlements.json"
gaz_map <- jsonlite::fromJSON(GAZETTEER_JSON_FILE, simplifyVector = FALSE)
settlements_list <- unname(gaz_map)

first_year_num <- function (arg0_s) {
  yrs <- as.numeric(names(arg0_s$population))
  if (length(yrs) == 0) return(99999)
  return(min(yrs))
}
last_year_num <- function (arg0_s) {
  yrs <- as.numeric(names(arg0_s$population))
  if (length(yrs) == 0) return(-99999)
  return(max(yrs))
}

ord_idx <- order(
  vapply(settlements_list, first_year_num, numeric(1)),
  vapply(settlements_list, function (s) as.character(s$name), character(1))
)
settlements_list <- settlements_list[ord_idx]

fmt_other_names <- function (arg0_s) {
  onames <- unlist(arg0_s$other_names)
  if (length(onames) == 0) return("-")
  clean_vec <- unique(as.character(onames))
  clean_vec <- clean_vec[nzchar(clean_vec) & tolower(clean_vec) != tolower(arg0_s$name)]
  if (length(clean_vec) == 0) clean_vec <- unique(as.character(onames))
  return(paste(head(clean_vec, 2L), collapse = "; "))
}

fmt_year_lbl <- function (arg0_y) {
  y <- as.numeric(arg0_y)
  if (y < 0) return(paste0(abs(round(y)), "BC"))
  return(paste0(round(y), "AD"))
}

fmt_span <- function (arg0_s) {
  y1 <- first_year_num(arg0_s)
  y2 <- last_year_num(arg0_s)
  if (y1 == y2) return(fmt_year_lbl(y1))
  if (y1 < 0 && y2 < 0) return(paste0(abs(y1), "-", abs(y2), "BC"))
  if (y1 > 0 && y2 > 0) return(paste0(y1, "-", y2, "AD"))
  return(paste0(fmt_year_lbl(y1), " - ", fmt_year_lbl(y2)))
}

fmt_num_eu <- function (arg0_val) {
  if (is.null(arg0_val) || is.na(arg0_val)) return("-")
  v <- as.numeric(arg0_val)
  if (v >= 1000) {
    s <- sprintf("%.1fk", v / 1000.0)
    s <- gsub("\\.", ",", s)
    return(s)
  }
  return(as.character(round(v)))
}

fmt_coord_pair <- function (arg0_coords) {
  lat <- as.numeric(arg0_coords[[1]])
  lon <- as.numeric(arg0_coords[[2]])
  lat_s <- paste0(gsub("\\.", ",", sprintf("%.2f", abs(lat))), if (lat >= 0) "°N" else "°S")
  lon_s <- paste0(gsub("\\.", ",", sprintf("%.2f", abs(lon))), if (lon >= 0) "°E" else "°W")
  return(paste0(lat_s, ", ", lon_s))
}

fmt_pop_series <- function (arg0_s, arg1_ymin = -99999, arg2_ymax = 99999) {
  pop_map <- arg0_s$population
  yrs <- as.numeric(names(pop_map))
  vals <- as.numeric(unlist(pop_map))
  keep <- which(yrs >= arg1_ymin & yrs <= arg2_ymax)
  if (length(keep) == 0) return("-")
  parts <- vapply(keep, function (idx) {
    paste0(fmt_year_lbl(yrs[idx]), ": ", fmt_num_eu(vals[idx]))
  }, character(1))
  return(paste(parts, collapse = "; "))
}

get_pop_window_val <- function (arg0_s, arg1_ymin, arg2_ymax) {
  pop_map <- arg0_s$population
  yrs <- as.numeric(names(pop_map))
  vals <- as.numeric(unlist(pop_map))
  keep <- which(yrs >= arg1_ymin & yrs <= arg2_ymax)
  if (length(keep) == 0) return("-")
  idx <- keep[which.max(yrs[keep])]
  return(fmt_num_eu(vals[idx]))
}
```
````

---

## 3. Automated Compilation & Verification Script (`pymupdf` + JSON Schema Validator)

Run this check after compiling `.Rmd` files and generating `_settlements.json` files:

```python
import glob
import json
import pathlib
import subprocess
import pymupdf

RSCRIPT = r"C:\Program Files\R\R-4.5.0\bin\Rscript.exe"

def compile_and_verify_rmd(rmd_path):
  p = pathlib.Path(rmd_path).resolve()
  workdir = str(p.parent).replace("\\", "/")
  r_expr = (
    f"setwd('{workdir}'); "
    f"rmarkdown::render('{p.name}', output_format='pdf_document', quiet=TRUE); "
    f"knitr::knit('{p.name}', output='{p.with_suffix('.md').name}', quiet=TRUE)"
  )
  subprocess.run([RSCRIPT, "-e", r_expr], check=True)
  pdf_path = p.with_suffix(".pdf")
  doc = pymupdf.open(str(pdf_path))
  max_x1 = 0.0
  qmarks = []
  for i, page in enumerate(doc):
    for w in page.get_text("words"):
      if w[2] > max_x1:
        max_x1 = w[2]
      if "??" in w[4]:
        qmarks.append((i + 1, w[4]))
  assert max_x1 <= 540.1, f"Right margin overflow in {pdf_path.name}: max_x1={max_x1:.2f}"
  assert len(qmarks) == 0, f"Unresolved ?? in {pdf_path.name}: {qmarks}"
  doc.close()

def verify_stadester_json(json_path):
  p = pathlib.Path(json_path)
  data = json.loads(p.read_text(encoding="utf-8"))
  assert len(data) >= 100, f"Too few settlements ({len(data)}) in {p.name}; expected comprehensive coverage (100-250+)."
  for k, v in data.items():
    assert set(v.keys()) == {"name", "other_names", "coords", "country", "key", "population"}, f"Bad keys in {k}"
    assert v["key"] == k, f"Key mismatch: {v['key']} != {k}"
    assert isinstance(v["coords"], list) and len(v["coords"]) == 2, f"Bad coords in {k}"
    assert len(v["population"]) > 0, f"Empty population map in {k}"
    for yr, pop in v["population"].items():
      int(yr)
      assert isinstance(pop, int) and pop > 0, f"Invalid population {yr}={pop} in {k} (must be int > 0, no 0 entries)"
```
