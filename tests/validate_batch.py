import json
import re
import unicodedata

DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")

# Script purity regexes
# For LATIN_COUNTRIES: must only contain ASCII / Latin characters (including Latin Extended) and punctuation/spaces
LATIN_ONLY_RE = re.compile(r"^[\u0020-\u007E\u00A0-\u024F\u1E00-\u1EFF\u2010-\u2027]+$")

# For Cambodia: Latin + Khmer (U+1780 to U+17FF) + spaces/punctuation
CAMBODIA_ALLOWED_RE = re.compile(r"^[\u0020-\u007E\u00A0-\u024F\u1E00-\u1EFF\u1780-\u17FF\u2010-\u2027]+$")

FORBIDDEN_ADMIN_PATTERNS = [
    r"\bDivision\b", r"\bRegency\b", r"\bResidency\b", r"\bProvince\b",
    r"\bDistrict\b", r"\bMunicipality\b", r"\bKingdom of\b", r"\bSultanate of\b",
    r"\bRepublic of\b", r"\bGemeente\b", r"\bKabupaten\b", r"\bAmphoe\b",
    r"\bTownship\b", r"Binh Tri Thien"
]
ADMIN_RE = re.compile("|".join(FORBIDDEN_ADMIN_PATTERNS), re.IGNORECASE)

MOJIBAKE_CHARS = ["?", "`", "\ufffd", "~"]

def validate_resolved_batch(batch_data, batch_idx, input_batch_data):
    errors = []
    warnings = []
    
    if batch_data.get("batch_index") != batch_idx:
        errors.append(f"batch_index {batch_data.get('batch_index')} != {batch_idx}")
        
    in_settlements = input_batch_data.get("settlements", [])
    out_settlements = batch_data.get("settlements", [])
    
    if len(in_settlements) != len(out_settlements):
        errors.append(f"Settlement count mismatch: input has {len(in_settlements)}, output has {len(out_settlements)}")
        
    in_keys = [s["key"] for s in in_settlements]
    out_keys = [s.get("key") for s in out_settlements]
    
    if in_keys != out_keys:
        errors.append(f"Settlement keys do not exactly match input order/keys! in[:3]={in_keys[:3]} out[:3]={out_keys[:3]}")
        
    for i, s in enumerate(out_settlements):
        k = s.get("key", f"item_{i}")
        cname = s.get("canonical_name", "")
        country = s.get("country", "")
        coords = s.get("coords_lat_lng", [])
        latest_year = s.get("latest_year")
        hnames = s.get("historical_names", [])
        other = s.get("other_names", [])
        
        if not cname:
            errors.append(f"[{k}] missing canonical_name")
        if ADMIN_RE.search(cname):
            errors.append(f"[{k}] canonical_name contains admin title: '{cname}'")
        if any(ch in cname for ch in MOJIBAKE_CHARS):
            errors.append(f"[{k}] canonical_name contains mojibake/punctuation: '{cname}'")
        if cname.startswith("-") or "(" in cname or ")" in cname or "'" in cname or '"' in cname:
            errors.append(f"[{k}] canonical_name contains forbidden punctuation (parens/quotes/leading hyphen): '{cname}'")
            
        if not coords or len(coords) != 2:
            errors.append(f"[{k}] invalid coords: {coords}")
            
        if not hnames:
            errors.append(f"[{k}] empty historical_names")
        else:
            # Check dates and names
            prev_name = None
            prev_date_tuple = None
            for idx_h, hn in enumerate(hnames):
                dt = hn.get("date", "")
                nm = hn.get("name", "")
                if not DATE_RE.match(dt):
                    errors.append(f"[{k}] invalid date format '{dt}' in hn[{idx_h}]")
                if ADMIN_RE.search(nm):
                    errors.append(f"[{k}] historical_name contains admin title: '{nm}'")
                if any(ch in nm for ch in MOJIBAKE_CHARS) or "(" in nm or ")" in nm or "`" in nm:
                    errors.append(f"[{k}] historical_name contains forbidden chars: '{nm}'")
                    
                # Date order check
                date_parts = [int(p) for p in dt.split(".")]
                dt_tuple = tuple(date_parts)
                if prev_date_tuple is not None and dt_tuple < prev_date_tuple:
                    errors.append(f"[{k}] dates not ascending: {dt} < previous")
                prev_date_tuple = dt_tuple
                
                # Rule 5: NO adjacent duplicate names
                if prev_name is not None and nm.lower() == prev_name.lower():
                    errors.append(f"[{k}] adjacent duplicate in historical_names: '{nm}'")
                prev_name = nm
                
            # Rule 6: Terminal Modern Anchor
            if latest_year is not None and latest_year >= 1950:
                if hnames[-1]["name"] != cname:
                    errors.append(f"[{k}] terminal historical name '{hnames[-1]['name']}' != canonical '{cname}' (latest_year={latest_year})")
                    
        # Rule 7: Script purity in other_names
        for o in other:
            if country in ("Brunei", "Indonesia", "East Timor", "Malaysia", "Singapore", "Philippines"):
                if not LATIN_ONLY_RE.match(o):
                    errors.append(f"[{k}] other_names contains non-Latin in {country}: '{o}'")
            elif country == "Cambodia":
                if not CAMBODIA_ALLOWED_RE.match(o):
                    errors.append(f"[{k}] other_names contains forbidden script in Cambodia: '{o}'")
            if any(ch in o for ch in MOJIBAKE_CHARS) or "(" in o or ")" in o or "[" in o or "]" in o:
                errors.append(f"[{k}] other_names contains forbidden chars: '{o}'")
                
    return errors, warnings
