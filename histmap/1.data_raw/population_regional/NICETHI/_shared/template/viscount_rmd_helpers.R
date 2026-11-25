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
  s <- gsub("\u0167", "h", s, fixed = TRUE)
  s <- gsub("\u0166", "H", s, fixed = TRUE)
  s <- gsub("\u1E6F", "th", s, fixed = TRUE)
  s <- gsub("\u1E6E", "Th", s, fixed = TRUE)
  s <- gsub("\u1E0F", "dh", s, fixed = TRUE)
  s <- gsub("\u1E0E", "Dh", s, fixed = TRUE)
  s <- gsub("\u1E2B", "kh", s, fixed = TRUE)
  s <- gsub("\u1E2A", "Kh", s, fixed = TRUE)
  s <- gsub("\u0121", "gh", s, fixed = TRUE)
  s <- gsub("\u0120", "Gh", s, fixed = TRUE)
  s <- gsub("\u01E7", "j", s, fixed = TRUE)
  s <- gsub("\u01E6", "J", s, fixed = TRUE)
  s <- gsub("\u02BB", "'", s, fixed = TRUE)
  s <- gsub("\u02BC", "'", s, fixed = TRUE)
  s <- gsub("\u02BE", "'", s, fixed = TRUE)
  s <- gsub("\u02BF", "'", s, fixed = TRUE)
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
  extra <- list(...)
  if (is.null(arg1_caption) && !is.null(extra$caption)) arg1_caption <- extra$caption
  if (is.null(arg2_col_names) && !is.null(extra$col_names)) arg2_col_names <- extra$col_names
  if (is.null(arg2_col_names) && !is.null(extra$col.names)) arg2_col_names <- extra$col.names
  df_clean <- arg0_df
  if (is.data.frame(df_clean)) {
    for (col_i in seq_along(df_clean)) {
      if (is.character(df_clean[[col_i]])) {
        df_clean[[col_i]] <- viscount_sanitise_tex_str(df_clean[[col_i]])
      }
    }
  }
  opts <- if (is.list(arg3_options)) arg3_options else list()
  for (nm in setdiff(names(extra), c("caption", "col_names", "col.names"))) {
    if (is.null(opts[[nm]])) opts[[nm]] <- extra[[nm]]
  }
  max_display_rows <- if (!is.null(opts$max_rows)) as.integer(opts$max_rows) else 45L
  if (is.data.frame(df_clean) && !isTRUE(opts$allow_unbounded) && nrow(df_clean) > max_display_rows) {
    total_n <- nrow(df_clean)
    keep_n <- min(40L, max_display_rows)
    rem_n <- total_n - keep_n
    df_clean <- df_clean[seq_len(keep_n), , drop = FALSE]
    tail_row <- as.list(rep("-", ncol(df_clean)))
    names(tail_row) <- names(df_clean)
    tail_row[[1]] <- paste0("... plus ", viscount_fmt_number(rem_n, 0L), " additional assessed settlements (complete ledger in JSON)")
    df_clean <- rbind(df_clean, as.data.frame(tail_row, check.names = FALSE, stringsAsFactors = FALSE))
    rownames(df_clean) <- NULL
    if (!is.null(arg1_caption) && nzchar(arg1_caption) && !grepl("leading|top ", arg1_caption, ignore.case = TRUE)) {
      arg1_caption <- paste0(
        sub("\\.$", "", arg1_caption),
        " (top ", keep_n, " of ", viscount_fmt_number(total_n, 0L), " entries; full dataset archived in chapter JSON)."
      )
    }
  }
  if (!is.null(opts$label)) opts$label <- gsub("_", "-", as.character(opts$label))
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
  extra <- list(...)
  if (is.null(arg1_caption) && !is.null(extra$caption)) arg1_caption <- extra$caption
  if (is.null(arg2_label) && !is.null(extra$label)) arg2_label <- extra$label
  opts <- if (is.list(arg3_options)) arg3_options else list()
  for (nm in setdiff(names(extra), c("caption", "label"))) {
    if (is.null(opts[[nm]])) opts[[nm]] <- extra[[nm]]
  }
  opts$caption <- arg1_caption
  if (!is.null(arg2_label)) opts$label <- gsub("_", "-", as.character(arg2_label))
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


#' Safe ISO-3 lookup that falls back cleanly without throwing subscript-out-of-bounds
#'
#' @param arg0_country Country name string
#' @param arg1_map Optional named character vector of Country -> ISO3
#' @return 3-letter ISO code
viscount_iso3 <- function (arg0_country, arg1_map = NULL) {
  cn <- as.character(arg0_country)
  if (!is.null(arg1_map) && cn %in% names(arg1_map)) {
    val <- unname(arg1_map[[cn]])
    if (!is.null(val) && !is.na(val) && nzchar(val)) return(val)
  }
  canon <- c(
    "Angola" = "AGO", "Benin" = "BEN", "Botswana" = "BWA", "British Indian Ocean Territory" = "IOT",
    "Burkina Faso" = "BFA", "Burundi" = "BDI", "Cabo Verde" = "CPV", "Cameroon" = "CMR",
    "Central African Republic" = "CAF", "Chad" = "TCD", "Comoros" = "COM",
    "Democratic Republic of the Congo" = "COD", "Djibouti" = "DJI", "Equatorial Guinea" = "GNQ",
    "Eritrea" = "ERI", "Ethiopia" = "ETH", "French Southern and Antarctic Lands" = "ATF",
    "Gabon" = "GAB", "Gambia" = "GMB", "Ghana" = "GHA", "Guinea" = "GIN", "Guinea-Bissau" = "GNB",
    "Ivory Coast" = "CIV", "Kenya" = "KEN", "Lesotho" = "LSO", "Liberia" = "LBR",
    "Madagascar" = "MDG", "Malawi" = "MWI", "Mali" = "MLI", "Mauritania" = "MRT",
    "Mauritius" = "MUS", "Mayotte" = "MYT", "Mozambique" = "MOZ", "Namibia" = "NAM",
    "Niger" = "NER", "Nigeria" = "NGA", "Republic of the Congo" = "COG", "Reunion" = "REU",
    "Rwanda" = "RWA", "Saint Helena" = "SHN", "Sao Tome and Principe" = "STP", "Senegal" = "SEN",
    "Seychelles" = "SYC", "Sierra Leone" = "SLE", "Somalia" = "SOM", "Somaliland" = "SML",
    "South Africa" = "ZAF", "South Sudan" = "SSD", "Sudan" = "SDN", "Togo" = "TGO",
    "Uganda" = "UGA", "United Republic of Tanzania" = "TZA", "Zambia" = "ZMB",
    "Zimbabwe" = "ZWE", "eSwatini" = "SWZ"
  )
  if (cn %in% names(canon)) return(unname(canon[[cn]]))
  toupper(substr(gsub("[^A-Za-z]", "", cn), 1L, 3L))
}


#' Dynamically assigns every settlement entry to a chapter sub-region ID using
#' an optional legacy key lookup plus the chapter areal mask PNG (with -5:5 search
#' and nearest-assigned fallback so newly enriched settlements never throw out-of-bounds).
#'
#' @param arg0_entries List of settlement entries with `$key` and `$coords`
#' @param arg1_summary_cache Parsed `<stem>_summary_cache.json` list containing `$subregions`
#' @param arg2_mask_png Path to `<stem>_areal_mask.png`
#' @param arg3_legacy_lookup Optional named character vector `key -> subregion_id`
#' @return Named character vector `key -> subregion_id` covering all entries
viscount_resolve_subregion_keys <- function (arg0_entries, arg1_summary_cache, arg2_mask_png, arg3_legacy_lookup = NULL) {
  sub_list <- arg1_summary_cache$subregions
  sub_ids <- vapply(sub_list, function (x) as.character(x$id), character(1))
  all_keys <- vapply(arg0_entries, function (e) as.character(e$key), character(1))
  out <- setNames(rep(NA_character_, length(all_keys)), all_keys)

  if (!is.null(arg3_legacy_lookup) && length(arg3_legacy_lookup) > 0L) {
    hits <- intersect(all_keys, names(arg3_legacy_lookup))
    if (length(hits) > 0L) {
      vals <- unname(arg3_legacy_lookup[hits])
      valid_v <- !is.na(vals) & nzchar(vals)
      out[hits[valid_v]] <- vals[valid_v]
    }
  }

  need_idx <- which(is.na(out))
  if (length(need_idx) > 0L && requireNamespace("png", quietly = TRUE) && file.exists(arg2_mask_png)) {
    mask_img <- png::readPNG(arg2_mask_png)
    h_px <- dim(mask_img)[1]
    w_px <- dim(mask_img)[2]
    rgb_keys <- vapply(sub_list, function (sr) paste(as.integer(sr$rgb), collapse = "_"), character(1))
    rgb_map <- as.list(setNames(sub_ids, rgb_keys))
    for (i in need_idx) {
      e <- arg0_entries[[i]]
      lat <- as.numeric(e$coords[[1]])
      lon <- as.numeric(e$coords[[2]])
      r_idx <- min(max(as.integer(floor((90 - lat) * h_px / 180)) + 1L, 1L), h_px)
      c_idx <- min(max(as.integer(floor((lon + 180) * w_px / 360)) + 1L, 1L), w_px)
      px_key <- paste(
        as.integer(round(mask_img[r_idx, c_idx, 1] * 255)),
        as.integer(round(mask_img[r_idx, c_idx, 2] * 255)),
        as.integer(round(mask_img[r_idx, c_idx, 3] * 255)),
        sep = "_"
      )
      sid <- rgb_map[[px_key]]
      if (is.null(sid) || is.na(sid)) {
        best_d <- 1e9
        for (dr in -5:5) {
          for (dc in -5:5) {
            rr <- min(max(r_idx + dr, 1L), h_px)
            cc <- min(max(c_idx + dc, 1L), w_px)
            p2 <- paste(
              as.integer(round(mask_img[rr, cc, 1] * 255)),
              as.integer(round(mask_img[rr, cc, 2] * 255)),
              as.integer(round(mask_img[rr, cc, 3] * 255)),
              sep = "_"
            )
            cand <- rgb_map[[p2]]
            if (!is.null(cand) && !is.na(cand)) {
              d <- dr * dr + dc * dc
              if (d < best_d) {
                best_d <- d
                sid <- cand
              }
            }
          }
        }
      }
      if (!is.null(sid) && !is.na(sid)) out[[i]] <- sid
    }
  }

  # Nearest-neighbour geographic fallback for any remaining offshore edge point
  still_na <- which(is.na(out))
  if (length(still_na) > 0L) {
    ok_idx <- which(!is.na(out))
    if (length(ok_idx) > 0L) {
      ok_lats <- vapply(arg0_entries[ok_idx], function (e) as.numeric(e$coords[[1]]), numeric(1))
      ok_lons <- vapply(arg0_entries[ok_idx], function (e) as.numeric(e$coords[[2]]), numeric(1))
      ok_sids <- unname(out[ok_idx])
      for (i in still_na) {
        lat <- as.numeric(arg0_entries[[i]]$coords[[1]])
        lon <- as.numeric(arg0_entries[[i]]$coords[[2]])
        d2 <- (ok_lats - lat)^2 + (ok_lons - lon)^2
        out[[i]] <- ok_sids[which.min(d2)]
      }
    } else {
      out[still_na] <- sub_ids[1L]
    }
  }
  out
}
