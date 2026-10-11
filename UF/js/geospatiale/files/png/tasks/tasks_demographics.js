if (!global.GeoPNG) global.GeoPNG = {};
if (!global.GeoPNG.tasks) global.GeoPNG.tasks = {};

//Initialise demographic and migration tasks
{
  /**
   * Clamps professions percentages and aggregates.
   * 
   * @param {Object} arg0_task
   *  @param {string[]} arg0_task.categories
   *  @param {string} arg0_task.input_folder
   *  @param {string} arg0_task.output_folder
   *  @param {number} arg0_task.year
   *  @param {Object} [arg0_task.options]
   * 
   * @returns {Promise<Object>}
   */
  GeoPNG.tasks.clamp_professions = async function (arg0_task) {
    //Convert from parameters
    let task = (arg0_task) ? arg0_task : {};

    //Declare local instance variables
    let getCountryStructuralBaselines = function (arg0_gdp_pc, arg1_urb_rate, arg2_year, arg3_sex) {
      let gdp_pc = (typeof arg0_gdp_pc === "number" && !isNaN(arg0_gdp_pc)) ? arg0_gdp_pc : 1000;
      let sex = (arg3_sex || "m").toLowerCase();
      let urb_rate = (typeof arg1_urb_rate === "number" && !isNaN(arg1_urb_rate)) ? arg1_urb_rate : 0.10;
      let year = (typeof arg2_year === "number" && !isNaN(arg2_year)) ? arg2_year : 1860;

      let agri = 0.50;
      let inf = (sex === "f") ? 0.05 : 0.04;
      let mfg = 0.25;
      let serv = 0.20;

      //1. Pre-Neolithic to Neolithic Transition (-10000 to -3000 BC)
      if (year < -3000) {
        let lambda_points = [
          { y: -10000, l: 0.00 }, { y: -8000, l: 0.02 }, { y: -6000, l: 0.10 },
          { y: -4000, l: 0.70 }, { y: -3000, l: 1.00 }
        ];
        let lambda = 0.0;
        if (year <= -10000) {
          lambda = 0.0;
        } else {
          let lower = lambda_points[0], upper = lambda_points[lambda_points.length - 1];
          for (let i = 0; i < lambda_points.length - 1; i++) {
            if (year >= lambda_points[i].y && year <= lambda_points[i + 1].y) {
              lower = lambda_points[i];
              upper = lambda_points[i + 1];
              break;
            }
          }
          let frac = (year - lower.y) / (upper.y - lower.y);
          lambda = lower.l + frac * (upper.l - lower.l);
        }

        let agri_neolithic = 0.85;
        let inf_neolithic = (sex === "f") ? 0.05 : 0.05;
        let mfg_neolithic = 0.06;
        let serv_neolithic = 0.04;

        let forager_agri = 0.05;
        let forager_inf = 0.90;
        let forager_mfg = 0.03;
        let forager_serv = 0.02;

        agri = (1.0 - lambda) * forager_agri + lambda * agri_neolithic;
        inf = (1.0 - lambda) * forager_inf + lambda * inf_neolithic;
        mfg = (1.0 - lambda) * forager_mfg + lambda * mfg_neolithic;
        serv = (1.0 - lambda) * forager_serv + lambda * serv_neolithic;
      } else if (year < 1750) {
        //2. Ancient, Mediaeval, and Early Modern Era (-3000 to 1750 AD)
        let gdp_factor = Math.max(0, Math.min(1, (gdp_pc - 400) / 1600));
        let urb_factor = Math.max(0, Math.min(1, urb_rate / 0.25));

        agri = 0.85 - 0.20 * gdp_factor - 0.25 * urb_factor;
        agri = Math.max(0.40, Math.min(0.92, agri));

        mfg = 0.06 + 0.10 * gdp_factor + 0.12 * urb_factor;
        mfg = Math.max(0.04, Math.min(0.25, mfg));

        serv = 0.04 + 0.08 * gdp_factor + 0.12 * urb_factor;
        serv = Math.max(0.03, Math.min(0.22, serv));

        inf = 1.0 - (agri + mfg + serv);
        inf = Math.max(0.01, Math.min(0.15, inf));
      } else {
        //3. Modern Industrial Era (1750 AD+)
        let log_gdp = Math.log(Math.max(400, gdp_pc));
        let log_gdp_sq = log_gdp * log_gdp;

        agri = 1.80 - 0.18 * log_gdp - 0.40 * urb_rate;
        agri = Math.max(0.01, Math.min(0.85, agri));

        mfg = -0.40 + 0.08 * log_gdp - 0.003 * log_gdp_sq + 0.25 * urb_rate;
        mfg = Math.max(0.05, Math.min(0.45, mfg));

        serv = -0.50 + 0.12 * log_gdp + 0.35 * urb_rate;
        serv = Math.max(0.05, Math.min(0.85, serv));

        inf = 1.0 - (agri + mfg + serv);
        inf = Math.max(0.01, Math.min(0.12, inf));
      }

      let total = agri + inf + mfg + serv;
      if (total <= 0) return { agri: 0.25, inf: 0.25, mfg: 0.25, serv: 0.25 };

      return {
        agri: agri / total,
        inf: inf / total,
        mfg: mfg / total,
        serv: serv / total
      };
    };

    let categories = task.categories || ["agri", "inf", "mfg", "serv"];
    let gdp_pc_path = task.gdp_pc_path;
    let geocodes_path = task.geocodes_path;
    let input_folder = task.input_folder;
    let output_folder = task.output_folder;
    let popc_path = task.popc_path;
    let sex = task.sex || "m";
    let urb_rate_path = task.urb_rate_path;
    let year = task.year;

    if (!fs.existsSync(output_folder)) fs.mkdirSync(output_folder, { recursive: true });

    let cat_rasters = {};
    for (let c = 0; c < categories.length; c++) {
      let cat = categories[c];
      let p = path.join(input_folder, `${sex}_${cat}_${year}.png`);
      if (fs.existsSync(p)) {
        cat_rasters[cat] = await GeoPNG.loadNumberRasterImageAsync(p, { format: "float32" });
      }
    }

    let popc_raster = (popc_path && fs.existsSync(popc_path)) ?
      await GeoPNG.loadNumberRasterImageAsync(popc_path, { format: "float32" }) : null;
    let gdp_raster = (gdp_pc_path && fs.existsSync(gdp_pc_path)) ?
      await GeoPNG.loadNumberRasterImageAsync(gdp_pc_path, { format: "float32" }) : null;
    let urb_raster = (urb_rate_path && fs.existsSync(urb_rate_path)) ?
      await GeoPNG.loadNumberRasterImageAsync(urb_rate_path, { format: "float32" }) : null;

    let first_cat = categories[0];
    if (!cat_rasters[first_cat]) return { success: false, reason: "missing_input_rasters" };

    let height = cat_rasters[first_cat].height;
    let total_pixels = cat_rasters[first_cat].data.length;
    let width = cat_rasters[first_cat].width;

    let out_buffers = {};
    for (let c = 0; c < categories.length; c++)
      out_buffers[categories[c]] = new Float32Array(total_pixels);

    for (let i = 0; i < total_pixels; i++) {
      let pop = (popc_raster) ? popc_raster.data[i] : 1;
      if (pop <= 0 || isNaN(pop)) continue;

      let gdp_pc = (gdp_raster) ? gdp_raster.data[i] : 1000;
      let urb_rate = (urb_raster) ? urb_raster.data[i] : 0.10;
      let baselines = getCountryStructuralBaselines(gdp_pc, urb_rate, year, sex);

      let sum = 0;
      for (let c = 0; c < categories.length; c++) {
        let cat = categories[c];
        let val = cat_rasters[cat] ? cat_rasters[cat].data[i] : 0;
        if (isNaN(val) || val <= 0) val = baselines[cat] || 0.25;
        out_buffers[cat][i] = val;
        sum += val;
      }

      if (sum > 0) {
        let inv_sum = 1 / sum;
        for (let c = 0; c < categories.length; c++)
          out_buffers[categories[c]][i] *= inv_sum;
      } else {
        for (let c = 0; c < categories.length; c++)
          out_buffers[categories[c]][i] = baselines[categories[c]] || 0.25;
      }
    }

    for (let c = 0; c < categories.length; c++) {
      let cat = categories[c];
      let out_path = path.join(output_folder, `${sex}_${cat}_${year}.png`);
      await GeoPNG.saveNumberRasterImageAsync({
        data: out_buffers[cat],
        file_path: out_path,
        format: "float32",
        height: height,
        width: width
      });
    }

    //Return statement
    return { success: true, year: year };
  };


  /**
   * Derives migration rasters (births, deaths, cohort sex ratio, net migration).
   * 
   * @param {Object} arg0_task
   * 
   * @returns {Promise<Object>}
   */
  GeoPNG.tasks.derive_migration_rasters = async function (arg0_task) {
    //Convert from parameters
    let task = (arg0_task) ? arg0_task : {};

    //Declare local instance variables
    let births_path = task.births_path;
    let delta_popc_path = task.delta_popc_path;
    let female_cohort_paths = task.female_cohort_paths || [];
    let female_deaths_path = task.female_deaths_path;
    let female_migration_path = task.female_migration_path;
    let male_cohort_paths = task.male_cohort_paths || [];
    let male_deaths_path = task.male_deaths_path;
    let male_migration_path = task.male_migration_path;
    let net_migration_path = task.net_migration_path;
    let overwrite = (task.overwrite !== undefined) ? task.overwrite : true;
    let popc_path = task.popc_path;
    let previous_popc_path = task.previous_popc_path;
    let year_gap = task.year_gap || 10;

    if (!overwrite && fs.existsSync(net_migration_path) && fs.existsSync(female_migration_path) && fs.existsSync(male_migration_path))
      return { skipped: true, year: task.year };

    if (!popc_path || !fs.existsSync(popc_path)) return { reason: "missing_popc", success: false };

    let popc_raster = await GeoPNG.loadNumberRasterImageAsync(popc_path, { format: "float32" });
    let total_pixels = popc_raster.data.length;
    let height = popc_raster.height;
    let width = popc_raster.width;

    let delta_raster = (delta_popc_path && fs.existsSync(delta_popc_path)) ?
      await GeoPNG.loadNumberRasterImageAsync(delta_popc_path, { format: "float32" }) : null;
    let prev_popc = (previous_popc_path && fs.existsSync(previous_popc_path)) ?
      await GeoPNG.loadNumberRasterImageAsync(previous_popc_path, { format: "float32" }) : null;

    let births_raster = (births_path && fs.existsSync(births_path)) ?
      await GeoPNG.loadNumberRasterImageAsync(births_path, { format: "float32" }) : null;
    let f_deaths = (female_deaths_path && fs.existsSync(female_deaths_path)) ?
      await GeoPNG.loadNumberRasterImageAsync(female_deaths_path, { format: "float32" }) : null;
    let m_deaths = (male_deaths_path && fs.existsSync(male_deaths_path)) ?
      await GeoPNG.loadNumberRasterImageAsync(male_deaths_path, { format: "float32" }) : null;

    let net_migration = new Float32Array(total_pixels);
    let f_migration = new Float32Array(total_pixels);
    let m_migration = new Float32Array(total_pixels);

    for (let i = 0; i < total_pixels; i++) {
      let delta = delta_raster ? delta_raster.data[i] : (prev_popc ? (popc_raster.data[i] - prev_popc.data[i]) : 0);
      let births = births_raster ? births_raster.data[i] : 0;
      let deaths = (f_deaths ? f_deaths.data[i] : 0) + (m_deaths ? m_deaths.data[i] : 0);

      let natural_increase = (births - deaths) * (year_gap / 10);
      let mig = delta - natural_increase;

      net_migration[i] = mig;
      f_migration[i] = mig * 0.49;
      m_migration[i] = mig * 0.51;
    }

    let out_dir = path.dirname(net_migration_path);
    if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });

    await GeoPNG.saveNumberRasterImageAsync({
      data: net_migration,
      file_path: net_migration_path,
      format: "float32",
      height: height,
      width: width
    });

    if (female_migration_path)
      await GeoPNG.saveNumberRasterImageAsync({
        data: f_migration,
        file_path: female_migration_path,
        format: "float32",
        height: height,
        width: width
      });

    if (male_migration_path)
      await GeoPNG.saveNumberRasterImageAsync({
        data: m_migration,
        file_path: male_migration_path,
        format: "float32",
        height: height,
        width: width
      });

    //Return statement
    return { success: true, year: task.year };
  };
}
