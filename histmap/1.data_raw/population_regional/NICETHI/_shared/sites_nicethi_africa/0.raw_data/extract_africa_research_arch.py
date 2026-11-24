"""Extract explicit georeferenced archaeological site coordinates from local Africa Research Files PDFs."""

import json
import os
import re
import numpy as np
from PIL import Image
import pymupdf

SVEA = r"f:\Active Projects\Project 1509 - SVEA"
ARCHIVE_ROOT = os.path.join(SVEA, "histmap", "1.data_raw", "population_regional", "_references", "Africa Research Files")
IDX_PATH = os.path.join(SVEA, "histmap", "1.data_raw", "population_regional", "NICETHI", "_shared", "africa_research_files_index.json")
MASK_PATH = os.path.join(SVEA, "histmap", "1.data_raw", "population_regional", "NICETHI", "_shared", "sites_nicethi_africa", "config", "nicethi_domain_mask.png")
OUT_PATH = os.path.join(SVEA, "histmap", "1.data_raw", "population_regional", "NICETHI", "_shared", "sites_nicethi_africa", "0.raw_data", "africa_research_files_arch_sites.json")

dm = np.asarray(Image.open(MASK_PATH).convert("RGBA"), dtype=np.uint8)
mask = (dm[:, :, 3] > 0) & (dm[:, :, :3].sum(axis=2) > 0)
H, W = mask.shape

def in_mask(la, lo):
    if not (-41.0 <= la <= 28.0 and -26.0 <= lo <= 73.0):
        return False
    r = min(H - 1, max(0, int((90.0 - la) * H / 180.0)))
    c = min(W - 1, max(0, int((lo + 180.0) * W / 360.0)))
    return bool(mask[r, c])

# Match DMS coordinate pairs like 13°54'12"N, 4°33'20"W or 13° 54' N / 4° 33' W or 14°21'N 16°12'W
DMS_RE = re.compile(
    r"(\d{1,2})\s*[°º]\s*(\d{1,2})\s*(?:['’′]\s*(?:(\d{1,2}(?:\.\d+)?)\s*(?:[\"”″]|'')?)?)?\s*([NS])\s*[,;/\s]+\s*"
    r"(\d{1,2})\s*[°º]\s*(\d{1,2})\s*(?:['’′]\s*(?:(\d{1,2}(?:\.\d+)?)\s*(?:[\"”″]|'')?)?)?\s*([EW])",
    re.IGNORECASE
)
# Also match N13°54' W4°33'
DMS_PRE_RE = re.compile(
    r"([NS])\s*(\d{1,2})\s*[°º]\s*(\d{1,2})(?:\s*['’′]\s*(\d{1,2}(?:\.\d+)?)?)?\s*[,;/\s]+\s*"
    r"([EW])\s*(\d{1,2})\s*[°º]\s*(\d{1,2})(?:\s*['’′]\s*(\d{1,2}(?:\.\d+)?)?)?",
    re.IGNORECASE
)

idx = json.load(open(IDX_PATH, "r", encoding="utf-8"))
items = idx if isinstance(idx, list) else (idx.get("files") or idx.get("entries") or [])
arch_pdfs = []
for it in items:
    rp = str(it.get("rel_path") or it.get("path") or "")
    if not rp.lower().endswith(".pdf"):
        continue
    l = rp.lower()
    if any(k in l for k in [
        "archaeolog", "radiocarbon", "excavat", "iron age", "neolithic", "megalith", "tumul",
        "mound", "tell", "nok", "tichitt", "jenne", "djenne", "zimbabwe", "mapungubwe",
        "kilwa", "swahili", "aksum", "axum", "meroe", "kerma", "nubia", "kush",
        "madagascar", "bantu", "stone circle", "ruin", "survey", "settlement", "prehistor",
        "cemetery", "burial", "pottery", "smelt", "furnace", "takrur", "walald", "gao", "dia", "timbuktu", "oyo", "ife", "benin", "begho", "bono", "gonja"
    ]):
        arch_pdfs.append(rp)

print(f"Scanning {len(arch_pdfs)} archaeological/settlement PDFs in Africa Research Files...", flush=True)
sites = []
seen = set()
pdfs_with_hits = 0

for rp in arch_pdfs:
    fp = os.path.join(ARCHIVE_ROOT, rp)
    if not os.path.exists(fp):
        continue
    try:
        doc = pymupdf.open(fp)
    except Exception:
        continue
    pdf_hits = 0
    max_pages = min(len(doc), 120)
    for pg_i in range(max_pages):
        try:
            txt = doc[pg_i].get_text("text") or ""
        except Exception:
            continue
        if "°" not in txt and "º" not in txt:
            continue
        for m in DMS_RE.finditer(txt):
            d1, m1, s1, ns, d2, m2, s2, ew = m.groups()
            la = int(d1) + int(m1) / 60.0 + (float(s1) / 3600.0 if s1 else 0.0)
            lo = int(d2) + int(m2) / 60.0 + (float(s2) / 3600.0 if s2 else 0.0)
            if int(m1) >= 60 or int(m2) >= 60:
                continue
            if ns.upper() == "S":
                la = -la
            if ew.upper() == "W":
                lo = -lo
            if not in_mask(la, lo):
                continue
            key = (round(la, 3), round(lo, 3))
            if key in seen:
                continue
            seen.add(key)
            ctx = txt[max(0, m.start() - 140):min(len(txt), m.end() + 140)].replace("\n", " ")
            sites.append({"lat": round(la, 5), "lon": round(lo, 5), "pdf": rp, "page": pg_i + 1, "context": ctx[:260]})
            pdf_hits += 1
        for m in DMS_PRE_RE.finditer(txt):
            ns, d1, m1, s1, ew, d2, m2, s2 = m.groups()
            if int(m1) >= 60 or int(m2) >= 60:
                continue
            la = int(d1) + int(m1) / 60.0 + (float(s1) / 3600.0 if s1 else 0.0)
            lo = int(d2) + int(m2) / 60.0 + (float(s2) / 3600.0 if s2 else 0.0)
            if ns.upper() == "S":
                la = -la
            if ew.upper() == "W":
                lo = -lo
            if not in_mask(la, lo):
                continue
            key = (round(la, 3), round(lo, 3))
            if key in seen:
                continue
            seen.add(key)
            ctx = txt[max(0, m.start() - 140):min(len(txt), m.end() + 140)].replace("\n", " ")
            sites.append({"lat": round(la, 5), "lon": round(lo, 5), "pdf": rp, "page": pg_i + 1, "context": ctx[:260]})
            pdf_hits += 1
    doc.close()
    if pdf_hits:
        pdfs_with_hits += 1

with open(OUT_PATH, "w", encoding="utf-8") as fh:
    json.dump({"pdf_scanned": len(arch_pdfs), "pdfs_with_hits": pdfs_with_hits, "site_count": len(sites), "sites": sites}, fh, indent=2, ensure_ascii=False)

print(f"[OK] Extracted {len(sites):,} unique archaeological coordinates from {pdfs_with_hits}/{len(arch_pdfs)} Africa Research Files PDFs.", flush=True)
