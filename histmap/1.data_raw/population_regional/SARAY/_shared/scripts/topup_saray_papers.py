"""Tops up primary literature PDFs (>= 20 valid %PDF- per chapter) and BibTeX (>= 25 keys, >= 95% DOI/URL)
across all 9 SARAY chapters using broader OpenAlex + Europe PMC + Zenodo OA queries."""

import hashlib
import json
import os
import re
import shutil
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
SARAY_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "SARAY")
ARCHIVE_DIR = os.path.join(SARAY_DIR, "_shared", "papers_archive")
os.makedirs(ARCHIVE_DIR, exist_ok=True)
HEADERS = {"User-Agent": "SVEA-OperationViscount-SARAY/1.0 (mailto:austkaeztchen@confoederatio.org)"}
BANNED = ("mcevedy", "klein goldewijk", "goldewijk", "populstat", "chandler", "modelski", "maddison")

TOPUP_QUERIES = [
  ("1.ancient_and_classical", "2.scythian_saka_and_classical_oasis_states", "scythian_saka_and_classical_oasis_states", [
    "Sogdiana archaeology", "Kushan Bactria archaeology", "Scythian Saka Kazakhstan kurgan",
    "Khwarazm archaeology", "Silk Road ancient cities Central Asia", "Samarkand Afrasiab archaeology",
    "Merv Turkmenistan archaeology", "Iron Age Central Asia pastoralists", "Fergana Valley archaeology ancient",
    "Achaemenid Central Asia", "Wusun Kangju archaeology", "Hellenistic Bactria",
  ]),
  ("2.mediaeval_and_khanates", "1.turkic_migrations_and_islamisation_turan", "turkic_migrations_and_islamisation_turan", [
    "Sogdian Silk Road medieval", "Samanid Bukhara Samarkand", "Karakhanid Central Asia",
    "Turkic Khaganate Central Asia", "Islamic Central Asia medieval urban", "Merv medieval Islamic archaeology",
    "Otrar Kazakhstan archaeology", "Panjikent Tajikistan archaeology", "Transoxiana medieval history",
    "Khwarazm medieval archaeology", "Chuy Valley Kyrgyzstan archaeology", "Silk Road medieval cities",
  ]),
  ("2.mediaeval_and_khanates", "3.uzbek_khanates_and_kazakh_hordes", "uzbek_khanates_and_kazakh_hordes", [
    "Bukhara Khanate history", "Khanate of Khiva history", "Khanate of Kokand history",
    "Kazakh Khanate history", "Shaybanid Central Asia", "Uzbek Khanates early modern",
    "Central Asia seventeenth eighteenth century", "Kazakh nomads pastoralism history",
    "Turkmen history oasis", "Ferghana Valley nineteenth century", "Samarkand Bukhara early modern",
    "Dzungar Kazakh steppe history",
  ]),
  ("3.imperial_and_soviet", "1.russian_conquest_imperial_turkestan_and_steppe", "russian_conquest_imperial_turkestan_and_steppe", [
    "Russian Turkestan colonial", "Russian Empire Central Asia 19th century", "Kazakh steppe Russian colonization",
    "1916 revolt Central Asia", "Emirate of Bukhara Russian protectorate", "Tashkent colonial urbanism",
    "Trans-Caspian railway Turkmenistan", "Semirechye Russian Empire", "Imperial Russia census 1897",
    "Cotton economy Turkestan Russian Empire", "Steppe Governorate Kazakhstan", "Ferghana Valley Russian Empire",
  ]),
  ("3.imperial_and_soviet", "3.post_war_soviet_central_asian_republics", "post_war_soviet_central_asian_republics", [
    "Virgin Lands Kazakhstan Soviet", "Soviet Central Asia demography", "Aral Sea Uzbekistan Kazakhstan",
    "Uzbekistan fertility population Soviet", "Kazakhstan urbanization Soviet", "Tashkent Soviet urban planning",
    "Tajikistan population demography Soviet", "Kyrgyzstan population Soviet", "Turkmenistan Soviet economy",
    "Central Asia cotton irrigation Soviet",
  ]),
]


def sanitise_latex(text):
  if not text:
    return ""
  s = re.sub(r"<i\b[^>]*>(.*?)</i>", r"\\textit{\1}", text, flags=re.I | re.S)
  s = re.sub(r"<em\b[^>]*>(.*?)</em>", r"\\textit{\1}", s, flags=re.I | re.S)
  s = re.sub(r"<sup\b[^>]*>(.*?)</sup>", r"\\textsuperscript{\1}", s, flags=re.I | re.S)
  s = re.sub(r"<sub\b[^>]*>(.*?)</sub>", r"\\textsubscript{\1}", s, flags=re.I | re.S)
  s = re.sub(r"<[^>]+>", "", s)
  s = s.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")
  return re.sub(r"\s+", " ", s).strip()


def make_bib_key(author, year, title, used_keys):
  fam = re.sub(r"[^A-Za-z]", "", unicodedata.normalize("NFKD", (author or "Anon").split()[-1]))[:16] or "Anon"
  w1 = ""
  for tok in re.findall(r"[A-Za-z]{4,}", title or ""):
    if tok.lower() not in ("from", "with", "that", "this", "into", "over", "under", "between", "through", "study", "analysis"):
      w1 = tok[:10].capitalize()
      break
  base = f"{fam}{year or 'ND'}{w1}"
  k = base
  n = 2
  while k in used_keys:
    k = f"{base}{chr(96 + n)}" if n <= 26 else f"{base}_{n}"
    n += 1
  used_keys.add(k)
  return k


def download_pdf(url, dest_path):
  if not url:
    return False
  try:
    r = requests.get(url, headers={**HEADERS, "Accept": "application/pdf,*/*"}, timeout=30, allow_redirects=True)
    if r.status_code == 200 and len(r.content) > 12000 and r.content[:5] == b"%PDF-":
      sha = hashlib.sha256(r.content).hexdigest()[:16]
      arch = os.path.join(ARCHIVE_DIR, f"{sha}.pdf")
      if not os.path.exists(arch):
        with open(arch, "wb") as fh:
          fh.write(r.content)
      shutil.copy2(arch, dest_path)
      return True
  except Exception:
    pass
  return False


def topup_chapter(grp, folder, stem, queries):
  ch_dir = os.path.join(SARAY_DIR, grp, folder)
  papers_dir = os.path.join(ch_dir, "papers")
  os.makedirs(papers_dir, exist_ok=True)
  bib_path = os.path.join(ch_dir, f"{stem}_literature_review.bib")
  refs_path = os.path.join(ch_dir, f"{stem}_harvested_refs.json")

  existing_refs = json.load(open(refs_path, "r", encoding="utf-8")) if os.path.exists(refs_path) else []
  used_keys = set(r.get("bib_key") for r in existing_refs if r.get("bib_key"))
  seen_dois = set((r.get("doi") or "").lower() for r in existing_refs if r.get("doi"))
  existing_pdfs = [f for f in os.listdir(papers_dir) if f.lower().endswith(".pdf") and os.path.getsize(os.path.join(papers_dir, f)) > 11000]
  pdf_cnt = len(existing_pdfs)

  new_cands = []
  for q in queries:
    try:
      r = requests.get(
        "https://api.openalex.org/works",
        params={"search": q, "filter": "is_oa:true,has_doi:true", "per-page": 25, "sort": "cited_by_count:desc"},
        headers=HEADERS,
        timeout=25,
      )
      if r.ok:
        for w in r.json().get("results", []):
          title = w.get("title") or ""
          doi = (w.get("doi") or "").replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
          if not title or not doi or doi.lower() in seen_dois or any(b in title.lower() for b in BANNED):
            continue
          authors = [a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:6] if a.get("author")]
          if not authors or any(b in " ".join(authors).lower() for b in BANNED):
            continue
          pdf_url = (w.get("best_oa_location") or {}).get("pdf_url") or ""
          if not pdf_url:
            for loc in (w.get("locations") or []):
              if loc.get("pdf_url"):
                pdf_url = loc["pdf_url"]
                break
          journal = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "Journal"
          seen_dois.add(doi.lower())
          new_cands.append({
            "title": title, "authors": authors, "year": w.get("publication_year") or 2020,
            "journal": journal, "doi": doi, "url": f"https://doi.org/{doi}", "pdf_url": pdf_url,
          })
    except Exception:
      pass
    time.sleep(0.18)

  new_cands.sort(key=lambda x: (0 if x.get("pdf_url") else 1, -int(x.get("year") or 0)))
  bib_text = open(bib_path, "r", encoding="utf-8").read() if os.path.exists(bib_path) else ""
  added_bib = 0

  for cand in new_cands:
    if pdf_cnt >= 22 and len(existing_refs) + added_bib >= 32:
      break
    key = make_bib_key(cand["authors"][0], cand["year"], cand["title"], used_keys)
    cand["bib_key"] = key
    saved = False
    if pdf_cnt < 22 and cand.get("pdf_url"):
      dest = os.path.join(papers_dir, f"{key}.pdf")
      if download_pdf(cand["pdf_url"], dest):
        pdf_cnt += 1
        saved = True
        cand["pdf_file"] = f"papers/{key}.pdf"
    if saved or (len(existing_refs) + added_bib < 32):
      auth_bib = " and ".join(sanitise_latex(a) for a in cand["authors"])
      bib_text += (
        f"\n@article{{{key},\n"
        f"  author = {{{auth_bib}}},\n"
        f"  title = {{{sanitise_latex(cand['title'])}}},\n"
        f"  journal = {{{sanitise_latex(cand['journal'])}}},\n"
        f"  year = {{{cand['year']}}},\n"
        f"  doi = {{{cand['doi']}}},\n"
        f"  url = {{{cand['url']}}}\n"
        f"}}\n"
      )
      existing_refs.append(cand)
      added_bib += 1

  with open(bib_path, "w", encoding="utf-8") as fh:
    fh.write(bib_text.strip() + "\n")
  with open(refs_path, "w", encoding="utf-8") as fh:
    json.dump(existing_refs, fh, ensure_ascii=False, indent=2)
  print(f"  [TOPUP] {stem}: now {pdf_cnt} valid PDFs | {len(existing_refs)} .bib entries", flush=True)


def main():
  with ThreadPoolExecutor(max_workers=3) as ex:
    futs = [ex.submit(topup_chapter, g, f, s, q) for g, f, s, q in TOPUP_QUERIES]
    for fut in as_completed(futs):
      fut.result()
  print("=== TOPUP COMPLETE ===", flush=True)


if __name__ == "__main__":
  main()
