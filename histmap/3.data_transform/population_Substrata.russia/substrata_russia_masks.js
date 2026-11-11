//Initialise functions
{
  if (!global.population_Substrata_russia_masks)
    global.population_Substrata_russia_masks = {};

  let fs = global.fs || require("fs");
  let JSON5 = global.JSON5 || require("json5");
  let path = global.path || require("path");
  let { PNG } = global.pngjs || require("pngjs");

  /**
   * Helper: Safely reads a positive big-endian IEEE-754 `float32` value from a PNG RGBA buffer.
   * @alias population_Substrata_russia_masks.readPositiveFloat32
   *
   * @param {Buffer|Uint8Array} arg0_png_data
   * @param {DataView} arg1_data_view
   * @param {number} arg2_byte_offset
   *
   * @returns {number}
   */
  population_Substrata_russia_masks.readPositiveFloat32 = function (arg0_png_data, arg1_data_view, arg2_byte_offset) {
    //Convert from parameters
    let png_data = arg0_png_data;
    let data_view = arg1_data_view;
    let p4 = arg2_byte_offset;

    //Guard clauses
    if ((png_data[p4] | png_data[p4 + 1] | png_data[p4 + 2] | png_data[p4 + 3]) === 0)
      return 0;

    //Declare local instance variables
    let val = data_view.getFloat32(p4, false);

    //Return statement
    return (Number.isFinite(val) && val > 0) ? val : 0;
  };


  /**
   * Step A: Loads `histmap/1.data_raw/population_regional/POLARIS/russia_areal_masks.json5`, indexes all specialist (Priority 2),
   * macro (Priority 1), and national epoch (Priority 3) `4320x2160` RGB PNG areal masks, closes western frontier mask gaps via BFS,
   * identifies foreign border spillover pixels from Russian macro outlier masks, and builds pixel-level domain, cross-domain seam,
   * and exterior foreign-feathering tables.
   * @alias population_Substrata_russia_masks.A_loadManifestAndMasks
   *
   * @param {Object} [arg0_options]
   *
   * @returns {Object}
   */
  population_Substrata_russia_masks.A_loadManifestAndMasks = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let border_dist;
    let bu_pop_sample_path;
    let cross_dom_anchor_idx;
    let cross_dom_dist;
    let default_config_path = (typeof h1 !== "undefined" && fs.existsSync(`${h1}population_regional/POLARIS/russia_areal_masks.json5`)) ?
      path.resolve(`${h1}population_regional/POLARIS/russia_areal_masks.json5`) :
      ((fs.existsSync("./histmap/1.data_raw/population_regional/POLARIS/russia_areal_masks.json5")) ?
        path.resolve("./histmap/1.data_raw/population_regional/POLARIS/russia_areal_masks.json5") :
        path.resolve(__dirname, "../../1.data_raw/population_regional/POLARIS/russia_areal_masks.json5"));
    let default_root = (fs.existsSync("./histmap/1.data_raw")) ?
      path.resolve(".") :
      path.resolve(__dirname, "../../..");
    let feather_px = 3;
    let feather_weights;
    let foreign_anchor_idx;
    let foreign_spillover_pairs = [];
    let height = 2160;
    let macro_entry = null;
    let manifest_path = (options.config_path) ? options.config_path : default_config_path;
    let manifest_obj = JSON5.parse(fs.readFileSync(manifest_path, "utf8"));
    let n_pixels = 4320*2160;
    let national_epoch_entries = [];
    let pixel_domain = new Uint8Array(4320*2160);
    let pixel_macro_zone = new Int16Array(4320*2160).fill(-1);
    let pixel_spec_mask = new Int16Array(4320*2160).fill(-1);
    let pixel_spec_zone = new Int16Array(4320*2160).fill(-1);
    let root_dir = (options.project_root) ? options.project_root : default_root;
    let rus_pop_sample_path;
    let specialist_entries = [];
    let valid_indices = [];
    let width = 4320;

    //Function body
    if (manifest_obj.smoothing && Number.isFinite(manifest_obj.smoothing.border_feather_radius_px))
      feather_px = manifest_obj.smoothing.border_feather_radius_px;

    //1. Identify valid domain pixels strictly from kriged population rasters (`popc_1000.png`) so foreign/water cells are never forced into domain 1
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
        ) pixel_domain[idx] = 1; //Russia + Crimea (`sites_IA_RAS`)
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
        ) pixel_domain[idx] = 2; //Belarus + Mainland Ukraine (`sites_belarus_ukraine`)
      }
    }

    //2. Load Priority 1 Macro Mask (`migration_period`) onto active `pixel_domain === 1` or Russian ISO (`643`/`999`) pixels
    let is_foreign_iso = new Uint8Array(n_pixels);
    let is_rus_iso = new Uint8Array(n_pixels);
    let asc_path = path.join(root_dir, "histmap/1.data_raw/metadata_HYDE/general_files/sub_iso_cr.asc");
    if (fs.existsSync(asc_path)) {
      let raw_asc = fs.readFileSync(asc_path, "utf8").trim().split(/\s+/);
      for (let idx = 0; idx < n_pixels; idx++) {
        let v = Math.round(Number(raw_asc[12 + idx]));
        if (v > 0) {
          let iso_num = Math.floor(v/1000);
          if (iso_num === 643 || iso_num === 999) is_rus_iso[idx] = 1;
          else if (iso_num !== 804 && iso_num !== 112) is_foreign_iso[idx] = 1;
        }
      }
    }

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
          if (pixel_domain[idx] === 0 && is_rus_iso[idx]) pixel_domain[idx] = 1;
          if (pixel_domain[idx] !== 1) continue;
          let c_str = `${m_png.data[p4]},${m_png.data[p4 + 1]},${m_png.data[p4 + 2]}`;
          let z_idx = colour_to_z.get(c_str);
          if (z_idx !== undefined) {
            pixel_macro_zone[idx] = z_idx;
            m_zones[z_idx].pixels.push(idx);
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
        domain: s_meta.domain || s_json.domain || [-10000, 1900],
        domain_code: dom_code,
        zones: s_zones,
        pixel_sub_weight: pixel_sub_weight
      });
    }

    //3b. Close specialist mask coverage gaps on Western Russia (Karelia/Leningrad/Murmansk/Western border, lon < 42.0) and Belarus/Ukraine (`dom === 2`) via BFS
    let spec_bfs_q = [];
    let spec_bfs_dist = new Uint8Array(n_pixels).fill(255);
    for (let idx = 0; idx < n_pixels; idx++) {
      if (pixel_domain[idx] > 0 && pixel_spec_mask[idx] >= 0) {
        let c = idx % width;
        let lon = -180 + ((c + 0.5)/width)*360;
        if (pixel_domain[idx] === 2 || lon < 42.5) {
          spec_bfs_dist[idx] = 0;
          spec_bfs_q.push(idx);
        }
      }
    }

    let s_head = 0;
    while (s_head < spec_bfs_q.length) {
      let curr_idx = spec_bfs_q[s_head++];
      let d = spec_bfs_dist[curr_idx];
      if (d >= 120) continue;
      let dom = pixel_domain[curr_idx];
      let sm = pixel_spec_mask[curr_idx];
      let sz = pixel_spec_zone[curr_idx];
      let r = Math.floor(curr_idx/width);
      let c = curr_idx % width;
      let nbrs = [
        (r > 0) ? curr_idx - width : -1,
        (r + 1 < height) ? curr_idx + width : -1,
        (c > 0) ? curr_idx - 1 : -1,
        (c + 1 < width) ? curr_idx + 1 : -1
      ];
      for (let x = 0; x < 4; x++) {
        let n_idx = nbrs[x];
        if (n_idx >= 0 && pixel_domain[n_idx] === dom && pixel_spec_mask[n_idx] < 0) {
          let n_lon = -180 + (((n_idx % width) + 0.5)/width)*360;
          if (dom === 2 || n_lon < 42.0) {
            pixel_spec_mask[n_idx] = sm;
            pixel_spec_zone[n_idx] = sz;
            spec_bfs_dist[n_idx] = d + 1;
            specialist_entries[sm].zones[sz].pixels.push(n_idx);
            specialist_entries[sm].zones[sz].total_mask_pixels++;
            spec_bfs_q.push(n_idx);
          }
        }
      }
    }

    for (let i = 0; i < specialist_entries.length; i++) {
      let s_zones = specialist_entries[i].zones;
      for (let x = 0; x < s_zones.length; x++) {
        let z = s_zones[x];
        if (z.total_mask_pixels > 0 && z.pixels.length > 0)
          z.domain_fraction = Math.min(1.0, z.pixels.length/z.total_mask_pixels);
      }
    }

    //4. Collect active domain pixels, identify foreign outlier-mask spillover cells, and compute exterior border anchors
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
    foreign_anchor_idx = new Int32Array(n_valid).fill(-1);

    let land_png_path = path.join(root_dir, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png");
    let is_foreign_land = new Uint8Array(n_pixels);
    if (fs.existsSync(land_png_path)) {
      let l_png = PNG.sync.read(fs.readFileSync(land_png_path));
      let l_dv = new DataView(l_png.data.buffer, l_png.data.byteOffset, l_png.data.byteLength);
      for (let idx = 0; idx < n_pixels; idx++) {
        if (pixel_domain[idx] > 0) continue;
        if (this.readPositiveFloat32(l_png.data, l_dv, idx*4) > 0)
          is_foreign_land[idx] = 1;
      }
    }

    //4b. Load Priority 3 National Epoch Masks (1400..2026 AD) across both `pixel_domain === 1` and `pixel_domain === 2`
    let raw_nat_masks = manifest_obj.national_epoch_masks || [];
    for (let i = 0; i < raw_nat_masks.length; i++) {
      let n_meta = raw_nat_masks[i];
      let n_cfg_path = path.join(root_dir, n_meta.json5_path);
      let n_png_path = path.join(root_dir, n_meta.mask_path);
      if (!fs.existsSync(n_cfg_path) || !fs.existsSync(n_png_path)) continue;

      let n_json = JSON5.parse(fs.readFileSync(n_cfg_path, "utf8"));
      let n_png = PNG.sync.read(fs.readFileSync(n_png_path));
      let n_zones = [];
      let colour_to_z = new Map();
      let z_keys = Object.keys(n_json.regions || {});
      let pixel_nat_zone = new Int16Array(n_pixels).fill(-1);

      for (let x = 0; x < z_keys.length; x++) {
        let zk = z_keys[x];
        let zc = n_json.regions[zk];
        let col = zc.colour || zc.color;
        if (Array.isArray(col) && col.length >= 3) {
          colour_to_z.set(`${col[0]},${col[1]},${col[2]}`, x);
          n_zones.push({
            key: zk,
            colour: col,
            population: zc.population || {},
            pixels: [],
            dom1_pixels: [],
            dom2_pixels: [],
            direct_domain_pixels: 0,
            foreign_land_pixels: 0,
            total_mask_pixels: 0,
            domain_fraction: 1.0
          });
        }
      }

      let nat_bfs_q = [];
      let nat_bfs_dist = new Uint8Array(n_pixels).fill(255);
      for (let idx = 0; idx < n_pixels; idx++) {
        let p4 = idx*4;
        if (n_png.data[p4 + 3] === 0) continue;
        let r = n_png.data[p4];
        let g = n_png.data[p4 + 1];
        let b = n_png.data[p4 + 2];
        if (r === 0 && g === 0 && b === 0) continue;
        let z_idx = colour_to_z.get(`${r},${g},${b}`);
        if (z_idx !== undefined) {
          let z = n_zones[z_idx];
          z.total_mask_pixels++;
          if (pixel_domain[idx] > 0) {
            z.direct_domain_pixels++;
          } else if (is_foreign_iso[idx] || is_rus_iso[idx]) {
            z.foreign_land_pixels++;
          }
        }
      }

      for (let x = 0; x < n_zones.length; x++) {
        let z = n_zones[x];
        if (z.total_mask_pixels > 0 && z.direct_domain_pixels < z.total_mask_pixels*0.05) {
          z.direct_domain_pixels = 0;
          z.domain_fraction = 0;
          continue;
        }
        let land_mask_px = z.direct_domain_pixels + z.foreign_land_pixels;
        if (land_mask_px > 0 && z.direct_domain_pixels > 0) {
          let raw_frac = Math.min(1.0, z.direct_domain_pixels/land_mask_px);
          z.domain_fraction = (raw_frac >= 0.87 && !z.key.includes("kaliningrad")) ? 1.0 : raw_frac;
        }
      }

      for (let idx = 0; idx < n_pixels; idx++) {
        if (pixel_domain[idx] === 0) continue;
        let p4 = idx*4;
        if (n_png.data[p4 + 3] === 0) continue;
        let z_idx = colour_to_z.get(`${n_png.data[p4]},${n_png.data[p4 + 1]},${n_png.data[p4 + 2]}`);
        if (z_idx !== undefined && n_zones[z_idx].direct_domain_pixels > 0) {
          let z = n_zones[z_idx];
          pixel_nat_zone[idx] = z_idx;
          z.pixels.push(idx);
          if (pixel_domain[idx] === 1) z.dom1_pixels.push(idx);
          else if (pixel_domain[idx] === 2) z.dom2_pixels.push(idx);
          nat_bfs_dist[idx] = 0;
          nat_bfs_q.push(idx);
        }
      }

      //Close minor coastal/shoreline fringe gaps inside `pixel_domain > 0` via BFS within the same domain
      let n_head = 0;
      while (n_head < nat_bfs_q.length) {
        let curr_idx = nat_bfs_q[n_head++];
        let d = nat_bfs_dist[curr_idx];
        if (d >= 24) continue;
        let dom = pixel_domain[curr_idx];
        let nz = pixel_nat_zone[curr_idx];
        let r = Math.floor(curr_idx/width);
        let c = curr_idx % width;
        let nbrs = [
          (r > 0) ? curr_idx - width : -1,
          (r + 1 < height) ? curr_idx + width : -1,
          (c > 0) ? curr_idx - 1 : -1,
          (c + 1 < width) ? curr_idx + 1 : -1
        ];
        for (let x = 0; x < 4; x++) {
          let nb_idx = nbrs[x];
          if (nb_idx >= 0 && pixel_domain[nb_idx] === dom && pixel_nat_zone[nb_idx] < 0) {
            pixel_nat_zone[nb_idx] = nz;
            nat_bfs_dist[nb_idx] = d + 1;
            n_zones[nz].pixels.push(nb_idx);
            if (dom === 1) n_zones[nz].dom1_pixels.push(nb_idx);
            else if (dom === 2) n_zones[nz].dom2_pixels.push(nb_idx);
            nat_bfs_q.push(nb_idx);
          }
        }
      }

      national_epoch_entries.push({
        id: n_meta.id,
        domain: n_meta.domain || n_json.domain || [1400, 2026],
        pixel_nat_zone: pixel_nat_zone,
        zones: n_zones
      });
    }

    //Detect foreign land pixels (`pixel_domain === 0`) where Russian outlier masks spilled across the border
    let is_rus_outlier_spill = new Uint8Array(n_pixels);
    let outlier_dir = path.join(root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_outliers");
    let rus_outlier_files = ["russia_-10000_0.png", "stpetersburgrussia_-10000_0.png", "siberia_-10000_1800.png"];
    for (let i = 0; i < rus_outlier_files.length; i++) {
      let o_path = path.join(outlier_dir, rus_outlier_files[i]);
      if (!fs.existsSync(o_path)) continue;
      let o_png = PNG.sync.read(fs.readFileSync(o_path));
      for (let idx = 0; idx < n_pixels; idx++) {
        if (!is_foreign_land[idx]) continue;
        let b = idx*4;
        if (o_png.data[b] === 0 && o_png.data[b + 1] === 0 && o_png.data[b + 2] === 0 && o_png.data[b + 3] === 255)
          is_rus_outlier_spill[idx] = 1;
      }
    }

    //Pair each foreign spillover pixel with its nearest clean `is_foreign_land` pixel via multi-source BFS
    let clean_foreign_anchor = new Int32Array(n_pixels).fill(-1);
    let cf_dist = new Uint8Array(n_pixels).fill(255);
    let cf_q = [];
    for (let idx = 0; idx < n_pixels; idx++) {
      if (is_foreign_land[idx] && !is_rus_outlier_spill[idx]) {
        clean_foreign_anchor[idx] = idx;
        cf_dist[idx] = 0;
        cf_q.push(idx);
      }
    }
    let cf_head = 0;
    while (cf_head < cf_q.length) {
      let curr_idx = cf_q[cf_head++];
      let d = cf_dist[curr_idx];
      if (d >= 16) continue;
      let r = Math.floor(curr_idx/width);
      let c = curr_idx % width;
      let nbrs = [
        (r > 0) ? curr_idx - width : -1,
        (r + 1 < height) ? curr_idx + width : -1,
        (c > 0) ? curr_idx - 1 : -1,
        (c + 1 < width) ? curr_idx + 1 : -1
      ];
      for (let x = 0; x < 4; x++) {
        let n_idx = nbrs[x];
        if (n_idx >= 0 && is_foreign_land[n_idx] && cf_dist[n_idx] > d + 1) {
          cf_dist[n_idx] = d + 1;
          clean_foreign_anchor[n_idx] = clean_foreign_anchor[curr_idx];
          cf_q.push(n_idx);
        }
      }
    }
    for (let idx = 0; idx < n_pixels; idx++) {
      if (is_rus_outlier_spill[idx] && clean_foreign_anchor[idx] >= 0)
        foreign_spillover_pairs.push([idx, clean_foreign_anchor[idx]]);
    }

    let bfs_q = [];
    for (let i = 0; i < n_valid; i++) {
      let idx = valid_indices[i];
      let r = Math.floor(idx/width);
      let c = idx % width;
      let f_idx = -1;
      if (r > 0 && is_foreign_land[idx - width]) f_idx = idx - width;
      else if (r + 1 < height && is_foreign_land[idx + width]) f_idx = idx + width;
      else if (c > 0 && is_foreign_land[idx - 1]) f_idx = idx - 1;
      else if (c + 1 < width && is_foreign_land[idx + 1]) f_idx = idx + 1;

      if (f_idx >= 0) {
        border_dist[i] = 1;
        foreign_anchor_idx[i] = (clean_foreign_anchor[f_idx] >= 0) ? clean_foreign_anchor[f_idx] : f_idx;
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
            foreign_anchor_idx[nv] = foreign_anchor_idx[curr_v];
            bfs_q.push(nv);
          }
        }
      }
    }

    for (let i = 0; i < n_valid; i++) {
      let d = border_dist[i];
      if (d <= feather_px) {
        let raw_w = 0.5*(1 - Math.cos(Math.PI*(d/(feather_px + 1))));
        feather_weights[i] = 0.65 + 0.35*raw_w;
      }
    }

    //5. Precompute distance and nearest cross-domain anchor along internal `dom 1 <-> dom 2` boundary
    cross_dom_anchor_idx = new Int32Array(n_valid).fill(-1);
    cross_dom_dist = new Uint8Array(n_valid).fill(255);
    let cd_q = [];
    for (let i = 0; i < n_valid; i++) {
      let idx = valid_indices[i];
      let dom = pixel_domain[idx];
      let r = Math.floor(idx/width);
      let c = idx % width;
      let other_idx = -1;
      let nbrs = [
        (r > 0) ? idx - width : -1,
        (r + 1 < height) ? idx + width : -1,
        (c > 0) ? idx - 1 : -1,
        (c + 1 < width) ? idx + 1 : -1
      ];
      for (let x = 0; x < 4; x++) {
        let n_idx = nbrs[x];
        if (n_idx >= 0 && pixel_domain[n_idx] > 0 && pixel_domain[n_idx] !== dom) {
          other_idx = n_idx;
          break;
        }
      }
      if (other_idx >= 0) {
        cross_dom_dist[i] = 1;
        cross_dom_anchor_idx[i] = other_idx;
        cd_q.push(i);
      }
    }

    let cd_head = 0;
    while (cd_head < cd_q.length) {
      let curr_v = cd_q[cd_head++];
      let d = cross_dom_dist[curr_v];
      if (d >= 6) continue;
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
          if (nv >= 0 && cross_dom_dist[nv] > d + 1) {
            cross_dom_dist[nv] = d + 1;
            cross_dom_anchor_idx[nv] = cross_dom_anchor_idx[curr_v];
            cd_q.push(nv);
          }
        }
      }
    }

    //Return statement
    return {
      border_dist: border_dist,
      cross_dom_anchor_idx: cross_dom_anchor_idx,
      cross_dom_dist: cross_dom_dist,
      feather_weights: feather_weights,
      foreign_anchor_idx: foreign_anchor_idx,
      foreign_spillover_pairs: foreign_spillover_pairs,
      height: height,
      hyde_years: manifest_obj.hyde_years,
      macro_entry: macro_entry,
      manifest: manifest_obj,
      n_pixels: n_pixels,
      n_valid: n_valid,
      national_epoch_entries: national_epoch_entries,
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
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = global.population_Substrata_russia_masks;
