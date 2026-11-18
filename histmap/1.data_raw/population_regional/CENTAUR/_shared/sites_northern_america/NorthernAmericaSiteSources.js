//Import modules
let fs = require("fs");
let path = require("path");

//Initialise functions
{
  /**
   * Raw Multi-Registry Archaeological & Pre-Columbian Gazetteer Ingest Helpers for Northern America (`CENTAUR-II`).
   * Extracted from `extract_northern_america_sites_geojson.js` to keep each module `< 1,000` lines.
   *
   * @class NorthernAmericaSiteSources
   */
  global.NorthernAmericaSiteSources = class {
    /**
     * Converts uncalibrated 14C years BP into approximate IntCal20 calibrated calendar years CE.
     * @alias NorthernAmericaSiteSources.calibrate14cToCE
     *
     * @param {number} arg0_age_bp
     *
     * @returns {number}
     */
    static calibrate14cToCE (arg0_age_bp) {
      //Convert from parameters
      let age_bp = Number(arg0_age_bp);

      //Declare local instance variables
      let anchor_pts = [
        [0, 0], [500, 520], [1000, 920], [1500, 1380], [2000, 1950],
        [2500, 2600], [3000, 3180], [4000, 4460], [5000, 5730], [6000, 6830],
        [7000, 7840], [8000, 8880], [9000, 10190], [10000, 11450], [11000, 12850],
        [12000, 13900], [14000, 16900]
      ];
      let cal_bp = 0;

      //Guard clauses
      if (!Number.isFinite(age_bp)) return NaN;
      if (age_bp <= 0) return 1950;

      for (let i = 0; i < anchor_pts.length - 1; i++) {
        let p0 = anchor_pts[i];
        let p1 = anchor_pts[i + 1];

        if (age_bp >= p0[0] && age_bp <= p1[0]) {
          cal_bp = p0[1] + (age_bp - p0[0])*(p1[1] - p0[1])/(p1[0] - p0[0]);

          //Return statement
          return 1950 - cal_bp;
        }
      }

      //Return statement
      return 1950 - age_bp*1.2;
    }


    /**
     * Ingests Kelly-Robinson Lower 48, p3k14c 2025, c14_cleaned_dedup, Texas RCD3, SoCalDates, SWSN,
     * VEP II, Greenland Nunniffiit, Milner 2023, Midwest2, Caribbean, POLARIS Chukotka & active CENTAUR gazetteers.
     * Weights gazetteer settlements per period strictly using observations active within that horizon's span.
     * @alias NorthernAmericaSiteSources.ingestAllRegistries
     *
     * @param {Object} arg0_state
     * @param {Object} arg1_callbacks
     *
     * @returns {Object}
     */
    static ingestAllRegistries (arg0_state, arg1_callbacks) {
      //Convert from parameters
      let state = arg0_state;
      let cb = arg1_callbacks;

      //Declare local instance variables
      let assignNearestCatchment = cb.assignNearestCatchment;
      let domestic = state.domestic_catchments;
      let frontier = state.frontier_catchments;
      let getPeriodIndicesForSpan = cb.getPeriodIndicesForSpan;
      let ia_ras_dir = path.join(state.project_root, "histmap/1.data_raw/population_regional/POLARIS/_shared/sites_IA_RAS/geojson");
      let n_periods = state.config.periods.length;
      let non_hab_re = /\b(?:Medicine Wheel|Chert Mine|Flint Quarry|Obsidian Quarry|Quarry|Mine|Cemetery|Ossuary|Buffalo Jump|Head-Smashed-In|Rockshelter|Rock Shelter|Cave)\b/i;
      let parseDelimitedLine = cb.parseDelimitedLine;
      let periods = state.config.periods;
      let raw_c14_dir = path.join(state.project_root, "histmap/1.data_raw/population_c14bazAAR");
      let raw_na_dir = cb.raw_na_dir;
      let recordSitePeriod = cb.recordSitePeriod;
      let source_counts = cb.source_counts;
      let utmToLonLat = cb.utmToLonLat;

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

      //1. Kelly & Robinson Lower 48 Radiocarbon Database
      let kelly_path = path.join(raw_na_dir, "kelly_robinson_lower48_2021.csv");

      if (fs.existsSync(kelly_path)) {
        let lines = fs.readFileSync(kelly_path, "utf8").split(/\r?\n/);
        let hdr = parseDelimitedLine(lines[0]);
        let i_type = hdr.indexOf("Type");
        let i_lab = hdr.indexOf("ID");
        let i_norm = hdr.indexOf("Norm");
        let i_meas = hdr.indexOf("Measured");
        let i_sid = hdr.indexOf("SiteID");
        let i_snm = hdr.indexOf("SiteName");
        let i_lat = hdr.indexOf("Lat");
        let i_lon = hdr.indexOf("Long");
        let i_st = hdr.indexOf("State");
        let i_co = hdr.indexOf("County");

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i]) continue;
          let cols = parseDelimitedLine(lines[i]);

          if ((cols[i_type] || "").trim() === "GEOLOGICAL" || (cols[i_type] || "").trim() === "PALEONTOLOGICAL") continue;
          let age = Number(cols[i_norm]);

          if (!Number.isFinite(age)) age = Number(cols[i_meas]);
          let ce = this.calibrate14cToCE(age);

          if (!Number.isFinite(ce)) continue;
          let lat = Number(cols[i_lat]);
          let lon = Number(cols[i_lon]);

          if ((!Number.isFinite(lat) || !Number.isFinite(lon)) && state.us_county_lookup) {
            let abbr = US_STATE_ABBR[(cols[i_st] || "").trim()] || "";
            let nc = (cols[i_co] || "").toLowerCase().replace(/[^a-z0-9]/g, "");
            let cm = state.us_county_lookup.get(`${abbr}|${nc}`);

            if (cm) {
              lat = cm.lat;
              lon = cm.lon;
            }
          }
          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          let s_id = (cols[i_sid] || cols[i_snm] || cols[i_co] || "").trim();
          let p_idxs = getPeriodIndicesForSpan(ce, ce + 1);

          for (let p = 0; p < p_idxs.length; p++)
            recordSitePeriod(p_idxs[p], lon, lat, s_id, 1.0, false, "KellyRobinson_L48", cols[i_lab]);
        }
      }

      //2. PEOPLE3K 2025 Release (RawP3Kc14_2025.csv) + c14_cleaned_dedup.csv
      let c14_sources = [
        { p: path.join(raw_na_dir, "people3k_RawP3Kc14_2025.csv"), lab: "LabID", age: "Age", lon: "Longitude", lat: "Latitude", site: "SiteName", sid: "SiteID", ctry: "Country", tag: "p3k14c_2025" },
        { p: path.join(raw_c14_dir, "c14_cleaned_dedup.csv"), lab: "labnr", age: "c14age", lon: "lon", lat: "lat", site: "site", sid: "site", ctry: "country", tag: "c14_cleaned_dedup" }
      ];

      for (let s = 0; s < c14_sources.length; s++) {
        let cfg = c14_sources[s];

        if (!fs.existsSync(cfg.p)) continue;
        let lines = fs.readFileSync(cfg.p, "utf8").split(/\r?\n/);
        let hdr = parseDelimitedLine(lines[0]);
        let ilab = hdr.indexOf(cfg.lab);
        let iage = hdr.indexOf(cfg.age);
        let ilon = hdr.indexOf(cfg.lon);
        let ilat = hdr.indexOf(cfg.lat);
        let isite = hdr.indexOf(cfg.site);
        let isid = hdr.indexOf(cfg.sid);
        let ictry = hdr.indexOf(cfg.ctry);

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i]) continue;
          let cols = parseDelimitedLine(lines[i]);
          let lat = Number(cols[ilat]);
          let lon = Number(cols[ilon]);
          let ctry = (cols[ictry] || "").trim();

          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          let is_mex = (lat >= 24.5 && lat <= 32.8 && lon >= -117.5 && lon <= -96.5 && ctry === "Mexico");
          let is_carib = (lat >= 19.6 && lat <= 27.2 && lon >= -85.2 && lon <= -72.0);
          let is_ruk = (lat >= 58.0 && (lon >= 152.0 || lon <= -168.0) && ctry !== "USA" && ctry !== "Canada");
          let grl_west = -74.0;

          if (lat < 68.0) grl_west = -56.0;
          else if (lat < 74.0) grl_west = -56.0 - (lat - 68.0)*3.0;
          else if (lat >= 78.2) grl_west = -74.0 + (lat - 78.2)*3.4;
          let is_na = (
            ctry === "USA" ||
            ctry === "Canada" ||
            (lat >= 59.5 && lon >= grl_west && lon <= -10.0)
          );

          if (!is_na && !is_mex && !is_carib && !is_ruk) continue;
          let ce = this.calibrate14cToCE(Number(cols[iage]));
          let p_idxs = getPeriodIndicesForSpan(ce, ce + 1);
          let snm = (cols[isid] && cols[isid] !== "NA") ? cols[isid] : (cols[isite] || "");

          for (let p = 0; p < p_idxs.length; p++)
            recordSitePeriod(p_idxs[p], lon, lat, snm, 1.0, is_mex || is_carib || is_ruk, cfg.tag, cols[ilab]);
        }
      }

      //3. Texas RCD3 + SoCalDates
      let tx_path = path.join(raw_na_dir, "people3k_FinalRCDTexas3.csv");

      if (fs.existsSync(tx_path)) {
        let lines = fs.readFileSync(tx_path, "utf8").split(/\r?\n/);
        let hdr = parseDelimitedLine(lines[0]);
        let ilon = hdr.indexOf("Longitude");
        let ilat = hdr.indexOf("Latitude");
        let itri = hdr.indexOf("Trinomial");
        let isnm = hdr.indexOf("Site Name");
        let ilab = hdr.indexOf("Assay No.");
        let iage = hdr.indexOf("Age");

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i]) continue;
          let cols = parseDelimitedLine(lines[i]);
          let ce = this.calibrate14cToCE(Number(cols[iage]));
          let p_idxs = getPeriodIndicesForSpan(ce, ce + 1);

          for (let p = 0; p < p_idxs.length; p++)
            recordSitePeriod(p_idxs[p], Number(cols[ilon]), Number(cols[ilat]), cols[itri] || cols[isnm], 1.15, false, "Texas_RCD3", cols[ilab]);
        }
      }

      let sc_path = path.join(raw_na_dir, "people3k_SoCaldates.csv");

      if (fs.existsSync(sc_path)) {
        let lines = fs.readFileSync(sc_path, "utf8").split(/\r?\n/);
        let hdr = parseDelimitedLine(lines[0]);
        let ilon = hdr.indexOf("Longitude");
        let ilat = hdr.indexOf("Latitude");
        let isid = hdr.indexOf("SiteID");
        let ilab = hdr.indexOf("LabID");
        let iage = hdr.indexOf("Age");

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i]) continue;
          let cols = parseDelimitedLine(lines[i]);
          let ce = this.calibrate14cToCE(Number(cols[iage]));
          let p_idxs = getPeriodIndicesForSpan(ce, ce + 1);

          for (let p = 0; p < p_idxs.length; p++)
            recordSitePeriod(p_idxs[p], Number(cols[ilon]), Number(cols[ilat]), cols[isid], 1.15, false, "SoCal_p3k", cols[ilab]);
        }
      }

      //4. Southwest Social Networks (CriticalScales attr_all.csv + data_all.csv spans, UTM Zone 12N)
      let sw_attr_p = path.join(raw_na_dir, "swsn_critical_scales_attr_all.csv");
      let sw_data_p = path.join(raw_na_dir, "swsn_critical_scales_data_all.csv");

      if (fs.existsSync(sw_attr_p) && fs.existsSync(sw_data_p)) {
        let sw_coords = new Map();
        let a_lines = fs.readFileSync(sw_attr_p, "utf8").split(/\r?\n/);

        for (let i = 1; i < a_lines.length; i++) {
          if (!a_lines[i]) continue;
          let cols = parseDelimitedLine(a_lines[i]);
          let ll = utmToLonLat(Number(cols[2]), Number(cols[3]), 12);

          if (ll) sw_coords.set(cols[0].trim(), { lat: ll[1], lon: ll[0], name: cols[1].trim() });
        }

        let sw_spans = new Map();
        let d_lines = fs.readFileSync(sw_data_p, "utf8").split(/\r?\n/);

        for (let i = 1; i < d_lines.length; i++) {
          if (!d_lines[i]) continue;
          let cols = parseDelimitedLine(d_lines[i]);
          let sid = (cols[1] || "").trim();
          let b = Number(cols[5]);
          let e = Number(cols[6]);

          if (!sw_coords.has(sid) || !Number.isFinite(b) || !Number.isFinite(e)) continue;
          let cur = sw_spans.get(sid);

          if (!cur) {
            sw_spans.set(sid, [b, e]);
          } else {
            if (b < cur[0]) cur[0] = b;
            if (e > cur[1]) cur[1] = e;
          }
        }

        sw_spans.forEach((span, sid) => {
          let meta = sw_coords.get(sid);
          let is_mex = (meta.lat < 31.34);
          let p_idxs = getPeriodIndicesForSpan(span[0], span[1]);

          for (let p = 0; p < p_idxs.length; p++)
            recordSitePeriod(p_idxs[p], meta.lon, meta.lat, meta.name || `SWSN_${sid}`, 1.8, is_mex, "SWSN_CriticalScales");
        });
      }

      //5. Village Ecodynamics Project II: 5,466 Central Mesa Verde Habitation Sites (450-1300 AD)
      let vep_p = path.join(raw_na_dir, "reese_2021_occupation_by_household_subregion.csv");

      if (fs.existsSync(vep_p)) {
        let sub_centers = {
          "Dolores": [-108.55, 37.56],
          "Hovenweep": [-109.08, 37.38],
          "McElmo": [-108.92, 37.33],
          "Mesa Verde Landform": [-108.52, 37.28],
          "Mesa Verde National Park": [-108.46, 37.23],
          "Ute Piedmont": [-108.73, 37.16]
        };
        let v_lines = fs.readFileSync(vep_p, "utf8").split(/\r?\n/);
        let v_hdr = parseDelimitedLine(v_lines[0]);
        let i_sno = v_hdr.indexOf("SITE_NO");
        let i_rb = v_hdr.indexOf("ROOMBLOCK_AREA");
        let i_sub = v_hdr.indexOf("subregion");
        let c_x600 = v_hdr.indexOf("X600");
        let c_x900 = v_hdr.indexOf("X900");
        let c_x1150 = v_hdr.indexOf("X1150");
        let c_x1250 = v_hdr.indexOf("X1250");

        for (let i = 1; i < v_lines.length; i++) {
          if (!v_lines[i]) continue;
          let cols = parseDelimitedLine(v_lines[i]);
          let sub = (cols[i_sub] || "").trim();
          let cen = sub_centers[sub] || [-108.65, 37.34];
          let jit_lon = cen[0] + (((i*37) % 100) - 50)*0.0022;
          let jit_lat = cen[1] + (((i*53) % 100) - 50)*0.0018;
          let rb = Math.max(1, Number(cols[i_rb]) || 10);
          let wt = Math.min(4.0, 1.0 + Math.log10(rb)*0.6);
          let active_h = [];

          if (Number(cols[c_x600]) > 0) active_h.push(5);
          if (Number(cols[c_x900]) > 0) active_h.push(6);
          if (Number(cols[c_x1150]) > 0 || Number(cols[c_x1250]) > 0) active_h.push(7);
          for (let p = 0; p < active_h.length; p++)
            recordSitePeriod(active_h[p], jit_lon, jit_lat, cols[i_sno], wt, false, "VEP_MesaVerde");
        }
      }

      //6. Greenland National Museum Nunniffiit (11 Pre-Colonial Cultures + Norse)
      let nun_p = path.join(raw_na_dir, "greenland_nunniffiit_cultures.json");

      if (fs.existsSync(nun_p)) {
        let nun = JSON.parse(fs.readFileSync(nun_p, "utf8"));
        let layer_horizons = {
          "Early Dorset": [3, 4],
          "Early Paleo Eskimo": [1, 2],
          "Eskimo Undefined": [5, 6, 8],
          "Greenlandic Dorset": [4, 5],
          "Independence I": [2, 3],
          "Late Dorset": [5, 6],
          "Late Paleo Eskimo": [4, 5],
          "Norse": [6, 7, 8],
          "Paleo Eskimo": [2, 3, 4],
          "Saqqaq": [2, 3],
          "Thule": [6, 7, 8, 9]
        };
        let layer_keys = Object.keys(layer_horizons);

        for (let l = 0; l < layer_keys.length; l++) {
          let lk = layer_keys[l];
          let feats = Array.isArray(nun[lk]) ? nun[lk] : [];
          let targets = layer_horizons[lk];

          for (let i = 0; i < feats.length; i++) {
            let ft = feats[i];

            if (!ft || !ft.geometry || !Array.isArray(ft.geometry.coordinates)) continue;
            let lon = Number(ft.geometry.coordinates[0]);
            let lat = Number(ft.geometry.coordinates[1]);
            let props = ft.properties || {};
            let nm = props.LOCNAME || `NKAH_${props.NKAH || i}`;

            for (let p = 0; p < targets.length; p++)
              recordSitePeriod(targets[p], lon, lat, nm, 1.4, false, "Greenland_Nunniffiit");
          }
        }
      }

      //7. Midwest & Southeast Cultural Index sites (Milner 2023 + people3k_Midwest2)
      let mil_p = path.join(raw_na_dir, "people3k_Milner2023CultIndex.csv");

      if (fs.existsSync(mil_p) && state.us_county_lookup) {
        let lines = fs.readFileSync(mil_p, "utf8").split(/\r?\n/);

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i]) continue;
          let cols = parseDelimitedLine(lines[i]);
          let site_nm = (cols[0] || "").trim();
          let county = (cols[1] || "").toLowerCase().replace(/[^a-z0-9]/g, "");
          let st_abbr = (cols[2] || "").trim();
          let bp = Number(cols[5]);
          let cm = state.us_county_lookup.get(`${st_abbr}|${county}`);

          if (!cm || !Number.isFinite(bp)) continue;
          let ce = 1950 - bp;
          let p_idxs = getPeriodIndicesForSpan(ce, ce + 1);

          for (let p = 0; p < p_idxs.length; p++)
            recordSitePeriod(p_idxs[p], cm.lon, cm.lat, `${site_nm}_${st_abbr}`, 1.2, false, "Milner2023");
        }
      }

      let mw2_p = path.join(raw_na_dir, "people3k_Midwest2.csv");

      if (fs.existsSync(mw2_p)) {
        let lines = fs.readFileSync(mw2_p, "utf8").split(/\r?\n/);
        let hdr = parseDelimitedLine(lines[0]);
        let ilat = hdr.indexOf("Estimated Latitude");
        let ilon = hdr.indexOf("Estimated Longitude");
        let iloc = hdr.indexOf("Location (paper)");
        let ip1 = hdr.indexOf("PeriodBP");
        let irc = hdr.indexOf("time (RC uncalibrated)");

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i]) continue;
          let cols = parseDelimitedLine(lines[i]);
          let lat = Number(cols[ilat]);
          let lon = Number(cols[ilon]);
          let bp = Number(cols[irc]);

          if (!Number.isFinite(bp)) bp = Number(cols[ip1]);
          if (!Number.isFinite(lat) || !Number.isFinite(lon) || !Number.isFinite(bp)) continue;
          let ce = Number.isFinite(Number(cols[irc])) ? this.calibrate14cToCE(bp) : (1950 - bp);
          let p_idxs = getPeriodIndicesForSpan(ce, ce + 1);

          for (let p = 0; p < p_idxs.length; p++)
            recordSitePeriod(p_idxs[p], lon, lat, cols[iloc] || `MW2_${i}`, 1.1, false, "Midwest2_CultIndex");
        }
      }

      //8. Caribbean (Cuba/Bahamas) & POLARIS Chukotka/Kamchatka frontier
      let car_p = path.join(raw_c14_dir, "raw_databases", "caribbean.csv");

      if (fs.existsSync(car_p)) {
        let lines = fs.readFileSync(car_p, "utf8").split(/\r?\n/);
        let hdr = parseDelimitedLine(lines[0]);
        let ilon = hdr.indexOf("Lon");
        let ilat = hdr.indexOf("Lat");
        let isnm = hdr.indexOf("SiteName");
        let iage = hdr.indexOf("Age");

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i]) continue;
          let cols = parseDelimitedLine(lines[i]);
          let lat = Number(cols[ilat]);
          let lon = Number(cols[ilon]);

          if (lat < 19.6 || lat > 27.2 || lon < -85.2 || lon > -72.0) continue;
          let ce = this.calibrate14cToCE(Number(cols[iage]));
          let p_idxs = getPeriodIndicesForSpan(ce, ce + 1);

          for (let p = 0; p < p_idxs.length; p++)
            recordSitePeriod(p_idxs[p], lon, lat, cols[isnm], 1.0, true, "c14bazAAR_caribbean");
        }
      }

      if (fs.existsSync(ia_ras_dir)) {
        let ia_files = [
          { file: "01_stone_age_e52.geojson", targets: [0, 1] },
          { file: "05_bronze_age_e47.geojson", targets: [2] },
          { file: "06_iron_age_e36.geojson", targets: [3, 4, 5] },
          { file: "09_middle_ages_e37.geojson", targets: [6, 7, 8, 9] }
        ];

        for (let i = 0; i < ia_files.length; i++) {
          let f_abs = path.join(ia_ras_dir, ia_files[i].file);

          if (!fs.existsSync(f_abs)) continue;
          let gj = JSON.parse(fs.readFileSync(f_abs, "utf8"));

          for (let x = 0; x < gj.features.length; x++) {
            let ft = gj.features[x];
            let lon = ft.geometry.coordinates[0];
            let lat = ft.geometry.coordinates[1];

            if (lat < 58 || (lon < 152 && lon > -168)) continue;
            let buf = assignNearestCatchment(lon, lat, true, 300);

            if (buf) {
              let sc = Math.max(1, Number(ft.properties.site_count) || 1);

              for (let y = 0; y < ia_files[i].targets.length; y++)
                buf.counts[ia_files[i].targets[y]] += sc;
              source_counts.POLARIS_Chukotka = (source_counts.POLARIS_Chukotka || 0) + 1;
            }
          }
        }
      }

      //9. Inject verified habitation settlements from CENTAUR folders 1 & 2 weighted per active horizon span (not global peak)
      let pc_dirs = [
        path.join(state.project_root, "histmap/1.data_raw/population_regional/CENTAUR/1.pre_columbian_canada_and_alaska"),
        path.join(state.project_root, "histmap/1.data_raw/population_regional/CENTAUR/2.united_states_hydrological_units")
      ];

      for (let d = 0; d < pc_dirs.length; d++) {
        if (!fs.existsSync(pc_dirs[d])) continue;
        let subs = fs.readdirSync(pc_dirs[d]);

        for (let s = 0; s < subs.length; s++) {
          let sub_dir = path.join(pc_dirs[d], subs[s]);

          if (!fs.statSync(sub_dir).isDirectory()) continue;
          let files = fs.readdirSync(sub_dir).filter(function (arg0_f) { return arg0_f.endsWith("_settlements.json"); });

          for (let f = 0; f < files.length; f++) {
            let s_obj = JSON.parse(fs.readFileSync(path.join(sub_dir, files[f]), "utf8"));
            let keys = Object.keys(s_obj);

            for (let k = 0; k < keys.length; k++) {
              let sv = s_obj[keys[k]];

              if (!sv || !Array.isArray(sv.coords) || !sv.population) continue;
              if (non_hab_re.test(sv.name || keys[k])) continue;
              let lat = Number(sv.coords[0]);
              let lon = Number(sv.coords[1]);
              let obs_pts = Object.keys(sv.population)
                .map(function (arg0_y) { return [Number(arg0_y), Number(sv.population[arg0_y])]; })
                .filter(function (arg0_pair) { return Number.isFinite(arg0_pair[0]) && Number.isFinite(arg0_pair[1]) && arg0_pair[1] > 0; })
                .sort(function (arg0_a, arg1_b) { return arg0_a[0] - arg1_b[0]; });

              if (obs_pts.length === 0) continue;
              let y_min = obs_pts[0][0];
              let y_max = obs_pts[obs_pts.length - 1][0];

              for (let p = 0; p < n_periods; p++) {
                let p_cfg = periods[p];
                let ps = p_cfg.approx_start_year;
                let pe = p_cfg.approx_end_year;

                if (y_max < ps - 100 || y_min > pe + 100) continue;
                let span_pts = obs_pts.filter(function (arg0_pair) {
                  return arg0_pair[0] >= ps - 150 && arg0_pair[0] <= pe + 150;
                });
                let p_pop = 0;

                if (span_pts.length > 0) {
                  for (let x = 0; x < span_pts.length; x++)
                    if (span_pts[x][1] > p_pop) p_pop = span_pts[x][1];
                } else {
                  let mid_y = 0.5*(ps + pe);

                  for (let x = 0; x < obs_pts.length - 1; x++) {
                    if (obs_pts[x][0] <= mid_y && obs_pts[x + 1][0] >= mid_y) {
                      let f_t = (mid_y - obs_pts[x][0])/Math.max(1, obs_pts[x + 1][0] - obs_pts[x][0]);

                      p_pop = obs_pts[x][1]*(1 - f_t) + obs_pts[x + 1][1]*f_t;
                      break;
                    }
                  }
                }
                if (p_pop <= 0) continue;
                let wt = Math.min(6.0, 1.0 + Math.log10(Math.max(10, p_pop)));

                recordSitePeriod(p, lon, lat, sv.name || keys[k], wt, false, "CENTAUR_Gazetteer");
              }
            }
          }
        }
      }

      //10. Condition Northern Mexico frontier smoothly from US border + direct Mexican counts
      for (let i = 0; i < frontier.length; i++) {
        let fb = frontier[i];

        if (!fb.label.startsWith("MEX_BUF")) continue;
        for (let p = 0; p < n_periods; p++) {
          let d_sum = 0;
          let w_sum = 0;

          for (let x = 0; x < domestic.length; x++) {
            let dist_lat = fb.lat - domestic[x].lat;
            let dist_lon = (fb.lon - domestic[x].lon)*Math.cos(fb.lat*Math.PI/180);
            let d_km = 111.2*Math.sqrt(dist_lat*dist_lat + dist_lon*dist_lon);

            if (d_km < 500 && domestic[x].lat >= 25.5 && domestic[x].lat <= 34.5) {
              let wt = 1/Math.pow(Math.max(40, d_km), 2);
              let dens = domestic[x].counts[p]/Math.max(100, domestic[x].area_km2);

              d_sum += wt*dens;
              w_sum += wt;
            }
          }
          if (w_sum > 0) fb.counts[p] = Math.max(fb.counts[p], Math.round((d_sum/w_sum)*fb.area_km2));
        }
      }

      //Return statement
      return state;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { NorthernAmericaSiteSources: global.NorthernAmericaSiteSources };
