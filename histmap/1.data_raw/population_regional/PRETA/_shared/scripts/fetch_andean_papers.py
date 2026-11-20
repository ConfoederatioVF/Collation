"""Supplements PRETA Andean-adjacent chapters (`2.western_amazon_basin`,
`4.colonial_spanish_amazon`, `2.bolivia_after_independence`) with authoritative
open-access Peruvian, Bolivian and Central Andean archaeological, radiocarbon,
and historical demography PDFs from OpenAlex, Europe PMC, and HAL.
"""

import json
import pathlib
import re
import sys
import time
import requests

sys.stdout.reconfigure(encoding="utf-8")

PRETA = pathlib.Path(__file__).resolve().parents[2]
CAT_PATH = PRETA / "_shared/papers_archive/preta_papers_catalog.json"
cat = json.loads(CAT_PATH.read_text(encoding="utf-8")) if CAT_PATH.exists() else {}

S = requests.Session()
S.headers.update({"User-Agent": "ViscountPRETA/1.0 (mailto:research@confoederatio.org)"})

ANDEAN_TARGETS = {
  "1.pre_columbian/2.western_amazon_basin": [
    "Chachapoya archaeology Peru Kuelap",
    "Tiwanaku Lake Titicaca population archaeology",
    "Central Andes radiocarbon population demography Peru Bolivia",
    "Inca Qhapaq Nan settlement Peru Bolivia",
    "Andean Amazonian interaction Peru Ecuador Bolivia archaeology",
    "Bolivian Altiplano Formative archaeology Chiripa",
  ],
  "2.colonial/4.colonial_spanish_amazon": [
    "Andean colonial demography Peru epidemics population",
    "Potosi Charcas colonial population Bolivia demography",
    "Chachapoyas Moyobamba Maynas colonial Peru missions",
    "Andes Spanish conquest demographic collapse Peru",
    "Jesuit missions Moxos Chiquitos Maynas population",
  ],
  "3.post_independence/2.bolivia_after_independence": [
    "Bolivia Altiplano demography La Paz Potosi Cochabamba census",
    "Bolivia historical population urban Santa Cruz El Alto",
    "Tiwanaku Lake Titicaca Bolivia archaeology heritage",
    "Bolivia nineteenth twentieth century population census",
  ],
}


def safe_fn(arg0_yr, arg1_auth, arg2_title):
  a = re.sub(r"[^a-z0-9]+", "_", (arg1_auth or "anon").lower()).strip("_")[:18] or "anon"
  t = re.sub(r"[^a-z0-9]+", "_", (arg2_title or "paper").lower()).strip("_")[:42] or "paper"
  return f"{arg0_yr}_{a}_{t}.pdf"


def try_dl(arg0_url, arg1_dest):
  if not arg0_url:
    return False
  try:
    r = S.get(arg0_url, timeout=18, allow_redirects=True, stream=True)
    if r.status_code != 200:
      return False
    chunks = []
    tot = 0
    for ch in r.iter_content(65536):
      chunks.append(ch)
      tot += len(ch)
      if tot > 25 * 1024 * 1024:
        break
    data = b"".join(chunks)
    if len(data) <= 10240 or b"%PDF-" not in data[:1024]:
      return False
    arg1_dest.write_bytes(data)
    return True
  except Exception:
    return False


def search_oa(arg0_q):
  out = []
  try:
    r = S.get("https://api.openalex.org/works", params={
      "search": arg0_q, "filter": "is_oa:true", "per-page": 15, "mailto": "research@confoederatio.org"
    }, timeout=15)
    if r.status_code == 200:
      for w in r.json().get("results", []):
        pdf = None
        for loc in ([w.get("best_oa_location"), w.get("primary_location")] + (w.get("locations") or [])):
          if isinstance(loc, dict) and loc.get("pdf_url"):
            pdf = loc["pdf_url"]
            break
        if not pdf:
          continue
        title = w.get("display_name") or ""
        if not re.search(r"peru|bolivia|ande|tiwanaku|titicaca|inca|chachapoya|potos|charcas|amazon|moxos|maynas|cusco|cuzco|qhapaq|altiplano", title, re.I):
          continue
        auths = [a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:4]]
        out.append({
          "title": title,
          "year": w.get("publication_year") or 2020,
          "authors": [a for a in auths if a],
          "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
          "url": pdf,
          "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "",
        })
  except Exception:
    pass
  return out


def search_epmc(arg0_q):
  out = []
  try:
    r = S.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={
      "query": f"({arg0_q}) AND OPEN_ACCESS:y AND HAS_PDF:y",
      "format": "json", "pageSize": 12, "resultType": "core"
    }, timeout=15)
    if r.status_code == 200:
      for w in r.json().get("resultList", {}).get("result", []):
        pmcid = w.get("pmcid")
        title = w.get("title") or ""
        if not pmcid or not re.search(r"peru|bolivia|ande|tiwanaku|titicaca|inca|chachapoya|potos|charcas|amazon|moxos|maynas|cusco|cuzco|qhapaq|altiplano", title, re.I):
          continue
        auths = [a.get("fullName", "") for a in ((w.get("authorList") or {}).get("author") or [])[:4]]
        out.append({
          "title": title,
          "year": int(w.get("pubYear") or 2020),
          "authors": [a for a in auths if a],
          "doi": w.get("doi") or "",
          "url": f"https://europepmc.org/articles/{pmcid}?pdf=render",
          "venue": ((w.get("journalInfo") or {}).get("journal") or {}).get("title") or "Europe PMC",
        })
  except Exception:
    pass
  return out


for rel, queries in ANDEAN_TARGETS.items():
  pdir = PRETA / rel / "papers"
  pdir.mkdir(parents=True, exist_ok=True)
  chap_list = cat.get(rel, [])
  seen = {re.sub(r"\W+", "", str(x.get("title", "")).lower())[:40] for x in chap_list}
  added = 0
  print(f"[ANDEAN PDFs] {rel} (existing catalog={len(chap_list)})", flush=True)
  for q in queries:
    if added >= 10:
      break
    for c in search_oa(q) + search_epmc(q):
      if added >= 10:
        break
      tn = re.sub(r"\W+", "", c["title"].lower())[:40]
      if not tn or tn in seen:
        continue
      seen.add(tn)
      first_a = (c["authors"][0].split()[-1] if c["authors"] else "anon")
      dest = pdir / safe_fn(c["year"], first_a, c["title"])
      if dest.exists():
        continue
      if try_dl(c["url"], dest):
        added += 1
        c["local_pdf"] = dest.name
        chap_list.append(c)
        print(f"  + [{added:2d}/10] {c['year']} | {c['title'][:66]} ({dest.stat().st_size // 1024} kB)", flush=True)
    time.sleep(0.2)
  cat[rel] = chap_list

CAT_PATH.write_text(json.dumps(cat, indent=2, ensure_ascii=False), encoding="utf-8")
print("=== ANDEAN OA PDF SUPPLEMENT COMPLETE ===", flush=True)
