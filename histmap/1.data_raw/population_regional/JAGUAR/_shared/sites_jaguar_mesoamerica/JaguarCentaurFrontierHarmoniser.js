//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Non-blurring 2D Screened-Laplace (Helmholtz) Cross-Frontier Harmoniser for Operation Viscount Project JAGUAR.
   *
   * Aligns JAGUAR's northern US-Mexico frontier belt (Baja California, Sonora, Chihuahua, Coahuila,
   * Nuevo León and Tamaulipas) smoothly with canonical CENTAUR calibrated frontier densities
   * (`CENTAUR/_shared/sites_northern_america/2.population_rasters/popc_<yr>.png`) across pre-contemporary
   * epochs (`-10000` to `1940 AD`), whilst leaving Mesoamerican, Central American and Caribbean interiors
   * strictly untouched (`u = 0`) and preserving 100% of 5-arcminute fluvial and topographic texture.
   *
   * @class JaguarCentaurFrontierHarmoniser
   */
  global.JaguarCentaurFrontierHarmoniser = class {
    static DEFAULT_MIN_SOLVE_LAT = 22.0;
    static DEFAULT_SCREENING_LENGTH_PX = 24.0;

    /**
     * Harmonises JAGUAR `2.population_rasters/popc_<yr>.png` along the northern US-Mexico seam with CENTAUR
     * using a non-blurring 2D screened-Laplace multiplicative field.
     * @alias JaguarCentaurFrontierHarmoniser.harmoniseAllRasters
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
      let cent_mask_path = path.join(root_dir, "histmap/1.data_raw/population_regional/CENTAUR/_shared/sites_northern_america/config/centaur_na_domain_mask.png");
      let cent_pop_dir = path.join(root_dir, "histmap/1.data_raw/population_regional/CENTAUR/_shared/sites_northern_america/2.population_rasters");
      let jag_pop_dir = path.join(mask_data.domain_dir, "2.population_rasters");

      if (!fs.existsSync(cent_mask_path) || !fs.existsSync(cent_pop_dir) || !fs.existsSync(jag_pop_dir))
        return { elapsed_seconds: 0, harmonised_years: 0 };

      let grid_h = mask_data.grid_height || 2160;
      let grid_w = mask_data.grid_width || 4320;
      let jag_mask = mask_data.mask_grid;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let valid_indices = mask_data.valid_indices;

      //Function body
      let cent_png = PNG.sync.read(fs.readFileSync(cent_mask_path));
      let cent_mask = new Uint8Array(grid_w*grid_h);

      for (let i = 0; i < grid_w*grid_h; i++) {
        let p4 = i*4;

        if (cent_png.data[p4 + 3] > 0 && (cent_png.data[p4] | cent_png.data[p4 + 1] | cent_png.data[p4 + 2]) !== 0)
          cent_mask[i] = 1;
      }

      let border_list = [];
      let cent_nbr_gidx = new Array(n_valid);
      let inv_cos2 = new Float32Array(n_valid);
      let is_border = new Uint8Array(n_valid);
      let is_solve = new Uint8Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let c = gidx % grid_w;
        let r = Math.floor(gidx/grid_w);
        let lat = 90.0 - (r + 0.5)*180.0/grid_h;
        let lon = -180.0 + (c + 0.5)*360.0/grid_w;

        if (lat < this.DEFAULT_MIN_SOLVE_LAT || lon > -94.0) continue;
        let cos_lat = Math.max(0.35, Math.cos(lat*Math.PI/180.0));

        inv_cos2[i] = 1.0/(cos_lat*cos_lat);
        is_solve[i] = 1;

        let touches = false;

        for (let dr = -1; dr <= 1 && !touches; dr++) {
          let nr = r + dr;

          if (nr < 0 || nr >= grid_h) continue;
          for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            let nc = (c + dc + grid_w) % grid_w;
            let nidx = nr*grid_w + nc;

            if (jag_mask[nidx] === 0 && cent_mask[nidx] === 1) {
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

            if (jag_mask[nidx] === 0 && cent_mask[nidx] === 1) {
              let d2 = dr*dr + (dc*cos_lat)*(dc*cos_lat);

              nbrs.push([nidx, Math.exp(-d2/2.5)]);
            }
          }
        }
        if (nbrs.length > 0) {
          is_border[i] = 1;
          cent_nbr_gidx[i] = nbrs;
          border_list.push(i);
        }
      }

      if (border_list.length === 0)
        return { border_pixels: 0, elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)), harmonised_years: 0 };

      let n_down = new Int32Array(n_valid).fill(-1);
      let n_left = new Int32Array(n_valid).fill(-1);
      let n_right = new Int32Array(n_valid).fill(-1);
      let n_up = new Int32Array(n_valid).fill(-1);
      let parity = new Uint8Array(n_valid);
      let solve_list = [];

      for (let i = 0; i < n_valid; i++) {
        if (!is_solve[i]) continue;
        let gidx = valid_indices[i];
        let c = gidx % grid_w;
        let r = Math.floor(gidx/grid_w);

        parity[i] = (r + c) & 1;
        if (r > 0) n_up[i] = p2v[(r - 1)*grid_w + c];
        if (r + 1 < grid_h) n_down[i] = p2v[(r + 1)*grid_w + c];
        n_left[i] = p2v[r*grid_w + ((c + grid_w - 1) % grid_w)];
        n_right[i] = p2v[r*grid_w + ((c + 1) % grid_w)];
        if (!is_border[i]) solve_list.push(i);
      }

      let files = fs.readdirSync(jag_pop_dir).filter(function (arg0_f) { return /^popc_-?\d+\.png$/.test(arg0_f); });
      let harmonised = 0;
      let kappa2 = 1.0/(this.DEFAULT_SCREENING_LENGTH_PX*this.DEFAULT_SCREENING_LENGTH_PX);

      for (let f = 0; f < files.length; f++) {
        let m_yr = files[f].match(/^popc_(-?\d+)\.png$/);

        if (!m_yr) continue;
        let yr = parseInt(m_yr[1], 10);

        if (yr >= 1950) continue;
        let cent_file = path.join(cent_pop_dir, files[f]);

        if (!fs.existsSync(cent_file)) continue;
        let taper = (yr <= 1895) ? 1.0 : Math.max(0.0, (1950 - yr)/55.0);

        if (taper <= 0) continue;

        let jag_path = path.join(jag_pop_dir, files[f]);
        let c_png = PNG.sync.read(fs.readFileSync(cent_file));
        let j_png = PNG.sync.read(fs.readFileSync(jag_path));
        let c_dv = new DataView(c_png.data.buffer, c_png.data.byteOffset, c_png.data.byteLength);
        let j_dv = new DataView(j_png.data.buffer, j_png.data.byteOffset, j_png.data.byteLength);
        let u_field = new Float32Array(n_valid);

        for (let b = 0; b < border_list.length; b++) {
          let vi = border_list[b];
          let j_val = this.readPosF32(j_png.data, j_dv, valid_indices[vi]*4);

          if (j_val <= 0) continue;
          let acc = 0;
          let nbrs = cent_nbr_gidx[vi];
          let wsum = 0;

          for (let k = 0; k < nbrs.length; k++) {
            let cv = this.readPosF32(c_png.data, c_dv, nbrs[k][0]*4);

            if (cv > 0) {
              acc += cv*nbrs[k][1];
              wsum += nbrs[k][1];
            }
          }
          if (wsum > 0) {
            let c_ref = acc/wsum;
            let raw_u = Math.log(Math.max(1e-3, c_ref)/Math.max(1e-3, j_val));

            u_field[vi] = Math.max(-2.2, Math.min(2.2, raw_u*0.85*taper));
          }
        }

        //Red-Black SOR solving (grad^2 - kappa^2) u = 0 on northern frontier belt
        let omega = 1.75;

        for (let iter = 0; iter < 110; iter++) {
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
          let val = this.readPosF32(j_png.data, j_dv, p4);

          if (val <= 0) continue;
          j_dv.setFloat32(p4, Math.max(1e-5, val*Math.exp(u_field[i])), false);
        }

        fs.writeFileSync(jag_path, PNG.sync.write(j_png, { colorType: 6, deflateLevel: 6, filterType: 0 }));
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
     * @alias JaguarCentaurFrontierHarmoniser.readPosF32
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
  module.exports = { JaguarCentaurFrontierHarmoniser: global.JaguarCentaurFrontierHarmoniser };
