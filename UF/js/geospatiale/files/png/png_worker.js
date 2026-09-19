//[VERCENGEN / GEOSPATIALE]
//Dedicated worker thread for parallel geoprocessing, timeseries raster operations, and statistical model training.

let fs = require("fs");
let path = require("path");

let parentPort = null;
let workerData = null;

try {
  let worker_threads = require("worker_threads");
  parentPort = worker_threads.parentPort;
  workerData = worker_threads.workerData;
} catch (e) {}

let is_child_process = (!parentPort && typeof process !== "undefined" && typeof process.send === "function");
let message_port = (parentPort) ? parentPort : ((is_child_process) ? {
  on: (event, callback) => process.on(event, callback),
  postMessage: (data) => process.send(data)
} : null);

let worker_id = (workerData && workerData.worker_id !== undefined) ?
  workerData.worker_id : (process.env.WORKER_ID ? parseInt(process.env.WORKER_ID) : 0);

//Safeguard require against AMD loader pollution in worker
{
  let Module = require("module");
  let original_require = Module.prototype.require;

  Module.prototype.require = function () {
    let saved_amd;
    let saved_define;

    if (typeof global.define !== "undefined" && global.define && global.define.amd) {
      saved_amd = global.define.amd;
      saved_define = global.define;
      try { delete global.define.amd; } catch (e) {}
      global.define = undefined;
    }

    try {
      return original_require.apply(this, arguments);
    } finally {
      if (saved_define !== undefined) {
        global.define = saved_define;
        if (saved_amd !== undefined) global.define.amd = saved_amd;
      }
    }
  };
}

//Bootstrap worker global environment
global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");

try { global.JSON5 = require("json5"); } catch (e) {}
try { global.mathjs = require("mathjs"); } catch (e) {}
try { global.ml_matrix = require("ml-matrix"); } catch (e) {}

//Load core UF dependencies
let root_dir = path.resolve(__dirname, "../../../../../");

let loadDirectory = function (rel_dir) {
  let full_dir = path.join(root_dir, rel_dir);
  if (fs.existsSync(full_dir)) {
    let files = fs.readdirSync(full_dir).filter(f => f.endsWith(".js") && !f.includes("worker"));
    for (let i = 0; i < files.length; i++) {
      try {
        require(path.join(full_dir, files[i]));
      } catch (e) {
        console.error(`[GeoWorker ${worker_id}] Failed to require ${path.join(rel_dir, files[i])}:`, e);
      }
    }
  }
};

loadDirectory("UF/js/number");
loadDirectory("UF/js/colour");
loadDirectory("UF/js/file");
loadDirectory("UF/js/object");
loadDirectory("UF/js/array");
loadDirectory("UF/js/blacktraffic");
loadDirectory("UF/js/statistics");
loadDirectory("UF/js/geospatiale/files/png");

//Define Histmap paths on global for stage modules
global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");
global.h4 = path.join(root_dir, "histmap/4.data_exports/");
global.h5 = path.join(root_dir, "histmap/5.data_visualisation/");

let safeRequire = function (rel_path) {
  let full_path = path.join(root_dir, rel_path);
  if (fs.existsSync(full_path)) {
    try {
      require(full_path);
    } catch (err) {
      console.error(`[GeoWorker ${worker_id}] Failed to require ${rel_path}:`, err);
    }
  }
};

//Load common histmap pipeline modules
safeRequire("histmap/2.data_cleaning/population_Stadester/stadester_rasters.js");
safeRequire("histmap/2.data_cleaning/population_Stadester/stadester_uud.js");
safeRequire("histmap/2.data_cleaning/metadata_HYDE/metadata_HYDE.js");

//Task execution handlers
let handleTask = async function (task) {
  let task_type = task.type;

  //1. Ping healthcheck
  if (task_type === "ping") {
    return { pong: true, worker_id: worker_id };
  }

  //2. Linear raster interpolation between two years
  if (task_type === "linear_interpolation") {
    return GeoPNG.linearInterpolation(
      task.from_file_path,
      task.to_file_path,
      task.output_file_path,
      task.options
    );
  }

  //3. Areal timeseries clamping
  if (task_type === "areal_clamping") {
    let indexing = task.areal_indexing;
    let input_path = task.input_path;
    let output_path = task.output_path;

    if (!fs.existsSync(input_path)) return null;

    let raster = await GeoPNG.loadNumberRasterImageAsync(input_path, { format: task.format || "float32" });
    let clamped_data = GeoPNG.applyArealClamping({
      data: raster.data,
      mask_areas: indexing.mask_areas,
      mask_pixel_indices: indexing.mask_pixel_indices,
      mode: task.mode,
      targets: task.targets,
      weights: task.weights
    });

    await GeoPNG.saveNumberRasterImageAsync({
      data: clamped_data,
      file_path: output_path,
      format: task.format || "float32",
      height: indexing.height,
      width: indexing.width
    });

    return output_path;
  }

  //4. Raster math operation (multiply, divide, add, subtract, scale)
  if (task_type === "raster_operation") {
    let format = task.format || "float32";
    let format_1 = task.format_1 || format;
    let format_2 = task.format_2 || format;
    let input_path_1 = task.input_path_1;
    let input_path_2 = task.input_path_2;
    let op = task.operation || task.op || "multiply";
    let output_path = task.output_path;

    if (!fs.existsSync(input_path_1)) return null;

    let raster1 = await GeoPNG.loadNumberRasterImageAsync(input_path_1, { format: format_1 });
    let total_pixels = raster1.data.length;
    let output_data = new Float32Array(total_pixels);

    if (input_path_2 && fs.existsSync(input_path_2)) {
      let data1 = raster1.data;
      let raster2 = await GeoPNG.loadNumberRasterImageAsync(input_path_2, { format: format_2 });
      let data2 = raster2.data;

      if (op === "multiply") {
        for (let i = 0; i < total_pixels; i++) output_data[i] = data1[i]*data2[i];
      } else if (op === "divide") {
        for (let i = 0; i < total_pixels; i++) {
          if (data1[i] > 0 && data2[i] > 0 && !isNaN(data1[i]) && !isNaN(data2[i])) {
            let val = data1[i]/data2[i];
            output_data[i] = isFinite(val) ? val : 0;
          } else {
            output_data[i] = 0;
          }
        }
      } else if (op === "add") {
        for (let i = 0; i < total_pixels; i++) output_data[i] = data1[i] + data2[i];
      } else if (op === "subtract") {
        for (let i = 0; i < total_pixels; i++) output_data[i] = data1[i] - data2[i];
      } else if (op === "subtract_clamped") {
        for (let i = 0; i < total_pixels; i++) output_data[i] = Math.max(0, data1[i] - data2[i]);
      } else if (op === "overlay") {
        for (let i = 0; i < total_pixels; i++) output_data[i] = (data2[i] > 0) ? data2[i] : data1[i];
      }
    } else if (task.scalar !== undefined) {
      let data1 = raster1.data;
      let scalar = task.scalar;
      for (let i = 0; i < total_pixels; i++) output_data[i] = data1[i]*scalar;
    }

    let out_dir = path.dirname(output_path);
    if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });

    await GeoPNG.saveNumberRasterImageAsync({
      data: output_data,
      file_path: output_path,
      format: format,
      height: raster1.height,
      width: raster1.width
    });

    return output_path;
  }

  //5. Train OLS Model on continuous raster target & covariates
  if (task_type === "train_ols") {
    let covariates_map = task.covariates_map || {};
    let options = task.options || {};
    let output_file_path = path.resolve(task.output_file_path);
    let target_file_path = path.resolve(task.target_file_path);
    let target_format = task.target_format || "float32";

    let out_dir = path.dirname(output_file_path);
    if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });

    if (!fs.existsSync(target_file_path))
      throw new Error(`Target raster not found: ${target_file_path}`);

    let loaded_obj = await Statistics.loadOLSCovariates(target_file_path, {
      covariates_obj: covariates_map,
      formatting_parameters: options.formatting_parameters || [],
      utility_format: target_format
    });

    if (!loaded_obj || !loaded_obj.X || loaded_obj.X.length === 0)
      return { key: options.key, reason: "no_valid_samples", success: false };

    let model = Statistics.trainOLSModel(output_file_path, loaded_obj, options);
    return {
      key: options.key,
      output_file_path: output_file_path,
      sample_count: loaded_obj.X.length,
      success: true
    };
  }

  //6. Train OLS Model on point dataset & covariates
  if (task_type === "train_ols_points") {
    let covariates_map = task.covariates_map || {};
    let options = task.options || {};
    let output_file_path = path.resolve(task.output_file_path);
    let points = task.points || [];
    let target_year = task.target_year;

    let out_dir = path.dirname(output_file_path);
    if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });

    let dataset = await Statistics.LearningFramework.extractPointDataset(points, target_year, {
      covariates_obj: covariates_map,
      covariates_year: task.covariates_year || target_year
    });

    if (!dataset || !dataset.X || dataset.X.length === 0)
      return { key: options.key, reason: "no_valid_samples", success: false };

    let model = Statistics.trainOLSModel(output_file_path, dataset, options);
    return {
      key: options.key,
      output_file_path: output_file_path,
      sample_count: dataset.X.length,
      success: true
    };
  }

  //7. Generate OLS continuous prediction raster
  if (task_type === "generate_ols_raster") {
    let covariates_map = task.covariates_map || {};
    let model_obj = task.model_obj;
    let options = task.options || {};
    let output_file_path = path.resolve(task.output_file_path);

    let out_dir = path.dirname(output_file_path);
    if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });

    await Statistics.generateOLSRaster(output_file_path, {
      ...options,
      covariates_obj: covariates_map,
      model_obj: model_obj
    });

    return { output_file_path: output_file_path, success: true };
  }

  //8. Train Multinomial Logit categorical model
  if (task_type === "train_multinomial_logit") {
    let categories = task.categories || [];
    let covariates_map = task.covariates_map || {};
    let model_path = path.resolve(task.model_path);
    let options = task.options || {};
    let target_paths = task.target_paths || {};

    let out_dir = path.dirname(model_path);
    if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });

    //Load covariate rasters
    let cov_rasters = {};
    let valid_keys = [];
    for (let k in covariates_map) {
      let entry = covariates_map[k];
      let fmt = Array.isArray(entry) ? entry[1] : "float32";
      let p = Array.isArray(entry) ? entry[0] : entry;
      if (fs.existsSync(p)) {
        cov_rasters[k] = GeoPNG.loadNumberRasterImage(p, { format: fmt });
        valid_keys.push(k);
      }
    }

    //Load target category rasters
    let missing_target = false;
    let target_rasters = {};
    for (let i = 0; i < categories.length; i++) {
      let cat = categories[i];
      let p = target_paths[cat];
      if (!p || !fs.existsSync(p)) {
        missing_target = true;
        break;
      }
      target_rasters[cat] = GeoPNG.loadNumberRasterImage(p, { format: "float32" });
    }

    if (missing_target || valid_keys.length === 0)
      return { reason: "missing_inputs", success: false };

    //Optional filter raster (e.g. popc_ to skip uninhabited pixels)
    let filter_raster = null;
    if (task.filter_raster_path && fs.existsSync(task.filter_raster_path))
      filter_raster = GeoPNG.loadNumberRasterImage(task.filter_raster_path, { format: task.filter_format || "float32" });

    //Sample pixels
    let first_target = target_rasters[categories[0]];
    let data_len = first_target.data.length;
    let X = [];
    let Y = [];

    for (let i = 0; i < data_len; i++) {
      if (filter_raster && filter_raster.data[i] <= 0) continue;

      let cat_pops = [];
      let total_pop = 0;
      for (let j = 0; j < categories.length; j++) {
        let cp = target_rasters[categories[j]].data[i];
        cp = (isNaN(cp) || cp < 0) ? 0 : cp;
        cat_pops.push(cp);
        total_pop += cp;
      }
      if (total_pop <= 0) continue;

      let is_valid = true;
      let x_row = [];
      for (let j = 0; j < valid_keys.length; j++) {
        let val = cov_rasters[valid_keys[j]].data[i];
        if (isNaN(val)) {
          is_valid = false;
          break;
        }
        x_row.push(val);
      }
      if (!is_valid) continue;

      let cumulative = 0;
      let rand = Math.random()*total_pop;
      let selected_class = categories[categories.length - 1];
      for (let j = 0; j < categories.length; j++) {
        cumulative += cat_pops[j];
        if (rand <= cumulative) {
          selected_class = categories[j];
          break;
        }
      }

      X.push(x_row);
      Y.push([selected_class]);
    }

    if (X.length === 0)
      return { reason: "no_samples", success: false };

    await Statistics.trainMultinomialLogitModel(model_path, { keys: valid_keys, X: X, Y: Y }, options);
    return { model_path: model_path, sample_count: X.length, success: true };
  }

  //9. Generate Multinomial Logit prediction raster
  if (task_type === "generate_multinomial_raster") {
    let covariates_map = task.covariates_map || {};
    let model_obj = task.model_obj;
    let options = task.options || {};
    let output_file_path = path.resolve(task.output_file_path);

    let out_dir = path.dirname(output_file_path);
    if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });

    await Statistics.generateMultinomialRaster(output_file_path, {
      ...options,
      covariates_obj: covariates_map,
      model_obj: model_obj
    });

    return { output_file_path: output_file_path, success: true };
  }

  //10. Regression raster prediction (OLS / Multinomial logit)
  if (task_type === "predict_raster") {
    return await Statistics.LearningFramework.predictRaster(
      task.output_file_path,
      task.model,
      task.options
    );
  }

  //11. Invoke specified stage method dynamically
  if (task_type === "invoke_method") {
    if (task.module_path) safeRequire(task.module_path);

    let target_class = global[task.class_name];
    if (!target_class || typeof target_class[task.method_name] !== "function")
      throw new Error(`Target class or method not found: ${task.class_name}.${task.method_name}`);

    let args = task.args || [];
    return await target_class[task.method_name](...args);
  }

  //12. Execute serialized handler function
  if (task_type === "eval_handler") {
    let AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
    let fn = new AsyncFunction(
      "item",
      "index",
      "context",
      "GeoPNG",
      "Statistics",
      "fs",
      "path",
      `"use strict"; return (${task.handler_source})(item, index, context);`
    );

    return await fn(
      task.item,
      task.index,
      task.context,
      global.GeoPNG,
      global.Statistics,
      global.fs,
      global.path
    );
  }

  //13. Stadester raster generation tasks
  if (task_type === "stadester_density_raster") {
    return await population_Stadester_rasters.prepareDensityRaster(task.year, task.options || {});
  }
  if (task_type === "stadester_base_raster") {
    return await population_Stadester_rasters.generateStadesterBaseRaster(task.year, task.options || {});
  }
  if (task_type === "stadester_urban_raster") {
    return await population_Stadester_rasters.generateStadesterUrbanRaster(task.year, task.options || {});
  }
  if (task_type === "stadester_rural_raster") {
    return await population_Stadester_rasters.generateStadesterRuralRaster(task.year, task.options || {});
  }
  if (task_type === "stadester_population_raster") {
    return await population_Stadester_rasters.generateStadesterPopulationRaster(task.year, task.options || {});
  }

  throw new Error(`Unknown GeoWorker task type: ${task_type}`);
};

//Message receiver
if (message_port) {
  message_port.on("message", async (task) => {
    if (!task) return;

    //Abort request
    if (task.type === "abort") {
      process.exit(0);
    }

    let task_id = task.task_id;
    try {
      let result = await handleTask(task);
      message_port.postMessage({
        result: result,
        success: true,
        task_id: task_id
      });
    } catch (err) {
      message_port.postMessage({
        error: err.message || String(err),
        stack: err.stack,
        success: false,
        task_id: task_id
      });
    }
  });

  //Ensure safe exit if parent port closes or process disconnects
  if (parentPort) {
    parentPort.on("close", () => {
      process.exit(0);
    });
  } else if (typeof process !== "undefined" && process.on) {
    process.on("disconnect", () => {
      process.exit(0);
    });
  }
}
