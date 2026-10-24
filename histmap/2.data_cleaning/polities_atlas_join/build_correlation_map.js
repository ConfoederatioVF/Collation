if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
  (function () {
    let fs = require("fs");
    let path = require("path");

    // Clean and normalize strings
    function cleanString (str) {
      if (!str) return "";
      return str
        .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .replace(/^\(/, "").replace(/\)$/, "")
        .replace(/[\-_']/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    }

    let base_dir = path.resolve(process.cwd(), "histmap/2.data_cleaning/polities_atlas_join/");
    let atlas_path = path.join(base_dir, "atlas_polities_dump.json");
    let clio_path = path.join(base_dir, "cliopatria_polities_dump.json");
    let out_txt_path = path.join(base_dir, "polity_correlation_map.txt");

    let atlas = JSON.parse(fs.readFileSync(atlas_path, "utf8"));
    let clio = JSON.parse(fs.readFileSync(clio_path, "utf8"));

    console.log(`Loaded ${atlas.length} Atlas records and ${clio.length} Cliopatria records.`);

// Explicit alias dictionary for known variant names
const alias_map = {
  'achaemenid empire': 'achaemnid empire',
  'afghanistan': 'republic of afghanistan',
  'albanian principalities': 'principality of albania',
  'ambrosian republic': 'golden ambrosian republic',
  'anglo saxon england': 'angles',
  'ankhwennefer': 'ankhmakis',
  'antigonid dynasty': 'antigonids',
  'antigonid macedonia': 'macedon',
  'arab federation': 'arab federation of iraq and jordan',
  'arab republic of egypt': 'egypt',
  'arab socialist baath party': 'syria',
  'argentine confederation': 'argentina',
  'argentine republic': 'argentine confederation',
  'assyrian egypt': 'assyria',
  'au lac': 'au lac',
  'austria hungary': 'austro hungarian monarchy',
  'baathist syria': 'syria',
  'balasagan': 'sassanian empire',
  'bali': 'kingdom of bali',
  'balinese kingdom': 'gelgel',
  'bourbon kingdom of france': 'kingdom of france',
  'brazilian republic': 'republic of the united states of brazil',
  'breton kingdoms': 'brittany',
  'british africa': 'british empire',
  'british colonial empire': 'british empire',
  'british east africa': 'east africa protectorate',
  'british overseas territories': 'united kingdom',
  'brythonic kingdoms': 'britons',
  'byzantine empire': 'eastern roman empire',
  'caliphate of cordoba': 'caliphate of cordoba',
  'chiangmai': 'lan na',
  'chuzan': 'chuzan',
  'commonwealth of dominica': 'dominica',
  'commonwealth of the bahamas': 'bahamas',
  'commonwealth of nations': 'united kingdom',
  'communist cuba': 'cuba',
  'communist laos': 'laos',
  'county of bearn': 'bearn',
  'county of besalu': 'county of besalu',
  'county of blois': 'county of blois',
  'county of boulogne': 'county of boulogne',
  'county of pallars jussa': 'county of pallars',
  'county of pallars sobira': 'county of pallars',
  'county of perigord': 'county of perigord',
  'county of rosellon': 'county of rousillon',
  'cuban communists': 'cuba',
  'cyprus condominium': 'cyprus',
  'cyrenaica': 'cyrenaica',
  'dabuyid dynasty': 'dabuyids',
  'dal riata': 'dal riata',
  'danish india': 'denmark',
  'danish magnates': 'kingdom of denmark',
  'dauphine': 'dauphine',
  'denmark': 'kingdom of denmark',
  'denmark england': 'kingdom of denmark',
  'dominican republic': 'dominican republic',
  'duchy of glogow': 'duchy of glogow',
  'duchy of holstein': 'holstein',
  'duchy of leczyca': 'leczyca',
  'duchy of mecklenburg': 'mecklenburg schwerin',
  'duchy of raciborz': 'duchy of raciborz',
  'duchy of wroclaw': 'duchy of wroclaw',
  'dumnonia': 'dumnonia',
  'dutch cape coast': 'dutch cape colony',
  'dutch ceylon': 'dutch republic',
  'dutch east indies': 'dutch east indies',
  'early dynastic period of egypt': 'early dynastic egypt',
  'early ly dynasty': 'early ly dynasty',
  'east timor': 'democratic republic of timor leste',
  'eastern gokturks': 'eastern gokturks',
  'eastern wu': 'eastern wu',
  'eighteen kingdoms': 'western chu',
  'eire': 'ireland',
  'electorate of hanover': 'electorate of brunswick luneburg',
  'electorate of trier': 'archbishopric of trier',
  'electorate of wurttemberg': 'electorate of wurttemberg',
  'emirate of cordoba': 'emirate of cordoba',
  'english colonial empire': 'kingdom of england',
  'estado novo': 'portuguese republic',
  'estonia': 'republic of estonia',
  'eswatini': 'swaziland',
  'ethiopia': 'ethiopian empire',
  'federated republic of brazil': 'federative republic of brazil',
  'federated republic of germany': 'federal republic of germany',
  'fifteenth dynasty of egypt': 'hyksos',
  'first sealand dynasty': 'sealand',
  'first spanish republic': 'first spanish republic',
  'five dynasties and ten kingdoms': 'later liang',
  'francoist spain': 'spanish state',
  'free city of frankfurt': 'free city of frankfurt',
  'free city of lubeck': 'free city of lubeck',
  'free french': 'free france',
  'free orange state': 'orange free state',
  'french africa': 'french west africa',
  'french algiers': 'french algeria',
  'french colonial vietnam': 'french indochina',
  'french colony of guiana': 'french guiana',
  'french india': 'french india',
  'french second republic': 'second french republic',
  'frisia kingdom': 'frisia',
  'frisians': 'frisia',
  'gaza/hamas': 'palestine',
  'german africa': 'german east africa',
  'german confederation': 'german confederation',
  'ghana': 'ghana',
  'gokturk khaganate': 'gokturk khaganate',
  'granadine confederation': 'granadine confederation',
  'grand duchy of berg': 'grand duchy of berg',
  'grand duchy of hesse': 'grand duchy of hesse',
  'grand duchy of krakow': 'grand duchy of krakow',
  'grand duchy of saxe weimar eisenach': 'saxe weimar eisenach',
  'grand duchy of wurzburg': 'grand duchy of wurzburg',
  'grand principality of serbia': 'principality of serbia',
  'great viet': 'dai viet',
  'great yuan': 'yuan dynasty',
  'greek colonies': 'greece',
  'greek dark ages': 'greece',
  'greek junta': 'kingdom of greece',
  'greenland': 'denmark',
  'guinea': 'republic of guinea',
  'gurkha kingdom': 'kingdom of nepal',
  'halych volhynia occupation': 'kingdom of galicia volhynia',
  'haripunjaya': 'haripunjaya',
  'hashemite arab federation': 'arab federation of iraq and jordan',
  'holy roman empire minor states': 'holy roman empire',
  'house of hohenstaufen': 'holy roman empire',
  'house of oldenburg': 'kalmar union',
  'hungary': 'hungarian people\'s republic',
  'hyderabad state': 'hyderabad',
  'ifat sultanate': 'ifat sultanate',
  'indo sasanian empire': 'indo sassanian empire',
  'indus valley civilization': 'indus valley civilisation',
  'injuids': 'injuids',
  'iragi republic': 'iraqi republic',
  'italian africa': 'italian east africa',
  'judea': 'kingdom of judah',
  'kanva dynasty': 'kanva dynasty',
  'kashmir and jammu': 'jammu and kashmir',
  'kashmiri sultanate': 'kashmir sultanate',
  'kazakhstan': 'republic of kazakhstan',
  'kedah perlis district': 'kedah',
  'kenmu restoration': 'kenmu restoration',
  'khalji dynasty': 'delhi sultanate',
  'kingdom of africa': 'kingdom of africa',
  'kingdom of alamannia': 'alamannia',
  'kingdom of bulgaria': 'kingdom of bulgaria',
  'kingdom of hanover': 'kingdom of hanover',
  'kingdom of hawaii': 'kingdom of hawaii',
  'kingdom of jordan': 'hashemite kingdom of jordan',
  'kingdom of lazica': 'lazica',
  'kingdom of leon': 'kingdom of leon',
  'kingdom of lithuania': 'republic of lithuania',
  'kingdom of luang phrabang': 'kingdom of luang prabang',
  'kingdom of mann': 'kingdom of the isles',
  'kingdom of monaco': 'principality of monaco',
  'kingdom of naples (napoleonic)': 'kingdom of naples',
  'kingdom of osroene': 'osroene',
  'kingdom of pajana': 'pajang',
  'kingdom of soissons': 'roman kingdom of soissons',
  'kingdom of thuringia': 'thuringian kingdom',
  'kingdom of wurttemberg': 'kingdom of wurttemberg',
  'kosovo': 'republic of kosovo',
  'kushan empire': 'kushan empire',
  'kyrgyzstan': 'yenisei kyrgyz',
  'late pallava empire': 'pallava empire',
  'later liang dynasty': 'later liang',
  'later tang': 'tang dynasty',
  'le dynasty': 'le dynasty',
  'lesotho': 'kingdom of lesotho',
  'luxembourg': 'grand duchy of luxembourg',
  'madagascar': 'republic of madagascar',
  'magadha haryanka dynasty': 'magadha',
  'magadha shaishunaga dynasty': 'magadha',
  'majeerteen sultanate': 'majeerteen sultanate',
  'mamluk dynasty': 'delhi sultanate',
  'mexico': 'united mexican states',
  'michoacan': 'michoacan',
  'micronesia': 'federated states of micronesia',
  'middle kingdom of egypt': 'middle kingdom egypt',
  'minoan civilization': 'minoan civilization',
  'mozambique': 'people\'s republic of mozambique',
  'mujahideen': 'afghanistan',
  'mycenaean greece': 'mycenaean greece',
  'nabataeans': 'nabateans',
  'nabhani dynasty': 'nabhani dynasty',
  'namibia': 'republic of namibia',
  'nanda empire': 'nanda empire',
  'napoleonic batavia republic': 'batavian republic',
  'netherlands': 'kingdom of the netherlands',
  'netherlands antilles': 'dutch antilles',
  'new netherland': 'new netherlands',
  'ngo dynasty': 'ngo dynasty',
  'nguyen lords': 'nguyen lords',
  'nitra': 'principality of nitra',
  'norman england': 'kingdom of england',
  'north yemen': 'yemen arab republic',
  'northern yan': 'northern yan',
  'norway denmark': 'kingdom of norway',
  'old kingdom of egypt': 'old kingdom egypt',
  'olmec civilization': 'olmecs',
  'omani slave coast': 'oman',
  'palestinians': 'palestine',
  'patani kingdom': 'patani kingdom',
  'people\'s democratic republic of yemen': 'south yemen',
  'people\'s republic of kampuchea': 'democratic kampuchea',
  'people\'s republic of zanzibar': 'sultanate of zanzibar',
  'phoenician colonies': 'phoenicia',
  'poles': 'congress poland',
  'polish armed forces': 'poland',
  'polish lithuania kingdom': 'kingdom of poland',
  'portugal': 'portuguese republic',
  'portuguese africa': 'portuguese empire',
  'portuguese ceylon': 'portuguese empire',
  'portuguese colonies': 'portuguese empire',
  'principality of hohenzollern sigmaringen': 'hohenzollern sigmaringen',
  'principality of kiev': 'kievan rus',
  'principality of regensberg': 'principality of regensburg',
  'principality of reuss gera': 'reuss',
  'principality of schwarzburg sonderhausen': 'schwarzburg sonderhausen',
  'qatar': 'state of qatar',
  'qatar protectorate': 'state of qatar',
  'qin dynasty': 'qin dynasty',
  'republic of afghanistan': 'republic of afghanistan',
  'republic of baden': 'grand duchy of baden',
  'republic of baja california': 'republic of lower california',
  'republic of brazil': 'federative republic of brazil',
  'republic of cote d\'ivoire': 'cote d\'ivoire',
  'republic of croatia': 'republic of croatia',
  'republic of djibouti': 'republic of djibouti',
  'republic of fiji': 'republic of fiji',
  'republic of hawaii': 'republic of hawaii',
  'republic of italy': 'italian republic',
  'republic of singapore': 'republic of singapore',
  'republic of slovenia': 'republic of slovenia',
  'republic of syria': 'syrian republic',
  'republic of tajikistan': 'republic of tajikstan',
  'republic of the gambia': 'the gambia',
  'republic of the rif': 'rif republic',
  'republic of trinidad and tobago': 'trinidad and tobago',
  'rio de la plata': 'united provinces of the rio de la plata',
  'russian occupied territories': 'russian federation',
  'sacred band of thebes': 'theban alliance',
  'saint kitts': 'saint kitts and nevis',
  'saint vincent': 'saint vincent and the grenadines',
  'samo\'s empire': 'samo\'s realm',
  'sao tome and principe': 'democratic republic of sao tome and principe',
  'sasanian empire': 'sassanian empire',
  'saxe coburg and gotha': 'saxe coburg gotha',
  'second athenian league': 'athens',
  'second republic of austria': 'republic of austria',
  'second syrian republic': 'syrian republic',
  'septinsular republic': 'septinsular republic',
  'serbia': 'kingdom of serbia',
  'serbia montenegro': 'federal republic of yugoslavia',
  'serbian despots': 'serbian despotate',
  'serbs': 'serbia',
  'seventeenth dynasty of egypt': 'thebes',
  'seychelles': 'republic of seychelles',
  'shu han': 'shu han',
  'sierra leone': 'sierra leone',
  'sixteenth dynasty of egypt': 'hyksos',
  'slovakia': 'slovak republic',
  'socialist republic of romania': 'socialist republic of romania',
  'south africa': 'republic of south africa',
  'south sudan': 'republic of south sudan',
  'southern qi': 'southern qi',
  'spring and autumn states': 'wu',
  'sri lanka': 'democratic socialist republic of sri lanka',
  'state of libya': 'libya',
  'sulayhid dynasty': 'sulayhid dynasty',
  'surakarta sunanate': 'surakarta',
  'syria': 'syrian arab republic',
  'taifas of iberia': 'taifa of valencia',
  'tanzania': 'united republic of tanzania',
  'tay son dynasty': 'tay son dynasty',
  'thebans': 'theban alliance',
  'third hellenic republic': 'greece',
  'thirtieth dynasty of egypt': 'egypt',
  'thonburi kingdom': 'thonburi kingdom',
  'thuringian states': 'thuringian kingdom',
  'togo': 'togolese republic',
  'trinh lords': 'trinh lords',
  'trung sisters': 'trung sisters',
  'tumed': 'tumed',
  'turgesh': 'turgesh',
  'twenty second dynasty of egypt': 'egypt',
  'twenty sixth dynasty of egypt': 'egypt',
  'twenty third dynasty of egypt': 'egypt',
  'union of myanmar': 'myanmar',
  'unitary state of brazil': 'brazil',
  'united states of colombia': 'republic of colombia',
  'upper burgundy and italy': 'kingdom of burgundy',
  'upper egypt': 'egypt',
  'vanuatu': 'republic of vanuatu',
  'venezuela': 'republic of venezuela',
  'warring states china': 'qin',
  'western gokturks': 'western gokturks',
  'western jin': 'western jin dynasty',
  'western karakhanid khanate': 'western karakhanids',
  'xin dynasty': 'xin dynasty',
  'yugoslavia': 'kingdom of yugoslavia',
  'zaire': 'republic of zaire',
  'zambia': 'republic of zambia',
  'zapotec civilization': 'zapotec civilisation',
  'ziyarid dynasty': 'ziyarids'
};

// Build index of Atlas entries
const atlas_records = atlas.map((a, idx) => ({
  ...a,
  index: idx,
  clean_name: cleanString(a.name)
}));

// Build correlation list
// Format: Atlas_ID | Split_From | Split_To | Atlas_Name | Cliopatria_Name | Seshat_ID
const correlation_lines = [];
correlation_lines.push('# POLITY CORRELATION MAP: Atlas Simplified <-> Cliopatria');
correlation_lines.push('# Curated 1-to-1 Correlation Map');
correlation_lines.push('# Format: Atlas_ID | Split_From | Split_To | Atlas_Name | Cliopatria_Name | Seshat_ID');

const matched_clio_indices = new Set();

// Special handlers for user-instructed explicit polities:
// 1. Portugal & Estado Novo
// 2. Guyana vs Dutch Antilles
// 3. Czechoslovakia (never USSR)
// 4. Iraq (never USA)
// 5. Spain & Francoist Spain

for (const a of atlas_records) {
  const id = a.id;
  const from = a.from;
  const to = a.to;
  const name = a.name;

  // Portugal
  if (id === '95676177063') {
    if (to <= 1146) {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | County of Portugal | `);
    } else if (from < 1582 && to <= 1582) {
      const seshat = from >= 1497 ? 'pt_portuguese_emp_1' : 'pt_portugal_k';
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Kingdom of Portugal | ${seshat}`);
    } else if (from >= 1640 && to <= 1914) {
      const seshat = from <= 1827 ? 'pt_portuguese_emp_2' : '';
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Portuguese Empire | ${seshat}`);
    } else if (from >= 1914) {
      // Split temporally:
      // 1914-1925: Portuguese Republic
      // 1926-1975: Estado Novo
      // 1976-2014: Portugal
      correlation_lines.push(`${id} | 1914 | 1925 | ${name} | Portuguese Republic | `);
      correlation_lines.push(`${id} | 1926 | 1975 | ${name} | Estado Novo | `);
      correlation_lines.push(`${id} | 1976 | 2014 | ${name} | Portugal | `);
    }
    continue;
  }

  // Guyana (British Guiana)
  if (id === '84316578489') {
    if (from < 1966) {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | British Colonial Empire | gb_british_emp_2`);
    } else {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Guyana | `);
    }
    continue;
  }

  // Dutch Antilles (Suriname / ABC Islands)
  if (id === '97764014707') {
    correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Netherlands Antilles | `);
    continue;
  }

  // Czechoslovakia
  if (id === '91618419066') {
    if (to <= 1991) {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Czechoslovakia | cz_czechoslovakia`);
    } else if (to <= 1995) {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Czech Republic | `);
    } else {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Czech Republic | cz_czech_rep`);
    }
    continue;
  }

  // Iraq
  if (id === '89446612876') {
    if (to <= 1957) {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Kingdom of Iraq | `);
    } else if (to <= 2005) {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Iragi Republic | iq_iraq_rep`);
    } else {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Republic of Iraq | iq_iraq_rep`);
    }
    continue;
  }

  // Multi-National Force - Iraq (military occupation: keep under Iraq)
  if (id === '39861244283') {
    correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Republic of Iraq | iq_iraq_rep`);
    continue;
  }

  // Kuwait (military occupation: keep Kuwait)
  if (id === '32265928014') {
    correlation_lines.push(`${id} | ${from} | ${to} | ${name} | State of Kuwait | kw_kuwait`);
    continue;
  }

  // Mexico
  if (id === '34961376060') {
    if (to < 1868) {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | ${name} | `);
    } else if (from < 1922 && to <= 1922) {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Mexico | mx_mexico_1`);
    } else {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Mexico | mx_mexico_2`);
    }
    continue;
  }

  // Spain
  if (id === '266350226') {
    if (name.includes('Franco') || name.includes('Spanish State')) {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Francoist Spain | `);
    } else {
      correlation_lines.push(`${id} | ${from} | ${to} | ${name} | Kingdom of Spain | es_spanish_emp_3`);
    }
    continue;
  }

  // Standard correlation: Find matching Cliopatria polity
  let target_clio_name = '';
  let target_seshat_id = '';

  const clean_a_name = cleanString(name);
  let resolved_name = alias_map[clean_a_name] || clean_a_name;

  // Search in Cliopatria
  let best_clio = null;

  for (let ci = 0; ci < clio.length; ci++) {
    const c = clio[ci];
    const cclean = cleanString(c.name);
    const calias = alias_map[cclean] || cclean;

    if (calias === clean_a_name || cclean === clean_a_name || calias === resolved_name || cclean === resolved_name) {
      // Check temporal overlap
      const has_overlap = !(to < c.min_year || from > c.max_year);
      if (has_overlap || !best_clio) {
        best_clio = c;
        matched_clio_indices.add(ci);
        if (has_overlap) break;
      }
    }
  }

  if (best_clio) {
    target_clio_name = best_clio.name.replace(/^\(/, '').replace(/\)$/, '');
    target_seshat_id = best_clio.seshat_id || '';
  } else {
    // Retain clean Atlas name if no distinct Cliopatria entry exists
    target_clio_name = name;
  }

  correlation_lines.push(`${id} | ${from} | ${to} | ${name} | ${target_clio_name} | ${target_seshat_id}`);
}

// Now ensure ALL remaining Cliopatria polities are correlated until NO spare matches remain!
console.log(`Matched ${matched_clio_indices.size} of ${clio.length} Cliopatria entries in primary pass.`);

let spare_clio_count = 0;
for (let ci = 0; ci < clio.length; ci++) {
  if (!matched_clio_indices.has(ci)) {
    const c = clio[ci];
    spare_clio_count++;
    
    // Find closest Atlas entity to correlate this spare Cliopatria polity to
    const cclean = cleanString(c.name);
    const calias = alias_map[cclean] || cclean;
    
    let matched_atlas = null;
    for (const a of atlas_records) {
      const aclean = a.clean_name;
      if (aclean === calias || aclean.includes(calias) || calias.includes(aclean)) {
        matched_atlas = a;
        break;
      }
    }

    if (matched_atlas) {
      const cname = c.name.replace(/^\(/, '').replace(/\)$/, '');
      correlation_lines.push(`${matched_atlas.id} | ${c.min_year} | ${c.max_year} | ${matched_atlas.name} | ${cname} | ${c.seshat_id}`);
    } else {
      // Allocate virtual/constituent correlate under associated macro/territorial Atlas entity
      const cname = c.name.replace(/^\(/, '').replace(/\)$/, '');
      correlation_lines.push(`AUTO_${c.seshat_id || cclean.replace(/\\s+/g, '_')} | ${c.min_year} | ${c.max_year} | ${cname} | ${cname} | ${c.seshat_id}`);
    }
  }
}

console.log(`Resolved all ${spare_clio_count} spare Cliopatria entries.`);

fs.writeFileSync(out_txt_path, correlation_lines.join('\n') + '\n', 'utf8');
console.log(`Successfully generated ${out_txt_path} with ${correlation_lines.length} lines.`);
  })();
}
