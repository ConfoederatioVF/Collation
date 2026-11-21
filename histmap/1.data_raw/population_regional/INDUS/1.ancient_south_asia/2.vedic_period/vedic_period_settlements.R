## ----setup, include=FALSE-----------------------------------------------------
knitr::opts_chunk$set(echo = FALSE, message = FALSE, warning = FALSE, fig.align = "center", out.width = "100%")
source("../../_shared/template/viscount_rmd_helpers.R")
library(jsonlite)

read_json_file <- function (arg0_path) {
  txt <- readLines(arg0_path, warn = FALSE, encoding = "UTF-8")
  fromJSON(paste(txt, collapse = "\n"), simplifyVector = FALSE)
}

mod_data <- read_json_file("vedic_period.json5")
set_data <- read_json_file("vedic_period_settlements.json")
led_data <- read_json_file("vedic_period_source_ledger.json5")

clean_text <- function (arg0_s) {
  s <- gsub("&", "and", as.character(arg0_s), fixed = TRUE)
  s <- gsub("_", " ", s, fixed = TRUE)
  trimws(s)
}

fmt_yr <- function (arg0_y) {
  y <- as.numeric(arg0_y)
  if (y < 0) return(paste0(abs(round(y)), "BC"))
  return(paste0(round(y), "AD"))
}

fmt_coord <- function (arg0_coords) {
  lat <- as.numeric(arg0_coords[[1]])
  lon <- as.numeric(arg0_coords[[2]])
  lat_s <- paste0(viscount_fmt_number(abs(lat), 2L), if (lat >= 0) " N" else " S")
  lon_s <- paste0(viscount_fmt_number(abs(lon), 2L), if (lon >= 0) " E" else " W")
  paste0(lat_s, ", ", lon_s)
}

fmt_pop_series <- function (arg0_pop) {
  yrs <- as.numeric(names(arg0_pop))
  ord <- order(yrs)
  yrs <- yrs[ord]
  vals <- as.numeric(unlist(arg0_pop))[ord]
  if (length(yrs) > 5L) {
    keep <- unique(round(seq(1, length(yrs), length.out = 5L)))
    yrs <- yrs[keep]
    vals <- vals[keep]
  }
  parts <- vapply(seq_along(yrs), function (i) {
    paste0(fmt_yr(yrs[i]), ": ", viscount_fmt_pop(vals[i]))
  }, character(1))
  paste(parts, collapse = "; ")
}

set_list <- unname(set_data)
sett_peaks <- vapply(set_list, function (s) {
  if (is.null(s$population) || length(s$population) == 0) return(0)
  max(as.numeric(unlist(s$population)))
}, numeric(1))

reg_short <- list(
  ved_sapta_sindhu = "Sapta Sindhu and Punjab",
  ved_kurukshetra_doab = "Kurukshetra and Upper Doab",
  ved_kosala_videha_magadha = "Middle Ganga and Magadha",
  ved_malwa_rajasthan_gujarat = "Malwa and Western Periphery"
)

reg_json_to_key <- list(
  "Sapta Sindhu & Gandhara" = "ved_sapta_sindhu",
  "Kurukshetra" = "ved_kurukshetra_doab",
  "Middle Ganga & Kosala & Videha" = "ved_kosala_videha_magadha",
  "Malwa & Matsya & Rajasthan" = "ved_malwa_rajasthan_gujarat"
)

norm_reg_key <- function (arg0_reg) {
  if (!is.null(reg_json_to_key[[arg0_reg]])) return(reg_json_to_key[[arg0_reg]])
  arg0_reg
}

exc_list <- Filter(function (c) identical(c$status, "excluded") || identical(c$included, FALSE), led_data$candidates)


## ----tbl-summary, results='asis'----------------------------------------------
sum_rows <- lapply(names(mod_data$regions), function (rk) {
  sub_sets <- Filter(function (s) identical(norm_reg_key(s$region), rk), set_list)
  peaks <- if (length(sub_sets) > 0) vapply(sub_sets, function (s) max(as.numeric(unlist(s$population))), numeric(1)) else 0
  top_name <- if (length(sub_sets) > 0) clean_text(sub_sets[[which.max(peaks)]]$name) else "-"
  top_pk <- if (length(sub_sets) > 0) max(peaks) else 0
  data.frame(
    SubRegion = reg_short[[rk]],
    Sites = viscount_fmt_number(length(sub_sets), 0L),
    Share = paste0(viscount_fmt_number(length(sub_sets) / length(set_list) * 100, 1L), "%"),
    PeakSum = viscount_fmt_pop(sum(peaks)),
    LeadingSite = paste0(top_name, " (", viscount_fmt_pop(top_pk), ")"),
    stringsAsFactors = FALSE
  )
})
df_sum <- do.call(rbind, sum_rows)
df_tot_sum <- data.frame(
  SubRegion = "Regional Total",
  Sites = viscount_fmt_number(length(set_list), 0L),
  Share = "100%",
  PeakSum = viscount_fmt_pop(sum(sett_peaks)),
  LeadingSite = paste0(clean_text(set_list[[which.max(sett_peaks)]]$name), " (", viscount_fmt_pop(max(sett_peaks)), ")"),
  stringsAsFactors = FALSE
)
df_sum <- rbind(df_sum, df_tot_sum)
viscount_table(
  df_sum,
  "Sub-regional distribution of 5.905 catalogued settlements and summed site peaks across Northern and Western South Asia.",
  c("Sub-Region", "Sites", "Site Share", "Sum of Peaks", "Leading Settlement (Peak)"),
  list(label = "tab:summary", font_size = "scriptsize")
)


## ----tbl-gazetteer, results='asis'--------------------------------------------
ord_all <- order(sett_peaks, decreasing = TRUE)
top_45 <- set_list[ord_all[seq_len(min(45L, length(set_list)))]]

gaz_rows <- lapply(top_45, function (s) {
  yrs <- as.numeric(names(s$population))
  y_min <- min(yrs)
  y_max <- max(yrs)
  span_s <- if (y_min == y_max) fmt_yr(y_min) else paste0(fmt_yr(y_min), " - ", fmt_yr(y_max))
  pk <- max(as.numeric(unlist(s$population)))
  p_500 <- if (!is.null(s$population[["-500"]])) as.numeric(s$population[["-500"]]) else "-"
  s_rk <- norm_reg_key(s$region)
  reg_lbl <- if (!is.null(reg_short[[s_rk]])) reg_short[[s_rk]] else clean_text(s$region)
  data.frame(
    Settlement = substr(clean_text(s$name), 1, 26),
    SubRegion = reg_lbl,
    Coordinates = fmt_coord(s$coords),
    Span = span_s,
    Peak = viscount_fmt_pop(pk),
    P500BC = if (is.numeric(p_500)) viscount_fmt_pop(p_500) else "-",
    stringsAsFactors = FALSE
  )
})
df_gaz <- do.call(rbind, gaz_rows)
viscount_table(
  df_gaz,
  "Leading 45 settlements ordered by peak population across Northern and Western South Asia (1500BC to 500BC).",
  c("Settlement Name", "Sub-Region", "Coordinates", "Span", "Peak Pop", "500BC Pop"),
  list(label = "tab:gazetteer", font_size = "scriptsize")
)


## ----tbl-excluded, results='asis'---------------------------------------------
exc_show <- exc_list[seq_len(min(25L, length(exc_list)))]
exc_rows <- lapply(exc_show, function (c) {
  j_txt <- clean_text(c$justification)
  if (nchar(j_txt) > 52) j_txt <- paste0(substr(j_txt, 1, 49), "...")
  data.frame(
    Candidate = substr(clean_text(c$name), 1, 26),
    Territory = clean_text(c$country),
    Reason = clean_text(c$reason),
    Justification = j_txt,
    stringsAsFactors = FALSE
  )
})
df_exc <- do.call(rbind, exc_rows)
viscount_table(
  df_exc,
  "Leading twenty-five excluded candidate sites from the Vedic Period source ledger.",
  c("Candidate Site", "Territory", "Exclusion Category", "Justification"),
  list(label = "tab:excluded", font_size = "scriptsize")
)

