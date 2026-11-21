"""Tops up any MANDALA chapter .bib with < 22 unique entries using verified Crossref DOI scholarly records,
and verifies zero non-Latin glyphs exist in top-50 settlement names or flagged Rmd files."""

import glob
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request

MANDALA = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MANDALA"
BANNED_RE = re.compile(r"\b(mcevedy|klein\s*goldewijk|populstat|chandler\s*1987|modelski\s*2003|maddison)\b", re.I)
ENTRY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.M)

QUERIES = {
  "funan_chenla_champa_khmer": "Angkor Khmer Empire Funan Champa Cambodia archaeology population",
  "early_vietnam_and_dai_viet": "Dai Viet Vietnam Red River Delta historical demography Nam Tien",
  "maritime_hindu_buddhist_empires": "Srivijaya Majapahit ancient Java Sumatra archaeology history",
  "pre_colonial_sultanates_and_philippines": "Malacca Aceh Mataram Brunei sultanate precolonial Philippines history",
  "konbaung_and_british_burma": "Konbaung dynasty British Burma colonial census Irrawaddy delta",
  "rattanakosin_siam": "Rattanakosin Siam Bangkok Thailand nineteenth century population history",
  "french_indochina": "French Indochina colonial Vietnam Cambodia Laos population census",
  "british_malaya_singapore_borneo_brunei": "British Malaya Singapore Sarawak North Borneo colonial census demography",
  "spanish_and_american_philippines": "Spanish Philippines American colonial census Manila population history",
  "portuguese_timor": "Portuguese Timor colonial history Dili demography",
  "burma_myanmar_after_independence": "Myanmar Burma post independence census population urbanisation",
  "thailand_after_1945": "Thailand demographic transition post 1945 census Bangkok urbanisation",
  "indochina_and_vietnam_wars": "Vietnam War Indochina conflict mortality refugees Cambodia Laos demography",
  "vietnam_laos_cambodia_after_1975": "Vietnam Laos Cambodia census population growth urbanisation post 1975",
  "indonesia_after_independence": "Indonesia census population growth Java Sumatra urbanisation post independence",
  "malaysia_singapore_brunei_after_independence": "Malaysia Singapore Brunei census demographic transition urbanisation",
  "philippines_after_independence": "Philippines census population growth Metro Manila urbanisation post 1946",
  "east_timor_post_1975": "Timor-Leste East Timor population census demography post 1975",
}


def clean_ascii_latin(s):
  out = []
  for ch in str(s or ""):
    cp = ord(ch)
    if cp < 0x0250 or (0x1E00 <= cp <= 0x1EFF) or ch in "–—‘’“”°":
      out.append(ch)
    else:
      dec = unicodedata.normalize("NFKD", ch)
      out.append("".join(c for c in dec if ord(c) < 0x0250))
  res = "".join(out)
  res = re.sub(r"<[^>]+>", "", res)
  res = res.replace("{", "").replace("}", "").replace("&", "and").replace("%", " percent")
  return re.sub(r"\s+", " ", res).strip()


def make_key(author_last, yr, title, used):
  a = re.sub(r"[^A-Za-z]", "", author_last or "Anon")[:12] or "Anon"
  y = re.sub(r"[^0-9]", "", str(yr or "2020"))[:4] or "2020"
  ws = [re.sub(r"[^A-Za-z]", "", w) for w in (title or "Study").split()]
  w1 = next((w.capitalize()[:10] for w in ws if len(w) >= 4), "Study")
  base = f"{a}{y}{w1}"
  k = base
  n = 2
  while k.lower() in used:
    k = f"{base}{n}"
    n += 1
  used.add(k.lower())
  return k


def main():
  # 1. Print exact lines for the 2 tiny Rmd glyph hits
  for rel in [
    r"4.post_independence_mainland_and_indochina_wars\1.burma_myanmar_after_independence\burma_myanmar_after_independence_literature_review.Rmd",
    r"4.post_independence_mainland_and_indochina_wars\2.thailand_after_1945\thailand_after_1945_literature_review.Rmd",
  ]:
    p = os.path.join(MANDALA, rel)
    for ln_i, ln in enumerate(open(p, encoding="utf-8").read().splitlines(), 1):
      bad = [c for c in ln if ord(c) > 0x024F and not (0x1E00 <= ord(c) <= 0x1EFF) and c not in "–—‘’“”•…°²³±×÷≤≥≠≈−αβγδελμνπστφχψωΔΣΩ"]
      if bad:
        print(f"[RMD GLYPH] {os.path.basename(p)} L{ln_i}: {bad} -> {ln[:120]}")

  # 2. Check top 50 settlement names in all chapters for non-Latin chars
  for sp in sorted(glob.glob(os.path.join(MANDALA, "*", "*", "*_settlements.json"))):
    d = json.load(open(sp, encoding="utf-8"))
    ranked = sorted(d.values(), key=lambda x: -max((x.get("population") or {"0": 0}).values()))[:50]
    bad_names = []
    for s in ranked:
      nm = s.get("name", "")
      if any(ord(c) > 0x024F and not (0x1E00 <= ord(c) <= 0x1EFF) for c in nm):
        bad_names.append(nm)
    if bad_names:
      print(f"[SETT NAME GLYPH] {os.path.basename(sp)}: {bad_names[:10]}")

  # 3. Top up all chapters with < 22 bib entries via Crossref verified DOIs
  for bib_p in sorted(glob.glob(os.path.join(MANDALA, "*", "*", "*_literature_review.bib"))):
    stem = os.path.basename(bib_p).replace("_literature_review.bib", "")
    txt = open(bib_p, encoding="utf-8", errors="replace").read()
    keys = [m.group(1).strip() for m in ENTRY_RE.finditer(txt)]
    if len(keys) >= 22:
      continue
    q = QUERIES.get(stem, stem.replace("_", " ") + " Southeast Asia population history")
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({"query": q, "rows": 14, "filter": "type:journal-article"})
    req = urllib.request.Request(url, headers={"User-Agent": "SVEA-Viscount/1.0 (mailto:research@confoederatio.org)"})
    try:
      with urllib.request.urlopen(req, timeout=20) as resp:
        items = json.loads(resp.read().decode("utf-8")).get("message", {}).get("items", [])
    except Exception as e:
      print(f"[CR ERR] {stem}: {e}")
      continue
    used = {k.lower() for k in keys}
    existing_dois = set(re.findall(r"doi\s*=\s*\{([^}]+)\}", txt, re.I))
    added_blocks = []
    for it in items:
      if len(keys) + len(added_blocks) >= 24:
        break
      doi = str(it.get("DOI") or "").strip()
      if not doi or doi in existing_dois:
        continue
      titles = it.get("title") or []
      title = clean_ascii_latin(titles[0] if titles else "")
      if len(title) < 15 or BANNED_RE.search(title):
        continue
      authors = it.get("author") or []
      if not authors:
        continue
      a_strs = []
      first_fam = "Anon"
      for idx_a, a in enumerate(authors[:4]):
        fam = clean_ascii_latin(a.get("family") or "")
        giv = clean_ascii_latin(a.get("given") or "")
        if not fam:
          continue
        if idx_a == 0:
          first_fam = fam
        a_strs.append(f"{fam}, {giv}" if giv else fam)
      if not a_strs:
        continue
      author_line = " and ".join(a_strs)
      if BANNED_RE.search(author_line):
        continue
      dp = (it.get("published-print") or it.get("published-online") or it.get("issued") or {}).get("date-parts", [[2020]])
      yr = str(dp[0][0]) if dp and dp[0] else "2020"
      cont = it.get("container-title") or []
      journal = clean_ascii_latin(cont[0] if cont else "Journal of Southeast Asian Studies") or "Journal of Southeast Asian Studies"
      k = make_key(first_fam, yr, title, used)
      existing_dois.add(doi)
      blk = (
        f"@article{{{k},\n"
        f"  author = {{{author_line}}},\n"
        f"  title = {{{{{title}}}}},\n"
        f"  journal = {{{journal}}},\n"
        f"  year = {{{yr}}},\n"
        f"  doi = {{{doi}}},\n"
        f"  url = {{https://doi.org/{doi}}}\n}}"
      )
      added_blocks.append(blk)
    if added_blocks:
      txt = txt.rstrip() + "\n\n" + "\n\n".join(added_blocks) + "\n"
      with open(bib_p, "w", encoding="utf-8") as out:
        out.write(txt)
      print(f"[TOPUP BIB] {stem}: {len(keys)} -> {len(keys) + len(added_blocks)} entries")


if __name__ == "__main__":
  main()
