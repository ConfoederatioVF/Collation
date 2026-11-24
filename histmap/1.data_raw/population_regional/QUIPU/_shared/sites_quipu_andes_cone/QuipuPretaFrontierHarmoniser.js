//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Non-blurring 2D Screened-Laplace (Helmholtz) Cross-Frontier Harmoniser for Operation Viscount Project QUIPU.
   *
   * Aligns QUIPU's eastern Amazonian/Chaco/La Plata frontier belt smoothly with canonical PRETA
   * calibrated frontier densities (`PRETA/_shared/sites_preta_amazon_brazil/2.population_rasters/popc_<yr>.png`)
   * across pre-1950 epochs (`-10000` to `1940 AD`), preserving 100% of 5-arcminute Andean, fluvial
   * and topographic texture.
   *
   * @class QuipuPretaFrontierHarmoniser
   */
  global.QuipuPretaFrontierHarmoniser = class {
    static DEFAULT_SCREENING_LENGTH_PX = 22.0;

    /**
     * Harmonises QUIPU `2.population_rasters/popc_<yr>.png` along the eastern seam with PRETA
     * using a non-blurring 2D screened-Laplace multiplicative field.
     * @alias QuipuPretaFrontierHarmoniser.harmoniseAllRasters
     *
     * @param {Object} arg0_surface
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    static harmoniseAllRasters (arg0_surface, arg1_options) {
      //Convert from parameters
      let options = (arg1_options) ? arg1_options : {};
      let surface = arg0_surface;

      //Declare local instance variables
      let mask_data = (surface && surface.kriging_bundle) ? surface.kriging_bundle.mask_data : null;
      let t0 = Date.now();

      //Guard clauses
      if (!mask_data) return { elapsed_seconds: 0, harmonised_years: 0 };

      let root_dir = options.project_root || mask_data.project_root || path.resolve(__dirname, "../../../../../..");
      let preta_mask_path = path.join(root_dir, "histmap/1.data_raw/population_regional/PRETA/_shared/sites_preta_amazon_brazil/config/preta_domain_mask.png");
      let preta_pop_dir = path.join(root_dir, "histmap/1.data_raw/population_regional/PRETA/_shared/sites_preta_amazon_brazil/2.population_rasters");
      let quipu_pop_dir = path.join(mask_data.domain_dir, "2.population_rasters");

      if (!fs.existsSync(preta_mask_path) || !fs.existsSync(preta_pop_dir) || !fs.existsSync(quipu_pop_dir))
        return { elapsed_seconds: 0, harmonised_years: 0 };

      let grid_h = mask_data.grid_height || 2160;
      let grid_w = mask_data.grid_width || 4320;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let quipu_mask = mask_data.mask_grid;
      let valid_indices = mask_data.valid_indices;

      //Function body
      let preta_png = PNG.sync.read(fs.readFileSync(preta_mask_path));
      let preta_mask = new Uint8Array(grid_w*grid_h);

      for (let i = 0; i < grid_w*grid_h; i++) {
        let p4 = i*4;

        if (preta_png.data[p4 + 3] > 0 && (preta_png.data[p4] | preta_png.data[p4 + 1] | preta_png.data[p4 + 2]) !== 0)
          preta_mask[i] = 1;
      }

      let border_list = [];
      let inv_cos2 = new Float32Array(n_valid);
      let is_border = new Uint8Array(n_valid);
      let is_solve = new Uint8Array(n_valid);
      let preta_nbr_gidx = new Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let c = gidx % grid_w;
        let r = Math.floor(gidx/grid_w);
        let lat = 90.0 - (r + 0.5)*180.0/grid_h;
        let cos_lat = Math.max(0.35, Math.cos(lat*Math.PI/180.0));

        inv_cos2[i] = 1.0/(cos_lat*cos_lat);

        let touches = false;

        for (let dr = -1; dr <= 1 && !touches; dr++) {
          let nr = r + dr;

          if (nr < 0 || nr >= grid_h) continue;
          for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            let nc = (c + dc + grid_w) % grid_w;
            let nidx = nr*grid_w + nc;

            if (quipu_mask[nidx] === 0 && preta_mask[nidx] === 1) {
              touches = true;
              break;
            }
          }
        }
        if (!touches) continue;

        let nbrs = [];

        for (let dr = -2; dr <= 2; dr++) {
          let nr = r + dr;

          if (nr < 0 || nr >= grid_h) continue;
          for (let dc = -2; dc <= 2; dc++) {
            let nc = (c + dc + grid_w) % grid_w;
            let nidx = nr*grid_w + nc;

            if (quipu_mask[nidx] === 0 && preta_mask[nidx] === 1) {
              let d2 = dr*dr + (dc*cos_lat)*(dc*cos_lat);

              nbrs.push([nidx, Math.exp(-d2/2.5)]);
            }
          }
        }
        if (nbrs.length > 0) {
          is_border[i] = 1;
          is_solve[i] = 1;
          preta_nbr_gidx[i] = nbrs;
          border_list.push(i);
        }
      }

      if (border_list.length === 0)
        return { border_pixels: 0, elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)), harmonised_years: 0 };

      //BFS out 48 px from eastern PRETA seam to define the local Helmholtz relaxation belt
      let n_down = new Int32Array(n_valid).fill(-1);
      let n_left = new Int32Array(n_valid).fill(-1);
      let n_right = new Int32Array(n_valid).fill(-1);
      let n_up = new Int32Array(n_valid).fill(-1);
      let dist = new Int16Array(n_valid).fill(999);
      let queue = [];

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let c = gidx % grid_w;
        let r = Math.floor(gidx/grid_w);

        if (r > 0) n_up[i] = p2v[(r - 1)*grid_w + c];
        if (r + 1 < grid_h) n_down[i] = p2v[(r + 1)*grid_w + c];
        n_left[i] = p2v[r*grid_w + ((c + grid_w - 1) % grid_w)];
        n_right[i] = p2v[r*grid_w + ((c + 1) % grid_w)];
        if (is_border[i]) {
          dist[i] = 0;
          queue.push(i);
        }
      }
      for (let qh = 0; qh < queue.length; qh++) {
        let curr = queue[qh];
        let cd = dist[curr];

        if (cd >= 48) continue;
        let ns = [n_up[curr], n_down[curr], n_left[curr], n_right[curr]];

        for (let d = 0; d < 4; d++) {
          let nv = ns[d];

          if (nv >= 0 && dist[nv] > cd + 1) {
            dist[nv] = cd + 1;
            is_solve[nv] = 1;
            queue.push(nv);
          }
        }
      }

      let parity = new Uint8Array(n_valid);
      let solve_list = [];

      for (let i = 0; i < n_valid; i++) {
        if (!is_solve[i]) continue;
        let gidx = valid_indices[i];

        parity[i] = (Math.floor(gidx/grid_w) + (gidx % grid_w)) & 1;
        if (!is_border[i]) solve_list.push(i);
      }

      let files = fs.readdirSync(quipu_pop_dir).filter(function (arg0_f) { return /^popc_-?\d+\.png$/.test(arg0_f); });
      let harmonised = 0;
      let kappa2 = 1.0/(this.DEFAULT_SCREENING_LENGTH_PX*this.DEFAULT_SCREENING_LENGTH_PX);

      for (let f = 0; f < files.length; f++) {
        let m_yr = files[f].match(/^popc_(-?\d+)\.png$/);

        if (!m_yr) continue;
        let yr = parseInt(m_yr[1], 10);

        if (yr >= 1950) continue;
        let preta_file = path.join(preta_pop_dir, files[f]);

        if (!fs.existsSync(preta_file)) continue;
        let taper = (yr <= 1870) ? 1.0 : Math.max(0.0, (1950 - yr)/80.0);

        if (taper <= 0) continue;

        let quipu_path = path.join(quipu_pop_dir, files[f]);
        let p_png = PNG.sync.read(fs.readFileSync(preta_file));
        let q_png = PNG.sync.read(fs.readFileSync(quipu_path));
        let p_dv = new DataView(p_png.data.buffer, p_png.data.byteOffset, p_png.data.byteLength);
        let q_dv = new DataView(q_png.data.buffer, q_png.data.byteOffset, q_png.data.byteLength);
        let u_field = new Float32Array(n_valid);

        for (let b = 0; b < border_list.length; b++) {
          let vi = border_list[b];
          let q_val = this.readPosF32(q_png.data, q_dv, valid_indices[vi]*4);

          if (q_val <= 0) continue;
          let acc = 0;
          let nbrs = preta_nbr_gidx[vi];
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
            let raw_u = Math.log(Math.max(1e-3, p_ref)/Math.max(1e-3, q_val));

            u_field[vi] = Math.max(-2.2, Math.min(2.2, raw_u*0.85*taper));
          }
        }

        let omega = 1.75;

        for (let iter = 0; iter < 100; iter++) {
          for (let col = 0; col < 2; col++) {
            for (let s = 0; s < solve_list.length; s++) {
              let vi = solve_list[s];

              if (parity[vi] !== col) continue;
              let ic2 = inv_cos2[vi];
              let nd = n_down[vi];
              let nl = n_left[vi];
              let nr = n_right[vi];
              let nu = n_up[vi];
              let sum_u = 0;
              let sum_w = kappa2;

              if (nu >= 0 && is_solve[nu]) { sum_w += 1.0; sum_u += u_field[nu]; }
              if (nd >= 0 && is_solve[nd]) { sum_w += 1.0; sum_u += u_field[nd]; }
              if (nl >= 0 && is_solve[nl]) { sum_w += ic2; sum_u += ic2*u_field[nl]; }
              if (nr >= 0 && is_solve[nr]) { sum_w += ic2; sum_u += ic2*u_field[nr]; }
              let target = sum_u/sum_w;

              u_field[vi] += omega*(target - u_field[vi]);
            }
          }
        }

        for (let i = 0; i < n_valid; i++) {
          if (!is_solve[i] || Math.abs(u_field[i]) < 1e-4) continue;
          let p4 = valid_indices[i]*4;
          let val = this.readPosF32(q_png.data, q_dv, p4);

          if (val <= 0) continue;
          q_dv.setFloat32(p4, Math.max(1e-5, val*Math.exp(u_field[i])), false);
        }

        fs.writeFileSync(quipu_path, PNG.sync.write(q_png, { colorType: 6, deflateLevel: 6, filterType: 0 }));
        harmonised++;
      }

      //Return statement
      return {
        border_pixels: border_list.length,
        elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)),
        harmonised_years: harmonised
      };
    }


    /**
     * Reads a positive finite Big-Endian float32 value from an RGBA PNG buffer.
     * @alias QuipuPretaFrontierHarmoniser.readPosF32
     *
     * @param {Buffer} arg0_data
     * @param {DataView} arg1_dv
     * @param {number} arg2_p4
     *
     * @returns {number}
     */
    static readPosF32 (arg0_data, arg1_dv, arg2_p4) {
      let b0 = arg0_data[arg2_p4];
      let b1 = arg0_data[arg2_p4 + 1];
      let b2 = arg0_data[arg2_p4 + 2];
      let b3 = arg0_data[arg2_p4 + 3];

      if ((b0 | b1 | b2 | b3) === 0) return 0;
      let val = arg1_dv.getFloat32(arg2_p4, false);

      //Return statement
      return (Number.isFinite(val) && val > 0) ? val : 0;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { QuipuPretaFrontierHarmoniser: global.QuipuPretaFrontierHarmoniser };
