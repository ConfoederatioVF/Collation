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
- Drop words that serve no purpose, especially from headers.
- Do not overuse LaTeX in body prose; reserve `$...$` and `$$...$$` purely for equations or expressions. However, inside Matplotlib figures, axis labels, titles and legends, mathematical parameters, Greek symbols and exponents MUST be properly rendered with Matplotlib MathText (`$\nu = 3/2$`, `$\tau_1 = 1{,}41$`, `$R^2$`, `$\log_{10}$`, wrapping European decimal commas in braces `{,}`) rather than ugly raw ASCII (`nu = 3/2`, `tau1=1,41`, `Pseudo R-squared`, `log10(`). Figure plots must preserve Matplotlib's default sans-serif theme (`plt.rcdefaults()`, `DejaVu Sans`, 4-sided axes frame), format decimal axis ticks with European commas (`0,75`, not `0.75`), never use technobabble titles (`Non-Stationary Matérn Residual Kriging Fit Summary`) and never apply `.replace('_', ' ').title()` to raw schema keys (which corrupts Roman numerals into `Pueblo Iii` or `Pueblo Ii`).
- Do not overuse bullet points. Bullet points should be reserved for lists.
- Do not place a space between /, i.e. ' / '. Humans do not write this way.
- Do not use em dashes, use hyphens instead.
- Do not use trailing zeroes in numbers unless needed (i.e. 15:00GMT; here trailing zeroes are needed, but not in 42,000, the number forty-two. Here it is merely confusing). 
  - A preference is generally held for two decimal places at most (i.e. 48,72) to not confuse Americans, but this can be exceeded if needed for accuracy.
  - If a unit is not explicitly an order of magnitude (i.e. 'Coal (in thousands of tonnes)'), or needed for coding purposes, then the abbreviation should default to the higher order of magnitude possible. Instead of '2.040k', write '2,04M'.

## Step 2. Formatting Rules.

- Do not overuse bold.
- Monospace must be reserved for code only. Never leak JSON schema field names (`other_names`, `coords`, `positive integer population series`), raw `snake_case` folder/variable tokens, or database boilerplate into academic prose or table headers.
- Refer to named projects barefoot (`POLARIS`, `CENTAUR`) rather than padding with `"the <PROJECT> synthesis/framework/model"`.
- Never pair a spelled-out number with parenthetical sample counts in prose (`forty-five regions (n=45)` -> `45 regions`; use `(t=n)` inside compact module tables if needed), and write full-stop European thousands separators (`110.642`).
- Use non-Oxford British orthography consistently, including `mediaeval` rather than US `medieval`.
- Omit `AD` on modern calendar month-year dates (`March 1953`, never `March 1953AD`).
- Avoid compound decorator colour adjectives (`warm gold` -> `gold`) and vague conflict or demographic euphemisms in headings, legends and prose.
- **Zero Prose-Rewriting Scripts**: Never run Python or regex scripts to draft, rewrite or mechanically "humanise" prose. Prose editing MUST be performed by a read/edit-only model (`read_file` + `edit_file` only) followed by reading the compiled output.
- Where a term is from a foreign language, and you are introducing it for the first time, place it in italics at discretion, transliterating non-Latin scripts cleanly into Latin script with scholarly diacritics preserved.

- Captions for figures may not be more than two sentences as a general rule.
- Ensure figures are not squashed or distorted.
- Ensure tables do not have occluded text.
- Instead of arrows (->), write 'to'.
- When sample sizes are relevant, provide it as (n=17) or n=19, not spelled out in prose.

Papers or reports should follow the top-level outline as follows. In such cases, you cannot have random top-level header titles, it has to be structured:
- Abstract
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