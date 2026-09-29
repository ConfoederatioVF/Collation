/**
 * Out-of-sample accuracy and R^2 evaluation suite for LFPR and Professions rasters.
 * 
 * Compares population-weighted country aggregates from existing predicted rasters against
 * independent empirical ground truth from ILOSTAT and historical Olivetti datasets across
 * all decadal benchmark years (1890-2020).
 * 
 * Evaluates:
 *   - Regime C: Pre-Clamp Raw SuperLearner & OLS Ensembles (Zero Clamping - pure model prediction).
 *   - Post-Clamp: Calibrated Rasters (Global & Historical OECD Core Transfer Holdout).
 * 
 * Usage:
 *   node tests/test_professions_lfpr_out_of_sample.js
 */

let fs = require("fs");
let path = require("path");
let readline = require("readline");

let root_dir = path.resolve(__dirname, "..");
let pngjs = require(path.join(root_dir, "node_modules/pngjs"));

//Define directory paths
let admin_folder = path.join(root_dir, "histmap/1.data_raw/admin_modern");
let lfpr_ilo_folder = path.join(root_dir, "histmap/1.data_raw/LFPR_ILO");
let lfpr_masks_folder = path.join(root_dir, "histmap/1.data_raw/LFPR_Olivetti/masks");
let lfpr_norm_folder = path.join(root_dir, "histmap/2.data_cleaning/LFPR_OLS/2.normalised_rasters");
let lfpr_olivetti_folder = path.join(root_dir, "histmap/1.data_raw/LFPR_Olivetti");
let lfpr_rates_folder = path.join(root_dir, "histmap/2.data_cleaning/LFPR_OLS/3.lfpr_rates");
let output_json_path = path.join(root_dir, "tests/professions_lfpr_oos_metrics.json");
let pop_folder = path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_population_rasters");
let prof_ilo_folder = path.join(root_dir, "histmap/1.data_raw/professions_ILO");
let prof_logit_folder = path.join(root_dir, "histmap/3.data_transform/professions/2.logit_rasters");
let prof_masks_folder = path.join(root_dir, "histmap/1.data_raw/professions_Olivetti/output_rasters");
let prof_olivetti_folder = path.join(root_dir, "histmap/1.data_raw/professions_Olivetti");
let prof_pct_folder = path.join(root_dir, "histmap/3.data_transform/professions/3.percentages");

/**
 * Loads a float32 PNG raster and converts big-endian IEEE 754 words into native Float32 in-place.
 * 
 * @param {string} arg0_file_path
 * 
 * @returns {{ data: Float32Array, height: number, width: number }|null}
 */
let loadFloat32Raster = function (arg0_file_path) {
  //Convert from parameters
  let file_path = arg0_file_path;

  //Guard clauses
  if (!fs.existsSync(file_path)) return null;

  //Declare local instance variables
  let buffer = fs.readFileSync(file_path);
  let parsed_png = pngjs.PNG.sync.read(buffer);

  let byte_offset = parsed_png.data.byteOffset;
  let pixel_count = parsed_png.width * parsed_png.height;
  let raw_buffer = parsed_png.data.buffer;
  let u32_view = new Uint32Array(raw_buffer, byte_offset, pixel_count);

  //In-place big-endian word swap
  for (let i = 0; i < pixel_count; i++) {
    let u = u32_view[i];
    u32_view[i] = ((u >>> 24) & 0xff) | ((u >>> 8) & 0xff00) | ((u << 8) & 0xff0000) | (u << 24);
  }

  //Return statement
  return {
    data: new Float32Array(raw_buffer, byte_offset, pixel_count),
    height: parsed_png.height,
    width: parsed_png.width
  };
};

/**
 * Calculates statistical goodness-of-fit metrics including R^2, weighted R^2, and Pearson correlation.
 * 
 * @param {number[]} arg0_y_true
 * @param {number[]} arg1_y_pred
 * @param {number[]} [arg2_weights]
 * 
 * @returns {{ mae: number, mbe: number, n: number, pearson_r: number, r2: number, r2_weighted: number, rmse: number }}
 */
let calculateMetrics = function (arg0_y_true, arg1_y_pred, arg2_weights) {
  //Convert from parameters
  let weights = (arg2_weights) ? arg2_weights : [];
  let y_pred = arg1_y_pred;
  let y_true = arg0_y_true;

  //Declare local instance variables
  let n = y_true.length;

  //Guard clauses
  if (n < 3)
    return { mae: 0, mbe: 0, n: n, pearson_r: 0, r2: 0, r2_weighted: 0, rmse: 0 };

  let denom_r = 0;
  let mean_pred = 0;
  let mean_true = 0;
  let mean_true_w = 0;
  let pearson_r = 0;
  let r2 = 0;
  let r2_weighted = 0;
  let ss_res = 0;
  let ss_res_w = 0;
  let ss_tot = 0;
  let ss_tot_w = 0;
  let sum_abs_err = 0;
  let sum_diff_x2 = 0;
  let sum_diff_xy = 0;
  let sum_diff_y2 = 0;
  let sum_err = 0;
  let sum_pred = 0;
  let sum_sq_err = 0;
  let sum_true = 0;
  let sum_w = 0;

  for (let i = 0; i < n; i++) {
    sum_pred += y_pred[i];
    sum_true += y_true[i];
    sum_w += (weights[i] || 1.0);
  }

  mean_pred = sum_pred / n;
  mean_true = sum_true / n;
  for (let i = 0; i < n; i++) mean_true_w += y_true[i] * (weights[i] || 1.0) / sum_w;

  for (let i = 0; i < n; i++) {
    let dp = y_pred[i] - mean_pred;
    let dt = y_true[i] - mean_true;
    let err = y_true[i] - y_pred[i];
    let w = weights[i] || 1.0;

    ss_res += err * err;
    ss_res_w += w * err * err;
    ss_tot += (y_true[i] - mean_true) * (y_true[i] - mean_true);
    ss_tot_w += w * (y_true[i] - mean_true_w) * (y_true[i] - mean_true_w);

    sum_abs_err += Math.abs(err);
    sum_diff_x2 += dt * dt;
    sum_diff_xy += dt * dp;
    sum_diff_y2 += dp * dp;
    sum_err += (y_pred[i] - y_true[i]);
    sum_sq_err += err * err;
  }

  denom_r = Math.sqrt(sum_diff_x2 * sum_diff_y2);
  pearson_r = (denom_r > 0) ? (sum_diff_xy / denom_r) : 0;
  r2 = (ss_tot > 0) ? (1.0 - ss_res / ss_tot) : 0;
  r2_weighted = (ss_tot_w > 0) ? (1.0 - ss_res_w / ss_tot_w) : 0;

  //Return statement
  return {
    mae: sum_abs_err / n,
    mbe: sum_err / n,
    n: n,
    pearson_r: pearson_r,
    r2: r2,
    r2_weighted: r2_weighted,
    rmse: Math.sqrt(sum_sq_err / n)
  };
};

global.ProfessionsLFPROutOfSample = class {
  /**
   * Loads geocodes mappings between RGB colours and ISO3 strings.
   * 
   * @returns {{ iso3_to_name: Object, rgb_to_iso3: Object }}
   */
  static loadGeocodes () {
    //Declare local instance variables
    let geocodes_path = path.join(admin_folder, "geocodes.csv");
    let iso3_to_name = {};
    let lines = fs.readFileSync(geocodes_path, "utf8").split("\n");
    let rgb_to_iso3 = {};

    for (let i = 1; i < lines.length; i++) {
      let parts = lines[i].split(";");
      if (parts.length >= 5) {
        let iso3 = parts[0].trim();
        let name = parts[1].trim();
        let rgb = parts[4].trim();

        if (iso3) iso3_to_name[iso3] = name;
        if (rgb) rgb_to_iso3[rgb] = iso3;
      }
    }

    //Return statement
    return { iso3_to_name, rgb_to_iso3 };
  }

  /**
   * Loads ILO country name to ISO3 dictionary.
   * 
   * @returns {Object}
   */
  static loadILONameMapping () {
    //Declare local instance variables
    let ilo_path = path.join(admin_folder, "iso3_ilo_geocodes.csv");
    let lines = fs.readFileSync(ilo_path, "utf8").split("\n");
    let name_to_iso3 = {};

    for (let i = 1; i < lines.length; i++) {
      let line = lines[i];
      if (!line) continue;
      let parts = line.split('","');
      if (parts.length >= 3) {
        let iso3 = parts[1].replace(/"/g, "").trim();
        let name = parts[2].replace(/"/g, "").trim();
        name_to_iso3[name] = iso3;
      }
    }

    //Return statement
    return name_to_iso3;
  }

  /**
   * Harmonises and loads decadal LFPR empirical ground truth (1890-2020) across Olivetti and ILOSTAT.
   * 
   * @param {number[]} arg0_years
   * @param {Object} arg1_name_to_iso3
   * 
   * @returns {Promise<Object>}
   */
  static async loadDecadalEmpiricalLFPR (arg0_years, arg1_name_to_iso3) {
    //Convert from parameters
    let name_to_iso3 = arg1_name_to_iso3;
    let years = arg0_years;

    //Declare local instance variables
    let lfpr_data = {};
    let lfpr_olivetti_path = path.join(lfpr_olivetti_folder, "lfpr_sex_olivetti.csv");
    let national_path = path.join(lfpr_ilo_folder, "national_lfpr.csv");
    let sex_path = path.join(lfpr_ilo_folder, "lfpr_age_sex.csv");
    let target_years_set = new Set(years.map(String));

    for (let y of years) lfpr_data[y] = {};

    //1. Read historical Olivetti LFPR (1890-2000)
    if (fs.existsSync(lfpr_olivetti_path)) {
      let lines = fs.readFileSync(lfpr_olivetti_path, "utf8").split("\n");
      let hdr = lines[0].split(",");
      for (let i = 1; i < lines.length; i++) {
        let p = lines[i].split(",");
        let iso3 = p[0];
        let gender = p[2];
        if (!iso3 || !gender) continue;
        let s_key = (gender === "Male") ? "m" : (gender === "Female") ? "f" : null;
        if (!s_key) continue;

        for (let c = 4; c < hdr.length; c++) {
          let y = parseInt(hdr[c]);
          let val = parseFloat(p[c]);
          if (target_years_set.has(y.toString()) && !isNaN(val) && val > 0) {
            if (!lfpr_data[y][iso3]) lfpr_data[y][iso3] = {};
            lfpr_data[y][iso3][s_key] = val; //Olivetti values are already in [0, 1]
          }
        }
      }
    }

    //2. Read modern ILO national_lfpr.csv (1990-2020)
    if (fs.existsSync(national_path)) {
      let nat_lines = fs.readFileSync(national_path, "utf8").split("\n");
      let header = nat_lines[4].split('","').map(s => s.replace(/"/g, ""));

      for (let y of years) {
        let y_idx = header.indexOf(y.toString());
        if (y_idx === -1) continue;

        for (let i = 5; i < nat_lines.length; i++) {
          let line = nat_lines[i];
          if (!line) continue;
          let parts = line.split('","');
          if (parts.length > y_idx) {
            let iso3 = parts[1].replace(/"/g, "").trim();
            let val_str = parts[y_idx].replace(/"/g, "").trim();
            if (val_str && !isNaN(val_str)) {
              if (!lfpr_data[y][iso3]) lfpr_data[y][iso3] = {};
              lfpr_data[y][iso3].t = parseFloat(val_str) / 100.0;
            }
          }
        }
      }
    }

    //3. Read modern ILO lfpr_age_sex.csv (1990-2020)
    if (fs.existsSync(sex_path)) {
      let stream = fs.createReadStream(sex_path);
      let rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

      for await (let line of rl) {
        if (!line.includes('"Age (Youth, adults): 15+"')) continue;
        if (!line.includes('"Education (Aggregate levels): Total"')) continue;

        let m = line.match(/^"([^"]+)","([^"]+)","([^"]+)","([^"]+)","([^"]+)","([^"]+)","(\d{4})",([0-9.]+)/);
        if (m) {
          let country = m[1];
          let obs = parseFloat(m[8]);
          let sex = m[4];
          let year_str = m[7];

          if (target_years_set.has(year_str) && !isNaN(obs) && obs > 0) {
            let iso3 = name_to_iso3[country];
            let y = parseInt(year_str);
            if (iso3 && lfpr_data[y]) {
              if (!lfpr_data[y][iso3]) lfpr_data[y][iso3] = {};
              let s_key = (sex === "Male") ? "m" : (sex === "Female") ? "f" : "t";
              if (lfpr_data[y][iso3][s_key] === undefined) {
                lfpr_data[y][iso3][s_key] = obs / 100.0;
              }
            }
          }
        }
      }
    }

    //Synthesise total if m and f are present but t is unassigned
    for (let y of years) {
      for (let iso3 in lfpr_data[y]) {
        let ent = lfpr_data[y][iso3];
        if (ent.t === undefined && ent.m !== undefined && ent.f !== undefined) {
          ent.t = (ent.m + ent.f) / 2.0;
        }
      }
    }

    //Return statement
    return lfpr_data;
  }

  /**
   * Harmonises and loads decadal Professions empirical ground truth (1890-2020) across Olivetti and ILOSTAT.
   * 
   * @param {number[]} arg0_years
   * @param {Object} arg1_name_to_iso3
   * 
   * @returns {Promise<Object>}
   */
  static async loadDecadalEmpiricalProfessions (arg0_years, arg1_name_to_iso3) {
    //Convert from parameters
    let name_to_iso3 = arg1_name_to_iso3;
    let years = arg0_years;

    //Declare local instance variables
    let prof_data = {};
    let prof_ilo_path = path.join(prof_ilo_folder, "age_sex_professions.csv");
    let prof_olivetti_path = path.join(prof_olivetti_folder, "professions_sex_olivetti.csv");
    let target_years_set = new Set(years.map(String));

    for (let y of years) prof_data[y] = {};

    //1. Read historical Olivetti professions (1890-2000)
    if (fs.existsSync(prof_olivetti_path)) {
      let lines = fs.readFileSync(prof_olivetti_path, "utf8").split("\n");
      let hdr = lines[0].split(",");
      for (let i = 1; i < lines.length; i++) {
        let p = lines[i].split(",");
        let iso3 = p[0];
        let gender = p[2];
        let sector = p[3];
        if (!iso3 || !gender || !sector) continue;

        let s_key = (gender === "Male") ? "m" : (gender === "Female") ? "f" : null;
        let sec_key = (sector === "Agriculture") ? "agriculture" : (sector === "Manufacturing") ? "manufacturing" : (sector === "Services") ? "services" : null;
        if (!s_key || !sec_key) continue;

        for (let c = 5; c < hdr.length; c++) {
          let y = parseInt(hdr[c]);
          let val = parseFloat(p[c]);
          if (target_years_set.has(y.toString()) && !isNaN(val) && val >= 0) {
            if (!prof_data[y][iso3]) prof_data[y][iso3] = { f: {}, m: {}, t: {} };
            prof_data[y][iso3][s_key][sec_key] = val;
          }
        }
      }
    }

    //2. Read modern ILO age_sex_professions.csv (1990-2020)
    if (fs.existsSync(prof_ilo_path)) {
      let stream = fs.createReadStream(prof_ilo_path);
      let rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

      let raw_ilo = {};
      for (let y of years) raw_ilo[y] = {};

      for await (let line of rl) {
        if (!line.includes('"Area type: National"')) continue;
        if (!line.includes('"Economic activity (Broad sector):')) continue;

        let m = line.match(/^"([^"]+)","([^"]+)","([^"]+)","([^"]+)","([^"]+)","([^"]+)","(\d{4})",([0-9.]+)/);
        if (m) {
          let country = m[1];
          let obs = parseFloat(m[8]);
          let sector = m[5];
          let sex = m[4];
          let year_str = m[7];

          if (target_years_set.has(year_str) && !isNaN(obs) && obs >= 0) {
            let iso3 = name_to_iso3[country];
            let y = parseInt(year_str);
            if (iso3 && raw_ilo[y]) {
              if (!raw_ilo[y][iso3]) raw_ilo[y][iso3] = { f: {}, m: {}, t: {} };
              let s_key = (sex === "Male") ? "m" : (sex === "Female") ? "f" : "t";

              if (sector === "Economic activity (Broad sector): Agriculture") raw_ilo[y][iso3][s_key].agr = obs;
              else if (sector === "Economic activity (Broad sector): Industry") raw_ilo[y][iso3][s_key].man = obs;
              else if (sector === "Economic activity (Broad sector): Services") raw_ilo[y][iso3][s_key].ser = obs;
            }
          }
        }
      }

      //Derive valid empirical sectoral shares
      for (let y of years) {
        for (let iso3 in raw_ilo[y]) {
          for (let s of ["t", "m", "f"]) {
            let ent = raw_ilo[y][iso3][s];
            if (ent && ent.agr !== undefined && ent.man !== undefined && ent.ser !== undefined && ent.agr > 0 && ent.man > 0 && ent.ser > 0) {
              let sum = ent.agr + ent.man + ent.ser;
              if (sum > 0) {
                if (!prof_data[y][iso3]) prof_data[y][iso3] = { f: {}, m: {}, t: {} };
                prof_data[y][iso3][s] = {
                  agriculture: ent.agr / sum,
                  manufacturing: ent.man / sum,
                  services: ent.ser / sum
                };
              }
            }
          }
        }
      }
    }

    //Derive total active shares for Olivetti where m and f exist
    for (let y of years) {
      for (let iso3 in prof_data[y]) {
        let ent = prof_data[y][iso3];
        if (!ent.t) ent.t = {};
        for (let sec of ["agriculture", "manufacturing", "services"]) {
          if (ent.t[sec] === undefined && ent.m && ent.m[sec] !== undefined && ent.f && ent.f[sec] !== undefined) {
            ent.t[sec] = (ent.m[sec] + ent.f[sec]) / 2.0;
          }
        }
      }
    }

    //Return statement
    return prof_data;
  }

  /**
   * Main assessment execution method evaluating LFPR and Professions across decadal years (1890-2020).
   */
  static async runAssessment () {
    console.log("================================================================================");
    console.log("OUT-OF-SAMPLE ACCURACY & R^2 EVALUATION SUITE: DECADAL 1890-2020");
    console.log("REGIME C (PRE-CLAMP ML/OLS ENSEMBLE) VS POST-CLAMP CALIBRATION");
    console.log("================================================================================\n");

    let t0 = Date.now();
    let benchmark_years = [1890, 1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020];
    let { iso3_to_name, rgb_to_iso3 } = this.loadGeocodes();
    let name_to_iso3 = this.loadILONameMapping();

    let core_oecd_set = new Set([
      "AUS", "AUT", "BEL", "CAN", "CHE", "DEU", "DNK", "ESP", "FIN", "FRA",
      "GBR", "IRL", "ITA", "KOR", "NLD", "NOR", "PRT", "SWE", "USA"
    ]);

    let geo_png = pngjs.PNG.sync.read(fs.readFileSync(path.join(admin_folder, "geocodes.png")));
    let total_pixels = geo_png.width * geo_png.height;

    console.log("Ingesting empirical ground-truth benchmarks across 14 decadal periods...");
    let empirical_lfpr = await this.loadDecadalEmpiricalLFPR(benchmark_years, name_to_iso3);
    let empirical_prof = await this.loadDecadalEmpiricalProfessions(benchmark_years, name_to_iso3);
    console.log(`Ingested decadal empirical benchmarks in ${((Date.now() - t0) / 1000).toFixed(2)}s.\n`);

    let all_evaluation_results = {};
    let longitudinal_summary = [];

    for (let y = 0; y < benchmark_years.length; y++) {
      let year = benchmark_years[y];
      let t_year_start = Date.now();

      let pop_path = path.join(pop_folder, `stadester_population_${year}.png`);
      let pop_raster = loadFloat32Raster(pop_path);
      if (!pop_raster) {
        console.warn(`[WARN] Missing population raster for year ${year}. Skipping.`);
        continue;
      }

      //1. Load LFPR Pre-Clamp (Regime C) and Post-Clamp rasters
      let lfpr_pre_m = loadFloat32Raster(path.join(lfpr_norm_folder, `normalised_lfpr_m_${year}.png`));
      let lfpr_pre_f = loadFloat32Raster(path.join(lfpr_norm_folder, `normalised_lfpr_f_${year}.png`));
      let lfpr_post_m = loadFloat32Raster(path.join(lfpr_rates_folder, `lfpr_m_${year}.png`));
      let lfpr_post_f = loadFloat32Raster(path.join(lfpr_rates_folder, `lfpr_f_${year}.png`));

      //2. Load Professions Pre-Clamp (Regime C: 2.logit_rasters)
      let prof_pre_agr_m = loadFloat32Raster(path.join(prof_logit_folder, `logit_m_${year}_class_agriculture.png`));
      let prof_pre_man_m = loadFloat32Raster(path.join(prof_logit_folder, `logit_m_${year}_class_manufacturing.png`));
      let prof_pre_ser_m = loadFloat32Raster(path.join(prof_logit_folder, `logit_m_${year}_class_services.png`));

      let prof_pre_agr_f = loadFloat32Raster(path.join(prof_logit_folder, `logit_f_${year}_class_agriculture.png`));
      let prof_pre_man_f = loadFloat32Raster(path.join(prof_logit_folder, `logit_f_${year}_class_manufacturing.png`));
      let prof_pre_ser_f = loadFloat32Raster(path.join(prof_logit_folder, `logit_f_${year}_class_services.png`));

      //3. Load Professions Post-Clamp (3.percentages)
      let prof_post_agr_t = loadFloat32Raster(path.join(prof_pct_folder, `agriculture_t_${year}.png`));
      let prof_post_agr_m = loadFloat32Raster(path.join(prof_pct_folder, `agriculture_m_${year}.png`));
      let prof_post_agr_f = loadFloat32Raster(path.join(prof_pct_folder, `agriculture_f_${year}.png`));

      let prof_post_man_t = loadFloat32Raster(path.join(prof_pct_folder, `manufacturing_t_${year}.png`));
      let prof_post_man_m = loadFloat32Raster(path.join(prof_pct_folder, `manufacturing_m_${year}.png`));
      let prof_post_man_f = loadFloat32Raster(path.join(prof_pct_folder, `manufacturing_f_${year}.png`));

      let prof_post_ser_t = loadFloat32Raster(path.join(prof_pct_folder, `services_t_${year}.png`));
      let prof_post_ser_m = loadFloat32Raster(path.join(prof_pct_folder, `services_m_${year}.png`));
      let prof_post_ser_f = loadFloat32Raster(path.join(prof_pct_folder, `services_f_${year}.png`));

      let prof_post_niw_t = loadFloat32Raster(path.join(prof_pct_folder, `not_in_work_t_${year}.png`));

      //4. Fast parallel pixel aggregation across 9.3M pixels
      let country_aggregates = {};

      for (let i = 0; i < total_pixels; i++) {
        let pop = pop_raster.data[i];
        if (pop <= 0 || isNaN(pop)) continue;

        let b_idx = i * 4;
        let b = geo_png.data[b_idx + 2];
        let g = geo_png.data[b_idx + 1];
        let r = geo_png.data[b_idx];
        let iso3 = rgb_to_iso3[`${r},${g},${b}`];
        if (!iso3) continue;

        if (!country_aggregates[iso3]) {
          country_aggregates[iso3] = {
            pop: 0,
            //LFPR pre
            sum_lfpr_pre_f: 0, sum_lfpr_pre_m: 0,
            //LFPR post
            sum_lfpr_post_f: 0, sum_lfpr_post_m: 0,
            //Professions pre (active logits)
            sum_prof_pre_agr_f: 0, sum_prof_pre_agr_m: 0,
            sum_prof_pre_man_f: 0, sum_prof_pre_man_m: 0,
            sum_prof_pre_ser_f: 0, sum_prof_pre_ser_m: 0,
            //Professions post
            sum_prof_post_agr_f: 0, sum_prof_post_agr_m: 0, sum_prof_post_agr_t: 0,
            sum_prof_post_man_f: 0, sum_prof_post_man_m: 0, sum_prof_post_man_t: 0,
            sum_prof_post_niw_t: 0,
            sum_prof_post_ser_f: 0, sum_prof_post_ser_m: 0, sum_prof_post_ser_t: 0
          };
        }

        let c = country_aggregates[iso3];
        c.pop += pop;

        //Accumulate LFPR
        if (lfpr_pre_m && !isNaN(lfpr_pre_m.data[i])) c.sum_lfpr_pre_m += lfpr_pre_m.data[i] * pop;
        if (lfpr_pre_f && !isNaN(lfpr_pre_f.data[i])) c.sum_lfpr_pre_f += lfpr_pre_f.data[i] * pop;
        if (lfpr_post_m && !isNaN(lfpr_post_m.data[i])) c.sum_lfpr_post_m += lfpr_post_m.data[i] * pop;
        if (lfpr_post_f && !isNaN(lfpr_post_f.data[i])) c.sum_lfpr_post_f += lfpr_post_f.data[i] * pop;

        //Accumulate Professions Pre
        if (prof_pre_agr_m && !isNaN(prof_pre_agr_m.data[i])) c.sum_prof_pre_agr_m += prof_pre_agr_m.data[i] * pop;
        if (prof_pre_man_m && !isNaN(prof_pre_man_m.data[i])) c.sum_prof_pre_man_m += prof_pre_man_m.data[i] * pop;
        if (prof_pre_ser_m && !isNaN(prof_pre_ser_m.data[i])) c.sum_prof_pre_ser_m += prof_pre_ser_m.data[i] * pop;

        if (prof_pre_agr_f && !isNaN(prof_pre_agr_f.data[i])) c.sum_prof_pre_agr_f += prof_pre_agr_f.data[i] * pop;
        if (prof_pre_man_f && !isNaN(prof_pre_man_f.data[i])) c.sum_prof_pre_man_f += prof_pre_man_f.data[i] * pop;
        if (prof_pre_ser_f && !isNaN(prof_pre_ser_f.data[i])) c.sum_prof_pre_ser_f += prof_pre_ser_f.data[i] * pop;

        //Accumulate Professions Post
        if (prof_post_agr_t && !isNaN(prof_post_agr_t.data[i])) c.sum_prof_post_agr_t += prof_post_agr_t.data[i] * pop;
        if (prof_post_agr_m && !isNaN(prof_post_agr_m.data[i])) c.sum_prof_post_agr_m += prof_post_agr_m.data[i] * pop;
        if (prof_post_agr_f && !isNaN(prof_post_agr_f.data[i])) c.sum_prof_post_agr_f += prof_post_agr_f.data[i] * pop;

        if (prof_post_man_t && !isNaN(prof_post_man_t.data[i])) c.sum_prof_post_man_t += prof_post_man_t.data[i] * pop;
        if (prof_post_man_m && !isNaN(prof_post_man_m.data[i])) c.sum_prof_post_man_m += prof_post_man_m.data[i] * pop;
        if (prof_post_man_f && !isNaN(prof_post_man_f.data[i])) c.sum_prof_post_man_f += prof_post_man_f.data[i] * pop;

        if (prof_post_ser_t && !isNaN(prof_post_ser_t.data[i])) c.sum_prof_post_ser_t += prof_post_ser_t.data[i] * pop;
        if (prof_post_ser_m && !isNaN(prof_post_ser_m.data[i])) c.sum_prof_post_ser_m += prof_post_ser_m.data[i] * pop;
        if (prof_post_ser_f && !isNaN(prof_post_ser_f.data[i])) c.sum_prof_post_ser_f += prof_post_ser_f.data[i] * pop;

        if (prof_post_niw_t && !isNaN(prof_post_niw_t.data[i])) c.sum_prof_post_niw_t += prof_post_niw_t.data[i] * pop;
      }

      //Derive country rates for both Pre (Regime C) and Post
      let country_rates = {};
      for (let iso3 in country_aggregates) {
        let c = country_aggregates[iso3];
        if (c.pop > 0) {
          //Pre (Regime C) active sums
          let pre_act_m = c.sum_prof_pre_agr_m + c.sum_prof_pre_man_m + c.sum_prof_pre_ser_m;
          let pre_act_f = c.sum_prof_pre_agr_f + c.sum_prof_pre_man_f + c.sum_prof_pre_ser_f;

          let pre_agr_m = (pre_act_m > 0) ? (c.sum_prof_pre_agr_m / pre_act_m) : 0;
          let pre_man_m = (pre_act_m > 0) ? (c.sum_prof_pre_man_m / pre_act_m) : 0;
          let pre_ser_m = (pre_act_m > 0) ? (c.sum_prof_pre_ser_m / pre_act_m) : 0;

          let pre_agr_f = (pre_act_f > 0) ? (c.sum_prof_pre_agr_f / pre_act_f) : 0;
          let pre_man_f = (pre_act_f > 0) ? (c.sum_prof_pre_man_f / pre_act_f) : 0;
          let pre_ser_f = (pre_act_f > 0) ? (c.sum_prof_pre_ser_f / pre_act_f) : 0;

          //Post active sums
          let post_act_m = c.sum_prof_post_agr_m + c.sum_prof_post_man_m + c.sum_prof_post_ser_m;
          let post_act_f = c.sum_prof_post_agr_f + c.sum_prof_post_man_f + c.sum_prof_post_ser_f;
          let post_act_t = c.sum_prof_post_agr_t + c.sum_prof_post_man_t + c.sum_prof_post_ser_t;

          country_rates[iso3] = {
            pop: c.pop,
            //Pre-Clamp (Regime C)
            pre: {
              agriculture_f: pre_agr_f,
              agriculture_m: pre_agr_m,
              agriculture_t: (pre_agr_m + pre_agr_f) / 2.0,
              lfpr_f: c.sum_lfpr_pre_f / c.pop,
              lfpr_m: c.sum_lfpr_pre_m / c.pop,
              lfpr_t: (c.sum_lfpr_pre_m + c.sum_lfpr_pre_f) / (2 * c.pop),
              manufacturing_f: pre_man_f,
              manufacturing_m: pre_man_m,
              manufacturing_t: (pre_man_m + pre_man_f) / 2.0,
              not_in_work_t: 1.0 - (c.sum_lfpr_pre_m + c.sum_lfpr_pre_f) / (2 * c.pop),
              services_f: pre_ser_f,
              services_m: pre_ser_m,
              services_t: (pre_ser_m + pre_ser_f) / 2.0
            },
            //Post-Clamp
            post: {
              agriculture_f: (post_act_f > 0) ? (c.sum_prof_post_agr_f / post_act_f) : 0,
              agriculture_m: (post_act_m > 0) ? (c.sum_prof_post_agr_m / post_act_m) : 0,
              agriculture_t: (post_act_t > 0) ? (c.sum_prof_post_agr_t / post_act_t) : 0,
              lfpr_f: c.sum_lfpr_post_f / c.pop,
              lfpr_m: c.sum_lfpr_post_m / c.pop,
              lfpr_t: (c.sum_lfpr_post_m + c.sum_lfpr_post_f) / (2 * c.pop),
              manufacturing_f: (post_act_f > 0) ? (c.sum_prof_post_man_f / post_act_f) : 0,
              manufacturing_m: (post_act_m > 0) ? (c.sum_prof_post_man_m / post_act_m) : 0,
              manufacturing_t: (post_act_t > 0) ? (c.sum_prof_post_man_t / post_act_t) : 0,
              not_in_work_t: c.sum_prof_post_niw_t / c.pop,
              services_f: (post_act_f > 0) ? (c.sum_prof_post_ser_f / post_act_f) : 0,
              services_m: (post_act_m > 0) ? (c.sum_prof_post_ser_m / post_act_m) : 0,
              services_t: (post_act_t > 0) ? (c.sum_prof_post_ser_t / post_act_t) : 0
            }
          };
        }
      }

      //5. Compute Metrics for both Regime C and Post-Clamp
      let indicators_list = [
        { domain: "lfpr", key: "lfpr_t", sex: "t" },
        { domain: "lfpr", key: "lfpr_m", sex: "m" },
        { domain: "lfpr", key: "lfpr_f", sex: "f" },
        { domain: "prof", key: "agriculture_t", sector: "agriculture", sex: "t" },
        { domain: "prof", key: "agriculture_m", sector: "agriculture", sex: "m" },
        { domain: "prof", key: "agriculture_f", sector: "agriculture", sex: "f" },
        { domain: "prof", key: "manufacturing_t", sector: "manufacturing", sex: "t" },
        { domain: "prof", key: "manufacturing_m", sector: "manufacturing", sex: "m" },
        { domain: "prof", key: "manufacturing_f", sector: "manufacturing", sex: "f" },
        { domain: "prof", key: "services_t", sector: "services", sex: "t" },
        { domain: "prof", key: "services_m", sector: "services", sex: "m" },
        { domain: "prof", key: "services_f", sector: "services", sex: "f" },
        { domain: "niw", key: "not_in_work_t", sex: "t" }
      ];

      let display_rows = [];
      let year_results = {};

      for (let ind of indicators_list) {
        let yt = [], yp_post = [], yp_pre = [], w = [];
        let yt_oos = [], yp_post_oos = [], yp_pre_oos = [], w_oos = [];

        for (let iso3 in country_rates) {
          let pred_post = country_rates[iso3].post[ind.key];
          let pred_pre = country_rates[iso3].pre[ind.key];
          let true_val = null;

          if (ind.domain === "lfpr") {
            if (empirical_lfpr[year] && empirical_lfpr[year][iso3]) {
              true_val = empirical_lfpr[year][iso3][ind.sex];
            }
          } else if (ind.domain === "prof") {
            if (empirical_prof[year] && empirical_prof[year][iso3] && empirical_prof[year][iso3][ind.sex]) {
              true_val = empirical_prof[year][iso3][ind.sex][ind.sector];
            }
          } else if (ind.domain === "niw") {
            if (empirical_lfpr[year] && empirical_lfpr[year][iso3] && empirical_lfpr[year][iso3].t !== undefined) {
              true_val = 1.0 - empirical_lfpr[year][iso3].t;
            }
          }

          if (true_val !== null && true_val !== undefined && !isNaN(true_val) && pred_post !== undefined && !isNaN(pred_post)) {
            let pop_w = country_rates[iso3].pop;
            yt.push(true_val);
            yp_post.push(pred_post);
            yp_pre.push(pred_pre);
            w.push(pop_w);

            //OECD Core Transfer Out-of-Sample partition
            if (!core_oecd_set.has(iso3)) {
              yt_oos.push(true_val);
              yp_post_oos.push(pred_post);
              yp_pre_oos.push(pred_pre);
              w_oos.push(pop_w);
            }
          }
        }

        let m_post_global = calculateMetrics(yt, yp_post, w);
        let m_post_oos = calculateMetrics(yt_oos, yp_post_oos, w_oos);
        let m_pre_global = calculateMetrics(yt, yp_pre, w);
        let m_pre_oos = calculateMetrics(yt_oos, yp_pre_oos, w_oos);

        year_results[ind.key] = {
          post_clamp_global: m_post_global,
          post_clamp_non_oecd_oos: m_post_oos,
          regime_c_pre_clamp_global: m_pre_global,
          regime_c_pre_clamp_non_oecd_oos: m_pre_oos
        };

        if (m_pre_global.n > 0) {
          display_rows.push({
            "Indicator": ind.key,
            "N": m_pre_global.n,
            "Regime C Pre R^2": (m_pre_global.r2 * 100).toFixed(2).replace(".", ",") + "%",
            "Regime C Pre r": m_pre_global.pearson_r.toFixed(4).replace(".", ","),
            "Regime C Pre MAE": (m_pre_global.mae * 100).toFixed(2).replace(".", ",") + "%",
            "Post R^2": (m_post_global.r2 * 100).toFixed(2).replace(".", ",") + "%",
            "Post Weighted R^2": (m_post_global.r2_weighted * 100).toFixed(2).replace(".", ",") + "%",
            "Post Pearson r": m_post_global.pearson_r.toFixed(4).replace(".", ","),
            "Post MAE": (m_post_global.mae * 100).toFixed(2).replace(".", ",") + "%"
          });
        }
      }

      console.log(`--------------------------------------------------------------------------------`);
      console.log(`BENCHMARK YEAR ${year} (Processed in ${((Date.now() - t_year_start) / 1000).toFixed(2)}s)`);
      console.log(`--------------------------------------------------------------------------------`);
      if (display_rows.length > 0) {
        console.table(display_rows);
      } else {
        console.log(`No reporting ground truth for year ${year}.`);
      }

      all_evaluation_results[year] = year_results;

      //Accumulate longitudinal summary
      let lfpr_m_ent = year_results["lfpr_t"];
      let agr_m_ent = year_results["agriculture_t"];
      let man_m_ent = year_results["manufacturing_t"];
      let ser_m_ent = year_results["services_t"];

      longitudinal_summary.push({
        "Year": year,
        "N (LFPR)": lfpr_m_ent ? lfpr_m_ent.regime_c_pre_clamp_global.n : 0,
        "LFPR Pre R^2": lfpr_m_ent ? (lfpr_m_ent.regime_c_pre_clamp_global.r2 * 100).toFixed(2).replace(".", ",") + "%" : "-",
        "LFPR Post R^2": lfpr_m_ent ? (lfpr_m_ent.post_clamp_global.r2 * 100).toFixed(2).replace(".", ",") + "%" : "-",
        "LFPR Post R^2_w": lfpr_m_ent ? (lfpr_m_ent.post_clamp_global.r2_weighted * 100).toFixed(2).replace(".", ",") + "%" : "-",
        "N (Prof)": agr_m_ent ? agr_m_ent.regime_c_pre_clamp_global.n : 0,
        "Agr Pre r": agr_m_ent ? agr_m_ent.regime_c_pre_clamp_global.pearson_r.toFixed(4).replace(".", ",") : "-",
        "Agr Post r": agr_m_ent ? agr_m_ent.post_clamp_global.pearson_r.toFixed(4).replace(".", ",") : "-",
        "Man Pre r": man_m_ent ? man_m_ent.regime_c_pre_clamp_global.pearson_r.toFixed(4).replace(".", ",") : "-",
        "Man Post r": man_m_ent ? man_m_ent.post_clamp_global.pearson_r.toFixed(4).replace(".", ",") : "-",
        "Ser Pre r": ser_m_ent ? ser_m_ent.regime_c_pre_clamp_global.pearson_r.toFixed(4).replace(".", ",") : "-",
        "Ser Post r": ser_m_ent ? ser_m_ent.post_clamp_global.pearson_r.toFixed(4).replace(".", ",") : "-"
      });
    }

    console.log(`\n================================================================================`);
    console.log(`LONGITUDINAL DECADAL EVALUATION SUMMARY (1890 - 2020)`);
    console.log(`================================================================================`);
    console.table(longitudinal_summary);

    //6. Persist JSON results
    fs.writeFileSync(output_json_path, JSON.stringify({
      generated_at: new Date().toISOString(),
      longitudinal_decadal_summary: longitudinal_summary,
      results_by_year: all_evaluation_results,
      tested_benchmark_years: benchmark_years
    }, null, 2), "utf8");

    console.log(`\n================================================================================`);
    console.log(`Saved complete decadal evaluation metrics to: ${output_json_path}`);
    console.log(`Total execution duration: ${((Date.now() - t0) / 1000).toFixed(2)}s.`);
    console.log(`================================================================================\n`);
  }
};

//Auto-run when invoked directly
if (require.main === module) {
  global.ProfessionsLFPROutOfSample.runAssessment().catch(console.error);
}
