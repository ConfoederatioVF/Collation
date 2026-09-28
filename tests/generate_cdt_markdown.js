const fs = require('fs');
const path = require('path');

let d1 = JSON.parse(fs.readFileSync(path.join(__dirname, 'validation_age_sex_cdt.json'), 'utf8'));
let d2 = JSON.parse(fs.readFileSync(path.join(__dirname, 'validation_births_deaths_cdt.json'), 'utf8'));

let md = [];

md.push(`# Contemporary Demographic Transition (CDT) Validation Audit`);
md.push(`\n**Evaluation Dataset**: Project 1509 SVEA / Histmap (Stadestér Demographics, Raw MNL, PAVA/Whittaker smoothing)`);
md.push(`**Priors**: Human Mortality Database (HMD), UNWPP, Niva et al. (Kummu)\n`);

md.push(`---\n`);

md.push(`## 1. Age/Sex Validation (MNL vs Clamped to Stadestér)\n`);
md.push(`Evaluates the goodness-of-fit ($R^2$) of the raw Multinomial Logit (MNL) baseline probabilities against the final Stadestér age/sex output (post-PAVA, Whittaker graduation, and clamping) using HMD and UNWPP empirical benchmarks.\n`);

md.push(`### Overall Performance`);
md.push(`- **Raw MNL Geomean $R^2$**: $${d1.overall_cdt.raw_mnl_geomean_r2.toFixed(4)}$`);
md.push(`- **Clamped Geomean $R^2$**: $${d1.overall_cdt.clamped_geomean_r2.toFixed(4)}$`);
md.push(`- **Improvement ($\\Delta R^2$)**: $${(d1.overall_cdt.delta_geomean_r2 > 0 ? '+' : '')}${d1.overall_cdt.delta_geomean_r2.toFixed(4)}$\n`);

md.push(`### Table 1: Age/Sex $R^2$ Validation by Epoch`);
md.push(`| Year | Empirical Source | Sample ($N$ Countries) | Raw MNL $R^2$ | Clamped $R^2$ (Stadestér) | $\\Delta R^2$ (Improvement) |`);
md.push(`| :---: | :--- | :---: | :---: | :---: | :---: |`);

let age_sex_epochs = Object.values(d1.summary_by_epoch).sort((a, b) => a.year - b.year);
for (let ep of age_sex_epochs) {
  let delta = ep.delta_geomean;
  let delta_str = (delta >= 0 ? "+" : "") + delta.toFixed(4);
  md.push(`| **${ep.year}** | ${ep.domain} | $${ep.num_countries}$ | $${ep.raw_mnl.geomean_r2.toFixed(4)}$ | **$${ep.clamped.geomean_r2.toFixed(4)}$** | **$${delta_str}$** |`);
}

md.push(`\n---\n`);

md.push(`## 2. Births & Deaths Validation (Proxy Residuals vs Empirical)\n`);
md.push(`Evaluates proxy birth and death counts against UNWPP and Niva et al. (Kummu) empirical data. The error percentage reflects the discrepancy between inferred proxy natural events and actual historical statistics.\n`);

md.push(`### Table 2: Global Births and Deaths Accuracy by Epoch`);
md.push(`| Year | Source | Sample ($N$) | Proxy Births | Empirical Births | Births Error | Proxy Deaths | Empirical Deaths | Deaths Error |`);
md.push(`| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |`);

let formatNum = function(num) {
  return Math.round(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

let bd_epochs = Object.values(d2.summary_by_epoch).sort((a, b) => a.year - b.year);
for (let ep of bd_epochs) {
  let b_err = ep.birth_error_pct;
  let b_err_str = (b_err >= 0 ? "+" : "") + b_err.toFixed(2) + "\\%";
  let d_err = ep.death_error_pct;
  let d_err_str = (d_err >= 0 ? "+" : "") + d_err.toFixed(2) + "\\%";
  
  md.push(`| **${ep.year}** | ${ep.source} | $${ep.num_countries}$ | $${formatNum(ep.proxy_births)}$ | $${formatNum(ep.empirical_births)}$ | **$${b_err_str}$** | $${formatNum(ep.proxy_deaths)}$ | $${formatNum(ep.empirical_deaths)}$ | **$${d_err_str}$** |`);
}

md.push(`\n---\n`);
md.push(`*Generated autonomously by Project 1509 SVEA Contemporary Demographic Transition Validation Engine.*`);

fs.writeFileSync(path.join(__dirname, 'cdt.md'), md.join('\n'));
console.log('Successfully generated tests/cdt.md');
