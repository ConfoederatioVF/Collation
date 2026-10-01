# ==============================================================================
# Contemporary Demographic Transition (CDT) Validation Plotter (2x2 Dashboard)
# ==============================================================================
# UPDATED: Increased vertical margins to prevent header cutoff.
# Normalized residuals to median relative country error.
# FIXED: Added coord_cartesian(clip = 'off') to prevent label cutoff.
# ==============================================================================

# 1. Package Management & Setup ------------------------------------------------
required_packages <- c("jsonlite", "ggplot2", "patchwork", "scales", "dplyr")

for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    message(sprintf("Installing required package: %s ...", pkg))
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
  library(pkg, character.only = TRUE)
}

# Determine project directories
get_project_dir <- function () {
  if (requireNamespace("rstudioapi", quietly = TRUE) && rstudioapi::isAvailable()) {
    doc_path <- tryCatch(rstudioapi::getActiveDocumentContext()$path, error = function(e) "")
    if (nzchar(doc_path)) return(normalizePath(file.path(dirname(doc_path), "..")))
  }
  wd <- getwd()
  if (file.exists(file.path(wd, "tests", "validation_age_sex_cdt.json"))) return(wd)
  return(wd)
}

project_dir <- get_project_dir()
tests_dir   <- file.path(project_dir, "tests")

as_json_path <- file.path(tests_dir, "validation_age_sex_cdt.json")
bd_json_path <- file.path(tests_dir, "validation_births_deaths_cdt.json")

if (!file.exists(as_json_path) || !file.exists(bd_json_path)) {
  stop("Validation JSON files not found. Please run validation tests first.")
}

# 2. Data Ingestion & Transformation -------------------------------------------
message("Ingesting validation datasets...")
as_root <- jsonlite::fromJSON(as_json_path)
bd_root <- jsonlite::fromJSON(bd_json_path)

# --- 2A. Age/Sex Dataset (Left Column) ---
as_data_list <- list()
for (yr in names(as_root$per_country)) {
  yr_obj <- as_root$per_country[[yr]]
  for (iso in names(yr_obj)) {
    item <- yr_obj[[iso]]
    as_data_list[[length(as_data_list) + 1]] <- data.frame(
      year = as.numeric(yr), iso3 = iso,
      raw_r2 = if (!is.null(item$raw_mnl$r2_country)) as.numeric(item$raw_mnl$r2_country) else NA,
      clamped_r2 = if (!is.null(item$clamped$r2_country)) as.numeric(item$clamped$r2_country) else NA
    )
  }
}
df_age_sex <- do.call(rbind, as_data_list)
df_as_summary <- data.frame(
  year = as.numeric(as_root$summary_by_epoch$year),
  raw_geomean = as.numeric(as_root$summary_by_epoch$raw_mnl$geomean_r2),
  clamped_geomean = as.numeric(as_root$summary_by_epoch$clamped$geomean_r2)
)

# --- 2B. Births & Deaths Dataset (Right Column: Normalised) ---
bd_data_list <- list()
for (yr in names(bd_root$per_country)) {
  yr_obj <- bd_root$per_country[[yr]]
  for (iso in names(yr_obj)) {
    item <- yr_obj[[iso]]
    b_emp <- if(!is.null(item$empirical_births)) as.numeric(item$empirical_births) else 0
    d_emp <- if(!is.null(item$empirical_deaths)) as.numeric(item$empirical_deaths) else 0
    
    # Calculate relative error for the country: (Proxy - Empirical) / Empirical
    b_err <- if(b_emp > 0) as.numeric(item$diff_births) / b_emp else NA
    d_err <- if(d_emp > 0) as.numeric(item$diff_deaths) / d_emp else NA
    
    bd_data_list[[length(bd_data_list) + 1]] <- data.frame(
      year = as.numeric(yr), iso3 = iso,
      birth_err_pct = b_err, death_err_pct = d_err
    )
  }
}
df_bd <- do.call(rbind, bd_data_list)

# Normalize Trend to represent Median Country Deviation
df_bd_summary <- df_bd %>%
  group_by(year) %>%
  summarise(
    median_birth_err = median(birth_err_pct, na.rm = TRUE),
    median_death_err = median(death_err_pct, na.rm = TRUE),
    .groups = "drop"
  )

# 3. Theme & Aesthetics --------------------------------------------------------
cdt_theme <- theme_minimal(base_size = 12) +
  theme(
    plot.title       = element_text(face = "bold", size = 13, colour = "#1E293B", margin = margin(b = 4)),
    plot.subtitle    = element_text(size = 10, colour = "#64748B", margin = margin(b = 20)),
    axis.title       = element_text(face = "bold", size = 10.5, colour = "#334155"),
    panel.grid.major = element_line(colour = "#E2E8F0", linewidth = 0.5),
    panel.background = element_rect(fill = "#FAFAFA", colour = NA),
    plot.background  = element_rect(fill = "#FFFFFF", colour = NA),
    plot.margin      = margin(t = 15, r = 15, b = 15, l = 15) # Added margin to safely house unclipped text
  )

# 4. Construct Subplots -------------------------------------------------------

p1_raw <- ggplot() +
  geom_point(data = df_age_sex, aes(x = year, y = raw_r2), colour = "#3B82F6", alpha = 0.4, position = position_jitter(width=0.8, seed=42)) +
  geom_line(data = df_as_summary, aes(x = year, y = raw_geomean), colour = "#3B82F6", linewidth = 1.2) +
  geom_label(data = df_as_summary, aes(x = year, y = raw_geomean, label = sprintf("%.1f%%", raw_geomean*100)), colour="black", size=3, fontface="bold", vjust=-0.7, label.size=0) +
  scale_y_continuous(labels = percent_format(), limits = c(0, 1.05)) +
  coord_cartesian(clip = "off") + # Fixes vertical clipping
  labs(title = "Multinomial Logit, R^2", x = "Year", y = "R²") + cdt_theme

p3_births <- ggplot() +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "#475569") +
  geom_point(data = df_bd, aes(x = year, y = birth_err_pct), colour = "#F59E0B", alpha = 0.4, position = position_jitter(width=0.8, seed=42)) +
  geom_line(data = df_bd_summary, aes(x = year, y = median_birth_err), colour = "#F59E0B", linewidth = 1.2) +
  geom_label(data = df_bd_summary, aes(x = year, y = median_birth_err, label = sprintf("%+.1f%%", median_birth_err*100)), colour="black", size=3, fontface="bold", vjust=-0.7, label.size=0) +
  scale_y_continuous(labels = percent_format(), limits = c(-0.6, 0.6), oob = scales::squish) +
  coord_cartesian(clip = "off") + # Fixes vertical clipping
  labs(title = "Births Relative Error (%)", subtitle = "Median Country Deviation", x = "Year", y = "% Difference") + cdt_theme

p2_clamped <- ggplot() +
  geom_point(data = df_age_sex, aes(x = year, y = clamped_r2), colour = "#10B981", alpha = 0.4, position = position_jitter(width=0.8, seed=42)) +
  geom_line(data = df_as_summary, aes(x = year, y = clamped_geomean), colour = "#10B981", linewidth = 1.2) +
  geom_label(data = df_as_summary, aes(x = year, y = clamped_geomean, label = sprintf("%.1f%%", clamped_geomean*100)), colour="black", size=3, fontface="bold", vjust=-0.7, label.size=0) +
  scale_y_continuous(labels = percent_format(), limits = c(0, 1.05)) +
  coord_cartesian(clip = "off") + # Fixes vertical clipping
  labs(title = "MNL Clamping, R^2", subtitle = "PAVA/Whittaker-Henderson (logistic kernel)", x = "Year", y = "R²") + cdt_theme

p4_deaths <- ggplot() +
  geom_hline(yintercept = 0, linetype = "dashed", colour = "#475569") +
  geom_point(data = df_bd, aes(x = year, y = death_err_pct), colour = "#8B5CF6", alpha = 0.4, position = position_jitter(width=0.8, seed=42)) +
  geom_line(data = df_bd_summary, aes(x = year, y = median_death_err), colour = "#8B5CF6", linewidth = 1.2) +
  geom_label(data = df_bd_summary, aes(x = year, y = median_death_err, label = sprintf("%+.1f%%", median_death_err*100)), colour="black", size=3, fontface="bold", vjust=-0.7, label.size=0) +
  scale_y_continuous(labels = percent_format(), limits = c(-0.6, 0.6), oob = scales::squish) +
  coord_cartesian(clip = "off") + # Fixes vertical clipping
  labs(title = "Deaths Relative Error (%)", subtitle = "Median Country Deviation", x = "Year", y = "% Difference") + cdt_theme

# 5. Assemble Dashboard with Increased Margins ---------------------------------
# We increase the plot.margin top (t) and subtitle bottom (b) to ensure text 
# is not cut off by the device boundaries or the grid itself.
cdt_2x2_dashboard <- (p1_raw | p3_births) / (p2_clamped | p4_deaths) +
  plot_annotation(
    title    = "Velkscala 1.0: CDT Proxy vs. CDT Empirical",
    subtitle = "Out-of-sample testing | Age/Sex: 69,2% Acc. | Births: 83,1% Acc. | Deaths: 78,9% Acc.",
    caption  = "CDT: Contemporary Demographic Transition. Data: HMD, UNWPP, Niva et al. (2023); Velkscala 1.0 (2026)\nAccuracy rates reflect R^2 and 1 - MAPE for age/sex vs. births/deaths respectively.\n\nProxy models are discarded after 1950AD in final composites; UN data is used by Velkscala 1.0 after that period.",
    theme    = theme(
      plot.title    = element_text(face = "bold", size = 22, margin = margin(t = 20, b = 10)),
      plot.subtitle = element_text(size = 15, colour = "#64748B", margin = margin(b = 40)),
      plot.caption  = element_text(size = 11, colour = "#64748B", margin = margin(t = 15)),
      plot.margin   = margin(t = 15, r = 25, b = 20, l = 15) # Broad margins for the assembly
    )
  )

# 6. Export Visualisation -----------------------------------------------------
out_path <- file.path(tests_dir, "cdt_proxy_vs_empirical.png")
ggsave(out_path, plot = cdt_2x2_dashboard, width = 16, height = 10, dpi = 200)
message(sprintf("✔ Final dashboard saved to: %s", out_path))
print(cdt_2x2_dashboard)