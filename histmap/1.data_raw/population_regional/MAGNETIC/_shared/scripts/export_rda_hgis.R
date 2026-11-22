# Converts downloaded .rda/.rds European Historical GIS & census datasets into GeoJSON/CSV
library(sf)
library(jsonlite)

raw_dir <- "f:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_regional/MAGNETIC/_shared/subadmin_hgis/raw_sources"
parsed_dir <- "f:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_regional/MAGNETIC/_shared/subadmin_hgis/parsed"
dir.create(parsed_dir, showWarnings = FALSE, recursive = TRUE)

cat("=== 1. France SGF (1801-1925) ===\n")
tryCatch({
  geo_fr <- readRDS(file.path(raw_dir, "sgf_france/geo_DEP_SGF_histo.rds"))
  cat("geo_DEP_SGF_histo class:", paste(class(geo_fr), collapse=","), "nrow:", nrow(geo_fr), "\n")
  cat("geo cols:", paste(names(geo_fr), collapse=", "), "\n")
  if (inherits(geo_fr, "sf")) {
    geo_fr_wgs <- st_transform(geo_fr, 4326)
    out_gj <- file.path(parsed_dir, "sgf_france_dep_histo.geojson")
    if (file.exists(out_gj)) file.remove(out_gj)
    st_write(geo_fr_wgs, out_gj, driver = "GeoJSON", quiet = TRUE)
    cat("Wrote sgf_france_dep_histo.geojson (", nrow(geo_fr_wgs), " features)\n")
  }
}, error = function(e) cat("SGF geo err:", conditionMessage(e), "\n"))

tryCatch({
  e1 <- new.env()
  load(file.path(raw_dir, "sgf_france/indicateurs_SGF.rda"), envir = e1)
  cat("indicateurs_SGF objs:", paste(ls(e1), collapse=", "), "\n")
  ind <- get(ls(e1)[1], envir = e1)
  cat("ind cols:", paste(names(ind), collapse=", "), "nrow:", nrow(ind), "\n")
  # Filter population indicators
  pop_idx <- grep("pop|total|habit", paste(ind[[1]], ind[[2]], ind[[3]]), ignore.case = TRUE)
  if (length(pop_idx) > 0) {
    print(head(ind[pop_idx, ], 20))
  } else {
    print(head(ind, 20))
  }
  write.csv(ind, file.path(parsed_dir, "sgf_france_indicateurs.csv"), row.names = FALSE)
}, error = function(e) cat("SGF ind err:", conditionMessage(e), "\n"))

tryCatch({
  e2 <- new.env()
  load(file.path(raw_dir, "sgf_france/data_SGF.rda"), envir = e2)
  cat("data_SGF objs:", paste(ls(e2), collapse=", "), "\n")
  ds <- get(ls(e2)[1], envir = e2)
  cat("data_SGF cols:", paste(names(ds), collapse=", "), "nrow:", nrow(ds), "\n")
  print(head(ds, 5))
  # Save population-related rows (check column names dynamically)
  if ("IND" %in% names(ds) || "codvar" %in% names(ds)) {
    vcol <- if ("IND" %in% names(ds)) "IND" else "codvar"
    uvals <- unique(ds[[vcol]])
    cat("Sample IND values:", paste(head(uvals, 30), collapse=", "), "\n")
  }
}, error = function(e) cat("SGF data err:", conditionMessage(e), "\n"))

cat("\n=== 2. Spain mapSpainHist ===\n")
tryCatch({
  es <- new.env()
  load(file.path(raw_dir, "spain_hist/censos.rda"), envir = es)
  load(file.path(raw_dir, "spain_hist/unitats.rda"), envir = es)
  cat("Spain objs:", paste(ls(es), collapse=", "), "\n")
  for (nm in ls(es)) {
    obj <- get(nm, envir = es)
    cat(" ", nm, "class:", paste(class(obj), collapse=","), "nrow:", nrow(obj), "cols:", paste(names(obj), collapse=", "), "\n")
    write.csv(obj, file.path(parsed_dir, paste0("spain_hist_", nm, ".csv")), row.names = FALSE)
  }
}, error = function(e) cat("Spain err:", conditionMessage(e), "\n"))

cat("\n=== 3. Sweden swehist ===\n")
tryCatch({
  se <- new.env()
  load(file.path(raw_dir, "sweden_hist/boundaries.rda"), envir = se)
  load(file.path(raw_dir, "sweden_hist/sweden.rda"), envir = se)
  load(file.path(raw_dir, "sweden_hist/hist_town.rda"), envir = se)
  cat("Sweden objs:", paste(ls(se), collapse=", "), "\n")
  for (nm in ls(se)) {
    obj <- get(nm, envir = se)
    cat(" ", nm, "class:", paste(class(obj), collapse=","), "nrow:", if (is.data.frame(obj)) nrow(obj) else length(obj), "cols:", paste(names(obj), collapse=", "), "\n")
    if (inherits(obj, "sf")) {
      cat("   CRS:", st_crs(obj)$input, "\n")
      if ("type" %in% names(obj)) cat("   types:", paste(unique(obj$type), collapse=", "), "\n")
    } else if (is.data.frame(obj)) {
      write.csv(obj, file.path(parsed_dir, paste0("sweden_hist_", nm, ".csv")), row.names = FALSE)
    }
  }
}, error = function(e) cat("Sweden err:", conditionMessage(e), "\n"))
