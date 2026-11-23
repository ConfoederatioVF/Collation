//Import modules
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let figure_scripts_auditor = {
    BAD_FONT_VALUES: [
      "serif", "times", "times new roman", "georgia", "palatino", "garamond",
      "bookman", "computer modern", "cmr", "courier", "monospace"
    ],
    BARE_COMMA_DECIMAL_RE: /\d,\d/,
    CALLOUT_GUARD_IDENTIFIERS: [
      "verify_panel_bounds_and_overlaps", "verify_zero_text_overlaps",
      "place_inbounds_callouts", "place_bbox_callouts",
      "place_callout_in_bounds", "place_callout", "save_viscount_figure"
    ],
    MANGLED_ROMAN_RE: /\b(?:Ii|Iii|Iv|Vii|Viii|Ix|Xii|Xiii|Xiv|Xvi|Xvii|Xviii|Xix)\b/,
    MASK_SOURCE_RE: /(?:_areal_mask\.png|_domain_mask\.png|["']mask_file["']|["']mask_path["'])/,
    MATPLOTLIB_IMPORT_RE: /\b(?:matplotlib|pyplot|mpl_toolkits|seaborn)\b/,
    RAW_CARET_MATH_RE: /(?<![A-Za-z0-9])\^|[A-Za-z0-9]\^(?:\{?-?[0-9A-Za-z]+\}?)/,
    RAW_GREEK_PARAM_RE: /\b(?:nu|tau_?[0-9]*|sigma_?[0-9]*|gamma|alpha|beta|lambda|kappa|rho|theta|chi|mu)\s*(?:=|[<>~])|\b(?:tau1|tau2|sigma2)\b|\bc0\s*\/\s*sill\b/,
    RAW_LOG_SQRT_RE: /\b(?:log_?10|log2|ln|sqrt)\s*\(|\|\s*grad\b/,
    RAW_RSQUARED_RE: /\b(?:r-squared|r\^2|chi-squared|chi\^2)\b/i,
    SKIP_DIRS: new Set([".git", ".Rproj.user", "__pycache__", "archive", "diagnostics_visual", "node_modules", "papers"]),
    TECHNOBABBLE_TITLE_RE: /\b(?:Fit Summary|Complete Secular|Carrying-Capacity Envelope|Spatiotemporal Paleodemographic|Empirical Validation)\b/,
    US_SHORT_DECIMAL_RE: /(?<!\d)\d+\.\d{1,2}(?!\d)/,

    /**
     * Checks a plot title/label string for balanced MathText, unrendered ASCII math, Roman numeral mangling and technobabble.
     * @alias figure_scripts_auditor.auditMathStringLiteral
     *
     * @param {string} arg0_text
     * @param {string} arg1_label
     * @param {number} arg2_line
     * @param {boolean} arg3_is_title
     * @param {Array<string>} arg4_errors
     * @param {Array<string>} arg5_warnings
     */
    auditMathStringLiteral (arg0_text, arg1_label, arg2_line, arg3_is_title, arg4_errors, arg5_warnings) {
      //Convert from parameters
      let errors = arg4_errors;
      let is_title = Boolean(arg3_is_title);
      let label = arg1_label;
      let line = arg2_line;
      let text = String(arg0_text || "");
      let warnings = arg5_warnings;

      //Guard clauses
      if (!text.trim()) return;

      //Function body
      if (this.MANGLED_ROMAN_RE.test(text))
        errors.push(`[${label}] line ${line}: mangled Title-Cased Roman numeral in plot label \`${text}\` (preserve \`II\`/\`III\`/\`IV\`).`);

      if (is_title && this.TECHNOBABBLE_TITLE_RE.test(text))
        errors.push(`[${label}] line ${line}: technobabble plot title \`${text}\` violates \`/humanise\` plain academic naming.`);

      let dollars = text.match(/(?<!\\)\$/g) || [];
      if (dollars.length % 2 !== 0) {
        errors.push(`[${label}] line ${line}: unbalanced \`$\` MathText delimiter in \`${text}\`.`);
        return;
      }

      let spans = text.split(/(?<!\\)\$/);
      let plain_parts = [];
      for (let i = 0; i < spans.length; i++) {
        if (i % 2 === 1) {
          if (this.BARE_COMMA_DECIMAL_RE.test(spans[i]))
            warnings.push(`[${label}] line ${line}: bare decimal comma inside MathText \`$${spans[i]}$\` adds TeX spacing; write \`{,}\` instead.`);
          if (this.US_SHORT_DECIMAL_RE.test(spans[i]))
            warnings.push(`[${label}] line ${line}: US decimal dot inside MathText \`$${spans[i]}$\`; use European \`{,}\` decimal.`);
        } else {
          plain_parts.push(spans[i]);
        }
      }

      let outside = plain_parts.join(" ");
      if (this.RAW_GREEK_PARAM_RE.test(outside))
        errors.push(`[${label}] line ${line}: unrendered ASCII Greek/parameter math outside \`$...$\` in \`${text}\`.`);
      if (this.RAW_RSQUARED_RE.test(outside))
        errors.push(`[${label}] line ${line}: unrendered \`R-squared\`/\`R^2\` outside \`$...$\` in \`${text}\` (render via \`$R^2$\`).`);
      if (this.RAW_LOG_SQRT_RE.test(outside))
        errors.push(`[${label}] line ${line}: unrendered \`log10\`/\`sqrt\`/\`grad\` outside \`$...$\` in \`${text}\`.`);
      if (this.RAW_CARET_MATH_RE.test(outside))
        errors.push(`[${label}] line ${line}: raw caret exponent outside \`$...$\` in \`${text}\` (use Unicode \`km²\`/\`m²\` or MathText \`$...$\`).`);
    },

    /**
     * Audits Python Matplotlib source code via line-preserving lexical scanning for all 5 POLARIS Figure Laws.
     * @alias figure_scripts_auditor.auditPythonSource
     *
     * @param {string} arg0_source
     * @param {string} arg1_label
     *
     * @returns {{ errors: Array<string>, warnings: Array<string> }}
     */
    auditPythonSource (arg0_source, arg1_label) {
      //Convert from parameters
      let label = arg1_label;
      let source = String(arg0_source || "");

      //Declare local instance variables
      let errors = [];
      let has_default_style_reset = source.includes("apply_viscount_style") ||
        /\brcdefaults\s*\(\s*\)/.test(source) ||
        /\bstyle\.use\s*\(\s*["']default["']\s*\)/.test(source);
      let has_fractional_axis_lim = false;
      let has_geo_labels = /\b(?:Longitude|Latitude)\b/.test(source);
      let has_layout_guard = false;
      let has_legend_or_cbar = /\b(?:legend|colorbar)\s*\(/.test(source);
      let has_log_formatter = /\b(?:apply_human_log_ticks|apply_plain_log_cbar|euro_log_formatter|set_major_formatter|set_ticklabels|set_xticklabels|set_yticklabels)\b/.test(source);
      let has_lognorm = /\b(?:LogNorm|SymLogNorm)\b/.test(source);
      let has_subplot_creation = /\b(?:subplots|figure)\s*\(/.test(source);
      let has_suptitle = false;
      let has_tick_formatter = /\b(?:FuncFormatter|euro_tick_formatter|apply_human_log_ticks|set_xticklabels|set_yticklabels)\b/.test(source);
      let has_tight_layout_no_rect = false;
      let is_stage_a_overlay = path.basename(label).toLowerCase() === "audit_areal_masks.py";
      let lines = source.split(/\r?\n/);
      let mask_vars = new Set();
      let text_annotate_count = 0;
      let warnings = [];

      //Function body
      for (let i = 0; i < this.CALLOUT_GUARD_IDENTIFIERS.length; i++) {
        if (source.includes(this.CALLOUT_GUARD_IDENTIFIERS[i])) {
          has_layout_guard = true;
          break;
        }
      }

      // Track categorical mask variable assignments
      for (let i = 0; i < lines.length; i++) {
        let code = this.stripPyComment(lines[i]);
        let assign_m = code.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$/);
        if (assign_m && this.MASK_SOURCE_RE.test(assign_m[2]))
          mask_vars.add(assign_m[1]);
      }

      for (let i = 0; i < lines.length; i++) {
        let line_no = i + 1;
        let code = this.stripPyComment(lines[i]);
        if (!code.trim()) continue;

        // Style overrides
        let style_m = code.match(/\bstyle\.use\s*\(\s*["']([^"']+)["']\s*\)/);
        if (style_m && style_m[1] !== "default")
          errors.push(`[${label}] line ${line_no}: non-default Matplotlib style \`${style_m[1]}\` is forbidden; use \`plt.rcdefaults(); plt.style.use('default')\`.`);

        let sns_m = code.match(/\b(?:sns|seaborn)\.(set_theme|set_style|set|despine)\s*\(/);
        if (sns_m)
          errors.push(`[${label}] line ${line_no}: Seaborn theme/despine \`sns.${sns_m[1]}\` overrides default Matplotlib styling.`);

        // Font overrides
        let font_re = /(?:["']font\.(?:family|serif)["']\s*[:=\]]\s*|family\s*=\s*|fontfamily\s*=\s*)["']([^"']+)["']/gi;
        let fm = null;
        for (let iter = 0; (fm = font_re.exec(code)) !== null && iter < 10; iter++) {
          if (this.isBannedFontName(fm[1]) || code.includes("font.serif"))
            errors.push(`[${label}] line ${line_no}: forbidden custom font \`${fm[1]}\`; keep Matplotlib default \`DejaVu Sans\` (\`sans-serif\`).`);
        }

        // Spine stripping
        if (/spines\[["'](?:top|right)["']\]\.set_visible\s*\(\s*False\s*\)/.test(code) ||
            /["']axes\.spines\.(?:top|right)["']\s*[:=\]]\s*False/.test(code)) {
          errors.push(`[${label}] line ${line_no}: disabling top/right spines violates default Matplotlib 4-sided axes frame.`);
        }

        // Mechanical .replace("_", " ").title()
        if (/\.replace\s*\(\s*["']_["']\s*,\s*["']\s*["']\s*\)\.title\s*\(\s*\)/.test(code))
          errors.push(`[${label}] line ${line_no}: mechanical \`.replace('_', ' ').title()\` mangles Roman numerals and acronyms; use an explicit display dictionary.`);

        // Geographic aspect warping
        if (has_geo_labels && /\bset_aspect\s*\(\s*["']auto["']\s*\)/.test(code))
          errors.push(`[${label}] line ${line_no}: \`set_aspect('auto')\` on geographic axes warps coastlines; use Equal-Area projection with \`set_aspect('equal')\`.`);

        if (/\bimshow\s*\(/.test(code)) {
          if (/\bextent\s*=/.test(code) && /\baspect\s*=\s*["']auto["']/.test(code))
            errors.push(`[${label}] line ${line_no}: spatial \`imshow(..., extent=..., aspect='auto')\` warps map geometry; use \`ax.set_aspect('equal')\`.`);
          if (!is_stage_a_overlay) {
            let im_m = code.match(/\bimshow\s*\(\s*([A-Za-z_][A-Za-z0-9_.\[\]:,\s]*)/);
            let first_arg = im_m ? im_m[1].trim() : "";
            let uses_mask_var = /(?:areal_mask|domain_mask)/i.test(first_arg);
            if (!uses_mask_var) {
              mask_vars.forEach(function (arg0_v) {
                if (new RegExp(`\\b${arg0_v}\\b`).test(first_arg)) uses_mask_var = true;
              });
            }
            if (uses_mask_var)
              errors.push(`[${label}] line ${line_no}: pixelated categorical mask \`${first_arg}\` rendered via \`imshow()\`; plot smooth vector GeoJSON PatchCollections.`);
          }
        }

        // Text/annotate & suptitle / tight_layout checks
        if (/\.\s*(?:text|annotate)\s*\(|\bplt\.(?:text|annotate)\s*\(/.test(code))
          text_annotate_count++;
        if (/\bsuptitle\s*\(/.test(code)) has_suptitle = true;
        if (/\btight_layout\s*\([^)]*\)/.test(code) && !/\brect\s*=/.test(code))
          has_tight_layout_no_rect = true;

        // Scientific notation & unformatted log axes
        let sci_t = code.match(/\bticklabel_format\s*\([^)]*style\s*=\s*["'](sci|scientific)["']/i);
        if (sci_t)
          errors.push(`[${label}] line ${line_no}: \`ticklabel_format(style='${sci_t[1]}')\` enables scientific notation; use plain European numerals.`);

        let fspec_re = /\{[^{}]*:([+\-<>^= 0-9.,_#]*[eE])\}/g;
        let fsm = null;
        for (let iter = 0; (fsm = fspec_re.exec(code)) !== null && iter < 10; iter++) {
          if (/\b(?:label|set_title|title|suptitle|set_xlabel|set_ylabel|xlabel|ylabel|annotate|text|FuncFormatter|set_ticklabels)\b/.test(code))
            errors.push(`[${label}] line ${line_no}: scientific format spec \`:${fsm[1]}\` forbidden in figure label/tick; use plain European numerals.`);
        }

        if (!has_log_formatter) {
          if (/\b(?:loglog|semilogx|semilogy)\s*\(/.test(code) || /\bset_[xy]scale\s*\(\s*["']log["']\s*\)/.test(code))
            errors.push(`[${label}] line ${line_no}: unformatted log axis defaults to \`10^k\` scientific notation; apply \`apply_human_log_ticks()\` or \`euro_log_formatter()\`.`);
          if (has_lognorm && /\bcolorbar\s*\(/.test(code) && !/\bformat\s*=/.test(code))
            errors.push(`[${label}] line ${line_no}: \`colorbar()\` paired with \`LogNorm\` lacks plain tick formatting (\`format=euro_log_formatter()\`).`);
        }

        // Fractional limits
        let lim_m = code.match(/\b(?:set_[xy]lim|[xy]lim)\s*\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)/);
        if (lim_m) {
          let lo = Number(lim_m[1]);
          let hi = Number(lim_m[2]);
          if (lo >= 0 && lo < hi && hi <= 1.05) has_fractional_axis_lim = true;
        }

        // Plot text sinks -> auditMathStringLiteral
        let sink_re = /\b(suptitle|set_title|title|set_xlabel|xlabel|set_ylabel|ylabel|set_label|annotate|text|figtext)\s*\(([^)]*)\)/g;
        let sm = null;
        for (let iter = 0; (sm = sink_re.exec(code)) !== null && iter < 10; iter++) {
          let fn_name = sm[1];
          let is_title = (fn_name === "suptitle" || fn_name === "set_title" || fn_name === "title");
          let str_re = /[rfRF]?(["'])((?:\\.|(?!\1).)*)\1/g;
          let st_m = null;
          for (let j = 0; (st_m = str_re.exec(sm[2])) !== null && j < 6; j++)
            this.auditMathStringLiteral(st_m[2], label, line_no, is_title, errors, warnings);
        }

        let lbl_re = /\blabel\s*=\s*[rfRF]?(["'])((?:\\.|(?!\1).)*)\1/g;
        let lm = null;
        for (let iter = 0; (lm = lbl_re.exec(code)) !== null && iter < 6; iter++)
          this.auditMathStringLiteral(lm[2], label, line_no, false, errors, warnings);
      }

      if (has_subplot_creation && !has_default_style_reset)
        warnings.push(`[${label}] script creates Matplotlib figures without explicit \`plt.rcdefaults()\` / \`plt.style.use('default')\` reset.`);
      if (has_fractional_axis_lim && !has_tick_formatter)
        warnings.push(`[${label}] fractional [0, 1] axis limits set without European \`FuncFormatter\` / tick formatting.`);
      if (has_subplot_creation && (text_annotate_count >= 1 || has_legend_or_cbar) &&
          !has_layout_guard && !is_stage_a_overlay && !label.includes("render_and_audit_kriging_visuals.py")) {
        errors.push(`[${label}] [OCCLUSION_GUARD] Figure script places labels/legends/colorbars without calling \`verify_panel_bounds_and_overlaps\` or \`save_viscount_figure(..., strict_layout=True)\`.`);
      }
      if (has_suptitle && has_tight_layout_no_rect)
        errors.push(`[${label}] [OCCLUSION_GUARD] Calls \`suptitle()\` paired with \`tight_layout()\` without \`rect=[0, 0, 1, 0.94]\`; risks suptitle overlapping top panel titles.`);

      //Return statement
      return { errors: errors, warnings: warnings };
    },

    /**
     * Audits an R plotting chunk or standalone R plotting script.
     * @alias figure_scripts_auditor.auditRPlotChunk
     *
     * @param {string} arg0_code
     * @param {string} arg1_label
     *
     * @returns {{ errors: Array<string>, warnings: Array<string> }}
     */
    auditRPlotChunk (arg0_code, arg1_label) {
      //Convert from parameters
      let code = String(arg0_code || "");
      let label = arg1_label;

      //Declare local instance variables
      let errors = [];
      let warnings = [];

      //Function body
      if (/family\s*=\s*["'](?:serif|Times|Georgia|Palatino|Garamond)["']/i.test(code))
        errors.push(`[${label}] forbidden serif font override in R plot.`);
      if (/\b(?:theme_classic|panel\.border\s*=\s*element_blank)\b/.test(code))
        warnings.push(`[${label}] R plot removes top/right panel border.`);

      let r_re = /(?:ggtitle|xlab|ylab)\s*\(\s*["']([^"']+)["']|(?:main|title|subtitle|x|y)\s*=\s*["']([^"']+)["']/g;
      let rm = null;
      for (let iter = 0; (rm = r_re.exec(code)) !== null && iter < 40; iter++) {
        let txt = rm[1] || rm[2];
        if (txt) this.auditMathStringLiteral(txt, label, 1, true, errors, warnings);
      }

      //Return statement
      return { errors: errors, warnings: warnings };
    },

    /**
     * Audits R scripts or Python/R chunks inside `.Rmd` files.
     * @alias figure_scripts_auditor.auditROrRmdSource
     *
     * @param {string} arg0_source
     * @param {string} arg1_label
     * @param {boolean} arg2_is_rmd
     *
     * @returns {{ errors: Array<string>, warnings: Array<string> }}
     */
    auditROrRmdSource (arg0_source, arg1_label, arg2_is_rmd) {
      //Convert from parameters
      let is_rmd = Boolean(arg2_is_rmd);
      let label = arg1_label;
      let source = String(arg0_source || "");

      //Declare local instance variables
      let errors = [];
      let warnings = [];

      //Function body
      if (is_rmd) {
        let chunk_re = /```\{([A-Za-z]+)[^}]*\}\r?\n([\s\S]*?)```/g;
        let m = null;
        let idx = 0;
        for (let iter = 0; (m = chunk_re.exec(source)) !== null && iter < 200; iter++) {
          idx++;
          let lang = m[1].trim().toLowerCase();
          let body = m[2];
          let chunk_label = `${label}#chunk${idx}(${lang})`;
          if (lang === "python" && this.MATPLOTLIB_IMPORT_RE.test(body)) {
            let r = this.auditPythonSource(body, chunk_label);
            for (let i = 0; i < r.errors.length; i++) errors.push(r.errors[i]);
            for (let i = 0; i < r.warnings.length; i++) warnings.push(r.warnings[i]);
          } else if (lang === "r" && /\b(?:ggplot|plot)\s*\(/.test(body)) {
            let r = this.auditRPlotChunk(body, chunk_label);
            for (let i = 0; i < r.errors.length; i++) errors.push(r.errors[i]);
            for (let i = 0; i < r.warnings.length; i++) warnings.push(r.warnings[i]);
          }
        }
        return { errors: errors, warnings: warnings };
      }

      if (/\b(?:ggplot|plot)\s*\(/.test(source))
        return this.auditRPlotChunk(source, label);

      //Return statement
      return { errors: errors, warnings: warnings };
    },

    /**
     * Discovers and audits all figure scripts under a file or directory.
     * @alias figure_scripts_auditor.auditTarget
     *
     * @param {string} arg0_target_path
     *
     * @returns {{ errors: Array<string>, files_checked: number, success: boolean, warnings: Array<string> }}
     */
    auditTarget (arg0_target_path) {
      //Convert from parameters
      let abs_target = path.resolve(arg0_target_path);

      //Guard clauses
      if (!fs.existsSync(abs_target))
        return { errors: [`Target path does not exist: ${arg0_target_path}`], files_checked: 0, success: false, warnings: [] };

      //Declare local instance variables
      let all_errors = [];
      let all_warnings = [];
      let is_dir = fs.statSync(abs_target).isDirectory();
      let base_root = is_dir ? abs_target : path.dirname(abs_target);
      let files = this.collectFigureScripts(abs_target);

      //Function body
      for (let i = 0; i < files.length; i++) {
        let fpath = files[i];
        let rel = path.relative(base_root, fpath).replace(/\\/g, "/") || path.basename(fpath);
        let content = "";
        try {
          content = fs.readFileSync(fpath, "utf8");
        } catch (e) {
          all_errors.push(`[${rel}] Failed to read file: ${e.message}`);
          continue;
        }
        let ext = path.extname(fpath).toLowerCase();
        let res = (ext === ".py") ? this.auditPythonSource(content, rel) :
          this.auditROrRmdSource(content, rel, ext !== ".r");
        for (let x = 0; x < res.errors.length; x++) all_errors.push(res.errors[x]);
        for (let x = 0; x < res.warnings.length; x++) all_warnings.push(res.warnings[x]);
      }

      //Return statement
      return {
        errors: all_errors,
        files_checked: files.length,
        success: all_errors.length === 0,
        warnings: all_warnings
      };
    },

    /**
     * Collects Matplotlib Python scripts, R plotting scripts and `.Rmd` files with plot chunks.
     * @alias figure_scripts_auditor.collectFigureScripts
     *
     * @param {string} arg0_target_path
     *
     * @returns {Array<string>}
     */
    collectFigureScripts (arg0_target_path) {
      //Convert from parameters
      let abs_target = path.resolve(arg0_target_path);

      //Guard clauses
      if (fs.statSync(abs_target).isFile()) return [abs_target];

      //Declare local instance variables
      let that = this;
      let collected = [];
      let all = viscount_audit_utils.walkFiles(abs_target, function (arg0_full, arg1_name) {
        let low = arg1_name.toLowerCase();
        return low.endsWith(".py") || low.endsWith(".r") || low.endsWith(".rmd");
      }, this.SKIP_DIRS);

      //Function body
      for (let i = 0; i < all.length; i++) {
        let fpath = all[i];
        let low = fpath.toLowerCase();
        let src = "";
        try {
          src = fs.readFileSync(fpath, "utf8");
        } catch (e) {
          continue;
        }
        if (low.endsWith(".py") && that.MATPLOTLIB_IMPORT_RE.test(src))
          collected.push(fpath);
        else if ((low.endsWith(".r") || low.endsWith(".rmd")) && /\b(?:ggplot|matplotlib|pyplot)\b/.test(src))
          collected.push(fpath);
      }

      //Return statement
      return collected;
    },

    /**
     * Returns true when a font-family specifier overrides default `DejaVu Sans` / `sans-serif`.
     * @alias figure_scripts_auditor.isBannedFontName
     *
     * @param {string} arg0_font_value
     *
     * @returns {boolean}
     */
    isBannedFontName (arg0_font_value) {
      //Convert from parameters
      let low = String(arg0_font_value || "").trim().toLowerCase();

      //Guard clauses
      if (!low || low === "sans-serif" || low === "dejavu sans" || low === "sans") return false;

      //Function body
      for (let i = 0; i < this.BAD_FONT_VALUES.length; i++) {
        if (low.includes(this.BAD_FONT_VALUES[i])) return true;
      }

      //Return statement
      return false;
    },

    /**
     * Parses CLI flags.
     * @alias figure_scripts_auditor.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let out = { json: false, target: "" };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        if (argv[i] === "--json") out.json = true;
        else if (!argv[i].startsWith("--") && !out.target) out.target = argv[i];
      }

      //Return statement
      return out;
    },

    /**
     * Strips trailing Python `#` comments outside quoted strings.
     * @alias figure_scripts_auditor.stripPyComment
     *
     * @param {string} arg0_line
     *
     * @returns {string}
     */
    stripPyComment (arg0_line) {
      //Convert from parameters
      let s = String(arg0_line || "");

      //Declare local instance variables
      let quote = "";

      //Function body
      for (let i = 0; i < s.length; i++) {
        let ch = s[i];
        if (quote) {
          if (ch === "\\") {
            i++;
            continue;
          }
          if (ch === quote) quote = "";
        } else {
          if (ch === "'" || ch === "\"") quote = ch;
          else if (ch === "#") return s.slice(0, i);
        }
      }

      //Return statement
      return s;
    }
  };

  if (require.main === module) {
    let cli = figure_scripts_auditor.parseCliArgs(process.argv.slice(2));
    if (!cli.target) {
      console.error("Usage: node audit_figure_scripts.js <target> [--json]");
      process.exit(2);
    }
    let res = figure_scripts_auditor.auditTarget(cli.target);
    if (cli.json) {
      console.log(JSON.stringify(res, null, 2));
    } else {
      for (let i = 0; i < Math.min(50, res.errors.length); i++)
        console.error(`[FAIL] ${res.errors[i]}`);
      if (res.errors.length > 50)
        console.error(`[FAIL] ... and ${res.errors.length - 50} additional error(s).`);
      for (let i = 0; i < Math.min(30, res.warnings.length); i++)
        console.log(`[WARN] ${res.warnings[i]}`);
      if (res.warnings.length > 30)
        console.log(`[WARN] ... and ${res.warnings.length - 30} additional warning(s).`);
      console.log(`[audit_figure_scripts] ${cli.target}: ${res.files_checked} file(s), ${res.errors.length} error(s), ${res.warnings.length} warning(s).`);
    }
    process.exit(res.success ? 0 : 1);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { figure_scripts_auditor: figure_scripts_auditor };
  }
}
