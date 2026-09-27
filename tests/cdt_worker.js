let fs = require("fs");
let path = require("path");
let { parentPort } = require("worker_threads");

//Initialise worker environment and dependencies
let root_dir = path.resolve(__dirname, "..");
let pngjs = require(path.join(root_dir, "node_modules/pngjs"));

//Declare worker local instance variables
let height = 0;
let num_countries = 0;
let pixel_country = null;
let total_pixels = 0;
let width = 0;

//Listen for messages from master thread
parentPort.on("message", (arg0_message) => {
  //Convert from parameters
  let message = arg0_message;

  //Guard clauses
  if (!message || typeof message !== "object") return;

  //1. Initialisation phase
  if (message.type === "init") {
    height = message.height;
    num_countries = message.num_countries;
    pixel_country = new Int16Array(message.shared_pixel_country_buffer);
    total_pixels = message.width * message.height;
    width = message.width;

    parentPort.postMessage({ id: message.id, status: "ready" });
    return;
  }

  //2. Processing phase
  if (message.type === "aggregate_raster") {
    let file_path = message.file_path;
    let id = message.id;
    let is_logit = Boolean(message.is_logit);
    let pop_data = (message.shared_pop_buffer) ? new Float32Array(message.shared_pop_buffer) : null;

    if (!fs.existsSync(file_path)) {
      parentPort.postMessage({ error: `File not found: ${file_path}`, id: id });
      return;
    }

    try {
      let dv;
      let raw_bytes = fs.readFileSync(file_path);
      let parsed_png = pngjs.PNG.sync.read(raw_bytes);
      let sums = new Float64Array(num_countries);

      dv = new DataView(parsed_png.data.buffer, parsed_png.data.byteOffset, parsed_png.data.byteLength);

      //Fast tight aggregation loop
      if (is_logit && pop_data) {
        for (let i = 0; i < total_pixels; i++) {
          let cid = pixel_country[i];
          if (cid > 0) {
            let prob = dv.getFloat32(i * 4, false);
            if (prob > 0) sums[cid] += prob * pop_data[i];
          }
        }
      } else {
        for (let i = 0; i < total_pixels; i++) {
          let cid = pixel_country[i];
          if (cid > 0) {
            let val = dv.getFloat32(i * 4, false);
            if (val > 0) sums[cid] += val;
          }
        }
      }

      //Post result buffer back with zero-copy transfer
      parentPort.postMessage({ id: id, sums: sums.buffer }, [sums.buffer]);
    } catch (e) {
      parentPort.postMessage({ error: e.message, id: id });
    }
  }
});
