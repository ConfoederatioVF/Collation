//Initialise functions
{
  if (!global.population_c14bazAAR_maps) global.population_c14bazAAR_maps = {};

  /**
   * Builds projected polygon, translucent graticule, label, colourbar, and point-dot geometry
   * for rendering a radiocarbon distribution map over Russia (excluding Kaliningrad).
   * @alias population_c14bazAAR_maps.buildMapRenderPayload
   *
   * @param {string} arg0_projection_mode - Either 'conical' (Albers Equal-Area Conic) or 'equirectangular'.
   * @param {Array<Object>} arg1_polygons_array - Array of Russia landmass polygon objects ({ exterior, holes }).
   * @param {Array<Object>} arg2_dates_array - Filtered calibrated radiocarbon date records.
   * @param {Object} [arg3_options]
   *
   * @returns {Object} Self-contained canvas render job specification.
   */
  population_c14bazAAR_maps.buildMapRenderPayload = function (arg0_projection_mode, arg1_polygons_array, arg2_dates_array, arg3_options) {
    //Convert from parameters
    let projection_mode = arg0_projection_mode;
    let polygons_array = (arg1_polygons_array) ? arg1_polygons_array : [];
    let dates_array = (arg2_dates_array) ? arg2_dates_array : [];
    let options = (arg3_options) ? arg3_options : {};

    //Initialise options
    if (options.dot_radius === undefined) options.dot_radius = 2.6;
    if (options.max_year === undefined) options.max_year = 1500;
    if (options.min_year === undefined) options.min_year = 1;

    //Declare local instance variables
    let c_const = 0;
    let canvas_height = 1760;
    let canvas_width = 2800;
    let central_lon = 105.0;
    let coord_groups = {};
    let deg_to_rad = Math.PI/180.0;
    let dots_array = [];
    let eq_lat_max = 81.0;
    let eq_lat_min = 40.0;
    let eq_lon_max = 192.0;
    let eq_lon_min = 26.0;
    let eq_px_per_deg = 18.0;
    let frame_obj = { x0: 76, x1: 2724, y0: 108, y1: 1596 };
    let graticule_labels = [];
    let graticule_lines = [];
    let max_px = -Infinity;
    let max_py = -Infinity;
    let min_px = Infinity;
    let min_py = Infinity;
    let n_cone = 0;
    let origin_lat = 60.0;
    let pad_frac = 0.038;
    let parallel_1 = 50.0;
    let parallel_2 = 70.0;
    let phi_0 = 0;
    let phi_1 = 0;
    let phi_2 = 0;
    let proj_polygons = [];
    let projectPoint = null;
    let rho_0 = 0;
    let scale_factor = 1.0;
    let sorted_dates = [];
    let spectral_stops = [];
    let subtitle_str = "";
    let title_str = "";
    let toScreen = null;

    phi_0 = origin_lat*deg_to_rad;
    phi_1 = parallel_1*deg_to_rad;
    phi_2 = parallel_2*deg_to_rad;
    n_cone = 0.5*(Math.sin(phi_1) + Math.sin(phi_2));
    c_const = Math.cos(phi_1)*Math.cos(phi_1) + 2.0*n_cone*Math.sin(phi_1);
    rho_0 = Math.sqrt(Math.max(0, c_const - 2.0*n_cone*Math.sin(phi_0)))/n_cone;

    if (projection_mode === "conical") {
      canvas_width = 2800;
      canvas_height = 1760;
      frame_obj = { x0: 76, x1: 2724, y0: 108, y1: 1596 };
      projectPoint = function (arg0_lon_u, arg1_lat) {
        let lon_u = arg0_lon_u;
        let lat = arg1_lat;
        let phi = lat*deg_to_rad;
        let rho = Math.sqrt(Math.max(0, c_const - 2.0*n_cone*Math.sin(phi)))/n_cone;
        let theta = n_cone*(lon_u - central_lon)*deg_to_rad;
        return [rho*Math.sin(theta), rho_0 - rho*Math.cos(theta)];
      };

      for (let i = 0; i < polygons_array.length; i++) {
        let local_ring = polygons_array[i].exterior;
        for (let x = 0; x < local_ring.length; x++) {
          let local_pt = projectPoint(local_ring[x][0], local_ring[x][1]);
          min_px = Math.min(min_px, local_pt[0]);
          max_px = Math.max(max_px, local_pt[0]);
          min_py = Math.min(min_py, local_pt[1]);
          max_py = Math.max(max_py, local_pt[1]);
        }
      }

      let span_x = (max_px - min_px)*(1.0 + 2.0*pad_frac);
      let span_y = (max_py - min_py)*(1.0 + 2.0*pad_frac);
      let cx_proj = 0.5*(min_px + max_px);
      let cy_proj = 0.5*(min_py + max_py);
      let fw = frame_obj.x1 - frame_obj.x0;
      let fh = frame_obj.y1 - frame_obj.y0;
      scale_factor = Math.min(fw/span_x, fh/span_y);

      toScreen = function (arg0_lon_u, arg1_lat) {
        let local_p = projectPoint(arg0_lon_u, arg1_lat);
        return [
          0.5*(frame_obj.x0 + frame_obj.x1) + (local_p[0] - cx_proj)*scale_factor,
          0.5*(frame_obj.y0 + frame_obj.y1) - (local_p[1] - cy_proj)*scale_factor
        ];
      };

      title_str = "c14bazAAR Radiocarbon Determinations — Russia (excl. Kaliningrad), 1 AD–1500 AD";
      subtitle_str = `Albers Equal-Area Conic (λ₀ = 105°E, φ₁ = 50°N, φ₂ = 70°N)  •  IntCal20 Calibrated Date  •  n = ${dates_array.length} determinations`;
    } else {
      let fw = Math.round((eq_lon_max - eq_lon_min)*eq_px_per_deg);
      let fh = Math.round((eq_lat_max - eq_lat_min)*eq_px_per_deg);
      canvas_width = fw + 172;
      canvas_height = fh + 264;
      frame_obj = { x0: 86, x1: 86 + fw, y0: 112, y1: 112 + fh };

      toScreen = function (arg0_lon_u, arg1_lat) {
        return [
          frame_obj.x0 + (arg0_lon_u - eq_lon_min)*eq_px_per_deg,
          frame_obj.y0 + (eq_lat_max - arg1_lat)*eq_px_per_deg
        ];
      };

      title_str = "c14bazAAR Radiocarbon Determinations — Russia (excl. Kaliningrad), 1 AD–1500 AD";
      subtitle_str = `Equirectangular Projection (Plate Carrée, 1:1 Degree Reference Grid)  •  IntCal20 Calibrated Date  •  n = ${dates_array.length} determinations`;
    }

    //1. Project landmass polygons and mark internal 180-degree antimeridian split edges
    for (let i = 0; i < polygons_array.length; i++) {
      let local_ext = polygons_array[i].exterior;
      let local_holes = polygons_array[i].holes || [];
      let proj_ext = [];
      let proj_holes = [];
      let stroke_segments = [];

      for (let x = 0; x < local_ext.length; x++)
        proj_ext.push(toScreen(local_ext[x][0], local_ext[x][1]));

      for (let x = 0; x < local_ext.length - 1; x++) {
        let local_p0 = local_ext[x];
        let local_p1 = local_ext[x + 1];
        let is_seam = (Math.abs(local_p0[0] - 180.0) < 0.008 && Math.abs(local_p1[0] - 180.0) < 0.008);
        if (!is_seam)
          stroke_segments.push([proj_ext[x], proj_ext[x + 1]]);
      }

      for (let x = 0; x < local_holes.length; x++) {
        let local_h = local_holes[x];
        let local_ph = [];
        for (let y = 0; y < local_h.length; y++)
          local_ph.push(toScreen(local_h[y][0], local_h[y][1]));
        proj_holes.push(local_ph);
        for (let y = 0; y < local_h.length - 1; y++)
          stroke_segments.push([local_ph[y], local_ph[y + 1]]);
      }

      proj_polygons.push({
        exterior: proj_ext,
        holes: proj_holes,
        stroke_segments: stroke_segments
      });
    }

    //2. Build translucent graticule polylines and coordinate labels
    if (projection_mode === "conical") {
      let lat_parallels = [35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85];
      let lon_meridians = [15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195];

      for (let i = 0; i < lat_parallels.length; i++) {
        let local_lat = lat_parallels[i];
        let local_pts = [];
        for (let x = 0; x <= 440; x++) {
          let local_lon = -5.0 + x*0.5;
          local_pts.push(toScreen(local_lon, local_lat));
        }
        graticule_lines.push(local_pts);

        if (local_lat >= 40 && local_lat <= 80 && local_lat % 10 === 0) {
          let hits = population_c14bazAAR_maps.findSegmentFrameIntersections(local_pts, frame_obj);
          for (let x = 0; x < hits.length; x++)
            if (hits[x].edge === "left" || hits[x].edge === "right")
              graticule_labels.push({
                align: (hits[x].edge === "left") ? "right" : "left",
                baseline: "middle",
                edge: hits[x].edge,
                text: `${local_lat}°N`,
                x: (hits[x].edge === "left") ? frame_obj.x0 - 10 : frame_obj.x1 + 10,
                y: hits[x].y
              });
        }
      }

      for (let i = 0; i < lon_meridians.length; i++) {
        let local_lon = lon_meridians[i];
        let local_pts = [];
        for (let x = 0; x <= 120; x++) {
          let local_lat = 25.0 + x*0.5;
          local_pts.push(toScreen(local_lon, local_lat));
        }
        graticule_lines.push(local_pts);

        if (local_lon >= 30 && local_lon <= 195) {
          let hits = population_c14bazAAR_maps.findSegmentFrameIntersections(local_pts, frame_obj);
          //Select the southernmost (largest screen y) exit point on bottom, left, or right border
          let best_hit = null;
          for (let x = 0; x < hits.length; x++)
            if (hits[x].edge === "bottom" || hits[x].edge === "left" || hits[x].edge === "right")
              if (!best_hit || hits[x].y > best_hit.y)
                best_hit = hits[x];

          if (best_hit) {
            let candidate_lbl = {
              align: (best_hit.edge === "bottom") ? "center" : ((best_hit.edge === "left") ? "right" : "left"),
              baseline: (best_hit.edge === "bottom") ? "top" : "middle",
              edge: best_hit.edge,
              text: population_c14bazAAR_maps.formatLongitudeLabel(local_lon),
              x: (best_hit.edge === "bottom") ? best_hit.x : ((best_hit.edge === "left") ? frame_obj.x0 - 10 : frame_obj.x1 + 10),
              y: (best_hit.edge === "bottom") ? frame_obj.y1 + 10 : best_hit.y
            };
            let has_overlap = false;
            for (let x = 0; x < graticule_labels.length; x++) {
              let ex_lbl = graticule_labels[x];
              if (ex_lbl.edge === candidate_lbl.edge) {
                let dist = Math.hypot(ex_lbl.x - candidate_lbl.x, ex_lbl.y - candidate_lbl.y);
                if (dist < 24) {
                  has_overlap = true;
                  break;
                }
              }
            }
            if (!has_overlap)
              graticule_labels.push(candidate_lbl);
          }
        }
      }

      //Add subtle interior parallel labels along central meridian 105E for high-latitude rings (70N, 80N) that close inside frame
      let interior_lats = [50, 60, 70, 80];
      for (let i = 0; i < interior_lats.length; i++) {
        let local_pt = toScreen(105.0, interior_lats[i]);
        if (local_pt[1] > frame_obj.y0 + 24 && local_pt[1] < frame_obj.y1 - 24)
          graticule_labels.push({
            align: "left",
            baseline: "bottom",
            edge: "interior",
            text: `${interior_lats[i]}°N`,
            x: local_pt[0] + 6,
            y: local_pt[1] - 3
          });
      }
    } else {
      for (let i = 40; i <= 80; i += 5) {
        let p0 = toScreen(eq_lon_min, i);
        let p1 = toScreen(eq_lon_max, i);
        graticule_lines.push([p0, p1]);
        graticule_labels.push({
          align: "right",
          baseline: "middle",
          edge: "left",
          text: `${i}°N`,
          x: frame_obj.x0 - 10,
          y: p0[1]
        });
        graticule_labels.push({
          align: "left",
          baseline: "middle",
          edge: "right",
          text: `${i}°N`,
          x: frame_obj.x1 + 10,
          y: p1[1]
        });
      }

      for (let i = 30; i <= 190; i += 10) {
        let p0 = toScreen(i, eq_lat_max);
        let p1 = toScreen(i, eq_lat_min);
        let lbl = population_c14bazAAR_maps.formatLongitudeLabel(i);
        graticule_lines.push([p0, p1]);
        graticule_labels.push({
          align: "center",
          baseline: "bottom",
          edge: "top",
          text: lbl,
          x: p0[0],
          y: frame_obj.y0 - 8
        });
        graticule_labels.push({
          align: "center",
          baseline: "top",
          edge: "bottom",
          text: lbl,
          x: p1[0],
          y: frame_obj.y1 + 10
        });
      }
    }

    //3. Project calibrated dates and apply Spectral colourscheme (1 AD -> 1500 AD)
    sorted_dates = dates_array.slice().sort((a, b) => a.cal_ad - b.cal_ad);
    for (let i = 0; i < sorted_dates.length; i++) {
      let local_d = sorted_dates[i];
      let local_key = `${local_d.lat.toFixed(3)}_${local_d.lon_u.toFixed(3)}`;
      if (!coord_groups[local_key]) coord_groups[local_key] = [];
      coord_groups[local_key].push(i);
    }

    for (let i = 0; i < sorted_dates.length; i++) {
      let local_d = sorted_dates[i];
      let local_key = `${local_d.lat.toFixed(3)}_${local_d.lon_u.toFixed(3)}`;
      let local_grp = coord_groups[local_key];
      let local_pt = toScreen(local_d.lon_u, local_d.lat);
      let local_t = Math.min(1, Math.max(0, (local_d.cal_ad - options.min_year)/(options.max_year - options.min_year)));
      let local_rgb = population_c14bazAAR_maps.sampleSpectralColour(local_t);
      let dx = 0;
      let dy = 0;

      if (local_grp.length > 1) {
        let local_idx = local_grp.indexOf(i);
        let local_ang = (2.0*Math.PI*local_idx)/local_grp.length - Math.PI*0.25;
        let local_sep = options.dot_radius*1.35;
        dx = Math.cos(local_ang)*local_sep;
        dy = Math.sin(local_ang)*local_sep;
      }

      dots_array.push({
        cal_ad: local_d.cal_ad,
        colour: `rgb(${local_rgb[0]},${local_rgb[1]},${local_rgb[2]})`,
        labnr: local_d.labnr,
        radius: options.dot_radius,
        x: local_pt[0] + dx,
        y: local_pt[1] + dy
      });
    }

    for (let i = 0; i <= 100; i++) {
      let local_t = i/100.0;
      let local_rgb = population_c14bazAAR_maps.sampleSpectralColour(local_t);
      spectral_stops.push({
        colour: `rgb(${local_rgb[0]},${local_rgb[1]},${local_rgb[2]})`,
        offset: local_t
      });
    }

    //Return statement
    return {
      canvas_height: canvas_height,
      canvas_width: canvas_width,
      dots: dots_array,
      frame: frame_obj,
      graticule_labels: graticule_labels,
      graticule_lines: graticule_lines,
      legend: {
        max_year: options.max_year,
        min_year: options.min_year,
        stops: spectral_stops,
        ticks: [1, 250, 500, 750, 1000, 1250, 1500]
      },
      output_path: options.output_path,
      polygons: proj_polygons,
      projection_mode: projection_mode,
      subtitle: subtitle_str,
      title: title_str
    };
  };


  /**
   * Calibrates a single radiocarbon determination (c14age, c14std) against IntCal20,
   * returning the posterior weighted-mean and median calendar years AD (1950 - cal BP).
   * @alias population_c14bazAAR_maps.calibrateIntCal20Record
   *
   * @param {number} arg0_c14_age - Uncalibrated radiocarbon age BP.
   * @param {number} arg1_c14_std - Radiocarbon standard error (1-sigma).
   * @param {Object} arg2_curve_obj - Parsed IntCal20 calibration curve object.
   *
   * @returns {Object} { cal_ad: number, median_ad: number }
   */
  population_c14bazAAR_maps.calibrateIntCal20Record = function (arg0_c14_age, arg1_c14_std, arg2_curve_obj) {
    //Convert from parameters
    let c14_age = arg0_c14_age;
    let c14_std = arg1_c14_std;
    let curve_obj = arg2_curve_obj;

    //Declare local instance variables
    let cal_bp_arr = curve_obj.cal_bp;
    let cum_w = 0;
    let curve_age_arr = curve_obj.c14_age;
    let curve_sig_arr = curve_obj.sigma;
    let dt_arr = curve_obj._dt;
    let log_max = -Infinity;
    let log_w = null;
    let mean_bp = 0;
    let median_bp = 0;
    let n_pts = cal_bp_arr.length;
    let sample_var = Math.max(1, c14_std*c14_std);
    let sum_w = 0;
    let weights = null;

    if (!dt_arr) {
      dt_arr = new Float64Array(n_pts);
      for (let i = 0; i < n_pts; i++) {
        if (i === 0) {
          dt_arr[i] = Math.abs(cal_bp_arr[1] - cal_bp_arr[0]);
        } else if (i === n_pts - 1) {
          dt_arr[i] = Math.abs(cal_bp_arr[n_pts - 1] - cal_bp_arr[n_pts - 2]);
        } else {
          dt_arr[i] = 0.5*Math.abs(cal_bp_arr[i + 1] - cal_bp_arr[i - 1]);
        }
      }
      curve_obj._dt = dt_arr;
    }

    log_w = new Float64Array(n_pts);
    weights = new Float64Array(n_pts);

    for (let i = 0; i < n_pts; i++) {
      let local_diff = c14_age - curve_age_arr[i];
      let local_var = sample_var + curve_sig_arr[i]*curve_sig_arr[i];
      let local_lw = -0.5*(local_diff*local_diff)/local_var - 0.5*Math.log(local_var);
      log_w[i] = local_lw;
      if (local_lw > log_max) log_max = local_lw;
    }

    for (let i = 0; i < n_pts; i++) {
      let local_d = log_w[i] - log_max;
      let local_w = (local_d > -60) ? Math.exp(local_d)*dt_arr[i] : 0;
      weights[i] = local_w;
      sum_w += local_w;
    }

    if (sum_w <= 0) {
      return { cal_ad: 1950.0 - c14_age, median_ad: 1950.0 - c14_age };
    }

    median_bp = cal_bp_arr[0];
    for (let i = 0; i < n_pts; i++) {
      let local_nw = weights[i]/sum_w;
      mean_bp += local_nw*cal_bp_arr[i];
      cum_w += local_nw;
      if (cum_w <= 0.5) median_bp = cal_bp_arr[i];
    }

    //Return statement
    return {
      cal_ad: 1950.0 - mean_bp,
      median_ad: 1950.0 - median_bp
    };
  };


  /**
   * Extracts high-Arctic Russian island polygons (e.g. Severnaya Zemlya north of 77,73°N)
   * from admin_modern/geocodes.png where CShapes-2.0 clips high latitudes.
   * @alias population_c14bazAAR_maps.extractArcticRasterPolygons
   *
   * @param {Object} arg0_geocodes_png - Decoded pngjs image object of geocodes.png.
   * @param {number} [arg1_min_lat=77.74] - Minimum latitude threshold in degrees N.
   *
   * @returns {Array<Object>} Array of polygon objects ({ exterior, holes: [] }).
   */
  population_c14bazAAR_maps.extractArcticRasterPolygons = function (arg0_geocodes_png, arg1_min_lat) {
    //Convert from parameters
    let geocodes_png = arg0_geocodes_png;
    let min_lat = (arg1_min_lat !== undefined) ? arg1_min_lat : 77.74;

    //Declare local instance variables
    let edge_keys = [];
    let edge_map = new Map();
    let height = 0;
    let max_row = 0;
    let polygons_out = [];
    let res_x = 0;
    let res_y = 0;
    let width = 0;

    //Guard clauses
    if (!geocodes_png || !geocodes_png.data) return polygons_out;


    height = geocodes_png.height;
    width = geocodes_png.width;
    res_x = 360.0/width;
    res_y = 180.0/height;
    max_row = Math.min(height - 1, Math.ceil((90.0 - min_lat)/res_y));

    let isRusArctic = function (arg0_x, arg1_y) {
      if (arg0_x < 0 || arg1_y < 0 || arg0_x >= width || arg1_y > max_row) return false;
      let local_idx = (arg1_y*width + arg0_x)*4;
      return (
        geocodes_png.data[local_idx] === 20 &&
        geocodes_png.data[local_idx + 1] === 114 &&
        geocodes_png.data[local_idx + 2] === 30
      );
    };

    let addDirectedEdge = function (arg0_x1, arg1_y1, arg2_x2, arg3_y2) {
      let local_k1 = `${arg0_x1},${arg1_y1}`;
      let local_k2 = `${arg2_x2},${arg3_y2}`;
      if (!edge_map.has(local_k1)) edge_map.set(local_k1, []);
      edge_map.get(local_k1).push(local_k2);
    };

    for (let i = 0; i <= max_row + 1; i++)
      for (let x = 0; x <= width; x++) {
        let cur = isRusArctic(x, i);
        let left = isRusArctic(x - 1, i);
        let up = isRusArctic(x, i - 1);

        if (cur !== up) {
          if (cur) addDirectedEdge(x, i, x + 1, i);
          else addDirectedEdge(x + 1, i, x, i);
        }
        if (cur !== left) {
          if (cur) addDirectedEdge(x, i + 1, x, i);
          else addDirectedEdge(x, i, x, i + 1);
        }
      }

    edge_keys = Array.from(edge_map.keys());
    for (let i = 0; i < edge_keys.length; i++) {
      let start_key = edge_keys[i];
      if (!edge_map.has(start_key)) continue;

      for (let x = 0; x < 32; x++) {
        if (!edge_map.has(start_key)) break;
        let cur_key = start_key;
        let ring = [];

        for (let y = 0; y < 20000; y++) {
          let parts = cur_key.split(",");
          let px = Number(parts[0]);
          let py = Number(parts[1]);
          let lon_val = -180.0 + px*res_x;
          let lon_u = (lon_val < 0) ? lon_val + 360.0 : lon_val;
          ring.push([lon_u, 90.0 - py*res_y]);

          let next_list = edge_map.get(cur_key);
          if (!next_list || next_list.length === 0) break;
          let next_key = next_list.pop();
          if (next_list.length === 0) edge_map.delete(cur_key);
          cur_key = next_key;

          if (cur_key === start_key) {
            let sp = start_key.split(",");
            let slon = -180.0 + Number(sp[0])*res_x;
            ring.push([(slon < 0) ? slon + 360.0 : slon, 90.0 - Number(sp[1])*res_y]);
            break;
          }
        }

        if (ring.length >= 4)
          polygons_out.push({ exterior: ring, holes: [] });
      }
    }

    //Return statement
    return polygons_out;
  };


  /**
   * Computes intersections between a screen-space polyline and a rectangular viewport frame.
   * @alias population_c14bazAAR_maps.findSegmentFrameIntersections
   *
   * @param {Array<number[]>} arg0_polyline - Screen-space [x, y] vertices.
   * @param {Object} arg1_frame - { x0, x1, y0, y1 } viewport bounds.
   *
   * @returns {Array<Object>} Array of { edge, x, y } intersections.
   */
  population_c14bazAAR_maps.findSegmentFrameIntersections = function (arg0_polyline, arg1_frame) {
    //Convert from parameters
    let polyline = arg0_polyline;
    let frame = arg1_frame;

    //Declare local instance variables
    let hits = [];

    for (let i = 0; i < polyline.length - 1; i++) {
      let x0 = polyline[i][0];
      let y0 = polyline[i][1];
      let x1 = polyline[i + 1][0];
      let y1 = polyline[i + 1][1];
      let dx = x1 - x0;
      let dy = y1 - y0;

      if (Math.abs(dx) > 1e-6) {
        let t_left = (frame.x0 - x0)/dx;
        if (t_left >= 0 && t_left <= 1) {
          let yl = y0 + t_left*dy;
          if (yl >= frame.y0 + 14 && yl <= frame.y1 - 14)
            hits.push({ edge: "left", x: frame.x0, y: yl });
        }
        let t_right = (frame.x1 - x0)/dx;
        if (t_right >= 0 && t_right <= 1) {
          let yr = y0 + t_right*dy;
          if (yr >= frame.y0 + 14 && yr <= frame.y1 - 14)
            hits.push({ edge: "right", x: frame.x1, y: yr });
        }
      }

      if (Math.abs(dy) > 1e-6) {
        let t_top = (frame.y0 - y0)/dy;
        if (t_top >= 0 && t_top <= 1) {
          let xt = x0 + t_top*dx;
          if (xt >= frame.x0 + 20 && xt <= frame.x1 - 20)
            hits.push({ edge: "top", x: xt, y: frame.y0 });
        }
        let t_bot = (frame.y1 - y0)/dy;
        if (t_bot >= 0 && t_bot <= 1) {
          let xb = x0 + t_bot*dx;
          if (xb >= frame.x0 + 20 && xb <= frame.x1 - 20)
            hits.push({ edge: "bottom", x: xb, y: frame.y1 });
        }
      }
    }

    //Return statement
    return hits;
  };


  /**
   * Formats an unwrapped longitude (0..360) into standard E/W degree notation.
   * @alias population_c14bazAAR_maps.formatLongitudeLabel
   *
   * @param {number} arg0_lon_unwrapped
   *
   * @returns {string}
   */
  population_c14bazAAR_maps.formatLongitudeLabel = function (arg0_lon_unwrapped) {
    //Convert from parameters
    let lon_u = arg0_lon_unwrapped;

    //Return statement
    if (Math.abs(lon_u - 180) < 1e-6) return "180°";
    else if (lon_u > 180) return `${Math.round(360 - lon_u)}°W`;
    else return `${Math.round(lon_u)}°E`;
  };


  /**
   * Generates conical (Albers Equal-Area Conic) and equirectangular radiocarbon distribution maps
   * over the landmass of Russia excluding the Kaliningrad exclave for 1 AD–1500 AD.
   * @alias population_c14bazAAR_maps.generateRussiaRadiocarbonMaps
   *
   * @param {Object} [arg0_options]
   *
   * @returns {Promise<Object>} Summary report and output image paths.
   */
  population_c14bazAAR_maps.generateRussiaRadiocarbonMaps = async function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let base_dir = options.base_dir || path.resolve(__dirname, "../../..");
    let c14_cls = global.population_c14bazAAR || {};
    let c14_csv_path = options.input_c14_csv || c14_cls.input_c14_csv ||
      path.join(base_dir, "histmap/1.data_raw/population_c14bazAAR/c14_cleaned_dedup.csv");
    let conical_job = null;
    let conical_out_path = "";
    let csv_lines = [];
    let cshapes_path = options.input_cshapes_geojson ||
      path.join(base_dir, "saves/CShapes-2.0.geojson");
    let curve_obj = null;
    let equirect_job = null;
    let equirect_out_path = "";
    let filtered_dates = [];
    let geocodes_path = options.input_geocodes_raster ||
      path.join(base_dir, "histmap/1.data_raw/admin_modern/geocodes.png");
    let geocodes_png = null;
    let header_cols = [];
    let idx_age = -1;
    let idx_country = -1;
    let idx_lab = -1;
    let idx_lat = -1;
    let idx_lon = -1;
    let idx_site = -1;
    let idx_src = -1;
    let idx_std = -1;
    let images_dir = options.output_images_folder || c14_cls.output_images_folder ||
      path.join(base_dir, "histmap/2.data_cleaning/population_c14bazAAR/images");
    let intcal_path = options.input_intcal_json || c14_cls.input_intcal_json ||
      path.join(base_dir, "histmap/2.data_cleaning/population_c14bazAAR/config/intcal20.json");
    let max_year = (options.max_year !== undefined) ? options.max_year : 1500;
    let min_year = (options.min_year !== undefined) ? options.min_year : 1;
    let png_lib = global.pngjs || require("pngjs");
    let polygons_array = [];
    let regional_counts = { european_russia: 0, northern_caucasus: 0, siberia_and_far_east: 0 };
    let total_russia_all_epochs = 0;

    //Guard clauses
    if (!fs.existsSync(c14_csv_path) || !fs.existsSync(intcal_path) || !fs.existsSync(cshapes_path)) {
      console.error("- [population_c14bazAAR_maps.generateRussiaRadiocarbonMaps] Missing required input files.");
      return null;
    }


    if (!fs.existsSync(images_dir))
      fs.mkdirSync(images_dir, { recursive: true });

    if (fs.existsSync(geocodes_path))
      geocodes_png = png_lib.PNG.sync.read(fs.readFileSync(geocodes_path));

    polygons_array = population_c14bazAAR_maps.loadRussiaLandmassPolygons({
      cshapes_path: cshapes_path,
      geocodes_png: geocodes_png
    });
    curve_obj = JSON.parse(fs.readFileSync(intcal_path, "utf8"));

    csv_lines = fs.readFileSync(c14_csv_path, "utf8").split(/\r?\n/);
    header_cols = population_c14bazAAR_maps.parseCSVRow(csv_lines[0]);
    idx_age = header_cols.indexOf("c14age");
    idx_country = header_cols.indexOf("country");
    idx_lab = header_cols.indexOf("labnr");
    idx_lat = header_cols.indexOf("lat");
    idx_lon = header_cols.indexOf("lon");
    idx_site = header_cols.indexOf("site");
    idx_src = header_cols.indexOf("sourcedb");
    idx_std = header_cols.indexOf("c14std");

    for (let i = 1; i < csv_lines.length; i++) {
      let local_line = csv_lines[i];
      if (!local_line) continue;

      let local_cols = population_c14bazAAR_maps.parseCSVRow(local_line);
      let local_lat = parseFloat(local_cols[idx_lat]);
      let local_lon = parseFloat(local_cols[idx_lon]);
      if (isNaN(local_lat) || isNaN(local_lon)) continue;
      if (local_lat < 40.5 || local_lat > 83.0) continue;

      let local_lon_u = (local_lon < 0) ? local_lon + 360.0 : local_lon;
      if (local_lon_u < 26.5 || local_lon_u > 192.0) continue;

      //Strictly exclude Kaliningrad exclave
      if (local_lon_u > 18.0 && local_lon_u < 25.0 && local_lat > 53.0 && local_lat < 56.5)
        continue;

      if (!population_c14bazAAR_maps.isPointInRussiaLandmass(local_lon_u, local_lat, polygons_array, geocodes_png))
        continue;

      total_russia_all_epochs++;

      let local_age = parseFloat(local_cols[idx_age]);
      let local_std = parseFloat(local_cols[idx_std]);
      if (isNaN(local_age) || isNaN(local_std) || local_age > 2600) continue;

      let local_cal = population_c14bazAAR_maps.calibrateIntCal20Record(local_age, local_std, curve_obj);
      if (local_cal.cal_ad >= min_year && local_cal.cal_ad <= max_year) {
        filtered_dates.push({
          c14age: local_age,
          c14std: local_std,
          cal_ad: local_cal.cal_ad,
          country: local_cols[idx_country] || "",
          labnr: local_cols[idx_lab] || "",
          lat: local_lat,
          lon: local_lon,
          lon_u: local_lon_u,
          median_ad: local_cal.median_ad,
          site: local_cols[idx_site] || "",
          sourcedb: local_cols[idx_src] || ""
        });

        if (local_lon_u >= 60.0) {
          regional_counts.siberia_and_far_east++;
        } else if (local_lat < 46.5 && local_lon_u >= 36.5 && local_lon_u <= 50.5) {
          regional_counts.northern_caucasus++;
        } else {
          regional_counts.european_russia++;
        }
      }
    }

    conical_out_path = path.join(images_dir, "c14_russia_1ad_1500ad_conical.png");
    equirect_out_path = path.join(images_dir, "c14_russia_1ad_1500ad_equirectangular.png");

    conical_job = population_c14bazAAR_maps.buildMapRenderPayload("conical", polygons_array, filtered_dates, {
      dot_radius: options.dot_radius || 2.6,
      max_year: max_year,
      min_year: min_year,
      output_path: conical_out_path
    });

    equirect_job = population_c14bazAAR_maps.buildMapRenderPayload("equirectangular", polygons_array, filtered_dates, {
      dot_radius: options.dot_radius || 2.6,
      max_year: max_year,
      min_year: min_year,
      output_path: equirect_out_path
    });

    await population_c14bazAAR_maps.renderPayloadsToPNGs([conical_job, equirect_job], options);

    console.log(`- Saved conical map to ${conical_out_path}`);
    console.log(`- Saved equirectangular map to ${equirect_out_path}`);

    //Return statement
    return {
      conical_path: conical_out_path,
      dates: filtered_dates,
      equirectangular_path: equirect_out_path,
      regional_counts: regional_counts,
      total_dates_1ad_1500ad: filtered_dates.length,
      total_russia_all_epochs: total_russia_all_epochs
    };
  };


  /**
   * Tests whether a point (lon_u, lat) lies inside a single closed polygon ring using ray casting.
   * @alias population_c14bazAAR_maps.isPointInPolygonRing
   *
   * @param {number} arg0_lon_u - Unwrapped longitude.
   * @param {number} arg1_lat - Latitude.
   * @param {Array<number[]>} arg2_ring_array - Array of [lon_u, lat] vertices.
   *
   * @returns {boolean}
   */
  population_c14bazAAR_maps.isPointInPolygonRing = function (arg0_lon_u, arg1_lat, arg2_ring_array) {
    //Convert from parameters
    let lon_u = arg0_lon_u;
    let lat = arg1_lat;
    let ring = arg2_ring_array;

    //Declare local instance variables
    let inside = false;
    let n = ring.length;

    for (let i = 0, x = n - 1; i < n; x = i++) {
      let xi = ring[i][0], yi = ring[i][1];
      let xj = ring[x][0], yj = ring[x][1];
      let intersect = ((yi > lat) !== (yj > lat)) &&
        (lon_u < (xj - xi)*(lat - yi)/((yj - yi) || 1e-12) + xi);
      if (intersect) inside = !inside;
    }

    //Return statement
    return inside;
  };


  /**
   * Checks if (lon_u, lat) falls within the landmass of Russia (excluding Kaliningrad)
   * using vector polygon containment or 5-arcminute admin_modern/geocodes.png RUS cell membership.
   * @alias population_c14bazAAR_maps.isPointInRussiaLandmass
   *
   * @param {number} arg0_lon_u - Unwrapped longitude (0..360).
   * @param {number} arg1_lat - Latitude (-90..90).
   * @param {Array<Object>} arg2_polygons_array - Preloaded Russia polygon objects.
   * @param {Object} [arg3_geocodes_png] - Optional pngjs geocodes raster.
   *
   * @returns {boolean}
   */
  population_c14bazAAR_maps.isPointInRussiaLandmass = function (arg0_lon_u, arg1_lat, arg2_polygons_array, arg3_geocodes_png) {
    //Convert from parameters
    let lon_u = arg0_lon_u;
    let lat = arg1_lat;
    let polygons_array = arg2_polygons_array;
    let geocodes_png = arg3_geocodes_png;

    //Declare local instance variables
    let std_lon = (lon_u > 180.0) ? lon_u - 360.0 : lon_u;

    //Guard clauses
    if (lon_u > 18.0 && lon_u < 25.0 && lat > 53.0 && lat < 56.5) return false;


    for (let i = 0; i < polygons_array.length; i++) {
      let poly = polygons_array[i];
      if (lon_u < poly.bbox[0] || lon_u > poly.bbox[2] || lat < poly.bbox[1] || lat > poly.bbox[3])
        continue;
      if (population_c14bazAAR_maps.isPointInPolygonRing(lon_u, lat, poly.exterior)) {
        let in_hole = false;
        for (let x = 0; x < poly.holes.length; x++)
          if (population_c14bazAAR_maps.isPointInPolygonRing(lon_u, lat, poly.holes[x])) {
            in_hole = true;
            break;
          }
        if (!in_hole) return true;
      }
    }

    if (geocodes_png && geocodes_png.data) {
      let px = Math.min(geocodes_png.width - 1, Math.max(0, Math.floor((std_lon + 180.0)/360.0*geocodes_png.width)));
      let py = Math.min(geocodes_png.height - 1, Math.max(0, Math.floor((90.0 - lat)/180.0*geocodes_png.height)));
      let idx = (py*geocodes_png.width + px)*4;
      if (geocodes_png.data[idx] === 20 && geocodes_png.data[idx + 1] === 114 && geocodes_png.data[idx + 2] === 30)
        return true;
    }

    //Return statement
    return false;
  };


  /**
   * Loads modern Russian Federation vector landmass polygons from CShapes-2.0.geojson,
   * strips the Kaliningrad exclave, unwraps eastern Chukotka/Wrangel across 180°,
   * densifies long edges for smooth conic projection, and appends Severnaya Zemlya from geocodes.png.
   * @alias population_c14bazAAR_maps.loadRussiaLandmassPolygons
   *
   * @param {Object} arg0_options
   *
   * @returns {Array<Object>} Array of { bbox, exterior, holes } polygon objects.
   */
  population_c14bazAAR_maps.loadRussiaLandmassPolygons = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let arctic_polys = [];
    let cshapes_obj = JSON.parse(fs.readFileSync(options.cshapes_path, "utf8"));
    let features = cshapes_obj.features || [];
    let polygons_out = [];
    let rus_feature = null;

    for (let i = 0; i < features.length; i++) {
      let props = features[i].properties || {};
      if (props.gwcode === 365 && props.gweyear === 2014) {
        rus_feature = features[i];
        break;
      }
    }

    if (!rus_feature)
      for (let i = 0; i < features.length; i++) {
        let props = features[i].properties || {};
        if (props.gwcode === 365 && props.gweyear >= 2014) {
          rus_feature = features[i];
          break;
        }
      }

    let densifyAndUnwrapRing = function (arg0_raw_ring) {
      let raw_ring = arg0_raw_ring;
      let out_ring = [];

      for (let i = 0; i < raw_ring.length; i++) {
        let lon0 = (raw_ring[i][0] < 0) ? raw_ring[i][0] + 360.0 : raw_ring[i][0];
        let lat0 = raw_ring[i][1];
        out_ring.push([lon0, lat0]);

        if (i < raw_ring.length - 1) {
          let lon1 = (raw_ring[i + 1][0] < 0) ? raw_ring[i + 1][0] + 360.0 : raw_ring[i + 1][0];
          let lat1 = raw_ring[i + 1][1];
          let d_lon = lon1 - lon0;
          let d_lat = lat1 - lat0;
          let steps = Math.ceil(Math.max(Math.abs(d_lon), Math.abs(d_lat))/0.30);
          if (steps > 1 && steps < 200)
            for (let x = 1; x < steps; x++) {
              let f = x/steps;
              out_ring.push([lon0 + d_lon*f, lat0 + d_lat*f]);
            }
        }
      }
      return out_ring;
    };

    let computeBBox = function (arg0_ring) {
      let min_x = Infinity, min_y = Infinity, max_x = -Infinity, max_y = -Infinity;
      for (let i = 0; i < arg0_ring.length; i++) {
        min_x = Math.min(min_x, arg0_ring[i][0]);
        max_x = Math.max(max_x, arg0_ring[i][0]);
        min_y = Math.min(min_y, arg0_ring[i][1]);
        max_y = Math.max(max_y, arg0_ring[i][1]);
      }
      return [min_x, min_y, max_x, max_y];
    };

    if (rus_feature && rus_feature.geometry) {
      let raw_polys = (rus_feature.geometry.type === "MultiPolygon") ?
        rus_feature.geometry.coordinates : [rus_feature.geometry.coordinates];

      for (let i = 0; i < raw_polys.length; i++) {
        let poly_rings = raw_polys[i];
        if (!poly_rings || poly_rings.length === 0) continue;

        let ext = densifyAndUnwrapRing(poly_rings[0]);
        let bbox = computeBBox(ext);

        //Exclude Kaliningrad exclave polygons (19,6°E–22,9°E, 54,3°N–55,3°N)
        if (bbox[0] > 18.0 && bbox[2] < 25.0 && bbox[1] > 53.0 && bbox[3] < 56.5)
          continue;

        let holes = [];
        for (let x = 1; x < poly_rings.length; x++)
          holes.push(densifyAndUnwrapRing(poly_rings[x]));

        polygons_out.push({ bbox: bbox, exterior: ext, holes: holes });
      }
    }

    if (options.geocodes_png) {
      arctic_polys = population_c14bazAAR_maps.extractArcticRasterPolygons(options.geocodes_png, 77.74);
      for (let i = 0; i < arctic_polys.length; i++) {
        let ext = densifyAndUnwrapRing(arctic_polys[i].exterior);
        polygons_out.push({
          bbox: computeBBox(ext),
          exterior: ext,
          holes: []
        });
      }
    }

    //Return statement
    return polygons_out;
  };


  /**
   * Parses a single CSV line handling double-quoted fields containing commas.
   * @alias population_c14bazAAR_maps.parseCSVRow
   *
   * @param {string} arg0_line_str
   *
   * @returns {Array<string>}
   */
  population_c14bazAAR_maps.parseCSVRow = function (arg0_line_str) {
    //Convert from parameters
    let line_str = arg0_line_str || "";

    //Declare local instance variables
    let cur = "";
    let fields = [];
    let in_quotes = false;

    for (let i = 0; i < line_str.length; i++) {
      let ch = line_str[i];
      if (ch === "\"") {
        if (in_quotes && line_str[i + 1] === "\"") {
          cur += "\"";
          i++;
        } else {
          in_quotes = !in_quotes;
        }
      } else if (ch === "," && !in_quotes) {
        fields.push(cur);
        cur = "";
      } else {
        cur += ch;
      }
    }
    fields.push(cur);

    //Return statement
    return fields;
  };


  /**
   * Executes 2D Canvas drawing instructions for a prepared map render payload.
   * Designed to execute identically in Electron/Vercengen DOM or headless Chromium.
   * @alias population_c14bazAAR_maps.renderCanvasJob
   *
   * @param {HTMLCanvasElement} arg0_canvas
   * @param {Object} arg1_job
   */
  population_c14bazAAR_maps.renderCanvasJob = function (arg0_canvas, arg1_job) {
    //Convert from parameters
    let canvas = arg0_canvas;
    let job = arg1_job;

    //Declare local instance variables
    let bar_h = 16;
    let bar_w = 860;
    let bar_x = 0;
    let bar_y = 0;
    let ctx = canvas.getContext("2d");
    let f = job.frame;
    let font_stack = "'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif";
    let grad = null;

    canvas.width = job.canvas_width;
    canvas.height = job.canvas_height;

    //1. Outer canvas & map viewport background
    ctx.fillStyle = "#0b1017";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = "#101823";
    ctx.fillRect(f.x0, f.y0, f.x1 - f.x0, f.y1 - f.y0);

    //2. Clip to map viewport and render Russia landmass (excl. Kaliningrad)
    ctx.save();
    ctx.beginPath();
    ctx.rect(f.x0, f.y0, f.x1 - f.x0, f.y1 - f.y0);
    ctx.clip();

    ctx.fillStyle = "#243040";
    for (let i = 0; i < job.polygons.length; i++) {
      let poly = job.polygons[i];
      ctx.beginPath();
      for (let x = 0; x < poly.exterior.length; x++) {
        if (x === 0) ctx.moveTo(poly.exterior[x][0], poly.exterior[x][1]);
        else ctx.lineTo(poly.exterior[x][0], poly.exterior[x][1]);
      }
      ctx.closePath();

      for (let x = 0; x < poly.holes.length; x++) {
        let h = poly.holes[x];
        for (let y = 0; y < h.length; y++) {
          if (y === 0) ctx.moveTo(h[y][0], h[y][1]);
          else ctx.lineTo(h[y][0], h[y][1]);
        }
        ctx.closePath();
      }
      ctx.fill("evenodd");
    }

    //Seal sub-pixel antialiasing along 180° Chukotka/Wrangel seam before stroking true coastline
    ctx.strokeStyle = "#243040";
    ctx.lineWidth = 0.7;
    for (let i = 0; i < job.polygons.length; i++) {
      let ext = job.polygons[i].exterior;
      ctx.beginPath();
      for (let x = 0; x < ext.length; x++) {
        if (x === 0) ctx.moveTo(ext[x][0], ext[x][1]);
        else ctx.lineTo(ext[x][0], ext[x][1]);
      }
      ctx.stroke();
    }

    ctx.strokeStyle = "#5c7490";
    ctx.lineWidth = 1.05;
    ctx.lineJoin = "round";
    ctx.beginPath();
    for (let i = 0; i < job.polygons.length; i++) {
      let segs = job.polygons[i].stroke_segments;
      for (let x = 0; x < segs.length; x++) {
        ctx.moveTo(segs[x][0][0], segs[x][0][1]);
        ctx.lineTo(segs[x][1][0], segs[x][1][1]);
      }
    }
    ctx.stroke();

    //3. Translucent graticules overlaid across ocean and landmass
    ctx.strokeStyle = "rgba(218, 234, 250, 0.24)";
    ctx.lineWidth = 1.0;
    for (let i = 0; i < job.graticule_lines.length; i++) {
      let pts = job.graticule_lines[i];
      ctx.beginPath();
      for (let x = 0; x < pts.length; x++) {
        if (x === 0) ctx.moveTo(pts[x][0], pts[x][1]);
        else ctx.lineTo(pts[x][0], pts[x][1]);
      }
      ctx.stroke();
    }

    //4. Small Spectral-coloured radiocarbon dots
    for (let i = 0; i < job.dots.length; i++) {
      let d = job.dots[i];
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.radius + 0.55, 0, Math.PI*2.0);
      ctx.fillStyle = "rgba(7, 10, 15, 0.88)";
      ctx.fill();

      ctx.beginPath();
      ctx.arc(d.x, d.y, d.radius, 0, Math.PI*2.0);
      ctx.fillStyle = d.colour;
      ctx.fill();
    }

    //Interior parallel labels (conical mode)
    ctx.font = `500 13px ${font_stack}`;
    for (let i = 0; i < job.graticule_labels.length; i++) {
      let lbl = job.graticule_labels[i];
      if (lbl.edge !== "interior") continue;
      ctx.textAlign = lbl.align;
      ctx.textBaseline = lbl.baseline;
      ctx.lineWidth = 3.0;
      ctx.strokeStyle = "rgba(16, 24, 35, 0.85)";
      ctx.strokeText(lbl.text, lbl.x, lbl.y);
      ctx.fillStyle = "rgba(198, 218, 238, 0.72)";
      ctx.fillText(lbl.text, lbl.x, lbl.y);
    }

    ctx.restore();

    //5. Map viewport border & exterior graticule ticks/labels
    ctx.strokeStyle = "#3b4d63";
    ctx.lineWidth = 1.4;
    ctx.strokeRect(f.x0, f.y0, f.x1 - f.x0, f.y1 - f.y0);

    ctx.font = `500 14px ${font_stack}`;
    ctx.fillStyle = "#9fb3c8";
    ctx.strokeStyle = "#52667d";
    ctx.lineWidth = 1.1;

    for (let i = 0; i < job.graticule_labels.length; i++) {
      let lbl = job.graticule_labels[i];
      if (lbl.edge === "interior") continue;

      ctx.beginPath();
      if (lbl.edge === "left") {
        ctx.moveTo(f.x0 - 5, lbl.y);
        ctx.lineTo(f.x0, lbl.y);
      } else if (lbl.edge === "right") {
        ctx.moveTo(f.x1, lbl.y);
        ctx.lineTo(f.x1 + 5, lbl.y);
      } else if (lbl.edge === "top") {
        ctx.moveTo(lbl.x, f.y0 - 5);
        ctx.lineTo(lbl.x, f.y0);
      } else if (lbl.edge === "bottom") {
        ctx.moveTo(lbl.x, f.y1);
        ctx.lineTo(lbl.x, f.y1 + 5);
      }
      ctx.stroke();

      ctx.textAlign = lbl.align;
      ctx.textBaseline = lbl.baseline;
      ctx.fillText(lbl.text, lbl.x, lbl.y);
    }

    //6. Title & subtitle header
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillStyle = "#eef4fa";
    ctx.font = `600 24px ${font_stack}`;
    ctx.fillText(job.title, f.x0, 24);

    ctx.fillStyle = "#96acc2";
    ctx.font = `400 15px ${font_stack}`;
    ctx.fillText(job.subtitle, f.x0, 58);

    //7. Horizontal Spectral colourbar legend in footer
    bar_x = Math.round(0.5*(canvas.width - bar_w));
    bar_y = f.y1 + ((job.projection_mode === "equirectangular") ? 52 : 56);

    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#cbd9e8";
    ctx.font = `600 14px ${font_stack}`;
    ctx.fillText("Calibrated Date (Spectral):", bar_x - 18, bar_y + 0.5*bar_h);

    grad = ctx.createLinearGradient(bar_x, 0, bar_x + bar_w, 0);
    for (let i = 0; i < job.legend.stops.length; i++)
      grad.addColorStop(job.legend.stops[i].offset, job.legend.stops[i].colour);

    ctx.fillStyle = grad;
    ctx.fillRect(bar_x, bar_y, bar_w, bar_h);
    ctx.strokeStyle = "#627892";
    ctx.lineWidth = 1.0;
    ctx.strokeRect(bar_x, bar_y, bar_w, bar_h);

    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.font = `500 13px ${font_stack}`;
    for (let i = 0; i < job.legend.ticks.length; i++) {
      let yr = job.legend.ticks[i];
      let t = (yr - job.legend.min_year)/(job.legend.max_year - job.legend.min_year);
      let tx = bar_x + t*bar_w;

      ctx.beginPath();
      ctx.moveTo(tx, bar_y + bar_h);
      ctx.lineTo(tx, bar_y + bar_h + 5);
      ctx.strokeStyle = "#8aa1b8";
      ctx.stroke();

      ctx.fillStyle = "#b8cadc";
      ctx.fillText(`${yr} AD`, tx, bar_y + bar_h + 8);
    }
  };


  /**
   * Renders one or more prepared map payloads to disk as PNG files,
   * executing directly on HTMLCanvasElement when in Vercengen/Electron or via headless Chromium in CLI Node.js.
   * @alias population_c14bazAAR_maps.renderPayloadsToPNGs
   *
   * @param {Array<Object>} arg0_render_jobs_array
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<void>}
   */
  population_c14bazAAR_maps.renderPayloadsToPNGs = async function (arg0_render_jobs_array, arg1_options) {
    //Convert from parameters
    let render_jobs = (arg0_render_jobs_array) ? arg0_render_jobs_array : [];
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let browser = null;
    let browser_candidates = [
      options.browser_executable_path,
      "C:/Program Files/Google/Chrome/Application/chrome.exe",
      "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
      "C:/Program Files/Microsoft/Edge/Application/msedge.exe"
    ];
    let exec_path = null;
    let fn_source = population_c14bazAAR_maps.renderCanvasJob.toString();
    let launch_opts = { args: ["--no-sandbox", "--disable-gpu"], headless: true };
    let page = null;
    let pptr = null;

    //Guard clauses
    if (render_jobs.length === 0) return;

    if (typeof document !== "undefined" && typeof document.createElement === "function") {
      for (let i = 0; i < render_jobs.length; i++) {
        let local_canvas = document.createElement("canvas");
        population_c14bazAAR_maps.renderCanvasJob(local_canvas, render_jobs[i]);
        let local_b64 = local_canvas.toDataURL("image/png").replace(/^data:image\/png;base64,/, "");
        fs.writeFileSync(render_jobs[i].output_path, Buffer.from(local_b64, "base64"));
      }
      return;
    }


    for (let i = 0; i < browser_candidates.length; i++)
      if (browser_candidates[i] && fs.existsSync(browser_candidates[i])) {
        exec_path = browser_candidates[i];
        break;
      }
    if (exec_path) launch_opts.executablePath = exec_path;

    pptr = global.puppeteer || require("puppeteer");
    browser = await pptr.launch(launch_opts);
    try {
      page = await browser.newPage();
      await page.setContent("<!DOCTYPE html><html><body style='margin:0;background:#000;'><canvas id='c'></canvas></body></html>");

      for (let i = 0; i < render_jobs.length; i++) {
        let b64_png = await page.evaluate(function (arg0_fn_src, arg1_job_data) {
          let canvas_el = document.getElementById("c");
          let draw_fn = new Function("return (" + arg0_fn_src + ");")();
          draw_fn(canvas_el, arg1_job_data);
          return canvas_el.toDataURL("image/png").replace(/^data:image\/png;base64,/, "");
        }, fn_source, render_jobs[i]);

        fs.writeFileSync(render_jobs[i].output_path, Buffer.from(b64_png, "base64"));
      }
    } finally {
      await browser.close();
    }
  };


  /**
   * Samples the 11-stop ColorBrewer Spectral palette at normalised position t in [0, 1],
   * delegating to {@link Colour.samplePalette} when UF/Colour is loaded.
   * @alias population_c14bazAAR_maps.sampleSpectralColour
   *
   * @param {number} arg0_t - Normalised value in [0, 1].
   *
   * @returns {number[]} [R, G, B] integer components.
   */
  population_c14bazAAR_maps.sampleSpectralColour = function (arg0_t) {
    //Convert from parameters
    let t = arg0_t;

    //Declare local instance variables
    let fallback_stops = [
      [158, 1, 66],
      [213, 62, 79],
      [244, 109, 67],
      [253, 174, 97],
      [254, 224, 139],
      [255, 255, 191],
      [230, 245, 152],
      [171, 221, 164],
      [102, 194, 165],
      [50, 136, 189],
      [94, 79, 162]
    ];
    let frac = 0;
    let hi = 0;
    let lo = 0;
    let pos = 0;
    let tc = Math.min(1, Math.max(0, Number(t) || 0));

    //Guard clauses
    if (global.Colour && typeof Colour.samplePalette === "function")
      return Colour.samplePalette("spectral", tc);


    pos = tc*(fallback_stops.length - 1);
    lo = Math.floor(pos);
    hi = Math.min(fallback_stops.length - 1, lo + 1);
    frac = pos - lo;

    //Return statement
    return [
      Math.round(fallback_stops[lo][0] + (fallback_stops[hi][0] - fallback_stops[lo][0])*frac),
      Math.round(fallback_stops[lo][1] + (fallback_stops[hi][1] - fallback_stops[lo][1])*frac),
      Math.round(fallback_stops[lo][2] + (fallback_stops[hi][2] - fallback_stops[lo][2])*frac)
    ];
  };
}
