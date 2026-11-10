//Initialise functions
{
  if (!global.population_c14bazAAR_binning) global.population_c14bazAAR_binning = {};

  /**
   * Pre-indexes WMO watersheds across modern ISO3 country boundaries into (watershed, ISO3) chunks,
   * recording chunk pixel arrays, land areas, and 8-connected cross-border pixel pairs and collars
   * for pre-1 AD fractional binning border reconciliation.
   * @alias population_c14bazAAR_binning.buildWatershedISO3ChunkIndex
   *
   * @param {Object} [arg0_options]
   *  @param {string} [arg0_options.input_land_area_raster]
   *  @param {string} [arg0_options.input_wmobb_raster]
   *  @param {Int32Array|Float32Array} [arg0_options.land_area_data]
   *  @param {Array<string|null>} [arg0_options.pixel_to_geocode]
   *  @param {Int32Array} [arg0_options.wmobb_data]
   *
   * @returns {Object} Pre-indexed multi-ISO3 watershed chunk topology.
   */
  population_c14bazAAR_binning.buildWatershedISO3ChunkIndex = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let all_basin_ids = [];
    let basin_chunks_temp = {};
    let basins_obj = {};
    let c14_cls = global.population_c14bazAAR || {};
    let geocode_img = null;
    let geocode_obj = null;
    let geocode_path = "";
    let height = 2160;
    let land_area_data = options.land_area_data || null;
    let land_area_path = options.input_land_area_raster || c14_cls.input_land_area_raster;
    let land_area_raster = null;
    let multi_basin_keys = [];
    let neighbour_offsets = [[0, 1, 1.0], [1, -1, 0.5], [1, 0, 1.0], [1, 1, 0.5]];
    let pixel_to_geocode = options.pixel_to_geocode || null;
    let rgb_to_iso3 = {};
    let total_chunks = 0;
    let total_pixels = 0;
    let width = 4320;
    let wmobb_data = options.wmobb_data || null;
    let wmobb_path = options.input_wmobb_raster || c14_cls.input_wmobb_raster;
    let wmobb_raster = null;

    //Guard clauses
    if (!wmobb_data) {
      if (!wmobb_path || !fs.existsSync(wmobb_path)) {
        console.error("- [population_c14bazAAR_binning.buildWatershedISO3ChunkIndex] Missing wmobb_raster.");
        return { basins_obj: {}, multi_basin_keys: [], total_chunks: 0, total_multi_basins: 0 };
      }
      wmobb_raster = GeoPNG.loadNumberRasterImage(wmobb_path, { format: "int32" });
      wmobb_data = wmobb_raster.data;
      height = wmobb_raster.height || 2160;
      width = wmobb_raster.width || 4320;
    }
    if (!land_area_data) {
      if (!land_area_path || !fs.existsSync(land_area_path)) {
        console.error("- [population_c14bazAAR_binning.buildWatershedISO3ChunkIndex] Missing land_area_raster.");
        return { basins_obj: {}, multi_basin_keys: [], total_chunks: 0, total_multi_basins: 0 };
      }
      land_area_raster = GeoPNG.loadNumberRasterImage(land_area_path, { format: "int32" });
      land_area_data = land_area_raster.data;
    }


    if (!pixel_to_geocode && typeof population_Stadester_rasters !== "undefined" && typeof population_Stadester_rasters.getPixelToGeocodeMapping === "function")
      pixel_to_geocode = population_Stadester_rasters.getPixelToGeocodeMapping();

    if (!pixel_to_geocode) {
      geocode_path = (typeof admin_modern !== "undefined" && admin_modern.input_geocodes_raster) ?
        admin_modern.input_geocodes_raster : `${global.h1 || "./histmap/1.data_raw/"}admin_modern/geocodes.png`;
      if (fs.existsSync(geocode_path) && typeof admin_modern !== "undefined" && typeof admin_modern.getISO3ColourcodesObject === "function") {
        geocode_obj = admin_modern.getISO3ColourcodesObject();
        geocode_img = GeoPNG.loadImage(geocode_path);
        pixel_to_geocode = new Array(width*height);
        for (let local_colour in geocode_obj) {
          let local_codes = geocode_obj[local_colour];
          if (local_codes && local_codes.length > 0)
            rgb_to_iso3[local_colour.split(",").slice(0, 3).join(",")] = local_codes[0];
        }
        for (let i = 0; i < width*height; i++) {
          let local_b = i*4;
          let local_rgb = `${geocode_img.data[local_b]},${geocode_img.data[local_b + 1]},${geocode_img.data[local_b + 2]}`;
          pixel_to_geocode[i] = rgb_to_iso3[local_rgb] || null;
        }
      }
    }

    if (!pixel_to_geocode) {
      console.error("- [population_c14bazAAR_binning.buildWatershedISO3ChunkIndex] Missing pixel_to_geocode mapping.");
      return { basins_obj: {}, multi_basin_keys: [], total_chunks: 0, total_multi_basins: 0 };
    }

    total_pixels = width*height;

    //1. Partition habitable watershed pixels into (watershed, ISO3) chunks
    for (let i = 0; i < total_pixels; i++) {
      let local_area = land_area_data[i] || 0;
      let local_b = wmobb_data[i];
      let local_iso = pixel_to_geocode[i];

      if (local_b > 0 && local_area > 0 && local_iso) {
        let local_b_key = String(local_b);
        if (!basin_chunks_temp[local_b_key]) basin_chunks_temp[local_b_key] = {};
        if (!basin_chunks_temp[local_b_key][local_iso])
          basin_chunks_temp[local_b_key][local_iso] = { area_km2: 0, pixels: [] };
        basin_chunks_temp[local_b_key][local_iso].area_km2 += local_area;
        basin_chunks_temp[local_b_key][local_iso].pixels.push(i);
      }
    }

    all_basin_ids = Object.keys(basin_chunks_temp).sort((a, b) => Number(a) - Number(b));
    for (let i = 0; i < all_basin_ids.length; i++) {
      let local_b_key = all_basin_ids[i];
      let local_iso_keys = Object.keys(basin_chunks_temp[local_b_key]).sort();

      if (local_iso_keys.length >= 2) {
        let local_chunks_array = [];
        let local_iso_to_idx = {};

        for (let x = 0; x < local_iso_keys.length; x++) {
          let local_iso = local_iso_keys[x];
          let local_raw = basin_chunks_temp[local_b_key][local_iso];
          local_iso_to_idx[local_iso] = x;
          local_chunks_array.push({
            area_km2: local_raw.area_km2,
            iso3: local_iso,
            pixels_array: new Int32Array(local_raw.pixels)
          });
        }

        basins_obj[local_b_key] = {
          chunks_array: local_chunks_array,
          edges_array: [],
          edges_temp_obj: {},
          iso_to_idx: local_iso_to_idx
        };
        multi_basin_keys.push(local_b_key);
        total_chunks += local_chunks_array.length;
      }
    }
    basin_chunks_temp = null;

    //2. Scan 8-connected habitable land pixel pairs inside multi-ISO3 watersheds
    for (let i = 0; i < height; i++) {
      let local_row = i*width;
      for (let x = 0; x < width; x++) {
        let local_p1 = local_row + x;
        let local_b1 = wmobb_data[local_p1];
        if (local_b1 <= 0) continue;

        let local_b_entry = basins_obj[String(local_b1)];
        if (!local_b_entry) continue;

        let local_a1 = land_area_data[local_p1] || 0;
        let local_iso1 = pixel_to_geocode[local_p1];
        if (local_a1 <= 0 || !local_iso1) continue;

        let local_u1 = local_b_entry.iso_to_idx[local_iso1];
        if (local_u1 === undefined) continue;

        for (let y = 0; y < neighbour_offsets.length; y++) {
          let local_dy = neighbour_offsets[y][0];
          let local_dx = neighbour_offsets[y][1];
          let local_cw = neighbour_offsets[y][2];
          let local_ny = i + local_dy;

          if (local_ny < 0 || local_ny >= height) continue;
          let local_nx = (x + local_dx + width) % width;
          let local_p2 = local_ny*width + local_nx;

          if (wmobb_data[local_p2] !== local_b1) continue;
          let local_a2 = land_area_data[local_p2] || 0;
          let local_iso2 = pixel_to_geocode[local_p2];
          if (local_a2 <= 0 || !local_iso2 || local_iso1 === local_iso2) continue;

          let local_u2 = local_b_entry.iso_to_idx[local_iso2];
          if (local_u2 === undefined) continue;

          let local_edge_u = local_u1;
          let local_edge_v = local_u2;
          let local_pair_p = local_p1;
          let local_pair_q = local_p2;

          if (local_u1 > local_u2) {
            local_edge_u = local_u2;
            local_edge_v = local_u1;
            local_pair_p = local_p2;
            local_pair_q = local_p1;
          }

          let local_edge_key = `${local_edge_u}_${local_edge_v}`;
          let local_edge = local_b_entry.edges_temp_obj[local_edge_key];
          if (!local_edge) {
            local_edge = {
              collar_u_set: new Set(),
              collar_v_set: new Set(),
              cw_list: [],
              p1_list: [],
              p2_list: [],
              u: local_edge_u,
              v: local_edge_v
            };
            local_b_entry.edges_temp_obj[local_edge_key] = local_edge;
          }

          local_edge.p1_list.push(local_pair_p);
          local_edge.p2_list.push(local_pair_q);
          local_edge.cw_list.push(local_cw);
          local_edge.collar_u_set.add(local_pair_p);
          local_edge.collar_v_set.add(local_pair_q);
        }
      }
    }

    //3. Finalise compact typed arrays per cross-border edge
    for (let i = 0; i < multi_basin_keys.length; i++) {
      let local_b_entry = basins_obj[multi_basin_keys[i]];
      let local_edge_keys = Object.keys(local_b_entry.edges_temp_obj).sort();

      for (let x = 0; x < local_edge_keys.length; x++) {
        let local_raw_edge = local_b_entry.edges_temp_obj[local_edge_keys[x]];
        local_b_entry.edges_array.push({
          collar_u_array: new Int32Array(Array.from(local_raw_edge.collar_u_set)),
          collar_v_array: new Int32Array(Array.from(local_raw_edge.collar_v_set)),
          cw_array: new Float32Array(local_raw_edge.cw_list),
          p1_array: new Int32Array(local_raw_edge.p1_list),
          p2_array: new Int32Array(local_raw_edge.p2_list),
          u: local_raw_edge.u,
          v: local_raw_edge.v
        });
      }
      delete local_b_entry.edges_temp_obj;
    }

    //Return statement
    return {
      basins_obj: basins_obj,
      multi_basin_keys: multi_basin_keys,
      total_chunks: total_chunks,
      total_multi_basins: multi_basin_keys.length
    };
  };


  /**
   * Computes the weighted median of an array of values given non-negative weights.
   * @alias population_c14bazAAR_binning.computeWeightedMedian
   *
   * @param {Array<number>} arg0_values_array
   * @param {Array<number>} arg1_weights_array
   *
   * @returns {number} Weighted median value.
   */
  population_c14bazAAR_binning.computeWeightedMedian = function (arg0_values_array, arg1_weights_array) {
    //Convert from parameters
    let values_array = (arg0_values_array) ? arg0_values_array : [];
    let weights_array = (arg1_weights_array) ? arg1_weights_array : [];

    //Declare local instance variables
    let cumulative_weight = 0;
    let half_weight = 0;
    let n = values_array.length;
    let pairs_array = [];
    let total_weight = 0;

    //Guard clauses
    if (n === 0) return 0;
    if (n === 1) return values_array[0];


    for (let i = 0; i < n; i++) {
      let local_w = Math.max(0, weights_array[i] || 0);
      if (local_w > 0) {
        pairs_array.push({ val: values_array[i], w: local_w });
        total_weight += local_w;
      }
    }

    if (pairs_array.length === 0 || total_weight <= 0) return 0;
    pairs_array.sort((a, b) => a.val - b.val);
    half_weight = 0.5*total_weight;

    for (let i = 0; i < pairs_array.length; i++) {
      cumulative_weight += pairs_array[i].w;
      if (cumulative_weight > half_weight) return pairs_array[i].val;
      if (Math.abs(cumulative_weight - half_weight) <= 1e-12 && i + 1 < pairs_array.length)
        return 0.5*(pairs_array[i].val + pairs_array[i + 1].val);
    }

    //Return statement
    return pairs_array[pairs_array.length - 1].val;
  };


  /**
   * Builds a binary mask of active compact local HYDE outlier regions (e.g. microstate or point anomalies <= max_pixels)
   * for a given year from population_Substrata.outlier_removal/rasters_outliers/, excluding macro-regional/continental masks.
   * @alias population_c14bazAAR_binning.getCompactOutlierMask
   *
   * @param {number|string} arg0_year
   * @param {Object} [arg1_options]
   *  @param {string} [arg1_options.input_outlier_rasters]
   *  @param {number} [arg1_options.max_pixels=300]
   *  @param {number} [arg1_options.total_pixels=9331200]
   *
   * @returns {Object} { count: number, mask_array: Uint8Array }
   */
  population_c14bazAAR_binning.getCompactOutlierMask = function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let all_files = [];
    let c14_cls = global.population_c14bazAAR || {};
    let count = 0;
    let mask_array = null;
    let mask_dir = options.input_outlier_rasters || c14_cls.input_outlier_rasters;
    let max_pixels = (options.max_pixels !== undefined) ? options.max_pixels : 300;
    let total_pixels = (options.total_pixels !== undefined) ? options.total_pixels : 4320*2160;

    //Guard clauses
    mask_array = new Uint8Array(total_pixels);
    if (isNaN(year) || !mask_dir || !fs.existsSync(mask_dir))
      return { count: 0, mask_array: mask_array };


    all_files = fs.readdirSync(mask_dir).filter((local_f) => local_f.endsWith(".png"));
    for (let i = 0; i < all_files.length; i++) {
      let local_file_path = path.join(mask_dir, all_files[i]);
      let local_parts = path.basename(local_file_path, ".png").split("_");
      if (local_parts.length < 2) continue;

      let local_end_year = parseInt(local_parts[local_parts.length - 1]);
      let local_start_year = parseInt(local_parts[local_parts.length - 2]);
      if (isNaN(local_start_year) || isNaN(local_end_year)) continue;
      if (year < local_start_year || year > local_end_year) continue;

      let local_img = GeoPNG.loadImage(local_file_path);
      let local_indices = [];
      let local_limit = Math.min(total_pixels, local_img.width*local_img.height);

      for (let x = 0; x < local_limit; x++) {
        let local_b = x*4;
        if (
          local_img.data[local_b] === 0 &&
          local_img.data[local_b + 1] === 0 &&
          local_img.data[local_b + 2] === 0 &&
          local_img.data[local_b + 3] === 255
        ) {
          local_indices.push(x);
          if (local_indices.length > max_pixels) break;
        }
      }

      if (local_indices.length > 0 && local_indices.length <= max_pixels)
        for (let x = 0; x < local_indices.length; x++) {
          let local_idx = local_indices[x];
          if (mask_array[local_idx] === 0) {
            mask_array[local_idx] = 1;
            count++;
          }
        }
    }

    //Return statement
    return { count: count, mask_array: mask_array };
  };


  /**
   * Inpaints compact local HYDE outlier masks (such as microstate agricultural back-projection spikes)
   * across HYDE land-use covariate rasters via inverse-distance weighted boundary interpolation.
   * @alias population_c14bazAAR_binning.inpaintOutlierCovariates
   *
   * @param {number|string} arg0_year
   * @param {Array<Object|null>} arg1_rasters_array - Array of { data: Float32Array } raster objects.
   * @param {Object} [arg2_options]
   *  @param {Int32Array|Float32Array} [arg2_options.land_area]
   *  @param {number} [arg2_options.max_pixels=300]
   *  @param {number} [arg2_options.radius=4]
   *
   * @returns {number} Count of outlier pixels inpainted.
   */
  population_c14bazAAR_binning.inpaintOutlierCovariates = function (arg0_year, arg1_rasters_array, arg2_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let rasters_array = (arg1_rasters_array) ? arg1_rasters_array : [];
    let options = (arg2_options) ? arg2_options : {};

    //Declare local instance variables
    let inpaint_radius = (options.radius !== undefined) ? options.radius : 4;
    let land_area = options.land_area || null;
    let outlier_mask_obj = null;

    //Guard clauses
    if (!rasters_array || rasters_array.length === 0 || typeof GeoPNG === "undefined" || typeof GeoPNG.inpaintUrbanMask !== "function")
      return 0;


    outlier_mask_obj = population_c14bazAAR_binning.getCompactOutlierMask(year, options);
    if (outlier_mask_obj.count <= 0) return 0;

    for (let i = 0; i < rasters_array.length; i++) {
      let local_raster = rasters_array[i];
      if (local_raster && local_raster.data)
        GeoPNG.inpaintUrbanMask(local_raster.data, outlier_mask_obj.mask_array, {
          land_area: land_area,
          radius: inpaint_radius
        });
    }

    //Return statement
    return outlier_mask_obj.count;
  };


  /**
   * Erases modern ISO3 national border discontinuities inside each multi-country WMO watershed prior to 1 AD
   * via graph-reconciled fractional binning across (watershed, ISO3) chunks, scaling each chunk by a constant
   * factor so intra-chunk spatial variance (CV and relative pixel profile) is strictly preserved.
   * @alias population_c14bazAAR_binning.reconcileWatershedISO3Chunks
   *
   * @param {Float32Array} arg0_weights_data - Mutable global WLS rural disaggregation weights buffer.
   * @param {Object} [arg1_options]
   *  @param {Object} arg1_options.chunk_index - Pre-indexed topology from buildWatershedISO3ChunkIndex.
   *  @param {Int32Array|Float32Array} arg1_options.land_area_data - Global habitable land area buffer.
   *  @param {number} [arg1_options.max_log_shift=8.0] - Maximum absolute log-scalar shift per chunk.
   *  @param {Float32Array} [arg1_options.urban_data] - Optional historical urban population buffer (urban pixels > 0 remain 0).
   *
   * @returns {number} Number of multi-ISO3 watersheds reconciled.
   */
  population_c14bazAAR_binning.reconcileWatershedISO3Chunks = function (arg0_weights_data, arg1_options) {
    //Convert from parameters
    let weights_data = arg0_weights_data;
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let chunk_index = options.chunk_index || null;
    let land_area_data = options.land_area_data || null;
    let max_log_shift = (options.max_log_shift !== undefined) ? options.max_log_shift : 0.45;
    let multi_basin_keys = [];
    let reconciled_basins = 0;
    let urban_data = options.urban_data || null;

    //Guard clauses
    if (!weights_data || !chunk_index || !chunk_index.basins_obj || !land_area_data) {
      console.error("- [population_c14bazAAR_binning.reconcileWatershedISO3Chunks] Missing weights_data, chunk_index, or land_area_data.");
      return 0;
    }


    multi_basin_keys = chunk_index.multi_basin_keys || [];
    for (let i = 0; i < multi_basin_keys.length; i++) {
      let local_basin = chunk_index.basins_obj[multi_basin_keys[i]];
      let local_chunks = local_basin.chunks_array;
      let local_edges = local_basin.edges_array;
      let local_n_chunks = local_chunks.length;

      if (local_n_chunks < 2 || local_edges.length === 0) continue;

      let local_active_adj = new Array(local_n_chunks);
      let local_active_edges = [];
      let local_basin_area = 0;
      let local_basin_weight = 0;
      let local_chunk_area = new Float64Array(local_n_chunks);
      let local_chunk_weight = new Float64Array(local_n_chunks);

      for (let x = 0; x < local_n_chunks; x++) {
        let local_px_arr = local_chunks[x].pixels_array;
        local_active_adj[x] = [];
        for (let y = 0; y < local_px_arr.length; y++) {
          let local_p = local_px_arr[y];
          let local_a = land_area_data[local_p] || 0;
          let local_w = Math.max(0, weights_data[local_p] || 0);
          if (local_a > 0) {
            local_chunk_area[x] += local_a;
            local_chunk_weight[x] += local_w;
          }
        }
        local_basin_area += local_chunk_area[x];
        local_basin_weight += local_chunk_weight[x];
      }

      if (local_basin_weight <= 0 || local_basin_area <= 0) continue;

      let local_eps_d = Math.max(1e-12, 1e-5*(local_basin_weight/local_basin_area));

      //Evaluate empirical cross-border log-density jumps along each shared chunk boundary
      for (let x = 0; x < local_edges.length; x++) {
        let local_active_w = 0;
        let local_edge = local_edges[x];
        let local_log_ratios = [];
        let local_pair_weights = [];
        let local_pos_w = 0;

        for (let y = 0; y < local_edge.p1_array.length; y++) {
          let local_p1 = local_edge.p1_array[y];
          let local_p2 = local_edge.p2_array[y];
          if (urban_data && (urban_data[local_p1] > 0 || urban_data[local_p2] > 0)) continue;

          let local_a1 = land_area_data[local_p1] || 0;
          let local_a2 = land_area_data[local_p2] || 0;
          if (local_a1 <= 0 || local_a2 <= 0) continue;

          let local_cw = local_edge.cw_array[y];
          let local_d1 = Math.max(0, weights_data[local_p1] || 0)/local_a1;
          let local_d2 = Math.max(0, weights_data[local_p2] || 0)/local_a2;

          if (Math.max(local_d1, local_d2) > local_eps_d) {
            local_active_w += local_cw;
            if (local_d1 > local_eps_d && local_d2 > local_eps_d) {
              local_log_ratios.push(Math.log(local_d2/local_d1));
              local_pair_weights.push(local_cw);
              local_pos_w += local_cw;
            }
          }
        }

        if (local_active_w > 0) {
          let local_col_a_u = 0;
          let local_col_a_v = 0;
          let local_col_w_u = 0;
          let local_col_w_v = 0;
          let local_delta = 0;
          let local_delta_collar = 0;

          for (let y = 0; y < local_edge.collar_u_array.length; y++) {
            let local_p = local_edge.collar_u_array[y];
            if (!urban_data || urban_data[local_p] <= 0) {
              local_col_a_u += Math.max(0, land_area_data[local_p] || 0);
              local_col_w_u += Math.max(0, weights_data[local_p] || 0);
            }
          }
          for (let y = 0; y < local_edge.collar_v_array.length; y++) {
            let local_q = local_edge.collar_v_array[y];
            if (!urban_data || urban_data[local_q] <= 0) {
              local_col_a_v += Math.max(0, land_area_data[local_q] || 0);
              local_col_w_v += Math.max(0, weights_data[local_q] || 0);
            }
          }

          let local_du = (local_col_a_u > 0) ? (local_col_w_u/local_col_a_u) : 0;
          let local_dv = (local_col_a_v > 0) ? (local_col_w_v/local_col_a_v) : 0;
          local_delta_collar = Math.log(Math.max(local_eps_d, local_dv)/Math.max(local_eps_d, local_du));

          if (local_pos_w > 0) {
            let local_delta_med = population_c14bazAAR_binning.computeWeightedMedian(local_log_ratios, local_pair_weights);
            let local_theta = Math.min(1.0, Math.max(0.0, local_pos_w/local_active_w));
            local_delta = local_theta*local_delta_med + (1.0 - local_theta)*local_delta_collar;
          } else {
            local_delta = local_delta_collar;
          }

          local_delta = Math.max(-max_log_shift, Math.min(max_log_shift, local_delta));
          let local_edge_idx = local_active_edges.length;
          local_active_edges.push({
            delta: local_delta,
            omega: local_active_w,
            u: local_edge.u,
            v: local_edge.v
          });
          local_active_adj[local_edge.u].push({ edge_idx: local_edge_idx, node: local_edge.v });
          local_active_adj[local_edge.v].push({ edge_idx: local_edge_idx, node: local_edge.u });
        }
      }

      if (local_active_edges.length === 0) continue;

      //Solve weighted Laplacian reconciliation independently on each connected chunk component
      let local_chunk_scalars = new Float64Array(local_n_chunks);
      let local_visited = new Uint8Array(local_n_chunks);
      local_chunk_scalars.fill(1.0);

      for (let x = 0; x < local_n_chunks; x++) {
        if (local_visited[x] === 1 || local_active_adj[x].length === 0) continue;

        let local_comp_nodes = [x];
        local_visited[x] = 1;
        for (let y = 0; y < local_comp_nodes.length; y++) {
          let local_curr = local_comp_nodes[y];
          let local_nbrs = local_active_adj[local_curr];
          for (let z = 0; z < local_nbrs.length; z++) {
            let local_next = local_nbrs[z].node;
            if (local_visited[local_next] === 0) {
              local_visited[local_next] = 1;
              local_comp_nodes.push(local_next);
            }
          }
        }

        let local_m = local_comp_nodes.length;
        if (local_m < 2) continue;

        let local_comp_area = 0;
        let local_global_to_local = new Int32Array(local_n_chunks);
        local_global_to_local.fill(-1);

        for (let y = 0; y < local_m; y++) {
          let local_g = local_comp_nodes[y];
          local_global_to_local[local_g] = y;
          local_comp_area += Math.max(1.0, local_chunk_area[local_g]);
        }

        let local_kkt_dim = local_m + 1;
        let local_matrix = new Array(local_kkt_dim);
        let local_rhs = new Float64Array(local_kkt_dim);
        for (let y = 0; y < local_kkt_dim; y++) {
          local_matrix[y] = new Float64Array(local_kkt_dim);
          if (y < local_m) local_matrix[y][y] = 1e-9;
        }

        for (let y = 0; y < local_active_edges.length; y++) {
          let local_ae = local_active_edges[y];
          let local_lu = local_global_to_local[local_ae.u];
          let local_lv = local_global_to_local[local_ae.v];
          if (local_lu >= 0 && local_lv >= 0) {
            let local_w = local_ae.omega;
            local_matrix[local_lu][local_lu] += local_w;
            local_matrix[local_lv][local_lv] += local_w;
            local_matrix[local_lu][local_lv] -= local_w;
            local_matrix[local_lv][local_lu] -= local_w;
            local_rhs[local_lu] += local_w*local_ae.delta;
            local_rhs[local_lv] -= local_w*local_ae.delta;
          }
        }

        for (let y = 0; y < local_m; y++) {
          let local_mu = Math.max(1.0, local_chunk_area[local_comp_nodes[y]])/local_comp_area;
          local_matrix[y][local_m] = local_mu;
          local_matrix[local_m][y] = local_mu;
        }

        let local_sol = population_c14bazAAR_binning.solveLinearSystem(local_matrix, local_rhs);
        for (let y = 0; y < local_m; y++) {
          let local_g = local_comp_nodes[y];
          let local_x_val = Math.max(-max_log_shift, Math.min(max_log_shift, local_sol[y] || 0));
          local_chunk_scalars[local_g] = Math.exp(local_x_val);

          //Seed strictly zero chunk when connected across an active inhabited border in the same watershed
          if (local_chunk_weight[local_g] <= 0 && local_chunk_area[local_g] > 0) {
            let local_px_arr = local_chunks[local_g].pixels_array;
            for (let z = 0; z < local_px_arr.length; z++) {
              let local_p = local_px_arr[z];
              weights_data[local_p] = local_eps_d*Math.max(0, land_area_data[local_p] || 0);
            }
          }
        }
      }

      //Apply chunk-constant scalars (strictly preserving intra-chunk spatial variance) and conserve basin weight sum
      let local_new_basin_weight = 0;
      for (let x = 0; x < local_n_chunks; x++) {
        let local_px_arr = local_chunks[x].pixels_array;
        let local_scalar = local_chunk_scalars[x];
        for (let y = 0; y < local_px_arr.length; y++) {
          let local_p = local_px_arr[y];
          let local_v = Math.max(0, weights_data[local_p] || 0)*local_scalar;
          weights_data[local_p] = local_v;
          local_new_basin_weight += local_v;
        }
      }

      if (local_new_basin_weight > 0) {
        let local_norm = local_basin_weight/local_new_basin_weight;
        for (let x = 0; x < local_n_chunks; x++) {
          let local_px_arr = local_chunks[x].pixels_array;
          for (let y = 0; y < local_px_arr.length; y++)
            weights_data[local_px_arr[y]] *= local_norm;
        }
      }

      reconciled_basins++;
    }

    //Return statement
    return reconciled_basins;
  };


  /**
   * Solves a small dense linear system A * x = b via Gaussian elimination with partial pivoting.
   * @alias population_c14bazAAR_binning.solveLinearSystem
   *
   * @param {Array<Float64Array|Array<number>>} arg0_matrix
   * @param {Float64Array|Array<number>} arg1_rhs
   *
   * @returns {Float64Array} Solution vector x.
   */
  population_c14bazAAR_binning.solveLinearSystem = function (arg0_matrix, arg1_rhs) {
    //Convert from parameters
    let matrix = arg0_matrix;
    let rhs = arg1_rhs;

    //Declare local instance variables
    let aug = [];
    let n = (matrix) ? matrix.length : 0;
    let sol = null;

    //Guard clauses
    if (n === 0) return new Float64Array(0);


    sol = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      let local_row = new Float64Array(n + 1);
      for (let x = 0; x < n; x++) local_row[x] = matrix[i][x] || 0;
      local_row[n] = rhs[i] || 0;
      aug.push(local_row);
    }

    for (let i = 0; i < n; i++) {
      let local_max_row = i;
      let local_max_val = Math.abs(aug[i][i]);

      for (let x = i + 1; x < n; x++) {
        let local_abs = Math.abs(aug[x][i]);
        if (local_abs > local_max_val) {
          local_max_val = local_abs;
          local_max_row = x;
        }
      }

      if (local_max_row !== i) {
        let local_tmp = aug[i];
        aug[i] = aug[local_max_row];
        aug[local_max_row] = local_tmp;
      }

      let local_pivot = aug[i][i];
      if (Math.abs(local_pivot) <= 1e-15) continue;

      for (let x = i + 1; x < n; x++) {
        let local_factor = aug[x][i]/local_pivot;
        if (local_factor !== 0)
          for (let y = i; y <= n; y++)
            aug[x][y] -= local_factor*aug[i][y];
      }
    }

    for (let i = n - 1; i >= 0; i--) {
      let local_pivot = aug[i][i];
      if (Math.abs(local_pivot) <= 1e-15) {
        sol[i] = 0;
      } else {
        let local_sum = aug[i][n];
        for (let x = i + 1; x < n; x++) local_sum -= aug[i][x]*sol[x];
        sol[i] = local_sum/local_pivot;
      }
    }

    //Return statement
    return sol;
  };
}
