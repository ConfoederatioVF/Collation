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
  val <- suppressWarnings(as.numeric(arg0_value))
  if (is.na(val) || !is.finite(val)) return("NA")
  s <- formatC(val, format = "f", digits = as.integer(arg1_digits), big.mark = ".", decimal.mark = ",")
  s <- sub("(,[0-9]*?[1-9])0+$", "\\1", s, perl = TRUE)
  sub(",0+$", "", s, perl = TRUE)
}


#' Format a population figure using EN-GB semantic suffixes (`k`, `M`, `B`, `T`)
#'
#' @param arg0_population Population count in persons
#' @return Character string using European decimals and semantic suffix
viscount_fmt_pop <- function (arg0_population) {
  val <- suppressWarnings(as.numeric(arg0_population))
  if (is.na(val) || !is.finite(val)) return("NA")
  abs_val <- abs(val)
  if (abs_val >= 1e12) return(paste0(viscount_fmt_number(val / 1e12, 2L), "T"))
  if (abs_val >= 1e9) return(paste0(viscount_fmt_number(val / 1e9, 2L), "B"))
  if (abs_val >= 1e6) return(paste0(viscount_fmt_number(val / 1e6, 2L), "M"))
  if (abs_val >= 1e3) return(paste0(viscount_fmt_number(val / 1e3, 1L), "k"))
  formatC(as.integer(round(val)), format = "d", big.mark = ".")
}


#' Thin regional wrapper around Intellte `render_table_template`
#'
#' @param arg0_df Data frame to render
#' @param arg1_caption Table caption
#' @param arg2_col_names Character vector of display column names
#' @param arg3_options Optional list passed to `render_table_template`
viscount_table <- function (arg0_df, arg1_caption, arg2_col_names = NULL, arg3_options = list()) {
  opts <- if (is.list(arg3_options)) arg3_options else list()
  opts$caption <- arg1_caption
  if (!is.null(arg2_col_names)) opts$col_names <- arg2_col_names
  if (is.null(opts$font_size)) opts$font_size <- "footnotesize"
  if (is.null(opts$scale_to_fit)) opts$scale_to_fit <- FALSE
  if (is.null(opts$span_columns)) opts$span_columns <- TRUE
  if (is.null(opts$bold_first_col)) opts$bold_first_col <- TRUE

  if (knitr::is_latex_output() && is.data.frame(arg0_df)) {
    for (ci in seq_along(arg0_df)) {
      if (is.character(arg0_df[[ci]]) || is.factor(arg0_df[[ci]])) {
        col_v <- as.character(arg0_df[[ci]])
        col_v <- gsub("\\s*#\\s*", " No. ", col_v, perl = TRUE)
        arg0_df[[ci]] <- col_v
      }
    }
  }
  if (exists("render_table_template", mode = "function")) {
    return(render_table_template(arg0_df, opts))
  }
  knitr::kable(arg0_df, format = "pipe", caption = arg1_caption, col.names = arg2_col_names)
}


#' Thin regional wrapper around Intellte `render_figure_template` constraining float heights
#'
#' @param arg0_file_path Figure file path relative to the chapter Rmd directory
#' @param arg1_caption Figure caption
#' @param arg2_label LaTeX cross-reference label (e.g. `"fig:settlements"`)
#' @param arg3_options Optional overrides (`max_height`, `placement`, `span_columns`)
viscount_figure <- function (arg0_file_path, arg1_caption, arg2_label = NULL, arg3_options = list()) {
  opts <- if (is.list(arg3_options)) arg3_options else list()
  opts$caption <- arg1_caption
  if (!is.null(arg2_label)) opts$label <- arg2_label
  if (is.null(opts$placement)) opts$placement <- "!htbp"
  if (is.null(opts$max_height) || identical(opts$max_height, "none")) {
    opts$max_height <- "0.42\\textheight"
  }
  if (is.null(opts$span_columns)) opts$span_columns <- TRUE

  if (exists("render_figure_template", mode = "function")) {
    return(render_figure_template(arg0_file_path, opts))
  }
  cat(sprintf("\n![%s](%s)\n\n", arg1_caption, arg0_file_path))
}
