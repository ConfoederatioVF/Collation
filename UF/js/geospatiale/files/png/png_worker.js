//[VERCENGEN / GEOSPATIALE]
//Dedicated worker thread for parallel geoprocessing and timeseries raster operations.

let fs = require("fs");
let path = require("path");
let { parentPort, workerData } = require("worker_threads");

//Bootstrap worker global environment
global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");

try {
	global.JSON5 = require("json5");
} catch (e) {}

//Load core UF dependencies
let root_dir = path.resolve(__dirname, "../../../../../");

let safeRequire = function (rel_path) {
	let full_path = path.join(root_dir, rel_path);
	if (fs.existsSync(full_path))
		try {
			require(full_path);
		} catch (err) {
			console.error(`[GeoWorker] Failed to require ${rel_path}:`, err);
		}
};

safeRequire("UF/js/number/number_basic.js");
safeRequire("UF/js/colour/colour_basic.js");
safeRequire("UF/js/file/file_basic.js");
safeRequire("UF/js/blacktraffic/blacktraffic_basic.js");
safeRequire("UF/js/geospatiale/files/png/png_framework.js");
safeRequire("UF/js/geospatiale/files/png/png_areal_framework.js");
safeRequire("UF/js/geospatiale/files/png/png_dasymetric_framework.js");
safeRequire("UF/js/geospatiale/files/png/png_delta_framework.js");
safeRequire("UF/js/geospatiale/files/png/png_interpolation.js");
safeRequire("UF/js/statistics/learning_framework.js");

//Define Histmap paths on global for stage modules
global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");
global.h4 = path.join(root_dir, "histmap/4.data_exports/");
global.h5 = path.join(root_dir, "histmap/5.data_visualisation/");

//Task execution handlers
let handleTask = async function (task) {
	let task_type = task.type;
	
	//1. Ping healthcheck
	if (task_type === "ping") {
		return { pong: true, worker_id: workerData?.worker_id };
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
	
	//4. Raster math operation (e.g. multiply A * B, divide A / B, scale A * k)
	if (task_type === "raster_operation") {
		let input_path_1 = task.input_path_1;
		let input_path_2 = task.input_path_2;
		let output_path = task.output_path;
		let op = task.operation || "multiply";
		let format = task.format || "float32";
		
		if (!fs.existsSync(input_path_1)) return null;
		
		let raster1 = await GeoPNG.loadNumberRasterImageAsync(input_path_1, { format: format });
		let total_pixels = raster1.data.length;
		let output_data = new Float32Array(total_pixels);
		
		if (input_path_2 && fs.existsSync(input_path_2)) {
			let raster2 = await GeoPNG.loadNumberRasterImageAsync(input_path_2, { format: format });
			let data1 = raster1.data;
			let data2 = raster2.data;
			
			if (op === "multiply") {
				for (let i = 0; i < total_pixels; i++) output_data[i] = data1[i]*data2[i];
			} else if (op === "divide") {
				for (let i = 0; i < total_pixels; i++) output_data[i] = (data2[i] !== 0) ? (data1[i]/data2[i]) : 0;
			} else if (op === "add") {
				for (let i = 0; i < total_pixels; i++) output_data[i] = data1[i] + data2[i];
			} else if (op === "subtract") {
				for (let i = 0; i < total_pixels; i++) output_data[i] = data1[i] - data2[i];
			}
		} else if (task.scalar !== undefined) {
			let scalar = task.scalar;
			let data1 = raster1.data;
			for (let i = 0; i < total_pixels; i++) output_data[i] = data1[i]*scalar;
		}
		
		await GeoPNG.saveNumberRasterImageAsync({
			data: output_data,
			file_path: output_path,
			format: format,
			height: raster1.height,
			width: raster1.width
		});
		
		return output_path;
	}
	
	//5. Regression raster prediction (OLS / Multinomial logit)
	if (task_type === "predict_raster") {
		return await Statistics.LearningFramework.predictRaster(
			task.output_file_path,
			task.model,
			task.options
		);
	}
	
	//6. Invoke specified stage method dynamically
	if (task_type === "invoke_method") {
		if (task.module_path) safeRequire(task.module_path);
		
		let target_class = global[task.class_name];
		if (!target_class || typeof target_class[task.method_name] !== "function")
			throw new Error(`Target class or method not found: ${task.class_name}.${task.method_name}`);
		
		let args = task.args || [];
		return await target_class[task.method_name](...args);
	}
	
	//7. Execute serialized handler function
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
	
	throw new Error(`Unknown GeoWorker task type: ${task_type}`);
};

//Message receiver
if (parentPort) {
	parentPort.on("message", async (task) => {
		if (!task) return;
		
		//Abort request
		if (task.type === "abort") {
			process.exit(0);
		}
		
		let task_id = task.task_id;
		try {
			let result = await handleTask(task);
			parentPort.postMessage({
				task_id: task_id,
				success: true,
				result: result
			});
		} catch (err) {
			parentPort.postMessage({
				task_id: task_id,
				success: false,
				error: err.message || String(err),
				stack: err.stack
			});
		}
	});
	
	//Ensure safe exit if parent port closes
	parentPort.on("close", () => {
		process.exit(0);
	});
}
