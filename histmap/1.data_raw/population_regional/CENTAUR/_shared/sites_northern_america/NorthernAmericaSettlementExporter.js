//Import modules
let fs = require("fs");
let path = require("path");

//Initialise functions
{
  /**
   * Exports documented historical/pre-Columbian settlements and dated Southwest/Plains dendrochronological
   * occupation curves for `CENTAUR-II` per-HU residual kriging (`ViscountHUResidualKriging`).
   *
   * @class NorthernAmericaSettlementExporter
   */
  global.NorthernAmericaSettlementExporter = class {
    /**
     * Ingests pre-1850 settlements from colonial gazetteers and Plains earthlodge dates into kriging catchments
     * while collecting `documented_settlements.json` and `dendro_occupation_series.json`.
     * @alias NorthernAmericaSettlementExporter.ingestColonialPlainsAndCollect
     *
     * @param {Object} arg0_state
     * @param {Object} arg1_callbacks
     *
     * @returns {Object}
     */
    static ingestColonialPlainsAndCollect (arg0_state, arg1_callbacks) {
      //Convert from parameters
      let state = arg0_state;
      let cb = arg1_callbacks;

      //Declare local instance variables
      let centaur_root = path.join(state.project_root, "histmap/1.data_raw/population_regional/CENTAUR");
      let col_dir = path.join(centaur_root, "4.colonial_america_and_canada");
      let dendro_regions = [];
      let n_periods = state.config.periods.length;
      let non_hab_re = /\b(?:Medicine Wheel|Chert Mine|Flint Quarry|Obsidian Quarry|Quarry|Mine|Cemetery|Ossuary|Buffalo Jump|Head-Smashed-In|Rockshelter|Rock Shelter|Cave)\b/i;
      let parseDelimitedLine = cb.parseDelimitedLine;
      let periods = state.config.periods;
      let plains_coords = {
        "Arzberger": [-100.22, 44.32],
        "Bendish": [-100.85, 47.05],
        "Big Village": [-96.42, 42.18],
        "Black Partizan": [-99.43, 44.08],
        "Breeden": [-100.38, 44.38],
        "Cannonball": [-100.62, 46.39],
        "Crow Creek": [-99.37, 43.98],
        "Demery": [-100.47, 45.95],
        "Dodd": [-100.38, 44.41],
        "Fire Heart Creek": [-100.65, 46.15],
        "Holdredge": [-100.21, 40.37],
        "Huff": [-100.64, 46.62],
        "Jiggs Thompson": [-99.78, 44.13],
        "Langdeau": [-99.83, 44.12],
        "Like A Fishhook": [-102.07, 47.62],
        "Little Pawnee Creek": [-96.02, 41.20],
        "Mitchell": [-98.02, 43.73],
        "Molstad": [-100.40, 45.46],
        "Mowry Bluff": [-100.22, 40.38],
        "Over's La Roche": [-100.05, 44.22],
        "Owens": [-100.23, 40.38],
        "Patterson Site": [-96.15, 41.05],
        "Pretty Head": [-99.66, 44.05],
        "Red Willow": [-100.64, 40.25],
        "Shermer": [-100.62, 46.50],
        "Swanson": [-99.35, 43.82],
        "Sweetwater Site": [-98.98, 41.05],
        "Talking Crow": [-99.47, 44.03],
        "Theodore Davis": [-96.05, 41.28],
        "Thomas Riggs": [-100.53, 44.52]
      };
      let plains_p = path.join(cb.raw_na_dir, "plains_house_dates.csv");
      let raw_folders = [
        { dir: path.join(centaur_root, "1.pre_columbian_canada_and_alaska"), max_yr: 1890, inject_krige: false },
        { dir: path.join(centaur_root, "2.united_states_hydrological_units"), max_yr: 1890, inject_krige: false },
        { dir: col_dir, max_yr: 1890, inject_krige: true }
      ];
      let recordSitePeriod = cb.recordSitePeriod;
      let sett_map = new Map();

      let addSettlementSeries = (arg0_name, arg1_lon, arg2_lat, arg3_pairs) => {
        if (!Number.isFinite(arg1_lon) || !Number.isFinite(arg2_lat) || arg2_lat > 79.0 || arg2_lat < 18.0) return;
        if (!Array.isArray(arg3_pairs) || arg3_pairs.length === 0) return;
        let norm_n = String(arg0_name || "site").trim().toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 18);
        let key = `${arg2_lat.toFixed(2)}|${arg1_lon.toFixed(2)}|${norm_n}`;

        if (!sett_map.has(key)) {
          sett_map.set(key, {
            lat: Number(arg2_lat.toFixed(4)),
            lon: Number(arg1_lon.toFixed(4)),
            name: String(arg0_name || "").slice(0, 48),
            pts: new Map()
          });
        }
        let rec = sett_map.get(key);

        for (let i = 0; i < arg3_pairs.length; i++) {
          let yr = Math.round(Number(arg3_pairs[i][0]));
          let val = Number(arg3_pairs[i][1]);

          if (Number.isFinite(yr) && Number.isFinite(val) && val > 0) {
            let prev = rec.pts.get(yr) || 0;

            if (val > prev) rec.pts.set(yr, val);
          }
        }
      };

      //1. Collect all CENTAUR folder 1, 2 & 4 settlement time series (and inject pre-1650 colonial baseline settlements)
      for (let fd = 0; fd < raw_folders.length; fd++) {
        let base_d = raw_folders[fd].dir;

        if (!fs.existsSync(base_d)) continue;
        let subs = fs.readdirSync(base_d);

        for (let s = 0; s < subs.length; s++) {
          let sub_dir = path.join(base_d, subs[s]);

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
                .filter(function (arg0_pair) {
                  return Number.isFinite(arg0_pair[0]) && arg0_pair[0] <= raw_folders[fd].max_yr &&
                    Number.isFinite(arg0_pair[1]) && arg0_pair[1] > 0;
                })
                .sort(function (arg0_a, arg1_b) { return arg0_a[0] - arg1_b[0]; });

              if (obs_pts.length === 0) continue;
              addSettlementSeries(sv.name || keys[k], lon, lat, obs_pts);

              if (raw_folders[fd].inject_krige) {
                for (let p = 0; p < n_periods; p++) {
                  let p_cfg = periods[p];
                  let ps = p_cfg.approx_start_year;
                  let pe = p_cfg.approx_end_year;
                  let p_pop = 0;

                  if (pe > 1650 && p_cfg.key !== "protohistoric_contact_horizon") continue;
                  for (let x = 0; x < obs_pts.length; x++)
                    if (obs_pts[x][0] >= ps - 60 && obs_pts[x][0] <= Math.min(1660, pe + 60) && obs_pts[x][1] > p_pop)
                      p_pop = obs_pts[x][1];
                  if (p_pop <= 0) continue;
                  let wt = Math.min(36.0, 2.5 + 0.35*Math.pow(Math.max(15, p_pop), 0.55));

                  recordSitePeriod(p, lon, lat, sv.name || keys[k], wt, false, "CENTAUR_Colonial", "", p_pop);
                }
              }
            }
          }
        }
      }

      //2. Ingest Plains Earthlodge tree-ring / radiocarbon village series (Middle Missouri & Central Plains)
      if (fs.existsSync(plains_p)) {
        let lines = fs.readFileSync(plains_p, "utf8").split(/\r?\n/);
        let plains_names = Object.keys(plains_coords);

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i]) continue;
          let cols = parseDelimitedLine(lines[i]);
          let site_s = (cols[0] || "").trim();
          let mean_d = Number(cols[3]);

          if (!site_s || !Number.isFinite(mean_d)) continue;
          let coord = null;
          let match_k = "";

          for (let k = 0; k < plains_names.length; k++) {
            if (site_s.includes(plains_names[k])) {
              coord = plains_coords[plains_names[k]];
              match_k = plains_names[k];
              break;
            }
          }
          if (!coord) continue;
          let early_d = Number(cols[5]) || (mean_d - 80);
          let late_d = Number(cols[6]) || (mean_d + 80);

          addSettlementSeries(match_k, coord[0], coord[1], [
            [early_d - 60, 120],
            [mean_d, 450],
            [late_d + 60, 120]
          ]);
          dendro_regions.push({
            label: `Plains_${match_k}`,
            lat: coord[1],
            lon: coord[0],
            radius_km: 42,
            series: [
              [early_d - 100, 0.05],
              [early_d, 0.65],
              [mean_d, 1.00],
              [late_d, 0.55],
              [late_d + 100, 0.05]
            ]
          });
          for (let p = 0; p < n_periods; p++) {
            if (late_d >= periods[p].approx_start_year && early_d < periods[p].approx_end_year)
              recordSitePeriod(p, coord[0], coord[1], match_k, 3.8, false, "Plains_Earthlodges", "", 450);
          }
        }
      }

      //3. Build Southwest Dendrochronological Occupation Curves (VEP II Mesa Verde + SWSN Pueblos)
      let vep_mom_p = path.join(cb.raw_na_dir, "vepiin_momentary_population.csv");
      let vep_sub_p = path.join(cb.raw_na_dir, "reese_2021_occupation_by_household_subregion.csv");

      if (fs.existsSync(vep_mom_p) && fs.existsSync(vep_sub_p)) {
        let mom_lines = fs.readFileSync(vep_mom_p, "utf8").split(/\r?\n/);
        let mom_by_yr = new Map();

        for (let i = 1; i < mom_lines.length; i++) {
          if (!mom_lines[i]) continue;
          let cols = parseDelimitedLine(mom_lines[i]);
          let yr = Number(cols[0]);
          let pop = Number(cols[2]);

          if (Number.isFinite(yr) && Number.isFinite(pop)) mom_by_yr.set(yr, pop);
        }
        let vep_pts = [450, 500, 600, 700, 800, 900, 1000, 1100, 1150, 1200, 1250, 1275, 1300, 1350];
        let cmv_series = [];

        for (let y = 0; y < vep_pts.length; y++) {
          let yr = vep_pts[y];
          let v = mom_by_yr.has(yr) ? mom_by_yr.get(yr) : ((yr < 600) ? 1200 : ((yr <= 1300) ? 1800 : 120));

          cmv_series.push([yr, Number(Math.max(0.02, v/22000).toFixed(4))]);
        }
        let cmv_nodes = [
          { label: "VEP_Dolores", lat: 37.56, lon: -108.55, mult: 0.72 },
          { label: "VEP_MesaVerde_Core", lat: 37.25, lon: -108.49, mult: 1.00 },
          { label: "VEP_McElmo_Hovenweep", lat: 37.36, lon: -109.00, mult: 0.92 }
        ];

        for (let c = 0; c < cmv_nodes.length; c++) {
          let nd = cmv_nodes[c];

          dendro_regions.push({
            label: nd.label,
            lat: nd.lat,
            lon: nd.lon,
            radius_km: 48,
            series: cmv_series.map(function (arg0_s) {
              return [arg0_s[0], Number((arg0_s[1]*nd.mult).toFixed(4))];
            })
          });
        }
        addSettlementSeries("Mesa Verde-Dolores Cluster", -108.49, 37.25, [
          [600, 2900], [900, 7500], [1150, 14500], [1250, 22000], [1300, 350]
        ]);
      }

      //4. Aggregate SWSN dated Pueblo ceramic/tree-ring intervals into 16 macro Southwest basins (500..1650 AD)
      let sw_attr_p = path.join(cb.raw_na_dir, "swsn_critical_scales_attr_all.csv");
      let sw_data_p = path.join(cb.raw_na_dir, "swsn_critical_scales_data_all.csv");

      if (fs.existsSync(sw_attr_p) && fs.existsSync(sw_data_p)) {
        let buckets = new Map();
        let coords = new Map();
        let a_lines = fs.readFileSync(sw_attr_p, "utf8").split(/\r?\n/);
        let sample_yrs = [500, 600, 700, 800, 900, 1000, 1050, 1100, 1150, 1200, 1250, 1275, 1300, 1350, 1400, 1450, 1500, 1550, 1600, 1650];

        for (let i = 1; i < a_lines.length; i++) {
          if (!a_lines[i]) continue;
          let cols = parseDelimitedLine(a_lines[i]);
          let ll = cb.utmToLonLat(Number(cols[2]), Number(cols[3]), 12);

          if (ll) coords.set(cols[0].trim(), { lat: ll[1], lon: ll[0], name: (cols[1] || "").trim() });
        }
        let d_lines = fs.readFileSync(sw_data_p, "utf8").split(/\r?\n/);
        let site_spans = new Map();

        for (let i = 1; i < d_lines.length; i++) {
          if (!d_lines[i]) continue;
          let cols = parseDelimitedLine(d_lines[i]);
          let sid = (cols[1] || "").trim();
          let b = Number(cols[5]);
          let e = Number(cols[6]);

          if (!coords.has(sid) || !Number.isFinite(b) || !Number.isFinite(e)) continue;
          let cur = site_spans.get(sid);

          if (!cur) site_spans.set(sid, [b, e]);
          else {
            if (b < cur[0]) cur[0] = b;
            if (e > cur[1]) cur[1] = e;
          }
        }
        site_spans.forEach(function (arg0_sp, arg1_sid) {
          let meta = coords.get(arg1_sid);

          if (meta.lat < 31.34) return;
          let bk = `${Math.floor(meta.lat/1.5)}_${Math.floor(meta.lon/1.5)}`;

          if (!buckets.has(bk)) buckets.set(bk, { cnt: 0, lat_s: 0, lon_s: 0, yr_cnt: new Float64Array(sample_yrs.length) });
          let b_obj = buckets.get(bk);

          b_obj.cnt++;
          b_obj.lat_s += meta.lat;
          b_obj.lon_s += meta.lon;
          for (let y = 0; y < sample_yrs.length; y++)
            if (sample_yrs[y] >= arg0_sp[0] && sample_yrs[y] <= arg0_sp[1]) b_obj.yr_cnt[y] += 1;
        });

        let max_b = 1;

        buckets.forEach(function (arg0_b) {
          for (let y = 0; y < sample_yrs.length; y++)
            if (arg0_b.yr_cnt[y] > max_b) max_b = arg0_b.yr_cnt[y];
        });
        buckets.forEach(function (arg0_b, arg1_bk) {
          if (arg0_b.cnt < 3) return;
          let ser = [];

          for (let y = 0; y < sample_yrs.length; y++)
            ser.push([sample_yrs[y], Number(Math.sqrt(arg0_b.yr_cnt[y]/max_b).toFixed(4))]);
          dendro_regions.push({
            label: `SWSN_Basin_${arg1_bk}`,
            lat: Number((arg0_b.lat_s/arg0_b.cnt).toFixed(4)),
            lon: Number((arg0_b.lon_s/arg0_b.cnt).toFixed(4)),
            radius_km: 85,
            series: ser
          });
        });
      }

      let settlements_arr = [];

      sett_map.forEach(function (arg0_rec) {
        let ser = Array.from(arg0_rec.pts.entries()).sort(function (arg0_a, arg1_b) { return arg0_a[0] - arg1_b[0]; });

        settlements_arr.push({
          lat: arg0_rec.lat,
          lon: arg0_rec.lon,
          name: arg0_rec.name,
          series: ser
        });
      });

      state.exported_settlements = settlements_arr;
      state.exported_dendro_regions = dendro_regions;

      //Return statement
      return state;
    }

    /**
     * Writes `config/documented_settlements.json` and `config/dendro_occupation_series.json`.
     * @alias NorthernAmericaSettlementExporter.writeOutputs
     *
     * @param {Object} arg0_state
     * @param {string} arg1_settlements_path
     * @param {string} arg2_dendro_path
     */
    static writeOutputs (arg0_state, arg1_settlements_path, arg2_dendro_path) {
      //Convert from parameters
      let state = arg0_state;
      let settlements_path = arg1_settlements_path;
      let dendro_path = arg2_dendro_path;

      //Declare local instance variables
      let dendro_list = Array.isArray(state.exported_dendro_regions) ? state.exported_dendro_regions : [];
      let sett_list = Array.isArray(state.exported_settlements) ? state.exported_settlements : [];

      //Function body
      fs.mkdirSync(path.dirname(settlements_path), { recursive: true });
      fs.writeFileSync(settlements_path, JSON.stringify({
        count: sett_list.length,
        generated_at_gmt0: new Date().toISOString(),
        settlements: sett_list
      }), "utf8");
      fs.writeFileSync(dendro_path, JSON.stringify({
        count: dendro_list.length,
        generated_at_gmt0: new Date().toISOString(),
        regions: dendro_list
      }), "utf8");
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { NorthernAmericaSettlementExporter: global.NorthernAmericaSettlementExporter };
