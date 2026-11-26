//Import modules
let child_process = require("child_process");
let crypto = require("crypto");
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");

//Initialise functions
{
  let phase_gate_checker = {
    /**
     * Computes a deterministic composite SHA-256 over the UUD & config files listed in alignment_contract.json5.
     * @alias phase_gate_checker.computeCodeSha256
     *
     * @param {string} arg0_root_dir
     * @param {Array<string>} arg1_rel_paths
     *
     * @returns {string}
     */
    computeCodeSha256 (arg0_root_dir, arg1_rel_paths) {
      //Convert from parameters
      let rel_paths = Array.isArray(arg1_rel_paths) ? arg1_rel_paths : [];
      let root_dir = arg0_root_dir;

      //Declare local instance variables
      let hash = crypto.createHash("sha256");

      //Function body
      for (let i = 0; i < rel_paths.length; i++) {
        let abs = path.resolve(root_dir, rel_paths[i]);
        hash.update(rel_paths[i]);
        if (fs.existsSync(abs)) {
          hash.update(fs.readFileSync(abs));
        } else {
          hash.update("MISSING");
        }
      }

      //Return statement
      return hash.digest("hex");
    },

    /**
     * Executes Phase 1..4 deterministic invariant checks against alignment_contract.json5 v2.0.
     * @alias phase_gate_checker.runPhaseGate
     *
     * @param {number} arg0_phase
     * @param {string} [arg1_root_dir]
     *
     * @returns {{ errors: Array<string>, ok: boolean, phase: number, sha256: string }}
     */
    runPhaseGate (arg0_phase, arg1_root_dir) {
      //Convert from parameters
      let phase = Number(arg0_phase);
      let root_dir = arg1_root_dir ? path.resolve(arg1_root_dir) : path.resolve(__dirname, "../..");

      //Declare local instance variables
      let contract_path = path.join(root_dir, "tests/alignment/alignment_contract.json5");
      let errors = [];

      //Guard clauses
      if (!Number.isFinite(phase) || phase < 1 || phase > 7) {
        console.error(`[check_phase_gate] Invalid phase: ${arg0_phase}`);
        return { errors: ["Invalid phase number"], ok: false, phase: phase, sha256: "" };
      }
      if (!fs.existsSync(contract_path)) {
        console.error(`[check_phase_gate] Missing contract: ${contract_path}`);
        return { errors: ["Missing alignment_contract.json5"], ok: false, phase: phase, sha256: "" };
      }

      //Function body
      let contract = JSON5.parse(fs.readFileSync(contract_path, "utf8"));
      let code_sha = this.computeCodeSha256(root_dir, contract.uud_code_hash_targets);

      if (phase === 1) {
        let global_dir = path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/config/municipal_boundaries_global");
        let manifest_path = path.join(global_dir, "manifest.json");
        let sub_path = path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/config/metropolitan_subdivisions.json5");
        let amalg_path = path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/config/historical_municipal_amalgamations.json5");
        let norm_path = path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_name_normaliser.js");
        let uud_path = path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_uud.js");
        let src_path = path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_uud_sources.js");

        if (!fs.existsSync(manifest_path)) {
          errors.push("Missing municipal_boundaries_global/manifest.json");
        } else {
          let mf = JSON.parse(fs.readFileSync(manifest_path, "utf8"));
          let shards = Array.isArray(mf.shards) ? mf.shards : [];
          if (shards.length < 2) errors.push("municipal_boundaries_global must contain >= 2 regional shards (EU + non-EU)");
          for (let i = 0; i < shards.length; i++) {
            let sp = path.join(global_dir, shards[i].file || "");
            if (!fs.existsSync(sp) || fs.statSync(sp).size < 1000)
              errors.push(`Missing or empty boundary shard: ${shards[i].file}`);
          }
        }

        if (!fs.existsSync(sub_path) || fs.statSync(sub_path).size < 1000) {
          errors.push("metropolitan_subdivisions.json5 missing or too small");
        } else {
          try {
            let sub_obj = JSON5.parse(fs.readFileSync(sub_path, "utf8"));
            let ip = sub_obj.intra_municipal_parents || {};
            if (ip.egypt && ip.egypt.cairo && Array.isArray(ip.egypt.cairo.districts)) {
              let c_dists = ip.egypt.cairo.districts.map(function (arg0_d) { return String(arg0_d).toLowerCase(); });
              if (c_dists.includes("giza") || c_dists.includes("shubra al-khaymah"))
                errors.push("metropolitan_subdivisions.json5 Cairo still contains Giza or Shubra al-Khaymah");
            }
            if (ip.morocco && ip.morocco.rabat && Array.isArray(ip.morocco.rabat.districts)) {
              let r_dists = ip.morocco.rabat.districts.map(function (arg0_d) { return String(arg0_d).toLowerCase(); });
              if (r_dists.includes("sale") || r_dists.includes("salé"))
                errors.push("metropolitan_subdivisions.json5 Rabat still contains Salé");
            }
          } catch (e) {
            errors.push(`metropolitan_subdivisions.json5 JSON5 parse error: ${e.message}`);
          }
        }

        if (!fs.existsSync(amalg_path) || fs.statSync(amalg_path).size < 500) {
          errors.push("historical_municipal_amalgamations.json5 missing or empty");
        } else {
          try {
            let am_obj = JSON5.parse(fs.readFileSync(amalg_path, "utf8"));
            if (!Array.isArray(am_obj.amalgamations) || am_obj.amalgamations.length < 10)
              errors.push("historical_municipal_amalgamations.json5 must contain >= 10 global historical amalgamation entries");
          } catch (e) {
            errors.push(`historical_municipal_amalgamations.json5 JSON5 parse error: ${e.message}`);
          }
        }

        if (fs.existsSync(norm_path)) {
          let norm_src = fs.readFileSync(norm_path, "utf8");
          if (norm_src.includes("lat < 27.0 || lat > 72.0"))
            errors.push("stadester_name_normaliser.js still contains hardcoded European lat/lng cutoff");
        }

        if (fs.existsSync(uud_path)) {
          let uud_src = fs.readFileSync(uud_path, "utf8");
          if (uud_src.includes("local_distance <= 0.015"))
            errors.push("stadester_uud.js still contains unverified proximity bypass (local_distance <= 0.015)");
          if (/if\s*\(\s*mun_gate\.reason\s*===\s*["']same_municipality_polygon["']\s*\)\s*\{\s*is_match\s*=\s*true/m.test(uud_src))
            errors.push("stadester_uud.js still contains blind same_municipality_polygon merge bypass");
          if (!uud_src.includes("canMergeMunicipalities"))
            errors.push("stadester_uud.js missing unified canMergeMunicipalities gate");
          if (!uud_src.includes("prepareAndFlattenSourceDB"))
            errors.push("stadester_uud.js missing pre-UUD prepareAndFlattenSourceDB");
        }

        if (fs.existsSync(src_path)) {
          let src_txt = fs.readFileSync(src_path, "utf8");
          if (!src_txt.includes("resolveHistoricalAmalgamation"))
            errors.push("stadester_uud_sources.js missing Class 3 resolveHistoricalAmalgamation epoch splitting");
        }

        for (let i = 0; i < contract.uud_code_hash_targets.length; i++) {
          let rel = contract.uud_code_hash_targets[i];
          if (!rel.endsWith(".js")) continue;
          let abs = path.join(root_dir, rel);
          if (!fs.existsSync(abs)) {
            errors.push(`Missing file: ${rel}`);
            continue;
          }
          let chk = child_process.spawnSync(process.execPath, ["--check", abs], { encoding: "utf8" });
          if (chk.status !== 0)
            errors.push(`Syntax error in ${rel}: ${chk.stderr}`);
        }

        let unit_test_path = path.join(root_dir, "tests/alignment/test_uud_invariants.js");
        if (!fs.existsSync(unit_test_path)) {
          errors.push("Missing tests/alignment/test_uud_invariants.js");
        } else {
          let ut = child_process.spawnSync(process.execPath, [unit_test_path], { encoding: "utf8" });
          if (ut.status !== 0)
            errors.push(`test_uud_invariants.js failed: ${ut.stderr || ut.stdout}`);
        }
      } else if (phase === 2) {
        let audit_p = path.join(root_dir, "tests/alignment/pale_swarm_audit.json");
        if (!fs.existsSync(audit_p)) {
          errors.push("Missing tests/alignment/pale_swarm_audit.json");
        } else {
          let aud = JSON.parse(fs.readFileSync(audit_p, "utf8"));
          if (!aud.approved) errors.push("pale_swarm_audit.json not approved");
          if (!(Number(aud.swarm_workers_used) >= 4)) errors.push("pale_swarm_audit.json swarm_workers_used < 4");
          if (Number(aud.synthetic_fallbacks) !== 0) errors.push("pale_swarm_audit.json synthetic_fallbacks != 0");
          if (Number(aud.blind_backprojections) !== 0) errors.push("pale_swarm_audit.json blind_backprojections != 0");
          if (!aud.pale_density_parity_verified) errors.push("pale_swarm_audit.json pale_density_parity_verified != true");
        }
      } else if (phase === 3) {
        let jade_build = path.join(root_dir, "histmap/1.data_raw/population_regional/JADE/_shared/_gis_cache/build_jade_settlements.py");
        let jade_front = path.join(root_dir, "histmap/1.data_raw/population_regional/JADE/_shared/_gis_cache/jade_frontier_gazetteer.py");
        let mn1_p = path.join(root_dir, "histmap/1.data_raw/population_regional/JADE/1.mongolia_pre_1912/1.steppe_prehistory_and_nomadic_empires/steppe_prehistory_and_nomadic_empires_settlements.json");
        let mn2_p = path.join(root_dir, "histmap/1.data_raw/population_regional/JADE/1.mongolia_pre_1912/2.mongol_empire_and_qing_mongolia/mongol_empire_and_qing_mongolia_settlements.json");

        if (fs.existsSync(jade_build)) {
          let jb = fs.readFileSync(jade_build, "utf8");
          if (/mn1_cands[\s\S]{0,1800}det_pareto_pop/.test(jb) || /mn2_cands[\s\S]{0,2200}det_pareto_pop/.test(jb))
            errors.push("build_jade_settlements.py still uses det_pareto_pop in Mongolia sections");
        }
        if (fs.existsSync(jade_front)) {
          let jf = fs.readFileSync(jade_front, "utf8");
          if (/base\s*=\s*2200/.test(jf))
            errors.push("jade_frontier_gazetteer.py still contains flat base = 2200 stamping");
        }
        let banned_mn = ["bilge qagan", "biluut-tolgoi", "khar chuluu", "erchu khot", "noyon uul", "gol mod", "burkhan tolgoi", "ulaanzuukh", "olon-dov", "tsatsyn ereg", "uushigiin ovor", "kherlen-bars"];
        for (let fp of [mn1_p, mn2_p]) {
          if (!fs.existsSync(fp)) { errors.push(`Missing ${fp}`); continue; }
          let obj = JSON.parse(fs.readFileSync(fp, "utf8"));
          let keys = Object.keys(obj);
          for (let i = 0; i < keys.length; i++) {
            let nm = String(obj[keys[i]].name || "").toLowerCase();
            if (banned_mn.includes(nm))
              errors.push(`Banned funerary/duplicate site '${obj[keys[i]].name}' still in ${path.basename(fp)}`);
          }
        }
      } else if (phase === 4) {
        let png_dir = path.join(root_dir, "tests/uud_audit/pngs");
        let yrs = contract.required_benchmark_years || [];
        let bboxes = ["europe", "greece_turkey"];
        for (let b = 0; b < bboxes.length; b++) {
          for (let y = 0; y < yrs.length; y++) {
            let fp = path.join(png_dir, `${bboxes[b]}_${yrs[y]}.png`);
            if (!fs.existsSync(fp) || fs.statSync(fp).size < 15000)
              errors.push(`Missing or tiny benchmark PNG: ${bboxes[b]}_${yrs[y]}.png`);
          }
        }
        let signoff_p = path.join(root_dir, "tests/uud_audit/auditor_signoff.json");
        if (!fs.existsSync(signoff_p)) {
          errors.push("Missing tests/uud_audit/auditor_signoff.json");
        } else {
          let so = JSON.parse(fs.readFileSync(signoff_p, "utf8"));
          if (!so.approved || Number(so.defects_found) !== 0)
            errors.push("uud_visual_auditor signoff not approved with 0 defects");
          if (so.code_sha256 !== code_sha)
            errors.push(`Stale auditor_signoff.json SHA-256 (${so.code_sha256} !== ${code_sha})`);
        }
      } else if (phase === 5) {
        let signoff_p = path.join(root_dir, "tests/uud_audit/auditor_signoff.json");
        if (!fs.existsSync(signoff_p)) {
          errors.push("INV-07: Missing tests/uud_audit/auditor_signoff.json");
        } else {
          let so = JSON.parse(fs.readFileSync(signoff_p, "utf8"));
          if (!so.approved || Number(so.defects_found) !== 0)
            errors.push("INV-07: uud_visual_auditor signoff not approved with 0 defects");
          if (so.code_sha256 !== code_sha)
            errors.push(`INV-07: Stale auditor_signoff.json SHA-256 (${so.code_sha256} !== ${code_sha})`);
        }
        if (fs.existsSync(path.join(root_dir, "histmap/5.data_visualisationstadester")))
          errors.push("Accidental misnamed directory exists: histmap/5.data_visualisationstadester");
        let dv_base = "F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0";
        let shard_dirs = [
          path.join(root_dir, "histmap/3.data_transform/population_Stadester.transform/stadester"),
          path.join(root_dir, "histmap/5.data_visualisation/stadester/stadester_2.0"),
          dv_base
        ];
        let ref_manifest = null;
        for (let s = 0; s < shard_dirs.length; s++) {
          let sdir = shard_dirs[s];
          if (!fs.existsSync(sdir)) {
            errors.push(`Missing Stadester shard directory: ${sdir}`);
            continue;
          }
          let man_p = path.join(sdir, "stadester_manifest.json");
          if (!fs.existsSync(man_p)) {
            errors.push(`Missing stadester_manifest.json in ${sdir}`);
          } else {
            let man = JSON.parse(fs.readFileSync(man_p, "utf8"));
            let tot = Number(man.total_cities || man.total_entries || 0);
            if (tot < 600000)
              errors.push(`Manifest total_cities < 600000 (${tot}) in ${sdir}`);
            if (!ref_manifest) {
              ref_manifest = { dir: sdir, man: man };
            } else {
              let ref_tot = Number(ref_manifest.man.total_cities || ref_manifest.man.total_entries || 0);
              if (tot !== ref_tot)
                errors.push(`Manifest total_cities mismatch (${tot} in ${sdir} !== ${ref_tot} in ${ref_manifest.dir})`);
              let r1 = Array.isArray(ref_manifest.man.regions) ? ref_manifest.man.regions : [];
              let r2 = Array.isArray(man.regions) ? man.regions : [];
              if (r1.length !== r2.length) {
                errors.push(`Manifest region count mismatch in ${sdir}`);
              } else {
                for (let ri = 0; ri < r1.length; ri++) {
                  if (r1[ri].key !== r2[ri].key || Number(r1[ri].count) !== Number(r2[ri].count) || JSON.stringify(r1[ri].files) !== JSON.stringify(r2[ri].files))
                    errors.push(`Manifest mismatch for ${r1[ri].key} between ${ref_manifest.dir} and ${sdir}`);
                }
              }
            }
          }
          let files = fs.readdirSync(sdir).filter(function (arg0_f) { return arg0_f.endsWith(".json"); });
          if (files.length === 0)
            errors.push(`No .json shard files in ${sdir}`);
          for (let fi = 0; fi < files.length; fi++) {
            let st = fs.statSync(path.join(sdir, files[fi]));
            if (st.size > 200*1024*1024)
              errors.push(`Shard exceeds 200 MB limit (${Math.round(st.size/(1024*1024))} MB): ${path.join(sdir, files[fi])}`);
          }
        }
        let cm_dir = path.join(dv_base, "city_metadata");
        let req_cm = [
          "city_metadata_manifest.json", "00_capitals.json", "01_centaur.json", "02_polaris.json",
          "03_preta.json", "04_jade.json", "05_indus.json", "06_castle.json", "07_mandala.json",
          "08_saray.json", "09_handbook.json", "10_magnetic.json", "11_quipu.json", "12_jaguar.json",
          "13_austral.json", "14_nicethi.json"
        ];
        for (let i = 0; i < req_cm.length; i++) {
          let cp = path.join(cm_dir, req_cm[i]);
          if (!fs.existsSync(cp) || fs.statSync(cp).size < 10)
            errors.push(`Missing or empty city_metadata shard: ${cp}`);
        }
      } else if (phase === 6) {
        let projects = contract.canonical_macro_regions || [
          "CENTAUR", "POLARIS", "PRETA", "JADE", "INDUS", "CASTLE", "MANDALA",
          "SARAY", "HANDBOOK", "MAGNETIC", "QUIPU", "JAGUAR", "AUSTRAL", "NICETHI"
        ];
        let audit_script = path.join(root_dir, ".agents/skills/population-regional-study/scripts/audit_city_metadata.js");
        for (let i = 0; i < projects.length; i++) {
          let pk = String(projects[i]);
          let slug = pk.toLowerCase();
          let bdir = path.join(root_dir, "tests/toponymy_batches", slug);
          let p1_so = path.join(bdir, "pass1/auditor_signoff.json");
          let p2_rp = path.join(bdir, "pass2/pass2_whg_geohack_report.json");
          if (!fs.existsSync(p1_so)) {
            errors.push(`Missing Pass-1 auditor_signoff.json for ${pk}`);
          } else {
            let so = JSON.parse(fs.readFileSync(p1_so, "utf8"));
            if (!so.approved || Number(so.errors_remaining) !== 0)
              errors.push(`Pass-1 auditor_signoff.json not approved for ${pk}`);
          }
          if (!fs.existsSync(p2_rp)) {
            errors.push(`Missing Pass-2 report for ${pk}`);
          } else {
            let rp = JSON.parse(fs.readFileSync(p2_rp, "utf8"));
            if (Number(rp.llm_agents_used) !== 0)
              errors.push(`Pass-2 used LLM agents for ${pk} (forbidden)`);
          }
          let chk = child_process.spawnSync(process.execPath, [audit_script, `--project=${pk}`], { encoding: "utf8" });
          if (chk.status !== 0)
            errors.push(`audit_city_metadata.js failed for ${pk}: ${(chk.stderr || chk.stdout || "").slice(0, 200)}`);
        }
      } else if (phase === 7) {
        let rb_script = path.join(root_dir, ".agents/skills/population-regional-study/scripts/run_bounded.js");
        let orph = child_process.spawnSync(process.execPath, [rb_script, "--audit-orphans"], { encoding: "utf8" });
        if (orph.status !== 0)
          errors.push(`run_bounded.js --audit-orphans failed: ${orph.stderr || orph.stdout}`);
        let dv_dist = "F:/Active Projects/Project 1436 - Dataview/dist";
        if (!fs.existsSync(dv_dist) || fs.readdirSync(dv_dist).length === 0)
          errors.push("Missing Dataview dist/ build output");
        let intellte_sync_dir = "E:/Active Projects/Project 1746 - Intellte";
        if (!fs.existsSync(intellte_sync_dir))
          errors.push("Missing Intellte root directory");
      }

      //Return statement
      return { errors: errors, ok: errors.length === 0, phase: phase, sha256: code_sha };
    }
  };

  if (require.main === module) {
    let phase_arg = 0;
    for (let i = 2; i < process.argv.length; i++) {
      if (process.argv[i].startsWith("--phase="))
        phase_arg = Number(process.argv[i].slice(8));
    }
    let res = phase_gate_checker.runPhaseGate(phase_arg);
    console.log(JSON.stringify(res, null, 2));
    process.exit(res.ok ? 0 : 1);
  } else {
    module.exports = { phase_gate_checker: phase_gate_checker };
  }
}
