{
	if (!global.GeoPNG) global.GeoPNG = {};
	
  /**
   * Builds a binary Uint8Array mask of HYDE urban pixels by buffering modern built-up areas (uopp > threshold)
   * and optionally unioning historical HYDE urban population pixels (urbc > 0).
   * @alias GeoPNG.getModernUrbanMask
   *
   * @param {Object|string} arg0_uopp_raster - Loaded GeoPNG number raster or path to uopp_2023AD.png.
   * @param {Object} [arg1_options]
   *  @param {number} [arg1_options.buffer_radius=1] - Moore neighbourhood dilation radius around uopp > threshold pixels.
   *  @param {number} [arg1_options.height=2160] - Raster height.
   *  @param {number} [arg1_options.threshold=10.0] - Minimum built-up area (km^2) to classify as modern urban core.
   *  @param {Object|string} [arg1_options.urbc_raster] - Optional historical urbc_<yr>.png raster or path to union (urbc > 0).
   *  @param {number} [arg1_options.width=4320] - Raster width.
   *
   * @returns {Uint8Array}
   */
  GeoPNG.getModernUrbanMask = function (arg0_uopp_raster, arg1_options) {
    //Convert from parameters
    let uopp_input = arg0_uopp_raster;
    let options = (arg1_options) ? arg1_options : {};

    //Initialise options
    if (!GeoPNG._modern_urban_mask_cache) GeoPNG._modern_urban_mask_cache = new Map();

    //Declare local instance variables
    let base_mask = null;
    let buffer_radius = (options.buffer_radius !== undefined) ? parseInt(options.buffer_radius) : 1;
    let cache_key = (typeof uopp_input === "string") ? `${uopp_input}_${options.threshold ?? 10.0}_${buffer_radius}` : null;
    let height = (options.height !== undefined) ? options.height : 2160;
    let threshold = (options.threshold !== undefined) ? options.threshold : 10.0;
    let total_pixels = height*4320;
    let uopp_raster = null;
    let urban_mask = null;
    let urbc_raster = null;
    let width = (options.width !== undefined) ? options.width : 4320;

    total_pixels = width*height;

    //1. Retrieve or compute cached base modern uopp buffered mask
    if (cache_key && GeoPNG._modern_urban_mask_cache.has(cache_key)) {
      base_mask = GeoPNG._modern_urban_mask_cache.get(cache_key);
    } else {
      base_mask = new Uint8Array(total_pixels);
      if (uopp_input) {
        uopp_raster = (typeof uopp_input === "string") ?
          ((fs.existsSync(uopp_input)) ? GeoPNG.loadNumberRasterImage(uopp_input, { format: "float32" }) : null) : uopp_input;
      }

      if (uopp_raster && uopp_raster.data) {
        height = uopp_raster.height;
        width = uopp_raster.width;
        total_pixels = width*height;
        if (base_mask.length !== total_pixels) base_mask = new Uint8Array(total_pixels);

        for (let i = 0; i < height; i++)
          for (let x = 0; x < width; x++)
            if (uopp_raster.data[i*width + x] > threshold)
              for (let y = -buffer_radius; y <= buffer_radius; y++) {
                let ny = i + y;
                if (ny >= 0 && ny < height)
                  for (let z = -buffer_radius; z <= buffer_radius; z++)
                    base_mask[ny*width + ((x + z + width) % width)] = 1;
              }
      }

      if (cache_key) GeoPNG._modern_urban_mask_cache.set(cache_key, base_mask);
    }

    //2. Optionally union historical HYDE urbc > 0 pixels on a fresh copy
    if (options.urbc_raster) {
      urbc_raster = (typeof options.urbc_raster === "string") ?
        ((fs.existsSync(options.urbc_raster)) ? GeoPNG.loadNumberRasterImage(options.urbc_raster, { format: "float32" }) : null) : options.urbc_raster;
    }

    if (urbc_raster && urbc_raster.data) {
      urban_mask = new Uint8Array(base_mask);
      let limit = Math.min(urban_mask.length, urbc_raster.data.length);
      for (let i = 0; i < limit; i++)
        if (urbc_raster.data[i] > 0) urban_mask[i] = 1;
    } else {
      urban_mask = base_mask;
    }

    //Return statement
    return urban_mask;
  };


	/**
	 * Returns the centroid of a given polygon, given its pixels.
	 * 
	 * @param {Array.<number[]>} arg0_pixels
	 * 
	 * @returns {number[]|null}
	 */
	GeoPNG.getPolygonCentroid = function (arg0_pixels) {
		//Convert from parameters
		let pixels = arg0_pixels;
		
		if (!pixels.length) return null; //Internal guard clause if pixels are not provided
		
		//Declare local instance variables
		let sum_x = 0;
		let sum_y = 0;
		
		//Iterate over all pixels
		for (let [x, y] of pixels) {
			sum_x += x;
			sum_y += y;
		}
		
		//Return statement
		return [sum_x/pixels.length, sum_y/pixels.length];
	};
	
	/**
	 * Returns the average (assuming a number-formatted GeoPNG) of the Moore neighbourhood surrounding a pixel.
	 * 
	 * @param {number[]} arg0_geopng_array
	 * @param {number} arg1_x
	 * @param {number} arg2_y
	 * @param {number} arg3_height
	 * @param {number} arg4_width
	 * 
	 * @returns {number}
	 */
	GeoPNG.getRasterNeighbourAverage = function (arg0_geopng_array, arg1_x, arg2_y, arg3_height, arg4_width) {
		//Convert from parameters
		let geopng_array = arg0_geopng_array;
		let local_x = arg1_x;
		let local_y = arg2_y;
		let height = arg3_height;
		let width = arg4_width;
		
		//Declare local instance variables
		let count = 0;
		let sum = 0;
		
		for (let i = -1; i <= 1; i++)
			for (let x = -1; x <= 1; x++) {
				if (i === 0 && x === 0) continue;
				
				let neighbour_x = local_x + i;
				let neighbour_y = local_y + x;
				
				if (neighbour_x >= 0 && neighbour_x < height && neighbour_y >= 0 && neighbour_y < width) {
					let local_index = neighbour_x*width + neighbour_y;
					let local_value = geopng_array[local_index];
					
					if (!isNaN(local_value)) {
						sum += local_value;
						count++;
					}
				}
			}
		
		//Return statement
		return (count > 0) ? sum/count : NaN;
	};


  /**
   * Inpaints masked urban pixels via inverse-distance weighted boundary interpolation over unmasked habitable land neighbours,
   * preserving uninhabited zero-population territories without leaking fallback values.
   * @alias GeoPNG.inpaintUrbanMask
   *
   * @param {Float32Array|Float64Array} arg0_raster_data - Mutable global raster buffer to inpaint.
   * @param {Uint8Array} arg1_urban_mask - Binary mask of urban pixels (1 = masked, 0 = unmasked).
   * @param {Object} [arg2_options]
   *  @param {Float32Array|Float64Array} [arg2_options.fallback_data] - Fallback raster data (e.g. KK10LUH2) when wide neighbourhood is fully masked.
   *  @param {number} [arg2_options.height=2160] - Raster height.
   *  @param {Float32Array|Float64Array|Int32Array} [arg2_options.land_area] - Habitable land area buffer (> 0 for land).
   *  @param {number} [arg2_options.radius=3] - Primary IDW search radius in pixels.
   *  @param {number} [arg2_options.width=4320] - Raster width.
   *
   * @returns {Float32Array|Float64Array}
   */
  GeoPNG.inpaintUrbanMask = function (arg0_raster_data, arg1_urban_mask, arg2_options) {
    //Convert from parameters
    let raster_data = arg0_raster_data;
    let urban_mask = arg1_urban_mask;
    let options = (arg2_options) ? arg2_options : {};

    //Declare local instance variables
    let fallback_data = options.fallback_data;
    let height = (options.height !== undefined) ? options.height : 2160;
    let land_area = options.land_area;
    let masked_indices = [];
    let radius = (options.radius !== undefined) ? options.radius : 3;
    let temp_data = null;
    let total_pixels = 0;
    let weights = [];
    let width = (options.width !== undefined) ? options.width : 4320;

    //Guard clauses
    if (!raster_data || !urban_mask) return raster_data;

    total_pixels = Math.min(raster_data.length, width*height);

    //Identify all masked pixels on habitable land
    for (let i = 0; i < total_pixels; i++)
      if (urban_mask[i] === 1 && (!land_area || land_area[i] > 0)) masked_indices.push(i);
    if (masked_indices.length === 0) return raster_data;

    for (let i = -radius; i <= radius; i++)
      for (let x = -radius; x <= radius; x++) {
        let d2 = x*x + i*i;
        if (d2 > 0 && d2 <= radius*radius + 1)
          weights.push({ rx: x, ry: i, w: 1.0/Math.max(1, d2) });
      }

    temp_data = new Float32Array(raster_data);
    for (let i = 0; i < masked_indices.length; i++) {
      let den = 0;
      let num = 0;
      let p = masked_indices[i];
      let px = p % width;
      let py = Math.floor(p/width);

      for (let x = 0; x < weights.length; x++) {
        let entry = weights[x];
        let ny = py + entry.ry;
        if (ny >= 0 && ny < height) {
          let n_idx = ny*width + ((px + entry.rx + width) % width);
          if (urban_mask[n_idx] === 0 && (!land_area || land_area[n_idx] > 0)) {
            num += entry.w*raster_data[n_idx];
            den += entry.w;
          }
        }
      }

      if (den > 0) {
        temp_data[p] = num/den;
      } else {
        let wide_den = 0;
        let wide_num = 0;
        let wide_r = radius*2;

        for (let y = -wide_r; y <= wide_r; y++) {
          let ny = py + y;
          if (ny >= 0 && ny < height)
            for (let z = -wide_r; z <= wide_r; z++) {
              let nx = (px + z + width) % width;
              let n_idx = ny*width + nx;
              if (urban_mask[n_idx] === 0 && (!land_area || land_area[n_idx] > 0)) {
                let w = 1.0/Math.max(1, z*z + y*y);
                wide_num += w*raster_data[n_idx];
                wide_den += w;
              }
            }
        }

        if (wide_den > 0) {
          temp_data[p] = wide_num/wide_den;
        } else {
          //Preserve zero on uninhabited islands; only fall back to KK10LUH2 when underlying pixel was inhabited
          temp_data[p] = (raster_data[p] > 0 && fallback_data && fallback_data[p] > 0) ? fallback_data[p] : raster_data[p];
        }
      }
    }

    for (let i = 0; i < masked_indices.length; i++)
      raster_data[masked_indices[i]] = temp_data[masked_indices[i]];

    //Return statement
    return raster_data;
  };
	
	/**
	 * Robustly eliminates specific colours by binning them to the nearest available non-binned colour.
	 *
	 * @param {string} arg0_input_path
	 * @param {string} arg1_output_path
	 * @param {Object} [arg2_options]
	 *  @param {Array.<number[]|Object>} arg2_options.bin_colours - Colours to be destroyed (supports [r,g,b,a], [r,g,b,a,tol], or { colour, tolerance }).
	 *   @param {Array.<number[]|Object>} arg2_options.ignore_colours - Colours to leave untouched.
	 *  @param {number} [arg2_options.bin_tolerance=0] - Default RGBA Euclidean distance tolerance for bin_colours.
	 *  @param {number} [arg2_options.ignore_tolerance=0] - Default RGBA Euclidean distance tolerance for ignore_colours.
	 */
	GeoPNG.kNNBin = async function (arg0_input_path, arg1_output_path, arg2_options) { //[WIP] - Test function
		//Convert from parameters
		let input_path = arg0_input_path;
		let output_path = arg1_output_path;
		let options = (arg2_options) ? arg2_options : {};
		
		//Declare local instance variables
		let default_bin_tolerance = (options.bin_tolerance !== undefined) ? 
			options.bin_tolerance : 0;
		let default_ignore_tolerance = (options.ignore_tolerance !== undefined) ? 
			options.ignore_tolerance : 0;
		
		//Helper to parse colour definitions and pre-calculate squared tolerances
		let parseColourList = (colour_list, default_tolerance) => {
			return (colour_list || []).map((item) => {
				let colour = Array.isArray(item) ? item.slice(0, 4) : (item.colour || item.color || [0, 0, 0, 255]);
				let tolerance = (Array.isArray(item) && item.length > 4) ? item[4] : ((item.tolerance !== undefined) ? item.tolerance : default_tolerance);
				
				return {
					colour: colour,
					sq_tolerance: tolerance*tolerance
				};
			});
		};
		
		let bin_list = parseColourList(options.bin_colours, default_bin_tolerance);
		let ignore_list = parseColourList(options.ignore_colours, default_ignore_tolerance);
		
		//Helper to check RGBA Euclidean distance against parsed colour thresholds
		let isColourMatched = (r, g, b, a, list) => {
			for (let i = 0; i < list.length; i++) {
				let target = list[i];
				let dr = r - target.colour[0];
				let dg = g - target.colour[1];
				let db = b - target.colour[2];
				let da = a - target.colour[3];
				let sq_dist = dr*dr + dg*dg + db*db + da*da;
				
				if (sq_dist <= target.sq_tolerance) return true;
			}
			return false;
		};
		
		let buffer = await fs.promises.readFile(input_path);
		let png = await new Promise((resolve, reject) =>
			new pngjs.PNG().parse(buffer, (err, data) => (err) ? reject(err) : resolve(data)));
		
		let { width, height, data } = png;
		let seed_map = new Array(width*height);
		let fallback_seed = null;
		
		//Initialise helper functions
		let checkNeighbour = (x, y, current_data, neighbour) => {
			if (neighbour && neighbour.sx !== -1) {
				let dx = x - neighbour.sx;
				let dy = y - neighbour.sy;
				let d2 = dx*dx + dy*dy;
				
				if (d2 < current_data.dist) {
					current_data.sx = neighbour.sx;
					current_data.sy = neighbour.sy;
					current_data.dist = d2;
				}
			}
		};
		
		//Step 1: Initialise Seed Map
		for (let y = 0; y < height; y++) {
			if (y % 500 === 0) await Blacktraffic.yield();
			
			for (let x = 0; x < width; x++) {
				let idx = (width*y + x) << 2;
				let r = data[idx];
				let g = data[idx + 1];
				let b = data[idx + 2];
				let a = data[idx + 3];
				
				let is_binned = isColourMatched(r, g, b, a, bin_list);
				let is_ignored = isColourMatched(r, g, b, a, ignore_list);
				
				if (!is_binned && !is_ignored) {
					seed_map[width*y + x] = { sx: x, sy: y, dist: 0 };
					if (!fallback_seed) fallback_seed = { x, y };
				} else {
					seed_map[width*y + x] = { sx: -1, sy: -1, dist: Infinity };
				}
			}
		}
		
		//Step 2: Forward Raster Scan
		for (let y = 0; y < height; y++) {
			if (y % 500 === 0) await Blacktraffic.yield();
			
			for (let x = 0; x < width; x++) {
				let idx = width*y + x;
				let current_data = seed_map[idx];
				if (current_data.dist === 0) continue;
				
				if (x > 0) checkNeighbour(x, y, current_data, seed_map[idx - 1]);
				if (y > 0) checkNeighbour(x, y, current_data, seed_map[idx - width]);
				if (x > 0 && y > 0) checkNeighbour(x, y, current_data, seed_map[idx - width - 1]);
				if (x < width - 1 && y > 0) checkNeighbour(x, y, current_data, seed_map[idx - width + 1]);
			}
		}
		
		//Step 3: Backward Raster Scan
		for (let y = height - 1; y >= 0; y--) {
			if (y % 500 === 0) await Blacktraffic.yield();
			
			for (let x = width - 1; x >= 0; x--) {
				let idx = width*y + x;
				let current_data = seed_map[idx];
				if (current_data.dist === 0) continue;
				
				if (x < width - 1) checkNeighbour(x, y, current_data, seed_map[idx + 1]);
				if (y < height - 1) checkNeighbour(x, y, current_data, seed_map[idx + width]);
				if (x < width - 1 && y < height - 1) checkNeighbour(x, y, current_data, seed_map[idx + width + 1]);
				if (x > 0 && y < height - 1) checkNeighbour(x, y, current_data, seed_map[idx + width - 1]);
			}
		}
		
		//Step 4: Apply Transformation
		let fallback_rgba = [0, 0, 0, 0];
		for (let y = 0; y < height; y++) {
			if (y % 500 === 0) await Blacktraffic.yield();
			
			for (let x = 0; x < width; x++) {
				let idx = (width*y + x) << 2;
				let r = data[idx];
				let g = data[idx + 1];
				let b = data[idx + 2];
				let a = data[idx + 3];
				
				if (isColourMatched(r, g, b, a, bin_list)) {
					let final_index = -1;
					let seed = seed_map[width*y + x];
					
					if (seed.sx !== -1) {
						final_index = (width*seed.sy + seed.sx) << 2;
					} else if (fallback_seed) {
						final_index = (width*fallback_seed.y + fallback_seed.x) << 2;
					}
					
					if (final_index !== -1) {
						data[idx] = data[final_index];
						data[idx + 1] = data[final_index + 1];
						data[idx + 2] = data[final_index + 2];
						data[idx + 3] = data[final_index + 3];
					} else {
						data[idx] = fallback_rgba[0];
						data[idx + 1] = fallback_rgba[1];
						data[idx + 2] = fallback_rgba[2];
						data[idx + 3] = fallback_rgba[3];
					}
				}
			}
		}
		
		//Step 5: Save Output
		await new Promise((resolve, reject) => {
			png.pack().pipe(fs.createWriteStream(output_path))
			.on("finish", resolve)
			.on("error", reject);
		});
	};
}