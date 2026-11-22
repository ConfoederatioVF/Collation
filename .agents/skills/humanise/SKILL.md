---
name: humanise
description: Humanises a paper or piece of text, removing traces of AI writing.
---

This skill may be pointed at any piece of text, file, or a folder. The scope of the text to humanise is determined by the user or agent. If pointed at a folder, discover all files that the user/agent is asking to change first.

- See global rules: write in non-Oxford British English (EN-GB), with European decimal formatting (DE). Timezones should be GMT, spell out dates (i.e. 17 November 2025).

## Step 1. DO NOTs.

- Do not use technobabble.
- Do not use hyperbolic words, e.g. 'complete', 'empirical', 'validated', 'verified'. 
  - Ask if a caption or title sounds natural. Does this phrase sound human, or is it grandiose technobabble? If it's the latter, change it.
- Drop words that serve no purpose, especially from headers and titles. Keep document titles concise and matched to the assigned itinerary (`<= 78` characters / `<= 12` words for sub-chapters; root synthesis `"Studies on Population"`; subtitles `<= 95` characters), avoiding bloated formulaic prefixes (`"Demographic Trajectory of..."`, `"Studies on Population across..."`).
- Do not overuse LaTeX in body prose; reserve `$...$` and `$$...$$` purely for equations or expressions. However, inside Matplotlib figures, axis labels, titles and legends, mathematical parameters, Greek symbols and exponents MUST be properly rendered with Matplotlib MathText (`$\nu = 3/2$`, `$\tau_1 = 1{,}41$`, `$R^2$`, `$\log_{10}$`, wrapping European decimal commas in braces `{,}`) rather than ugly raw ASCII (`nu = 3/2`, `tau1=1,41`, `Pseudo R-squared`, `log10(`). Figure plots must preserve Matplotlib's default sans-serif theme (`plt.rcdefaults()`, `DejaVu Sans`, 4-sided axes frame), format decimal axis ticks with European commas (`0,75`, not `0.75`), never display scientific notation (`10^4`, `1e5`) or raw `log10` exponents on real-world counts (sites, inhabitants, settlements or densities — write plain numbers or semantic suffixes `k`, `M`, `B`), never use technobabble titles (`Non-Stationary Matérn Residual Kriging Fit Summary`) and never apply `.replace('_', ' ').title()` to raw schema keys (which corrupts Roman numerals into `Pueblo Iii` or `Pueblo Ii`).
- Do not overuse bullet points. Bullet points should be reserved for lists.
- Do not place a space between /, i.e. ' / '. Humans do not write this way.
- Do not use em dashes, use hyphens instead.
- Do not use trailing zeroes in numbers unless needed (i.e. 15:00GMT; here trailing zeroes are needed, but not in 42,000, the number forty-two. Here it is merely confusing). 
  - A preference is generally held for two decimal places at most (i.e. 48,72) to not confuse Americans, but this can be exceeded if needed for accuracy.
  - If a unit is not explicitly an order of magnitude (i.e. 'Coal (in thousands of tonnes)'), or needed for coding purposes, then the abbreviation should default to the higher order of magnitude possible. Instead of '2.040k', write '2,04M'.

## Step 2. Formatting Rules.

- Do not overuse bold.
- Monospace must be reserved STRICTLY for code blocks only (forbid inline backticks outside evaluated template/knitr calls such as `` `r ...` ``, `\texttt{}`, `\verb` or `<code>` around numbers, units (`km²`), dates (`10000BC`), sample sizes (`n=18`), place names, dataset/project names or table cells). Never leak JSON schema field names (`other_names`, `coords`, `positive integer population series`), raw `snake_case` folder/variable tokens, or database boilerplate into academic prose, headings, captions or table headers.
- Refer to named projects barefoot (`POLARIS`, `CENTAUR`) rather than padding with `"the <PROJECT> synthesis/framework/model"`.
- Never pair a spelled-out number with parenthetical sample counts in prose (`forty-five regions (n=45)` to `45 regions`; use `(t=n)` inside compact module tables if needed), write full-stop European thousands separators (`110.642`), and never use scientific notation (`10^4`, `1e5`) for real-world counts (sites, inhabitants, settlements or densities) in tables or figures.
- Use non-Oxford British orthography consistently, including `mediaeval` rather than US `medieval`.
- Omit `AD` on modern calendar month-year dates (`March 1953`, never `March 1953AD`).
- Avoid compound decorator colour adjectives (`warm gold` -> `gold`) and vague conflict or demographic euphemisms in headings, legends and prose.
- **Zero Prose-Rewriting Scripts**: Never run Python or regex scripts to draft, rewrite or mechanically "humanise" prose. Prose editing MUST be performed by a read/edit-only model (`read_file` + `edit_file` only) followed by reading the compiled output.
- Where a term is from a foreign language, and you are introducing it for the first time, place it in italics at discretion, transliterating non-Latin scripts cleanly into Latin script with scholarly diacritics preserved.

- Captions for figures may not be more than two sentences as a general rule.
- Ensure figures are not squashed, stretched (`aspect="auto"` on maps) or overextended across empty ocean; draw spatial regions using crisp vector boundaries (`PatchCollection`) rather than pixelated categorical raster masks (reserving rasters strictly for continuous density/kriging surfaces and matrix heatmaps).
- Ensure tables and figures have zero occluded text, tick labels, suptitles, legends or labels, and that labels, callouts and bar values never cross outside their panel spines or figure bounds. Tune LaTeX float heights (`<= 0,42\textheight` for interior figures) and float fractions so compiled PDF pages contain zero excessive vertical deadspace (`>= 35%` interior page occupancy). Regenerate figures and recompile PDFs whenever upstream masks or data change, inspecting every figure individually via `read_file`.
- Instead of arrows (->), write 'to'.
- When sample sizes are relevant, provide it as (n=17) or n=19, not spelled out in prose.

Papers or reports should follow the top-level outline as follows. In such cases, you cannot have random top-level header titles, it has to be structured:
- Abstract (keep as a single undivided prose block with zero `##` sub-headings inside it; if a Page-1 cover figure leaves insufficient room for the title plus at least three opening lines, move `Abstract` onto Page 2 together with its opening paragraph so the heading is never orphaned alone at the bottom of Page 1)
- Background
- Methodology
- Testing and Validation (if applicable)
- Results
- Limitations (optional)
- Conclusion (optional)
- Appendix (optional)
- Sources
- Footnotes (optional)

## Step 3. Human References.

Your prose should be as human as possible. Examples of great academic writing on quantitative topics include McEvedy and Jones' Atlas of World Population History, and Durkheim's Suicide. You should write in the style of McEvedy, Durkheim, or Kees Klein Goldewijk of HYDE.