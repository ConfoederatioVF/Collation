let fs = require("fs");
let path = require("path");
let { parentPort } = require("worker_threads");

//Bootstrap worker dependencies
let root_dir = path.resolve(__dirname, "..");
let pngjs = require(path.join(root_dir, "node_modules/pngjs"));

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
  let pixel_count = parsed_png.width * parsed_png.height;
  let raw_buffer = parsed_png.data.buffer;
  let raw_byte_offset = parsed_png.data.byteOffset;
  let u32_view = new Uint32Array(raw_buffer, raw_byte_offset, pixel_count);

  //In-place bitwise big-endian to little-endian word swap
  for (let i = 0; i < pixel_count; i++) {
    let u = u32_view[i];
    u32_view[i] = ((u >>> 24) & 0xff) | ((u >>> 8) & 0xff00) | ((u << 8) & 0xff0000) | (u << 24);
  }

  //Return statement
  return {
    data: new Float32Array(raw_buffer, raw_byte_offset, pixel_count),
    height: parsed_png.height,
    width: parsed_png.width
  };
};

/**
 * Computes quantile distribution summary from sampled array.
 * 
 * @param {number[]} arg0_sample_array
 * 
 * @returns {{ max: number, mean: number, median: number, min: number, p25: number, p75: number }}
 */
let computeQuantiles = function (arg0_sample_array) {
  //Convert from parameters
  let sample_array = arg0_sample_array;

  //Guard clauses
  if (!sample_array || sample_array.length === 0)
    return { max: 0, mean: 0, median: 0, min: 0, p25: 0, p75: 0 };

  //Declare local instance variables
  let len = sample_array.length;
  let sum = 0;

  sample_array.sort((a, b) => a - b);
  for (let i = 0; i < len; i++) sum += sample_array[i];

  //Return statement
  return {
    max: sample_array[len - 1],
    mean: sum / len,
    median: sample_array[Math.floor(len * 0.50)],
    min: sample_array[0],
    p25: sample_array[Math.floor(len * 0.25)],
    p75: sample_array[Math.floor(len * 0.75)]
  };
};

//Listen for messages from master thread
parentPort.on("message", (arg0_message) => {
  //Convert from parameters
  let message = arg0_message;

  //Guard clauses
  if (!message || typeof message !== "object") return;
  if (message.type !== "validate_year") return;

  //Declare local instance variables
  let agg_folder = message.agg_folder;
  let categories = ["agriculture", "manufacturing", "services", "informal_labour", "not_in_work"];
  let id = message.id;
  let lfpr_folder = message.lfpr_folder;
  let pct_folder = message.pct_folder;
  let sexes = ["m", "f", "t"];
  let year = message.year;

  try {
    let agg_rasters = {};
    let pct_rasters = {};

    //1. Load percentage rasters
    for (let i = 0; i < sexes.length; i++) {
      let s = sexes[i];
      pct_rasters[s] = {};
      agg_rasters[s] = {};

      for (let x = 0; x < categories.length; x++) {
        let c = categories[x];
        let agg_path = path.join(agg_folder, `${c}_${s}_${year}.png`);
        let pct_path = path.join(pct_folder, `${c}_${s}_${year}.png`);

        pct_rasters[s][c] = loadFloat32Raster(pct_path);
        agg_rasters[s][c] = loadFloat32Raster(agg_path);

        if (!pct_rasters[s][c] || !agg_rasters[s][c])
          throw new Error(`Missing raster for ${c}_${s}_${year}`);
      }
    }

    //2. Load LFPR rasters
    let lfpr_f = loadFloat32Raster(path.join(lfpr_folder, `lfpr_f_${year}.png`));
    let lfpr_m = loadFloat32Raster(path.join(lfpr_folder, `lfpr_m_${year}.png`));

    if (!lfpr_f || !lfpr_m)
      throw new Error(`Missing LFPR raster for year ${year}`);

    //3. Pixel validation loop
    let total_pixels = pct_rasters["m"]["agriculture"].data.length;
    let sample_step = Math.max(1, Math.floor(total_pixels / 30000));

    let bounds_valid = true;
    let flags = [];
    let headcount_sums = {};
    let inhabited_cell_count = { f: 0, m: 0, t: 0 };
    let lfpr_samples = { f: [], m: [], t: [] };
    let lfpr_weighted_sum = { f: 0, m: 0, t: 0 };
    let max_lfpr_error = { f: 0, m: 0 };
    let max_sex_agg_error = 0;
    let max_sum_to_one_error = { f: 0, m: 0, t: 0 };
    let pct_samples = {};
    let total_pop_sums = { f: 0, m: 0, t: 0 };

    for (let i = 0; i < sexes.length; i++) {
      let s = sexes[i];
      headcount_sums[s] = {};
      pct_samples[s] = {};
      for (let x = 0; x < categories.length; x++) {
        headcount_sums[s][categories[x]] = 0;
        pct_samples[s][categories[x]] = [];
      }
    }

    for (let i = 0; i < total_pixels; i++) {
      //A. Evaluate sexes m and f
      let pop_f = 0;
      let pop_m = 0;

      for (let x = 0; x < categories.length; x++) {
        let c = categories[x];
        pop_f += agg_rasters["f"][c].data[i];
        pop_m += agg_rasters["m"][c].data[i];
      }

      let is_sampled = (i % sample_step === 0);

      //Evaluate Male
      if (pop_m > 0) {
        inhabited_cell_count.m++;
        total_pop_sums.m += pop_m;

        let lfpr_val_m = lfpr_m.data[i];
        let sum_pct_m = 0;

        if (lfpr_val_m < -0.001 || lfpr_val_m > 1.001 || isNaN(lfpr_val_m)) bounds_valid = false;
        lfpr_weighted_sum.m += lfpr_val_m * pop_m;
        if (is_sampled) lfpr_samples.m.push(lfpr_val_m);

        for (let x = 0; x < categories.length; x++) {
          let c = categories[x];
          let p = pct_rasters["m"][c].data[i];
          let ag = agg_rasters["m"][c].data[i];

          if (p < -0.001 || p > 1.001 || isNaN(p)) bounds_valid = false;
          sum_pct_m += p;
          headcount_sums["m"][c] += ag;
          if (is_sampled) pct_samples["m"][c].push(p);
        }

        let dev_s1_m = Math.abs(sum_pct_m - 1.0);
        if (dev_s1_m > max_sum_to_one_error.m) max_sum_to_one_error.m = dev_s1_m;

        let not_in_work_m = pct_rasters["m"]["not_in_work"].data[i];
        let dev_lfpr_m = Math.abs(not_in_work_m - Math.max(0, 1.0 - lfpr_val_m));
        if (dev_lfpr_m > max_lfpr_error.m) max_lfpr_error.m = dev_lfpr_m;
      }

      //Evaluate Female
      if (pop_f > 0) {
        inhabited_cell_count.f++;
        total_pop_sums.f += pop_f;

        let lfpr_val_f = lfpr_f.data[i];
        let sum_pct_f = 0;

        if (lfpr_val_f < -0.001 || lfpr_val_f > 1.001 || isNaN(lfpr_val_f)) bounds_valid = false;
        lfpr_weighted_sum.f += lfpr_val_f * pop_f;
        if (is_sampled) lfpr_samples.f.push(lfpr_val_f);

        for (let x = 0; x < categories.length; x++) {
          let c = categories[x];
          let p = pct_rasters["f"][c].data[i];
          let ag = agg_rasters["f"][c].data[i];

          if (p < -0.001 || p > 1.001 || isNaN(p)) bounds_valid = false;
          sum_pct_f += p;
          headcount_sums["f"][c] += ag;
          if (is_sampled) pct_samples["f"][c].push(p);
        }

        let dev_s1_f = Math.abs(sum_pct_f - 1.0);
        if (dev_s1_f > max_sum_to_one_error.f) max_sum_to_one_error.f = dev_s1_f;

        let not_in_work_f = pct_rasters["f"]["not_in_work"].data[i];
        let dev_lfpr_f = Math.abs(not_in_work_f - Math.max(0, 1.0 - lfpr_val_f));
        if (dev_lfpr_f > max_lfpr_error.f) max_lfpr_error.f = dev_lfpr_f;
      }

      //Evaluate Total (t)
      let pop_t = 0;
      for (let x = 0; x < categories.length; x++)
        pop_t += agg_rasters["t"][categories[x]].data[i];

      if (pop_t > 0) {
        inhabited_cell_count.t++;
        total_pop_sums.t += pop_t;

        let sum_pct_t = 0;
        let lfpr_t_val = (pop_m + pop_f > 0)
          ? ((pop_m * lfpr_m.data[i] + pop_f * lfpr_f.data[i]) / (pop_m + pop_f))
          : 0;

        lfpr_weighted_sum.t += lfpr_t_val * pop_t;
        if (is_sampled) lfpr_samples.t.push(lfpr_t_val);

        for (let x = 0; x < categories.length; x++) {
          let c = categories[x];
          let p = pct_rasters["t"][c].data[i];
          let ag = agg_rasters["t"][c].data[i];

          if (p < -0.001 || p > 1.001 || isNaN(p)) bounds_valid = false;
          sum_pct_t += p;
          headcount_sums["t"][c] += ag;
          if (is_sampled) pct_samples["t"][c].push(p);

          //Sex aggregation consistency check
          let expected_ag_t = agg_rasters["m"][c].data[i] + agg_rasters["f"][c].data[i];
          let diff_ag = Math.abs(ag - expected_ag_t);
          if (diff_ag > max_sex_agg_error) max_sex_agg_error = diff_ag;
        }

        let dev_s1_t = Math.abs(sum_pct_t - 1.0);
        if (dev_s1_t > max_sum_to_one_error.t) max_sum_to_one_error.t = dev_s1_t;
      }
    }

    //4. Compile structured metrics
    let professions_out = {};
    for (let i = 0; i < sexes.length; i++) {
      let s = sexes[i];
      let active_headcount = 0;
      let categories_data = {};
      let total_pop = total_pop_sums[s];

      for (let x = 0; x < categories.length; x++) {
        let c = categories[x];
        let quantiles = computeQuantiles(pct_samples[s][c]);
        let hc = headcount_sums[s][c];

        if (c !== "not_in_work") active_headcount += hc;

        categories_data[c] = {
          headcount_millions: hc / 1e6,
          max: quantiles.max,
          mean_unweighted: quantiles.mean,
          median: quantiles.median,
          min: quantiles.min,
          p25: quantiles.p25,
          p75: quantiles.p75,
          pop_weighted_pct: (total_pop > 0) ? (hc / total_pop) : 0
        };
      }

      //Add active shares for the 4 active categories
      for (let x = 0; x < categories.length; x++) {
        let c = categories[x];
        if (c !== "not_in_work") {
          categories_data[c].active_share_pct = (active_headcount > 0)
            ? (headcount_sums[s][c] / active_headcount)
            : 0;
        }
      }

      professions_out[s] = {
        active_labour_millions: active_headcount / 1e6,
        categories: categories_data,
        inhabited_cells: inhabited_cell_count[s],
        max_sum_to_one_error: max_sum_to_one_error[s],
        sum_to_one_valid: (max_sum_to_one_error[s] < 0.001)
      };
    }

    //Compile LFPR metrics
    let lfpr_out = {};
    for (let i = 0; i < sexes.length; i++) {
      let s = sexes[i];
      let quantiles = computeQuantiles(lfpr_samples[s]);
      let total_pop = total_pop_sums[s];

      lfpr_out[s] = {
        max: quantiles.max,
        mean_unweighted: quantiles.mean,
        median: quantiles.median,
        min: quantiles.min,
        p25: quantiles.p25,
        p75: quantiles.p75,
        pop_weighted_mean: (total_pop > 0) ? (lfpr_weighted_sum[s] / total_pop) : 0,
        valid: (quantiles.min >= -0.001 && quantiles.max <= 1.001)
      };

      if (s !== "t") {
        lfpr_out[s].max_residual_error = max_lfpr_error[s];
        lfpr_out[s].residual_valid = (max_lfpr_error[s] < 0.001);
      }
    }

    //Check flags and validity
    let sum_to_one_ok = (max_sum_to_one_error.m < 0.001 && max_sum_to_one_error.f < 0.001 && max_sum_to_one_error.t < 0.001);
    let lfpr_ok = (max_lfpr_error.m < 0.001 && max_lfpr_error.f < 0.001);
    let sex_consistency_ok = (max_sex_agg_error < 1.0);

    if (!bounds_valid) flags.push("Bounds error: percentages outside [0, 1]");
    if (!sum_to_one_ok) flags.push(`Sum-to-one error: max dev ${Math.max(max_sum_to_one_error.m, max_sum_to_one_error.f, max_sum_to_one_error.t)}`);
    if (!lfpr_ok) flags.push(`LFPR consistency error: max dev ${Math.max(max_lfpr_error.m, max_lfpr_error.f)}`);
    if (!sex_consistency_ok) flags.push(`Sex aggregation error: max dev ${max_sex_agg_error}`);

    let overall_valid = (bounds_valid && sum_to_one_ok && lfpr_ok && sex_consistency_ok);

    //Return result
    parentPort.postMessage({
      data: {
        flags: flags,
        is_valid: overall_valid,
        lfpr: lfpr_out,
        professions: professions_out,
        sex_consistency: {
          is_valid: sex_consistency_ok,
          max_aggregation_error: max_sex_agg_error
        },
        validation: {
          bounds_valid: bounds_valid,
          lfpr_valid: lfpr_ok,
          sex_consistency_valid: sex_consistency_ok,
          sum_to_one_valid: sum_to_one_ok
        },
        working_age_population_millions: {
          f: total_pop_sums.f / 1e6,
          m: total_pop_sums.m / 1e6,
          t: total_pop_sums.t / 1e6
        },
        year: year
      },
      id: id,
      success: true
    });
  } catch (err) {
    parentPort.postMessage({
      error: err.message,
      id: id,
      success: false,
      year: year
    });
  }
});
