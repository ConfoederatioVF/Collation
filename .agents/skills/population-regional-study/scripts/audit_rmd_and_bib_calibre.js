//Import modules
let child_process = require("child_process");
let crypto = require("crypto");
let fs = require("fs");
let os = require("os");
let path = require("path");
let { figure_scripts_auditor } = require("./audit_figure_scripts");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let rmd_and_bib_auditor = {
    BANNED_FALLBACK_PATTERNS: [
      ["mcevedy", /\bmcevedy\b/i],
      ["kleingoldewijk", /\bklein\s*goldewijk\b/i],
      ["populstat", /\bpopulstat\b/i],
      ["chandler1987", /\bchandler\s*1987\b/i],
      ["modelski2003", /\bmodelski\s*2003\b/i],
      ["maddison", /\bmaddison\b/i]
    ],
    CROWD_BIB_RE: /wikidata\.org|openstreetmap\.org|overpass-api|geonames\.org|wikipedia\.org/i,
    PUBLISHER_FIELD_RE: /\b(?:journal|publisher|institution|booktitle)\s*=\s*[{"]([^}"]+)/i,
    SKIP_DIRS: new Set(["_shared", "archive", "diagnostics_visual", "papers", ".git", ".Rproj.user", "figures", "node_modules"]),
    URL_HOST_RE: /https?:\/\/(?:www\.)?([A-Za-z0-9.-]+\.[A-Za-z]{2,})/i,
    ZENODO_BIB_RE: /zenodo\.org|10\.5281\/zenodo|\bzenodo\b/i,

    /**
     * Audits a single Viscount sub-chapter folder for Rmd/bib calibre, citation diversity, path lengths,
     * archival PDF validity/deduplication, Zipf floors, freshness and visual checks.
     * @alias rmd_and_bib_auditor.auditChapterDir
     *
     * @param {string} arg0_chapter_dir
     * @param {string} arg1_root_dir
     * @param {Object} [arg2_options]
     * @param {Object} [arg3_pdf_probes]
     *
     * @returns {{ errors: Array<string>, metrics: Object, warnings: Array<string> }}
     */
    auditChapterDir (arg0_chapter_dir, arg1_root_dir, arg2_options, arg3_pdf_probes) {
      //Convert from parameters
      let chapter_dir = path.resolve(arg0_chapter_dir);
      let opts = (arg2_options) ? arg2_options : {};
      let pdf_probes = (arg3_pdf_probes) ? arg3_pdf_probes : {};
      let root_dir = path.resolve(arg1_root_dir);

      //Declare local instance variables
      let errors = [];
      let rel_label = path.relative(root_dir, chapter_dir).replace(/\\/g, "/");
      let require_pdfs = Boolean(opts.require_compiled_pdfs);
      let require_visual = Boolean(opts.require_visual_check);
      let svea_root = opts.svea_root || viscount_audit_utils.findSveaRoot(chapter_dir);
      let profiles = viscount_audit_utils.loadSkillProfiles(svea_root);
      let cite_lim = (profiles && profiles.citation_diversity_limits) ? profiles.citation_diversity_limits : {};
      let path_lim = (profiles && profiles.path_and_title_limits) ? profiles.path_and_title_limits : {};
      let prov_caps = (profiles && profiles.provenance_caps) ? profiles.provenance_caps : {};
      let warnings = [];

      if (!rel_label || rel_label === ".") rel_label = path.basename(chapter_dir);

      //Function body
      let max_fn_chars = Number(path_lim.max_filename_chars || 72);
      let max_repo_chars = Number(path_lim.max_repo_rel_path_chars || 180);
      let max_stem_chars = Number(path_lim.max_chapter_stem_chars || 42);

      let files = fs.readdirSync(chapter_dir).sort();
      let rmds = files.filter(function (arg0_f) { return arg0_f.toLowerCase().endsWith(".rmd"); });
      let settlement_stems = {};
      let review_stems = {};

      for (let i = 0; i < rmds.length; i++) {
        let fn = rmds[i];
        let low = fn.toLowerCase();
        if (fn.length > max_fn_chars)
          errors.push(`[${rel_label}] [PATH_LIMIT] Rmd filename \`${fn}\` is ${fn.length} chars (> ${max_fn_chars} max).`);
        if (svea_root) {
          let rp = path.relative(svea_root, path.join(chapter_dir, fn)).replace(/\\/g, "/");
          if (!rp.startsWith("..") && rp.length > max_repo_chars)
            errors.push(`[${rel_label}] [PATH_LIMIT] Repo-relative path \`${rp}\` is ${rp.length} chars (> ${max_repo_chars} max).`);
        }
        if (low.endsWith("_settlements.rmd"))
          settlement_stems[fn.replace(/_settlements\.rmd$/i, "")] = fn;
        else if (low.endsWith("_literature_review.rmd") || low.endsWith("_areal_masks_and_bins.rmd"))
          review_stems[fn.replace(/_(?:literature_review|areal_masks_and_bins)\.rmd$/i, "")] = fn;
      }

      let paired_stems = Object.keys(settlement_stems).filter(function (arg0_k) {
        return Boolean(review_stems[arg0_k]);
      }).sort();

      if (paired_stems.length === 0)
        errors.push(`[${rel_label}] Missing paired \`<stem>_settlements.Rmd\` and \`<stem>_literature_review.Rmd\` (or \`*_areal_masks_and_bins.Rmd\`). Found: ${JSON.stringify(rmds)}`);

      let review_lines = 0;
      let review_words = 0;
      let combined_review_text = "";
      for (let i = 0; i < paired_stems.length; i++) {
        let stem = paired_stems[i];
        if (stem.length > max_stem_chars)
          errors.push(`[${rel_label}] [PATH_LIMIT] Chapter stem \`${stem}\` is ${stem.length} chars (> ${max_stem_chars} max).`);

        let rev_path = path.join(chapter_dir, review_stems[stem]);
        let sett_path = path.join(chapter_dir, settlement_stems[stem]);
        let rev_text = fs.readFileSync(rev_path, "utf8");
        let sett_text = fs.readFileSync(sett_path, "utf8");
        combined_review_text += "\n" + rev_text;

        let l_cnt = rev_text.split(/\r?\n/).length;
        let w_cnt = (rev_text.match(/\S+/g) || []).length;
        if (l_cnt > review_lines) review_lines = l_cnt;
        if (w_cnt > review_words) review_words = w_cnt;

        if (l_cnt < 350)
          errors.push(`[${rel_label}] ${review_stems[stem]}: ${l_cnt} lines below anti-stub guardrail (>= 350 lines).`);
        if (w_cnt < 2500)
          errors.push(`[${rel_label}] ${review_stems[stem]}: ${w_cnt} words below anti-stub guardrail (>= 2500 words).`);
        if (sett_text.split(/\r?\n/).length < 30)
          errors.push(`[${rel_label}] ${settlement_stems[stem]} appears stubbed (< 30 lines).`);

        if (require_pdfs) {
          let pair_rmds = [review_stems[stem], settlement_stems[stem]];
          for (let x = 0; x < pair_rmds.length; x++) {
            let expected_pdf = path.join(chapter_dir, pair_rmds[x].replace(/\.rmd$/i, ".pdf"));
            if (!fs.existsSync(expected_pdf))
              errors.push(`[${rel_label}] Missing compiled PDF ${path.basename(expected_pdf)}.`);
          }
        }
      }

      // Archival PDFs in ./papers/ (magic bytes, SHA-256 deduplication, GitHub filename & path length caps)
      let papers_dir = path.join(chapter_dir, "papers");
      let valid_pdfs = [];
      let seen_pdf_hashes = new Map();
      let min_pdf_count = Number(cite_lim.min_pdf_count_chapter || 15);

      if (!fs.existsSync(papers_dir) || !fs.statSync(papers_dir).isDirectory()) {
        errors.push(`[${rel_label}] Missing ./papers/ directory (anti-stub guardrail requires >= ${min_pdf_count} valid archival PDFs).`);
      } else {
        let p_files = fs.readdirSync(papers_dir).filter(function (arg0_f) {
          return arg0_f.toLowerCase().endsWith(".pdf");
        }).sort();
        for (let i = 0; i < p_files.length; i++) {
          let p_fn = p_files[i];
          let pdf_path = path.join(papers_dir, p_fn);
          if (p_fn.length > max_fn_chars)
            errors.push(`[${rel_label}] [PATH_LIMIT] Archival PDF \`papers/${p_fn}\` filename is ${p_fn.length} chars (> ${max_fn_chars} GitHub/Windows max; rename concisely).`);
          if (svea_root) {
            let rp = path.relative(svea_root, pdf_path).replace(/\\/g, "/");
            if (!rp.startsWith("..") && rp.length > max_repo_chars)
              errors.push(`[${rel_label}] [PATH_LIMIT] Archival PDF path \`${rp}\` is ${rp.length} chars (> ${max_repo_chars} GitHub max).`);
          }
          if (this.isValidPdfFile(pdf_path)) {
            let h_val = crypto.createHash("sha256").update(fs.readFileSync(pdf_path)).digest("hex");
            if (seen_pdf_hashes.has(h_val)) {
              errors.push(`[${rel_label}] Duplicate archival PDF in ./papers/: \`${p_fn}\` is identical to \`${seen_pdf_hashes.get(h_val)}\`.`);
            } else {
              seen_pdf_hashes.set(h_val, p_fn);
              valid_pdfs.push(p_fn);
            }
          } else {
            errors.push(`[${rel_label}] Corrupt/stub archival file papers/${p_fn} (failed > 10 KB + \`%PDF-\` magic check).`);
          }
        }
        if (valid_pdfs.length < min_pdf_count)
          errors.push(`[${rel_label}] Only ${valid_pdfs.length} unique valid PDFs in ./papers/ (anti-stub guardrail requires >= ${min_pdf_count} valid \`%PDF-\` files).`);
      }

      // Unique .bib entries, DOI/URL coverage, source diversity & in-text citation concentration
      let ref_bibs = [];
      for (let i = 0; i < paired_stems.length; i++) {
        let stem = paired_stems[i];
        let p_rmds = [path.join(chapter_dir, review_stems[stem]), path.join(chapter_dir, settlement_stems[stem])];
        for (let x = 0; x < p_rmds.length; x++) {
          let hdr = fs.readFileSync(p_rmds[x], "utf8");
          let bm = hdr.match(/^bibliography\s*:\s*([^\r\n#]+)/m);
          if (bm) {
            let bname = bm[1].trim().replace(/^["']|["']$/g, "");
            if (!ref_bibs.includes(bname)) ref_bibs.push(bname);
          }
        }
      }

      let bib_info = this.parseChapterBibs(chapter_dir, ref_bibs.length > 0 ? ref_bibs : null);
      let min_bib_keys = Number(cite_lim.min_unique_bib_keys_chapter || 20);
      let max_zen_ch = Number(prov_caps.max_zenodo_bib_ratio_chapter || 0.15);
      let max_crowd_bib = Number(prov_caps.max_crowd_bib_ratio || 0.10);
      let min_pub_doms = Number(prov_caps.min_bib_publisher_domains || 5);
      let max_author_dom_share = Number(cite_lim.max_single_author_or_domain_share || 0.30);

      if (bib_info.keys.length < min_bib_keys)
        errors.push(`[${rel_label}] Only ${bib_info.keys.length} unique .bib entries (anti-stub guardrail requires >= ${min_bib_keys}).`);

      if (bib_info.total_entries > 0) {
        let doi_ratio = bib_info.linked_entries/bib_info.total_entries;
        if (doi_ratio < 0.85)
          errors.push(`[${rel_label}] Referenced bibliography DOI/URL coverage is ${bib_info.linked_entries}/${bib_info.total_entries} (${(doi_ratio*100).toFixed(1)}% < 85,0% floor).`);

        let zen_ratio = bib_info.zenodo_entries/bib_info.total_entries;
        if (zen_ratio > max_zen_ch)
          errors.push(`[${rel_label}] [BIB_DIVERSITY] Excessive Zenodo reliance: ${bib_info.zenodo_entries}/${bib_info.total_entries} (${(zen_ratio*100).toFixed(1)}% > ${(max_zen_ch*100).toFixed(0)}% cap).`);

        let crowd_ratio = bib_info.crowd_entries/bib_info.total_entries;
        if (crowd_ratio > max_crowd_bib)
          errors.push(`[${rel_label}] [BIB_DIVERSITY] Excessive Wikidata/OSM/GeoNames/Wikipedia citations: ${bib_info.crowd_entries}/${bib_info.total_entries} (${(crowd_ratio*100).toFixed(1)}% > ${(max_crowd_bib*100).toFixed(0)}% cap).`);

        if (bib_info.total_entries >= 10 && bib_info.publisher_domains < min_pub_doms)
          errors.push(`[${rel_label}] [BIB_DIVERSITY] Bibliography cites only ${bib_info.publisher_domains} distinct publisher/journal/domain(s) (< ${min_pub_doms} minimum).`);

        if (bib_info.total_entries >= 10 && bib_info.max_author_share > max_author_dom_share)
          errors.push(`[${rel_label}] [SOURCE_CONCENTRATION] Single first author \`${bib_info.top_author}\` accounts for ${(bib_info.max_author_share*100).toFixed(1)}% of .bib entries (> ${(max_author_dom_share*100).toFixed(0)}% cap).`);

        if (bib_info.total_entries >= 10 && bib_info.max_domain_share > max_author_dom_share)
          errors.push(`[${rel_label}] [SOURCE_CONCENTRATION] Single publisher/domain \`${bib_info.top_domain}\` accounts for ${(bib_info.max_domain_share*100).toFixed(1)}% of .bib entries (> ${(max_author_dom_share*100).toFixed(0)}% cap).`);
      }

      // In-text citation concentration & bibliography utilisation check
      let cite_stats = this.auditInTextCitations(combined_review_text, bib_info.keys, rel_label, cite_lim, errors);

      // Banned fallback datasets, # References ban, wide tables
      for (let i = 0; i < files.length; i++) {
        let fn = files[i];
        let low = fn.toLowerCase();
        if (!low.endsWith(".rmd") && !low.endsWith(".bib")) continue;
        let txt = fs.readFileSync(path.join(chapter_dir, fn), "utf8");
        for (let x = 0; x < this.BANNED_FALLBACK_PATTERNS.length; x++) {
          if (this.BANNED_FALLBACK_PATTERNS[x][1].test(txt))
            errors.push(`[${rel_label}] ${fn}: banned global fallback reference \`${this.BANNED_FALLBACK_PATTERNS[x][0]}\` found in sub-chapter source/bibliography.`);
        }
        if (low.endsWith(".rmd")) {
          if (/^#\s+References\s*$/m.test(txt))
            errors.push(`[${rel_label}] ${fn}: use \`# Sources\` rather than \`# References\`.`);
          let tm_re = /col_names\s*=\s*c\(([^)]+)\)/g;
          let tm = null;
          for (let iter = 0; (tm = tm_re.exec(txt)) !== null && iter < 30; iter++) {
            let ncols = (tm[1].match(/["'][^"']+["']/g) || []).length;
            if (ncols > 14)
              errors.push(`[${rel_label}] ${fn}: table defines ${ncols} columns (> 14 max); split across multiple compact tables.`);
            else if (ncols > 10)
              warnings.push(`[${rel_label}] ${fn}: wide table has ${ncols} columns (> 10); consider splitting for portrait readability.`);
          }
        }
      }

      this.auditZipfSampleFloor(chapter_dir, rel_label, errors);

      // Compiled PDF geometry evaluation (using pre-batched PyMuPDF probe results)
      let compiled_pdfs = files.filter(function (arg0_f) { return arg0_f.toLowerCase().endsWith(".pdf"); })
        .map(function (arg0_f) { return path.join(chapter_dir, arg0_f); });
      let pdf_metrics = {};
      for (let i = 0; i < compiled_pdfs.length; i++) {
        let pdf_p = compiled_pdfs[i];
        pdf_metrics[path.basename(pdf_p)] = this.evaluatePdfProbe(pdf_p, pdf_probes[path.resolve(pdf_p)], rel_label, errors, warnings);
      }

      this.auditFigureAndPdfFreshness(chapter_dir, root_dir, rel_label, require_visual, errors, warnings);
      this.auditVisualCheckManifest(chapter_dir, rel_label, require_visual, errors, warnings);

      let metrics = {
        bib_entries: bib_info.keys.length,
        bib_linked_entries: bib_info.linked_entries,
        bib_total_entries: bib_info.total_entries,
        chapter: rel_label,
        citation_concentration: cite_stats,
        compiled_pdfs: pdf_metrics,
        review_lines: review_lines,
        review_words: review_words,
        valid_paper_pdfs: valid_pdfs.length
      };

      //Return statement
      return { errors: errors, metrics: metrics, warnings: warnings };
    },

    /**
     * Verifies mask/GeoJSON -> figure PNG -> compiled PDF mtime synchronisation.
     * @alias rmd_and_bib_auditor.auditFigureAndPdfFreshness
     *
     * @param {string} arg0_dir
     * @param {string} arg1_root_dir
     * @param {string} arg2_label
     * @param {boolean} arg3_require_visual_check
     * @param {Array<string>} arg4_errors
     * @param {Array<string>} arg5_warnings
     */
    auditFigureAndPdfFreshness (arg0_dir, arg1_root_dir, arg2_label, arg3_require_visual_check, arg4_errors, arg5_warnings) {
      //Convert from parameters
      let dir = path.resolve(arg0_dir);
      let errors = arg4_errors;
      let label = arg2_label;
      let require_visual = Boolean(arg3_require_visual_check);
      let root_dir = path.resolve(arg1_root_dir);
      let warnings = arg5_warnings;

      //Declare local instance variables
      let fig_dir = path.join(dir, "figures");
      let pngs = (fs.existsSync(fig_dir) && fs.statSync(fig_dir).isDirectory()) ?
        fs.readdirSync(fig_dir).filter(function (arg0_f) { return arg0_f.toLowerCase().endsWith(".png"); })
          .map(function (arg0_f) { return path.join(fig_dir, arg0_f); }) : [];
      let pdfs = fs.readdirSync(dir).filter(function (arg0_f) { return arg0_f.toLowerCase().endsWith(".pdf"); })
        .map(function (arg0_f) { return path.join(dir, arg0_f); });

      //Guard clauses
      if (pngs.length === 0) return;

      //Function body
      let newest_png_m = 0;
      for (let i = 0; i < pngs.length; i++) {
        let mt = fs.statSync(pngs[i]).mtimeMs/1000.0;
        if (mt > newest_png_m) newest_png_m = mt;
      }

      if (pdfs.length > 0) {
        let oldest_pdf_m = Infinity;
        for (let i = 0; i < pdfs.length; i++) {
          let mt = fs.statSync(pdfs[i]).mtimeMs/1000.0;
          if (mt < oldest_pdf_m) oldest_pdf_m = mt;
        }
        if (oldest_pdf_m + 2.0 < newest_png_m)
          errors.push(`[${label}] Compiled PDF is older than regenerated figure PNG(s) in figures/; recompile RMarkdown so PDFs reflect current figures and masks.`);
      }

      let spatial_pngs = pngs.filter(function (arg0_p) {
        return /(?:^fig1_|spatial|map|hero|zones)/i.test(path.basename(arg0_p));
      });
      if (spatial_pngs.length === 0) return;

      let source_paths = fs.readdirSync(dir).filter(function (arg0_f) {
        return arg0_f.toLowerCase().endsWith("_areal_mask.png");
      }).map(function (arg0_f) { return path.join(dir, arg0_f); });

      let subreg_dir = path.join(root_dir, "_shared", "_gis_cache", "chapter_subregions");
      let base_len = source_paths.length;
      for (let i = 0; i < base_len; i++) {
        let stem = path.basename(source_paths[i]).replace(/_areal_mask\.png$/i, "");
        let vec_p = path.join(subreg_dir, `${stem}_subregions.geojson`);
        if (fs.existsSync(vec_p)) source_paths.push(vec_p);
      }
      if (dir === root_dir) {
        let gcache = path.join(root_dir, "_shared", "_gis_cache");
        if (fs.existsSync(gcache)) {
          let gf = fs.readdirSync(gcache).filter(function (arg0_f) { return arg0_f.endsWith("_polygons.geojson"); });
          for (let i = 0; i < gf.length; i++) source_paths.push(path.join(gcache, gf[i]));
        }
      }
      if (source_paths.length === 0) return;

      let oldest_sp_m = Infinity;
      let newest_src_m = 0;
      for (let i = 0; i < spatial_pngs.length; i++) {
        let mt = fs.statSync(spatial_pngs[i]).mtimeMs/1000.0;
        if (mt < oldest_sp_m) oldest_sp_m = mt;
      }
      for (let i = 0; i < source_paths.length; i++) {
        let mt = fs.statSync(source_paths[i]).mtimeMs/1000.0;
        if (mt > newest_src_m) newest_src_m = mt;
      }

      if (oldest_sp_m + 2.0 < newest_src_m) {
        let msg = `[${label}] Spatial figure PNG(s) are older than updated areal mask/GeoJSON sources; regenerate figures and recompile PDF.`;
        if (require_visual) errors.push(msg);
        else warnings.push(msg);
      }
    },

    /**
     * Audits in-text citation concentration and bibliography utilisation across a chapter's review text.
     * @alias rmd_and_bib_auditor.auditInTextCitations
     *
     * @param {string} arg0_rmd_text
     * @param {Array<string>} arg1_bib_keys
     * @param {string} arg2_label
     * @param {Object} arg3_limits
     * @param {Array<string>} arg4_errors
     *
     * @returns {Object}
     */
    auditInTextCitations (arg0_rmd_text, arg1_bib_keys, arg2_label, arg3_limits, arg4_errors) {
      //Convert from parameters
      let bib_keys = Array.isArray(arg1_bib_keys) ? arg1_bib_keys : [];
      let errors = arg4_errors;
      let label = arg2_label;
      let limits = (arg3_limits) ? arg3_limits : {};
      let raw = String(arg0_rmd_text || "");

      //Declare local instance variables
      let bib_set = new Set(bib_keys.map(function (arg0_k) { return arg0_k.toLowerCase(); }));
      let cite_counts = new Map();
      let max_single = Number(limits.max_single_source_cite_share || 0.20);
      let max_top3 = Number(limits.max_top3_sources_cite_share || 0.45);
      let min_distinct = Number(limits.min_distinct_cited_keys_chapter || 15);
      let min_util = Number(limits.min_cited_bib_utilisation || 0.75);
      let total_cites = 0;

      //Guard clauses
      if (!raw || bib_keys.length === 0)
        return { distinct_cited: 0, max_single_share: 0, top3_share: 0, total_cites: 0, utilisation: 0 };

      //Function body
      // Strip YAML frontmatter and fenced code blocks
      let lines = raw.split(/\r?\n/);
      let in_yaml = false;
      let in_code = false;
      let body_lines = [];
      for (let i = 0; i < lines.length; i++) {
        let st = lines[i].trim();
        if (i === 0 && st === "---") { in_yaml = true; continue; }
        if (in_yaml) { if (st === "---") in_yaml = false; continue; }
        if (st.startsWith("```")) { in_code = !in_code; continue; }
        if (!in_code) body_lines.push(lines[i]);
      }
      let body = body_lines.join("\n");

      let cite_re = /@([A-Za-z0-9][A-Za-z0-9_.:-]{1,80})/g;
      let m = null;
      for (let iter = 0; (m = cite_re.exec(body)) !== null && iter < 10000; iter++) {
        let key_low = m[1].replace(/[.,;:]+$/, "").toLowerCase();
        if (bib_set.has(key_low)) {
          cite_counts.set(key_low, (cite_counts.get(key_low) || 0) + 1);
          total_cites++;
        }
      }

      let distinct_cited = cite_counts.size;
      let utilisation = (bib_keys.length > 0) ? (distinct_cited/bib_keys.length) : 0;
      let sorted_counts = Array.from(cite_counts.entries()).sort(function (arg0_a, arg1_b) {
        return arg1_b[1] - arg0_a[1];
      });
      let top1_share = (total_cites > 0 && sorted_counts.length > 0) ? (sorted_counts[0][1]/total_cites) : 0;
      let top3_sum = 0;
      for (let i = 0; i < Math.min(3, sorted_counts.length); i++) top3_sum += sorted_counts[i][1];
      let top3_share = (total_cites > 0) ? (top3_sum/total_cites) : 0;

      if (distinct_cited < Math.min(min_distinct, bib_keys.length))
        errors.push(`[${label}] [SOURCE_CONCENTRATION] Only ${distinct_cited} distinct .bib keys cited in prose (< ${min_distinct} minimum).`);
      if (bib_keys.length >= 10 && utilisation < min_util)
        errors.push(`[${label}] [SOURCE_CONCENTRATION] Bibliography utilisation is ${distinct_cited}/${bib_keys.length} (${(utilisation*100).toFixed(1)}% < ${(min_util*100).toFixed(0)}% floor; avoid uncited padding in .bib).`);
      if (total_cites >= 15 && top1_share > max_single)
        errors.push(`[${label}] [SOURCE_CONCENTRATION] Single source \`@${sorted_counts[0][0]}\` accounts for ${sorted_counts[0][1]}/${total_cites} (${(top1_share*100).toFixed(1)}% > ${(max_single*100).toFixed(0)}% cap) of in-text citations.`);
      if (total_cites >= 15 && top3_share > max_top3)
        errors.push(`[${label}] [SOURCE_CONCENTRATION] Top-3 sources (${sorted_counts.slice(0, 3).map(function (arg0_x) { return "@" + arg0_x[0]; }).join(", ")}) account for ${top3_sum}/${total_cites} (${(top3_share*100).toFixed(1)}% > ${(max_top3*100).toFixed(0)}% cap) of in-text citations.`);

      //Return statement
      return {
        distinct_cited: distinct_cited,
        max_single_share: Number(top1_share.toFixed(4)),
        top3_share: Number(top3_share.toFixed(4)),
        total_cites: total_cites,
        utilisation: Number(utilisation.toFixed(4))
      };
    },

    /**
     * Audits a chapter directory or an entire Viscount macro-project directory.
     * @alias rmd_and_bib_auditor.auditTarget
     *
     * @param {string} arg0_target_path
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    auditTarget (arg0_target_path, arg1_options) {
      //Convert from parameters
      let opts = (arg1_options) ? arg1_options : {};
      let mode = opts.mode || "auto";
      let target_abs = path.resolve(arg0_target_path);

      //Guard clauses
      if (!fs.existsSync(target_abs) || !fs.statSync(target_abs).isDirectory())
        return { chapters: [], errors: [`Target directory does not exist: ${arg0_target_path}`], root: null, success: false, warnings: [] };

      //Declare local instance variables
      let all_errors = [];
      let all_warnings = [];
      let chapter_dirs = this.detectChapterDirs(target_abs, mode);
      let chapter_reports = [];
      let svea_root = viscount_audit_utils.findSveaRoot(target_abs);
      let profiles = viscount_audit_utils.loadSkillProfiles(svea_root);

      //Function body
      // Gather all compiled PDFs across root + chapters for ONE single batched PyMuPDF probe
      let all_pdf_paths = [];
      let root_pdf = path.join(target_abs, "studies_on_population.pdf");
      if (fs.existsSync(root_pdf)) all_pdf_paths.push(root_pdf);
      for (let i = 0; i < chapter_dirs.length; i++) {
        let cfiles = fs.readdirSync(chapter_dirs[i]).sort();
        for (let x = 0; x < cfiles.length; x++) {
          if (cfiles[x].toLowerCase().endsWith(".pdf"))
            all_pdf_paths.push(path.join(chapter_dirs[i], cfiles[x]));
        }
      }
      let pdf_probes = this.runBatchedPdfProbe(all_pdf_paths, all_warnings);

      let is_project_mode = !(chapter_dirs.length === 1 && path.resolve(chapter_dirs[0]) === target_abs);
      let root_rmd = path.join(target_abs, "studies_on_population.Rmd");
      let root_metrics = null;
      if (is_project_mode && fs.existsSync(root_rmd)) {
        let root_lines = fs.readFileSync(root_rmd, "utf8").split(/\r?\n/).length;
        if (root_lines < 450)
          all_errors.push(`[root] studies_on_population.Rmd has ${root_lines} lines (< 450 anti-stub line floor).`);
        let root_pdf_info = fs.existsSync(root_pdf) ?
          this.evaluatePdfProbe(root_pdf, pdf_probes[path.resolve(root_pdf)], "root", all_errors, all_warnings) : null;
        root_metrics = { lines: root_lines, pdf: root_pdf_info };
        let require_vis_root = Boolean(opts.require_visual_check);
        this.auditFigureAndPdfFreshness(target_abs, target_abs, "root", require_vis_root, all_errors, all_warnings);
        let root_fig_dir = path.join(target_abs, "figures");
        if (fs.existsSync(root_fig_dir) && fs.readdirSync(root_fig_dir).some(function (arg0_f) { return arg0_f.toLowerCase().endsWith(".png"); }))
          this.auditVisualCheckManifest(target_abs, "root", require_vis_root, all_errors, all_warnings);
      }

      if (chapter_dirs.length === 0)
        all_errors.push(`No Viscount chapter directories containing .Rmd files found under ${arg0_target_path}.`);

      let ch_opts = Object.assign({}, opts, { svea_root: svea_root });
      for (let i = 0; i < chapter_dirs.length; i++) {
        let r = this.auditChapterDir(chapter_dirs[i], target_abs, ch_opts, pdf_probes);
        chapter_reports.push(r.metrics);
        for (let x = 0; x < r.errors.length; x++) all_errors.push(r.errors[x]);
        for (let x = 0; x < r.warnings.length; x++) all_warnings.push(r.warnings[x]);
      }

      // Project-level Zenodo cap & per-jurisdiction historical demography literature check
      if (is_project_mode && chapter_dirs.length > 0) {
        let caps = (profiles && profiles.provenance_caps) ? profiles.provenance_caps : {};
        let max_zen_proj = Number(caps.max_zenodo_bib_ratio_project || 0.10);
        let proj_bib_text = [];
        let proj_paper_names = [];
        let total_proj_bib = 0;
        let total_proj_zen = 0;

        let all_bibs = [];
        let root_bib = path.join(target_abs, "studies_on_population.bib");
        if (fs.existsSync(root_bib)) all_bibs.push(root_bib);
        for (let i = 0; i < chapter_dirs.length; i++) {
          let cf = fs.readdirSync(chapter_dirs[i]).sort();
          for (let x = 0; x < cf.length; x++) {
            if (cf[x].toLowerCase().endsWith(".bib") && cf[x].toLowerCase() !== "intellte-sample.bib")
              all_bibs.push(path.join(chapter_dirs[i], cf[x]));
          }
          let p_d = path.join(chapter_dirs[i], "papers");
          if (fs.existsSync(p_d) && fs.statSync(p_d).isDirectory()) {
            let pnames = fs.readdirSync(p_d);
            for (let x = 0; x < pnames.length; x++) proj_paper_names.push(pnames[x]);
          }
        }

        for (let i = 0; i < all_bibs.length; i++) {
          let b_txt = fs.readFileSync(all_bibs[i], "utf8");
          proj_bib_text.push(b_txt);
          if (path.basename(all_bibs[i]).toLowerCase() === "studies_on_population.bib") {
            let ents = b_txt.split(/^\s*@[A-Za-z]+\s*\{/m).slice(1);
            total_proj_bib = ents.length;
            for (let x = 0; x < ents.length; x++) {
              if (this.ZENODO_BIB_RE.test(ents[x])) total_proj_zen++;
            }
          }
        }
        if (total_proj_bib > 0 && (total_proj_zen/total_proj_bib) > max_zen_proj)
          all_errors.push(`[root] [BIB_DIVERSITY] Project-wide Zenodo citation share is ${total_proj_zen}/${total_proj_bib} (${(100.0*total_proj_zen/total_proj_bib).toFixed(1)}% > ${(max_zen_proj*100).toFixed(0)}% ceiling).`);

        let proj_key = path.basename(target_abs).toUpperCase();
        let j_matrix = (profiles && profiles.jurisdiction_source_matrix) ? profiles.jurisdiction_source_matrix[proj_key] : null;
        if (j_matrix && Array.isArray(j_matrix.required_jurisdictions)) {
          let corpus_blob = (proj_bib_text.join("\n") + "\n" + proj_paper_names.join("\n")).toLowerCase();
          let stop_toks = new Set(["incl", "excl", "main", "south", "north", "east", "west", "associated", "territories", "provinces", "archipelago"]);
          for (let i = 0; i < j_matrix.required_jurisdictions.length; i++) {
            let j_item = j_matrix.required_jurisdictions[i];
            let toks = String(j_item.label || "").toLowerCase().split(/[^a-z]+/).filter(function (arg0_t) {
              return arg0_t.length >= 4 && !stop_toks.has(arg0_t);
            });
            if (toks.length > 0 && !toks.some(function (arg0_t) { return corpus_blob.includes(arg0_t); }))
              all_errors.push(`[root] [JURISDICTION_LIT] Required jurisdiction \`${j_item.id}\` (${j_item.label}) has 0 matching historical demography references across project \`.bib\` / \`./papers/\`.`);
          }
        }
      }

      // In-process figure script audit (zero subprocess overhead)
      let fig_res = figure_scripts_auditor.auditTarget(target_abs);
      for (let i = 0; i < fig_res.errors.length; i++) all_errors.push(fig_res.errors[i]);
      for (let i = 0; i < fig_res.warnings.length; i++) all_warnings.push(fig_res.warnings[i]);

      //Return statement
      return {
        chapters: chapter_reports,
        errors: all_errors,
        root: root_metrics,
        success: all_errors.length === 0,
        warnings: all_warnings
      };
    },

    /**
     * Verifies `figures/visual_check.json` exists, is fresh, covers all PNGs and has unique >= 50-char notes.
     * @alias rmd_and_bib_auditor.auditVisualCheckManifest
     *
     * @param {string} arg0_chapter_dir
     * @param {string} arg1_label
     * @param {boolean} arg2_require_visual_check
     * @param {Array<string>} arg3_errors
     * @param {Array<string>} arg4_warnings
     */
    auditVisualCheckManifest (arg0_chapter_dir, arg1_label, arg2_require_visual_check, arg3_errors, arg4_warnings) {
      //Convert from parameters
      let chapter_dir = arg0_chapter_dir;
      let errors = arg3_errors;
      let label = arg1_label;
      let require_visual = Boolean(arg2_require_visual_check);
      let warnings = arg4_warnings;

      //Declare local instance variables
      let fig_dir = path.join(chapter_dir, "figures");
      let manifest_path = path.join(fig_dir, "visual_check.json");
      let pngs = (fs.existsSync(fig_dir) && fs.statSync(fig_dir).isDirectory()) ?
        fs.readdirSync(fig_dir).filter(function (arg0_f) { return arg0_f.toLowerCase().endsWith(".png"); })
          .map(function (arg0_f) { return path.join(fig_dir, arg0_f); }).sort() : [];

      //Guard clauses
      if (!fs.existsSync(manifest_path)) {
        let msg = `[${label}] Missing figures/visual_check.json inspection manifest.`;
        if (require_visual) errors.push(msg);
        else if (pngs.length > 0) warnings.push(msg);
        return;
      }

      //Function body
      let data = null;
      try {
        data = JSON.parse(fs.readFileSync(manifest_path, "utf8"));
      } catch (e) {
        errors.push(`[${label}] Invalid figures/visual_check.json: ${e.message}`);
        return;
      }

      let top_dict = (data && typeof data === "object" && !Array.isArray(data)) ? data : {};
      let entries = Array.isArray(data) ? data : (top_dict.figures || top_dict.panels || top_dict.checked || []);
      if (top_dict.approved === false)
        errors.push(`[${label}] figures/visual_check.json marks figures as not approved.`);
      if (!Array.isArray(entries) || entries.length === 0)
        errors.push(`[${label}] figures/visual_check.json contains no inspected figure entries.`);

      if (pngs.length > 0) {
        let newest_png_m = 0;
        for (let i = 0; i < pngs.length; i++) {
          let mt = fs.statSync(pngs[i]).mtimeMs;
          if (mt > newest_png_m) newest_png_m = mt;
        }
        if (fs.statSync(manifest_path).mtimeMs < newest_png_m)
          errors.push(`[${label}] figures/visual_check.json is stale (older than newest PNG in figures/); re-inspect rendered figures.`);
      }

      if (require_visual && pngs.length > 0) {
        let recorded = new Set();
        let dict_entries = [];
        for (let i = 0; i < entries.length; i++) {
          let ent = entries[i];
          if (ent && typeof ent === "object") {
            dict_entries.push(ent);
            let fn_e = String(ent.file || ent.panel || "").trim();
            if (fn_e) recorded.add(path.basename(fn_e));
          } else if (typeof ent === "string" && ent.trim()) {
            recorded.add(path.basename(ent.trim()));
          }
        }

        let missing_pngs = pngs.map(function (arg0_p) { return path.basename(arg0_p); })
          .filter(function (arg0_bn) { return !recorded.has(arg0_bn); });
        if (missing_pngs.length > 0)
          errors.push(`[${label}] figures/visual_check.json omits rendered PNG(s): ${JSON.stringify(missing_pngs.slice(0, 5))}.`);

        if (dict_entries.length < pngs.length) {
          errors.push(`[${label}] figures/visual_check.json must contain one dict entry per PNG (\`${dict_entries.length}\`/\`${pngs.length}\`) with unique figure-specific notes.`);
        } else {
          let notes_list = [];
          let short_notes = [];
          let unique_notes = new Set();
          for (let i = 0; i < dict_entries.length; i++) {
            let n = String(dict_entries[i].notes || "").trim();
            notes_list.push(n);
            unique_notes.add(n);
            if (n.length < 50) short_notes.push(String(dict_entries[i].file || "?"));
          }
          if (short_notes.length > 0)
            errors.push(`[${label}] figures/visual_check.json entries lack >= 50-char figure-specific visual notes: ${JSON.stringify(short_notes.slice(0, 5))}.`);
          else if (unique_notes.size < notes_list.length && notes_list.length >= 2)
            errors.push(`[${label}] figures/visual_check.json contains duplicate boilerplate \`notes\` across figures; write unique observations per PNG via \`read_file\`.`);

          let top_zero = top_dict.zero_occlusion_and_in_panel_bounds === true;
          let top_parity = top_dict.polaris_visual_parity === true;
          let missing_att = [];
          for (let i = 0; i < dict_entries.length; i++) {
            let fn_e = String(dict_entries[i].file || dict_entries[i].panel || "?");
            if (!top_zero && dict_entries[i].zero_occlusion_and_in_panel_bounds !== true)
              missing_att.push(`${fn_e}:zero_occlusion_and_in_panel_bounds`);
            if (!top_parity && dict_entries[i].polaris_visual_parity !== true)
              missing_att.push(`${fn_e}:polaris_visual_parity`);
          }
          if (missing_att.length > 0)
            errors.push(`[${label}] figures/visual_check.json missing required true attestation(s): ${JSON.stringify(missing_att.slice(0, 5))}.`);
        }
      }
    },

    /**
     * Rejects Zipf / rank-size regressions or plots constructed on `n < 25` settlements.
     * @alias rmd_and_bib_auditor.auditZipfSampleFloor
     *
     * @param {string} arg0_chapter_dir
     * @param {string} arg1_label
     * @param {Array<string>} arg2_errors
     */
    auditZipfSampleFloor (arg0_chapter_dir, arg1_label, arg2_errors) {
      //Convert from parameters
      let chapter_dir = arg0_chapter_dir;
      let errors = arg2_errors;
      let label = arg1_label;

      //Declare local instance variables
      let n_re = /(?:\bn\s*=\s*|nrow\s*\([^)]*\)\s*[<=-]*\s*|sample\s+of\s+)(\d+)\b|\b(\d+)\s+settlements?\b/gi;
      let zipf_re = /\b(?:zipf|rank[-_\s]*size)\b/i;

      //Function body
      let files = fs.readdirSync(chapter_dir).filter(function (arg0_f) {
        return /\.(?:rmd|r)$/i.test(arg0_f);
      }).sort();

      for (let i = 0; i < files.length; i++) {
        let lines = fs.readFileSync(path.join(chapter_dir, files[i]), "utf8").split(/\r?\n/);
        for (let idx = 0; idx < lines.length; idx++) {
          if (!zipf_re.test(lines[idx])) continue;
          let win = lines.slice(Math.max(0, idx - 4), Math.min(lines.length, idx + 5)).join(" ");
          n_re.lastIndex = 0;
          let m = null;
          for (let iter = 0; (m = n_re.exec(win)) !== null && iter < 10; iter++) {
            let n_val = Number(m[1] || m[2]);
            if (Number.isFinite(n_val) && n_val < 25)
              errors.push(`[${label}] ${files[i]} line ${idx + 1}: banned rank-size/Zipf analysis on small sample n=${n_val} (< 25).`);
          }
        }
      }
    },

    /**
     * Discovers Viscount sub-chapter directories inside `arg0_root_dir`.
     * @alias rmd_and_bib_auditor.detectChapterDirs
     *
     * @param {string} arg0_root_dir
     * @param {string} [arg1_mode="auto"]
     *
     * @returns {Array<string>}
     */
    detectChapterDirs (arg0_root_dir, arg1_mode) {
      //Convert from parameters
      let mode = arg1_mode || "auto";
      let root_dir = path.resolve(arg0_root_dir);

      //Guard clauses
      if (mode === "chapter") return [root_dir];

      //Function body
      if (mode === "auto") {
        let direct_rmds = fs.readdirSync(root_dir).filter(function (arg0_f) {
          return /_(?:settlements|literature_review|areal_masks_and_bins)\.rmd$/i.test(arg0_f);
        });
        if (direct_rmds.length > 0) return [root_dir];
      }

      let found = new Set();
      let rmds = viscount_audit_utils.walkFiles(root_dir, function (arg0_full, arg1_name) {
        return arg1_name.toLowerCase().endsWith(".rmd");
      }, this.SKIP_DIRS);
      for (let i = 0; i < rmds.length; i++) {
        let d = path.dirname(rmds[i]);
        if (path.resolve(d) !== root_dir) found.add(d);
      }

      //Return statement
      return Array.from(found).sort();
    },

    /**
     * Evaluates a single PDF's batched PyMuPDF probe result into errors/warnings.
     * @alias rmd_and_bib_auditor.evaluatePdfProbe
     *
     * @param {string} arg0_pdf_path
     * @param {Object|null} arg1_probe
     * @param {string} arg2_label
     * @param {Array<string>} arg3_errors
     * @param {Array<string>} arg4_warnings
     *
     * @returns {Object}
     */
    evaluatePdfProbe (arg0_pdf_path, arg1_probe, arg2_label, arg3_errors, arg4_warnings) {
      //Convert from parameters
      let errors = arg3_errors;
      let label = arg2_label;
      let pdf_name = path.basename(arg0_pdf_path);
      let probe = arg1_probe;
      let warnings = arg4_warnings;

      //Guard clauses
      if (!probe)
        return { deadspace_pages: 0, max_x1: null, mono_pages: 0, pages: 0, qq_hits: 0 };
      if (probe.error) {
        errors.push(`[${label}] Failed to open compiled PDF ${pdf_name}: ${probe.error}`);
        return { deadspace_pages: 0, max_x1: null, mono_pages: 0, pages: 0, qq_hits: 0 };
      }

      //Function body
      let has_code_blocks = this.rmdHasVisibleCodeBlocks(arg0_pdf_path);
      if (probe.is_blank_page1)
        errors.push(`[${label}] ${pdf_name} p.1: Page 1 appears nearly blank (${probe.p1_chars} chars); rescale hero figure <= 0,52\\textheight.`);

      let orph = Array.isArray(probe.page1_orphaned_headings) ? probe.page1_orphaned_headings : [];
      for (let i = 0; i < orph.length; i++)
        errors.push(`[${label}] ${pdf_name} p.1: Orphaned Page-1 heading \`${orph[i].text}\` (y=${orph[i].y0} pt) with only ${orph[i].body_lines_below} prose line(s) beneath it.`);

      let shal = Array.isArray(probe.page1_shallow_headings) ? probe.page1_shallow_headings : [];
      for (let i = 0; i < shal.length; i++)
        warnings.push(`[${label}] ${pdf_name} p.1: Shallow Page-1 heading \`${shal[i].text}\` (y=${shal[i].y0} pt) with only 2 prose lines beneath it.`);

      let qq_pages = Array.isArray(probe.qq_pages) ? probe.qq_pages : [];
      for (let i = 0; i < qq_pages.length; i++)
        errors.push(`[${label}] ${pdf_name} p.${qq_pages[i].page}: unresolved \`??\` token(s) (${qq_pages[i].count}).`);

      let mono_pages = Array.isArray(probe.mono_pages) ? probe.mono_pages : [];
      if (mono_pages.length > 0 && !has_code_blocks) {
        let is_legacy_sett = pdf_name.toLowerCase().endsWith("_settlements.pdf");
        if (is_legacy_sett && mono_pages.length === 1 && Number(probe.mono_single_page_spans || 0) <= 2)
          warnings.push(`[${label}] ${pdf_name} p.${mono_pages[0]}: minor legacy monospace font usage (${probe.mono_single_page_spans} span(s)).`);
        else
          errors.push(`[${label}] ${pdf_name}: unexpected monospace font on page(s) ${JSON.stringify(mono_pages)} (monospace is reserved strictly for code).`);
      }

      if (Number(probe.continued_banners || 0) > 0)
        errors.push(`[${label}] ${pdf_name}: found \`(Continued from previous page)\` on ${probe.continued_banners} page(s); leave \\endhead empty.`);

      let tofu = Number(probe.tofu_chars || 0);
      if (tofu >= 2)
        errors.push(`[${label}] ${pdf_name}: found ${tofu} missing-glyph/replacement (U+FFFD / .notdef) char(s); transliterate scripts cleanly.`);
      else if (tofu === 1)
        warnings.push(`[${label}] ${pdf_name}: found 1 .notdef glyph character; verify script romanisation.`);

      if (Number(probe.max_x1 || 0) > 540.5)
        errors.push(`[${label}] ${pdf_name}: horizontal margin overflow max_x1=${probe.max_x1} pt (> 540,5 pt).`);

      let ds_errs = Array.isArray(probe.deadspace_errors) ? probe.deadspace_errors : [];
      for (let i = 0; i < ds_errs.length; i++) {
        if (ds_errs[i].blank)
          errors.push(`[${label}] ${pdf_name} p.${ds_errs[i].page}: [DEADSPACE] blank interior page (0% vertical occupancy).`);
        else
          errors.push(`[${label}] ${pdf_name} p.${ds_errs[i].page}: [DEADSPACE] excessive interior page whitespace (occupancy=${ds_errs[i].occ_pct}% < 35% or max_gap=${ds_errs[i].max_gap_pct}% > 55%).`);
      }
      let ds_warns = Array.isArray(probe.deadspace_warnings) ? probe.deadspace_warnings : [];
      for (let i = 0; i < ds_warns.length; i++)
        warnings.push(`[${label}] ${pdf_name} p.${ds_warns[i].page}: elevated interior page deadspace (occupancy=${ds_warns[i].occ_pct}% < 48%).`);

      //Return statement
      return {
        deadspace_pages: ds_errs.length,
        max_x1: probe.max_x1,
        mono_pages: mono_pages.length,
        pages: probe.pages,
        qq_hits: probe.qq_hits
      };
    },

    /**
     * Returns true when a file exceeds 10240 bytes and contains a `%PDF-` header.
     * @alias rmd_and_bib_auditor.isValidPdfFile
     *
     * @param {string} arg0_pdf_path
     *
     * @returns {boolean}
     */
    isValidPdfFile (arg0_pdf_path) {
      //Function body
      try {
        let st = fs.statSync(arg0_pdf_path);
        if (st.size <= 10240) return false;
        let fd = fs.openSync(arg0_pdf_path, "r");
        let buf = Buffer.alloc(1024);
        let n = fs.readSync(fd, buf, 0, 1024, 0);
        fs.closeSync(fd);
        return buf.subarray(0, n).includes("%PDF-");
      } catch (e) {
        return false;
      }
    },

    /**
     * Parses `.bib` files in a chapter directory for unique keys, DOI/URL coverage, Zenodo/crowd counts and author/domain concentration.
     * @alias rmd_and_bib_auditor.parseChapterBibs
     *
     * @param {string} arg0_chapter_dir
     * @param {Array<string>|null} [arg1_bib_names]
     *
     * @returns {Object}
     */
    parseChapterBibs (arg0_chapter_dir, arg1_bib_names) {
      //Convert from parameters
      let bib_names = arg1_bib_names;
      let chapter_dir = arg0_chapter_dir;

      //Declare local instance variables
      let author_counts = new Map();
      let bib_files = [];
      let crowd_entries = 0;
      let domain_counts = new Map();
      let keys = new Set();
      let linked = 0;
      let total_entries = 0;
      let zenodo_entries = 0;

      //Function body
      if (Array.isArray(bib_names) && bib_names.length > 0) {
        for (let i = 0; i < bib_names.length; i++) {
          let p = path.join(chapter_dir, bib_names[i]);
          if (fs.existsSync(p)) bib_files.push(p);
        }
      } else {
        let all = fs.readdirSync(chapter_dir).sort();
        for (let i = 0; i < all.length; i++) {
          if (all[i].toLowerCase().endsWith(".bib") && all[i].toLowerCase() !== "intellte-sample.bib")
            bib_files.push(path.join(chapter_dir, all[i]));
        }
      }

      let link_re = /\b(?:doi|url)\s*=\s*[{"](?:10\.|https?:\/\/)/i;
      let author_re = /\bauthor\s*=\s*[{"]([^}"]+)/i;
      for (let i = 0; i < bib_files.length; i++) {
        let content = fs.readFileSync(bib_files[i], "utf8");
        let entries = content.split(/^\s*@[A-Za-z]+\s*\{/m).slice(1);
        for (let x = 0; x < entries.length; x++) {
          let ent = entries[x];
          let km = ent.match(/^\s*([^,\s]+)/);
          if (km) keys.add(km[1].trim());
          total_entries++;
          if (link_re.test(ent)) linked++;
          if (this.ZENODO_BIB_RE.test(ent)) zenodo_entries++;
          if (this.CROWD_BIB_RE.test(ent)) crowd_entries++;

          let dom = "";
          let pm = ent.match(this.PUBLISHER_FIELD_RE);
          if (pm) dom = pm[1].trim().toLowerCase().slice(0, 40);
          else {
            let um = ent.match(this.URL_HOST_RE);
            if (um) dom = um[1].trim().toLowerCase();
          }
          if (dom) domain_counts.set(dom, (domain_counts.get(dom) || 0) + 1);

          let am = ent.match(author_re);
          if (am) {
            let first = am[1].split(/\band\b/i)[0].replace(/[{}]/g, "").trim();
            let surname = first.includes(",") ? first.split(",")[0].trim().toLowerCase() :
              (first.split(/\s+/).pop() || "").toLowerCase();
            if (surname && surname.length >= 3)
              author_counts.set(surname, (author_counts.get(surname) || 0) + 1);
          }
        }
      }

      let top_author = "";
      let max_author_cnt = 0;
      author_counts.forEach(function (arg0_cnt, arg1_a) {
        if (arg0_cnt > max_author_cnt) { max_author_cnt = arg0_cnt; top_author = arg1_a; }
      });

      let top_domain = "";
      let max_domain_cnt = 0;
      domain_counts.forEach(function (arg0_cnt, arg1_d) {
        if (arg0_cnt > max_domain_cnt) { max_domain_cnt = arg0_cnt; top_domain = arg1_d; }
      });

      //Return statement
      return {
        bib_files: bib_files,
        crowd_entries: crowd_entries,
        keys: Array.from(keys).sort(),
        linked_entries: linked,
        max_author_share: total_entries > 0 ? max_author_cnt/total_entries : 0,
        max_domain_share: total_entries > 0 ? max_domain_cnt/total_entries : 0,
        publisher_domains: domain_counts.size,
        top_author: top_author,
        top_domain: top_domain,
        total_entries: total_entries,
        zenodo_entries: zenodo_entries
      };
    },

    /**
     * Parses CLI arguments.
     * @alias rmd_and_bib_auditor.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let out = {
        json: false,
        mode: "auto",
        require_compiled_pdfs: false,
        require_visual_check: false,
        target_dir: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok === "--mode" && i + 1 < argv.length) out.mode = argv[++i];
        else if (tok.startsWith("--mode=")) out.mode = tok.slice(7);
        else if (tok === "--require-visual-check") out.require_visual_check = true;
        else if (tok === "--require-compiled-pdfs") out.require_compiled_pdfs = true;
        else if (tok === "--json") out.json = true;
        else if (!tok.startsWith("--") && !out.target_dir) out.target_dir = tok;
      }

      //Return statement
      return out;
    },

    /**
     * Returns true if the sibling Rmd intentionally displays fenced code or echo=TRUE chunks.
     * @alias rmd_and_bib_auditor.rmdHasVisibleCodeBlocks
     *
     * @param {string} arg0_pdf_path
     *
     * @returns {boolean}
     */
    rmdHasVisibleCodeBlocks (arg0_pdf_path) {
      //Convert from parameters
      let stem = arg0_pdf_path.replace(/\.pdf$/i, "");

      //Declare local instance variables
      let rmd_path = fs.existsSync(stem + ".Rmd") ? (stem + ".Rmd") :
        (fs.existsSync(stem + ".rmd") ? (stem + ".rmd") : null);

      //Guard clauses
      if (!rmd_path) return false;

      //Function body
      let lines = fs.readFileSync(rmd_path, "utf8").split(/\r?\n/);
      let start_idx = 0;
      if (lines.length > 0 && lines[0].trim() === "---") {
        for (let i = 1; i < lines.length; i++) {
          if (lines[i].trim() === "---") { start_idx = i + 1; break; }
        }
      }

      let global_echo_false = false;
      let in_fence = false;
      let fence_header = "";
      let chunk_body = [];

      for (let idx = start_idx; idx < lines.length; idx++) {
        let stripped = lines[idx].trim();
        if (stripped.startsWith("```")) {
          if (!in_fence) {
            in_fence = true;
            fence_header = stripped.slice(3).trim();
            chunk_body = [];
          } else {
            let body_text = chunk_body.join("\n");
            if (body_text.includes("opts_chunk$set") && /echo\s*=\s*(?:FALSE|F)\b/.test(body_text))
              global_echo_false = true;
            if (body_text.includes("viscount_rmd_helpers.R"))
              global_echo_false = true;

            let has_nonempty = chunk_body.some(function (arg0_l) { return arg0_l.trim().length > 0; });
            if (!fence_header.startsWith("{=")) {
              let km = fence_header.match(/^\{\s*(?:r|python|bash|sh|stan|sql)\b([^}]*)\}/i);
              if (km) {
                let opts_str = km[1] || "";
                let is_hidden = /\b(?:include|echo)\s*=\s*(?:FALSE|F)\b/.test(opts_str);
                let is_explicit_echo = /\becho\s*=\s*(?:TRUE|T)\b/.test(opts_str);
                if ((is_explicit_echo || (!is_hidden && !global_echo_false)) && has_nonempty)
                  return true;
              } else if (has_nonempty) {
                return true;
              }
            }
            in_fence = false;
            fence_header = "";
            chunk_body = [];
          }
        } else if (in_fence) {
          chunk_body.push(lines[idx]);
        }
      }

      //Return statement
      return false;
    },

    /**
     * Runs `pdf_geometry_probe.py` once in a single batched process over all compiled PDFs.
     * @alias rmd_and_bib_auditor.runBatchedPdfProbe
     *
     * @param {Array<string>} arg0_pdf_paths
     * @param {Array<string>} arg1_warnings
     *
     * @returns {Object}
     */
    runBatchedPdfProbe (arg0_pdf_paths, arg1_warnings) {
      //Convert from parameters
      let pdf_paths = Array.isArray(arg0_pdf_paths) ? arg0_pdf_paths : [];
      let warnings = arg1_warnings;

      //Guard clauses
      if (pdf_paths.length === 0) return {};

      //Declare local instance variables
      let probe_script = path.join(__dirname, "pdf_geometry_probe.py");
      let tmp_manifest = path.join(os.tmpdir(), `viscount_pdf_probe_${process.pid}_${Date.now()}.json`);

      if (!fs.existsSync(probe_script)) {
        warnings.push(`[pdf_probe] Missing batched PyMuPDF probe script: ${probe_script}`);
        return {};
      }

      //Function body
      try {
        fs.writeFileSync(tmp_manifest, JSON.stringify(pdf_paths.map(function (arg0_p) { return path.resolve(arg0_p); })), "utf8");
        let res = child_process.spawnSync("python", [probe_script, "--manifest", tmp_manifest], {
          encoding: "utf8",
          maxBuffer: 32*1024*1024
        });
        if (res.status !== 0 || !res.stdout) {
          warnings.push(`[pdf_probe] PyMuPDF probe exited with status ${res.status}: ${(res.stderr || "").slice(0, 300)}`);
          return {};
        }
        return JSON.parse(res.stdout);
      } catch (e) {
        warnings.push(`[pdf_probe] Failed to execute batched PyMuPDF probe: ${e.message}`);
        return {};
      } finally {
        try {
          if (fs.existsSync(tmp_manifest)) fs.unlinkSync(tmp_manifest);
        } catch (e) {}
      }
    }
  };

  if (require.main === module) {
    let cli = rmd_and_bib_auditor.parseCliArgs(process.argv.slice(2));
    if (!cli.target_dir) {
      console.error("Usage: node audit_rmd_and_bib_calibre.js <target_dir> [--mode auto|chapter|project] [--require-visual-check] [--require-compiled-pdfs] [--json]");
      process.exit(2);
    }
    let res = rmd_and_bib_auditor.auditTarget(cli.target_dir, cli);
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
      console.log(`[audit_rmd_and_bib_calibre] ${cli.target_dir}: ${res.chapters.length} chapter(s), ${res.errors.length} error(s), ${res.warnings.length} warning(s).`);
    }
    process.exit(res.success ? 0 : 1);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { rmd_and_bib_auditor: rmd_and_bib_auditor };
  }
}
