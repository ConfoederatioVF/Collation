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

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "ViscountPRETA/1.0 (mailto:research@confoederatio.org)"})

TARGETS = {
  "1.pre_columbian/2.western_amazon_basin": [
    "Amazonian dark earth",
    "Terra preta Amazon",
    "Pre-Columbian Amazonia",
    "Llanos de Moxos",
    "Southwestern Amazonia archaeology",
    "Upper Amazon archaeology",
    "Amazonian earthworks",
    "Amazonian archaeology radiocarbon",
    "Bolivian Amazon archaeology",
    "Ecuadorian Amazon archaeology",
  ],
  "3.post_independence/4.guianas_post_1815": [
    "French Guiana population",
    "Suriname population demography",
    "Guyana demography migration",
    "Guyane population",
    "Suriname census migration",
    "Guyana urban population",
  ],
}


def safe_fn(arg0_year, arg1_first_auth, arg2_title):
  a = re.sub(r"[^a-z0-9]+", "_", (arg1_first_auth or "anon").lower()).strip("_")[:18] or "anon"
  t = re.sub(r"[^a-z0-9]+", "_", (arg2_title or "paper").lower()).strip("_")[:44] or "paper"
  return f"{arg0_year}_{a}_{t}.pdf"


def is_valid_pdf(arg0_p):
  if not arg0_p.is_file() or arg0_p.stat().st_size <= 10240:
    return False
  with open(arg0_p, "rb") as f:
    return b"%PDF-" in f.read(1024)


def try_dl(arg0_url, arg1_dest):
  if not arg0_url:
    return False
  try:
    r = SESSION.get(arg0_url, timeout=18, allow_redirects=True, stream=True)
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


def search_openalex(arg0_q):
  out = []
  try:
    r = SESSION.get("https://api.openalex.org/works", params={
      "search": arg0_q, "filter": "is_oa:true", "per-page": 20, "mailto": "research@confoederatio.org"
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
        auths = [a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:4]]
        out.append({
          "title": w.get("display_name") or "",
          "year": w.get("publication_year") or 2020,
          "authors": [a for a in auths if a],
          "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
          "url": pdf,
          "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "",
        })
  except Exception:
    pass
  return out


def search_hal(arg0_q):
  out = []
  try:
    r = SESSION.get("https://api.archives-ouvertes.fr/search/", params={
      "q": arg0_q, "fq": "fileMain_s:[* TO *]",
      "fl": "title_s,authFullName_s,producedDateY_i,doiId_s,fileMain_s,journalTitle_s",
      "rows": 15, "wt": "json"
    }, timeout=15)
    if r.status_code == 200:
      for doc in r.json().get("response", {}).get("docs", []):
        pdf = doc.get("fileMain_s")
        if not pdf:
          continue
        t = doc.get("title_s")
        t = t[0] if isinstance(t, list) and t else str(t or "")
        out.append({
          "title": t,
          "year": int(doc.get("producedDateY_i") or 2020),
          "authors": doc.get("authFullName_s") or [],
          "doi": doc.get("doiId_s") or "",
          "url": pdf,
          "venue": doc.get("journalTitle_s") or "HAL Open Archive",
        })
  except Exception:
    pass
  return out


def search_epmc(arg0_q):
  out = []
  try:
    r = SESSION.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={
      "query": f"({arg0_q}) AND OPEN_ACCESS:y AND HAS_PDF:y",
      "format": "json", "pageSize": 15, "resultType": "core"
    }, timeout=15)
    if r.status_code == 200:
      for w in r.json().get("resultList", {}).get("result", []):
        pmcid = w.get("pmcid")
        if not pmcid:
          continue
        pdf = f"https://europepmc.org/articles/{pmcid}?pdf=render"
        auths = [a.get("fullName", "") for a in ((w.get("authorList") or {}).get("author") or [])[:4]]
        out.append({
          "title": w.get("title") or "",
          "year": int(w.get("pubYear") or 2020),
          "authors": [a for a in auths if a],
          "doi": w.get("doi") or "",
          "url": pdf,
          "venue": ((w.get("journalInfo") or {}).get("journal") or {}).get("title") or "Europe PMC",
        })
  except Exception:
    pass
  return out


for rel, queries in TARGETS.items():
  pdir = PRETA / rel / "papers"
  pdir.mkdir(parents=True, exist_ok=True)
  existing = [p for p in pdir.glob("*.pdf") if is_valid_pdf(p)]
  seen_titles = set()
  chap_list = cat.get(rel, [])
  print(f"[{rel}] start={len(existing)}/16", flush=True)
  for q in queries:
    if len(existing) >= 16:
      break
    cands = search_openalex(q) + search_hal(q) + search_epmc(q)
    for c in cands:
      if len(existing) >= 16:
        break
      t_norm = re.sub(r"\W+", "", c["title"].lower())[:40]
      if not t_norm or t_norm in seen_titles:
        continue
      seen_titles.add(t_norm)
      first_a = (c["authors"][0].split()[-1] if c["authors"] else "anon")
      dest = pdir / safe_fn(c["year"], first_a, c["title"])
      if dest.exists():
        continue
      if try_dl(c["url"], dest):
        existing.append(dest)
        c["local_pdf"] = dest.name
        chap_list.append(c)
        yr_s = c["year"]
        ti_s = c["title"][:64]
        kb = dest.stat().st_size // 1024
        print(f"  + [{len(existing):2d}/16] {yr_s} | {ti_s} ({kb} kB)", flush=True)
    time.sleep(0.25)
  cat[rel] = chap_list

CAT_PATH.write_text(json.dumps(cat, indent=2, ensure_ascii=False), encoding="utf-8")
print("DONE TOP-UP", flush=True)
