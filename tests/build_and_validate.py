import json
import re
import unicodedata
import os
import sys

# Compile regex patterns
cjk_re = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af]')
cyrillic_re = re.compile(r'[\u0400-\u04ff]')
arabic_re = re.compile(r'[\u0600-\u06ff]')
devanagari_re = re.compile(r'[\u0900-\u097f]')
thai_re = re.compile(r'[\u0e00-\u0e7f]')

FORBIDDEN_ADMIN_PATTERNS = [
    re.compile(r'\bDivision\b', re.I),
    re.compile(r'\bRegency\b', re.I),
    re.compile(r'\bResidency\b', re.I),
    re.compile(r'\bProvince\b', re.I),
    re.compile(r'\bDistrict\b', re.I),
    re.compile(r'\bMunicipality\b', re.I),
    re.compile(r'\bKingdom of\b', re.I),
    re.compile(r'\bSultanate of\b', re.I),
    re.compile(r'\bRepublic of\b', re.I),
    re.compile(r'\bGemeente\b', re.I),
    re.compile(r'\bKabupaten\b', re.I),
    re.compile(r'\bAmphoe\b', re.I),
    re.compile(r'\bTownship\b', re.I),
    re.compile(r'\bBinh Tri Thien\b', re.I),
    re.compile(r'\bCity of\b', re.I),
    re.compile(r'\bBayan ng\b', re.I),
    re.compile(r'\bLungsod ng\b', re.I),
    re.compile(r'\bMunicipio de\b', re.I),
]

ADMIN_ALIAS_PREFIXES = [
    r'^(?:Amphoe|Amphu|King Amphoe|Khet|Changwat|Provincia de|Provincia di|Propinsi)\s+',
    r'^(?:Bayan ng|Lungsod ng|Dakbayan sa|Municipio de|City of|Ili ti)\s+',
    r'^(?:Kota|Banwa it|Banwa kang|Banwa sang|Munisipalidad sa)\s+'
]

ADMIN_ALIAS_SUFFIXES = [
    r'\s+(?:City|District|Province|Township|Novyj gorod|Lakanbalen)$'
]

CANONICAL_NAME_OVERRIDES = {
    'Palayan City-Philippines': 'Palayan',
    'Sengkang New Town-Singapore': 'Sengkang',
    'Ang Mo Kio New Town-Singapore': 'Ang Mo Kio',
    'Bukit Batok New Town-Singapore': 'Bukit Batok',
    'Reina Mercedes-Philippines': 'Reina Mercedes',
    'Sattahip-Thailand': 'Sattahip',
    'Sa Kaeo-Thailand': 'Sa Kaeo',
    'Fort Pilar-Philippines': 'Fort Pilar',
    'Caoayan-Philippines': 'Caoayan',
    'Mabitac-Philippines': 'Mabitac',
    'Ayala Alabang-Philippines': 'Ayala Alabang',
    'Gumaca-Philippines': 'Gumaca',
    'Guihulngan-Philippines': 'Guihulngan',
    'Sara Buri-Thailand': 'Saraburi',
    'Saraburi-Thailand': 'Saraburi',
}

HISTORICAL_NAME_OVERRIDES = {
    # Batch 41
    'Sasmuan-Philippines': [
        {"date": "1572.5.3", "name": "Lubao"},
        {"date": "1611.1.1", "name": "Sexmoan"},
        {"date": "1991.1.15", "name": "Sasmuan"}
    ],
    'Tangub-Philippines': [
        {"date": "1200.1.1", "name": "Regidor"},
        {"date": "1930.2.28", "name": "Tangub"}
    ],
    'Delfin Albano-Philippines': [
        {"date": "1957.6.22", "name": "Magsaysay"},
        {"date": "1982.11.14", "name": "Delfin Albano"}
    ],
    
    # Batch 42
    'Tandag-Philippines': [
        {"date": "1609.1.1", "name": "Tandag"}
    ],
    'Reina Mercedes-Philippines': [
        {"date": "1886.1.1", "name": "Reina Mercedes"}
    ],
    'Garchitorena-Philippines': [
        {"date": "1919.1.1", "name": "Anderson"},
        {"date": "1949.3.4", "name": "Garchitorena"}
    ],
    'Conner-Philippines': [
        {"date": "1914.1.1", "name": "Ripang"},
        {"date": "1950.6.25", "name": "Conner"}
    ],
    
    # Batch 43
    'Ayala Alabang-Philippines': [
        {"date": "1950.1.1", "name": "Muntinlupa"},
        {"date": "1981.1.1", "name": "Ayala Alabang"}
    ],
    'Tugaya-Philippines': [
        {"date": "1521.1.1", "name": "Tugaya"}
    ],
    
    # Batch 44
    'Palayan City-Philippines': [
        {"date": "1960.1.1", "name": "Palayan"}
    ],
    'Guihulngan-Philippines': [
        {"date": "1936.1.1", "name": "Guihulñgan"},
        {"date": "1950.1.1", "name": "Guihulngan"}
    ],
    'Gumaca-Philippines': [
        {"date": "1574.1.1", "name": "Bumaka"},
        {"date": "1582.1.1", "name": "Gumaca"}
    ],
    'Ramos-Philippines': [
        {"date": "1900.1.1", "name": "Bani"},
        {"date": "1920.1.1", "name": "Ramos"}
    ],
    
    # Batch 45
    'Mabitac-Philippines': [
        {"date": "1600.1.1", "name": "Siniloan"},
        {"date": "1611.1.1", "name": "Mabitac"}
    ],
    'Baras-Philippines_2': [
        {"date": "1595.1.1", "name": "Baras"}
    ],
    'Salcedo-Philippines': [
        {"date": "1900.1.1", "name": "Bauguen"},
        {"date": "1957.6.20", "name": "Salcedo"}
    ],
    'Luna-Philippines': [
        {"date": "1929.1.1", "name": "Antatet"},
        {"date": "1951.9.28", "name": "Luna"}
    ],
    'Luna-Philippines_2': [
        {"date": "1929.1.1", "name": "Antatet"},
        {"date": "1951.9.28", "name": "Luna"}
    ],
    'Del Carmen-Philippines': [
        {"date": "1920.1.1", "name": "Numancia"},
        {"date": "1966.6.18", "name": "Del Carmen"}
    ],
    
    # Batch 46
    'Caoayan-Philippines': [
        {"date": "1903.1.1", "name": "Vigan"},
        {"date": "1911.1.1", "name": "Caoayan"}
    ],
    'Lagawe-Philippines': [
        {"date": "1960.1.1", "name": "Lagawe"}
    ],
    'Maasin-Philippines_2': [
        {"date": "1700.1.1", "name": "Maasin"}
    ],
    'Butuan-Philippines_2': [
        {"date": "800.1.1", "name": "Butuan"}
    ],
    'Fort Pilar-Philippines': [
        {"date": "1635.6.23", "name": "Jambangan"},
        {"date": "1635.6.24", "name": "Villa de Zamboanga"},
        {"date": "1719.1.1", "name": "Fort Pilar"}
    ],
    'Serangoon-Singapore': [
        {"date": "1828.1.1", "name": "Serangoon"}
    ],
    'Sengkang New Town-Singapore': [
        {"date": "1997.1.1", "name": "Sengkang"}
    ],
    'Ang Mo Kio New Town-Singapore': [
        {"date": "1973.1.1", "name": "Ang Mo Kio"}
    ],
    'Bukit Batok New Town-Singapore': [
        {"date": "1981.1.1", "name": "Bukit Batok"}
    ],
    'Nakhon Ratchasima-Thailand': [
        {"date": "1656.1.1", "name": "Khorat"},
        {"date": "1939.6.24", "name": "Nakhon Ratchasima"}
    ],
    'Maha Sarakham-Thailand': [
        {"date": "1865.8.22", "name": "Maha Sarakham"}
    ],
    'Kanchanaburi-Thailand': [
        {"date": "1500.1.1", "name": "Kanburi"},
        {"date": "1784.1.1", "name": "Kanchanaburi"}
    ],
    'Nakhon Phanom-Thailand': [
        {"date": "1400.1.1", "name": "Marukkha Nakhon"},
        {"date": "1786.1.1", "name": "Nakhon Phanom"}
    ],
    'Saraburi-Thailand': [
        {"date": "1549.1.1", "name": "Saraburi"}
    ],
    'Chachoengsao-Thailand': [
        {"date": "1549.1.1", "name": "Chachoengsao"}
    ],
    'Khon Kaen-Thailand': [
        {"date": "1797.1.1", "name": "Khon Kaen"}
    ],
    'Bang Phli-Thailand': [
        {"date": "1895.1.1", "name": "Bang Phli"}
    ],
    
    # Batch 47
    'Si Racha-Thailand': [
        {"date": "1894.1.1", "name": "Si Racha"}
    ],
    'Sukhothai-Thailand': [
        {"date": "1238.1.1", "name": "Sukhothai"}
    ],
    'Sa Kaeo-Thailand': [
        {"date": "1909.1.1", "name": "Ban Sa Kaeo"},
        {"date": "1993.12.1", "name": "Sa Kaeo"}
    ],
    'Phatthalung-Thailand': [
        {"date": "1350.1.1", "name": "Phatthalung"}
    ],
    'Nong Khai-Thailand': [
        {"date": "1827.1.1", "name": "Nong Khai"}
    ],
    'Chumphon-Thailand': [
        {"date": "1400.1.1", "name": "Chumphon"}
    ],
    'Phetchaburi-Thailand': [
        {"date": "750.1.1", "name": "Phetchaburi"}
    ],
    'Lampang-Thailand_2': [
        {"date": "680.1.1", "name": "Khelang Nakhon"},
        {"date": "1892.1.1", "name": "Lampang"}
    ],
    'Sing Buri-Thailand': [
        {"date": "1100.1.1", "name": "Sing Buri"}
    ],
    'Kanchanaburi-Thailand_2': [
        {"date": "1500.1.1", "name": "Kanburi"},
        {"date": "1784.1.1", "name": "Kanchanaburi"}
    ],
    'Sattahip-Thailand': [
        {"date": "1960.1.1", "name": "Sattahip"}
    ],
    'Bangkok Noi-Thailand': [
        {"date": "1915.10.15", "name": "Amarin"},
        {"date": "1916.7.11", "name": "Bangkok Noi"}
    ]
}

def clean_alias(alias, country):
    alias = alias.strip()
    if not alias:
        return None
    # No Cyrillic, Arabic, Devanagari, CJK
    if cjk_re.search(alias) or cyrillic_re.search(alias) or arabic_re.search(alias) or devanagari_re.search(alias):
        return None
    # Script purity:
    if country in ['Philippines', 'Singapore']:
        if thai_re.search(alias):
            return None
        for ch in alias:
            cat = unicodedata.category(ch)
            if cat.startswith('L'):
                name = unicodedata.name(ch, '')
                if 'LATIN' not in name:
                    return None
            elif ch not in " -'.,":
                return None
    elif country == 'Thailand':
        for ch in alias:
            cat = unicodedata.category(ch)
            if cat.startswith('L'):
                name = unicodedata.name(ch, '')
                if 'LATIN' not in name and 'THAI' not in name:
                    return None
            elif ch not in " -'.,":
                if not thai_re.search(ch):
                    return None
    
    # Strip admin prefixes/suffixes
    cleaned = alias
    for pref in ADMIN_ALIAS_PREFIXES:
        cleaned = re.sub(pref, '', cleaned, flags=re.I).strip()
    for suff in ADMIN_ALIAS_SUFFIXES:
        cleaned = re.sub(suff, '', cleaned, flags=re.I).strip()
    
    # Filter out corrupted strings or parentheticals
    if re.search(r'[\?`\uFFFD\(\)\/\\]', cleaned):
        return None
    if cleaned.startswith('-') or cleaned.endswith('-'):
        return None
    if len(cleaned) < 2:
        return None
    return cleaned

def resolve_settlement(s):
    key = s["key"]
    country = s["country"]
    coords = s["coords_lat_lng"]
    latest_year = s["latest_year"]
    meta_idx = s.get("existing_meta_index")
    
    # Canonical name
    if key in CANONICAL_NAME_OVERRIDES:
        canonical_name = CANONICAL_NAME_OVERRIDES[key]
    else:
        name = s["name"]
        for pref in ADMIN_ALIAS_PREFIXES:
            name = re.sub(pref, '', name, flags=re.I).strip()
        for suff in ADMIN_ALIAS_SUFFIXES:
            name = re.sub(suff, '', name, flags=re.I).strip()
        canonical_name = name
    
    # Historical names
    if key in HISTORICAL_NAME_OVERRIDES:
        hist_names = list(HISTORICAL_NAME_OVERRIDES[key])
    elif s.get("existing_historical_names"):
        cleaned_hist = []
        for h in s["existing_historical_names"]:
            h_date = h["date"]
            h_name = h["name"]
            for pref in ADMIN_ALIAS_PREFIXES:
                h_name = re.sub(pref, '', h_name, flags=re.I).strip()
            for suff in ADMIN_ALIAS_SUFFIXES:
                h_name = re.sub(suff, '', h_name, flags=re.I).strip()
            if not h_name:
                h_name = canonical_name
            cleaned_hist.append({"date": h_date, "name": h_name})
        
        cleaned_hist.sort(key=lambda x: [int(p) for p in x["date"].split('.')])
        
        dedup_hist = []
        for h in cleaned_hist:
            if not dedup_hist or dedup_hist[-1]["name"] != h["name"]:
                dedup_hist.append(h)
        
        if latest_year >= 1950 and dedup_hist[-1]["name"] != canonical_name:
            dedup_hist.append({"date": f"{latest_year}.1.1", "name": canonical_name})
        
        hist_names = dedup_hist
    else:
        fnd_year = s.get("foundation_year")
        ear_year = s.get("earliest_year")
        anchor_year = fnd_year if fnd_year is not None else (ear_year if ear_year is not None else 1200)
        hist_names = [{"date": f"{anchor_year}.1.1", "name": canonical_name}]
    
    if latest_year >= 1950 and hist_names[-1]["name"] != canonical_name:
        hist_names.append({"date": f"{latest_year}.1.1", "name": canonical_name})
    
    # Clean other_names
    other_names = []
    seen = {canonical_name.lower()}
    
    for h in hist_names:
        hn = h["name"]
        if hn.lower() not in seen:
            other_names.append(hn)
            seen.add(hn.lower())
    
    for a in s.get("known_aliases", []):
        ca = clean_alias(a, country)
        if ca and ca.lower() not in seen:
            other_names.append(ca)
            seen.add(ca.lower())
    
    return {
        "key": key,
        "canonical_name": canonical_name,
        "coords_lat_lng": coords,
        "country": country,
        "latest_year": latest_year,
        "existing_meta_index": meta_idx,
        "historical_names": hist_names,
        "other_names": other_names
    }

def process_and_validate():
    all_resolved = {}
    total_errors = 0
    all_seen_keys = set()
    
    for b in range(41, 49):
        in_fn = f"tests/mandala_toponymy_swarm/swarm_in_{b:03d}.json"
        out_fn = f"tests/mandala_toponymy_swarm/resolved_batch_{b:03d}.json"
        
        with open(in_fn, "r", encoding="utf-8") as f:
            in_data = json.load(f)
        
        batch_idx = in_data["batch_index"]
        settlements = in_data["settlements"]
        
        resolved_settlements = []
        batch_keys = set()
        
        for s in settlements:
            k = s["key"]
            if k in all_seen_keys:
                print(f"[ERROR] Global duplicate key: {k}")
                total_errors += 1
            all_seen_keys.add(k)
            batch_keys.add(k)
            
            res = resolve_settlement(s)
            
            # --- STRICT AUDIT OF RESOLVED SETTLEMENT ---
            c_name = res["canonical_name"]
            
            # 1. Check administrative suffixes / forbidden patterns
            for pat in FORBIDDEN_ADMIN_PATTERNS:
                if pat.search(c_name):
                    print(f"[ERROR] Admin word in canonical_name: '{c_name}' in key {k}")
                    total_errors += 1
            
            for h in res["historical_names"]:
                h_name = h["name"]
                for pat in FORBIDDEN_ADMIN_PATTERNS:
                    if pat.search(h_name):
                        print(f"[ERROR] Admin word in historical name: '{h_name}' in key {k}")
                        total_errors += 1
            
            # 2. Check corrupt punctuation / Mojibake
            for text_val, src in [(c_name, "canonical_name")] + [(h["name"], "hist_name") for h in res["historical_names"]]:
                if any(bad in text_val for bad in ['?', '`', '\uFFFD', '(', ')']):
                    print(f"[ERROR] Corrupt char in {src}: '{text_val}' in key {k}")
                    total_errors += 1
                if text_val.startswith("-") or text_val.endswith("-"):
                    print(f"[ERROR] Hyphen edge in {src}: '{text_val}' in key {k}")
                    total_errors += 1
            
            # 3. Check dates format, order, duplicates
            hist = res["historical_names"]
            if not hist:
                print(f"[ERROR] Empty historical_names for key {k}")
                total_errors += 1
            
            parsed_dates = []
            for i, h in enumerate(hist):
                d_str = h["date"]
                if not re.match(r'^-?\d+\.\d+\.\d+$', d_str):
                    print(f"[ERROR] Invalid date format '{d_str}' in key {k}")
                    total_errors += 1
                parts = [int(p) for p in d_str.split('.')]
                parsed_dates.append(parts)
                if i > 0:
                    prev = parsed_dates[i-1]
                    curr = parsed_dates[i]
                    if curr < prev:
                        print(f"[ERROR] Chronology violation in key {k}: {hist[i-1]['date']} before {d_str}")
                        total_errors += 1
                    if hist[i-1]["name"] == h["name"]:
                        print(f"[ERROR] Adjacent duplicate name '{h['name']}' in key {k}")
                        total_errors += 1
            
            # 4. Terminal Modern Anchor
            if res["latest_year"] >= 1950:
                if hist[-1]["name"] != c_name:
                    print(f"[ERROR] Terminal anchor mismatch in key {k}: '{hist[-1]['name']}' != '{c_name}'")
                    total_errors += 1
            
            # 5. Script purity in other_names
            country = res["country"]
            for a in res["other_names"]:
                if cjk_re.search(a) or cyrillic_re.search(a) or arabic_re.search(a) or devanagari_re.search(a):
                    print(f"[ERROR] Foreign script spam in other_names: '{a}' in key {k}")
                    total_errors += 1
                if country in ['Philippines', 'Singapore']:
                    if thai_re.search(a):
                        print(f"[ERROR] Thai script in Latin country other_names: '{a}' in key {k}")
                        total_errors += 1
            
            resolved_settlements.append(res)
        
        if len(resolved_settlements) != len(settlements):
            print(f"[ERROR] Batch {b} count mismatch: {len(resolved_settlements)} != {len(settlements)}")
            total_errors += 1
        
        out_payload = {
            "batch_index": batch_idx,
            "settlements": resolved_settlements
        }
        
        with open(out_fn, "w", encoding="utf-8") as f:
            json.dump(out_payload, f, indent=2, ensure_ascii=False)
        
        all_resolved[b] = len(resolved_settlements)
        print(f"Batch {b:03d} written to {out_fn} ({len(resolved_settlements)} settlements).")

    print("\n================ AUDIT SUMMARY ================")
    print(f"Total batches processed: {len(all_resolved)}")
    print(f"Total settlements resolved: {len(all_seen_keys)}")
    print(f"Total audit errors: {total_errors}")
    if total_errors == 0:
        print("ALL BATCHES PASSED 100% CLEAN!")
    else:
        print(f"FAILED WITH {total_errors} ERRORS!")

if __name__ == "__main__":
    process_and_validate()
