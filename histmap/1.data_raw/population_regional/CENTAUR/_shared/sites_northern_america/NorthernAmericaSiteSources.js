//Import modules
let fs = require("fs");
let path = require("path");
let { PNG } = require("pngjs");
let { NorthernAmericaSettlementExporter } = require("./NorthernAmericaSettlementExporter.js");

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
            recordSitePeriod(p_idxs[p], lon, lat, s_id, 0.65, false, "KellyRobinson_L48", cols[i_lab]);
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
            recordSitePeriod(p_idxs[p], lon, lat, snm, 0.65, is_mex || is_carib || is_ruk, cfg.tag, cols[ilab]);
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
          let wt = Math.min(0.65, 0.22 + Math.log10(rb)*0.12);
          let active_h = [];

          if (Number(cols[c_x600]) > 0) active_h.push(5);
          if (Number(cols[c_x900]) > 0) active_h.push(6);
          if (Number(cols[c_x1150]) > 0 || Number(cols[c_x1250]) > 0) active_h.push(7);
          for (let p = 0; p < active_h.length; p++)
            recordSitePeriod(active_h[p], jit_lon, jit_lat, cols[i_sno], wt, false, "VEP_MesaVerde");
        }
      }

      //6. Greenland National Museum Nunniffiit (Chronology & High-Arctic Geography Normalised)
      let nun_p = path.join(raw_na_dir, "greenland_nunniffiit_cultures.json");

      if (fs.existsSync(nun_p)) {
        let nun = JSON.parse(fs.readFileSync(nun_p, "utf8"));
        let layer_keys = Object.keys(nun);

        for (let l = 0; l < layer_keys.length; l++) {
          let lk = layer_keys[l];

          if (lk === "Colonial" || lk === "Eskimo Undefined") continue;
          let feats = Array.isArray(nun[lk]) ? nun[lk] : [];

          for (let i = 0; i < feats.length; i++) {
            let ft = feats[i];

            if (!ft || !ft.geometry || !Array.isArray(ft.geometry.coordinates)) continue;
            let lon = Number(ft.geometry.coordinates[0]);
            let lat = Number(ft.geometry.coordinates[1]);

            if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
            let is_peary_ne = (lat > 78.5 || (lat > 71.5 && lon > -32.0));
            let is_nw_avan = (!is_peary_ne && lat >= 74.5 && lon <= -54.0);
            let is_sw_gl = (lat >= 59.5 && lat <= 66.2 && lon >= -56.0 && lon <= -41.5);
            let is_w_gl = (!is_peary_ne && !is_nw_avan && !is_sw_gl && lon <= -43.0);
            let targets = [];
            let wt = 0.50;

            if (lk === "Early Paleo Eskimo") {
              targets = is_peary_ne ? [2] : [1, 2];
              wt = 0.45;
            } else if (lk === "Independence I") {
              targets = [2];
              wt = 0.45;
            } else if (lk === "Saqqaq") {
              targets = is_peary_ne ? [] : [2, 3];
              wt = 0.55;
            } else if (lk === "Paleo Eskimo") {
              targets = is_peary_ne ? [2] : [2, 3];
              wt = 0.40;
            } else if (lk === "Early Dorset") {
              targets = is_peary_ne ? [] : [3, 4];
              wt = 0.50;
            } else if (lk === "Greenlandic Dorset") {
              targets = is_peary_ne ? [3] : [3, 4];
              wt = 0.45;
            } else if (lk === "Late Paleo Eskimo") {
              targets = is_peary_ne ? [] : [4, 5];
              wt = 0.45;
            } else if (lk === "Late Dorset") {
              targets = (is_nw_avan || is_w_gl) ? [5, 6] : [];
              wt = 0.55;
            } else if (lk === "Norse") {
              if (!is_sw_gl) continue;
              targets = (lat < 62.5) ? [6, 7, 8] : [6, 7];
              wt = 0.65;
            } else if (lk === "Thule") {
              if (is_peary_ne) {
                if (lat > 78.5) continue;
                targets = [8];
                wt = 0.22;
              } else if (is_nw_avan) {
                targets = [7, 8, 9];
                wt = 0.55;
              } else if (is_w_gl && lat >= 68.0) {
                targets = [7, 8, 9];
                wt = 0.55;
              } else {
                targets = [8, 9];
                wt = 0.50;
              }
            }
            if (targets.length === 0) continue;
            let props = ft.properties || {};
            let nm = props.LOCNAME || `NKAH_${props.NKAH || i}`;

            for (let p = 0; p < targets.length; p++)
              recordSitePeriod(targets[p], lon, lat, nm, wt, false, "Greenland_Nunniffiit");
          }
        }
      }

      //6b. NPS NRHP Indigenous Monuments + Plains Earthlodge Village Houses + Kohler/Reese NDT
      this.ingestExtraArchRegistries(state, cb);

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
                let wt = Math.min(48.0, 3.0 + 0.42*Math.pow(Math.max(15, p_pop), 0.55));

                recordSitePeriod(p, lon, lat, sv.name || keys[k], wt, false, "CENTAUR_Gazetteer", "", p_pop);
              }
            }
          }
        }
      }

      //9b. Colonial baseline settlements, Plains earthlodges & Southwest VEP II / SWSN dendro series
      NorthernAmericaSettlementExporter.ingestColonialPlainsAndCollect(state, cb);

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


    /**
     * Ingests verified pre-Columbian Indigenous monuments from NPS NRHP Locations (`nps_nrhp_locations.geojson`)
     * plus Kohler & Reese (2014) Neolithic Demographic Transition regional sites (`kohler_reese2014_ndt.csv`).
     * @alias NorthernAmericaSiteSources.ingestExtraArchRegistries
     *
     * @param {Object} arg0_state
     * @param {Object} arg1_callbacks
     */
    static ingestExtraArchRegistries (arg0_state, arg1_callbacks) {
      //Convert from parameters
      let state = arg0_state;
      let cb = arg1_callbacks;

      //Declare local instance variables
      let arch_re = /\b(archaeolog\w+|archeolog\w+|mound\s*(?:group|site|complex|park|district)?|mounds\b|earthwork\w*|pueblo\b|cliff dwelling\w*|shell\s*(?:ring|mound|midden|heap)|prehistoric|village\s+site|petroglyph\w*|pictograph\w*|effigy|pithouse\w*|kiva|cahokia|etowah|moundville|chaco|mesa\s+verde|pueblo\s+bonito|aztec\s+ruins|spiro|kincaid|poverty\s+point|angel\s+mounds|ocmulgee|kolomoki|serpent\s+mound|newark\s+earthworks|aztalan|toltec\s+mounds|marksville|crystal\s+river|snaketown|casa\s+grande|hovenweep|wupatki|tuzigoot|bandelier)\b/i;
      let exc_re = /\b(street|ave|avenue|blvd|building|courthouse|church|chapel|hotel|bank|school|academy|hospital|library|depot|station|mill|factory|theatre|theater|house\b|mansion|cottage|plantation|post\s+office|bridge|dam|canal|federal|mine|smelter|shipwreck|wreck|lighthouse|cemetery\b(?!.*mound)|memorial\b(?!.*(?:mound|archaeolog|archeolog))|statue|monument\s+to|farmstead|ranch|railroad|commercial|residential|civil\s+war|revolutionary|chinese\s+mining|columbus|arcade|garage|dispatch|museum|homestead|spanish)\b/i;
      let getPeriodIndicesForSpan = cb.getPeriodIndicesForSpan;
      let nrhp_p = path.join(cb.raw_na_dir, "nps_nrhp_locations.geojson");
      let recordSitePeriod = cb.recordSitePeriod;

      //Function body
      if (fs.existsSync(nrhp_p)) {
        let gj = JSON.parse(fs.readFileSync(nrhp_p, "utf8"));
        let feats = Array.isArray(gj.features) ? gj.features : [];

        for (let i = 0; i < feats.length; i++) {
          let ft = feats[i];
          let pr = ft.properties || {};
          let nm = String(pr.RESNAME || "");
          let rt = String(pr.ResType || "").toLowerCase();
          let st = String(pr.State || "").toUpperCase();

          if (st === "HAWAII" || st === "AMERICAN SAMOA" || st === "PUERTO RICO" || st === "VIRGIN ISLANDS" || st === "GUAM") continue;
          if (rt !== "site" && rt !== "district") continue;
          if (!arch_re.test(nm) || exc_re.test(nm)) continue;
          if (!ft.geometry || !Array.isArray(ft.geometry.coordinates)) continue;
          let lon = Number(ft.geometry.coordinates[0]);
          let lat = Number(ft.geometry.coordinates[1]);

          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          let is_pueblo = /\b(pueblo|cliff|chaco|mesa verde|snaketown|casa grande|hovenweep|wupatki|tuzigoot|bandelier)\b/i.test(nm);
          let is_late_archaic = /\b(poverty point|shell\s*(?:mound|ring|midden))\b/i.test(nm);
          let targets = is_late_archaic ? [2, 3] : (is_pueblo ? [6, 7, 8, 9] : [4, 5, 6, 7, 8]);
          let wt = /\b(mound|earthwork|pueblo|village|cahokia|etowah|moundville|spiro|poverty point|chaco)\b/i.test(nm) ? 3.2 : 1.8;

          for (let p = 0; p < targets.length; p++)
            recordSitePeriod(targets[p], lon, lat, nm, wt, false, "NPS_NRHP_Arch");
        }
      }

      let ndt_p = path.join(cb.raw_na_dir, "kohler_reese2014_ndt.csv");

      if (fs.existsSync(ndt_p)) {
        let ndt_centers = {
          HOH: [-111.0, 32.25],
          KAY: [-110.35, 36.68],
          MIM: [-108.05, 32.85],
          NGR: [-106.10, 35.65],
          SAN: [-107.95, 36.05]
        };
        let lines = fs.readFileSync(ndt_p, "utf8").split(/\r?\n/);

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i]) continue;
          let cols = cb.parseDelimitedLine(lines[i]);
          let reg = (cols[1] || "").trim();
          let yr = Number(cols[4]);
          let cen = ndt_centers[reg];

          if (!cen || !Number.isFinite(yr)) continue;
          let p_idxs = getPeriodIndicesForSpan(yr - 150, yr + 150);

          for (let p = 0; p < p_idxs.length; p++)
            recordSitePeriod(p_idxs[p], cen[0], cen[1], cols[3] || cols[0], 1.5, false, "KohlerReese_NDT");
        }
      }
    }


    /**
     * Loads HYDE `popc_1500AD`, `popc_1000AD` and `popc_1900AD` rasters to build a binary 5-arcminute
     * HYDE habitability mask (`density >= 0,002` persons/km²) so synthetic empty catchments are never
     * placed inside uninhabitable desert, alpine or High-Arctic barrens.
     * @alias NorthernAmericaSiteSources.loadHydeHabitabilityMask
     *
     * @param {Object} arg0_state
     *
     * @returns {Uint8Array}
     */
    static loadHydeHabitabilityMask (arg0_state) {
      //Convert from parameters
      let state = arg0_state;

      //Declare local instance variables
      let hyde_dir = path.join(state.project_root, "histmap/2.data_cleaning/landuse_HYDE/rasters");
      let n_px = state.width*state.height;
      let out = new Uint8Array(n_px);
      let r10 = path.join(hyde_dir, "popc_1000AD.png");
      let r15 = path.join(hyde_dir, "popc_1500AD.png");
      let r19 = path.join(hyde_dir, "popc_1900AD.png");
      let rasters = [
        { p: r15, w: 1.0 },
        { p: r10, w: 1.0 },
        { p: r19, w: 0.15 }
      ];

      //Function body
      for (let i = 0; i < rasters.length; i++) {
        if (!fs.existsSync(rasters[i].p)) continue;
        let data = PNG.sync.read(fs.readFileSync(rasters[i].p)).data;
        let dv = new DataView(data.buffer, data.byteOffset, data.byteLength);
        let mult = rasters[i].w;

        for (let px = 0; px < n_px; px++) {
          let la = state.land_area[px];

          if (la <= 0 || out[px] === 1) continue;
          let off = px*4;

          if ((data[off] | data[off + 1] | data[off + 2] | data[off + 3]) === 0) continue;
          let v = dv.getFloat32(off, false)*mult;

          if (Number.isFinite(v) && v/la >= 0.002)
            out[px] = 1;
        }
      }

      //Return statement
      return out;
    }


    /**
     * Prunes purely empty synthetic wasteland catchments lacking both archaeological evidence and HYDE habitation,
     * while preserving genuine agrarian catchments for spatial continuity.
     * @alias NorthernAmericaSiteSources.pruneWastelandCatchments
     *
     * @param {Object} arg0_state
     *
     * @returns {Object}
     */
    static pruneWastelandCatchments (arg0_state) {
      //Convert from parameters
      let state = arg0_state;

      //Declare local instance variables
      let kept_dom = [];
      let kept_front = [];

      //Function body
      for (let i = 0; i < state.all_catchments.length; i++) {
        let c = state.all_catchments[i];
        let tot = 0;

        for (let p = 0; p < c.counts.length; p++) tot += c.counts[p];
        if (c.is_frontier_buffer) {
          kept_front.push(c);
          continue;
        }
        let hab_frac = (c.habitable_area_km2 > 0) ? (c.hyde_hab_area_km2 || 0)/c.habitable_area_km2 : 0;

        if (tot > 0 || hab_frac >= 0.08)
          kept_dom.push(c);
      }

      state.domestic_catchments = kept_dom;
      state.frontier_catchments = kept_front;
      state.all_catchments = kept_dom.concat(kept_front);

      //Return statement
      return state;
    }


    /**
     * Converts UTM NAD83/WGS84 (easting, northing) in given zone to [lon, lat].
     * @alias NorthernAmericaSiteSources.utmToLonLat
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
     * Writes deduplicated 5-arcminute pixel coordinates [col, row] of documented archaeological sites/settlements
     * to `config/documented_site_pixels.json` for pixel-level dasymetric habitability enforcement.
     * @alias NorthernAmericaSiteSources.writeDocumentedSitePixels
     *
     * @param {Object} arg0_state
     * @param {string} arg1_out_path
     */
    static writeDocumentedSitePixels (arg0_state, arg1_out_path) {
      //Convert from parameters
      let state = arg0_state;
      let out_path = arg1_out_path;

      //Declare local instance variables
      let out_dir = path.dirname(out_path);
      let pts = Array.isArray(state.documented_site_pixels) ? state.documented_site_pixels : [];

      //Function body
      if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
      fs.writeFileSync(out_path, JSON.stringify({
        count: pts.length,
        generated_at_gmt0: new Date().toISOString(),
        pixels: pts
      }), "utf8");
      NorthernAmericaSettlementExporter.writeOutputs(
        state,
        path.join(out_dir, "documented_settlements.json"),
        path.join(out_dir, "dendro_occupation_series.json")
      );
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { NorthernAmericaSiteSources: global.NorthernAmericaSiteSources };
