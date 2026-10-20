if (!global.naissance) global.naissance = {};

naissance.BrushNodeEditor = class extends ve.Class {
  constructor () {
    super();

    //Declare local instance variables
    this.busy = false;
    this.coords = [];
    this.enabled = false;
    this.mode = "Polygon";
    this.type = "add";

    this._click_listener = (e) => { this.onclick(e); };
    this._dblclick_listener = (e) => { this.ondblclick(e); };
    this._keydown_listener = (e) => { this.onkeydown(e); };
    this._last_closed_time = 0;
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
    this.busy = false;
    this.enabled = false;
    this.coords = [];

    if (this.geometry) {
      this.geometry.remove();
      this.geometry = null;
    }

    if (typeof map !== "undefined" && map) {
      map.off("click", this._click_listener);
      map.off("dblclick", this._dblclick_listener);
      map.off("mousemove", this._mousemove_listener);
      try { map.config("doubleClickZoom", true); } catch (e) {}
    }

    if (typeof window !== "undefined")
      window.removeEventListener("keydown", this._keydown_listener);
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
    if (this.mode === "LineString" || this.mode === "FreeHandLineString" || draw_coords.length < 3)
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
    this.busy = false;
    this.enabled = true;
    this.type = "add";

    if (typeof map !== "undefined" && map) {
      try { map.config("doubleClickZoom", false); } catch (e) {}
      map.on("click", this._click_listener);
      map.on("dblclick", this._dblclick_listener);
      map.on("mousemove", this._mousemove_listener);
    }

    if (typeof window !== "undefined")
      window.addEventListener("keydown", this._keydown_listener);
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

    //Guard clause
    if (this.busy) return;
    if (this._last_closed_time && (Date.now() - this._last_closed_time < 400)) return;

    //Declare local instance variables
    let is_ctrl = Boolean(e?.domEvent?.ctrlKey || e?.ctrlKey || HTML.ctrl_pressed);
    let is_line = ["FreeHandLineString", "LineString"].includes(this.mode);
    let is_node_brush = ["node", "node_override", "node_transfer"].includes(main.brush.mode);
    let is_polygon = (this.mode === "Polygon");

    //Guard clause
    if (is_line && is_ctrl) return; //Remove isn't valid for GeometryLine

    if (this.coords.length === 0) {
      if (is_line && !is_node_brush && main.brush._selected_geometry?.isOpen("instance"))
        return;

      this.type = (is_ctrl) ? "remove" : "add";
    } else if (is_ctrl) {
      this.type = "remove";
    }

    //Check if user clicked near the starting vertex to close the polygon ring
    if (is_polygon && this.coords.length >= 3 && e.coordinate) {
      let is_near_start = false;

      if (typeof map !== "undefined" && map.coordinateToContainerPoint) {
        let click_cp = (e.containerPoint) ? e.containerPoint : map.coordinateToContainerPoint(e.coordinate);
        let first_cp = map.coordinateToContainerPoint(this.coords[0]);

        if (first_cp && click_cp) {
          let screen_dist = Math.hypot(click_cp.x - first_cp.x, click_cp.y - first_cp.y);
          if (screen_dist <= 15) is_near_start = true;
        }
      }

      if (is_near_start) {
        this.ondblclick(e);
        return;
      }
    }

    //Deduplicate accidental rapid repeat clicks in virtually the same screen spot
    if (this.coords.length > 0 && e.coordinate) {
      let last_node = this.coords[this.coords.length - 1];

      if (typeof map !== "undefined" && map.coordinateToContainerPoint) {
        let click_cp = (e.containerPoint) ? e.containerPoint : map.coordinateToContainerPoint(e.coordinate);
        let last_cp = map.coordinateToContainerPoint(last_node);

        if (last_cp && click_cp) {
          let screen_dist = Math.hypot(click_cp.x - last_cp.x, click_cp.y - last_cp.y);
          if (screen_dist < 6) return;
        }
      }
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
    if (this.busy) return;
    if (this._last_closed_time && (Date.now() - this._last_closed_time < 400)) return;
    this.busy = true;
    this._last_closed_time = Date.now();

    //Declare local instance variables
    let is_ctrl = Boolean(e?.domEvent?.ctrlKey || e?.ctrlKey || HTML.ctrl_pressed);
    let is_polygon = (this.mode === "Polygon");
    let local_coords = [...this.coords];
    let selected_geometry = main.brush._selected_geometry;

    if (is_ctrl) this.type = "remove";

    //Clear active preview immediately so user gets instant visual feedback
    if (this.geometry) {
      this.geometry.remove();
      this.geometry = null;
    }
    this.coords = [];

    //Deduplicate consecutive identical/micro-jitter coordinates (e.g. from rapid double-click)
    let clean_coords = [];
    for (let i = 0; i < local_coords.length; i++) {
      let pt = local_coords[i];
      let prev = clean_coords[clean_coords.length - 1];

      if (prev) {
        let px = (pt.x !== undefined) ? pt.x : pt[0];
        let py = (pt.y !== undefined) ? pt.y : pt[1];
        let qx = (prev.x !== undefined) ? prev.x : prev[0];
        let qy = (prev.y !== undefined) ? prev.y : prev[1];
        let dist = Math.hypot(px - qx, py - qy);
        if (dist < 1e-6) continue;
      }
      clean_coords.push(pt);
    }

    //If user clicked near the starting node, remove closing duplicate from the ring vertices
    if (is_polygon && clean_coords.length >= 2) {
      let first = clean_coords[0];
      let last = clean_coords[clean_coords.length - 1];
      let fx = (first.x !== undefined) ? first.x : first[0];
      let fy = (first.y !== undefined) ? first.y : first[1];
      let lx = (last.x !== undefined) ? last.x : last[0];
      let ly = (last.y !== undefined) ? last.y : last[1];

      let is_closing_node = (Math.hypot(lx - fx, ly - fy) < 1e-6);
      if (!is_closing_node && typeof map !== "undefined" && map.coordinateToContainerPoint) {
        let first_cp = map.coordinateToContainerPoint(first);
        let last_cp = map.coordinateToContainerPoint(last);
        if (first_cp && last_cp && Math.hypot(last_cp.x - first_cp.x, last_cp.y - first_cp.y) <= 15)
          is_closing_node = true;
      }

      if (is_closing_node) clean_coords.pop();
    }

    //Guard clauses
    if (clean_coords.length < 2 || (is_polygon && clean_coords.length < 3)) {
      if (is_polygon && clean_coords.length > 0)
        veToast("<icon>warning</icon> Polygons require at least 3 distinct points.");
      this.busy = false;
      this.disable();
      this.enable();
      return;
    }

    let finished_geometry = null;
    if (is_polygon) {
      let ring_coords = [...clean_coords];
      ring_coords.push(clean_coords[0]);
      finished_geometry = new maptalks.Polygon(ring_coords);
    } else {
      finished_geometry = new maptalks.LineString(clean_coords);
    }

    try {
      if (selected_geometry) {
        let layer_obj = selected_geometry.getLayer();

        if (layer_obj?._type === "provinces" || layer_obj?.type === "provinces")
          return;

        if (naissance[selected_geometry.class_name]?.handleNodeEditorEnd) {
          try {
            await naissance[selected_geometry.class_name].handleNodeEditorEnd.call(selected_geometry, { geometry: finished_geometry });
          } catch (handler_err) {
            console.error("[ondblclick] Error in handleNodeEditorEnd:", handler_err);
            veToast("<icon>error</icon> Failed to apply node editing.");
          }
        }
      }
    } finally {
      this.busy = false;
      this.disable();
      this.enable();
    }
  }

  /**
   * Handles keydown events to allow Enter to finish or Escape to cancel.
   *
   * @param {KeyboardEvent} arg0_e - Keydown event.
   */
  onkeydown (arg0_e) {
    //Convert from parameters
    let e = arg0_e;

    //Guard clause
    if (this.busy || !this.enabled) return;

    //Function body
    if (e.key === "Enter") {
      let is_polygon = (this.mode === "Polygon");
      let min_points = (is_polygon) ? 3 : 2;

      if (this.coords.length >= min_points) {
        e.preventDefault();
        this.ondblclick(e);
      }
    } else if (e.key === "Escape") {
      this.coords = [];
      if (this.geometry) {
        this.geometry.remove();
        this.geometry = null;
      }
    }
  }

  /**
   * Handles map mousemove events to preview drawn nodes.
   *
   * @param {Object} arg0_e - Map mousemove event.
   */
  onmousemove (arg0_e) {
    //Convert from parameters
    let e = arg0_e;

    //Guard clause
    if (this.busy) return;
    if (this.coords.length === 0) return;

    //Declare local instance variables
    let hover_coord = e.coordinate;
    let is_polygon = (this.mode === "Polygon");

    //Snap cursor preview to starting vertex if hovering near it
    if (is_polygon && this.coords.length >= 3 && typeof map !== "undefined" && map.coordinateToContainerPoint && e.coordinate) {
      let first_cp = map.coordinateToContainerPoint(this.coords[0]);
      let mouse_cp = (e.containerPoint) ? e.containerPoint : map.coordinateToContainerPoint(e.coordinate);

      if (first_cp && mouse_cp) {
        let screen_dist = Math.hypot(mouse_cp.x - first_cp.x, mouse_cp.y - first_cp.y);
        if (screen_dist <= 15) hover_coord = this.coords[0];
      }
    }

    //Function body
    this.draw(hover_coord);
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
      let clean_geom = (Geospatiale.cleanRings) ?
        Geospatiale.cleanRings(turf_geometry) : turf_geometry;
      clean_geom = clean_geom || turf_geometry;

      let kinks = (turf.kinks) ? turf.kinks(clean_geom) : null;
      if (kinks && kinks.features && kinks.features.length > 0 && turf.unkinkPolygon) {
        let unkinked = turf.unkinkPolygon(clean_geom);

        if (unkinked && unkinked.features && unkinked.features.length > 0) {
          if (unkinked.features.length === 1) {
            return unkinked.features[0];
          } else {
            let coords_list = unkinked.features.map(f => f.geometry.coordinates);
            return turf.multiPolygon(coords_list);
          }
        }
      }

      return clean_geom;
    } catch (e) {
      console.warn("[healTopology] error, using original geometry:", e);
    }

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

    if (!resolved) return null;

    //Function body
    for (let i = 0; i < layer_geometries.length; i++) {
      let cand = layer_geometries[i];
      if (!cand) continue;

      //Check visibility and active state
      if (cand._is_visible === false) continue;
      if (cand.value && cand.value[0] === null) continue;
      if (cand.value && cand.value[2] && cand.value[2].hidden) continue;
      try {
        if (cand.history?.getKeyframe) {
          let current_keyframe = cand.history.getKeyframe();
          if (current_keyframe?.value?.[0] === null || current_keyframe?.value?.[0] === "null") continue;
          if (current_keyframe?.value?.[2]?.hidden) continue;
        }
      } catch (e) {}

      let cand_maptalks = cand.geometry || (cand.value ? cand.value[0] : null);
      if (!cand_maptalks) continue;

      let cand_bbox = null;
      let cur_bbox = turf.bbox(resolved);

      if (cand_maptalks.getExtent) {
        let ext = cand_maptalks.getExtent();
        if (ext) cand_bbox = [ext.xmin, ext.ymin, ext.xmax, ext.ymax];
      } else if (cand.bbox) {
        cand_bbox = cand.bbox;
      }

      if (cand_bbox) {
        if (cand_bbox[0] > cur_bbox[2] || cand_bbox[2] < cur_bbox[0] ||
            cand_bbox[1] > cur_bbox[3] || cand_bbox[3] < cur_bbox[1])
          continue;
      }

      let cand_turf = Geospatiale.convertMaptalksToTurf(cand_maptalks);
      if (!cand_turf) continue;

      cand_turf = naissance.BrushNodeEditor.healTopology(cand_turf);
      if (!cand_turf) continue;

      let cand_geom = cand_turf.geometry || cand_turf;
      if (!cand_geom || !Array.isArray(cand_geom.coordinates) || cand_geom.coordinates.length === 0)
        continue;

      try {
        let diff = (Geospatiale.diffComponentWise) ?
          Geospatiale.diffComponentWise(resolved, cand_turf) :
          turf.difference(turf.featureCollection([resolved, cand_turf]));

        if (diff !== undefined) {
          if (diff && diff.geometry?.type === "GeometryCollection") {
            let poly_geoms = diff.geometry.geometries.filter(g => g.type === "Polygon" || g.type === "MultiPolygon");
            if (poly_geoms.length === 1) diff = turf.feature(poly_geoms[0]);
            else if (poly_geoms.length > 1) diff = turf.multiPolygon(poly_geoms.flatMap(g => (g.type === "Polygon") ? [g.coordinates] : g.coordinates));
            else diff = null;
          }
          resolved = diff;
        }

        if (!resolved) break;
      } catch (diff_err) {
        console.warn("[snapPolygonToLayer] diff error:", diff_err);
      }
    }

    //Return statement
    return resolved;
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
      let target_date = main.date;
      if (date_range) {
        let end_ts = Math.max(Date.getTimestamp(date_range[0]), Date.getTimestamp(date_range[1]));
        let main_ts = Date.getTimestamp(main.date);
        let start_ts = Math.min(Date.getTimestamp(date_range[0]), Date.getTimestamp(date_range[1]));
        if (main_ts < start_ts || main_ts > end_ts) target_date = start_ts;
      }
      let kf_json = arg_geom.getGeometryKeyframeAtDate(target_date);
      if (!kf_json && date_range && arg_geom.history) {
        let all_ts = Object.keys(arg_geom.history.keyframes || {}).map(ts => Date.convertTimestampToInt(ts)).sort((a, b) => a - b);
        let end_ts = Math.max(Date.getTimestamp(date_range[0]), Date.getTimestamp(date_range[1]));
        let start_ts = Math.min(Date.getTimestamp(date_range[0]), Date.getTimestamp(date_range[1]));
        for (let i = 0; i < all_ts.length; i++) {
          let ts = all_ts[i];
          if (ts >= start_ts && ts <= end_ts) {
            let candidate_json = arg_geom.getGeometryKeyframeAtDate(ts);
            if (candidate_json) {
              kf_json = candidate_json;
              break;
            }
          }
        }
      }
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

  //Guard clause: fallback to coordinate extraction if standard conversion returned null
  if (!cursor_turf_geometry && e.geometry) {
    try {
      let raw_coords = (e.geometry.getCoordinates) ? e.geometry.getCoordinates() : e.geometry.coordinates;
      let flat_rings = naissance.BrushNodeEditor.flattenCoordinates(raw_coords);
      if (flat_rings.length > 0 && flat_rings[0].length >= 3) {
        let clean_ring = flat_rings[0].map(pt => [pt.x !== undefined ? pt.x : pt[0], pt.y !== undefined ? pt.y : pt[1]]);
        let first = clean_ring[0];
        let last = clean_ring[clean_ring.length - 1];
        if (first[0] !== last[0] || first[1] !== last[1]) clean_ring.push([first[0], first[1]]);
        if (clean_ring.length >= 4) cursor_turf_geometry = turf.polygon([clean_ring]);
      }
    } catch (fallback_err) {
      console.error("[handleNodeEditorEnd] Fallback conversion failed:", fallback_err);
    }
  }

  if (!cursor_turf_geometry) {
    veToast("<icon>warning</icon> Could not form a valid geometry from drawn nodes.");
    return;
  }

  //Heal topology of drawn selection to eliminate self-intersections and bowties
  cursor_turf_geometry = naissance.BrushNodeEditor.healTopology(cursor_turf_geometry);
  if (!cursor_turf_geometry) return;

  //Collect other rendered polities in the same layer
  if (current_layer && typeof current_layer.getAllGeometries === "function") {
    candidate_geometries = current_layer.getAllGeometries().filter(g => g.id !== this.id && (g.geometry || g.value?.[0]));
  } else {
    candidate_geometries = Object.values(naissance.Geometry?.instances || {}).filter(
      g => g.id !== this.id && g instanceof naissance.GeometryPolygon && (g.geometry || g.value?.[0])
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
        let cursor_bbox = turf.bbox(cursor_turf_geometry);

        for (let i = 0; i < candidate_geometries.length; i++) {
          let cand = candidate_geometries[i];
          let cand_ext = cand.geometry?.getExtent ? cand.geometry.getExtent() : null;
          if (cand_ext) {
            if (cand_ext.xmin > cursor_bbox[2] || cand_ext.xmax < cursor_bbox[0] || cand_ext.ymin > cursor_bbox[3] || cand_ext.ymax < cursor_bbox[1])
              continue;
          } else if (cand.bbox) {
            if (cand.bbox[0] > cursor_bbox[2] || cand.bbox[2] < cursor_bbox[0] || cand.bbox[1] > cursor_bbox[3] || cand.bbox[3] < cursor_bbox[1])
              continue;
          }

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
      if (main.brush.simplify > 0 && main.brush.simplify_applies_to_polygon)
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
        let isAlive = function (arg_geom, arg_ts) {
          if (!arg_geom || !arg_geom.history) return false;
          let ts_int = Date.convertTimestampToInt(arg_ts);
          if (arg_geom.history._hasTimestampAfter && !arg_geom.history._hasTimestampAfter(ts_int))
            return false;
          let kf = arg_geom.history.getKeyframe({ date: ts_int });
          if (!kf || !kf.value) return false;
          if (kf.value[0] === null || kf.value[0] === undefined || kf.value[0] === "null" || kf.value[0] === "")
            return false;
          if (kf.value[2] && kf.value[2].hidden)
            return false;
          return true;
        };

        let end_ts = Math.max(Date.getTimestamp(date_range[0]), Date.getTimestamp(date_range[1]));
        let start_ts = Math.min(Date.getTimestamp(date_range[0]), Date.getTimestamp(date_range[1]));

        let source_ts = source_geom.history?.keyframes ? Object.keys(source_geom.history.keyframes).map(ts => Date.convertTimestampToInt(ts)) : [];
        let target_ts = target_geom.history?.keyframes ? Object.keys(target_geom.history.keyframes).map(ts => Date.convertTimestampToInt(ts)) : [];

        //Find effective start date where both geometries coexist
        let effective_start_ts = null;
        if (isAlive(source_geom, start_ts) && isAlive(target_geom, start_ts)) {
          effective_start_ts = start_ts;
        } else {
          let combined_ts = Array.from(new Set([start_ts, ...source_ts, ...target_ts])).sort((a, b) => a - b);
          for (let i = 0; i < combined_ts.length; i++) {
            let ts = combined_ts[i];
            if (ts >= start_ts && ts <= end_ts && isAlive(source_geom, ts) && isAlive(target_geom, ts)) {
              effective_start_ts = ts;
              break;
            }
          }
        }

        if (effective_start_ts === null) {
          veToast("<icon>warning</icon> Source and target geometries do not coexist within the selected date range.");
          return;
        }

        let source_set = new Set();
        let target_set = new Set();

        source_set.add(effective_start_ts);
        target_set.add(effective_start_ts);

        for (let i = 0; i < source_ts.length; i++) {
          let ts = source_ts[i];
          if (ts >= effective_start_ts && ts <= end_ts && isAlive(source_geom, ts))
            source_set.add(ts);
        }

        for (let i = 0; i < target_ts.length; i++) {
          let ts = target_ts[i];
          if (ts >= effective_start_ts && ts <= end_ts && isAlive(target_geom, ts))
            target_set.add(ts);
        }

        let all_source_ts = Array.from(source_set).sort((a, b) => a - b);
        let all_target_ts = Array.from(target_set).sort((a, b) => a - b);

        for (let i = 0; i < all_source_ts.length; i++) {
          await DALS.Timeline.parseAction("remove_from_polygon", [{
            geometry_obj: source_geom.id,
            remove_from_polygon: { date: all_source_ts[i], do_not_draw: true, geometry: remove_json }
          }], true);
          await new Promise(resolve => setTimeout(resolve, 0));
        }

        for (let i = 0; i < all_target_ts.length; i++) {
          await DALS.Timeline.parseAction("add_to_polygon", [{
            geometry_obj: target_geom.id,
            add_to_polygon: { date: all_target_ts[i], do_not_draw: true, geometry: add_json }
          }], true);
          await new Promise(resolve => setTimeout(resolve, 0));
        }

        if (source_geom.draw) source_geom.draw();
        if (target_geom.draw) target_geom.draw();
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

        if (main.brush.simplify > 0 && main.brush.simplify_applies_to_polygon)
          cursor_turf_geometry = turf.simplify(cursor_turf_geometry, { tolerance: main.brush.simplify });

        let maptalks_override = Geospatiale.convertTurfToMaptalks(cursor_turf_geometry);
        if (!maptalks_override) return;
        let override_json = maptalks_override.toJSON();

        //Find all other polities in the same layer that overlap the drawn geometry
        let affected_geometries = [];
        let cursor_bbox = turf.bbox(cursor_turf_geometry);

        for (let i = 0; i < candidate_geometries.length; i++) {
          let local_geom = candidate_geometries[i];
          let local_ext = local_geom.geometry?.getExtent ? local_geom.geometry.getExtent() : null;
          if (local_ext) {
            if (local_ext.xmin > cursor_bbox[2] || local_ext.xmax < cursor_bbox[0] || local_ext.ymin > cursor_bbox[3] || local_ext.ymax < cursor_bbox[1])
              continue;
          } else if (local_geom.bbox) {
            if (local_geom.bbox[0] > cursor_bbox[2] || local_geom.bbox[2] < cursor_bbox[0] || local_geom.bbox[1] > cursor_bbox[3] || local_geom.bbox[3] < cursor_bbox[1])
              continue;
          }

          if (typeof local_geom.loadHistory === "function")
            await local_geom.loadHistory();

          let local_turf = getTurfGeometry(local_geom);

          if (local_turf) {
            local_turf = naissance.BrushNodeEditor.healTopology(local_turf);
            let test_cand = local_turf;
            let l_geom = local_turf.geometry || local_turf;

            if (!l_geom || !Array.isArray(l_geom.coordinates) || l_geom.coordinates.length === 0)
              continue;

            let l_type = l_geom.type;

            if (l_type === "MultiPolygon") {
              let l_coords = l_geom.coordinates;
              let l_matches = [];

              for (let c = 0; c < l_coords.length; c++) {
                if (!Array.isArray(l_coords[c]) || l_coords[c].length === 0) continue;
                try {
                  let p_f = turf.polygon(l_coords[c]);
                  let p_b = turf.bbox(p_f);
                  let p_ol = !(
                    p_b[0] > cursor_bbox[2] || p_b[2] < cursor_bbox[0] ||
                    p_b[1] > cursor_bbox[3] || p_b[3] < cursor_bbox[1]
                  );
                  if (p_ol) l_matches.push(l_coords[c]);
                } catch (p_err) {}
              }

              if (l_matches.length === 1) test_cand = turf.polygon(l_matches[0]);
              else if (l_matches.length > 1) test_cand = turf.multiPolygon(l_matches);
              else test_cand = null;
            } else if (l_type === "Polygon") {
              try {
                let p_b = turf.bbox(test_cand);
                let p_ol = !(
                  p_b[0] > cursor_bbox[2] || p_b[2] < cursor_bbox[0] ||
                  p_b[1] > cursor_bbox[3] || p_b[3] < cursor_bbox[1]
                );
                if (!p_ol) test_cand = null;
              } catch (p_err) {
                test_cand = null;
              }
            } else {
              test_cand = null;
            }

            if (test_cand) {
              let inter = null;
              try {
                inter = turf.intersect(turf.featureCollection([test_cand, cursor_turf_geometry]));
              } catch (cand_err) {}

              if (inter && turf.area(inter) > 1.0) affected_geometries.push(local_geom);
            }
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
          await new Promise(resolve => setTimeout(resolve, 0));
        }

        let has_simplify = Boolean(main.brush.simplify > 0 && main.brush.simplify_applies_to_polygon);
        let mvp_entry = {
          geometry_obj: this.id,
          add_to_polygon: {
            date: (date_range) ? undefined : main.date,
            date_range: date_range,
            geometry: override_json
          }
        };
        if (has_simplify) {
          mvp_entry.simplify_polygon = {
            date_range: date_range,
            tolerance: main.brush.simplify
          };
        }

        await DALS.Timeline.parseAction("add_to_polygon", [mvp_entry], true);

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
    if (!cursor_turf_geometry) {
      veToast("<icon>info</icon> Drawn nodes completely overlap adjacent polities in the same layer.");
      return;
    }

    let maptalks_add = Geospatiale.convertTurfToMaptalks(cursor_turf_geometry);
    if (!maptalks_add) return;

    let has_simplify = Boolean(main.brush.simplify > 0 && main.brush.simplify_applies_to_polygon);
    let mvp_entry = {
      geometry_obj: this.id,
      add_to_polygon: {
        date: (date_range) ? undefined : main.date,
        date_range: date_range,
        geometry: maptalks_add.toJSON()
      }
    };
    if (has_simplify) {
      mvp_entry.simplify_polygon = {
        date_range: date_range,
        tolerance: main.brush.simplify
      };
    }

    await DALS.Timeline.parseAction("add_to_polygon", [mvp_entry], true);
    if (typeof this.draw === "function") this.draw();
    if (typeof UI_Leftbar !== "undefined" && UI_Leftbar.refresh) UI_Leftbar.refresh();
    veToast("<icon>check</icon> Added nodes to polygon successfully.");
  } else if (main.brush.node_editor.type === "remove") {
    let maptalks_remove = Geospatiale.convertTurfToMaptalks(cursor_turf_geometry);
    if (!maptalks_remove) return;

    await DALS.Timeline.parseAction("remove_from_polygon", [{
      geometry_obj: this.id,
      remove_from_polygon: {
        date: (date_range) ? undefined : main.date,
        date_range: date_range,
        geometry: maptalks_remove.toJSON()
      }
    }], true);
    if (typeof this.draw === "function") this.draw();
    if (typeof UI_Leftbar !== "undefined" && UI_Leftbar.refresh) UI_Leftbar.refresh();
    veToast("<icon>check</icon> Removed nodes from polygon successfully.");
  }
};