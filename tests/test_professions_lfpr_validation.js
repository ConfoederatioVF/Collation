let fs = require("fs");
let os = require("os");
let path = require("path");
let { Worker } = require("worker_threads");

//Bootstrap paths
let root_dir = path.resolve(__dirname, "..");
let agg_folder = path.join(root_dir, "histmap/3.data_transform/professions/4.aggregates");
let lfpr_folder = path.join(root_dir, "histmap/2.data_cleaning/LFPR_OLS/3.lfpr_rates");
let output_json_path = path.join(root_dir, "tests/professions_lfpr_metrics.json");
let pct_folder = path.join(root_dir, "histmap/3.data_transform/professions/3.percentages");
let worker_script = path.join(__dirname, "professions_validation_worker.js");

/**
 * Worker pool managing concurrent evaluation of rasters across threads.
 */
class ValidationWorkerPool {
  constructor (arg0_worker_count) {
    //Convert from parameters
    let worker_count = arg0_worker_count || Math.min(16, os.cpus().length);

    //Declare local instance variables
    this.active_tasks = new Map();
    this.free_workers = [];
    this.next_task_id = 1;
    this.task_queue = [];
    this.workers = [];

    //Initialise workers
    for (let i = 0; i < worker_count; i++) {
      let worker = new Worker(worker_script);

      worker.on("message", (msg) => {
        let task = this.active_tasks.get(msg.id);
        if (task) {
          this.active_tasks.delete(msg.id);
          this.free_workers.push(worker);

          if (!msg.success) {
            task.reject(new Error(msg.error || `Worker failed for year ${msg.year}`));
          } else {
            task.resolve(msg.data);
          }
          this._dispatch();
        }
      });

      worker.on("error", (err) => {
        console.error(`[Worker ${i}] error:`, err);
      });

      this.free_workers.push(worker);
      this.workers.push(worker);
    }
  }

  _dispatch () {
    while (this.free_workers.length > 0 && this.task_queue.length > 0) {
      let task = this.task_queue.shift();
      let worker = this.free_workers.shift();

      this.active_tasks.set(task.id, task);
      worker.postMessage({
        agg_folder: task.payload.agg_folder,
        id: task.id,
        lfpr_folder: task.payload.lfpr_folder,
        pct_folder: task.payload.pct_folder,
        type: "validate_year",
        year: task.payload.year
      });
    }
  }

  execute (arg0_payload) {
    //Convert from parameters
    let payload = arg0_payload;
    let task_id = this.next_task_id++;

    //Return statement
    return new Promise((resolve, reject) => {
      this.task_queue.push({
        id: task_id,
        payload: payload,
        reject: reject,
        resolve: resolve
      });
      this._dispatch();
    });
  }

  terminate () {
    for (let i = 0; i < this.workers.length; i++) this.workers[i].terminate();
  }
}

/**
 * Main assessment function for validating LFPR and professions distributions across all years.
 */
let runValidationAssessment = async function () {
  console.log("================================================================================");
  console.log("PROFESSIONS & LFPR MULTI-THREADED PERCENTAGE VALIDATION FRAMEWORK");
  console.log("================================================================================\n");

  let t0 = Date.now();

  //1. Discover all years from saved rasters
  let all_files = fs.readdirSync(pct_folder);
  let target_years = all_files
    .filter(f => f.startsWith("agriculture_m_") && f.endsWith(".png"))
    .map(f => parseInt(f.replace("agriculture_m_", "").replace(".png", "")))
    .sort((a, b) => a - b);

  console.log(`Discovered ${target_years.length} years across percentage archive [${target_years[0]} to ${target_years[target_years.length - 1]}].`);

  let completed_count = 0;
  let results = [];
  let total_years = target_years.length;

  if (process.argv.includes("--recalc") && fs.existsSync(output_json_path)) {
    console.log("Loading existing year metrics from JSON for summary recalculation...\n");
    let existing_data = JSON.parse(fs.readFileSync(output_json_path, "utf8"));
    results = Object.values(existing_data.years);
  } else {
    //2. Initialise worker pool
    let worker_count = Math.min(16, os.cpus().length);
    let pool = new ValidationWorkerPool(worker_count);
    console.log(`Initialised ValidationWorkerPool with ${worker_count} concurrent worker threads.\n`);

    let year_promises = [];

    for (let i = 0; i < total_years; i++) {
      let year = target_years[i];
      let promise = pool.execute({
        agg_folder: agg_folder,
        lfpr_folder: lfpr_folder,
        pct_folder: pct_folder,
        year: year
      }).then((res) => {
        completed_count++;
        if (completed_count % 16 === 0 || completed_count === total_years) {
          let pct = Math.round((completed_count / total_years) * 100);
          console.log(`[Progress] Validated ${completed_count}/${total_years} years (${pct}% complete)..`);
        }
        return res;
      });

      year_promises.push(promise);
    }

    results = await Promise.all(year_promises);
    pool.terminate();
    console.log(`\nCompleted evaluation of all ${results.length} years in ${((Date.now() - t0) / 1000).toFixed(2)}s.`);
  }

  //3. Sort and index results
  results.sort((a, b) => a.year - b.year);

  let all_years_valid = true;
  let global_bounds_valid = true;
  let max_lfpr_error_global = 0;
  let max_sex_agg_error_global = 0;
  let max_sum_to_one_error_global = 0;
  let years_map = {};

  for (let i = 0; i < results.length; i++) {
    let r = results[i];

    //Update validity check against machine precision threshold
    let sex_consistency_ok = (r.sex_consistency.max_aggregation_error < 1.0);
    r.sex_consistency.is_valid = sex_consistency_ok;
    r.validation.sex_consistency_valid = sex_consistency_ok;
    r.flags = r.flags.filter(f => !f.includes("Sex aggregation error"));
    if (!sex_consistency_ok) r.flags.push(`Sex aggregation error: max dev ${r.sex_consistency.max_aggregation_error}`);

    r.is_valid = (r.validation.bounds_valid && r.validation.sum_to_one_valid && r.validation.lfpr_valid && sex_consistency_ok);
    years_map[r.year] = r;

    if (!r.is_valid) all_years_valid = false;
    if (!r.validation.bounds_valid) global_bounds_valid = false;

    let s1_max = Math.max(r.professions.m.max_sum_to_one_error, r.professions.f.max_sum_to_one_error, r.professions.t.max_sum_to_one_error);
    if (s1_max > max_sum_to_one_error_global) max_sum_to_one_error_global = s1_max;

    let lfpr_max = Math.max(r.lfpr.m.max_residual_error || 0, r.lfpr.f.max_residual_error || 0);
    if (lfpr_max > max_lfpr_error_global) max_lfpr_error_global = lfpr_max;

    if (r.sex_consistency.max_aggregation_error > max_sex_agg_error_global)
      max_sex_agg_error_global = r.sex_consistency.max_aggregation_error;
  }

  //4. Extract benchmark milestones by sex
  let milestone_years = [-10000, -8000, -6000, -4000, -3000, -2000, -1000, 0, 500, 1000, 1500, 1750, 1820, 1890, 1950, 2000, 2025];
  let milestone_summaries = { f: [], m: [], t: [] };
  let sexes = ["m", "f", "t"];

  for (let s = 0; s < sexes.length; s++) {
    let sex = sexes[s];
    for (let i = 0; i < milestone_years.length; i++) {
      let y = milestone_years[i];
      let yr_data = years_map[y];
      if (!yr_data) continue;

      let prof = yr_data.professions[sex];
      let lfpr = yr_data.lfpr[sex];

      milestone_summaries[sex].push({
        agriculture_active_pct: prof.categories.agriculture.active_share_pct,
        agriculture_pop_pct: prof.categories.agriculture.pop_weighted_pct,
        informal_active_pct: prof.categories.informal_labour.active_share_pct,
        informal_pop_pct: prof.categories.informal_labour.pop_weighted_pct,
        is_valid: yr_data.is_valid,
        lfpr_pct: lfpr.pop_weighted_mean,
        manufacturing_active_pct: prof.categories.manufacturing.active_share_pct,
        manufacturing_pop_pct: prof.categories.manufacturing.pop_weighted_pct,
        not_in_work_pop_pct: prof.categories.not_in_work.pop_weighted_pct,
        services_active_pct: prof.categories.services.active_share_pct,
        services_pop_pct: prof.categories.services.pop_weighted_pct,
        working_pop_millions: yr_data.working_age_population_millions[sex],
        year: y
      });
    }
  }

  //5. Assemble single compiled JSON artifact
  let output_object = {
    summary: {
      all_years_valid: all_years_valid,
      execution_time_seconds: parseFloat(((Date.now() - t0) / 1000).toFixed(2)),
      generated_at: new Date().toISOString(),
      global_bounds_valid: global_bounds_valid,
      key_milestones_by_sex: milestone_summaries,
      key_milestones_summary: milestone_summaries.t,
      max_lfpr_error_global: max_lfpr_error_global,
      max_sex_aggregation_error_global: max_sex_agg_error_global,
      max_sum_to_one_error_global: max_sum_to_one_error_global,
      total_pixels_per_raster: 9331200,
      total_years_evaluated: total_years,
      year_range: [target_years[0], target_years[target_years.length - 1]]
    },
    years: years_map
  };

  fs.writeFileSync(output_json_path, JSON.stringify(output_object, null, 2));
  console.log(`\nSuccessfully compiled and written global validation metrics to:`);
  console.log(`-> ${output_json_path}\n`);

  //6. Print formatted console tables for each sex
  let sex_titles = {
    f: "FEMALE (F) WORKING-AGE POPULATION",
    m: "MALE (M) WORKING-AGE POPULATION",
    t: "TOTAL (T) COMBINED POPULATION"
  };

  for (let s = 0; s < sexes.length; s++) {
    let sex = sexes[s];
    let list = milestone_summaries[sex];

    console.log("=========================================================================================================================");
    console.log(`HISTORICAL BENCHMARK MILESTONES: ${sex_titles[sex]}`);
    console.log("=========================================================================================================================");
    console.log(
      "Year".padEnd(8) +
      "WorkingPop".padEnd(12) +
      "LFPR (%)".padEnd(10) +
      "Agri(Act)".padEnd(11) +
      "Mfg(Act)".padEnd(11) +
      "Serv(Act)".padEnd(11) +
      "Inf(Act)".padEnd(11) +
      "NotWork(Pop)".padEnd(14) +
      "Status"
    );
    console.log("-------------------------------------------------------------------------------------------------------------------------");

    for (let i = 0; i < list.length; i++) {
      let m = list[i];
      let yr_str = (m.year < 0 ? `${Math.abs(m.year)} BC` : `${m.year} AD`).padEnd(8);
      let pop_str = `${m.working_pop_millions.toFixed(2)}M`.padEnd(12);
      let lfpr_str = `${(m.lfpr_pct * 100).toFixed(1)}%`.padEnd(10);
      let agri_str = `${(m.agriculture_active_pct * 100).toFixed(1)}%`.padEnd(11);
      let mfg_str = `${(m.manufacturing_active_pct * 100).toFixed(1)}%`.padEnd(11);
      let serv_str = `${(m.services_active_pct * 100).toFixed(1)}%`.padEnd(11);
      let inf_str = `${(m.informal_active_pct * 100).toFixed(1)}%`.padEnd(11);
      let not_work_str = `${(m.not_in_work_pop_pct * 100).toFixed(1)}%`.padEnd(14);
      let status_str = m.is_valid ? "VALID" : "INVALID";

      console.log(yr_str + pop_str + lfpr_str + agri_str + mfg_str + serv_str + inf_str + not_work_str + status_str);
    }
    console.log("=========================================================================================================================\n");
  }

  console.log(`Global Assessment Verdict: ${all_years_valid ? "ALL YEARS PASSED VALIDATION CHECKS" : "VALIDATION ISSUES ENCOUNTERED"}`);
  console.log(`Max Sum-to-One Error: ${max_sum_to_one_error_global}`);
  console.log(`Max LFPR Consistency Error: ${max_lfpr_error_global}`);
  console.log(`Max Sex Aggregation Error: ${max_sex_agg_error_global}`);
};

//Execute
runValidationAssessment().catch((err) => {
  console.error("Validation assessment failed:", err);
  process.exit(1);
});
