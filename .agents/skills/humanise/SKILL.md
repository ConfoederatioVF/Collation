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
- Do not overuse LaTex. It should be reserved purely for equations or expressions.
- Do not overuse bullet points. Bullet points should be reserved for lists.
- Do not place a space between /, i.e. ' / '. Humans do not write this way.
- Do not use em dashes, use hyphens instead.
- Do not use trailing zeroes in numbers unless needed (i.e. 15:00GMT; here trailing zeroes are needed, but not in 42,000, the number forty-two. Here it is merely confusing). 
  - A preference is generally held for two decimal places at most (i.e. 48,72) to not confuse Americans, but this can be exceeded if needed for accuracy.
  - If a unit is not explicitly an order of magnitude (i.e. 'Coal (in thousands of tonnes)'), or needed for coding purposes, then the abbreviation should default to the higher order of magnitude possible. Instead of '2.040k', write '2,04M'.

## Step 2. Formatting Rules.

- Do not overuse bold.
- Monospace must be reserved for code only.
- Where a term is from a foreign language, and you are introducing it for the first time, place it in italics at discretion.

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