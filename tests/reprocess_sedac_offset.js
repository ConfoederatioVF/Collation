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

(async () => {
  console.log("1. Checking alignment metrics for 1990 raster (offset_y = 0)...");
  let land_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, { format: "float32" });
  let pop_raster = GeoPNG.loadNumberRasterImage(`${population_Stadester.input_popc_folder}/stadester_population_1990.png`, { format: "float32" });
  let ppp_1990 = GeoPNG.loadNumberRasterImage(`${GDP_PPP_SEDAC.bf}/GDP_PPP_1990.png`, { format: "float32" });

  let on_land = 0;
  let in_ocean = 0;
  let with_pop = 0;

  for (let i = 0; i < ppp_1990.data.length; i++) {
    let val = ppp_1990.data[i];
    if (val > 0) {
      let is_land = land_raster.data[i] > 0;
      let has_pop = pop_raster ? (pop_raster.data[i] > 0) : false;
      if (is_land) on_land++;
      else in_ocean++;
      if (has_pop) with_pop++;
    }
  }

  console.log(`Alignment check results:`);
  console.log(`  on_land:  ${on_land.toLocaleString()}`);
  console.log(`  in_ocean: ${in_ocean.toLocaleString()}`);
  console.log(`  with_pop: ${with_pop.toLocaleString()}`);

  console.log("\n2. Normalising SEDAC rasters to nominal (GDP_nominal_SEDAC)...");
  let t1 = Date.now();
  await GDP_nominal_SEDAC.A_normaliseSEDACRastersToNominal();
  console.log(`GDP_nominal_SEDAC normalisation completed in ${((Date.now() - t1)/1000).toFixed(1)}s.`);

  console.log("\n3. Retraining GDP_PPP_SEDAC OLS models on unshifted rasters...");
  let t2 = Date.now();
  await GDP_PPP_SEDAC.B_trainGDP_PPPModels({ concurrency: 8 });
  await GDP_PPP_SEDAC.C_geomeanGDP_PPPModel("OLS_GDP_PPP_");
  console.log(`GDP_PPP_SEDAC OLS models completed in ${((Date.now() - t2)/1000).toFixed(1)}s.`);

  console.log("\n4. Retraining GDP_nominal_SEDAC OLS models on unshifted rasters...");
  let t3 = Date.now();
  await GDP_nominal_SEDAC.B_trainGDPModels({ concurrency: 8 });
  await GDP_nominal_SEDAC.C_geomeanGDPModel("OLS_GDP_");
  console.log(`GDP_nominal_SEDAC OLS models completed in ${((Date.now() - t3)/1000).toFixed(1)}s.`);

  console.log("\nAll SEDAC PPP and nominal rasters and OLS models successfully synchronized!");
})();
