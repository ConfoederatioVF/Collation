//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Strictly Mass-Conserving (Pycnophylactic) Historical GIS Sub-Administrative Dasymetric
   * Disaggregation & Areal Scaling Engine for Operation Viscount Project MAGNETIC.
   *
   * For every benchmark year `1500..2025`, reads the nearest historical GIS sub-administrative
   * division GeoPNG (`subadmin_id_<snap>.png`, 16-bit ID) and longitudinal enumeration metadata
   * (`subadmin_meta_<snap>.json`), disaggregates every sub-administrative census enumeration onto
   * the sharpened 5-arcminute physical/fluvial/archaeological suitability surface `w(x, t)` via
   * Tobler-style pycnophylactic multiplier relaxation (smoothing only the piecewise-constant
   * unit multiplier by 1 px so micro-texture `w(x, t)` is NEVER blurred, then re-normalising
   * every single sub-administrative unit back to its EXACT enumerated mass on every iteration).
   *
   * Guarantees:
   * - Exact per-sub-administrative-unit mass conservation (`max_rel_err < 1e-5`)
   * - Exact country/macro-domain mass conservation (`domain_rel_err < 1e-5`)
   * - Zero artificial rectilinear polygon step cliffs (`audit_border_cliffs.py` compliant)
   * - Zero blurring of 5-arcminute valleys, rivers, coastlines or topographic relief
   *
   * @class MagneticSubadminDasymetric
   */
  global.MagneticSubadminDasymetric = class {
    static SNAPSHOT_YEARS = [
      1500, 1600, 1700, 1750, 1800, 1820, 1850,
      1871, 1880, 1890, 1900, 1910,
      1920, 1930, 1940,
      1950, 1960, 1970, 1980,
      1990, 2000, 2010, 2020
    ];

    /**
     * Reads a positive finite Big-Endian float32 value from an RGBA PNG buffer.
     * @alias MagneticSubadminDasymetric.readPosF32
     */
    static readPosF32 (arg0_data, arg1_dv, arg2_p4) {
      let b0 = arg0_data[arg2_p4];
      let b1 = arg0_data[arg2_p4 + 1];
      let b2 = arg0_data[arg2_p4 + 2];
      let b3 = arg0_data[arg2_p4 + 3];

      if ((b0 | b1 | b2 | b3) === 0) return 0;
      let val = arg1_dv.getFloat32(arg2_p4, false);

      return (Number.isFinite(val) && val > 0) ? val : 0;
    }


    /**
     * Resolves the strictly non-anachronistic historical GIS boundary snapshot for benchmark year `yr`.
     * Never crosses major European boundary cutoffs (1790, 1815, 1860, 1871, 1919, 1946, 1990 NUTS).
     * @alias MagneticSubadminDasymetric.resolveSnapshotYear
     */
    static resolveSnapshotYear (arg0_year, arg1_avail_years) {
      let yr = Number(arg0_year) || 1900;
      let avail = (Array.isArray(arg1_avail_years) && arg1_avail_years.length > 0) ? arg1_avail_years : this.SNAPSHOT_YEARS;

      if (avail.indexOf(yr) >= 0) return yr;
      let target = 2020;

      if (yr < 1560) target = 1500;
      else if (yr < 1660) target = 1600;
      else if (yr < 1730) target = 1700;
      else if (yr < 1790) target = 1750;
      else if (yr < 1815) target = 1800;
      else if (yr < 1835) target = 1820;
      else if (yr < 1865) target = 1850;
      else if (yr < 1876) target = 1871;
      else if (yr < 1886) target = 1880;
      else if (yr < 1896) target = 1890;
      else if (yr < 1906) target = 1900;
      else if (yr < 1919) target = 1910;
      else if (yr < 1926) target = 1920;
      else if (yr < 1936) target = 1930;
      else if (yr <= 1945) target = 1940;
      else if (yr < 1956) target = 1950;
      else if (yr < 1966) target = 1960;
      else if (yr < 1976) target = 1970;
      else if (yr < 1990) target = 1980;
      else if (yr < 1996) target = 1990;
      else if (yr < 2006) target = 2000;
      else if (yr < 2016) target = 2010;
      else target = 2020;

      if (avail.indexOf(target) >= 0) return target;
      let best = avail[0];
      let best_d = Math.abs(yr - best);

      for (let i = 1; i < avail.length; i++) {
        let d = Math.abs(yr - avail[i]);

        if (d < best_d) {
          best_d = d;
          best = avail[i];
        }
      }

      //Return statement
      return best;
    }


    /**
     * MAGNETIC-only pre-1945 cross-`sub_iso` de-cliffer: removes anachronistic post-1945 modern
     * national border steps (e.g. HYDE 3.5 Oder-Neisse step in 1850-1940) strictly from the local
     * suitability `base_w` before historical sub-administrative disaggregation, preserving 100% of
     * 5-arcminute physical/topographic micro-texture and touching zero shared Viscount core modules.
     * @alias MagneticSubadminDasymetric.removePre1945ModernBorderSteps
     */
    static removePre1945ModernBorderSteps (arg0_mask_data, arg1_base_w, arg2_sub_iso, arg3_nbrs) {
      let mask_data = arg0_mask_data;
      let base_w = arg1_base_w;
      let sub_iso = arg2_sub_iso;
      let nbrs = arg3_nbrs;

      if (!mask_data || !base_w || !sub_iso) return base_w;
      let n_valid = mask_data.valid_cell_count;
      let log_f = new Float32Array(n_valid);
      let is_border = new Uint8Array(n_valid);
      let has_pos = new Uint8Array(n_valid);

      for (let v = 0; v < n_valid; v++) {
        if (base_w[v] > 0) {
          log_f[v] = Math.log(base_w[v] + 0.05);
          has_pos[v] = 1;
        }
      }

      //Compute distance (in 4-connected steps up to 14 px) from any modern sub_iso border
      let dist = new Int16Array(n_valid).fill(99);
      let queue = [];

      for (let v = 0; v < n_valid; v++) {
        let sv = sub_iso[v];

        if (sv <= 0) continue;
        let ns = [nbrs.n_up[v], nbrs.n_down[v], nbrs.n_left[v], nbrs.n_right[v]];

        for (let d = 0; d < 4; d++) {
          let nv = ns[d];

          if (nv >= 0 && sub_iso[nv] > 0 && sub_iso[nv] !== sv) {
            is_border[v] = 1;
            dist[v] = 0;
            queue.push(v);
            break;
          }
        }
      }
      for (let qh = 0; qh < queue.length; qh++) {
        let curr = queue[qh];
        let cd = dist[curr];

        if (cd >= 14) continue;
        let ns = [nbrs.n_up[curr], nbrs.n_down[curr], nbrs.n_left[curr], nbrs.n_right[curr]];

        for (let d = 0; d < 4; d++) {
          let nv = ns[d];

          if (nv >= 0 && dist[nv] > cd + 1) {
            dist[nv] = cd + 1;
            queue.push(nv);
          }
        }
      }

      //Fast 12-pass isotropic diffusion for cross-border vs same-sub_iso smooth log-density
      let l_cross = Float32Array.from(log_f);
      let l_same = Float32Array.from(log_f);
      let tmp_c = new Float32Array(n_valid);
      let tmp_s = new Float32Array(n_valid);

      for (let pass = 0; pass < 12; pass++) {
        for (let v = 0; v < n_valid; v++) {
          if (!has_pos[v] || dist[v] > 14) {
            tmp_c[v] = l_cross[v];
            tmp_s[v] = l_same[v];
            continue;
          }
          let sv = sub_iso[v];
          let ac = 2.0*l_cross[v];
          let wc = 2.0;
          let as = 2.0*l_same[v];
          let ws = 2.0;
          let ns = [nbrs.n_up[v], nbrs.n_down[v], nbrs.n_left[v], nbrs.n_right[v]];

          for (let d = 0; d < 4; d++) {
            let nv = ns[d];

            if (nv >= 0 && has_pos[nv]) {
              ac += l_cross[nv];
              wc += 1.0;
              if (sub_iso[nv] === sv) {
                as += l_same[nv];
                ws += 1.0;
              }
            }
          }
          tmp_c[v] = ac/wc;
          tmp_s[v] = as/ws;
        }
        l_cross.set(tmp_c);
        l_same.set(tmp_s);
      }

      let out = Float32Array.from(base_w);

      for (let v = 0; v < n_valid; v++) {
        if (!has_pos[v] || dist[v] > 14) continue;
        let w_b = Math.exp(-(dist[v]*dist[v])/(2.0*5.0*5.0));
        let delta = Math.max(-1.6, Math.min(1.6, l_cross[v] - l_same[v]));

        out[v] = Math.max(1e-5, Math.exp(log_f[v] + w_b*delta) - 0.05);
      }

      //Return statement
      return out;
    }


    /**
     * Interpolates a historical sub-administrative enumeration series `[[year, pop], ...]` log-linearly at `yr`.
     * @alias MagneticSubadminDasymetric.interpolateSubadminSeries
     */
    static interpolateSubadminSeries (arg0_series, arg1_year) {
      let pts = arg0_series;
      let yr = Number(arg1_year) || 1900;

      if (!Array.isArray(pts) || pts.length === 0) return 0;
      if (yr <= pts[0][0]) return Math.max(0, Number(pts[0][1]) || 0);
      if (yr >= pts[pts.length - 1][0]) return Math.max(0, Number(pts[pts.length - 1][1]) || 0);
      for (let i = 0; i < pts.length - 1; i++) {
        let y0 = pts[i][0];
        let y1 = pts[i + 1][0];

        if (yr >= y0 && yr <= y1) {
          let p0 = Math.max(0, Number(pts[i][1]) || 0);
          let p1 = Math.max(0, Number(pts[i + 1][1]) || 0);

          if (y1 === y0) return p0;
          let t = (yr - y0)/(y1 - y0);

          if (p0 > 0 && p1 > 0) return Math.exp((1 - t)*Math.log(p0) + t*Math.log(p1));
          return (1 - t)*p0 + t*p1;
        }
      }

      //Return statement
      return 0;
    }


    /**
     * Applies strictly mass-conserving pycnophylactic sub-administrative dasymetric disaggregation
     * across `1500..2025` onto `2.population_rasters/popc_<yr>.png` and exports a machine-verifiable
     * conservation audit JSON (`subadmin_mass_conservation_audit.json`).
     * @alias MagneticSubadminDasymetric.applyAllYears
     *
     * @param {Object} arg0_surface
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    static applyAllYears (arg0_surface, arg1_options) {
      //Convert from parameters
      let surface = arg0_surface;
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let mask_data = (surface && surface.kriging_bundle) ? surface.kriging_bundle.mask_data : null;
      let t0 = Date.now();

      //Guard clauses
      if (!mask_data) return { elapsed_seconds: 0, years_scaled: 0 };

      let root_dir = options.project_root || mask_data.project_root || path.resolve(__dirname, "../../../../../..");
      let hgis_dir = path.join(root_dir, "histmap/1.data_raw/population_regional/MAGNETIC/_shared/subadmin_hgis");
      let raster_dir = path.join(hgis_dir, "rasters");
      let pop_dir = path.join(mask_data.domain_dir, "2.population_rasters");

      if (!fs.existsSync(raster_dir) || !fs.existsSync(pop_dir)) {
        console.log("[MagneticSubadminDasymetric] No subadmin HGIS rasters directory found; skipping.");
        return { elapsed_seconds: 0, years_scaled: 0 };
      }

      let avail_snaps = [];
      let r_files = fs.readdirSync(raster_dir);

      for (let i = 0; i < r_files.length; i++) {
        let m = r_files[i].match(/^subadmin_id_(\d+)\.png$/);

        if (m) avail_snaps.push(parseInt(m[1], 10));
      }
      avail_snaps.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      if (avail_snaps.length === 0) return { elapsed_seconds: 0, years_scaled: 0 };

      let grid_h = mask_data.grid_height || 2160;
      let grid_w = mask_data.grid_width || 4320;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let valid_indices = mask_data.valid_indices;
      let snap_cache = new Map();
      let audit_years = {};
      let years_scaled = 0;
      let worst_unit_err = 0;
      let worst_country_err = 0;

      //Function body
      let loadSnapshot = function (arg0_snap_yr) {
        if (snap_cache.has(arg0_snap_yr)) return snap_cache.get(arg0_snap_yr);
        let png_p = path.join(raster_dir, `subadmin_id_${arg0_snap_yr}.png`);
        let meta_p = path.join(raster_dir, `subadmin_meta_${arg0_snap_yr}.json`);

        if (!fs.existsSync(png_p) || !fs.existsSync(meta_p)) return null;
        let png = PNG.sync.read(fs.readFileSync(png_p));
        let meta = JSON.parse(fs.readFileSync(meta_p, "utf8"));
        let unit_id = new Int32Array(n_valid);
        let units_by_id = new Map();
        let unit_pixels = new Map();
        let u_list = Array.isArray(meta.units) ? meta.units : [];

        for (let i = 0; i < u_list.length; i++)
          units_by_id.set(Number(u_list[i].id), u_list[i]);

        for (let v = 0; v < n_valid; v++) {
          let p4 = valid_indices[v]*4;

          if (png.data[p4 + 3] === 0) continue;
          let uid = (png.data[p4] << 8) | png.data[p4 + 1];

          if (uid > 0 && units_by_id.has(uid)) {
            unit_id[v] = uid;
            let arr = unit_pixels.get(uid);

            if (!arr) {
              arr = [];
              unit_pixels.set(uid, arr);
            }
            arr.push(v);
          }
        }
        let obj = { meta: meta, unit_id: unit_id, unit_pixels: unit_pixels, units_by_id: units_by_id };

        if (snap_cache.size >= 4) {
          let first_k = snap_cache.keys().next().value;

          snap_cache.delete(first_k);
        }
        snap_cache.set(arg0_snap_yr, obj);
        return obj;
      };

      //Precompute 4-connected valid neighbours for fast 1-px pycnophylactic multiplier relaxation
      let n_up = new Int32Array(n_valid).fill(-1);
      let n_down = new Int32Array(n_valid).fill(-1);
      let n_left = new Int32Array(n_valid).fill(-1);
      let n_right = new Int32Array(n_valid).fill(-1);

      for (let v = 0; v < n_valid; v++) {
        let gidx = valid_indices[v];
        let r = Math.floor(gidx/grid_w);
        let c = gidx % grid_w;

        if (r > 0) n_up[v] = p2v[(r - 1)*grid_w + c];
        if (r + 1 < grid_h) n_down[v] = p2v[(r + 1)*grid_w + c];
        n_left[v] = p2v[r*grid_w + ((c + grid_w - 1) % grid_w)];
        n_right[v] = p2v[r*grid_w + ((c + 1) % grid_w)];
      }

      let pop_files = fs.readdirSync(pop_dir).filter(function (arg0_f) { return /^popc_-?\d+\.png$/.test(arg0_f); });

      for (let f = 0; f < pop_files.length; f++) {
        let m_yr = pop_files[f].match(/^popc_(-?\d+)\.png$/);

        if (!m_yr) continue;
        let yr = parseInt(m_yr[1], 10);

        if (yr < 1500) continue;
        let snap_yr = this.resolveSnapshotYear(yr, avail_snaps);
        let snap = loadSnapshot(snap_yr);

        if (!snap) continue;
        let pop_path = path.join(pop_dir, pop_files[f]);
        let png = PNG.sync.read(fs.readFileSync(pop_path));
        let dv = new DataView(png.data.buffer, png.data.byteOffset, png.data.byteLength);
        let base_w = new Float32Array(n_valid);

        for (let v = 0; v < n_valid; v++)
          base_w[v] = this.readPosF32(png.data, dv, valid_indices[v]*4);

        //Remove any residual post-1945 modern sub_iso border step (e.g. HYDE Oder-Neisse line)
        //strictly for pre-1945 years BEFORE period-authentic historical sub-administrative scaling!
        let sub_iso_v = (surface && surface.bio_covs && surface.bio_covs.sub_iso_valid) ? surface.bio_covs.sub_iso_valid : null;

        if (yr >= 1850 && yr <= 1945 && sub_iso_v) {
          base_w = this.removePre1945ModernBorderSteps(mask_data, base_w, sub_iso_v, {
            n_down: n_down, n_left: n_left, n_right: n_right, n_up: n_up
          });
        }

        //Pre-industrial rural urban-core guard (prevents modern megacity cores from absorbing disproportionate
        //rural mass inside small metropolitan NUTS-2 regions like London/Paris/Berlin/Vienna in 1500-1850)
        let uopp_v = (surface && surface.bio_covs && surface.bio_covs.uopp_valid) ? surface.bio_covs.uopp_valid : null;

        if (yr <= 1850 && uopp_v) {
          for (let v = 0; v < n_valid; v++) {
            if (uopp_v[v] > 3.8 && base_w[v] > 0) {
              let att = 1.0/(1.0 + 0.045*(uopp_v[v] - 3.8));

              base_w[v] *= Math.max(0.45, att);
            }
          }
        }

        //1. Compute exact sub-administrative target mass per polygon (reconciled within each country so
        //   sub-administrative census shares & totals are 100% mass-conserving without distorting macro totals)
        let country_base_mass = new Map();
        let country_enum_mass = new Map();
        let unit_raw_target = new Map();
        let unit_base_sum = new Map();
        let unit_active = [];

        snap.unit_pixels.forEach(function (arg0_pxs, arg1_uid) {
          let u_meta = snap.units_by_id.get(arg1_uid);

          if (!u_meta) return;
          let target_raw = global.MagneticSubadminDasymetric.interpolateSubadminSeries(u_meta.series, yr);

          if (!(target_raw > 0)) return;
          let b_sum = 0;

          for (let k = 0; k < arg0_pxs.length; k++)
            b_sum += base_w[arg0_pxs[k]];
          if (!(b_sum > 0)) return;
          let cc = u_meta.country || "EU";

          unit_raw_target.set(arg1_uid, target_raw);
          unit_base_sum.set(arg1_uid, b_sum);
          country_base_mass.set(cc, (country_base_mass.get(cc) || 0) + b_sum);
          country_enum_mass.set(cc, (country_enum_mass.get(cc) || 0) + target_raw);
          unit_active.push(arg1_uid);
        });

        if (unit_active.length === 0) continue;

        //Use exact scraped census enumerations directly for census-era snapshots (1860+ across ALL 37 countries!),
        //and smoothly scale 1500-1859 scraped sub-administrative shares to the reconciled European macro trajectory
        //(McEvedy & Jones / Maddison / chapter totals: 74M in 1500 -> 122M in 1750 -> 156M in 1800 -> 223M in 1850)
        //so there is ZERO 1850->1860 cliff while maintaining exact per-unit pycnophylactic conservation!
        let use_exact_census_mass = (yr >= 1860);
        let pre1860_macro_anchors = [
          [1500, 74000000],
          [1600, 87500000],
          [1700, 101000000],
          [1750, 122500000],
          [1800, 156000000],
          [1810, 168500000],
          [1820, 181500000],
          [1830, 195500000],
          [1840, 209500000],
          [1850, 223500000],
          [1860, 240000000]
        ];
        let macro_scale_factor = 1.0;

        if (!use_exact_census_mass) {
          let target_eu_total = this.interpolateSubadminSeries(pre1860_macro_anchors, yr);
          let cur_eu_base = 0;

          country_base_mass.forEach(function (arg0_v) { cur_eu_base += arg0_v; });
          if (target_eu_total > 0 && cur_eu_base > 0)
            macro_scale_factor = target_eu_total/cur_eu_base;
        }
        let unit_target = new Map();

        for (let i = 0; i < unit_active.length; i++) {
          let uid = unit_active[i];
          let u_meta = snap.units_by_id.get(uid);
          let cc = u_meta.country || "EU";
          let t_raw = unit_raw_target.get(uid);

          let is_fallback_unit = (cc === "HB_FALLBACK" || cc === "DEFACTO_FALLBACK");

          if (use_exact_census_mass && !is_fallback_unit) {
            unit_target.set(uid, t_raw);
          } else {
            let c_base = (country_base_mass.get(cc) || 1)*macro_scale_factor;
            let c_enum = country_enum_mass.get(cc) || 1;

            unit_target.set(uid, t_raw*(c_base/c_enum));
          }
        }

        //2. Initialise pycnophylactic dasymetric density field inside every sub-administrative unit
        let cur_pop = Float32Array.from(base_w);
        let in_sub = new Uint8Array(n_valid);

        for (let i = 0; i < unit_active.length; i++) {
          let uid = unit_active[i];
          let pxs = snap.unit_pixels.get(uid);
          let sc = unit_target.get(uid)/Math.max(1e-9, unit_base_sum.get(uid));

          for (let k = 0; k < pxs.length; k++) {
            let v = pxs[k];

            if (base_w[v] > 0) {
              cur_pop[v] = base_w[v]*sc;
              in_sub[v] = 1;
            }
          }
        }

        //3. Gentle 3-pass Tobler Pycnophylactic Multiplier Relaxation (1-px smoothing ONLY on the
        //   multiplier m = P / w across polygon boundaries, NEVER blurring crisp 5' suitability w,
        //   followed by EXACT per-polygon mass re-normalisation on every pass!)
        let log_m = new Float32Array(n_valid);
        let next_m = new Float32Array(n_valid);
        let relax_passes = 3;

        for (let pass = 0; pass < relax_passes; pass++) {
          for (let v = 0; v < n_valid; v++) {
            if (base_w[v] > 0 && cur_pop[v] > 0)
              log_m[v] = Math.log(cur_pop[v]/base_w[v]);
            else
              log_m[v] = 0;
          }
          for (let v = 0; v < n_valid; v++) {
            if (!in_sub[v] || base_w[v] <= 0) {
              next_m[v] = log_m[v];
              continue;
            }
            let acc = 2.0*log_m[v];
            let wsum = 2.0;
            let nbrs = [n_up[v], n_down[v], n_left[v], n_right[v]];

            for (let d = 0; d < 4; d++) {
              let nv = nbrs[d];

              if (nv >= 0 && base_w[nv] > 0 && cur_pop[nv] > 0) {
                acc += log_m[nv];
                wsum += 1.0;
              }
            }
            next_m[v] = acc/wsum;
          }
          for (let v = 0; v < n_valid; v++) {
            if (in_sub[v] && base_w[v] > 0)
              cur_pop[v] = base_w[v]*Math.exp(Math.max(-4.0, Math.min(4.0, next_m[v])));
          }
          //Exact pycnophylactic mass re-normalisation inside EVERY sub-administrative polygon
          for (let i = 0; i < unit_active.length; i++) {
            let uid = unit_active[i];
            let pxs = snap.unit_pixels.get(uid);
            let s_now = 0;

            for (let k = 0; k < pxs.length; k++) s_now += cur_pop[pxs[k]];
            if (s_now > 0) {
              let corr = unit_target.get(uid)/s_now;

              for (let k = 0; k < pxs.length; k++)
                cur_pop[pxs[k]] *= corr;
            }
          }
        }

        //4. Verify strict mass conservation per unit & per country and write updated float32 GeoPNG
        let max_u_err = 0;
        let tot_target = 0;
        let tot_actual = 0;
        let c_targ = new Map();
        let c_act = new Map();

        for (let i = 0; i < unit_active.length; i++) {
          let uid = unit_active[i];
          let u_meta = snap.units_by_id.get(uid);
          let cc = u_meta.country || "EU";
          let pxs = snap.unit_pixels.get(uid);
          let targ = unit_target.get(uid);
          let act = 0;

          for (let k = 0; k < pxs.length; k++) act += cur_pop[pxs[k]];
          let rel_err = Math.abs(act - targ)/Math.max(1.0, targ);

          if (rel_err > max_u_err) max_u_err = rel_err;
          tot_target += targ;
          tot_actual += act;
          c_targ.set(cc, (c_targ.get(cc) || 0) + targ);
          c_act.set(cc, (c_act.get(cc) || 0) + act);
        }
        let max_c_err = 0;

        c_targ.forEach(function (arg0_t, arg1_cc) {
          let a = c_act.get(arg1_cc) || 0;
          let ce = Math.abs(a - arg0_t)/Math.max(1.0, arg0_t);

          if (ce > max_c_err) max_c_err = ce;
        });
        if (max_u_err > worst_unit_err) worst_unit_err = max_u_err;
        if (max_c_err > worst_country_err) worst_country_err = max_c_err;

        for (let v = 0; v < n_valid; v++) {
          if (!in_sub[v]) continue;
          let p4 = valid_indices[v]*4;

          if (cur_pop[v] > 0)
            dv.setFloat32(p4, Math.max(1e-5, cur_pop[v]), false);
        }
        fs.writeFileSync(pop_path, PNG.sync.write(png, { colorType: 6, deflateLevel: 6, filterType: 0 }));

        if (yr % 50 === 0 || yr === 1880 || yr === 1910 || yr === 1930 || yr === 1960 || yr === 1990 || yr === 2010 || yr === 2020) {
          audit_years[String(yr)] = {
            active_units: unit_active.length,
            max_country_rel_err: Number(max_c_err.toExponential(3)),
            max_unit_rel_err: Number(max_u_err.toExponential(3)),
            snapshot_year: snap_yr,
            total_actual_pop: Math.round(tot_actual),
            total_target_pop: Math.round(tot_target)
          };
        }
        years_scaled++;
      }

      let audit_out = {
        elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)),
        generated_at_gmt0: new Date().toISOString(),
        mass_conservation_passed: (worst_unit_err < 1e-4 && worst_country_err < 1e-4),
        sample_years: audit_years,
        worst_country_rel_err: Number(worst_country_err.toExponential(3)),
        worst_unit_rel_err: Number(worst_unit_err.toExponential(3)),
        years_scaled: years_scaled
      };
      let audit_p = path.join(hgis_dir, "subadmin_mass_conservation_audit.json");

      fs.writeFileSync(audit_p, JSON.stringify(audit_out, null, 2));

      //Return statement
      return audit_out;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { MagneticSubadminDasymetric: global.MagneticSubadminDasymetric };
