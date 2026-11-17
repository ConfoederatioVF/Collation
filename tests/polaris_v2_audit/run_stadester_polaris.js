//Import modules
global.fs = require("fs");
global.JSON5 = require("json5");
global.path = require("path");
global.pngjs = require("pngjs");
try { global.cubic_spline = require("cubic-spline"); } catch (e) {}

//Configure SVEA base paths
global.h1 = "./histmap/1.data_raw";
global.h2 = "./histmap/2.data_cleaning";
global.h3 = "./histmap/3.data_transform";
global.h5 = "./histmap/5.data_visualisation/";

//Load required UF utility libraries into global namespace
{
  let uf_dirs = ["boolean", "number", "string", "array", "object", "file"];
  for (let i = 0; i < uf_dirs.length; i++) {
    let dir_path = path.resolve("./UF/js", uf_dirs[i]);
    if (!fs.existsSync(dir_path)) continue;
    let files = fs.readdirSync(dir_path).filter((f) => f.endsWith(".js")).sort();
    for (let x = 0; x < files.length; x++)
      require(path.join(dir_path, files[x]));
  }
}

//Load population_Stadester module
require(path.resolve("./histmap/2.data_cleaning/population_Stadester/population_Stadester.js"));

//Execute sequential Stadestér 2.0 city pipeline steps A..E
{
  let uud_obj = population_Stadester.A_initialiseUUD();
  uud_obj = population_Stadester.B_interpolateUUD({ uud_obj: uud_obj });
  let stadester_obj = population_Stadester.C_processUUDToStadester({ uud_obj: uud_obj });
  stadester_obj = population_Stadester.D_processCitiesAreas({ stadester_obj: stadester_obj });
  population_Stadester.E_cacheRadialBuffers({ stadester_obj: stadester_obj });
  console.log("Stadestér 2.0 pipeline steps A..E completed.");
}
