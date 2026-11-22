//Initialise GeoPNG Compute Governance Kernel, Win32 Job Object & Native C++20 Accelerator
{
  if (!global.GeoPNG)
    /**
     * Analogous to a GeoTIFF file format, but in PNG form for easier editing. Single variable. Part of Geospatiale III.
     *
     * @namespace GeoPNG
     */
    global.GeoPNG = {};

  /**
   * Native C++20 AVX2 BelowNormal thread-pool accelerator bridge (via koffi -> svea_geopng_accel.dll).
   * Executes memory-bandwidth-bound 4K raster & parser operations in 1,4-13 ms with 0% GPU/DWM contention.
   *
   * @namespace GeoPNG.native
   */
  GeoPNG.native = {
    _fn: null,
    _init_attempted: false,
    _init_error: null,
    _ready: false
  };

  /**
   * WDDM frame-budget GPU governor & process lifecycle manager (prevents dual-monitor FPS lag & orphaned workers).
   *
   * @namespace GeoPNG.governor
   */
  GeoPNG.governor = {
    _frame_window_ms: 16.67,
    _job_initialised: false,
    _lifecycle_hooked: false,
    _shutdown_called: false,
    _window_gpu_ms: 0,
    _window_start_ms: 0
  };

  /**
   * Assigns a spawned child process PID to the active Win32 Job Object so OS kernel terminates it on parent exit.
   * @alias GeoPNG.governor.assignChildPid
   *
   * @param {number} arg0_pid
   *
   * @returns {boolean}
   */
  GeoPNG.governor.assignChildPid = function (arg0_pid) {
    //Convert from parameters
    let pid = Number(arg0_pid) || 0;

    //Guard clauses
    if (pid <= 0 || process.platform !== "win32") return false;
    if (!GeoPNG.native.isAvailable()) return false;
    let limits = (GeoPNG.compute_limits && GeoPNG.compute_limits.native) ? GeoPNG.compute_limits.native : {};
    if (limits.enforce_job_object === false) return false;

    try {
      if (!GeoPNG.governor._job_initialised) {
        GeoPNG.governor._job_initialised = Boolean(GeoPNG.native._fn.svea_init_job_object());
      }
      //Return statement
      return Boolean(GeoPNG.native._fn.svea_assign_pid_to_job(pid >>> 0));
    } catch (e) {
      return false;
    }
  };

  /**
   * Returns current wall-clock timestamp in milliseconds with sub-millisecond precision.
   * @alias GeoPNG.governor.nowMs
   *
   * @returns {number}
   */
  GeoPNG.governor.nowMs = function () {
    //Function body
    if (typeof performance !== "undefined" && typeof performance.now === "function")
      return performance.now();

    //Return statement
    return Date.now();
  };

  /**
   * Records a GPU kernel wave duration and yields only when the WDDM 60 Hz frame budget is exceeded.
   * Avoids the 15,7 ms Windows timer penalty on fast (< 5 ms) GPU kernels whilst keeping DWM locked at 60 FPS.
   * @alias GeoPNG.governor.paceGpuWaveAsync
   *
   * @param {number} arg0_wave_ms
   *
   * @returns {Promise<void>}
   */
  GeoPNG.governor.paceGpuWaveAsync = async function (arg0_wave_ms) {
    //Convert from parameters
    let wave_ms = Math.max(0, Number(arg0_wave_ms) || 0);

    //Declare local instance variables
    let budget_ms = (GeoPNG.compute_limits && GeoPNG.compute_limits.gpu && GeoPNG.compute_limits.gpu.frame_budget_ms !== undefined) ?
      Number(GeoPNG.compute_limits.gpu.frame_budget_ms) : 6.0;
    let now = GeoPNG.governor.nowMs();
    let window_ms = GeoPNG.governor._frame_window_ms;

    //Function body
    if (now - GeoPNG.governor._window_start_ms >= window_ms) {
      GeoPNG.governor._window_start_ms = now;
      GeoPNG.governor._window_gpu_ms = 0;
    }
    GeoPNG.governor._window_gpu_ms += wave_ms;

    if (GeoPNG.governor._window_gpu_ms >= budget_ms) {
      let rem_ms = Math.max(1, Math.ceil(window_ms - (now - GeoPNG.governor._window_start_ms)));
      GeoPNG.governor._window_gpu_ms = 0;
      GeoPNG.governor._window_start_ms = now + rem_ms;
      await new Promise((resolve) => setTimeout(resolve, Math.min(16, rem_ms)));
    } else if (typeof setImmediate === "function") {
      await new Promise((resolve) => setImmediate(resolve));
    }
  };

  /**
   * Synchronous WDDM pacing hook for synchronous Viscount GPU dispatches.
   * @alias GeoPNG.governor.recordGpuWaveSync
   *
   * @param {number} arg0_wave_ms
   */
  GeoPNG.governor.recordGpuWaveSync = function (arg0_wave_ms) {
    //Convert from parameters
    let wave_ms = Math.max(0, Number(arg0_wave_ms) || 0);

    //Declare local instance variables
    let now = GeoPNG.governor.nowMs();

    //Function body
    if (now - GeoPNG.governor._window_start_ms >= GeoPNG.governor._frame_window_ms) {
      GeoPNG.governor._window_start_ms = now;
      GeoPNG.governor._window_gpu_ms = 0;
    }
    GeoPNG.governor._window_gpu_ms += wave_ms;
  };

  /**
   * Registers idempotent OS signal & exit hooks to release GPU contexts, native thread pools & child workers cleanly.
   * Prevents orphaned Node/Electron workers and wedged NVIDIA WDDM OpenCL contexts when tasks stop.
   * @alias GeoPNG.governor.registerLifecycleHooks
   */
  GeoPNG.governor.registerLifecycleHooks = function () {
    //Guard clauses
    if (GeoPNG.governor._lifecycle_hooked) return;
    if (typeof process === "undefined" || typeof process.on !== "function") return;
    GeoPNG.governor._lifecycle_hooked = true;

    //Declare local instance variables
    let gracefulShutdown = function (arg0_signal) {
      if (GeoPNG.governor._shutdown_called) return;
      GeoPNG.governor._shutdown_called = true;

      try {
        if (typeof GeoPNG.terminateAllWorkers === "function") GeoPNG.terminateAllWorkers();
      } catch (e) {}
      try {
        if (GeoPNG.gpu && typeof GeoPNG.gpu.shutdown === "function") GeoPNG.gpu.shutdown();
      } catch (e) {}
      try {
        if (GeoPNG.native && typeof GeoPNG.native.shutdown === "function") GeoPNG.native.shutdown();
      } catch (e) {}

      if (arg0_signal && typeof arg0_signal === "string") {
        let code = (arg0_signal === "SIGINT") ? 130 : ((arg0_signal === "SIGTERM") ? 143 : 1);
        process.exit(code);
      }
    };

    //Function body
    if (GeoPNG.native.isAvailable() && process.platform === "win32") {
      try {
        GeoPNG.governor._job_initialised = Boolean(GeoPNG.native._fn.svea_init_job_object());
      } catch (e) {}
    }

    process.on("exit", function () { gracefulShutdown(null); });
    process.on("SIGINT", function () { gracefulShutdown("SIGINT"); });
    process.on("SIGTERM", function () { gracefulShutdown("SIGTERM"); });
    if (process.platform === "win32")
      process.on("SIGBREAK", function () { gracefulShutdown("SIGBREAK"); });
  };

  /**
   * Executes a binary BE-RGBA raster operation on the native C++20 BelowNormal thread pool.
   * @alias GeoPNG.native.binaryOpRGBA
   *
   * @param {Buffer|Uint8Array} arg0_buf_a
   * @param {Buffer|Uint8Array} arg1_buf_b
   * @param {number} arg2_op_code
   * @param {number} arg3_fmt_a
   * @param {number} arg4_fmt_b
   * @param {number} arg5_p0
   * @param {number} arg6_p1
   * @param {number} arg7_p2
   * @param {number} arg8_p3
   *
   * @returns {Buffer|null}
   */
  GeoPNG.native.binaryOpRGBA = function (arg0_buf_a, arg1_buf_b, arg2_op_code, arg3_fmt_a, arg4_fmt_b, arg5_p0, arg6_p1, arg7_p2, arg8_p3) {
    //Convert from parameters
    let buf_a = arg0_buf_a;
    let buf_b = arg1_buf_b;
    let op_code = arg2_op_code >>> 0;
    let fmt_a = arg3_fmt_a >>> 0;
    let fmt_b = arg4_fmt_b >>> 0;
    let p0 = Number(arg5_p0) || 0;
    let p1 = Number(arg6_p1) || 3.4028234e38;
    let p2 = Number(arg7_p2) || 0;
    let p3 = Number(arg8_p3) || 0;

    //Guard clauses
    if (!buf_a || !buf_b || buf_a.byteLength !== buf_b.byteLength || !GeoPNG.native.isAvailable())
      return null;

    //Declare local instance variables
    let out_buf = Buffer.allocUnsafe(buf_a.byteLength);
    let pixel_count = Math.floor(buf_a.byteLength/4);
    let threads = GeoPNG.native.getThreadCount();

    //Function body
    GeoPNG.native._fn.svea_binary_op_be_rgba(buf_a, buf_b, out_buf, pixel_count, op_code, fmt_a, fmt_b, p0, p1, p2, p3, threads);

    //Return statement
    return out_buf;
  };

  /**
   * Converts big-endian float32 RGBA bytes to big-endian uint32 RGBA bytes natively.
   * @alias GeoPNG.native.convertF32ToU32RGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {number} arg1_mode - 0 = ceil, 1 = round
   *
   * @returns {Buffer|null}
   */
  GeoPNG.native.convertF32ToU32RGBA = function (arg0_in_rgba, arg1_mode) {
    //Convert from parameters
    let in_rgba = arg0_in_rgba;
    let mode = (arg1_mode === 0) ? 0 : 1;

    //Guard clauses
    if (!in_rgba || !GeoPNG.native.isAvailable()) return null;

    //Declare local instance variables
    let out_buf = Buffer.allocUnsafe(in_rgba.byteLength);
    let pixel_count = Math.floor(in_rgba.byteLength/4);

    //Function body
    GeoPNG.native._fn.svea_convert_f32_to_u32_be_rgba(in_rgba, out_buf, pixel_count, mode, GeoPNG.native.getThreadCount());

    //Return statement
    return out_buf;
  };

  /**
   * Expands a 2-pixel coastal fringe on a compact Int32Array mask grid natively.
   * @alias GeoPNG.native.expandMaskFringeI32
   *
   * @param {Int32Array} arg0_id_grid
   * @param {Uint8Array} arg1_src_mask
   * @param {Uint8Array|null} arg2_raw_land_mask
   * @param {number} arg3_width
   * @param {number} arg4_height
   *
   * @returns {boolean}
   */
  GeoPNG.native.expandMaskFringeI32 = function (arg0_id_grid, arg1_src_mask, arg2_raw_land_mask, arg3_width, arg4_height) {
    //Convert from parameters
    let id_grid = arg0_id_grid;
    let src_mask = arg1_src_mask;
    let raw_land_mask = arg2_raw_land_mask || null;
    let width = Number(arg3_width) || 4320;
    let height = Number(arg4_height) || 2160;

    //Guard clauses
    if (!id_grid || !src_mask || !GeoPNG.native.isAvailable()) return false;

    //Function body
    GeoPNG.native._fn.svea_expand_mask_fringe_i32(id_grid, src_mask, raw_land_mask, width, height, GeoPNG.native.getThreadCount());

    //Return statement
    return true;
  };

  /**
   * Returns configured BelowNormal C++ worker thread count (bounded so desktop/IDE cores stay free).
   * @alias GeoPNG.native.getThreadCount
   *
   * @returns {number}
   */
  GeoPNG.native.getThreadCount = function () {
    //Declare local instance variables
    let cfg_t = (GeoPNG.compute_limits && GeoPNG.compute_limits.native && GeoPNG.compute_limits.native.max_threads) ?
      Number(GeoPNG.compute_limits.native.max_threads) : 8;

    //Return statement
    return Math.max(1, Math.min(16, cfg_t));
  };

  /**
   * Loads svea_geopng_accel.dll via koffi and binds all native C++20 functions.
   * @alias GeoPNG.native.init
   *
   * @returns {boolean}
   */
  GeoPNG.native.init = function () {
    //Guard clauses
    if (GeoPNG.native._ready) return true;
    if (GeoPNG.native._init_attempted) return false;
    GeoPNG.native._init_attempted = true;

    if (GeoPNG.compute_limits && GeoPNG.compute_limits.native && GeoPNG.compute_limits.native.enabled === false)
      return false;
    if (typeof require === "undefined" || process.platform !== "win32") return false;
    if (typeof process !== "undefined" && process.type === "renderer") return false;

    //Declare local instance variables
    let fs_mod = (typeof global.fs !== "undefined") ? global.fs : require("fs");
    let path_mod = (typeof global.path !== "undefined") ? global.path : require("path");
    let candidates = [];
    let dll_path = null;

    if (typeof __dirname !== "undefined")
      candidates.push(path_mod.join(__dirname, "native", "svea_geopng_accel.dll"));
    if (typeof process !== "undefined" && process.cwd)
      candidates.push(path_mod.join(process.cwd(), "UF/js/geospatiale/files/png/native/svea_geopng_accel.dll"));
    if (typeof global.main_dir === "string")
      candidates.push(path_mod.join(global.main_dir, "UF/js/geospatiale/files/png/native/svea_geopng_accel.dll"));

    for (let i = 0; i < candidates.length; i++) {
      if (candidates[i] && fs_mod.existsSync(candidates[i])) {
        dll_path = candidates[i];
        break;
      }
    }
    if (!dll_path) {
      GeoPNG.native._init_error = "svea_geopng_accel.dll not found.";
      return false;
    }

    try {
      let koffi = require("koffi");
      let lib = koffi.load(dll_path);
      GeoPNG.native._fn = {
        svea_assign_pid_to_job: lib.func("int svea_assign_pid_to_job(uint32_t)"),
        svea_binary_op_be_rgba: lib.func("void svea_binary_op_be_rgba(const uint8_t*, const uint8_t*, _Out_ uint8_t*, int, uint32_t, uint32_t, uint32_t, float, float, float, float, int)"),
        svea_convert_f32_to_u32_be_rgba: lib.func("void svea_convert_f32_to_u32_be_rgba(const uint8_t*, _Out_ uint8_t*, int, uint32_t, int)"),
        svea_expand_mask_fringe_i32: lib.func("void svea_expand_mask_fringe_i32(_Inout_ int32_t*, const uint8_t*, const uint8_t*, int, int, int)"),
        svea_init_job_object: lib.func("int svea_init_job_object()"),
        svea_parse_asc_grid: lib.func("int svea_parse_asc_grid(const uint8_t*, size_t, _Out_ float*, int)"),
        svea_reconcile_demographics: lib.func("void svea_reconcile_demographics(const uint8_t*, const uint8_t*, const float*, const int32_t*, _Out_ uint8_t*, _Out_ uint8_t*, _Out_ uint8_t*, int, int, int)"),
        svea_reconcile_ghsl_modern: lib.func("void svea_reconcile_ghsl_modern(const uint8_t*, const uint8_t*, _Out_ uint8_t*, _Out_ uint8_t*, _Out_ uint8_t*, int, int)"),
        svea_regional_scale_be_rgba: lib.func("void svea_regional_scale_be_rgba(const uint8_t*, const int32_t*, const float*, _Out_ uint8_t*, int, int, float, int)"),
        svea_regional_sum_be_rgba: lib.func("void svea_regional_sum_be_rgba(const uint8_t*, const int32_t*, _Out_ double*, int, int, int, int)"),
        svea_scale_be_f32: lib.func("void svea_scale_be_f32(const uint8_t*, _Out_ uint8_t*, int, float, int)"),
        svea_set_process_below_normal: lib.func("int svea_set_process_below_normal()"),
        svea_shutdown: lib.func("void svea_shutdown()"),
        svea_sum_be_rgba: lib.func("double svea_sum_be_rgba(const uint8_t*, int, uint32_t, int, int)"),
        svea_threshold_clamp_be_f32: lib.func("void svea_threshold_clamp_be_f32(const uint8_t*, _Out_ uint8_t*, int, float, int)"),
        svea_velkscala_antiquity_overlay: lib.func("void svea_velkscala_antiquity_overlay(const uint8_t*, const uint8_t*, const uint8_t*, const float*, const float*, const uint32_t*, int, const uint32_t*, int, _Inout_ uint8_t*, _Inout_ uint8_t*, _Inout_ uint8_t*, _Inout_ uint8_t*, int, int, float, int, int)"),
        svea_viscount_mosaic_tent_blur: lib.func("void svea_viscount_mosaic_tent_blur(_Inout_ float*, const uint8_t*, const float*, const int32_t*, const int32_t*, const uint8_t*, int, int, int, int, int, int)")
      };
      GeoPNG.native._ready = true;
      GeoPNG.native._init_error = null;

      //Return statement
      return true;
    } catch (e) {
      GeoPNG.native._init_error = e.message || String(e);
      return false;
    }
  };

  /**
   * Returns true if the native C++20 accelerator DLL is loaded and ready.
   * @alias GeoPNG.native.isAvailable
   *
   * @returns {boolean}
   */
  GeoPNG.native.isAvailable = function () {
    //Function body
    if (!GeoPNG.native._ready && !GeoPNG.native._init_attempted)
      GeoPNG.native.init();

    //Return statement
    return Boolean(GeoPNG.native._ready);
  };

  /**
   * Parses an Esri ASCII (.asc) raster buffer directly into a Float32Array natively (170x faster than JS split).
   * @alias GeoPNG.native.parseAscGrid
   *
   * @param {Buffer|Uint8Array} arg0_buf
   * @param {number} arg1_total_pixels
   *
   * @returns {Float32Array|null}
   */
  GeoPNG.native.parseAscGrid = function (arg0_buf, arg1_total_pixels) {
    //Convert from parameters
    let buf = arg0_buf;
    let total_pixels = Math.max(0, Math.floor(Number(arg1_total_pixels) || 0));

    //Guard clauses
    if (!buf || total_pixels === 0 || !GeoPNG.native.isAvailable()) return null;

    //Declare local instance variables
    let out = new Float32Array(total_pixels);

    //Function body
    GeoPNG.native._fn.svea_parse_asc_grid(buf, buf.byteLength, out, total_pixels);

    //Return statement
    return out;
  };

  /**
   * Executes zero-alloc two-pass Stadestér demographic reconciliation natively on BelowNormal threads.
   * @alias GeoPNG.native.reconcileDemographicsRGBA
   *
   * @param {Object} arg0_params
   *
   * @returns {{rural_rgba: Buffer, total_rgba: Buffer, urban_rgba: Buffer}|null}
   */
  GeoPNG.native.reconcileDemographicsRGBA = function (arg0_params) {
    //Convert from parameters
    let params = (arg0_params) ? arg0_params : {};

    //Guard clauses
    if (!params.substrata_rgba || !params.urban_rgba || !params.sub_urban_f32 || !params.mask_ids || !GeoPNG.native.isAvailable())
      return null;

    //Declare local instance variables
    let bytes = params.substrata_rgba.byteLength;
    let num_masks = Math.max(1, Math.floor(Number(params.num_masks) || 1));
    let pixel_count = Math.floor(bytes/4);
    let rural_out = Buffer.allocUnsafe(bytes);
    let total_out = Buffer.allocUnsafe(bytes);
    let urban_out = Buffer.allocUnsafe(bytes);

    //Function body
    GeoPNG.native._fn.svea_reconcile_demographics(
      params.substrata_rgba,
      params.urban_rgba,
      params.sub_urban_f32,
      params.mask_ids,
      rural_out,
      urban_out,
      total_out,
      pixel_count,
      num_masks,
      GeoPNG.native.getThreadCount()
    );

    //Return statement
    return { rural_rgba: rural_out, total_rgba: total_out, urban_rgba: urban_out };
  };

  /**
   * Executes zero-alloc modern-era (1975-2025) GHSL-preserved reconciliation natively.
   * @alias GeoPNG.native.reconcileGHSLModernRGBA
   *
   * @param {Buffer|Uint8Array} arg0_substrata_rgba
   * @param {Buffer|Uint8Array} arg1_urban_rgba
   *
   * @returns {{rural_rgba: Buffer, total_rgba: Buffer, urban_rgba: Buffer}|null}
   */
  GeoPNG.native.reconcileGHSLModernRGBA = function (arg0_substrata_rgba, arg1_urban_rgba) {
    //Convert from parameters
    let substrata_rgba = arg0_substrata_rgba;
    let urban_rgba = arg1_urban_rgba;

    //Guard clauses
    if (!substrata_rgba || !urban_rgba || !GeoPNG.native.isAvailable()) return null;

    //Declare local instance variables
    let bytes = substrata_rgba.byteLength;
    let pixel_count = Math.floor(bytes/4);
    let rural_out = Buffer.allocUnsafe(bytes);
    let total_out = Buffer.allocUnsafe(bytes);
    let urban_out = Buffer.allocUnsafe(bytes);

    //Function body
    GeoPNG.native._fn.svea_reconcile_ghsl_modern(
      substrata_rgba,
      urban_rgba,
      rural_out,
      urban_out,
      total_out,
      pixel_count,
      GeoPNG.native.getThreadCount()
    );

    //Return statement
    return { rural_rgba: rural_out, total_rgba: total_out, urban_rgba: urban_out };
  };

  /**
   * Scales a big-endian float32 RGBA raster per Int32 region ID natively.
   * @alias GeoPNG.native.regionalScaleRGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {Int32Array} arg1_region_ids
   * @param {Float32Array} arg2_region_scalars
   * @param {number} [arg3_fallback_scalar=1]
   *
   * @returns {Buffer|null}
   */
  GeoPNG.native.regionalScaleRGBA = function (arg0_in_rgba, arg1_region_ids, arg2_region_scalars, arg3_fallback_scalar) {
    //Convert from parameters
    let in_rgba = arg0_in_rgba;
    let region_ids = arg1_region_ids;
    let region_scalars = arg2_region_scalars;
    let fallback_scalar = (arg3_fallback_scalar !== undefined) ? Number(arg3_fallback_scalar) : 1;

    //Guard clauses
    if (!in_rgba || !region_ids || !region_scalars || !GeoPNG.native.isAvailable()) return null;

    //Declare local instance variables
    let out_buf = Buffer.allocUnsafe(in_rgba.byteLength);
    let pixel_count = Math.floor(in_rgba.byteLength/4);

    //Function body
    GeoPNG.native._fn.svea_regional_scale_be_rgba(
      in_rgba, region_ids, region_scalars, out_buf, pixel_count, region_scalars.length, fallback_scalar, GeoPNG.native.getThreadCount()
    );

    //Return statement
    return out_buf;
  };

  /**
   * Computes fp64 per-region sums over a big-endian float32 RGBA raster natively.
   * @alias GeoPNG.native.regionalSumRGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {Int32Array} arg1_region_ids
   * @param {number} arg2_num_regions
   * @param {boolean} [arg3_positive_only=true]
   *
   * @returns {Float64Array|null}
   */
  GeoPNG.native.regionalSumRGBA = function (arg0_in_rgba, arg1_region_ids, arg2_num_regions, arg3_positive_only) {
    //Convert from parameters
    let in_rgba = arg0_in_rgba;
    let region_ids = arg1_region_ids;
    let num_regions = Math.max(1, Math.floor(Number(arg2_num_regions) || 1));
    let positive_only = (arg3_positive_only !== false) ? 1 : 0;

    //Guard clauses
    if (!in_rgba || !region_ids || !GeoPNG.native.isAvailable()) return null;

    //Declare local instance variables
    let out_sums = new Float64Array(num_regions);
    let pixel_count = Math.floor(in_rgba.byteLength/4);

    //Function body
    GeoPNG.native._fn.svea_regional_sum_be_rgba(
      in_rgba, region_ids, out_sums, pixel_count, num_regions, positive_only, GeoPNG.native.getThreadCount()
    );

    //Return statement
    return out_sums;
  };

  /**
   * Scales a big-endian float32 RGBA raster by a scalar natively.
   * @alias GeoPNG.native.scaleRGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {number} arg1_scalar
   *
   * @returns {Buffer|null}
   */
  GeoPNG.native.scaleRGBA = function (arg0_in_rgba, arg1_scalar) {
    //Convert from parameters
    let in_rgba = arg0_in_rgba;
    let scalar = Number(arg1_scalar);

    //Guard clauses
    if (!in_rgba || !Number.isFinite(scalar) || !GeoPNG.native.isAvailable()) return null;

    //Declare local instance variables
    let out_buf = Buffer.allocUnsafe(in_rgba.byteLength);
    let pixel_count = Math.floor(in_rgba.byteLength/4);

    //Function body
    GeoPNG.native._fn.svea_scale_be_f32(in_rgba, out_buf, pixel_count, scalar, GeoPNG.native.getThreadCount());

    //Return statement
    return out_buf;
  };

  /**
   * Cleanly joins C++ worker threads, frees scratch pools, and closes the Win32 Job Object handle.
   * @alias GeoPNG.native.shutdown
   */
  GeoPNG.native.shutdown = function () {
    //Guard clause
    if (!GeoPNG.native._ready || !GeoPNG.native._fn) return;

    try { GeoPNG.native._fn.svea_shutdown(); } catch (e) {}
  };

  /**
   * Computes fp64 global sum over a big-endian RGBA raster natively.
   * @alias GeoPNG.native.sumRGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {number} arg1_fmt
   * @param {boolean} arg2_positive_only
   *
   * @returns {number|null}
   */
  GeoPNG.native.sumRGBA = function (arg0_in_rgba, arg1_fmt, arg2_positive_only) {
    //Convert from parameters
    let in_rgba = arg0_in_rgba;
    let fmt = arg1_fmt >>> 0;
    let positive_only = arg2_positive_only ? 1 : 0;

    //Guard clauses
    if (!in_rgba || !GeoPNG.native.isAvailable()) return null;

    //Declare local instance variables
    let pixel_count = Math.floor(in_rgba.byteLength/4);

    //Return statement
    return GeoPNG.native._fn.svea_sum_be_rgba(in_rgba, pixel_count, fmt, positive_only, GeoPNG.native.getThreadCount());
  };

  /**
   * Clamps a big-endian float32 RGBA raster below min_val to 0 natively.
   * @alias GeoPNG.native.thresholdClampRGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {number} [arg1_min_val=0.01]
   *
   * @returns {Buffer|null}
   */
  GeoPNG.native.thresholdClampRGBA = function (arg0_in_rgba, arg1_min_val) {
    //Convert from parameters
    let in_rgba = arg0_in_rgba;
    let min_val = (arg1_min_val !== undefined) ? Number(arg1_min_val) : 0.01;

    //Guard clauses
    if (!in_rgba || !GeoPNG.native.isAvailable()) return null;

    //Declare local instance variables
    let out_buf = Buffer.allocUnsafe(in_rgba.byteLength);
    let pixel_count = Math.floor(in_rgba.byteLength/4);

    //Function body
    GeoPNG.native._fn.svea_threshold_clamp_be_f32(in_rgba, out_buf, pixel_count, min_val, GeoPNG.native.getThreadCount());

    //Return statement
    return out_buf;
  };

  /**
   * Executes sparse zero-alloc Velkscala antiquity harmonic diffusion + Viscount overlay natively (~1,5 ms).
   * @alias GeoPNG.native.velkscalaAntiquityOverlayRGBA
   *
   * @param {Object} arg0_params
   *
   * @returns {{popc_rgba: Buffer, popd_rgba: Buffer, rurc_rgba: Buffer, urbc_rgba: Buffer}|null}
   */
  GeoPNG.native.velkscalaAntiquityOverlayRGBA = function (arg0_params) {
    //Convert from parameters
    let p = (arg0_params) ? arg0_params : {};

    //Guard clauses
    if (!p.grid_a_rgba || !p.grid_b_rgba || !p.popc_rgba || !p.urbc_rgba || !p.rurc_rgba || !p.popd_rgba ||
      !p.owner_grid || !p.land_area || !p.bfs_dist || !p.viscount_pixels || !GeoPNG.native.isAvailable()) {
      return null;
    }

    //Declare local instance variables
    let height = Number(p.height) || 2160;
    let popc_out = Buffer.from(p.popc_rgba);
    let popd_out = Buffer.from(p.popd_rgba);
    let rurc_out = Buffer.from(p.rurc_rgba);
    let seam_cnt = (p.seam_pixels) ? p.seam_pixels.length : 0;
    let seam_u32 = (p.seam_pixels instanceof Uint32Array) ? p.seam_pixels : Uint32Array.from(p.seam_pixels || []);
    let urbc_out = Buffer.from(p.urbc_rgba);
    let vis_u32 = (p.viscount_pixels instanceof Uint32Array) ? p.viscount_pixels : Uint32Array.from(p.viscount_pixels);
    let width = Number(p.width) || 4320;

    //Function body
    GeoPNG.native._fn.svea_velkscala_antiquity_overlay(
      p.grid_a_rgba,
      p.grid_b_rgba,
      p.owner_grid,
      p.land_area,
      p.bfs_dist,
      seam_u32,
      seam_cnt,
      vis_u32,
      vis_u32.length,
      urbc_out,
      popc_out,
      rurc_out,
      popd_out,
      width,
      height,
      Number(p.frac) || 0,
      Number(p.seam_px) || 16,
      GeoPNG.native.getThreadCount()
    );

    //Return statement
    return {
      popc_rgba: popc_out,
      popd_rgba: popd_out,
      rurc_rgba: rurc_out,
      urbc_rgba: urbc_out
    };
  };

  /**
   * Executes domain-gated separable tent blur for ViscountSubstrataMosaic natively.
   * @alias GeoPNG.native.viscountMosaicTentBlur
   *
   * @param {Float32Array} arg0_log_mult
   * @param {Uint8Array} arg1_touched
   * @param {Float32Array} arg2_base_rural
   * @param {Int32Array} arg3_valid_indices
   * @param {Int32Array} arg4_pixel_to_valid
   * @param {Uint8Array} arg5_pixel_domain
   * @param {number} arg6_width
   * @param {number} arg7_height
   * @param {number} arg8_blur_r
   * @param {number} arg9_blur_passes
   *
   * @returns {boolean}
   */
  GeoPNG.native.viscountMosaicTentBlur = function (
    arg0_log_mult, arg1_touched, arg2_base_rural, arg3_valid_indices, arg4_pixel_to_valid,
    arg5_pixel_domain, arg6_width, arg7_height, arg8_blur_r, arg9_blur_passes
  ) {
    //Guard clauses
    if (!arg0_log_mult || !arg1_touched || !arg2_base_rural || !GeoPNG.native.isAvailable())
      return false;

    //Function body
    GeoPNG.native._fn.svea_viscount_mosaic_tent_blur(
      arg0_log_mult,
      arg1_touched,
      arg2_base_rural,
      arg3_valid_indices,
      arg4_pixel_to_valid,
      arg5_pixel_domain,
      arg0_log_mult.length,
      Number(arg6_width) || 4320,
      Number(arg7_height) || 2160,
      Number(arg8_blur_r) || 5,
      Number(arg9_blur_passes) || 3,
      GeoPNG.native.getThreadCount()
    );

    //Return statement
    return true;
  };

  GeoPNG.governor.registerLifecycleHooks();
}
