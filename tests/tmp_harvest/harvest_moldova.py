import json
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict

import requests

OUT_DIR = "tests/tmp_harvest"
os.makedirs(OUT_DIR, exist_ok=True)
HEADERS = {"User-Agent": "SVEA-Project/1.0 (https://github.com/confoederatio; research@confoederatio.org)"}

TRANSLIT_RU = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "і": "i", "ѣ": "e", "ѳ": "f", "ѵ": "i",
}

def strip_accents(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))

def norm_ro(s):
    s = s.lower().strip()
    s = s.replace("ş", "s").replace("ș", "s").replace("ţ", "t").replace("ț", "t")
    s = s.replace("î", "i").replace("â", "a").replace("ă", "a")
    s = strip_accents(s)
    s = re.sub(r"\b(comuna|satul|orasul|or\.|s\.|mun\.|municipiul|primaria|loc\.\s*st\.\s*c\.\s*f\.|loc\.)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    s = re.sub(r"\bnoui\b", "noi", s)
    s = re.sub(r"\bvechiu\b", "vechi", s)
    return s

def norm_phonetic(s):
    """Phonetic Romanian/Russian-transliterated normalizer for 1897 & 1930 OCR matching."""
    s = norm_ro(s)
    s = s.replace(" ", "")
    s = s.replace("shch", "s").replace("sh", "s").replace("ch", "c").replace("ts", "t").replace("zh", "j")
    s = s.replace("kh", "h").replace("gh", "g").replace("ph", "f")
    s = s.replace("ya", "a").replace("ia", "a").replace("ea", "a").replace("yu", "u").replace("iu", "u")
    s = s.replace("y", "i").replace("e", "i").replace("o", "u")
    # Collapse repeated letters
    s = re.sub(r"(.)\1+", r"\1", s)
    return s

def translit_ru_ro(s):
    """Transliterate Russian Cyrillic using Romanian-friendly phonetic rules."""
    m = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "j", "з": "z", "и": "i", "й": "i", "к": "c", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "t", "ч": "c", "ш": "s", "щ": "st",
        "ъ": "", "ы": "i", "ь": "i", "э": "e", "ю": "iu", "я": "ia",
        "і": "i", "ѣ": "e", "ѳ": "f", "ѵ": "i",
    }
    res = "".join(m.get(ch, ch) for ch in s.lower())
    return re.sub(r"[^a-z0-9]+", " ", res).strip()

def translit_ru(s):
    res = "".join(TRANSLIT_RU.get(ch, ch) for ch in s.lower())
    return re.sub(r"[^a-z0-9]+", " ", res).strip()

def norm_ru(s):
    return re.sub(r"[^а-яёіѣѳѵa-z0-9]+", " ", s.lower().strip()).strip()

def fetch_text(url):
    fn = os.path.join(OUT_DIR, re.sub(r"[^A-Za-z0-9._-]+", "_", url))
    if os.path.exists(fn):
        return open(fn, "r", encoding="utf-8").read()
    r = requests.get(url, timeout=30, headers=HEADERS)
    r.encoding = "utf-8"
    with open(fn, "w", encoding="utf-8") as f:
        f.write(r.text)
    return r.text

def parse_popstat_rows(html):
    rows = re.split(r"<tr[^>]*>", html, flags=re.I)[1:]
    out = []
    for row in rows:
        parts = re.split(r"<t[hd][^>]*>", row, flags=re.I)[1:]
        if not parts:
            continue
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip() for c in parts]
        out.append(("<th" in row.lower(), cells))
    return out

def load_md_geo():
    places = []
    seen_gn = set()
    with zipfile.ZipFile("histmap/1.data_raw/population_regional/MAGNETIC/_shared/settlement_sources/pale_east_prussia/gn_MD.zip") as z:
        for line in z.open("MD.txt").read().decode("utf-8").splitlines():
            cols = line.split("\t")
            if len(cols) < 15 or cols[6] != "P":
                continue
            lat, lon = float(cols[4]), float(cols[5])
            pop = int(cols[14] or 0)
            alts = [a.strip() for a in cols[3].split(",") if a.strip()] if cols[3] else []
            places.append({
                "name": cols[1].strip(), "ascii": cols[2].strip(),
                "lat": round(lat, 5), "lon": round(lon, 5),
                "fcode": cols[7], "pop": pop, "alts": alts,
            })
            seen_gn.add((norm_ro(cols[1]), round(lat, 2), round(lon, 2)))

    with open("histmap/1.data_raw/population_regional/MAGNETIC/_shared/settlement_sources/pale_east_prussia/wd_moldova_direct.json", "r", encoding="utf-8") as f:
        wd = json.load(f)
    for row in wd:
        nm = row.get("itemLabel", {}).get("value", "").strip()
        pt = row.get("coord", {}).get("value", "")
        m = re.match(r"Point\(([-\d.]+)\s+([-\d.]+)\)", pt)
        if not nm or not m:
            continue
        lon, lat = float(m.group(1)), float(m.group(2))
        if not (45.4 <= lat <= 48.55 and 26.6 <= lon <= 30.2):
            continue
        key = (norm_ro(nm), round(lat, 2), round(lon, 2))
        if key not in seen_gn:
            seen_gn.add(key)
            places.append({
                "name": nm, "ascii": strip_accents(nm),
                "lat": round(lat, 5), "lon": round(lon, 5),
                "fcode": "PPL", "pop": int(float(row.get("pop", {}).get("value", 0) or 0)), "alts": [],
            })

    idx_ro = defaultdict(list)
    idx_ru = defaultdict(list)
    idx_tr = defaultdict(list)
    idx_ph = defaultdict(list)
    for i, p in enumerate(places):
        for cand in [p["name"], p["ascii"]] + p["alts"]:
            if re.search(r"[А-Яа-яЁё]", cand):
                k = norm_ru(cand)
                if k:
                    idx_ru[k].append(i)
                for kt in (translit_ru(cand), translit_ru_ro(cand)):
                    if kt:
                        idx_tr[kt].append(i)
            else:
                k = norm_ro(cand)
                if k:
                    idx_ro[k].append(i)
            kp = norm_phonetic(cand if not re.search(r"[А-Яа-яЁё]", cand) else translit_ru_ro(cand))
            if kp and len(kp) >= 4:
                idx_ph[kp].append(i)
                # Also index g->h variant for Russian-to-Romanian
                if "g" in kp:
                    idx_ph[kp.replace("g", "h")].append(i)
    return places, idx_ro, idx_ru, idx_tr, idx_ph

places, idx_ro, idx_ru, idx_tr, idx_ph = load_md_geo()
print(f"Loaded {len(places)} Moldova places")

def pick_best(cands, hint_lat=None, hint_lon=None, max_deg=None):
    if not cands:
        return None
    if max_deg is not None and hint_lat is not None:
        cands = [i for i in cands if (places[i]["lat"] - hint_lat)**2 + (places[i]["lon"] - hint_lon)**2 <= max_deg**2]
        if not cands:
            return None
    if len(cands) == 1:
        return cands[0]
    if hint_lat is not None and hint_lon is not None:
        return min(cands, key=lambda i: (places[i]["lat"] - hint_lat)**2 + (places[i]["lon"] - hint_lon)**2)
    return max(cands, key=lambda i: (1 if places[i]["fcode"] in ("PPLC", "PPLA") else 0, places[i]["pop"]))

CITE_1897 = "Troinitsky, N. A. (ed.) (1905). Naselennye mesta Rossiiskoi imperii v 500 i bolee zhitelei po dannym pervoi vseobshchei perepisi naseleniya 1897 g. St. Petersburg: Obshchestvennaya polza (via pop-stat.mashke.org)."
CITE_1930 = "Manuila, S. (ed.) (1938). Recensamantul General al Populatiei Romaniei din 29 Decemvrie 1930, Vol. II: Neam, Limba Materna, Religie. Bucuresti: Institutul Central de Statistica."
CITE_USSR = "Central Statistical Administration of the USSR / Moldavian SSR (1959, 1970, 1979, 1989). All-Union Population Censuses (via pop-stat.mashke.org/moldova-cities.htm)."
CITE_NBS = "National Bureau of Statistics of the Republic of Moldova (2004, 2014, 2024). Population and Housing Censuses (statistica.gov.md; via pop-stat.mashke.org)."

records = {}
def ensure_rec(pi):
    if pi not in records:
        p = places[pi]
        records[pi] = {
            "name": p["name"], "country": "Moldova", "coords": [p["lat"], p["lon"]],
            "population": {}, "citations": set(), "urls": set(), "other_names": set(),
        }
    return records[pi]

def add_pop(pi, year, val, citation, url, alt_name=None):
    if val is None or val <= 0:
        return
    rec = ensure_rec(pi)
    ys = str(year)
    if ys not in rec["population"]:
        rec["population"][ys] = int(val)
    rec["citations"].add(citation)
    rec["urls"].add(url)
    if alt_name and alt_name.strip() and alt_name.strip().lower() != rec["name"].lower():
        rec["other_names"].add(alt_name.strip())

# 1. moldova-cities.htm (NOTE: has a second <th> header row before Transnistria cities!)
URL_MD_CITIES = "http://pop-stat.mashke.org/moldova-cities.htm"
rows_mc = parse_popstat_rows(fetch_text(URL_MD_CITIES))
col_years = {}

mc_matched = 0
for is_th, cells in rows_mc:
    if is_th:
        new_cols = {}
        for ci, h in enumerate(cells):
            m = re.match(r"^(\d{4})-\d{2}-\d{2}$", h.strip())
            if m:
                new_cols[ci] = int(m.group(1))
        if new_cols:
            col_years = new_cols
            print("moldova-cities header cols:", col_years)
        continue
    if not cells or len(cells) < 5:
        continue
    raw_nm = re.sub(r"\d+\)$", "", cells[0]).strip()
    if not raw_nm or raw_nm.startswith("Note:"):
        continue
    # Handle "Bender (Tighina)"
    cands_nm = [raw_nm]
    mp = re.match(r"^([^(]+)\(([^)]+)\)", raw_nm)
    if mp:
        cands_nm = [mp.group(1).strip(), mp.group(2).strip()]
    pi = None
    for cn in cands_nm:
        k = norm_ro(cn)
        if k == "dniestrovsc":
            k = "dnestrovsc"
        pi = pick_best(idx_ro.get(k))
        if pi is not None:
            break
    if pi is None:
        print("  UNMATCHED moldova-cities:", raw_nm)
        continue
    mc_matched += 1
    for ci, yr in col_years.items():
        if ci < len(cells):
            v = cells[ci].strip()
            if re.match(r"^\d+,\d{3}$", v) or re.match(r"^\d+$", v):
                num = int(v.replace(",", ""))
                if num > 0:
                    if yr == 1897:
                        cite = CITE_1897
                    elif yr in (1920, 1923, 1926, 1939):
                        cite = "Central Statistical Administration of the USSR (1920, 1923, 1926, 1939). All-Union / Urban Censuses (via pop-stat.mashke.org/moldova-cities.htm)."
                    elif yr == 1930:
                        cite = CITE_1930 + " (via pop-stat.mashke.org)"
                    elif yr in (1959, 1970, 1979, 1989):
                        cite = CITE_USSR
                    else:
                        cite = CITE_NBS
                    add_pop(pi, yr, num, cite, URL_MD_CITIES, raw_nm)
print("moldova-cities matched:", mc_matched)

# 2. moldova-census.htm (including 2014 single-village communes!)
URL_MD_CENSUS = "http://pop-stat.mashke.org/moldova-census.htm"
rows_cen = parse_popstat_rows(fetch_text(URL_MD_CENSUS))
raion_centers = {norm_ro(p["name"]): (p["lat"], p["lon"]) for p in places if p["fcode"] in ("PPLC", "PPLA")}

# Group rows by comuna blocks to detect single-village communes for 2014
cur_raion = None
cur_comuna = None  # (name, p2004, p2014, p2024, children_rows)
cen_matched = 0

def flush_comuna(com):
    global cen_matched
    if not com:
        return
    cname, c04, c14, c24, children, r_hint = com
    single_village = (len(children) == 1)
    for lbl, p04, p14, p24 in children:
        if single_village and not p14 and c14 and p04 and c04 and p04 == c04:
            p14 = c14
        nm_clean = re.sub(r"^(or\.|s\.|mun\.|loc\.\s*st\.\s*c\.\s*f\.|loc\.)\s*", "", lbl, flags=re.I).strip()
        nm_clean = re.sub(r"\d+\)$", "", nm_clean).strip()
        if not nm_clean:
            continue
        cands_nm = [nm_clean]
        if ", loc." in nm_clean:
            cands_nm.append(nm_clean.split(",")[0].strip())
        mp = re.match(r"^([^(]+)\(([^)]+)\)", nm_clean)
        if mp:
            cands_nm = [mp.group(1).strip(), mp.group(2).strip()]
        pi = None
        for cn in cands_nm:
            pi = pick_best(idx_ro.get(norm_ro(cn)), *(r_hint or (None, None)))
            if pi is not None:
                break
        if pi is None:
            continue
        cen_matched += 1
        if p04: add_pop(pi, 2004, p04, CITE_NBS, URL_MD_CENSUS, nm_clean)
        if p14: add_pop(pi, 2014, p14, CITE_NBS, URL_MD_CENSUS, nm_clean)
        if p24: add_pop(pi, 2024, p24, CITE_NBS, URL_MD_CENSUS, nm_clean)

def to_int(s):
    d = re.sub(r"[^\d]", "", s or "")
    return int(d) if d else None

for is_th, cells in rows_cen[1:]:
    if not cells or len(cells) < 4:
        continue
    lbl = cells[0].strip()
    if is_th:
        flush_comuna(cur_comuna)
        cur_comuna = None
        rl = re.sub(r"^(raionul|municipiul|uta)\s+", "", lbl, flags=re.I).strip()
        cur_raion = raion_centers.get(norm_ro(rl))
        continue
    p04, p14, p24 = to_int(cells[1]), to_int(cells[2]), to_int(cells[3])
    if re.match(r"^(comuna|primăria)\b", lbl, re.I):
        flush_comuna(cur_comuna)
        cur_comuna = [lbl, p04, p14, p24, [], cur_raion]
    else:
        if cur_comuna is not None:
            cur_comuna[4].append((lbl, p04, p14, p24))
        else:
            # Direct town/sector row (e.g. or. Bălți)
            flush_comuna([lbl, p04, p14, p24, [(lbl, p04, p14, p24)], cur_raion])
flush_comuna(cur_comuna)
print("moldova-census matched:", cen_matched)

# 3. 1897 Russian Imperial Census (bessarabskaja, podolskaja, hersonskaja)
BESS_UYEZD_HINTS = {
    "белецкий": (47.76, 27.92), "бендерский": (46.83, 29.47), "кагульский": (45.90, 28.19),
    "кишиневский": (47.01, 28.86), "оргеевский": (47.38, 28.82), "сорокский": (48.16, 28.29),
    "хотинский": (48.35, 27.15), "аккерманский": (46.45, 29.75), "измаильский": (45.75, 28.35),
    "тираспольский": (46.84, 29.63), "ананьевский": (47.55, 29.30),
    "ольгопольский": (48.05, 28.85), "балцкий": (47.80, 29.05),
}

def match_1897(raw_name, uhint, max_deg=0.55):
    nm = re.sub(r",\s*(у\.г\.|г\.|м\.|с\.|д\.|кол\.|клн\.|пос\.|пслк\.|прслк\.|сл\.|х\.|пр\.|ст\.|сц\.|им\.|з\.|ф\.|м-ко|р\.|ур\.|выс\.).*$", "", raw_name.strip())
    variants = [nm]
    mp = re.match(r"^([^(]+)\(([^)]+)\)", nm)
    if mp:
        variants = [mp.group(1).strip(), mp.group(2).strip()]
    for v in variants:
        k = norm_ru(v)
        if k in idx_ru:
            pi = pick_best(idx_ru[k], *(uhint or (None, None)), max_deg=max_deg if uhint else None)
            if pi is not None: return pi, v
        for kt in (translit_ru(v), translit_ru_ro(v)):
            if kt in idx_tr:
                pi = pick_best(idx_tr[kt], *(uhint or (None, None)), max_deg=max_deg if uhint else None)
                if pi is not None: return pi, v
            if kt in idx_ro:
                pi = pick_best(idx_ro[kt], *(uhint or (None, None)), max_deg=max_deg if uhint else None)
                if pi is not None: return pi, v
        # Phonetic match (strictly bounded within uyezd radius <= 0.45 deg ~ 45km)
        if uhint:
            kp = norm_phonetic(translit_ru_ro(v))
            for cand_kp in (kp, kp.replace("g", "h")):
                if cand_kp in idx_ph:
                    pi = pick_best(idx_ph[cand_kp], *uhint, max_deg=0.45)
                    if pi is not None: return pi, v
    return None, nm

m1897_matched = 0
for gub in ["bessarabskaja", "hersonskaja", "podolskaja"]:
    u1897 = f"http://pop-stat.mashke.org/empire-census-1897-religion/{gub}.htm"
    rows_97 = parse_popstat_rows(fetch_text(u1897))
    cur_uhint, cur_uname = None, ""
    for is_th, cells in rows_97[1:]:
        if not cells: continue
        lbl = cells[0].strip()
        if is_th:
            cur_uname = lbl
            cur_uhint = next((v for k, v in BESS_UYEZD_HINTS.items() if k in lbl.lower()), None)
            continue
        if gub in ("hersonskaja", "podolskaja") and not any(k in cur_uname.lower() for k in ["тирасполь", "ананьев", "ольгополь", "балт"]):
            continue
        tot_s = re.sub(r"[^\d]", "", cells[1]) if len(cells) > 1 else ""
        if not tot_s: continue
        is_border = gub in ("hersonskaja", "podolskaja") or any(u in cur_uname.lower() for u in ["аккерман", "измаил", "хотин"])
        pi, used_nm = match_1897(lbl, cur_uhint, max_deg=0.65 if not is_border else 0.45)
        if pi is None: continue
        m1897_matched += 1
        add_pop(pi, 1897, int(tot_s), CITE_1897, u1897, used_nm)
print("1897 matched to Moldova:", m1897_matched)

# 4. 1930 Romanian General Census (Vol. II, BOTH Part 1 and Part 2)
JUD_HINTS = {
    "Bălți": (47.76, 27.92), "Cahul": (45.95, 28.25), "Cetatea-Albă": (46.45, 29.75),
    "Hotin": (48.30, 27.15), "Ismail": (45.75, 28.35), "Lăpușna": (47.01, 28.70),
    "Orhei": (47.38, 28.82), "Soroca": (48.10, 28.25), "Tighina": (46.75, 29.20),
}
PART1_RANGES = {
    "Bălți": range(206, 215, 2), "Cahul": range(258, 263, 2), "Cetatea-Albă": range(282, 287, 2),
    "Hotin": range(374, 381, 2), "Ismail": range(422, 425, 2), "Lăpușna": range(426, 433, 2),
    "Orhei": range(488, 495, 2), "Soroca": range(580, 587, 2), "Tighina": range(620, 625, 2),
}
PART2_RANGES = {
    "Bălți": range(703, 708), "Cahul": range(729, 732), "Cetatea-Albă": range(741, 744),
    "Hotin": range(787, 791), "Ismail": range(811, 813), "Lăpușna": range(813, 817),
    "Orhei": range(844, 848), "Soroca": range(890, 894), "Tighina": range(910, 913),
}
p1_map = {p: j for j, r in PART1_RANGES.items() for p in r}
p2_map = {p: j for j, r in PART2_RANGES.items() for p in r}

def clean_int_toks(tokens):
    s = re.sub(r"[^\d]", "", "".join(tokens))
    return int(s) if s else None

URL_1930 = "https://archive.org/details/recensamantul-romaniei-din-1930-vol.-2"
p1_hits, p2_hits = {}, {}  # pi -> tot
page_idx = 0
for event, elem in ET.iterparse("tests/tmp_harvest/ro1930_v2.xml", events=("end",)):
    if elem.tag == "OBJECT":
        page_idx += 1
        is_p1 = page_idx in p1_map
        is_p2 = page_idx in p2_map
        if is_p1 or is_p2:
            jud = p1_map[page_idx] if is_p1 else p2_map[page_idx]
            jhint = JUD_HINTS[jud]
            words = [
                (int(w.attrib["coords"].split(",")[0]), int(w.attrib["coords"].split(",")[3]), w.text)
                for w in elem.iter("WORD") if w.text and "coords" in w.attrib
            ]
            # Find left_bar before TOTAL column
            x_min_bar = 660 if is_p1 else 540
            x_max_bar = 850 if is_p1 else 820
            bars = [x for x, y, t in words if 750 < y < 3000 and x_min_bar <= x <= x_max_bar and t in ("|", "||", "!", "]")]
            if bars:
                left_bar = Counter(round(x / 10) * 10 for x in bars).most_common(1)[0][0]
                rbars = [x for x, y, t in words if 750 < y < 3000 and (left_bar + 85) <= x <= (left_bar + 175) and t in ("|", "||", "!", "]")]
                right_bar = Counter(round(x / 10) * 10 for x in rbars).most_common(1)[0][0] if rbars else left_bar + 130

                # Cluster words into tight y-rows (within 10px) anchored on name tokens
                # Exclude footnote band (y > 2920)
                name_words = sorted([w for w in words if 760 <= w[1] <= 2920 and (left_bar - 480) <= w[0] < (left_bar - 10)], key=lambda z: (z[1], z[0]))
                # Group consecutive name words within dy <= 10 into rows
                y_clusters = []
                for x, y, t in name_words:
                    if not y_clusters or abs(y - y_clusters[-1][0]) > 10:
                        y_clusters.append([y, [(x, y, t)]])
                    else:
                        y_clusters[-1][1].append((x, y, t))
                for y_mid, n_list in y_clusters:
                    raw_name = " ".join(t for _, _, t in sorted(n_list, key=lambda z: z[0]))
                    low = raw_name.lower()
                    if not raw_name or any(k in low for k in ["procent", "procen", "total", "tolal", "jude", "plasa ", "pinsa ", "vezi ", "notel", "inclusiv", "locuitori", "mânăstirea", "manastirea", "pag."]):
                        continue
                    if re.match(r"^[\d\*]+[\)\.]\s*inclusiv", low):
                        continue
                    # Collect total and col2 words strictly within +-10px of y_mid
                    tot_toks = [t for x, y, t in sorted(words, key=lambda z: z[0]) if abs(y - y_mid) <= 10 and (left_bar + 12) <= x <= (right_bar - 8)]
                    col2_toks = [t for x, y, t in sorted(words, key=lambda z: z[0]) if abs(y - y_mid) <= 10 and (right_bar + 10) <= x <= (right_bar + 140)]
                    nm = re.sub(r"[\.\-_=\*]{2,}.*$", "", raw_name)
                    nm = re.sub(r"^[|\[\]!\d\.\s]+", "", nm)
                    nm = re.sub(r"^(Ora[șs]ul|Municipiul)\s+", "", nm, flags=re.I)
                    nm = re.sub(r"\s+", " ", nm).strip(" ,.;:-")
                    tot = clean_int_toks(tot_toks)
                    c2 = clean_int_toks(col2_toks)
                    if not nm or len(nm) < 3 or not tot or tot < 40 or tot > 200000:
                        continue
                    if c2 and c2 > 50 and tot > 3 * c2 and str(tot).startswith("1"):
                        cand_tot = int(str(tot)[1:])
                        if cand_tot >= c2:
                            tot = cand_tot
                    if c2 and tot < c2 * 0.85:
                        continue
                    k = norm_ro(nm)
                    cands = idx_ro.get(k)
                    if not cands:
                        kp = norm_phonetic(nm)
                        cands = idx_ph.get(kp)
                    if not cands:
                        continue
                    max_d = 0.65 if jud in ("Hotin", "Cetatea-Albă", "Ismail") else 0.85
                    pi = pick_best(cands, *jhint, max_deg=max_d)
                    if pi is None:
                        continue
                    # Cross-check against 1897 / 2004: reject obvious OCR digit-drop (< 0.22 * 1897 when 1897 exists)
                    prev897 = records.get(pi, {}).get("population", {}).get("1897")
                    if prev897 and tot < 0.22 * prev897:
                        continue
                    if is_p1:
                        p1_hits[pi] = (tot, nm)
                    else:
                        p2_hits[pi] = (tot, nm)
        elem.clear()

# Merge Part 1 and Part 2 (prefer Part 2 when both agree or Part 2 exists, fallback Part 1)
all_1930_pis = set(p1_hits) | set(p2_hits)
for pi in all_1930_pis:
    tot, nm = p2_hits.get(pi) or p1_hits.get(pi)
    add_pop(pi, 1930, tot, CITE_1930, URL_1930, nm)
print(f"1930 XML matched: Part1={len(p1_hits)}, Part2={len(p2_hits)}, Union={len(all_1930_pis)}")

out_list = []
for pi, rec in sorted(records.items(), key=lambda x: x[1]["name"]):
    if not rec["population"]:
        continue
    pop_sorted = {k: rec["population"][k] for k in sorted(rec["population"].keys(), key=lambda y: int(y))}
    alts_dedup = []
    seen_a = {rec["name"].lower()}
    for a in sorted(rec["other_names"]):
        if a.lower() not in seen_a:
            seen_a.add(a.lower())
            alts_dedup.append(a)
    out_list.append({
        "name": rec["name"],
        "other_names": alts_dedup,
        "country": "Moldova",
        "coords": rec["coords"],
        "population": pop_sorted,
        "source_citation": " ; ".join(sorted(rec["citations"])),
        "source_url": " ; ".join(sorted(rec["urls"])),
    })

with open(os.path.join(OUT_DIR, "moldova_harvest.json"), "w", encoding="utf-8") as f:
    json.dump(out_list, f, ensure_ascii=False, indent=2)

yr_cov = Counter()
for r in out_list:
    for y in r["population"]:
        yr_cov[y] += 1
print(f"TOTAL MOLDOVA SETTLEMENTS: {len(out_list)}")
print("Year coverage:", dict(sorted(yr_cov.items())))
