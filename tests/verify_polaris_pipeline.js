let fs = require("fs");
let path = require("path");
let JSON5 = require("json5");
let { PNG } = require("pngjs");

//Bootstrap UF and histmap environment
global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");
global.JSON5 = JSON5;

let root_dir = process.cwd();

function loadDirectory (arg0_rel_dir) {
  let rel_dir = arg0_rel_dir;
  let full_dir = path.join(root_dir, rel_dir);
  if (fs.existsSync(full_dir)) {
    let files = fs.readdirSync(full_dir).filter((f) => f.endsWith(".js") && !f.includes("worker"));
    for (let i = 0; i < files.length; i++)
      require(path.join(full_dir, files[i]));
  }
}

loadDirectory("UF/js/number");
loadDirectory("UF/js/string");
loadDirectory("UF/js/colour");
loadDirectory("UF/js/file");
loadDirectory("UF/js/object");
loadDirectory("UF/js/array");
loadDirectory("UF/js/blacktraffic");
loadDirectory("UF/js/statistics");
loadDirectory("UF/js/geospatiale/coords");
loadDirectory("UF/js/geospatiale/operations");
loadDirectory("UF/js/geospatiale/files");
loadDirectory("UF/js/geospatiale/files/png");
loadDirectory("UF/js/geospatiale/files/png/tasks");

global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");
global.h4 = path.join(root_dir, "histmap/4.data_exports/");
global.h5 = path.join(root_dir, "histmap/5.data_visualisation/");

require(path.join(root_dir, "histmap/2.data_cleaning/metadata_HYDE/metadata_HYDE.js"));
require(path.join(root_dir, "histmap/2.data_cleaning/landuse_HYDE/landuse_HYDE.js"));
require(path.join(root_dir, "histmap/2.data_cleaning/population_Global/population_Global.js"));
require(path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/config/stadester_config.js"));
require(path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_density.js"));
require(path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_rasters.js"));
require(path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/population_Stadester.js"));
require(path.join(root_dir, "histmap/2.data_cleaning/population_Velkscala/population_Velkscala.js"));
let SubstrataRussia = require(path.join(root_dir, "histmap/3.data_transform/population_Substrata.russia/population_Substrata_russia.js"));

async function main () {
  let context = SubstrataRussia.A_loadManifestAndMasks();
  let hyde_years = context.hyde_years;

  console.log(`[1/4] Reconciling Stadestér Rural, Total & Density rasters for ${hyde_years.length} benchmark years...`);
  await population_Stadester.I_generatePopulationRasters({ years: hyde_years });
  await population_Stadester.J_prepareIntermediates({ years: hyde_years });

  console.log(`[2/4] Compositing Velkscala population rasters and syncing metadata for ${hyde_years.length} benchmark years...`);
  await population_Velkscala.B_compositePost1ADRasters({ years: hyde_years });
  await population_Velkscala.C_syncMetadata();

  //Close worker pool if open
  if (GeoPNG.terminateWorkerPool) GeoPNG.terminateWorkerPool();

  console.log(`[3/4] Running Zero-Hole & Temporal Continuity Audits on population_Velkscala and stadester_rural...`);
  let check_years = [-5000, -1000, 0, 500, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1700, 1900];
  let velk_series = {};

  for (let i = 0; i < check_years.length; i++) {
    let yr = check_years[i];
    let v_path = path.join(root_dir, `histmap/2.data_cleaning/population_Velkscala/population_rasters/population_${yr}.png`);
    let r_path = path.join(root_dir, `histmap/2.data_cleaning/population_Stadester/stadester_rural_rasters/stadester_rural_${yr}.png`);
    let v_png = PNG.sync.read(fs.readFileSync(v_path));
    let v_dv = new DataView(v_png.data.buffer, v_png.data.byteOffset, v_png.data.byteLength);
    let r_png = PNG.sync.read(fs.readFileSync(r_path));
    let r_dv = new DataView(r_png.data.buffer, r_png.data.byteOffset, r_png.data.byteLength);

    let v_arr = new Float32Array(context.n_valid);
    let zero_velk = 0;
    let zero_rur = 0;
    let rus_sum = 0;
    let bu_sum = 0;

    for (let x = 0; x < context.n_valid; x++) {
      let idx = context.valid_indices[x];
      let dom = context.pixel_domain[idx];
      let v_val = SubstrataRussia.readPositiveFloat32(v_png.data, v_dv, idx*4);
      let r_val = SubstrataRussia.readPositiveFloat32(r_png.data, r_dv, idx*4);
      v_arr[x] = v_val;
      if (v_val <= 0) zero_velk++;
      if (r_val <= 0) zero_rur++;
      if (dom === 1) rus_sum += v_val;
      else if (dom === 2) bu_sum += v_val;
    }
    velk_series[yr] = v_arr;
    console.log(`  Year ${String(yr).padStart(6)}: zero_velk=${zero_velk}, zero_rur=${zero_rur}, RUS+Crimea=${Math.round(rus_sum).toLocaleString()}, BLR+UKR=${Math.round(bu_sum).toLocaleString()}`);
  }

  //Compute Pearson correlation on log(r_i) and total field across 700 -> 800 -> 900 -> 1000 AD
  function pearsonLog (arr_a, arr_b) {
    let n = arr_a.length;
    let ma = 0;
    let mb = 0;
    for (let i = 0; i < n; i++) {
      ma += Math.log(Math.max(1e-6, arr_a[i]));
      mb += Math.log(Math.max(1e-6, arr_b[i]));
    }
    ma /= n;
    mb /= n;
    let cov = 0;
    let va = 0;
    let vb = 0;
    for (let i = 0; i < n; i++) {
      let da = Math.log(Math.max(1e-6, arr_a[i])) - ma;
      let db = Math.log(Math.max(1e-6, arr_b[i])) - mb;
      cov += da*db;
      va += da*da;
      vb += db*db;
    }
    return cov/Math.sqrt(Math.max(1e-12, va*vb));
  }

  let r_700_800 = pearsonLog(velk_series[700], velk_series[800]);
  let r_800_900 = pearsonLog(velk_series[800], velk_series[900]);
  let r_900_1000 = pearsonLog(velk_series[900], velk_series[1000]);
  let r_800_1000 = pearsonLog(velk_series[800], velk_series[1000]);
  console.log(`  Temporal log-correlations: r(700,800)=${r_700_800.toFixed(4)}, r(800,900)=${r_800_900.toFixed(4)}, r(900,1000)=${r_900_1000.toFixed(4)}, r(800,1000)=${r_800_1000.toFixed(4)}`);

  console.log(`[4/4] Auditing Specialist Mask Regional Target Conservation at 1000 AD...`);
  let v1000 = velk_series[1000];
  let px_to_valid = context.pixel_to_valid;
  let max_rel_err = 0;
  for (let i = 0; i < context.specialist_entries.length; i++) {
    let se = context.specialist_entries[i];
    if (1000 < se.domain[0] || 1000 > se.domain[1]) continue;
    let mask_target = 0;
    let mask_actual = 0;
    for (let x = 0; x < se.zones.length; x++) {
      let z = se.zones[x];
      let t_pop = SubstrataRussia.resolveZoneTargetPopulation(z.population, 1000);
      if (t_pop < 0 || z.pixels.length === 0) continue;
      mask_target += t_pop*(z.domain_fraction || 1.0);
      for (let y = 0; y < z.pixels.length; y++) {
        let vi = px_to_valid[z.pixels[y]];
        if (vi >= 0) mask_actual += v1000[vi];
      }
    }
    let rel_err = (mask_target > 0) ? Math.abs(mask_actual - mask_target)/mask_target : 0;
    if (rel_err > max_rel_err) max_rel_err = rel_err;
    console.log(`  Mask ${se.id.padEnd(28)}: target=${Math.round(mask_target).toLocaleString()}, actual=${Math.round(mask_actual).toLocaleString()}, rel_err=${(rel_err*100).toFixed(2)}%`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

