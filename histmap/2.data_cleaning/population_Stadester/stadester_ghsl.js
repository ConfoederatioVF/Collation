//Initialise functions
{
  if (!global.population_Stadester_ghsl) global.population_Stadester_ghsl = {};
  if (!global.population_Stadester_uud) global.population_Stadester_uud = {};
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
  if (!global.StadesterPartitionIO && typeof require !== "undefined")
    try { require(path.join(__dirname, "StadesterPartitionIO.js")); } catch (e) {}
  if (!global.population_Stadester_ghsl_helpers && typeof require !== "undefined")
    try { require(path.join(__dirname, "stadester_ghsl_helpers.js")); } catch (e) {}
  if (!global.population_Stadester_ghs_pop && typeof require !== "undefined")
    try { require(path.join(__dirname, "stadester_ghs_pop.js")); } catch (e) {}
  if ((!global.population_Stadester_uud.appendCitySources || !global.population_Stadester_uud.hasCitySource) && typeof require !== "undefined")
    try { require(path.join(__dirname, "stadester_uud_fixes.js")); } catch (e) {}
  
  /**
   * Integrates modern GHSL urban centre populations (1975-2025) into Stadestér by subtracting
   * non-primary Stadestér settlements falling within each GHSL DEGURBA areal mask and overwriting
   * the primary city's 1975-2025 population. Leaves all pre-1975 data untouched.
   * @alias population_Stadester_ghsl.integrateGHSLIntoStadester
   * 
   * @param {Object} arg0_stadester_obj
   * @param {Object} [arg1_options]
   * 
   * @returns {Object}
   */
  population_Stadester_ghsl.integrateGHSLIntoStadester = function (arg0_stadester_obj, arg1_options) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let built_entries;
    let cfg = global.population_Stadester_config;
    let city_entries = [];
    let city_grid = new Map();
    let cluster_members = new Map();
    let cutoff_year = (cfg && cfg.cutoff_year) ? cfg.cutoff_year : 1975;
    let end_year = 2025;
    let epochs = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025];
    let ghsl_by_id;
    let ghsl_folder = options.ghsl_mask_folder || path.join((typeof h1 !== "undefined") ? h1 : "./histmap/1.data_raw", "population_GHSL");
    let ghsl_json_path;
    let ghsl_obj = options.ghsl_obj;
    let integrated_count = 0;
    let pngjs_lib = (typeof pngjs !== "undefined") ? pngjs : (global.pngjs || require("pngjs"));
    let preserve_manual = (options.preserve_manual_entries !== undefined) ?
      options.preserve_manual_entries :
      ((cfg && cfg.preserve_manual_entries !== undefined) ? cfg.preserve_manual_entries : true);
    let raw_folder = options.raw_folder ? options.raw_folder : `${(typeof h1 !== "undefined") ? h1 : "./histmap/1.data_raw"}/population_Stadester/`;
    
    //Guard clauses
    if (!stadester_obj) return stadester_obj;
    
    //Function body
    if (!ghsl_obj) {
      ghsl_json_path = options.ghsl_file || path.join(raw_folder, "ghsl", "ghsl.json");
      if (!fs.existsSync(ghsl_json_path))
        ghsl_json_path = path.join(ghsl_folder, "ghsl.json");
      if (fs.existsSync(ghsl_json_path))
        ghsl_obj = JSON.parse(fs.readFileSync(ghsl_json_path, "utf8"));
    }
    if (!ghsl_obj) return stadester_obj;
    
    ghsl_by_id = population_Stadester_ghs_pop.loadCompleteUCDBMap(ghsl_obj, options);
    built_entries = population_Stadester_ghs_pop.buildGHSLCityEntries(stadester_obj, { cutoff_year: cutoff_year });
    city_entries = built_entries.city_entries;
    city_grid = built_entries.city_grid;
    
    //1. Match Stadestér settlements against epoch-specific GHSL GeoJSON and PNG areal masks (1975..2025)
    for (let i = 0; i < epochs.length; i++) {
      let ep = epochs[i];
      let geo_path = path.join(ghsl_folder, "geojson", `GHS_urban_${ep}.geojson`);
      let png_path = path.join(ghsl_folder, "urban_area_rasters", `GHS_urban_${ep}.png`);
      
      if (fs.existsSync(geo_path)) {
        let geo_obj = JSON.parse(fs.readFileSync(geo_path, "utf8"));
        let features = geo_obj.features || [];
        
        for (let x = 0; x < features.length; x++) {
          let feat = features[x];
          let uc_id = feat && feat.properties ? Number(feat.properties.ID_UC_G0) : 0;
          if (!uc_id || !ghsl_by_id.has(uc_id) || !feat.geometry) continue;
          
          let max_x = -180;
          let max_y = -90;
          let min_x = 180;
          let min_y = 90;
          let polys = (feat.geometry.type === "Polygon") ? [feat.geometry.coordinates] : (feat.geometry.coordinates || []);
          
          for (let y = 0; y < polys.length; y++) {
            let outer_ring = polys[y][0] || [];
            for (let z = 0; z < outer_ring.length; z++) {
              let pt_x = outer_ring[z][0];
              let pt_y = outer_ring[z][1];
              if (pt_x < min_x) min_x = pt_x;
              if (pt_x > max_x) max_x = pt_x;
              if (pt_y < min_y) min_y = pt_y;
              if (pt_y > max_y) max_y = pt_y;
            }
          }
          
          let gx_end = Math.floor(max_x);
          let gx_start = Math.floor(min_x);
          let gy_end = Math.floor(max_y);
          let gy_start = Math.floor(min_y);
          
          for (let gx = gx_start; gx <= gx_end; gx++) {
            for (let gy = gy_start; gy <= gy_end; gy++) {
              let cell_list = city_grid.get(`${gx},${gy}`);
              if (!cell_list) continue;
              
              for (let a = 0; a < cell_list.length; a++) {
                let ce = city_entries[cell_list[a]];
                if (ce.epoch_cluster[ep]) continue;
                if (ce.lng < min_x || ce.lng > max_x || ce.lat < min_y || ce.lat > max_y) continue;
                if (population_Stadester_ghsl.pointInGeometry(ce.lng, ce.lat, feat.geometry))
                  ce.epoch_cluster[ep] = uc_id;
              }
            }
          }
        }
      }
      
      if (fs.existsSync(png_path)) {
        let png_obj = pngjs_lib.PNG.sync.read(fs.readFileSync(png_path));
        let height = png_obj.height;
        let width = png_obj.width;
        
        for (let x = 0; x < city_entries.length; x++) {
          let ce = city_entries[x];
          if (ce.epoch_cluster[ep]) continue;
          
          let idx = (ce.py*width + ce.px)*4;
          let center_id = (((png_obj.data[idx] << 24) | (png_obj.data[idx + 1] << 16) | (png_obj.data[idx + 2] << 8) | png_obj.data[idx + 3]) >>> 0);
          if (center_id > 0 && ghsl_by_id.has(center_id)) {
            ce.epoch_cluster[ep] = center_id;
          } else {
            for (let dy = -1; dy <= 1 && !ce.epoch_cluster[ep]; dy++) {
              let ny = ce.py + dy;
              if (ny < 0 || ny >= height) continue;
              for (let dx = -1; dx <= 1; dx++) {
                if (dx === 0 && dy === 0) continue;
                let nx = ce.px + dx;
                if (nx < 0 || nx >= width) continue;
                let n_idx = (ny*width + nx)*4;
                let n_id = (((png_obj.data[n_idx] << 24) | (png_obj.data[n_idx + 1] << 16) | (png_obj.data[n_idx + 2] << 8) | png_obj.data[n_idx + 3]) >>> 0);
                if (n_id > 0 && ghsl_by_id.has(n_id)) {
                  let n_ghsl = ghsl_by_id.get(n_id);
                  let n_toks = String(n_ghsl.name || "").split(";").map(s => population_Stadester_ghsl.normaliseGHSLName(s)).filter(Boolean);
                  if (n_toks.length > 0 && population_Stadester_ghsl.matchesAnyGHSLToken(ce.norm_names, [n_toks[0]])) {
                    ce.epoch_cluster[ep] = n_id;
                    break;
                  }
                }
              }
            }
          }
        }
      }
    }
    
    //2. Group Stadestér settlements by GHSL cluster ID across 1975..2025
    for (let i = 0; i < city_entries.length; i++) {
      let ce = city_entries[i];
      for (let x = 0; x < epochs.length; x++) {
        let uc_id = ce.epoch_cluster[epochs[x]];
        if (uc_id) {
          if (!cluster_members.has(uc_id)) cluster_members.set(uc_id, new Set());
          cluster_members.get(uc_id).add(i);
        }
      }
    }
    
    //3A. Rank GHSL clusters by peak population and claim exclusive primary cities and twins
    let all_cluster_ids = Array.from(cluster_members.keys());
    let claimed_primary_set = new Set();
    let cluster_peaks = new Map();
    let cluster_plans = [];
    
    for (let i = 0; i < all_cluster_ids.length; i++) {
      let c_id = all_cluster_ids[i];
      let g_city = ghsl_by_id.get(c_id);
      let peak_val = 0;
      if (g_city && g_city.population) {
        for (let x = 0; x < epochs.length; x++) {
          let v = Number(g_city.population[epochs[x]]) || 0;
          if (v > peak_val) peak_val = v;
        }
      }
      cluster_peaks.set(c_id, peak_val);
    }
    all_cluster_ids.sort((a, b) => (cluster_peaks.get(b) || 0) - (cluster_peaks.get(a) || 0));
    
    for (let i = 0; i < all_cluster_ids.length; i++) {
      let uc_id = all_cluster_ids[i];
      let ghsl_city = ghsl_by_id.get(uc_id);
      if (!ghsl_city || !ghsl_city.population) continue;
      
      let earliest_ep = epochs[epochs.length - 1];
      let member_indices = Array.from(cluster_members.get(uc_id));
      let members = [];
      
      for (let x = 0; x < member_indices.length; x++)
        members.push(city_entries[member_indices[x]]);
      
      for (let x = 0; x < epochs.length; x++) {
        let ep = epochs[x];
        let has_ep = false;
        for (let y = 0; y < members.length; y++) {
          if (members[y].epoch_cluster[ep] === uc_id) {
            has_ep = true;
            break;
          }
        }
        if (has_ep) {
          earliest_ep = ep;
          break;
        }
      }
      
      let earliest_pool = [];
      for (let x = 0; x < members.length; x++)
        if (members[x].epoch_cluster[earliest_ep] === uc_id && !claimed_primary_set.has(members[x]))
          earliest_pool.push(members[x]);
      if (earliest_pool.length === 0) {
        for (let x = 0; x < members.length; x++)
          if (!claimed_primary_set.has(members[x]))
            earliest_pool.push(members[x]);
      }
      if (earliest_pool.length === 0) continue;
      
      let ghsl_tokens = String(ghsl_city.name || "").split(";").map(s => population_Stadester_ghsl.normaliseGHSLName(s)).filter(Boolean);
      let first_token = ghsl_tokens.length > 0 ? [ghsl_tokens[0]] : [];
      let primary_candidates = [];
      let token_candidates = [];
      
      for (let x = 0; x < earliest_pool.length; x++) {
        let m = earliest_pool[x];
        let ref_pop = population_Stadester_ghsl.getModernReferencePopulation({ population: m.raw_pop });
        if (ref_pop <= 0) continue;
        if (population_Stadester_ghsl.matchesAnyGHSLToken(m.norm_names, first_token))
          primary_candidates.push(m);
        if (population_Stadester_ghsl.matchesAnyGHSLToken(m.norm_names, ghsl_tokens))
          token_candidates.push(m);
      }
      if (primary_candidates.length === 0 && token_candidates.length === 0) {
        for (let x = 0; x < members.length; x++) {
          let m = members[x];
          if (claimed_primary_set.has(m)) continue;
          let ref_pop = population_Stadester_ghsl.getModernReferencePopulation({ population: m.raw_pop });
          if (ref_pop <= 0) continue;
          if (population_Stadester_ghsl.matchesAnyGHSLToken(m.norm_names, first_token))
            primary_candidates.push(m);
          if (population_Stadester_ghsl.matchesAnyGHSLToken(m.norm_names, ghsl_tokens))
            token_candidates.push(m);
        }
      }
      
      primary_candidates.sort((a, b) =>
        population_Stadester_ghsl.getModernReferencePopulation({ population: b.raw_pop }) -
        population_Stadester_ghsl.getModernReferencePopulation({ population: a.raw_pop })
      );
      token_candidates.sort((a, b) =>
        population_Stadester_ghsl.getModernReferencePopulation({ population: b.raw_pop }) -
        population_Stadester_ghsl.getModernReferencePopulation({ population: a.raw_pop })
      );
      earliest_pool.sort((a, b) =>
        population_Stadester_ghsl.getModernReferencePopulation({ population: b.raw_pop }) -
        population_Stadester_ghsl.getModernReferencePopulation({ population: a.raw_pop })
      );
      
      let chosen_list = primary_candidates;
      if (token_candidates.length > 0) {
        let best_tok_pop = population_Stadester_ghsl.getModernReferencePopulation({ population: token_candidates[0].raw_pop });
        let best_pri_pop = (chosen_list.length > 0) ?
          population_Stadester_ghsl.getModernReferencePopulation({ population: chosen_list[0].raw_pop }) : 0;
        if (chosen_list.length === 0 || best_tok_pop > best_pri_pop*1.5)
          chosen_list = token_candidates;
      }
      if (chosen_list.length === 0) {
        chosen_list = earliest_pool;
      } else if (earliest_pool.length > 0) {
        let best_pool_pop = population_Stadester_ghsl.getModernReferencePopulation({ population: earliest_pool[0].raw_pop });
        let best_chosen_pop = population_Stadester_ghsl.getModernReferencePopulation({ population: chosen_list[0].raw_pop });
        if (best_pool_pop > best_chosen_pop*2.0)
          chosen_list = earliest_pool;
      }
      
      let primary_entry = chosen_list[0];
      if (!primary_entry) continue;
      
      //Prefer non-agglomeration entry as primary record only when it represents the comparable core twin within 25 km
      if (primary_entry.key.toLowerCase().includes("agglomeration")) {
        let pri_ref_w = population_Stadester_ghsl.getClusterEntryReferenceWeight(primary_entry.raw_pop, earliest_ep);
        for (let x = 0; x < members.length; x++) {
          let m = members[x];
          if (claimed_primary_set.has(m) || m.key.toLowerCase().includes("agglomeration")) continue;
          let dist_km = population_Stadester_uud.haversineDistance(m.city.coords, primary_entry.city.coords);
          if (
            dist_km <= 25 &&
            population_Stadester_ghsl.isCoLocatedCityTwin(m, primary_entry, dist_km) &&
            population_Stadester_ghsl.getClusterEntryReferenceWeight(m.raw_pop, earliest_ep) >= 0.5*pri_ref_w
          ) {
            primary_entry = m;
            break;
          }
        }
      }
      
      //Group co-located same-name / agglomeration twins within primary jurisdiction
      let primary_group = [];
      for (let x = 0; x < members.length; x++) {
        let m = members[x];
        if (claimed_primary_set.has(m)) continue;
        let dist_km = (m === primary_entry) ? 0 : population_Stadester_uud.haversineDistance(m.city.coords, primary_entry.city.coords);
        if (
          m === primary_entry ||
          population_Stadester_ghsl.isCoLocatedCityTwin(m, primary_entry, dist_km)
        ) {
          primary_group.push(m);
          claimed_primary_set.add(m);
          m.locked_primary_uc_id = uc_id;
        }
      }
      
      cluster_plans.push({
        ghsl_city: ghsl_city,
        members: members,
        primary_entry: primary_entry,
        primary_group: primary_group,
        uc_id: uc_id
      });
    }
    
    //3B. Conserving proportional partition of PCHIP-smoothed GHSL totals (1975-2025)
    for (let i = 0; i < cluster_plans.length; i++) {
      let plan = cluster_plans[i];
      let ghsl_city = plan.ghsl_city;
      let members = plan.members;
      let primary_entry = plan.primary_entry;
      let primary_group = plan.primary_group;
      let uc_id = plan.uc_id;
      
      let pop_interp = population_Stadester_ghsl.interpolateGHSLSeries(ghsl_city.population);
      let first_active_ep = pop_interp.first_active_ep;
      if (!first_active_ep) continue;
      let area_interp = population_Stadester_ghsl.interpolateGHSLSeries(ghsl_city.area);
      
      let g0 = pop_interp.values[first_active_ep] || 0;
      let r_pri = population_Stadester_ghsl.getClusterEntryReferenceWeight(primary_entry.raw_pop, first_active_ep);
      let r_sum_grp = 0;
      for (let x = 0; x < primary_group.length; x++)
        r_sum_grp += population_Stadester_ghsl.getClusterEntryReferenceWeight(primary_group[x].raw_pop, first_active_ep);
      
      let w_primary = (primary_group.length > 1 && r_pri < 0.5*Math.min(g0, r_sum_grp)) ?
        Math.min(g0, r_sum_grp) : r_pri;
      w_primary = Math.max(1, w_primary);
      
      let sub_entries = [];
      for (let x = 0; x < members.length; x++) {
        let m = members[x];
        if (m.locked_primary_uc_id) continue;
        let sub_w = population_Stadester_ghsl.getClusterEntryReferenceWeight(m.raw_pop, first_active_ep);
        if (sub_w > 0)
          sub_entries.push({ sub: m, w_ref: sub_w });
      }
      
      if (!primary_entry.city.population) primary_entry.city.population = {};
      if (!primary_entry.city._ghsl_area) primary_entry.city._ghsl_area = {};
      
      for (let yr = cutoff_year; yr <= end_year; yr++) {
        let alpha = 1;
        if (first_active_ep > cutoff_year) {
          if (yr <= first_active_ep - 5) continue;
          if (yr < first_active_ep) alpha = (yr - (first_active_ep - 5))/5;
        }
        
        let eff_yr = Math.max(first_active_ep, yr);
        let g_pop = pop_interp.values[eff_yr];
        if (!Number.isFinite(g_pop) || g_pop <= 0) continue;
        let g_area = (area_interp && area_interp.values && area_interp.values[eff_yr] > 0) ?
          area_interp.values[eff_yr] : 0;
        
        let e0 = epochs[0];
        let e1 = epochs[epochs.length - 1];
        for (let a = 0; a < epochs.length - 1; a++) {
          if (yr >= epochs[a] && yr <= epochs[a + 1]) {
            e0 = epochs[a];
            e1 = epochs[a + 1];
            break;
          }
        }
        
        let active_subs = [];
        let frac = (e1 > e0) ? (yr - e0)/(e1 - e0) : 0;
        let sub_weight_sum = 0;
        
        for (let x = 0; x < sub_entries.length; x++) {
          let sub_info = sub_entries[x];
          let sub = sub_info.sub;
          let is_war_city = sub.city && (
            (Array.isArray(sub.city._war_displacement_years) && sub.city._war_displacement_years.length > 0) ||
            sub.city.polaris_source === "russian_invasion_of_ukraine"
          );
          if (is_war_city && Number.isFinite(sub.raw_min_year) && yr < sub.raw_min_year)
            continue;
          let w0 = (sub.epoch_cluster[e0] === uc_id) ? 1 : 0;
          let w1 = (sub.epoch_cluster[e1] === uc_id) ? 1 : 0;
          let w_raw = (1 - frac)*w0 + frac*w1;
          if (w_raw > 0) {
            let w_contrib = w_raw*sub_info.w_ref;
            sub_weight_sum += w_contrib;
            active_subs.push({ sub: sub, w_contrib: w_contrib, w_raw: w_raw });
          }
        }
        
        let denom = w_primary + sub_weight_sum;
        let p_ghsl = g_pop*(w_primary/denom);
        let a_ghsl = (g_area > 0) ? g_area*(w_primary/denom) : 0;
        
        primary_entry.has_ucdb = true;
        primary_entry.ucdb_weight_by_year[yr] = alpha;
        primary_entry.ucdb_pop_by_year[yr] = p_ghsl;
        
        if (alpha >= 1 - 1e-9) {
          let g_pop_int = Math.round(g_pop);
          let sub_int_total = 0;
          
          for (let x = 0; x < active_subs.length; x++) {
            let item = active_subs[x];
            let sub = item.sub;
            let s_share = g_pop*(item.w_contrib/denom);
            let s_int = Math.min(Math.max(0, g_pop_int - sub_int_total), Math.round(s_share));
            let a_sub = (g_area > 0) ? g_area*(item.w_contrib/denom) : 0;
            
            sub_int_total += s_int;
            if (!sub.ghsl_w_sum) sub.ghsl_w_sum = {};
            if (!sub.ghsl_pop_sum) sub.ghsl_pop_sum = {};
            if (!sub.ghsl_area_sum) sub.ghsl_area_sum = {};
            sub.ghsl_w_sum[yr] = (sub.ghsl_w_sum[yr] || 0) + item.w_raw;
            sub.ghsl_pop_sum[yr] = (sub.ghsl_pop_sum[yr] || 0) + s_int;
            sub.ghsl_area_sum[yr] = (sub.ghsl_area_sum[yr] || 0) + a_sub;
          }
          
          primary_entry.city.population[yr] = Math.max(0, g_pop_int - sub_int_total);
          if (a_ghsl > 0) primary_entry.city._ghsl_area[yr] = a_ghsl;
          
          for (let x = 0; x < primary_group.length; x++) {
            let twin = primary_group[x];
            if (twin !== primary_entry && twin.city.population) {
              twin.is_suppressed_ucdb_twin = true;
              twin.city.population[yr] = 0;
              if (!twin.city._ghsl_area) twin.city._ghsl_area = {};
              twin.city._ghsl_area[yr] = 0;
            }
          }
        } else {
          let pri_raw = population_Stadester_ghsl.getContinuousCityPopulation(primary_entry.raw_pop, yr);
          if (pri_raw > 0)
            primary_entry.city.population[yr] = Math.max(0, Math.round((1 - alpha)*pri_raw + alpha*p_ghsl));
          if (a_ghsl > 0) {
            if (!primary_entry.city._ghsl_area_partial) primary_entry.city._ghsl_area_partial = {};
            primary_entry.city._ghsl_area_partial[yr] = { area: alpha*a_ghsl, weight: alpha };
          }
          
          for (let x = 0; x < primary_group.length; x++) {
            let twin = primary_group[x];
            if (twin !== primary_entry && twin.city.population) {
              twin.is_suppressed_ucdb_twin = true;
              let twin_raw = population_Stadester_ghsl.getContinuousCityPopulation(twin.raw_pop, yr);
              twin.city.population[yr] = Math.max(0, Math.round((1 - alpha)*twin_raw));
            }
          }
          
          for (let x = 0; x < active_subs.length; x++) {
            let item = active_subs[x];
            let sub = item.sub;
            let s_share = g_pop*(item.w_contrib/denom);
            let a_sub = (g_area > 0) ? g_area*(item.w_contrib/denom) : 0;
            if (!sub.ghsl_w_sum) sub.ghsl_w_sum = {};
            if (!sub.ghsl_pop_sum) sub.ghsl_pop_sum = {};
            if (!sub.ghsl_area_sum) sub.ghsl_area_sum = {};
            sub.ghsl_w_sum[yr] = (sub.ghsl_w_sum[yr] || 0) + alpha*item.w_raw;
            sub.ghsl_pop_sum[yr] = (sub.ghsl_pop_sum[yr] || 0) + alpha*s_share;
            sub.ghsl_area_sum[yr] = (sub.ghsl_area_sum[yr] || 0) + alpha*a_sub;
          }
        }
      }
      
      if (primary_entry.has_ucdb && !(preserve_manual && population_Stadester_uud.hasCitySource(primary_entry.city, "manual")))
        population_Stadester_uud.appendCitySources(primary_entry.city, "ghsl");
      integrated_count++;
    }
    
    //3C. Finalise subordinate settlement populations across all GHSL clusters
    for (let i = 0; i < city_entries.length; i++) {
      let ce = city_entries[i];
      if (ce.locked_primary_uc_id || !ce.ghsl_w_sum) continue;
      if (!ce.city.population) ce.city.population = {};
      let did_write_ghsl = false;
      
      for (let yr = cutoff_year; yr <= end_year; yr++) {
        let w_raw_sum = ce.ghsl_w_sum[yr] || 0;
        if (w_raw_sum <= 0) continue;
        
        let area_sum = ce.ghsl_area_sum[yr] || 0;
        let pop_sum = ce.ghsl_pop_sum[yr] || 0;
        let w_tot = Math.min(1, w_raw_sum);
        if (w_raw_sum > 1) {
          area_sum = area_sum*(1/w_raw_sum);
          pop_sum = pop_sum*(1/w_raw_sum);
        }
        
        ce.has_ucdb = true;
        ce.ucdb_weight_by_year[yr] = w_tot;
        ce.ucdb_pop_by_year[yr] = pop_sum;
        
        if (w_tot >= 1 - 1e-9) {
          ce.city.population[yr] = Math.max(0, Math.round(pop_sum));
          did_write_ghsl = true;
          if (area_sum > 0) {
            if (!ce.city._ghsl_area) ce.city._ghsl_area = {};
            ce.city._ghsl_area[yr] = area_sum;
          }
        } else {
          let out_pop = (1 - w_tot)*population_Stadester_ghsl.getContinuousCityPopulation(ce.raw_pop, yr);
          if (out_pop > 0) {
            ce.city.population[yr] = Math.max(0, Math.round(out_pop + pop_sum));
            did_write_ghsl = true;
          }
          if (area_sum > 0) {
            if (!ce.city._ghsl_area_partial) ce.city._ghsl_area_partial = {};
            ce.city._ghsl_area_partial[yr] = { area: area_sum, weight: w_tot };
          }
        }
      }
      if (did_write_ghsl && !(preserve_manual && population_Stadester_uud.hasCitySource(ce.city, "manual")))
        population_Stadester_uud.appendCitySources(ce.city, "ghsl");
    }
    
    console.log(`- Integrated GHSL (1975-2025) DEGURBA areal mask populations into ${integrated_count} primary Stadestér cities.`);
    
    //3D. Partition 5-arcmin GHS-POP gridcells across post-empirical years for settlements missing GHS-UCDB coverage and restore protected overrides
    population_Stadester_ghs_pop.partitionGHSPopGridcells(stadester_obj, city_entries, options);
    population_Stadester_ghs_pop.restoreManualEntries(city_entries, options);
    population_Stadester_ghs_pop.restoreWarDisplacementYears(city_entries, options);
    
    //Return statement
    return stadester_obj;
  };
  
  //Expose on population_Stadester_uud for pipeline compatibility
  population_Stadester_uud.integrateGHSLIntoStadester = population_Stadester_ghsl.integrateGHSLIntoStadester;
}

