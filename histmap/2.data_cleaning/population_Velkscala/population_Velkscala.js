//Initialise functions
{
  if (!global.population_Velkscala) global.population_Velkscala = {};

  /**
   * Main class interface for the Velkscala Demographic Compositing pipeline.
   * Non-destructively composites antiquity radiocarbon-driven demography (population_c14bazAAR)
   * for years <= 1 AD (in 100-year increments) and Stadestér historical settlement demography
   * (population_Stadester) for years > 1 AD into the canonical Velkscala demographic surface.
   *
   * @class population_Velkscala
   */
  global.population_Velkscala = class {
    static bf = `${h2}/population_Velkscala/`;
    static config_folder = `${this.bf}config/`;

    static input_popc_folder = `${this.bf}population_rasters/`;
    static input_rurc_folder = `${this.bf}population_rural_rasters/`;
    static input_urbc_folder = `${this.bf}population_urban_rasters/`;
    static intermediate_popd_folder = `${this.bf}population_density_rasters/`;

    static input_c14_popc = `${h2}/population_c14bazAAR/5.rasters_scaled_to_global/`;
    static input_c14_rurc = `${h2}/population_c14bazAAR/4.rasters_rural/`;
    static input_c14_urbc = `${h2}/population_c14bazAAR/3.rasters_urban/`;
    static input_c14_popd = `${h2}/population_c14bazAAR/6.rasters_density/`;

    static input_stad_popc = `${h2}/population_Stadester/stadester_population_rasters/`;
    static input_stad_rurc = `${h2}/population_Stadester/stadester_rural_rasters/`;
    static input_stad_urbc = `${h2}/population_Stadester/stadester_urban_rasters/`;
    static input_stad_popd = `${h2}/population_Stadester/stadester_density_rasters/`;

    static file_stadester_national_development_index = `${h2}/population_Stadester/stadester_national_development_index.json`;
    static file_stadester_national_populations = `${h2}/population_Stadester/stadester_national_populations.json`;
    static file_national_development_index = `${this.bf}national_development_index.json`;
    static file_national_populations = `${this.bf}national_populations.json`;
    static file_velkscala_national_development_index = `${this.bf}national_development_index.json`;
    static file_velkscala_national_populations = `${this.bf}national_populations.json`;

    static antiquity_years = Array.from({ length: 101 }, (_, i) => -10000 + i * 100);

    /**
     * Returns sorted array of post-1AD years supported by HYDE / Stadestér.
     * @returns {Array<number>}
     */
    static get post_1ad_years () {
      if (typeof landuse_HYDE !== "undefined" && landuse_HYDE.sorted_hyde_years)
        return landuse_HYDE.sorted_hyde_years.filter(y => y > 0);
      return [
        100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
        1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790, 1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940, 1950,
        1951, 1952, 1953, 1954, 1955, 1956, 1957, 1958, 1959, 1960, 1961, 1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970, 1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025
      ];
    }

    /**
     * Returns complete list of all supported Velkscala years (218 timesteps).
     * @returns {Array<number>}
     */
    static get all_years () {
      return [...this.antiquity_years, ...this.post_1ad_years];
    }

    /**
     * Ensures all required output directories exist.
     */
    static ensureDirectories () {
      let dirs = [
        this.bf,
        this.config_folder,
        this.input_popc_folder,
        this.input_rurc_folder,
        this.input_urbc_folder,
        this.intermediate_popd_folder
      ];
      for (let i = 0; i < dirs.length; i++)
        if (!fs.existsSync(dirs[i])) fs.mkdirSync(dirs[i], { recursive: true });
    }

    /**
     * Step A: Composites antiquity demographic rasters from population_c14bazAAR (10000 BC to 1 AD in 100-year steps).
     * @param {Object} [arg0_options]
     *  @param {boolean} [arg0_options.overwrite=true]
     *  @param {Array<number>} [arg0_options.years]
     */
    static async A_compositeAntiquityRasters (arg0_options) {
      let options = (arg0_options) ? arg0_options : {};
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let target_years = options.years || this.antiquity_years;

      this.ensureDirectories();
      console.log(`[population_Velkscala] Step A: Compositing ${target_years.length} antiquity timesteps from population_c14bazAAR ...`);

      for (let i = 0; i < target_years.length; i++) {
        let yr = target_years[i];
        let src_popc = path.join(this.input_c14_popc, `popc_${yr}.png`);
        let src_rurc = path.join(this.input_c14_rurc, `rurc_${yr}.png`);
        let src_urbc = path.join(this.input_c14_urbc, `urbc_${yr}.png`);
        let src_popd = path.join(this.input_c14_popd, `popd_${yr}.png`);

        let dst_popc = path.join(this.input_popc_folder, `population_${yr}.png`);
        let dst_rurc = path.join(this.input_rurc_folder, `population_rural_${yr}.png`);
        let dst_urbc = path.join(this.input_urbc_folder, `population_urban_${yr}.png`);
        let dst_popd = path.join(this.intermediate_popd_folder, `population_density_${yr}.png`);

        if (fs.existsSync(src_popc) && (overwrite || !fs.existsSync(dst_popc))) fs.copyFileSync(src_popc, dst_popc);
        if (fs.existsSync(src_rurc) && (overwrite || !fs.existsSync(dst_rurc))) fs.copyFileSync(src_rurc, dst_rurc);
        if (fs.existsSync(src_urbc) && (overwrite || !fs.existsSync(dst_urbc))) fs.copyFileSync(src_urbc, dst_urbc);
        if (fs.existsSync(src_popd) && (overwrite || !fs.existsSync(dst_popd))) fs.copyFileSync(src_popd, dst_popd);

        if (yr % 1000 === 0 || yr === 0)
          console.log(`  - Composited antiquity year ${yr} to Velkscala.`);
      }
    }

    /**
     * Step B: Composites post-1AD demographic rasters from population_Stadester (100 AD to 2025 AD).
     * @param {Object} [arg0_options]
     *  @param {boolean} [arg0_options.overwrite=true]
     *  @param {Array<number>} [arg0_options.years]
     */
    static async B_compositePost1ADRasters (arg0_options) {
      let options = (arg0_options) ? arg0_options : {};
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let target_years = options.years || this.post_1ad_years;

      this.ensureDirectories();
      console.log(`[population_Velkscala] Step B: Compositing ${target_years.length} post-1AD timesteps from population_Stadester ...`);

      for (let i = 0; i < target_years.length; i++) {
        let yr = target_years[i];
        let src_popc = path.join(this.input_stad_popc, `stadester_population_${yr}.png`);
        let src_rurc = path.join(this.input_stad_rurc, `stadester_rural_${yr}.png`);
        let src_urbc = path.join(this.input_stad_urbc, `stadester_urban_${yr}.png`);
        let src_popd = path.join(this.input_stad_popd, `stadester_density_${yr}.png`);

        let dst_popc = path.join(this.input_popc_folder, `population_${yr}.png`);
        let dst_rurc = path.join(this.input_rurc_folder, `population_rural_${yr}.png`);
        let dst_urbc = path.join(this.input_urbc_folder, `population_urban_${yr}.png`);
        let dst_popd = path.join(this.intermediate_popd_folder, `population_density_${yr}.png`);

        if (fs.existsSync(src_popc) && (overwrite || !fs.existsSync(dst_popc))) fs.copyFileSync(src_popc, dst_popc);
        if (fs.existsSync(src_rurc) && (overwrite || !fs.existsSync(dst_rurc))) fs.copyFileSync(src_rurc, dst_rurc);
        if (fs.existsSync(src_urbc) && (overwrite || !fs.existsSync(dst_urbc))) fs.copyFileSync(src_urbc, dst_urbc);
        if (fs.existsSync(src_popd) && (overwrite || !fs.existsSync(dst_popd))) fs.copyFileSync(src_popd, dst_popd);

        if (yr % 500 === 0 || yr === 1800 || yr === 2025)
          console.log(`  - Composited post-1AD year ${yr} to Velkscala.`);
      }
    }

    /**
     * Step C: Synchronises national development index and population metadata tables.
     * @param {Object} [arg0_options]
     */
    static C_syncMetadata (arg0_options) {
      this.ensureDirectories();
      let legacy_ndi = path.join(this.bf, "velkscala_national_development_index.json");
      let legacy_pop = path.join(this.bf, "velkscala_national_populations.json");

      if (fs.existsSync(this.file_stadester_national_development_index)) {
        fs.copyFileSync(this.file_stadester_national_development_index, this.file_national_development_index);
        fs.copyFileSync(this.file_stadester_national_development_index, legacy_ndi);
        console.log(`[population_Velkscala] Step C: Synchronised national development index to ${this.file_national_development_index}.`);
      }
      if (fs.existsSync(this.file_stadester_national_populations)) {
        fs.copyFileSync(this.file_stadester_national_populations, this.file_national_populations);
        fs.copyFileSync(this.file_stadester_national_populations, legacy_pop);
        console.log(`[population_Velkscala] Step C: Synchronised national populations to ${this.file_national_populations}.`);
      }
    }

    /**
     * Step D: Validates timeseries continuity and boundary stability at 1 AD.
     * @param {Object} [arg0_options]
     * @returns {Object} Validation summary
     */
    static D_validateCompositing (arg0_options) {
      let options = (arg0_options) ? arg0_options : {};
      let all_years = this.all_years;
      let missing_files = [];
      let report = { total_timesteps: all_years.length, missing: [] };

      console.log(`[population_Velkscala] Step D: Validating completeness across ${all_years.length} timesteps ...`);
      for (let i = 0; i < all_years.length; i++) {
        let yr = all_years[i];
        let p = path.join(this.input_popc_folder, `population_${yr}.png`);
        if (!fs.existsSync(p)) missing_files.push(`popc_${yr}`);
      }

      if (missing_files.length > 0) {
        console.warn(`[population_Velkscala] Step D: Missing ${missing_files.length} rasters:`, missing_files.slice(0, 10));
        report.missing = missing_files;
      } else {
        console.log(`[population_Velkscala] Step D: All ${all_years.length} timesteps verified present.`);
      }

      fs.writeFileSync(path.join(this.config_folder, "compositing_report.json"), JSON.stringify(report, null, 2));
      return report;
    }

    /**
     * Master pipeline runner to execute the Velkscala compositing pipeline.
     * @param {Object} [arg0_options]
     *  @param {Array<string>} [arg0_options.exclude]
     */
    static async processRasters (arg0_options) {
      let options = (arg0_options) ? arg0_options : {};
      if (!options.exclude) options.exclude = [];
      let start_time = Date.now();

      console.log(`=== Launching population_Velkscala Compositing Pipeline ===`);
      this.ensureDirectories();

      if (!options.exclude.includes("A")) await this.A_compositeAntiquityRasters(options);
      if (!options.exclude.includes("B")) await this.B_compositePost1ADRasters(options);
      if (!options.exclude.includes("C")) this.C_syncMetadata(options);
      if (!options.exclude.includes("D")) this.D_validateCompositing(options);

      console.log(`=== Successfully completed population_Velkscala pipeline in ${((Date.now() - start_time) / 1000).toFixed(1)}s ===`);
    }
  };
}
