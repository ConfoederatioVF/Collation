//Initialise GeoPNG GPU Pipeline Kernels (Stadestér Reconciliation, Regional Scaling & Velkscala Antiquity Overlay)
{
  if (!global.GeoPNG) global.GeoPNG = {};
  if (!global.GeoPNG.gpu) global.GeoPNG.gpu = {};

  /**
   * Executes a GPU-accelerated binary raster operation on two raw RGBA buffers.
   * @alias GeoPNG.gpu.binaryOpRGBA
   *
   * @param {Buffer|Uint8Array} arg0_buf_a
   * @param {Buffer|Uint8Array} arg1_buf_b
   * @param {string} arg2_op
   * @param {Object} [arg3_options]
   *
   * @returns {Promise<Buffer|null>}
   */
  GeoPNG.gpu.binaryOpRGBA = async function (arg0_buf_a, arg1_buf_b, arg2_op, arg3_options) {
    //Convert from parameters
    let buf_a = arg0_buf_a;
    let buf_b = arg1_buf_b;
    let op = String(arg2_op || "multiply");
    let options = (arg3_options) ? arg3_options : {};

    //Guard clauses
    if (!buf_a || !buf_b || buf_a.byteLength !== buf_b.byteLength) return null;
    let pixel_count = Math.floor(buf_a.byteLength/4);
    if (!GeoPNG.gpu.shouldUseGPU(pixel_count)) return null;

    //Declare local instance variables
    let fmt_a = (options.format_1 === "int32") ? 1 : ((options.format_1 === "float32_le") ? 2 : 0);
    let fmt_b = (options.format_2 === "int32") ? 1 : ((options.format_2 === "float32_le") ? 2 : 0);
    let op_code = 3;
    let param0 = 0;
    let param1 = 3.4028234e38;
    let param2 = 0;
    let param3 = 0;

    if (op === "add") {
      op_code = 0;
    } else if (op === "subtract") {
      op_code = 1;
    } else if (op === "subtract_clamped") {
      op_code = 2;
    } else if (op === "multiply") {
      op_code = 3;
    } else if (op === "divide") {
      op_code = 4;
      param0 = (options.min_denominator !== undefined) ? options.min_denominator : 1e-12;
      param1 = (options.max_val !== undefined) ? options.max_val : 3.4028234e38;
      param2 = (options.log_compression_threshold !== undefined) ? options.log_compression_threshold : 0;
      param3 = (options.log_compression_threshold !== undefined) ?
        (options.clamp_alpha || options.log_compression_threshold*0.1) : 0;
    } else if (op === "overlay") {
      op_code = 5;
    } else if (op === "slope" || op === "delta") {
      op_code = 6;
      param0 = (options.scalar !== undefined) ? options.scalar : 1;
    } else if (op === "lerp") {
      op_code = 7;
      param0 = (options.fraction !== undefined) ? options.fraction : 0.5;
    } else if (op === "log_lerp") {
      op_code = 8;
      param0 = (options.fraction !== undefined) ? options.fraction : 0.5;
    } else if (op === "density_stadester") {
      op_code = 9;
    }

    //Return statement
    return GeoPNG.gpu.runSerialised(async function () {
      let bytes = pixel_count*4;
      let cl = GeoPNG.gpu._cl;
      let d_a = GeoPNG.gpu.acquireBuffer("bin_a", bytes, 4n);
      let d_b = GeoPNG.gpu.acquireBuffer("bin_b", bytes, 4n);
      let d_out = GeoPNG.gpu.acquireBuffer("bin_out", bytes, 2n);
      let kernel = GeoPNG.gpu._kernels.binary_op_be_rgba;
      let out_buf = Buffer.allocUnsafe(bytes);

      if (!d_a || !d_b || !d_out || !kernel) return null;

      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_a.mem, 0, 0, bytes, buf_a, 0, null, null);
      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_b.mem, 0, 0, bytes, buf_b, 0, null, null);

      await GeoPNG.gpu.dispatchWaves(pixel_count, function (arg0_offset, arg1_count, arg2_global, arg3_local) {
        cl.clSetKernelArgMem(kernel, 0, 8, [d_a.mem]);
        cl.clSetKernelArgMem(kernel, 1, 8, [d_b.mem]);
        cl.clSetKernelArgMem(kernel, 2, 8, [d_out.mem]);
        cl.clSetKernelArgU32(kernel, 3, 4, [arg0_offset]);
        cl.clSetKernelArgU32(kernel, 4, 4, [arg1_count]);
        cl.clSetKernelArgU32(kernel, 5, 4, [op_code]);
        cl.clSetKernelArgU32(kernel, 6, 4, [fmt_a]);
        cl.clSetKernelArgU32(kernel, 7, 4, [fmt_b]);
        cl.clSetKernelArgF32(kernel, 8, 4, [param0]);
        cl.clSetKernelArgF32(kernel, 9, 4, [param1]);
        cl.clSetKernelArgF32(kernel, 10, 4, [param2]);
        cl.clSetKernelArgF32(kernel, 11, 4, [param3]);
        cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, kernel, 1, null, [arg2_global], [arg3_local], 0, null, null);
      });

      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_out.mem, 1, 0, bytes, out_buf, 0, null, null);
      return out_buf;
    });
  };

  /**
   * Executes full two-pass Stadestér demographic reconciliation on the NVIDIA GPU.
   * Preserves exact float64 per-mask sums and float32 big-endian RGBA output equivalence.
   * @alias GeoPNG.gpu.reconcileDemographicsRGBA
   *
   * @param {Object} arg0_params
   *  @param {Int32Array} arg0_params.mask_ids
   *  @param {number} arg0_params.num_masks
   *  @param {Float32Array} arg0_params.sub_urban_f32
   *  @param {Buffer|Uint8Array} arg0_params.substrata_rgba
   *  @param {Buffer|Uint8Array} arg0_params.urban_rgba
   *
   * @returns {Promise<{rural_rgba: Buffer, total_rgba: Buffer, urban_rgba: Buffer}|null>}
   */
  GeoPNG.gpu.reconcileDemographicsRGBA = async function (arg0_params) {
    //Convert from parameters
    let params = (arg0_params) ? arg0_params : {};

    //Declare local instance variables
    let mask_ids = params.mask_ids;
    let num_masks = Math.max(1, Math.floor(Number(params.num_masks) || 1));
    let sub_urban_f32 = params.sub_urban_f32;
    let substrata_rgba = params.substrata_rgba;
    let urban_rgba = params.urban_rgba;

    //Guard clauses
    if (!substrata_rgba || !urban_rgba || !sub_urban_f32 || !mask_ids) return null;
    let pixel_count = Math.floor(substrata_rgba.byteLength/4);
    if (!GeoPNG.gpu.shouldUseGPU(pixel_count)) return null;

    //Return statement
    return GeoPNG.gpu.runSerialised(async function () {
      let bytes = pixel_count*4;
      let cl = GeoPNG.gpu._cl;
      let d_global = GeoPNG.gpu.acquireBuffer("rec_global", 16, 1n);
      let d_mask_comb = GeoPNG.gpu.acquireBuffer("rec_mask_comb", num_masks*8, 1n);
      let d_mask_ids = GeoPNG.gpu.acquireBuffer("rec_mask_ids", bytes, 4n);
      let d_mask_scalars = GeoPNG.gpu.acquireBuffer("rec_mask_scalars", num_masks*4, 4n);
      let d_mask_sub = GeoPNG.gpu.acquireBuffer("rec_mask_sub", num_masks*8, 1n);
      let d_raw_rural = GeoPNG.gpu.acquireBuffer("rec_raw_rural", bytes, 1n);
      let d_raw_urban = GeoPNG.gpu.acquireBuffer("rec_raw_urban", bytes, 1n);
      let d_rural_out = GeoPNG.gpu.acquireBuffer("rec_rural_out", bytes, 2n);
      let d_sub = GeoPNG.gpu.acquireBuffer("rec_sub", bytes, 4n);
      let d_sub_u = GeoPNG.gpu.acquireBuffer("rec_sub_u", bytes, 4n);
      let d_total_out = GeoPNG.gpu.acquireBuffer("rec_total_out", bytes, 2n);
      let d_urb = GeoPNG.gpu.acquireBuffer("rec_urb", bytes, 4n);
      let d_urban_out = GeoPNG.gpu.acquireBuffer("rec_urban_out", bytes, 2n);
      let k1 = GeoPNG.gpu._kernels.reconcile_pass1_be_rgba;
      let k2 = GeoPNG.gpu._kernels.reconcile_pass2_be_rgba;
      let zero_pattern = Buffer.alloc(8, 0);

      if (!d_sub || !d_urb || !d_sub_u || !d_mask_ids || !d_raw_rural || !d_raw_urban || !d_mask_sub || !d_mask_comb || !d_global || !d_mask_scalars || !d_rural_out || !d_urban_out || !d_total_out)
        return null;

      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_sub.mem, 0, 0, bytes, substrata_rgba, 0, null, null);
      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_urb.mem, 0, 0, bytes, urban_rgba, 0, null, null);
      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_sub_u.mem, 0, 0, bytes, new Uint8Array(sub_urban_f32.buffer, sub_urban_f32.byteOffset, bytes), 0, null, null);
      if (GeoPNG.gpu._last_rec_mask_ref !== mask_ids) {
        cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_mask_ids.mem, 0, 0, bytes, new Uint8Array(mask_ids.buffer, mask_ids.byteOffset, bytes), 0, null, null);
        GeoPNG.gpu._last_rec_mask_ref = mask_ids;
      }

      cl.clEnqueueFillBuffer(GeoPNG.gpu._queue, d_mask_sub.mem, zero_pattern, 8, 0, num_masks*8, 0, null, null);
      cl.clEnqueueFillBuffer(GeoPNG.gpu._queue, d_mask_comb.mem, zero_pattern, 8, 0, num_masks*8, 0, null, null);
      cl.clEnqueueFillBuffer(GeoPNG.gpu._queue, d_global.mem, zero_pattern, 8, 0, 16, 0, null, null);

      await GeoPNG.gpu.dispatchWaves(pixel_count, function (arg0_offset, arg1_count, arg2_global, arg3_local) {
        cl.clSetKernelArgMem(k1, 0, 8, [d_sub.mem]);
        cl.clSetKernelArgMem(k1, 1, 8, [d_urb.mem]);
        cl.clSetKernelArgMem(k1, 2, 8, [d_sub_u.mem]);
        cl.clSetKernelArgMem(k1, 3, 8, [d_mask_ids.mem]);
        cl.clSetKernelArgMem(k1, 4, 8, [d_raw_rural.mem]);
        cl.clSetKernelArgMem(k1, 5, 8, [d_raw_urban.mem]);
        cl.clSetKernelArgMem(k1, 6, 8, [d_mask_sub.mem]);
        cl.clSetKernelArgMem(k1, 7, 8, [d_mask_comb.mem]);
        cl.clSetKernelArgMem(k1, 8, 8, [d_global.mem]);
        cl.clSetKernelArgU32(k1, 9, 4, [arg0_offset]);
        cl.clSetKernelArgU32(k1, 10, 4, [arg1_count]);
        cl.clSetKernelArgU32(k1, 11, 4, [num_masks]);
        cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, k1, 1, null, [arg2_global], [arg3_local], 0, null, null);
      });

      let host_global_bytes = Buffer.allocUnsafe(16);
      let host_mask_comb_bytes = Buffer.allocUnsafe(num_masks*8);
      let host_mask_sub_bytes = Buffer.allocUnsafe(num_masks*8);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_global.mem, 0, 0, 16, host_global_bytes, 0, null, null);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_mask_sub.mem, 0, 0, num_masks*8, host_mask_sub_bytes, 0, null, null);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_mask_comb.mem, 1, 0, num_masks*8, host_mask_comb_bytes, 0, null, null);

      let global_f64 = new Float64Array(host_global_bytes.buffer, host_global_bytes.byteOffset, 2);
      let mask_comb_f64 = new Float64Array(host_mask_comb_bytes.buffer, host_mask_comb_bytes.byteOffset, num_masks);
      let mask_sub_f64 = new Float64Array(host_mask_sub_bytes.buffer, host_mask_sub_bytes.byteOffset, num_masks);
      let global_sub = global_f64[0];
      let global_comb = global_f64[1];
      let fallback_scalar = (global_comb > 0 && global_sub > 0) ? (global_sub/global_comb) : 1;
      let mask_scalars = new Float32Array(num_masks);

      for (let m = 0; m < num_masks; m++) {
        let c_sum = mask_comb_f64[m];
        let s_sum = mask_sub_f64[m];
        if (s_sum > 0 && c_sum > 0) {
          mask_scalars[m] = s_sum/c_sum;
        } else if (s_sum <= 0 && c_sum > 0) {
          mask_scalars[m] = fallback_scalar;
        } else {
          mask_scalars[m] = 1;
        }
      }

      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_mask_scalars.mem, 0, 0, num_masks*4, new Uint8Array(mask_scalars.buffer, mask_scalars.byteOffset, num_masks*4), 0, null, null);

      await GeoPNG.gpu.dispatchWaves(pixel_count, function (arg0_offset, arg1_count, arg2_global, arg3_local) {
        cl.clSetKernelArgMem(k2, 0, 8, [d_raw_rural.mem]);
        cl.clSetKernelArgMem(k2, 1, 8, [d_raw_urban.mem]);
        cl.clSetKernelArgMem(k2, 2, 8, [d_mask_ids.mem]);
        cl.clSetKernelArgMem(k2, 3, 8, [d_mask_scalars.mem]);
        cl.clSetKernelArgMem(k2, 4, 8, [d_rural_out.mem]);
        cl.clSetKernelArgMem(k2, 5, 8, [d_urban_out.mem]);
        cl.clSetKernelArgMem(k2, 6, 8, [d_total_out.mem]);
        cl.clSetKernelArgU32(k2, 7, 4, [arg0_offset]);
        cl.clSetKernelArgU32(k2, 8, 4, [arg1_count]);
        cl.clSetKernelArgU32(k2, 9, 4, [num_masks]);
        cl.clSetKernelArgF32(k2, 10, 4, [fallback_scalar]);
        cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, k2, 1, null, [arg2_global], [arg3_local], 0, null, null);
      });

      let out_rural_rgba = Buffer.allocUnsafe(bytes);
      let out_total_rgba = Buffer.allocUnsafe(bytes);
      let out_urban_rgba = Buffer.allocUnsafe(bytes);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_rural_out.mem, 0, 0, bytes, out_rural_rgba, 0, null, null);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_urban_out.mem, 0, 0, bytes, out_urban_rgba, 0, null, null);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_total_out.mem, 1, 0, bytes, out_total_rgba, 0, null, null);

      return { rural_rgba: out_rural_rgba, total_rgba: out_total_rgba, urban_rgba: out_urban_rgba };
    });
  };

  /**
   * Scales a big-endian float32 RGBA raster per Int32 region ID on the NVIDIA GPU.
   * @alias GeoPNG.gpu.regionalScaleRGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {Int32Array} arg1_region_ids
   * @param {Float32Array} arg2_region_scalars
   * @param {number} [arg3_fallback_scalar=1]
   *
   * @returns {Promise<Buffer|null>}
   */
  GeoPNG.gpu.regionalScaleRGBA = async function (arg0_in_rgba, arg1_region_ids, arg2_region_scalars, arg3_fallback_scalar) {
    //Convert from parameters
    let fallback_scalar = (arg3_fallback_scalar !== undefined) ? arg3_fallback_scalar : 1;
    let in_rgba = arg0_in_rgba;
    let region_ids = arg1_region_ids;
    let region_scalars = arg2_region_scalars;

    //Guard clauses
    if (!in_rgba || !region_ids || !region_scalars) return null;
    let pixel_count = Math.floor(in_rgba.byteLength/4);
    if (!GeoPNG.gpu.shouldUseGPU(pixel_count)) return null;

    //Return statement
    return GeoPNG.gpu.runSerialised(async function () {
      let bytes = pixel_count*4;
      let cl = GeoPNG.gpu._cl;
      let d_in = GeoPNG.gpu.acquireBuffer("rscale_in", bytes, 4n);
      let d_out = GeoPNG.gpu.acquireBuffer("rscale_out", bytes, 2n);
      let d_rids = GeoPNG.gpu.acquireBuffer("rscale_rids", bytes, 4n);
      let d_sc = GeoPNG.gpu.acquireBuffer("rscale_sc", region_scalars.byteLength, 4n);
      let kernel = GeoPNG.gpu._kernels.regional_scale_be_rgba;
      let num_regions = region_scalars.length;
      let out_buf = Buffer.allocUnsafe(bytes);

      if (!d_in || !d_out || !d_rids || !d_sc || !kernel) return null;

      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_in.mem, 0, 0, bytes, in_rgba, 0, null, null);
      if (GeoPNG.gpu._last_rscale_ids_ref !== region_ids) {
        cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_rids.mem, 0, 0, bytes, new Uint8Array(region_ids.buffer, region_ids.byteOffset, bytes), 0, null, null);
        GeoPNG.gpu._last_rscale_ids_ref = region_ids;
      }
      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_sc.mem, 0, 0, region_scalars.byteLength, new Uint8Array(region_scalars.buffer, region_scalars.byteOffset, region_scalars.byteLength), 0, null, null);

      await GeoPNG.gpu.dispatchWaves(pixel_count, function (arg0_offset, arg1_count, arg2_global, arg3_local) {
        cl.clSetKernelArgMem(kernel, 0, 8, [d_in.mem]);
        cl.clSetKernelArgMem(kernel, 1, 8, [d_rids.mem]);
        cl.clSetKernelArgMem(kernel, 2, 8, [d_sc.mem]);
        cl.clSetKernelArgMem(kernel, 3, 8, [d_out.mem]);
        cl.clSetKernelArgU32(kernel, 4, 4, [arg0_offset]);
        cl.clSetKernelArgU32(kernel, 5, 4, [arg1_count]);
        cl.clSetKernelArgU32(kernel, 6, 4, [num_regions]);
        cl.clSetKernelArgF32(kernel, 7, 4, [fallback_scalar]);
        cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, kernel, 1, null, [arg2_global], [arg3_local], 0, null, null);
      });

      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_out.mem, 1, 0, bytes, out_buf, 0, null, null);
      return out_buf;
    });
  };

  /**
   * Computes fp64 per-region sums over a big-endian float32 RGBA raster on the NVIDIA GPU.
   * @alias GeoPNG.gpu.regionalSumRGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {Int32Array} arg1_region_ids
   * @param {number} arg2_num_regions
   * @param {Object} [arg3_options]
   *
   * @returns {Promise<Float64Array|null>}
   */
  GeoPNG.gpu.regionalSumRGBA = async function (arg0_in_rgba, arg1_region_ids, arg2_num_regions, arg3_options) {
    //Convert from parameters
    let in_rgba = arg0_in_rgba;
    let num_regions = Math.max(1, Math.floor(Number(arg2_num_regions) || 1));
    let options = (arg3_options) ? arg3_options : {};
    let region_ids = arg1_region_ids;

    //Guard clauses
    if (!in_rgba || !region_ids) return null;
    let pixel_count = Math.floor(in_rgba.byteLength/4);
    if (!GeoPNG.gpu.shouldUseGPU(pixel_count)) return null;

    let positive_only = (options.positive_only !== false) ? 1 : 0;

    //Return statement
    return GeoPNG.gpu.runSerialised(async function () {
      let bytes = pixel_count*4;
      let cl = GeoPNG.gpu._cl;
      let d_in = GeoPNG.gpu.acquireBuffer("rsum_in", bytes, 4n);
      let d_rids = GeoPNG.gpu.acquireBuffer("rsum_rids", bytes, 4n);
      let d_sums = GeoPNG.gpu.acquireBuffer("rsum_out", num_regions*8, 1n);
      let kernel = GeoPNG.gpu._kernels.regional_sum_be_rgba;
      let zero_pattern = Buffer.alloc(8, 0);

      if (!d_in || !d_rids || !d_sums || !kernel) return null;

      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_in.mem, 0, 0, bytes, in_rgba, 0, null, null);
      if (GeoPNG.gpu._last_rsum_ids_ref !== region_ids) {
        cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_rids.mem, 0, 0, bytes, new Uint8Array(region_ids.buffer, region_ids.byteOffset, bytes), 0, null, null);
        GeoPNG.gpu._last_rsum_ids_ref = region_ids;
      }
      cl.clEnqueueFillBuffer(GeoPNG.gpu._queue, d_sums.mem, zero_pattern, 8, 0, num_regions*8, 0, null, null);

      await GeoPNG.gpu.dispatchWaves(pixel_count, function (arg0_offset, arg1_count, arg2_global, arg3_local) {
        cl.clSetKernelArgMem(kernel, 0, 8, [d_in.mem]);
        cl.clSetKernelArgMem(kernel, 1, 8, [d_rids.mem]);
        cl.clSetKernelArgMem(kernel, 2, 8, [d_sums.mem]);
        cl.clSetKernelArgU32(kernel, 3, 4, [arg0_offset]);
        cl.clSetKernelArgU32(kernel, 4, 4, [arg1_count]);
        cl.clSetKernelArgU32(kernel, 5, 4, [num_regions]);
        cl.clSetKernelArgU32(kernel, 6, 4, [positive_only]);
        cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, kernel, 1, null, [arg2_global], [arg3_local], 0, null, null);
      });

      let host_bytes = Buffer.allocUnsafe(num_regions*8);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_sums.mem, 1, 0, num_regions*8, host_bytes, 0, null, null);
      return new Float64Array(host_bytes.buffer, host_bytes.byteOffset, num_regions);
    });
  };

  /**
   * Executes full Velkscala antiquity Viscount domain overlay on the NVIDIA GPU.
   * @alias GeoPNG.gpu.velkscalaAntiquityOverlayRGBA
   *
   * @param {Object} arg0_params
   *
   * @returns {Promise<{popc_rgba: Buffer, popd_rgba: Buffer, rurc_rgba: Buffer, urbc_rgba: Buffer}|null>}
   */
  GeoPNG.gpu.velkscalaAntiquityOverlayRGBA = async function (arg0_params) {
    //Convert from parameters
    let params = (arg0_params) ? arg0_params : {};

    //Declare local instance variables
    let bfs_dist = params.bfs_dist;
    let frac = Number(params.frac) || 0;
    let grid_a_rgba = params.grid_a_rgba;
    let grid_b_rgba = params.grid_b_rgba;
    let height = Number(params.height) || 2160;
    let land_area = params.land_area;
    let owner_grid = params.owner_grid;
    let popc_rgba = params.popc_rgba;
    let popd_rgba = params.popd_rgba;
    let rurc_rgba = params.rurc_rgba;
    let seam_pixels = params.seam_pixels;
    let seam_px = Number(params.seam_px) || 16;
    let static_key = params.static_key || "velk_default";
    let urbc_rgba = params.urbc_rgba;
    let width = Number(params.width) || 4320;
    let total_px = width*height;

    //Guard clauses
    if (!grid_a_rgba || !grid_b_rgba || !popc_rgba || !urbc_rgba || !rurc_rgba || !popd_rgba || !owner_grid || !land_area || !bfs_dist)
      return null;
    if (!GeoPNG.gpu.shouldUseGPU(total_px)) return null;

    //Return statement
    return GeoPNG.gpu.runSerialised(async function () {
      let bytes = total_px*4;
      let cl = GeoPNG.gpu._cl;
      let d_bfs = GeoPNG.gpu.acquireBuffer("velk_bfs", bytes, 4n);
      let d_ext_a = GeoPNG.gpu.acquireBuffer("velk_ext_a", bytes, 1n);
      let d_ext_b = GeoPNG.gpu.acquireBuffer("velk_ext_b", bytes, 1n);
      let d_ga = GeoPNG.gpu.acquireBuffer("velk_ga", bytes, 4n);
      let d_gb = GeoPNG.gpu.acquireBuffer("velk_gb", bytes, 4n);
      let d_la = GeoPNG.gpu.acquireBuffer("velk_la", bytes, 4n);
      let d_owner = GeoPNG.gpu.acquireBuffer("velk_owner", total_px, 4n);
      let d_popc = GeoPNG.gpu.acquireBuffer("velk_popc", bytes, 1n);
      let d_popd = GeoPNG.gpu.acquireBuffer("velk_popd", bytes, 1n);
      let d_rurc = GeoPNG.gpu.acquireBuffer("velk_rurc", bytes, 1n);
      let d_seam = (seam_pixels && seam_pixels.length > 0) ?
        GeoPNG.gpu.acquireBuffer("velk_seam_idx", seam_pixels.byteLength, 4n) : null;
      let d_urbc = GeoPNG.gpu.acquireBuffer("velk_urbc", bytes, 1n);
      let k_blend = GeoPNG.gpu._kernels.velkscala_antiquity_blend;
      let k_harm = GeoPNG.gpu._kernels.velkscala_harmonic_step;
      let k_init = GeoPNG.gpu._kernels.velkscala_seam_init;

      if (!d_bfs || !d_ext_a || !d_ext_b || !d_ga || !d_gb || !d_la || !d_owner || !d_popc || !d_popd || !d_rurc || !d_urbc)
        return null;

      if (GeoPNG.gpu._last_velk_static_key !== static_key) {
        cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_owner.mem, 0, 0, total_px, owner_grid, 0, null, null);
        cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_la.mem, 0, 0, bytes, new Uint8Array(land_area.buffer, land_area.byteOffset, bytes), 0, null, null);
        cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_bfs.mem, 0, 0, bytes, new Uint8Array(bfs_dist.buffer, bfs_dist.byteOffset, bytes), 0, null, null);
        if (d_seam && seam_pixels && seam_pixels.length > 0)
          cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_seam.mem, 0, 0, seam_pixels.byteLength, new Uint8Array(seam_pixels.buffer, seam_pixels.byteOffset, seam_pixels.byteLength), 0, null, null);
        GeoPNG.gpu._last_velk_static_key = static_key;
      }

      if (GeoPNG.gpu._last_velk_ga_ref !== grid_a_rgba) {
        cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_ga.mem, 0, 0, bytes, grid_a_rgba, 0, null, null);
        GeoPNG.gpu._last_velk_ga_ref = grid_a_rgba;
      }
      if (GeoPNG.gpu._last_velk_gb_ref !== grid_b_rgba) {
        cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_gb.mem, 0, 0, bytes, grid_b_rgba, 0, null, null);
        GeoPNG.gpu._last_velk_gb_ref = grid_b_rgba;
      }

      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_popc.mem, 0, 0, bytes, popc_rgba, 0, null, null);
      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_urbc.mem, 0, 0, bytes, urbc_rgba, 0, null, null);
      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_rurc.mem, 0, 0, bytes, rurc_rgba, 0, null, null);
      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_popd.mem, 0, 0, bytes, popd_rgba, 0, null, null);

      let local_size = Math.max(32, Number(GeoPNG.compute_limits.gpu.workgroup_size) || 256);

      if (d_seam && seam_pixels && seam_pixels.length > 0) {
        let init_global = Math.ceil(total_px/local_size)*local_size;
        cl.clSetKernelArgMem(k_init, 0, 8, [d_popc.mem]);
        cl.clSetKernelArgMem(k_init, 1, 8, [d_owner.mem]);
        cl.clSetKernelArgMem(k_init, 2, 8, [d_la.mem]);
        cl.clSetKernelArgMem(k_init, 3, 8, [d_bfs.mem]);
        cl.clSetKernelArgMem(k_init, 4, 8, [d_ext_a.mem]);
        cl.clSetKernelArgMem(k_init, 5, 8, [d_ext_b.mem]);
        cl.clSetKernelArgU32(k_init, 6, 4, [width]);
        cl.clSetKernelArgU32(k_init, 7, 4, [height]);
        cl.clSetKernelArgF32(k_init, 8, 4, [seam_px]);
        cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, k_init, 1, null, [init_global], [local_size], 0, null, null);

        let seam_count = seam_pixels.length;
        let seam_global = Math.ceil(seam_count/local_size)*local_size;

        for (let it = 0; it < seam_px; it++) {
          let src_mem = (it % 2 === 0) ? d_ext_a.mem : d_ext_b.mem;
          let dst_mem = (it % 2 === 0) ? d_ext_b.mem : d_ext_a.mem;
          cl.clSetKernelArgMem(k_harm, 0, 8, [d_seam.mem]);
          cl.clSetKernelArgMem(k_harm, 1, 8, [d_owner.mem]);
          cl.clSetKernelArgMem(k_harm, 2, 8, [d_la.mem]);
          cl.clSetKernelArgMem(k_harm, 3, 8, [d_bfs.mem]);
          cl.clSetKernelArgMem(k_harm, 4, 8, [src_mem]);
          cl.clSetKernelArgMem(k_harm, 5, 8, [dst_mem]);
          cl.clSetKernelArgU32(k_harm, 6, 4, [seam_count]);
          cl.clSetKernelArgU32(k_harm, 7, 4, [width]);
          cl.clSetKernelArgU32(k_harm, 8, 4, [height]);
          cl.clSetKernelArgF32(k_harm, 9, 4, [seam_px]);
          cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, k_harm, 1, null, [seam_global], [local_size], 0, null, null);
        }
        cl.clFinish(GeoPNG.gpu._queue);
      }

      let ext_smooth_mem = (seam_px % 2 === 0) ? d_ext_a.mem : d_ext_b.mem;

      await GeoPNG.gpu.dispatchWaves(total_px, function (arg0_offset, arg1_count, arg2_global, arg3_local) {
        cl.clSetKernelArgMem(k_blend, 0, 8, [d_ga.mem]);
        cl.clSetKernelArgMem(k_blend, 1, 8, [d_gb.mem]);
        cl.clSetKernelArgMem(k_blend, 2, 8, [d_owner.mem]);
        cl.clSetKernelArgMem(k_blend, 3, 8, [d_la.mem]);
        cl.clSetKernelArgMem(k_blend, 4, 8, [d_bfs.mem]);
        cl.clSetKernelArgMem(k_blend, 5, 8, [ext_smooth_mem]);
        cl.clSetKernelArgMem(k_blend, 6, 8, [d_urbc.mem]);
        cl.clSetKernelArgMem(k_blend, 7, 8, [d_popc.mem]);
        cl.clSetKernelArgMem(k_blend, 8, 8, [d_rurc.mem]);
        cl.clSetKernelArgMem(k_blend, 9, 8, [d_popd.mem]);
        cl.clSetKernelArgU32(k_blend, 10, 4, [arg0_offset]);
        cl.clSetKernelArgU32(k_blend, 11, 4, [arg1_count]);
        cl.clSetKernelArgF32(k_blend, 12, 4, [frac]);
        cl.clSetKernelArgF32(k_blend, 13, 4, [seam_px]);
        cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, k_blend, 1, null, [arg2_global], [arg3_local], 0, null, null);
      });

      let out_popc = Buffer.allocUnsafe(bytes);
      let out_popd = Buffer.allocUnsafe(bytes);
      let out_rurc = Buffer.allocUnsafe(bytes);
      let out_urbc = Buffer.allocUnsafe(bytes);

      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_urbc.mem, 0, 0, bytes, out_urbc, 0, null, null);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_popc.mem, 0, 0, bytes, out_popc, 0, null, null);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_rurc.mem, 0, 0, bytes, out_rurc, 0, null, null);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_popd.mem, 1, 0, bytes, out_popd, 0, null, null);

      return {
        popc_rgba: out_popc,
        popd_rgba: out_popd,
        rurc_rgba: out_rurc,
        urbc_rgba: out_urbc
      };
    });
  };
}
