//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { VISCOUNT_OPENCL_KERNELS } = global.VISCOUNT_OPENCL_KERNELS ? global : require("./ViscountKrigingGPUKernels.js");

if (!global.GeoPNG || !global.GeoPNG.gpu) {
  let gpu_candidates = [
    path.resolve(__dirname, "../../../UF/js/geospatiale/files/png/png_gpu_framework.js"),
    path.resolve(process.cwd(), "UF/js/geospatiale/files/png/png_gpu_framework.js")
  ];

  for (let i = 0; i < gpu_candidates.length; i++) {
    if (fs.existsSync(gpu_candidates[i])) {
      try { require(gpu_candidates[i]); } catch (e) {}
      break;
    }
  }
}

//Initialise functions
{
  let _asF32 = function (arg0_arr) {
    if (!arg0_arr) return null;
    if (arg0_arr instanceof Float32Array) return arg0_arr;
    return Float32Array.from(arg0_arr);
  };

  let _asI32 = function (arg0_arr) {
    if (!arg0_arr) return null;
    if (arg0_arr instanceof Int32Array) return arg0_arr;
    return Int32Array.from(arg0_arr);
  };

  let _bufView = function (arg0_typed) {
    return new Uint8Array(arg0_typed.buffer, arg0_typed.byteOffset, arg0_typed.byteLength);
  };

  let _uploadCached = function (arg0_queue, arg1_cl, arg2_dev_buf, arg3_typed_arr) {
    if (arg2_dev_buf._cache_ref === arg3_typed_arr) return;
    arg1_cl.clEnqueueWriteBuffer(arg0_queue, arg2_dev_buf.mem, 1, 0, arg3_typed_arr.byteLength, _bufView(arg3_typed_arr), 0, null, null);
    arg2_dev_buf._cache_ref = arg3_typed_arr;
  };

  /**
   * Pure Node.js OpenCL 3.0 GPU compute backend for Operation Viscount Kriging & Substrata.
   * Uses FP32 local-memory tiled kernels (11x-24x faster on Ada Lovelace WDDM), blocking DMA transfers,
   * static buffer reference caching, and WDDM frame-budget wave slicing configured in `geopng_compute.json5`.
   *
   * @class ViscountKrigingGPU
   */
  global.ViscountKrigingGPU = class {
    /**
     * Computes symmetric pairwise `u_matrix` and `scale_pref_mat` on the NVIDIA GPU (Step C).
     * @alias ViscountKrigingGPU.computePairwiseUPref
     *
     * @param {Float64Array|Float32Array} arg0_obs_ux
     * @param {Float64Array|Float32Array} arg1_obs_uy
     * @param {Float64Array|Float32Array} arg2_obs_uz
     * @param {Float64Array|Float32Array} arg3_obs_r
     * @param {number} arg4_earth_r
     *
     * @returns {{scale_pref_mat: Float32Array, u_matrix: Float32Array}|null}
     */
    static computePairwiseUPref (arg0_obs_ux, arg1_obs_uy, arg2_obs_uz, arg3_obs_r, arg4_earth_r) {
      //Convert from parameters
      let earth_r = Number(arg4_earth_r) || 6371;
      let obs_r = _asF32(arg3_obs_r);
      let obs_ux = _asF32(arg0_obs_ux);
      let obs_uy = _asF32(arg1_obs_uy);
      let obs_uz = _asF32(arg2_obs_uz);

      //Guard clauses
      if (!obs_ux || !obs_r) return null;
      let n_obs = obs_ux.length;
      if (n_obs < 128 || !this.isAvailable()) return null;

      //Declare local instance variables
      let cl = GeoPNG.gpu._cl;
      let kernel = this._kernels.viscount_pairwise_u_pref;
      let obs_bytes = n_obs*4;
      let pair_count = n_obs*n_obs;
      let pair_bytes = pair_count*4;
      let queue = GeoPNG.gpu._queue;

      //Function body
      let d_obs_r = GeoPNG.gpu.acquireBuffer("vk_pw_obs_r", obs_bytes, 4n);
      let d_obs_ux = GeoPNG.gpu.acquireBuffer("vk_pw_obs_ux", obs_bytes, 4n);
      let d_obs_uy = GeoPNG.gpu.acquireBuffer("vk_pw_obs_uy", obs_bytes, 4n);
      let d_obs_uz = GeoPNG.gpu.acquireBuffer("vk_pw_obs_uz", obs_bytes, 4n);
      let d_pref = GeoPNG.gpu.acquireBuffer("vk_pw_pref", pair_bytes, 1n);
      let d_u = GeoPNG.gpu.acquireBuffer("vk_pw_u", pair_bytes, 1n);

      if (!d_obs_r || !d_obs_ux || !d_obs_uy || !d_obs_uz || !d_pref || !d_u || !kernel)
        return null;

      cl.clEnqueueWriteBuffer(queue, d_obs_ux.mem, 1, 0, obs_bytes, _bufView(obs_ux), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_uy.mem, 1, 0, obs_bytes, _bufView(obs_uy), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_uz.mem, 1, 0, obs_bytes, _bufView(obs_uz), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_r.mem, 1, 0, obs_bytes, _bufView(obs_r), 0, null, null);

      this.dispatchWavesSync(pair_count, 0, function (arg0_off, arg1_cnt, arg2_glob, arg3_loc) {
        cl.clSetKernelArgMem(kernel, 0, 8, [d_obs_ux.mem]);
        cl.clSetKernelArgMem(kernel, 1, 8, [d_obs_uy.mem]);
        cl.clSetKernelArgMem(kernel, 2, 8, [d_obs_uz.mem]);
        cl.clSetKernelArgMem(kernel, 3, 8, [d_obs_r.mem]);
        cl.clSetKernelArgMem(kernel, 4, 8, [d_u.mem]);
        cl.clSetKernelArgMem(kernel, 5, 8, [d_pref.mem]);
        cl.clSetKernelArgU32(kernel, 6, 4, [arg0_off]);
        cl.clSetKernelArgU32(kernel, 7, 4, [arg1_cnt]);
        cl.clSetKernelArgU32(kernel, 8, 4, [n_obs]);
        cl.clSetKernelArgF32(kernel, 9, 4, [earth_r]);
        cl.clEnqueueNDRangeKernel(queue, kernel, 1, null, [arg2_glob], [arg3_loc], 0, null, null);
      });

      let scale_pref_mat = new Float32Array(pair_count);
      let u_matrix = new Float32Array(pair_count);

      cl.clEnqueueReadBuffer(queue, d_u.mem, 1, 0, pair_bytes, _bufView(u_matrix), 0, null, null);
      cl.clEnqueueReadBuffer(queue, d_pref.mem, 1, 0, pair_bytes, _bufView(scale_pref_mat), 0, null, null);
      this._last_pw_u_ref = u_matrix;
      this._last_pw_pref_ref = scale_pref_mat;

      //Return statement
      return { scale_pref_mat: scale_pref_mat, u_matrix: u_matrix };
    }


    /**
     * Computes exact geodesic Voronoi nearest catchment index for every valid cell on the NVIDIA GPU (Step B).
     * @alias ViscountKrigingGPU.computeVoronoiNearest
     *
     * @param {Float32Array} arg0_cell_ux
     * @param {Float32Array} arg1_cell_uy
     * @param {Float32Array} arg2_cell_uz
     * @param {Float64Array|Float32Array} arg3_obs_ux
     * @param {Float64Array|Float32Array} arg4_obs_uy
     * @param {Float64Array|Float32Array} arg5_obs_uz
     *
     * @returns {Int32Array|null}
     */
    static computeVoronoiNearest (arg0_cell_ux, arg1_cell_uy, arg2_cell_uz, arg3_obs_ux, arg4_obs_uy, arg5_obs_uz) {
      //Convert from parameters
      let cell_ux = _asF32(arg0_cell_ux);
      let cell_uy = _asF32(arg1_cell_uy);
      let cell_uz = _asF32(arg2_cell_uz);
      let obs_ux = _asF32(arg3_obs_ux);
      let obs_uy = _asF32(arg4_obs_uy);
      let obs_uz = _asF32(arg5_obs_uz);

      //Guard clauses
      if (!cell_ux || !obs_ux) return null;
      let n_obs = obs_ux.length;
      let n_valid = cell_ux.length;
      if (n_valid*n_obs < 1000000 || !this.isAvailable()) return null;

      //Declare local instance variables
      let cell_bytes = n_valid*4;
      let cl = GeoPNG.gpu._cl;
      let kernel = this._kernels.viscount_voronoi_nearest;
      let obs_bytes = n_obs*4;
      let queue = GeoPNG.gpu._queue;

      //Function body
      let d_cell_ux = GeoPNG.gpu.acquireBuffer("vk_cell_ux", cell_bytes, 4n);
      let d_cell_uy = GeoPNG.gpu.acquireBuffer("vk_cell_uy", cell_bytes, 4n);
      let d_cell_uz = GeoPNG.gpu.acquireBuffer("vk_cell_uz", cell_bytes, 4n);
      let d_nearest = GeoPNG.gpu.acquireBuffer("vk_nearest", cell_bytes, 2n);
      let d_obs_ux = GeoPNG.gpu.acquireBuffer("vk_obs_ux", obs_bytes, 4n);
      let d_obs_uy = GeoPNG.gpu.acquireBuffer("vk_obs_uy", obs_bytes, 4n);
      let d_obs_uz = GeoPNG.gpu.acquireBuffer("vk_obs_uz", obs_bytes, 4n);

      if (!d_cell_ux || !d_cell_uy || !d_cell_uz || !d_nearest || !d_obs_ux || !d_obs_uy || !d_obs_uz || !kernel)
        return null;

      _uploadCached(queue, cl, d_cell_ux, cell_ux);
      _uploadCached(queue, cl, d_cell_uy, cell_uy);
      _uploadCached(queue, cl, d_cell_uz, cell_uz);
      cl.clEnqueueWriteBuffer(queue, d_obs_ux.mem, 1, 0, obs_bytes, _bufView(obs_ux), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_uy.mem, 1, 0, obs_bytes, _bufView(obs_uy), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_uz.mem, 1, 0, obs_bytes, _bufView(obs_uz), 0, null, null);

      let max_wave = Math.max(16384, Math.min(524288, Math.floor(2000000000/Math.max(1, n_obs))));

      this.dispatchWavesSync(n_valid, max_wave, function (arg0_off, arg1_cnt, arg2_glob, arg3_loc) {
        cl.clSetKernelArgMem(kernel, 0, 8, [d_cell_ux.mem]);
        cl.clSetKernelArgMem(kernel, 1, 8, [d_cell_uy.mem]);
        cl.clSetKernelArgMem(kernel, 2, 8, [d_cell_uz.mem]);
        cl.clSetKernelArgMem(kernel, 3, 8, [d_obs_ux.mem]);
        cl.clSetKernelArgMem(kernel, 4, 8, [d_obs_uy.mem]);
        cl.clSetKernelArgMem(kernel, 5, 8, [d_obs_uz.mem]);
        cl.clSetKernelArgMem(kernel, 6, 8, [d_nearest.mem]);
        cl.clSetKernelArgU32(kernel, 7, 4, [arg0_off]);
        cl.clSetKernelArgU32(kernel, 8, 4, [arg1_cnt]);
        cl.clSetKernelArgU32(kernel, 9, 4, [n_obs]);
        cl.clEnqueueNDRangeKernel(queue, kernel, 1, null, [arg2_glob], [arg3_loc], 0, null, null);
      });

      let cell_nearest = new Int32Array(n_valid);
      cl.clEnqueueReadBuffer(queue, d_nearest.mem, 1, 0, cell_bytes, _bufView(cell_nearest), 0, null, null);

      //Return statement
      return cell_nearest;
    }


    /**
     * Executes a 1D OpenCL kernel synchronously in WDDM-safe bounded waves (keeping each wave < 6 ms).
     * @alias ViscountKrigingGPU.dispatchWavesSync
     *
     * @param {number} arg0_total_items
     * @param {number} arg1_wave_cap
     * @param {function} arg2_enqueue_fn
     */
    static dispatchWavesSync (arg0_total_items, arg1_wave_cap, arg2_enqueue_fn) {
      //Convert from parameters
      let enqueue_fn = arg2_enqueue_fn;
      let total_items = Math.max(0, Math.floor(Number(arg0_total_items) || 0));
      let wave_cap = Number(arg1_wave_cap) || 0;

      //Guard clause
      if (total_items === 0 || typeof enqueue_fn !== "function") return;

      //Declare local instance variables
      let cl = GeoPNG.gpu._cl;
      let cfg_wave = Number(GeoPNG.compute_limits.gpu.max_dispatch_pixels) || 4665600;
      let local_size = 256;
      let max_wave = Math.max(local_size, (wave_cap > 0) ? Math.min(cfg_wave, wave_cap) : cfg_wave);

      //Function body
      for (let offset = 0; offset < total_items; offset += max_wave) {
        let count = Math.min(max_wave, total_items - offset);
        let global_size = Math.ceil(count/local_size)*local_size;
        let t0 = (typeof performance !== "undefined") ? performance.now() : Date.now();

        enqueue_fn(offset, count, global_size, local_size);
        cl.clFinish(GeoPNG.gpu._queue);

        if (GeoPNG.governor && typeof GeoPNG.governor.recordGpuWaveSync === "function") {
          let dt = ((typeof performance !== "undefined") ? performance.now() : Date.now()) - t0;
          GeoPNG.governor.recordGpuWaveSync(dt);
        }
      }
    }


    /**
     * Evaluates two-scale Paciorek-Schervish Matérn potentials across all active periods on the NVIDIA GPU (Step E).
     * @alias ViscountKrigingGPU.evaluateMaternPotentials
     *
     * @param {Object} arg0_params
     *
     * @returns {boolean}
     */
    static evaluateMaternPotentials (arg0_params) {
      //Convert from parameters
      let p = (arg0_params) ? arg0_params : {};

      //Guard clauses
      let active_periods = p.active_periods;
      let n_active = Array.isArray(active_periods) ? active_periods.length : 0;
      let n_obs = Number(p.n_obs) || 0;
      let n_valid = Number(p.n_valid) || 0;

      if (n_active === 0 || n_obs === 0 || n_valid === 0) return false;
      if (n_valid*n_obs < 1000000 || !this.isAvailable()) return false;

      //Declare local instance variables
      let c1_arr = new Float32Array(n_active);
      let c2_arr = new Float32Array(n_active);
      let cell_area = _asF32(p.cell_area);
      let cell_bytes = n_valid*4;
      let cell_r = _asF32(p.cell_r);
      let cell_ux = _asF32(p.cell_ux);
      let cell_uy = _asF32(p.cell_uy);
      let cell_uz = _asF32(p.cell_uz);
      let cl = GeoPNG.gpu._cl;
      let earth_r = Number(p.earth_r) || 6371;
      let inv_tau1_arr = new Float32Array(n_active);
      let inv_tau2_arr = new Float32Array(n_active);
      let kernel = this._kernels.viscount_matern_eval_potentials;
      let lut = (this._last_lut_src === p.lut && this._last_lut_f32) ? this._last_lut_f32 : _asF32(p.lut);
      let min_dot = _asF32(p.min_dot_per_obs);
      let obs_bytes = n_obs*4;
      let obs_r = _asF32(p.obs_r);
      let obs_ux = _asF32(p.obs_ux);
      let obs_uy = _asF32(p.obs_uy);
      let obs_uz = _asF32(p.obs_uz);
      let out_bytes = n_active*n_valid*4;
      let queue = GeoPNG.gpu._queue;
      let shared_tau = p.shared_tau ? 1 : 0;
      let var_restore_arr = new Float32Array(n_active);
      let w_packed = new Float32Array(n_obs*n_active);

      this._last_lut_src = p.lut;
      this._last_lut_f32 = lut;

      //Function body
      for (let a = 0; a < n_active; a++) {
        let ap = active_periods[a];

        c1_arr[a] = ap.c1;
        c2_arr[a] = ap.c2;
        inv_tau1_arr[a] = ap.inv_tau1;
        inv_tau2_arr[a] = ap.inv_tau2;
        var_restore_arr[a] = ap.var_restore;
        for (let x = 0; x < n_obs; x++)
          w_packed[x*n_active + a] = ap.w[x];
      }

      let d_c1 = GeoPNG.gpu.acquireBuffer("vk_mp_c1", n_active*4, 4n);
      let d_c2 = GeoPNG.gpu.acquireBuffer("vk_mp_c2", n_active*4, 4n);
      let d_cell_area = GeoPNG.gpu.acquireBuffer("vk_cell_area", cell_bytes, 4n);
      let d_cell_r = GeoPNG.gpu.acquireBuffer("vk_cell_r", cell_bytes, 4n);
      let d_cell_ux = GeoPNG.gpu.acquireBuffer("vk_cell_ux", cell_bytes, 4n);
      let d_cell_uy = GeoPNG.gpu.acquireBuffer("vk_cell_uy", cell_bytes, 4n);
      let d_cell_uz = GeoPNG.gpu.acquireBuffer("vk_cell_uz", cell_bytes, 4n);
      let d_it1 = GeoPNG.gpu.acquireBuffer("vk_mp_it1", n_active*4, 4n);
      let d_it2 = GeoPNG.gpu.acquireBuffer("vk_mp_it2", n_active*4, 4n);
      let d_lut = GeoPNG.gpu.acquireBuffer("vk_lut_f32", lut.byteLength, 4n);
      let d_min_dot = GeoPNG.gpu.acquireBuffer("vk_mp_mindot", obs_bytes, 4n);
      let d_obs_r = GeoPNG.gpu.acquireBuffer("vk_obs_r", obs_bytes, 4n);
      let d_obs_ux = GeoPNG.gpu.acquireBuffer("vk_obs_ux", obs_bytes, 4n);
      let d_obs_uy = GeoPNG.gpu.acquireBuffer("vk_obs_uy", obs_bytes, 4n);
      let d_obs_uz = GeoPNG.gpu.acquireBuffer("vk_obs_uz", obs_bytes, 4n);
      let d_out_pot = GeoPNG.gpu.acquireBuffer("vk_mp_out_pot", out_bytes, 2n);
      let d_vr = GeoPNG.gpu.acquireBuffer("vk_mp_vr", n_active*4, 4n);
      let d_w = GeoPNG.gpu.acquireBuffer("vk_mp_w", w_packed.byteLength, 4n);

      if (
        !d_c1 || !d_c2 || !d_cell_area || !d_cell_r || !d_cell_ux || !d_cell_uy || !d_cell_uz ||
        !d_it1 || !d_it2 || !d_lut || !d_min_dot || !d_obs_r || !d_obs_ux || !d_obs_uy || !d_obs_uz ||
        !d_out_pot || !d_vr || !d_w || !kernel
      ) {
        return false;
      }

      _uploadCached(queue, cl, d_cell_ux, cell_ux);
      _uploadCached(queue, cl, d_cell_uy, cell_uy);
      _uploadCached(queue, cl, d_cell_uz, cell_uz);
      _uploadCached(queue, cl, d_cell_r, cell_r);
      _uploadCached(queue, cl, d_cell_area, cell_area);
      _uploadCached(queue, cl, d_lut, lut);
      cl.clEnqueueWriteBuffer(queue, d_obs_ux.mem, 1, 0, obs_bytes, _bufView(obs_ux), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_uy.mem, 1, 0, obs_bytes, _bufView(obs_uy), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_uz.mem, 1, 0, obs_bytes, _bufView(obs_uz), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_r.mem, 1, 0, obs_bytes, _bufView(obs_r), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_min_dot.mem, 1, 0, obs_bytes, _bufView(min_dot), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_w.mem, 1, 0, w_packed.byteLength, _bufView(w_packed), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_c1.mem, 1, 0, c1_arr.byteLength, _bufView(c1_arr), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_c2.mem, 1, 0, c2_arr.byteLength, _bufView(c2_arr), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_it1.mem, 1, 0, inv_tau1_arr.byteLength, _bufView(inv_tau1_arr), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_it2.mem, 1, 0, inv_tau2_arr.byteLength, _bufView(inv_tau2_arr), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_vr.mem, 1, 0, var_restore_arr.byteLength, _bufView(var_restore_arr), 0, null, null);

      let max_wave = Math.max(8192, Math.min(49152, Math.floor(180000000/Math.max(1, n_obs))));

      this.dispatchWavesSync(n_valid, max_wave, function (arg0_off, arg1_cnt, arg2_glob, arg3_loc) {
        cl.clSetKernelArgMem(kernel, 0, 8, [d_cell_ux.mem]);
        cl.clSetKernelArgMem(kernel, 1, 8, [d_cell_uy.mem]);
        cl.clSetKernelArgMem(kernel, 2, 8, [d_cell_uz.mem]);
        cl.clSetKernelArgMem(kernel, 3, 8, [d_cell_r.mem]);
        cl.clSetKernelArgMem(kernel, 4, 8, [d_cell_area.mem]);
        cl.clSetKernelArgMem(kernel, 5, 8, [d_obs_ux.mem]);
        cl.clSetKernelArgMem(kernel, 6, 8, [d_obs_uy.mem]);
        cl.clSetKernelArgMem(kernel, 7, 8, [d_obs_uz.mem]);
        cl.clSetKernelArgMem(kernel, 8, 8, [d_obs_r.mem]);
        cl.clSetKernelArgMem(kernel, 9, 8, [d_min_dot.mem]);
        cl.clSetKernelArgMem(kernel, 10, 8, [d_w.mem]);
        cl.clSetKernelArgMem(kernel, 11, 8, [d_c1.mem]);
        cl.clSetKernelArgMem(kernel, 12, 8, [d_c2.mem]);
        cl.clSetKernelArgMem(kernel, 13, 8, [d_it1.mem]);
        cl.clSetKernelArgMem(kernel, 14, 8, [d_it2.mem]);
        cl.clSetKernelArgMem(kernel, 15, 8, [d_vr.mem]);
        cl.clSetKernelArgMem(kernel, 16, 8, [d_lut.mem]);
        cl.clSetKernelArgMem(kernel, 17, 8, [d_out_pot.mem]);
        cl.clSetKernelArgU32(kernel, 18, 4, [arg0_off]);
        cl.clSetKernelArgU32(kernel, 19, 4, [arg1_cnt]);
        cl.clSetKernelArgU32(kernel, 20, 4, [n_valid]);
        cl.clSetKernelArgU32(kernel, 21, 4, [n_obs]);
        cl.clSetKernelArgU32(kernel, 22, 4, [n_active]);
        cl.clSetKernelArgU32(kernel, 23, 4, [shared_tau]);
        cl.clSetKernelArgF32(kernel, 24, 4, [earth_r]);
        cl.clEnqueueNDRangeKernel(queue, kernel, 1, null, [arg2_glob], [arg3_loc], 0, null, null);
      });

      let flat_out = new Float32Array(n_active*n_valid);
      cl.clEnqueueReadBuffer(queue, d_out_pot.mem, 1, 0, out_bytes, _bufView(flat_out), 0, null, null);

      for (let a = 0; a < n_active; a++)
        active_periods[a].pot.set(flat_out.subarray(a*n_valid, (a + 1)*n_valid));

      //Return statement
      return true;
    }


    /**
     * Evaluates terrain-barrier-aware signed residual Matérn fields across multiple periods on the NVIDIA GPU.
     * @alias ViscountKrigingGPU.evaluateResidualMaternMulti
     *
     * @param {Object} arg0_params
     *
     * @returns {boolean}
     */
    static evaluateResidualMaternMulti (arg0_params) {
      //Convert from parameters
      let p = (arg0_params) ? arg0_params : {};

      //Guard clauses
      let n_obs = Number(p.n_obs) || 0;
      let n_p = Number(p.n_p) || 0;
      let n_valid = Number(p.n_valid) || 0;

      if (n_p === 0 || n_obs === 0 || n_valid === 0) return false;
      if (n_valid*n_obs < 1000000 || !this.isAvailable()) return false;

      //Declare local instance variables
      let cell_area = _asF32(p.cell_area);
      let cell_bytes = n_valid*4;
      let cell_obs = p.cell_obs ? _asI32(p.cell_obs) : null;
      let cell_r = _asF32(p.cell_r);
      let cell_ux = _asF32(p.cell_ux);
      let cell_uy = _asF32(p.cell_uy);
      let cell_uz = _asF32(p.cell_uz);
      let cl = GeoPNG.gpu._cl;
      let elev_valid = p.elev_valid ? _asF32(p.elev_valid) : null;
      let flags = (elev_valid ? 1 : 0) | (cell_obs ? 2 : 0);
      let kernel = this._kernels.viscount_residual_matern_multi;
      let lut = (this._last_lut_src === p.lut && this._last_lut_f32) ? this._last_lut_f32 : _asF32(p.lut);
      let min_dot = _asF32(p.min_dot);
      let obs_bytes = n_obs*4;
      let obs_elev_m = _asF32(p.obs_elev_m);
      let obs_r = _asF32(p.obs_r);
      let obs_ux = _asF32(p.obs_ux);
      let obs_uy = _asF32(p.obs_uy);
      let obs_uz = _asF32(p.obs_uz);
      let out_bytes = n_p*n_valid*4;
      let prior_packed = new Float32Array(n_p*n_valid);
      let queue = GeoPNG.gpu._queue;
      let v_packed = new Float32Array(n_obs*n_p);

      this._last_lut_src = p.lut;
      this._last_lut_f32 = lut;

      //Function body
      for (let a = 0; a < n_p; a++) {
        prior_packed.set(p.prior_bundles[a].prior_dens, a*n_valid);
        for (let x = 0; x < n_obs; x++)
          v_packed[x*n_p + a] = p.v_vecs[a][x];
      }

      let d_cell_area = GeoPNG.gpu.acquireBuffer("vk_cell_area", cell_bytes, 4n);
      let d_cell_obs = GeoPNG.gpu.acquireBuffer("vk_res_cell_obs", cell_obs ? cell_bytes : 16, 4n);
      let d_cell_r = GeoPNG.gpu.acquireBuffer("vk_cell_r", cell_bytes, 4n);
      let d_cell_ux = GeoPNG.gpu.acquireBuffer("vk_cell_ux", cell_bytes, 4n);
      let d_cell_uy = GeoPNG.gpu.acquireBuffer("vk_cell_uy", cell_bytes, 4n);
      let d_cell_uz = GeoPNG.gpu.acquireBuffer("vk_cell_uz", cell_bytes, 4n);
      let d_elev = GeoPNG.gpu.acquireBuffer("vk_res_elev", elev_valid ? cell_bytes : 16, 4n);
      let d_lut = GeoPNG.gpu.acquireBuffer("vk_lut_f32", lut.byteLength, 4n);
      let d_min_dot = GeoPNG.gpu.acquireBuffer("vk_res_mindot", obs_bytes, 4n);
      let d_obs_elev = GeoPNG.gpu.acquireBuffer("vk_res_obs_elev", obs_bytes, 4n);
      let d_obs_r = GeoPNG.gpu.acquireBuffer("vk_obs_r", obs_bytes, 4n);
      let d_obs_ux = GeoPNG.gpu.acquireBuffer("vk_obs_ux", obs_bytes, 4n);
      let d_obs_uy = GeoPNG.gpu.acquireBuffer("vk_obs_uy", obs_bytes, 4n);
      let d_obs_uz = GeoPNG.gpu.acquireBuffer("vk_obs_uz", obs_bytes, 4n);
      let d_out_pop = GeoPNG.gpu.acquireBuffer("vk_res_out_pop", out_bytes, 2n);
      let d_out_r = GeoPNG.gpu.acquireBuffer("vk_res_out_r", out_bytes, 2n);
      let d_prior = GeoPNG.gpu.acquireBuffer("vk_res_prior", out_bytes, 4n);
      let d_v = GeoPNG.gpu.acquireBuffer("vk_res_v", v_packed.byteLength, 4n);

      if (
        !d_cell_area || !d_cell_obs || !d_cell_r || !d_cell_ux || !d_cell_uy || !d_cell_uz ||
        !d_elev || !d_lut || !d_min_dot || !d_obs_elev || !d_obs_r || !d_obs_ux || !d_obs_uy || !d_obs_uz ||
        !d_out_pop || !d_out_r || !d_prior || !d_v || !kernel
      ) {
        return false;
      }

      _uploadCached(queue, cl, d_cell_ux, cell_ux);
      _uploadCached(queue, cl, d_cell_uy, cell_uy);
      _uploadCached(queue, cl, d_cell_uz, cell_uz);
      _uploadCached(queue, cl, d_cell_r, cell_r);
      _uploadCached(queue, cl, d_cell_area, cell_area);
      _uploadCached(queue, cl, d_lut, lut);
      if (elev_valid) _uploadCached(queue, cl, d_elev, elev_valid);
      if (cell_obs) _uploadCached(queue, cl, d_cell_obs, cell_obs);
      cl.clEnqueueWriteBuffer(queue, d_obs_ux.mem, 1, 0, obs_bytes, _bufView(obs_ux), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_uy.mem, 1, 0, obs_bytes, _bufView(obs_uy), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_uz.mem, 1, 0, obs_bytes, _bufView(obs_uz), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_r.mem, 1, 0, obs_bytes, _bufView(obs_r), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_obs_elev.mem, 1, 0, obs_bytes, _bufView(obs_elev_m), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_min_dot.mem, 1, 0, obs_bytes, _bufView(min_dot), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_v.mem, 1, 0, v_packed.byteLength, _bufView(v_packed), 0, null, null);
      cl.clEnqueueWriteBuffer(queue, d_prior.mem, 1, 0, out_bytes, _bufView(prior_packed), 0, null, null);

      let max_wave = Math.max(8192, Math.min(32768, Math.floor(120000000/Math.max(1, n_obs))));

      this.dispatchWavesSync(n_valid, max_wave, function (arg0_off, arg1_cnt, arg2_glob, arg3_loc) {
        cl.clSetKernelArgMem(kernel, 0, 8, [d_cell_ux.mem]);
        cl.clSetKernelArgMem(kernel, 1, 8, [d_cell_uy.mem]);
        cl.clSetKernelArgMem(kernel, 2, 8, [d_cell_uz.mem]);
        cl.clSetKernelArgMem(kernel, 3, 8, [d_cell_r.mem]);
        cl.clSetKernelArgMem(kernel, 4, 8, [d_cell_area.mem]);
        cl.clSetKernelArgMem(kernel, 5, 8, [d_elev.mem]);
        cl.clSetKernelArgMem(kernel, 6, 8, [d_cell_obs.mem]);
        cl.clSetKernelArgMem(kernel, 7, 8, [d_obs_ux.mem]);
        cl.clSetKernelArgMem(kernel, 8, 8, [d_obs_uy.mem]);
        cl.clSetKernelArgMem(kernel, 9, 8, [d_obs_uz.mem]);
        cl.clSetKernelArgMem(kernel, 10, 8, [d_obs_r.mem]);
        cl.clSetKernelArgMem(kernel, 11, 8, [d_obs_elev.mem]);
        cl.clSetKernelArgMem(kernel, 12, 8, [d_min_dot.mem]);
        cl.clSetKernelArgMem(kernel, 13, 8, [d_v.mem]);
        cl.clSetKernelArgMem(kernel, 14, 8, [d_prior.mem]);
        cl.clSetKernelArgMem(kernel, 15, 8, [d_lut.mem]);
        cl.clSetKernelArgMem(kernel, 16, 8, [d_out_r.mem]);
        cl.clSetKernelArgMem(kernel, 17, 8, [d_out_pop.mem]);
        cl.clSetKernelArgU32(kernel, 18, 4, [arg0_off]);
        cl.clSetKernelArgU32(kernel, 19, 4, [arg1_cnt]);
        cl.clSetKernelArgU32(kernel, 20, 4, [n_valid]);
        cl.clSetKernelArgU32(kernel, 21, 4, [n_obs]);
        cl.clSetKernelArgU32(kernel, 22, 4, [n_p]);
        cl.clSetKernelArgU32(kernel, 23, 4, [flags]);
        cl.clSetKernelArgF32(kernel, 24, 4, [Number(p.earth_r) || 6371]);
        cl.clSetKernelArgF32(kernel, 25, 4, [Number(p.c1)]);
        cl.clSetKernelArgF32(kernel, 26, 4, [Number(p.c2)]);
        cl.clSetKernelArgF32(kernel, 27, 4, [Number(p.inv_tau1)]);
        cl.clSetKernelArgF32(kernel, 28, 4, [Number(p.inv_tau2)]);
        cl.clSetKernelArgF32(kernel, 29, 4, [Number(p.inv_eb)]);
        cl.clSetKernelArgF32(kernel, 30, 4, [Number(p.cross_catch_mult)]);
        cl.clSetKernelArgF32(kernel, 31, 4, [Number(p.r_gain)]);
        cl.clSetKernelArgF32(kernel, 32, 4, [Number(p.r_clamp_min)]);
        cl.clSetKernelArgF32(kernel, 33, 4, [Number(p.r_clamp_max)]);
        cl.clEnqueueNDRangeKernel(queue, kernel, 1, null, [arg2_glob], [arg3_loc], 0, null, null);
      });

      let flat_pop = new Float32Array(n_p*n_valid);
      let flat_r = new Float32Array(n_p*n_valid);

      cl.clEnqueueReadBuffer(queue, d_out_r.mem, 1, 0, out_bytes, _bufView(flat_r), 0, null, null);
      cl.clEnqueueReadBuffer(queue, d_out_pop.mem, 1, 0, out_bytes, _bufView(flat_pop), 0, null, null);

      for (let a = 0; a < n_p; a++) {
        p.r_fields[a].set(flat_r.subarray(a*n_valid, (a + 1)*n_valid));
        p.pop_fields[a].set(flat_pop.subarray(a*n_valid, (a + 1)*n_valid));
      }

      //Return statement
      return true;
    }


    /**
     * Fills symmetric two-scale Matérn (`nu = 3/2`) kernel matrices `m1_mat` and `m2_mat` on the NVIDIA GPU (Step C).
     * @alias ViscountKrigingGPU.fillMaternKernels
     *
     * @param {Float32Array} arg0_u_matrix
     * @param {Float32Array} arg1_scale_pref_mat
     * @param {number} arg2_n_obs
     * @param {number} arg3_tau1
     * @param {number} arg4_tau2
     * @param {Float64Array} arg5_m1_mat
     * @param {Float64Array} arg6_m2_mat
     *
     * @returns {boolean}
     */
    static fillMaternKernels (arg0_u_matrix, arg1_scale_pref_mat, arg2_n_obs, arg3_tau1, arg4_tau2, arg5_m1_mat, arg6_m2_mat) {
      //Convert from parameters
      let m1_mat = arg5_m1_mat;
      let m2_mat = arg6_m2_mat;
      let n_obs = Number(arg2_n_obs) || 0;
      let scale_pref_mat = arg1_scale_pref_mat;
      let tau1 = Number(arg3_tau1);
      let tau2 = Number(arg4_tau2);
      let u_matrix = arg0_u_matrix;

      //Guard clauses
      if (!u_matrix || !scale_pref_mat || !m1_mat || !m2_mat) return false;
      if (n_obs < 128 || !this.isAvailable()) return false;

      //Declare local instance variables
      let cl = GeoPNG.gpu._cl;
      let inv_t1_s3 = Math.sqrt(3)/tau1;
      let inv_t2_s3 = Math.sqrt(3)/tau2;
      let kernel = this._kernels.viscount_fill_matern_kernels;
      let pair_count = n_obs*n_obs;
      let pair_f32_bytes = pair_count*4;
      let pair_f64_bytes = pair_count*8;
      let queue = GeoPNG.gpu._queue;

      //Function body
      let d_m1 = GeoPNG.gpu.acquireBuffer("vk_pw_m1", pair_f64_bytes, 2n);
      let d_m2 = GeoPNG.gpu.acquireBuffer("vk_pw_m2", pair_f64_bytes, 2n);
      let d_pref = GeoPNG.gpu.acquireBuffer("vk_pw_pref", pair_f32_bytes, 1n);
      let d_u = GeoPNG.gpu.acquireBuffer("vk_pw_u", pair_f32_bytes, 1n);

      if (!d_m1 || !d_m2 || !d_pref || !d_u || !kernel) return false;

      if (this._last_pw_u_ref !== u_matrix) {
        cl.clEnqueueWriteBuffer(queue, d_u.mem, 1, 0, pair_f32_bytes, _bufView(u_matrix), 0, null, null);
        this._last_pw_u_ref = u_matrix;
      }
      if (this._last_pw_pref_ref !== scale_pref_mat) {
        cl.clEnqueueWriteBuffer(queue, d_pref.mem, 1, 0, pair_f32_bytes, _bufView(scale_pref_mat), 0, null, null);
        this._last_pw_pref_ref = scale_pref_mat;
      }

      this.dispatchWavesSync(pair_count, 0, function (arg0_off, arg1_cnt, arg2_glob, arg3_loc) {
        cl.clSetKernelArgMem(kernel, 0, 8, [d_u.mem]);
        cl.clSetKernelArgMem(kernel, 1, 8, [d_pref.mem]);
        cl.clSetKernelArgMem(kernel, 2, 8, [d_m1.mem]);
        cl.clSetKernelArgMem(kernel, 3, 8, [d_m2.mem]);
        cl.clSetKernelArgU32(kernel, 4, 4, [arg0_off]);
        cl.clSetKernelArgU32(kernel, 5, 4, [arg1_cnt]);
        cl.clSetKernelArgU32(kernel, 6, 4, [n_obs]);
        cl.clSetKernelArgF32(kernel, 7, 4, [inv_t1_s3]);
        cl.clSetKernelArgF32(kernel, 8, 4, [inv_t2_s3]);
        cl.clEnqueueNDRangeKernel(queue, kernel, 1, null, [arg2_glob], [arg3_loc], 0, null, null);
      });

      cl.clEnqueueReadBuffer(queue, d_m1.mem, 1, 0, pair_f64_bytes, _bufView(m1_mat), 0, null, null);
      cl.clEnqueueReadBuffer(queue, d_m2.mem, 1, 0, pair_f64_bytes, _bufView(m2_mat), 0, null, null);

      //Return statement
      return true;
    }


    /**
     * Returns fast lossless PNG.sync.write options aligned with GeoPNG compute governance.
     * @alias ViscountKrigingGPU.getFastPNGWriteOptions
     *
     * @returns {Object}
     */
    static getFastPNGWriteOptions () {
      //Declare local instance variables
      let io_cfg = (global.GeoPNG && GeoPNG.compute_limits && GeoPNG.compute_limits.io) ? GeoPNG.compute_limits.io : {};

      //Return statement
      return {
        colorType: 6,
        deflateLevel: (io_cfg.png_compression_level !== undefined) ? Number(io_cfg.png_compression_level) : 1,
        filterType: (io_cfg.png_filter_type !== undefined) ? Number(io_cfg.png_filter_type) : 0
      };
    }


    /**
     * Compiles Viscount kriging OpenCL kernels onto the shared GeoPNG NVIDIA OpenCL context.
     * @alias ViscountKrigingGPU.init
     *
     * @param {Object} [arg0_options]
     *
     * @returns {boolean}
     */
    static init (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Guard clauses
      if (this._ready && GeoPNG.gpu && GeoPNG.gpu._ready) return true;
      if (this._init_attempted && !options.force) return false;
      this._init_attempted = true;

      if (!global.GeoPNG || !GeoPNG.gpu || !GeoPNG.gpu.isAvailable()) return false;

      //Declare local instance variables
      let cl = GeoPNG.gpu._cl;
      let ctx = GeoPNG.gpu._ctx;
      let dev = GeoPNG.gpu._device;
      let err = [0];
      let kernel_names = [
        "viscount_fill_matern_kernels",
        "viscount_matern_eval_potentials",
        "viscount_pairwise_u_pref",
        "viscount_residual_matern_multi",
        "viscount_smooth_grid_h",
        "viscount_smooth_grid_v",
        "viscount_voronoi_nearest"
      ];

      //Function body
      GeoPNG.applyBackgroundProcessPriority();

      try {
        let prog = cl.clCreateProgramWithSource(ctx, 1, [VISCOUNT_OPENCL_KERNELS], null, err);
        let brc = cl.clBuildProgram(prog, 1, [dev], "-cl-mad-enable -cl-no-signed-zeros", null, null);

        if (brc !== 0) {
          let log_buf = Buffer.alloc(16384);
          let sz = [0];

          cl.clGetProgramBuildInfo(prog, dev, 0x1183, 16384, log_buf, sz);
          console.error(`- [ViscountKrigingGPU] OpenCL build failed (${brc}): ${log_buf.toString("utf8", 0, sz[0])}`);
          cl.clReleaseProgram(prog);
          return false;
        }

        let kernels = {};
        for (let i = 0; i < kernel_names.length; i++) {
          let kname = kernel_names[i];
          let k = cl.clCreateKernel(prog, kname, err);

          if (!k || err[0] !== 0) {
            console.error(`- [ViscountKrigingGPU] clCreateKernel(${kname}) failed (${err[0]}).`);
            return false;
          }
          kernels[kname] = k;
        }

        this._kernels = kernels;
        this._program = prog;
        this._ready = true;

        if (!this._shutdown_registered && Array.isArray(GeoPNG.gpu._shutdown_hooks)) {
          this._shutdown_registered = true;
          GeoPNG.gpu._shutdown_hooks.push(function () {
            ViscountKrigingGPU.shutdown();
          });
        }

        //Return statement
        return true;
      } catch (e) {
        console.error(`- [ViscountKrigingGPU] Initialisation error:`, e.message || e);
        return false;
      }
    }


    /**
     * Returns whether Viscount OpenCL GPU kriging kernels are compiled and ready.
     * @alias ViscountKrigingGPU.isAvailable
     *
     * @returns {boolean}
     */
    static isAvailable () {
      //Function body
      if (this._ready && global.GeoPNG && GeoPNG.gpu && GeoPNG.gpu._ready) return true;
      if (this._ready && (!global.GeoPNG || !GeoPNG.gpu || !GeoPNG.gpu._ready)) {
        this._ready = false;
        this._init_attempted = false;
      }
      if (!this._ready && !this._init_attempted)
        this.init();

      //Return statement
      return Boolean(this._ready && global.GeoPNG && GeoPNG.gpu && GeoPNG.gpu._ready);
    }


    /**
     * Releases Viscount OpenCL program, kernels, and cached mask references.
     * @alias ViscountKrigingGPU.shutdown
     */
    static shutdown () {
      //Declare local instance variables
      let cl = (global.GeoPNG && GeoPNG.gpu) ? GeoPNG.gpu._cl : null;

      //Function body
      if (cl && this._kernels) {
        let names = Object.keys(this._kernels);

        for (let i = 0; i < names.length; i++) {
          try { cl.clReleaseKernel(this._kernels[names[i]]); } catch (e) {}
        }
      }
      if (cl && this._program) {
        try { cl.clReleaseProgram(this._program); } catch (e) {}
      }

      this._init_attempted = false;
      this._kernels = {};
      this._last_lut_f32 = null;
      this._last_lut_src = null;
      this._last_p2v_ref = null;
      this._last_pw_pref_ref = null;
      this._last_pw_u_ref = null;
      this._last_vidx_ref = null;
      this._program = null;
      this._ready = false;
    }


    /**
     * Executes multi-pass separable tent/Gaussian smoothing resident in VRAM on the NVIDIA GPU.
     * Matches `ViscountHUResidualHelpers.smoothGaussianGrid` with partition, gate, positive-only, and elevation gating.
     * @alias ViscountKrigingGPU.smoothGaussianGrid
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_field
     * @param {number} arg2_rad_px
     * @param {number} arg3_passes
     * @param {Int32Array|null} arg4_part_ids
     * @param {boolean} arg5_pos_only
     * @param {Float32Array|Uint8Array|null} arg6_active_gate
     * @param {Float32Array|null} arg7_elev_valid
     *
     * @returns {Float32Array|null}
     */
    static smoothGaussianGrid (arg0_mask_data, arg1_field, arg2_rad_px, arg3_passes, arg4_part_ids, arg5_pos_only, arg6_active_gate, arg7_elev_valid) {
      //Convert from parameters
      let elev_v = arg7_elev_valid ? _asF32(arg7_elev_valid) : null;
      let field = _asF32(arg1_field);
      let gate = arg6_active_gate ? _asF32(arg6_active_gate) : null;
      let mask_data = arg0_mask_data;
      let part_ids = arg4_part_ids ? _asI32(arg4_part_ids) : null;
      let passes = Math.max(1, arg3_passes || 3);
      let pos_only = Boolean(arg5_pos_only);
      let rad = Math.max(1, arg2_rad_px || 4);

      //Guard clauses
      if (!mask_data || !field) return null;
      let n_valid = mask_data.valid_cell_count;
      if (n_valid < 4096 || !this.isAvailable()) return null;

      //Declare local instance variables
      let cell_bytes = n_valid*4;
      let cl = GeoPNG.gpu._cl;
      let flags = (gate ? 1 : 0) | (pos_only ? 2 : 0) | (part_ids ? 4 : 0) | (elev_v ? 8 : 0);
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let kh = this._kernels.viscount_smooth_grid_h;
      let kv = this._kernels.viscount_smooth_grid_v;
      let p2v = mask_data.pixel_to_valid_idx;
      let queue = GeoPNG.gpu._queue;
      let v_idx = mask_data.valid_indices;

      //Function body
      let d_cur = GeoPNG.gpu.acquireBuffer("vk_sm_cur", cell_bytes, 1n);
      let d_elev = GeoPNG.gpu.acquireBuffer("vk_sm_elev", elev_v ? cell_bytes : 16, 4n);
      let d_gate = GeoPNG.gpu.acquireBuffer("vk_sm_gate", gate ? cell_bytes : 16, 4n);
      let d_orig = GeoPNG.gpu.acquireBuffer("vk_sm_orig", cell_bytes, 4n);
      let d_p2v = GeoPNG.gpu.acquireBuffer("vk_sm_p2v", p2v.byteLength, 4n);
      let d_part = GeoPNG.gpu.acquireBuffer("vk_sm_part", part_ids ? cell_bytes : 16, 4n);
      let d_tmp = GeoPNG.gpu.acquireBuffer("vk_sm_tmp", cell_bytes, 1n);
      let d_vidx = GeoPNG.gpu.acquireBuffer("vk_sm_vidx", v_idx.byteLength, 4n);

      if (!d_cur || !d_elev || !d_gate || !d_orig || !d_p2v || !d_part || !d_tmp || !d_vidx || !kh || !kv)
        return null;

      //Pin static mask lookup tables across the 128-year smoothing loop
      d_p2v.pinned = true;
      d_vidx.pinned = true;
      if (this._last_p2v_ref !== p2v) {
        cl.clEnqueueWriteBuffer(queue, d_p2v.mem, 1, 0, p2v.byteLength, _bufView(p2v), 0, null, null);
        this._last_p2v_ref = p2v;
      }
      if (this._last_vidx_ref !== v_idx) {
        cl.clEnqueueWriteBuffer(queue, d_vidx.mem, 1, 0, v_idx.byteLength, _bufView(v_idx), 0, null, null);
        this._last_vidx_ref = v_idx;
      }

      cl.clEnqueueWriteBuffer(queue, d_cur.mem, 1, 0, cell_bytes, _bufView(field), 0, null, null);
      if (pos_only) cl.clEnqueueWriteBuffer(queue, d_orig.mem, 1, 0, cell_bytes, _bufView(field), 0, null, null);
      if (part_ids) _uploadCached(queue, cl, d_part, part_ids);
      if (gate) cl.clEnqueueWriteBuffer(queue, d_gate.mem, 1, 0, cell_bytes, _bufView(gate), 0, null, null);
      if (elev_v) _uploadCached(queue, cl, d_elev, elev_v);

      for (let pass = 0; pass < passes; pass++) {
        this.dispatchWavesSync(n_valid, 0, function (arg0_off, arg1_cnt, arg2_glob, arg3_loc) {
          cl.clSetKernelArgMem(kh, 0, 8, [d_cur.mem]);
          cl.clSetKernelArgMem(kh, 1, 8, [d_tmp.mem]);
          cl.clSetKernelArgMem(kh, 2, 8, [d_vidx.mem]);
          cl.clSetKernelArgMem(kh, 3, 8, [d_p2v.mem]);
          cl.clSetKernelArgMem(kh, 4, 8, [d_part.mem]);
          cl.clSetKernelArgMem(kh, 5, 8, [d_gate.mem]);
          cl.clSetKernelArgMem(kh, 6, 8, [d_elev.mem]);
          cl.clSetKernelArgU32(kh, 7, 4, [arg0_off]);
          cl.clSetKernelArgU32(kh, 8, 4, [arg1_cnt]);
          cl.clSetKernelArgI32(kh, 9, 4, [grid_w]);
          cl.clSetKernelArgI32(kh, 10, 4, [rad]);
          cl.clSetKernelArgU32(kh, 11, 4, [flags]);
          cl.clEnqueueNDRangeKernel(queue, kh, 1, null, [arg2_glob], [arg3_loc], 0, null, null);
        });

        this.dispatchWavesSync(n_valid, 0, function (arg0_off, arg1_cnt, arg2_glob, arg3_loc) {
          cl.clSetKernelArgMem(kv, 0, 8, [d_tmp.mem]);
          cl.clSetKernelArgMem(kv, 1, 8, [d_orig.mem]);
          cl.clSetKernelArgMem(kv, 2, 8, [d_cur.mem]);
          cl.clSetKernelArgMem(kv, 3, 8, [d_vidx.mem]);
          cl.clSetKernelArgMem(kv, 4, 8, [d_p2v.mem]);
          cl.clSetKernelArgMem(kv, 5, 8, [d_part.mem]);
          cl.clSetKernelArgMem(kv, 6, 8, [d_gate.mem]);
          cl.clSetKernelArgMem(kv, 7, 8, [d_elev.mem]);
          cl.clSetKernelArgU32(kv, 8, 4, [arg0_off]);
          cl.clSetKernelArgU32(kv, 9, 4, [arg1_cnt]);
          cl.clSetKernelArgI32(kv, 10, 4, [grid_w]);
          cl.clSetKernelArgI32(kv, 11, 4, [grid_h]);
          cl.clSetKernelArgI32(kv, 12, 4, [rad]);
          cl.clSetKernelArgU32(kv, 13, 4, [flags]);
          cl.clEnqueueNDRangeKernel(queue, kv, 1, null, [arg2_glob], [arg3_loc], 0, null, null);
        });
      }

      let out_cur = new Float32Array(n_valid);
      cl.clEnqueueReadBuffer(queue, d_cur.mem, 1, 0, cell_bytes, _bufView(out_cur), 0, null, null);

      //Return statement
      return out_cur;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountKrigingGPU: global.ViscountKrigingGPU };
