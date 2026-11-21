//Initialise functions
{
  if (!global.population_Stadester_rasters) global.population_Stadester_rasters = {};
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
  if (!global.StadesterPartitionIO && typeof require !== "undefined")
    try { require(path.join(__dirname, "StadesterPartitionIO.js")); } catch (e) {}

  /**
   * Generates Stadestér Population rasters in parallel using GeoPNG.processTimeseriesParallel.
   * @alias population_Stadester_rasters.generatePopulationRastersParallel
   *
   * @param {Array<number>} arg0_years
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<Array<string>>}
   */
  population_Stadester_rasters.generatePopulationRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let cfg_cap = (GeoPNG.compute_limits && GeoPNG.compute_limits.cpu && GeoPNG.compute_limits.cpu.max_workers) ?
      Number(GeoPNG.compute_limits.cpu.max_workers) : 4;
    let default_concurrency = (typeof require !== "undefined") ? Math.min(cfg_cap, require("os").cpus().length || 4) : 4;
    let use_gpu_local = (options.use_gpu !== false && GeoPNG.gpu && GeoPNG.gpu.isAvailable());
    let worker_options = (population_Stadester_rasters.buildWorkerOptions) ?
      population_Stadester_rasters.buildWorkerOptions(options) : Object.assign({}, options);

    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: use_gpu_local ? 1 : Math.min(options.concurrency || default_concurrency, cfg_cap),
      items: years,
      name: use_gpu_local ? "Stadester Population Rasters [GPU]" : "Stadester Population Rasters",
      use_workers: use_gpu_local ? false : options.use_workers,
      task_generator: use_gpu_local ? null : ((year) => {
        return {
          type: "stadester_population_raster",
          options: worker_options,
          year: year
        };
      }),
      handler: async (year) => population_Stadester_rasters.generateStadesterPopulationRaster(year, options)
    });
  };


  /**
   * Generates Stadestér Rural rasters in parallel using GeoPNG.processTimeseriesParallel.
   * @alias population_Stadester_rasters.generateRuralRastersParallel
   *
   * @param {Array<number>} arg0_years
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<Array<string>>}
   */
  population_Stadester_rasters.generateRuralRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let cfg_cap = (GeoPNG.compute_limits && GeoPNG.compute_limits.cpu && GeoPNG.compute_limits.cpu.max_workers) ?
      Number(GeoPNG.compute_limits.cpu.max_workers) : 4;
    let default_concurrency = (typeof require !== "undefined") ? Math.min(cfg_cap, require("os").cpus().length || 4) : 4;
    let use_gpu_local = (options.use_gpu !== false && GeoPNG.gpu && GeoPNG.gpu.isAvailable());
    let worker_options = (population_Stadester_rasters.buildWorkerOptions) ?
      population_Stadester_rasters.buildWorkerOptions(options) : Object.assign({}, options);

    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: use_gpu_local ? 1 : Math.min(options.concurrency || default_concurrency, cfg_cap),
      items: years,
      name: use_gpu_local ? "Stadester Rural Rasters [GPU]" : "Stadester Rural Rasters",
      use_workers: use_gpu_local ? false : options.use_workers,
      task_generator: use_gpu_local ? null : ((year) => {
        if (year < -10000) {
          let rural_folder = options.input_rurc_folder || `${h2}/population_Stadester/stadester_rural_rasters/`;
          let output_file_path = path.join(rural_folder, `stadester_rural_${year}.png`);
          let substrata_file_path = population_Stadester_rasters.getSubstrataRasterPath(year, options);
          if (fs.existsSync(substrata_file_path)) {
            return {
              type: "copy",
              from_file_path: substrata_file_path,
              output_file_path: output_file_path
            };
          }
        }
        return {
          type: "stadester_rural_raster",
          options: worker_options,
          year: year
        };
      }),
      handler: async (year) => population_Stadester_rasters.generateStadesterRuralRaster(year, options)
    });
  };


  /**
   * Generates Stadestér Population raster and reconciles rural population to targets in float32.
   * @alias population_Stadester_rasters.generateStadesterPopulationRaster
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.generateStadesterPopulationRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let result = await population_Stadester_rasters.reconcileStadesterDemographics(year, options);

    //Return statement
    return result.pop_file_path;
  };


  /**
   * Generates Stadestér Rural raster for a single year by reconciling with national targets in float32.
   * @alias population_Stadester_rasters.generateStadesterRuralRaster
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.generateStadesterRuralRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let result = await population_Stadester_rasters.reconcileStadesterDemographics(year, options);

    //Return statement
    return result.rural_file_path;
  };


  /**
   * Caches active Viscount areal mask definitions and returns a flat pixel index to areal mask label mapping for a given year,
   * falling back to ISO3 country geocodes outside active Viscount masks.
   * @alias population_Stadester_rasters.getPixelToArealMaskMapping
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Array<string|null>|null}
   */
  population_Stadester_rasters.getPixelToArealMaskMapping = function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let best_dist_sq;
    let config_dir = "";
    let height = 2160;
    let is_viscount_px;
    let json5_lib = global.JSON5 || ((typeof require !== "undefined") ? require("json5") : null);
    let mask_map;
    let n_pixels = 4320*2160;
    let pixel_to_geocode = population_Stadester_rasters.getPixelToGeocodeMapping();
    let png_cls = (global.pngjs && global.pngjs.PNG) ? global.pngjs.PNG : (global.PNG || require("pngjs").PNG);
    let projects;
    let raw_land_mask = global._cached_stadester_raw_land_mask || null;
    let root_dir = "";
    let stamped_any = false;
    let width = 4320;

    //Guard clauses
    if (!pixel_to_geocode) return null;
    if (global._cached_stadester_areal_mask_year === year && global._cached_stadester_areal_mask_map && !options.viscount_config_dir && !options.project_root)
      return global._cached_stadester_areal_mask_map;

    //Function body
    if (!global._cached_stadester_viscount_masks || options.viscount_config_dir || options.project_root) {
      let candidate_dirs = [];

      if (options.viscount_config_dir) candidate_dirs.push(options.viscount_config_dir);
      if (typeof h3 !== "undefined") candidate_dirs.push(path.join(h3, "population_Substrata.viscount/config"));
      candidate_dirs.push(path.resolve(__dirname, "../../3.data_transform/population_Substrata.viscount/config"));
      for (let i = 0; i < candidate_dirs.length; i++) {
        if (candidate_dirs[i] && fs.existsSync(candidate_dirs[i])) { config_dir = candidate_dirs[i]; break; }
      }

      if (options.project_root) {
        root_dir = options.project_root;
      } else if (config_dir) {
        let up_root = path.resolve(config_dir, "../../../..");
        root_dir = fs.existsSync(path.join(up_root, "histmap")) ? up_root : process.cwd();
      } else {
        root_dir = process.cwd();
      }

      let cached_list = [];

      if (config_dir && fs.existsSync(config_dir) && json5_lib) {
        let cfg_files = fs.readdirSync(config_dir).filter((arg0_f) => arg0_f.endsWith(".json5") || arg0_f.endsWith(".json"));
        let descriptors = [];
        let owner_z_grid = new Uint8Array(n_pixels);
        let registry = (global.StadesterPartitionIO) ?
          global.StadesterPartitionIO.loadPrecedenceRegistry(options.precedence_config_path) : { projects_by_key: {} };

        for (let i = 0; i < cfg_files.length; i++) {
          let abs_cfg = path.join(config_dir, cfg_files[i]);
          try {
            let raw = json5_lib.parse(fs.readFileSync(abs_cfg, "utf8"));
            let proj_key = String(raw.key || "").toUpperCase();
            let reg_proj = (registry.projects_by_key && registry.projects_by_key[proj_key]) ? registry.projects_by_key[proj_key] : {};

            descriptors.push({
              ...reg_proj,
              ...raw,
              key: proj_key,
              order: Number(raw.order || reg_proj.order || 1),
              z_priority: Number(raw.z_priority || reg_proj.z_priority || raw.order || reg_proj.order || 1)
            });
          } catch (e) {}
        }
        descriptors.sort((arg0_a, arg1_b) => (arg1_b.z_priority || arg1_b.order || 0) - (arg0_a.z_priority || arg0_a.order || 0));

        for (let i = 0; i < descriptors.length; i++) {
          let desc = descriptors[i];
          let manifest_abs = desc.areal_masks_manifest ? path.resolve(root_dir, desc.areal_masks_manifest) : "";

          if (!manifest_abs || !fs.existsSync(manifest_abs)) continue;
          let is_polaris = (desc.pipeline_mode === "polaris_russia_delegate");
          let manifest_obj = json5_lib.parse(fs.readFileSync(manifest_abs, "utf8"));
          let proj_domain = new Uint8Array(n_pixels);
          let proj_z = Number(desc.z_priority || desc.order || 1);
          let sources = manifest_obj.substrata_sources || {};
          let src_keys = Object.keys(sources);

          for (let x = 0; x < src_keys.length; x++) {
            let src = sources[src_keys[x]];
            let dom_code = (src.domain_code !== undefined) ? src.domain_code : (x + 1);
            let domain_mask_abs = src.domain_mask_png ? path.resolve(root_dir, src.domain_mask_png) : "";
            let sample_yr = (src.sample_year !== undefined) ? src.sample_year : 1000;
            let sample_path = path.join(root_dir, src.rasters_folder || "", `popc_${sample_yr}.png`);

            if (domain_mask_abs && fs.existsSync(domain_mask_abs)) {
              let dm_png = png_cls.sync.read(fs.readFileSync(domain_mask_abs));
              for (let idx = 0; idx < n_pixels; idx++) {
                if (proj_domain[idx] !== 0) continue;
                let p4 = idx*4;
                if (dm_png.data[p4 + 3] > 0 && (dm_png.data[p4] | dm_png.data[p4 + 1] | dm_png.data[p4 + 2]) !== 0)
                  proj_domain[idx] = dom_code;
              }
              dm_png = null;
            }
            if (fs.existsSync(sample_path)) {
              let s_png = png_cls.sync.read(fs.readFileSync(sample_path));
              for (let idx = 0; idx < n_pixels; idx++) {
                if (proj_domain[idx] !== 0) continue;
                let p4 = idx*4;
                if ((s_png.data[p4] | s_png.data[p4 + 1] | s_png.data[p4 + 2] | s_png.data[p4 + 3]) !== 0)
                  proj_domain[idx] = dom_code;
              }
              s_png = null;
            }
          }

          if (is_polaris && manifest_obj.macro_mask) {
            let asc_path = path.join(root_dir, "histmap/1.data_raw/metadata_HYDE/general_files/sub_iso_cr.asc");
            let is_rus_iso = new Uint8Array(n_pixels);
            let m_png_abs = path.resolve(root_dir, manifest_obj.macro_mask.mask_path || "");

            if (fs.existsSync(asc_path)) {
              let asc_buf = fs.readFileSync(asc_path);
              let buf_len = asc_buf.length;
              let idx = 0;
              let pos = 0;
              let tok_count = 0;

              while (pos < buf_len && idx < n_pixels) {
                while (pos < buf_len && asc_buf[pos] <= 32) pos++;
                if (pos >= buf_len) break;
                if (tok_count < 12) {
                  while (pos < buf_len && asc_buf[pos] > 32) pos++;
                  tok_count++;
                  continue;
                }
                let neg = (asc_buf[pos] === 45);
                if (neg) pos++;
                let int_val = 0;
                while (pos < buf_len && asc_buf[pos] >= 48 && asc_buf[pos] <= 57) {
                  int_val = int_val*10 + (asc_buf[pos] - 48);
                  pos++;
                }
                if (pos < buf_len && asc_buf[pos] === 46) {
                  pos++;
                  if (pos < buf_len && asc_buf[pos] >= 53 && asc_buf[pos] <= 57) int_val++;
                }
                while (pos < buf_len && asc_buf[pos] > 32) pos++;
                let v = neg ? -int_val : int_val;
                if (v > 0) {
                  let iso_num = Math.floor(v/1000);
                  if (iso_num === 643 || iso_num === 999) is_rus_iso[idx] = 1;
                }
                idx++;
              }
              asc_buf = null;
            }
            if (fs.existsSync(m_png_abs)) {
              let mm_png = png_cls.sync.read(fs.readFileSync(m_png_abs));
              for (let idx = 0; idx < n_pixels; idx++) {
                let p4 = idx*4;
                if (mm_png.data[p4 + 3] === 0) {
                  if (Math.floor(idx/width) <= 130 && proj_domain[idx] === 1) proj_domain[idx] = 0;
                } else if (proj_domain[idx] === 0 && is_rus_iso[idx]) {
                  proj_domain[idx] = 1;
                }
              }
              mm_png = null;
            }
          }

          let has_domain = false;
          for (let idx = 0; idx < n_pixels; idx++) {
            if (proj_domain[idx] > 0 && owner_z_grid[idx] === 0) {
              owner_z_grid[idx] = proj_z;
              has_domain = true;
            }
          }
          if (!has_domain) continue;

          let polaris_spec_mask = is_polaris ? new Int16Array(n_pixels).fill(-1) : null;
          let polaris_spec_zone = is_polaris ? new Int16Array(n_pixels).fill(-1) : null;
          let loadMaskGroup = function (arg0_list, arg1_polaris_spec) {
            let list = Array.isArray(arg0_list) ? arg0_list : [];
            let out = [];

            for (let x = 0; x < list.length; x++) {
              let meta = list[x];
              let cfg_abs = path.resolve(root_dir, meta.json5_path || "");
              let png_abs = path.resolve(root_dir, meta.mask_path || "");

              if (!fs.existsSync(cfg_abs) || !fs.existsSync(png_abs)) continue;
              let col_map = new Map();
              let dom_code = (meta.domain_group === "belarus_ukraine") ? 2 : 1;
              let e_idx = out.length;
              let m_json = json5_lib.parse(fs.readFileSync(cfg_abs, "utf8"));
              let m_png = png_cls.sync.read(fs.readFileSync(png_abs));
              let r_keys = Object.keys(m_json.regions || {});
              let zones = [];

              for (let y = 0; y < r_keys.length; y++) {
                let zc = m_json.regions[r_keys[y]];
                let col = zc.colour || zc.color;
                if (Array.isArray(col) && col.length >= 3) {
                  col_map.set(`${col[0]},${col[1]},${col[2]}`, zones.length);
                  zones.push({ domain: zc.domain || null, key: r_keys[y], pixels: [] });
                }
              }

              for (let idx = 0; idx < n_pixels; idx++) {
                if (proj_domain[idx] === 0 || owner_z_grid[idx] !== proj_z) continue;
                if (arg1_polaris_spec && (proj_domain[idx] !== dom_code || polaris_spec_mask[idx] >= 0)) continue;
                let p4 = idx*4;
                if (m_png.data[p4 + 3] === 0) continue;
                let r = m_png.data[p4], g = m_png.data[p4 + 1], b = m_png.data[p4 + 2];
                if ((r | g | b) === 0) continue;
                let z_idx = col_map.get(`${r},${g},${b}`);

                if (z_idx !== undefined) {
                  zones[z_idx].pixels.push(idx);
                  if (arg1_polaris_spec) {
                    polaris_spec_mask[idx] = e_idx;
                    polaris_spec_zone[idx] = z_idx;
                  }
                }
              }
              m_png = null;
              out.push({ domain: meta.domain || m_json.domain || null, id: meta.id || path.basename(cfg_abs, path.extname(cfg_abs)), zones: zones });
            }
            return out;
          };

          let macro_list = manifest_obj.macro_mask ? loadMaskGroup([manifest_obj.macro_mask], false) : [];
          let nat_list = loadMaskGroup(manifest_obj.national_epoch_masks, false);
          let spec_list = loadMaskGroup(manifest_obj.specialist_masks, is_polaris);

          if (is_polaris && spec_list.length > 0) {
            let bfs_dist = new Uint8Array(n_pixels).fill(255);
            let bfs_q = [];
            let s_head = 0;

            for (let idx = 0; idx < n_pixels; idx++) {
              if (proj_domain[idx] > 0 && owner_z_grid[idx] === proj_z && polaris_spec_mask[idx] >= 0) {
                let lon = -180 + (((idx % width) + 0.5)/width)*360;

                if (proj_domain[idx] === 2 || lon < 42.5) {
                  bfs_dist[idx] = 0;
                  bfs_q.push(idx);
                }
              }
            }
            while (s_head < bfs_q.length) {
              let curr_idx = bfs_q[s_head++];
              let d = bfs_dist[curr_idx];

              if (d >= 120) continue;
              let c = curr_idx % width;
              let dom = proj_domain[curr_idx];
              let nbrs = [
                (Math.floor(curr_idx/width) > 0) ? curr_idx - width : -1,
                (Math.floor(curr_idx/width) + 1 < height) ? curr_idx + width : -1,
                (c > 0) ? curr_idx - 1 : -1,
                (c + 1 < width) ? curr_idx + 1 : -1
              ];
              let sm = polaris_spec_mask[curr_idx];
              let sz = polaris_spec_zone[curr_idx];

              for (let x = 0; x < 4; x++) {
                let n_idx = nbrs[x];

                if (n_idx >= 0 && proj_domain[n_idx] === dom && owner_z_grid[n_idx] === proj_z && polaris_spec_mask[n_idx] < 0) {
                  let n_lon = -180 + (((n_idx % width) + 0.5)/width)*360;

                  if (dom === 2 || n_lon < 42.0) {
                    polaris_spec_mask[n_idx] = sm;
                    polaris_spec_zone[n_idx] = sz;
                    bfs_dist[n_idx] = d + 1;
                    spec_list[sm].zones[sz].pixels.push(n_idx);
                    bfs_q.push(n_idx);
                  }
                }
              }
            }
          }

          let compactGroup = function (arg0_entries) {
            for (let x = 0; x < arg0_entries.length; x++) {
              let zones = arg0_entries[x].zones;

              for (let y = 0; y < zones.length; y++)
                zones[y].pixels = Int32Array.from(zones[y].pixels);
            }
            return arg0_entries;
          };

          cached_list.push({
            key: desc.key,
            macro_entry: compactGroup(macro_list)[0] || null,
            national_epoch_entries: compactGroup(nat_list),
            pipeline_mode: desc.pipeline_mode || "generic_viscount_mosaic",
            specialist_entries: compactGroup(spec_list)
          });
        }
      }

      if (!options.viscount_config_dir && !options.project_root)
        global._cached_stadester_viscount_masks = cached_list;
      projects = cached_list;
    } else {
      projects = global._cached_stadester_viscount_masks;
    }

    if (!projects || projects.length === 0) return pixel_to_geocode;

    let active_stamps = [];

    for (let i = 0; i < projects.length; i++) {
      let entries = [];
      let proj = projects[i];

      if (proj.pipeline_mode === "polaris_russia_delegate") {
        if (proj.macro_entry && year <= 1900) entries.push(proj.macro_entry);
        for (let x = 0; x < proj.specialist_entries.length; x++) {
          let sp = proj.specialist_entries[x];

          if (!sp.domain || (year >= sp.domain[0] && year <= sp.domain[1])) entries.push(sp);
        }
        if (year >= 1400) {
          for (let x = 0; x < proj.national_epoch_entries.length; x++) {
            let ne = proj.national_epoch_entries[x];

            if (!ne.domain || (year >= ne.domain[0] && year <= ne.domain[1])) entries.push(ne);
          }
        }
      } else {
        let groups = [
          proj.macro_entry ? [proj.macro_entry] : [],
          proj.specialist_entries || [],
          proj.national_epoch_entries || []
        ];

        for (let g = 0; g < groups.length; g++) {
          for (let x = 0; x < groups[g].length; x++) {
            let entry = groups[g][x];

            if (!entry.domain || (year >= entry.domain[0] && year <= entry.domain[1]))
              entries.push(entry);
          }
        }
      }

      for (let x = 0; x < entries.length; x++) {
        let entry = entries[x];

        for (let y = 0; y < entry.zones.length; y++) {
          let zone = entry.zones[y];

          if (zone.pixels.length === 0) continue;
          if (zone.domain && (year < zone.domain[0] || year > zone.domain[1])) continue;
          active_stamps.push({
            label: `V:${proj.key}:${entry.id}:${zone.key}`,
            pixels: zone.pixels
          });
        }
      }
    }

    if (active_stamps.length === 0) return pixel_to_geocode;

    is_viscount_px = new Uint8Array(n_pixels);
    mask_map = pixel_to_geocode.slice();

    for (let i = 0; i < active_stamps.length; i++) {
      let lbl = active_stamps[i].label;
      let px_arr = active_stamps[i].pixels;

      for (let x = 0; x < px_arr.length; x++) {
        let idx = px_arr[x];

        mask_map[idx] = lbl;
        is_viscount_px[idx] = 1;
        stamped_any = true;
      }
    }

    if (stamped_any) {
      best_dist_sq = new Uint8Array(n_pixels).fill(255);

      for (let i = 0; i < height; i++) {
        let row_offset = i*width;

        for (let x = 0; x < width; x++) {
          let idx = row_offset + x;

          if (is_viscount_px[idx] === 0) continue;
          let left_v = is_viscount_px[row_offset + ((x + width - 1) % width)];
          let right_v = is_viscount_px[row_offset + ((x + 1) % width)];
          let up_v = (i > 0) ? is_viscount_px[idx - width] : 1;
          let down_v = (i < height - 1) ? is_viscount_px[idx + width] : 1;

          if (left_v && right_v && up_v && down_v) continue;
          let lbl = mask_map[idx];

          for (let y = -2; y <= 2; y++) {
            let ny = i + y;

            if (ny < 0 || ny >= height) continue;
            let n_row = ny*width;

            for (let z = -2; z <= 2; z++) {
              if (y === 0 && z === 0) continue;
              let nx = (x + z + width) % width;
              let n_idx = n_row + nx;

              if (is_viscount_px[n_idx] === 0 && (!raw_land_mask || raw_land_mask[n_idx] === 0)) {
                let dist_sq = y*y + z*z;

                if (dist_sq < best_dist_sq[n_idx]) {
                  best_dist_sq[n_idx] = dist_sq;
                  mask_map[n_idx] = lbl;
                }
              }
            }
          }
        }
      }
    }

    if (!options.viscount_config_dir && !options.project_root) {
      global._cached_stadester_areal_mask_year = year;
      global._cached_stadester_areal_mask_map = mask_map;
      global._cached_stadester_compact_mask = null;
    }

    //Return statement
    return mask_map;
  };


  /**
   * Returns a GPU-ready compact Int32Array mask ID grid (`-1` for unmasked) for a given year.
   * @alias population_Stadester_rasters.getCompactArealMaskMapping
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {{id_grid: Int32Array, labels: Array<string>, num_masks: number}|null}
   */
  population_Stadester_rasters.getCompactArealMaskMapping = function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Guard clause
    if (!options.pixel_to_geocode && !options.viscount_config_dir && !options.project_root &&
      global._cached_stadester_compact_mask && global._cached_stadester_compact_mask.year === year)
      return global._cached_stadester_compact_mask;

    //Declare local instance variables
    let pixel_to_mask = (options.pixel_to_geocode) ?
      options.pixel_to_geocode : population_Stadester_rasters.getPixelToArealMaskMapping(year, options);
    if (!pixel_to_mask) return null;

    let id_grid = new Int32Array(pixel_to_mask.length);
    let label_to_id = new Map();
    let labels = [];

    for (let i = 0; i < pixel_to_mask.length; i++) {
      let lbl = pixel_to_mask[i];
      if (!lbl) {
        id_grid[i] = -1;
        continue;
      }
      let mid = label_to_id.get(lbl);
      if (mid === undefined) {
        mid = labels.length;
        label_to_id.set(lbl, mid);
        labels.push(lbl);
      }
      id_grid[i] = mid;
    }

    let compact = { id_grid: id_grid, labels: labels, num_masks: Math.max(1, labels.length), year: year };
    if (!options.pixel_to_geocode && !options.viscount_config_dir && !options.project_root)
      global._cached_stadester_compact_mask = compact;

    //Return statement
    return compact;
  };


  /**
   * Caches and returns a flat pixel index to ISO3 country code mapping.
   * @alias population_Stadester_rasters.getPixelToGeocodeMapping
   *
   * @returns {Array<string|null>}
   */
  population_Stadester_rasters.getPixelToGeocodeMapping = function () {
    //Declare local instance variables
    let best_dist_sq;
    let colourcodes;
    let geocode_img;
    let geocode_path;
    let land_map;
    let pixel_map;
    let raw_land_mask;
    let rgb_to_iso3;

    //Guard clauses
    if (global._cached_stadester_pixel_to_geocode)
      return global._cached_stadester_pixel_to_geocode;

    //Function body
    geocode_path = (typeof admin_modern !== "undefined" && admin_modern.input_geocodes_raster) ?
      admin_modern.input_geocodes_raster : `${h1}/admin_modern/geocodes.png`;

    if (!fs.existsSync(geocode_path)) return null;

    colourcodes = (typeof admin_modern !== "undefined" && admin_modern.getISO3ColourcodesObject) ?
      admin_modern.getISO3ColourcodesObject() : {};
    geocode_img = GeoPNG.loadImage(geocode_path);
    pixel_map = new Array(4320*2160);
    rgb_to_iso3 = {};

    let rgb_int_to_iso3 = new Map();
    for (let colour in colourcodes) {
      let codes = colourcodes[colour];
      if (codes && codes.length > 0) {
        let parts = colour.split(",");
        if (parts.length >= 3) {
          let rgb_int = ((parseInt(parts[0], 10) & 255) << 16) | ((parseInt(parts[1], 10) & 255) << 8) | (parseInt(parts[2], 10) & 255);
          rgb_int_to_iso3.set(rgb_int, codes[0]);
        }
      }
    }

    for (let i = 0; i < 4320*2160; i++) {
      let b = i*4;
      let rgb_int = (geocode_img.data[b] << 16) | (geocode_img.data[b + 1] << 8) | geocode_img.data[b + 2];
      pixel_map[i] = rgb_int_to_iso3.get(rgb_int) || null;
    }

    //Assign 2-pixel coastal fringe so harbour/island cities map to nearest land ISO3 geocode
    best_dist_sq = new Uint8Array(4320*2160);
    land_map = pixel_map.slice();
    raw_land_mask = new Uint8Array(4320*2160);
    for (let i = 0; i < 4320*2160; i++)
      if (land_map[i]) raw_land_mask[i] = 1;
    best_dist_sq.fill(255);
    for (let i = 0; i < 2160; i++) {
      let row_offset = i*4320;
      for (let x = 0; x < 4320; x++) {
        let idx = row_offset + x;
        let iso = land_map[idx];
        if (!iso) continue;

        let left_iso = land_map[row_offset + ((x + 4319) % 4320)];
        let right_iso = land_map[row_offset + ((x + 1) % 4320)];
        let up_iso = (i > 0) ? land_map[idx - 4320] : iso;
        let down_iso = (i < 2159) ? land_map[idx + 4320] : iso;
        if (left_iso && right_iso && up_iso && down_iso) continue;

        for (let y = -2; y <= 2; y++) {
          let ny = i + y;
          if (ny < 0 || ny >= 2160) continue;
          let n_row = ny*4320;
          for (let z = -2; z <= 2; z++) {
            if (y === 0 && z === 0) continue;
            let nx = (x + z + 4320) % 4320;
            let n_idx = n_row + nx;
            if (!land_map[n_idx]) {
              let dist_sq = y*y + z*z;
              if (dist_sq < best_dist_sq[n_idx]) {
                best_dist_sq[n_idx] = dist_sq;
                pixel_map[n_idx] = iso;
              }
            }
          }
        }
      }
    }

    global._cached_stadester_pixel_to_geocode = pixel_map;
    global._cached_stadester_raw_land_mask = raw_land_mask;

    //Return statement
    return pixel_map;
  };

  population_Stadester_rasters.getPixelToISO2Mapping = population_Stadester_rasters.getPixelToGeocodeMapping;


  /**
   * Prepares density raster (population / land area) in float32.
   * @alias population_Stadester_rasters.prepareDensityRaster
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.prepareDensityRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let landarea_file = (typeof metadata_HYDE !== "undefined" && metadata_HYDE.input_raster_land_area) ?
      metadata_HYDE.input_raster_land_area : `${h1}/metadata_HYDE/general_rasters/land_area.png`;
    let landarea_raster = null;
    let output_file_path = path.join(options.intermediate_popd_folder || `${h2}/population_Stadester/stadester_density_rasters/`, `stadester_density_${year}.png`);
    let pop_file_path = path.join(options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`, `stadester_population_${year}.png`);
    let pop_raster = null;

    //GPU-accelerated direct BE-RGBA density calculation on NVIDIA OpenCL
    if (options.use_gpu !== false && fs.existsSync(pop_file_path) && fs.existsSync(landarea_file) && GeoPNG.gpu && GeoPNG.gpu.isAvailable() && typeof GeoPNG.loadRawRGBAAsync === "function") {
      if (!global._cached_landarea_raw_rgba || global._cached_landarea_raw_path !== landarea_file) {
        global._cached_landarea_raw_rgba = await GeoPNG.loadRawRGBAAsync(landarea_file);
        global._cached_landarea_raw_path = landarea_file;
      }
      let pop_raw = await GeoPNG.loadRawRGBAAsync(pop_file_path);
      let land_raw = global._cached_landarea_raw_rgba;
      if (pop_raw && pop_raw.data && land_raw && land_raw.data && pop_raw.data.byteLength === land_raw.data.byteLength) {
        let dens_rgba = await GeoPNG.gpu.binaryOpRGBA(pop_raw.data, land_raw.data, "density_stadester", {
          format_1: "float32",
          format_2: "int32"
        });
        if (dens_rgba) {
          await GeoPNG.saveRawRGBAAsync({
            data: dens_rgba,
            file_path: output_file_path,
            height: pop_raw.height,
            width: pop_raw.width
          });
          console.log(`- Saved Stadestér Density raster for ${year} [GPU]: ${output_file_path}`);

          //Return statement
          return output_file_path;
        }
      }
    }

    //Function body (fast async CPU fallback)
    if (fs.existsSync(landarea_file)) {
      if (!global._cached_landarea_raster || global._cached_landarea_raster_path !== landarea_file) {
        global._cached_landarea_raster = await GeoPNG.loadNumberRasterImageAsync(landarea_file, { format: "int32" });
        global._cached_landarea_raster_path = landarea_file;
      }
      landarea_raster = global._cached_landarea_raster;
    }
    if (fs.existsSync(pop_file_path))
      pop_raster = await GeoPNG.loadNumberRasterImageAsync(pop_file_path, { format: "float32" });

    let dens_data = new Float32Array(4320*2160);
    for (let i = 0; i < dens_data.length; i++) {
      let km2 = (landarea_raster && landarea_raster.data[i]) ? landarea_raster.data[i] : 0;
      let p = (pop_raster && pop_raster.data[i]) ? pop_raster.data[i] : 0;
      if (km2 <= 0 || p < 0.01) continue;
      let val = p/km2;
      if (isFinite(val)) dens_data[i] = val;
    }

    await GeoPNG.saveNumberRasterImageAsync({
      data: dens_data,
      file_path: output_file_path,
      format: "float32",
      height: 2160,
      return_data: false,
      width: 4320
    });

    console.log(`- Saved Stadestér Density raster for ${year}: ${output_file_path}`);

    //Return statement
    return output_file_path;
  };


  /**
   * Prepares Stadestér Density rasters in parallel using GeoPNG.processTimeseriesParallel.
   * @alias population_Stadester_rasters.prepareDensityRastersParallel
   *
   * @param {Array<number>} arg0_years
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<Array<string>>}
   */
  population_Stadester_rasters.prepareDensityRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let cfg_cap = (GeoPNG.compute_limits && GeoPNG.compute_limits.cpu && GeoPNG.compute_limits.cpu.max_workers) ?
      Number(GeoPNG.compute_limits.cpu.max_workers) : 4;
    let default_concurrency = (typeof require !== "undefined") ? Math.min(cfg_cap, require("os").cpus().length || 4) : 4;
    let input_popc = options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`;
    let intermediate_popd = options.intermediate_popd_folder || `${h2}/population_Stadester/stadester_density_rasters/`;
    let landarea_file = (typeof metadata_HYDE !== "undefined" && metadata_HYDE.input_raster_land_area) ?
      metadata_HYDE.input_raster_land_area : `${h1}/metadata_HYDE/general_rasters/land_area.png`;
    let use_gpu_local = (options.use_gpu !== false && GeoPNG.gpu && GeoPNG.gpu.isAvailable());

    //Function body
    if (!fs.existsSync(intermediate_popd)) fs.mkdirSync(intermediate_popd, { recursive: true });

    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: use_gpu_local ? 1 : Math.min(options.concurrency || default_concurrency, cfg_cap),
      items: years,
      name: use_gpu_local ? "Stadester Density Rasters [GPU]" : "Stadester Density Rasters",
      use_workers: use_gpu_local ? false : options.use_workers,
      task_generator: use_gpu_local ? null : ((year) => {
        let output_file_path = path.join(intermediate_popd, `stadester_density_${year}.png`);
        let pop_file_path = path.join(input_popc, `stadester_population_${year}.png`);
        if (!fs.existsSync(pop_file_path) || !fs.existsSync(landarea_file)) return null;

        return {
          type: "raster_operation",
          format: "float32",
          format_1: "float32",
          format_2: "int32",
          input_path_1: pop_file_path,
          input_path_2: landarea_file,
          op: "density_stadester",
          operation: "density_stadester",
          output_path: output_file_path
        };
      }),
      handler: async (year) => population_Stadester_rasters.prepareDensityRaster(year, options)
    });
  };


  /**
   * Reconciles Rural, Urban, and Total Population rasters using direct top-down areal scaling in float32.
   * Sums combined `rural + urban` per areal mask (active Viscount mask or ISO3 country) and scales all pixels
   * in the mask uniformly to satisfy the top-down substrata constraint without zeroing out rural pixels.
   * @alias population_Stadester_rasters.reconcileStadesterDemographics
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<Object>} { pop_file_path, rural_file_path, urban_file_path }
   */
  population_Stadester_rasters.reconcileStadesterDemographics = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let base_file_path = null;
    let default_urb_folder = `${h2}/population_Stadester/stadester_urban_rasters/`;
    let fallback_scalar = 1;
    let global_comb = 0;
    let global_sub = 0;
    let mask_comb = {};
    let mask_scalar = {};
    let mask_sub = {};
    let pixel_to_mask = (options.pixel_to_geocode) ?
      options.pixel_to_geocode : population_Stadester_rasters.getPixelToArealMaskMapping(year, options);
    let pop_file_path = path.join(options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`, `stadester_population_${year}.png`);
    let pop_folder = path.dirname(pop_file_path);
    let raw_rural_data = new Float32Array(4320*2160);
    let raw_urban_data = new Float32Array(4320*2160);
    let rural_data = new Float32Array(4320*2160);
    let rural_file_path = path.join(options.input_rurc_folder || `${h2}/population_Stadester/stadester_rural_rasters/`, `stadester_rural_${year}.png`);
    let rural_folder = path.dirname(rural_file_path);
    let sub_urban_data = null;
    let substrata_file_path = population_Stadester_rasters.getSubstrataRasterPath(year, options);
    let substrata_raster = null;
    let total_data = new Float32Array(4320*2160);
    let total_pixels = 4320*2160;
    let urban_data = new Float32Array(4320*2160);
    let urban_file_path = path.join(options.input_urbc_folder || default_urb_folder, `stadester_urban_${year}.png`);
    let urban_folder = path.dirname(urban_file_path);
    let urban_raster = null;

    //Ensure destination directories exist
    if (!fs.existsSync(pop_folder)) fs.mkdirSync(pop_folder, { recursive: true });
    if (!fs.existsSync(rural_folder)) fs.mkdirSync(rural_folder, { recursive: true });
    if (!fs.existsSync(urban_folder)) fs.mkdirSync(urban_folder, { recursive: true });

    //Guard clauses
    if (year < -10000) {
      if (fs.existsSync(substrata_file_path)) {
        fs.copyFileSync(substrata_file_path, rural_file_path);
        fs.copyFileSync(substrata_file_path, pop_file_path);
        console.log(`- Copied Stadestér Rural & Pop rasters from substrata for ${year}`);
      }
      return { pop_file_path: pop_file_path, rural_file_path: rural_file_path, urban_file_path: urban_file_path };
    }

    //Function body
    if (options.intermediate_base_folder) {
      base_file_path = path.join(options.intermediate_base_folder, `stadester_base_${year}.png`);
    } else if (!options.input_urbc_folder || path.resolve(options.input_urbc_folder) === path.resolve(default_urb_folder)) {
      base_file_path = path.join(`${h2}/population_Stadester/stadester_base_rasters/`, `stadester_base_${year}.png`);
    }

    //GPU-accelerated direct BE-RGBA two-pass reconciliation on NVIDIA OpenCL
    if (options.use_gpu !== false && !options.substrata_raster && !options.urban_raster && GeoPNG.gpu && GeoPNG.gpu.isAvailable() && typeof GeoPNG.loadRawRGBAAsync === "function") {
      let compact_mask = population_Stadester_rasters.getCompactArealMaskMapping(year, options);
      let resolved_urb_path = (base_file_path && fs.existsSync(base_file_path)) ? base_file_path : urban_file_path;
      if (!fs.existsSync(resolved_urb_path)) {
        await population_Stadester_rasters.generateStadesterUrbanRaster(year, options);
        resolved_urb_path = urban_file_path;
      }

      let [sub_raw, urb_raw] = await Promise.all([
        fs.existsSync(substrata_file_path) ? GeoPNG.loadRawRGBAAsync(substrata_file_path) : Promise.resolve(null),
        fs.existsSync(resolved_urb_path) ? GeoPNG.loadRawRGBAAsync(resolved_urb_path) : Promise.resolve(null)
      ]);
      let zero_rgba = Buffer.alloc(total_pixels*4, 0);
      let substrata_rgba = (sub_raw && sub_raw.data) ? sub_raw.data : zero_rgba;
      let urban_rgba = (urb_raw && urb_raw.data) ? urb_raw.data : zero_rgba;
      let mask_ids = (compact_mask && compact_mask.id_grid) ? compact_mask.id_grid : new Int32Array(total_pixels).fill(-1);
      let num_masks = (compact_mask && compact_mask.num_masks) ? compact_mask.num_masks : 1;

      sub_urban_data = (options.sub_urban_data) ?
        options.sub_urban_data :
        population_Stadester_rasters.getSubUrbanSettlementsData(year, options);

      let gpu_res = await GeoPNG.gpu.reconcileDemographicsRGBA({
        mask_ids: mask_ids,
        num_masks: num_masks,
        sub_urban_f32: sub_urban_data,
        substrata_rgba: substrata_rgba,
        urban_rgba: urban_rgba
      });

      if (gpu_res) {
        await Promise.all([
          GeoPNG.saveRawRGBAAsync({ data: gpu_res.rural_rgba, file_path: rural_file_path, height: 2160, width: 4320 }),
          GeoPNG.saveRawRGBAAsync({ data: gpu_res.total_rgba, file_path: pop_file_path, height: 2160, width: 4320 }),
          GeoPNG.saveRawRGBAAsync({ data: gpu_res.urban_rgba, file_path: urban_file_path, height: 2160, width: 4320 })
        ]);
        gpu_res = null;
        sub_urban_data = null;
        console.log(`- Saved reconciled Stadestér Urban, Rural & Pop rasters for ${year} [GPU]: Total=${pop_file_path}`);

        //Return statement
        return { pop_file_path: pop_file_path, rural_file_path: rural_file_path, urban_file_path: urban_file_path };
      }
    }

    if (options.substrata_raster) {
      substrata_raster = options.substrata_raster;
    } else if (fs.existsSync(substrata_file_path)) {
      substrata_raster = await GeoPNG.loadNumberRasterImageAsync(substrata_file_path, { format: "float32" });
    }

    if (options.urban_raster) {
      urban_raster = options.urban_raster;
    } else if (base_file_path && fs.existsSync(base_file_path)) {
      urban_raster = await GeoPNG.loadNumberRasterImageAsync(base_file_path, { format: "float32" });
    } else if (fs.existsSync(urban_file_path)) {
      urban_raster = await GeoPNG.loadNumberRasterImageAsync(urban_file_path, { format: "float32" });
    } else {
      await population_Stadester_rasters.generateStadesterUrbanRaster(year, options);
      if (fs.existsSync(urban_file_path))
        urban_raster = await GeoPNG.loadNumberRasterImageAsync(urban_file_path, { format: "float32" });
    }

    //Load sub-5k settlement populations from stadester so small settlements are anchored in rural & total rasters
    sub_urban_data = (options.sub_urban_data) ?
      options.sub_urban_data :
      population_Stadester_rasters.getSubUrbanSettlementsData(year, options);

    //Pass 1: Accumulate Substrata target, unscaled Urban (5k+), unscaled Rural (incl. <5k), and combined totals per areal mask
    for (let i = 0; i < total_pixels; i++) {
      let s = (substrata_raster && substrata_raster.data[i]) ? substrata_raster.data[i] : 0;
      let sub_u = (sub_urban_data && sub_urban_data[i]) ? sub_urban_data[i] : 0;
      let u_raw = (urban_raster && urban_raster.data[i]) ? urban_raster.data[i] : 0;
      let u = (u_raw >= 0.01) ? u_raw : 0;
      let settled = u + sub_u;
      let rr = sub_u + Math.max(0, s - settled);
      let comb = rr + u;

      raw_rural_data[i] = rr;
      raw_urban_data[i] = u;

      global_comb += comb;
      global_sub += s;

      if (pixel_to_mask) {
        let m = pixel_to_mask[i];

        if (m) {
          mask_comb[m] = (mask_comb[m] || 0) + comb;
          mask_sub[m] = (mask_sub[m] || 0) + s;
        }
      }
    }

    //Compute uniform areal scalars per mask
    fallback_scalar = (global_comb > 0 && global_sub > 0) ? (global_sub/global_comb) : 1;
    if (pixel_to_mask) {
      let all_masks = Object.keys(mask_comb);

      for (let i = 0; i < all_masks.length; i++) {
        let m = all_masks[i];
        let c_sum = mask_comb[m] || 0;
        let s_sum = mask_sub[m] || 0;

        if (s_sum > 0 && c_sum > 0) {
          mask_scalar[m] = s_sum/c_sum;
        } else if (s_sum <= 0 && c_sum > 0) {
          mask_scalar[m] = fallback_scalar;
        } else {
          mask_scalar[m] = 1;
        }
      }
    }

    //Pass 2: Multiply both rural and urban pixels in each areal mask by its scalar so Rural + Urban matches top-down target
    for (let i = 0; i < total_pixels; i++) {
      let m = pixel_to_mask ? pixel_to_mask[i] : null;
      let sc = (m && mask_scalar[m] !== undefined) ? mask_scalar[m] : fallback_scalar;
      let r = raw_rural_data[i]*sc;
      let u = raw_urban_data[i]*sc;

      if (u > 0 && u < 0.01) {
        r += u;
        u = 0;
      }

      rural_data[i] = (r >= 1e-6) ? r : 0;
      urban_data[i] = u;
      let tot = urban_data[i] + rural_data[i];
      total_data[i] = (tot >= 1e-6) ? tot : 0;
    }

    //Save Rural, Total Population, and synchronised Urban rasters via fast async native PNG encoder
    await Promise.all([
      GeoPNG.saveNumberRasterImageAsync({
        data: rural_data,
        file_path: rural_file_path,
        format: "float32",
        height: 2160,
        return_data: false,
        width: 4320
      }),
      GeoPNG.saveNumberRasterImageAsync({
        data: total_data,
        file_path: pop_file_path,
        format: "float32",
        height: 2160,
        return_data: false,
        width: 4320
      }),
      GeoPNG.saveNumberRasterImageAsync({
        data: urban_data,
        file_path: urban_file_path,
        format: "float32",
        height: 2160,
        return_data: false,
        width: 4320
      })
    ]);

    raw_rural_data = null;
    raw_urban_data = null;
    rural_data = null;
    sub_urban_data = null;
    substrata_raster = null;
    total_data = null;
    urban_data = null;
    urban_raster = null;

    console.log(`- Saved reconciled Stadestér Urban, Rural & Pop rasters for ${year}: Total=${pop_file_path}`);

    //Return statement
    return { pop_file_path: pop_file_path, rural_file_path: rural_file_path, urban_file_path: urban_file_path };
  };
}
