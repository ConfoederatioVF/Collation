//scratch/test_benchmark_stadester.js
let assert = require("assert");

//Set up environment
global.h1 = "d:/Project 1509 - SVEA/histmap/1.data_raw";
global.h2 = "d:/Project 1509 - SVEA/histmap/2.data_cleaning";
global.h3 = "d:/Project 1509 - SVEA/histmap/3.data_transform";

require("../histmap/2.data_cleaning/population_Stadester/config/stadester_config.js");
require("../histmap/2.data_cleaning/population_Stadester/stadester_uud.js");
require("../histmap/2.data_cleaning/population_Stadester/stadester_density.js");
require("../histmap/2.data_cleaning/population_Stadester/stadester_rasters.js");

console.log("=== 1. Benchmarking calculateCitiesCentreDensities ===");
//Synthesize 10,000 cities with realistic density timelines
let test_stadester_obj = {};
for (let i = 0; i < 10000; i++) {
  let key = `city_${i}`;
  let density = {};
  let start_yr = 1800 + (i % 50);
  let base_d = 1000 + (i % 20000);
  for (let yr = start_yr; yr <= 2000; yr += 5) {
    density[yr] = base_d * (1 + (yr - start_yr) * 0.005);
  }
  test_stadester_obj[key] = {
    key: key,
    density: density
  };
}

let t0 = Date.now();
population_Stadester_density.calculateCitiesCentreDensities(test_stadester_obj);
let t1 = Date.now();
console.log(`[PERF] 10,000 cities x 201 years completed in ${t1 - t0} ms!`);

//Verify city_0 centre density results
assert(test_stadester_obj.city_0.centre_density[1800] !== undefined, "centre_density[1800] should exist");
assert(test_stadester_obj.city_0.centre_density[2000] !== undefined, "centre_density[2000] should exist");
console.log(`[VERIFY] city_0 centre_density: 1800 -> ${test_stadester_obj.city_0.centre_density[1800].toFixed(2)}, 2000 -> ${test_stadester_obj.city_0.centre_density[2000].toFixed(2)}`);

console.log("\n=== 2. Benchmarking getPixelFractionInRing Fast Path & Equivalence ===");
let center = [48.8566, 2.3522];
let test_pixels = [];
for (let i = 0; i < 50000; i++) {
  let d_lat = (Math.random() - 0.5) * 0.5;
  let d_lng = (Math.random() - 0.5) * 0.5;
  test_pixels.push([center[0] + d_lat, center[1] + d_lng]);
}

let t2 = Date.now();
let total_frac = 0;
for (let i = 0; i < test_pixels.length; i++) {
  total_frac += population_Stadester_density.getPixelFractionInRing(center, test_pixels[i], 5, 15);
}
let t3 = Date.now();
console.log(`[PERF] 50,000 ring fraction evaluations completed in ${t3 - t2} ms (avg ${((t3 - t2)/50000).toFixed(4)} ms/call)!`);

//Equivalence check: compare fast path against brute-force 10x10 sampling
function bruteForceFraction(city_coords, pixel_coords, inner_radius, outer_radius) {
  let cfg = global.population_Stadester_config;
  let half = cfg.pixel_deg/2;
  let inside = 0;
  let subsamples = 10;
  let total = subsamples*subsamples;
  for (let i = 0; i < subsamples; i++) {
    for (let x = 0; x < subsamples; x++) {
      let d_lat = (i + 0.5)/subsamples*cfg.pixel_deg - half;
      let d_lng = (x + 0.5)/subsamples*cfg.pixel_deg - half;
      let d = population_Stadester_density.equirectangularDistance(city_coords, [pixel_coords[0] + d_lat, pixel_coords[1] + d_lng]);
      if (d >= inner_radius && d < outer_radius) inside++;
    }
  }
  return inside/total;
}

let max_diff = 0;
for (let i = 0; i < 5000; i++) {
  let opt_val = population_Stadester_density.getPixelFractionInRing(center, test_pixels[i], 5, 15);
  let brute_val = bruteForceFraction(center, test_pixels[i], 5, 15);
  let diff = Math.abs(opt_val - brute_val);
  if (diff > max_diff) max_diff = diff;
}
assert(max_diff < 1e-9, `Maximum difference must be 0, got ${max_diff}`);
console.log(`[VERIFY] Mathematical equivalence verified across 5,000 points! Max diff = ${max_diff}`);

console.log("\n=== 3. Benchmarking Float32Array Flat Indexing in Base Raster ===");
let t4 = Date.now();
let flat_array = new Float32Array(4320 * 2160);
for (let i = 0; i < 50000; i++) {
  let idx = (i * 186) % (4320 * 2160);
  flat_array[idx] += 123.45;
}
let t5 = Date.now();
console.log(`[PERF] 50,000 direct Float32Array accumulations completed in ${t5 - t4} ms!`);

console.log("\nALL STADESTER PERFORMANCE BENCHMARKS PASSED SUCCESSFULLY!");
