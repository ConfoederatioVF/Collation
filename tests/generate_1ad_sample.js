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
require(path.join(h3, "Eoscala_GDP/Eoscala_GDP.js"));
require(path.join(h3, "GDP_pc/GDP_pc.js"));
require(path.join(h3, "GDP_PPP_pc/GDP_PPP_pc.js"));

(async () => {
  console.log("=== Generating 1 AD (Year 0) and 100 AD Sample GDP Rasters ===");
  let start_time = Date.now();
  
  let options = {
    concurrency: 4,
    overwrite: true,
    skip_training: true,
    years: [0, 100]
  };
  
  console.log("\n[1/2] Processing GDP_PPP_pc and GDP_PPP for 1 AD and 100 AD...");
  await GDP_PPP_pc.processRasters(options);
  
  console.log("\n[2/2] Processing GDP_pc and GDP_nominal for 1 AD and 100 AD...");
  await GDP_pc.processRasters(options);
  
  //Also create explicit 1AD and 100AD copies in tests/ for direct convenience
  let out_test_dir = path.join(root_dir, "tests/sample_1AD_gdp");
  if (!fs.existsSync(out_test_dir)) fs.mkdirSync(out_test_dir, { recursive: true });
  
  let files_to_copy = [
    {
      src: path.join(GDP_PPP_pc.output_gdp_pc_folder, "GDP_PPP_pc_0.png"),
      dest: path.join(out_test_dir, "GDP_PPP_pc_1AD.png")
    },
    {
      src: path.join(GDP_PPP_pc.intermediate_gdp_scaled_to_national, "GDP_PPP_0.png"),
      dest: path.join(out_test_dir, "GDP_PPP_1AD.png")
    },
    {
      src: path.join(GDP_pc.output_gdp_pc_folder, "GDP_pc_0.png"),
      dest: path.join(out_test_dir, "GDP_pc_1AD.png")
    },
    {
      src: path.join(GDP_pc.intermediate_gdp_scaled_to_national, "GDP_0.png"),
      dest: path.join(out_test_dir, "GDP_nominal_1AD.png")
    },
    {
      src: path.join(GDP_PPP_pc.output_gdp_pc_folder, "GDP_PPP_pc_100.png"),
      dest: path.join(out_test_dir, "GDP_PPP_pc_100AD.png")
    },
    {
      src: path.join(GDP_PPP_pc.intermediate_gdp_scaled_to_national, "GDP_PPP_100.png"),
      dest: path.join(out_test_dir, "GDP_PPP_100AD.png")
    },
    {
      src: path.join(GDP_pc.output_gdp_pc_folder, "GDP_pc_100.png"),
      dest: path.join(out_test_dir, "GDP_pc_100AD.png")
    },
    {
      src: path.join(GDP_pc.intermediate_gdp_scaled_to_national, "GDP_100.png"),
      dest: path.join(out_test_dir, "GDP_nominal_100AD.png")
    }
  ];
  
  for (let i = 0; i < files_to_copy.length; i++) {
    let item = files_to_copy[i];
    if (fs.existsSync(item.src)) {
      fs.copyFileSync(item.src, item.dest);
      let stat = fs.statSync(item.dest);
      let sum = GeoPNG.getImageSum(item.dest, { format: "float32" });
      console.log(`- Created ${item.dest} (${stat.size} bytes, raster sum = ${sum})`);
    } else {
      console.error(`- Missing source: ${item.src}`);
    }
  }
  
  let elapsed = ((Date.now() - start_time) / 1000).toFixed(1);
  console.log(`\n=== 1 AD and 100 AD Rasters Generated Successfully in ${elapsed}s ===`);
  process.exit(0);
})();
