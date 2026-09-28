let fs = require("fs");
let path = require("path");
let { parentPort } = require("worker_threads");

//Bootstrap worker dependencies
let root_dir = path.resolve(__dirname, "..");
let pngjs = require(path.join(root_dir, "node_modules/pngjs"));

//Declare worker local instance variables
let height = 0;
let num_regions = 0;
let pixel_region = null;
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
    num_regions = message.num_regions;
    pixel_region = new Uint16Array(message.shared_pixel_region_buffer);
    total_pixels = message.width * message.height;
    width = message.width;

    parentPort.postMessage({ id: message.id, status: "ready" });
    return;
  }

  //2. Processing phase
  if (message.type === "aggregate_raster") {
    let file_path = message.file_path;
    let id = message.id;

    if (!fs.existsSync(file_path)) {
      parentPort.postMessage({ error: `File not found: ${file_path}`, id: id });
      return;
    }

    try {
      let dv;
      let raw_bytes = fs.readFileSync(file_path);
      let parsed_png = pngjs.PNG.sync.read(raw_bytes);
      let sums = new Float64Array(num_regions + 1);

      dv = new DataView(parsed_png.data.buffer, parsed_png.data.byteOffset, parsed_png.data.byteLength);

      //Fast tight aggregation loop across all country and state bins
      for (let i = 0; i < total_pixels; i++) {
        let cid = pixel_region[i];
        if (cid > 0) {
          let val = dv.getFloat32(i * 4, false);
          if (val > 0) sums[cid] += val;
        }
      }

      //Post result buffer back with zero-copy transfer
      parentPort.postMessage({ id: id, sums: sums.buffer }, [sums.buffer]);
    } catch (e) {
      parentPort.postMessage({ error: e.message, id: id });
    }
  }
});
