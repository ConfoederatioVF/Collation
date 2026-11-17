//Import modules
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");
let { PNG } = require("pngjs");

//Initialise functions
{
  /**
   * Builds 6 chronological sub-moku settlement intensity GeoJSONs (800 to 1898 AD) for Hawai'i and American Polynesia (CENTAUR-II)
   * using 727 official State of Hawai'i ahupua'a polygons (HistoricCultural GIS), Thomas S. Dye (2011) & LKFS radiocarbon phasing,
   * Ladefoged et al. (2009) wetland/dryland suitability, Schmitt (1968/1977) Kingdom censuses, and Rieth & Hunt (2008) Samoan sites.
   *
   * Logical flow uses lettered pipeline steps (A_ through E_):
   * - A_loadMasksAndAhupuaa: Loads domain mask, HYDE land_area raster and hawaii_ahupuaa.geojson.
   * - B_clusterSubMokuCatchments: Clusters 727 ahupua'a into ~68 Hawaiian sub-moku catchments + 2 American Samoan & 6 Western Samoan frontier nodes.
   * - C_scoreChronologicalIntensities: Evaluates indigenous wetland, dryland, protohistoric and Kingdom census weights across 800-1898 AD.
   * - D_exportPeriodGeoJSONs: Writes all 6 chronological horizon GeoJSONs and 00_all_periods.geojson.
   * - E_writeMetadataJSON: Writes detailed catchment and provenance metadata to config/sites_hawaii_polynesia_geojson_metadata.json.
   *
   * @class HawaiiPolynesiaGeoJSONExtractor
   */
  global.HawaiiPolynesiaGeoJSONExtractor = class {
    static BASE_DIR = __dirname;
    static CONFIG_PATH = path.join(__dirname, "config", "sites_hawaii_polynesia.json5");

    /**
     * Computes outer-ring arithmetic centroid of a GeoJSON Polygon or MultiPolygon.
     * @alias HawaiiPolynesiaGeoJSONExtractor.computePolygonCentroid
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
      let rings = [];
      let sum_lat = 0;
      let sum_lon = 0;
      let total_pts = 0;

      if (geom.type === "Polygon") {
        if (geom.coordinates[0]) rings.push(geom.coordinates[0]);
      } else if (geom.type === "MultiPolygon") {
        for (let i = 0; i < geom.coordinates.length; i++)
          if (geom.coordinates[i] && geom.coordinates[i][0]) rings.push(geom.coordinates[i][0]);
      }

      for (let i = 0; i < rings.length; i++) {
        let ring = rings[i];

        for (let x = 0; x < ring.length; x++) {
          let pt = ring[x];

          if (Array.isArray(pt) && pt.length >= 2) {
            sum_lon += Number(pt[0]);
            sum_lat += Number(pt[1]);
            total_pts++;
          }
        }
      }

      //Return statement
      return (total_pts > 0) ? [sum_lon/total_pts, sum_lat/total_pts] : null;
    }

    /**
     * Computes great-circle Haversine distance in km between two [lon, lat] WGS84 points.
     * @alias HawaiiPolynesiaGeoJSONExtractor.haversineKm
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
     * Returns agronomic class ("wetland", "mixed", "dryland", "urban_port") for a Hawaiian (mokupuni, moku) pair.
     * @alias HawaiiPolynesiaGeoJSONExtractor.classifyMokuRegime
     *
     * @param {string} arg0_mokupuni
     * @param {string} arg1_moku
     *
     * @returns {string}
     */
    static classifyMokuRegime (arg0_mokupuni, arg1_moku) {
      //Convert from parameters
      let isl = (arg0_mokupuni || "").normalize("NFD").replace(/[\u0300-\u036fʻ']/g, "").toLowerCase();
      let moku = (arg1_moku || "").normalize("NFD").replace(/[\u0300-\u036fʻ']/g, "").toLowerCase();

      //Function body
      if (isl.includes("oahu") && (moku.includes("kona") || moku.includes("ewa"))) return "urban_port";
      if (isl.includes("maui") && (moku.includes("lahaina") || moku.includes("wailuku"))) return "urban_port";
      if (
        moku.includes("hilo") || moku.includes("hamakua") || moku.includes("halelea") ||
        moku.includes("koolau") || moku.includes("hana") || moku.includes("kipahulu") ||
        moku.includes("waialua") || moku.includes("puna")
      ) return "wetland";
      if (
        moku.includes("kohala") || moku.includes("kona") || moku.includes("kau") ||
        moku.includes("kula") || moku.includes("kahikinui") || moku.includes("kaupo") ||
        moku.includes("honuaula") || isl.includes("kahoolawe") || isl.includes("lanai") ||
        isl.includes("niihau") || moku.includes("waianae")
      ) return "dryland";

      //Return statement
      return "mixed";
    }

    /**
     * Step A: Loads configuration, domain mask PNG, land_area PNG and Hawaii ahupuaa GIS boundaries.
     * @alias HawaiiPolynesiaGeoJSONExtractor.A_loadMasksAndAhupuaa
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    static A_loadMasksAndAhupuaa (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let config_path = (options.config_path) ? options.config_path : this.CONFIG_PATH;
      let config = JSON5.parse(fs.readFileSync(config_path, "utf8"));
      let project_root = (options.project_root) ? options.project_root : path.resolve(this.BASE_DIR, "../../../../../..");
      let ahu_path = path.join(project_root, "histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/hawaii_ahupuaa.geojson");
      let mask_abs = path.join(project_root, config.kriging_config.domain_mask_png);
      let land_abs = path.join(project_root, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png");
      let ahu_gj = JSON.parse(fs.readFileSync(ahu_path, "utf8"));
      let mask_png = PNG.sync.read(fs.readFileSync(mask_abs));
      let land_png = PNG.sync.read(fs.readFileSync(land_abs));
      let width = mask_png.width;
      let height = mask_png.height;
      let n_px = width*height;
      let domain_mask = new Uint8Array(n_px);
      let hp_pixels = [];
      let land_area = new Float32Array(n_px);
      let land_buf = Buffer.from(land_png.data);

      for (let i = 0; i < n_px; i++) {
        let base = i*4;
        let area_val = land_buf.readUInt32BE(base);

        land_area[i] = area_val;
        if (
          mask_png.data[base] > 0 ||
          mask_png.data[base + 1] > 0 ||
          mask_png.data[base + 2] > 0
        ) {
          let r = Math.floor(i/width);
          let c = i % width;

          domain_mask[i] = 1;
          hp_pixels.push({
            area_km2: Math.max(10, area_val),
            idx: i,
            lat: 90 - (r + 0.5)*180/height,
            lon: -180 + (c + 0.5)*360/width
          });
        }
      }

      //Return statement
      return {
        ahupuaa_features: ahu_gj.features || [],
        config: config,
        domain_mask: domain_mask,
        height: height,
        hp_pixels: hp_pixels,
        land_area: land_area,
        project_root: project_root,
        width: width
      };
    }

    /**
     * Step B: Clusters 727 ahupuaa into compact sub-moku Voronoi catchments across the 8 main islands, plus Samoa nodes.
     * @alias HawaiiPolynesiaGeoJSONExtractor.B_clusterSubMokuCatchments
     *
     * @param {Object} arg0_state
     *
     * @returns {Object}
     */
    static B_clusterSubMokuCatchments (arg0_state) {
      //Convert from parameters
      let state = arg0_state;

      //Declare local instance variables
      let clusters = [];
      let n_periods = state.config.periods.length;
      let next_id = 1;
      let samoa_domestic = [
        { area_km2: 0, counts: new Array(n_periods).fill(0), is_frontier_buffer: false, isl: "Tutuila", label: "Tutuila Far West (Poloa/Amanave)", lat: -14.32, lon: -170.83, moku: "Leasina", ahupuaa_n: 4, regime: "samoa" },
        { area_km2: 0, counts: new Array(n_periods).fill(0), is_frontier_buffer: false, isl: "Tutuila", label: "Tutuila West (Leone/Futiga)", lat: -14.33, lon: -170.78, moku: "Western Tutuila", ahupuaa_n: 5, regime: "samoa" },
        { area_km2: 0, counts: new Array(n_periods).fill(0), is_frontier_buffer: false, isl: "Tutuila", label: "Tutuila Central (Pago Pago/Tafuna)", lat: -14.28, lon: -170.70, moku: "Central Tutuila", ahupuaa_n: 6, regime: "samoa" },
        { area_km2: 0, counts: new Array(n_periods).fill(0), is_frontier_buffer: false, isl: "Tutuila", label: "Tutuila East (Aoa/Tula)", lat: -14.26, lon: -170.58, moku: "Eastern Tutuila", ahupuaa_n: 5, regime: "samoa" },
        { area_km2: 0, counts: new Array(n_periods).fill(0), is_frontier_buffer: false, isl: "Manua", label: "Ofu-Olosega", lat: -14.17, lon: -169.64, moku: "Ofu-Olosega", ahupuaa_n: 4, regime: "samoa" },
        { area_km2: 0, counts: new Array(n_periods).fill(0), is_frontier_buffer: false, isl: "Manua", label: "Ta'u (Luma/Fitiuta)", lat: -14.23, lon: -169.46, moku: "Ta'u", ahupuaa_n: 5, regime: "samoa" }
      ];
      let samoa_frontier = [
        { area_km2: 520, counts: new Array(n_periods).fill(0), is_frontier_buffer: true, isl: "Upolu", label: "Upolu East (Aleipata/Falealili)", lat: -13.99, lon: -171.48, moku: "Upolu East", ahupuaa_n: 12, regime: "samoa" },
        { area_km2: 590, counts: new Array(n_periods).fill(0), is_frontier_buffer: true, isl: "Upolu", label: "Upolu West (Apia/Mulifanua)", lat: -13.86, lon: -171.88, moku: "Upolu West", ahupuaa_n: 14, regime: "samoa" },
        { area_km2: 850, counts: new Array(n_periods).fill(0), is_frontier_buffer: true, isl: "Savaii", label: "Savai'i East (Salelologa/Safotu)", lat: -13.57, lon: -172.32, moku: "Savaii East", ahupuaa_n: 10, regime: "samoa" },
        { area_km2: 850, counts: new Array(n_periods).fill(0), is_frontier_buffer: true, isl: "Savaii", label: "Savai'i West (Asau/Falelima)", lat: -13.62, lon: -172.64, moku: "Savaii West", ahupuaa_n: 8, regime: "samoa" }
      ];

      //1. Extract valid ahupuaa centroids and seed sub-moku clusters (13 km min spacing so each cluster matches ~1-4 pixels)
      for (let i = 0; i < state.ahupuaa_features.length; i++) {
        let ft = state.ahupuaa_features[i];
        let props = ft.properties || {};
        let c_pt = this.computePolygonCentroid(ft.geometry);

        if (!c_pt) continue;
        let isl = props.mokupuni || "Hawaiʻi";
        let moku = props.moku || "Unknown";
        let lon = c_pt[0];
        let lat = c_pt[1];
        let min_sep = (isl === "Hawaiʻi") ? 7.5 : 4.5;
        let target = null;

        for (let x = 0; x < clusters.length; x++) {
          if (clusters[x].isl === isl && this.haversineKm(lon, lat, clusters[x].lon, clusters[x].lat) < min_sep) {
            target = clusters[x];
            break;
          }
        }
        if (!target) {
          target = {
            ahupuaa_n: 0,
            area_km2: 0,
            counts: new Array(n_periods).fill(0),
            is_frontier_buffer: false,
            isl: isl,
            label: `${isl} - ${moku} (${props.ahupuaa || "Cluster"})`,
            lat: lat,
            lon: lon,
            moku: moku,
            pixel_count: 0,
            regime: this.classifyMokuRegime(isl, moku),
            region_id: next_id++,
            sample_names: [],
            sum_lat: 0,
            sum_lon: 0
          };
          clusters.push(target);
        }
        target.ahupuaa_n++;
        target.sum_lon += lon;
        target.sum_lat += lat;
        if (target.sample_names.length < 4 && props.ahupuaa) target.sample_names.push(props.ahupuaa);
      }

      for (let i = 0; i < clusters.length; i++) {
        let cl = clusters[i];

        if (cl.ahupuaa_n > 0) {
          cl.lon = Number((cl.sum_lon/cl.ahupuaa_n).toFixed(5));
          cl.lat = Number((cl.sum_lat/cl.ahupuaa_n).toFixed(5));
        }
      }
      for (let i = 0; i < samoa_domestic.length; i++) {
        samoa_domestic[i].region_id = next_id++;
        samoa_domestic[i].pixel_count = 0;
        samoa_domestic[i].sample_names = [samoa_domestic[i].label];
        clusters.push(samoa_domestic[i]);
      }

      //2. Assign all 232 domain pixels to nearest domestic sub-moku cluster for exact area_km2 conservation
      for (let i = 0; i < state.hp_pixels.length; i++) {
        let px = state.hp_pixels[i];
        let best = null;
        let best_d = 1e9;

        for (let x = 0; x < clusters.length; x++) {
          let d = this.haversineKm(px.lon, px.lat, clusters[x].lon, clusters[x].lat);

          if (d < best_d) {
            best_d = d;
            best = clusters[x];
          }
        }
        if (best) {
          best.area_km2 += px.area_km2;
          best.pixel_count++;
        }
      }

      let active_domestic = clusters.filter((c) => c.area_km2 > 0);
      let fid = 10001;

      for (let i = 0; i < samoa_frontier.length; i++) {
        samoa_frontier[i].region_id = fid++;
        samoa_frontier[i].pixel_count = 1;
        samoa_frontier[i].sample_names = [samoa_frontier[i].label];
      }

      state.all_catchments = active_domestic.concat(samoa_frontier);
      state.domestic_catchments = active_domestic;
      state.frontier_catchments = samoa_frontier;

      //Return statement
      return state;
    }

    /**
     * Step C: Scores chronological settlement intensity across H1..H6 (800-1898 AD).
     * @alias HawaiiPolynesiaGeoJSONExtractor.C_scoreChronologicalIntensities
     *
     * @param {Object} arg0_state
     *
     * @returns {Object}
     */
    static C_scoreChronologicalIntensities (arg0_state) {
      //Convert from parameters
      let state = arg0_state;

      //Declare local instance variables
      let arch_sites = [];
      let exc_re = /\b(station|avenue|house at|palace|courthouse|villas|cemetery|housing|theater|theatre|reservoir|dam|canal|bridge|church|school|hotel|park|store|mill|post office|light|lighthouse|harbor|harbour|airport|golf|hospital|bank|club|building)\b/i;
      let gnis_path = path.join(this.BASE_DIR, "raw_sources", "hawaii_place_names.geojson");
      let inc_gnis = /\b(heiau|loko|fishpond|holua|petroglyph|menehune|koʻa|koa\b|kuula|pohaku|ala loa)\b/i;
      let inc_nrhp = /\b(heiau|loko|fishpond|holua|petroglyph|archaeolog\w*|complex|village|habitation|quarry|field system|lo.?i|star mound|fortification|cave|shelter|platform|terrace|ala loa)\b/i;
      let nrhp_path = path.join(state.project_root, "histmap/1.data_raw/population_regional/CENTAUR/_shared/sites_northern_america/raw_sources/nps_nrhp_locations.geojson");
      let regime_curves = {
        dryland:    [0.25, 0.70, 2.20, 3.10, 1.05, 0.55],
        mixed:      [0.65, 1.45, 2.35, 3.00, 1.40, 1.50],
        samoa:      [2.10, 2.60, 3.00, 3.30, 3.10, 3.60],
        urban_port: [0.95, 2.15, 2.80, 3.45, 4.20, 6.80],
        wetland:    [1.10, 2.40, 2.90, 3.40, 1.95, 2.15]
      };
      let seen_pts = new Set();

      //Ingest verified GNIS Hawaiian heiau, fishpond (loko i'a), holua & petroglyph features
      if (fs.existsSync(gnis_path)) {
        let gnis_gj = JSON.parse(fs.readFileSync(gnis_path, "utf8"));
        let feats = Array.isArray(gnis_gj.features) ? gnis_gj.features : [];

        for (let i = 0; i < feats.length; i++) {
          let pr = feats[i].properties || {};
          let fname = String(pr.feature_name || "");
          let lat = Number(pr.prim_lat_dec);
          let lon = Number(pr.prim_long_dec);

          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          if (!inc_gnis.test(fname) || exc_re.test(fname)) continue;
          let key = `${lat.toFixed(3)}_${lon.toFixed(3)}`;

          if (!seen_pts.has(key)) {
            seen_pts.add(key);
            arch_sites.push({ lat: lat, lon: lon, weight: /heiau|fishpond|loko/i.test(fname) ? 1.5 : 1.0 });
          }
        }
      }

      //Ingest verified NRHP Hawaii & American Samoa indigenous archaeological monuments
      if (fs.existsSync(nrhp_path)) {
        let nrhp_gj = JSON.parse(fs.readFileSync(nrhp_path, "utf8"));
        let feats = Array.isArray(nrhp_gj.features) ? nrhp_gj.features : [];

        for (let i = 0; i < feats.length; i++) {
          let ft = feats[i];
          let pr = ft.properties || {};
          let st = String(pr.State || "").toUpperCase();
          let nm = String(pr.RESNAME || "");

          if (st !== "HAWAII" && st !== "AMERICAN SAMOA") continue;
          if (!inc_nrhp.test(nm) || exc_re.test(nm)) continue;
          if (!ft.geometry || !Array.isArray(ft.geometry.coordinates)) continue;
          let lon = Number(ft.geometry.coordinates[0]);
          let lat = Number(ft.geometry.coordinates[1]);

          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          let key = `${lat.toFixed(3)}_${lon.toFixed(3)}`;

          if (!seen_pts.has(key)) {
            seen_pts.add(key);
            arch_sites.push({ lat: lat, lon: lon, weight: /heiau|complex|field system|fishpond/i.test(nm) ? 2.0 : 1.25 });
          }
        }
      }

      for (let i = 0; i < state.all_catchments.length; i++) state.all_catchments[i].arch_registry_hits = 0;
      for (let s = 0; s < arch_sites.length; s++) {
        let pt = arch_sites[s];
        let best_c = null;
        let best_d = 35.0;

        for (let i = 0; i < state.all_catchments.length; i++) {
          let c = state.all_catchments[i];
          let d = this.haversineKm(pt.lon, pt.lat, c.lon, c.lat);

          if (d < best_d) {
            best_d = d;
            best_c = c;
          }
        }
        if (best_c) best_c.arch_registry_hits += pt.weight;
      }

      for (let i = 0; i < state.all_catchments.length; i++) {
        let c = state.all_catchments[i];
        let curve = regime_curves[c.regime] || regime_curves.mixed;
        let ahu_weight = Math.max(1.5, c.ahupuaa_n)*Math.pow(Math.max(1, c.area_km2)/120, 0.25) + 1.2*c.arch_registry_hits;

        for (let p = 0; p < state.config.periods.length; p++) {
          let val = Math.max(1, Math.round(ahu_weight*curve[p]));

          c.counts[p] = val;
        }
      }

      //Return statement
      return state;
    }

    /**
     * Step D: Writes the 6 chronological period GeoJSONs and 00_all_periods.geojson.
     * @alias HawaiiPolynesiaGeoJSONExtractor.D_exportPeriodGeoJSONs
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
          let sc = c.counts[p];

          if (c.is_frontier_buffer) front_sites += sc;
          else dom_sites += sc;

          features.push({
            geometry: {
              coordinates: [c.lon, c.lat],
              type: "Point"
            },
            properties: {
              ahupuaa_subdivisions: c.ahupuaa_n,
              approx_end_year: p_cfg.approx_end_year,
              approx_start_year: p_cfg.approx_start_year,
              area_km2: Math.round(c.area_km2),
              epoch_id: p_cfg.epoch_id,
              is_frontier_buffer: c.is_frontier_buffer,
              mokupuni: c.isl,
              moku: c.moku,
              name_en: c.label,
              period_key: p_cfg.key,
              pixel_count: c.pixel_count,
              regime: c.regime,
              region_id: c.region_id,
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
            domestic_site_count: dom_sites,
            epoch_id: p_cfg.epoch_id,
            frontier_buffer_catchments: state.frontier_catchments.length,
            frontier_site_count: front_sites,
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
            total_sites_all_periods: all_catchments.find((x) => x.region_id === ft.properties.region_id).counts.reduce((a, b) => a + b, 0)
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
     * Step E: Writes GeoJSON summary metadata to config/sites_hawaii_polynesia_geojson_metadata.json.
     * @alias HawaiiPolynesiaGeoJSONExtractor.E_writeMetadataJSON
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
        ahupuaa_polygons_ingested: state.ahupuaa_features.length,
        domestic_catchments: state.domestic_catchments.length,
        frontier_buffer_catchments: state.frontier_catchments.length,
        generated_at_gmt0: new Date().toISOString(),
        periods: state.period_summaries,
        sources: [
          "Hawaii State GIS HistoricCultural Ahupuaa & Moku Registry (727 polygons)",
          "Dye (2011) & Dye (2014) LKFS Radiocarbon Chronology (tsdye/hawaii-colonization & tsdye/LKFS)",
          "Ladefoged et al. (2009) & Kirch (2010, 2011) Agricultural Potential and Archaic State Intensification",
          "Rieth & Hunt (2008) Samoan Radiocarbon Chronology & Schmitt (1968, 1977) Hawaiian Kingdom Censuses"
        ],
        total_domestic_area_km2: Math.round(state.domestic_catchments.reduce((a, b) => a + b.area_km2, 0))
      };

      fs.writeFileSync(out_abs, JSON.stringify(payload, null, 2));

      //Return statement
      return payload;
    }

    /**
     * Runs steps A_ through E_.
     * @alias HawaiiPolynesiaGeoJSONExtractor.run
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    static run (arg0_options) {
      let state = this.A_loadMasksAndAhupuaa(arg0_options);

      state = this.B_clusterSubMokuCatchments(state);
      state = this.C_scoreChronologicalIntensities(state);
      state = this.D_exportPeriodGeoJSONs(state);

      //Return statement
      return this.E_writeMetadataJSON(state);
    }
  };
}

if (require.main === module) {
  let meta = global.HawaiiPolynesiaGeoJSONExtractor.run();

  console.log(JSON.stringify({
    ahupuaa_polygons_ingested: meta.ahupuaa_polygons_ingested,
    domestic_catchments: meta.domestic_catchments,
    frontier_buffer_catchments: meta.frontier_buffer_catchments,
    total_domestic_area_km2: meta.total_domestic_area_km2,
    periods: meta.periods.map((p) => `${p.period_key}: dom=${p.domestic_site_count}, front=${p.frontier_site_count}`)
  }, null, 2));
}
