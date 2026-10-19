let fs = require("node:fs");
let readline = require("node:readline");

let sov_targets = {
  '7370': '#D1453B', // Ukrainian SSR
  '1788': '#D1453B', // Byelorussian SSR
  '2765': '#D1453B', // Galician SSR
  '7261': '#D1453B', // Transcaucasian SFSR
  '1402': '#D1453B', // Azerbaijan SSR
  '1310': '#D1453B', // Armenian SSR
  '2813': '#D1453B', // Georgian SSR
  '2312': '#D1453B', // Donetsk-Krivoi Rog
  '5394': '#D1453B', // Odessa Soviet Republic
  '7085': '#D1453B', // Taurida SSR
  '1549': '#944481'  // Bavarian Soviet Republic (distinct)
};

let german_targets = [
  '2830', // Germany (Military Occupation)
  '5915', // Protectorate of Bohemia and Moravia
  '6705', // Slovak Republic
  '6706', // Slovak Republic (Germany)
  '2805', // General Gouvernement
  '2271', // District of Byalistok
  '2820', // German East Africa (Military Occupation)
  '6753', // South West Africa (Military Occupation)
  '7488', // Vichy France
  '5443', // Operational Zone Adriatic
  '5444', // Operational Zone Alpine
  '7130', // Territory Commander Serbia
  '3029', // Hellenic State (Germany)
  '4618', // Lokot Republic
  '2347', // Duchy of Courland
  '3207', // Independent State of Croatia (Germany)
  '4534', // Latvia (Germany)
  '7367', // Ukraine State / Hetmanate
  '1994', '2329', '2578', '2756', '2815', '2817', '2816', '2821', '2823',
  '2825', '2828', '2222', '2925', '2958', '3385', '3686', '4050', '4755',
  '4802', '5216', '5226', '6284', '6391', '6402', '6409', '6477', '6821',
  '7537', '7603'
];

let all_color_updates = { ...sov_targets };
for (let id of german_targets) all_color_updates[id] = '#191919';

async function locatePartitions() {
  let cache_dir = "saves/.cache/detailed";
  let files = fs.readdirSync(cache_dir).filter(f => f.startsWith("partition_") && f.endsWith(".ndjson"));
  let key_to_file = {};

  for (let f of files) {
    let rs = fs.createReadStream(`${cache_dir}/${f}`);
    let rl = readline.createInterface({ input: rs });
    for await (let l of rl) {
      if (!l.startsWith('"')) continue;
      let q_end = l.indexOf('"', 1);
      let k = l.slice(1, q_end);
      if (all_color_updates[k] || k === '6537' || k === '4112' || k === '7432') {
        key_to_file[k] = f;
      }
    }
  }

  console.log(`Found partition for ${Object.keys(key_to_file).length} keys.`);
  for (let k in all_color_updates) {
    if (!key_to_file[k]) console.warn(`Key ${k} not found in cache!`);
  }
  return key_to_file;
}

locatePartitions().catch(console.error);
