//Import modules
let fs = global.fs || require("fs");
let JSON5 = global.JSON5 || require("json5");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Extracts and aggregates documented Stadestér settlement time-series and 5-arcminute (`4320x2160`)
   * habitation pixel indices directly from regional Operation Viscount `*_gazetteers.json5` manifests
   * without recompiling Stadestér or Velkscala.
   *
   * @class ViscountSettlementAnchors
   */
  global.ViscountSettlementAnchors = class {
    /**
     * Step A: Builds a valid 5-arcminute land-pixel lookup set from a domain mask PNG or geocode RGBs.
     * @alias ViscountSettlementAnchors.A_buildDomainLandMask
     *
     * @param {Object} arg0_options
     *  @param {Array<Array<number>>} [arg0_options.domain_geocode_rgbs]
     *  @param {string} [arg0_options.domain_mask_png]
     *  @param {Object} [arg0_options.exclude_bbox]
     *  @param {number} [arg0_options.grid_height=2160]
     *  @param {number} [arg0_options.grid_width=4320]
     *  @param {Object} [arg0_options.include_bbox]
     *  @param {string} [arg0_options.project_root]
     *
     * @returns {Uint8Array}
     */
    static A_buildDomainLandMask (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let exclude_bbox = options.exclude_bbox || null;
      let grid_h = Number(options.grid_height) || 2160;
      let grid_w = Number(options.grid_width) || 4320;
      let include_bbox = options.include_bbox || null;
      let root = options.project_root || process.cwd();
      let total_px = grid_w*grid_h;
      let valid_mask = new Uint8Array(total_px);

      //Function body
      let la_path = path.resolve(root, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png");
      let la_png = fs.existsSync(la_path) ? PNG.sync.read(fs.readFileSync(la_path)) : null;

      if (options.domain_mask_png) {
        let abs_m = path.resolve(root, options.domain_mask_png);

        if (fs.existsSync(abs_m)) {
          let m_png = PNG.sync.read(fs.readFileSync(abs_m));

          for (let i = 0; i < total_px; i++) {
            let p4 = i*4;
            let has_la = (!la_png) || (
              (la_png.data[p4] | la_png.data[p4 + 1] | la_png.data[p4 + 2] | la_png.data[p4 + 3]) !== 0
            );

            if (has_la && m_png.data[p4 + 3] > 0 && (m_png.data[p4] | m_png.data[p4 + 1] | m_png.data[p4 + 2]) !== 0)
              valid_mask[i] = 1;
          }
        }
      } else if (Array.isArray(options.domain_geocode_rgbs) && options.domain_geocode_rgbs.length > 0) {
        let geo_path = path.resolve(root, "histmap/1.data_raw/admin_modern/geocodes.png");

        if (fs.existsSync(geo_path)) {
          let geo_png = PNG.sync.read(fs.readFileSync(geo_path));
          let target_set = new Set(options.domain_geocode_rgbs.map(function (arg0_rgb) {
            return `${arg0_rgb[0]},${arg0_rgb[1]},${arg0_rgb[2]}`;
          }));

          for (let i = 0; i < total_px; i++) {
            let p4 = i*4;
            let has_la = (!la_png) || (
              (la_png.data[p4] | la_png.data[p4 + 1] | la_png.data[p4 + 2] | la_png.data[p4 + 3]) !== 0
            );

            if (!has_la) continue;
            let row = Math.floor(i/grid_w);
            let col = i % grid_w;
            let lat = 90 - (row + 0.5)*180/grid_h;
            let lon = -180 + (col + 0.5)*360/grid_w;
            let in_excl = Boolean(
              exclude_bbox &&
              lat >= exclude_bbox.min_lat && lat <= exclude_bbox.max_lat &&
              lon >= exclude_bbox.min_lon && lon <= exclude_bbox.max_lon
            );

            if (in_excl) continue;
            let in_incl = Boolean(
              include_bbox &&
              lat >= include_bbox.min_lat && lat <= include_bbox.max_lat &&
              lon >= include_bbox.min_lon && lon <= include_bbox.max_lon
            );
            let key = `${geo_png.data[p4]},${geo_png.data[p4 + 1]},${geo_png.data[p4 + 2]}`;

            if (in_incl || (geo_png.data[p4 + 3] > 0 && target_set.has(key)))
              valid_mask[i] = 1;
          }
        }
      }

      //Return statement
      return valid_mask;
    }


    /**
     * Step B: Extracts documented Stadestér settlements from a regional `*_gazetteers.json5` manifest,
     * filters them to the domain mask (plus 1-pixel coastal tolerance) and aggregates per 5-arcminute pixel
     * to prevent duplicate over-counting while preserving complete historical time-series.
     * @alias ViscountSettlementAnchors.B_extractFromGazetteerManifest
     *
     * @param {string} arg0_manifest_path
     * @param {Uint8Array} arg1_valid_mask
     * @param {Object} [arg2_options]
     *  @param {number} [arg2_options.grid_height=2160]
     *  @param {number} [arg2_options.grid_width=4320]
     *  @param {number} [arg2_options.max_year=1915]
     *  @param {number} [arg2_options.preindustrial_max_year=1850]
     *  @param {string} [arg2_options.project_root]
     *
     * @returns {Object}
     */
    static B_extractFromGazetteerManifest (arg0_manifest_path, arg1_valid_mask, arg2_options) {
      //Convert from parameters
      let manifest_path = arg0_manifest_path;
      let valid_mask = arg1_valid_mask;
      let options = (arg2_options) ? arg2_options : {};

      //Guard clauses
      let root = options.project_root || process.cwd();
      let abs_manifest = path.resolve(root, manifest_path);

      if (!fs.existsSync(abs_manifest)) {
        console.error(`[ViscountSettlementAnchors] Gazetteer manifest not found: ${abs_manifest}`);
        return null;
      }

      //Declare local instance variables
      let grid_h = Number(options.grid_height) || 2160;
      let grid_w = Number(options.grid_width) || 4320;
      let manifest = JSON5.parse(fs.readFileSync(abs_manifest, "utf8"));
      let max_year = Number.isFinite(options.max_year) ? Number(options.max_year) : 1915;
      let pixel_map = new Map();
      let preind_max_year = Number.isFinite(options.preindustrial_max_year) ? Number(options.preindustrial_max_year) : 1850;
      let raw_records_used = 0;

      //Function body
      let gaz_list = Array.isArray(manifest.gazetteers) ? manifest.gazetteers : [];

      for (let i = 0; i < gaz_list.length; i++) {
        let g_item = gaz_list[i];

        if (!g_item || !g_item.path) continue;
        if (Array.isArray(g_item.domain) && Number(g_item.domain[0]) > max_year) continue;
        let abs_g = path.resolve(root, g_item.path);

        if (!fs.existsSync(abs_g)) continue;
        let parsed = JSON.parse(fs.readFileSync(abs_g, "utf8"));
        let entries = Array.isArray(parsed) ? parsed : Object.values(parsed);

        for (let x = 0; x < entries.length; x++) {
          let ent = entries[x];

          if (!ent || !Array.isArray(ent.coords) || ent.coords.length < 2) continue;
          let lat = Number(ent.coords[0]);
          let lon = Number(ent.coords[1]);

          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          let gx = Math.max(0, Math.min(grid_w - 1, Math.floor((lon + 180)*grid_w/360)));
          let gy = Math.max(0, Math.min(grid_h - 1, Math.floor((90 - lat)*grid_h/180)));
          let gidx = gy*grid_w + gx;

          //Accept direct valid pixel or immediate 1-pixel coastal neighbour snapped onto valid land
          if (valid_mask && valid_mask[gidx] !== 1) {
            let snapped = -1;

            for (let dy = -1; dy <= 1 && snapped < 0; dy++) {
              let ny = gy + dy;

              if (ny < 0 || ny >= grid_h) continue;
              for (let dx = -1; dx <= 1; dx++) {
                let nx = (gx + dx + grid_w) % grid_w;

                if (valid_mask[ny*grid_w + nx] === 1) {
                  snapped = ny*grid_w + nx;
                  gx = nx;
                  gy = ny;
                  break;
                }
              }
            }
            if (snapped < 0) continue;
            gidx = snapped;
          }

          let pop_obj = (ent.population && typeof ent.population === "object") ? ent.population : null;

          if (!pop_obj) continue;
          let yr_keys = Object.keys(pop_obj);
          let has_valid_yr = false;

          for (let y = 0; y < yr_keys.length; y++) {
            let yr = Number(yr_keys[y]);
            let val = Number(pop_obj[yr_keys[y]]);

            if (!Number.isFinite(yr) || !Number.isFinite(val) || val <= 0 || yr > max_year) continue;
            has_valid_yr = true;
            let rec = pixel_map.get(gidx);

            if (!rec) {
              rec = {
                gx: gx,
                gy: gy,
                lat: lat,
                lon: lon,
                max_pop: 0,
                min_year: 99999,
                name: String(ent.name || ent.key || `px_${gx}_${gy}`),
                yr_pops: new Map()
              };
              pixel_map.set(gidx, rec);
            }
            if (yr < rec.min_year) rec.min_year = yr;
            if (val > rec.max_pop) {
              rec.max_pop = val;
              rec.name = String(ent.name || rec.name);
            }
            let prev = rec.yr_pops.get(yr) || 0;

            rec.yr_pops.set(yr, Math.max(prev, val));
          }
          if (has_valid_yr) raw_records_used++;
        }
      }

      let all_pixels = [];
      let preind_pixels = [];
      let settlements = [];

      pixel_map.forEach(function (arg0_rec) {
        let series = Array.from(arg0_rec.yr_pops.entries())
          .sort(function (arg0_a, arg1_b) { return arg0_a[0] - arg1_b[0]; })
          .map(function (arg0_pair) { return [arg0_pair[0], Math.round(arg0_pair[1])]; });

        if (series.length === 0) return;
        all_pixels.push([arg0_rec.gx, arg0_rec.gy]);
        if (arg0_rec.min_year <= preind_max_year)
          preind_pixels.push([arg0_rec.gx, arg0_rec.gy]);
        settlements.push({
          lat: Number(arg0_rec.lat.toFixed(4)),
          lon: Number(arg0_rec.lon.toFixed(4)),
          min_year: arg0_rec.min_year,
          name: arg0_rec.name,
          series: series
        });
      });

      settlements.sort(function (arg0_a, arg1_b) {
        return (arg0_a.lat !== arg1_b.lat) ? (arg0_a.lat - arg1_b.lat) : (arg0_a.lon - arg1_b.lon);
      });

      //Return statement
      return {
        all_pixels: all_pixels,
        preindustrial_pixels: preind_pixels,
        raw_records_used: raw_records_used,
        settlements: settlements
      };
    }


    /**
     * Step C: Writes canonical `documented_settlements.json` and `documented_site_pixels.json` into a domain's `config/` directory.
     * @alias ViscountSettlementAnchors.C_writeDomainAnchorFiles
     *
     * @param {string} arg0_config_dir
     * @param {Object} arg1_extracted
     * @param {Object} [arg2_options]
     *
     * @returns {Object}
     */
    static C_writeDomainAnchorFiles (arg0_config_dir, arg1_extracted, arg2_options) {
      //Convert from parameters
      let config_dir = arg0_config_dir;
      let extracted = arg1_extracted;
      let options = (arg2_options) ? arg2_options : {};

      //Guard clauses
      if (!extracted) return null;

      //Declare local instance variables
      let now_iso = new Date().toISOString();
      let px_path = path.join(config_dir, "documented_site_pixels.json");
      let sett_path = path.join(config_dir, "documented_settlements.json");

      //Function body
      fs.mkdirSync(config_dir, { recursive: true });
      let sett_payload = {
        count: extracted.settlements.length,
        generated_at_gmt0: now_iso,
        raw_records_merged: extracted.raw_records_used,
        settlements: extracted.settlements
      };
      let px_list = (options.use_preindustrial_for_pixels && extracted.preindustrial_pixels.length > 0) ?
        extracted.preindustrial_pixels :
        extracted.all_pixels;
      let px_payload = {
        count: px_list.length,
        generated_at_gmt0: now_iso,
        grid_height: 2160,
        grid_width: 4320,
        pixels: px_list,
        preindustrial_count: extracted.preindustrial_pixels.length,
        preindustrial_pixels: extracted.preindustrial_pixels
      };

      fs.writeFileSync(sett_path, JSON.stringify(sett_payload), "utf8");
      fs.writeFileSync(px_path, JSON.stringify(px_payload), "utf8");

      //Return statement
      return {
        pixel_count: px_list.length,
        preindustrial_pixel_count: extracted.preindustrial_pixels.length,
        px_path: px_path,
        sett_path: sett_path,
        settlement_count: extracted.settlements.length
      };
    }


    /**
     * Generates documented Stadestér settlement anchors for JADE, PRETA, and POLARIS (`sites_IA_RAS` & `sites_belarus_ukraine`).
     * @alias ViscountSettlementAnchors.buildAllRegionalAnchors
     *
     * @param {string} [arg0_project_root]
     *
     * @returns {Object}
     */
    static buildAllRegionalAnchors (arg0_project_root) {
      //Convert from parameters
      let root = arg0_project_root || process.cwd();

      //Declare local instance variables
      let results = {};
      let specs = [
        {
          config_dir: "histmap/1.data_raw/population_regional/JADE/_shared/sites_east_asia/config",
          domain_mask_png: "histmap/1.data_raw/population_regional/JADE/_shared/sites_east_asia/config/jade_domain_mask.png",
          key: "JADE",
          manifest: "histmap/1.data_raw/population_regional/JADE/jade_gazetteers.json5",
          max_year: 1911,
          preindustrial_max_year: 1850
        },
        {
          config_dir: "histmap/1.data_raw/population_regional/PRETA/_shared/sites_preta_amazon_brazil/config",
          domain_mask_png: "histmap/1.data_raw/population_regional/PRETA/_shared/sites_preta_amazon_brazil/config/preta_domain_mask.png",
          key: "PRETA",
          manifest: "histmap/1.data_raw/population_regional/PRETA/preta_gazetteers.json5",
          max_year: 1900,
          preindustrial_max_year: 1825
        },
        {
          config_dir: "histmap/1.data_raw/population_regional/POLARIS/_shared/sites_IA_RAS/config",
          domain_geocode_rgbs: [[20, 114, 30]],
          exclude_bbox: { max_lat: 56.5, max_lon: 25.0, min_lat: 53.0, min_lon: 18.0 },
          include_bbox: { max_lat: 46.23, max_lon: 36.66, min_lat: 44.35, min_lon: 32.45 },
          key: "POLARIS_IA_RAS",
          manifest: "histmap/1.data_raw/population_regional/POLARIS/polaris_gazetteers.json5",
          max_year: 1900,
          preindustrial_max_year: 1850
        },
        {
          config_dir: "histmap/1.data_raw/population_regional/POLARIS/_shared/sites_belarus_ukraine/config",
          domain_geocode_rgbs: [[169, 201, 169], [97, 150, 175]],
          exclude_bbox: { max_lat: 46.23, max_lon: 36.66, min_lat: 44.35, min_lon: 32.45 },
          key: "POLARIS_BY_UA",
          manifest: "histmap/1.data_raw/population_regional/POLARIS/polaris_gazetteers.json5",
          max_year: 1900,
          preindustrial_max_year: 1850
        }
      ];

      //Function body
      for (let i = 0; i < specs.length; i++) {
        let sp = specs[i];
        let mask = this.A_buildDomainLandMask({
          domain_geocode_rgbs: sp.domain_geocode_rgbs,
          domain_mask_png: sp.domain_mask_png,
          exclude_bbox: sp.exclude_bbox,
          include_bbox: sp.include_bbox,
          project_root: root
        });
        let extracted = this.B_extractFromGazetteerManifest(sp.manifest, mask, {
          max_year: sp.max_year,
          preindustrial_max_year: sp.preindustrial_max_year,
          project_root: root
        });
        let written = this.C_writeDomainAnchorFiles(path.resolve(root, sp.config_dir), extracted, {
          use_preindustrial_for_pixels: true
        });

        results[sp.key] = written;
        console.log(`[ViscountSettlementAnchors] ${sp.key}: settlements=${written.settlement_count}, pixels=${written.pixel_count}, preind_pixels=${written.preindustrial_pixel_count}`);
      }

      //Return statement
      return results;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountSettlementAnchors: global.ViscountSettlementAnchors };

if (require.main === module)
  global.ViscountSettlementAnchors.buildAllRegionalAnchors(process.cwd());
