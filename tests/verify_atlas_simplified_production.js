let fs = require("fs");
let path = require("path");

if (!global.ve) global.ve = { registry: { settings: {} } };
try { require(path.resolve(process.cwd(), "UF/js/date/date_basic.js")); } catch (e) {}
try { require(path.resolve(process.cwd(), "UF/js/date/date_conversion.js")); } catch (e) {}
let turf = require(path.resolve(process.cwd(), "UF/js/geospatiale/turf.min.js"));
let polities_join = require(path.resolve(process.cwd(), "histmap/3.data_transform/polities_atlas_join/polities_atlas_join.js"));

let results = {
  details: {},
  errors: [],
  gates_passed: 0,
  total_gates: 6
};

console.log("=== COMPREHENSIVE PRODUCTION VERIFICATION FOR saves/atlas_simplified.naissance ===");

// -------------------------------------------------------------
// GATE 1: File Existence, Parse Validity & Structural Integrity
// -------------------------------------------------------------
console.log("\n[Gate 1] Checking File Size and Top-level Entities...");
let savefile_path = "saves/atlas_simplified.naissance";
if (!fs.existsSync(savefile_path)) {
  console.error("FAIL: saves/atlas_simplified.naissance does not exist!");
  process.exit(1);
}

let stat = fs.statSync(savefile_path);
let file_size_mb = (stat.size / 1024 / 1024).toFixed(2);
console.log(`- File Size: ${file_size_mb} MB`);

let raw_data = fs.readFileSync(savefile_path, "utf8");
let savefile = JSON.parse(raw_data);
let entity_keys = Object.keys(savefile);
console.log(`- Total entities: ${entity_keys.length}`);

let fg_count = 0;
let poly_count = 0;
for (let k of entity_keys) {
  if (savefile[k].class_name === "FeatureGroup") fg_count++;
  if (savefile[k].class_name === "GeometryPolygon") poly_count++;
}
console.log(`- FeatureGroups: ${fg_count}, Polygons: ${poly_count}`);
console.log(`- map_settings: ${savefile.map_settings ? "Present" : "Missing"}`);

if (poly_count > 100 && fg_count > 0 && savefile.map_settings) {
  console.log("PASS: Gate 1 passed.");
  results.gates_passed++;
} else {
  results.errors.push("Gate 1: Incomplete top-level structure");
}

// -------------------------------------------------------------
// GATE 2: Area Comparison: Area(Simplified) >= Area(Atlas)
// -------------------------------------------------------------
console.log("\n[Gate 2] Verifying Area(Simplified) >= Area(Atlas) across Epochs...");
let atlas = JSON.parse(fs.readFileSync("saves/atlas.naissance", "utf8"));

function computeTotalArea(file_obj, year) {
  let ts = Date.getTimestamp({ minute: 1, year: year });
  let total_sqkm = 0;
  let active_count = 0;

  for (let k in file_obj) {
    let ent = file_obj[k];
    if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;

    let state = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts);
    if (!state || !state.geometry) continue;

    try {
      let feat = turf.feature(state.geometry);
      let a = turf.area(feat) / 1e6;
      if (a > 0) {
        total_sqkm += a;
        active_count++;
      }
    } catch (e) {}
  }
  return { area: total_sqkm, count: active_count };
}

let test_years = [-1000, -500, 0, 500, 1000, 1500, 1700, 1800, 1850, 1900, 1945, 1950, 2000, 2014];
let area_failures = [];

console.log("Year | Atlas Area (M km²) | Simplified Area (M km²) | Delta (%) | Simp >= Atlas?");
console.log("-----|---------------------|--------------------------|-----------|---------------");

for (let y of test_years) {
  let atlas_res = computeTotalArea(atlas, y);
  let simp_res = computeTotalArea(savefile, y);

  let a_m = (atlas_res.area / 1e6).toFixed(2);
  let s_m = (simp_res.area / 1e6).toFixed(2);
  let delta_pct = atlas_res.area > 0 ? (((simp_res.area - atlas_res.area) / atlas_res.area) * 100).toFixed(1) : "0.0";
  let ok = simp_res.area >= atlas_res.area * 0.999; // Allow 0.1% tolerance

  console.log(`${String(y).padStart(4)} | ${String(a_m).padStart(19)} | ${String(s_m).padStart(24)} | ${String(delta_pct + "%").padStart(9)} | ${ok ? "PASS" : "FAIL"}`);

  if (!ok) {
    area_failures.push({ atlas: a_m, simp: s_m, year: y });
  }
}

if (area_failures.length === 0) {
  console.log("PASS: Gate 2 passed - Total Simplified Area >= Atlas Area across all epochs.");
  results.gates_passed++;
} else {
  results.errors.push(`Gate 2: Area check failed in years: ${area_failures.map(f => f.year).join(", ")}`);
}

// -------------------------------------------------------------
// GATE 3: Disappeared Countries Coverage Verification
// -------------------------------------------------------------
console.log("\n[Gate 3] Verifying Formerly Missing Countries...");
let capitals = [
  { coords: [-68.15, -16.50], country: "Bolivia", years: [1830, 1850, 1900, 1950, 2014] },
  { coords: [-57.63, -25.28], country: "Paraguay", years: [1820, 1850, 1900, 1950, 2014] },
  { coords: [10.75, 59.91], country: "Norway", years: [1820, 1900, 1946, 1950, 2014] },
  { coords: [37.47, 12.60], country: "Ethiopia (Gondar)", years: [1850] },
  { coords: [38.74, 9.03], country: "Ethiopia (Addis Ababa)", years: [1900, 1930, 1950, 2014] },
  { coords: [-70.66, -33.45], country: "Chile", years: [1830, 1900, 1950, 2000, 2014] },
  { coords: [104.92, 11.56], country: "Cambodia", years: [1960, 1980, 2000, 2014] },
  { coords: [35.92, 31.95], country: "Jordan", years: [1950, 1980, 2000, 2014] },
  { coords: [-75.69, 45.42], country: "Canada (Ottawa)", years: [1870, 1900, 1950, 2014] },
  { coords: [-77.03, 38.90], country: "USA (DC)", years: [1800, 1850, 1900, 1950, 2014] },
  { coords: [-118.24, 34.05], country: "USA (LA)", years: [1850, 1900, 1950, 2014] },
  { coords: [-0.12, 51.50], country: "UK (London)", years: [1800, 1850, 1900, 1950, 2014] }
];

let coverage_failures = [];

for (let c of capitals) {
  let pt = turf.point(c.coords);
  for (let y of c.years) {
    let ts = Date.getTimestamp({ minute: 1, year: y });
    let covered = false;
    let matched_id = "";
    let matched_name = "";

    for (let k in savefile) {
      let ent = savefile[k];
      if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;

      let state = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts);
      if (!state || !state.geometry) continue;

      try {
        let feat = turf.feature(state.geometry);
        if (turf.booleanPointInPolygon(pt, feat)) {
          covered = true;
          matched_id = ent.id;
          matched_name = (state.properties && state.properties.name) || (ent.metadata && ent.metadata.description.split("\n")[0]);
          break;
        }
      } catch (e) {}
    }

    if (covered) {
      console.log(`- ${c.country} at Year ${y}: COVERED by ${matched_id} (${matched_name})`);
    } else {
      console.log(`- ${c.country} at Year ${y}: NOT COVERED!`);
      coverage_failures.push(`${c.country} at ${y}`);
    }
  }
}

if (coverage_failures.length === 0) {
  console.log("PASS: Gate 3 passed - All tested countries covered throughout their historical lifespans.");
  results.gates_passed++;
} else {
  results.errors.push(`Gate 3: Coverage failures: ${coverage_failures.join(", ")}`);
}

// -------------------------------------------------------------
// GATE 4: Parenthetical Peer Merging (Burma Shan States & Princely States)
// -------------------------------------------------------------
console.log("\n[Gate 4] Checking Peer Constituent Merging (Burma Shan States & Indian Princely States)...");
let ts_burma = Date.getTimestamp({ minute: 1, year: 1900 });
let burma_ents = [];
let burma_taunggyi = turf.point([97.03, 20.78]); // Shan States capital
let burma_covered_by = null;

for (let k of entity_keys) {
  let ent = savefile[k];
  if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;

  let desc = (ent.metadata && ent.metadata.description) || "";
  if (desc.includes("SeshatID: (Burma)")) {
    burma_ents.push(ent);
    let state = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts_burma);
    if (state && state.geometry) {
      try {
        if (turf.booleanPointInPolygon(burma_taunggyi, turf.feature(state.geometry))) {
          burma_covered_by = ent;
        }
      } catch (e) {}
    }
  }
}

console.log(`- Entities with SeshatID: (Burma) in savefile: ${burma_ents.length} (Expected: 1 merged polity)`);
console.log(`- Taunggyi (Shan States) covered by merged Burma: ${!!burma_covered_by}`);

let ts_raj = Date.getTimestamp({ minute: 1, year: 1935 });
let raj_ents = [];
let raj_gwalior = turf.point([78.18, 26.22]);
let raj_covered_by = null;

for (let k of entity_keys) {
  let ent = savefile[k];
  if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;

  let desc = (ent.metadata && ent.metadata.description) || "";
  if (desc.includes("SeshatID: (British Raj)")) {
    raj_ents.push(ent);
    let state = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts_raj);
    if (state && state.geometry) {
      try {
        if (turf.booleanPointInPolygon(raj_gwalior, turf.feature(state.geometry))) {
          raj_covered_by = ent;
        }
      } catch (e) {}
    }
  }
}

console.log(`- Entities with SeshatID: (British Raj) in savefile: ${raj_ents.length} (Expected: 1 merged polity)`);
console.log(`- Gwalior (Princely States) covered by merged British Raj: ${!!raj_covered_by}`);

if (burma_ents.length === 1 && raj_ents.length === 1 && burma_covered_by && raj_covered_by) {
  console.log("PASS: Gate 4 passed - Peer constituents sharing parenthetical Seshat IDs are cleanly merged.");
  results.gates_passed++;
} else {
  results.errors.push(`Gate 4: Peer merging check failed: burma_ents=${burma_ents.length}, raj_ents=${raj_ents.length}`);
}

// -------------------------------------------------------------
// GATE 5: Metropole Defence & Semantic Separation Check
// -------------------------------------------------------------
console.log("\n[Gate 5] Verifying Metropole Defence (France/Syria, HRE/Arles, UK/Sudan)...");
let metropole_defence_ok = true;

// 1. France at 1922
let ts_1922 = Date.getTimestamp({ minute: 1, year: 1922 });
let paris = turf.point([2.35, 48.85]);
let damascus = turf.point([36.29, 33.51]);
let france_ent_1922 = null;
let syria_ent_1922 = null;

for (let k of entity_keys) {
  let ent = savefile[k];
  if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;
  let state = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts_1922);
  if (!state || !state.geometry) continue;

  try {
    let f = turf.feature(state.geometry);
    if (turf.booleanPointInPolygon(paris, f)) france_ent_1922 = { ent, state };
    if (turf.booleanPointInPolygon(damascus, f)) syria_ent_1922 = { ent, state };
  } catch (e) {}
}

let fr_name = france_ent_1922 ? (france_ent_1922.state.properties.name || "") : "NONE";
let sy_name = syria_ent_1922 ? (syria_ent_1922.state.properties.name || "") : "NONE";
let fr_id = france_ent_1922 ? france_ent_1922.ent.id : "NONE";
let sy_id = syria_ent_1922 ? syria_ent_1922.ent.id : "NONE";

console.log(`- France (Paris) at 1922: ID=${fr_id}, Name="${fr_name}"`);
console.log(`- Syria (Damascus) at 1922: ID=${sy_id}, Name="${sy_name}"`);

if (fr_id === sy_id || !fr_name.toLowerCase().includes("french") || fr_name.toLowerCase().includes("syria") || fr_name.toLowerCase().includes("mandate")) {
  console.error("FAIL: France merged into French Mandate for Syria!");
  metropole_defence_ok = false;
}

// 2. HRE at 1050
let ts_1050 = Date.getTimestamp({ minute: 1, year: 1050 });
let frankfurt = turf.point([8.68, 50.11]);
let arles_pt = turf.point([4.6, 47.0]); // Historical Kingdom of Arles (Burgundy)
let hre_ent_1050 = null;
let arles_ent_1050 = null;

for (let k of entity_keys) {
  let ent = savefile[k];
  if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;
  let state = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts_1050);
  if (!state || !state.geometry) continue;

  try {
    let f = turf.feature(state.geometry);
    if (turf.booleanPointInPolygon(frankfurt, f)) hre_ent_1050 = { ent, state };
    if (turf.booleanPointInPolygon(arles_pt, f)) arles_ent_1050 = { ent, state };
  } catch (e) {}
}

let hre_name = hre_ent_1050 ? (hre_ent_1050.state.properties.name || "") : "NONE";
let arles_name = arles_ent_1050 ? (arles_ent_1050.state.properties.name || "") : "NONE";
let hre_id = hre_ent_1050 ? hre_ent_1050.ent.id : "NONE";
let arles_id = arles_ent_1050 ? arles_ent_1050.ent.id : "NONE";

console.log(`- HRE (Frankfurt) at 1050: ID=${hre_id}, Name="${hre_name}"`);
console.log(`- Arles at 1050: ID=${arles_id}, Name="${arles_name}"`);

if (hre_id === arles_id || hre_name.toLowerCase().includes("arles") || !hre_name.toLowerCase().includes("holy roman empire")) {
  console.error("FAIL: Kingdom of Arles annexed the Holy Roman Empire!");
  metropole_defence_ok = false;
}

// 3. UK at 1900
let ts_1900 = Date.getTimestamp({ minute: 1, year: 1900 });
let london = turf.point([-0.12, 51.50]);
let khartoum = turf.point([32.53, 15.50]);
let uk_ent_1900 = null;
let sudan_ent_1900 = null;

for (let k of entity_keys) {
  let ent = savefile[k];
  if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;
  let state = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts_1900);
  if (!state || !state.geometry) continue;

  try {
    let f = turf.feature(state.geometry);
    if (turf.booleanPointInPolygon(london, f)) uk_ent_1900 = { ent, state };
    if (turf.booleanPointInPolygon(khartoum, f)) sudan_ent_1900 = { ent, state };
  } catch (e) {}
}

let uk_name = uk_ent_1900 ? (uk_ent_1900.state.properties.name || "") : "NONE";
let sudan_name = sudan_ent_1900 ? (sudan_ent_1900.state.properties.name || "") : "NONE";
let uk_id = uk_ent_1900 ? uk_ent_1900.ent.id : "NONE";
let sudan_id = sudan_ent_1900 ? sudan_ent_1900.ent.id : "NONE";

console.log(`- UK (London) at 1900: ID=${uk_id}, Name="${uk_name}"`);
console.log(`- Sudan (Khartoum) at 1900: ID=${sudan_id}, Name="${sudan_name}"`);

if (uk_id === sudan_id || uk_name.toLowerCase().includes("sudan") || uk_name.toLowerCase().includes("india")) {
  console.error("FAIL: UK overwritten by colony/condominium!");
  metropole_defence_ok = false;
}

// 4. Germany across 1934-1944 (must ALWAYS be Nazi Germany, never Kingdom of Greece or Czechoslovakia)
let berlin = turf.point([13.40, 52.52]);
let athens = turf.point([23.72, 37.98]);
let test_years_germany = [1934, 1939, 1941, 1944];
let germany_names_seen = [];

for (let yr of test_years_germany) {
  let ts = Date.getTimestamp({ minute: 1, year: yr });
  for (let k of entity_keys) {
    let ent = savefile[k];
    if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;
    let state = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts);
    if (!state || !state.geometry) continue;
    try {
      if (turf.booleanPointInPolygon(berlin, turf.feature(state.geometry))) {
        let n = state.properties.name || "";
        germany_names_seen.push(`${yr}:${n}`);
        if (n.toLowerCase().includes("greece") || n.toLowerCase().includes("czechoslovakia")) {
          console.error(`FAIL: Germany at ${yr} renamed to "${n}"!`);
          metropole_defence_ok = false;
        }
      }
    } catch (e) {}
  }
}
console.log(`- Germany (Berlin) across WWII: ${germany_names_seen.join(", ")}`);

// 5. Check no entities have name mutations across keyframes
let entities_with_name_mutations = 0;
for (let k of entity_keys) {
  let ent = savefile[k];
  if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;
  let seen_names = new Set();
  for (let ts in ent.history) {
    let kf = ent.history[ts];
    if (kf && kf[2] && kf[2].name) seen_names.add(kf[2].name);
  }
  if (seen_names.size > 1) entities_with_name_mutations++;
}
console.log(`- Entities with name mutations across keyframes: ${entities_with_name_mutations} (Expected: 0)`);
if (entities_with_name_mutations > 0) {
  console.error(`FAIL: ${entities_with_name_mutations} polities mutate names across keyframes!`);
  metropole_defence_ok = false;
}

if (metropole_defence_ok) {
  console.log("PASS: Gate 5 passed - Semantic defence check prevents dependencies from annexing/renaming metropoles.");
  results.gates_passed++;
} else {
  results.errors.push("Gate 5: Metropole defence check failed");
}

// -------------------------------------------------------------
// GATE 6: Keyframe Diff Ratio & Redundancy Check
// -------------------------------------------------------------
console.log("\n[Gate 6] Checking Keyframe Diff Pattern...");
let total_kfs = 0;
let kf_len_dist = { 1: 0, 2: 0, 3: 0 };
let dup_props = 0;

for (let k of entity_keys) {
  let ent = savefile[k];
  if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;

  let ts_keys = Object.keys(ent.history).sort((a, b) => Number(a) - Number(b));
  let last_seen_props = null;
  let is_active = false;

  for (let i = 0; i < ts_keys.length; i++) {
    let kf = ent.history[ts_keys[i]];
    total_kfs++;
    let len = kf.length;
    kf_len_dist[len] = (kf_len_dist[len] || 0) + 1;

    if (kf[0] === null) {
      is_active = false;
      continue;
    }

    if (!is_active) {
      is_active = true;
      last_seen_props = kf[2] || last_seen_props;
      continue;
    }

    let props = kf[2];
    if (props) {
      if (last_seen_props) {
        let is_dup = true;
        for (let p in props) {
          if (props[p] !== last_seen_props[p]) { is_dup = false; break; }
        }
        if (is_dup) dup_props++;
      }
      last_seen_props = Object.assign({}, last_seen_props, props);
    }
  }
}

let len1_ratio = ((kf_len_dist[1] / total_kfs) * 100).toFixed(1);
console.log(`- Keyframe distribution: Total=${total_kfs}, len1=${kf_len_dist[1]} (${len1_ratio}%), len2=${kf_len_dist[2]}, len3=${kf_len_dist[3]}`);
console.log(`- Duplicate properties count: ${dup_props}`);

if (Number(len1_ratio) >= 70 && dup_props === 0) {
  console.log("PASS: Gate 6 passed - Sparse diff pattern with >=70% length-1 and 0 redundant properties.");
  results.gates_passed++;
} else {
  results.errors.push(`Gate 6: Diff pattern len1_ratio=${len1_ratio}%, dup_props=${dup_props}`);
}

console.log(`\n========================================`);
console.log(`RESULTS: ${results.gates_passed} / ${results.total_gates} gates passed.`);
if (results.errors.length > 0) {
  console.log("Errors:", results.errors);
  process.exit(1);
} else {
  console.log("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!");
  process.exit(0);
}
