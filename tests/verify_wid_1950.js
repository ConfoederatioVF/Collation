const fs = require("fs");
const path = require("path");

global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");
let root_dir = path.resolve(".");

let loadDirectory = function (rel_dir) {
	let full_dir = path.join(root_dir, rel_dir);
	if (fs.existsSync(full_dir)) {
		let files = fs.readdirSync(full_dir).filter(f => f.endsWith(".js") && !f.includes("worker"));
		for (let i = 0; i < files.length; i++) require(path.join(full_dir, files[i]));
	}
};

loadDirectory("UF/js/number");
loadDirectory("UF/js/string");
loadDirectory("UF/js/colour");
loadDirectory("UF/js/file");
loadDirectory("UF/js/object");
loadDirectory("UF/js/array");
loadDirectory("UF/js/statistics");
loadDirectory("UF/js/geospatiale/coords");
loadDirectory("UF/js/geospatiale/operations");
loadDirectory("UF/js/geospatiale/files");
loadDirectory("UF/js/geospatiale/files/png");

global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");

let samples = [
	{ name: "Papua New Guinea (PNG)", lat: -6.3, lon: 143.9 },
	{ name: "Australia (AUS - Sydney)", lat: -33.86, lon: 151.2 },
	{ name: "New Zealand (NZL)", lat: -41.3, lon: 174.8 },
	{ name: "Fiji (FJI)", lat: -16.04, lon: 179.96 },
	{ name: "United States (USA)", lat: 38.9, lon: -77.0 },
	{ name: "Great Britain (GBR)", lat: 51.5, lon: -0.1 },
	{ name: "South Africa (ZAF)", lat: -25.7, lon: 28.2 },
	{ name: "Albania (ALB)", lat: 41.3, lon: 19.8 }
];

let variables = ["net_income", "net_wealth", "disposable_income", "discretionary_income"];

console.log("=========================================================================================");
console.log("                 1950 AD WEALTH & INCOME RASTER VERIFICATION");
console.log("=========================================================================================");

for (let i = 0; i < variables.length; i++) {
	let v = variables[i];
	let wid_path = path.join(h2, "wealth_income_WID", v, `${v}_1950.png`);
	let final_path = path.join(h3, "wealth_income", `1.${v}`, `${v}_1950.png`);
	
	let wid_img = fs.existsSync(wid_path) ? GeoPNG.loadNumberRasterImage(wid_path, { format: "float32" }) : null;
	let final_img = fs.existsSync(final_path) ? GeoPNG.loadNumberRasterImage(final_path, { format: "float32" }) : null;
	
	console.log(`\nVariable: ${v.toUpperCase()} (1950 AD)`);
	console.log("-----------------------------------------------------------------------------------------");
	console.log(`  ${"Region / Nation".padEnd(28)} | ${"WID Target (h2)".padStart(18)} | ${"Final Layer (h3)".padStart(18)}`);
	console.log("-----------------------------------------------------------------------------------------");
	
	for (let s = 0; s < samples.length; s++) {
		let loc = samples[s];
		let px = Math.floor((loc.lon + 180) / 360 * 4320);
		let py = Math.floor((90 - loc.lat) / 180 * 2160);
		let idx = py * 4320 + px;
		
		let wid_val = wid_img ? wid_img.data[idx] : 0;
		let final_val = final_img ? final_img.data[idx] : 0;
		
		let wid_str = (wid_val > 0) ? `${wid_val.toFixed(2)} $` : "0,00 $";
		let final_str = (final_val > 0) ? `${final_val.toFixed(2)} $` : "0,00 $";
		
		console.log(`  ${loc.name.padEnd(28)} | ${wid_str.padStart(18)} | ${final_str.padStart(18)}`);
	}
}

console.log("\n=========================================================================================");
console.log("Verification finished.");
