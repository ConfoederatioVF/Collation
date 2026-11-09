global.fs = require("fs");
global.path = require("path");
global.JSON5 = require("json5");
global.pngjs = require("pngjs");
global.cubic_spline = require("cubic-spline");
global.h1 = "./histmap/1.data_raw/";
global.h2 = "./histmap/2.data_cleaning/";
global.h3 = "./histmap/3.data_transform/";
global.h4 = "./histmap/4.data_exports/";
global.h5 = "./histmap/5.data_visualisation/";

require("../UF/js/file/file_csv.js");
require("../histmap/2.data_cleaning/landuse_HYDE/landuse_HYDE.js");
require("../histmap/2.data_cleaning/population_Stadester/config/stadester_config.js");
require("../histmap/2.data_cleaning/population_Stadester/stadester_uud_sources.js");
require("../histmap/2.data_cleaning/population_Stadester/stadester_uud.js");
require("../histmap/2.data_cleaning/population_Stadester/stadester_density.js");
require("../histmap/2.data_cleaning/population_Stadester/stadester_rasters.js");
require("../histmap/2.data_cleaning/population_Stadester/population_Stadester.js");

console.log("=== Running Step A: A_initialiseUUD ===");
let uud = population_Stadester.A_initialiseUUD();

console.log("=== Running Step B: B_interpolateUUD ===");
uud = population_Stadester.B_interpolateUUD({ uud_obj: uud });

console.log("=== Verifying Angarsk, Gorelyi Les, and all polaris_russia entries ===");
console.log("Angarsk-Russia:", JSON.stringify(uud["Angarsk-Russia"] ? uud["Angarsk-Russia"].population : null));
console.log("Gorelyi Les-Russia:", JSON.stringify(uud["Gorelyi Les-Russia"] ? uud["Gorelyi Les-Russia"].population : null));

let anomalies = [];
for (const [k, v] of Object.entries(uud)) {
  if (v.type !== "polaris_russia") continue;
  const yrs = Object.keys(v.population || {}).map(Number).filter(n => !isNaN(n) && v.population[n] > 0).sort((a, b) => a - b);
  if (yrs.length === 0) continue;
  const minY = yrs[0], maxY = yrs[yrs.length - 1];
  const fYr = parseInt(v["found.yr"], 10);
  if (Number.isFinite(fYr) && minY < fYr - 200) {
    anomalies.push({ k, reason: `minY=${minY} < found.yr=${fYr}`, minY, maxY });
  }
  if (minY < 0 && maxY >= 1500 && k !== "Derbent-Russia" && k !== "Taman-Russia") {
    anomalies.push({ k, reason: `BC to modern span (${minY}..${maxY})`, minY, maxY });
  }
}
console.log("Anomalies found:", anomalies.length);
for (const a of anomalies) console.log(" ", a);

console.log("=== Running Step C: C_processUUDToStadester ===");
let stadester = population_Stadester.C_processUUDToStadester({ uud_obj: uud });

console.log("=== Running Step D: D_processCitiesAreas ===");
stadester = population_Stadester.D_processCitiesAreas({ stadester_obj: stadester });

console.log("=== Running Step E: E_cacheRadialBuffers ===");
stadester = population_Stadester.E_cacheRadialBuffers({ stadester_obj: stadester });

console.log("=== Done rebuilding all Stadestér city JSON caches ===");
