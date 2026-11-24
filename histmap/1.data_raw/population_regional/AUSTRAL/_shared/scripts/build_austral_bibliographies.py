"""Generates clean BibTeX files for all 16 Project AUSTRAL chapters and root studies_on_population.bib
strictly from the verified Wave-2 archival PDF & canonical monograph catalogs."""
import json
import os
import re

SVEA = r"f:\Active Projects\Project 1509 - SVEA"
AUS = os.path.join(SVEA, "histmap", "1.data_raw", "population_regional", "AUSTRAL")


def bib_escape (arg0_text):
  s = str(arg0_text or "").strip()
  s = re.sub(r"<[^>]+>", "", s)
  s = s.replace("\\", "")
  s = s.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")
  s = s.replace("{", "").replace("}", "")
  return s


def make_entry (arg0_item):
  etype = str(arg0_item.get("entry_type") or "article").strip().lower()
  if etype not in ("article", "book", "incollection", "inproceedings", "techreport", "misc", "phdthesis"):
    etype = "article"
  key = re.sub(r"[^A-Za-z0-9_:-]", "", str(arg0_item.get("cite_key") or ""))
  lines = [f"@{etype}{{{key},"]

  def add_f (arg0_name, arg1_val, arg2_raw=False):
    v = str(arg1_val or "").strip()
    if not v:
      return
    lines.append(f"  {arg0_name} = {{{v if arg2_raw else bib_escape(v)}}},")

  add_f("author", arg0_item.get("author") or "Unknown")
  add_f("title", arg0_item.get("title") or "Untitled")
  add_f("year", arg0_item.get("year") or "", True)
  if arg0_item.get("journal"):
    add_f("journal", arg0_item.get("journal"))
  if arg0_item.get("booktitle"):
    add_f("booktitle", arg0_item.get("booktitle"))
  if arg0_item.get("publisher"):
    add_f("publisher", arg0_item.get("publisher"))
  if arg0_item.get("volume"):
    add_f("volume", arg0_item.get("volume"), True)
  if arg0_item.get("number"):
    add_f("number", arg0_item.get("number"), True)
  if arg0_item.get("pages"):
    add_f("pages", arg0_item.get("pages"), True)
  if arg0_item.get("doi"):
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", str(arg0_item.get("doi")).strip())
    add_f("doi", doi, True)
  if arg0_item.get("url"):
    add_f("url", str(arg0_item.get("url")).strip(), True)
  lines.append("}")
  return "\n".join(lines)


def main ():
  itin = json.load(open(os.path.join(AUS, "austral_itinerary.json5"), encoding="utf-8"))
  root_entries = {}
  for ch in itin["chapters"]:
    ch_dir = os.path.join(AUS, ch["folder"])
    stem = ch["key"]
    cat_p = os.path.join(ch_dir, f"{stem}_wave2_bib_catalog.json")
    cat = json.load(open(cat_p, encoding="utf-8"))
    rows = cat if isinstance(cat, list) else (
      cat.get("entries") or cat.get("bibliography") or cat.get("items") or cat.get("works") or []
    )
    seen = set()
    blocks = []
    for item in rows:
      k = re.sub(r"[^A-Za-z0-9_:-]", "", str(item.get("cite_key") or ""))
      if not k or k in seen:
        continue
      seen.add(k)
      b = make_entry(item)
      blocks.append(b)
      if k not in root_entries and len(root_entries) < 96:
        root_entries[k] = b
    bib_p = os.path.join(ch_dir, f"{stem}.bib")
    with open(bib_p, "w", encoding="utf-8", newline="\n") as fh:
      fh.write("\n\n".join(blocks) + "\n")
    print(f"Ch {ch['index']:02d} {stem}.bib: {len(blocks)} keys")

  # Canonical global methodological references strictly restricted to root studies_on_population.bib
  root_entries["McEvedyJones1978"] = (
    "@book{McEvedyJones1978,\n"
    "  author = {McEvedy, Colin and Jones, Richard},\n"
    "  title = {Atlas of World Population History},\n"
    "  year = {1978},\n"
    "  publisher = {Penguin Books},\n"
    "  url = {https://archive.org/details/atlasofworldpopu0000mcev},\n"
    "}"
  )
  root_entries["KleinGoldewijk2017"] = (
    "@article{KleinGoldewijk2017,\n"
    "  author = {Klein Goldewijk, Kees and Beusen, Arthur and Doelman, Jonathan and Stehfest, Elke},\n"
    "  title = {Anthropogenic Land Use Estimates for the Holocene -- HYDE 3.2},\n"
    "  year = {2017},\n"
    "  journal = {Earth System Science Data},\n"
    "  volume = {9},\n"
    "  number = {2},\n"
    "  pages = {927--953},\n"
    "  doi = {10.5194/essd-9-927-2017},\n"
    "  url = {https://doi.org/10.5194/essd-9-927-2017},\n"
    "}"
  )
  root_entries["Kaplan2011"] = (
    "@article{Kaplan2011,\n"
    "  author = {Kaplan, Jed O. and Krumhardt, Kristen M. and Ellis, Erle C. and Ruddiman, William F. and Lemmen, Carsten and Klein Goldewijk, Kees},\n"
    "  title = {Holocene Carbon Emissions as a Result of Anthropogenic Land Cover Change},\n"
    "  year = {2011},\n"
    "  journal = {The Holocene},\n"
    "  volume = {21},\n"
    "  number = {5},\n"
    "  pages = {775--791},\n"
    "  doi = {10.1177/0959683610386983},\n"
    "  url = {https://doi.org/10.1177/0959683610386983},\n"
    "}"
  )
  root_entries["PaciorekSchervish2006"] = (
    "@article{PaciorekSchervish2006,\n"
    "  author = {Paciorek, Christopher J. and Schervish, Mark J.},\n"
    "  title = {Spatial Modelling Using a New Class of Nonstationary Covariance Functions},\n"
    "  year = {2006},\n"
    "  journal = {Environmetrics},\n"
    "  volume = {17},\n"
    "  number = {5},\n"
    "  pages = {483--506},\n"
    "  doi = {10.1002/env.785},\n"
    "  url = {https://doi.org/10.1002/env.785},\n"
    "}"
  )
  with open(os.path.join(AUS, "studies_on_population.bib"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n\n".join(root_entries.values()) + "\n")
  print(f"Root studies_on_population.bib: {len(root_entries)} keys")


if __name__ == "__main__":
  main()
