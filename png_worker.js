//Forwarding wrapper for GeoPNG worker in root directory
let fs = require("fs");
let path = require("path");

let target_path = path.join(__dirname, "UF/js/geospatiale/files/png/png_worker.js");

if (fs.existsSync(target_path)) {
	require(target_path);
} else {
	console.error("Could not find UF/js/geospatiale/files/png/png_worker.js from", __dirname);
}
