if (!global.naissance) global.naissance = {};

naissance.BrushNodeEditor = class extends ve.Class {
  constructor () {
    super();

    //Declare local instance variables
    this.coords = [];
    this.enabled = false;
    this.mode = "Polygon";
    this.type = "add";

    this._click_listener = (e) => { this.onclick(e); };
    this._dblclick_listener = (e) => { this.ondblclick(e); };
    this._mousemove_listener = (e) => { this.onmousemove(e); };
  }

  /**
   * Appends a coordinate node to the active editing path.
   *
   * @param {maptalks.Coordinate} arg0_coord - The coordinate to append.
   */
  addNode (arg0_coord) {
    //Convert from parameters
    let coord = arg0_coord;

    //Function body
    this.coords.push(coord);
    this.draw();
  }

  /**
   * Disables the node editor and clears map listeners and preview geometries.
   */
  disable () {
    this.enabled = false;
    this.coords = [];

    if (this.geometry) {
      this.geometry.remove();
      this.geometry = null;
    }

    map.off("click", this._click_listener);
    map.off("dblclick", this._dblclick_listener);
    map.off("mousemove", this._mousemove_listener);
  }

  /**
   * Draws the active preview polygon or line string on the cursor layer.
   *
   * @param {maptalks.Coordinate} [arg0_temp_coord] - Optional preview coordinate under the cursor.
   */
  draw (arg0_temp_coord) {
    //Convert from parameters
    let temp_coord = arg0_temp_coord;

    //Declare local instance variables
    let current_mode = "Polygon";
    let draw_coords = [...this.coords];
    let fill_color = (this.type === "remove") ? "rgba(240, 60, 60, 0.5)" : "rgba(255, 255, 255, 0.5)";
    let stroke_color = (this.type === "remove") ? "rgba(240, 60, 60, 1)" : "rgba(255, 255, 255, 1)";

    //Guard clause
    if (this.geometry) this.geometry.remove();
    if (temp_coord) draw_coords.push(temp_coord);
    if (draw_coords.length < 2) return;

    //Function body
    if (this.mode === "LineString" || this.mode === "FreeHandLineString")
      current_mode = "LineString";

    this.geometry = new maptalks[current_mode](draw_coords, {
      symbol: {
        polygonFill: fill_color,
        lineColor: stroke_color,
        lineWidth: 2
      }
    });

    this.geometry.addTo(main.layers.cursor_layer);
  }

  /**
   * Enables the node editor and registers event listeners on the map.
   */
  enable () {
    this.disable();
    this.enabled = true;
    this.type = "add";

    map_component.on("click", this._click_listener);
    map_component.on("dblclick", this._dblclick_listener);
    map_component.on("mousemove", this._mousemove_listener);
  }

  /**
   * Flattens nested coordinate structures from Polygon, MultiPolygon, LineString, or arrays into linear rings.
   *
   * @param {Array} arg0_coords - Nested coordinate array.
   *
   * @returns {Array<Array<maptalks.Coordinate|Array<number>>>}
   */
  static flattenCoordinates (arg0_coords) {
    //Convert from parameters
    let coords = arg0_coords;

    //Guard clause
    if (!Array.isArray(coords) || coords.length === 0) return [];

    if (coords[0] && (coords[0].x !== undefined || typeof coords[0][0] === "number"))
      return [coords];

    //Declare local instance variables
    let rings = [];

    //Function body
    for (let i = 0; i < coords.length; i++) {
      let sub = naissance.BrushNodeEditor.flattenCoordinates(coords[i]);

      for (let x = 0; x < sub.length; x++) rings.push(sub[x]);
    }

    //Return statement
    return rings;
  }

  /**
   * Handles map click events to place nodes.
   *
   * @param {Object} arg0_e - Map click event.
   */
  onclick (arg0_e) {
    //Convert from parameters
    let e = arg0_e;

    //Declare local instance variables
    let is_line = ["FreeHandLineString", "LineString"].includes(this.mode);
    let is_node_brush = ["node", "node_override", "node_transfer"].includes(main.brush.mode);

    //Guard clause
    if (is_line && HTML.ctrl_pressed) return; //Remove isn't valid for GeometryLine

    if (this.coords.length === 0) {
      if (is_line && !is_node_brush && main.brush._selected_geometry?.isOpen("instance"))
        return;

      this.disable();
      this.enable();
      this.type = (HTML.ctrl_pressed) ? "remove" : "add";
    }

    this.addNode(e.coordinate);
  }

  /**
   * Handles map double click events to finish drawing the node path.
   *
   * @param {Object} arg0_e - Map double click event.
   */
  async ondblclick (arg0_e) {
    //Convert from parameters
    let e = arg0_e;

    //Guard clause
    if (this.coords.length < 2) return;

    //Declare local instance variables
    let selected_geometry = main.brush._selected_geometry;

    if (selected_geometry) {
      let layer_obj = selected_geometry.getLayer();

      if (layer_obj?._type === "provinces") {
        this.disable();
        this.enable();
        return;
      }

      if (naissance[selected_geometry.class_name]?.handleNodeEditorEnd)
        await naissance[selected_geometry.class_name].handleNodeEditorEnd.call(selected_geometry, { geometry: this.geometry });
    }

    this.disable();
    this.enable();
  }

  /**
   * Handles map mousemove events to preview drawn nodes.
   *
   * @param {Object} arg0_e - Map mousemove event.
   */
  onmousemove (arg0_e) {
    //Convert from parameters
    let e = arg0_e;

    //Function body
    if (this.coords.length === 0) return;
    this.draw(e.coordinate);
  }

  /**
   * Cleans and heals topology of a Turf geometry, resolving self-intersections and degenerate rings.
   *
   * @param {Object} arg0_turf_geometry - Turf GeoJSON feature or geometry.
   *
   * @returns {Object} Healed Turf GeoJSON feature.
   */
  static healTopology (arg0_turf_geometry) {
    //Convert from parameters
    let turf_geometry = arg0_turf_geometry;

    //Guard clause
    if (!turf_geometry) return null;

    //Function body
    try {
      let truncated = turf.truncate(turf_geometry, { precision: 6, coordinates: 2, mutate: false });
      let clean = turf.buffer(truncated, 0);
      if (clean && clean.geometry) return clean;
    } catch (e) {}

    //Return statement
    return turf_geometry;
  }


  /**
   * Automatically snaps and resolves a Turf polygon against adjacent polities in the same layer.
   * Uses exact boolean differences rather than vertex warping to guarantee clean, non-degenerate topology.
   *
   * @param {Object} arg0_turf_geometry - Turf GeoJSON feature or geometry to snap.
   * @param {Array<naissance.Geometry>} arg1_layer_geometries - Array of candidate polities in the layer.
   * @param {number} [arg2_tolerance_km] - Optional snap distance in kilometres.
   *
   * @returns {Object} Snapped Turf GeoJSON feature.
   */
  static snapPolygonToLayer (arg0_turf_geometry, arg1_layer_geometries, arg2_tolerance_km) {
    //Convert from parameters
    let turf_geometry = arg0_turf_geometry;
    let layer_geometries = (arg1_layer_geometries) ? arg1_layer_geometries : [];
    let tolerance_km = (arg2_tolerance_km !== undefined) ? arg2_tolerance_km : undefined;

    //Guard clause
    if (!turf_geometry || layer_geometries.length === 0)
      return turf_geometry;

    //Declare local instance variables
    let healed = naissance.BrushNodeEditor.healTopology(turf_geometry);
    let resolved = healed;
    let snap_buffer_km = tolerance_km;

    if (snap_buffer_km === undefined) {
      let screen_res = (typeof map !== "undefined" && typeof map.getResolution === "function") ? map.getResolution() : 0.001;
      snap_buffer_km = Math.max(0.01, screen_res * 10 * 111.32);
    }

    //Function body
    for (let i = 0; i < layer_geometries.length; i++) {
      let cand = layer_geometries[i];
      let cand_maptalks = cand.geometry;

      if (!cand_maptalks && typeof cand.getGeometryKeyframeAtDate === "function") {
        let kf_json = cand.getGeometryKeyframeAtDate(main.date);
        if (kf_json && maptalks.Geometry?.fromJSON)
          cand_maptalks = maptalks.Geometry.fromJSON(kf_json);
        else if (kf_json)
          cand_maptalks = kf_json;
      }
      if (!cand_maptalks && cand.value?.[0])
        cand_maptalks = (maptalks.Geometry?.fromJSON) ? maptalks.Geometry.fromJSON(cand.value[0]) : cand.value[0];

      if (!cand_maptalks) continue;
      let cand_turf = (cand_maptalks.type) ? cand_maptalks : Geospatiale.convertMaptalksToTurf(cand_maptalks);
      if (!cand_turf) continue;

      cand_turf = naissance.BrushNodeEditor.healTopology(cand_turf);

      try {
        let is_overlapping = false;
        let is_nearby = false;

        let inter = turf.intersect(turf.featureCollection([resolved, cand_turf]));
        if (inter && turf.area(inter) > 0.1) is_overlapping = true;

        if (!is_overlapping) {
          let test_buf = turf.buffer(resolved, snap_buffer_km, { units: "kilometers" });
          if (test_buf) {
            let near_inter = turf.intersect(turf.featureCollection([test_buf, cand_turf]));
            if (near_inter && turf.area(near_inter) > 0.1) {
              is_nearby = true;
              resolved = test_buf;
            }
          }
        }

        if (is_overlapping || is_nearby) {
          let diff = turf.difference(turf.featureCollection([resolved, cand_turf]));
          if (diff) {
            if (diff.geometry?.type === "GeometryCollection") {
              let poly_geoms = diff.geometry.geometries.filter(g => g.type === "Polygon" || g.type === "MultiPolygon");
              if (poly_geoms.length === 1) diff = turf.feature(poly_geoms[0]);
              else if (poly_geoms.length > 1) diff = turf.multiPolygon(poly_geoms.flatMap(g => (g.type === "Polygon") ? [g.coordinates] : g.coordinates));
            }
            if (diff) resolved = diff;
          }
        }
      } catch (diff_err) {}
    }

    //Return statement
    return (resolved) ? resolved : turf_geometry;
  }

  /**
   * Updates node editor state based on currently selected geometry and brush mode.
   */
  update () {
    //Declare local instance variables
    let is_node_brush = ["node", "node_override", "node_transfer"].includes(main.brush.mode);
    let selected_geometry = main.brush._selected_geometry;

    //Function body
    if (selected_geometry) {
      let is_geometry_line = selected_geometry instanceof naissance.GeometryLine;

      if (is_node_brush || is_geometry_line) {
        this.mode = (is_geometry_line) ? "LineString" : (selected_geometry.node_editor_mode || "Polygon");
        this.enable();
      } else {
        this.disable();
      }
    } else {
      this.disable();
    }
  }
};


naissance.GeometryLine.handleNodeEditorEnd = function (arg0_e) {
  //Convert from parameters
  let e = arg0_e;

  //Function body
  if (main.brush.node_editor.type === "add") {
    e.geometry = main.brush.getAddLine(e.geometry);
    DALS.Timeline.parseAction("add_to_line", [{
      geometry_obj: this.id,
      add_to_line: { geometry: e.geometry.toJSON() }
    }]);
  }

  main.brush.node_editor.disable();
  main.brush.node_editor.enable();
};


/**
 * Finishes node editing for a Polygon geometry, processing node, node_override, and node_transfer operations.
 * Automatically snaps and resolves against other polities in the same layer.
 *
 * @param {Object} arg0_e - End event containing the drawn maptalks geometry.
 */
naissance.GeometryPolygon.handleNodeEditorEnd = async function (arg0_e) {
  //Convert from parameters
  let e = arg0_e;

  //Declare local instance variables
  let candidate_geometries = [];
  let current_layer = this.getLayer();
  let cursor_turf_geometry = (e.geometry) ? Geospatiale.convertMaptalksToTurf(e.geometry) : null;
  let date_range = main.interfaces.edit_brush_keyframes.getDateRange();

  let getTurfGeometry = function (arg_geom) {
    if (!arg_geom) return null;
    let m_geom = arg_geom.geometry;
    if (!m_geom && typeof arg_geom.getGeometryKeyframeAtDate === "function") {
      let kf_json = arg_geom.getGeometryKeyframeAtDate(main.date);
      if (kf_json && maptalks.Geometry?.fromJSON)
        m_geom = maptalks.Geometry.fromJSON(kf_json);
      else if (kf_json)
        return Geospatiale.convertMaptalksToTurf(kf_json);
    }
    if (!m_geom && arg_geom.value?.[0]) {
      if (maptalks.Geometry?.fromJSON)
        m_geom = maptalks.Geometry.fromJSON(arg_geom.value[0]);
      else
        return Geospatiale.convertMaptalksToTurf(arg_geom.value[0]);
    }
    return (m_geom) ? Geospatiale.convertMaptalksToTurf(m_geom) : null;
  };

  //Guard clause
  if (!cursor_turf_geometry) return;

  //Heal topology of drawn selection to eliminate self-intersections and bowties
  cursor_turf_geometry = naissance.BrushNodeEditor.healTopology(cursor_turf_geometry);
  if (!cursor_turf_geometry) return;

  //Collect other polities in the same layer
  if (current_layer && typeof current_layer.getAllGeometries === "function") {
    candidate_geometries = current_layer.getAllGeometries().filter(g => g.id !== this.id);
  } else {
    candidate_geometries = Object.values(naissance.Geometry?.instances || {}).filter(
      g => g.id !== this.id && g instanceof naissance.GeometryPolygon
    );
  }

  //1. Transfer handler (Node Transfer)
  if (main.brush.mode === "node_transfer") {
    try {
      let from_geometry_id = main.brush.from_geometry_id;

      if (!from_geometry_id && main.brush.brush_options?.from_geometry)
        from_geometry_id = main.brush.brush_options.from_geometry.v;
      if (!from_geometry_id && main.brush.brush_options?.components_obj?.from_geometry)
        from_geometry_id = main.brush.brush_options.components_obj.from_geometry.v;

      let from_geometry = (from_geometry_id) ?
        (naissance.Geometry.instances[from_geometry_id] || naissance.Feature?.instances?.[from_geometry_id]) : null;

      if (!from_geometry && from_geometry_id) {
        let norm_id = String(from_geometry_id).replace(/\s+/g, "").toLowerCase();

        Object.iterate(naissance.Geometry.instances, (local_id, local_geom) => {
          let geom_id = String(local_id).replace(/\s+/g, "").toLowerCase();
          let geom_name = (local_geom.name) ? String(local_geom.name).replace(/\s+/g, "").toLowerCase() : "";

          if (geom_name === norm_id || geom_id === norm_id) {
            from_geometry = local_geom;
            from_geometry_id = local_id;
          }
        });

        if (!from_geometry && naissance.Feature?.instances) {
          Object.iterate(naissance.Feature.instances, (local_id, local_feat) => {
            let feat_id = String(local_id).replace(/\s+/g, "").toLowerCase();
            let feat_name = (local_feat.name) ? String(local_feat.name).replace(/\s+/g, "").toLowerCase() : "";

            if (feat_name === norm_id || feat_id === norm_id) {
              from_geometry = local_feat;
              from_geometry_id = local_id;
            }
          });
        }
      }

      //If from_geometry is a Feature, resolve its sub-geometry
      if (from_geometry && from_geometry instanceof naissance.Feature) {
        let sub_geoms = (typeof from_geometry.getAllGeometries === "function") ?
          from_geometry.getAllGeometries() : (from_geometry.entities || []);

        for (let i = 0; i < sub_geoms.length; i++) {
          if (sub_geoms[i] instanceof naissance.GeometryPolygon || sub_geoms[i] instanceof naissance.GeometryLine) {
            from_geometry = sub_geoms[i];
            from_geometry_id = sub_geoms[i].id;
            break;
          }
        }
      }

      //Auto-detect from_geometry from intersecting polities in the same layer if not set
      if (!from_geometry) {
        let best_area = 0;
        let best_candidate;

        for (let i = 0; i < candidate_geometries.length; i++) {
          let cand = candidate_geometries[i];
          let cand_turf = getTurfGeometry(cand);

          if (cand_turf) {
            try {
              let cand_inter = turf.intersect(turf.featureCollection([cand_turf, cursor_turf_geometry]));

              if (cand_inter) {
                let area = turf.area(cand_inter);
                if (area > best_area) {
                  best_area = area;
                  best_candidate = cand;
                }
              }
            } catch (cand_err) {}
          }
        }

        if (best_candidate) {
          from_geometry = best_candidate;
          from_geometry_id = best_candidate.id;
          main.brush.from_geometry_id = best_candidate.id;
          if (main.brush.brush_options?.from_geometry)
            main.brush.brush_options.from_geometry.v = best_candidate.id;
        }
      }

      if (from_geometry) main.brush.from_geometry_id = from_geometry.id;

      if (!from_geometry) {
        veToast("<icon>warning</icon> No source geometry selected or detected for node transfer.");
        return;
      }
      if (from_geometry.id === this.id) {
        veToast("<icon>warning</icon> Cannot transfer nodes to the same geometry.");
        return;
      }

      //Ensure history is loaded
      if (typeof from_geometry.loadHistory === "function")
        await from_geometry.loadHistory();
      if (typeof this.loadHistory === "function")
        await this.loadHistory();

      if (!from_geometry.geometry && typeof from_geometry.draw === "function") from_geometry.draw();
      if (!this.geometry && typeof this.draw === "function") this.draw();

      let source_geom = (main.brush.node_editor.type === "add") ? from_geometry : this;
      let target_geom = (main.brush.node_editor.type === "add") ? this : from_geometry;

      let source_turf = getTurfGeometry(source_geom);
      let target_turf = getTurfGeometry(target_geom);

      if (!source_turf) {
        veToast("<icon>warning</icon> Source geometry has no spatial coordinates at current date.");
        return;
      }

      source_turf = naissance.BrushNodeEditor.healTopology(source_turf);

      let raw_intersection = null;
      try {
        raw_intersection = turf.intersect(turf.featureCollection([source_turf, cursor_turf_geometry]));
      } catch (e) {}

      //If no direct overlap, test small screen-pixel tolerance buffer in case user drew slightly off the boundary
      if (!raw_intersection || (raw_intersection && turf.area(raw_intersection) < 1.0)) {
        let screen_res = (typeof map !== "undefined" && typeof map.getResolution === "function") ? map.getResolution() : 0.001;
        let snap_buffer_km = Math.max(0.1, screen_res * 12 * 111.32);
        try {
          let buffered_cursor = turf.buffer(cursor_turf_geometry, snap_buffer_km, { units: "kilometers" });
          if (buffered_cursor) {
            let test_inter = turf.intersect(turf.featureCollection([source_turf, buffered_cursor]));
            if (test_inter && turf.area(test_inter) > 1.0)
              raw_intersection = test_inter;
          }
        } catch (buf_e) {}
      }

      if (!raw_intersection) {
        veToast("<icon>info</icon> No overlapping geometry found to transfer.");
        return;
      }

      //Clean up GeometryCollection if points/lines mixed in
      let turf_intersection = raw_intersection;
      if (raw_intersection.geometry?.type === "GeometryCollection") {
        let poly_geoms = raw_intersection.geometry.geometries.filter(
          g => g.type === "Polygon" || g.type === "MultiPolygon"
        );

        if (poly_geoms.length === 0) {
          veToast("<icon>info</icon> No overlapping polygon area found to transfer.");
          return;
        } else if (poly_geoms.length === 1) {
          turf_intersection = turf.feature(poly_geoms[0]);
        } else {
          turf_intersection = turf.multiPolygon(poly_geoms.flatMap(g => (g.type === "Polygon") ? [g.coordinates] : g.coordinates));
        }
      }

      //Apply simplify if configured
      if (main.brush.simplify > 0)
        turf_intersection = turf.simplify(turf_intersection, { tolerance: main.brush.simplify });

      let node_buffer_m = Math.returnSafeNumber(main.brush.node_buffer, 0);
      let turf_subtraction = turf_intersection;

      if (node_buffer_m > 0) {
        let buffer_km = node_buffer_m / 1000;
        try {
          let buffered = turf.buffer(turf_intersection, buffer_km, { units: "kilometers", steps: 8 });
          if (buffered) turf_subtraction = buffered;
        } catch (buf_err) {}
      }

      let maptalks_add = Geospatiale.convertTurfToMaptalks(turf_intersection);
      let maptalks_remove = Geospatiale.convertTurfToMaptalks(turf_subtraction);

      if (!maptalks_add) return;

      let add_json = maptalks_add.toJSON();
      let remove_json = maptalks_remove ? maptalks_remove.toJSON() : add_json;

      if (date_range) {
        let end_ts = Math.max(Date.getTimestamp(date_range[0]), Date.getTimestamp(date_range[1]));
        let start_ts = Math.min(Date.getTimestamp(date_range[0]), Date.getTimestamp(date_range[1]));
        let ts_set = new Set();
        ts_set.add(start_ts);

        let source_ts = source_geom.history ? source_geom.history.getTimestamps() : [];
        for (let i = 0; i < source_ts.length; i++)
          if (source_ts[i] >= start_ts && source_ts[i] <= end_ts)
            ts_set.add(source_ts[i]);

        let target_ts = target_geom.history ? target_geom.history.getTimestamps() : [];
        for (let i = 0; i < target_ts.length; i++)
          if (target_ts[i] >= start_ts && target_ts[i] <= end_ts)
            ts_set.add(target_ts[i]);

        let all_timestamps = Array.from(ts_set).sort((a, b) => a - b);

        for (let i = 0; i < all_timestamps.length; i++) {
          let local_ts = all_timestamps[i];

          await DALS.Timeline.parseAction("remove_from_polygon", [{
            geometry_obj: source_geom.id,
            remove_from_polygon: { date: local_ts, geometry: remove_json }
          }], true);
          await DALS.Timeline.parseAction("add_to_polygon", [{
            geometry_obj: target_geom.id,
            add_to_polygon: { date: local_ts, geometry: add_json }
          }], true);
        }
      } else {
        await DALS.Timeline.parseAction("remove_from_polygon", [{
          geometry_obj: source_geom.id,
          remove_from_polygon: { date: main.date, geometry: remove_json }
        }], true);
        await DALS.Timeline.parseAction("add_to_polygon", [{
          geometry_obj: target_geom.id,
          add_to_polygon: { date: main.date, geometry: add_json }
        }], true);
      }

      if (typeof source_geom.draw === "function") source_geom.draw();
      if (typeof target_geom.draw === "function") target_geom.draw();
      if (typeof UI_Leftbar !== "undefined" && UI_Leftbar.refresh) UI_Leftbar.refresh();
      veToast("<icon>check</icon> Transferred nodes successfully.");
    } catch (err) {
      console.error("[handleNodeEditorEnd] Error during node transfer:", err);
    }

    return;
  }

  //2. Override handler (Node Override - guarantees topological overwrites)
  if (main.brush.mode === "node_override") {
    try {
      if (main.brush.node_editor.type === "add") {
        if (typeof this.loadHistory === "function")
          await this.loadHistory();
        if (!this.geometry && typeof this.draw === "function")
          this.draw();

        if (main.brush.simplify > 0)
          cursor_turf_geometry = turf.simplify(cursor_turf_geometry, { tolerance: main.brush.simplify });

        let maptalks_override = Geospatiale.convertTurfToMaptalks(cursor_turf_geometry);
        if (!maptalks_override) return;
        let override_json = maptalks_override.toJSON();

        //Find all other polities in the same layer that overlap the drawn geometry
        let affected_geometries = [];

        for (let i = 0; i < candidate_geometries.length; i++) {
          let local_geom = candidate_geometries[i];
          if (typeof local_geom.loadHistory === "function")
            await local_geom.loadHistory();

          let local_turf = getTurfGeometry(local_geom);

          if (local_turf) {
            local_turf = naissance.BrushNodeEditor.healTopology(local_turf);
            let inter = null;
            try {
              inter = turf.intersect(turf.featureCollection([local_turf, cursor_turf_geometry]));
            } catch (cand_err) {}

            if (inter && turf.area(inter) > 1.0) affected_geometries.push(local_geom);
          }
        }

        //Subtract override geometry from all overlapping polities in the same layer
        for (let i = 0; i < affected_geometries.length; i++) {
          await DALS.Timeline.parseAction("remove_from_polygon", [{
            geometry_obj: affected_geometries[i].id,
            remove_from_polygon: {
              date: (date_range) ? undefined : main.date,
              date_range: date_range,
              geometry: override_json
            }
          }], true);
          if (affected_geometries[i].draw) affected_geometries[i].draw();
        }

        //Add override geometry to this selected polity (union over)
        await DALS.Timeline.parseAction("add_to_polygon", [{
          geometry_obj: this.id,
          add_to_polygon: {
            date: (date_range) ? undefined : main.date,
            date_range: date_range,
            geometry: override_json
          },
          simplify_polygon: {
            date_range: date_range,
            tolerance: (main.brush.simplify > 0 && main.brush.simplify_applies_to_polygon) ?
              main.brush.simplify : undefined
          }
        }], true);

        this.draw();
        if (typeof UI_Leftbar !== "undefined" && UI_Leftbar.refresh) UI_Leftbar.refresh();
        veToast(`<icon>check</icon> Overrode ${String.formatNumber(affected_geometries.length)} polities successfully.`);
      } else if (main.brush.node_editor.type === "remove") {
        e.geometry = main.brush.getRemovePolygon(e.geometry);
        await DALS.Timeline.parseAction("remove_from_polygon", [{
          geometry_obj: this.id,
          remove_from_polygon: {
            date: (date_range) ? undefined : main.date,
            date_range: date_range,
            geometry: e.geometry.toJSON()
          }
        }], true);
      }
    } catch (err) {
      console.error("[handleNodeEditorEnd] Error during node override:", err);
    }

    return;
  }

  //3. Default Node handler
  if (main.brush.node_editor.type === "add") {
    //Snap and resolve against other polities in the same layer
    cursor_turf_geometry = naissance.BrushNodeEditor.snapPolygonToLayer(cursor_turf_geometry, candidate_geometries);
    e.geometry = Geospatiale.convertTurfToMaptalks(cursor_turf_geometry);

    e.geometry = main.brush.getAddPolygon(e.geometry);
    if (!e.geometry) return;

    await DALS.Timeline.parseAction("add_to_polygon", [{
      geometry_obj: this.id,
      add_to_polygon: {
        date: (date_range) ? undefined : main.date,
        date_range: date_range,
        geometry: e.geometry.toJSON()
      },
      simplify_polygon: {
        date_range: date_range,
        tolerance: (main.brush.simplify > 0 && main.brush.simplify_applies_to_polygon) ?
          main.brush.simplify : undefined
      }
    }], true);
  } else if (main.brush.node_editor.type === "remove") {
    e.geometry = main.brush.getRemovePolygon(e.geometry);

    await DALS.Timeline.parseAction("remove_from_polygon", [{
      geometry_obj: this.id,
      remove_from_polygon: {
        date: (date_range) ? undefined : main.date,
        date_range: date_range,
        geometry: e.geometry.toJSON()
      }
    }], true);
  }
};