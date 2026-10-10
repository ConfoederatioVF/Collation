global.professions_Bairoch = class {
  static input_table_json = "./common/economics/bairoch_table_4.json";
  static input_detailed_borders_1914 = "./saves/detailed_borders/4.1914.1.1.naissance";
  static input_detailed_borders_1991 = "./saves/detailed_borders/7.1991.1.1.naissance";
  static output_folder = `${(global.h2 || "./histmap/2.data_cleaning/").replace(/[\\\/]$/, "")}/professions_Bairoch/`;
  static output_geocodes_1913_raster = `${this.output_folder}geocodes_1913.png`;
  static output_geocodes_1913_json = `${this.output_folder}geocodes_1913.json`;
  static output_borders_1913_geojson = `${this.output_folder}borders_1913.geojson`;

  static entity_to_bairoch_map = {
    "United Kingdom of Great Britain and Ireland": "GBR",
    "Kingdom of Belgium": "BEL",
    "Granduchy of Luxembourg": "BEL",
    "French Third Republic": "FRA",
    "Principality of Monaco": "FRA",
    "German Empire": "DEU",
    "Swiss Confederation": "CHE",
    "Principality of Liechtenstein": "CHE",
    "Austro-Hungarian Monarchy": "AUT_HUN",
    "Kingdom of Italy": "ITA",
    "Republic of San Marino": "ITA",
    "Kingdom of Spain": "ESP",
    "Principality of Andorra": "ESP",
    "First Portuguese Republic": "ESP",
    "Kingdom of Sweden": "SWE",
    "Kingdom of Norway": "SWE",
    "Kingdom of the Netherlands": "EUROPE",
    "Kingdom of Denmark": "EUROPE",
    "Kingdom of Bulgaria": "EUROPE",
    "Kingdom of Greece": "EUROPE",
    "Kingdom of Montenegro": "EUROPE",
    "Kingdom of Romania": "EUROPE",
    "Kingdom of Serbia": "EUROPE",
    "Republic of Central Albania": "EUROPE",
    "Russian Empire": "RUS",
    "USA": "USA",
    "Alaska Territory": "USA",
    "Hawaii Territory": "USA",
    "Puerto Rico": "USA",
    "Canada (Dominion)": "CAN",
    "Newfoundland (Dominion)": "CAN",
    "Commonwealth of Australia (Dominion)": "CAN",
    "Dominion of New Zealand": "CAN",
    "Japanese Empire": "JPN",
    "Republic of China": "CHN",
    "British India": "IND",
    "Republic of the United States of Brazil": "BRA",
    "United Mexican States": "MEX"
  };

  /**
   * Resolves a historical 1913 entity name to a Bairoch key.
   * @param {string} arg0_name
   * @returns {string|null}
   */
  static getBairochKeyFromEntityName (arg0_name) {
    //Convert from parameters
    let name = arg0_name || "";

    //Guard clause
    if (!name) return null;

    if (this.entity_to_bairoch_map[name]) return this.entity_to_bairoch_map[name];
    if (name.includes("Princely State") || name.includes("India")) return "IND";
    if (name.includes("Canada") || name.includes("Newfoundland") || name.includes("Australia") || name.includes("New Zealand")) return "CAN";
    if (name.includes("Denmark") || name.includes("Greenland")) return "EUROPE";
    if (name.includes("Norway")) return "SWE";
    if (name.includes("Portugal")) return "ESP";
    if (name.includes("Luxembourg")) return "BEL";
    if (name.includes("Liechtenstein")) return "CHE";
    if (name.includes("Monaco")) return "FRA";
    if (name.includes("San Marino")) return "ITA";
    if (name.includes("Alaska") || name.includes("Hawaii") || name.includes("Puerto Rico")) return "USA";
    if (name.includes("Bulgaria") || name.includes("Greece") || name.includes("Montenegro") || name.includes("Romania") || name.includes("Serbia") || name.includes("Albania")) return "EUROPE";

    for (let k in this.entity_to_bairoch_map) {
      if (name.includes(k)) return this.entity_to_bairoch_map[k];
    }

    //Return statement
    return null;
  };

  static iso3_to_bairoch_map = {
    "GBR": "GBR",
    "BEL": "BEL",
    "LUX": "BEL",
    "FRA": "FRA",
    "DEU": "DEU",
    "CHE": "CHE",
    "AUT": "AUT_HUN",
    "HUN": "AUT_HUN",
    "CZE": "AUT_HUN",
    "SVK": "AUT_HUN",
    "ITA": "ITA",
    "ESP": "ESP",
    "PRT": "ESP",
    "SWE": "SWE",
    "NOR": "SWE",
    "DNK": "EUROPE",
    "NLD": "EUROPE",
    "RUS": "RUS",
    "UKR": "RUS",
    "BLR": "RUS",
    "USA": "USA",
    "CAN": "CAN",
    "JPN": "JPN",
    "KOR": "JPN",
    "CHN": "CHN",
    "IND": "IND",
    "PAK": "IND",
    "BGD": "IND",
    "BRA": "BRA",
    "MEX": "MEX"
  };

  //UK benchmark points mapping Bairoch per-capita industrialisation index to manufacturing active share
  static uk_benchmark_points = [
    { b: 0, m: 0.050 },
    { b: 3, m: 0.080 },
    { b: 7, m: 0.135 },
    { b: 10, m: 0.180 },
    { b: 16, m: 0.285 },
    { b: 32, m: 0.380 },
    { b: 64, m: 0.455 },
    { b: 100, m: 0.480 },
    { b: 150, m: 0.485 }
  ];

  /**
   * Returns parsed Bairoch Table 4 data.
   * @returns {Object}
   */
  static getTableData () {
    //Declare local instance variables
    let table_path = path.resolve(this.input_table_json);

    //Guard clause
    if (!fs.existsSync(table_path)) {
      console.error(`Bairoch Table 4 not found at ${table_path}`);
      return null;
    }

    //Return statement
    return JSON.parse(fs.readFileSync(table_path, "utf8"));
  }

  /**
   * Interpolates Bairoch Table 4 per-capita level of industrialisation for any country series and year.
   * @param {string} arg0_bairoch_key
   * @param {number} arg1_year
   * 
   * @returns {number|null}
   */
  static getBairochLevel (arg0_bairoch_key, arg1_year) {
    //Convert from parameters
    let bairoch_key = arg0_bairoch_key;
    let year = parseFloat(arg1_year);

    //Declare local instance variables
    let table = this.getTableData();

    //Guard clauses
    if (!table || !table.data[bairoch_key]) return null;

    let row = table.data[bairoch_key];
    let vals = row.values;
    let years = table.years;

    if (year <= years[0]) return vals[0];
    if (year >= years[years.length - 1]) return vals[vals.length - 1];

    //Find bounding interval and interpolate with smoothstep spline
    for (let i = 0; i < years.length - 1; i++) {
      if (year >= years[i] && year <= years[i + 1]) {
        let v0 = (vals[i] !== null) ? vals[i] : vals[i + 1];
        let v1 = (vals[i + 1] !== null) ? vals[i + 1] : vals[i];
        let t = (year - years[i]) / (years[i + 1] - years[i]);
        let s = t * t * (3 - 2 * t);

        //Return statement
        return v0 + (v1 - v0) * s;
      }
    }

    //Return statement
    return null;
  }

  /**
   * Maps Bairoch index to target active manufacturing share calibrated against the UK 1900 benchmark.
   * @param {number} arg0_bairoch_level
   * @param {string} [arg1_sex="t"]
   * 
   * @returns {number}
   */
  static mapLevelToManufacturingShare (arg0_bairoch_level, arg1_sex) {
    //Convert from parameters
    let b = parseFloat(arg0_bairoch_level);
    let sex = arg1_sex || "t";

    //Guard clause
    if (isNaN(b) || b <= 0) return 0.05;

    //Declare local instance variables
    let pts = this.uk_benchmark_points;
    let share = pts[pts.length - 1].m;

    for (let i = 0; i < pts.length - 1; i++) {
      if (b >= pts[i].b && b <= pts[i + 1].b) {
        let t = (b - pts[i].b) / (pts[i + 1].b - pts[i].b);
        let s = t * t * (3 - 2 * t);
        share = pts[i].m + (pts[i + 1].m - pts[i].m) * s;
        break;
      }
    }

    //Sex differential alignment with historical LFPR distributions
    if (sex === "m") share = Math.min(0.58, share * 1.08);
    if (sex === "f") share = Math.max(0.04, share * 0.92);

    //Return statement
    return share;
  }

  /**
   * Returns target manufacturing share for a given Bairoch country key and year.
   * @param {string} arg0_bairoch_key
   * @param {number} arg1_year
   * @param {string} [arg2_sex="t"]
   * 
   * @returns {number|null}
   */
  static getManufacturingIntercept (arg0_bairoch_key, arg1_year, arg2_sex) {
    //Convert from parameters
    let bairoch_key = arg0_bairoch_key;
    let year = parseFloat(arg1_year);
    let sex = arg2_sex || "t";

    //Declare local instance variables
    let level = this.getBairochLevel(bairoch_key, year);

    //Guard clause
    if (level === null) return null;

    //Return statement
    return this.mapLevelToManufacturingShare(level, sex);
  }

  /**
   * Applies the empirical Bairoch manufacturing target to a structural baseline.
   * @param {string} arg0_bairoch_key
   * @param {Object} arg1_struct_target
   * @param {number} arg2_year
   * @param {string} [arg3_sex="t"]
   * 
   * @returns {Object}
   */
  static applyBairochTarget (arg0_bairoch_key, arg1_struct_target, arg2_year, arg3_sex) {
    //Convert from parameters
    let bairoch_key = arg0_bairoch_key;
    let struct_target = arg1_struct_target;
    let year = parseFloat(arg2_year);
    let sex = arg3_sex || "t";

    //Guard clauses
    if (!bairoch_key || !struct_target) return struct_target;

    let b_mfg = this.getManufacturingIntercept(bairoch_key, year, sex);
    if (b_mfg === null) return struct_target;

    let inf = struct_target.informal_labour;
    let rem = Math.max(0.01, 1.0 - inf - b_mfg);
    let tot_non_mfg = struct_target.agriculture + struct_target.services;
    let alpha_ag = (tot_non_mfg > 0) ? (struct_target.agriculture / tot_non_mfg) : 0.75;
    let alpha_se = (tot_non_mfg > 0) ? (struct_target.services / tot_non_mfg) : 0.25;

    //Return statement
    return {
      agriculture: rem * alpha_ag,
      manufacturing: b_mfg,
      services: rem * alpha_se,
      informal_labour: inf
    };
  }

  /**
   * Extracts 1913 boundaries from 4.1914.1.1.naissance, generates 1913 GeoJSON and raster.
   * @param {Object} [arg0_options]
   * @param {boolean} [arg0_options.overwrite=false]
   * 
   * @returns {Promise<Object>}
   */
  static async extract1913Borders (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
    let overwrite = (options.overwrite !== undefined) ? options.overwrite : false;

    //Declare local instance variables
    let output_folder = this.output_folder;
    let output_geojson_path = this.output_borders_1913_geojson;
    let output_json_path = this.output_geocodes_1913_json;
    let output_raster_path = this.output_geocodes_1913_raster;

    if (!fs.existsSync(output_folder)) fs.mkdirSync(output_folder, { recursive: true });

    if (!overwrite && fs.existsSync(output_raster_path) && fs.existsSync(output_json_path)) {
      console.log(`[professions_Bairoch] 1913 boundaries and raster already exist at ${output_raster_path}`);
      return JSON.parse(fs.readFileSync(output_json_path, "utf8"));
    }

    console.log(`[professions_Bairoch] Extracting 1913 borders from ${this.input_detailed_borders_1914}..`);

    let naissance_path = path.resolve(this.input_detailed_borders_1914);
    if (!fs.existsSync(naissance_path)) {
      console.error(`Naissance file not found at ${naissance_path}`);
      return null;
    }

    let data = JSON.parse(fs.readFileSync(naissance_path, "utf8"));
    let ts1913 = Date.getTimestamp({ year: 1913, month: 12, day: 31, hour: 0, minute: 0 });

    let features = [];
    let entity_map = {};
    let next_cid = 1;
    let width = 4320;
    let height = 2160;
    let buf = new Int32Array(width * height);

    //Fast scanline polygon rasteriser
    let rasterizeRing = function (ring, cid) {
      if (!ring || ring.length < 3) return;
      let pts = [];
      let min_y = height, max_y = 0;

      for (let i = 0; i < ring.length; i++) {
        let lon = ring[i][0];
        let lat = ring[i][1];
        let x = (lon + 180) * (width / 360);
        let y = (90 - lat) * (height / 180);
        pts.push([x, y]);
        if (y < min_y) min_y = Math.floor(y);
        if (y > max_y) max_y = Math.ceil(y);
      }
      min_y = Math.max(0, min_y);
      max_y = Math.min(height - 1, max_y);

      for (let y = min_y; y <= max_y; y++) {
        let scan_y = y + 0.5;
        let node_x = [];

        for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
          let y1 = pts[i][1], y2 = pts[j][1];
          if ((y1 < scan_y && y2 >= scan_y) || (y2 < scan_y && y1 >= scan_y)) {
            let x1 = pts[i][0], x2 = pts[j][0];
            let x = x1 + (scan_y - y1) / (y2 - y1) * (x2 - x1);
            node_x.push(x);
          }
        }

        node_x.sort((a, b) => a - b);
        for (let k = 0; k < node_x.length; k += 2) {
          let x_start = Math.max(0, Math.ceil(node_x[k]));
          let x_end = Math.min(width - 1, Math.floor(node_x[k + 1]));
          let row_offset = y * width;
          for (let x = x_start; x <= x_end; x++) {
            buf[row_offset + x] = cid;
          }
        }
      }
    };

    let all_ids = Object.keys(data);
    for (let i = 0; i < all_ids.length; i++) {
      let id = all_ids[i];
      let ent = data[id];

      if (ent.type === "geometry" && ent.history) {
        let hist = new History();
        hist.fromJSON(ent.history);
        let res = hist.getKeyframe({ date: ts1913 });

        if (res && res.value && res.value[0] && res.value[0].coordinates && res.value[0].coordinates.length > 0) {
          let geom = res.value[0];
          let meta = res.value[2] || {};
          let raw_name = (meta.name || "").replace(/\n/g, " ").trim();
          let cid = next_cid++;

          let bairoch_key = professions_Bairoch.getBairochKeyFromEntityName(raw_name);

          let r = (cid >> 16) & 255;
          let g = (cid >> 8) & 255;
          let b = cid & 255;
          let col_str = `${r},${g},${b}`;

          entity_map[col_str] = {
            cid: cid,
            id: id,
            name: raw_name,
            bairoch_key: bairoch_key,
            area: meta.area
          };

          features.push({
            type: "Feature",
            id: id,
            properties: {
              cid: cid,
              col_str: col_str,
              id: id,
              name: raw_name,
              bairoch_key: bairoch_key,
              area: meta.area
            },
            geometry: geom
          });

          let polys = (geom.type === "Polygon") ? [geom.coordinates] : ((geom.type === "MultiPolygon") ? geom.coordinates : []);
          for (let p = 0; p < polys.length; p++) {
            rasterizeRing(polys[p][0], cid);
          }
        }
      }
    }

    console.log(`[professions_Bairoch] Rasterised ${features.length} entities to 1913 grid.`);

    //Save GeoJSON
    fs.writeFileSync(output_geojson_path, JSON.stringify({
      type: "FeatureCollection",
      features: features
    }), "utf8");

    //Save JSON Lookup
    fs.writeFileSync(output_json_path, JSON.stringify(entity_map, null, 2), "utf8");

    //Save GeoPNG
    let png = new pngjs.PNG({ width: width, height: height });
    for (let j = 0; j < width * height; j++) {
      let cid = buf[j];
      let idx = j << 2;
      if (cid > 0) {
        png.data[idx] = (cid >> 16) & 255;
        png.data[idx + 1] = (cid >> 8) & 255;
        png.data[idx + 2] = cid & 255;
        png.data[idx + 3] = 255;
      } else {
        png.data[idx] = 0;
        png.data[idx + 1] = 0;
        png.data[idx + 2] = 0;
        png.data[idx + 3] = 0;
      }
    }

    await new Promise((resolve, reject) => {
      png.pack().pipe(fs.createWriteStream(output_raster_path)).on("finish", resolve).on("error", reject);
    });

    console.log(`[professions_Bairoch] Successfully saved 1913 boundaries raster to ${output_raster_path}`);

    //Return statement
    return entity_map;
  }
};
