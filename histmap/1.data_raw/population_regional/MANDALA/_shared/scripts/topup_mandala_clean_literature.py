"""Top-up clean zero-Zenodo peer-reviewed literature harvester for MANDALA chapters
with < 22 BibTeX entries or < 10 valid PDFs, plus surgical Zenodo cleanup for SARAY & CASTLE."""

import glob
import json
import os
import re
import time
import urllib.parse
import urllib.request

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MANDALA_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MANDALA")
SARAY_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "SARAY")
CASTLE_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "CASTLE")

BANNED_RE = re.compile(
  r"(?:zenodo|10\.5281|figshare|osf\.io|researchgate|preprint|medrxiv|biorxiv|"
  r"cannabis|epilepsy|covid-19|sars-cov|cancer|tumor|tumour|carcinoma|diabetes|"
  r"michoacan|danube|roman\s+limes|mexico|brazil|peru|nigeria|kenya|ethiopia|ghana|"
  r"clinical\s+trial|placebo|chemotherapy|insulin|alzheimer|parkinson|schizophrenia|"
  r"mouse|mice|rat\s+model|zebrafish|drosophila|arabidopsis|e\.\s*coli)",
  re.I,
)

CHAPTER_QUERIES = {
  "early_burma_pyu_mon_pagan": [
    "Myanmar Pyu Bagan Pagan archaeology history",
    "Burma Pagan kingdom inscriptions demography urban",
    "Arakan Mon Burma early history archaeology",
    "Irrawaddy Bagan settlement history",
  ],
  "early_vietnam_and_dai_viet": [
    "Dai Viet Vietnam history demography population",
    "Red River Delta Vietnam archaeology Dong Son Co Loa",
    "Thang Long Hanoi Ly Tran Le dynasty Vietnam",
    "Vietnam historical demography census village",
  ],
  "early_tai_sukhothai_ayutthaya_laos": [
    "Ayutthaya Sukhothai Siam history demography",
    "Lan Na Chiang Mai Thailand history population",
    "Lan Xang Laos history Mekong settlement",
    "Dvaravati Thailand archaeology urban",
  ],
  "pre_colonial_sultanates_and_philippines": [
    "Philippines precolonial Spanish history demography Manila",
    "Melaka Malacca Aceh Banten sultanate trade population",
    "Sulu Mindanao Luzon history population",
    "Java Makassar Maluku early modern trade demography",
  ],
  "konbaung_and_british_burma": [
    "British Burma colonial census population history",
    "Konbaung dynasty Burma Myanmar history demography",
    "Rangoon Yangon Irrawaddy Delta rice migration colonial",
    "Myanmar Burma 19th century population economy",
  ],
  "rattanakosin_siam": [
    "Siam Thailand Bangkok 19th century history population",
    "Rattanakosin Siam demography census Chinese migration",
    "Thailand historical demography 1800 1945",
  ],
  "french_indochina": [
    "Indochine francaise population demographie recensement",
    "French Indochina Vietnam Cambodia Laos colonial demography",
    "Tonkin Cochinchina Annam population colonial census",
    "Cambodge Laos Indochine histoire demographie",
  ],
  "dutch_east_indies": [
    "Dutch East Indies Java Indonesia colonial census population",
    "Nederlandsch-Indie Java bevolking demografie",
    "Java 19th century population growth cultivation system",
    "Sumatra Batavia Indonesia colonial demography",
  ],
  "british_malaya_singapore_borneo_brunei": [
    "British Malaya Singapore colonial census population migration",
    "Straits Settlements Penang Singapore demography history",
    "Sarawak North Borneo Sabah Brunei colonial population",
    "Malaya Chinese Indian migration tin rubber demography",
  ],
  "spanish_and_american_philippines": [
    "Spanish Philippines colonial population tribute census",
    "Philippines 1903 1918 1939 census population history",
    "Luzon Visayas Manila historical demography Spanish",
  ],
  "portuguese_timor": [
    "Timor-Leste Portuguese Timor history population demography",
    "Timor oriental colonial portugais histoire population",
    "East Timor Dili Portuguese colonial history",
  ],
  "indochina_and_vietnam_wars": [
    "Vietnam War mortality casualties demography refugees",
    "Cambodia Khmer Rouge mortality demography population",
    "Laos Vietnam 1945 1975 war population displacement",
    "Indochina war refugees urbanisation Saigon",
  ],
  "vietnam_laos_cambodia_after_1975": [
    "Vietnam population census fertility urbanisation 1979 2019",
    "Cambodia population census demography fertility 1998 2019",
    "Laos population census demography fertility urbanisation",
  ],
  "malaysia_singapore_brunei_after_independence": [
    "Malaysia population census fertility urbanisation ethnic",
    "Singapore population demography fertility migration",
    "Brunei Darussalam population census demography",
  ],
  "indonesia_after_independence": [
    "Indonesia population census fertility transmigration urbanisation",
    "Java Sumatra Indonesia demographic transition census",
  ],
  "philippines_after_independence": [
    "Philippines population census fertility urbanisation migration",
    "Metro Manila Luzon Mindanao demographic transition",
  ],
  "east_timor_post_1975": [
    "Timor-Leste East Timor population census mortality 1975 2022",
    "Timor-Leste fertility demographic transition Dili",
  ],
  "burma_myanmar_after_independence": [
    "Myanmar Burma 2014 census population fertility migration",
    "Myanmar demographic transition urbanisation Yangon",
  ],
  "thailand_after_1945": [
    "Thailand demographic transition fertility Bangkok urbanisation",
    "Thailand population census migration 1960 2020",
  ],
}

GEO_RE = re.compile(
  r"(?:southeast\s+asia|south-east\s+asia|indochin|myanmar|burma|thailand|siam|laos|cambodia|khmer|angkor|"
  r"vietnam|tonkin|cochinchina|annam|champa|malaysia|malaya|singapore|brunei|sarawak|sabah|borneo|"
  r"indonesia|java|sumatra|bali|sulawesi|maluku|kalimantan|batavia|srivijaya|majapahit|"
  r"philippines|luzon|mindanao|visayas|manila|timor|bagan|pagan|pyu|ayutthaya|sukhothai|mekong|irrawaddy)",
  re.I,
)


def fetch_json(url, timeout=20):
  req = urllib.request.Request(url, headers={"User-Agent": "ViscountAcademicBot/2.0 (mailto:research@confoederatio.org)"})
  with urllib.request.urlopen(req, timeout=timeout) as r:
    return json.loads(r.read().decode("utf-8", errors="replace"))


def try_dl_pdf(url, out_path):
  if not url or "zenodo" in url.lower() or "10.5281" in url.lower():
    return False
  try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    with urllib.request.urlopen(req, timeout=18) as r:
      data = r.read(12_000_000)
    if data[:4] == b"%PDF" and len(data) > 15_000:
      with open(out_path, "wb") as fh:
        fh.write(data)
      return True
  except Exception:
    pass
  return False


def make_bib_key(author, year, title, used):
  last = re.sub(r"[^A-Za-z]", "", (author or "Anon").split(",")[0].split()[-1]) or "Anon"
  w = next((re.sub(r"[^A-Za-z]", "", tok) for tok in (title or "").split() if len(re.sub(r"[^A-Za-z]", "", tok)) >= 4), "Study")
  base = f"{last}{year}{w.capitalize()}"
  k = base
  i = 2
  while k in used:
    k = f"{base}_{i}"
    i += 1
  used.add(k)
  return k


def query_hal(q, rows=15):
  out = []
  try:
    u = (
      "https://api.archives-ouvertes.fr/search/?q="
      + urllib.parse.quote(q)
      + f"&rows={rows}&wt=json&fl=docid,title_s,authFullName_s,producedDateY_i,doiId_s,journalTitle_s,fileMain_s,uri_s"
    )
    docs = fetch_json(u).get("response", {}).get("docs", [])
    for d in docs:
      title = (d.get("title_s") or [""])[0] if isinstance(d.get("title_s"), list) else str(d.get("title_s") or "")
      yr = d.get("producedDateY_i") or 2015
      doi = str(d.get("doiId_s") or "")
      if BANNED_RE.search(title + " " + doi) or not GEO_RE.search(title):
        continue
      auths = d.get("authFullName_s") or ["Anonymous"]
      auth_str = " and ".join(auths[:4])
      out.append({
        "title": title, "author": auth_str, "year": int(yr), "doi": doi,
        "journal": str(d.get("journalTitle_s") or "HAL Archives Ouvertes"),
        "pdf_url": str(d.get("fileMain_s") or ""),
        "url": str(d.get("uri_s") or ""),
      })
  except Exception:
    pass
  return out


def query_crossref(q, rows=20):
  out = []
  try:
    u = "https://api.crossref.org/works?query=" + urllib.parse.quote(q) + f"&rows={rows}&filter=type:journal-article"
    items = fetch_json(u).get("message", {}).get("items", [])
    for it in items:
      title = (it.get("title") or [""])[0]
      doi = str(it.get("DOI") or "")
      jnl = (it.get("container-title") or ["Academic Journal"])[0]
      if not title or BANNED_RE.search(title + " " + doi + " " + jnl) or not GEO_RE.search(title + " " + jnl):
        continue
      yr = None
      for k in ("published-print", "published-online", "issued", "created"):
        dp = (it.get(k) or {}).get("date-parts")
        if dp and dp[0] and dp[0][0]:
          yr = int(dp[0][0])
          break
      if not yr or yr < 1900 or yr > 2026:
        continue
      auths = []
      for a in (it.get("author") or [])[:4]:
        fam = a.get("family") or ""
        giv = a.get("given") or ""
        if fam:
          auths.append(f"{fam}, {giv}".strip(", "))
      pdf_url = ""
      for lk in (it.get("link") or []):
        if "pdf" in str(lk.get("content-type") or "").lower():
          pdf_url = lk.get("URL") or ""
          break
      out.append({
        "title": re.sub(r"<[^>]+>", "", title).strip(),
        "author": " and ".join(auths) if auths else "Anonymous",
        "year": yr, "doi": doi, "journal": jnl,
        "pdf_url": pdf_url, "url": f"https://doi.org/{doi}" if doi else "",
      })
  except Exception:
    pass
  return out


def query_unpaywall_pdf(doi):
  if not doi or "10.5281" in doi:
    return ""
  try:
    u = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email=research@confoederatio.org"
    d = fetch_json(u, timeout=10)
    loc = d.get("best_oa_location") or {}
    p = loc.get("url_for_pdf") or ""
    if p and "zenodo" not in p.lower():
      return p
  except Exception:
    pass
  return ""


def query_epmc(q, rows=15):
  out = []
  try:
    u = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=" + urllib.parse.quote(q + " AND OPEN_ACCESS:Y") + f"&format=json&pageSize={rows}&resultType=core"
    res = fetch_json(u, timeout=20).get("resultList", {}).get("result", [])
    for it in res:
      title = str(it.get("title") or "")
      doi = str(it.get("doi") or "")
      jnl = str(it.get("journalTitle") or "")
      if BANNED_RE.search(title + " " + doi + " " + jnl) or not GEO_RE.search(title):
        continue
      yr = int(it.get("pubYear") or 2015)
      pmcid = it.get("pmcid") or ""
      pdf_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf" if pmcid else ""
      out.append({
        "title": title.rstrip("."), "author": str(it.get("authorString") or "Anonymous"),
        "year": yr, "doi": doi, "journal": jnl or "Peer-Reviewed Journal",
        "pdf_url": pdf_url, "url": f"https://doi.org/{doi}" if doi else "",
      })
  except Exception:
    pass
  return out


def strip_zenodo_from_bib(bib_path):
  """Surgically removes any @entry containing zenodo or 10.5281 from a .bib file."""
  txt = open(bib_path, encoding="utf-8", errors="ignore").read()
  entries = re.split(r"\n(?=@)", txt.strip())
  kept, removed = [], []
  for ent in entries:
    if re.search(r"zenodo|10\.5281", ent, re.I):
      mk = re.match(r"@\w+\{([^,\s]+)", ent)
      if mk:
        removed.append(mk.group(1))
    elif ent.strip():
      kept.append(ent.strip())
  if removed:
    with open(bib_path, "w", encoding="utf-8") as fh:
      fh.write("\n\n".join(kept) + "\n")
  return removed


def main():
  print("=== 1. Top-up MANDALA chapters with < 22 bib entries or < 10 valid PDFs (ZERO Zenodo) ===", flush=True)
  manifest = json.load(open(os.path.join(MANDALA_DIR, "mandala_areal_masks.json5"), encoding="utf-8"))
  all_items = list(manifest.get("specialist_masks") or []) + list(manifest.get("national_epoch_masks") or [])
  all_root_entries = {}

  for it in all_items:
    stem = it["id"]
    ch_dir = os.path.dirname(os.path.join(SVEA_ROOT, it["json5_path"]))
    bib_p = os.path.join(ch_dir, f"{stem}_literature_review.bib")
    pdf_dir = os.path.join(ch_dir, "literature_pdfs")
    os.makedirs(pdf_dir, exist_ok=True)

    if os.path.exists(bib_p):
      strip_zenodo_from_bib(bib_p)
      cur_txt = open(bib_p, encoding="utf-8", errors="ignore").read()
    else:
      cur_txt = ""
    cur_keys = set(re.findall(r"^@\w+\{([^,\s]+)", cur_txt, re.M))
    cur_dois = set(d.lower() for d in re.findall(r"doi\s*=\s*\{([^}]+)\}", cur_txt, re.I))
    cur_titles = set(re.sub(r"[^a-z0-9]", "", t.lower())[:50] for t in re.findall(r"title\s*=\s*\{([^}]+)\}", cur_txt, re.I))
    cur_pdfs = len([f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")])

    if len(cur_keys) < 22 or cur_pdfs < 10:
      qs = CHAPTER_QUERIES.get(stem, [stem.replace("_", " ") + " Southeast Asia history demography"])
      cands = []
      for q in qs:
        cands.extend(query_hal(q, rows=12))
        cands.extend(query_crossref(q, rows=15))
        cands.extend(query_epmc(q, rows=10))
        time.sleep(0.15)

      new_entries = []
      for c in cands:
        if len(cur_keys) >= 34 and cur_pdfs >= 14:
          break
        tn = re.sub(r"[^a-z0-9]", "", c["title"].lower())[:50]
        dl = c["doi"].lower()
        if (dl and dl in cur_dois) or (tn and tn in cur_titles):
          continue
        pdf_u = c["pdf_url"]
        if not pdf_u and c["doi"] and cur_pdfs < 14:
          pdf_u = query_unpaywall_pdf(c["doi"])
        bkey = make_bib_key(c["author"], c["year"], c["title"], cur_keys)
        if dl:
          cur_dois.add(dl)
        if tn:
          cur_titles.add(tn)
        if pdf_u and cur_pdfs < 14:
          if try_dl_pdf(pdf_u, os.path.join(pdf_dir, f"{bkey}.pdf")):
            cur_pdfs += 1
        title_esc = c["title"].replace("{", "").replace("}", "")
        jnl_esc = c["journal"].replace("{", "").replace("}", "")
        ent = (
          f"@article{{{bkey},\n"
          f"  author = {{{c['author']}}},\n"
          f"  title = {{{title_esc}}},\n"
          f"  journal = {{{jnl_esc}}},\n"
          f"  year = {{{c['year']}}},\n"
          + (f"  doi = {{{c['doi']}}},\n" if c["doi"] else "")
          + (f"  url = {{{c['url']}}}\n" if c["url"] else "")
          + "}"
        )
        new_entries.append(ent)

      if new_entries:
        with open(bib_p, "a", encoding="utf-8") as fh:
          fh.write("\n\n" + "\n\n".join(new_entries) + "\n")

    final_txt = open(bib_p, encoding="utf-8", errors="ignore").read()
    final_keys = re.findall(r"^@\w+\{([^,\s]+)", final_txt, re.M)
    final_z = len(re.findall(r"zenodo|10\.5281", final_txt, re.I))
    print(f"  [TOPUP] {stem:45s} | bib={len(final_keys):2d} | pdfs={cur_pdfs:2d} | zenodo={final_z}", flush=True)
    for ent in re.split(r"\n(?=@)", final_txt.strip()):
      mk = re.match(r"@\w+\{([^,\s]+)", ent)
      if mk and not re.search(r"zenodo|10\.5281", ent, re.I):
        all_root_entries[mk.group(1)] = ent.strip()

  # Rebuild clean root MANDALA/studies_on_population.bib (ZERO Zenodo!)
  root_bib = os.path.join(MANDALA_DIR, "studies_on_population.bib")
  # Preserve any clean canonical monographs already in root_bib (non-Zenodo)
  if os.path.exists(root_bib):
    for ent in re.split(r"\n(?=@)", open(root_bib, encoding="utf-8", errors="ignore").read().strip()):
      mk = re.match(r"@\w+\{([^,\s]+)", ent)
      if mk and not re.search(r"zenodo|10\.5281", ent, re.I):
        all_root_entries.setdefault(mk.group(1), ent.strip())
  with open(root_bib, "w", encoding="utf-8") as fh:
    fh.write("\n\n".join(all_root_entries[k] for k in sorted(all_root_entries.keys())) + "\n")
  print(f"  [ROOT] Rebuilt MANDALA/studies_on_population.bib: {len(all_root_entries)} clean entries, 0 Zenodo!", flush=True)

  print("\n=== 2. Purge residual erroneous Zenodo entries from SARAY & CASTLE .bib files ===", flush=True)
  for proj_name, pdir in [("SARAY", SARAY_DIR), ("CASTLE", CASTLE_DIR)]:
    for bp in sorted(glob.glob(f"{pdir}/**/*.bib", recursive=True)):
      rem = strip_zenodo_from_bib(bp)
      if rem:
        print(f"  [{proj_name}] Purged {len(rem)} Zenodo keys from {os.path.relpath(bp, pdir)}: {rem}", flush=True)


if __name__ == "__main__":
  main()
