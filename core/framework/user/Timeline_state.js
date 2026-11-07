//State mutation and tracking helpers
{
  if (!DALS._synced_deleted_ids) DALS._synced_deleted_ids = new Set();
  if (!DALS.deleted_ids) DALS.deleted_ids = new Set();
  if (!DALS.dirty_ids) DALS.dirty_ids = new Set();
  if (!DALS.unsynced_dirty_ids) DALS.unsynced_dirty_ids = new Set();


  /**
   * Marks an entity ID as modified in the active session and queues it for in-memory DB worker synchronisation.
   *
   * @param {number|string} arg0_id
   */
  DALS.markDirty = function (arg0_id) {
    //Convert from parameters
    let id = arg0_id;

    //Guard clause for empty IDs
    if (id === undefined || id === null) return;

    //Declare local instance variables
    let str_id = String(id);


    DALS.dirty_ids.add(str_id);
    DALS.unsynced_dirty_ids.add(str_id);
    if (DALS.deleted_ids) DALS.deleted_ids.delete(str_id);
    if (DALS._synced_deleted_ids) DALS._synced_deleted_ids.delete(str_id);
  };


  /**
   * Coalesces UI hierarchy, timeline and map renderer refreshes without thrashing during Undo/Redo replay.
   *
   * @param {number} [arg0_delay_ms=50]
   */
  DALS.scheduleRefresh = function (arg0_delay_ms) {
    //Convert from parameters
    let delay_ms = (arg0_delay_ms !== undefined) ? arg0_delay_ms : 50;

    //Declare local instance variables
    let main_obj = (typeof main !== "undefined") ? main : (globalThis.main || global.main);

    if (DALS._refresh_timeout) {
      clearTimeout(DALS._refresh_timeout);
      DALS._refresh_timeout = null;
    }

    //Skip intermediate refreshes while jumpToAction is replaying
    if (DALS.Timeline?.is_replaying && delay_ms > 0) return;


    DALS._refresh_timeout = setTimeout(() => {
      DALS._refresh_timeout = null;
      try {
        if (global.UI_Leftbar?.refresh) UI_Leftbar.refresh();
      } catch (e) {
        console.error("[DALS] UI_Leftbar.refresh error:", e);
      }
      try {
        if (global.UI_LeftbarTimeline?.refresh) UI_LeftbarTimeline.refresh();
      } catch (e) {
        console.error("[DALS] UI_LeftbarTimeline.refresh error:", e);
      }
      try {
        if (main_obj?.renderer?.update) main_obj.renderer.update();
      } catch (e) {
        console.error("[DALS] renderer.update error:", e);
      }
    }, delay_ms);
  };


  /**
   * Serialises a Feature instance into its standard `.naissance` object representation.
   *
   * @param {Object} arg0_feature
   *
   * @returns {Object}
   */
  DALS.serialiseFeature = function (arg0_feature) {
    //Convert from parameters
    let feature_obj = arg0_feature;

    //Declare local instance variables
    let payload_obj = {
      class_name: feature_obj.class_name,
      id: feature_obj.id,
      metadata: feature_obj.metadata,
      type: "feature",
      value: (typeof feature_obj.toJSON === "function") ? feature_obj.toJSON() : feature_obj.json
    };


    if (feature_obj._is_visible === false)
      payload_obj.is_visible = false;

    //Return statement
    return payload_obj;
  };


  /**
   * Serialises a Geometry instance into its standard `.naissance` object representation.
   *
   * @param {Object} arg0_geometry
   *
   * @returns {Object}
   */
  DALS.serialiseGeometry = function (arg0_geometry) {
    //Convert from parameters
    let geometry_obj = arg0_geometry;

    //Declare local instance variables
    let local_history_json = (typeof geometry_obj.history?.toJSON === "function") ?
      geometry_obj.history.toJSON() : {};


    Object.iterate(local_history_json, (local_timestamp, local_value) => {
      if (local_value && local_value[0] && typeof local_value[0] === "object") {
        delete local_value[0].options;
        delete local_value[0].symbol;
      }
    });

    //Return statement
    return {
      class_name: geometry_obj.class_name,
      history: local_history_json,
      id: geometry_obj.id,
      metadata: geometry_obj.metadata,
      type: "geometry"
    };
  };


  /**
   * Pushes only unsynchronised deletions, dirty geometries and modified features to the in-memory DB worker cache.
   *
   * @returns {Promise<boolean>}
   */
  DALS.syncDirtyToDB = async function () {
    //Guard clause when DB mode is inactive
    if (!global.ve?.ndjson_file_path) return false;

    //Declare local instance variables
    let pending_deletes = [];
    let update_map = {};


    //1. Collect newly deleted IDs that are not currently live
    if (DALS.deleted_ids && DALS.deleted_ids.size > 0)
      for (let local_id of DALS.deleted_ids) {
        let str_id = String(local_id);
        let is_live = Boolean(naissance.Geometry?.instances?.[str_id] || naissance.Feature?.instances?.[str_id]);
        if (!is_live && !DALS._synced_deleted_ids.has(str_id)) {
          pending_deletes.push(str_id);
          DALS._synced_deleted_ids.add(str_id);
        }
      }

    if (pending_deletes.length > 0 && global.db?.removeValues)
      await db.removeValues(pending_deletes);

    //2. Collect only geometries dirtied since the last sync
    if (DALS.unsynced_dirty_ids && DALS.unsynced_dirty_ids.size > 0) {
      for (let local_id of DALS.unsynced_dirty_ids) {
        let str_id = String(local_id);
        let inst = naissance.Geometry?.instances?.[str_id];
        if (!inst) continue;

        DALS.deleted_ids?.delete(str_id);
        DALS._synced_deleted_ids?.delete(str_id);

        let serialised_geom = DALS.serialiseGeometry(inst);
        if (
          Object.keys(serialised_geom.history).length === 0 &&
          global.db?.getValue
        ) {
          let existing_val = await db.getValue(str_id);
          if (existing_val?.history && Object.keys(existing_val.history).length > 0)
            serialised_geom.history = existing_val.history;
        }
        update_map[str_id] = serialised_geom;
      }
      DALS.unsynced_dirty_ids.clear();
    }

    //3. Collect only features whose serialised state changed since last sync/load
    if (naissance.Feature?.instances)
      for (let local_id in naissance.Feature.instances) {
        let feat = naissance.Feature.instances[local_id];
        if (!feat) continue;

        let feat_payload = DALS.serialiseFeature(feat);
        let snapshot_str = JSON.stringify(feat_payload);
        if (feat._clean_snapshot_str !== snapshot_str) {
          feat._clean_snapshot_str = snapshot_str;
          update_map[local_id] = feat_payload;
          DALS.deleted_ids?.delete(String(local_id));
          DALS._synced_deleted_ids?.delete(String(local_id));
        }
      }

    if (Object.keys(update_map).length > 0 && global.db?.setValues)
      await db.setValues(update_map);

    //Return statement
    return true;
  };


  /**
   * Parses a user action inside Naissance. All user actions must be mapped to a valid JSON schema.
   * @alias DALS.Timeline.parseAction
   *
   * @param {string} [arg0_key] - The key to push to the current DALS timeline.
   * @param {Object[]} [arg1_json] - If no top-level ID is passed, the action is assumed to be global.
   * @param {boolean} [arg2_do_not_push_action=false]
   */
  DALS.Timeline.parseAction = async function (arg0_key, arg1_json, arg2_do_not_push_action) {
    //Convert from parameters
    let key = arg0_key;
    let json = (typeof arg1_json === "string") ? JSON.parse(arg1_json) : arg1_json;
    let do_not_push_action = arg2_do_not_push_action;

    //Initialise JSON
    if (json === undefined) json = [];

    //Allow callers to pass either a raw MVP array or a full action object
    if (!Array.isArray(json) && json.value !== undefined) {
      if (key === undefined)
        key = json.key || json.options?.key;

      json = (typeof json.value === "string") ?
        JSON.parse(json.value) : json.value;
    }
    if (json === undefined) json = [];
    if (!Array.isArray(json)) json = [json];

    //Declare local instance variables
    let current_tl = (!do_not_push_action && DALS.Timeline?.getTimeline) ?
      DALS.Timeline.getTimeline(DALS.Timeline.current_timeline) : null;
    let pre_action_head;
    let scope_map = naissance.Action.scope_map;


    //Capture pre-mutation head state when branching from an undone timeline index
    if (
      !do_not_push_action &&
      current_tl &&
      DALS.Timeline.current_index !== current_tl.value.length - 1
    )
      pre_action_head = DALS.toJSON();

    //Iterate over multi-value packet (MVP) and filter it down to superclass single-value packets (SVPs)
    for (let i = 0; i < json.length; i++) {
      if (!json[i] || typeof json[i] !== "object") continue;

      let has_scoped_target = Boolean(
        json[i].feature_obj ||
        json[i].geometry_obj ||
        (json[i].type && json[i].type !== "global")
      );

      //1. Scoped Actions Palette handling
      if (has_scoped_target) {
        let feature_obj = (json[i].feature_obj !== undefined) ?
          naissance.Feature?.instances?.[json[i].feature_obj] : undefined;
        let geometry_obj = (json[i].geometry_obj !== undefined) ?
          naissance.Geometry?.instances?.[json[i].geometry_obj] : undefined;

        //Instantiate geometry shell from DB if referenced during replay before inspection
        if (
          !geometry_obj &&
          json[i].geometry_obj &&
          global.ve?.ndjson_file_path &&
          global.db?.getValue &&
          !DALS.deleted_ids?.has(String(json[i].geometry_obj)) &&
          json[i].delete_geometry !== true
        ) {
          let db_val = await db.getValue(String(json[i].geometry_obj));
          if (db_val?.class_name && naissance[db_val.class_name]) {
            geometry_obj = new naissance[db_val.class_name]({ is_import: true });
            geometry_obj.setID(String(json[i].geometry_obj));
            if (db_val.metadata) geometry_obj.metadata = db_val.metadata;
            if (db_val.history) {
              geometry_obj.history._is_loading_from_db = true;
              try {
                geometry_obj.history.fromJSON(db_val.history);
              } finally {
                geometry_obj.history._is_loading_from_db = false;
              }
            }
          }
        }

        let naissance_obj;
        if (feature_obj) naissance_obj = feature_obj;
        if (geometry_obj) naissance_obj = geometry_obj;

        //Ensure DB geometry history is hydrated before mutating keyframes, symbols, names or properties
        if (
          naissance_obj &&
          naissance.Geometry &&
          naissance_obj instanceof naissance.Geometry &&
          global.ve?.ndjson_file_path &&
          json[i].delete_geometry !== true &&
          typeof naissance_obj.loadHistory === "function" &&
          (!naissance_obj.history?.keyframes || Object.keys(naissance_obj.history.keyframes).length === 0)
        )
          await naissance_obj.loadHistory();

        //Resolve scope target safely even when deleting an unloaded entity or encountering a missing ID
        let scope_target = (naissance_obj || json[i].type);
        if (!scope_target) {
          if (json[i].delete_geometry === true) {
            scope_target = "Geometry";
          } else if (json[i].delete_feature === true) {
            scope_target = "Feature";
          } else {
            console.warn("[DALS] Skipping action packet targeting missing entity:", json[i]);
            continue;
          }
        }

        if (
          naissance_obj?.id &&
          json[i].delete_geometry !== true &&
          json[i].delete_feature !== true
        )
          DALS.markDirty(naissance_obj.id);

        //Iterate over all scopes and handle their actions
        let scopes = naissance.Action.getScopes(scope_target);

        for (let x = 0; x < scopes.length; x++) {
          let local_scope_map = scope_map[scopes[x]];
          if (!local_scope_map) continue;

          let all_scope_keys = Object.keys(local_scope_map);

          for (let y = 0; y < all_scope_keys.length; y++) {
            let local_action = local_scope_map[all_scope_keys[y]];

            if (json[i][local_action.key] !== undefined && typeof local_action.special_function === "function")
              await local_action.special_function({
                naissance_obj,
                ...json[i]
              });
          }
        }
      }

      //2. Global state commands (including manual commits with type: "global")
      if (!has_scoped_target || json[i].type === "global") {
        if (json[i].load_save || json[i].load_savefile) {
          if (json[i].load_save) {
            await Promise.resolve(DALS.fromJSON(json[i].load_save));
            if (typeof window !== "undefined" && window?.discordRPC?.updateActivity)
              window.discordRPC.updateActivity("editing_default");
          }
          if (json[i].load_savefile) {
            await DALS.load(json[i].load_savefile, {
              is_replay: Boolean(do_not_push_action)
            });
            if (typeof window !== "undefined" && window?.discordRPC?.updateActivity)
              window.discordRPC.updateActivity("editing_savefile", path.basename(json[i].load_savefile));
          }
        }
        if (json[i].set_date) {
          if (global.UI_DateMenu?.setDate)
            UI_DateMenu.setDate(json[i].set_date);
        } else if (json[i].refresh_date === true) {
          let is_playing = (global.UI_DateMenu?.isPlaying) ? UI_DateMenu.isPlaying() : false;
          let main_obj = (typeof main !== "undefined") ? main : (globalThis.main || global.main);

          if (global.ve?.ndjson_file_path) {
            if (main_obj?.renderer?.update)
              main_obj.renderer.update();

            Object.iterate(naissance.Geometry.instances, (local_key, local_value) => {
              let has_local_history = (local_value.history?.keyframes && Object.keys(local_value.history.keyframes).length > 0);
              if (has_local_history) {
                local_value.draw();
                local_value.update();
              }
            });
          } else {
            Object.iterate(naissance.Geometry.instances, (local_key, local_value) => {
              local_value.draw();
              local_value.update();
            });
          }

          if (naissance.GeometryMedia?.syncToDate) naissance.GeometryMedia.syncToDate();
          if (naissance.Mapmode?.draw) naissance.Mapmode.draw();
          if (!is_playing && global.UI_Leftbar?.refresh) UI_Leftbar.refresh();
        }
      }
    }

    if (!DALS.Timeline?.is_replaying && global.ve?.ndjson_file_path)
      await DALS.syncDirtyToDB();

    //Save action to current timeline if needed
    if (!do_not_push_action) {
      new DALS.Action({
        head_state: pre_action_head,
        options: {
          key: key,
          name: String.formalise(key)
        },
        value: json
      });

      //Force all UI_LeftbarHierarchy instances to .refresh()
      if (global.UI_Leftbar?.refresh)
        UI_Leftbar.refresh();
    }
  };
}


//State save/load functions
{
  /**
   * Clears all active map layers, rendered entities, hierarchy instances and dirty tracking sets.
   */
  DALS.clearMap = function () {
    //Declare local instance variables
    let main_obj = (typeof main !== "undefined") ? main : (globalThis.main || global.main);
    let map_container = (typeof map !== "undefined" && map?.getContainer) ? map.getContainer() : null;


    if (DALS._refresh_timeout) {
      clearTimeout(DALS._refresh_timeout);
      DALS._refresh_timeout = null;
    }
    if (main_obj?.renderer?.raf_handle && typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(main_obj.renderer.raf_handle);
      main_obj.renderer.raf_handle = null;
    }

    //Clear _layers
    if (main_obj?._layers) {
      main_obj._layers.province_layers = [];
      if (main_obj._layers.provinces)
        main_obj._layers.provinces.clear();
    }
    if (main_obj?.layers?.entity_layer)
      main_obj.layers.entity_layer.clear();
    if (main_obj?.layers?.selection_layer)
      main_obj.layers.selection_layer.clear();
    if (main_obj?.layers?.label_layer)
      main_obj.layers.label_layer.clear();

    //Derender and remove all cached renderer entities
    if (main_obj?.renderer?.rendered_entities) {
      for (let [, inst] of main_obj.renderer.rendered_entities) {
        if (typeof inst?.remove === "function") {
          try { inst.remove(true); } catch (e) {}
        }
        if (main_obj.renderer?.derenderEntity)
          main_obj.renderer.derenderEntity(inst);
      }
      main_obj.renderer.rendered_entities.clear();
    }

    //Clear geometries
    if (naissance.Geometry?.instances)
      Object.iterate(naissance.Geometry.instances, (local_key, local_geometry) => {
        try { local_geometry.remove(true); } catch (e) {}
      });

    //Remove any lingering media canvases attached to the map container
    if (map_container) {
      let all_media_canvases = map_container.querySelectorAll("canvas.geometry-media-canvas");
      for (let i = 0; i < all_media_canvases.length; i++)
        if (all_media_canvases[i].parentNode)
          all_media_canvases[i].parentNode.removeChild(all_media_canvases[i]);
    }

    //Clear scene and registries
    if (typeof scene !== "undefined" && scene?.map_component?.clear)
      scene.map_component.clear();
    if (naissance.Feature) naissance.Feature.instances = {};
    if (naissance.Geometry) naissance.Geometry.instances = {};
    if (DALS.deleted_ids) DALS.deleted_ids.clear();
    if (DALS._synced_deleted_ids) DALS._synced_deleted_ids.clear();
    if (DALS.dirty_ids) DALS.dirty_ids.clear();
    if (DALS.unsynced_dirty_ids) DALS.unsynced_dirty_ids.clear();
  };


  /**
   * Restores application state from either an in-memory JSON object or a lightweight DB timeline snapshot.
   *
   * @param {Object|string} [arg0_json]
   */
  DALS.fromJSON = async function (arg0_json) {
    //Convert from parameters
    let json = (arg0_json) ? arg0_json : {};
    if (typeof json === "string") json = JSON.parse(json);

    //Declare local instance variables
    let main_obj = (typeof main !== "undefined") ? main : (globalThis.main || global.main);


    //Fast-path: Restore from lightweight DB timeline snapshot (e.g. timeline branch head)
    if (json._is_db_snapshot && json.naissance_file_path) {
      await DALS.load(json.naissance_file_path, {
        is_replay: true,
        skip_map_settings: true
      });

      //1. Re-apply session deletions captured in snapshot
      if (Array.isArray(json.deleted_ids) && json.deleted_ids.length > 0) {
        for (let i = 0; i < json.deleted_ids.length; i++) {
          let del_id = String(json.deleted_ids[i]);
          if (naissance.Geometry?.instances?.[del_id])
            naissance.Geometry.instances[del_id].remove(true);
          if (naissance.Feature?.instances?.[del_id])
            naissance.Feature.instances[del_id].remove(true);
          DALS.deleted_ids.add(del_id);
          DALS._synced_deleted_ids.add(del_id);
        }
        if (global.db?.removeValues)
          await db.removeValues(json.deleted_ids.map(String));
      }

      //2. Re-apply dirty geometries captured in snapshot
      let snapshot_updates = {};
      if (json.dirty_geometries && typeof json.dirty_geometries === "object") {
        Object.iterate(json.dirty_geometries, (local_id, local_val) => {
          if (!local_val?.class_name || !naissance[local_val.class_name]) return;
          let geom_obj = naissance.Geometry?.instances?.[local_id];
          if (!geom_obj) {
            geom_obj = new naissance[local_val.class_name]({ is_import: true });
            geom_obj.setID(String(local_id));
          }
          if (local_val.metadata) geom_obj.metadata = structuredClone(local_val.metadata);
          geom_obj.history._is_loading_from_db = true;
          try {
            geom_obj.history.fromJSON(structuredClone(local_val.history || {}));
          } finally {
            geom_obj.history._is_loading_from_db = false;
          }
          DALS.dirty_ids.add(String(local_id));
          snapshot_updates[String(local_id)] = structuredClone(local_val);
        });
      }

      //3. Reconstruct feature hierarchy from snapshot
      if (json.features && typeof json.features === "object") {
        Object.iterate(naissance.Feature.instances, (local_id, local_feat) => {
          if (!json.features[local_id]) {
            local_feat.remove(true);
            DALS.deleted_ids.add(String(local_id));
            DALS._synced_deleted_ids.add(String(local_id));
            if (global.db?.removeValue) db.removeValue(String(local_id));
          }
        });

        Object.iterate(json.features, (local_id, local_val) => {
          if (!local_val?.class_name || !naissance[local_val.class_name]) return;
          let feat_obj = naissance.Feature?.instances?.[local_id];
          if (!feat_obj) {
            feat_obj = new naissance[local_val.class_name](undefined, {
              metadata: structuredClone(local_val.metadata || {})
            });
            feat_obj.setID(String(local_id));
          }
          if (local_val.metadata)
            feat_obj.metadata = structuredClone(local_val.metadata);
          feat_obj._is_visible = (local_val.is_visible !== false);
          feat_obj.json = structuredClone(local_val.value);
        });

        Object.iterate(naissance.Feature.instances, (local_id, local_feat) => {
          if (typeof local_feat.fromJSON === "function")
            local_feat.fromJSON(local_feat.json);
          try {
            if (local_feat.draw) local_feat.draw();
            if (local_feat._is_visible === false && local_feat.hide) local_feat.hide();
          } catch (e) { console.warn(e); }

          let feat_payload = DALS.serialiseFeature(local_feat);
          let snap_str = JSON.stringify(feat_payload);
          if (local_feat._clean_snapshot_str !== snap_str) {
            local_feat._clean_snapshot_str = snap_str;
            snapshot_updates[String(local_id)] = feat_payload;
          }
        });
      }

      if (Object.keys(snapshot_updates).length > 0 && global.db?.setValues)
        await db.setValues(snapshot_updates);
      DALS.unsynced_dirty_ids.clear();

      if (json.map_settings && global.UI_MapSettings?.fromJSON)
        UI_MapSettings.fromJSON(json.map_settings);

      DALS.scheduleRefresh(50);
      if (main_obj?.layers?.cursor_layer && main_obj?.brush?.cursor)
        main_obj.layers.cursor_layer.addGeometry(main_obj.brush.cursor);
      return;
    }

    //0. Clear map and exit DB mode when loading a non-DB state (such as initial {} head)
    DALS.clearMap();
    if (global.ve) {
      global.ve.naissance_file_path = null;
      global.ve.ndjson_file_path = null;
    }

    //1. Handle main map
    if (json.map_settings && global.UI_MapSettings?.fromJSON)
      UI_MapSettings.fromJSON(json.map_settings);

    //2. Iterate over JSON to load in each class
    Object.iterate(json, (local_key, local_value) => {
      if (local_value?.class_name && naissance[local_value.class_name]) {
        //2.1. Handle naissance.Geometry classes
        if (local_value.type === "geometry") {
          let geometry_obj = new naissance[local_value.class_name]({ is_import: true });

          //ID/History/Metadata deserialisation
          if (local_value.id) geometry_obj.setID(local_value.id);
          geometry_obj.history.fromJSON(local_value.history);
          if (local_value.metadata) geometry_obj.metadata = local_value.metadata;
        }
        //2.2. Handle naissance.Feature classes
        else if (local_value.type === "feature") {
          let feature_obj = new naissance[local_value.class_name](undefined, {
            metadata: local_value.metadata
          });

          if (local_value.id) feature_obj.setID(local_value.id);
          if (local_value.metadata) feature_obj.metadata = local_value.metadata;
          if (local_value.is_visible === false) feature_obj._is_visible = false;
          if (local_value.value) feature_obj.json = local_value.value;
        }
      }
    });
    DALS.dirty_ids.clear();
    DALS.unsynced_dirty_ids.clear();

    //3. Features must be rendered separately
    Object.iterate(naissance.Feature.instances, (local_key, local_feature) => {
      local_feature.fromJSON(local_feature.json);
      try {
        if (local_feature.draw) local_feature.draw();
        if (local_feature._is_visible === false) local_feature.hide();
      } catch (e) { console.warn(e); }
    });

    //4. Schedule coalesced UI and renderer refresh
    DALS.scheduleRefresh(50);

    //Reload cursor
    if (main_obj?.layers?.cursor_layer && main_obj?.brush?.cursor)
      main_obj.layers.cursor_layer.addGeometry(main_obj.brush.cursor);
  };


  /**
   * Loads a `.naissance` savefile via the multithreaded NDJSON DB (with <1 ms baseline replay fast-path) or non-DB fallback.
   *
   * @param {string} arg0_file_path
   * @param {Object} [arg1_options]
   *  @param {boolean} [arg1_options.is_replay=false]
   *  @param {boolean} [arg1_options.skip_map_settings=false]
   */
  DALS.load = async function (arg0_file_path, arg1_options) {
    //Convert from parameters
    let file_path = path.resolve(arg0_file_path);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let main_obj = (typeof main !== "undefined") ? main : (globalThis.main || global.main);


    if (!options.is_replay)
      console.log(`[DALS] Loading savefile via multithreaded DB: ${file_path}`);
    DALS.clearMap();

    if (global.db?.load) {
      let shard_folder = await db.load(file_path, {
        is_replay: Boolean(options.is_replay)
      });

      //Load map settings from metadata.json if present
      let folder_path = (global.db?.getCacheDirectory) ?
        db.getCacheDirectory(file_path) :
        ((global.NDJSON?.getCacheDirectory) ?
          NDJSON.getCacheDirectory(file_path) :
          path.resolve(process.cwd(), "saves/.cache", path.basename(file_path, path.extname(file_path))));
      let metadata_file = path.join(folder_path, "metadata.json");

      if (!global.ve) global.ve = {};
      global.ve.naissance_file_path = file_path;
      global.ve.ndjson_file_path = shard_folder || path.join(folder_path, "partition_0.ndjson");

      let metadata_json = {};
      if (fs.existsSync(metadata_file)) {
        try {
          let metadata_raw = await fs.promises.readFile(metadata_file, "utf8");
          if (metadata_raw.trim().length > 0)
            metadata_json = JSON.parse(metadata_raw);
        } catch (e) {
          console.error(e);
        }
      }

      //1. Populate UI Leftbar Hierarchy and instances BEFORE applying map settings and date
      let hierarchy_fn = global.db?.getHierarchyValues || global.NDJSON?.getHierarchyValues;
      if (hierarchy_fn) {
        let timestamp = (main_obj?.timestamp !== undefined) ? main_obj.timestamp :
          (main_obj?.date ? Date.getTimestamp(main_obj.date) : 0);
        let hierarchy_values = await hierarchy_fn(timestamp);

        if (Array.isArray(hierarchy_values)) {
          let feature_instances = [];

          for (let i = 0; i < hierarchy_values.length; i++) {
            let entry = hierarchy_values[i];
            let id = String(entry.key !== undefined ? entry.key : entry.id);
            let class_name = entry.class_name;

            if (class_name && naissance[class_name]) {
              if (class_name.startsWith("Feature")) {
                let feature_obj = new naissance[class_name](undefined, { metadata: entry.metadata });
                feature_obj.setID(id);
                if (entry.metadata) feature_obj.metadata = entry.metadata;
                if (entry.is_visible === false) feature_obj._is_visible = false;
                if (entry.value) feature_obj.json = entry.value;
                if (entry.name) feature_obj._name = entry.name;
                feature_instances.push(feature_obj);
              } else if (class_name.startsWith("Geometry")) {
                let geom_obj = new naissance[class_name]({ is_import: true });
                geom_obj.setID(id);
                if (entry.metadata) geom_obj.metadata = entry.metadata;
                if (entry.name) geom_obj._name = entry.name;
              }
            }
          }

          //Second pass: deserialise features and stamp clean snapshot strings after all geometries exist
          for (let i = 0; i < feature_instances.length; i++) {
            let feature_obj = feature_instances[i];
            if (feature_obj.json && typeof feature_obj.fromJSON === "function")
              feature_obj.fromJSON(feature_obj.json);
            feature_obj._clean_snapshot_str = JSON.stringify(DALS.serialiseFeature(feature_obj));
          }
        }
      }

      DALS.deleted_ids.clear();
      DALS._synced_deleted_ids.clear();
      DALS.dirty_ids.clear();
      DALS.unsynced_dirty_ids.clear();

      //2. Load global timestamps for Timeline Chronology
      let global_timestamps = metadata_json?.timestamps;

      if (!global_timestamps || !Array.isArray(global_timestamps) || global_timestamps.length === 0) {
        let timestamps_fn = global.db?.getTimestamps || global.NDJSON?.getTimestamps;
        if (timestamps_fn) {
          try {
            global_timestamps = await timestamps_fn();
            if (Array.isArray(global_timestamps) && global_timestamps.length > 0)
              metadata_json.timestamps = global_timestamps;
          } catch (e) {
            console.error("[DALS] Error loading global timestamps:", e);
          }
        }
      }

      if (main_obj?.renderer && Array.isArray(global_timestamps))
        main_obj.renderer.timestamps = global_timestamps;

      //3. Apply map settings and date from metadata.json now that instances exist
      if (!options.skip_map_settings && metadata_json && Object.keys(metadata_json).length > 0 && global.UI_MapSettings?.fromJSON)
        UI_MapSettings.fromJSON(metadata_json);

      //4. Schedule coalesced hierarchy refresh and renderer update
      DALS.scheduleRefresh(100);

      //Reload cursor
      if (main_obj?.layers?.cursor_layer && main_obj?.brush?.cursor)
        main_obj.layers.cursor_layer.addGeometry(main_obj.brush.cursor);

      return;
    }

    //Fallback for non-db environment
    try {
      let data = await fs.promises.readFile(file_path, "utf8");
      await DALS.fromJSON(data);
    } catch (err) {
      console.error(err);
    }
  };


  /**
   * Saves the current state either via the off-main-thread NDJSON streaming pipeline (in DB mode)
   * or via an asynchronous atomic streaming writer (in legacy/in-memory mode).
   *
   * @param {string} [arg0_target_path]
   *
   * @returns {Promise<string>}
   */
  DALS.save = async function (arg0_target_path) {
    //Convert from parameters
    let target_path = (arg0_target_path) ?
      path.resolve(arg0_target_path) :
      path.resolve(global.ve?.naissance_file_path || "saves/autosave.naissance");


    //DB Mode: Flush only dirty entities and stream shards into .naissance off the main thread
    if (global.ve?.ndjson_file_path && global.db?.save) {
      if (typeof DALS.flushPendingDBSync === "function")
        await DALS.flushPendingDBSync();
      await DALS.syncDirtyToDB();

      let file_path = global.ve.naissance_file_path || target_path;
      let folder_path = (global.db?.getCacheDirectory) ?
        db.getCacheDirectory(file_path) :
        ((global.NDJSON?.getCacheDirectory) ? global.NDJSON.getCacheDirectory(file_path) : null);

      //1. Update metadata.json asynchronously with latest map settings
      if (folder_path && fs.existsSync(folder_path)) {
        let metadata_path = path.join(folder_path, "metadata.json");
        let current_meta = {};
        if (fs.existsSync(metadata_path)) {
          try { current_meta = JSON.parse(await fs.promises.readFile(metadata_path, "utf8")); } catch (e) {}
        }
        if (global.UI_MapSettings?.toJSON && global.map) {
          try {
            let live_settings = UI_MapSettings.toJSON();
            current_meta = { ...current_meta, ...live_settings };
          } catch (e) {}
        }
        try {
          await fs.promises.writeFile(metadata_path, JSON.stringify(current_meta, null, 2), "utf8");
        } catch (e) {}
      }

      //2. Compile and atomically replace savefile via worker pipeline
      let saved_path = await db.save(target_path);
      global.ve.naissance_file_path = saved_path;
      let new_cache_dir = (global.db?.getCacheDirectory) ?
        db.getCacheDirectory(saved_path) : null;
      if (new_cache_dir)
        global.ve.ndjson_file_path = path.join(new_cache_dir, "partition_0.ndjson");

      //Return statement
      return saved_path;
    }

    //In-memory mode: Stream top-level JSON entries asynchronously and replace atomically
    let json_data = DALS.toJSON({ full: true });
    let target_dir = path.dirname(target_path);
    await fs.promises.mkdir(target_dir, { recursive: true });

    let bak_path = `${target_path}.bak`;
    let tmp_path = `${target_path}.tmp_${process.pid}_${Date.now()}`;
    let ws = fs.createWriteStream(tmp_path, { encoding: "utf8", highWaterMark: 4*1024*1024 });

    let writeChunk = (chunk) => new Promise((resolve, reject) => {
      if (ws.write(chunk)) {
        resolve();
      } else {
        ws.once("drain", resolve);
        ws.once("error", reject);
      }
    });

    try {
      let all_keys = Object.keys(json_data);
      await writeChunk("{\n");
      for (let i = 0; i < all_keys.length; i++) {
        let k = all_keys[i];
        let comma = (i < all_keys.length - 1) ? ",\n" : "\n";
        let line_str = `  ${JSON.stringify(k)}: ${JSON.stringify(json_data[k])}${comma}`;
        await writeChunk(line_str);
        if (i > 0 && i % 500 === 0)
          await new Promise((resolve) => setImmediate(resolve));
      }
      await writeChunk("}\n");
      await new Promise((resolve, reject) => {
        ws.end(() => resolve());
        ws.once("error", reject);
      });

      if (fs.existsSync(target_path)) {
        try { await fs.promises.unlink(bak_path); } catch (e) {}
        await fs.promises.rename(target_path, bak_path);
      }
      await fs.promises.rename(tmp_path, target_path);
    } catch (err) {
      try { ws.destroy(); } catch (e) {}
      try { if (fs.existsSync(tmp_path)) await fs.promises.unlink(tmp_path); } catch (e) {}
      console.error("[DALS] Failed to save in-memory file:", err);
      return target_path;
    }

    if (!global.ve) global.ve = {};
    global.ve.naissance_file_path = target_path;

    //Return statement
    return target_path;
  };


  /**
   * Serialises current state into a lightweight DB snapshot (when in DB mode and `options.full` is not set)
   * or a full `.naissance`-compatible JSON object.
   *
   * @param {Object} [arg0_options]
   *  @param {boolean} [arg0_options.full=false]
   *
   * @returns {Object}
   */
  DALS.toJSON = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let json_obj = {};


    //Set json_obj.map_settings
    try {
      if (global.map && global.UI_MapSettings?.toJSON)
        json_obj.map_settings = UI_MapSettings.toJSON();
    } catch (e) { console.error(e); }

    //Lightweight DB timeline snapshot for instant timeline branching
    if (global.ve?.ndjson_file_path && !options.full) {
      let dirty_geometries = {};
      let features = {};

      if (DALS.dirty_ids)
        for (let local_id of DALS.dirty_ids) {
          let inst = naissance.Geometry?.instances?.[local_id];
          if (inst)
            dirty_geometries[local_id] = DALS.serialiseGeometry(inst);
        }

      if (naissance.Feature?.instances)
        Object.iterate(naissance.Feature.instances, (local_key, local_feature) => {
          features[local_feature.id] = DALS.serialiseFeature(local_feature);
        });

      //Return statement
      return {
        _is_db_snapshot: true,
        deleted_ids: Array.from(DALS.deleted_ids || []),
        dirty_geometries: dirty_geometries,
        features: features,
        map_settings: json_obj.map_settings,
        naissance_file_path: global.ve.naissance_file_path,
        ndjson_file_path: global.ve.ndjson_file_path
      };
    }

    //Full serialisation: Iterate over all naissance.Geometry.instances
    Object.iterate(naissance.Geometry.instances, (local_key, local_geometry) => {
      json_obj[local_geometry.id] = DALS.serialiseGeometry(local_geometry);
    });

    //Iterate over all naissance.Feature.instances and serialise them
    Object.iterate(naissance.Feature.instances, (local_key, local_feature) => {
      json_obj[local_feature.id] = DALS.serialiseFeature(local_feature);
    });

    //Return statement
    return json_obj;
  };
}
