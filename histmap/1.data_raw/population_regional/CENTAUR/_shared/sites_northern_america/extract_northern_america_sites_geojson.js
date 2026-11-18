//Import modules
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");
let { PNG } = require("pngjs");
let zlib = require("zlib");
let { NorthernAmericaSiteSources } = require("./NorthernAmericaSiteSources.js");

//Initialise functions
{
  /**
   * Builds 10 Holocene multi-registry archaeological catchment GeoJSONs (-10000 to 1600 AD) for CENTAUR-II
   * across North America, Greenland, Bermuda and Saint-Pierre-et-Miquelon, using fine US county / Canadian CD /
   * coastal Greenland fjord catchments (~2,350 domestic + ~240 cross-frontier units) and compositing ALL open
   * Northern American archaeological registries far beyond p3k14c/c14bazAAR.
   *
   * Logical flow uses lettered pipeline steps (A_ through E_):
   * - A_loadMasksAndConfig: Loads domain mask, HYDE land_area raster, ice-cap helper and kriging configuration.
   * - B_buildFineCatchments: Constructs ~2,350 fine US county, Canadian CD & Greenland fjord catchments + 240 frontier nodes.
   * - C_ingestMultiRegistryComposite: Composites Kelly/Robinson Lower48, p3k14c 2025, c14bazAAR, Nunniffiit, SWSN, VEP II, TX, SoCal, Plains, Midwest, NRHP, GeoNames, Gazetteer & POLARIS Chukotka.
   * - D_exportPeriodGeoJSONs: Writes all 10 chronological horizon GeoJSONs and 00_all_periods.geojson.
   * - E_writeMetadataJSON: Writes detailed catchment and source attribution metadata.
   *
   * @class NorthernAmericaSitesGeoJSONExtractor
   */
  global.NorthernAmericaSitesGeoJSONExtractor = class {
    static BASE_DIR = __dirname;
    static CONFIG_PATH = path.join(__dirname, "config", "sites_northern_america.json5");

    /**
     * Converts uncalibrated 14C years BP into approximate IntCal20 calibrated calendar years CE.
     * @alias NorthernAmericaSitesGeoJSONExtractor.calibrate14cToCE
     *
     * @param {number} arg0_age_bp
     *
     * @returns {number}
     */
    static calibrate14cToCE (arg0_age_bp) {
      return NorthernAmericaSiteSources.calibrate14cToCE(arg0_age_bp);
    }

    /**
     * Computes outer-ring mean centroid of a GeoJSON Polygon or MultiPolygon.
     * @alias NorthernAmericaSitesGeoJSONExtractor.computePolygonCentroid
     *
     * @param {Object} arg0_geometry
     *
     * @returns {Array<number>|null}
     */
    static computePolygonCentroid (arg0_geometry) {
      //Convert from parameters
      let geom = arg0_geometry;

      //Guard clauses
      if (!geom || !geom.coordinates) return null;

      //Declare local instance variables
      let lat_sum = 0;
      let lon_sum = 0;
      let pt_count = 0;
      let rings = [];

      if (geom.type === "Polygon" && geom.coordinates[0]) {
        rings.push(geom.coordinates[0]);
      } else if (geom.type === "MultiPolygon") {
        for (let i = 0; i < geom.coordinates.length; i++)
          if (geom.coordinates[i] && geom.coordinates[i][0]) rings.push(geom.coordinates[i][0]);
      }

      for (let i = 0; i < rings.length; i++) {
        let ring = rings[i];

        for (let x = 0; x < ring.length; x++) {
          let pt = ring[x];

          if (Array.isArray(pt) && pt.length >= 2) {
            lon_sum += Number(pt[0]);
            lat_sum += Number(pt[1]);
            pt_count++;
          }
        }
      }

      //Return statement
      return (pt_count > 0) ? [lon_sum/pt_count, lat_sum/pt_count] : null;
    }

    /**
     * Extracts text entry from a stored or deflated single-file ZIP archive using pure Node zlib.
     * @alias NorthernAmericaSitesGeoJSONExtractor.extractZipText
     *
     * @param {string} arg0_zip_path
     *
     * @returns {string}
     */
    static extractZipText (arg0_zip_path) {
      //Convert from parameters
      let zip_path = arg0_zip_path;

      //Guard clauses
      if (!fs.existsSync(zip_path)) return "";

      //Declare local instance variables
      let buf = fs.readFileSync(zip_path);
      let eocd = buf.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));

      if (eocd < 0) return "";
      let cd_offset = buf.readUInt32LE(eocd + 16);
      let sig = buf.readUInt32LE(cd_offset);

      if (sig !== 0x02014b50) return "";
      let comp_method = buf.readUInt16LE(cd_offset + 10);
      let comp_size = buf.readUInt32LE(cd_offset + 20);
      let local_hdr_off = buf.readUInt32LE(cd_offset + 42);
      let fname_len = buf.readUInt16LE(local_hdr_off + 26);
      let extra_len = buf.readUInt16LE(local_hdr_off + 28);
      let data_start = local_hdr_off + 30 + fname_len + extra_len;
      let slice = buf.subarray(data_start, data_start + comp_size);

      //Return statement
      if (comp_method === 0) return slice.toString("utf8");
      if (comp_method === 8) return zlib.inflateRawSync(slice).toString("utf8");
      return "";
    }

    /**
     * Computes great-circle Haversine distance in km between two [lon, lat] WGS84 points.
     * @alias NorthernAmericaSitesGeoJSONExtractor.haversineKm
     *
     * @param {number} arg0_lon1
     * @param {number} arg1_lat1
     * @param {number} arg2_lon2
     * @param {number} arg3_lat2
     *
     * @returns {number}
     */
    static haversineKm (arg0_lon1, arg1_lat1, arg2_lon2, arg3_lat2) {
      //Convert from parameters
      let lon1 = arg0_lon1*Math.PI/180;
      let lat1 = arg1_lat1*Math.PI/180;
      let lon2 = arg2_lon2*Math.PI/180;
      let lat2 = arg3_lat2*Math.PI/180;

      //Declare local instance variables
      let d_lat = lat2 - lat1;
      let d_lon = lon2 - lon1;
      let sin_dlat = Math.sin(d_lat*0.5);
      let sin_dlon = Math.sin(d_lon*0.5);
      let h = sin_dlat*sin_dlat + Math.cos(lat1)*Math.cos(lat2)*sin_dlon*sin_dlon;

      //Return statement
      return 12742*Math.asin(Math.min(1, Math.sqrt(h)));
    }

    /**
     * Parses a delimited CSV or TSV line respecting quoted fields.
     * @alias NorthernAmericaSitesGeoJSONExtractor.parseDelimitedLine
     *
     * @param {string} arg0_line
     * @param {string} [arg1_delim=","]
     *
     * @returns {Array<string>}
     */
    static parseDelimitedLine (arg0_line, arg1_delim) {
      //Convert from parameters
      let line = arg0_line;
      let delim = (arg1_delim !== undefined) ? arg1_delim : ",";

      //Declare local instance variables
      let current = "";
      let fields = [];
      let in_quotes = false;

      for (let i = 0; i < line.length; i++) {
        let ch = line[i];

        if (ch === "\"") {
          if (in_quotes && line[i + 1] === "\"") {
            current += "\"";
            i++;
          } else {
            in_quotes = !in_quotes;
          }
        } else if (ch === delim && !in_quotes) {
          fields.push(current);
          current = "";
        } else {
          current += ch;
        }
      }
      fields.push(current);

      //Return statement
      return fields;
    }

    /**
     * Converts UTM NAD83/WGS84 (easting, northing) in given zone to [lon, lat].
     * @alias NorthernAmericaSitesGeoJSONExtractor.utmToLonLat
     *
     * @param {number} arg0_easting
     * @param {number} arg1_northing
     * @param {number} [arg2_zone=12]
     *
     * @returns {Array<number>|null}
     */
    static utmToLonLat (arg0_easting, arg1_northing, arg2_zone) {
      //Convert from parameters
      let easting = Number(arg0_easting);
      let northing = Number(arg1_northing);
      let zone = (arg2_zone !== undefined) ? Number(arg2_zone) : 12;

      //Guard clauses
      if (!Number.isFinite(easting) || !Number.isFinite(northing)) return null;

      //Declare local instance variables
      let a = 6378137.0;
      let f = 1.0/298.257223563;
      let e2 = f*(2 - f);
      let ep2 = e2/(1 - e2);
      let k0 = 0.9996;
      let lon0 = ((zone - 1)*6 - 180 + 3)*Math.PI/180;
      let m = northing/k0;
      let mu = m/(a*(1 - e2/4 - 3*e2*e2/64 - 5*e2*e2*e2/256));
      let e1 = (1 - Math.sqrt(1 - e2))/(1 + Math.sqrt(1 - e2));
      let phi1 = mu +
        (3*e1/2 - 27*e1*e1*e1/32)*Math.sin(2*mu) +
        (21*e1*e1/16 - 55*e1*e1*e1*e1/32)*Math.sin(4*mu) +
        (151*e1*e1*e1/96)*Math.sin(6*mu);
      let sin_p = Math.sin(phi1);
      let cos_p = Math.cos(phi1);
      let tan_p = Math.tan(phi1);
      let n1 = a/Math.sqrt(1 - e2*sin_p*sin_p);
      let t1 = tan_p*tan_p;
      let c1 = ep2*cos_p*cos_p;
      let r1 = a*(1 - e2)/Math.pow(1 - e2*sin_p*sin_p, 1.5);
      let d = (easting - 500000.0)/(n1*k0);
      let lat = phi1 - (n1*tan_p/r1)*(
        d*d/2 -
        (5 + 3*t1 + 10*c1 - 4*c1*c1 - 9*ep2)*Math.pow(d, 4)/24 +
        (61 + 90*t1 + 298*c1 + 45*t1*t1 - 252*ep2 - 3*c1*c1)*Math.pow(d, 6)/720
      );
      let lon = lon0 + (
        d -
        (1 + 2*t1 + c1)*d*d*d/6 +
        (5 - 2*c1 + 28*t1 - 3*c1*c1 + 8*ep2 + 24*t1*t1)*Math.pow(d, 5)/120
      )/cos_p;

      //Return statement
      return [lon*180/Math.PI, lat*180/Math.PI];
    }

    /**
     * Step A: Loads sites_northern_america.json5, domain mask PNG, land_area raster and Greenland coastal ice-free mask.
     * @alias NorthernAmericaSitesGeoJSONExtractor.A_loadMasksAndConfig
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    static A_loadMasksAndConfig (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let config_path = (options.config_path) ? options.config_path : this.CONFIG_PATH;
      let config = JSON5.parse(fs.readFileSync(config_path, "utf8"));
      let project_root = (options.project_root) ? options.project_root : path.resolve(this.BASE_DIR, "../../../../../..");
      let mask_abs = path.join(project_root, config.kriging_config.domain_mask_png);
      let land_abs = path.join(project_root, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png");
      let mask_png = PNG.sync.read(fs.readFileSync(mask_abs));
      let land_png = PNG.sync.read(fs.readFileSync(land_abs));
      let width = mask_png.width;
      let height = mask_png.height;
      let n_px = width*height;
      let domain_mask = new Uint8Array(n_px);
      let gl_ice_mask = new Uint8Array(n_px);
      let land_area = new Float32Array(n_px);
      let land_buf = Buffer.from(land_png.data);

      for (let i = 0; i < n_px; i++) {
        let base = i*4;

        if (
          mask_png.data[base] > 0 ||
          mask_png.data[base + 1] > 0 ||
          mask_png.data[base + 2] > 0
        ) domain_mask[i] = 1;
        land_area[i] = land_buf.readUInt32BE(base);
      }

      if (config.kriging_config.bermuda_pixel) {
        let bp = config.kriging_config.bermuda_pixel;
        let b_idx = bp.row*width + bp.col;

        domain_mask[b_idx] = 1;
        if (land_area[b_idx] <= 0) land_area[b_idx] = bp.area_km2;
      }

      //Identify permanent Greenland interior ice cap (>2 pixels inland from ocean across lat>=60, lon>=-74)
      for (let r = 0; r < height; r++) {
        let lat = 90 - (r + 0.5)*180/height;

        if (lat < 60.0) continue;
        for (let c = 0; c < width; c++) {
          let lon = -180 + (c + 0.5)*360/width;
          let grl_west = -74.0;

          if (lat < 68.0) grl_west = -56.0;
          else if (lat < 74.0) grl_west = -56.0 - (lat - 68.0)*3.0;
          else if (lat >= 78.2) grl_west = -74.0 + (lat - 78.2)*3.4;

          if (lon < grl_west || lon > -11.0) continue;
          let idx = r*width + c;

          if (domain_mask[idx] !== 1 || land_area[idx] <= 0) continue;
          let near_sea = false;

          for (let dr = -2; dr <= 2 && !near_sea; dr++) {
            let nr = r + dr;

            if (nr < 0 || nr >= height) continue;
            for (let dc = -4; dc <= 4; dc++) {
              let nc = (c + dc + width) % width;

              if (land_area[nr*width + nc] <= 0) {
                near_sea = true;
                break;
              }
            }
          }
          if (!near_sea) gl_ice_mask[idx] = 1;
        }
      }

      //Return statement
      return {
        config: config,
        domain_mask: domain_mask,
        gl_ice_mask: gl_ice_mask,
        height: height,
        land_area: land_area,
        project_root: project_root,
        width: width
      };
    }

    /**
     * Step B: Builds ~2,350 fine domestic US county / Canadian CD / Greenland fjord catchments and ~240 cross-frontier units.
     * @alias NorthernAmericaSitesGeoJSONExtractor.B_buildFineCatchments
     *
     * @param {Object} arg0_state
     *
     * @returns {Object}
     */
    static B_buildFineCatchments (arg0_state) {
      //Convert from parameters
      let state = arg0_state;

      //Declare local instance variables
      let census_raw_dir = path.join(state.project_root, "histmap/1.data_raw/population_regional/CENTAUR/_shared/census_ingest/raw_sources");
      let domestic = [];
      let dom_mask = state.domain_mask;
      let frontier = [];
      let gl_ice = state.gl_ice_mask;
      let h = state.height;
      let hash_deg = 2.0;
      let land_area = state.land_area;
      let next_dom_id = 1;
      let next_front_id = 10001;
      let raw_na_dir = path.join(this.BASE_DIR, "raw_sources");
      let spatial_hash = new Map();
      let us_county_lookup = new Map();
      let w = state.width;

      let insertSeed = (arg0_list, arg1_id, arg2_lon, arg3_lat, arg4_is_front, arg5_label, arg6_min_sep) => {
        if (!Number.isFinite(arg2_lon) || !Number.isFinite(arg3_lat) || arg3_lat > 85 || arg3_lat < 18) return false;
        let cell_lon = Math.floor(arg2_lon/hash_deg);
        let cell_lat = Math.floor(arg3_lat/hash_deg);
        let max_dl = Math.min(20, Math.ceil(arg6_min_sep/(111*Math.max(0.15, Math.cos(arg3_lat*Math.PI/180))*hash_deg)) + 1);

        for (let dl = -max_dl; dl <= max_dl; dl++) {
          for (let dp = -2; dp <= 2; dp++) {
            let bucket = spatial_hash.get(`${cell_lon + dl}_${cell_lat + dp}`);

            if (!bucket) continue;
            for (let x = 0; x < bucket.length; x++) {
              let o = bucket[x];

              if (o.is_frontier_buffer !== arg4_is_front) continue;
              if (this.haversineKm(arg2_lon, arg3_lat, o.lon, o.lat) < arg6_min_sep) return false;
            }
          }
        }

        let item = {
          area_km2: 0,
          counts: new Array(state.config.periods.length).fill(0),
          habitable_area_km2: 0,
          is_frontier_buffer: arg4_is_front,
          label: arg5_label,
          lat: arg3_lat,
          lon: arg2_lon,
          pixel_count: 0,
          region_id: arg1_id,
          sample_sites: [],
          sum_lat: 0,
          sum_lon: 0
        };
        let key = `${cell_lon}_${cell_lat}`;

        arg0_list.push(item);
        if (!spatial_hash.has(key)) spatial_hash.set(key, []);
        spatial_hash.get(key).push(item);

        return true;
      };

      //1. Pin special island & Greenland coastal fjord anchors first
      let special_anchors = [
        [-64.78, 32.30, "Bermuda"],
        [-56.17, 46.78, "Saint-Pierre-et-Miquelon"],
        [-132.10, 53.10, "Haida Gwaii"],
        [-126.00, 49.70, "Vancouver Island North"],
        [-123.40, 48.50, "Victoria-Salish"],
        [-63.20, 46.40, "Prince Edward Island"],
        [-153.30, 57.60, "Kodiak Island"],
        [-174.00, 52.20, "Central Aleutians"],
        [-166.50, 53.90, "Unalaska"],
        [-70.56, 76.80, "Nuulliit-Avanersuaq"],
        [-69.23, 77.47, "Qaanaaq-Thule"],
        [-56.15, 72.79, "Upernavik"],
        [-52.13, 70.67, "Uummannaq"],
        [-53.53, 69.25, "Qeqertarsuaq-Disko"],
        [-51.10, 69.22, "Ilulissat-Sermermiut"],
        [-51.15, 68.82, "Qasigiannguit"],
        [-52.85, 68.71, "Aasiaat"],
        [-53.67, 66.94, "Sisimiut-Nipisat"],
        [-52.90, 65.42, "Maniitsoq"],
        [-51.74, 64.18, "Nuuk-Sandnes"],
        [-50.70, 63.08, "Qeqertarsuatsiaat"],
        [-49.67, 62.00, "Paamiut"],
        [-46.03, 60.72, "Qaqortoq-Brattahlid"],
        [-45.24, 60.14, "Nanortalik-Herjolfsnes"],
        [-37.63, 65.61, "Tasiilaq-Ammassalik"],
        [-21.97, 70.49, "Ittoqqortoormiit"]
      ];

      for (let i = 0; i < special_anchors.length; i++) {
        let sp = special_anchors[i];

        if (insertSeed(domestic, next_dom_id, sp[0], sp[1], false, sp[2], 35)) next_dom_id++;
      }

      //2. Load all US County centroids (2020_Gaz_counties_national.zip) and index County+State for gazetteer/Midwest matching
      let county_txt = this.extractZipText(path.join(census_raw_dir, "2020_Gaz_counties_national.zip"));

      if (county_txt) {
        let c_lines = county_txt.split(/\r?\n/);

        for (let i = 1; i < c_lines.length; i++) {
          if (!c_lines[i]) continue;
          let cols = c_lines[i].split("\t");

          if (cols.length < 10) continue;
          let usps = cols[0].trim();
          let cname = cols[3].trim();
          let aland_km2 = Number(cols[4])/(1e6);
          let lat = Number(cols[8]);
          let lon = Number(cols[9]);

          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          let norm_c = cname.replace(/\s+(County|Parish|Borough|Census Area|Municipality|City and Borough|City)$/i, "").toLowerCase().replace(/[^a-z0-9]/g, "");

          us_county_lookup.set(`${usps}|${norm_c}`, { aland_km2: aland_km2, lat: lat, lon: lon, name: cname });
          if (insertSeed(domestic, next_dom_id, lon, lat, false, `${cname}, ${usps}`, 18)) next_dom_id++;
        }
      }

      //3. Seed StatCan 2021 Census Divisions (293 CDs)
      let cd_path = path.join(census_raw_dir, "statcan_2021_cd.geojson");

      if (fs.existsSync(cd_path)) {
        let cd_gj = JSON.parse(fs.readFileSync(cd_path, "utf8"));
        let feats = Array.isArray(cd_gj.features) ? cd_gj.features : [];

        for (let i = 0; i < feats.length; i++) {
          let ft = feats[i];
          let props = ft.properties || {};
          let cen = this.computePolygonCentroid(ft.geometry);

          if (!cen) continue;
          let min_sep = (cen[1] < 50) ? 22 : 65;

          if (insertSeed(domestic, next_dom_id, cen[0], cen[1], false, `${props.CDNAME || "CD"} (${props.PRUID || ""})`, min_sep))
            next_dom_id++;
        }
      }

      //3b. Seed HydroBASINS Level 4 watershed subbasin centroids across Western US, Canada, Alaska & Greenland (ADM2 x HydroBASINS)
      let hb_path = path.join(state.project_root, "histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/hydrobasins_centroids_na_ar_gr.json");

      if (fs.existsSync(hb_path)) {
        let hb_pts = JSON.parse(fs.readFileSync(hb_path, "utf8"));

        for (let i = 0; i < hb_pts.length; i++) {
          let hp = hb_pts[i];
          let gx = Math.min(w - 1, Math.max(0, Math.floor((hp.lon + 180)*w/360)));
          let gy = Math.min(h - 1, Math.max(0, Math.floor((90 - hp.lat)*h/180)));
          let gidx = gy*w + gx;

          if (dom_mask[gidx] === 1 && gl_ice[gidx] === 0 && land_area[gidx] > 0) {
            let h_sep = (hp.lat < 50) ? 34 : 58;

            if (insertSeed(domestic, next_dom_id, hp.lon, hp.lat, false, `HB_${hp.pfaf_id}`, h_sep))
              next_dom_id++;
          }
        }
      }

      //4. Fill remaining large western/Alaskan counties, Canadian river corridors, and ice-free Greenland fjords stratified by latitude
      for (let r = 0; r < h; r++) {
        let lat = 90 - (r + 0.5)*180/h;

        if (lat < 23 || lat > 84) continue;
        for (let c = 0; c < w; c++) {
          let idx = r*w + c;

          if (dom_mask[idx] !== 1 || land_area[idx] <= 0 || gl_ice[idx] === 1) continue;
          let lon = -180 + (c + 0.5)*360/w;
          let min_sep = (lon < -100) ? 44 : 58;

          if (lat >= 50 && lat < 60) min_sep = 88;
          if (lat >= 60) min_sep = (lon >= -58) ? 120 : 128;
          if (lat >= 55 && lon >= -170 && lon <= -130) min_sep = 92;

          if (insertSeed(domestic, next_dom_id, lon, lat, false, `NA_${next_dom_id}`, min_sep))
            next_dom_id++;
        }
      }

      //5. Seed cross-frontier conditioning centroids across N. Mexico, Chukotka/Kamchatka and Cuba/Bahamas
      for (let r = 0; r < h; r++) {
        let lat = 90 - (r + 0.5)*180/h;

        for (let c = 0; c < w; c++) {
          let idx = r*w + c;

          if (dom_mask[idx] === 1 || land_area[idx] <= 0) continue;
          let lon = -180 + (c + 0.5)*360/w;
          let is_mex_buf = (lat >= 24.5 && lat <= 32.8 && lon >= -117.5 && lon <= -96.5);
          let is_cub_buf = (lat >= 19.6 && lat <= 27.2 && lon >= -85.2 && lon <= -72.0);
          let is_ruk_buf = (lat >= 58.0 && lat <= 71.5 && ((lon >= 152.0 && lon <= 180.0) || lon <= -168.0));

          if (!is_mex_buf && !is_cub_buf && !is_ruk_buf) continue;
          let f_sep = (is_ruk_buf) ? 140 : 95;
          let f_tag = (is_mex_buf) ? "MEX_BUF" : ((is_cub_buf) ? "CARIB_BUF" : "RUK_BUF");

          if (insertSeed(frontier, next_front_id, lon, lat, true, `${f_tag}_${next_front_id}`, f_sep))
            next_front_id++;
        }
      }

      //6. Assign domain & frontier pixels to nearest catchment centroid using fast spatial hash lookup
      let assignNearest = (arg0_list, arg1_lon, arg2_lat, arg3_max_km) => {
        let cl = Math.floor(arg1_lon/hash_deg);
        let cp = Math.floor(arg2_lat/hash_deg);
        let best = null;
        let best_d = arg3_max_km;
        let is_f = (arg0_list === frontier);

        for (let dl = -2; dl <= 2; dl++) {
          for (let dp = -2; dp <= 2; dp++) {
            let bucket = spatial_hash.get(`${cl + dl}_${cp + dp}`);

            if (!bucket) continue;
            for (let x = 0; x < bucket.length; x++) {
              let o = bucket[x];

              if (o.is_frontier_buffer !== is_f) continue;
              let d = this.haversineKm(arg1_lon, arg2_lat, o.lon, o.lat);

              if (d < best_d) {
                best_d = d;
                best = o;
              }
            }
          }
        }
        if (!best) {
          for (let x = 0; x < arg0_list.length; x++) {
            let d = this.haversineKm(arg1_lon, arg2_lat, arg0_list[x].lon, arg0_list[x].lat);

            if (d < best_d) {
              best_d = d;
              best = arg0_list[x];
            }
          }
        }
        return best;
      };

      for (let r = 0; r < h; r++) {
        let lat = 90 - (r + 0.5)*180/h;

        if (lat < 19 || lat > 84) continue;
        for (let c = 0; c < w; c++) {
          let idx = r*w + c;
          let area = land_area[idx];

          if (area <= 0) continue;
          let lon = -180 + (c + 0.5)*360/w;

          if (dom_mask[idx] === 1) {
            let target = assignNearest(domestic, lon, lat, 1500);

            if (target) {
              target.area_km2 += area;
              if (gl_ice[idx] === 0) {
                target.habitable_area_km2 += area;
                target.sum_lon += lon*area;
                target.sum_lat += lat*area;
              }
              target.pixel_count++;
            }
          } else {
            let in_buf = (
              (lat >= 24.5 && lat <= 32.8 && lon >= -117.5 && lon <= -96.5) ||
              (lat >= 19.6 && lat <= 27.2 && lon >= -85.2 && lon <= -72.0) ||
              (lat >= 58.0 && lat <= 71.5 && ((lon >= 152.0 && lon <= 180.0) || lon <= -168.0))
            );

            if (in_buf) {
              let target = assignNearest(frontier, lon, lat, 400);

              if (target) {
                target.area_km2 += area;
                target.habitable_area_km2 += area;
                target.pixel_count++;
                target.sum_lon += lon*area;
                target.sum_lat += lat*area;
              }
            }
          }
        }
      }

      //Re-centre each catchment on its habitable area-weighted centroid (excluding Greenland interior ice cap!)
      let all_catchments = [];
      let raw_all = domestic.concat(frontier);

      for (let i = 0; i < raw_all.length; i++) {
        let c_obj = raw_all[i];

        if (c_obj.area_km2 <= 0) continue;
        let denom = (c_obj.habitable_area_km2 > 0) ? c_obj.habitable_area_km2 : c_obj.area_km2;

        if (c_obj.habitable_area_km2 > 0) {
          c_obj.lon = Number((c_obj.sum_lon/denom).toFixed(5));
          c_obj.lat = Number((c_obj.sum_lat/denom).toFixed(5));
        }
        c_obj.area_km2 = Math.round(denom);
        all_catchments.push(c_obj);
      }

      state.all_catchments = all_catchments;
      state.domestic_catchments = all_catchments.filter((x) => !x.is_frontier_buffer);
      state.frontier_catchments = all_catchments.filter((x) => x.is_frontier_buffer);
      state.us_county_lookup = us_county_lookup;
      state.hash_deg = hash_deg;

      //Rebuild spatial hash on final centroids for rapid C_ assignment
      let final_hash = new Map();

      for (let i = 0; i < all_catchments.length; i++) {
        let o = all_catchments[i];
        let k = `${Math.floor(o.lon/hash_deg)}_${Math.floor(o.lat/hash_deg)}`;

        if (!final_hash.has(k)) final_hash.set(k, []);
        final_hash.get(k).push(o);
      }
      state.final_hash = final_hash;

      //Return statement
      return state;
    }

    /**
     * Step C: Composites ALL open Northern American archaeological registries + Chukotka/Mexico/Caribbean frontier conditioning.
     * @alias NorthernAmericaSitesGeoJSONExtractor.C_ingestMultiRegistryComposite
     *
     * @param {Object} arg0_state
     *
     * @returns {Object}
     */
    static C_ingestMultiRegistryComposite (arg0_state) {
      //Convert from parameters
      let state = arg0_state;

      //Declare local instance variables
      let domestic = state.domestic_catchments;
      let final_hash = state.final_hash;
      let frontier = state.frontier_catchments;
      let hash_deg = state.hash_deg || 2.0;
      let ia_ras_dir = path.join(state.project_root, "histmap/1.data_raw/population_regional/POLARIS/_shared/sites_IA_RAS/geojson");
      let n_periods = state.config.periods.length;
      let periods = state.config.periods;
      let raw_c14_dir = path.join(state.project_root, "histmap/1.data_raw/population_c14bazAAR");
      let raw_na_dir = path.join(this.BASE_DIR, "raw_sources");
      let seen_labs = new Set();
      let seen_site_horizon = new Set();
      let source_counts = {};
      let total_unique_site_periods = 0;

      let US_STATE_ABBR = {
        "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
        "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
        "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
        "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
        "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
        "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
        "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
        "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
        "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
        "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
      };

      let assignNearestCatchment = (arg0_lon, arg1_lat, arg2_is_front, arg3_max_km) => {
        let cl = Math.floor(arg0_lon/hash_deg);
        let cp = Math.floor(arg1_lat/hash_deg);
        let best = null;
        let best_d = arg3_max_km;

        for (let dl = -2; dl <= 2; dl++) {
          for (let dp = -2; dp <= 2; dp++) {
            let bucket = final_hash.get(`${cl + dl}_${cp + dp}`);

            if (!bucket) continue;
            for (let x = 0; x < bucket.length; x++) {
              let o = bucket[x];

              if (o.is_frontier_buffer !== arg2_is_front) continue;
              let d = this.haversineKm(arg0_lon, arg1_lat, o.lon, o.lat);

              if (d < best_d) {
                best_d = d;
                best = o;
              }
            }
          }
        }
        if (!best) {
          let list = (arg2_is_front) ? frontier : domestic;

          for (let x = 0; x < list.length; x++) {
            let d = this.haversineKm(arg0_lon, arg1_lat, list[x].lon, list[x].lat);

            if (d < best_d) {
              best_d = d;
              best = list[x];
            }
          }
        }
        return best;
      };

      let getPeriodIndicesForSpan = (arg0_y0, arg1_y1) => {
        let out = [];

        for (let i = 0; i < n_periods; i++) {
          if (arg1_y1 >= periods[i].approx_start_year && arg0_y0 < periods[i].approx_end_year)
            out.push(i);
        }
        return out;
      };

      let recordSitePeriod = (arg0_p_idx, arg1_lon, arg2_lat, arg3_site, arg4_weight, arg5_is_front, arg6_src, arg7_lab) => {
        if (arg0_p_idx < 0 || arg0_p_idx >= n_periods) return;
        if (!Number.isFinite(arg1_lon) || !Number.isFinite(arg2_lat)) return;
        let clean_lab = (arg7_lab || "").trim();

        if (clean_lab.length > 2) {
          if (seen_labs.has(clean_lab)) return;
          seen_labs.add(clean_lab);
        }

        let norm_site = (arg3_site || "anon").toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 18);
        let site_key = (arg6_src === "Greenland_Nunniffiit") ?
          `${arg0_p_idx}|${(Math.round(arg2_lat/0.03)*0.03).toFixed(2)}|${(Math.round(arg1_lon/0.03)*0.03).toFixed(2)}|gl` :
          `${arg0_p_idx}|${arg2_lat.toFixed(2)}|${arg1_lon.toFixed(2)}|${norm_site}`;

        if (seen_site_horizon.has(site_key)) return;
        seen_site_horizon.add(site_key);

        let catchment = assignNearestCatchment(arg1_lon, arg2_lat, arg5_is_front, 200);

        if (catchment) {
          catchment.counts[arg0_p_idx] += (arg4_weight || 1.0);
          total_unique_site_periods++;
          source_counts[arg6_src] = (source_counts[arg6_src] || 0) + 1;
          if (catchment.sample_sites.length < 3 && norm_site.length > 1)
            catchment.sample_sites.push({
              coordinates: [Number(arg1_lon.toFixed(4)), Number(arg2_lat.toFixed(4))],
              name: String(arg3_site || "").slice(0, 48),
              source: arg6_src
            });
        }
      };

      NorthernAmericaSiteSources.ingestAllRegistries(state, {
        assignNearestCatchment: assignNearestCatchment,
        getPeriodIndicesForSpan: getPeriodIndicesForSpan,
        parseDelimitedLine: this.parseDelimitedLine.bind(this),
        raw_na_dir: raw_na_dir,
        recordSitePeriod: recordSitePeriod,
        source_counts: source_counts,
        utmToLonLat: this.utmToLonLat.bind(this)
      });

      state.total_unique_site_periods = total_unique_site_periods;
      state.source_counts = source_counts;

      //Return statement
      return state;
    }

    /**
     * Step D: Writes the 10 period GeoJSONs and 00_all_periods.geojson.
     * @alias NorthernAmericaSitesGeoJSONExtractor.D_exportPeriodGeoJSONs
     *
     * @param {Object} arg0_state
     *
     * @returns {Object}
     */
    static D_exportPeriodGeoJSONs (arg0_state) {
      //Convert from parameters
      let state = arg0_state;

      //Declare local instance variables
      let all_catchments = state.all_catchments;
      let all_periods_features = [];
      let geojson_dir = path.join(this.BASE_DIR, state.config.output_geojson_subfolder);
      let periods = state.config.periods;
      let period_summaries = [];

      fs.mkdirSync(geojson_dir, { recursive: true });
      for (let p = 0; p < periods.length; p++) {
        let p_cfg = periods[p];
        let features = [];
        let dom_sites = 0;
        let front_sites = 0;

        for (let i = 0; i < all_catchments.length; i++) {
          let c = all_catchments[i];
          let sc = Number(c.counts[p].toFixed(2));

          if (c.is_frontier_buffer) front_sites += sc;
          else dom_sites += sc;

          features.push({
            geometry: {
              coordinates: [c.lon, c.lat],
              type: "Point"
            },
            properties: {
              approx_end_year: p_cfg.approx_end_year,
              approx_start_year: p_cfg.approx_start_year,
              area_km2: c.area_km2,
              epoch_id: p_cfg.epoch_id,
              is_frontier_buffer: c.is_frontier_buffer,
              name_en: c.label,
              period_key: p_cfg.key,
              pixel_count: c.pixel_count,
              region_id: c.region_id,
              sample_sites: c.sample_sites,
              site_count: sc
            },
            type: "Feature"
          });
        }

        let fc = {
          features: features,
          metadata: {
            approx_end_year: p_cfg.approx_end_year,
            approx_start_year: p_cfg.approx_start_year,
            date_range_en: p_cfg.date_range_en,
            domestic_catchments: state.domestic_catchments.length,
            domestic_site_count: Math.round(dom_sites),
            epoch_id: p_cfg.epoch_id,
            frontier_buffer_catchments: state.frontier_catchments.length,
            frontier_site_count: Math.round(front_sites),
            period_key: p_cfg.key
          },
          type: "FeatureCollection"
        };

        fs.writeFileSync(path.join(geojson_dir, p_cfg.geojson_filename), JSON.stringify(fc, null, 2));
        period_summaries.push(fc.metadata);
        if (p === 0) all_periods_features = features.map((ft) => ({
          geometry: ft.geometry,
          properties: {
            area_km2: ft.properties.area_km2,
            is_frontier_buffer: ft.properties.is_frontier_buffer,
            name_en: ft.properties.name_en,
            region_id: ft.properties.region_id,
            total_sites_all_periods: Math.round(all_catchments.find((x) => x.region_id === ft.properties.region_id).counts.reduce((a, b) => a + b, 0))
          },
          type: "Feature"
        }));
      }

      if (state.config.include_all_periods_geojson) {
        fs.writeFileSync(
          path.join(geojson_dir, "00_all_periods.geojson"),
          JSON.stringify({ features: all_periods_features, type: "FeatureCollection" }, null, 2)
        );
      }

      state.period_summaries = period_summaries;

      //Return statement
      return state;
    }

    /**
     * Step E: Writes GeoJSON summary metadata and multi-registry source counts.
     * @alias NorthernAmericaSitesGeoJSONExtractor.E_writeMetadataJSON
     *
     * @param {Object} arg0_state
     *
     * @returns {Object}
     */
    static E_writeMetadataJSON (arg0_state) {
      //Convert from parameters
      let state = arg0_state;

      //Declare local instance variables
      let out_abs = path.join(this.BASE_DIR, state.config.geojson_metadata_filename);
      let payload = {
        domestic_catchments: state.domestic_catchments.length,
        frontier_buffer_catchments: state.frontier_catchments.length,
        generated_at_gmt0: new Date().toISOString(),
        periods: state.period_summaries,
        source_counts: state.source_counts,
        sources: [
          "Kelly, Robinson et al. (2021/2025) Lower 48 Archaeological Radiocarbon Database",
          "PEOPLE 3000 (p3k14c 2025.07 Release) & c14bazAAR Deduplicated Synthesis (USA, Canada, Greenland, Mexico, Caribbean, Chukotka)",
          "Greenland National Museum Nunniffiit Archaeological & Historical Database (11 Pre-Colonial Cultures + Norse)",
          "Southwest Social Networks (SWSN) & cyberSW CriticalScales Regional Site Database",
          "Village Ecodynamics Project II (Reese 2021 / Kohler et al.) Central Mesa Verde Habitation Sites",
          "Texas Trinomial Radiocarbon Database (FinalRCDTexas3) & Southern California Radiocarbon Database (SoCaldates)",
          "Milner et al. (2023) Midwest & Southeast Cultural Index Settlement Database",
          "POLARIS sites_IA_RAS Russian Far East GeoJSON Conditioning Frontier"
        ],
        total_domestic_area_km2: state.domestic_catchments.reduce((a, b) => a + b.area_km2, 0),
        total_unique_site_periods: state.total_unique_site_periods
      };

      fs.writeFileSync(out_abs, JSON.stringify(payload, null, 2));

      //Return statement
      return payload;
    }

    /**
     * Runs steps A_ through E_.
     * @alias NorthernAmericaSitesGeoJSONExtractor.run
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    static run (arg0_options) {
      let state = this.A_loadMasksAndConfig(arg0_options);

      state = this.B_buildFineCatchments(state);
      state = this.C_ingestMultiRegistryComposite(state);
      state = this.D_exportPeriodGeoJSONs(state);

      //Return statement
      return this.E_writeMetadataJSON(state);
    }
  };
}

if (require.main === module) {
  let meta = global.NorthernAmericaSitesGeoJSONExtractor.run();

  console.log(JSON.stringify({
    domestic_catchments: meta.domestic_catchments,
    frontier_buffer_catchments: meta.frontier_buffer_catchments,
    total_domestic_area_km2: meta.total_domestic_area_km2,
    total_unique_site_periods: meta.total_unique_site_periods,
    source_counts: meta.source_counts,
    periods: meta.periods.map((p) => `${p.period_key}: dom=${p.domestic_site_count}, front=${p.frontier_site_count}`)
  }, null, 2));
}
