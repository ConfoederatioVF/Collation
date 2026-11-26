//Import modules
let assert = require("assert");
let path = require("path");

//Initialise functions
{
  let root_dir = path.resolve(__dirname, "../..");
  let stad_dir = path.join(root_dir, "histmap/2.data_cleaning/population_Stadester");

  global.fs = require("fs");
  global.path = path;
  global.JSON5 = require("json5");
  global.h1 = path.join(root_dir, "histmap/1.data_raw");
  global.h2 = path.join(root_dir, "histmap/2.data_cleaning");
  global.h3 = path.join(root_dir, "histmap/3.data_transform");
  global.h5 = path.join(root_dir, "histmap/5.data_visualisation");

  require(path.join(stad_dir, "stadester_name_normaliser.js"));
  require(path.join(stad_dir, "stadester_uud.js"));

  let norm = global.stadester_name_normaliser;
  let uud = global.population_Stadester_uud;

  //1. Blocked cross-municipality pairs (INV-01 & INV-14)
  let blocked_pairs = [
    [{ name: "Valletta", country: "Malta", coords: [35.89924, 14.5141], is_capital: true, population: { 2021: 5157 } },
     { name: "Hamrun", country: "Malta", coords: [35.885, 14.480], population: { 2021: 10514 } }],
    [{ name: "Athens", country: "Greece", coords: [37.98381, 23.72754], is_capital: true, population: { 2021: 643452 } },
     { name: "Piraeus", country: "Greece", coords: [37.94299, 23.64698], population: { 2021: 168151 } }],
    [{ name: "Naples", country: "Italy", coords: [40.85177, 14.26812], population: { 2021: 913462 } },
     { name: "Giugliano in Campania", country: "Italy", coords: [40.92817, 14.19556], population: { 2021: 123679 } }],
    [{ name: "Cairo", country: "Egypt", coords: [30.04444, 31.23583], is_capital: true, population: { 2021: 9600000 } },
     { name: "Giza", country: "Egypt", coords: [29.987, 31.2118], population: { 2021: 4300000 } }],
    [{ name: "Rabat", country: "Morocco", coords: [34.01325, -6.83255], is_capital: true, population: { 2014: 577827 } },
     { name: "Salé", country: "Morocco", coords: [34.0531, -6.7985], population: { 2014: 890403 } }],
    [{ name: "Tokyo", country: "Japan", coords: [35.6895, 139.69171], is_capital: true, population: { 2020: 9733276 } },
     { name: "Yokohama", country: "Japan", coords: [35.4437, 139.6380], population: { 2020: 3777491 } }],
    [{ name: "New York", country: "United States of America", coords: [40.7128, -74.006], population: { 2020: 8804190 } },
     { name: "Newark", country: "United States of America", coords: [40.7357, -74.1724], population: { 2020: 311549 } }],
    [{ name: "Rhodes", country: "Greece", coords: [36.4408, 28.2225], population: { "-400": 60000, 2021: 50636 } },
     { name: "Lindos", country: "Greece", coords: [36.0913, 28.0875], population: { "-400": 15000, 2021: 1087 } }]
  ];

  for (let i = 0; i < blocked_pairs.length; i++) {
    let a = blocked_pairs[i][0];
    let b = blocked_pairs[i][1];
    let res = uud.canMergeMunicipalities(a, b);
    assert.strictEqual(res.allow, false, `Expected BLOCK for ${a.name} vs ${b.name}, got allow=true (${res.reason})`);
  }

  //2. Allowed semantic/exonym identity merges (INV-02)
  let semantic_pairs = [
    [{ name: "London", country: "United Kingdom", coords: [51.5112, -0.1198], is_capital: true, population: { 1800: 959310 } },
     { name: "Londinium", country: "United Kingdom", coords: [51.5128, -0.0918], population: { 100: 45000 } }],
    [{ name: "Kyiv", country: "Ukraine", coords: [50.4501, 30.5234], is_capital: true, population: { 2021: 2962180 } },
     { name: "Kiev", country: "Ukraine", coords: [50.4547, 30.5238], population: { 1989: 2587945 } }],
    [{ name: "Istanbul", country: "Turkey", coords: [41.01384, 28.94966], population: { 1950: 983041 } },
     { name: "Constantinople", country: "Turkey", coords: [41.0082, 28.9784], population: { 1500: 200000 } }],
    [{ name: "Tokyo", country: "Japan", coords: [35.6895, 139.69171], is_capital: true, population: { 1950: 5385071 } },
     { name: "Edo", country: "Japan", coords: [35.685, 139.753], population: { 1800: 1000000 } }],
    [{ name: "Beijing", country: "China", coords: [39.9042, 116.4074], is_capital: true, population: { 2020: 21893095 } },
     { name: "Peking", country: "China", coords: [39.9042, 116.4074], population: { 1900: 1100000 } }]
  ];

  for (let i = 0; i < semantic_pairs.length; i++) {
    let a = semantic_pairs[i][0];
    let b = semantic_pairs[i][1];
    let res = uud.canMergeMunicipalities(a, b);
    assert.strictEqual(res.allow, true, `Expected ALLOW for ${a.name} + ${b.name}, got allow=false (${res.reason})`);
  }

  //3. Class 3 Temporal Anti-Anachronism splitting (INV-13)
  let raw_db = {
    "Hamburg-Germany": { name: "Hamburg", country: "Germany", coords: [53.55108, 9.99368], population: { 1800: 130000, 1950: 1605606 } },
    "Altona-Germany": { name: "Altona", country: "Germany", coords: [53.550, 9.935], population: { 1800: 24000, 1925: 185653, 1950: 230000 } },
    "Berlin-Germany": { name: "Berlin", country: "Germany", coords: [52.52001, 13.40495], is_capital: true, population: { 1800: 172132, 1950: 3336026 } },
    "Charlottenburg-Germany": { name: "Charlottenburg", country: "Germany", coords: [52.516, 13.304], population: { 1800: 3200, 1910: 305978 } },
    "Budapest-Hungary": { name: "Budapest", country: "Hungary", coords: [47.49791, 19.04023], is_capital: true, population: { 1900: 733358 } },
    "Buda-Hungary": { name: "Buda", country: "Hungary", coords: [47.496, 19.039], population: { 1800: 24300 } },
    "Pest-Hungary": { name: "Pest", country: "Hungary", coords: [47.498, 19.055], population: { 1800: 29870 } },
    "New York-United States of America": { name: "New York", country: "United States of America", coords: [40.7128, -74.006], population: { 1800: 60515, 1950: 7891957 } },
    "Brooklyn-United States of America": { name: "Brooklyn", country: "United States of America", coords: [40.6782, -73.9442], population: { 1800: 2378, 1890: 806343 } },
    "Bydgoszcz-Poland": { name: "Bydgoszcz", country: "Poland", coords: [53.12348, 18.00844], population: { 1800: 4500, 1980: 348000 } },
    "Fordon-Poland": { name: "Fordon", country: "Poland", coords: [53.149, 18.172], population: { 1800: 1600, 1970: 8200 } },
    "Paris 18 Buttes-Montmartre-France": { name: "Paris 18 Buttes-Montmartre", country: "France", coords: [48.892, 2.344], population: { 1990: 187657 } },
    "Paris-France": { name: "Paris", country: "France", coords: [48.85661, 2.35222], is_capital: true, population: { 1990: 2152423 } },
    "Osmangazi-Turkey": { name: "Osmangazi", country: "Turkey", coords: [40.195, 29.060], population: { 2020: 881459 } },
    "Bursa-Turkey": { name: "Bursa", country: "Turkey", coords: [40.19559, 29.06013], population: { 2020: 2100000 } }
  };

  let flat = uud.prepareAndFlattenSourceDB(raw_db, "test");
  assert.ok(flat["Altona-Germany"] && flat["Altona-Germany"].population[1800] === 24000, "Altona 1800 MUST remain separate (INV-13)");
  assert.strictEqual(flat["Altona-Germany"].population[1950], undefined, "Altona 1950 MUST NOT remain separate post-1937");
  assert.ok(flat["Charlottenburg-Germany"] && flat["Charlottenburg-Germany"].population[1800] === 3200, "Charlottenburg 1800 MUST remain separate (INV-13)");
  assert.ok(flat["Buda-Hungary"] && flat["Pest-Hungary"], "Buda & Pest 1800 MUST remain separate (INV-13)");
  assert.ok(flat["Brooklyn-United States of America"] && flat["Brooklyn-United States of America"].population[1800] === 2378, "Brooklyn 1800 MUST remain separate (INV-13)");
  assert.ok(flat["Fordon-Poland"] && flat["Fordon-Poland"].population[1800] === 1600, "Fordon 1800 MUST remain separate (INV-13)");
  assert.strictEqual(flat["Paris 18 Buttes-Montmartre-France"], undefined, "Class 2 Paris 18 MUST flatten into Paris");
  assert.strictEqual(flat["Osmangazi-Turkey"], undefined, "Class 2 Osmangazi MUST flatten into Bursa");

  //4. Global statistical wrapper cleaning (INV-02 & INV-14)
  assert.strictEqual(norm.normaliseCityName("Kėdainių rajono savivaldybė", "Lithuania").name, "Kėdainiai");
  assert.strictEqual(norm.normaliseCityName("Pärnu linn", "Estonia").name, "Pärnu");
  assert.strictEqual(norm.normaliseCityName("Stolichna", "Bulgaria").name, "Sofia");
  assert.strictEqual(norm.normaliseCityName("Oraș Năvodari", "Romania").name, "Năvodari");
  assert.strictEqual(norm.normaliseCityName("Springfield (CDP)", "United States of America").name, "Springfield");
  assert.strictEqual(norm.normaliseCityName("Howrah Municipal Corporation", "India").name, "Howrah");
  assert.strictEqual(norm.isNonHabitationFeature("Greater Valletta"), true);
  assert.strictEqual(norm.isNonHabitationFeature("Bilge Qagan"), false);

  //5. Post-review regression checks (parent_creation_year, Paris 13e, Tund`'za, Skopje pin snap)
  assert.strictEqual(norm.resolveAmalgamationParentFloor("London", "United Kingdom"), null);
  assert.strictEqual(norm.resolveAmalgamationParentFloor("Berlin", "Germany"), null);
  assert.strictEqual(norm.resolveAmalgamationParentFloor("Hamburg", "Germany"), null);
  assert.strictEqual(norm.resolveAmalgamationParentFloor("Istanbul", "Turkey"), null);
  assert.strictEqual(norm.resolveAmalgamationParentFloor("Budapest", "Hungary"), 1873);
  assert.strictEqual(norm.resolveAmalgamationParentFloor("Wuhan", "China"), 1949);
  assert.strictEqual(norm.decodeHaceksAndQuotes("Tund`'za", "Bulgaria"), "Tundža");
  let paris_13 = norm.resolveParentMunicipality("Paris 13e Arrondissement", "France", [48.83, 2.36]);
  assert.ok(paris_13 && paris_13.parent_name === "Paris", "Paris 13e Arrondissement MUST flatten into Paris");
  let skopje_a = { name: "Skopje", country: "North Macedonia", coords: [41.9981, 21.4254], population: { 2021: 526502 } };
  let skopje_b = { name: "Skopje", country: "North Macedonia", coords: [41.98, 21.43], population: { 2021: 541832 } };
  assert.strictEqual(uud.canMergeMunicipalities(skopje_a, skopje_b).allow, true, "Two Skopje records 2 km apart MUST merge");

  //6. Alignment steerer regressions (Devlet Mah, Ba'albak - Al-Harmal, Ghajnsielem, Mestre/Venice separation, Alibeyköyü)
  assert.strictEqual(norm.isNonHabitationFeature("Devlet Mah"), true);
  assert.strictEqual(norm.isNonHabitationFeature("Ba'albak - Al-Harmal"), true);
  assert.strictEqual(norm.normaliseCityName("Ghajnsielem and Comino", "Malta").name, "Ghajnsielem");
  assert.strictEqual(norm.resolveParentMunicipality("Mestre", "Italy", [45.49, 12.24]), null);
  let alibey = norm.resolveParentMunicipality("Alibeyköyü", "Turkey", [41.08, 28.94]);
  assert.ok(alibey && alibey.parent_name === "Istanbul", "Alibeyköyü MUST flatten into Istanbul");

  //7. Cross-frontier sovereign-transfer deduplication (Konigsberg/Kaliningrad & Weisbaden/Wiesbaden)
  let mock_frontier = {
    "Konigsberg-Germany": {
      key: "Konigsberg-Germany", name: "Konigsberg", country: "Germany",
      coords: [54.70649, 20.51095], population: { 1500: 10000, 1800: 59000 }
    },
    "Kaliningrad-Russia": {
      key: "Kaliningrad-Russia", name: "Kaliningrad", country: "Russia",
      coords: [54.70639, 20.51102], population: { 1950: 145000, 2025: 488690 }, viscount_project: "POLARIS"
    },
    "Weisbaden-Germany": {
      key: "Weisbaden-Germany", name: "Weisbaden", country: "Germany",
      coords: [50.06308, 8.24334], population: { 1800: 96500, 2025: 280000 }
    },
    "Wiesbaden-Germany": {
      key: "Wiesbaden-Germany", name: "Wiesbaden", country: "Germany",
      coords: [50.07219, 8.25329], population: { 1800: 8650, 2025: 339176 }
    },
    "Gross Legitten-Germany": {
      key: "Gross Legitten-Germany", name: "Groß Legitten", other_names: ["Turgenevo"], country: "Germany",
      coords: [54.82, 20.92], population: { 1910: 420, 1939: 510 }
    },
    "Turgenevo-Russia": {
      key: "Turgenevo-Russia", name: "Turgenevo", country: "Russia",
      coords: [54.8205, 20.9205], population: { 1959: 480, 2021: 650 }, viscount_project: "POLARIS"
    }
  };
  require("../../histmap/2.data_cleaning/population_Stadester/stadester_uud_fixes.js");
  uud.flattenToMunicipalityLevelAndCleanNames(mock_frontier);
  assert.ok(!mock_frontier["Konigsberg-Germany"] && mock_frontier["Kaliningrad-Russia"], "Konigsberg MUST merge into Kaliningrad");
  assert.strictEqual(mock_frontier["Kaliningrad-Russia"].population[1800], 59000, "Kaliningrad MUST retain Konigsberg 1800 pop");
  assert.ok(!mock_frontier["Weisbaden-Germany"] && mock_frontier["Wiesbaden-Germany"], "Weisbaden MUST merge into Wiesbaden");
  assert.strictEqual(mock_frontier["Wiesbaden-Germany"].population[1800], 8650, "Wiesbaden MUST NOT keep Chandler Weisbaden 1800 spike");
  assert.ok(!mock_frontier["Gross Legitten-Germany"] && mock_frontier["Turgenevo-Russia"], "other_names cross-frontier match MUST merge into Turgenevo");
  assert.strictEqual(mock_frontier["Turgenevo-Russia"].population[1910], 420, "Turgenevo MUST retain pre-1945 population");

  console.log("[test_uud_invariants] PASS: All INV-01, INV-02, INV-13, INV-14 assertions succeeded.");
}
