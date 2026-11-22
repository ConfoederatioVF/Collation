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
      let use_direct_viscount_composite = (options.use_gpu !== false && !options.exclude_viscount_antiquity && overwrite && typeof GeoPNG !== "undefined" && GeoPNG.gpu && ((GeoPNG.native && GeoPNG.native.isAvailable()) || GeoPNG.gpu.isAvailable()) && typeof GeoPNG.loadRawRGBAAsync === "function");

      if (use_direct_viscount_composite) {
        console.log(`[population_Velkscala] Step A: Direct pipelined compositing + Viscount overlay over ${target_years.length} antiquity timesteps (skipping redundant 2,4 GB intermediate HDD copy) ...`);
        let overlaid = await this.overlayViscountAntiquityDomains(target_years, { ...options, read_c14_fallback: true });
        if (overlaid) return;
      }

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

      if (!options.exclude_viscount_antiquity)
        await this.overlayViscountAntiquityDomains(target_years, options);
    }

    /**
     * Step A2: Overlays calibrated antiquity rasters (`-10000` to `0 AD`) from active Viscount projects
     * (`rasters_2.scaled_to_regions/popc_*.png`) onto composited Velkscala antiquity rasters using
     * log-linear temporal interpolation between 1000-year anchors and a 16-px cosine outer seam blend.
     * Accelerated on NVIDIA OpenCL via GeoPNG.gpu when available.
     * @alias population_Velkscala.overlayViscountAntiquityDomains
     *
     * @param {Array<number>} arg0_target_years
     * @param {Object} [arg1_options]
     */
    static async overlayViscountAntiquityDomains (arg0_target_years, arg1_options) {
      //Convert from parameters
      let target_years = Array.isArray(arg0_target_years) ? arg0_target_years : this.antiquity_years;
      let options = (arg1_options) ? arg1_options : {};

      //Guard clauses
      if (typeof global.ViscountSubstrataPipeline === "undefined" && typeof require !== "undefined") {
        let viscount_dir = path.resolve(this.bf, "../../3.data_transform/population_Substrata.viscount");

        try {
          require(path.join(viscount_dir, "ViscountSubstrataMosaic.js"));
          require(path.join(viscount_dir, "ViscountSubstrataPipeline.js"));
        } catch (e) {}
      }
      if (typeof global.ViscountSubstrataPipeline === "undefined") return;

      let discovery = global.ViscountSubstrataPipeline.A_discoverActiveViscountContexts(options);

      if (!discovery || !Array.isArray(discovery.contexts) || discovery.contexts.length === 0) return;

      //Declare local instance variables
      let anchor_cache = new Map();
      let avail_anchors = [];
      let height = 2160;
      let land_area_path = (typeof metadata_HYDE !== "undefined" && metadata_HYDE.file_land_area) ?
        metadata_HYDE.file_land_area : path.join(discovery.root_dir, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png");
      let owner_grid = discovery.owner_z_grid;
      let png_cls = (global.pngjs && global.pngjs.PNG) ? global.pngjs.PNG : (global.PNG || require("pngjs").PNG);
      let r2_dir = path.join(discovery.root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions");
      let seam_px = 16;
      let total_px = 4320*2160;
      let viscount_pixels = [];
      let width = 4320;

      //Function body
      let loadFloatGrid = function (arg0_path) {
        if (!fs.existsSync(arg0_path)) return null;
        let png_obj = png_cls.sync.read(fs.readFileSync(arg0_path));
        let dv = new DataView(png_obj.data.buffer, png_obj.data.byteOffset, png_obj.data.byteLength);
        let out = new Float32Array(total_px);

        for (let i = 0; i < total_px; i++) {
          let p4 = i*4;

          if ((png_obj.data[p4] | png_obj.data[p4 + 1] | png_obj.data[p4 + 2] | png_obj.data[p4 + 3]) === 0) continue;
          let v = dv.getFloat32(p4, false);

          out[i] = (Number.isFinite(v) && v > 0) ? v : 0;
        }
        return out;
      };
      let writeFloatGrid = function (arg0_path, arg1_arr) {
        let img = new png_cls({ colorType: 6, height: height, width: width });
        let dv = new DataView(img.data.buffer, img.data.byteOffset, img.data.byteLength);

        for (let i = 0; i < total_px; i++) {
          let v = arg1_arr[i];

          if (v > 0 && Number.isFinite(v)) dv.setFloat32(i*4, v, false);
        }
        fs.writeFileSync(arg0_path, png_cls.sync.write(img, { colorType: 6, deflateLevel: 6 }));
      };
      let getAnchor = function (arg0_yr) {
        if (anchor_cache.has(arg0_yr)) return anchor_cache.get(arg0_yr);
        let grid = loadFloatGrid(path.join(r2_dir, `popc_${arg0_yr}.png`));

        anchor_cache.set(arg0_yr, grid);
        return grid;
      };

      if (fs.existsSync(r2_dir)) {
        let r2_files = fs.readdirSync(r2_dir);

        for (let i = 0; i < r2_files.length; i++) {
          let m = /^popc_(-?\d+)\.png$/.exec(r2_files[i]);

          if (m) {
            let ay = parseInt(m[1], 10);

            if (ay <= 0) avail_anchors.push(ay);
          }
        }
        avail_anchors.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      }
      if (avail_anchors.length === 0) {
        for (let ay = -10000; ay <= 0; ay += 1000) avail_anchors.push(ay);
      }

      let land_area = new Float32Array(total_px);

      if (fs.existsSync(land_area_path)) {
        let la_png = png_cls.sync.read(fs.readFileSync(land_area_path));

        for (let i = 0; i < total_px; i++) {
          let p4 = i*4;

          land_area[i] = ((la_png.data[p4] << 24) | (la_png.data[p4 + 1] << 16) | (la_png.data[p4 + 2] << 8) | la_png.data[p4 + 3]) >>> 0;
        }
      }

      //Build smooth 8-connected Chamfer distance belt along true external sovereign land frontiers (zero 1-px BFS column striping)
      let bfs_dist = new Float32Array(total_px).fill(255.0);
      let ext_seed_pixels = [];
      let seam_pixels = [];

      for (let i = 0; i < total_px; i++) {
        if (!owner_grid || owner_grid[i] <= 0) continue;
        viscount_pixels.push(i);
        let r = Math.floor(i/width);
        let c = i % width;

        for (let dr = -1; dr <= 1; dr++) {
          let nr = r + dr;

          if (nr < 0 || nr >= height) continue;
          for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            let nc = c + dc;

            if (nc < 0 || nc >= width) continue;
            let nb = nr*width + nc;

            if (owner_grid[nb] === 0 && land_area[nb] > 0) {
              if (bfs_dist[nb] > 0) {
                bfs_dist[nb] = 0;
                ext_seed_pixels.push(nb);
              }
              let step_d = (dr !== 0 && dc !== 0) ? 1.414 : 1.0;

              if (step_d < bfs_dist[i]) {
                if (bfs_dist[i] > 200) seam_pixels.push(i);
                bfs_dist[i] = step_d;
              }
            }
          }
        }
      }

      //Multi-pass isotropic Chamfer distance propagation across narrow seam belt (no single-anchor column copying)
      for (let pass = 0; pass < seam_px; pass++) {
        let next_candidates = [];

        for (let s = 0; s < seam_pixels.length; s++) {
          let curr = seam_pixels[s];
          let d_curr = bfs_dist[curr];

          if (d_curr >= seam_px) continue;
          let r = Math.floor(curr/width);
          let c = curr % width;

          for (let dr = -1; dr <= 1; dr++) {
            let nr = r + dr;

            if (nr < 0 || nr >= height) continue;
            for (let dc = -1; dc <= 1; dc++) {
              if (dr === 0 && dc === 0) continue;
              let nc = c + dc;

              if (nc < 0 || nc >= width) continue;
              let nb = nr*width + nc;

              if (!owner_grid || owner_grid[nb] <= 0) continue;
              let nd = d_curr + ((dr !== 0 && dc !== 0) ? 1.414 : 1.0);

              if (nd <= seam_px && nd < bfs_dist[nb] - 1e-3) {
                if (bfs_dist[nb] > 200) next_candidates.push(nb);
                bfs_dist[nb] = nd;
              }
            }
          }
        }
        for (let s = 0; s < next_candidates.length; s++) seam_pixels.push(next_candidates[s]);
        if (next_candidates.length === 0 && pass > 2) break;
      }

      let ext_diff_a = new Float32Array(total_px);
      let ext_diff_b = new Float32Array(total_px);
      let max_cached_anchors = (typeof GeoPNG !== "undefined" && GeoPNG.compute_limits && GeoPNG.compute_limits.ram && GeoPNG.compute_limits.ram.max_cached_rasters) ?
        Math.max(2, Number(GeoPNG.compute_limits.ram.max_cached_rasters)) : 8;
      let use_accel = (options.use_gpu !== false && typeof GeoPNG !== "undefined" && GeoPNG.gpu && ((GeoPNG.native && GeoPNG.native.isAvailable()) || GeoPNG.gpu.isAvailable()) && typeof GeoPNG.loadRawRGBAAsync === "function");

      if (use_accel) {
        if (typeof GeoPNG.applyBackgroundProcessPriority === "function")
          GeoPNG.applyBackgroundProcessPriority();

        let raw_anchor_cache = new Map();
        let raw_anchor_inflight = new Map();
        let getAnchorRaw = async function (arg0_yr) {
          if (raw_anchor_cache.has(arg0_yr)) {
            let val = raw_anchor_cache.get(arg0_yr);
            raw_anchor_cache.delete(arg0_yr);
            raw_anchor_cache.set(arg0_yr, val);
            return val;
          }
          if (raw_anchor_inflight.has(arg0_yr)) return raw_anchor_inflight.get(arg0_yr);
          let loader = (async () => {
            let p = path.join(r2_dir, `popc_${arg0_yr}.png`);
            let loaded = fs.existsSync(p) ? await GeoPNG.loadRawRGBAAsync(p) : null;
            let buf = (loaded && loaded.data) ? loaded.data : null;
            raw_anchor_cache.set(arg0_yr, buf);
            while (raw_anchor_cache.size > max_cached_anchors) {
              let oldest_key = raw_anchor_cache.keys().next().value;
              raw_anchor_cache.delete(oldest_key);
            }
            raw_anchor_inflight.delete(arg0_yr);
            return buf;
          })();
          raw_anchor_inflight.set(arg0_yr, loader);
          return loader;
        };

        let pipeline_conc = (GeoPNG.compute_limits && GeoPNG.compute_limits.cpu && GeoPNG.compute_limits.cpu.pipeline_concurrency) ?
          Number(GeoPNG.compute_limits.cpu.pipeline_concurrency) : 4;
        let read_c14_fallback = Boolean(options.read_c14_fallback);
        let seam_pixels_u32 = Uint32Array.from(seam_pixels);
        let static_key = `velk_${discovery.contexts.length}_${viscount_pixels.length}_${seam_pixels.length}`;
        let viscount_pixels_u32 = Uint32Array.from(viscount_pixels);
        let zero_rgba = Buffer.alloc(total_px*4, 0);
        let antiquity_only = target_years.filter((arg0_yr) => arg0_yr <= 0);

        console.log(`[population_Velkscala] Overlaying ${discovery.contexts.length} Viscount antiquity domains [Accel Pipelined x${pipeline_conc}] (${viscount_pixels.length} px, seam=${seam_pixels.length} px) across ${antiquity_only.length} timesteps...`);

        await GeoPNG.processTimeseriesParallel({
          concurrency: Math.min(options.concurrency || pipeline_conc, pipeline_conc),
          items: antiquity_only,
          name: "Velkscala Antiquity Overlay [Accel]",
          use_workers: false,
          handler: async (yr) => {
            let a0 = avail_anchors[0];
            let a1 = avail_anchors[avail_anchors.length - 1];

            if (yr <= a0) {
              a1 = a0;
            } else if (yr >= a1) {
              a0 = a1;
            } else {
              for (let k = 0; k < avail_anchors.length - 1; k++) {
                if (yr >= avail_anchors[k] && yr <= avail_anchors[k + 1]) {
                  a0 = avail_anchors[k];
                  a1 = avail_anchors[k + 1];
                  break;
                }
              }
            }
            let ga_rgba = await getAnchorRaw(a0);
            let gb_rgba = (a1 !== a0) ? await getAnchorRaw(a1) : ga_rgba;

            let dst_popc = path.join(this.input_popc_folder, `population_${yr}.png`);
            let dst_rurc = path.join(this.input_rurc_folder, `population_rural_${yr}.png`);
            let dst_urbc = path.join(this.input_urbc_folder, `population_urban_${yr}.png`);
            let dst_popd = path.join(this.intermediate_popd_folder, `population_density_${yr}.png`);

            let src_popc = read_c14_fallback ? path.join(this.input_c14_popc, `popc_${yr}.png`) : dst_popc;
            let src_rurc = read_c14_fallback ? path.join(this.input_c14_rurc, `rurc_${yr}.png`) : dst_rurc;
            let src_urbc = read_c14_fallback ? path.join(this.input_c14_urbc, `urbc_${yr}.png`) : dst_urbc;
            let src_popd = read_c14_fallback ? path.join(this.input_c14_popd, `popd_${yr}.png`) : dst_popd;

            if (!ga_rgba || !gb_rgba) {
              if (read_c14_fallback) {
                if (fs.existsSync(src_popc)) fs.copyFileSync(src_popc, dst_popc);
                if (fs.existsSync(src_rurc)) fs.copyFileSync(src_rurc, dst_rurc);
                if (fs.existsSync(src_urbc)) fs.copyFileSync(src_urbc, dst_urbc);
                if (fs.existsSync(src_popd)) fs.copyFileSync(src_popd, dst_popd);
              }
              return;
            }
            if (!fs.existsSync(src_popc)) return;

            let [popc_raw, urbc_raw, rurc_raw, popd_raw] = await Promise.all([
              GeoPNG.loadRawRGBAAsync(src_popc),
              fs.existsSync(src_urbc) ? GeoPNG.loadRawRGBAAsync(src_urbc) : Promise.resolve(null),
              fs.existsSync(src_rurc) ? GeoPNG.loadRawRGBAAsync(src_rurc) : Promise.resolve(null),
              fs.existsSync(src_popd) ? GeoPNG.loadRawRGBAAsync(src_popd) : Promise.resolve(null)
            ]);
            if (!popc_raw || !popc_raw.data) return;

            let frac = (a1 !== a0) ? (yr - a0)/Math.max(1, a1 - a0) : 0;
            let gpu_res = await GeoPNG.gpu.velkscalaAntiquityOverlayRGBA({
              bfs_dist: bfs_dist,
              frac: frac,
              grid_a_rgba: ga_rgba,
              grid_b_rgba: gb_rgba,
              height: height,
              land_area: land_area,
              owner_grid: owner_grid,
              popc_rgba: popc_raw.data,
              popd_rgba: (popd_raw && popd_raw.data) ? popd_raw.data : zero_rgba,
              rurc_rgba: (rurc_raw && rurc_raw.data) ? rurc_raw.data : zero_rgba,
              seam_pixels: seam_pixels_u32,
              seam_px: seam_px,
              static_key: static_key,
              urbc_rgba: (urbc_raw && urbc_raw.data) ? urbc_raw.data : zero_rgba,
              viscount_pixels: viscount_pixels_u32,
              width: width
            });

            if (gpu_res) {
              await Promise.all([
                GeoPNG.saveRawRGBAAsync({ data: gpu_res.urbc_rgba, file_path: dst_urbc, height: height, width: width }),
                GeoPNG.saveRawRGBAAsync({ data: gpu_res.popc_rgba, file_path: dst_popc, height: height, width: width }),
                GeoPNG.saveRawRGBAAsync({ data: gpu_res.rurc_rgba, file_path: dst_rurc, height: height, width: width }),
                GeoPNG.saveRawRGBAAsync({ data: gpu_res.popd_rgba, file_path: dst_popd, height: height, width: width })
              ]);
              gpu_res = null;
            }
          }
        });

        raw_anchor_cache.clear();
        return true;
      }

      console.log(`[population_Velkscala] Overlaying ${discovery.contexts.length} Viscount antiquity domains (${viscount_pixels.length} px, seam=${seam_pixels.length} px) across ${target_years.length} timesteps...`);

      for (let i = 0; i < target_years.length; i++) {
        let yr = target_years[i];

        if (yr > 0) continue;
        let a0 = avail_anchors[0];
        let a1 = avail_anchors[avail_anchors.length - 1];

        if (yr <= a0) {
          a1 = a0;
        } else if (yr >= a1) {
          a0 = a1;
        } else {
          for (let k = 0; k < avail_anchors.length - 1; k++) {
            if (yr >= avail_anchors[k] && yr <= avail_anchors[k + 1]) {
              a0 = avail_anchors[k];
              a1 = avail_anchors[k + 1];
              break;
            }
          }
        }
        let grid_a = getAnchor(a0);
        let grid_b = (a1 !== a0) ? getAnchor(a1) : grid_a;

        if (!grid_a || !grid_b) continue;

        let dst_popc = path.join(this.input_popc_folder, `population_${yr}.png`);
        let dst_rurc = path.join(this.input_rurc_folder, `population_rural_${yr}.png`);
        let dst_urbc = path.join(this.input_urbc_folder, `population_urban_${yr}.png`);
        let dst_popd = path.join(this.intermediate_popd_folder, `population_density_${yr}.png`);
        let popc_arr = loadFloatGrid(dst_popc);
        let urbc_arr = loadFloatGrid(dst_urbc) || new Float32Array(total_px);
        let rurc_arr = loadFloatGrid(dst_rurc) || new Float32Array(total_px);
        let popd_arr = loadFloatGrid(dst_popd) || new Float32Array(total_px);

        if (!popc_arr) continue;

        //Solve smooth 2D harmonic exterior transition field over seam pixels (eliminates single-pixel BFS barcode stripes)
        if (seam_pixels.length > 0) {
          for (let x = 0; x < ext_seed_pixels.length; x++) {
            let ep = ext_seed_pixels[x];

            ext_diff_a[ep] = popc_arr[ep];
            ext_diff_b[ep] = popc_arr[ep];
          }
          for (let x = 0; x < seam_pixels.length; x++) {
            let sp = seam_pixels[x];
            let acc0 = 0;
            let cnt0 = 0;
            let sr = Math.floor(sp/width);
            let sc = sp % width;

            for (let dr = -2; dr <= 2; dr++) {
              let nr = sr + dr;

              if (nr < 0 || nr >= height) continue;
              for (let dc = -2; dc <= 2; dc++) {
                let nc = sc + dc;

                if (nc < 0 || nc >= width) continue;
                let np = nr*width + nc;

                if (owner_grid[np] === 0 && land_area[np] > 0) {
                  acc0 += popc_arr[np];
                  cnt0++;
                }
              }
            }
            let init_v = (cnt0 > 0) ? acc0/cnt0 : 0;

            ext_diff_a[sp] = init_v;
            ext_diff_b[sp] = init_v;
          }

          for (let it = 0; it < seam_px; it++) {
            let src_g = (it % 2 === 0) ? ext_diff_a : ext_diff_b;
            let dst_g = (it % 2 === 0) ? ext_diff_b : ext_diff_a;

            for (let x = 0; x < seam_pixels.length; x++) {
              let sp = seam_pixels[x];
              let r = Math.floor(sp/width);
              let c = sp % width;
              let w_sum = 0;
              let v_sum = 0;
              let nbrs = [
                (r > 0) ? sp - width : -1,
                (r + 1 < height) ? sp + width : -1,
                (c > 0) ? sp - 1 : -1,
                (c + 1 < width) ? sp + 1 : -1
              ];

              for (let y = 0; y < 4; y++) {
                let nb = nbrs[y];

                if (nb < 0) continue;
                if (bfs_dist[nb] <= seam_px && (owner_grid[nb] > 0 || land_area[nb] > 0)) {
                  let wt = (owner_grid[nb] === 0) ? 2.0 : 1.0;

                  v_sum += wt*src_g[nb];
                  w_sum += wt;
                }
              }
              dst_g[sp] = (w_sum > 0) ? v_sum/w_sum : src_g[sp];
            }
          }
        }
        let ext_smooth = (seam_px % 2 === 0) ? ext_diff_a : ext_diff_b;
        let frac = (a1 !== a0) ? (yr - a0)/Math.max(1, a1 - a0) : 0;

        for (let x = 0; x < viscount_pixels.length; x++) {
          let px = viscount_pixels[x];
          let va = grid_a[px];
          let vb = grid_b[px];
          let v_vis = (va > 1e-4 && vb > 1e-4) ?
            Math.exp((1 - frac)*Math.log(va) + frac*Math.log(vb)) :
            ((1 - frac)*va + frac*vb);

          if (v_vis > 0 && bfs_dist[px] <= seam_px && ext_smooth[px] > 0) {
            let w_cos = 0.5*(1 - Math.cos(Math.PI*bfs_dist[px]/seam_px));

            v_vis = w_cos*v_vis + (1 - w_cos)*ext_smooth[px];
          }

          let u_val = urbc_arr[px] || 0;
          let p_val = Math.max(0, v_vis);
          let u_eff = Math.min(u_val, p_val);

          urbc_arr[px] = u_eff;
          popc_arr[px] = p_val;
          rurc_arr[px] = Math.max(0, p_val - u_eff);
          popd_arr[px] = (land_area[px] > 0) ? p_val/land_area[px] : 0;
        }

        writeFloatGrid(dst_urbc, urbc_arr);
        writeFloatGrid(dst_popc, popc_arr);
        writeFloatGrid(dst_rurc, rurc_arr);
        writeFloatGrid(dst_popd, popd_arr);
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
     * Step C: Synchronises national development index and population metadata tables,
     * updating antiquity HYDE anchor years (-10000 to 0) in Velkscala national populations
     * directly from composited c14bazAAR rasters.
     * @param {Object} [arg0_options]
     */
    static C_syncMetadata (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let anchor_years = [-10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000, 0, ...this.post_1ad_years];
      let geocode_img = null;
      let geocode_obj = null;
      let geocode_path = (typeof admin_modern !== "undefined" && admin_modern.input_geocodes_raster) ?
        admin_modern.input_geocodes_raster : `${h1}/admin_modern/geocodes.png`;
      let legacy_ndi = path.join(this.bf, "velkscala_national_development_index.json");
      let legacy_pop = path.join(this.bf, "velkscala_national_populations.json");
      let national_pops_obj = null;
      let rgb_to_iso3 = {};


      this.ensureDirectories();
      if (fs.existsSync(this.file_stadester_national_development_index)) {
        fs.copyFileSync(this.file_stadester_national_development_index, this.file_national_development_index);
        fs.copyFileSync(this.file_stadester_national_development_index, legacy_ndi);
        console.log(`[population_Velkscala] Step C: Synchronised national development index to ${this.file_national_development_index}.`);
      }

      if (fs.existsSync(this.file_stadester_national_populations)) {
        national_pops_obj = JSON.parse(fs.readFileSync(this.file_stadester_national_populations, "utf8"));

        if (!options.do_not_recompute_antiquity && fs.existsSync(geocode_path) && typeof admin_modern !== "undefined" && typeof admin_modern.getISO3ColourcodesObject === "function") {
          geocode_obj = admin_modern.getISO3ColourcodesObject();
          geocode_img = GeoPNG.loadImage(geocode_path);
          let iso_list = [];
          let iso_to_id = new Map();
          let rgb_int_to_id = new Map();
          for (let local_col in geocode_obj) {
            let local_codes = geocode_obj[local_col];
            if (local_codes && local_codes.length > 0) {
              let parts = local_col.split(",");
              if (parts.length < 3) continue;
              let rgb_int = ((parseInt(parts[0], 10) & 255) << 16) | ((parseInt(parts[1], 10) & 255) << 8) | (parseInt(parts[2], 10) & 255);
              let iso3 = local_codes[0];
              let id = iso_to_id.get(iso3);
              if (id === undefined) {
                id = iso_list.length;
                iso_to_id.set(iso3, id);
                iso_list.push(iso3);
              }
              rgb_int_to_id.set(rgb_int, id);
            }
          }

          let local_total_px = geocode_img.width*geocode_img.height;
          let local_px_ids = new Int32Array(local_total_px);
          local_px_ids.fill(-1);
          for (let i = 0; i < local_total_px; i++) {
            let local_b = i*4;
            let rgb_int = (geocode_img.data[local_b] << 16) | (geocode_img.data[local_b + 1] << 8) | geocode_img.data[local_b + 2];
            let id = rgb_int_to_id.get(rgb_int);
            if (id !== undefined) local_px_ids[i] = id;
          }

          let local_yr_sums = new Float64Array(iso_list.length);
          for (let i = 0; i < anchor_years.length; i++) {
            let local_yr = anchor_years[i];
            let local_pop_path = path.join(this.input_popc_folder, `population_${local_yr}.png`);
            if (!fs.existsSync(local_pop_path)) continue;

            let local_pop_r = GeoPNG.loadNumberRasterImage(local_pop_path, { format: "float32" });
            local_yr_sums.fill(0);
            for (let x = 0; x < local_total_px; x++) {
              let local_id = local_px_ids[x];
              let local_v = local_pop_r.data[x] || 0;
              if (local_id >= 0 && local_v > 0)
                local_yr_sums[local_id] += local_v;
            }

            let local_yr_map = {};
            for (let x = 0; x < iso_list.length; x++) {
              if (local_yr_sums[x] > 0)
                local_yr_map[iso_list[x]] = Number(local_yr_sums[x].toFixed(2));
            }
            let local_sorted_codes = Object.keys(local_yr_map).sort();
            let local_yr_entry = {};
            for (let x = 0; x < local_sorted_codes.length; x++)
              local_yr_entry[local_sorted_codes[x]] = local_yr_map[local_sorted_codes[x]];
            national_pops_obj[local_yr] = local_yr_entry;
          }
        }

        let local_json_str = JSON.stringify(national_pops_obj, null, 2);
        fs.writeFileSync(this.file_national_populations, local_json_str, "utf8");
        fs.writeFileSync(this.file_stadester_national_populations, local_json_str, "utf8");
        fs.writeFileSync(legacy_pop, local_json_str, "utf8");
        console.log(`[population_Velkscala] Step C: Synchronised national populations to ${this.file_national_populations}.`);
      }
    }

    /**
     * Step C (GPU-accelerated async): Computes national population sums across all anchor years on NVIDIA OpenCL.
     * Falls back cleanly to synchronous C_syncMetadata if GPU is unavailable.
     * @param {Object} [arg0_options]
     */
    static async C_syncMetadataGPU (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Guard clause
      let has_fast_accel = (options.use_gpu !== false && typeof GeoPNG !== "undefined" && GeoPNG.gpu && ((GeoPNG.native && GeoPNG.native.isAvailable()) || GeoPNG.gpu.isAvailable()) && typeof GeoPNG.loadRawRGBAAsync === "function");
      if (!has_fast_accel) {
        this.C_syncMetadata(options);
        return;
      }

      //Declare local instance variables
      let anchor_years = [-10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000, 0, ...this.post_1ad_years];
      let geocode_path = (typeof admin_modern !== "undefined" && admin_modern.input_geocodes_raster) ?
        admin_modern.input_geocodes_raster : `${h1}/admin_modern/geocodes.png`;
      let legacy_ndi = path.join(this.bf, "velkscala_national_development_index.json");
      let legacy_pop = path.join(this.bf, "velkscala_national_populations.json");

      this.ensureDirectories();
      if (fs.existsSync(this.file_stadester_national_development_index)) {
        fs.copyFileSync(this.file_stadester_national_development_index, this.file_national_development_index);
        fs.copyFileSync(this.file_stadester_national_development_index, legacy_ndi);
        console.log(`[population_Velkscala] Step C: Synchronised national development index to ${this.file_national_development_index}.`);
      }

      if (fs.existsSync(this.file_stadester_national_populations)) {
        let national_pops_obj = JSON.parse(fs.readFileSync(this.file_stadester_national_populations, "utf8"));

        if (!options.do_not_recompute_antiquity && fs.existsSync(geocode_path) && typeof admin_modern !== "undefined" && typeof admin_modern.getISO3ColourcodesObject === "function") {
          let geocode_obj = admin_modern.getISO3ColourcodesObject();
          let geocode_raw = await GeoPNG.loadRawRGBAAsync(geocode_path);
          if (geocode_raw && geocode_raw.data) {
            let iso_list = [];
            let iso_to_id = new Map();
            let rgb_int_to_id = new Map();

            for (let local_col in geocode_obj) {
              let local_codes = geocode_obj[local_col];
              if (local_codes && local_codes.length > 0) {
                let parts = local_col.split(",");
                if (parts.length < 3) continue;
                let rgb_int = ((parseInt(parts[0], 10) & 255) << 16) | ((parseInt(parts[1], 10) & 255) << 8) | (parseInt(parts[2], 10) & 255);
                let iso3 = local_codes[0];
                let id = iso_to_id.get(iso3);
                if (id === undefined) {
                  id = iso_list.length;
                  iso_to_id.set(iso3, id);
                  iso_list.push(iso3);
                }
                rgb_int_to_id.set(rgb_int, id);
              }
            }

            let total_px = geocode_raw.width*geocode_raw.height;
            let region_ids = new Int32Array(total_px);
            region_ids.fill(-1);
            for (let i = 0; i < total_px; i++) {
              let b = i*4;
              let rgb_int = (geocode_raw.data[b] << 16) | (geocode_raw.data[b + 1] << 8) | geocode_raw.data[b + 2];
              let id = rgb_int_to_id.get(rgb_int);
              if (id !== undefined) region_ids[i] = id;
            }

            let pipeline_conc = (GeoPNG.compute_limits && GeoPNG.compute_limits.cpu && GeoPNG.compute_limits.cpu.pipeline_concurrency) ?
              Number(GeoPNG.compute_limits.cpu.pipeline_concurrency) : 4;

            await GeoPNG.processTimeseriesParallel({
              concurrency: Math.min(options.concurrency || pipeline_conc, pipeline_conc),
              items: anchor_years,
              name: "Velkscala Metadata Regional Sum [Accel]",
              use_workers: false,
              handler: async (local_yr) => {
                let local_pop_path = path.join(this.input_popc_folder, `population_${local_yr}.png`);
                if (!fs.existsSync(local_pop_path)) return;

                let raw_pop = await GeoPNG.loadRawRGBAAsync(local_pop_path);
                if (!raw_pop || !raw_pop.data) return;
                let sums = await GeoPNG.gpu.regionalSumRGBA(raw_pop.data, region_ids, iso_list.length, { positive_only: true });
                if (!sums) return;

                let local_yr_map = {};
                for (let x = 0; x < iso_list.length; x++) {
                  if (sums[x] > 0)
                    local_yr_map[iso_list[x]] = Number(sums[x].toFixed(2));
                }
                let local_sorted_codes = Object.keys(local_yr_map).sort();
                let local_yr_entry = {};
                for (let x = 0; x < local_sorted_codes.length; x++)
                  local_yr_entry[local_sorted_codes[x]] = local_yr_map[local_sorted_codes[x]];
                national_pops_obj[local_yr] = local_yr_entry;
              }
            });
          }
        }

        let local_json_str = JSON.stringify(national_pops_obj, null, 2);
        fs.writeFileSync(this.file_national_populations, local_json_str, "utf8");
        fs.writeFileSync(this.file_stadester_national_populations, local_json_str, "utf8");
        fs.writeFileSync(legacy_pop, local_json_str, "utf8");
        console.log(`[population_Velkscala] Step C [GPU]: Synchronised national populations to ${this.file_national_populations}.`);
      }
    }

    /**
     * Reads the global raster for a specific year and returns its sum in base units.
     * @alias population_Velkscala.getGlobalPopulationSum
     * 
     * @param {number|string} arg0_year
     * 
     * @returns {number|null} Sum of all cells in persons, or null if raster is not found.
     */
    static getGlobalPopulationSum (arg0_year) {
      //Convert from parameters
      let year = parseInt(arg0_year);

      //Declare local instance variables
      let raster_path = path.join(this.input_popc_folder, `population_${year}.png`);

      //Guard clause
      if (!fs.existsSync(raster_path)) return null;

      //Return statement
      return Math.round(GeoPNG.getImageSum(raster_path, { format: "float32" }));
    }

    /**
     * Aggregates national population totals from the Velkscala population raster for a given year.
     * @alias population_Velkscala.getNationalPopulationsForYear
     * 
     * @param {number|string} arg0_year
     * @param {Object} [arg1_options]
     *  @param {Object} [arg1_options.pixel_to_geocode]
     * 
     * @returns {Object|null} { [iso_code]: population }
     */
    static getNationalPopulationsForYear (arg0_year, arg1_options) {
      //Convert from parameters
      let year = parseInt(arg0_year);
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let raster_path = path.join(this.input_popc_folder, `population_${year}.png`);
      let pixel_to_geocode = (options.pixel_to_geocode) ?
        options.pixel_to_geocode : ((typeof population_Stadester_rasters !== "undefined") ?
          population_Stadester_rasters.getPixelToGeocodeMapping() : null);

      //Guard clauses
      if (!fs.existsSync(raster_path) || !pixel_to_geocode) return null;

      let img = GeoPNG.loadNumberRasterImage(raster_path, { format: "float32" });
      let national_pops = {};
      let total_pixels = img.width*img.height;

      for (let i = 0; i < total_pixels; i++) {
        let code = pixel_to_geocode[i];
        if (code)
          national_pops[code] = (national_pops[code] || 0) + img.data[i];
      }

      Object.iterate(national_pops, (code, val) => {
        national_pops[code] = Math.round(val);
      });

      //Return statement
      return Object.sortKeys(national_pops, { type: "ascending" });
    }

    /**
     * Step D: Validates timeseries continuity and boundary stability at 1 AD.
     * @param {Object} [arg0_options]
     *  @param {boolean} [arg0_options.validate_sums=true] - Whether to check boundary continuity and sample raster sums.
     * 
     * @returns {Object} Validation summary
     */
    static D_validateCompositing (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let all_years = this.all_years;
      let missing_files = [];
      let report = {
        boundary_1ad_continuity: null,
        missing: [],
        sample_sums: {},
        total_timesteps: all_years.length
      };
      let validate_sums = (options.validate_sums !== undefined) ? options.validate_sums : true;

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

      //Check 1 AD boundary continuity and sample sums
      if (validate_sums && typeof GeoPNG !== "undefined") {
        let sum_0 = this.getGlobalPopulationSum(0);
        let sum_100 = this.getGlobalPopulationSum(100);

        if (sum_0 !== null && sum_100 !== null && sum_0 > 0) {
          let ratio = sum_100 / sum_0;
          let is_continuous = (ratio >= 0.4 && ratio <= 2.5);
          report.boundary_1ad_continuity = {
            is_continuous: is_continuous,
            ratio: Number(ratio.toFixed(4)),
            sum_0_ad: sum_0,
            sum_100_ad: sum_100
          };
          console.log(`[population_Velkscala] Step D: 1 AD Boundary check - 0 AD: ${sum_0.toLocaleString()}, 100 AD: ${sum_100.toLocaleString()} (Ratio: ${ratio.toFixed(4)}, Continuous: ${is_continuous})`);
        }

        //Sample benchmark years across antiquity and post-1AD
        let benchmark_years = [-10000, -5000, -1000, 0, 100, 500, 1000, 1500, 1750, 1900, 1975, 2025];
        for (let b = 0; b < benchmark_years.length; b++) {
          let b_yr = benchmark_years[b];
          let b_sum = this.getGlobalPopulationSum(b_yr);
          if (b_sum !== null) report.sample_sums[b_yr.toString()] = b_sum;
        }
      }

      fs.writeFileSync(path.join(this.config_folder, "compositing_report.json"), JSON.stringify(report, null, 2));

      //Return statement
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
      if (!options.exclude.includes("C")) await this.C_syncMetadataGPU(options);
      if (!options.exclude.includes("D")) this.D_validateCompositing(options);

      console.log(`=== Successfully completed population_Velkscala pipeline in ${((Date.now() - start_time) / 1000).toFixed(1)}s ===`);
    }
  };
}
