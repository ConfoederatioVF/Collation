//Temporary verification harness for Operation Viscount GPU Kriging (pure Node.js OpenCL 3.0)
let path = require("path");
let { ViscountMaternKriging } = require("../histmap/3.data_transform/population_Substrata.viscount/ViscountMaternKriging.js");
let { ViscountMaternVariogram } = require("../histmap/3.data_transform/population_Substrata.viscount/ViscountMaternVariogram.js");
let { ViscountDasymetricResidualSolver } = require("../histmap/3.data_transform/population_Substrata.viscount/ViscountDasymetricResidualSolver.js");
let { ViscountHUResidualHelpers } = require("../histmap/3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualHelpers.js");
let { ViscountKrigingGPU } = require("../histmap/3.data_transform/population_Substrata.viscount/ViscountKrigingGPU.js");

let compareArrays = function (arg0_a, arg1_b) {
  let max_abs = 0;
  let max_rel = 0;
  let sum_a = 0;
  let sum_b = 0;
  let zero_mismatches = 0;

  for (let i = 0; i < arg0_a.length; i++) {
    let va = arg0_a[i];
    let vb = arg1_b[i];
    let diff = Math.abs(va - vb);
    let denom = Math.max(1e-6, Math.abs(va), Math.abs(vb));
    let rel = diff/denom;

    sum_a += va;
    sum_b += vb;
    if (diff > max_abs) max_abs = diff;
    if (rel > max_rel) max_rel = rel;
    if ((va > 0) !== (vb > 0)) zero_mismatches++;
  }

  let sum_rel = Math.abs(sum_a - sum_b)/Math.max(1e-9, Math.abs(sum_a));
  return { max_abs: max_abs, max_rel: max_rel, sum_a: sum_a, sum_b: sum_b, sum_rel: sum_rel, zero_mismatches: zero_mismatches };
};

let main = function () {
  let cfg_path = path.resolve("histmap/1.data_raw/population_regional/MANDALA/_shared/sites_mandala_southeast_asia/config/sites_mandala_southeast_asia.json5");
  let all_pass = true;

  console.log("=== VISCOUNT KRIGING GPU EQUIVALENCE & BENCHMARK (MANDALA DOMAIN) ===");
  let ok_init = ViscountKrigingGPU.init();
  console.log("ViscountKrigingGPU.init():", ok_init, "| GeoPNG.gpu:", GeoPNG.gpu.getStatus().device_info);
  if (!ok_init) process.exit(1);

  let dom_cpu = ViscountMaternKriging.A_loadDomainConfigAndSites(cfg_path);
  let dom_gpu = ViscountMaternKriging.A_loadDomainConfigAndSites(cfg_path);
  console.log(`Domain loaded: n_valid=${dom_cpu.mask_data.valid_cell_count}, n_obs=${dom_cpu.obs_list.length}, periods=${dom_cpu.config.periods.length}`);

  //1. Step B: Geodesic Voronoi Nearest Catchment
  let t0 = performance.now();
  let b_cpu = ViscountMaternKriging.B_computeEmpiricalBayesIntensities(dom_cpu, { use_gpu: false });
  let ms_b_cpu = performance.now() - t0;

  t0 = performance.now();
  let b_gpu = ViscountMaternKriging.B_computeEmpiricalBayesIntensities(dom_gpu, { use_gpu: true });
  let ms_b_gpu = performance.now() - t0;

  let voronoi_mismatch = 0;
  for (let i = 0; i < b_cpu.cell_nearest_obs.length; i++) {
    if (b_cpu.cell_nearest_obs[i] !== b_gpu.cell_nearest_obs[i]) voronoi_mismatch++;
  }
  let pass_b = (voronoi_mismatch === 0);
  if (!pass_b) all_pass = false;
  console.log(`[1] Step B Voronoi: CPU=${ms_b_cpu.toFixed(1)} ms | GPU=${ms_b_gpu.toFixed(1)} ms | speedup=${(ms_b_cpu/Math.max(0.1, ms_b_gpu)).toFixed(2)}x | mismatches=${voronoi_mismatch} | ${pass_b ? "PASS" : "FAIL"}`);

  //2. Step C: Pairwise u_matrix/scale_pref + Two-Scale Matern Kernel Fill
  t0 = performance.now();
  let c_cpu = ViscountMaternVariogram.C_fitTwoScaleNonStationaryMatern(b_cpu, { use_gpu: false });
  let ms_c_cpu = performance.now() - t0;

  t0 = performance.now();
  let c_gpu = ViscountMaternVariogram.C_fitTwoScaleNonStationaryMatern(b_gpu, { use_gpu: true });
  let ms_c_gpu = performance.now() - t0;

  let pkeys = Object.keys(c_cpu.kriging_models);
  let max_w_rel = 0;
  for (let i = 0; i < pkeys.length; i++) {
    let cmp = compareArrays(c_cpu.kriging_models[pkeys[i]].dual_weights, c_gpu.kriging_models[pkeys[i]].dual_weights);
    if (cmp.max_rel > max_w_rel) max_w_rel = cmp.max_rel;
  }
  let pass_c = (max_w_rel < 1e-4);
  if (!pass_c) all_pass = false;
  console.log(`[2] Step C Variogram & Kernels: CPU=${ms_c_cpu.toFixed(1)} ms | GPU=${ms_c_gpu.toFixed(1)} ms | speedup=${(ms_c_cpu/Math.max(0.1, ms_c_gpu)).toFixed(2)}x | dual_weights max_rel=${max_w_rel.toExponential(2)} | ${pass_c ? "PASS" : "FAIL"}`);

  //3. Step E: Two-Scale Paciorek-Schervish Matern Potentials + Residual Matern Multi-Period
  global._viscount_force_cpu_smooth = true;
  if (c_cpu.config && c_cpu.config.kriging_config && c_cpu.config.kriging_config.hu_residual_kriging)
    c_cpu.config.kriging_config.hu_residual_kriging.use_gpu = false;
  t0 = performance.now();
  let e_cpu = ViscountMaternKriging.E_fitCarryCapacityResidualSurface(c_cpu, { use_gpu: false });
  let ms_e_cpu = performance.now() - t0;

  global._viscount_force_cpu_smooth = false;
  if (c_gpu.config && c_gpu.config.kriging_config && c_gpu.config.kriging_config.hu_residual_kriging)
    c_gpu.config.kriging_config.hu_residual_kriging.use_gpu = true;
  t0 = performance.now();
  let e_gpu = ViscountMaternKriging.E_fitCarryCapacityResidualSurface(c_gpu, { use_gpu: true });
  let ms_e_gpu = performance.now() - t0;

  let max_pot_rel = 0;
  let max_pot_sum_rel = 0;
  let pot_zero_mm = 0;
  for (let i = 0; i < pkeys.length; i++) {
    let cmp = compareArrays(e_cpu.raw_potentials[pkeys[i]], e_gpu.raw_potentials[pkeys[i]]);
    if (cmp.max_rel > max_pot_rel) max_pot_rel = cmp.max_rel;
    if (cmp.sum_rel > max_pot_sum_rel) max_pot_sum_rel = cmp.sum_rel;
    pot_zero_mm += cmp.zero_mismatches;
  }

  let max_fld_rel = 0;
  let max_fld_sum_rel = 0;
  let fld_zero_mm = 0;
  for (let i = 0; i < pkeys.length; i++) {
    let cmp = compareArrays(e_cpu.fields[pkeys[i]], e_gpu.fields[pkeys[i]]);
    if (cmp.max_rel > max_fld_rel) max_fld_rel = cmp.max_rel;
    if (cmp.sum_rel > max_fld_sum_rel) max_fld_sum_rel = cmp.sum_rel;
    fld_zero_mm += cmp.zero_mismatches;
  }

  let pass_e = (max_pot_rel < 1e-4 && max_pot_sum_rel < 1e-5 && max_fld_rel < 1e-3 && max_fld_sum_rel < 1e-5 && pot_zero_mm === 0);
  if (!pass_e) all_pass = false;
  console.log(`[3] Step E Full Surface (Potentials + Residual Matern + Smooth): CPU=${ms_e_cpu.toFixed(1)} ms | GPU=${ms_e_gpu.toFixed(1)} ms | speedup=${(ms_e_cpu/Math.max(0.1, ms_e_gpu)).toFixed(2)}x`);
  console.log(`    raw_potentials: max_rel=${max_pot_rel.toExponential(2)}, sum_rel=${max_pot_sum_rel.toExponential(2)}, zero_mm=${pot_zero_mm}`);
  console.log(`    final fields  : max_rel=${max_fld_rel.toExponential(2)}, sum_rel=${max_fld_sum_rel.toExponential(2)}, zero_mm=${fld_zero_mm} | ${pass_e ? "PASS" : "FAIL"}`);

  //4. Direct smoothGaussianGrid equivalence & speedup (with elevation + pos_only gating)
  let sample_field = e_cpu.fields[pkeys[pkeys.length - 1]];
  let elev_dummy = new Float32Array(dom_cpu.mask_data.valid_cell_count);
  for (let i = 0; i < elev_dummy.length; i++) elev_dummy[i] = (i % 7)*180.0;

  global._viscount_force_cpu_smooth = true;
  t0 = performance.now();
  let sm_cpu = ViscountHUResidualHelpers.smoothGaussianGrid(dom_cpu.mask_data, sample_field, 6, 3, null, true, null, elev_dummy);
  let ms_sm_cpu = performance.now() - t0;

  global._viscount_force_cpu_smooth = false;
  //Warm-up + timed run (simulating cached mask in 128-year loop)
  ViscountHUResidualHelpers.smoothGaussianGrid(dom_cpu.mask_data, sample_field, 6, 3, null, true, null, elev_dummy);
  t0 = performance.now();
  let sm_gpu = ViscountHUResidualHelpers.smoothGaussianGrid(dom_cpu.mask_data, sample_field, 6, 3, null, true, null, elev_dummy);
  let ms_sm_gpu = performance.now() - t0;

  let cmp_sm = compareArrays(sm_cpu, sm_gpu);
  let pass_sm = (cmp_sm.max_rel < 1e-4 && cmp_sm.zero_mismatches === 0);
  if (!pass_sm) all_pass = false;
  console.log(`[4] smoothGaussianGrid (r=6, 3 passes, elev-gated): CPU=${ms_sm_cpu.toFixed(1)} ms | GPU=${ms_sm_gpu.toFixed(1)} ms | speedup=${(ms_sm_cpu/Math.max(0.1, ms_sm_gpu)).toFixed(2)}x | max_rel=${cmp_sm.max_rel.toExponential(2)}, zero_mm=${cmp_sm.zero_mismatches} | ${pass_sm ? "PASS" : "FAIL"}`);

  //4b. Isolated kernel-only microbenchmarks (excluding static disk/ASC/GeoJSON I/O)
  let m = dom_cpu.mask_data;
  let n_obs = b_cpu.obs_count;
  let n_valid = m.valid_cell_count;
  t0 = performance.now();
  let tmp_cn = new Int32Array(n_valid);
  for (let i = 0; i < n_valid; i++) {
    let bd = -2, bi = 0, cx = m.cell_ux[i], cy = m.cell_uy[i], cz = m.cell_uz[i];
    for (let x = 0; x < n_obs; x++) {
      let d = cx*b_cpu.obs_ux[x] + cy*b_cpu.obs_uy[x] + cz*b_cpu.obs_uz[x];
      if (d > bd) { bd = d; bi = x; }
    }
    tmp_cn[i] = bi;
  }
  let ms_vor_cpu = performance.now() - t0;
  t0 = performance.now();
  ViscountKrigingGPU.computeVoronoiNearest(m.cell_ux, m.cell_uy, m.cell_uz, b_cpu.obs_ux, b_cpu.obs_uy, b_cpu.obs_uz);
  let ms_vor_gpu = performance.now() - t0;

  let active_p = [];
  for (let i = 0; i < pkeys.length; i++) {
    let mod = c_cpu.kriging_models[pkeys[i]];
    active_p.push({
      c1: mod.c1_weight, c2: mod.c2_weight,
      inv_tau1: 1/Math.max(0.4, mod.tau1_dimensionless || c_cpu.tau1_dimensionless),
      inv_tau2: 1/Math.max(0.8, mod.tau2_dimensionless || c_cpu.tau2_dimensionless),
      pot: new Float32Array(n_valid), var_restore: mod.centroid_variance_restoration || 1.0, w: mod.dual_weights
    });
  }
  let min_dot = new Float64Array(n_obs).fill(-2.0);
  t0 = performance.now();
  ViscountKrigingGPU.evaluateMaternPotentials({
    active_periods: active_p, cell_area: m.cell_land_area, cell_r: b_cpu.cell_radius_km,
    cell_ux: m.cell_ux, cell_uy: m.cell_uy, cell_uz: m.cell_uz, earth_r: m.earth_radius_km,
    lut: c_cpu.matern_lut, min_dot_per_obs: min_dot, n_obs: n_obs, n_valid: n_valid,
    obs_r: b_cpu.obs_radius_km, obs_ux: b_cpu.obs_ux, obs_uy: b_cpu.obs_uy, obs_uz: b_cpu.obs_uz, shared_tau: false
  });
  let ms_pot_gpu = performance.now() - t0;

  //Also time isolated CPU Matern potential loop (same inputs)
  let lut = c_cpu.matern_lut, lut_scale = 8191/8, z_acc = new Float64Array(active_p.length);
  t0 = performance.now();
  for (let i = 0; i < n_valid; i++) {
    let a_i = m.cell_land_area[i], cx = m.cell_ux[i], cy = m.cell_uy[i], cz = m.cell_uz[i], ri = b_cpu.cell_radius_km[i], ri2 = ri*ri;
    z_acc.fill(0);
    for (let x = 0; x < n_obs; x++) {
      let dot = Math.max(-1, Math.min(1, cx*b_cpu.obs_ux[x] + cy*b_cpu.obs_uy[x] + cz*b_cpu.obs_uz[x]));
      let c2 = Math.max(0, 2 - 2*dot), h = m.earth_radius_km*Math.sqrt(c2)*(1 + c2/24);
      let rx = b_cpu.obs_radius_km[x], r2_sum = ri2 + rx*rx, u = h/Math.sqrt(0.5*r2_sum), pref = (2*ri*rx)/Math.max(1e-8, r2_sum);
      for (let p = 0; p < active_p.length; p++) {
        let ap = active_p[p], wp = ap.w[x];
        if (wp <= 0) continue;
        let v2 = u*ap.inv_tau2;
        if (v2 >= 7.99) continue;
        let m1 = 0, v1 = u*ap.inv_tau1;
        if (v1 < 7.99) { let i1 = (v1*lut_scale) | 0, f1 = v1*lut_scale - i1; m1 = pref*(lut[i1]*(1 - f1) + lut[i1 + 1]*f1); }
        let i2 = (v2*lut_scale) | 0, f2 = v2*lut_scale - i2, m2 = pref*(lut[i2]*(1 - f2) + lut[i2 + 1]*f2);
        z_acc[p] += wp*(ap.c1*m1 + ap.c2*m2);
      }
    }
    for (let p = 0; p < active_p.length; p++) active_p[p].pot[i] = a_i*Math.pow(Math.max(0, active_p[p].var_restore*z_acc[p]), 2.25);
  }
  let ms_pot_cpu = performance.now() - t0;

  let v_vecs = pkeys.map(function (arg0_k) { return c_cpu.kriging_models[arg0_k].dual_weights; });
  let prior_b = pkeys.map(function () { return { prior_dens: new Float32Array(n_valid).fill(1.0) }; });
  let r_f = pkeys.map(function () { return new Float32Array(n_valid); });
  let pop_f = pkeys.map(function () { return new Float32Array(n_valid); });
  let obs_elev = new Float64Array(n_obs).fill(200.0);
  t0 = performance.now();
  ViscountKrigingGPU.evaluateResidualMaternMulti({
    c1: 0.78, c2: 0.22, cell_area: m.cell_land_area, cell_obs: b_cpu.cell_nearest_obs, cell_r: b_cpu.cell_radius_km,
    cell_ux: m.cell_ux, cell_uy: m.cell_uy, cell_uz: m.cell_uz, cross_catch_mult: 0.82, earth_r: m.earth_radius_km,
    elev_valid: elev_dummy, inv_eb: 1/650, inv_tau1: 1/0.8, inv_tau2: 1/1.8, lut: lut, min_dot: min_dot,
    n_obs: n_obs, n_p: pkeys.length, n_valid: n_valid, obs_elev_m: obs_elev, obs_r: b_cpu.obs_radius_km,
    obs_ux: b_cpu.obs_ux, obs_uy: b_cpu.obs_uy, obs_uz: b_cpu.obs_uz, pop_fields: pop_f, prior_bundles: prior_b,
    r_clamp_max: 1.3, r_clamp_min: -1.2, r_fields: r_f, r_gain: 0.88, v_vecs: v_vecs
  });
  let ms_res_gpu = performance.now() - t0;

  console.log(`[4b] Isolated Kernel Compute (no disk I/O):`);
  console.log(`     Voronoi (${n_valid}x${n_obs}): CPU=${ms_vor_cpu.toFixed(1)} ms | GPU=${ms_vor_gpu.toFixed(2)} ms | speedup=${(ms_vor_cpu/Math.max(0.05, ms_vor_gpu)).toFixed(1)}x`);
  console.log(`     Matern Potentials (${n_valid}x${n_obs}x${pkeys.length}): CPU=${ms_pot_cpu.toFixed(1)} ms | GPU=${ms_pot_gpu.toFixed(2)} ms | speedup=${(ms_pot_cpu/Math.max(0.05, ms_pot_gpu)).toFixed(1)}x`);
  console.log(`     Residual Matern Multi (${n_valid}x${n_obs}x${pkeys.length}): GPU=${ms_res_gpu.toFixed(2)} ms`);

  //5. Fast lossless PNG export equivalence & speedup (in-memory, zero disk overwrite)
  let { PNG } = require("pngjs");
  let png_img = new PNG({ colorType: 6, height: dom_cpu.mask_data.grid_height, width: dom_cpu.mask_data.grid_width });
  let f_dv = new DataView(new ArrayBuffer(4));
  for (let i = 0; i < dom_cpu.mask_data.valid_cell_count; i++) {
    if (sample_field[i] > 0) {
      let px = dom_cpu.mask_data.valid_indices[i]*4;
      f_dv.setFloat32(0, sample_field[i], false);
      png_img.data[px] = f_dv.getUint8(0);
      png_img.data[px + 1] = f_dv.getUint8(1);
      png_img.data[px + 2] = f_dv.getUint8(2);
      png_img.data[px + 3] = f_dv.getUint8(3);
    }
  }
  t0 = performance.now();
  let buf_legacy = PNG.sync.write(png_img, { colorType: 6, deflateLevel: 6 });
  let ms_png_legacy = performance.now() - t0;
  t0 = performance.now();
  let buf_fast = PNG.sync.write(png_img, ViscountKrigingGPU.getFastPNGWriteOptions());
  let ms_png_fast = performance.now() - t0;
  let dec_legacy = PNG.sync.read(buf_legacy).data;
  let dec_fast = PNG.sync.read(buf_fast).data;
  let png_diff_bytes = 0;
  for (let i = 0; i < dec_legacy.length; i++) if (dec_legacy[i] !== dec_fast[i]) png_diff_bytes++;
  let pass_png = (png_diff_bytes === 0);
  if (!pass_png) all_pass = false;
  console.log(`[5] GeoPNG 4320x2160 Sync Export: legacy(d=6)=${ms_png_legacy.toFixed(1)} ms | fast(d=1,f=0)=${ms_png_fast.toFixed(1)} ms | speedup=${(ms_png_legacy/Math.max(0.1, ms_png_fast)).toFixed(2)}x | diff_bytes=${png_diff_bytes} | ${pass_png ? "PASS" : "FAIL"}`);

  //6. Resource governance telemetry & clean shutdown
  let st_before = GeoPNG.gpu.getStatus();
  let rss_mb = Number((process.memoryUsage().rss/1048576).toFixed(1));
  let pass_gov = (st_before.allocated_vram_mb <= st_before.limits.gpu.max_vram_mb && rss_mb <= st_before.limits.ram.max_ram_mb);
  GeoPNG.gpu.shutdown();
  let st_after = GeoPNG.gpu.getStatus();
  let pass_shutdown = (st_after.allocated_vram_mb === 0 && !st_after.ready && !ViscountKrigingGPU._ready);
  if (!pass_gov || !pass_shutdown) all_pass = false;

  console.log(`[6] Governance: peak_vram=${st_before.allocated_vram_mb} MiB (cap=${st_before.limits.gpu.max_vram_mb}), rss=${rss_mb} MiB (cap=${st_before.limits.ram.max_ram_mb}), post_shutdown_vram=${st_after.allocated_vram_mb} MiB | ${(pass_gov && pass_shutdown) ? "PASS" : "FAIL"}`);
  console.log(all_pass ? "=== ALL VISCOUNT GPU KRIGING TESTS PASSED ===" : "=== SOME TESTS FAILED ===");
  process.exit(all_pass ? 0 : 1);
};

main();
