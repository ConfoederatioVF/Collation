let fs = require("fs");
let path = require("path");

global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");
global.mathjs = require("mathjs");
global.cubic_spline = require("cubic-spline");
global.JSON5 = require("json5");
let root_dir = path.resolve(".");

let loadDirectory = function (rel_dir) {
  let full_dir = path.join(root_dir, rel_dir);
  if (fs.existsSync(full_dir)) {
    let files = fs.readdirSync(full_dir).filter((f) => f.endsWith(".js") && !f.includes("worker"));
    for (let i = 0; i < files.length; i++) require(path.join(full_dir, files[i]));
  }
};

loadDirectory("UF/js/number");
loadDirectory("UF/js/string");
loadDirectory("UF/js/colour");
loadDirectory("UF/js/file");
loadDirectory("UF/js/object");
loadDirectory("UF/js/array");
loadDirectory("UF/js/blacktraffic");
loadDirectory("UF/js/statistics");
loadDirectory("UF/js/geospatiale/coords");
loadDirectory("UF/js/geospatiale/operations");
loadDirectory("UF/js/geospatiale/files");
loadDirectory("UF/js/geospatiale/files/png");

global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");
global.h4 = path.join(root_dir, "histmap/4.data_exports/");
global.h5 = path.join(root_dir, "histmap/5.data_visualisation/");

require(path.join(h2, "metadata_HYDE/metadata_HYDE.js"));
require(path.join(h2, "landuse_HYDE/landuse_HYDE.js"));
require(path.join(h2, "population_Global/population_Global.js"));

(async () => {
  try {
    console.log("=== Running landuse_HYDE.processRasters (Steps B, C, D) ===");
    let t0 = Date.now();
    await landuse_HYDE.processRasters({ exclude: ["A"] });
    let duration = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`landuse_HYDE processRasters completed in ${duration}s!`);
  } catch (err) {
    console.error("Error running landuse_HYDE:", err);
    process.exit(1);
  }
})();
