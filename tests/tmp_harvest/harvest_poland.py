import csv
import json
import os
import re
import time
import unicodedata
import zipfile
from collections import Counter, defaultdict

import requests

OUT_DIR = "tests/tmp_harvest"
os.makedirs(OUT_DIR, exist_ok=True)
HEADERS = {"User-Agent": "SVEA-Project/1.0 (https://github.com/confoederatio; research@confoederatio.org)"}

def strip_accents(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))

def norm_pl(s):
    s = s.lower().strip()
    s = s.replace("ł", "l")
    s = strip_accents(s)
    s = re.sub(r"^(m\.|gm\.\s*m\.|gm\.\s*w\.|gm\.|gmina|miasto|powiat)\s+", "", s)
    s = re.sub(r"\s*\([^)]*\)$", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s

def translit_ru_pl(s):
    """Transliterate pre-1918 Russian Cyrillic to Polish-compatible Latin."""
    m = {
        "а": "a", "б": "b", "в": "w", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "z", "з": "z", "и": "i", "й": "j", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "ch", "ц": "c", "ч": "cz", "ш": "sz", "щ": "szcz",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "ju", "я": "ja",
        "і": "i", "ѣ": "e", "ѳ": "f", "ѵ": "i",
    }
    res = "".join(m.get(ch, ch) for ch in s.lower())
    res = res.replace("rz", "rz").replace("sz", "sz").replace("cz", "cz")
    return re.sub(r"[^a-z0-9]+", " ", res).strip()

def norm_pl_phonetic(s):
    s = norm_pl(s)
    s = s.replace(" ", "")
    s = s.replace("szcz", "s").replace("sz", "s").replace("cz", "c").replace("rz", "z").replace("ch", "h")
    s = s.replace("dz", "z").replace("w", "v").replace("ó", "u").replace("u", "o")
    s = s.replace("ja", "a").replace("ia", "a").replace("ie", "e").replace("je", "e").replace("y", "i")
    s = re.sub(r"(.)\1+", r"\1", s)
    return s

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

# Eastern Congress Poland seam definition:
# Podlaskie (admin1=81), Lubelskie (admin1=75), Eastern Mazowieckie (admin1=78, specific powiats)
EAST_MAZ_POWIATS = {
    "garwoliński", "łosicki", "makowski", "ostrołęcki", "m. ostrołęka",
    "ostrowski", "siedlecki", "m. siedlce", "sokołowski", "węgrowski",
}
EAST_MAZ_ADMIN2 = {
    "1403", "1410", "1411", "1415", "1416", "1426", "1429", "1433", "1461", "1464",
}

# Load GeoNames PL.txt filtered to Eastern Poland seam
def load_pl_geo():
    places = []
    with zipfile.ZipFile("histmap/1.data_raw/population_regional/MAGNETIC/_shared/settlement_sources/pale_east_prussia/gn_PL.zip") as z:
        for line in z.open("PL.txt").read().decode("utf-8").splitlines():
            cols = line.split("\t")
            if len(cols) < 15 or cols[6] != "P":
                continue
            a1, a2 = cols[10].strip(), cols[11].strip()
            if a1 not in ("81", "75") and not (a1 == "78" and a2 in EAST_MAZ_ADMIN2):
                continue
            lat, lon = float(cols[4]), float(cols[5])
            pop = int(cols[14] or 0)
            alts = [a.strip() for a in cols[3].split(",") if a.strip()] if cols[3] else []
            places.append({
                "name": cols[1].strip(), "ascii": cols[2].strip(),
                "lat": round(lat, 5), "lon": round(lon, 5),
                "fcode": cols[7], "pop": pop, "admin1": a1, "admin2": a2, "alts": alts,
            })

    # Map powiat centroid hints by admin2
    pow_centers = {}
    by_a2 = defaultdict(list)
    for p in places:
        by_a2[p["admin2"]].append(p)
    for a2, lst in by_a2.items():
        best = max(lst, key=lambda x: (1 if x["fcode"] in ("PPLA2", "PPLA") else 0, x["pop"]))
        pow_centers[a2] = (best["lat"], best["lon"])

    idx_pl = defaultdict(list)
    idx_ru = defaultdict(list)
    idx_ph = defaultdict(list)
    for i, p in enumerate(places):
        for cand in [p["name"], p["ascii"]] + p["alts"]:
            if re.search(r"[А-Яа-яЁё]", cand):
                k = norm_ru(cand)
                if k:
                    idx_ru[k].append(i)
                kt = translit_ru_pl(cand)
                if kt:
                    idx_pl[norm_pl(kt)].append(i)
            else:
                k = norm_pl(cand)
                if k:
                    idx_pl[k].append(i)
                    kp = norm_pl_phonetic(cand)
                    if kp and len(kp) >= 4:
                        idx_ph[kp].append(i)
    return places, pow_centers, idx_pl, idx_ru, idx_ph

places, pow_centers, idx_pl, idx_ru, idx_ph = load_pl_geo()
print(f"Loaded {len(places)} Eastern Poland seam places")

def pick_best(cands, hint_lat=None, hint_lon=None, max_deg=None, prefer_urban=False):
    if not cands:
        return None
    if max_deg is not None and hint_lat is not None:
        cands = [i for i in cands if (places[i]["lat"] - hint_lat)**2 + (places[i]["lon"] - hint_lon)**2 <= max_deg**2]
        if not cands:
            return None
    if len(cands) == 1:
        return cands[0]
    if hint_lat is not None and hint_lon is not None:
        return min(cands, key=lambda i: (places[i]["lat"] - hint_lat)**2 + (places[i]["lon"] - hint_lon)**2 - (0.01 if prefer_urban and places[i]["pop"] > 1000 else 0))
    return max(cands, key=lambda i: (1 if places[i]["fcode"] in ("PPLA", "PPLA2") else 0, places[i]["pop"]))

CITE_1897 = "Troinitsky, N. A. (ed.) (1905). Naselennye mesta Rossiiskoi imperii v 500 i bolee zhitelei po dannym pervoi vseobshchei perepisi naseleniya 1897 g. St. Petersburg: Obshchestvennaya polza (via pop-stat.mashke.org)."
CITE_1931 = "Glowny Urzad Statystyczny (GUS) (1933-1934). Skorowidz gmin Rzeczypospolitej Polskiej. Ludnosc i budynki: 1921 & 1931 censuses (Statystyka Polski Ser. B, Zesz. 8-a, 8-b; via pop-stat.mashke.org)."
CITE_GUS_HIST = "Glowny Urzad Statystyczny (GUS) (1950-1988). Narodowe Spisy Powszechne 1950, 1960, 1970, 1978, 1988 (via Polish Wikipedia GUS town demographic series & Rocznik Statystyczny)."
CITE_GUS_MOD = "Glowny Urzad Statystyczny (GUS) (1988, 2002, 2011, 2021). Narodowe Spisy Powszechne Ludnosci i Mieszkan (stat.gov.pl; via pop-stat.mashke.org)."
CITE_EUROSTAT = "Eurostat GISCO / GUS Poland (2021, 2024). Local Administrative Units (LAU) Population Tables (eurostat_lau_2021.csv, eurostat_lau_2024.csv)."

records = {}
def ensure_rec(pi, unit_type="settlement"):
    if pi not in records:
        p = places[pi]
        records[pi] = {
            "name": p["name"], "country": "Poland", "coords": [p["lat"], p["lon"]],
            "unit_type": unit_type,
            "population": {}, "citations": set(), "urls": set(), "other_names": set(),
        }
    return records[pi]

def add_pop(pi, year, val, citation, url, alt_name=None, unit_type=None):
    if val is None or val <= 0:
        return
    rec = ensure_rec(pi, unit_type or "settlement")
    if unit_type == "city_proper":
        rec["unit_type"] = "city_proper"
    ys = str(year)
    if ys not in rec["population"]:
        rec["population"][ys] = int(val)
    rec["citations"].add(citation)
    rec["urls"].add(url)
    if alt_name and alt_name.strip() and alt_name.strip().lower() != rec["name"].lower():
        rec["other_names"].add(alt_name.strip())

# --- 1. Harvest poland-cities.htm (1988, 2002, 2011, 2021, 2024) for Podlaskie, Lubelskie, Eastern Mazowieckie ---
URL_PL_CITIES = "http://pop-stat.mashke.org/poland-cities.htm"
rows_pc = parse_popstat_rows(fetch_text(URL_PL_CITIES))
hdr = rows_pc[0][1]
# Map 1988-12-06, 2002-05-20, 2011-03-31, 2021-03-31, 2024'
city_col_map = {}
for ci, h in enumerate(hdr):
    hs = h.strip()
    if re.match(r"^(1988|2002|2011|2021)-\d{2}-\d{2}$", hs):
        city_col_map[ci] = int(hs[:4])
    elif hs == "2024'":
        city_col_map[ci] = 2024
print("poland-cities cols:", city_col_map)

EAST_MAZ_TOWNS = {
    "Garwolin", "Łaskarzew", "Pilawa", "Żelechów", "Maciejowice",
    "Łosice", "Maków Mazowiecki", "Różan", "Ostrołęka", "Myszyniec",
    "Ostrów Mazowiecka", "Brok", "Siedlce", "Mordy", "Sokołów Podlaski",
    "Kosów Lacki", "Węgrów", "Łochów", "Stoczek Łukowski",
}
EAST_MAZ_TOWNS_NORM = {norm_pl(t) for t in EAST_MAZ_TOWNS}

cur_woj = ""
city_pis = {}  # norm_pl -> pi
for is_th, cells in rows_pc[1:]:
    if not cells: continue
    if is_th:
        cur_woj = cells[0].strip().lower()
        continue
    if cur_woj not in ("podlaskie", "lubelskie", "mazowieckie"):
        continue
    nm = re.sub(r"\d+\)$", "", cells[0]).strip()
    if not nm or nm.startswith("Note:"):
        continue
    k = norm_pl(nm)
    if cur_woj == "mazowieckie" and k not in EAST_MAZ_TOWNS_NORM:
        continue
    a1_target = "81" if cur_woj == "podlaskie" else ("75" if cur_woj == "lubelskie" else "78")
    cands = [i for i in idx_pl.get(k, []) if places[i]["admin1"] == a1_target]
    pi = pick_best(cands, prefer_urban=True)
    if pi is None:
        print("  UNMATCHED poland-cities:", cur_woj, nm)
        continue
    city_pis[k] = pi
    for ci, yr in city_col_map.items():
        if ci < len(cells):
            d = re.sub(r"[^\d]", "", cells[ci])
            if d:
                add_pop(pi, yr, int(d), CITE_GUS_MOD, URL_PL_CITIES, nm, unit_type="city_proper")
print(f"poland-cities matched in seam: {len(city_pis)}")

# --- 2. Harvest poland-comm.htm (1988, 2002, 2011, 2021) for city_proper rows ('m. X') and verify ---
URL_PL_COMM = "http://pop-stat.mashke.org/poland-comm.htm"
rows_pcomm = parse_popstat_rows(fetch_text(URL_PL_COMM))
cur_woj, cur_pow = "", ""
comm_town_hits = 0
for is_th, cells in rows_pcomm[1:]:
    if not cells: continue
    lbl = cells[0].strip()
    if is_th:
        if lbl.lower().startswith("województwo "):
            cur_woj = lbl.lower().replace("województwo ", "").strip()
        elif lbl.lower().startswith("powiat "):
            cur_pow = lbl[7:].strip().lower()
        continue
    if cur_woj not in ("podlaskie", "lubelskie", "mazowieckie"):
        continue
    if cur_woj == "mazowieckie" and cur_pow not in EAST_MAZ_POWIATS:
        continue
    # Take urban 'm. X' rows cleanly (city_proper!)
    if lbl.startswith("m. "):
        tnm = lbl[3:].strip()
        k = norm_pl(tnm)
        a1_t = "81" if cur_woj == "podlaskie" else ("75" if cur_woj == "lubelskie" else "78")
        cands = [i for i in idx_pl.get(k, []) if places[i]["admin1"] == a1_t]
        pi = pick_best(cands, prefer_urban=True)
        if pi is not None:
            city_pis[k] = pi
            comm_town_hits += 1
            for ci, yr in [(1, 1988), (2, 2002), (3, 2011), (4, 2021)]:
                if ci < len(cells):
                    d = re.sub(r"[^\d]", "", cells[ci])
                    if d:
                        add_pop(pi, yr, int(d), CITE_GUS_MOD, URL_PL_COMM, tnm, unit_type="city_proper")
print(f"poland-comm urban rows matched: {comm_town_hits}")

# --- 3. Harvest poland-comm1931.htm (1921, 1931) for cities/towns ('miasta') in Białostockie, Lubelskie, Maków ---
URL_PL_1931 = "http://pop-stat.mashke.org/poland-comm1931.htm"
rows_31 = parse_popstat_rows(fetch_text(URL_PL_1931))
EAST_BIALOSTOCKIE_POW = {"augustów", "m. białystok", "białystok", "bielsk", "łomża", "ostrołęka", "ostrów", "sokółka", "suwałki", "szczuczyn", "wysokie mazowieckie"}
cur_woj, cur_pow, in_miasta = "", "", False
m1931_hits = 0
for is_th, cells in rows_31[1:]:
    if not cells: continue
    lbl = cells[0].strip()
    if is_th:
        if lbl in ("Warszawskie", "Łódzkie", "Kieleckie", "Lubelskie", "Białostockie", "Wileńskie", "Nowogródzkie", "Poleskie", "Wołynskie", "Poznańskie", "Pomorskie", "Śląskie", "Krakowskie", "Lwowskie", "Stanisławowskie", "Tarnopolskie"):
            cur_woj = lbl
            cur_pow = ""
        else:
            cur_pow = lbl.lower()
        in_miasta = False
        continue
    if cur_woj not in ("Lubelskie", "Białostockie", "Warszawskie"):
        continue
    if cur_woj == "Warszawskie" and cur_pow != "maków":
        continue
    if cur_woj == "Białostockie" and cur_pow not in EAST_BIALOSTOCKIE_POW:
        continue
    if lbl.startswith("---------- "):
        in_miasta = ("miasta" in lbl)
        continue
    if in_miasta or cur_pow in ("m. lublin", "m. białystok"):
        tnm = re.sub(r"\d+\)$", "", lbl).strip()
        k = norm_pl(tnm)
        # Disambiguate Ostrów -> Ostrów Mazowiecka, Wysokie -> Wysokie Mazowieckie
        if k == "ostrow":
            k = "ostrow mazowiecka"
        elif k == "janow" and cur_pow == "janów":
            k = "janow lubelski"
        elif k == "tomaszow" and cur_pow == "tomaszów":
            k = "tomaszow lubelski"
        elif k == "bielsk" and cur_pow == "bielsk":
            k = "bielsk podlaski"
        elif k == "radzyn":
            k = "radzyn podlaski"
        elif k == "sokolow":
            k = "sokolow podlaski"
        elif k == "biala":
            k = "biala podlaska"
        elif k == "miedzyrzec":
            k = "miedzyrzec podlaski"
        elif k == "szczuczyn" and cur_pow == "szczuczyn":
            k = "szczuczyn"
        pi = city_pis.get(k) or pick_best(idx_pl.get(k), prefer_urban=True)
        if pi is not None:
            m1931_hits += 1
            for ci, yr in [(1, 1921), (2, 1931)]:
                if ci < len(cells):
                    d = re.sub(r"[^\d]", "", cells[ci])
                    if d:
                        add_pop(pi, yr, int(d), CITE_1931, URL_PL_1931, tnm, unit_type="city_proper")
print(f"1921/1931 towns matched: {m1931_hits}")

# --- 4. Harvest GUS 1946, 1950, 1960, 1970, 1978 from pl.wikipedia.org for seam towns ---
town_titles = []
for cat in ["Kategoria:Miasta w województwie podlaskim", "Kategoria:Miasta w województwie lubelskim"]:
    r = requests.get("https://pl.wikipedia.org/w/api.php", params={
        "action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": "200", "format": "json"
    }, headers=HEADERS, timeout=20)
    for x in r.json()["query"]["categorymembers"]:
        if x["ns"] == 0 and not x["title"].startswith(("Lista ", "Miasta ")):
            town_titles.append(x["title"])
town_titles.extend(sorted(EAST_MAZ_TOWNS))

# Also fetch dedicated Ludność <City> articles
lud_titles = [
    "Ludność Białegostoku", "Ludność Białej Podlaskiej", "Ludność Chełma",
    "Ludność Lublina", "Ludność Puław", "Ludność Suwałk", "Ludność Zamościa", "Ludność Łomży",
    "Ludność Siedlec", "Ludność Ostrołęki",
]
lud_map = {
    "Ludność Białegostoku": "bialystok", "Ludność Białej Podlaskiej": "biala podlaska",
    "Ludność Chełma": "chelm", "Ludność Lublina": "lublin", "Ludność Puław": "pulawy",
    "Ludność Suwałk": "suwalki", "Ludność Zamościa": "zamosc", "Ludność Łomży": "lomza",
    "Ludność Siedlec": "siedlce", "Ludność Ostrołęki": "ostroleka",
}

def extract_wiki_census(txt):
    found = {}
    # 1) All <timeline> bar:YYYY ... from:0 till:NUM across 1945..1989
    for m in re.finditer(r"bar:(19(?:4[5-9]|[5-8]\d))(?:\s+color:\S+|\s+width:\S+|\s+align:\S+|\s+shift:[^\n]+)*\s+from:0\s+till:(\d+)", txt):
        y, v = int(m.group(1)), int(m.group(2))
        if 200 <= v <= 600000:
            found[str(y)] = v
    for y in [1946, 1950, 1960, 1970, 1978, 1988]:
        ys = str(y)
        if ys in found:
            continue
        # 2) Bullet list: * [[1950]] – 15 456 or * 1950 - 15 456
        m2 = re.search(rf"(?:^\*|\n\*)\s*(?:\[\[)?{y}(?:\]\])?\s*[–\-:]\s*(?:ok\.\s*)?(\d[\d\s]{{1,7}}\d)(?!\s*(?:tys|m|km|%))", txt)
        if m2:
            v = int(re.sub(r"\s+", "", m2.group(1)))
            if 200 <= v <= 600000:
                found[ys] = v
                continue
        # 3) Wikitable row: | 1950 || 12 345
        m3 = re.search(rf"\|\s*(?:\[\[)?{y}(?:\]\])?\s*\|\|?\s*(\d[\d\s]{{1,7}}\d)", txt)
        if m3:
            v = int(re.sub(r"\s+", "", m3.group(1)))
            if 200 <= v <= 600000:
                found[ys] = v
                continue
    return found

all_wiki_fetch = list(dict.fromkeys(town_titles + lud_titles))
wiki_hits = 0
for i in range(0, len(all_wiki_fetch), 15):
    time.sleep(0.2)
    r = requests.get("https://pl.wikipedia.org/w/api.php", params={
        "action": "query", "titles": "|".join(all_wiki_fetch[i:i+15]),
        "prop": "revisions", "rvprop": "content", "format": "json"
    }, headers=HEADERS, timeout=25)
    if r.status_code != 200 or not r.text.strip().startswith("{"):
        continue
    for pid, p in r.json().get("query", {}).get("pages", {}).items():
        txt = p.get("revisions", [{}])[0].get("*", "")
        if not txt:
            continue
        title = p["title"]
        k = lud_map.get(title) or norm_pl(re.sub(r"\s*\([^)]*\)$", "", title))
        pi = city_pis.get(k) or pick_best(idx_pl.get(k), prefer_urban=True)
        if pi is None:
            continue
        res = extract_wiki_census(txt)
        if res:
            wiki_hits += 1
            wurl = f"https://pl.wikipedia.org/wiki/{title.replace(' ', '_')}"
            for ys, val in res.items():
                add_pop(pi, int(ys), val, CITE_GUS_HIST, wurl, unit_type="city_proper")
print(f"GUS 1946-1978/1988 wiki census extracted for {wiki_hits} towns")

# --- 5. Harvest poland-census-2011/{podlaskie,lubelskie,mazowieckie}.htm (ALL villages + towns in 2011) ---
p2011_matched = 0
for woj in ["podlaskie", "lubelskie", "mazowieckie"]:
    u11 = f"http://pop-stat.mashke.org/poland-census-2011/{woj}.htm"
    rows_11 = parse_popstat_rows(fetch_text(u11))
    cur_pow = ""
    cur_gm = ""
    cur_hint = None
    for is_th, cells in rows_11[1:]:
        if not cells or len(cells) < 2: continue
        lbl = cells[0].strip()
        if lbl.startswith("Powiat "):
            cur_pow = lbl[7:].strip().lower()
            cur_hint = None
            # Try to locate powiat seat hint
            seat = re.sub(r"^(m\.\s*)", "", cur_pow)
            if seat in idx_pl:
                p0 = places[pick_best(idx_pl[seat], prefer_urban=True)]
                cur_hint = (p0["lat"], p0["lon"])
            continue
        if woj == "mazowieckie" and cur_pow not in EAST_MAZ_POWIATS:
            continue
        if lbl.startswith(("gm. ", "Województwo ")):
            cur_gm = re.sub(r"^gm\.\s*(m\.|w\.|m-w\.)?\s*", "", lbl).strip()
            g_pi = pick_best(idx_pl.get(norm_pl(cur_gm)), *(cur_hint or (None, None)))
            if g_pi is not None and not cur_hint:
                cur_hint = (places[g_pi]["lat"], places[g_pi]["lon"])
            continue
        d = re.sub(r"[^\d]", "", cells[1])
        if not d: continue
        pop11 = int(d)
        is_town = lbl.startswith("m. ")
        nm = lbl[3:].strip() if is_town else lbl
        k = norm_pl(nm)
        a1_t = "81" if woj == "podlaskie" else ("75" if woj == "lubelskie" else "78")
        cands = [i for i in idx_pl.get(k, []) if places[i]["admin1"] == a1_t]
        pi = pick_best(cands, *(cur_hint or (None, None)), max_deg=0.45 if cur_hint else None, prefer_urban=is_town)
        if pi is None:
            continue
        p2011_matched += 1
        add_pop(pi, 2011, pop11, CITE_GUS_MOD, u11, nm, unit_type="city_proper" if is_town else "village")
print(f"Poland 2011 localities matched: {p2011_matched}")

# --- 6. Harvest 1897 Russian Imperial Census (Suwalki, Lomza, Siedlce, Lublin, Grodno) ---
PL_UYEZD_HINTS = {
    # Suwalki (Polish part)
    "августовский": (53.84, 22.98), "сувалкский": (54.11, 22.93), "сейнский": (54.11, 23.35),
    # Lomza
    "ломжинский": (53.18, 22.07), "кольненский": (53.41, 21.93), "мазовецкий": (52.92, 22.52),
    "маковский": (52.86, 21.10), "остроленкский": (53.08, 21.57), "островский": (52.80, 21.90), "щучинский": (53.56, 22.28),
    # Siedlce
    "седлецкий": (52.17, 22.29), "бельский": (52.03, 23.12), "венгровский": (52.40, 22.02),
    "влодавский": (51.55, 23.55), "гарволинский": (51.90, 21.62), "константиновский": (52.21, 23.09),
    "луковский": (51.93, 22.38), "радинский": (51.78, 22.62), "соколовский": (52.41, 22.25),
    # Lublin
    "люблинский": (51.25, 22.57), "белгорайский": (50.54, 22.72), "грубешовский": (50.80, 23.89),
    "замосцкий": (50.72, 23.25), "красноставский": (50.98, 23.17), "любартовский": (51.46, 22.61),
    "ново-александрийский": (51.42, 21.97), "томашовский": (50.45, 23.42), "холмский": (51.14, 23.47), "яновский": (50.71, 22.41),
    # Grodno (Polish part only!)
    "белостокский": (53.13, 23.16), "сокольский": (53.41, 23.50),
}
# Note "бельский уезд" exists in both Siedlce (Biała Podlaska) and Grodno (Bielsk Podlaski)! Handle by gub!

def match_pl_1897(raw_name, uhint):
    nm = re.sub(r",\s*(г\.|у\.г\.|м\.|д\.|с\.|п\.|пос\.|колония|фольв\.|им\.|сл\.|выс\.|о\.|з\.|уч\.|м-ко).*$", "", raw_name.strip())
    nm = re.sub(r"\s*\([^)]*\)", "", nm).strip()
    k_ru = norm_ru(nm)
    if k_ru in idx_ru:
        pi = pick_best(idx_ru[k_ru], *uhint, max_deg=0.55)
        if pi is not None: return pi, nm
    kt = norm_pl(translit_ru_pl(nm))
    if kt in idx_pl:
        pi = pick_best(idx_pl[kt], *uhint, max_deg=0.55)
        if pi is not None: return pi, nm
    kp = norm_pl_phonetic(translit_ru_pl(nm))
    if kp in idx_ph:
        pi = pick_best(idx_ph[kp], *uhint, max_deg=0.40)
        if pi is not None: return pi, nm
    return None, nm

m97_pl = 0
for gub in ["suvalkskaja", "lomzinskaja", "sedleckaja", "ljublinskaja", "grodnenskaja"]:
    u97 = f"http://pop-stat.mashke.org/empire-census-1897-religion/{gub}.htm"
    rows_97 = parse_popstat_rows(fetch_text(u97))
    cur_uname, cur_uhint = "", None
    for is_th, cells in rows_97[1:]:
        if not cells: continue
        lbl = cells[0].strip()
        if is_th:
            cur_uname = lbl.lower()
            if gub == "grodnenskaja" and "бельский" in cur_uname:
                cur_uhint = (52.77, 23.19)  # Bielsk Podlaski
            elif gub == "grodnenskaja" and not any(u in cur_uname for u in ["белосток", "соколь"]):
                cur_uhint = None
            elif gub == "suvalkskaja" and not any(u in cur_uname for u in ["августов", "сувалк", "сейн"]):
                cur_uhint = None
            else:
                cur_uhint = next((v for k, v in PL_UYEZD_HINTS.items() if k in cur_uname), None)
            continue
        if cur_uhint is None:
            continue
        tot_s = re.sub(r"[^\d]", "", cells[1]) if len(cells) > 1 else ""
        if not tot_s: continue
        pi, used_nm = match_pl_1897(lbl, cur_uhint)
        if pi is None: continue
        m97_pl += 1
        add_pop(pi, 1897, int(tot_s), CITE_1897, u97, used_nm)
print(f"Poland 1897 matched: {m97_pl}")

# Save intermediate Poland dataset
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
        "country": "Poland",
        "unit_type": rec["unit_type"],
        "coords": rec["coords"],
        "population": pop_sorted,
        "source_citation": " ; ".join(sorted(rec["citations"])),
        "source_url": " ; ".join(sorted(rec["urls"])),
    })

with open(os.path.join(OUT_DIR, "poland_harvest.json"), "w", encoding="utf-8") as f:
    json.dump(out_list, f, ensure_ascii=False, indent=2)

yr_cov = Counter()
for r in out_list:
    for y in r["population"]:
        yr_cov[y] += 1
print(f"TOTAL EASTERN POLAND SETTLEMENTS: {len(out_list)}")
print("Year coverage:", dict(sorted(yr_cov.items())))
