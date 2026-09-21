#!/usr/bin/env node
/**
 * Interactive Terminal User Interface (TUI) for Age/Sex Counterfactuals Battery.
 * Evaluates 9 candidate models across 5 methodological families, benchmarks out-of-sample
 * utility [R^2(male) + R^2(female)]/2, and orchestrates raster generation and clamping.
 *
 * Usage:
 *   node histmap/3.data_transform/age_sex_counterfactuals/counterfactuals_tui.js
 *   node histmap/3.data_transform/age_sex_counterfactuals/counterfactuals_tui.js --benchmark
 *   node histmap/3.data_transform/age_sex_counterfactuals/counterfactuals_tui.js --generate --model=sgd_separate_curves
 */

let fs = require("fs");
let path = require("path");
let readline = require("readline");

//Bootstrap UF environment
global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");

try { global.JSON5 = require("json5"); } catch (e) {}
try { global.mathjs = require("mathjs"); } catch (e) {}
try { global.ml_matrix = require("ml-matrix"); } catch (e) {}

let root_dir = path.resolve(__dirname, "../../..");

let loadDirectory = function (rel_dir) {
  let full_dir = path.join(root_dir, rel_dir);
  if (fs.existsSync(full_dir)) {
    let files = fs.readdirSync(full_dir).filter(f => f.endsWith(".js") && !f.includes("worker"));
    for (let i = 0; i < files.length; i++) {
      try {
        require(path.join(full_dir, files[i]));
      } catch (e) {
        console.error(`Failed to require ${path.join(rel_dir, files[i])}:`, e);
      }
    }
  }
};

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

//Define Histmap paths
global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");
global.h4 = path.join(root_dir, "histmap/4.data_exports/");
global.h5 = path.join(root_dir, "histmap/5.data_visualisation/");

let safeRequire = function (rel_path) {
  let full_path = path.join(root_dir, rel_path);
  if (fs.existsSync(full_path)) {
    try {
      require(full_path);
    } catch (e) {
      console.error(`Failed to require ${rel_path}:`, e);
    }
  }
};

safeRequire("histmap/2.data_cleaning/landuse_HYDE/landuse_HYDE.js");
safeRequire("histmap/2.data_cleaning/population_Stadester/population_Stadester.js");
safeRequire("histmap/2.data_cleaning/population_Stadester/stadester_rasters.js");
safeRequire("histmap/2.data_cleaning/population_Stadester/stadester_uud.js");
safeRequire("histmap/2.data_cleaning/metadata_HYDE/metadata_HYDE.js");
safeRequire("histmap/2.data_cleaning/admin_modern/admin_modern.js");
safeRequire("histmap/2.data_cleaning/age_sex_HMD/age_sex_HMD.js");
safeRequire("histmap/2.data_cleaning/age_sex_UNWPP/age_sex_UNWPP.js");
safeRequire("histmap/3.data_transform/age_sex/age_sex.js");
safeRequire("histmap/3.data_transform/GDP_pc/GDP_pc.js");
safeRequire("histmap/3.data_transform/GDP_PPP_pc/GDP_PPP_pc.js");
safeRequire("histmap/3.data_transform/wealth_income/wealth_income.js");
safeRequire("histmap/3.data_transform/GDP_Eoscala.transform/GDP_Eoscala_transform.js");
safeRequire("histmap/3.data_transform/population_Stadester.transform/population_Stadester_transform.js");

//Require Counterfactual modules
require(path.join(__dirname, "counterfactuals_evaluator.js"));
require(path.join(__dirname, "1.1.un_model_life_tables/un_model_life_tables.js"));
require(path.join(__dirname, "1.2.coale_demeny_life_tables/coale_demeny_life_tables.js"));
require(path.join(__dirname, "1.3.ledermann_life_tables/ledermann_life_tables.js"));
require(path.join(__dirname, "1.4.brass_logit_life_tables/brass_logit_life_tables.js"));
require(path.join(__dirname, "1.5.un_developing_life_tables/un_developing_life_tables.js"));
require(path.join(__dirname, "2.0.gompertz_makeham_siler/gompertz_makeham_siler.js"));
require(path.join(__dirname, "3.0.sgd_separate_curves/sgd_separate_curves.js"));
require(path.join(__dirname, "4.0.sgd_gan_optimizer/sgd_gan_optimizer.js"));
require(path.join(__dirname, "5.0.multinomial_logit_piecewise/multinomial_logit_piecewise.js"));
require(path.join(__dirname, "age_sex_counterfactuals.js"));

//ANSI Color codes for rich console styling
let C_RESET = "\x1b[0m";
let C_BOLD = "\x1b[1m";
let C_CYAN = "\x1b[36m";
let C_GREEN = "\x1b[32m";
let C_YELLOW = "\x1b[33m";
let C_RED = "\x1b[31m";
let C_MAGENTA = "\x1b[35m";
let C_BLUE = "\x1b[34m";

/**
 * Terminal User Interface controller class.
 */
class CounterfactualsTUI {
  constructor () {
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });
  }

  clearScreen () {
    process.stdout.write("\x1b[2J\x1b[0;0H");
  }

  printHeader () {
    let report_path = path.join(age_sex_counterfactuals.benchmarks_folder, "battery_benchmark_report.json");
    let winner_str = "None (Benchmark not yet run)";

    if (fs.existsSync(report_path)) {
      try {
        let rep = JSON.parse(fs.readFileSync(report_path, "utf8"));
        if (rep && rep.winner)
          winner_str = `${rep.winner.name} [Utility: ${(rep.winner.utility*100).toFixed(2)}%]`;
      } catch (e) {}
    }

    console.log(`${C_CYAN}================================================================================${C_RESET}`);
    console.log(`${C_BOLD}${C_CYAN} NAISSANCE HGIS / SVEA — AGE/SEX COUNTERFACTUALS BATTERY TUI${C_RESET}`);
    console.log(`${C_CYAN}================================================================================${C_RESET}`);
    console.log(` Active Selected Winner : ${C_BOLD}${C_GREEN}${winner_str}${C_RESET}`);
    console.log(` Target Metric          : ${C_BOLD}[R^2(male) + R^2(female)] / 2${C_RESET} (Out-of-sample over HMD & UNWPP)`);
    console.log(` Candidate Models       : 9 models across 5 methodological families`);
    console.log(`${C_CYAN}--------------------------------------------------------------------------------${C_RESET}\n`);
  }

  showMainMenu () {
    this.printHeader();
    console.log(`${C_BOLD}BATTERY WORKFLOW ACTIONS:${C_RESET}`);
    console.log(`  ${C_CYAN}[1]${C_RESET} ${C_BOLD}Run Full Battery Benchmark${C_RESET} (trains & evaluates all 9 models)`);
    console.log(`  ${C_CYAN}[2]${C_RESET} ${C_BOLD}View Goodness-of-Fit Leaderboard${C_RESET} (R^2 male, R^2 female, Utility, MAE%)`);
    console.log(`  ${C_CYAN}[3]${C_RESET} ${C_BOLD}Inspect Detailed Model Diagnostic${C_RESET} (per-country fits & age-band errors)`);
    console.log(`  ${C_CYAN}[4]${C_RESET} ${C_BOLD}Designate Winning Model${C_RESET} (set active counterfactual for production)`);
    console.log(`  ${C_CYAN}[5]${C_RESET} ${C_BOLD}Generate Rasters for Model${C_RESET} (probabilities, PAVA isotonic clamping)`);
    console.log(`  ${C_CYAN}[6]${C_RESET} ${C_BOLD}Export Benchmark Report${C_RESET} (JSON & Markdown)`);
    console.log(`  ${C_RED}[0]${C_RESET} Exit TUI\n`);

    this.rl.question(`${C_YELLOW}Select option [0-6]: ${C_RESET}`, async (answer) => {
      let choice = answer.trim();
      if (choice === "1") {
        await this.handleRunBenchmark();
      } else if (choice === "2") {
        await this.handleViewLeaderboard();
      } else if (choice === "3") {
        await this.handleInspectDiagnostic();
      } else if (choice === "4") {
        await this.handleSelectWinner();
      } else if (choice === "5") {
        await this.handleGenerateRasters();
      } else if (choice === "6") {
        await this.handleExportReport();
      } else if (choice === "0" || choice.toLowerCase() === "q") {
        console.log(`\n${C_GREEN}Exiting Counterfactuals TUI. Goodbye!${C_RESET}\n`);
        this.rl.close();
        process.exit(0);
      } else {
        this.clearScreen();
        this.showMainMenu();
      }
    });
  }

  async handleRunBenchmark () {
    this.clearScreen();
    this.printHeader();
    console.log(`${C_BOLD}${C_YELLOW}Starting Full Battery Benchmark Execution...${C_RESET}\n`);

    try {
      await age_sex_counterfactuals.runBatteryBenchmark();
      console.log(`\n${C_BOLD}${C_GREEN}Benchmark completed successfully!${C_RESET}`);
    } catch (e) {
      console.error(`${C_RED}Error running battery benchmark:${C_RESET}`, e);
    }

    this.rl.question(`\n${C_YELLOW}Press Enter to return to main menu...${C_RESET}`, () => {
      this.clearScreen();
      this.showMainMenu();
    });
  }

  async handleViewLeaderboard () {
    this.clearScreen();
    this.printHeader();
    let report_path = path.join(age_sex_counterfactuals.benchmarks_folder, "battery_benchmark_report.json");

    if (!fs.existsSync(report_path)) {
      console.log(`${C_YELLOW}No benchmark results found on disk. Please run Option [1] first.${C_RESET}\n`);
    } else {
      let rep = JSON.parse(fs.readFileSync(report_path, "utf8"));
      let lb = rep.leaderboard || [];

      console.log(`${C_BOLD}GOODNESS-OF-FIT BENCHMARK LEADERBOARD (Out-of-sample over HMD & UNWPP):${C_RESET}\n`);
      let table_data = lb.map(m => ({
        Rank: m.rank,
        Model: m.name,
        "Utility Metric": (m.utility*100).toFixed(2) + "%",
        "R^2 (Male)": (m.r2_male*100).toFixed(2) + "%",
        "R^2 (Female)": (m.r2_female*100).toFixed(2) + "%",
        "MAE%": m.mae_pct.toFixed(3) + "%",
        "RMSE%": m.rmse_pct.toFixed(3) + "%",
        "Delta vs Base": (m.delta_vs_baseline_pct >= 0 ? "+" : "") + m.delta_vs_baseline_pct.toFixed(2) + "%"
      }));
      console.table(table_data);

      console.log(`\n${C_CYAN}Demographic Utility Metric Formula: [R^2(male) + R^2(female)] / 2${C_RESET}`);
      console.log(`Baseline reference: Multinomial Logit (Piecewise) = ${(rep.baseline_utility*100).toFixed(2)}%\n`);
    }

    this.rl.question(`${C_YELLOW}Press Enter to return to main menu...${C_RESET}`, () => {
      this.clearScreen();
      this.showMainMenu();
    });
  }

  async handleInspectDiagnostic () {
    this.clearScreen();
    this.printHeader();
    let report_path = path.join(age_sex_counterfactuals.benchmarks_folder, "battery_benchmark_report.json");

    if (!fs.existsSync(report_path)) {
      console.log(`${C_YELLOW}No benchmark results found. Please run Option [1] first.${C_RESET}\n`);
      this.rl.question(`${C_YELLOW}Press Enter to return...${C_RESET}`, () => {
        this.clearScreen();
        this.showMainMenu();
      });
      return;
    }

    let rep = JSON.parse(fs.readFileSync(report_path, "utf8"));
    let lb = rep.leaderboard || [];

    console.log(`${C_BOLD}SELECT MODEL FOR DETAILED DIAGNOSTIC:${C_RESET}\n`);
    for (let i = 0; i < lb.length; i++)
      console.log(`  [${i + 1}] ${lb[i].name} (Utility: ${(lb[i].utility*100).toFixed(2)}%)`);
    console.log(`  [0] Return to main menu\n`);

    this.rl.question(`${C_YELLOW}Enter model number: ${C_RESET}`, (ans) => {
      let idx = parseInt(ans.trim()) - 1;
      if (idx >= 0 && idx < lb.length) {
        let m = lb[idx];
        this.clearScreen();
        this.printHeader();
        console.log(`${C_BOLD}${C_CYAN}DIAGNOSTIC REPORT FOR: ${m.name}${C_RESET}\n`);
        console.log(`  - Overall Demographic Utility : ${(m.utility*100).toFixed(2)}%`);
        console.log(`  - Male Cohort Curve R^2        : ${(m.r2_male*100).toFixed(2)}%`);
        console.log(`  - Female Cohort Curve R^2      : ${(m.r2_female*100).toFixed(2)}%`);
        console.log(`  - Mean Absolute Error (MAE)    : ${m.mae_pct.toFixed(3)}%`);
        console.log(`  - Root Mean Squared Error      : ${m.rmse_pct.toFixed(3)}%`);
        console.log(`  - Mean Pyramid Pearson r       : ${m.mean_pyramid_r2 !== undefined ? (m.mean_pyramid_r2*100).toFixed(2) + "%" : "N/A"}`);
        console.log(`  - Delta vs Piecewise Baseline  : ${(m.delta_vs_baseline_pct >= 0 ? "+" : "")}${m.delta_vs_baseline_pct.toFixed(2)}%\n`);

        if (m.per_country_table && m.per_country_table.length > 0) {
          console.log(`${C_BOLD}Sample Out-of-Sample Per-Country Goodness-of-Fit (Top 10):${C_RESET}`);
          console.table(m.per_country_table.slice(0, 10));
        }

        this.rl.question(`\n${C_YELLOW}Press Enter to return to main menu...${C_RESET}`, () => {
          this.clearScreen();
          this.showMainMenu();
        });
      } else {
        this.clearScreen();
        this.showMainMenu();
      }
    });
  }

  async handleSelectWinner () {
    this.clearScreen();
    this.printHeader();
    let report_path = path.join(age_sex_counterfactuals.benchmarks_folder, "battery_benchmark_report.json");

    if (!fs.existsSync(report_path)) {
      console.log(`${C_YELLOW}Please run benchmark [1] first to evaluate candidate models.${C_RESET}\n`);
      this.rl.question(`${C_YELLOW}Press Enter to return...${C_RESET}`, () => {
        this.clearScreen();
        this.showMainMenu();
      });
      return;
    }

    let rep = JSON.parse(fs.readFileSync(report_path, "utf8"));
    let winner = rep.winner;
    console.log(`${C_BOLD}DESIGNATING PRODUCTION COUNTERFACTUAL MODEL:${C_RESET}\n`);
    console.log(`  Highest Utility Model: ${C_BOLD}${C_GREEN}${winner.name}${C_RESET} (${(winner.utility*100).toFixed(2)}%)`);
    console.log(`  Location              : histmap/3.data_transform/age_sex_counterfactuals/${winner.folder}/\n`);

    let winner_json_path = path.join(age_sex_counterfactuals.cf, "active_winner.json");
    fs.writeFileSync(winner_json_path, JSON.stringify(winner, null, 2));
    console.log(`${C_GREEN}Active winner successfully designated and written to active_winner.json!${C_RESET}\n`);

    this.rl.question(`${C_YELLOW}Press Enter to return to main menu...${C_RESET}`, () => {
      this.clearScreen();
      this.showMainMenu();
    });
  }

  async handleGenerateRasters () {
    this.clearScreen();
    this.printHeader();
    console.log(`${C_BOLD}RASTER GENERATION PIPELINE:${C_RESET}\n`);

    let cases = age_sex_counterfactuals.cases;
    for (let i = 0; i < cases.length; i++)
      console.log(`  [${i + 1}] ${cases[i].name} (${cases[i].id})`);
    console.log(`  [0] Return to main menu\n`);

    this.rl.question(`${C_YELLOW}Select model to generate rasters for [1-9]: ${C_RESET}`, async (ans) => {
      let idx = parseInt(ans.trim()) - 1;
      if (idx >= 0 && idx < cases.length) {
        let sel_case = cases[idx];
        console.log(`\n${C_BOLD}${C_CYAN}Selected: ${sel_case.name}${C_RESET}`);
        this.rl.question(`${C_YELLOW}Enter years separated by commas (default: 1850,1900,1950): ${C_RESET}`, async (y_ans) => {
          let y_str = y_ans.trim() || "1850,1900,1950";
          let years = y_str.split(",").map(s => parseInt(s.trim())).filter(n => !isNaN(n));

          try {
            console.log(`\n[TUI] Executing raster pipeline for ${sel_case.id} over years: ${years.join(", ")}...`);
            await age_sex_counterfactuals.processRasters({
              model_id: sel_case.id,
              years: years
            });
            console.log(`\n${C_GREEN}Raster generation and PAVA isotonic clamping complete!${C_RESET}`);
          } catch (e) {
            console.error(`${C_RED}Error generating rasters:${C_RESET}`, e);
          }

          this.rl.question(`\n${C_YELLOW}Press Enter to return to main menu...${C_RESET}`, () => {
            this.clearScreen();
            this.showMainMenu();
          });
        });
      } else {
        this.clearScreen();
        this.showMainMenu();
      }
    });
  }

  async handleExportReport () {
    this.clearScreen();
    this.printHeader();
    let report_path = path.join(age_sex_counterfactuals.benchmarks_folder, "battery_benchmark_report.json");
    let md_path = path.join(age_sex_counterfactuals.benchmarks_folder, "battery_benchmark_report.md");

    if (fs.existsSync(report_path) && fs.existsSync(md_path)) {
      console.log(`${C_BOLD}${C_GREEN}Benchmark reports are active and saved:${C_RESET}\n`);
      console.log(`  JSON Artifact: ${report_path}`);
      console.log(`  Markdown Doc : ${md_path}\n`);
    } else {
      console.log(`${C_YELLOW}No report exists yet. Running battery benchmark now to generate fresh report...${C_RESET}\n`);
      await age_sex_counterfactuals.runBatteryBenchmark();
      console.log(`\n${C_GREEN}Reports exported successfully!${C_RESET}\n`);
    }

    this.rl.question(`${C_YELLOW}Press Enter to return to main menu...${C_RESET}`, () => {
      this.clearScreen();
      this.showMainMenu();
    });
  }

  async start (cli_args) {
    if (cli_args.benchmark) {
      console.log(`[CLI] Running non-interactive counterfactuals benchmark...`);
      let bench = await age_sex_counterfactuals.runBatteryBenchmark({
        epochs: (cli_args.fast) ? 200 : 1000,
        iterations: (cli_args.fast) ? 500 : 3000
      });
      console.log(`[CLI] Benchmark complete. Winner: ${bench.winner.name} (Utility: ${(bench.winner.utility*100).toFixed(2)}%)`);
      process.exit(0);
    } else if (cli_args.generate || cli_args["generate-rasters"]) {
      let model_id = cli_args.model || (await age_sex_counterfactuals.selectWinningModel()).id;
      let years_str = cli_args.years || cli_args.year || "1850";
      let years = years_str.split(",").map(Number);
      console.log(`[CLI] Generating rasters for ${model_id} on years: ${years.join(", ")}...`);
      await age_sex_counterfactuals.processRasters({ model_id: model_id, years: years });
      console.log(`[CLI] Raster generation complete.`);
      process.exit(0);
    } else {
      this.clearScreen();
      this.showMainMenu();
    }
  }
}

//CLI Argument Parsing
let args = process.argv.slice(2);
let cli_options = {};
for (let i = 0; i < args.length; i++) {
  let a = args[i];
  if (a.startsWith("--")) {
    let parts = a.slice(2).split("=");
    cli_options[parts[0]] = (parts.length > 1) ? parts[1] : true;
  }
}

let tui = new CounterfactualsTUI();
tui.start(cli_options).catch(err => {
  console.error("Fatal error in Counterfactuals TUI:", err);
  process.exit(1);
});
