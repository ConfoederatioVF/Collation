//Import modules
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");

//Initialise globals expected by population_Stadester.js
{
  global.fs = fs;
  global.JSON5 = JSON5;
  global.path = path;
  global.h1 = "./histmap/1.data_raw";
  global.h2 = "./histmap/2.data_cleaning";
  global.h3 = "./histmap/3.data_transform";
  global.h5 = "./histmap/5.data_visualisation/";

  if (fs.existsSync("./UF/js/file/file_basic.js")) require("../UF/js/file/file_basic.js");
  if (fs.existsSync("./UF/js/file/file_read.js")) require("../UF/js/file/file_read.js");
  if (fs.existsSync("./UF/js/file/file_csv.js")) require("../UF/js/file/file_csv.js");
  require("../histmap/2.data_cleaning/population_Stadester/population_Stadester.js");

  let run = async function () {
    console.log("[run_stadester_ae] Starting Stadestér 2.0 Steps A-E (no rasters F-J)...");
    await global.population_Stadester.processRasters({
      exclude: ["F", "G", "H", "I", "J"],
      overwrite: true
    });

    let src_dir = path.resolve("./histmap/5.data_visualisation/stadester/stadester_2.0");
    let dv_dir = path.resolve("F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0");
    if (fs.existsSync(src_dir) && fs.existsSync(dv_dir)) {
      let files = fs.readdirSync(src_dir);
      let synced = 0;
      for (let i = 0; i < files.length; i++) {
        let f = files[i];
        if (f === "stadester_manifest.json" || /^\d{2}_[a-z0-9_]+\.json$/i.test(f)) {
          fs.copyFileSync(path.join(src_dir, f), path.join(dv_dir, f));
          synced++;
        }
      }
      // Remove any stale regional shard files in Dataview not present in src_dir
      let src_set = new Set(files);
      let dv_files = fs.readdirSync(dv_dir);
      for (let i = 0; i < dv_files.length; i++) {
        let f = dv_files[i];
        if (/^\d{2}_[a-z0-9_]+\.json$/i.test(f) && !src_set.has(f)) {
          try { fs.unlinkSync(path.join(dv_dir, f)); } catch (e) {}
        }
      }
      console.log(`[run_stadester_ae] Synced ${synced} Stadestér 2.0 shard/manifest file(s) to Dataview.`);
    }
    console.log("[run_stadester_ae] Complete.");
  };

  run().catch(function (arg0_err) {
    console.error("[run_stadester_ae] Failed:", arg0_err);
    process.exit(1);
  });
}
