"""Builds CASTLE/studies_on_population.bib by deduplicating all 13 chapter .bib files and adding
canonical macro-synthesis references (allowed ONLY in the root synthesis monograph, never in sub-chapters).
"""

import pathlib
import re

CASTLE_DIR = pathlib.Path(__file__).resolve().parents[2]

SYNTHESIS_EXTRA = r"""
@book{McEvedyJones1978,
  author = {McEvedy, Colin and Jones, Richard},
  title = {{Atlas of World Population History}},
  publisher = {Penguin Books},
  year = {1978},
  url = {https://archive.org/details/atlasofworldpopu00mcev}
}

@article{KleinGoldewijk2017,
  author = {Klein Goldewijk, Kees and Beusen, Arthur and Doelman, Jonathan and Stehfest, Elke},
  title = {{Anthropogenic land use estimates for the Holocene -- HYDE 3.2}},
  journal = {Earth System Science Data},
  year = {2017},
  volume = {9},
  doi = {10.5194/essd-9-927-2017},
  url = {https://doi.org/10.5194/essd-9-927-2017}
}

@book{Maddison2001,
  author = {Maddison, Angus},
  title = {{The World Economy: A Millennial Perspective}},
  publisher = {OECD Development Centre},
  year = {2001},
  doi = {10.1787/9789264189980-en},
  url = {https://doi.org/10.1787/9789264189980-en}
}
"""


def main():
  seen_keys = set()
  entries = []
  for bib_p in sorted(CASTLE_DIR.rglob("*_literature_review.bib")):
    txt = bib_p.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n(?=@\w+\{)", txt.strip())
    for blk in blocks:
      m = re.match(r"@\w+\{([^,\s]+),", blk.strip())
      if not m:
        continue
      k = m.group(1)
      if k in seen_keys:
        continue
      seen_keys.add(k)
      entries.append(blk.strip())

  for blk in re.split(r"\n(?=@\w+\{)", SYNTHESIS_EXTRA.strip()):
    m = re.match(r"@\w+\{([^,\s]+),", blk.strip())
    if m and m.group(1) not in seen_keys:
      seen_keys.add(m.group(1))
      entries.append(blk.strip())

  out_p = CASTLE_DIR / "studies_on_population.bib"
  out_p.write_text("\n\n".join(entries) + "\n", encoding="utf-8")
  print(f"Wrote {out_p} with {len(entries)} unique BibTeX entries.")


if __name__ == "__main__":
  main()

