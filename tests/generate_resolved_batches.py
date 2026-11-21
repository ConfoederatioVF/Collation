import json
import os
import re

# Banned administrative / state words
BANNED_ADMIN = [
    "division", "regency", "residency", "province", "district",
    "municipality", "kingdom of", "sultanate of", "republic of",
    "gemeente", "kabupaten", "amphoe", "township", "binh tri thien"
]

# Regex for foreign scripts
BANNED_GENERAL = re.compile(
    r"[\u0400-\u04FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF"
    r"\u0900-\u097F\u4E00-\u9FFF\u3400-\u4DBF\u3040-\u30FF\uAC00-\uD7AF\u1100-\u11FF]"
)

BANNED_FOR_LATIN_ONLY = re.compile(
    r"[\u0400-\u04FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF"
    r"\u0900-\u097F\u4E00-\u9FFF\u3400-\u4DBF\u3040-\u30FF\uAC00-\uD7AF\u1100-\u11FF"
    r"\u1000-\u109F\uA9E0-\uA9FF\u0E00-\u0E7F\u0E80-\u0EFF\u1780-\u17FF]"
)

ARABIC_ROMANIZED_TOKENS = {
    'shmaly', 'ghrby', 'shrqy', 'jnbwy', 'wady', 'dawayw', 'nygrws', 'kamarynz', 'kwmpwstyla',
    'pwlayw', 'balyk', 'dygws', 'qwwyt', 'kzwn', 'ysgyw', 'danbyw', 'myawngmya', 'myananwng',
    'maghwy', 'balytwa', 'parewwa', 'mineyaannmyahoet', 'titekyeemyahoet', 'dayt', 'maty'
}

PINYIN_ADMIN_TOKENS = {
    'xian', 'qu', 'zhen', 'jun', 'shi'
}

PINYIN_PHRASES = [
    'tang dou', 'sheng ke lu si', 'bo ge xian na', 'ya luo ya ye', 'ba ding yan dai',
    'fu luo shan bei', 'cang lun', 'xiang long', 'zhang lun', 'dan biao zha ya', 'mian ang',
    'gua la ban you', 'ba ba', 'shi la zhuo', 'bai li wa', 'ke xr tea h', 'ju cha'
]

CORRUPT_CHARS = re.compile(r"[\?\`\ufffd]")
DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")

# Custom historical enrichments dictionary keyed by input settlement key
CUSTOM_ENRICHMENTS = {
    # --- MALAYSIA ---
    "Kertih-Malaysia": {
        "canonical_name": "Kertih",
        "historical_names": [
            {"date": "1950.1.1", "name": "Kerteh"},
            {"date": "1980.1.1", "name": "Kertih"}
        ]
    },
    "Ladang Seri Kundang-Malaysia": {
        "canonical_name": "Ladang Seri Kundang",
        "historical_names": [
            {"date": "1950.1.1", "name": "Penkalang Kundang"},
            {"date": "1980.1.1", "name": "Ladang Seri Kundang"}
        ]
    },
    "Kampung Tanjung Minyak-Malaysia": {
        "canonical_name": "Kampung Tanjung Minyak",
        "historical_names": [
            {"date": "1950.1.1", "name": "Bukit Rambai"},
            {"date": "1970.1.1", "name": "Kampung Tanjung Minyak"}
        ]
    },
    "Kuala Kubu Bharu-Malaysia": {
        "canonical_name": "Kuala Kubu Bharu",
        "historical_names": [
            {"date": "1931.1.1", "name": "Kuala Kubu Baharu"},
            {"date": "1950.1.1", "name": "Kuala Kubu Bharu"}
        ]
    },
    "Tanjung Sepat-Malaysia": {
        "canonical_name": "Tanjung Sepat",
        "historical_names": [
            {"date": "1950.1.1", "name": "Tanjong Sepat"},
            {"date": "1980.1.1", "name": "Tanjung Sepat"}
        ]
    },
    "Baru Salak Tinggi-Malaysia": {
        "canonical_name": "Baru Salak Tinggi",
        "historical_names": [
            {"date": "1950.1.1", "name": "Bandar Baru Salak Tinggi"},
            {"date": "1980.1.1", "name": "Baru Salak Tinggi"}
        ]
    },
    "Batang Berjuntai-Malaysia": {
        "canonical_name": "Batang Berjuntai",
        "historical_names": [
            {"date": "1950.1.1", "name": "Batang Berjuntai"}
        ],
        "extra_other": ["Bestari Jaya"]
    },
    "Kampong Kadok-Malaysia": {
        "canonical_name": "Kampong Kadok",
        "historical_names": [
            {"date": "1950.1.1", "name": "Kadok"},
            {"date": "1980.1.1", "name": "Kampong Kadok"}
        ]
    },
    "Kampar-Malaysia": {
        "canonical_name": "Kampar",
        "historical_names": [
            {"date": "1887.1.1", "name": "Kampar"}
        ]
    },
    "FELDA Chini-Malaysia": {
        "canonical_name": "FELDA Chini",
        "historical_names": [
            {"date": "1970.1.1", "name": "FELDA Chini"}
        ]
    },
    "Bujang Valley-Malaysia": {
        "canonical_name": "Bujang Valley",
        "historical_names": [
            {"date": "-500.1.1", "name": "Bujang Valley"}
        ],
        "extra_other": ["Lembah Bujang"]
    },

    # --- MYANMAR ---
    "Chin State-Myanmar": {
        "canonical_name": "Chin Hills",
        "historical_names": [
            {"date": "1896.1.1", "name": "Chin Hills"}
        ],
        "extra_other": ["Hakha", "Chin"]
    },
    "Kalay-Myanmar": {
        "canonical_name": "Kalay",
        "historical_names": [
            {"date": "966.2.3", "name": "Kalemyo"},
            {"date": "1989.6.18", "name": "Kalay"}
        ]
    },
    "Pathein-Myanmar": {
        "canonical_name": "Pathein",
        "historical_names": [
            {"date": "1000.1.1", "name": "Kusima"},
            {"date": "1852.12.20", "name": "Bassein"},
            {"date": "1989.6.18", "name": "Pathein"}
        ]
    },
    "Bago-Myanmar": {
        "canonical_name": "Bago",
        "historical_names": [
            {"date": "825.1.1", "name": "Hanthawaddy"},
            {"date": "1369.1.1", "name": "Pegu"},
            {"date": "1989.6.18", "name": "Bago"}
        ]
    },
    "Dawei-Myanmar": {
        "canonical_name": "Dawei",
        "historical_names": [
            {"date": "1751.1.1", "name": "Tavoy"},
            {"date": "1989.6.18", "name": "Dawei"}
        ]
    },
    "Amarapura-Myanmar_2": {
        "canonical_name": "Amarapura",
        "historical_names": [
            {"date": "1783.5.10", "name": "Amarapura"}
        ],
        "extra_other": ["Taungmyo"]
    },
    "Mrauk U-Myanmar": {
        "canonical_name": "Mrauk U",
        "historical_names": [
            {"date": "1430.1.1", "name": "Mrauk U"},
            {"date": "1826.1.1", "name": "Mrohaung"},
            {"date": "1989.6.18", "name": "Mrauk U"}
        ]
    },
    "Taungoo-Myanmar": {
        "canonical_name": "Taungoo",
        "historical_names": [
            {"date": "1510.1.1", "name": "Ketumati"},
            {"date": "1852.1.1", "name": "Toungoo"},
            {"date": "1989.6.18", "name": "Taungoo"}
        ]
    },
    "Pagan-Myanmar": {
        "canonical_name": "Pagan",
        "historical_names": [
            {"date": "849.1.1", "name": "Arimaddanapura"},
            {"date": "1000.1.1", "name": "Pagan"}
        ],
        "extra_other": ["Bagan"]
    },
    "Thayetmyo-Myanmar": {
        "canonical_name": "Thayet",
        "historical_names": [
            {"date": "1854.1.1", "name": "Thayetmyo"},
            {"date": "1989.6.18", "name": "Thayet"}
        ]
    },
    "Magway-Myanmar": {
        "canonical_name": "Magway",
        "historical_names": [
            {"date": "1886.1.1", "name": "Magwe"},
            {"date": "1989.6.18", "name": "Magway"}
        ]
    },
    "Shwebo-Myanmar": {
        "canonical_name": "Shwebo",
        "historical_names": [
            {"date": "1752.1.1", "name": "Mokksobo"},
            {"date": "1753.1.1", "name": "Yadana-theinga"},
            {"date": "1886.1.1", "name": "Shwebo"}
        ]
    },
    "Sagaing-Myanmar": {
        "canonical_name": "Sagaing",
        "historical_names": [
            {"date": "1315.1.1", "name": "Zeyapura"},
            {"date": "1364.1.1", "name": "Sagaing"}
        ]
    },
    "Taikkyi-Myanmar": {
        "canonical_name": "Taikkyi",
        "historical_names": [
            {"date": "1890.1.1", "name": "Taikkyi"}
        ]
    },
    "Myaungmya-Myanmar": {
        "canonical_name": "Myaungmya",
        "historical_names": [
            {"date": "1921.1.1", "name": "Myaungmya"}
        ]
    },
    "Kawthoung-Myanmar": {
        "canonical_name": "Kawthaung",
        "historical_names": [
            {"date": "1890.1.1", "name": "Victoria Point"},
            {"date": "1989.6.18", "name": "Kawthaung"}
        ],
        "extra_other": ["Kawthoung"]
    },
    "Myaydo-Myanmar": {
        "canonical_name": "Aunglan",
        "historical_names": [
            {"date": "1000.1.1", "name": "Myaydo"},
            {"date": "1853.1.1", "name": "Allanmyo"},
            {"date": "1989.6.18", "name": "Aunglan"}
        ],
        "extra_other": ["Myaydo"]
    },
    "Buthidaung Town-Myanmar": {
        "canonical_name": "Buthidaung",
        "historical_names": [
            {"date": "1890.1.1", "name": "Buthidaung"}
        ]
    },
    "Martaban-Myanmar": {
        "canonical_name": "Mottama",
        "historical_names": [
            {"date": "1000.1.1", "name": "Martaban"},
            {"date": "1989.6.18", "name": "Mottama"}
        ],
        "extra_other": ["Martaban"]
    },
    "Kyaikkami-Myanmar": {
        "canonical_name": "Kyaikkami",
        "historical_names": [
            {"date": "1826.1.1", "name": "Amherst"},
            {"date": "1989.6.18", "name": "Kyaikkami"}
        ]
    },
    "Myanaung-Myanmar": {
        "canonical_name": "Myanaung",
        "historical_names": [
            {"date": "1931.1.1", "name": "Myanaung"}
        ]
    },
    "Myawaddy-Myanmar": {
        "canonical_name": "Myawaddy",
        "historical_names": [
            {"date": "1890.1.1", "name": "Myawaddy"}
        ]
    },
    "Mingaladon-Myanmar": {
        "canonical_name": "Mingaladon",
        "historical_names": [
            {"date": "1887.1.1", "name": "Mingaladon"}
        ]
    },
    "Kawkareik-Myanmar": {
        "canonical_name": "Kawkareik",
        "historical_names": [
            {"date": "1890.1.1", "name": "Kawkareik"}
        ]
    },
    "Hpakan-Myanmar": {
        "canonical_name": "Hpakant",
        "historical_names": [
            {"date": "2005.1.1", "name": "Hpakant"}
        ],
        "extra_other": ["Hpakan"]
    },
    "Tachilek-Myanmar": {
        "canonical_name": "Tachileik",
        "historical_names": [
            {"date": "2000.1.1", "name": "Tachileik"}
        ],
        "extra_other": ["Tachilek"]
    },
    "Daik-u-Myanmar": {
        "canonical_name": "Daik-U",
        "historical_names": [
            {"date": "1995.1.1", "name": "Daik-U"}
        ],
        "extra_other": ["Daik-u"]
    },
    "Zalun-Myanmar": {
        "canonical_name": "Zalun",
        "historical_names": [
            {"date": "1990.1.1", "name": "Za Lun"},
            {"date": "2000.1.1", "name": "Zalun"}
        ]
    },
    "Tharyarwady-Myanmar": {
        "canonical_name": "Tharyarwady",
        "historical_names": [
            {"date": "1931.1.1", "name": "Tharawaddy"},
            {"date": "1989.6.18", "name": "Tharyarwady"}
        ]
    },
    "Letpandan-Myanmar": {
        "canonical_name": "Letpandan",
        "historical_names": [
            {"date": "1931.1.1", "name": "Letpadan"},
            {"date": "1989.6.18", "name": "Letpandan"}
        ]
    },
    "Aungban-Myanmar": {
        "canonical_name": "Aungban",
        "historical_names": [
            {"date": "1701.1.1", "name": "Hsamonghkam"},
            {"date": "1913.1.1", "name": "Aungban"}
        ]
    },
    "Halin-Myanmar": {
        "canonical_name": "Halin",
        "historical_names": [
            {"date": "-500.1.1", "name": "Halin"}
        ]
    },
    "Dhanyawadi-Myanmar": {
        "canonical_name": "Dhanyawadi",
        "historical_names": [
            {"date": "300.1.1", "name": "Dhanyawadi"}
        ]
    },
    "Maingmaw-Myanmar": {
        "canonical_name": "Maingmaw",
        "historical_names": [
            {"date": "100.1.1", "name": "Maingmaw"}
        ]
    },
    "Sri Ksetra Kingdom-Myanmar": {
        "canonical_name": "Sri Ksetra",
        "historical_names": [
            {"date": "-500.1.1", "name": "Sri Ksetra"}
        ]
    },

    # --- PHILIPPINES ---
    "Davao-Philippines": {
        "canonical_name": "Davao",
        "historical_names": [
            {"date": "1848.1.1", "name": "Nueva Vergara"},
            {"date": "1867.1.1", "name": "Davao"}
        ]
    },
    "Caloocan-Philippines": {
        "canonical_name": "Caloocan",
        "historical_names": [
            {"date": "1815.1.1", "name": "Caloocan"}
        ]
    },
    "Taguig-Philippines": {
        "canonical_name": "Taguig",
        "historical_names": [
            {"date": "1587.1.1", "name": "Taguig"}
        ]
    },
    "Zamboanga-Philippines": {
        "canonical_name": "Zamboanga",
        "historical_names": [
            {"date": "1400.1.1", "name": "Jambangan"},
            {"date": "1635.6.23", "name": "Villa de Zamboanga"},
            {"date": "1910.1.1", "name": "Zamboanga"}
        ]
    },
    "Valenzuela-Philippines": {
        "canonical_name": "Valenzuela",
        "historical_names": [
            {"date": "1623.1.1", "name": "Polo"},
            {"date": "1960.1.1", "name": "Valenzuela"}
        ]
    },
    "Cabanatuan City-Philippines": {
        "canonical_name": "Cabanatuan",
        "historical_names": [
            {"date": "1777.1.1", "name": "Cabanatuan"}
        ]
    },
    "Binan-Philippines": {
        "canonical_name": "Biñan",
        "historical_names": [
            {"date": "1571.1.1", "name": "Biñan"}
        ]
    },
    "NIA Valencia-Philippines": {
        "canonical_name": "Valencia",
        "historical_names": [
            {"date": "1959.1.16", "name": "Valencia"}
        ],
        "extra_other": ["NIA Valencia"]
    },
    "Mabalacat City-Philippines": {
        "canonical_name": "Mabalacat",
        "historical_names": [
            {"date": "1712.1.1", "name": "Mabalacat"}
        ]
    },
    "Roxas-Philippines_5": {
        "canonical_name": "Roxas",
        "historical_names": [
            {"date": "1569.1.1", "name": "Capiz"},
            {"date": "1951.4.11", "name": "Roxas"}
        ]
    },
    "Tondo-Philippines": {
        "canonical_name": "Tondo",
        "historical_names": [
            {"date": "900.1.1", "name": "Tondo"}
        ]
    },
    "Cavite City-Philippines": {
        "canonical_name": "Cavite",
        "historical_names": [
            {"date": "1571.1.1", "name": "Cavite"}
        ]
    },
    "Iriga City-Philippines": {
        "canonical_name": "Iriga",
        "historical_names": [
            {"date": "1578.1.1", "name": "Iriga"}
        ]
    },
    "Plaridel-Philippines": {
        "canonical_name": "Plaridel",
        "historical_names": [
            {"date": "1602.1.1", "name": "Quingua"},
            {"date": "1936.1.1", "name": "Plaridel"}
        ]
    },
    "Manolo Fortich-Philippines": {
        "canonical_name": "Manolo Fortich",
        "historical_names": [
            {"date": "1946.1.1", "name": "Maluko"},
            {"date": "1957.6.21", "name": "Manolo Fortich"}
        ]
    },
    "Carmona-Philippines": {
        "canonical_name": "Carmona",
        "historical_names": [
            {"date": "1857.2.20", "name": "Carmona"}
        ]
    },
    "San Juan-Philippines": {
        "canonical_name": "San Juan",
        "historical_names": [
            {"date": "1602.1.1", "name": "San Juan del Monte"},
            {"date": "1960.1.1", "name": "San Juan"}
        ]
    },
    "Ozamiz City-Philippines": {
        "canonical_name": "Ozamiz",
        "historical_names": [
            {"date": "1757.1.1", "name": "Misamis"},
            {"date": "1948.7.16", "name": "Ozamiz"}
        ]
    },
    "Jaen-Philippines": {
        "canonical_name": "Jaen",
        "historical_names": [
            {"date": "1865.1.1", "name": "Jaen"}
        ]
    }
}

def clean_canonical_name(name):
    cn = name.strip()
    # Strip administrative suffixes
    for suffix in [" City", " Town", " Kingdom", " State", " Municipality"]:
        if cn.endswith(suffix):
            cn = cn[:-len(suffix)].strip()
    return cn

def is_spam_alias(s, country):
    low = s.lower().strip()
    # Keep valid native Burmese script for Myanmar
    has_burmese = bool(re.search(r"[\u1000-\u109F\uA9E0-\uA9FF]", s))
    if country == "Myanmar" and has_burmese:
        # Check that it doesn't contain CJK/Arabic/Cyrillic
        if re.search(r"[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]", s):
            return True
        return False
        
    words = [w.strip() for w in re.split(r"[\s\-_]+", low) if w.strip()]
    
    # Check if contains any Arabic romanized token
    if any(w in ARABIC_ROMANIZED_TOKENS for w in words):
        return True
        
    # Check if ends with pinyin admin token
    if len(words) > 1 and words[-1] in PINYIN_ADMIN_TOKENS:
        return True
        
    # Check if matches known pinyin phrase
    for p in PINYIN_PHRASES:
        if p in low:
            return True
            
    # Check for vowelless Latin tokens (except short uppercase acronyms <= 4 chars like SJDM, DVO, MEP, etc.)
    for w in words:
        if re.match(r"^[a-z]+$", w) and len(w) >= 4 and not re.search(r"[aeiouy]", w):
            if not (s.isupper() and len(s) <= 4):
                return True
            
    return False

def clean_alias_entry(a, country, canonical_name):
    if not a or not isinstance(a, str):
        return None
    s = a.strip()
    s = re.sub(r"\(.*?\)", "", s).strip()
    s = s.strip("-").strip()
    if not s:
        return None
    if CORRUPT_CHARS.search(s):
        return None
    if country in ["Malaysia", "Philippines", "Indonesia", "Singapore", "Brunei", "East Timor"]:
        if BANNED_FOR_LATIN_ONLY.search(s):
            return None
    elif country == "Myanmar":
        if BANNED_GENERAL.search(s):
            return None
    if is_spam_alias(s, country):
        return None
    if s.lower() == canonical_name.lower():
        return None
    return s

def sort_date_key(h):
    parts = [int(p) for p in h["date"].split(".")]
    return parts

def process_settlement(s):
    k = s["key"]
    raw_name = s["name"]
    country = s["country"]
    latest_year = s.get("latest_year") or 2025
    earliest_year = s.get("earliest_year") or 1200
    foundation_year = s.get("foundation_year")
    
    # 1. Determine canonical_name and historical_names
    if k in CUSTOM_ENRICHMENTS:
        custom = CUSTOM_ENRICHMENTS[k]
        canonical_name = custom["canonical_name"]
        hist_names = list(custom["historical_names"])
        extra_other = custom.get("extra_other", [])
    else:
        canonical_name = clean_canonical_name(raw_name)
        extra_other = []
        
        # Check existing_historical_names
        existing_hn = s.get("existing_historical_names", [])
        clean_hn = []
        for h in existing_hn:
            h_name = clean_canonical_name(h.get("name", ""))
            # Check for banned admin words
            is_banned = False
            for bw in BANNED_ADMIN:
                if bw in h_name.lower():
                    is_banned = True
                    break
            if not is_banned and h_name and not CORRUPT_CHARS.search(h_name):
                clean_hn.append({"date": h["date"], "name": h_name})
        
        # Deduplicate clean_hn adjacent entries
        deduped = []
        for h in sorted(clean_hn, key=sort_date_key):
            if not deduped or deduped[-1]["name"] != h["name"]:
                deduped.append(h)
        
        # Check terminal anchor
        if latest_year >= 1950:
            if not deduped:
                # Plausible year
                yr = foundation_year if (foundation_year is not None and foundation_year > -5000) else earliest_year
                if yr is None or yr > 2025:
                    yr = 1200
                deduped = [{"date": f"{yr}.1.1", "name": canonical_name}]
            elif deduped[-1]["name"] != canonical_name:
                deduped.append({"date": "1950.1.1", "name": canonical_name})
        else:
            if not deduped:
                yr = foundation_year if foundation_year is not None else earliest_year
                if yr is None:
                    yr = 1000
                deduped = [{"date": f"{yr}.1.1", "name": canonical_name}]
        
        # Final deduplication
        final_dedup = []
        for h in sorted(deduped, key=sort_date_key):
            if not final_dedup or final_dedup[-1]["name"] != h["name"]:
                final_dedup.append(h)
        hist_names = final_dedup

    # Ensure terminal anchor matches canonical_name if latest_year >= 1950
    if latest_year >= 1950:
        if not hist_names:
            hist_names = [{"date": f"{earliest_year}.1.1", "name": canonical_name}]
        elif hist_names[-1]["name"] != canonical_name:
            hist_names.append({"date": "1950.1.1", "name": canonical_name})
            
    # Re-deduplicate adjacent identical names (case-insensitive check)
    clean_sorted_hist = []
    for h in sorted(hist_names, key=sort_date_key):
        if not clean_sorted_hist or clean_sorted_hist[-1]["name"].lower() != h["name"].lower():
            clean_sorted_hist.append(h)
        elif clean_sorted_hist and clean_sorted_hist[-1]["name"].lower() == h["name"].lower():
            # Update to match canonical spelling if it matches canonical_name
            if h["name"] == canonical_name:
                clean_sorted_hist[-1] = h
    hist_names = clean_sorted_hist

    # 2. Process other_names
    other_names = []
    seen = set()
    seen.add(canonical_name.lower())
    
    # Include original raw_name if different from canonical
    if raw_name.lower() != canonical_name.lower():
        ca = clean_alias_entry(raw_name, country, canonical_name)
        if ca and ca.lower() not in seen:
            other_names.append(ca)
            seen.add(ca.lower())

    for eo in extra_other:
        ca = clean_alias_entry(eo, country, canonical_name)
        if ca and ca.lower() not in seen:
            other_names.append(ca)
            seen.add(ca.lower())

    for al in s.get("known_aliases", []):
        ca = clean_alias_entry(al, country, canonical_name)
        if ca and ca.lower() not in seen:
            other_names.append(ca)
            seen.add(ca.lower())

    for h in hist_names:
        hnm = h["name"]
        if hnm.lower() not in seen:
            other_names.append(hnm)
            seen.add(hnm.lower())

    out_record = {
        "key": k,
        "canonical_name": canonical_name,
        "coords_lat_lng": s["coords_lat_lng"],
        "country": country,
        "latest_year": latest_year,
        "existing_meta_index": s.get("existing_meta_index"),
        "historical_names": hist_names,
        "other_names": other_names
    }
    return out_record

def main():
    for b in range(25, 33):
        in_path = f"tests/mandala_toponymy_swarm/swarm_in_{b:03d}.json"
        out_path = f"tests/mandala_toponymy_swarm/resolved_batch_{b:03d}.json"
        with open(in_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        resolved_settlements = []
        for s in data["settlements"]:
            rec = process_settlement(s)
            resolved_settlements.append(rec)
            
        out_data = {
            "batch_index": b,
            "settlements": resolved_settlements
        }
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, ensure_ascii=False, indent=2)
            
        print(f"Wrote {out_path} with {len(resolved_settlements)} settlements.")

if __name__ == "__main__":
    main()
