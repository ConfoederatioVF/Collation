//Initialise functions
{
  let fs = global.fs || require("fs");
  let JSON5 = global.JSON5 || require("json5");
  let path = global.path || require("path");
  let { PNG } = global.pngjs || require("pngjs");

  /**
   * Mosaics, dasymetrically calibrates, and spatiotemporally smooths the Russian (`sites_IA_RAS`, -10000 to 1900 AD)
   * and Kievan Rus (`sites_belarus_ukraine`, -10000 to 1400 AD) kriged population substrata across all 13 regional
   * literature review areal masks (`histmap/1.data_raw/population_regional/russia/`) before compositing into
   * `population_Substrata.outlier_removal`.
   *
   * Logical flow is prefixed with step letters (`A_` through `E_`):
   * - `A_loadManifestAndMasks`: Loads `histmap/1.data_raw/population_regional/russia/russia_areal_masks.json5`, indexes all 13 regional
   *   `4320x2160` RGB PNG masks and their JSON5 population tables, and constructs the pixel-level calibration hierarchy
   *   and 3-pixel raised-cosine exterior border feathering weights.
   * - `B_mosaicKrigedSubstrataForYear`: Loads the kriged `sites_IA_RAS` (`-10000..1900`) and `sites_belarus_ukraine`
   *   (`-10000..1400`) rasters for a given benchmark year and mosaics them over their respective non-overlapping domains.
   * - `C_computeSmoothedRegionalMultipliers`: Computes exact dasymetric calibration multipliers per sub-region (including
   *   sub-mask appanage/ecological weights in `russian_core_principalities` and residual macro-region scaling in
   *   `migration_period`), applies separable 2D box-filter smoothing to the log-multiplier field across internal zone
   *   boundaries, and re-normalises each zone so exact regional totals are conserved without step-edge cliffs.
   * - `D_applyTemporalSmoothingAndComposite`: Applies temporal log-Laplacian regularisation across the 48 HYDE benchmark
   *   years (`-10000` to `1900 AD`), smoothly transitions Belarus & Ukraine across `1300 -> 1400 -> 1500 AD`, and
   *   composites the calibrated mosaic into `population_Substrata.outlier_removal` with raised-cosine border feathering.
   * - `E_writeDiagnosticsSummary`: Writes regional calibration and spatiotemporal smoothness diagnostics.
   *
   * @class population_Substrata_russia
   */
  global.population_Substrata_russia = class {
    static bf = (typeof h3 !== "undefined") ?
      `${h3}/population_Substrata.russia/` :
      ((fs.existsSync("./histmap/3.data_transform/population_Substrata.russia")) ?
        path.resolve("./histmap/3.data_transform/population_Substrata.russia") + path.sep :
        path.join(__dirname, "/"));
    static config_path = (typeof h1 !== "undefined" && fs.existsSync(`${h1}population_regional/russia/russia_areal_masks.json5`)) ?
      path.resolve(`${h1}population_regional/russia/russia_areal_masks.json5`) :
      ((fs.existsSync("./histmap/1.data_raw/population_regional/russia/russia_areal_masks.json5")) ?
        path.resolve("./histmap/1.data_raw/population_regional/russia/russia_areal_masks.json5") :
        path.resolve(__dirname, "../../1.data_raw/population_regional/russia/russia_areal_masks.json5"));
    static project_root = (fs.existsSync("./histmap/1.data_raw")) ?
      path.resolve(".") :
      path.resolve(__dirname, "../../..");

    /**
     * Step A: Loads `histmap/1.data_raw/population_regional/russia/russia_areal_masks.json5`, indexes all specialist (Priority 2)
     * and macro (Priority 1) `4320x2160` RGB PNG areal masks, and builds pixel-level domain and feathering tables.
     * @alias population_Substrata_russia.A_loadManifestAndMasks
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    static A_loadManifestAndMasks (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let border_dist;
      let feather_px = 3;
      let feather_weights;
      let height = 2160;
      let macro_entry = null;
      let manifest_path = (options.config_path) ? options.config_path : this.config_path;
      let manifest_obj = JSON5.parse(fs.readFileSync(manifest_path, "utf8"));
      let n_pixels = 4320*2160;
      let pixel_domain = new Uint8Array(4320*2160);
      let pixel_macro_zone = new Int16Array(4320*2160).fill(-1);
      let pixel_spec_mask = new Int16Array(4320*2160).fill(-1);
      let pixel_spec_zone = new Int16Array(4320*2160).fill(-1);
      let root_dir = (options.project_root) ? options.project_root : this.project_root;
      let rus_pop_sample_path;
      let bu_pop_sample_path;
      let specialist_entries = [];
      let valid_indices = [];
      let width = 4320;

      //Function body
      if (manifest_obj.smoothing && Number.isFinite(manifest_obj.smoothing.border_feather_radius_px))
        feather_px = manifest_obj.smoothing.border_feather_radius_px;

      //1. Identify valid domain pixels from sample kriged population rasters (popc_1000.png)
      rus_pop_sample_path = path.join(root_dir, manifest_obj.substrata_sources.russia_ia_ras.rasters_folder, "popc_1000.png");
      bu_pop_sample_path = path.join(root_dir, manifest_obj.substrata_sources.belarus_ukraine.rasters_folder, "popc_1000.png");

      if (fs.existsSync(rus_pop_sample_path)) {
        let rus_png = PNG.sync.read(fs.readFileSync(rus_pop_sample_path));
        for (let idx = 0; idx < n_pixels; idx++) {
          let p4 = idx*4;
          if (
            rus_png.data[p4] !== 0 ||
            rus_png.data[p4 + 1] !== 0 ||
            rus_png.data[p4 + 2] !== 0 ||
            rus_png.data[p4 + 3] !== 0
          ) pixel_domain[idx] = 1; //Russia + Crimea (sites_IA_RAS)
        }
      }

      if (fs.existsSync(bu_pop_sample_path)) {
        let bu_png = PNG.sync.read(fs.readFileSync(bu_pop_sample_path));
        for (let idx = 0; idx < n_pixels; idx++) {
          if (pixel_domain[idx] === 1) continue;
          let p4 = idx*4;
          if (
            bu_png.data[p4] !== 0 ||
            bu_png.data[p4 + 1] !== 0 ||
            bu_png.data[p4 + 2] !== 0 ||
            bu_png.data[p4 + 3] !== 0
          ) pixel_domain[idx] = 2; //Belarus + Mainland Ukraine (sites_belarus_ukraine)
        }
      }

      //2. Load Priority 1 Macro Mask (migration_period)
      if (manifest_obj.macro_mask) {
        let m_cfg_path = path.join(root_dir, manifest_obj.macro_mask.json5_path);
        let m_png_path = path.join(root_dir, manifest_obj.macro_mask.mask_path);
        if (fs.existsSync(m_cfg_path) && fs.existsSync(m_png_path)) {
          let m_json = JSON5.parse(fs.readFileSync(m_cfg_path, "utf8"));
          let m_png = PNG.sync.read(fs.readFileSync(m_png_path));
          let m_zones = [];
          let colour_to_z = new Map();
          let z_keys = Object.keys(m_json.regions || {});

          for (let i = 0; i < z_keys.length; i++) {
            let zk = z_keys[i];
            let zc = m_json.regions[zk];
            let col = zc.colour || zc.color;
            if (Array.isArray(col) && col.length >= 3) {
              colour_to_z.set(`${col[0]},${col[1]},${col[2]}`, i);
              m_zones.push({
                key: zk,
                colour: col,
                population: zc.population || {},
                pixels: []
              });
            }
          }

          for (let idx = 0; idx < n_pixels; idx++) {
            let p4 = idx*4;
            if (m_png.data[p4 + 3] === 0) {
              let r_row = Math.floor(idx/width);
              if (r_row <= 130 && pixel_domain[idx] === 1) pixel_domain[idx] = 0;
              continue;
            }
            let c_str = `${m_png.data[p4]},${m_png.data[p4 + 1]},${m_png.data[p4 + 2]}`;
            let z_idx = colour_to_z.get(c_str);
            if (z_idx !== undefined) {
              pixel_macro_zone[idx] = z_idx;
              m_zones[z_idx].pixels.push(idx);
              if (pixel_domain[idx] === 0) pixel_domain[idx] = 1;
            }
          }

          macro_entry = {
            id: manifest_obj.macro_mask.id,
            domain: m_json.domain || manifest_obj.macro_mask.domain || [100, 1900],
            zones: m_zones
          };
        }
      }

      //3. Load Priority 2 Specialist Masks
      for (let i = 0; i < manifest_obj.specialist_masks.length; i++) {
        let s_meta = manifest_obj.specialist_masks[i];
        let s_cfg_path = path.join(root_dir, s_meta.json5_path);
        let s_png_path = path.join(root_dir, s_meta.mask_path);
        if (!fs.existsSync(s_cfg_path) || !fs.existsSync(s_png_path)) continue;

        let s_json = JSON5.parse(fs.readFileSync(s_cfg_path, "utf8"));
        let s_png = PNG.sync.read(fs.readFileSync(s_png_path));
        let s_zones = [];
        let colour_to_z = new Map();
        let z_keys = Object.keys(s_json.regions || {});
        let s_idx = specialist_entries.length;
        let dom_code = (s_meta.domain_group === "belarus_ukraine") ? 2 : 1;

        for (let x = 0; x < z_keys.length; x++) {
          let zk = z_keys[x];
          let zc = s_json.regions[zk];
          let col = zc.colour || zc.color;
          if (Array.isArray(col) && col.length >= 3) {
            colour_to_z.set(`${col[0]},${col[1]},${col[2]}`, x);
            s_zones.push({
              key: zk,
              colour: col,
              population: zc.population || {},
              pixels: [],
              total_mask_pixels: 0,
              domain_fraction: 1.0
            });
          }
        }

        for (let idx = 0; idx < n_pixels; idx++) {
          let p4 = idx*4;
          if (s_png.data[p4 + 3] === 0) continue;
          let r = s_png.data[p4];
          let g = s_png.data[p4 + 1];
          let b = s_png.data[p4 + 2];
          if (r === 0 && g === 0 && b === 0) continue;
          let z_idx = colour_to_z.get(`${r},${g},${b}`);
          if (z_idx !== undefined) {
            s_zones[z_idx].total_mask_pixels++;
            if (pixel_domain[idx] === dom_code && pixel_spec_mask[idx] < 0) {
              pixel_spec_mask[idx] = s_idx;
              pixel_spec_zone[idx] = z_idx;
              s_zones[z_idx].pixels.push(idx);
            }
          }
        }

        for (let x = 0; x < s_zones.length; x++) {
          let z = s_zones[x];
          if (z.total_mask_pixels > 0 && z.pixels.length > 0)
            z.domain_fraction = z.pixels.length/z.total_mask_pixels;
        }

        //Load optional sub-mask modifiers (e.g. ecological_zones in russian_core_principalities)
        let pixel_sub_weight = null;
        if (s_meta.ecological_mask_path && s_json.sub_masks && s_json.sub_masks.ecological_zones) {
          let eco_png_path = path.join(root_dir, s_meta.ecological_mask_path);
          if (fs.existsSync(eco_png_path)) {
            let eco_png = PNG.sync.read(fs.readFileSync(eco_png_path));
            let eco_regions = s_json.sub_masks.ecological_zones.regions || {};
            let eco_col_to_mod = new Map();
            let eco_keys = Object.keys(eco_regions);
            for (let x = 0; x < eco_keys.length; x++) {
              let er = eco_regions[eco_keys[x]];
              let ecol = er.colour || er.color;
              let mod = Number(er.density_modifier || er.weight || 1.0);
              if (Array.isArray(ecol) && ecol.length >= 3 && Number.isFinite(mod) && mod > 0)
                eco_col_to_mod.set(`${ecol[0]},${ecol[1]},${ecol[2]}`, mod);
            }
            pixel_sub_weight = new Map();
            for (let x = 0; x < s_zones.length; x++) {
              let z_pixels = s_zones[x].pixels;
              for (let y = 0; y < z_pixels.length; y++) {
                let p_idx = z_pixels[y];
                let p4 = p_idx*4;
                if (eco_png.data[p4 + 3] > 0) {
                  let mod = eco_col_to_mod.get(`${eco_png.data[p4]},${eco_png.data[p4 + 1]},${eco_png.data[p4 + 2]}`);
                  if (mod !== undefined)
                    pixel_sub_weight.set(p_idx, Math.max(0.35, Math.min(3.0, Math.pow(mod, 0.35))));
                }
              }
            }
          }
        }

        specialist_entries.push({
          id: s_meta.id,
          domain: s_json.domain || s_meta.domain || [-10000, 1900],
          domain_code: dom_code,
          zones: s_zones,
          pixel_sub_weight: pixel_sub_weight
        });
      }

      //4. Collect all active domain pixels and compute exterior border distance for raised-cosine feathering
      let pixel_to_valid = new Int32Array(n_pixels).fill(-1);
      for (let idx = 0; idx < n_pixels; idx++) {
        if (pixel_domain[idx] > 0) {
          pixel_to_valid[idx] = valid_indices.length;
          valid_indices.push(idx);
        }
      }

      let n_valid = valid_indices.length;
      border_dist = new Uint8Array(n_valid).fill(feather_px + 1);
      feather_weights = new Float32Array(n_valid).fill(1.0);

      //Identify exterior land border pixels (adjacent to a non-POLARIS land pixel)
      let land_png_path = path.join(root_dir, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png");
      let is_foreign_land = new Uint8Array(n_pixels);
      if (fs.existsSync(land_png_path)) {
        let l_png = PNG.sync.read(fs.readFileSync(land_png_path));
        let l_dv = new DataView(l_png.data.buffer, l_png.data.byteOffset, l_png.data.byteLength);
        for (let idx = 0; idx < n_pixels; idx++) {
          if (pixel_domain[idx] > 0) continue;
          let p4 = idx*4;
          if (l_png.data[p4 + 3] > 0 && l_dv.getFloat32(p4, false) > 0)
            is_foreign_land[idx] = 1;
        }
      }

      let bfs_q = [];
      for (let i = 0; i < n_valid; i++) {
        let idx = valid_indices[i];
        let r = Math.floor(idx/width);
        let c = idx % width;
        let touches_foreign = false;
        if (r > 0 && is_foreign_land[idx - width]) touches_foreign = true;
        else if (r + 1 < height && is_foreign_land[idx + width]) touches_foreign = true;
        else if (c > 0 && is_foreign_land[idx - 1]) touches_foreign = true;
        else if (c + 1 < width && is_foreign_land[idx + 1]) touches_foreign = true;

        if (touches_foreign) {
          border_dist[i] = 1;
          bfs_q.push(i);
        }
      }

      let head = 0;
      while (head < bfs_q.length) {
        let curr_v = bfs_q[head++];
        let d = border_dist[curr_v];
        if (d >= feather_px) continue;
        let idx = valid_indices[curr_v];
        let r = Math.floor(idx/width);
        let c = idx % width;
        let nbrs = [
          (r > 0) ? idx - width : -1,
          (r + 1 < height) ? idx + width : -1,
          (c > 0) ? idx - 1 : -1,
          (c + 1 < width) ? idx + 1 : -1
        ];
        for (let x = 0; x < 4; x++) {
          let n_idx = nbrs[x];
          if (n_idx >= 0) {
            let nv = pixel_to_valid[n_idx];
            if (nv >= 0 && border_dist[nv] > d + 1) {
              border_dist[nv] = d + 1;
              bfs_q.push(nv);
            }
          }
        }
      }

      for (let i = 0; i < n_valid; i++) {
        let d = border_dist[i];
        if (d <= feather_px)
          feather_weights[i] = 0.5*(1 - Math.cos(Math.PI*(d/(feather_px + 1))));
      }

      //Return statement
      return {
        feather_weights: feather_weights,
        height: height,
        hyde_years: manifest_obj.hyde_years,
        macro_entry: macro_entry,
        manifest: manifest_obj,
        n_pixels: n_pixels,
        n_valid: n_valid,
        pixel_domain: pixel_domain,
        pixel_macro_zone: pixel_macro_zone,
        pixel_spec_mask: pixel_spec_mask,
        pixel_spec_zone: pixel_spec_zone,
        pixel_to_valid: pixel_to_valid,
        root_dir: root_dir,
        specialist_entries: specialist_entries,
        valid_indices: valid_indices,
        width: width
      };
    }


    /**
     * Step B: Loads and mosaics the `sites_IA_RAS` and `sites_belarus_ukraine` kriged population rasters for `arg1_year`.
     * @alias population_Substrata_russia.B_mosaicKrigedSubstrataForYear
     *
     * @param {Object} arg0_context - Output from `A_loadManifestAndMasks`
     * @param {number} arg1_year - Benchmark year (`-10000` to `1900`)
     *
     * @returns {Float32Array} Valid-cell array of length `arg0_context.n_valid`
     */
    static B_mosaicKrigedSubstrataForYear (arg0_context, arg1_year) {
      //Convert from parameters
      let context = arg0_context;
      let year = Number(arg1_year);

      //Declare local instance variables
      let bu_folder = path.join(context.root_dir, context.manifest.substrata_sources.belarus_ukraine.rasters_folder);
      let bu_path = path.join(bu_folder, `popc_${year}.png`);
      let mosaic_valid = new Float32Array(context.n_valid);
      let rus_folder = path.join(context.root_dir, context.manifest.substrata_sources.russia_ia_ras.rasters_folder);
      let rus_path = path.join(rus_folder, `popc_${year}.png`);

      //Function body
      if (fs.existsSync(rus_path)) {
        let rus_png = PNG.sync.read(fs.readFileSync(rus_path));
        let rus_dv = new DataView(rus_png.data.buffer, rus_png.data.byteOffset, rus_png.data.byteLength);
        for (let i = 0; i < context.n_valid; i++) {
          let idx = context.valid_indices[i];
          if (context.pixel_domain[idx] !== 1) continue;
          let p4 = idx*4;
          if (rus_png.data[p4 + 3] > 0) {
            let val = rus_dv.getFloat32(p4, false);
            if (Number.isFinite(val) && val > 0) mosaic_valid[i] = val;
          }
        }
      }

      if (year <= 1400 && fs.existsSync(bu_path)) {
        let bu_png = PNG.sync.read(fs.readFileSync(bu_path));
        let bu_dv = new DataView(bu_png.data.buffer, bu_png.data.byteOffset, bu_png.data.byteLength);
        for (let i = 0; i < context.n_valid; i++) {
          let idx = context.valid_indices[i];
          if (context.pixel_domain[idx] !== 2) continue;
          let p4 = idx*4;
          if (bu_png.data[p4 + 3] > 0) {
            let val = bu_dv.getFloat32(p4, false);
            if (Number.isFinite(val) && val > 0) mosaic_valid[i] = val;
          }
        }
      }

      //Return statement
      return mosaic_valid;
    }


    /**
     * Helper: Resolves a region's target population at `arg1_year` from its `population` dictionary,
     * supporting exact keys, `[min, max]` arrays, or linear interpolation between nearest benchmark years.
     * @alias population_Substrata_russia.resolveZoneTargetPopulation
     *
     * @param {Object} arg0_pop_dict
     * @param {number} arg1_year
     *
     * @returns {number}
     */
    static resolveZoneTargetPopulation (arg0_pop_dict, arg1_year) {
      //Convert from parameters
      let pop_dict = arg0_pop_dict;
      let year = Number(arg1_year);

      //Guard clauses
      if (!pop_dict || typeof pop_dict !== "object") return -1;

      //Function body
      function extractScalar (val) {
        if (Array.isArray(val) && val.length >= 2) {
          let a = Number(val[0]);
          let b = Number(val[1]);
          if (a > 0 && b > 0) return Math.sqrt(a*b);
          return 0.5*(a + b);
        }
        let n = Number(val);
        return Number.isFinite(n) ? n : -1;
      }

      if (pop_dict[year] !== undefined) {
        let exact = extractScalar(pop_dict[year]);
        if (exact >= 0) return exact;
      }

      let yrs = Object.keys(pop_dict).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
      if (yrs.length === 0) return -1;
      if (year <= yrs[0]) return extractScalar(pop_dict[yrs[0]]);
      if (year >= yrs[yrs.length - 1]) return extractScalar(pop_dict[yrs[yrs.length - 1]]);

      for (let i = 0; i < yrs.length - 1; i++) {
        if (year >= yrs[i] && year <= yrs[i + 1]) {
          let v0 = extractScalar(pop_dict[yrs[i]]);
          let v1 = extractScalar(pop_dict[yrs[i + 1]]);
          let t = (year - yrs[i])/Math.max(1, yrs[i + 1] - yrs[i]);
          return (1 - t)*v0 + t*v1;
        }
      }

      //Return statement
      return -1;
    }


    /**
     * Step C: Applies hierarchical areal-mask calibration (Priority 2 specialist masks + Priority 1 residual macro-mask)
     * and smooths the log-multiplier field across internal zone boundaries while preserving exact regional target sums.
     * @alias population_Substrata_russia.C_computeCalibratedFieldForYear
     *
     * @param {Object} arg0_context - Output from `A_loadManifestAndMasks`
     * @param {Float32Array} arg1_mosaic_valid - Unscaled mosaicked substratum on valid cells
     * @param {number} arg2_year - Benchmark year
     *
     * @returns {Float32Array} Calibrated and spatially smoothed valid-cell population array
     */
    static C_computeCalibratedFieldForYear (arg0_context, arg1_mosaic_valid, arg2_year) {
      //Convert from parameters
      let context = arg0_context;
      let mosaic_valid = arg1_mosaic_valid;
      let year = Number(arg2_year);

      //Declare local instance variables
      let blur_passes = (context.manifest.smoothing && context.manifest.smoothing.interior_multiplier_blur_passes) || 2;
      let blur_radius = (context.manifest.smoothing && context.manifest.smoothing.interior_multiplier_blur_radius_px) || 4;
      let calibrated = new Float32Array(context.n_valid);
      let log_mult = new Float32Array(context.n_valid);
      let n_valid = context.n_valid;
      let px_to_valid = context.pixel_to_valid;
      let zone_targets = [];

      //Function body
      for (let i = 0; i < n_valid; i++)
        calibrated[i] = mosaic_valid[i];

      //1. Priority 2 Specialist Masks calibration
      for (let i = 0; i < context.specialist_entries.length; i++) {
        let s_entry = context.specialist_entries[i];
        let eff_year = year;
        //For Kievan Rus masks at 1400 AD, use 1300 AD regional targets as anchor before blending with Statista 1400 AD
        if (s_entry.domain_code === 2 && year === 1400) eff_year = 1300;
        if (eff_year < s_entry.domain[0] || eff_year > s_entry.domain[1]) continue;

        let sub_weights = s_entry.pixel_sub_weight;
        for (let x = 0; x < s_entry.zones.length; x++) {
          let z = s_entry.zones[x];
          if (z.pixels.length === 0) continue;
          let raw_target_pop = this.resolveZoneTargetPopulation(z.population, eff_year);
          if (raw_target_pop < 0) continue;
          let target_pop = raw_target_pop*(z.domain_fraction !== undefined ? z.domain_fraction : 1.0);

          let current_sum = 0;
          for (let y = 0; y < z.pixels.length; y++) {
            let p_idx = z.pixels[y];
            let v_idx = px_to_valid[p_idx];
            if (v_idx >= 0) {
              let w = (sub_weights && sub_weights.has(p_idx)) ? sub_weights.get(p_idx) : 1.0;
              current_sum += mosaic_valid[v_idx]*w;
            }
          }

          let scalar = (current_sum > 0) ? (target_pop/current_sum) : 0;
          for (let y = 0; y < z.pixels.length; y++) {
            let p_idx = z.pixels[y];
            let v_idx = px_to_valid[p_idx];
            if (v_idx >= 0) {
              let w = (sub_weights && sub_weights.has(p_idx)) ? sub_weights.get(p_idx) : 1.0;
              let eff_s = Math.max(1e-4, Math.min(1e4, scalar*w));
              log_mult[v_idx] = Math.log(eff_s);
            }
          }

          zone_targets.push({
            pixels: z.pixels,
            target_pop: target_pop
          });
        }
      }

      //2. Priority 1 Macro-Mask (`migration_period`) residual calibration on uncovered Russia pixels
      if (context.macro_entry) {
        let m_entry = context.macro_entry;
        let m_year = Math.max(m_entry.domain[0], Math.min(m_entry.domain[1], year));
        for (let x = 0; x < m_entry.zones.length; x++) {
          let mz = m_entry.zones[x];
          if (mz.pixels.length === 0) continue;
          let macro_target = this.resolveZoneTargetPopulation(mz.population, m_year);
          if (macro_target <= 0) continue;

          //If year < 100 AD, scale macro_target proportionally to the specialist masks' prehistoric ratio
          let covered_raw_sum = 0;
          let covered_sum = 0;
          let uncovered_raw_sum = 0;
          let uncovered_pixels = [];

          for (let y = 0; y < mz.pixels.length; y++) {
            let p_idx = mz.pixels[y];
            let v_idx = px_to_valid[p_idx];
            if (v_idx < 0) continue;
            if (context.pixel_spec_mask[p_idx] >= 0) {
              covered_raw_sum += mosaic_valid[v_idx];
              covered_sum += mosaic_valid[v_idx]*Math.exp(log_mult[v_idx]);
            } else {
              uncovered_raw_sum += mosaic_valid[v_idx];
              uncovered_pixels.push(p_idx);
            }
          }

          if (uncovered_pixels.length > 0 && uncovered_raw_sum > 0) {
            let residual_target;
            if (year >= m_entry.domain[0]) {
              residual_target = Math.max(uncovered_raw_sum*0.25, macro_target - covered_sum);
            } else {
              //Pre-100 AD: scale the 100 AD residual target proportionally to the covered specialist ratio
              if (mz._covered_100 === undefined) {
                let c100 = 0;
                let seen_sz = new Map();
                for (let y = 0; y < mz.pixels.length; y++) {
                  let p_idx = mz.pixels[y];
                  let sm = context.pixel_spec_mask[p_idx];
                  let sz = context.pixel_spec_zone[p_idx];
                  if (sm >= 0 && sz >= 0) {
                    let k = `${sm}_${sz}`;
                    seen_sz.set(k, (seen_sz.get(k) || 0) + 1);
                  }
                }
                seen_sz.forEach((cnt, k) => {
                  let parts = k.split("_").map(Number);
                  let se = context.specialist_entries[parts[0]];
                  let zObj = se && se.zones[parts[1]];
                  if (zObj && zObj.pixels.length > 0) {
                    let t100 = this.resolveZoneTargetPopulation(zObj.population, m_entry.domain[0]);
                    if (t100 > 0)
                      c100 += t100*(zObj.domain_fraction || 1.0)*(cnt/zObj.pixels.length);
                  }
                });
                mz._covered_100 = c100;
              }
              let res_100 = Math.max(0, macro_target - (mz._covered_100 || 0));
              let ratio_pre = (mz._covered_100 > 0 && covered_sum > 0) ?
                (covered_sum/mz._covered_100) :
                ((covered_raw_sum > 0) ? (covered_sum/covered_raw_sum) : 1.0);
              residual_target = Math.max(uncovered_raw_sum*0.10, res_100*ratio_pre);
            }
            let res_scalar = Math.max(0.1, Math.min(10.0, residual_target/uncovered_raw_sum));
            let res_log = Math.log(res_scalar);
            for (let y = 0; y < uncovered_pixels.length; y++) {
              let v_idx = px_to_valid[uncovered_pixels[y]];
              if (v_idx >= 0) log_mult[v_idx] = res_log;
            }
            zone_targets.push({
              pixels: uncovered_pixels,
              target_pop: residual_target
            });
          }
        }
      }

      //3. Spatially smooth `log_mult` across internal zone boundaries within the same domain using separable box passes
      let width = context.width;
      let height = context.height;
      let valid_indices = context.valid_indices;
      let pixel_domain = context.pixel_domain;

      for (let p = 0; p < blur_passes; p++) {
        let horiz = new Float32Array(n_valid);
        for (let i = 0; i < n_valid; i++) {
          let idx = valid_indices[i];
          let dom = pixel_domain[idx];
          let row_start = Math.floor(idx/width)*width;
          let c = idx % width;
          let c0 = Math.max(0, c - blur_radius);
          let c1 = Math.min(width - 1, c + blur_radius);
          let sum = 0;
          let cnt = 0;
          for (let cx = c0; cx <= c1; cx++) {
            let n_idx = row_start + cx;
            if (pixel_domain[n_idx] === dom) {
              let nv = px_to_valid[n_idx];
              if (nv >= 0) {
                sum += log_mult[nv];
                cnt++;
              }
            }
          }
          horiz[i] = (cnt > 0) ? (sum/cnt) : log_mult[i];
        }

        for (let i = 0; i < n_valid; i++) {
          let idx = valid_indices[i];
          let dom = pixel_domain[idx];
          let r = Math.floor(idx/width);
          let c = idx % width;
          let r0 = Math.max(0, r - blur_radius);
          let r1 = Math.min(height - 1, r + blur_radius);
          let sum = 0;
          let cnt = 0;
          for (let ry = r0; ry <= r1; ry++) {
            let n_idx = ry*width + c;
            if (pixel_domain[n_idx] === dom) {
              let nv = px_to_valid[n_idx];
              if (nv >= 0) {
                sum += horiz[nv];
                cnt++;
              }
            }
          }
          log_mult[i] = (cnt > 0) ? (sum/cnt) : horiz[i];
        }
      }

      //4. Apply smoothed multipliers and gently re-normalise each zone so regional totals are conserved
      for (let i = 0; i < n_valid; i++)
        calibrated[i] = mosaic_valid[i]*Math.exp(log_mult[i]);

      for (let i = 0; i < zone_targets.length; i++) {
        let zt = zone_targets[i];
        let z_sum = 0;
        for (let x = 0; x < zt.pixels.length; x++) {
          let v_idx = px_to_valid[zt.pixels[x]];
          if (v_idx >= 0) z_sum += calibrated[v_idx];
        }
        if (z_sum > 0 && zt.target_pop >= 0) {
          let corr = zt.target_pop/z_sum;
          for (let x = 0; x < zt.pixels.length; x++) {
            let v_idx = px_to_valid[zt.pixels[x]];
            if (v_idx >= 0) calibrated[v_idx] *= corr;
          }
        }
      }

      //Return statement
      return calibrated;
    }


    /**
     * Step D: Executes the full timeseries calibration, temporal log-Laplacian smoothing, and raised-cosine border
     * compositing into `population_Substrata.outlier_removal/rasters_2.scaled_to_regions/`.
     * @alias population_Substrata_russia.processRasters
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Promise<Object>}
     */
    static async processRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let calibrated_series = [];
      let context = this.A_loadManifestAndMasks(options);
      let hyde_years = (options.hyde_years) ? options.hyde_years : context.hyde_years;
      let n_valid = context.n_valid;
      let n_years = hyde_years.length;
      let out_folder = options.output_folder ?
        options.output_folder :
        path.join(context.root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions");
      let start_ms = Date.now();
      let temp_weight = (context.manifest.smoothing && Number.isFinite(context.manifest.smoothing.temporal_log_Laplacian_weight)) ?
        context.manifest.smoothing.temporal_log_Laplacian_weight : 0.15;
      let year_summaries = {};

      //Function body
      console.log(`[population_Substrata_russia] Calibrating & mosaicking ${n_years} benchmark years across ${n_valid} domain pixels...`);

      //1. Compute spatially smoothed calibrated fields for all benchmark years
      for (let i = 0; i < n_years; i++) {
        let yr = hyde_years[i];
        let mosaic_valid = this.B_mosaicKrigedSubstrataForYear(context, yr);
        let cal_valid = this.C_computeCalibratedFieldForYear(context, mosaic_valid, yr);
        calibrated_series.push(cal_valid);
      }

      //2. Apply gentle temporal log-space smoothing across interior years so pixel trajectories have no step discontinuities
      let temporally_smoothed = calibrated_series.map((arr) => new Float32Array(arr));
      for (let t = 1; t < n_years - 1; t++) {
        let yr = hyde_years[t];
        let prev_arr = calibrated_series[t - 1];
        let curr_arr = calibrated_series[t];
        let next_arr = calibrated_series[t + 1];
        let out_arr = temporally_smoothed[t];
        let dt_prev = Math.max(1, yr - hyde_years[t - 1]);
        let dt_next = Math.max(1, hyde_years[t + 1] - yr);
        let alpha_t = dt_prev/(dt_prev + dt_next);

        for (let i = 0; i < n_valid; i++) {
          let idx = context.valid_indices[i];
          if (context.pixel_domain[idx] === 2 && yr > 1300) continue;
          let v_curr = curr_arr[i];
          let v_prev = prev_arr[i];
          let v_next = next_arr[i];
          if (v_curr > 0 && v_prev > 0 && v_next > 0) {
            let log_interp = (1 - alpha_t)*Math.log(v_prev) + alpha_t*Math.log(v_next);
            let log_curr = Math.log(v_curr);
            out_arr[i] = Math.exp((1 - temp_weight)*log_curr + temp_weight*log_interp);
          }
        }
      }

      //3. Composite into out_folder (`rasters_2.scaled_to_regions/popc_<year>.png`) with raised-cosine border feathering
      if (!fs.existsSync(out_folder)) fs.mkdirSync(out_folder, { recursive: true });

      //Compute 1300 AD calibration ratio on Belarus + Mainland Ukraine (`dom === 2`) so 1400..1790 AD transitions smoothly to 1800 AD
      let bu_ratio_1300 = 1.0;
      let idx_1300 = hyde_years.indexOf(1300);
      if (idx_1300 >= 0) {
        let p_1300 = path.join(out_folder, "popc_1300.png");
        let fb_1300 = path.join(
          context.root_dir,
          "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_1.northern_america/popc_1300.png"
        );
        let src_1300 = fs.existsSync(p_1300) ? p_1300 : (fs.existsSync(fb_1300) ? fb_1300 : null);
        if (src_1300) {
          let png_1300 = PNG.sync.read(fs.readFileSync(src_1300));
          let dv_1300 = new DataView(png_1300.data.buffer, png_1300.data.byteOffset, png_1300.data.byteLength);
          let cal_1300_arr = temporally_smoothed[idx_1300];
          let sum_cal_1300 = 0;
          let sum_base_1300 = 0;
          for (let i = 0; i < n_valid; i++) {
            let idx = context.valid_indices[i];
            if (context.pixel_domain[idx] !== 2) continue;
            sum_cal_1300 += cal_1300_arr[i];
            let p4 = idx*4;
            if (png_1300.data[p4 + 3] > 0) {
              let bv = dv_1300.getFloat32(p4, false);
              if (Number.isFinite(bv) && bv > 0) sum_base_1300 += bv;
            }
          }
          if (sum_base_1300 > 0 && sum_cal_1300 > sum_base_1300)
            bu_ratio_1300 = Math.min(3.0, sum_cal_1300/sum_base_1300);
        }
      }

      for (let t = 0; t < n_years; t++) {
        let yr = hyde_years[t];
        let cal_arr = temporally_smoothed[t];
        let target_png_path = path.join(out_folder, `popc_${yr}.png`);
        let fallback_png_path = path.join(
          context.root_dir,
          "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_1.northern_america",
          `popc_${yr}.png`
        );
        let src_png_path = fs.existsSync(target_png_path) ?
          target_png_path :
          (fs.existsSync(fallback_png_path) ? fallback_png_path : null);
        if (!src_png_path) continue;

        let base_png = PNG.sync.read(fs.readFileSync(src_png_path));
        let base_dv = new DataView(base_png.data.buffer, base_png.data.byteOffset, base_png.data.byteLength);
        let rus_sum = 0;
        let bu_sum = 0;
        let bu_post_mult = (yr > 1300 && yr < 1800) ?
          (1 + ((1800 - yr)/500)*(bu_ratio_1300 - 1)) : 1.0;

        for (let i = 0; i < n_valid; i++) {
          let idx = context.valid_indices[i];
          let dom = context.pixel_domain[idx];
          if (dom === 2 && yr >= 1800) {
            let p4_bu = idx*4;
            if (base_png.data[p4_bu + 3] > 0) {
              let bv_bu = base_dv.getFloat32(p4_bu, false);
              if (Number.isFinite(bv_bu) && bv_bu > 0) bu_sum += bv_bu;
            }
            continue;
          }

          let p4 = idx*4;
          let base_val = 0;
          if (base_png.data[p4 + 3] > 0) {
            let bv = base_dv.getFloat32(p4, false);
            if (Number.isFinite(bv) && bv > 0) base_val = bv;
          }

          let w_feather = context.feather_weights[i];
          let target_val = cal_arr[i];

          if (dom === 2 && yr === 1400) {
            //At 1400 AD on Belarus + Ukraine, blend 50% calibrated post-Mongol substratum with 50% tapered Statista baseline
            target_val = 0.5*cal_arr[i] + 0.5*(base_val*bu_post_mult);
          } else if (dom === 2 && yr > 1400 && yr < 1800) {
            //For 1500..1790 AD on Belarus + Ukraine, taper smoothly from 1300 AD calibration ratio to 1800 AD Statista baseline
            target_val = base_val*bu_post_mult;
          }

          let final_val = w_feather*target_val + (1 - w_feather)*base_val;
          if (final_val > 0) {
            base_dv.setFloat32(p4, final_val, false);
          } else {
            base_png.data[p4] = 0;
            base_png.data[p4 + 1] = 0;
            base_png.data[p4 + 2] = 0;
            base_png.data[p4 + 3] = 0;
          }

          if (dom === 1) rus_sum += final_val;
          else if (dom === 2) bu_sum += final_val;
        }

        fs.writeFileSync(target_png_path, PNG.sync.write(base_png));
        year_summaries[yr] = {
          russia_crimea: Math.round(rus_sum),
          belarus_ukraine: Math.round(bu_sum),
          combined: Math.round(rus_sum + bu_sum)
        };
      }

      console.log(`[population_Substrata_russia] Completed compositing ${n_years} benchmark rasters in ${((Date.now() - start_ms)/1000).toFixed(2)}s.`);

      //Return statement
      return {
        elapsed_seconds: Number(((Date.now() - start_ms)/1000).toFixed(2)),
        year_summaries: year_summaries
      };
    }


    /**
     * Step E: Preserves calibrated POLARIS (`dom === 1` for -10000..1900 AD, `dom === 2` for -10000..1400 AD)
     * populations in `rasters_3.scaled_to_global/` (while conserving the exact global population sum on non-POLARIS pixels)
     * and in `rasters_4.interpolated_to_GHSL/` (for 1800..1900 AD) so neither `C_scaleProcessedHYDEToGlobal` nor
     * `D_interpolateToGHSL` overwrites the calibrated literature-review figures.
     * @alias population_Substrata_russia.E_preserveDomainInGHSLInterpolatedRasters
     *
     * @param {Object} [arg0_options]
     */
    static E_preserveDomainInGHSLInterpolatedRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let context = this.A_loadManifestAndMasks(options);
      let ghsl_folder = path.join(
        context.root_dir,
        "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_4.interpolated_to_GHSL"
      );
      let global_folder = path.join(
        context.root_dir,
        "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_3.scaled_to_global"
      );
      let hyde_years = (options.hyde_years) ? options.hyde_years : context.hyde_years;
      let regions_folder = path.join(
        context.root_dir,
        "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions"
      );
      let years_1800_1900 = [1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890, 1900];

      //Guard clauses
      if (!fs.existsSync(global_folder)) return;

      //Function body
      //1. Preserve exact calibrated regional sums in `rasters_3.scaled_to_global/` while conserving global population sum
      if (fs.existsSync(regions_folder)) {
        for (let i = 0; i < hyde_years.length; i++) {
          let yr = hyde_years[i];
          let r2_path = path.join(regions_folder, `popc_${yr}.png`);
          let r3_path = path.join(global_folder, `popc_${yr}.png`);
          if (!fs.existsSync(r2_path) || !fs.existsSync(r3_path)) continue;

          let r2_png = PNG.sync.read(fs.readFileSync(r2_path));
          let r2_dv = new DataView(r2_png.data.buffer, r2_png.data.byteOffset, r2_png.data.byteLength);
          let r3_png = PNG.sync.read(fs.readFileSync(r3_path));
          let r3_dv = new DataView(r3_png.data.buffer, r3_png.data.byteOffset, r3_png.data.byteLength);

          let target_global_sum = 0;
          for (let idx = 0; idx < context.n_pixels; idx++) {
            let p4 = idx*4;
            if (r3_png.data[p4 + 3] > 0) {
              let v = r3_dv.getFloat32(p4, false);
              if (Number.isFinite(v) && v > 0) target_global_sum += v;
            }
          }

          let polaris_sum = 0;
          let is_polaris = new Uint8Array(context.n_pixels);
          for (let x = 0; x < context.n_valid; x++) {
            let idx = context.valid_indices[x];
            let dom = context.pixel_domain[idx];
            if (dom === 2 && yr > 1400) continue;
            is_polaris[idx] = 1;
            let p4 = idx*4;
            let v2 = (r2_png.data[p4 + 3] > 0) ? r2_dv.getFloat32(p4, false) : 0;
            let v3 = (r3_png.data[p4 + 3] > 0) ? r3_dv.getFloat32(p4, false) : 0;
            if (!Number.isFinite(v2) || v2 < 0) v2 = 0;
            if (!Number.isFinite(v3) || v3 < 0) v3 = 0;
            let wf = context.feather_weights[x];
            let v_out = wf*v2 + (1 - wf)*v3;
            if (v_out > 0) {
              r3_dv.setFloat32(p4, v_out, false);
              polaris_sum += v_out;
            } else {
              r3_png.data[p4] = 0;
              r3_png.data[p4 + 1] = 0;
              r3_png.data[p4 + 2] = 0;
              r3_png.data[p4 + 3] = 0;
            }
          }

          let rest_sum = 0;
          for (let idx = 0; idx < context.n_pixels; idx++) {
            if (is_polaris[idx]) continue;
            let p4 = idx*4;
            if (r3_png.data[p4 + 3] > 0) {
              let v = r3_dv.getFloat32(p4, false);
              if (Number.isFinite(v) && v > 0) rest_sum += v;
            }
          }

          if (rest_sum > 0 && target_global_sum > polaris_sum) {
            let rest_scalar = (target_global_sum - polaris_sum)/rest_sum;
            for (let idx = 0; idx < context.n_pixels; idx++) {
              if (is_polaris[idx]) continue;
              let p4 = idx*4;
              if (r3_png.data[p4 + 3] > 0) {
                let v = r3_dv.getFloat32(p4, false);
                if (Number.isFinite(v) && v > 0) r3_dv.setFloat32(p4, v*rest_scalar, false);
              }
            }
          }

          fs.writeFileSync(r3_path, PNG.sync.write(r3_png));
        }
      }

      if (!fs.existsSync(ghsl_folder)) return;

      //2. Preserve calibrated 1800..1900 AD Russia (`dom === 1`) in `rasters_4.interpolated_to_GHSL/`
      for (let i = 0; i < years_1800_1900.length; i++) {
        let yr = years_1800_1900[i];
        let r3_path = path.join(global_folder, `popc_${yr}.png`);
        let r4_path = path.join(ghsl_folder, `popc_${yr}.png`);
        if (!fs.existsSync(r3_path) || !fs.existsSync(r4_path)) continue;

        let r3_png = PNG.sync.read(fs.readFileSync(r3_path));
        let r3_dv = new DataView(r3_png.data.buffer, r3_png.data.byteOffset, r3_png.data.byteLength);
        let r4_png = PNG.sync.read(fs.readFileSync(r4_path));
        let r4_dv = new DataView(r4_png.data.buffer, r4_png.data.byteOffset, r4_png.data.byteLength);

        for (let x = 0; x < context.n_valid; x++) {
          let idx = context.valid_indices[x];
          if (context.pixel_domain[idx] !== 1) continue;
          let p4 = idx*4;
          let v3 = (r3_png.data[p4 + 3] > 0) ? r3_dv.getFloat32(p4, false) : 0;
          let v4 = (r4_png.data[p4 + 3] > 0) ? r4_dv.getFloat32(p4, false) : 0;
          if (!Number.isFinite(v3) || v3 < 0) v3 = 0;
          if (!Number.isFinite(v4) || v4 < 0) v4 = 0;

          let wf = context.feather_weights[x];
          let v_out = wf*v3 + (1 - wf)*v4;
          if (v_out > 0) {
            r4_dv.setFloat32(p4, v_out, false);
          } else {
            r4_png.data[p4] = 0;
            r4_png.data[p4 + 1] = 0;
            r4_png.data[p4 + 2] = 0;
            r4_png.data[p4 + 3] = 0;
          }
        }

        fs.writeFileSync(r4_path, PNG.sync.write(r4_png));
      }
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = global.population_Substrata_russia;

