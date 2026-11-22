# Extract 1801-1866 France SGF department population tables from data_SGF.rda
library(dplyr)
raw_dir <- "f:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_regional/MAGNETIC/_shared/subadmin_hgis/raw_sources"
parsed_dir <- "f:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_regional/MAGNETIC/_shared/subadmin_hgis/parsed"

e <- new.env()
load(file.path(raw_dir, "sgf_france/data_SGF.rda"), envir = e)
ds <- e$data_SGF
sub <- ds[ds$NIVGEO == "DEP" & as.numeric(ds$ANNEE_DONNEE) <= 1876, ]
tab <- sub %>%
  group_by(ANNEE_DONNEE, SRC_DATA, VAR_COD, VAR_LIB) %>%
  summarise(n_dep = n(), sum_val = sum(as.numeric(VAL), na.rm=TRUE), .groups="drop")
# Real France total pop in 1801-1876 is between 25M and 42M!
good <- tab[tab$n_dep >= 80 & tab$sum_val >= 25e6 & tab$sum_val <= 42e6, ]
good <- good[order(as.numeric(good$ANNEE_DONNEE)), ]
print(as.data.frame(good), max = 200)
keys <- paste(good$ANNEE_DONNEE, good$SRC_DATA, good$VAR_COD)
keep <- sub[paste(sub$ANNEE_DONNEE, sub$SRC_DATA, sub$VAR_COD) %in% keys, ]
write.csv(keep, file.path(parsed_dir, "sgf_france_dep_pop_1801_1876.csv"), row.names = FALSE)
cat("Wrote sgf_france_dep_pop_1801_1876.csv (", nrow(keep), " rows)\n")
