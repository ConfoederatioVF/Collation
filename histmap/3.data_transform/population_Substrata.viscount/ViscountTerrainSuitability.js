//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { ViscountUrbanMask } = global.ViscountUrbanMask ? global : require("./ViscountUrbanMask.js");

//Initialise functions
{
  /**
   * 5-arcminute (`4320x2160`) Topographic Elevation/Slope/TRI Step-Band Suitability,
   * Terrain-Gated Crisp Fluvial & Coastal Corridors, and Strict Union Habitability Mask
   * (Documented Stadestér Settlements Proximity Filter + HYDE 3.5 Inhabited Areas)
   * for Operation Viscount Dasymetric Residual Kriging.
   *
   * @class ViscountTerrainSuitability
   */
  global.ViscountTerrainSuitability = class {
    /**
     * Step A: Loads global 5-arcminute elevation (`elev_5m_m.png`), Horn macro-slope (`slope_5m_deg.png`)
     * and Terrain Ruggedness Index (`tri_5m_m.png`) over valid domain pixels.
     * @alias ViscountTerrainSuitability.A_loadTerrainArrays
     *
     * @param {Object} arg0_mask_data
     * @param {Object} [arg1_config]
     *
     * @returns {Object}
     */
    static A_loadTerrainArrays (arg0_mask_data, arg1_config) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let config = (arg1_config) ? arg1_config : {};

      //Declare local instance variables
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let elev_path = path.resolve(
        mask_data.project_root || ".",
        cov_paths.elev_raster || "histmap/1.data_raw/metadata_HYDE/general_rasters/elev_5m_m.png"
      );
      let elev_valid = new Float32Array(mask_data.valid_cell_count);
      let n_valid = mask_data.valid_cell_count;
      let slope_path = path.resolve(
        mask_data.project_root || ".",
        cov_paths.slope_raster || "histmap/1.data_raw/metadata_HYDE/general_rasters/slope_5m_deg.png"
      );
      let slope_valid = new Float32Array(n_valid);
      let total_px = mask_data.grid_width*mask_data.grid_height;
      let tri_path = path.resolve(
        mask_data.project_root || ".",
        cov_paths.tri_raster || "histmap/1.data_raw/metadata_HYDE/general_rasters/tri_5m_m.png"
      );
      let tri_valid = new Float32Array(n_valid);
      let valid_indices = mask_data.valid_indices;

      //Function body
      let elev_raw = fs.existsSync(elev_path) ? ViscountUrbanMask.readGlobalFloat32Raster(elev_path, total_px) : null;
      let slope_raw = fs.existsSync(slope_path) ? ViscountUrbanMask.readGlobalFloat32Raster(slope_path, total_px) : null;
      let tri_raw = fs.existsSync(tri_path) ? ViscountUrbanMask.readGlobalFloat32Raster(tri_path, total_px) : null;

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];

        elev_valid[i] = elev_raw ? Math.max(0, elev_raw[gidx]) : 150.0;
        slope_valid[i] = slope_raw ? Math.max(0, slope_raw[gidx]) : 0.15;
        tri_valid[i] = tri_raw ? Math.max(0, tri_raw[gidx]) : 25.0;
      }

      //Return statement
      return {
        elev_valid: elev_valid,
        has_dem: Boolean(elev_raw),
        slope_valid: slope_valid,
        tri_valid: tri_valid
      };
    }


    /**
     * Step B: Computes HYDE-inspired latitude-adjusted elevation contour step bands (`u_elev`),
     * macro-slope/TRI ruggedness step bands (`u_slope`) and combined terrain suitability (`u_terrain`).
     * Uses crisp smooth-stepped contour breaks rather than diffuse linear blurs.
     * @alias ViscountTerrainSuitability.B_computeTerrainStepBands
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_terrain
     * @param {Object} [arg2_config]
     *
     * @returns {Object}
     */
    static B_computeTerrainStepBands (arg0_mask_data, arg1_terrain, arg2_config) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let terrain = arg1_terrain;
      let config = (arg2_config) ? arg2_config : {};

      //Declare local instance variables
      let elev = terrain.elev_valid;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let is_micro_island = (mask_data.valid_cell_count < 2000);
      let n_valid = mask_data.valid_cell_count;
      let slope = terrain.slope_valid;
      let tri = terrain.tri_valid;
      let u_elev = new Float32Array(n_valid);
      let u_slope = new Float32Array(n_valid);
      let u_terrain = new Float32Array(n_valid);
      let valid_indices = mask_data.valid_indices;

      //Helper: crisp smoothstep over [0, 1]
      let smoothStep = function (arg0_x, arg1_edge0, arg2_edge1) {
        let t = Math.max(0, Math.min(1, (arg0_x - arg1_edge0)/Math.max(1e-6, arg2_edge1 - arg1_edge0)));

        return t*t*(3 - 2*t);
      };

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let lat = 90 - (Math.floor(gidx/grid_w) + 0.5)*180/grid_h;
        let abs_lat = Math.abs(lat);
        let e_m = elev[i];
        let s_deg = slope[i];
        let t_m = tri[i];

        //Latitude-adapted elevation thresholds (tropical inter-Andean valleys up to 4100m vs mid-latitude Tibet/Rockies)
        let e_low = 800.0;
        let e_mid = 2400.0;
        let e_high = 3950.0;
        let e_alp = 4550.0;
        let b2_w = 0.72;
        let b3_w = 0.42;
        let b4_w = 0.16;

        if (is_micro_island && abs_lat < 25.0) {
          //Volcanic oceanic islands (e.g. Hawai'i): coastal/lowland belts habitable; >2300m lava shields uninhabitable
          e_low = 450.0;
          e_mid = 1150.0;
          e_high = 1900.0;
          e_alp = 2550.0;
          b2_w = 0.62;
          b3_w = 0.28;
          b4_w = 0.09;
        } else if (abs_lat > 23.0 && abs_lat <= 42.0) {
          let f = (abs_lat - 23.0)/19.0;

          e_low = 800.0 - 370.0*f;
          e_mid = 2400.0 - 1100.0*f;
          e_high = 3950.0 - 1350.0*f;
          e_alp = 4550.0 - 750.0*f;
          b2_w = 0.72 - 0.10*f;
          b3_w = 0.42 - 0.14*f;
          b4_w = 0.16 - 0.07*f;
        } else if (abs_lat > 42.0 && abs_lat <= 58.0) {
          let f = (abs_lat - 42.0)/16.0;

          e_low = 430.0 - 150.0*f;
          e_mid = 1300.0 - 550.0*f;
          e_high = 2600.0 - 1150.0*f;
          e_alp = 3800.0 - 1800.0*f;
          b2_w = 0.62;
          b3_w = 0.28;
          b4_w = 0.09;
        } else if (abs_lat > 58.0) {
          let f = Math.min(1.0, (abs_lat - 58.0)/14.0);

          e_low = 280.0 - 100.0*f;
          e_mid = 750.0 - 300.0*f;
          e_high = 1450.0 - 650.0*f;
          e_alp = 2000.0 - 850.0*f;
          b2_w = 0.62;
          b3_w = 0.28;
          b4_w = 0.09;
        }

        //Crisp 5-tier elevation contour step bands (narrow 10% transition zone at each break)
        let b1 = 1.0 - smoothStep(e_m, e_low*0.92, e_low*1.08);
        let b2 = smoothStep(e_m, e_low*0.92, e_low*1.08)*(1.0 - smoothStep(e_m, e_mid*0.92, e_mid*1.08));
        let b3 = smoothStep(e_m, e_mid*0.92, e_mid*1.08)*(1.0 - smoothStep(e_m, e_high*0.92, e_high*1.08));
        let b4 = smoothStep(e_m, e_high*0.92, e_high*1.08)*(1.0 - smoothStep(e_m, e_alp*0.94, e_alp*1.06));
        let b5 = smoothStep(e_m, e_alp*0.94, e_alp*1.06);
        let ue = 1.00*b1 + b2_w*b2 + b3_w*b3 + b4_w*b4 + 0.02*b5;

        //Crisp 4-tier macro-slope & TRI ruggedness step bands (preserving 9 km pixels containing inter-montane valleys)
        let rug = Math.max(s_deg/0.38, t_m/75.0);
        let r1 = 1.0 - smoothStep(rug, 0.90, 1.15);
        let r2 = smoothStep(rug, 0.90, 1.15)*(1.0 - smoothStep(rug, 2.05, 2.40));
        let r3 = smoothStep(rug, 2.05, 2.40)*(1.0 - smoothStep(rug, 3.60, 4.15));
        let r4 = smoothStep(rug, 3.60, 4.15);
        let us = 1.00*r1 + 0.70*r2 + 0.38*r3 + 0.14*r4;

        u_elev[i] = ue;
        u_slope[i] = us;
        u_terrain[i] = Math.max(0.005, ue*us);
      }

      //Return statement
      return {
        u_elev: u_elev,
        u_slope: u_slope,
        u_terrain: u_terrain
      };
    }


    /**
     * Step C: Tightens raw fluvial & coastal proximity fields into crisp valley-floor / coastal-plain
     * step bands gated by terrain suitability (`u_terrain` / `u_slope`), eliminating wide glowing river worms
     * across mountain gorges and barren plateaus.
     * @alias ViscountTerrainSuitability.C_tightenFluvialAndCoastalFields
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_u_fluv_raw
     * @param {Float32Array} arg2_u_coast_raw
     * @param {Object} arg3_terrain_bands
     *
     * @returns {Object}
     */
    static C_tightenFluvialAndCoastalFields (arg0_mask_data, arg1_u_fluv_raw, arg2_u_coast_raw, arg3_terrain_bands) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let u_fluv_raw = arg1_u_fluv_raw;
      let u_coast_raw = arg2_u_coast_raw;
      let tb = arg3_terrain_bands;

      //Declare local instance variables
      let n_valid = mask_data.valid_cell_count;
      let u_coast = new Float32Array(n_valid);
      let u_fluv = new Float32Array(n_valid);

      //Function body
      //Legacy computeFluvialProximityField encoded 0.25 + 0.75*exp(-d_km/26.0); invert to d_km and re-band
      //Slope-adaptive: crisp valley-floor catchment breaks on sloped terrain, gentle floodplain diffusion on flat plains/steppe
      for (let i = 0; i < n_valid; i++) {
        let f_in = u_fluv_raw ? u_fluv_raw[i] : 0.05;
        let c_in = u_coast_raw ? u_coast_raw[i] : 0.05;
        let us_i = tb ? tb.u_slope[i] : 1.0;
        let flat_w = Math.max(0.0, Math.min(1.0, (us_i - 0.55)/0.35));
        let f_step = 0.06;
        let c_step = 0.05;

        if (f_in > 0.26) {
          let frac = Math.max(1e-4, Math.min(1.0, (f_in - 0.25)/0.75));
          let d_km = -26.0*Math.log(frac);
          let f_crisp = 0.06;

          if (d_km <= 5.5) f_crisp = 1.00;
          else if (d_km <= 12.5) f_crisp = 0.50;
          else if (d_km <= 21.0) f_crisp = 0.20;
          let f_flat = 0.06 + 0.58*Math.exp(-d_km/22.0);

          f_step = (1.0 - flat_w)*f_crisp + flat_w*f_flat;
        }
        if (c_in > 0.11) {
          let frac = Math.max(1e-4, Math.min(1.0, (c_in - 0.10)/0.90));
          let d_km = -32.0*Math.log(frac);
          let c_crisp = 0.05;

          if (d_km <= 6.5) c_crisp = 1.00;
          else if (d_km <= 15.0) c_crisp = 0.48;
          else if (d_km <= 25.0) c_crisp = 0.16;
          let c_flat = 0.05 + 0.72*Math.exp(-d_km/24.0);

          c_step = (1.0 - flat_w)*c_crisp + flat_w*c_flat;
        }

        //Gate river bonus by terrain suitability so gorge/alpine/permafrost canyon rivers never glow
        let terr_gate = tb ? Math.min(1.0, 1.40*tb.u_terrain[i]) : 1.0;
        let slope_gate = tb ? Math.min(1.0, 1.35*us_i) : 1.0;

        u_fluv[i] = 0.06 + (f_step - 0.06)*terr_gate;
        u_coast[i] = 0.05 + (c_step - 0.05)*slope_gate;
      }

      //Return statement
      return {
        u_coastal: u_coast,
        u_fluvial: u_fluv
      };
    }


    /**
     * Step D: Constructs the strict union habitability mask combining:
     * (1) Proximity filter around documented Stadestér settlements & verified archaeological site pixels
     *     (supporting `pixels`, `pixel_indices`, `documented_pixels` and `documented_settlements.json`),
     * (2) HYDE 3.5 inhabited areas with extreme-biome (alpine/permafrost/hyper-arid) numerical-dust rejection.
     * @alias ViscountTerrainSuitability.D_buildUnionHabitabilityMask
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_inputs
     * @param {Object} [arg2_config]
     * @param {Object} [arg3_obs_bundle]
     * @param {Function} arg4_bfs_fn
     *
     * @returns {Object}
     */
    static D_buildUnionHabitabilityMask (arg0_mask_data, arg1_inputs, arg2_config, arg3_obs_bundle, arg4_bfs_fn) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let inputs = arg1_inputs;
      let config = (arg2_config) ? arg2_config : {};
      let obs_bundle = arg3_obs_bundle;
      let bfs_fn = arg4_bfs_fn;

      //Declare local instance variables
      let catch_seeds = [];
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let doc_sites_json = cov_paths.documented_site_pixels_json ?
        path.resolve(mask_data.project_root || ".", cov_paths.documented_site_pixels_json) :
        path.join(mask_data.domain_dir || "", "config/documented_site_pixels.json");
      let doc_sett_json = cov_paths.documented_settlements_json ?
        path.resolve(mask_data.project_root || ".", cov_paths.documented_settlements_json) :
        path.join(mask_data.domain_dir || "", "config/documented_settlements.json");
      let elev_valid = inputs.elev_valid;
      let forest_valid = inputs.forest_valid;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let hab_cfg = (config.kriging_config && config.kriging_config.habitability_filter) ?
        config.kriging_config.habitability_filter : {};
      let hyde_raw_dir = path.resolve(
        mask_data.project_root || ".",
        cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters"
      );
      let is_micro_island = (mask_data.valid_cell_count < 2000);
      let maxln_valid = inputs.maxln_valid;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let perm_ice = inputs.perm_ice;
      let raw_hyde_dens = inputs.raw_hyde_dens;
      let site_seeds = [];
      let site_seed_set = new Set();
      let stadester_seeds = [];
      let stadester_seed_set = new Set();
      let total_px = grid_w*grid_h;
      let u_elev = inputs.u_elev;
      let u_terrain = inputs.u_terrain;
      let valid_indices = mask_data.valid_indices;

      //Function body
      //1. Load documented Stadestér settlements directly into stadester_seeds & site_seeds
      if (doc_sett_json && fs.existsSync(doc_sett_json)) {
        try {
          let raw_s = JSON.parse(fs.readFileSync(doc_sett_json, "utf8"));
          let s_list = Array.isArray(raw_s.settlements) ? raw_s.settlements : [];

          for (let i = 0; i < s_list.length; i++) {
            let s = s_list[i];

            if (!s || !Number.isFinite(Number(s.lat)) || !Number.isFinite(Number(s.lon))) continue;
            if (Number.isFinite(s.min_year) && s.min_year > Number(hab_cfg.stadester_max_first_year || 1850)) continue;
            let sc = Math.max(0, Math.min(grid_w - 1, Math.floor((Number(s.lon) + 180)*grid_w/360)));
            let sr = Math.max(0, Math.min(grid_h - 1, Math.floor((90 - Number(s.lat))*grid_h/180)));
            let gidx = sr*grid_w + sc;

            if (!stadester_seed_set.has(gidx)) {
              stadester_seed_set.add(gidx);
              stadester_seeds.push(gidx);
            }
            if (!site_seed_set.has(gidx)) {
              site_seed_set.add(gidx);
              site_seeds.push(gidx);
            }
          }
        } catch (e) {
          console.error(`[ViscountTerrainSuitability] Failed reading ${doc_sett_json}:`, e.message);
        }
      }

      //2. Load documented_site_pixels.json supporting all three schemas (pixels, pixel_indices, documented_pixels)
      if (doc_sites_json && fs.existsSync(doc_sites_json)) {
        try {
          let parsed = JSON.parse(fs.readFileSync(doc_sites_json, "utf8"));

          if (Array.isArray(parsed.preindustrial_pixels) && parsed.preindustrial_pixels.length > 0) {
            for (let i = 0; i < parsed.preindustrial_pixels.length; i++) {
              let sc = Number(parsed.preindustrial_pixels[i][0]);
              let sr = Number(parsed.preindustrial_pixels[i][1]);

              if (sc >= 0 && sc < grid_w && sr >= 0 && sr < grid_h) {
                let gidx = sr*grid_w + sc;

                if (!site_seed_set.has(gidx)) {
                  site_seed_set.add(gidx);
                  site_seeds.push(gidx);
                }
              }
            }
          } else if (Array.isArray(parsed.pixels)) {
            for (let i = 0; i < parsed.pixels.length; i++) {
              let sc = Number(parsed.pixels[i][0]);
              let sr = Number(parsed.pixels[i][1]);

              if (sc >= 0 && sc < grid_w && sr >= 0 && sr < grid_h) {
                let gidx = sr*grid_w + sc;

                if (!site_seed_set.has(gidx)) {
                  site_seed_set.add(gidx);
                  site_seeds.push(gidx);
                }
              }
            }
          } else {
            let flat = Array.isArray(parsed.pixel_indices) ? parsed.pixel_indices :
              (Array.isArray(parsed.documented_pixels) ? parsed.documented_pixels : []);

            for (let i = 0; i < flat.length; i++) {
              let gidx = Number(flat[i]);

              if (gidx >= 0 && gidx < total_px && !site_seed_set.has(gidx)) {
                site_seed_set.add(gidx);
                site_seeds.push(gidx);
              }
            }
          }
        } catch (e) {
          console.error(`[ViscountTerrainSuitability] Failed reading ${doc_sites_json}:`, e.message);
        }
      }

      if (obs_bundle && Array.isArray(obs_bundle.obs_list)) {
        for (let i = 0; i < obs_bundle.obs_list.length; i++) {
          let o = obs_bundle.obs_list[i];

          if (!o) continue;
          let cr = Math.max(0, Math.min(grid_h - 1, Math.floor((90 - o.lat)*grid_h/180)));
          let cc = Math.max(0, Math.min(grid_w - 1, Math.floor((o.lon + 180)*grid_w/360)));
          let cidx = cr*grid_w + cc;

          catch_seeds.push(cidx);
          if (site_seeds.length === 0 && !o.is_frontier_buffer && (o.total_sites_all_periods || 0) > 0)
            site_seeds.push(cidx);
        }
      }

      let dist_site_px = bfs_fn(mask_data, site_seeds, 8);
      let dist_stadester_px = (stadester_seeds.length > 0) ?
        bfs_fn(mask_data, stadester_seeds, 8) :
        dist_site_px;
      let dist_catch_px = (catch_seeds.length > 0) ?
        bfs_fn(mask_data, catch_seeds, 8) :
        dist_site_px;

      //Load HYDE 1500 AD agricultural land use to distinguish real oases/farms from diffuse HYDE numerical smear
      let crp_1500 = ViscountUrbanMask.readGlobalFloat32Raster(path.join(hyde_raw_dir, "cropland1500AD.png"), total_px);
      let irr_1500 = ViscountUrbanMask.readGlobalFloat32Raster(path.join(hyde_raw_dir, "tot_irri1500AD.png"), total_px);
      let grz_1500 = ViscountUrbanMask.readGlobalFloat32Raster(path.join(hyde_raw_dir, "grazing1500AD.png"), total_px);
      let hab_mask = new Uint8Array(n_valid);
      let r_sett = Number.isFinite(hab_cfg.stadester_radius_px) ? Number(hab_cfg.stadester_radius_px) : 2.0;
      let r_site = Number.isFinite(hab_cfg.site_radius_px) ? Number(hab_cfg.site_radius_px) : 2.0;
      let hyde_core_min = Number.isFinite(hab_cfg.hyde_core_min_dens) ? Number(hab_cfg.hyde_core_min_dens) : 0.002;
      let hyde_marginal_min = Number.isFinite(hab_cfg.hyde_marginal_min_dens) ? Number(hab_cfg.hyde_marginal_min_dens) : 0.14;
      let arctic_lat_cut = Number.isFinite(hab_cfg.arctic_lat_cut) ? Number(hab_cfg.arctic_lat_cut) : 60.5;
      let extreme_elev_cut = Number.isFinite(hab_cfg.extreme_elev_cut_m) ? Number(hab_cfg.extreme_elev_cut_m) : 4150.0;

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let r = Math.floor(gidx/grid_w);
        let c = gidx % grid_w;
        let lat = 90 - (r + 0.5)*180/grid_h;
        let lon = -180 + (c + 0.5)*360/grid_w;
        let la_i = Math.max(1.0, mask_data.cell_land_area[i]);
        let crop_1500 = (crp_1500[gidx] + 1.5*irr_1500[gidx])/la_i;
        let lu_1500 = crop_1500 + (0.25*grz_1500[gidx])/la_i;
        let e_m = elev_valid ? elev_valid[i] : 150.0;
        let ml = maxln_valid ? maxln_valid[i] : 0.5;
        let f_v = forest_valid ? forest_valid[i] : 0;
        let ut = u_terrain ? u_terrain[i] : 1.0;
        let ue = u_elev ? u_elev[i] : 1.0;
        let is_high_arctic_gl = (lat >= 59.5 && lon >= -74.0 && lon <= -10.0 && (lat > 78.5 || (lat > 71.5 && lon > -30.0)));

        //Hawai'i volcanic summit exclusion (>2500m uninhabitable lava domes)
        if (is_micro_island && Math.abs(lat) < 25.0 && e_m > 2500.0) {
          hab_mask[i] = 0;
          continue;
        }

        //Greenland documented coastal sites override
        if (lat >= 59.5 && lat <= 78.0 && lon >= -74.0 && lon <= -10.0 && dist_site_px[i] <= 1.5) {
          perm_ice[i] = Math.max(perm_ice[i], 0.25);
          hab_mask[i] = 1;
          continue;
        }
        if (perm_ice[i] <= 0.05) continue;

        //Branch 1: Documented Stadestér settlement proximity filter (CENTAUR union convention; always honours verified mountain settlements)
        let is_stadester_hab = (!is_high_arctic_gl) &&
          (dist_catch_px[i] <= 5.6) &&
          ((dist_stadester_px[i] <= 1.2) || (dist_stadester_px[i] <= r_sett && ut >= 0.03));

        //Branch 2: Verified archaeological site proximity filter (allows high-altitude Andean/montane archaeological valleys)
        let is_site_hab = is_micro_island ?
          (dist_catch_px[i] <= 5.6 && e_m <= 2500.0) :
          (!is_high_arctic_gl && dist_site_px[i] <= r_site && dist_catch_px[i] <= 5.6 && (ut >= 0.02 || crop_1500 >= 0.008));

        //Branch 3: HYDE 3.5 inhabited areas with barren/nival-plateau/permafrost numerical-dust rejection
        let is_tropical_belt = (Math.abs(lat) <= 23.0);
        let nival_cut = is_tropical_belt ? Math.max(4450.0, extreme_elev_cut) : extreme_elev_cut;
        let is_nival_plateau = (e_m >= nival_cut) || (!is_tropical_belt && e_m >= 3650.0 && ml < 0.08);
        let is_siberian_permafrost = (lat >= 60.5 && lon >= 65.0 && lon <= 180.0 && ml < 0.22);
        let is_extreme_biome = (
          is_nival_plateau ||
          is_siberian_permafrost ||
          (ue <= 0.095) ||
          (lat >= arctic_lat_cut && ml < 0.09) ||
          (lat >= 64.5 && ml < 0.16) ||
          (ml < 0.04 && f_v === 0 && lu_1500 < 0.005)
        );
        let is_hyde_hab = is_nival_plateau ?
          ((raw_hyde_dens[i] >= 0.85 && ut >= 0.02) || (crop_1500 >= 0.008 && raw_hyde_dens[i] >= 0.05)) :
          (is_extreme_biome ?
            ((raw_hyde_dens[i] >= hyde_marginal_min && ut >= 0.02) || (crop_1500 >= 0.008 && raw_hyde_dens[i] >= 0.02)) :
            (raw_hyde_dens[i] >= hyde_core_min));

        if (is_stadester_hab || is_site_hab || is_hyde_hab)
          hab_mask[i] = 1;
      }

      //Targeted 1-pass urban-pinhole closing (e.g. Brasilia) without leaking into uninhabitable wilderness pockets
      let uopp_v = inputs.uopp_valid || null;

      if (p2v) {
        let hab_next = Uint8Array.from(hab_mask);

        for (let i = 0; i < n_valid; i++) {
          if (hab_mask[i] === 1 || perm_ice[i] <= 0.05) continue;
          if (u_terrain && u_terrain[i] < 0.12) continue;
          if (is_micro_island && elev_valid && elev_valid[i] > 2500.0) continue;
          let is_urb_pinhole = Boolean(uopp_v && uopp_v[i] > 1.5);
          let near_site = (dist_catch_px[i] <= 5.6);

          if (!is_urb_pinhole && !near_site) continue;
          let gidx = valid_indices[i];
          let cy = Math.floor(gidx/grid_w);
          let cx = gidx % grid_w;
          let nbr_hab = 0;

          for (let dy = -1; dy <= 1; dy++) {
            let nr = cy + dy;

            if (nr < 0 || nr >= grid_h) continue;
            for (let dx = -1; dx <= 1; dx++) {
              if (dx === 0 && dy === 0) continue;
              let nv = p2v[nr*grid_w + ((cx + dx + grid_w) % grid_w)];

              if (nv >= 0 && hab_mask[nv] === 1) nbr_hab++;
            }
          }
          if (nbr_hab >= (is_urb_pinhole ? 5 : 7)) hab_next[i] = 1;
        }
        hab_mask = hab_next;
      }

      //Return statement
      return {
        dist_catch_px: dist_catch_px,
        dist_site_px: dist_site_px,
        dist_stadester_px: dist_stadester_px,
        hab_mask: hab_mask
      };
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountTerrainSuitability: global.ViscountTerrainSuitability };
