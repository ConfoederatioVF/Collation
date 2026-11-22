//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Non-blurring 2D Screened-Laplace (Helmholtz) Cross-Frontier Harmoniser for Operation Viscount Project MAGNETIC.
   *
   * Aligns MAGNETIC's eastern frontier belt (Finland, Estonia, Latvia, Lithuania, Poland, Slovakia,
   * Hungary, Romania and Moldova) smoothly with canonical POLARIS calibrated frontier densities across
   * pre-contemporary epochs (`-10000` to `1919 AD`), whilst leaving Western, Southern, Nordic and
   * Central European interiors strictly untouched (`u = 0`) and preserving 100% of fine fluvial and
   * topographic texture.
   *
   * @class MagneticPolarisFrontierHarmoniser
   */
  global.MagneticPolarisFrontierHarmoniser = class {
    static DEFAULT_SCREENING_LENGTH_PX = 24.0;
    static DEFAULT_WEST_LON_CUT = 18.0;

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
     * Harmonises MAGNETIC `2.population_rasters/popc_<yr>.png` along the eastern seam with POLARIS
     * (`rasters_2.scaled_to_regions/popc_<yr>.png`) using a non-blurring 2D screened-Laplace multiplicative field.
     * @alias MagneticPolarisFrontierHarmoniser.harmoniseAllRasters
     *
     * @param {Object} arg0_surface
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    static harmoniseAllRasters (arg0_surface, arg1_options) {
      let t0 = Date.now();
      let surface = arg0_surface;
      let options = (arg1_options) ? arg1_options : {};
      let mask_data = surface && surface.kriging_bundle ? surface.kriging_bundle.mask_data : null;
      if (!mask_data) return { elapsed_seconds: 0, harmonised_years: 0 };

      let root_dir = options.project_root || mask_data.project_root || path.resolve(__dirname, "../../../../../..");
      let pol_mask_path = path.join(root_dir, "histmap/1.data_raw/population_regional/POLARIS/1.entire_country/8.post_soviet_space/post_soviet_space_areal_mask.png");
      let r2_dir = path.join(root_dir, "histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions");
      let mag_pop_dir = path.join(mask_data.domain_dir, "2.population_rasters");
      if (!fs.existsSync(pol_mask_path) || !fs.existsSync(r2_dir) || !fs.existsSync(mag_pop_dir))
        return { elapsed_seconds: 0, harmonised_years: 0 };

      let grid_h = mask_data.grid_height || 2160;
      let grid_w = mask_data.grid_width || 4320;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let valid_indices = mask_data.valid_indices;
      let mag_mask = mask_data.mask_grid;

      let pol_png = PNG.sync.read(fs.readFileSync(pol_mask_path));
      let pol_mask = new Uint8Array(grid_w*grid_h);
      for (let i = 0; i < grid_w*grid_h; i++) {
        let p4 = i*4;
        if (pol_png.data[p4 + 3] > 0 && (pol_png.data[p4] | pol_png.data[p4 + 1] | pol_png.data[p4 + 2]) !== 0)
          pol_mask[i] = 1;
      }

      //Identify active solve belt (eastern POLARIS seam lon >= 18.0 E AND Greenland CENTAUR coastal seam lon <= -11.0 W, lat >= 59.0 N)
      let is_border = new Uint8Array(n_valid);
      let is_grl_border = new Uint8Array(n_valid);
      let is_solve = new Uint8Array(n_valid);
      let border_list = [];
      let pol_nbr_gidx = new Array(n_valid);
      let inv_cos2 = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let r = Math.floor(gidx/grid_w);
        let c = gidx % grid_w;
        let lat = 90.0 - (r + 0.5)*180.0/grid_h;
        let lon = -180.0 + (c + 0.5)*360.0/grid_w;
        let cos_lat = Math.max(0.32, Math.cos(lat*Math.PI/180.0));
        inv_cos2[i] = 1.0/(cos_lat*cos_lat);
        let in_east = (lon >= this.DEFAULT_WEST_LON_CUT);
        let in_grl = (lon <= -11.0 && lat >= 59.0);
        if (!in_east && !in_grl) continue;
        is_solve[i] = 1;

        let nbrs = [];
        let touches = false;
        for (let dr = -1; dr <= 1 && !touches; dr++) {
          let nr = r + dr;
          if (nr < 0 || nr >= grid_h) continue;
          for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            let nc = (c + dc + grid_w) % grid_w;
            let nidx = nr*grid_w + nc;
            if (in_east && mag_mask[nidx] === 0 && pol_mask[nidx] === 1) { touches = true; break; }
            if (in_grl && mag_mask[nidx] === 0) { touches = true; break; }
          }
        }
        if (!touches) continue;
        for (let dr = -2; dr <= 2; dr++) {
          let nr = r + dr;
          if (nr < 0 || nr >= grid_h) continue;
          for (let dc = -2; dc <= 2; dc++) {
            let nc = (c + dc + grid_w) % grid_w;
            let nidx = nr*grid_w + nc;
            if (mag_mask[nidx] === 0 && (in_grl || pol_mask[nidx] === 1)) {
              let d2 = dr*dr + (dc*cos_lat)*(dc*cos_lat);
              nbrs.push([nidx, Math.exp(-d2/2.5)]);
            }
          }
        }
        if (nbrs.length > 0) {
          is_border[i] = 1;
          if (in_grl) is_grl_border[i] = 1;
          pol_nbr_gidx[i] = nbrs;
          border_list.push(i);
        }
      }

      //Precompute 4-connected neighbours for fast Red-Black SOR on solve subset
      let solve_list = [];
      let n_up = new Int32Array(n_valid).fill(-1);
      let n_down = new Int32Array(n_valid).fill(-1);
      let n_left = new Int32Array(n_valid).fill(-1);
      let n_right = new Int32Array(n_valid).fill(-1);
      let parity = new Uint8Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        if (!is_solve[i]) continue;
        let gidx = valid_indices[i];
        let r = Math.floor(gidx/grid_w);
        let c = gidx % grid_w;
        parity[i] = (r + c) & 1;
        if (r > 0) n_up[i] = p2v[(r - 1)*grid_w + c];
        if (r + 1 < grid_h) n_down[i] = p2v[(r + 1)*grid_w + c];
        n_left[i] = p2v[r*grid_w + ((c + grid_w - 1) % grid_w)];
        n_right[i] = p2v[r*grid_w + ((c + 1) % grid_w)];
        if (!is_border[i]) solve_list.push(i);
      }

      let kappa2 = 1.0/(this.DEFAULT_SCREENING_LENGTH_PX*this.DEFAULT_SCREENING_LENGTH_PX);
      let files = fs.readdirSync(mag_pop_dir).filter(function (arg0_f) { return /^popc_-?\d+\.png$/.test(arg0_f); });
      let harmonised = 0;

      for (let f = 0; f < files.length; f++) {
        let m_yr = files[f].match(/^popc_(-?\d+)\.png$/);
        if (!m_yr) continue;
        let yr = parseInt(m_yr[1], 10);
        if (yr >= 1940) continue;
        let pol_file = path.join(r2_dir, files[f]);
        if (!fs.existsSync(pol_file)) continue;

        let mag_path = path.join(mag_pop_dir, files[f]);
        let m_png = PNG.sync.read(fs.readFileSync(mag_path));
        let p_png = PNG.sync.read(fs.readFileSync(pol_file));
        let m_dv = new DataView(m_png.data.buffer, m_png.data.byteOffset, m_png.data.byteLength);
        let p_dv = new DataView(p_png.data.buffer, p_png.data.byteOffset, p_png.data.byteLength);

        let u_field = new Float32Array(n_valid);
        let taper = (yr <= 1900) ? 1.0 : Math.max(0.0, (1940 - yr)/40.0);
        if (taper <= 0) continue;

        for (let b = 0; b < border_list.length; b++) {
          let vi = border_list[b];
          let m_val = this.readPosF32(m_png.data, m_dv, valid_indices[vi]*4);
          if (m_val <= 0) continue;
          let nbrs = pol_nbr_gidx[vi];
          let acc = 0;
          let wsum = 0;
          for (let k = 0; k < nbrs.length; k++) {
            let pv = this.readPosF32(p_png.data, p_dv, nbrs[k][0]*4);
            if (pv > 0) {
              acc += pv*nbrs[k][1];
              wsum += nbrs[k][1];
            }
          }
          if (wsum > 0) {
            let p_ref = acc/wsum;
            let raw_u = Math.log(Math.max(1e-3, p_ref)/Math.max(1e-3, m_val));
            let clamp_lim = is_grl_border[vi] ? 4.5 : 2.2;
            let gain = is_grl_border[vi] ? 0.94 : 0.85;
            u_field[vi] = Math.max(-clamp_lim, Math.min(clamp_lim, raw_u*gain*taper));
          }
        }

        //Red-Black SOR solving (grad^2 - kappa^2) u = 0 on eastern belt
        let omega = 1.75;
        for (let iter = 0; iter < 110; iter++) {
          for (let col = 0; col < 2; col++) {
            for (let s = 0; s < solve_list.length; s++) {
              let vi = solve_list[s];
              if (parity[vi] !== col) continue;
              let ic2 = inv_cos2[vi];
              let sum_w = kappa2;
              let sum_u = 0;
              let nu = n_up[vi];
              let nd = n_down[vi];
              let nl = n_left[vi];
              let nr = n_right[vi];
              if (nu >= 0 && is_solve[nu]) { sum_w += 1.0; sum_u += u_field[nu]; }
              if (nd >= 0 && is_solve[nd]) { sum_w += 1.0; sum_u += u_field[nd]; }
              if (nl >= 0 && is_solve[nl]) { sum_w += ic2; sum_u += ic2*u_field[nl]; }
              if (nr >= 0 && is_solve[nr]) { sum_w += ic2; sum_u += ic2*u_field[nr]; }
              let target = sum_u/sum_w;
              u_field[vi] += omega*(target - u_field[vi]);
            }
          }
        }

        //Apply multiplicative log-ratio field without blurring any interior pixels
        for (let i = 0; i < n_valid; i++) {
          if (!is_solve[i] || Math.abs(u_field[i]) < 1e-4) continue;
          let p4 = valid_indices[i]*4;
          let val = this.readPosF32(m_png.data, m_dv, p4);
          if (val <= 0) continue;
          let nv = val*Math.exp(u_field[i]);
          m_dv.setFloat32(p4, Math.max(1e-5, nv), false);
        }

        fs.writeFileSync(mag_path, PNG.sync.write(m_png, { colorType: 6, deflateLevel: 6, filterType: 0 }));
        harmonised++;
      }

      //Return statement
      return {
        border_pixels: border_list.length,
        elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)),
        harmonised_years: harmonised
      };
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { MagneticPolarisFrontierHarmoniser: global.MagneticPolarisFrontierHarmoniser };

