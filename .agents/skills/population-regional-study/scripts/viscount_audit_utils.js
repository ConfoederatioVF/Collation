//Import modules
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");
let { PNG } = require("pngjs");

//Initialise functions
{
  let viscount_audit_utils = {
    _c14_cache: null,
    _ne_countries_cache: null,
    _profiles_cache: null,

    /**
     * Builds a spatial grid index over `ne_10m_admin_0_countries.geojson` polygons for fast point-in-polygon lookups.
     * @alias viscount_audit_utils.buildCountryPolygonIndex
     *
     * @param {string} arg0_svea_root
     * @param {Object} [arg1_profiles]
     *
     * @returns {Object|null}
     */
    buildCountryPolygonIndex (arg0_svea_root, arg1_profiles) {
      //Guard clauses
      if (this._ne_countries_cache) return this._ne_countries_cache;

      //Convert from parameters
      let profiles = (arg1_profiles) ? arg1_profiles : this.loadSkillProfiles(arg0_svea_root);
      let svea_root = arg0_svea_root;

      //Declare local instance variables
      let by_name = new Map();
      let ne_path = path.join(svea_root, "histmap/1.data_raw/population_regional/_shared/_gis_cache/ne_10m_admin_0_countries.geojson");
      let union_bboxes = (profiles && profiles.polygon_union_bboxes) ? profiles.polygon_union_bboxes : {};

      if (!fs.existsSync(ne_path)) return null;

      //Function body
      let gj = JSON.parse(fs.readFileSync(ne_path, "utf8"));
      let feats = Array.isArray(gj.features) ? gj.features : [];
      for (let i = 0; i < feats.length; i++) {
        let feat = feats[i];
        let props = (feat && feat.properties) ? feat.properties : {};
        let geom = feat && feat.geometry;
        if (!geom || !geom.coordinates) continue;

        let polys = [];
        if (geom.type === "Polygon") {
          polys.push(geom.coordinates);
        } else if (geom.type === "MultiPolygon") {
          for (let x = 0; x < geom.coordinates.length; x++)
            polys.push(geom.coordinates[x]);
        }
        if (polys.length === 0) continue;

        let bboxes = [];
        let min_lon = 999;
        let min_lat = 999;
        let max_lon = -999;
        let max_lat = -999;
        for (let x = 0; x < polys.length; x++) {
          let ring = polys[x][0] || [];
          let pmin_x = 999;
          let pmin_y = 999;
          let pmax_x = -999;
          let pmax_y = -999;
          for (let y = 0; y < ring.length; y++) {
            let lon = ring[y][0];
            let lat = ring[y][1];
            if (lon < pmin_x) pmin_x = lon;
            if (lon > pmax_x) pmax_x = lon;
            if (lat < pmin_y) pmin_y = lat;
            if (lat > pmax_y) pmax_y = lat;
          }
          bboxes.push([pmin_x, pmin_y, pmax_x, pmax_y]);
          if (pmin_x < min_lon) min_lon = pmin_x;
          if (pmax_x > max_lon) max_lon = pmax_x;
          if (pmin_y < min_lat) min_lat = pmin_y;
          if (pmax_y > max_lat) max_lat = pmax_y;
        }

        let rec = {
          bboxes: bboxes,
          bbox: [min_lon, min_lat, max_lon, max_lat],
          polys: polys
        };
        let names = [props.ADMIN, props.NAME, props.NAME_LONG, props.SOVEREIGNT, props.GEOUNIT, props.BRK_NAME];
        for (let x = 0; x < names.length; x++) {
          let n = String(names[x] || "").trim().toLowerCase();
          if (!n) continue;
          if (!by_name.has(n)) by_name.set(n, []);
          by_name.get(n).push(rec);
        }
      }

      this._ne_countries_cache = { by_name: by_name, union_bboxes: union_bboxes };

      //Return statement
      return this._ne_countries_cache;
    },

    /**
     * Computes exact 2D Euclidean Distance Transform (Felzenszwalb-Huttenlocher 2-pass) on a boolean target grid.
     * Returns Float32Array of Euclidean pixel distances to the nearest `1` cell.
     * @alias viscount_audit_utils.computeExactEdt2d
     *
     * @param {Uint8Array} arg0_target_mask
     * @param {number} arg1_width
     * @param {number} arg2_height
     *
     * @returns {Float32Array}
     */
    computeExactEdt2d (arg0_target_mask, arg1_width, arg2_height) {
      //Convert from parameters
      let h = arg2_height;
      let mask = arg0_target_mask;
      let w = arg1_width;

      //Declare local instance variables
      let inf = 1e15;
      let d_sq = new Float64Array(w*h);
      let f = new Float64Array(Math.max(w, h));
      let v = new Int32Array(Math.max(w, h));
      let z = new Float64Array(Math.max(w, h) + 1);

      //Function body
      let edt1d = function (arg0_f, arg1_n, arg2_out, arg3_stride, arg4_offset) {
        let k = 0;
        v[0] = 0;
        z[0] = -inf;
        z[1] = inf;
        for (let q = 1; q < arg1_n; q++) {
          let s = ((arg0_f[q] + q*q) - (arg0_f[v[k]] + v[k]*v[k]))/(2*q - 2*v[k]);
          for (; k > 0 && s <= z[k]; ) {
            k--;
            s = ((arg0_f[q] + q*q) - (arg0_f[v[k]] + v[k]*v[k]))/(2*q - 2*v[k]);
          }
          k++;
          v[k] = q;
          z[k] = s;
          z[k + 1] = inf;
        }
        k = 0;
        for (let q = 0; q < arg1_n; q++) {
          for (; z[k + 1] < q; ) k++;
          let dx = q - v[k];
          arg2_out[arg4_offset + q*arg3_stride] = dx*dx + arg0_f[v[k]];
        }
      };

      for (let i = 0; i < w*h; i++)
        d_sq[i] = mask[i] ? 0.0 : inf;

      for (let x = 0; x < w; x++) {
        for (let y = 0; y < h; y++) f[y] = d_sq[y*w + x];
        edt1d(f, h, d_sq, w, x);
      }
      for (let y = 0; y < h; y++) {
        let row_off = y*w;
        for (let x = 0; x < w; x++) f[x] = d_sq[row_off + x];
        edt1d(f, w, d_sq, 1, row_off);
      }

      let out = new Float32Array(w*h);
      for (let i = 0; i < w*h; i++)
        out[i] = Math.sqrt(d_sq[i]);

      //Return statement
      return out;
    },

    /**
     * Counts unique `c14_cleaned_dedup.csv` sites falling inside a `4320x2160` boolean mask (cached globally per process).
     * @alias viscount_audit_utils.countC14SitesInMask
     *
     * @param {string} arg0_svea_root
     * @param {Uint8Array} arg1_mask
     * @param {number} [arg2_width=4320]
     * @param {number} [arg3_height=2160]
     *
     * @returns {number|null}
     */
    countC14SitesInMask (arg0_svea_root, arg1_mask, arg2_width, arg3_height) {
      //Convert from parameters
      let h = Number(arg3_height) || 2160;
      let mask = arg1_mask;
      let svea_root = arg0_svea_root;
      let w = Number(arg2_width) || 4320;

      //Guard clauses
      if (!svea_root || !mask) return null;

      //Function body
      if (!this._c14_cache) {
        let c14_path = path.join(svea_root, "histmap/1.data_raw/population_c14bazAAR/c14_cleaned_dedup.csv");
        if (!fs.existsSync(c14_path)) return null;
        let lines = fs.readFileSync(c14_path, "utf8").split(/\r?\n/);
        if (lines.length < 2) return 0;

        let hdr = lines[0].split(",").map(function (arg0_s) { return arg0_s.replace(/^"|"$/g, "").trim().toLowerCase(); });
        let lat_i = hdr.indexOf("lat");
        let lon_i = hdr.indexOf("lon");
        let site_i = hdr.indexOf("site");
        if (lat_i === -1 || lon_i === -1) return null;

        let seen = new Set();
        let pts = [];
        for (let i = 1; i < lines.length; i++) {
          let ln = lines[i];
          if (!ln) continue;
          let cols = ln.split(",");
          let lat = parseFloat(cols[lat_i]);
          let lon = parseFloat(cols[lon_i]);
          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          let site = (site_i >= 0 && cols[site_i]) ? cols[site_i].replace(/^"|"$/g, "").trim().toLowerCase() : "";
          let key = `${lat.toFixed(3)}|${lon.toFixed(3)}|${site}`;
          if (seen.has(key)) continue;
          seen.add(key);
          pts.push([lat, lon]);
        }
        this._c14_cache = pts;
      }

      let cnt = 0;
      for (let i = 0; i < this._c14_cache.length; i++) {
        let lat = this._c14_cache[i][0];
        let lon = this._c14_cache[i][1];
        let r = Math.min(h - 1, Math.max(0, Math.floor((90.0 - lat)*h/180.0)));
        let c = Math.min(w - 1, Math.max(0, Math.floor((lon + 180.0)*w/360.0)));
        if (mask[r*w + c]) cnt++;
      }

      //Return statement
      return cnt;
    },

    /**
     * Decodes a big-endian IEEE-754 float32 RGBA GeoPNG into a `Float32Array` and valid `Uint8Array` mask.
     * Never tests `data[p4 + 3] > 0` alone (avoids 1/256 low-mantissa Swiss-cheese bug).
     * @alias viscount_audit_utils.decodeFloat32Png
     *
     * @param {string} arg0_png_path
     *
     * @returns {{ data: Float32Array, height: number, valid: Uint8Array, width: number }}
     */
    decodeFloat32Png (arg0_png_path) {
      //Convert from parameters
      let png_path = arg0_png_path;

      //Declare local instance variables
      let png = PNG.sync.read(fs.readFileSync(png_path));
      let n = png.width*png.height;
      let buf = png.data;
      let dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
      let out = new Float32Array(n);
      let valid = new Uint8Array(n);

      //Function body
      for (let i = 0; i < n; i++) {
        let p4 = i*4;
        if ((buf[p4] | buf[p4 + 1] | buf[p4 + 2] | buf[p4 + 3]) === 0) continue;
        let val = dv.getFloat32(p4, false);
        if (Number.isFinite(val) && val > 0) {
          out[i] = val;
          valid[i] = 1;
        }
      }

      //Return statement
      return { data: out, height: png.height, valid: valid, width: png.width };
    },

    /**
     * Decodes an RGBA PNG synchronously via `pngjs`.
     * @alias viscount_audit_utils.decodeRgbaPng
     *
     * @param {string} arg0_png_path
     *
     * @returns {{ data: Buffer, height: number, width: number }}
     */
    decodeRgbaPng (arg0_png_path) {
      //Convert from parameters
      let png = PNG.sync.read(fs.readFileSync(arg0_png_path));

      //Return statement
      return { data: png.data, height: png.height, width: png.width };
    },

    /**
     * Decodes a big-endian uint32 RGBA GeoPNG (e.g. `land_area.png`) into a `Float64Array`.
     * @alias viscount_audit_utils.decodeUint32Png
     *
     * @param {string} arg0_png_path
     *
     * @returns {{ data: Float64Array, height: number, width: number }}
     */
    decodeUint32Png (arg0_png_path) {
      //Convert from parameters
      let png = PNG.sync.read(fs.readFileSync(arg0_png_path));
      let n = png.width*png.height;
      let dv = new DataView(png.data.buffer, png.data.byteOffset, png.data.byteLength);
      let out = new Float64Array(n);

      //Function body
      for (let i = 0; i < n; i++)
        out[i] = dv.getUint32(i*4, false);

      //Return statement
      return { data: out, height: png.height, width: png.width };
    },

    /**
     * Walks upward from a starting path to locate the SVEA repository root containing `histmap/` and `.agents/`.
     * @alias viscount_audit_utils.findSveaRoot
     *
     * @param {string} [arg0_start_path]
     *
     * @returns {string|null}
     */
    findSveaRoot (arg0_start_path) {
      //Convert from parameters
      let starts = [
        path.resolve(arg0_start_path || "."),
        path.resolve(__dirname),
        process.cwd()
      ];

      //Function body
      for (let i = 0; i < starts.length; i++) {
        let cur = starts[i];
        if (fs.existsSync(cur) && fs.statSync(cur).isFile()) cur = path.dirname(cur);
        for (let step = 0; step < 12; step++) {
          if (fs.existsSync(path.join(cur, "histmap")) && fs.existsSync(path.join(cur, ".agents")))
            return cur;
          let parent = path.dirname(cur);
          if (parent === cur) break;
          cur = parent;
        }
      }

      //Return statement
      return null;
    },

    /**
     * Computes great-circle Haversine distance in km between two `[lat, lon]` coordinates.
     * @alias viscount_audit_utils.haversineKm
     *
     * @param {number} arg0_lat1
     * @param {number} arg1_lon1
     * @param {number} arg2_lat2
     * @param {number} arg3_lon2
     *
     * @returns {number}
     */
    haversineKm (arg0_lat1, arg1_lon1, arg2_lat2, arg3_lon2) {
      //Convert from parameters
      let d_lat = (arg2_lat2 - arg0_lat1)*Math.PI/180;
      let d_lon = (arg3_lon2 - arg1_lon1)*Math.PI/180;
      let r1 = arg0_lat1*Math.PI/180;
      let r2 = arg2_lat2*Math.PI/180;

      //Function body
      let a = Math.sin(d_lat/2)*Math.sin(d_lat/2) +
        Math.cos(r1)*Math.cos(r2)*Math.sin(d_lon/2)*Math.sin(d_lon/2);

      //Return statement
      return 6371.0*2.0*Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0.0, 1.0 - a)));
    },

    /**
     * Tests whether `[lat, lon]` falls inside or within `arg3_buffer_deg` of a sovereign polygon set.
     * @alias viscount_audit_utils.isPointNearCountryPolygons
     *
     * @param {number} arg0_lat
     * @param {number} arg1_lon
     * @param {Array<Object>} arg2_recs
     * @param {number} [arg3_buffer_deg=0.28]
     *
     * @returns {boolean}
     */
    isPointNearCountryPolygons (arg0_lat, arg1_lon, arg2_recs, arg3_buffer_deg) {
      //Convert from parameters
      let buf = Number.isFinite(arg3_buffer_deg) ? arg3_buffer_deg : 0.28;
      let lat = arg0_lat;
      let lon = arg1_lon;
      let recs = Array.isArray(arg2_recs) ? arg2_recs : [];

      //Function body
      let pointInRing = function (arg0_x, arg1_y, arg2_ring) {
        let inside = false;
        for (let i = 0, j = arg2_ring.length - 1; i < arg2_ring.length; j = i++) {
          let xi = arg2_ring[i][0];
          let yi = arg2_ring[i][1];
          let xj = arg2_ring[j][0];
          let yj = arg2_ring[j][1];
          let inter = ((yi > arg1_y) !== (yj > arg1_y)) &&
            (arg0_x < (xj - xi)*(arg1_y - yi)/((yj - yi) || 1e-12) + xi);
          if (inter) inside = !inside;
        }
        return inside;
      };

      let offsets = [[0, 0], [buf, 0], [-buf, 0], [0, buf], [0, -buf], [buf*0.7, buf*0.7], [-buf*0.7, buf*0.7], [buf*0.7, -buf*0.7], [-buf*0.7, -buf*0.7]];
      for (let i = 0; i < recs.length; i++) {
        let rec = recs[i];
        let bb = rec.bbox;
        if (lon < bb[0] - buf || lon > bb[2] + buf || lat < bb[1] - buf || lat > bb[3] + buf) continue;
        for (let p = 0; p < rec.polys.length; p++) {
          let pbb = rec.bboxes[p];
          if (lon < pbb[0] - buf || lon > pbb[2] + buf || lat < pbb[1] - buf || lat > pbb[3] + buf) continue;
          let outer = rec.polys[p][0];
          if (!outer || outer.length < 3) continue;
          for (let o = 0; o < offsets.length; o++) {
            if (pointInRing(lon + offsets[o][0], lat + offsets[o][1], outer))
              return true;
          }
        }
      }

      //Return statement
      return false;
    },

    /**
     * Loads JSON via native `JSON.parse` first, falling back cleanly to `JSON5.parse`.
     * @alias viscount_audit_utils.loadJsonOrJson5
     *
     * @param {string} arg0_file_path
     *
     * @returns {*}
     */
    loadJsonOrJson5 (arg0_file_path) {
      //Convert from parameters
      let raw = fs.readFileSync(arg0_file_path, "utf8");

      //Function body
      try {
        return JSON.parse(raw);
      } catch (e) {
        return JSON5.parse(raw);
      }
    },

    /**
     * Loads and caches `.agents/skills/population-regional-study/config/viscount_skill_profiles.json5`.
     * @alias viscount_audit_utils.loadSkillProfiles
     *
     * @param {string} [arg0_svea_root]
     *
     * @returns {Object}
     */
    loadSkillProfiles (arg0_svea_root) {
      //Guard clauses
      if (this._profiles_cache) return this._profiles_cache;

      //Declare local instance variables
      let cands = [path.resolve(__dirname, "../config/viscount_skill_profiles.json5")];
      if (arg0_svea_root)
        cands.push(path.join(arg0_svea_root, ".agents/skills/population-regional-study/config/viscount_skill_profiles.json5"));

      //Function body
      for (let i = 0; i < cands.length; i++) {
        if (fs.existsSync(cands[i])) {
          this._profiles_cache = this.loadJsonOrJson5(cands[i]);
          return this._profiles_cache;
        }
      }

      //Return statement
      return {};
    },

    /**
     * Resolves a Viscount project key from a target path or `viscount_precedence.json5`.
     * @alias viscount_audit_utils.resolveProjectKey
     *
     * @param {string} arg0_target_path
     * @param {string} [arg1_svea_root]
     *
     * @returns {string|null}
     */
    resolveProjectKey (arg0_target_path, arg1_svea_root) {
      //Convert from parameters
      let norm = path.resolve(arg0_target_path || ".").replace(/\\/g, "/");
      let svea_root = arg1_svea_root || this.findSveaRoot(arg0_target_path);

      //Function body
      let m = norm.match(/\/population_regional\/([A-Za-z0-9_]+)(?:\/|$)/);
      if (m) return m[1].toUpperCase();

      if (svea_root) {
        let prec_p = path.join(svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5");
        if (fs.existsSync(prec_p)) {
          let prec = this.loadJsonOrJson5(prec_p);
          let list = Array.isArray(prec.projects) ? prec.projects : [];
          let base = path.basename(norm).toLowerCase();
          for (let i = 0; i < list.length; i++) {
            let k = String(list[i].key || "").toUpperCase();
            let pref = String(list[i].shard_prefix || "").toLowerCase();
            if ((pref && base.startsWith(pref)) || (k && norm.toUpperCase().includes(`/${k}/`)))
              return k;
          }
        }
      }

      //Return statement
      return null;
    },

    /**
     * Recursively collects files matching a predicate beneath a root directory.
     * @alias viscount_audit_utils.walkFiles
     *
     * @param {string} arg0_dir
     * @param {Function} arg1_filter_fn
     * @param {Set<string>} [arg2_skip_dirs]
     *
     * @returns {Array<string>}
     */
    walkFiles (arg0_dir, arg1_filter_fn, arg2_skip_dirs) {
      //Convert from parameters
      let dir = arg0_dir;
      let filter_fn = arg1_filter_fn;
      let skip_dirs = arg2_skip_dirs || new Set(["node_modules", ".git", "__pycache__", ".Rproj.user"]);

      //Declare local instance variables
      let out = [];

      //Guard clauses
      if (!fs.existsSync(dir)) return out;

      //Function body
      let stack = [dir];
      for (let step = 0; stack.length > 0 && step < 200000; step++) {
        let cur = stack.pop();
        let entries = fs.readdirSync(cur, { withFileTypes: true });
        for (let i = 0; i < entries.length; i++) {
          let ent = entries[i];
          let full = path.join(cur, ent.name);
          if (ent.isDirectory()) {
            if (!skip_dirs.has(ent.name)) stack.push(full);
          } else if (!filter_fn || filter_fn(full, ent.name)) {
            out.push(full);
          }
        }
      }
      out.sort();

      //Return statement
      return out;
    }
  };

  if (typeof module !== "undefined" && module.exports)
    module.exports = { viscount_audit_utils: viscount_audit_utils };
}
