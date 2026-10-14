let fs = require("fs");
let path = require("path");

global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");
global.mathjs = require("mathjs");
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
require(path.join(h2, "admin_modern/admin_modern.js"));
require(path.join(h3, "population_Stadester.transform/population_Stadester_transform.js"));
require(path.join(h2, "population_Stadester/population_Stadester.js"));
require(path.join(h2, "GDP_PPP_SEDAC/GDP_PPP_SEDAC.js"));
require(path.join(h2, "GDP_nominal_SEDAC/GDP_nominal_SEDAC.js"));
require(path.join(h2, "GDP_nominal/GDP_nominal.js"));
require(path.join(h3, "GDP_PPP/GDP_PPP.js"));
require(path.join(h3, "GDP_pc/GDP_pc.js"));
require(path.join(h3, "GDP_PPP_pc/GDP_PPP_pc.js"));
require(path.join(h3, "GDP_Eoscala.transform/GDP_Eoscala_transform.js"));
require(path.join(h3, "NWM/NWM.js"));

(async () => {
  let args = process.argv.slice(2);
  let do_nominal = !args.includes("--ppp-only");
  let do_ppp = !args.includes("--nominal-only");
  let do_deltas = args.includes("--deltas") || args.includes("--all");
  let skip_training = args.includes("--skip-training") || args.includes("--use-existing-models");
  let concurrency = 8;

  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith("--concurrency=")) {
      concurrency = parseInt(args[i].split("=")[1]) || 8;
    }
  }

  console.log("================================================================================");
  console.log("REPROCESSING GDP RASTERS (NOMINAL & PPP)");
  console.log(`Modes: Nominal=${do_nominal}, PPP=${do_ppp}, Deltas=${do_deltas}`);
  console.log(`Concurrency: ${concurrency} parallel workers | Skip Training: ${skip_training}`);
  console.log("================================================================================\n");

  let start_time = Date.now();
  let tasks = [];

  let options = {
    concurrency: concurrency,
    overwrite: true,
    skip_training: skip_training
  };

  if (do_nominal && global.GDP_pc) {
    console.log("[GDP_pc] Queuing Nominal GDP per capita processing (Steps A - I)...");
    tasks.push(GDP_pc.processRasters(options));
  }

  if (do_ppp && global.GDP_PPP_pc) {
    console.log("[GDP_PPP_pc] Queuing PPP GDP per capita processing (Steps A - I)...");
    tasks.push(GDP_PPP_pc.processRasters(options));
  }

  await Promise.all(tasks);
  console.log("\n[GDP] Completed core raster processing.");

  if (do_deltas && global.GDP_Eoscala_transform) {
    console.log("\n[GDP_Eoscala_transform] Generating spatiotemporal delta rasters...");
    await GDP_Eoscala_transform.processRasters({ overwrite: true });
    console.log("[GDP_Eoscala_transform] Finished delta rasters.");
  }

  let elapsed_sec = ((Date.now() - start_time) / 1000).toFixed(1);
  console.log(`\n================================================================================`);
  console.log(`ALL GDP RASTERS SUCCESSFULLY REPROCESSED IN ${elapsed_sec}s`);
  console.log(`================================================================================`);
})();
