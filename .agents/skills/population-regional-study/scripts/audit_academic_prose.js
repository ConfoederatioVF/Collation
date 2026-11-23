//Import modules
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let academic_prose_auditor = {
    BANNED_PHRASES: [
      /\bdelve(?:s|d|ing)?\b/i,
      /\btapestry\b/i,
      /\bserve(?:s|d)? as a testament\b/i,
      /\bpivotal role\b/i,
      /\bcomplex interplay\b/i,
      /\brobust framework\b/i,
      /\bholistic approach\b/i,
      /\bbeacon of\b/i,
      /\bunparalleled\b/i,
      /\bburgeoning\b/i,
      /\bspearhead(?:s|ed|ing)?\b/i,
      /\bit is worth noting that\b/i,
      /\bpaints a vivid picture\b/i,
      /\bsheds light on\b/i,
      /\brichest tapestry\b/i,
      /\bnot only\b.{1,80}\bbut also\b/i
    ],
    BLOATED_TITLE_PAT: /^Demographic\s+Trajectory\s+of\b|^Studies\s+on\s+Population\s+across\b|Holocene\s+Archaeological\s+Substrata,\s*Non-Stationary\s+Mat[eé]rn\s+Kriging/i,
    DECORATOR_COLOUR_PAT: /\b(?:warm gold|emerald teal|muted slate|crisp azure|vibrant coral)\b/i,
    EUPHEMISM_PAT: /\b(?:Contemporary Warfare|Regional Unrest|Growth Hub|Demographic Powerhouse)\b/i,
    EXPLICIT_MONO_PAT: /\\texttt\s*\{|\\verb(?![A-Za-z])|<code>/gi,
    INLINE_BACKTICK_PAT: /`([^`\n]+)`/g,
    INTERNAL_CIRC_PAT: /\b(?:histmap\/|population_Substrata|population_Velkscala)\b/,
    KNITR_INLINE_R_PAT: /`r\s+[^`\n]+`/g,
    MANUAL_PAGEBREAK_PAT: /\\(?:newpage|clearpage|pagebreak)\b/,
    MONTH_YEAR_AD_PAT: /\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2}\s*AD\b/g,
    SAFE_HTML_TAG_PAT: /<\/?(?:br|sup|sub|em|strong|a|div|span|p|img|code|kbd)(?:\s[^>]*)?>/gi,
    SCHEMA_LEAK_PAT: /\b(?:other_names|positive integer population series|JSON archive|Stadest[eé]r format)\b/,
    SNAKE_LEAK_PAT: /\b(?:sites_[A-Za-z0-9_]+|\d+\.[a-z]+_[a-z_]+)\b/,
    THE_PROJ_PAT: /\b[Tt]he\s+[A-Z]{4,12}\s+(?:synthesis|framework|model|paradigm|architecture)\b/,
    UNPROMOTED_K_PAT: /(?<![A-Za-z0-9.,])\d+\.\d{3}\s*k\b/,
    US_ENGLISH_PATTERNS: [
      /\banalyz(?:e|ed|es|ing)\b/i,
      /\bsynthesiz(?:e|ed|es|ing)\b/i,
      /\bstandardiz(?:e|ed|es|ing)\b/i,
      /\bnormaliz(?:e|ed|es|ing)\b/i,
      /\bsynchroniz(?:e|ed|es|ing)\b/i,
      /\bneighbor(?:s|ing|hood)?\b/i,
      /\bbehavior(?:s|al)?\b/i,
      /\bfavor(?:s|ed|able)?\b/i
    ],
    VUE_ANGLE_PAT: /<[A-Za-z][^>\n]*>/g,
    WARN_PHRASES: [
      /\bshowcase(?:s|d|ing)?\b/i,
      /\bunderscore(?:s|d|ing)?\b/i,
      /\bparamount\b/i,
      /\bmultifaceted\b/i,
      /\bseamless(?:ly)?\b/i,
      /\bin conclusion\b/i,
      /\bin summary\b/i,
      /\bmeticulous(?:ly)?\b/i,
      /\bvibrant\b/i
    ],
    WORD_N_EQ_PAT: /\b(?:ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[-\sA-Za-z]{0,24}\(\s*n\s*=\s*\d+\s*\)/i,

    /**
     * Enforces `/humanise` rules across YAML frontmatter, path/title lengths, headings, captions and prose.
     * @alias academic_prose_auditor.auditHumaniseStructure
     *
     * @param {string} arg0_rmd_path
     * @param {boolean} [arg1_legacy_baseline=false]
     * @param {Object} [arg2_limits]
     * @param {string} [arg3_svea_root]
     *
     * @returns {{ errors: Array<string>, warnings: Array<string> }}
     */
    auditHumaniseStructure (arg0_rmd_path, arg1_legacy_baseline, arg2_limits, arg3_svea_root) {
      //Convert from parameters
      let legacy_baseline = Boolean(arg1_legacy_baseline);
      let limits = (arg2_limits) ? arg2_limits : {};
      let rmd_path = arg0_rmd_path;
      let svea_root = arg3_svea_root || viscount_audit_utils.findSveaRoot(rmd_path);

      //Declare local instance variables
      let errors = [];
      let max_filename_chars = Number(limits.max_filename_chars || 72);
      let max_repo_rel_chars = Number(limits.max_repo_rel_path_chars || 180);
      let max_stem_chars = Number(limits.max_chapter_stem_chars || 42);
      let max_subtitle_chars = Number(limits.max_subtitle_chars || 90);
      let max_title_chars = Number(limits.max_chapter_title_chars || 72);
      let max_title_words = Number(limits.max_chapter_title_words || 10);
      let root_expected_title = String(limits.root_title || "Studies on Population");
      let warnings = [];

      //Guard clauses
      let raw_text = "";
      try {
        raw_text = fs.readFileSync(rmd_path, "utf8");
      } catch (e) {
        return { errors: [`Could not read Rmd file for humanise audit: ${e.message}`], warnings: warnings };
      }

      //Function body
      let abs_rmd = path.resolve(rmd_path);
      let basename = path.basename(abs_rmd);
      let is_root_file = basename.toLowerCase() === "studies_on_population.rmd";
      let is_settlements_file = basename.toLowerCase().endsWith("_settlements.rmd");
      let lines = raw_text.split(/\r?\n/);

      // Enforce GitHub / Windows MAX_PATH-safe filename, chapter stem and repo-relative path ceilings
      if (basename.length > max_filename_chars)
        errors.push(`[PATH_LIMIT] Filename \`${basename}\` length is ${basename.length} chars (> ${max_filename_chars} GitHub/Windows safe max).`);

      let rmd_stem_low = basename.replace(/\.rmd$/i, "").toLowerCase();
      let stem_short_low = rmd_stem_low.replace(/_(?:literature_review|areal_masks_and_bins|settlements)$/, "");
      if (!is_root_file && stem_short_low.length > max_stem_chars)
        errors.push(`[PATH_LIMIT] Chapter stem \`${stem_short_low}\` length is ${stem_short_low.length} chars (> ${max_stem_chars} max); shorten folder and file stem.`);

      if (svea_root) {
        let rel_repo = path.relative(svea_root, abs_rmd).replace(/\\/g, "/");
        if (!rel_repo.startsWith("..") && rel_repo.length > max_repo_rel_chars)
          errors.push(`[PATH_LIMIT] Repo-relative path \`${rel_repo}\` length is ${rel_repo.length} chars (> ${max_repo_rel_chars} GitHub max).`);
      }

      let yaml_end_idx = 0;
      if (lines.length > 0 && lines[0].trim() === "---") {
        for (let idx = 1; idx < lines.length; idx++) {
          if (lines[idx].trim() === "---") {
            yaml_end_idx = idx;
            break;
          }
        }
      }

      let itin_spec = this.loadItineraryTitleSpec(abs_rmd);
      let chap_folder_low = path.basename(path.dirname(abs_rmd)).toLowerCase();

      for (let idx = 1; idx < yaml_end_idx; idx++) {
        let line_no = idx + 1;
        let stripped_yaml = lines[idx].trim();
        let m = stripped_yaml.match(/^(hero_caption|subtitle)\s*:\s*(.+)$/);
        if (m) {
          let field_name = m[1];
          let val = m[2].trim().replace(/^["']|["']$/g, "");
          this.checkNoMonospace(line_no, val, errors, warnings, legacy_baseline);
          let clean_val = this.stripNonProseSpans(val);
          if (field_name === "subtitle") {
            if (clean_val.length > max_subtitle_chars) {
              let msg = `Line ${line_no}: YAML \`subtitle\` length is ${clean_val.length} chars (> ${max_subtitle_chars} max; keep subtitles concise).`;
              if (legacy_baseline && clean_val.length <= 115) warnings.push(msg);
              else errors.push(msg);
            }
            if (this.BLOATED_TITLE_PAT.test(clean_val)) {
              let msg = `Line ${line_no}: YAML \`subtitle\` uses bloated boilerplate wording (${JSON.stringify(clean_val)}).`;
              if (legacy_baseline) warnings.push(msg);
              else errors.push(msg);
            }
          }
          let badge_kws = ["verified", "validated", "empirical", "complete"];
          for (let b = 0; b < badge_kws.length; b++) {
            if (new RegExp(`\\b${badge_kws[b]}\\b`, "i").test(clean_val))
              errors.push(`Line ${line_no}: YAML \`${field_name}\` contains banned badge/hyperbole word \`${badge_kws[b]}\`.`);
          }
          this.checkFormattingTokens(line_no, clean_val, errors, warnings, legacy_baseline);
          continue;
        }

        let title_m = stripped_yaml.match(/^title\s*:\s*(.+)$/);
        if (title_m) {
          let val = title_m[1].trim().replace(/^["']|["']$/g, "");
          this.checkNoMonospace(line_no, val, errors, warnings, legacy_baseline);
          let clean_title = this.stripNonProseSpans(val).trim();
          if (is_root_file) {
            let expected_root = (itin_spec && itin_spec.root_title) ? itin_spec.root_title : root_expected_title;
            if (this.normaliseTitleKey(clean_title) !== this.normaliseTitleKey(expected_root)) {
              let msg = `Line ${line_no}: Root YAML \`title\` is ${JSON.stringify(clean_title)}; must match canonical itinerary title ${JSON.stringify(expected_root)}.`;
              if (legacy_baseline) warnings.push(msg);
              else errors.push(msg);
            }
          } else {
            let word_cnt = clean_title.split(/\s+/).filter(Boolean).length;
            if (clean_title.length > max_title_chars || word_cnt > max_title_words) {
              let msg = `Line ${line_no}: Sub-chapter YAML \`title\` is overly lengthy (${clean_title.length} chars, ${word_cnt} words; max ${max_title_chars} chars / ${max_title_words} words).`;
              if (legacy_baseline) warnings.push(msg);
              else errors.push(msg);
            }
            if (this.BLOATED_TITLE_PAT.test(clean_title)) {
              let msg = `Line ${line_no}: Sub-chapter YAML \`title\` uses bloated formulaic wrapper (${JSON.stringify(clean_title)}); use concise itinerary title.`;
              if (legacy_baseline) warnings.push(msg);
              else errors.push(msg);
            }
            if (itin_spec && itin_spec.chapters && typeof itin_spec.chapters === "object") {
              let cmap = itin_spec.chapters;
              let expected_it = cmap[rmd_stem_low] || cmap[stem_short_low] || cmap[chap_folder_low];
              if (expected_it && this.normaliseTitleKey(clean_title) !== this.normaliseTitleKey(expected_it))
                errors.push(`Line ${line_no}: YAML \`title\` ${JSON.stringify(clean_title)} deviates from itinerary title ${JSON.stringify(expected_it)} (from ${itin_spec.source}).`);
            }
          }
        }
      }

      let in_code = false;
      let in_display_math = false;
      let current_h1 = null;
      let body_start = yaml_end_idx + (yaml_end_idx > 0 ? 1 : 0);

      for (let idx = body_start; idx < lines.length; idx++) {
        let line_no = idx + 1;
        let raw_line = lines[idx];
        let stripped = raw_line.trim();

        if (stripped.startsWith("```")) {
          in_code = !in_code;
          continue;
        }

        if (in_code) {
          let cap_re = /(?:viscount_table|viscount_figure|render_table_template)\s*\([^)]*(?:caption\s*=\s*|,\s*)(["'])((?:\\.|(?!\1).)*)\1/g;
          let cap_m = null;
          for (let iter = 0; (cap_m = cap_re.exec(raw_line)) !== null && iter < 20; iter++) {
            let cap_text = cap_m[2];
            this.checkNoMonospace(line_no, cap_text, errors, warnings, legacy_baseline);
            let clean_cap = this.stripNonProseSpans(cap_text);
            let badge_kws = ["verified", "validated", "empirical", "complete"];
            for (let b = 0; b < badge_kws.length; b++) {
              let kw = badge_kws[b];
              if (new RegExp(`\\b${kw}\\b`, "i").test(clean_cap)) {
                if (kw === "complete" && is_settlements_file && /\bcomplete\s+settlement\b/i.test(clean_cap))
                  warnings.push(`Line ${line_no}: Caption contains \`Complete Settlement\` wording; consider concise noun phrasing.`);
                else
                  errors.push(`Line ${line_no}: Figure/table caption contains banned badge/hyperbole word \`${kw}\`.`);
              }
            }
            this.checkFormattingTokens(line_no, clean_cap, errors, warnings, legacy_baseline);
          }
          continue;
        }

        if (stripped.startsWith("$$") || stripped.startsWith("\\[")) {
          let dd_cnt = (stripped.match(/\$\$/g) || []).length;
          if (stripped === "$$" || stripped === "\\[" || stripped === "\\]" || dd_cnt === 1 ||
              (stripped.includes("\\[") && !stripped.includes("\\]")) ||
              (stripped.includes("\\]") && !stripped.includes("\\["))) {
            in_display_math = !in_display_math;
          }
          continue;
        }
        if (in_display_math) continue;

        if (stripped.startsWith("#")) {
          let level_m = stripped.match(/^(#+)\s*(.*)$/);
          let heading_level = level_m ? level_m[1].length : 1;
          let heading_text = level_m ? level_m[2] : stripped.replace(/^#+/, "").trim();
          this.checkNoMonospace(line_no, heading_text, errors, warnings, legacy_baseline);
          let clean_heading = this.stripNonProseSpans(heading_text);
          if (heading_level === 1) {
            current_h1 = clean_heading.trim().toLowerCase();
            if (current_h1 === "references")
              errors.push(`Line ${line_no}: Use \`# Sources\` rather than \`# References\`.`);
          } else if (heading_level >= 2 && current_h1 === "abstract") {
            errors.push(`Line ${line_no}: Sub-heading \`${heading_text}\` inside \`# Abstract\` is forbidden (keep \`# Abstract\` undivided so Page 1 never strands an orphaned heading).`);
          }
          let badge_kws = ["verified", "validated", "empirical", "complete"];
          for (let b = 0; b < badge_kws.length; b++) {
            let kw = badge_kws[b];
            if (new RegExp(`\\b${kw}\\b`, "i").test(clean_heading)) {
              if (kw === "complete" && is_settlements_file && /\bcomplete\s+settlement\b/i.test(clean_heading))
                warnings.push(`Line ${line_no}: Heading contains \`Complete Settlement\` in \`_settlements.Rmd\`; avoid elsewhere.`);
              else
                errors.push(`Line ${line_no}: Markdown heading contains banned hyperbole/badge word \`${kw}\` (${JSON.stringify(heading_text)}).`);
            }
          }
          this.checkFormattingTokens(line_no, clean_heading, errors, warnings, legacy_baseline);
          continue;
        }

        if (!stripped || stripped.startsWith("<!--")) continue;
        if (this.MANUAL_PAGEBREAK_PAT.test(raw_line) && current_h1 !== "appendix" && current_h1 !== "sources" && current_h1 !== "footnotes")
          warnings.push(`Line ${line_no}: Manual LaTeX page break (\`\\newpage\`/\`\\clearpage\`) in prose risks excessive PDF page deadspace.`);

        this.checkNoMonospace(line_no, raw_line, errors, warnings, legacy_baseline);
        let raw_no_code = raw_line.replace(/`[^`]+`|<!--.*?-->|<https?:\/\/[^>]+>/g, " ").replace(this.SAFE_HTML_TAG_PAT, " ");
        let vm = null;
        this.VUE_ANGLE_PAT.lastIndex = 0;
        for (let iter = 0; (vm = this.VUE_ANGLE_PAT.exec(raw_no_code)) !== null && iter < 20; iter++)
          errors.push(`Line ${line_no}: Unescaped angle-bracket token ${JSON.stringify(vm[0])} breaks VitePress Vue builds.`);

        let clean_prose = this.stripNonProseSpans(raw_line);
        this.checkFormattingTokens(line_no, clean_prose, errors, warnings, legacy_baseline);
      }

      //Return statement
      return { errors: errors, warnings: warnings };
    },

    /**
     * Audits an `.Rmd` file or recursively all `.Rmd` files in a directory.
     * @alias academic_prose_auditor.auditRmdFile
     *
     * @param {string} arg0_rmd_path
     * @param {Object} [arg1_options]
     *
     * @returns {{ errors: Array<string>, files_checked: number, success: boolean, warnings: Array<string> }}
     */
    auditRmdFile (arg0_rmd_path, arg1_options) {
      //Convert from parameters
      let options = (arg1_options) ? arg1_options : {};
      let legacy_baseline = Boolean(options.legacy_baseline);
      let rmd_path = path.resolve(arg0_rmd_path);
      let strict_prose = (options.strict_prose !== undefined) ? Boolean(options.strict_prose) : true;

      //Declare local instance variables
      let errors = [];
      let svea_root = viscount_audit_utils.findSveaRoot(rmd_path);
      let profiles = viscount_audit_utils.loadSkillProfiles(svea_root);
      let limits = (profiles && profiles.path_and_title_limits) ? profiles.path_and_title_limits : {};
      let warnings = [];

      //Guard clauses
      if (!fs.existsSync(rmd_path))
        return { errors: [`Target path not found: ${rmd_path}`], files_checked: 0, success: false, warnings: [] };

      //Function body
      if (fs.statSync(rmd_path).isDirectory()) {
        let skip = new Set(["_shared", "archive", "diagnostics_visual", ".git", ".Rproj.user", "node_modules", "papers", "figures"]);
        let rmd_paths = viscount_audit_utils.walkFiles(rmd_path, function (arg0_full, arg1_name) {
          return arg1_name.toLowerCase().endsWith(".rmd");
        }, skip);
        if (rmd_paths.length === 0)
          return { errors: [`No .Rmd files found under directory ${rmd_path}`], files_checked: 0, success: false, warnings: [] };

        for (let i = 0; i < rmd_paths.length; i++) {
          let rel = path.relative(rmd_path, rmd_paths[i]).replace(/\\/g, "/");
          let sub = this.auditRmdFile(rmd_paths[i], options);
          for (let x = 0; x < sub.errors.length; x++) errors.push(`[${rel}] ${sub.errors[x]}`);
          for (let x = 0; x < sub.warnings.length; x++) warnings.push(`[${rel}] ${sub.warnings[x]}`);
        }
        return { errors: errors, files_checked: rmd_paths.length, success: errors.length === 0, warnings: warnings };
      }

      let raw = fs.readFileSync(rmd_path, "utf8");
      let is_root_synthesis = path.basename(rmd_path).toLowerCase() === "studies_on_population.rmd";

      if (/render_table_template\s*<-\s*function/.test(raw))
        errors.push("Inline `render_table_template <- function` override detected; use shared `viscount_rmd_helpers.R` and Intellte framework instead.");

      let prose_lines = this.stripNonProse(raw);
      for (let i = 0; i < prose_lines.length; i++) {
        let line_no = prose_lines[i].line_no;
        let text = prose_lines[i].text;
        let trimmed = text.trim();
        if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("<") || trimmed.startsWith("|")) continue;

        if (!is_root_synthesis) {
          let cm = text.match(this.INTERNAL_CIRC_PAT);
          if (cm) {
            let msg = `Line ${line_no}: Sub-chapter circular reference to internal SVEA dataset/path ${JSON.stringify(cm[0])}.`;
            if (legacy_baseline) warnings.push(msg);
            else errors.push(msg);
          }
        }

        let sp_re = /(?<![A-Za-z0-9.,])\b\d{1,3}(?: \d{3})+\b/g;
        let sp_m = null;
        for (let iter = 0; (sp_m = sp_re.exec(text)) !== null && iter < 20; iter++)
          warnings.push(`Line ${line_no}: Space-delimited thousands ${JSON.stringify(sp_m[0])}; use DE full-stop separator.`);

        for (let x = 0; x < this.BANNED_PHRASES.length; x++) {
          let m = text.match(this.BANNED_PHRASES[x]);
          if (m) {
            let msg = `Line ${line_no}: AI cliché / anti-human pattern ${JSON.stringify(m[0])}`;
            if (strict_prose) errors.push(msg);
            else warnings.push(msg);
          }
        }

        for (let x = 0; x < this.WARN_PHRASES.length; x++) {
          let m = text.match(this.WARN_PHRASES[x]);
          if (m) warnings.push(`Line ${line_no}: Stylistic warning phrase ${JSON.stringify(m[0])}`);
        }

        for (let x = 0; x < this.US_ENGLISH_PATTERNS.length; x++) {
          let m = text.match(this.US_ENGLISH_PATTERNS[x]);
          if (m) errors.push(`Line ${line_no}: Non-British (US) spelling ${JSON.stringify(m[0])}`);
        }

        let dot_re = /(?<![a-zA-Z0-9.])(\d+\.\d+)(?=\s*%|(?:\s*(?:k|M|B|T)\b))/g;
        let dm = null;
        for (let iter = 0; (dm = dot_re.exec(text)) !== null && iter < 20; iter++)
          errors.push(`Line ${line_no}: English decimal dot ${JSON.stringify(dm[1])}; use European comma (e.g. ${JSON.stringify(dm[1].replace(".", ","))}).`);

        let mag_re = /\b\d+(?:,\d+)?\s+(?:thousand|million|billion|trillion)\b/gi;
        let mm = null;
        for (let iter = 0; (mm = mag_re.exec(text)) !== null && iter < 20; iter++)
          warnings.push(`Line ${line_no}: Spelled-out magnitude ${JSON.stringify(mm[0])}; prefer semantic suffix (k/M/B/T).`);

        let ox_re = /\b[A-Za-z0-9-]+,\s+[A-Za-z0-9-]+,\s+and\s+[A-Za-z0-9-]+\b/g;
        let om = null;
        for (let iter = 0; (om = ox_re.exec(text)) !== null && iter < 20; iter++)
          warnings.push(`Line ${line_no}: Possible Oxford serial comma ${JSON.stringify(om[0])}.`);
      }

      let hres = this.auditHumaniseStructure(rmd_path, legacy_baseline, limits, svea_root);
      for (let i = 0; i < hres.errors.length; i++) errors.push(hres.errors[i]);
      for (let i = 0; i < hres.warnings.length; i++) warnings.push(hres.warnings[i]);

      //Return statement
      return { errors: errors, files_checked: 1, success: errors.length === 0, warnings: warnings };
    },

    /**
     * Checks malformed BC/AD dates, ASCII km2/m2, prose arrows, spaced slashes and AI schema leaks.
     * @alias academic_prose_auditor.checkFormattingTokens
     *
     * @param {number} arg0_line_no
     * @param {string} arg1_clean_text
     * @param {Array<string>} arg2_errors
     * @param {Array<string>} arg3_warnings
     * @param {boolean} [arg4_legacy_baseline=false]
     */
    checkFormattingTokens (arg0_line_no, arg1_clean_text, arg2_errors, arg3_warnings, arg4_legacy_baseline) {
      //Convert from parameters
      let clean_text = String(arg1_clean_text || "");
      let errors = arg2_errors;
      let legacy_baseline = Boolean(arg4_legacy_baseline);
      let line_no = arg0_line_no;
      let warnings = arg3_warnings;

      //Function body
      let m = null;
      let re_dot_era = /(?<![A-Za-z0-9_])\d+(?:\.\d+)+(?:BC|BCE|AD|CE)\b/g;
      for (let iter = 0; (m = re_dot_era.exec(clean_text)) !== null && iter < 20; iter++)
        errors.push(`Line ${line_no}: Malformed dotted/attached era date ${JSON.stringify(m[0])} (drop dots, e.g. \`10000BC\` or \`10000 BC\`).`);

      this.MONTH_YEAR_AD_PAT.lastIndex = 0;
      for (let iter = 0; (m = this.MONTH_YEAR_AD_PAT.exec(clean_text)) !== null && iter < 20; iter++)
        warnings.push(`Line ${line_no}: Modern month-year date ${JSON.stringify(m[0])} should omit \`AD\`.`);

      let re_sp_ad = /(?<![A-Za-z0-9_])\d[\d.,]*\s+AD\b/g;
      for (let iter = 0; (m = re_sp_ad.exec(clean_text)) !== null && iter < 20; iter++)
        errors.push(`Line ${line_no}: Spaced trailing \`AD\` in date ${JSON.stringify(m[0])} (write \`1600AD\` or \`AD 1600\`).`);

      let re_km2 = /\b(?:km2|m2|km\^2|m\^2)\b/g;
      for (let iter = 0; (m = re_km2.exec(clean_text)) !== null && iter < 20; iter++) {
        let msg = `Line ${line_no}: Malformed ASCII area unit ${JSON.stringify(m[0])} (use Unicode \`km²\` or \`m²\`).`;
        if (legacy_baseline) warnings.push(msg);
        else errors.push(msg);
      }

      let re_arr = /(?:^|\s)->(?:\s|$)/g;
      for (let iter = 0; (m = re_arr.exec(clean_text)) !== null && iter < 20; iter++)
        errors.push(`Line ${line_no}: Prose ASCII arrow \`->\` detected (replace with \`to\` or proper wording).`);

      if (!clean_text.trimStart().startsWith("|")) {
        let re_slash = /[A-Za-z0-9)]\s+\/\s+[A-Za-z0-9(]/g;
        for (let iter = 0; (m = re_slash.exec(clean_text)) !== null && iter < 20; iter++) {
          let msg = `Line ${line_no}: Space-padded slash ${JSON.stringify(m[0])} detected (use \`or\`, \`to\` or unspaced slash).`;
          if (legacy_baseline) warnings.push(msg);
          else errors.push(msg);
        }
      }

      let leak_rules = [
        [this.SCHEMA_LEAK_PAT, "leaked database/JSON schema term"],
        [this.SNAKE_LEAK_PAT, "leaked snake_case folder/code identifier"],
        [this.THE_PROJ_PAT, "verbose 'the <PROJECT> <noun>' wrapper (use bare `<PROJECT>`)"],
        [this.WORD_N_EQ_PAT, "redundant spelled-out number paired with `(n=...)`"],
        [this.UNPROMOTED_K_PAT, "unpromoted magnitude >= 1.000k (promote to `M`)"],
        [this.DECORATOR_COLOUR_PAT, "compound decorator colour adjective"],
        [this.EUPHEMISM_PAT, "vague demographic/conflict euphemism"]
      ];
      for (let i = 0; i < leak_rules.length; i++) {
        let lm = clean_text.match(leak_rules[i][0]);
        if (lm) {
          let msg = `Line ${line_no}: Forbidden ${leak_rules[i][1]}: ${JSON.stringify(lm[0])}.`;
          if (legacy_baseline && leak_rules[i][0] === this.SNAKE_LEAK_PAT) warnings.push(msg);
          else errors.push(msg);
        }
      }

      let re_med = /\bmedieval\b/gi;
      for (let iter = 0; (m = re_med.exec(clean_text)) !== null && iter < 20; iter++)
        warnings.push(`Line ${line_no}: Use non-Oxford British spelling \`mediaeval\` rather than ${JSON.stringify(m[0])}.`);
    },

    /**
     * Rejects non-code inline backticks and explicit LaTeX/HTML monospace spans outside code blocks.
     * @alias academic_prose_auditor.checkNoMonospace
     *
     * @param {number} arg0_line_no
     * @param {string} arg1_text
     * @param {Array<string>} arg2_errors
     * @param {Array<string>} arg3_warnings
     * @param {boolean} [arg4_legacy_baseline=false]
     */
    checkNoMonospace (arg0_line_no, arg1_text, arg2_errors, arg3_warnings, arg4_legacy_baseline) {
      //Convert from parameters
      let errors = arg2_errors;
      let legacy_baseline = Boolean(arg4_legacy_baseline);
      let line_no = arg0_line_no;
      let text = String(arg1_text || "");
      let warnings = arg3_warnings;

      //Function body
      let without_r = text.replace(this.KNITR_INLINE_R_PAT, " ");
      let m = null;
      this.INLINE_BACKTICK_PAT.lastIndex = 0;
      for (let iter = 0; (m = this.INLINE_BACKTICK_PAT.exec(without_r)) !== null && iter < 30; iter++) {
        let token = m[1];
        let msg = `Line ${line_no}: Monospace backtick span \`${token}\` outside code blocks (reserve monospace strictly for code; use plain text or italics in prose/captions/tables).`;
        if (legacy_baseline && token.trim().length <= 3) warnings.push(msg);
        else errors.push(msg);
      }

      this.EXPLICIT_MONO_PAT.lastIndex = 0;
      for (let iter = 0; (m = this.EXPLICIT_MONO_PAT.exec(without_r)) !== null && iter < 30; iter++)
        errors.push(`Line ${line_no}: Explicit monospace markup '${m[0]}' outside code blocks (reserve monospace strictly for code).`);
    },

    /**
     * Loads canonical itinerary titles from `<slug>_itinerary.json5` (preferred) or `<slug>_gazetteers.json5`.
     * @alias academic_prose_auditor.loadItineraryTitleSpec
     *
     * @param {string} arg0_rmd_path
     *
     * @returns {Object|null}
     */
    loadItineraryTitleSpec (arg0_rmd_path) {
      //Convert from parameters
      let cur = path.dirname(path.resolve(arg0_rmd_path));

      //Function body
      for (let step = 0; step < 4; step++) {
        if (!fs.existsSync(cur)) break;
        let files = fs.readdirSync(cur).sort();
        let itin_cands = files.filter(function (arg0_f) {
          return /_itinerary\.json5?$/i.test(arg0_f);
        });
        let gaz_cands = files.filter(function (arg0_f) {
          return /_gazetteers\.json5$/i.test(arg0_f);
        });
        let cands = itin_cands.concat(gaz_cands);

        for (let i = 0; i < cands.length; i++) {
          let full = path.join(cur, cands[i]);
          let data = null;
          try {
            data = viscount_audit_utils.loadJsonOrJson5(full);
          } catch (e) {
            continue;
          }
          if (!data || typeof data !== "object") continue;

          let title_map = {};
          let root_title = data.root_title || null;
          let chapters = data.chapters || data.itinerary || [];
          if (Array.isArray(chapters)) {
            for (let x = 0; x < chapters.length; x++) {
              let item = chapters[x];
              if (!item || typeof item !== "object") continue;
              let it_title = item.itinerary_title || item.title;
              if (!it_title) continue;
              let kfields = ["stem", "rmd", "folder", "id", "slug"];
              for (let y = 0; y < kfields.length; y++) {
                let kv = item[kfields[y]];
                if (kv) {
                  let kclean = path.basename(String(kv)).replace(/\.rmd$/i, "").trim().toLowerCase();
                  title_map[kclean] = String(it_title).trim();
                }
              }
            }
          } else if (chapters && typeof chapters === "object") {
            let keys = Object.keys(chapters);
            for (let x = 0; x < keys.length; x++) {
              let v = chapters[keys[x]];
              if (typeof v === "string")
                title_map[keys[x].trim().toLowerCase()] = v.trim();
              else if (v && typeof v === "object" && (v.itinerary_title || v.title))
                title_map[keys[x].trim().toLowerCase()] = String(v.itinerary_title || v.title).trim();
            }
          }
          if (root_title || Object.keys(title_map).length > 0)
            return { chapters: title_map, root_title: root_title, source: cands[i] };
        }

        let parent = path.dirname(cur);
        if (parent === cur) break;
        cur = parent;
      }

      //Return statement
      return null;
    },

    /**
     * Normalises title strings for itinerary comparison.
     * @alias academic_prose_auditor.normaliseTitleKey
     *
     * @param {string} arg0_text
     *
     * @returns {string}
     */
    normaliseTitleKey (arg0_text) {
      //Return statement
      return String(arg0_text || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
    },

    /**
     * Parses CLI arguments.
     * @alias academic_prose_auditor.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let out = { json: false, legacy_baseline: false, rmd_path: "", strict_prose: true };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok === "--warn-only-cliches") out.strict_prose = false;
        else if (tok === "--legacy-baseline") out.legacy_baseline = true;
        else if (tok === "--json") out.json = true;
        else if (!tok.startsWith("--") && !out.rmd_path) out.rmd_path = tok;
      }

      //Return statement
      return out;
    },

    /**
     * Strips YAML frontmatter, R code chunks and inline LaTeX math for prose scanning.
     * @alias academic_prose_auditor.stripNonProse
     *
     * @param {string} arg0_text
     *
     * @returns {Array<{ line_no: number, text: string }>}
     */
    stripNonProse (arg0_text) {
      //Convert from parameters
      let lines = String(arg0_text || "").split(/\r?\n/);

      //Declare local instance variables
      let in_code = false;
      let in_yaml = false;
      let prose_lines = [];

      //Function body
      for (let i = 0; i < lines.length; i++) {
        let line_no = i + 1;
        let line = lines[i];
        let stripped = line.trim();
        if (line_no === 1 && stripped === "---") {
          in_yaml = true;
          continue;
        }
        if (in_yaml) {
          if (stripped === "---") in_yaml = false;
          continue;
        }
        if (stripped.startsWith("```")) {
          in_code = !in_code;
          continue;
        }
        if (in_code) continue;

        let cleaned = line
          .replace(/\$\$?.*?\$\$?/g, " MATH ")
          .replace(this.KNITR_INLINE_R_PAT, " CODE ")
          .replace(this.INLINE_BACKTICK_PAT, "$1")
          .replace(/\[@[^\]]+\]/g, " CITE ")
          .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
          .replace(/\\[a-zA-Z]+\{[^}]*\}/g, " TEX ");
        prose_lines.push({ line_no: line_no, text: cleaned });
      }

      //Return statement
      return prose_lines;
    },

    /**
     * Removes knitr inline R calls, inline LaTeX math, markdown link targets, safe HTML tags and URLs.
     * @alias academic_prose_auditor.stripNonProseSpans
     *
     * @param {string} arg0_line
     *
     * @returns {string}
     */
    stripNonProseSpans (arg0_line) {
      //Return statement
      return String(arg0_line || "")
        .replace(this.KNITR_INLINE_R_PAT, " ")
        .replace(this.INLINE_BACKTICK_PAT, "$1")
        .replace(/\$\$[^$]+\$\$|\$[^$\n]+\$/g, " ")
        .replace(/\\\[.*?\\\]|\\\(.*?\\\)/g, " ")
        .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
        .replace(/https?:\/\/\S+/g, " ")
        .replace(/<[^>]+>/g, " ");
    }
  };

  if (require.main === module) {
    let cli = academic_prose_auditor.parseCliArgs(process.argv.slice(2));
    if (!cli.rmd_path) {
      console.error("Usage: node audit_academic_prose.js <rmd_path_or_dir> [--warn-only-cliches] [--legacy-baseline] [--json]");
      process.exit(2);
    }
    let res = academic_prose_auditor.auditRmdFile(cli.rmd_path, cli);
    if (cli.json) {
      console.log(JSON.stringify(res, null, 2));
    } else {
      for (let i = 0; i < Math.min(40, res.warnings.length); i++)
        console.log(`[WARN] ${res.warnings[i]}`);
      if (res.warnings.length > 40)
        console.log(`[WARN] ... and ${res.warnings.length - 40} additional warnings`);
      for (let i = 0; i < Math.min(40, res.errors.length); i++)
        console.error(`[FAIL] ${res.errors[i]}`);
      if (res.errors.length > 40)
        console.error(`[FAIL] ... and ${res.errors.length - 40} additional errors`);
      console.log(`[audit_academic_prose] ${cli.rmd_path}: ${res.errors.length} error(s), ${res.warnings.length} warning(s)`);
    }
    process.exit(res.success ? 0 : 1);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { academic_prose_auditor: academic_prose_auditor };
  }
}
