//Initialise GeoPNG GPU Compute & Resource Governance Framework
{
  if (!global.GeoPNG)
    /**
     * Analogous to a GeoTIFF file format, but in PNG form for easier editing. Single variable. Part of Geospatiale III.
     *
     * @namespace GeoPNG
     */
    global.GeoPNG = {};

  if (typeof require !== "undefined" && (!global.GeoPNG.gpu || !global.GeoPNG.gpu._opencl_kernel_source)) {
    try { require("./png_gpu_kernels.js"); } catch (e) {}
  }

  /**
   * Default resource constraints loaded from /common/defines/geopng_compute.json5 when available.
   *
   * @namespace GeoPNG.compute_limits
   */
  GeoPNG.compute_limits = {
    cpu: {
      cooperative_yield_ms: 4,
      max_workers: 4,
      priority_below_normal: true,
      sharp_concurrency: 2
    },
    gpu: {
      enabled: true,
      max_dispatch_pixels: 2332800,
      max_vram_mb: 2048,
      min_pixels: 65536,
      pacing_ms: 2,
      preferred_vendor: "NVIDIA",
      workgroup_size: 256
    },
    io: {
      png_compression_level: 1,
      png_filter_type: 0,
      use_sharp: true
    },
    ram: {
      max_cached_rasters: 8,
      max_ram_mb: 4096
    }
  };

  /**
   * Applies below-normal CPU priority to background pipelines to preserve desktop & UI FPS.
   * @alias GeoPNG.applyBackgroundProcessPriority
   *
   * @returns {boolean}
   */
  GeoPNG.applyBackgroundProcessPriority = function () {
    //Guard clauses
    if (!GeoPNG.compute_limits.cpu.priority_below_normal) return false;
    if (typeof require === "undefined") return false;
    if (typeof process !== "undefined" && process.type === "renderer") return false;

    try {
      let os_mod = require("os");
      if (os_mod && typeof os_mod.setPriority === "function" && os_mod.constants && os_mod.constants.priority) {
        os_mod.setPriority(0, os_mod.constants.priority.PRIORITY_BELOW_NORMAL);
        return true;
      }
    } catch (e) {}

    //Return statement
    return false;
  };

  /**
   * Decodes big-endian RGBA bytes into a Float64Array or Float32Array with zero per-pixel JS array allocations.
   * @alias GeoPNG.decodeRGBABufferFast
   *
   * @param {Buffer|Uint8Array} arg0_rgba
   * @param {Object} [arg1_options]
   *  @param {string} [arg1_options.format="int32"]
   *  @param {boolean} [arg1_options.float32_output=false]
   *
   * @returns {Float64Array|Float32Array}
   */
  GeoPNG.decodeRGBABufferFast = function (arg0_rgba, arg1_options) {
    //Convert from parameters
    let options = (arg1_options) ? arg1_options : {};
    let rgba = arg0_rgba;

    //Declare local instance variables
    let dv = new DataView(rgba.buffer, rgba.byteOffset, rgba.byteLength);
    let format = options.format || "int32";
    let pixel_count = Math.floor(rgba.byteLength/4);
    let out = (options.float32_output) ? new Float32Array(pixel_count) : new Float64Array(pixel_count);

    if (format === "float32") {
      for (let i = 0; i < pixel_count; i++) {
        let p4 = i*4;
        if ((rgba[p4] | rgba[p4 + 1] | rgba[p4 + 2] | rgba[p4 + 3]) === 0) continue;
        let v = dv.getFloat32(p4, false);
        out[i] = Number.isFinite(v) ? v : 0;
      }
    } else if (format === "greyscale") {
      for (let i = 0; i < pixel_count; i++)
        out[i] = rgba[i*4]/255;
    } else {
      for (let i = 0; i < pixel_count; i++)
        out[i] = dv.getUint32(i*4, false);
    }

    //Return statement
    return out;
  };

  /**
   * Encodes a numeric TypedArray into big-endian RGBA bytes with zero per-pixel JS array allocations.
   * @alias GeoPNG.encodeNumberBufferFast
   *
   * @param {Float32Array|Float64Array|Int32Array|Uint32Array} arg0_values
   * @param {Object} [arg1_options]
   *  @param {string} [arg1_options.format="int32"]
   *
   * @returns {Buffer}
   */
  GeoPNG.encodeNumberBufferFast = function (arg0_values, arg1_options) {
    //Convert from parameters
    let options = (arg1_options) ? arg1_options : {};
    let values = arg0_values;

    //Declare local instance variables
    let format = options.format || "int32";
    let pixel_count = values.length;
    let out = Buffer.alloc(pixel_count*4);
    let dv = new DataView(out.buffer, out.byteOffset, out.byteLength);

    if (format === "float32") {
      for (let i = 0; i < pixel_count; i++) {
        let v = values[i];
        if (v && Number.isFinite(v)) dv.setFloat32(i*4, v, false);
      }
    } else if (format === "greyscale") {
      for (let i = 0; i < pixel_count; i++) {
        let g = Math.max(0, Math.min(255, Math.floor((values[i] || 0)*255)));
        let p4 = i*4;
        out[p4] = g;
        out[p4 + 1] = g;
        out[p4 + 2] = g;
        out[p4 + 3] = 255;
      }
    } else {
      for (let i = 0; i < pixel_count; i++) {
        let v = values[i];
        if (v && Number.isFinite(v)) dv.setUint32(i*4, Math.ceil(v) >>> 0, false);
      }
    }

    //Return statement
    return out;
  };

  /**
   * Enforces the configured soft RAM ceiling by trimming pooled buffers and triggering GC when exposed.
   * @alias GeoPNG.enforceMemoryBudget
   *
   * @returns {{rss_mb: number, trimmed: boolean}}
   */
  GeoPNG.enforceMemoryBudget = function () {
    //Guard clause
    if (typeof process === "undefined" || typeof process.memoryUsage !== "function")
      return { rss_mb: 0, trimmed: false };

    //Declare local instance variables
    let max_ram_mb = Number(GeoPNG.compute_limits.ram.max_ram_mb) || 4096;
    let rss_mb = process.memoryUsage().rss/1048576;
    let trimmed = false;

    if (rss_mb > max_ram_mb) {
      if (GeoPNG.gpu && typeof GeoPNG.gpu.trimPools === "function") {
        GeoPNG.gpu.trimPools();
        trimmed = true;
      }
      if (typeof global.gc === "function") {
        try { global.gc(); } catch (e) {}
      }
    }

    //Return statement
    return { rss_mb: Number(rss_mb.toFixed(1)), trimmed: trimmed };
  };

  /**
   * Returns the configured sharp instance with bounded concurrency, or null if unavailable.
   * @alias GeoPNG.getSharp
   *
   * @returns {Function|null}
   */
  GeoPNG.getSharp = function () {
    //Guard clauses
    if (!GeoPNG.compute_limits.io.use_sharp) return null;
    if (GeoPNG._sharp_checked) return GeoPNG._sharp_mod || null;

    GeoPNG._sharp_checked = true;
    if (typeof require === "undefined") return null;

    try {
      let sharp_mod = require("sharp");
      if (sharp_mod) {
        let conc = Math.max(1, Math.min(4, Number(GeoPNG.compute_limits.cpu.sharp_concurrency) || 2));
        if (typeof sharp_mod.concurrency === "function") sharp_mod.concurrency(conc);
        if (typeof sharp_mod.cache === "function") sharp_mod.cache(false);
        GeoPNG._sharp_mod = sharp_mod;
      }
    } catch (e) {
      GeoPNG._sharp_mod = null;
    }

    //Return statement
    return GeoPNG._sharp_mod || null;
  };

  /**
   * Loads compute governance limits from common/defines/geopng_compute.json5.
   * @alias GeoPNG.loadComputeLimits
   *
   * @param {Object} [arg0_overrides]
   *
   * @returns {Object}
   */
  GeoPNG.loadComputeLimits = function (arg0_overrides) {
    //Convert from parameters
    let overrides = (arg0_overrides) ? arg0_overrides : {};

    //Declare local instance variables
    let cfg_candidates = [];
    let fs_mod = (typeof global.fs !== "undefined") ? global.fs : ((typeof require !== "undefined") ? require("fs") : null);
    let json5_mod = (typeof global.JSON5 !== "undefined") ? global.JSON5 : null;
    let path_mod = (typeof global.path !== "undefined") ? global.path : ((typeof require !== "undefined") ? require("path") : null);

    if (!json5_mod && typeof require !== "undefined") {
      try { json5_mod = require("json5"); } catch (e) {}
    }

    if (fs_mod && path_mod) {
      if (typeof process !== "undefined" && process.cwd)
        cfg_candidates.push(path_mod.join(process.cwd(), "common/defines/geopng_compute.json5"));
      if (typeof __dirname !== "undefined")
        cfg_candidates.push(path_mod.resolve(__dirname, "../../../../../common/defines/geopng_compute.json5"));
      if (typeof global.main_dir === "string")
        cfg_candidates.push(path_mod.join(global.main_dir, "common/defines/geopng_compute.json5"));

      for (let i = 0; i < cfg_candidates.length; i++) {
        let cand = cfg_candidates[i];
        if (cand && fs_mod.existsSync(cand)) {
          try {
            let raw_text = fs_mod.readFileSync(cand, "utf8");
            let parsed = (json5_mod) ? json5_mod.parse(raw_text) : JSON.parse(raw_text);
            if (parsed && typeof parsed === "object") {
              if (parsed.cpu) Object.assign(GeoPNG.compute_limits.cpu, parsed.cpu);
              if (parsed.gpu) Object.assign(GeoPNG.compute_limits.gpu, parsed.gpu);
              if (parsed.io) Object.assign(GeoPNG.compute_limits.io, parsed.io);
              if (parsed.ram) Object.assign(GeoPNG.compute_limits.ram, parsed.ram);
            }
            break;
          } catch (e) {}
        }
      }
    }

    if (overrides.cpu) Object.assign(GeoPNG.compute_limits.cpu, overrides.cpu);
    if (overrides.gpu) Object.assign(GeoPNG.compute_limits.gpu, overrides.gpu);
    if (overrides.io) Object.assign(GeoPNG.compute_limits.io, overrides.io);
    if (overrides.ram) Object.assign(GeoPNG.compute_limits.ram, overrides.ram);

    //Return statement
    return GeoPNG.compute_limits;
  };

  /**
   * Loads raw lossless RGBA bytes from a PNG file using native sharp (fallback: pngjs).
   * @alias GeoPNG.loadRawRGBAAsync
   *
   * @param {string} arg0_file_path
   *
   * @returns {Promise<{data: Buffer, height: number, width: number}|null>}
   */
  GeoPNG.loadRawRGBAAsync = async function (arg0_file_path) {
    //Convert from parameters
    let file_path = arg0_file_path;

    //Guard clauses
    if (!file_path || typeof file_path !== "string") return null;

    //Declare local instance variables
    let fs_mod = (typeof global.fs !== "undefined") ? global.fs : require("fs");
    let sharp_mod = GeoPNG.getSharp();

    try {
      let stat = await fs_mod.promises.stat(file_path);
      if (stat.size < 8) return null;

      let raw_file = await fs_mod.promises.readFile(file_path);
      if (sharp_mod) {
        let out = await sharp_mod(raw_file, { limitInputPixels: false })
          .ensureAlpha()
          .raw()
          .toBuffer({ resolveWithObject: true });

        //Return statement
        return { data: out.data, height: out.info.height, width: out.info.width };
      }

      let png_lib = (typeof global.pngjs !== "undefined") ? global.pngjs : require("pngjs");
      let parsed = await new Promise((resolve, reject) => {
        new png_lib.PNG().parse(raw_file, (err, data) => (err) ? reject(err) : resolve(data));
      });

      //Return statement
      return { data: parsed.data, height: parsed.height, width: parsed.width };
    } catch (err) {
      console.error(`- [GeoPNG.loadRawRGBAAsync] Failed to load ${file_path}:`, err.message || err);
      return null;
    }
  };

  /**
   * Saves raw lossless RGBA bytes to a PNG file using native sharp (fallback: pngjs filterType 0).
   * @alias GeoPNG.saveRawRGBAAsync
   *
   * @param {Object} arg0_options
   *  @param {Buffer|Uint8Array} arg0_options.data
   *  @param {string} arg0_options.file_path
   *  @param {number} arg0_options.height
   *  @param {number} arg0_options.width
   *
   * @returns {Promise<string|null>}
   */
  GeoPNG.saveRawRGBAAsync = async function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let data = options.data;
    let file_path = options.file_path;
    let fs_mod = (typeof global.fs !== "undefined") ? global.fs : require("fs");
    let height = Number(options.height) || 2160;
    let path_mod = (typeof global.path !== "undefined") ? global.path : require("path");
    let sharp_mod = GeoPNG.getSharp();
    let width = Number(options.width) || 4320;

    //Guard clauses
    if (!data || !file_path) return null;

    let parent_dir = path_mod.dirname(path_mod.resolve(file_path));
    if (!fs_mod.existsSync(parent_dir))
      await fs_mod.promises.mkdir(parent_dir, { recursive: true });

    let buf = Buffer.isBuffer(data) ? data : Buffer.from(data.buffer, data.byteOffset, data.byteLength);

    if (sharp_mod) {
      let comp_lvl = Math.max(0, Math.min(9, Number(GeoPNG.compute_limits.io.png_compression_level) || 1));
      let out_png = await sharp_mod(buf, {
        limitInputPixels: false,
        raw: { channels: 4, height: height, width: width }
      }).png({
        adaptiveFiltering: false,
        compressionLevel: comp_lvl,
        force: true
      }).toBuffer();
      await fs_mod.promises.writeFile(file_path, out_png);

      //Return statement
      return file_path;
    }

    let png_lib = (typeof global.pngjs !== "undefined") ? global.pngjs : require("pngjs");
    let filter_type = (GeoPNG.compute_limits.io.png_filter_type !== undefined) ? GeoPNG.compute_limits.io.png_filter_type : 0;
    let png = new png_lib.PNG({ filterType: filter_type, height: height, width: width });
    png.data.set(buf.subarray(0, png.data.length));
    let packed = png_lib.PNG.sync.write(png, { filterType: filter_type });
    await fs_mod.promises.writeFile(file_path, packed);

    //Return statement
    return file_path;
  };

  /**
   * Pure Node.js OpenCL 3.0 GPU compute backend (via koffi -> OpenCL.dll -> NVIDIA CUDA).
   * Offloads matrix/raster operations to the NVIDIA GPU with strict VRAM, wave-pacing, and RAM bounds.
   *
   * @namespace GeoPNG.gpu
   */
  let preserved_kernel_src = (GeoPNG.gpu && GeoPNG.gpu._opencl_kernel_source) ? GeoPNG.gpu._opencl_kernel_source : "";
  GeoPNG.gpu = {
    _allocated_vram_bytes: 0,
    _buffer_pool: new Map(),
    _cl: null,
    _ctx: null,
    _device: null,
    _device_info: null,
    _init_attempted: false,
    _init_error: null,
    _kernels: {},
    _mutex: Promise.resolve(),
    _opencl_kernel_source: preserved_kernel_src,
    _program: null,
    _queue: null,
    _ready: false
  };

  /**
   * Acquires or reuses a VRAM buffer from the bounded pool under max_vram_mb governance.
   * @alias GeoPNG.gpu.acquireBuffer
   *
   * @param {string} arg0_tag
   * @param {number} arg1_byte_length
   * @param {BigInt} [arg2_flags=1n]
   *
   * @returns {Object|null}
   */
  GeoPNG.gpu.acquireBuffer = function (arg0_tag, arg1_byte_length, arg2_flags) {
    //Convert from parameters
    let byte_length = Math.max(16, Math.ceil(Number(arg1_byte_length) || 16));
    let flags = (arg2_flags !== undefined) ? arg2_flags : 1n;
    let tag = String(arg0_tag || "scratch");

    //Declare local instance variables
    let cl = GeoPNG.gpu._cl;
    let err = [0];
    let existing = GeoPNG.gpu._buffer_pool.get(`${tag}_${flags.toString()}`);
    let key = `${tag}_${flags.toString()}`;
    let max_vram_bytes = (Number(GeoPNG.compute_limits.gpu.max_vram_mb) || 2048)*1048576;

    //Guard clause
    if (!GeoPNG.gpu._ready || !cl || !GeoPNG.gpu._ctx) return null;

    if (existing && existing.size >= byte_length && existing.size <= byte_length*2)
      return existing;

    if (existing) {
      try { cl.clReleaseMemObject(existing.mem); } catch (e) {}
      GeoPNG.gpu._allocated_vram_bytes = Math.max(0, GeoPNG.gpu._allocated_vram_bytes - existing.size);
      GeoPNG.gpu._buffer_pool.delete(key);
    }

    if (GeoPNG.gpu._allocated_vram_bytes + byte_length > max_vram_bytes) {
      for (let [old_key, old_entry] of GeoPNG.gpu._buffer_pool.entries()) {
        if (old_entry.pinned) continue;
        try { cl.clReleaseMemObject(old_entry.mem); } catch (e) {}
        GeoPNG.gpu._allocated_vram_bytes = Math.max(0, GeoPNG.gpu._allocated_vram_bytes - old_entry.size);
        GeoPNG.gpu._buffer_pool.delete(old_key);
        if (GeoPNG.gpu._allocated_vram_bytes + byte_length <= max_vram_bytes) break;
      }
    }

    if (GeoPNG.gpu._allocated_vram_bytes + byte_length > max_vram_bytes) {
      console.error(`- [GeoPNG.gpu] VRAM budget (${GeoPNG.compute_limits.gpu.max_vram_mb} MiB) exceeded for buffer '${tag}'.`);
      return null;
    }

    let mem = cl.clCreateBuffer(GeoPNG.gpu._ctx, flags, byte_length, null, err);
    if (!mem || err[0] !== 0) {
      console.error(`- [GeoPNG.gpu] clCreateBuffer failed for '${tag}' (err=${err[0]}).`);
      return null;
    }

    let entry = { flags: flags, mem: mem, pinned: false, size: byte_length, tag: tag };
    GeoPNG.gpu._allocated_vram_bytes += byte_length;
    GeoPNG.gpu._buffer_pool.set(key, entry);

    //Return statement
    return entry;
  };

  /**
   * Executes a 1D kernel in bounded GPU waves with WDDM-friendly inter-wave pacing.
   * @alias GeoPNG.gpu.dispatchWaves
   *
   * @param {number} arg0_total_items
   * @param {function} arg1_enqueue_fn
   *
   * @returns {Promise<void>}
   */
  GeoPNG.gpu.dispatchWaves = async function (arg0_total_items, arg1_enqueue_fn) {
    //Convert from parameters
    let enqueue_fn = arg1_enqueue_fn;
    let total_items = Math.max(0, Math.floor(Number(arg0_total_items) || 0));

    //Guard clause
    if (total_items === 0 || typeof enqueue_fn !== "function") return;

    //Declare local instance variables
    let cl = GeoPNG.gpu._cl;
    let local_size = Math.max(32, Number(GeoPNG.compute_limits.gpu.workgroup_size) || 256);
    let max_wave = Math.max(local_size, Number(GeoPNG.compute_limits.gpu.max_dispatch_pixels) || 2332800);
    let pacing_ms = Math.max(0, Number(GeoPNG.compute_limits.gpu.pacing_ms) || 0);

    for (let offset = 0; offset < total_items; offset += max_wave) {
      let count = Math.min(max_wave, total_items - offset);
      let global_size = Math.ceil(count/local_size)*local_size;

      enqueue_fn(offset, count, global_size, local_size);
      cl.clFinish(GeoPNG.gpu._queue);

      if (pacing_ms > 0 && offset + count < total_items)
        await new Promise((resolve) => setTimeout(resolve, pacing_ms));
    }
  };

  /**
   * Returns runtime telemetry and active GPU device info.
   * @alias GeoPNG.gpu.getStatus
   *
   * @returns {Object}
   */
  GeoPNG.gpu.getStatus = function () {
    //Return statement
    return {
      allocated_vram_mb: Number((GeoPNG.gpu._allocated_vram_bytes/1048576).toFixed(1)),
      device_info: GeoPNG.gpu._device_info,
      error: GeoPNG.gpu._init_error,
      limits: GeoPNG.compute_limits,
      pooled_buffers: GeoPNG.gpu._buffer_pool.size,
      ready: GeoPNG.gpu._ready
    };
  };

  /**
   * Initialises the NVIDIA OpenCL 3.0 device, command queue, and precompiles all GeoPNG kernels.
   * @alias GeoPNG.gpu.init
   *
   * @param {Object} [arg0_options]
   *
   * @returns {boolean}
   */
  GeoPNG.gpu.init = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Guard clauses
    if (GeoPNG.gpu._ready) return true;
    if (GeoPNG.gpu._init_attempted && !options.force) return false;
    GeoPNG.gpu._init_attempted = true;

    GeoPNG.loadComputeLimits(options);
    if (!GeoPNG.compute_limits.gpu.enabled) return false;
    if (typeof require === "undefined") return false;
    if (typeof process !== "undefined" && process.type === "renderer" && !options.allow_in_renderer)
      return false;

    if (!GeoPNG.gpu._opencl_kernel_source) {
      try { require("./png_gpu_kernels.js"); } catch (e) {}
    }
    if (!GeoPNG.gpu._opencl_kernel_source) {
      GeoPNG.gpu._init_error = "OpenCL kernel source unavailable.";
      return false;
    }

    try {
      let koffi = require("koffi");
      let ocl = koffi.load("OpenCL.dll");
      let cl = {
        clBuildProgram: ocl.func("int clBuildProgram(void*, uint32_t, void**, const char*, void*, void*)"),
        clCreateBuffer: ocl.func("void* clCreateBuffer(void*, uint64_t, size_t, void*, _Out_ int*)"),
        clCreateCommandQueue: ocl.func("void* clCreateCommandQueue(void*, void*, uint64_t, _Out_ int*)"),
        clCreateContext: ocl.func("void* clCreateContext(void*, uint32_t, void**, void*, void*, _Out_ int*)"),
        clCreateKernel: ocl.func("void* clCreateKernel(void*, const char*, _Out_ int*)"),
        clCreateProgramWithSource: ocl.func("void* clCreateProgramWithSource(void*, uint32_t, const char**, const size_t*, _Out_ int*)"),
        clEnqueueFillBuffer: ocl.func("int clEnqueueFillBuffer(void*, void*, void*, size_t, size_t, size_t, uint32_t, void*, void*)"),
        clEnqueueNDRangeKernel: ocl.func("int clEnqueueNDRangeKernel(void*, void*, uint32_t, size_t*, size_t*, size_t*, uint32_t, void*, void*)"),
        clEnqueueReadBuffer: ocl.func("int clEnqueueReadBuffer(void*, void*, uint32_t, size_t, size_t, _Out_ uint8_t*, uint32_t, void*, void*)"),
        clEnqueueWriteBuffer: ocl.func("int clEnqueueWriteBuffer(void*, void*, uint32_t, size_t, size_t, void*, uint32_t, void*, void*)"),
        clFinish: ocl.func("int clFinish(void*)"),
        clGetDeviceIDs: ocl.func("int clGetDeviceIDs(void*, uint64_t, uint32_t, _Out_ void**, _Out_ uint32_t*)"),
        clGetDeviceInfo: ocl.func("int clGetDeviceInfo(void*, uint32_t, size_t, _Out_ uint8_t*, _Out_ size_t*)"),
        clGetPlatformIDs: ocl.func("int clGetPlatformIDs(uint32_t, _Out_ void**, _Out_ uint32_t*)"),
        clGetPlatformInfo: ocl.func("int clGetPlatformInfo(void*, uint32_t, size_t, _Out_ uint8_t*, _Out_ size_t*)"),
        clGetProgramBuildInfo: ocl.func("int clGetProgramBuildInfo(void*, void*, uint32_t, size_t, _Out_ uint8_t*, _Out_ size_t*)"),
        clReleaseCommandQueue: ocl.func("int clReleaseCommandQueue(void*)"),
        clReleaseContext: ocl.func("int clReleaseContext(void*)"),
        clReleaseKernel: ocl.func("int clReleaseKernel(void*)"),
        clReleaseMemObject: ocl.func("int clReleaseMemObject(void*)"),
        clReleaseProgram: ocl.func("int clReleaseProgram(void*)"),
        clSetKernelArgF32: ocl.func("int clSetKernelArg(void*, uint32_t, size_t, float*)"),
        clSetKernelArgMem: ocl.func("int clSetKernelArg(void*, uint32_t, size_t, void**)"),
        clSetKernelArgU32: ocl.func("int clSetKernelArg(void*, uint32_t, size_t, uint32_t*)")
      };

      let num_plats = [0];
      if (cl.clGetPlatformIDs(0, null, num_plats) !== 0 || num_plats[0] <= 0) {
        GeoPNG.gpu._init_error = "No OpenCL platforms detected.";
        return false;
      }

      let plats = new Array(num_plats[0]).fill(null);
      cl.clGetPlatformIDs(num_plats[0], plats, num_plats);

      let info_buf = Buffer.alloc(1024);
      let pref_vendor = String(GeoPNG.compute_limits.gpu.preferred_vendor || "NVIDIA").toUpperCase();
      let selected_dev = null;
      let selected_info = null;
      let sz = [0];

      for (let i = 0; i < num_plats[0]; i++) {
        cl.clGetPlatformInfo(plats[i], 0x0902, 1024, info_buf, sz);
        let plat_name = info_buf.toString("utf8", 0, Math.max(0, sz[0] - 1));
        let num_devs = [0];

        if (cl.clGetDeviceIDs(plats[i], 4n, 0, null, num_devs) !== 0 || num_devs[0] <= 0)
          continue;

        let devs = new Array(num_devs[0]).fill(null);
        cl.clGetDeviceIDs(plats[i], 4n, num_devs[0], devs, num_devs);
        cl.clGetDeviceInfo(devs[0], 0x102B, 1024, info_buf, sz);
        let dev_name = info_buf.toString("utf8", 0, Math.max(0, sz[0] - 1));

        let cu_buf = Buffer.alloc(4);
        cl.clGetDeviceInfo(devs[0], 0x1002, 4, cu_buf, sz);
        let vram_buf = Buffer.alloc(8);
        cl.clGetDeviceInfo(devs[0], 0x101F, 8, vram_buf, sz);

        let is_pref = plat_name.toUpperCase().includes(pref_vendor) || dev_name.toUpperCase().includes(pref_vendor);
        if (!selected_dev || is_pref) {
          selected_dev = devs[0];
          selected_info = {
            compute_units: cu_buf.readUInt32LE(0),
            device: dev_name,
            platform: plat_name,
            vram_mb: Math.round(Number(vram_buf.readBigUInt64LE(0))/1048576)
          };
          if (is_pref) break;
        }
      }

      if (!selected_dev) {
        GeoPNG.gpu._init_error = "No OpenCL GPU device available.";
        return false;
      }

      let err = [0];
      let ctx = cl.clCreateContext(null, 1, [selected_dev], null, null, err);
      if (!ctx || err[0] !== 0) {
        GeoPNG.gpu._init_error = `clCreateContext failed (${err[0]})`;
        return false;
      }

      let queue = cl.clCreateCommandQueue(ctx, selected_dev, 0n, err);
      if (!queue || err[0] !== 0) {
        cl.clReleaseContext(ctx);
        GeoPNG.gpu._init_error = `clCreateCommandQueue failed (${err[0]})`;
        return false;
      }

      let prog = cl.clCreateProgramWithSource(ctx, 1, [GeoPNG.gpu._opencl_kernel_source], null, err);
      let brc = cl.clBuildProgram(prog, 1, [selected_dev], "-cl-mad-enable", null, null);
      if (brc !== 0) {
        let log_buf = Buffer.alloc(16384);
        cl.clGetProgramBuildInfo(prog, selected_dev, 0x1183, 16384, log_buf, sz);
        GeoPNG.gpu._init_error = `OpenCL build failed (${brc}): ${log_buf.toString("utf8", 0, sz[0])}`;
        console.error(`- [GeoPNG.gpu] ${GeoPNG.gpu._init_error}`);
        cl.clReleaseProgram(prog);
        cl.clReleaseCommandQueue(queue);
        cl.clReleaseContext(ctx);
        return false;
      }

      let kernel_names = [
        "accumulate_positive_f32",
        "binary_op_be_rgba",
        "clamp_cohort_be_rgba",
        "reconcile_pass1_be_rgba",
        "reconcile_pass2_be_rgba",
        "reduce_sum_be_rgba",
        "regional_scale_be_rgba",
        "regional_sum_be_rgba",
        "scale_be_f32",
        "threshold_clamp_be_f32",
        "velkscala_antiquity_blend",
        "velkscala_harmonic_step",
        "velkscala_seam_init"
      ];
      let kernels = {};
      for (let i = 0; i < kernel_names.length; i++) {
        let kname = kernel_names[i];
        let k = cl.clCreateKernel(prog, kname, err);
        if (!k || err[0] !== 0) {
          GeoPNG.gpu._init_error = `clCreateKernel(${kname}) failed (${err[0]})`;
          console.error(`- [GeoPNG.gpu] ${GeoPNG.gpu._init_error}`);
          return false;
        }
        kernels[kname] = k;
      }

      GeoPNG.gpu._cl = cl;
      GeoPNG.gpu._ctx = ctx;
      GeoPNG.gpu._device = selected_dev;
      GeoPNG.gpu._device_info = selected_info;
      GeoPNG.gpu._kernels = kernels;
      GeoPNG.gpu._program = prog;
      GeoPNG.gpu._queue = queue;
      GeoPNG.gpu._ready = true;
      GeoPNG.gpu._init_error = null;

      console.log(`- [GeoPNG.gpu] Initialised ${selected_info.platform} :: ${selected_info.device} (${selected_info.compute_units} SMs, ${selected_info.vram_mb} MiB VRAM; cap=${GeoPNG.compute_limits.gpu.max_vram_mb} MiB, wave=${GeoPNG.compute_limits.gpu.max_dispatch_pixels} px, pacing=${GeoPNG.compute_limits.gpu.pacing_ms}ms)`);

      //Return statement
      return true;
    } catch (e) {
      GeoPNG.gpu._init_error = e.message || String(e);
      return false;
    }
  };

  /**
   * Returns whether the NVIDIA OpenCL GPU compute backend is active and ready.
   * @alias GeoPNG.gpu.isAvailable
   *
   * @returns {boolean}
   */
  GeoPNG.gpu.isAvailable = function () {
    //Function body
    if (!GeoPNG.gpu._ready && !GeoPNG.gpu._init_attempted)
      GeoPNG.gpu.init();

    //Return statement
    return Boolean(GeoPNG.gpu._ready);
  };

  /**
   * Serialises async GPU jobs cleanly so VRAM pools & WDDM queues are never oversubscribed.
   * @alias GeoPNG.gpu.runSerialised
   *
   * @param {function} arg0_fn
   *
   * @returns {Promise<any>}
   */
  GeoPNG.gpu.runSerialised = function (arg0_fn) {
    //Convert from parameters
    let fn = arg0_fn;

    //Function body
    let run_promise = GeoPNG.gpu._mutex.then(fn, fn);
    GeoPNG.gpu._mutex = run_promise.catch(function () {});

    //Return statement
    return run_promise;
  };

  /**
   * Scales a big-endian float32 RGBA raster by a uniform scalar on the NVIDIA GPU.
   * @alias GeoPNG.gpu.scaleRGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {number} arg1_scalar
   *
   * @returns {Promise<Buffer|null>}
   */
  GeoPNG.gpu.scaleRGBA = async function (arg0_in_rgba, arg1_scalar) {
    //Convert from parameters
    let in_rgba = arg0_in_rgba;
    let scalar = Number(arg1_scalar);

    //Guard clauses
    if (!in_rgba || !Number.isFinite(scalar)) return null;
    let pixel_count = Math.floor(in_rgba.byteLength/4);
    if (!GeoPNG.gpu.shouldUseGPU(pixel_count)) return null;

    //Return statement
    return GeoPNG.gpu.runSerialised(async function () {
      let bytes = pixel_count*4;
      let cl = GeoPNG.gpu._cl;
      let d_in = GeoPNG.gpu.acquireBuffer("scale_in", bytes, 4n);
      let d_out = GeoPNG.gpu.acquireBuffer("scale_out", bytes, 2n);
      let kernel = GeoPNG.gpu._kernels.scale_be_f32;
      let out_buf = Buffer.allocUnsafe(bytes);

      if (!d_in || !d_out || !kernel) return null;

      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_in.mem, 0, 0, bytes, in_rgba, 0, null, null);
      await GeoPNG.gpu.dispatchWaves(pixel_count, function (arg0_offset, arg1_count, arg2_global, arg3_local) {
        cl.clSetKernelArgMem(kernel, 0, 8, [d_in.mem]);
        cl.clSetKernelArgMem(kernel, 1, 8, [d_out.mem]);
        cl.clSetKernelArgU32(kernel, 2, 4, [arg0_offset]);
        cl.clSetKernelArgU32(kernel, 3, 4, [arg1_count]);
        cl.clSetKernelArgF32(kernel, 4, 4, [scalar]);
        cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, kernel, 1, null, [arg2_global], [arg3_local], 0, null, null);
      });

      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_out.mem, 1, 0, bytes, out_buf, 0, null, null);
      return out_buf;
    });
  };

  /**
   * Returns true if pixel_count qualifies for GPU offload and the GPU device is ready.
   * @alias GeoPNG.gpu.shouldUseGPU
   *
   * @param {number} arg0_pixel_count
   *
   * @returns {boolean}
   */
  GeoPNG.gpu.shouldUseGPU = function (arg0_pixel_count) {
    //Convert from parameters
    let pixel_count = Number(arg0_pixel_count) || 0;

    //Guard clauses
    if (pixel_count < (Number(GeoPNG.compute_limits.gpu.min_pixels) || 65536)) return false;

    //Return statement
    return GeoPNG.gpu.isAvailable();
  };

  /**
   * Releases all pooled VRAM buffers and OpenCL handles cleanly on shutdown.
   * @alias GeoPNG.gpu.shutdown
   */
  GeoPNG.gpu.shutdown = function () {
    //Declare local instance variables
    let cl = GeoPNG.gpu._cl;
    if (!cl) return;

    GeoPNG.gpu.trimPools(true);

    let k_names = Object.keys(GeoPNG.gpu._kernels || {});
    for (let i = 0; i < k_names.length; i++) {
      try { cl.clReleaseKernel(GeoPNG.gpu._kernels[k_names[i]]); } catch (e) {}
    }
    GeoPNG.gpu._kernels = {};

    if (GeoPNG.gpu._program) {
      try { cl.clReleaseProgram(GeoPNG.gpu._program); } catch (e) {}
      GeoPNG.gpu._program = null;
    }
    if (GeoPNG.gpu._queue) {
      try { cl.clReleaseCommandQueue(GeoPNG.gpu._queue); } catch (e) {}
      GeoPNG.gpu._queue = null;
    }
    if (GeoPNG.gpu._ctx) {
      try { cl.clReleaseContext(GeoPNG.gpu._ctx); } catch (e) {}
      GeoPNG.gpu._ctx = null;
    }

    GeoPNG.gpu._device = null;
    GeoPNG.gpu._ready = false;
    GeoPNG.gpu._init_attempted = false;
    GeoPNG.gpu._last_rec_mask_ref = null;
    GeoPNG.gpu._last_rscale_ids_ref = null;
    GeoPNG.gpu._last_rsum_ids_ref = null;
    GeoPNG.gpu._last_velk_static_key = null;
  };

  /**
   * Computes a full fp64 sum over a big-endian RGBA raster on the NVIDIA GPU.
   * @alias GeoPNG.gpu.sumRGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<number|null>}
   */
  GeoPNG.gpu.sumRGBA = async function (arg0_in_rgba, arg1_options) {
    //Convert from parameters
    let in_rgba = arg0_in_rgba;
    let options = (arg1_options) ? arg1_options : {};

    //Guard clauses
    if (!in_rgba) return null;
    let pixel_count = Math.floor(in_rgba.byteLength/4);
    if (!GeoPNG.gpu.shouldUseGPU(pixel_count)) return null;

    let fmt = (options.format === "int32") ? 1 : ((options.format === "float32_le") ? 2 : 0);
    let positive_only = (options.positive_only) ? 1 : 0;

    //Return statement
    return GeoPNG.gpu.runSerialised(async function () {
      let bytes = pixel_count*4;
      let cl = GeoPNG.gpu._cl;
      let d_in = GeoPNG.gpu.acquireBuffer("sum_in", bytes, 4n);
      let kernel = GeoPNG.gpu._kernels.reduce_sum_be_rgba;
      let local_size = 256;
      let num_groups = 1024;
      let d_partials = GeoPNG.gpu.acquireBuffer("sum_partials", num_groups*8, 2n);

      if (!d_in || !d_partials || !kernel) return null;

      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_in.mem, 0, 0, bytes, in_rgba, 0, null, null);
      cl.clSetKernelArgMem(kernel, 0, 8, [d_in.mem]);
      cl.clSetKernelArgMem(kernel, 1, 8, [d_partials.mem]);
      cl.clSetKernelArgU32(kernel, 2, 4, [pixel_count]);
      cl.clSetKernelArgU32(kernel, 3, 4, [fmt]);
      cl.clSetKernelArgU32(kernel, 4, 4, [positive_only]);
      cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, kernel, 1, null, [num_groups*local_size], [local_size], 0, null, null);

      let partial_bytes = Buffer.allocUnsafe(num_groups*8);
      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_partials.mem, 1, 0, num_groups*8, partial_bytes, 0, null, null);

      let partials = new Float64Array(partial_bytes.buffer, partial_bytes.byteOffset, num_groups);
      let total = 0;
      for (let i = 0; i < num_groups; i++) total += partials[i];
      return total;
    });
  };

  /**
   * Applies minimum threshold clamp on a big-endian float32 RGBA raster on the NVIDIA GPU.
   * @alias GeoPNG.gpu.thresholdClampRGBA
   *
   * @param {Buffer|Uint8Array} arg0_in_rgba
   * @param {number} [arg1_min_val=0.01]
   *
   * @returns {Promise<Buffer|null>}
   */
  GeoPNG.gpu.thresholdClampRGBA = async function (arg0_in_rgba, arg1_min_val) {
    //Convert from parameters
    let in_rgba = arg0_in_rgba;
    let min_val = (arg1_min_val !== undefined) ? Number(arg1_min_val) : 0.01;

    //Guard clauses
    if (!in_rgba) return null;
    let pixel_count = Math.floor(in_rgba.byteLength/4);
    if (!GeoPNG.gpu.shouldUseGPU(pixel_count)) return null;

    //Return statement
    return GeoPNG.gpu.runSerialised(async function () {
      let bytes = pixel_count*4;
      let cl = GeoPNG.gpu._cl;
      let d_in = GeoPNG.gpu.acquireBuffer("thr_in", bytes, 4n);
      let d_out = GeoPNG.gpu.acquireBuffer("thr_out", bytes, 2n);
      let kernel = GeoPNG.gpu._kernels.threshold_clamp_be_f32;
      let out_buf = Buffer.allocUnsafe(bytes);

      if (!d_in || !d_out || !kernel) return null;

      cl.clEnqueueWriteBuffer(GeoPNG.gpu._queue, d_in.mem, 0, 0, bytes, in_rgba, 0, null, null);
      await GeoPNG.gpu.dispatchWaves(pixel_count, function (arg0_offset, arg1_count, arg2_global, arg3_local) {
        cl.clSetKernelArgMem(kernel, 0, 8, [d_in.mem]);
        cl.clSetKernelArgMem(kernel, 1, 8, [d_out.mem]);
        cl.clSetKernelArgU32(kernel, 2, 4, [arg0_offset]);
        cl.clSetKernelArgU32(kernel, 3, 4, [arg1_count]);
        cl.clSetKernelArgF32(kernel, 4, 4, [min_val]);
        cl.clEnqueueNDRangeKernel(GeoPNG.gpu._queue, kernel, 1, null, [arg2_global], [arg3_local], 0, null, null);
      });

      cl.clEnqueueReadBuffer(GeoPNG.gpu._queue, d_out.mem, 1, 0, bytes, out_buf, 0, null, null);
      return out_buf;
    });
  };

  /**
   * Releases pooled VRAM scratch buffers to free GPU memory.
   * @alias GeoPNG.gpu.trimPools
   *
   * @param {boolean} [arg0_include_pinned=false]
   */
  GeoPNG.gpu.trimPools = function (arg0_include_pinned) {
    //Convert from parameters
    let include_pinned = Boolean(arg0_include_pinned);

    //Declare local instance variables
    let cl = GeoPNG.gpu._cl;
    if (!cl) return;

    for (let [key, entry] of GeoPNG.gpu._buffer_pool.entries()) {
      if (!include_pinned && entry.pinned) continue;
      try { cl.clReleaseMemObject(entry.mem); } catch (e) {}
      GeoPNG.gpu._allocated_vram_bytes = Math.max(0, GeoPNG.gpu._allocated_vram_bytes - entry.size);
      GeoPNG.gpu._buffer_pool.delete(key);
    }

    if (include_pinned) {
      GeoPNG.gpu._last_rec_mask_ref = null;
      GeoPNG.gpu._last_rscale_ids_ref = null;
      GeoPNG.gpu._last_rsum_ids_ref = null;
      GeoPNG.gpu._last_velk_static_key = null;
    }
  };

  if (typeof require !== "undefined" && !GeoPNG.gpu.reconcileDemographicsRGBA) {
    try { require("./png_gpu_pipelines.js"); } catch (e) {}
  }

  GeoPNG.loadComputeLimits();

  if (typeof process !== "undefined" && typeof process.on === "function") {
    process.on("exit", function () {
      try { GeoPNG.gpu.shutdown(); } catch (e) {}
    });
  }
}
