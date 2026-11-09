const fs = require("fs");
const path = require("path");
const JSON5 = require("json5");

const dir = "histmap/1.data_raw/population_regional/russia";
const manifestPath = path.join(dir, "polaris_gazetteers.json5");
const manifest = JSON5.parse(fs.readFileSync(manifestPath, "utf8"));

const continuous_classical_or_dyakovo = new Set([
  "Phanagoria-Russia",
  "Hermonassa-Russia",
  "Taman-Russia",
  "Tmutarakan-Ukraine",
  "Patraeus-Russia",
  "Achilleion-Russia",
  "Derbent-Russia",
  "Dyakovo Gorodishche-Russia",
  "Troitskoye Gorodishche-Russia",
  "Shcherbinskoye Gorodishche-Russia",
  "Borsheva Gorodishche-Russia"
]);

const special_splits = {
  "Novonikolayevsk-Russia": [
    { min: -10000, max: 1880, name: "Krivoshchekovo", offset: 0.004 },
    { min: 1881, max: 2025, name: null, offset: 0 }
  ],
  "Pskov-Russia": [
    { min: -10000, max: 750, name: "Kamno-Pskov Gorodishche", offset: 0.004 },
    { min: 751, max: 2025, name: null, offset: 0 }
  ],
  "Suzdal-Russia": [
    { min: -10000, max: 750, name: "Suzdal Merya Gorodishche", offset: 0.004 },
    { min: 751, max: 2025, name: null, offset: 0 }
  ],
  "Murom-Russia": [
    { min: -10000, max: 750, name: "Murom Oksky Gorodishche", offset: 0.004 },
    { min: 751, max: 2025, name: null, offset: 0 }
  ],
  "Ryazan-Russia": [
    { min: -10000, max: 750, name: "Borki-Ryazan Gorodishche", offset: 0.008 },
    { min: 751, max: 1250, name: "Pereyaslavl-Ryazansky Gorodishche", offset: 0.004 },
    { min: 1251, max: 2025, name: null, offset: 0 }
  ],
  "Kursk-Russia": [
    { min: -10000, max: 750, name: "Kursk Romny Gorodishche", offset: 0.008 },
    { min: 751, max: 1300, name: "Old Kursk Gorodishche", offset: 0.004 },
    { min: 1301, max: 2025, name: null, offset: 0 }
  ],
  "Tobolsk-Russia": [
    { min: -10000, max: 1550, name: "Qashliq-Isker", offset: 0.004 },
    { min: 1551, max: 2025, name: null, offset: 0 }
  ],
  "Potchevash-Russia": [
    { min: -10000, max: 950, name: null, offset: 0 },
    { min: 951, max: 2025, name: "Isker-Potchevash", offset: 0.004 }
  ],
  "Tomsk-Russia": [
    { min: -10000, max: 1000, name: "Timiryazevo-Tomsk Gorodishche", offset: 0.008 },
    { min: 1001, max: 1580, name: "Toyanov Gorodok", offset: 0.004 },
    { min: 1581, max: 2025, name: null, offset: 0 }
  ],
  "Bolgar-Russia": [
    { min: -10000, max: 1450, name: null, offset: 0 },
    { min: 1451, max: 2025, name: "Bolgary Village", offset: 0.004 }
  ],
  "Bilyar-Russia": [
    { min: -10000, max: 1450, name: null, offset: 0 },
    { min: 1451, max: 2025, name: "Bilyarsk Village", offset: 0.004 }
  ],
  "Tuapse-Russia": [
    { min: -10000, max: -500, name: "Tuapse Dolmen Site", offset: 0.008 },
    { min: -499, max: 1820, name: "Tuapse Circassian Aul", offset: 0.004 },
    { min: 1821, max: 2025, name: null, offset: 0 }
  ],
  "Sochi-Russia": [
    { min: -10000, max: -500, name: "Sochi Dolmen Site", offset: 0.008 },
    { min: -499, max: 1820, name: "Sochipsu Ubykh Aul", offset: 0.004 },
    { min: 1821, max: 2025, name: null, offset: 0 }
  ],
  "Anapa-Russia": [
    { min: -10000, max: 400, name: "Gorgippia-Anapa", offset: 0.008 },
    { min: 401, max: 1500, name: "Mapa Genoese Colony", offset: 0.004 },
    { min: 1501, max: 2025, name: null, offset: 0 }
  ],
  "Novorossiysk-Russia": [
    { min: -10000, max: 300, name: "Bata Classical Site", offset: 0.008 },
    { min: 301, max: 1500, name: "Tsemes Medieval Settlement", offset: 0.004 },
    { min: 1501, max: 2025, name: null, offset: 0 }
  ],
  "Gelendzhik-Russia": [
    { min: -10000, max: 300, name: "Torikos", offset: 0.008 },
    { min: 301, max: 1820, name: "Kheltsikhe Circassian Aul", offset: 0.004 },
    { min: 1821, max: 2025, name: null, offset: 0 }
  ],
  "Vladikavkaz-Russia": [
    { min: -10000, max: 100, name: "Vladikavkaz Koban Site", offset: 0.008 },
    { min: 101, max: 1400, name: "Dzaudzhikau Alanic Settlement", offset: 0.004 },
    { min: 1401, max: 2025, name: null, offset: 0 }
  ],
  "Kislovodsk-Russia": [
    { min: -10000, max: 1400, name: "Kislovodsk Alanic Fort", offset: 0.004 },
    { min: 1401, max: 2025, name: null, offset: 0 }
  ],
  "Roishche-Ukraine": [
    { min: -10000, max: 800, name: null, offset: 0 },
    { min: 801, max: 2025, name: "Roishche Medieval Settlement", offset: 0.004 }
  ],
  "Volyntsevo-Ukraine": [
    { min: -10000, max: 800, name: null, offset: 0 },
    { min: 801, max: 2025, name: "Volyntsevo Medieval Settlement", offset: 0.004 }
  ],
  "Halych-Ukraine": [
    { min: -10000, max: 650, name: "Krylos-Halych Early Slavic Site", offset: 0.004 },
    { min: 651, max: 2025, name: null, offset: 0 }
  ]
};

function isArchaeologicalPrimaryName(name) {
  const lower = name.toLowerCase();
  return (
    lower.includes("gorodishche") ||
    lower.includes("type-site") ||
    lower.includes("type-hillfort") ||
    lower.includes("palaeolithic") ||
    lower.includes("neolithic") ||
    lower.includes("bronze age") ||
    lower.includes("iron age") ||
    lower.includes("kurgan") ||
    lower.includes("cliff shelter") ||
    lower.includes("mounds") ||
    lower.includes("pushkari") ||
    lower.includes("mezin") ||
    lower.includes("chulatovo") ||
    lower.includes("kolochin i") ||
    lower.includes("milograd") ||
    lower.includes("gornal")
  );
}

function makeSplitName(baseName, cMin, cMax, isPrimaryCluster) {
  if (isPrimaryCluster) return baseName;
  if (isArchaeologicalPrimaryName(baseName)) {
    const shortBase = baseName
      .replace(/\s*(Palaeolithic|Neolithic|Bronze Age|Iron Age|Late Zarubintsy).*$/i, "")
      .replace(/\s*\/.*$/, "")
      .trim() || baseName;
    if (cMin >= 1500) return `${shortBase} Modern Village`;
    if (cMin >= 400) return `${shortBase} Medieval Settlement`;
    if (cMax <= -4000) return `${shortBase} Stone Age Site`;
    if (cMax <= -1000) return `${shortBase} Bronze Age Site`;
    return `${shortBase} Iron Age Site`;
  }
  if (cMax <= -4000) return `${baseName} Stone Age Site`;
  if (cMax <= -1000) return `${baseName} Bronze Age Site`;
  if (cMax <= 400) return `${baseName} Iron Age Site`;
  if (cMax <= 950) return `${baseName} Gorodishche`;
  if (cMax <= 1450) return `${baseName} Medieval Gorodishche`;
  return `${baseName} (${cMin}–${cMax})`;
}

let grandSplits = 0;

for (const g of manifest.gazetteers) {
  const gKey = g.key || g.id;
  const rawText = fs.readFileSync(g.path, "utf8");
  const data = JSON5.parse(rawText);

  // Compute pre-split year sums
  const preSums = {};
  for (const v of Object.values(data)) {
    for (const [yr, pop] of Object.entries(v.population || {})) {
      preSums[yr] = (preSums[yr] || 0) + Number(pop);
    }
  }

  const newData = {};
  let gSplits = 0;

  for (const [k, v] of Object.entries(data)) {
    // Clean specific polluted aliases first
    if (k === "Saygatskoye-Russia" && Array.isArray(v.other_names)) {
      v.other_names = v.other_names.filter(n => !n.includes("Чайковский") && !n.toLowerCase().includes("chaykovsky"));
    }
    if (k === "Turist-2-Russia" && Array.isArray(v.other_names)) {
      v.other_names = v.other_names.filter(n => !n.toLowerCase().includes("novosibirsk"));
    }
    if (k === "Tsemdolina-Russia" && Array.isArray(v.other_names)) {
      v.other_names = v.other_names.filter(n => !n.includes("Новороссийск") && !n.toLowerCase().includes("novorossiysk"));
    }

    const yrs = Object.keys(v.population || {}).map(Number).sort((a, b) => a - b);
    if (yrs.length < 2) {
      newData[k] = v;
      continue;
    }
    const minY = yrs[0], maxY = yrs[yrs.length - 1];
    const countrySuffix = k.includes("-") ? k.slice(k.lastIndexOf("-") + 1) : (v.country || "Russia");
    const baseName = v.name || k.slice(0, k.lastIndexOf("-"));

    if (special_splits[k]) {
      const spList = [];
      for (const sp of special_splits[k]) {
        const sub = yrs.filter(y => y >= sp.min && y <= sp.max);
        if (sub.length > 0) spList.push({ yrs: sub, spec: sp });
      }
      if (spList.length > 1) {
        gSplits++;
        grandSplits++;
        for (const item of spList) {
          const isOrig = item.spec.name === null;
          let entryName = isOrig ? baseName : item.spec.name;
          let entryKey = isOrig ? k : `${entryName}-${countrySuffix}`;
          let suffixNum = 2;
          while (!isOrig && (newData[entryKey] || data[entryKey])) {
            entryName = `${item.spec.name} ${suffixNum}`;
            entryKey = `${entryName}-${countrySuffix}`;
            suffixNum++;
          }
          const popObj = {};
          for (const y of item.yrs) popObj[y] = v.population[y];
          const clone = JSON.parse(JSON.stringify(v));
          clone.name = entryName;
          clone.population = popObj;
          if (!isOrig) {
            clone.coords = [
              Number((Number(v.coords[0]) + item.spec.offset).toFixed(4)),
              Number((Number(v.coords[1]) + item.spec.offset).toFixed(4))
            ];
            clone.other_names = [entryName];
          }
          newData[entryKey] = clone;
        }
        continue;
      }
    }

    // General cluster splitting
    let clusters = [];
    let curCluster = [yrs[0]];
    for (let i = 1; i < yrs.length; i++) {
      const y0 = yrs[i - 1], y1 = yrs[i];
      const gap = y1 - y0;
      let splitHere = false;
      if (y0 >= 0 && gap >= 450) splitHere = true;
      if (y0 >= 1100 && gap >= 360) splitHere = true;
      if (y0 < 0 && y1 >= 0 && gap >= 450 && k !== "Derbent-Russia") splitHere = true;
      if (y0 <= -1500 && y1 > -1500 && (gap >= 1000 || maxY >= 500)) splitHere = true;
      if (!continuous_classical_or_dyakovo.has(k) && minY < 0 && maxY >= 500 && y0 <= 350 && y1 >= 400) splitHere = true;
      if (y0 <= -4000 && gap >= 2500 && maxY > -2000) splitHere = true;

      if (splitHere) {
        clusters.push(curCluster);
        curCluster = [y1];
      } else {
        curCluster.push(y1);
      }
    }
    clusters.push(curCluster);

    if (clusters.length === 1) {
      newData[k] = v;
      continue;
    }

    gSplits++;
    grandSplits++;

    let primaryIdx = clusters.length - 1;
    if (isArchaeologicalPrimaryName(baseName)) {
      primaryIdx = 0;
    } else if (gKey === "migration_period" && clusters[clusters.length - 1][0] >= 1650) {
      const modernCitiesInMigration = new Set([
        "Belgorod-Russia", "Ufa-Russia", "Birsk-Russia", "Elabuga-Russia",
        "Meshchovsk-Russia", "Velye-Russia", "Tarki-Russia", "Zmeyskaya-Russia"
      ]);
      if (!modernCitiesInMigration.has(k)) {
        primaryIdx = 0;
      }
    }

    for (let idx = 0; idx < clusters.length; idx++) {
      const c = clusters[idx];
      const cMin = c[0], cMax = c[c.length - 1];
      const isPrimary = (idx === primaryIdx);
      let entryName = makeSplitName(baseName, cMin, cMax, isPrimary);
      let entryKey = isPrimary ? k : `${entryName}-${countrySuffix}`;
      let suffixNum = 2;
      while (!isPrimary && (newData[entryKey] || data[entryKey])) {
        entryName = `${makeSplitName(baseName, cMin, cMax, false)} ${suffixNum}`;
        entryKey = `${entryName}-${countrySuffix}`;
        suffixNum++;
      }

      const popObj = {};
      for (const y of c) popObj[y] = v.population[y];
      const clone = JSON.parse(JSON.stringify(v));
      clone.name = entryName;
      clone.population = popObj;
      if (!isPrimary) {
        const offset = 0.004 * (Math.abs(idx - primaryIdx));
        clone.coords = [
          Number((Number(v.coords[0]) + offset).toFixed(4)),
          Number((Number(v.coords[1]) + offset).toFixed(4))
        ];
        clone.other_names = [entryName];
      }
      newData[entryKey] = clone;
    }
  }

  // Verify post-split year sums
  const postSums = {};
  for (const v of Object.values(newData)) {
    for (const [yr, pop] of Object.entries(v.population || {})) {
      postSums[yr] = (postSums[yr] || 0) + Number(pop);
    }
  }
  for (const yr of Object.keys(preSums)) {
    if (preSums[yr] !== postSums[yr]) {
      throw new Error(`Sum mismatch in ${gKey} at year ${yr}: ${preSums[yr]} vs ${postSums[yr]}`);
    }
  }

  fs.writeFileSync(g.path, JSON.stringify(newData, null, 2) + "\n", "utf8");
  console.log(`${gKey}: split ${gSplits} conflated entries -> ${Object.keys(newData).length} total entries (100% benchmark sums conserved)`);
}

console.log(`Done! Total split entries across 13 gazetteers: ${grandSplits}`);
