# Extracts clean historical census CSVs & WGS84 GeoJSONs from France SGF and Sweden swehist
library(sf)
library(dplyr)

raw_dir <- "f:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_regional/MAGNETIC/_shared/subadmin_hgis/raw_sources"
parsed_dir <- "f:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_regional/MAGNETIC/_shared/subadmin_hgis/parsed"

cat("=== 1. Extracting France SGF 1801-1925 Department Total Population ===\n")
e_sgf <- new.env()
load(file.path(raw_dir, "sgf_france/data_SGF.rda"), envir = e_sgf)
ds <- e_sgf$data_SGF

# Find total population tables at DEP level
dep_pop <- ds[ds$NIVGEO == "DEP" & grepl("POP", ds$SRC_DATA, ignore.case = TRUE) &
              grepl("population totale|total de la population|population de fait|population légale|^population\\b", ds$VAR_LIB, ignore.case = TRUE) &
              !grepl("urbaine|rurale|masculin|féminin|sexe|âge|mariage|naissance|décès|étranger|ménage|maison|électeur|densité|superficie|accroissement", ds$VAR_LIB, ignore.case = TRUE), ]

cat("Matched DEP pop rows:", nrow(dep_pop), "\n")
if (nrow(dep_pop) > 0) {
  tab <- dep_pop %>% group_by(ANNEE_DONNEE, SRC_DATA, VAR_COD, VAR_LIB) %>% summarise(n_dep = n(), sum_val = sum(as.numeric(VAL), na.rm=TRUE), .groups="drop")
  tab_good <- tab[tab$n_dep >= 70 & tab$sum_val > 20e6 & tab$sum_val < 50e6, ]
  print(as.data.frame(tab_good), max = 200)
  # Keep clean rows
  good_keys <- paste(tab_good$ANNEE_DONNEE, tab_good$SRC_DATA, tab_good$VAR_COD)
  keep <- dep_pop[paste(dep_pop$ANNEE_DONNEE, dep_pop$SRC_DATA, dep_pop$VAR_COD) %in% good_keys, ]
  write.csv(keep, file.path(parsed_dir, "sgf_france_dep_pop_1801_1925.csv"), row.names = FALSE)
  cat("Wrote sgf_france_dep_pop_1801_1925.csv (", nrow(keep), " rows)\n")
} else {
  # Fallback: print unique SRC_DATA for DEP
  cat("DEP SRC_DATA prefixes:", paste(head(unique(ds$SRC_DATA[ds$NIVGEO == "DEP"]), 40), collapse=", "), "\n")
}

cat("\n=== 2. Extracting Sweden swehist Historical Counties (1750-1960) ===\n")
e_se <- new.env()
load(file.path(raw_dir, "sweden_hist/boundaries.rda"), envir = e_se)
b <- e_se$boundaries
counties <- b[b$type == "County", ]
cat("Total County polygons:", nrow(counties), "start range:", min(counties$start, na.rm=TRUE), "..", max(counties$end, na.rm=TRUE), "\n")
counties_wgs <- st_transform(counties, 4326)
for (yr in c(1750, 1800, 1850, 1880, 1910, 1930, 1960)) {
  sub <- counties_wgs[counties_wgs$start <= yr & counties_wgs$end >= yr, ]
  out_p <- file.path(parsed_dir, paste0("sweden_counties_", yr, ".geojson"))
  if (file.exists(out_p)) file.remove(out_p)
  if (nrow(sub) > 0) {
    st_write(sub, out_p, driver = "GeoJSON", quiet = TRUE)
    cat("  Sweden", yr, ":", nrow(sub), "counties\n")
  }
}
