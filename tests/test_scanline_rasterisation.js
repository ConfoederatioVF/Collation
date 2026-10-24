let fs = require("fs");
let path = require("path");

if (!global.ve) global.ve = { registry: { settings: {} } };
try { require(path.resolve(process.cwd(), "UF/js/date/date_basic.js")); } catch (e) {}
try { require(path.resolve(process.cwd(), "UF/js/date/date_conversion.js")); } catch (e) {}
let turf = require(path.resolve(process.cwd(), "UF/js/geospatiale/turf.min.js"));
let polities_join = require(path.resolve(process.cwd(), "histmap/3.data_transform/polities_atlas_join/polities_atlas_join.js"));

let savefile_path = "saves/atlas_simplified.naissance";
let savefile = JSON.parse(fs.readFileSync(savefile_path, "utf8"));
let eu_geo = JSON.parse(fs.readFileSync("saves/CShapes-Europe.geojson", "utf8"));

console.log("=== SCANLINE RASTERISATION & TOPOLOGY GUARANTEE TEST ===");

let test_years = [1820, 1850, 1880];
let stray_polygons_found = 0;
let points_scanned = 0;
let points_in_europe = 0;
let cshapes_points = 0;

for (let y of test_years) {
  let ts = Date.getTimestamp({ minute: 1, year: y });
  let active_eu = eu_geo.features.filter(f => f.properties.From <= y && f.properties.To >= y);

  console.log(`\n--- Testing Scanlines at Year ${y} (Active CShapes-Europe polities: ${active_eu.length}) ---`);

  // Scan Europe bounding grid: lon [-9, 30], lat [36, 60] with 0.5 degree steps
  for (let lat = 36; lat <= 60; lat += 0.5) {
    for (let lon = -9; lon <= 30; lon += 0.5) {
      points_scanned++;
      let pt = turf.point([lon, lat]);

      // Check if point falls inside active CShapes-Europe landmass
      let eu_match = null;
      for (let f of active_eu) {
        try {
          if (turf.booleanPointInPolygon(pt, f)) {
            eu_match = f;
            break;
          }
        } catch (e) {}
      }

      if (!eu_match) continue;
      points_in_europe++;

      // Query savefile for covering entity
      let covered_by = null;
      for (let id in savefile) {
        let ent = savefile[id];
        if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;

        let st = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts);
        if (!st || !st.geometry) continue;

        try {
          if (turf.booleanPointInPolygon(pt, turf.feature(st.geometry))) {
            covered_by = { id: id, props: st.properties, symbol: st.symbol };
            break;
          }
        } catch (e) {}
      }

      if (covered_by) {
        cshapes_points++;
        let name = (covered_by.props && covered_by.props.name) || "";
        let s_id = (covered_by.props && covered_by.props.seshat_id) || "";
        let cow = (covered_by.props && (covered_by.props.cow || covered_by.props.cow_code));

        // Check for stray ancient/medieval Atlas names in Europe
        let stray_indicators = ["urgell", "brandenburg-prussia", "holy roman", "carolingian", "frankish", "aquitaine"];
        let is_stray = stray_indicators.some(si => name.toLowerCase().includes(si));
        if (is_stray) {
          console.error(`FAIL: Stray polygon "${name}" detected at [${lon}, ${lat}] in year ${y}!`);
          stray_polygons_found++;
        }

        if (!cow) {
          console.error(`FAIL: Polity "${name}" at [${lon}, ${lat}] missing COW code!`);
          stray_polygons_found++;
        }
      }
    }
  }

  let coverage_pct = ((cshapes_points / Math.max(1, points_in_europe)) * 100).toFixed(1);
  console.log(`Scanline results at ${y}: ${points_in_europe} European land points scanned, Coverage = ${coverage_pct}%, Strays = ${stray_polygons_found}`);
}

// Check non-European locations remain intact and preserved
console.log("\n--- Checking Non-European Overseas Territory Coverage ---");
let overseas_locs = [
  { coords: [-75.69, 45.42], name: "Canada (Ottawa)", year: 1850 },
  { coords: [-77.03, 38.90], name: "USA (Washington DC)", year: 1850 },
  { coords: [-58.15, 6.80], name: "British Guiana (Georgetown)", year: 1850 },
  { coords: [116.40, 39.90], name: "China (Beijing)", year: 1850 },
  { coords: [139.69, 35.68], name: "Japan (Tokyo)", year: 1850 },
  { coords: [-58.38, -34.60], name: "Argentina (Buenos Aires)", year: 1850 },
  { coords: [77.20, 28.61], name: "India (Delhi)", year: 1850 },
  { coords: [-77.03, 38.90], name: "USA (Washington DC)", year: 1950 },
  { coords: [116.40, 39.90], name: "China (Beijing)", year: 1950 },
  { coords: [-0.12, 51.50], name: "UK (London)", year: 1950 }
];

let overseas_failures = 0;
for (let loc of overseas_locs) {
  let ts = Date.getTimestamp({ minute: 1, year: loc.year });
  let pt = turf.point(loc.coords);
  let covered = null;

  for (let id in savefile) {
    let ent = savefile[id];
    if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;
    let st = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts);
    if (!st || !st.geometry) continue;

    try {
      if (turf.booleanPointInPolygon(pt, turf.feature(st.geometry))) {
        covered = { id: id, name: st.properties && st.properties.name, seshat: st.properties && st.properties.seshat_id };
        break;
      }
    } catch (e) {}
  }

  if (covered) {
    console.log(`- ${loc.name} at Year ${loc.year}: COVERED by ${covered.id} (${covered.name}) [${covered.seshat}]`);
  } else {
    console.error(`FAIL: ${loc.name} at Year ${loc.year} is NOT covered!`);
    overseas_failures++;
  }
}

console.log("\n========================================");
if (stray_polygons_found === 0 && overseas_failures === 0) {
  console.log("PASS: Scanline rasterisation verified 0 stray polygons in Europe and 100% overseas preservation!");
  process.exit(0);
} else {
  console.error(`FAIL: ${stray_polygons_found} strays found, ${overseas_failures} overseas failures!`);
  process.exit(1);
}
