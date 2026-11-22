# Shared Operation Viscount RMarkdown Helpers
# Auto-discovers Intellte `core/framework/R/framework_init.R` and configures
# `TEXINPUTS`, European decimal/semantic formatting, and thin LaTeX/HTML table
# and figure wrappers without overriding Intellte's canonical `render_table_template`.

local({
  cur_dir <- normalizePath(getwd(), winslash = "/", mustWork = FALSE)

  # Ensure both Intellte root and regional _shared/template appear on TEXINPUTS
  find_intellte_root <- function () {
    env_root <- Sys.getenv("INTELLTE_ROOT", "")
    if (nzchar(env_root) && file.exists(file.path(env_root, "core/framework/R/framework_init.R"))) {
      return(normalizePath(env_root, winslash = "/", mustWork = FALSE))
    }
    candidates <- c(
      "E:/Active Projects/Project 1746 - Intellte",
      "F:/Active Projects/Project 1746 - Intellte"
    )
    for (cand in candidates) {
      if (file.exists(file.path(cand, "core/framework/R/framework_init.R"))) {
        return(normalizePath(cand, winslash = "/", mustWork = FALSE))
      }
    }
    probe <- cur_dir
    for (i in seq_len(8)) {
      test_path <- file.path(probe, "core/framework/R/framework_init.R")
      if (file.exists(test_path)) return(normalizePath(probe, winslash = "/", mustWork = FALSE))
      parent <- dirname(probe)
      if (identical(parent, probe)) break
      probe <- parent
    }
    return("")
  }

  find_shared_template_dirs <- function () {
    dirs <- c()
    probe <- cur_dir
    for (i in seq_len(8)) {
      local_tpl <- file.path(probe, "_shared/template")
      if (dir.exists(local_tpl)) {
        dirs <- c(dirs, normalizePath(local_tpl, winslash = "/", mustWork = FALSE))
      }
      parent <- dirname(probe)
      if (identical(parent, probe)) break
      probe <- parent
    }
    unique(dirs)
  }

  intellte_root <- find_intellte_root()
  if (nzchar(intellte_root)) {
    Sys.setenv(INTELLTE_ROOT = intellte_root)
    if (!nzchar(Sys.getenv("VELKSCALA_ROOT", ""))) {
      velk_dir <- file.path(intellte_root, "papers/velkscala")
      if (dir.exists(velk_dir)) Sys.setenv(VELKSCALA_ROOT = velk_dir)
    }
    init_r <- file.path(intellte_root, "core/framework/R/framework_init.R")
    if (file.exists(init_r) && !exists("render_table_template", mode = "function")) {
      source(init_r, local = globalenv())
    }
  }

  tpl_dirs <- find_shared_template_dirs()
  if (nzchar(intellte_root)) {
    r_fw_dir <- file.path(intellte_root, "core/framework/R")
    if (dir.exists(r_fw_dir)) tpl_dirs <- c(tpl_dirs, r_fw_dir)
  }
  tex_sep <- if (.Platform$OS.type == "windows") ";" else ":"
  old_tex <- Sys.getenv("TEXINPUTS", "")
  new_tex <- paste(c(".", tpl_dirs, old_tex, ""), collapse = tex_sep)
  Sys.setenv(TEXINPUTS = new_tex)

  tryCatch({
    Sys.setlocale("LC_CTYPE", "English_United Kingdom.UTF-8")
  }, warning = function (w) {}, error = function (e) {})
})


#' Format a numeric value with European decimal comma and dot thousands separator
#'
#' @param arg0_value Numeric value to format
#' @param arg1_digits Integer decimal digits (default 2)
#' @return Character string using `58,88` formatting
viscount_fmt_number <- function (arg0_value, arg1_digits = 2L) {
  if (length(arg0_value) > 1L) {
    return(vapply(arg0_value, viscount_fmt_number, character(1L), arg1_digits = arg1_digits))
  }
  val <- suppressWarnings(as.numeric(arg0_value))
  if (length(val) == 0L || is.na(val) || !is.finite(val)) return("NA")
  s <- formatC(val, format = "f", digits = as.integer(arg1_digits), big.mark = ".", decimal.mark = ",")
  s <- sub("(,[0-9]*?[1-9])0+$", "\\1", s, perl = TRUE)
  sub(",0+$", "", s, perl = TRUE)
}


#' Format a population figure using EN-GB semantic suffixes (`k`, `M`, `B`, `T`)
#'
#' @param arg0_population Population count in persons
#' @return Character string using European decimals and semantic suffix
viscount_fmt_pop <- function (arg0_population) {
  if (length(arg0_population) > 1L) {
    return(vapply(arg0_population, viscount_fmt_pop, character(1L)))
  }
  val <- suppressWarnings(as.numeric(arg0_population))
  if (length(val) == 0L || is.na(val) || !is.finite(val)) return("NA")
  abs_val <- abs(val)
  if (abs_val >= 1e12) return(paste0(viscount_fmt_number(val / 1e12, 2L), "T"))
  if (abs_val >= 1e9) return(paste0(viscount_fmt_number(val / 1e9, 2L), "B"))
  if (abs_val >= 1e6) return(paste0(viscount_fmt_number(val / 1e6, 2L), "M"))
  if (abs_val >= 1e3) return(paste0(viscount_fmt_number(val / 1e3, 1L), "k"))
  formatC(as.integer(round(val)), format = "d", big.mark = ".")
}


#' Sanitise table cell strings for XeLaTeX typography (normalise CJK/full-width
#' punctuation and allow clean wrapping of unbroken archaeological site tokens)
#'
#' @param arg0_vec Character vector of table cell values
#' @return Sanitised character vector safe for Karla/XeLaTeX rendering
viscount_sanitise_tex_str <- function (arg0_vec) {
  s <- as.character(arg0_vec)
  s <- gsub("\uFF08", "(", s, fixed = TRUE)
  s <- gsub("\uFF09", ")", s, fixed = TRUE)
  s <- gsub("\u30FB", "-", s, fixed = TRUE)
  s <- gsub("\uFF65", "-", s, fixed = TRUE)
  s <- gsub("\u3000", " ", s, fixed = TRUE)
  s <- gsub("\u3001", ", ", s, fixed = TRUE)
  s <- gsub("\uFF1A", ": ", s, fixed = TRUE)
  s <- gsub("\uFF5E", "-", s, fixed = TRUE)
  s <- gsub("\uFF1D", "=", s, fixed = TRUE)
  s <- gsub("\uFF1F", "?", s, fixed = TRUE)
  s <- gsub("\u2010", "-", s, fixed = TRUE)
  s <- gsub("\u2160", "I", s, fixed = TRUE)
  s <- gsub("\u2161", "II", s, fixed = TRUE)
  s <- gsub("\u2162", "III", s, fixed = TRUE)
  s <- gsub("\u2170", "i", s, fixed = TRUE)
  s <- gsub("\u2171", "ii", s, fixed = TRUE)
  s <- gsub("\u2172", "iii", s, fixed = TRUE)
  s <- chartr("\uFF10\uFF11\uFF12\uFF13\uFF14\uFF15\uFF16\uFF17\uFF18\uFF19", "0123456789", s)
  s <- gsub("[\u3002-\u30FF\u3400-\u9FFF\uAC00-\uD7AF\uFF00-\uFFEF]", "", s, perl = TRUE)
  s <- gsub("([^\\s-]{26})(?=[^\\s-]{4,})", "\\1- ", s, perl = TRUE)
  s <- gsub("\\s{2,}", " ", s, perl = TRUE)
  trimws(s)
}


#' Thin regional wrapper around Intellte `render_table_template`
#'
#' @param arg0_df Data frame to render
#' @param arg1_caption Table caption
#' @param arg2_col_names Character vector of display column names
#' @param arg3_options Optional list passed to `render_table_template`
viscount_table <- function (arg0_df, arg1_caption = NULL, arg2_col_names = NULL, arg3_options = list(), ...) {
  dots <- list(...)
  if (is.null(arg1_caption) && !is.null(dots$caption)) arg1_caption <- dots$caption
  if (is.null(arg2_col_names) && !is.null(dots$col_names)) arg2_col_names <- dots$col_names
  if (is.null(arg2_col_names) && !is.null(dots$col.names)) arg2_col_names <- dots$col.names
  if (length(arg3_options) == 0 && !is.null(dots$options) && is.list(dots$options)) arg3_options <- dots$options
  df_clean <- arg0_df
  if (is.data.frame(df_clean)) {
    for (col_i in seq_along(df_clean)) {
      if (is.character(df_clean[[col_i]])) {
        df_clean[[col_i]] <- viscount_sanitise_tex_str(df_clean[[col_i]])
      }
    }
  }
  opts <- if (is.list(arg3_options)) arg3_options else list()
  if (!is.null(dots$label) && is.null(opts$label)) opts$label <- dots$label
  if (!is.null(dots$font_size) && is.null(opts$font_size)) opts$font_size <- dots$font_size
  opts$caption <- arg1_caption
  if (!is.null(arg2_col_names)) opts$col_names <- arg2_col_names
  if (is.null(opts$font_size)) opts$font_size <- "footnotesize"
  if (is.null(opts$scale_to_fit)) opts$scale_to_fit <- FALSE
  if (is.null(opts$span_columns)) opts$span_columns <- TRUE
  if (is.null(opts$bold_first_col)) opts$bold_first_col <- TRUE

  if (exists("render_table_template", mode = "function")) {
    return(render_table_template(df_clean, opts))
  }
  knitr::kable(df_clean, format = "pipe", caption = arg1_caption, col.names = arg2_col_names)
}


#' Thin regional wrapper around Intellte `render_figure_template` constraining float heights
#'
#' @param arg0_file_path Figure file path relative to the chapter Rmd directory
#' @param arg1_caption Figure caption
#' @param arg2_label LaTeX cross-reference label (e.g. `"fig:settlements"`)
#' @param arg3_options Optional overrides (`max_height`, `placement`, `span_columns`)
viscount_figure <- function (arg0_file_path, arg1_caption = NULL, arg2_label = NULL, arg3_options = list(), ...) {
  dots <- list(...)
  if (is.null(arg1_caption) && !is.null(dots$caption)) arg1_caption <- dots$caption
  if (is.null(arg2_label) && !is.null(dots$label)) arg2_label <- dots$label
  if (length(arg3_options) == 0 && !is.null(dots$options) && is.list(dots$options)) arg3_options <- dots$options
  opts <- if (is.list(arg3_options)) arg3_options else list()
  if (!is.null(dots$max_height) && is.null(opts$max_height)) opts$max_height <- dots$max_height
  opts$caption <- arg1_caption
  if (!is.null(arg2_label)) opts$label <- arg2_label
  if (is.null(opts$placement)) opts$placement <- "!htbp"
  if (is.null(opts$max_height) || identical(opts$max_height, "none")) {
    opts$max_height <- "0.42\\textheight"
  }
  if (is.null(opts$span_columns)) opts$span_columns <- TRUE

  if (knitr::is_latex_output()) {
    abs_p <- normalizePath(arg0_file_path, winslash = "/", mustWork = FALSE)
    if (nchar(abs_p) > 150L) {
      env_name <- if (isTRUE(opts$span_columns)) "figure*" else "figure"
      lbl_tex <- if (!is.null(opts$label) && nzchar(opts$label)) paste0("\\label{", opts$label, "}") else ""
      cap_tex <- if (!is.null(opts$caption)) gsub("%", "\\%", gsub("&", "\\&", opts$caption, fixed = TRUE), fixed = TRUE) else ""
      cat(sprintf(
        "\n\\begin{%s}[%s]\n\\centering\n\\includegraphics[width=\\linewidth,height=%s,keepaspectratio]{%s}\n\\caption{%s}%s\n\\end{%s}\n\n",
        env_name, opts$placement, opts$max_height, arg0_file_path, cap_tex, lbl_tex, env_name
      ))
      return(invisible(NULL))
    }
  }

  if (exists("render_figure_template", mode = "function")) {
    return(render_figure_template(arg0_file_path, opts))
  }
  cat(sprintf("\n![%s](%s)\n\n", arg1_caption, arg0_file_path))
}
