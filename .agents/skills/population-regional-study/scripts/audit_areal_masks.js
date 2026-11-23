//Import modules
let fs = require("fs");
let path = require("path");
let sharp = require("sharp");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let areal_masks_auditor = {
    /**
     * Audits a full project areal-masks manifest plus HGIS provenance, HYDE `subadmin_hgis` coverage,
     * and Pass-2 separate `mask_auditor` sign-off.
     * @alias areal_masks_auditor.auditManifest
     *
     * @param {string} arg0_manifest_path
     * @param {Object} [arg1_options]
     *
     * @returns {Promise<Object>}
     */
    async auditManifest (arg0_manifest_path, arg1_options) {
      //Convert from parameters
      let manifest_path = path.resolve(arg0_manifest_path);
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let errors = [];
      let manifest_dir = path.dirname(manifest_path);
      let per_mask = [];
      let svea_root = viscount_audit_utils.findSveaRoot(manifest_path);
      let profiles = viscount_audit_utils.loadSkillProfiles(svea_root);
      let hgis_policy = (profiles && profiles.hgis_policy) ? profiles.hgis_policy : {};
      let proj_key = viscount_audit_utils.resolveProjectKey(manifest_path, svea_root);
      let proj_def = (proj_key && profiles.macro_region_defaults) ? (profiles.macro_region_defaults[proj_key] || {}) : {};
      let warnings = [];

      //Function body
      let data = viscount_audit_utils.loadJsonOrJson5(manifest_path);
      let has_micro_islands = Boolean(
        options.has_micro_islands ||
        proj_def.has_micro_islands ||
        (data.geography_profile && data.geography_profile.has_micro_islands)
      );

      //Collect mask definitions from standard Viscount manifest keys
      let raw_items = [];
      let list_keys = ["specialist_masks", "masks", "chapter_masks", "areal_masks"];
      for (let i = 0; i < list_keys.length; i++) {
        let v = data[list_keys[i]];
        if (Array.isArray(v)) {
          for (let x = 0; x < v.length; x++) raw_items.push(v[x]);
        } else if (v && typeof v === "object") {
          let ks = Object.keys(v);
          for (let x = 0; x < ks.length; x++)
            if (v[ks[x]] && typeof v[ks[x]] === "object") raw_items.push(Object.assign({ id: ks[x] }, v[ks[x]]));
        }
      }

      if (raw_items.length === 0) {
        let found = viscount_audit_utils.walkFiles(manifest_dir, function (arg0_p, arg1_n) {
          return /_areal_mask\.png$/i.test(arg1_n);
        });
        for (let i = 0; i < found.length; i++)
          raw_items.push({ path: found[i] });
      }

      //Build modern Admin-0 edge map once for pre-1945 modern-border leakage checks
      let ne_edge_grid = this.buildModernBorderEdgeGrid(svea_root);

      let seen_paths = new Set();
      for (let i = 0; i < raw_items.length; i++) {
        let item = raw_items[i];
        if (!item || typeof item !== "object") continue;
        let rel_p = item.mask_png || item.mask_path || item.path || item.file || "";
        if (!rel_p) continue;
        let abs_p = path.isAbsolute(rel_p) ? rel_p :
          (fs.existsSync(path.join(manifest_dir, rel_p)) ? path.join(manifest_dir, rel_p) :
            (svea_root ? path.join(svea_root, rel_p) : path.resolve(manifest_dir, rel_p)));
        if (seen_paths.has(abs_p)) continue;
        seen_paths.add(abs_p);

        let dom = Array.isArray(item.domain) ? item.domain :
          (Array.isArray(item.years) ? item.years : null);
        let end_yr = (dom && dom.length >= 2) ? Number(dom[1]) : 9999;
        let is_admin1 = Boolean(item.is_admin1 || (Number.isFinite(end_yr) && end_yr >= 1945));

        let res = await this.auditSingleMask(abs_p, {
          domain: dom,
          has_micro_islands: has_micro_islands,
          hgis_policy: hgis_policy,
          is_admin1: is_admin1,
          ne_edge_grid: ne_edge_grid,
          render_overlays: Boolean(options.render_overlays)
        });
        errors.push(...res.errors);
        warnings.push(...res.warnings);
        per_mask.push(Object.assign({ file: path.basename(abs_p), domain: dom }, res.stats));
      }

      //1. Scan project _shared scripts & manifests for banned HGIS sources (EU4/Vic2/aourednik)
      this.auditBannedHgisSources(manifest_dir, hgis_policy, errors);

      //2. Audit subadmin_hgis HYDE overlapping window coverage if directory exists
      let subadmin_stats = this.auditSubadminHgisWindows(manifest_dir, hgis_policy, errors, warnings, options);

      //3. Enforce Pass-2 separate mask_auditor sign-off when required
      let signoff_ok = this.auditSeparateAuditorSignoff(manifest_dir, per_mask, Boolean(options.require_auditor_signoff), errors, warnings);

      //Return statement
      return {
        errors: errors,
        has_micro_islands: has_micro_islands,
        mask_count: per_mask.length,
        per_mask: per_mask,
        project: proj_key || "UNKNOWN",
        signoff_ok: signoff_ok,
        subadmin_stats: subadmin_stats,
        warnings: warnings
      };
    },

    /**
     * Scans project scripts and HGIS manifests for banned videogame maps or aourednik historical-basemaps.
     * @alias areal_masks_auditor.auditBannedHgisSources
     *
     * @param {string} arg0_project_dir
     * @param {Object} arg1_policy
     * @param {Array<string>} arg2_errors
     */
    auditBannedHgisSources (arg0_project_dir, arg1_policy, arg2_errors) {
      //Convert from parameters
      let errors = arg2_errors;
      let policy = arg1_policy || {};
      let project_dir = arg0_project_dir;

      //Declare local instance variables
      let banned = Array.isArray(policy.banned_hgis_sources) ? policy.banned_hgis_sources :
        ["eu4", "vic2", "victoria2", "ck2", "ck3", "hoi4", "paradox", "aourednik", "historical-basemaps"];
      let shared_dir = path.join(project_dir, "_shared");

      //Guard clauses
      if (!fs.existsSync(shared_dir)) return;

      //Function body
      let files = viscount_audit_utils.walkFiles(shared_dir, function (arg0_p, arg1_n) {
        return /\.(?:py|js|json5)$/i.test(arg1_n) && !/summary_cache|enumerations/i.test(arg1_n);
      });
      for (let i = 0; i < files.length; i++) {
        let fp = files[i];
        let stat = fs.statSync(fp);
        if (stat.size > 2*1024*1024) continue;
        let txt = fs.readFileSync(fp, "utf8");
        let lines = txt.split(/\r?\n/);
        for (let ln_i = 0; ln_i < lines.length; ln_i++) {
          let line = lines[ln_i];
          if (/^\s*(?:#|\/\/|\*)/.test(line)) continue;
          if (/ban|forbid|exclude|reject|skip|never/i.test(line)) continue;
          let low = line.toLowerCase();
          for (let b = 0; b < banned.length; b++) {
            let tok = String(banned[b] || "").toLowerCase();
            if (!tok) continue;
            let re = new RegExp(`(?:^|[^a-z0-9])${tok.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?:$|[^a-z0-9])`, "i");
            if (re.test(low)) {
              errors.push(`[BANNED_HGIS] ${path.relative(project_dir, fp)}:${ln_i + 1} references banned source "${tok}" (use OHM + academic HGIS or atlas_dejure.naissance).`);
              break;
            }
          }
        }
      }
    },

    /**
     * Verifies `_shared/mask_audit_signoff.json` signed by a strictly separate Pass-2 `mask_auditor`.
     * @alias areal_masks_auditor.auditSeparateAuditorSignoff
     *
     * @param {string} arg0_project_dir
     * @param {Array<Object>} arg1_per_mask
     * @param {boolean} arg2_required
     * @param {Array<string>} arg3_errors
     * @param {Array<string>} arg4_warnings
     *
     * @returns {boolean}
     */
    auditSeparateAuditorSignoff (arg0_project_dir, arg1_per_mask, arg2_required, arg3_errors, arg4_warnings) {
      //Convert from parameters
      let errors = arg3_errors;
      let per_mask = Array.isArray(arg1_per_mask) ? arg1_per_mask : [];
      let project_dir = arg0_project_dir;
      let required = Boolean(arg2_required);
      let warnings = arg4_warnings;

      //Declare local instance variables
      let signoff_path = path.join(project_dir, "_shared/mask_audit_signoff.json");

      //Guard clauses
      if (!fs.existsSync(signoff_path)) {
        if (required)
          errors.push(`[PASS2_AUDITOR] Missing required separate Pass-2 mask auditor sign-off: ${signoff_path}`);
        else
          warnings.push(`Separate Pass-2 mask auditor sign-off not yet present (${signoff_path}).`);
        return false;
      }

      //Function body
      let obj = viscount_audit_utils.loadJsonOrJson5(signoff_path);
      let pass2_count = Number(obj.pass2_subagents_used || 0);
      if (pass2_count > 2)
        errors.push(`[PASS2_CAP] Pass-2 mask population used ${pass2_count} subagents (> hard cap of 2).`);
      if (!obj.verified_by_separate_auditor || !obj.auditor_role || obj.auditor_role === obj.builder_role)
        errors.push("[PASS2_AUDITOR] mask_audit_signoff.json must confirm strictly separate mask_builder and read-only mask_auditor roles.");

      let crops = Array.isArray(obj.inspected_crops) ? obj.inspected_crops : [];
      let seen_notes = new Set();
      let dup_notes = 0;
      for (let i = 0; i < crops.length; i++) {
        let note = String((crops[i] && crops[i].notes) || "").trim();
        if (note.length < 40)
          errors.push(`[PASS2_AUDITOR] Crop entry ${i + 1} has insufficient audit notes (< 40 chars).`);
        else if (seen_notes.has(note))
          dup_notes++;
        else
          seen_notes.add(note);
      }
      if (dup_notes > 0)
        errors.push(`[PASS2_AUDITOR] ${dup_notes} duplicate/copy-pasted crop audit notes detected in mask_audit_signoff.json.`);
      if (required && crops.length < Math.min(per_mask.length, 1))
        errors.push(`[PASS2_AUDITOR] mask_audit_signoff.json lists only ${crops.length} inspected crops.`);

      //Return statement
      return errors.length === 0;
    },

    /**
     * Audits a single `4320x2160` areal mask PNG for starvation, synthetic boxes, scanlines,
     * straight-line cuts, pre-1945 modern-border leakage, vector companion presence, and settlement containment.
     * @alias areal_masks_auditor.auditSingleMask
     *
     * @param {string} arg0_mask_path
     * @param {Object} [arg1_options]
     *
     * @returns {Promise<Object>}
     */
    async auditSingleMask (arg0_mask_path, arg1_options) {
      //Convert from parameters
      let mask_path = arg0_mask_path;
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let errors = [];
      let has_micro_islands = Boolean(options.has_micro_islands);
      let is_admin1 = Boolean(options.is_admin1);
      let policy = options.hgis_policy || {};
      let warnings = [];

      //Guard clauses
      if (!fs.existsSync(mask_path))
        return { errors: [`Missing mask PNG: ${mask_path}`], stats: { active_px: 0 }, warnings: warnings };

      //Function body
      let png = viscount_audit_utils.decodeRgbaPng(mask_path);
      let buf = png.data;
      let h = png.height;
      let w = png.width;
      let valid = new Uint8Array(w*h);

      let active_px = 0;
      let min_r = h;
      let max_r = -1;
      let min_c = w;
      let max_c = -1;
      let rgb_counts = new Map();
      let rgb_bounds = new Map();

      for (let r = 0; r < h; r++) {
        let row_off = r*w;
        for (let c = 0; c < w; c++) {
          let idx = row_off + c;
          let p4 = idx*4;
          let a = buf[p4 + 3];
          let rv = buf[p4];
          let gv = buf[p4 + 1];
          let bv = buf[p4 + 2];
          if (a > 0 && (rv + gv + bv) > 0) {
            valid[idx] = 1;
            active_px++;
            if (r < min_r) min_r = r;
            if (r > max_r) max_r = r;
            if (c < min_c) min_c = c;
            if (c > max_c) max_c = c;
            let ck = (rv << 16) | (gv << 8) | bv;
            rgb_counts.set(ck, (rgb_counts.get(ck) || 0) + 1);
            let bnd = rgb_bounds.get(ck);
            if (!bnd) {
              rgb_bounds.set(ck, [r, r, c, c]);
            } else {
              if (r < bnd[0]) bnd[0] = r;
              if (r > bnd[1]) bnd[1] = r;
              if (c < bnd[2]) bnd[2] = c;
              if (c > bnd[3]) bnd[3] = c;
            }
          }
        }
      }

      if (active_px === 0)
        return { errors: [`Areal mask ${path.basename(mask_path)} contains 0 active pixels.`], stats: { active_px: 0 }, warnings: warnings };

      let bbox_area = (max_r - min_r + 1)*(max_c - min_c + 1);
      let bbox_fill = active_px/Math.max(1, bbox_area);
      let is_micro_sheet = has_micro_islands && active_px < 1500;
      if (active_px >= 100 && !is_micro_sheet && !is_admin1 && bbox_fill > 0.96) {
        errors.push(
          `[GEOMETRY] Mask ${path.basename(mask_path)} has rectangular box fill ratio ${bbox_fill.toFixed(3)} (> 0.96); ` +
          "masks must follow watersheds, OHM/academic HGIS polygons or real GIS layers."
        );
      }

      //Scanline artefact detection (alternating empty rows strictly between populated rows)
      let scanline_gaps = 0;
      for (let r = min_r + 1; r < max_r; r++) {
        let row_cnt = 0;
        let prev_cnt = 0;
        let next_cnt = 0;
        for (let c = min_c; c <= max_c; c++) {
          if (valid[r*w + c]) row_cnt++;
          if (valid[(r - 1)*w + c]) prev_cnt++;
          if (valid[(r + 1)*w + c]) next_cnt++;
        }
        if (row_cnt === 0 && prev_cnt >= 15 && next_cnt >= 15) scanline_gaps++;
      }
      if (scanline_gaps >= 2)
        errors.push(`[TOPOLOGY_SCANLINE] Mask ${path.basename(mask_path)} exhibits ${scanline_gaps} horizontal scanline gap row(s).`);

      //Interior sliver check & pre-1945 modern border edge correlation
      let sliver_min_px = Number(policy.sliver_min_px) || 4;
      let tiny_sliver_colors = 0;
      rgb_counts.forEach(function (arg0_cnt) {
        if (arg0_cnt > 0 && arg0_cnt < sliver_min_px) tiny_sliver_colors++;
      });
      if (tiny_sliver_colors >= 6)
        warnings.push(`[TOPOLOGY_SLIVER] Mask ${path.basename(mask_path)} contains ${tiny_sliver_colors} micro-sliver colour fragments (< ${sliver_min_px} px).`);

      let modern_border_iou = 0.0;
      if (!is_admin1 && options.ne_edge_grid && active_px >= 400) {
        let mask_int_edges = 0;
        let overlap_edges = 0;
        let ne_edges = options.ne_edge_grid;
        for (let r = Math.max(1, min_r); r < Math.min(h - 1, max_r); r++) {
          let row_off = r*w;
          for (let c = Math.max(1, min_c); c < Math.min(w - 1, max_c); c++) {
            let idx = row_off + c;
            if (!valid[idx]) continue;
            let p4 = idx*4;
            let cur_c = (buf[p4] << 16) | (buf[p4 + 1] << 8) | buf[p4 + 2];
            let r_idx = idx + 1;
            let d_idx = idx + w;
            let is_int_edge = false;
            if (valid[r_idx]) {
              let rp4 = r_idx*4;
              if (((buf[rp4] << 16) | (buf[rp4 + 1] << 8) | buf[rp4 + 2]) !== cur_c) is_int_edge = true;
            }
            if (!is_int_edge && valid[d_idx]) {
              let dp4 = d_idx*4;
              if (((buf[dp4] << 16) | (buf[dp4 + 1] << 8) | buf[dp4 + 2]) !== cur_c) is_int_edge = true;
            }
            if (is_int_edge) {
              mask_int_edges++;
              if (ne_edges[idx] || ne_edges[idx - 1] || ne_edges[idx + 1] || ne_edges[idx - w] || ne_edges[idx + w])
                overlap_edges++;
            }
          }
        }
        if (mask_int_edges >= 120) {
          modern_border_iou = overlap_edges/mask_int_edges;
          let max_iou = Number(policy.max_modern_border_edge_iou_pre1945) || 0.62;
          if (modern_border_iou > max_iou) {
            warnings.push(
              `[MODERN_BORDER_LEAK] Pre-1945 mask ${path.basename(mask_path)} shares ${(modern_border_iou*100).toFixed(1)}% of interior edges with modern 2025 Admin-0 borders (> ${(max_iou*100).toFixed(0)}%); confirm optically via Pass-2 mask_auditor.`
            );
          }
        }
      }

      //Sibling JSON5 RGB sub-region starvation & box check
      let cfg_path = mask_path.replace(/_areal_mask\.png$/i, ".json5");
      let zero_rgb_regions = [];
      if (fs.existsSync(cfg_path)) {
        let cfg = viscount_audit_utils.loadJsonOrJson5(cfg_path);
        let sub_list = [];
        let sub_keys = ["regions", "subregions", "sub_regions", "zones"];
        for (let i = 0; i < sub_keys.length; i++) {
          let vk = cfg[sub_keys[i]];
          if (Array.isArray(vk)) { sub_list = vk; break; }
          if (vk && typeof vk === "object") {
            let ks = Object.keys(vk);
            for (let x = 0; x < ks.length; x++)
              if (vk[ks[x]] && typeof vk[ks[x]] === "object") sub_list.push(Object.assign({ id: ks[x] }, vk[ks[x]]));
            break;
          }
        }
        for (let i = 0; i < sub_list.length; i++) {
          let sub = sub_list[i];
          if (!sub || typeof sub !== "object") continue;
          let rgb = sub.rgb || sub.color || sub.colour;
          if (Array.isArray(rgb) && rgb.length >= 3) {
            let ck = ((Number(rgb[0]) & 255) << 16) | ((Number(rgb[1]) & 255) << 8) | (Number(rgb[2]) & 255);
            let cnt = rgb_counts.get(ck) || 0;
            if (cnt === 0) {
              zero_rgb_regions.push(sub.id || sub.name || JSON.stringify(rgb));
            } else if (cnt >= 150 && !is_micro_sheet && !is_admin1) {
              let bnd = rgb_bounds.get(ck);
              let sub_fill = cnt/Math.max(1, (bnd[1] - bnd[0] + 1)*(bnd[3] - bnd[2] + 1));
              if (sub_fill > 0.92)
                errors.push(`[GEOMETRY] Sub-region "${sub.id || rgb}" in ${path.basename(mask_path)} has synthetic box fill ratio ${sub_fill.toFixed(3)} (> 0.92).`);
            }
          }
        }
        if (zero_rgb_regions.length > 0)
          errors.push(`[STARVATION] Sub-region(s) declared in ${path.basename(cfg_path)} have 0 pixels: ${zero_rgb_regions.slice(0, 5).join(", ")}`);
      }

      //Sibling settlements containment & optional fast sharp bbox crop overlay
      let sett_path = mask_path.replace(/_areal_mask\.png$/i, "_settlements.json");
      let inside_count = 0;
      let total_setts = 0;
      let pts_render = [];
      if (fs.existsSync(sett_path)) {
        let sdata = viscount_audit_utils.loadJsonOrJson5(sett_path);
        let rows = Array.isArray(sdata) ? sdata : Object.values(sdata || {});
        let rad = has_micro_islands ? 5 : 2;
        for (let i = 0; i < rows.length; i++) {
          let c = rows[i];
          if (!c || !Array.isArray(c.coords) || c.coords.length < 2) continue;
          let lat = Number(c.coords[0]);
          let lon = Number(c.coords[1]);
          if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
          total_setts++;
          let r = Math.min(h - 1, Math.max(0, Math.floor((90.0 - lat)*h/180.0)));
          let col = Math.min(w - 1, Math.max(0, Math.floor((lon + 180.0)*w/360.0)));
          let hit = false;
          for (let dr = -rad; dr <= rad && !hit; dr++) {
            let rr = r + dr;
            if (rr < 0 || rr >= h) continue;
            for (let dc = -rad; dc <= rad; dc++) {
              let cc = col + dc;
              if (cc >= 0 && cc < w && valid[rr*w + cc]) { hit = true; break; }
            }
          }
          if (hit) inside_count++;
          if (options.render_overlays) pts_render.push({ col: col, hit: hit, row: r });
        }
        if (total_setts > 0 && inside_count === 0)
          errors.push(`[CONTAINMENT] 0/${total_setts} settlements fall inside ${path.basename(mask_path)}.`);
      }

      if (options.render_overlays) {
        let ov_dir = path.join(path.dirname(mask_path), "overlays_qa");
        let stem = path.basename(mask_path).replace(/_areal_mask\.png$/i, "");
        await this.renderBboxOverlayCrop(mask_path, [min_r, max_r, min_c, max_c], pts_render, path.join(ov_dir, `verify_${stem}_overlay.png`));
      }

      //Return statement
      return {
        errors: errors,
        stats: {
          active_px: active_px,
          bbox_fill: Number(bbox_fill.toFixed(4)),
          inside_settlements: inside_count,
          modern_border_edge_overlap: Number(modern_border_iou.toFixed(4)),
          scanline_gaps: scanline_gaps,
          total_settlements: total_setts
        },
        warnings: warnings
      };
    },

    /**
     * Checks `subadmin_hgis` overlapping HYDE windows (`100y` to `1700`, `10y` to `1950`, `1y` `1951..2025`).
     * @alias areal_masks_auditor.auditSubadminHgisWindows
     *
     * @param {string} arg0_project_dir
     * @param {Object} arg1_policy
     * @param {Array<string>} arg2_errors
     * @param {Array<string>} arg3_warnings
     * @param {Object} [arg4_options]
     *
     * @returns {Object}
     */
    auditSubadminHgisWindows (arg0_project_dir, arg1_policy, arg2_errors, arg3_warnings, arg4_options) {
      //Convert from parameters
      let errors = arg2_errors;
      let options = arg4_options || {};
      let project_dir = arg0_project_dir;
      let warnings = arg3_warnings;

      //Declare local instance variables
      let rdir = path.join(project_dir, "_shared/subadmin_hgis/rasters");

      //Guard clauses
      if (!fs.existsSync(rdir))
        return { present: false, raster_count: 0 };

      //Function body
      let files = fs.readdirSync(rdir).filter(function (arg0_f) { return /^subadmin_id_-?\d+\.png$/i.test(arg0_f); });
      let yrs = new Set();
      for (let i = 0; i < files.length; i++) {
        let m = files[i].match(/^subadmin_id_(-?\d+)\.png$/i);
        if (m) yrs.add(Number(m[1]));
      }
      let missing = [];
      for (let y = 1500; y <= 1700; y += 100) if (!yrs.has(y)) missing.push(y);
      for (let y = 1710; y <= 1950; y += 10) if (!yrs.has(y)) missing.push(y);
      for (let y = 1951; y <= 2025; y++) if (!yrs.has(y)) missing.push(y);

      if (missing.length > 0) {
        let msg = `[SUBADMIN_HYDE] Missing ${missing.length} required overlapping HYDE subadmin_id_<year>.png raster(s): ${missing.slice(0, 8).join(", ")}`;
        if (options.require_subadmin_hyde) errors.push(msg);
        else warnings.push(msg);
      }

      //Return statement
      return { missing_count: missing.length, present: true, raster_count: files.length };
    },

    /**
     * Builds a `4320x2160` boolean grid of modern Natural Earth Admin-0 border edge pixels (cached).
     * @alias areal_masks_auditor.buildModernBorderEdgeGrid
     *
     * @param {string} arg0_svea_root
     *
     * @returns {Uint8Array|null}
     */
    buildModernBorderEdgeGrid (arg0_svea_root) {
      //Guard clauses
      if (!arg0_svea_root) return null;
      let ne_path = path.join(arg0_svea_root, "histmap/1.data_raw/population_regional/_shared/_gis_cache/ne_10m_admin_0_countries.geojson");
      if (!fs.existsSync(ne_path)) return null;

      //Declare local instance variables
      let h = 2160;
      let w = 4320;
      let grid = new Uint8Array(w*h);

      //Function body
      let gj = JSON.parse(fs.readFileSync(ne_path, "utf8"));
      let feats = Array.isArray(gj.features) ? gj.features : [];
      let drawRing = function (arg0_ring) {
        for (let i = 1; i < arg0_ring.length; i++) {
          let x0 = (arg0_ring[i - 1][0] + 180.0)*w/360.0;
          let y0 = (90.0 - arg0_ring[i - 1][1])*h/180.0;
          let x1 = (arg0_ring[i][0] + 180.0)*w/360.0;
          let y1 = (90.0 - arg0_ring[i][1])*h/180.0;
          let steps = Math.max(1, Math.ceil(Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0))));
          if (steps > 400) continue;
          for (let s = 0; s <= steps; s++) {
            let t = s/steps;
            let c = Math.min(w - 1, Math.max(0, Math.floor(x0 + (x1 - x0)*t)));
            let r = Math.min(h - 1, Math.max(0, Math.floor(y0 + (y1 - y0)*t)));
            grid[r*w + c] = 1;
          }
        }
      };

      for (let i = 0; i < feats.length; i++) {
        let g = feats[i] && feats[i].geometry;
        if (!g || !g.coordinates) continue;
        if (g.type === "Polygon" && g.coordinates[0]) drawRing(g.coordinates[0]);
        else if (g.type === "MultiPolygon") {
          for (let p = 0; p < g.coordinates.length; p++)
            if (g.coordinates[p][0]) drawRing(g.coordinates[p][0]);
        }
      }

      //Return statement
      return grid;
    },

    /**
     * Parses CLI arguments for `audit_areal_masks.js`.
     * @alias areal_masks_auditor.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let args = {
        has_micro_islands: false,
        render_overlays: false,
        require_auditor_signoff: false,
        require_subadmin_hyde: false,
        target: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok === "--render-overlays") args.render_overlays = true;
        else if (tok === "--require-auditor-signoff") args.require_auditor_signoff = true;
        else if (tok === "--require-subadmin-hyde") args.require_subadmin_hyde = true;
        else if (tok === "--has-micro-islands") args.has_micro_islands = true;
        else if (!tok.startsWith("--") && !args.target) args.target = tok;
      }

      //Return statement
      return args;
    },

    /**
     * Fast `sharp` bbox crop overlay renderer for optical `read_file` visual QA (`< 80 ms` per mask).
     * @alias areal_masks_auditor.renderBboxOverlayCrop
     *
     * @param {string} arg0_mask_path
     * @param {Array<number>} arg1_bounds
     * @param {Array<Object>} arg2_points
     * @param {string} arg3_out_path
     *
     * @returns {Promise<void>}
     */
    async renderBboxOverlayCrop (arg0_mask_path, arg1_bounds, arg2_points, arg3_out_path) {
      //Convert from parameters
      let bounds = arg1_bounds;
      let mask_path = arg0_mask_path;
      let out_path = arg3_out_path;
      let points = Array.isArray(arg2_points) ? arg2_points : [];

      //Declare local instance variables
      let r0 = Math.max(0, bounds[0] - 16);
      let r1 = Math.min(2160, bounds[1] + 17);
      let c0 = Math.max(0, bounds[2] - 20);
      let c1 = Math.min(4320, bounds[3] + 21);
      let cw = Math.max(1, c1 - c0);
      let ch = Math.max(1, r1 - r0);
      let scale = Math.min(4, Math.max(1, Math.floor(1200/Math.max(cw, ch))));
      let ow = cw*scale;
      let oh = ch*scale;

      //Function body
      fs.mkdirSync(path.dirname(out_path), { recursive: true });
      let circles = [];
      let stride = Math.max(1, Math.floor(points.length/2500));
      for (let i = 0; i < points.length; i += stride) {
        let pt = points[i];
        let x = (pt.col - c0 + 0.5)*scale;
        let y = (pt.row - r0 + 0.5)*scale;
        if (x < 0 || x > ow || y < 0 || y > oh) continue;
        let col = pt.hit ? "#1f77b4" : "#d62728";
        circles.push(`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${pt.hit ? 2.2 : 3.5}" fill="${col}" stroke="#ffffff" stroke-width="0.5"/>`);
      }
      let svg = Buffer.from(`<svg width="${ow}" height="${oh}" xmlns="http://www.w3.org/2000/svg">${circles.join("")}</svg>`);

      await sharp(mask_path)
        .extract({ height: ch, left: c0, top: r0, width: cw })
        .resize(ow, oh, { kernel: sharp.kernel.nearest })
        .flatten({ background: { b: 248, g: 245, r: 240 } })
        .composite([{ input: svg, left: 0, top: 0 }])
        .png()
        .toFile(out_path);
    },

    /**
     * Resolves a target path into a manifest path or single mask path.
     * @alias areal_masks_auditor.resolveTarget
     *
     * @param {string} arg0_target
     *
     * @returns {{ mode: string, path: string }|null}
     */
    resolveTarget (arg0_target) {
      //Convert from parameters
      let abs_p = path.resolve(arg0_target || ".");

      //Guard clauses
      if (!fs.existsSync(abs_p)) return null;

      //Function body
      let st = fs.statSync(abs_p);
      if (st.isFile()) {
        if (/\.json5?$/i.test(abs_p)) return { mode: "manifest", path: abs_p };
        if (/_areal_mask\.png$/i.test(abs_p)) return { mode: "single", path: abs_p };
        return null;
      }
      let files = fs.readdirSync(abs_p).sort();
      for (let i = 0; i < files.length; i++)
        if (/areal_masks.*\.json5?$/i.test(files[i]))
          return { mode: "manifest", path: path.join(abs_p, files[i]) };
      for (let i = 0; i < files.length; i++)
        if (/_areal_mask\.png$/i.test(files[i]))
          return { mode: "single", path: path.join(abs_p, files[i]) };

      //Return statement
      return null;
    }
  };

  if (require.main === module) {
    let cli = areal_masks_auditor.parseCliArgs(process.argv.slice(2));
    let resolved = areal_masks_auditor.resolveTarget(cli.target);
    if (!resolved) {
      console.error(`[audit_areal_masks] Could not resolve areal mask or manifest from: ${cli.target}`);
      process.exit(1);
    }
    let run = (resolved.mode === "manifest") ?
      areal_masks_auditor.auditManifest(resolved.path, cli) :
      areal_masks_auditor.auditSingleMask(resolved.path, cli);
    run.then(function (arg0_res) {
      let warns = arg0_res.warnings || [];
      let errs = arg0_res.errors || [];
      for (let i = 0; i < Math.min(40, warns.length); i++) console.log(`[WARN] ${warns[i]}`);
      for (let i = 0; i < Math.min(40, errs.length); i++) console.error(`[FAIL] ${errs[i]}`);
      console.log(`[audit_areal_masks] Summary: masks=${arg0_res.mask_count || 1}, errors=${errs.length}, warnings=${warns.length}`);
      process.exit(errs.length > 0 ? 1 : 0);
    }).catch(function (arg0_err) {
      console.error("[audit_areal_masks] Fatal error:", arg0_err);
      process.exit(1);
    });
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { areal_masks_auditor: areal_masks_auditor };
  }
}
