let fs = require("fs");
let path = require("path");
let pngjs = require("pngjs");

let hk = pngjs.PNG.sync.read(fs.readFileSync("histmap/3.data_transform/population_Substrata.outlier_removal/rasters_outliers/hongkong_-10000_1850.png"));
console.log("HK PNG meta:", { width: hk.width, height: hk.height, colorType: hk.colorType, bitDepth: hk.bitDepth, alpha: hk.alpha });

let ndi = JSON.parse(fs.readFileSync("histmap/2.data_cleaning/population_Stadester/stadester_national_development_index.json", "utf8"));
for (let yr of [-10000, -3000, 0, 1000, 1500, 1800, 1900, 1930, 1950, 2025]) {
  console.log(`NDI Yr ${yr} LIE:`, ndi[yr]?.LIE, "| CHE:", ndi[yr]?.CHE);
}
