"""Master generator for Project MANDALA Toponymy Batches 001 to 008.

Slice: Batches 001 through 008 (Brunei, Cambodia, East Timor, Indonesia part 1).
"""

import json
import os
import re
import sys
from known_historical import KNOWN_HISTORICAL
from validate_batch import validate_resolved_batch

DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")

LATIN_ONLY_RE = re.compile(r"^[\u0020-\u007E\u00A0-\u024F\u1E00-\u1EFF\u2010-\u2027]+$")
CAMBODIA_ALLOWED_RE = re.compile(r"^[\u0020-\u007E\u00A0-\u024F\u1E00-\u1EFF\u1780-\u17FF\u2010-\u2027]+$")

FORBIDDEN_ADMIN_PATTERNS = [
    r"\bDivision\b", r"\bRegency\b", r"\bResidency\b", r"\bProvince\b",
    r"\bDistrict\b", r"\bMunicipality\b", r"\bKingdom of\b", r"\bSultanate of\b",
    r"\bRepublic of\b", r"\bGemeente\b", r"\bKabupaten\b", r"\bAmphoe\b",
    r"\bTownship\b", r"Binh Tri Thien"
]
ADMIN_RE = re.compile("|".join(FORBIDDEN_ADMIN_PATTERNS), re.IGNORECASE)

MOJIBAKE_CHARS = ["?", "`", "\ufffd", "~"]

FOREIGN_ROMANIZATION_PATTERNS = [
    r"\b(?:xian|sheng|shi|dao|seom|gun|gu)\b",
    r"\b(?:bo bo na luo|ma ge lang|jian yi li|nu shan ta la|dang ge lang)\b",
    r"\b(?:teleunate|terunate)\b",
    r"^[A-Z]{3,4}$",  # Airport codes like MES, SRG, PLM
]
FOREIGN_ROM_RE = re.compile("|".join(FOREIGN_ROMANIZATION_PATTERNS), re.IGNORECASE)


def clean_canonical_name(name, key):
    s = str(name or "").strip()
    # Remove single and double quotes and backticks
    s = s.replace("'", "").replace('"', '').replace("`", "")
    # Remove administrative post
    s = re.sub(r"\s+administrative post$", "", s, flags=re.I).strip()
    # Remove comma separated alternative like Kotagede, Plered
    if "," in s:
        s = s.split(",")[0].strip()
    # Clean leading hyphens
    s = s.lstrip("-").strip()
    return s


def is_clean_other_name(name, country, canon):
    if not name:
        return False
    s = str(name).strip()
    s = s.replace("`", "").replace("'", "").replace('"', '')
    if any(ch in s for ch in MOJIBAKE_CHARS) or "(" in s or ")" in s or "[" in s or "]" in s:
        return False
    if ADMIN_RE.search(s):
        return False
    if FOREIGN_ROM_RE.search(s):
        return False
    if s.lower() == canon.lower():
        return False
    if len(s) < 2 or len(s) > 60:
        return False
    # Baltic/Slavic grammatical cases like Semarangas, Palembangas
    if s.endswith("as") and s[:-2].lower() == canon.lower():
        return False
    if s.endswith("a") and s[:-1].lower() == canon.lower():
        return False
    if country in ("Brunei", "Indonesia", "East Timor", "Malaysia", "Singapore", "Philippines"):
        if not LATIN_ONLY_RE.match(s):
            return False
    elif country == "Cambodia":
        if not CAMBODIA_ALLOWED_RE.match(s):
            return False
    return True


def resolve_settlement(s):
    k = s["key"]
    country = s["country"]
    raw_name = s["name"]
    coords = s["coords_lat_lng"]
    latest_year = s.get("latest_year", 2025)
    meta_idx = s.get("existing_meta_index")
    ey = s.get("earliest_year", 2025)
    fy = s.get("foundation_year")
    
    if k in KNOWN_HISTORICAL:
        known = KNOWN_HISTORICAL[k]
        canon = known["canonical_name"]
        hnames = list(known["historical_names"])
        other_candidates = list(known.get("other_names", [])) + list(s.get("known_aliases", []))
    else:
        canon = clean_canonical_name(raw_name, k)
        other_candidates = list(s.get("known_aliases", []))
        
        ex_hn = s.get("existing_historical_names", [])
        clean_hn = []
        for h in ex_hn:
            hn_date = h.get("date", "")
            hn_nm = clean_canonical_name(h.get("name", ""), k)
            if ADMIN_RE.search(hn_nm) or any(ch in hn_nm for ch in MOJIBAKE_CHARS):
                continue
            if hn_nm.lower() == "kuturaja":
                hn_nm = "Kutaraja"
            if hn_nm.lower() == "djokjakarta":
                continue  # ignore legacy 800 AD djokjakarta
            clean_hn.append({"date": hn_date, "name": hn_nm})
            
        dedup_hn = []
        for h in clean_hn:
            if not dedup_hn or dedup_hn[-1]["name"].lower() != h["name"].lower():
                dedup_hn.append(h)
                
        start_year = fy if fy is not None else ey
        if start_year < 500:
            start_year = 1200
            
        if not dedup_hn:
            hnames = [{"date": f"{start_year}.1.1", "name": canon}]
        elif len(dedup_hn) == 1:
            hnames = [{"date": dedup_hn[0]["date"], "name": canon}]
        else:
            hnames = dedup_hn
            
    # Strictly sort by date
    hnames.sort(key=lambda x: [int(p) for p in x["date"].split(".")])
    
    # Rule 5: NO adjacent duplicate names
    final_hnames = []
    for h in hnames:
        if not final_hnames or final_hnames[-1]["name"].lower() != h["name"].lower():
            final_hnames.append(h)
            
    # Rule 6: Terminal Modern Anchor
    if latest_year is not None and latest_year >= 1950:
        if not final_hnames or final_hnames[-1]["name"] != canon:
            final_hnames.append({"date": "1950.1.1", "name": canon})
            
    cleaned_hnames = []
    for h in final_hnames:
        if not cleaned_hnames or cleaned_hnames[-1]["name"].lower() != h["name"].lower():
            cleaned_hnames.append(h)
    if latest_year is not None and latest_year >= 1950:
        cleaned_hnames[-1]["name"] = canon
        
    # Clean other_names
    cleaned_others = []
    seen = {canon.lower()}
    for o in other_candidates:
        if is_clean_other_name(o, country, canon):
            cleaned_s = str(o).strip().replace("`", "").replace("'", "").replace('"', '')
            if cleaned_s.lower() not in seen:
                seen.add(cleaned_s.lower())
                cleaned_others.append(cleaned_s)
                
    for h in cleaned_hnames:
        hn_val = h["name"]
        if is_clean_other_name(hn_val, country, canon):
            if hn_val.lower() not in seen:
                seen.add(hn_val.lower())
                cleaned_others.append(hn_val)
                
    return {
        "key": k,
        "canonical_name": canon,
        "coords_lat_lng": coords,
        "country": country,
        "latest_year": latest_year,
        "existing_meta_index": meta_idx,
        "historical_names": cleaned_hnames,
        "other_names": cleaned_others
    }


def main():
    target_dir = os.path.join("tests", "mandala_toponymy_swarm")
    all_passed = True
    
    for b in range(1, 9):
        in_path = os.path.join(target_dir, f"swarm_in_{b:03d}.json")
        out_path = os.path.join(target_dir, f"resolved_batch_{b:03d}.json")
        
        with open(in_path, "r", encoding="utf-8") as f:
            in_data = json.load(f)
            
        settlements = [resolve_settlement(s) for s in in_data["settlements"]]
        batch_out = {
            "batch_index": b,
            "settlements": settlements
        }
        
        errors, warnings = validate_resolved_batch(batch_out, b, in_data)
        if errors:
            print(f"[FAIL] Batch {b:03d} has {len(errors)} error(s):")
            for err in errors:
                print(f"   {err}")
            all_passed = False
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(batch_out, f, indent=2, ensure_ascii=False)
            print(f"[PASS] Batch {b:03d} written to {out_path} ({len(settlements)} settlements)")
            
    if not all_passed:
        print("\nERRORS DETECTED! Aborting.")
        sys.exit(1)
        
    print("\nALL 8 BATCHES RESOLVED AND VALIDATED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
