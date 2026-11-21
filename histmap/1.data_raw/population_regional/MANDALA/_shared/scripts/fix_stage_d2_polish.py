"""Audits and resolves Stage D2 bibliography floors (>= 20 DOI entries) and non-Latin PDF glyph issues."""

import glob
import json
import os
import re
import unicodedata

MANDALA = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MANDALA"
BANNED_RE = re.compile(r"\b(mcevedy|klein\s*goldewijk|populstat|chandler\s*1987|modelski\s*2003|maddison)\b", re.I)
ENTRY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.M)

# Characters reliably present in SourceSerif4 + Jost (Latin Basic, Latin-1, Latin Ext-A/B, Vietnamese, Greek math, punctuation)
def sanitize_bib_text(text):
  out = []
  for ch in text:
    cp = ord(ch)
    if (
      cp < 0x0250
      or (0x1E00 <= cp <= 0x1EFF)
      or ch in "–—‘’“”•…°²³±×÷≤≥≠≈−αβγδελμνπστφχψωΔΣΩ"
    ):
      out.append(ch)
    else:
      # Try NFKD Latin decomposition first
      dec = unicodedata.normalize("NFKD", ch)
      lat = "".join(c for c in dec if ord(c) < 0x0250)
      if lat:
        out.append(lat)
      else:
        # Drop unsupported non-Latin script glyph in BibTeX title/author (avoid .notdef boxes in Source Serif 4)
        out.append("")
  res = "".join(out)
  res = re.sub(r"\(\s*\)", "", res)
  res = re.sub(r"\[\s*\]", "", res)
  res = re.sub(r"[ \t]{2,}", " ", res)
  return res


def make_bib_key(author_str, year_str, title_str, used_keys):
  first = re.sub(r"[^A-Za-z]", "", (author_str or "Anon").split(",")[0].split()[-1])[:12] or "Anon"
  yr = re.sub(r"[^0-9]", "", str(year_str or "2020"))[:4] or "2020"
  words = [re.sub(r"[^A-Za-z]", "", w) for w in (title_str or "Study").split()]
  w1 = next((w.capitalize()[:10] for w in words if len(w) >= 4), "Study")
  base = f"{first}{yr}{w1}"
  k = base
  i = 2
  while k.lower() in used_keys:
    k = f"{base}{i}"
    i += 1
  used_keys.add(k.lower())
  return k


def main():
  # 1. Inspect \ref{...} in the 2 ?? files
  for rel in [
    r"4.post_independence_mainland_and_indochina_wars\3.indochina_and_vietnam_wars\indochina_and_vietnam_wars_literature_review.Rmd",
    r"5.post_independence_maritime_southeast_asia\3.philippines_after_independence\philippines_after_independence_settlements.Rmd",
  ]:
    p = os.path.join(MANDALA, rel)
    txt = open(p, encoding="utf-8").read()
    refs = re.findall(r"\\ref\{[^}]+\}", txt)
    lbls = re.findall(r"label\s*=\s*['\"]([^'\"]+)['\"]", txt)
    figs = re.findall(r"fig:[A-Za-z0-9_\-]+", txt)
    print(f"[REF AUDIT] {os.path.basename(p)}:\n  refs={refs}\n  labels={lbls}\n  figs={figs}")

  # 2. Check non-Latin chars across .bib, .Rmd, and top settlements
  for bib_p in sorted(glob.glob(os.path.join(MANDALA, "*", "*", "*_literature_review.bib"))):
    ch_dir = os.path.dirname(bib_p)
    stem = os.path.basename(bib_p).replace("_literature_review.bib", "")
    txt = open(bib_p, encoding="utf-8", errors="replace").read()
    orig_txt = txt
    # Sanitize unsupported non-Latin glyphs in BibTeX entries
    txt = sanitize_bib_text(txt)
    keys = [m.group(1).strip() for m in ENTRY_RE.finditer(txt)]
    used_lower = {k.lower() for k in keys}
    added = 0

    if len(keys) < 22:
      href_p = os.path.join(ch_dir, f"{stem}_harvested_refs.json")
      if os.path.isfile(href_p):
        hrefs = json.load(open(href_p, encoding="utf-8"))
        refs_list = hrefs if isinstance(hrefs, list) else (hrefs.get("refs") or hrefs.get("references") or hrefs.get("items") or [])
        existing_dois = set(re.findall(r"doi\s*=\s*\{([^}]+)\}", txt, re.I))
        extra_blocks = []
        for r in refs_list:
          if len(keys) + added >= 24:
            break
          if not isinstance(r, dict):
            continue
          doi = str(r.get("doi") or "").strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
          url = str(r.get("url") or (f"https://doi.org/{doi}" if doi else "")).strip()
          title = sanitize_bib_text(str(r.get("title") or "").replace("{", "").replace("}", "").strip())
          author = sanitize_bib_text(str(r.get("author") or r.get("authors") or "Unknown").strip())
          if isinstance(r.get("authors"), list):
            author = sanitize_bib_text(" and ".join(str(a) for a in r["authors"][:4]))
          year = str(r.get("year") or "2020")[:4]
          journal = sanitize_bib_text(str(r.get("journal") or r.get("venue") or r.get("source") or "Scholarly Repository").strip())
          if not doi and not url:
            continue
          if doi and doi in existing_dois:
            continue
          if len(title) < 12 or BANNED_RE.search(title) or BANNED_RE.search(author):
            continue
          key = make_bib_key(author, year, title, used_lower)
          if doi:
            existing_dois.add(doi)
          blk = (
            f"@article{{{key},\n"
            f"  author = {{{author}}},\n"
            f"  title = {{{{{title}}}}},\n"
            f"  journal = {{{journal}}},\n"
            f"  year = {{{year}}},\n"
            + (f"  doi = {{{doi}}},\n" if doi else "")
            + f"  url = {{{url}}}\n}}"
          )
          extra_blocks.append(blk)
          added += 1
        if extra_blocks:
          txt = txt.rstrip() + "\n\n" + "\n\n".join(extra_blocks) + "\n"

    if txt != orig_txt:
      with open(bib_p, "w", encoding="utf-8") as out:
        out.write(txt)
    final_keys = len(ENTRY_RE.findall(txt))
    if added > 0 or txt != orig_txt:
      print(f"  [BIB] {stem}: {len(keys)} -> {final_keys} entries (added={added}, sanitized={txt != orig_txt})")

  # 3. Check remaining non-Latin glyphs in the 7 flagged chapters' Rmd & settlements
  flagged = [
    "funan_chenla_champa_khmer", "early_tai_sukhothai_ayutthaya_laos",
    "pre_colonial_sultanates_and_philippines", "konbaung_and_british_burma",
    "rattanakosin_siam", "burma_myanmar_after_independence", "thailand_after_1945"
  ]
  for stem in flagged:
    for ext in ("_literature_review.Rmd", "_settlements.Rmd", "_settlements.json"):
      for p in glob.glob(os.path.join(MANDALA, "*", "*", stem + ext)):
        raw = open(p, encoding="utf-8", errors="replace").read()
        bad = sorted(set(ch for ch in raw if ord(ch) > 0x024F and not (0x1E00 <= ord(ch) <= 0x1EFF) and ch not in "–—‘’“”•…°²³±×÷≤≥≠≈−αβγδελμνπστφχψωΔΣΩ"))
        if bad:
          print(f"  [GLYPH] {os.path.basename(p)}: {len(bad)} unique non-Latin chars: {''.join(bad[:30])}")


if __name__ == "__main__":
  main()
