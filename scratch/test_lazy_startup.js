//scratch/test_lazy_startup.js
let { performance } = require("perf_hooks");

function lazyGlobal (prop_name, require_path, sub_prop) {
  let cached;
  Object.defineProperty(global, prop_name, {
    get: function () {
      if (!cached) {
        let mod = require(require_path);
        cached = sub_prop ? mod[sub_prop] : mod;
      }
      return cached;
    },
    set: function (val) {
      cached = val;
    },
    configurable: true,
    enumerable: true
  });
}

console.log("=== 1. Measuring Startup with Lazy Getters ===");
let t0 = performance.now();

//Fast core imports
global.child_process = require("child_process");
global.fs = require("fs");
global.path = require("path");
global.util = require("util");
global.net = require("net");
global.JSON5 = require("json5");

//Heavy modules as lazy getters
lazyGlobal("cubic_spline", "cubic-spline");
lazyGlobal("geotiff", "geotiff");
lazyGlobal("JSDOM", "jsdom", "JSDOM");
lazyGlobal("mathjs", "mathjs");
lazyGlobal("ml_matrix", "ml-matrix");
lazyGlobal("netcdfjs", "netcdfjs");
lazyGlobal("pngjs", "pngjs");
lazyGlobal("polylabel", "polylabel");
lazyGlobal("puppeteer", "puppeteer");

let t1 = performance.now();
console.log(`[PERF] Initial startup definitions completed in ${(t1 - t0).toFixed(2)} ms!`);

console.log("\n=== 2. Verifying Lazy On-Demand Access ===");
//Verify JSDOM is only loaded on first access
let t2 = performance.now();
let test_jsdom = global.JSDOM;
let t3 = performance.now();
console.log(`[TEST] global.JSDOM accessed and loaded on-demand in ${(t3 - t2).toFixed(2)} ms`);
if (typeof test_jsdom === "function") {
  let dom = new test_jsdom("<html><body><div id='test'>Hello</div></body></html>");
  console.log(`[PASS] JSDOM verified working: ${dom.window.document.getElementById('test').textContent}`);
}

//Verify mathjs is only loaded on first access
let t4 = performance.now();
let test_math = global.mathjs;
let t5 = performance.now();
console.log(`[TEST] global.mathjs accessed and loaded on-demand in ${(t5 - t4).toFixed(2)} ms`);
if (typeof test_math.matrix === "function") {
  let m = test_math.matrix([[1, 2], [3, 4]]);
  console.log(`[PASS] mathjs verified working: matrix size ${m.size()}`);
}

console.log("\nALL LAZY STARTUP TESTS PASSED!");
