"""
Compiles the clean, zero-defect Stage F merge set (`tests/toponymy_batches/jaguar_merge/`) from:
  1. All 64 auditor-approved Tier 1 Gemini 3.8 Flash batches (`tests/toponymy_batches/jaguar_flash/resolved_batch_*.json`)
     — preserving Flash-approved timelines verbatim (ZERO post-sign-off back-clamping across 1492/1519!).
  2. All Tier 2a pre-1900 (<5k) + Tier 2b INEGI AHL officially renamed (<5k) records, filtering out
     raw INEGI AHL article/abbreviation/ordinal/1-edit spelling/OCR noise so ONLY substantive legal
     renames remain in `historical_names` (trivial variants go to `other_names`).
  3. Strict deduplication of same-date entries, exact terminal `canonical_name` alignment for extant
     modern settlements (`latest_year >= 1950`), removal of modern intra-municipal district leaks,
     and strict pairwise spatial collision deduplication (<= 1.55 km any; <= 15.2 km same-stem)
     across the entire merge set + existing `00_capitals.json` + `12_jaguar.json`.
"""
import csv
import glob
import json
import math
import os
import re
import unicodedata

SVEA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATAVIEW_ROOT = r"F:\Active Projects\Project 1436 - Dataview"
RAW_BATCH_DIR = os.path.join(SVEA_ROOT, "tests", "toponymy_batches", "jaguar")
FLASH_DIR = os.path.join(SVEA_ROOT, "tests", "toponymy_batches", "jaguar_flash")
MERGE_DIR = os.path.join(SVEA_ROOT, "tests", "toponymy_batches", "jaguar_merge")
META_DIR = os.path.join(DATAVIEW_ROOT, "data/stadester/stadester_2.0/city_metadata")
AHL_CSV = os.path.join(SVEA_ROOT, "histmap/1.data_raw/population_regional/JAGUAR/_shared/settlement_sources/parsed/mexico_inegi_ahl_1900_2020_enriched.csv")
AHL_HIST = os.path.join(SVEA_ROOT, "histmap/1.data_raw/population_regional/JAGUAR/_shared/settlement_sources/parsed/mexico_ahl_historical_names.json")

ARCH_QUAL_RE = re.compile(
    r"\s+(?:Site|Complex|Hillfort|Settlement|Chiefdom\s+Settlement|Early\s+Settlement|Mound|Ruin|Ruins|Cemetery|Necropolis|Shelter|Cave|Camp|Earthwork|Enclosure|Midden|Shellmound|Terrace)$",
    re.IGNORECASE,
)
ARTICLE_INVERT_RE = re.compile(
    r"^(.+?),\s*(Al|El|As|Ash|Ar|Az|Ad|An|At|Le|La|Les|L'|Los|Las|Il|Lo|De|Den|Het|Der|Die|Das|The)$",
    re.IGNORECASE,
)
PAREN_RE = re.compile(r"\s*\([^)]*\)")
UNCLOSED_PAREN_RE = re.compile(r"\s*\([^)]*$")
DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")
FOREIGN_RE = re.compile(r"[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]")
SMALL_WORDS = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "al", "con", "sin", "por", "san", "santa", "santo", "of", "the", "and", "du", "des", "le", "les", "au", "aux"}

# Intra-municipal districts / barrios that must NEVER be emitted as modern standalone settlements
INTRA_MUNICIPAL_DROP_KEYS = {
    "Santurce-Puerto Rico",
    "Cupey-Puerto Rico",
    "Caimito-Puerto Rico",
    "Monacillo-Puerto Rico",
    "Gobernador Piñero-Puerto Rico",
    "Pueblo Viejo-Puerto Rico",
}
INTRA_MUNICIPAL_PATCH_NAMES = {
    ("Tláhuac", "Mexico"),
    ("Xochimilco", "Mexico"),
    ("Milpa Alta", "Mexico"),
    ("La Magdalena Contreras", "Mexico"),
    ("Iztapalapa", "Mexico"),
    ("Cerro", "Cuba"),
    ("Diez de Octubre", "Cuba"),
    ("La Lisa", "Cuba"),
    ("Aruba", "Aruba"),
}
COUNTRY_STUB_NAMES = {
    "turks and caicos islands",
    "antigua and barbuda",
    "caribbean netherlands",
    "the bahamas",
    "bahamas",
}

# Patterns indicating a European colonial / modern name (NEVER back-project before 1492/1519)
COLONIAL_PREFIX_RE = re.compile(
    r"^(?:San|Santa|Santo|Santiago|Ciudad|Villa|Puerto|Port|New|Nueva|Nuevo|The|Fort|Saint|Sainte|St\.|"
    r"El\s+(?:Rosario|Paraíso|Paraiso|Asintal|Naranjo|Pueblo|Puerto|Carmen|Salvador|Progreso|Triunfo|Porvenir)|"
    r"La\s+(?:Habana|Esperanza|Nueva|Magdalena|Candelaria|Concepción|Concepcion|Trinidad|Paz|Unión|Union|Cruz|Libertad|Reforma|Palma|Victoria)|"
    r"Las\s+|Los\s+|Fraccionamiento\s+|Ejido\s+|Colonia\s+|Rancho\s+|Hacienda\s+|Dolores|Magdalena|Cabañas|Piedra\s+Grande|Bridgetown|Kingston|Nassau)",
    re.IGNORECASE,
)

# Caribbean countries (1492 contact threshold; mainland = 1519)
CARIBBEAN_COUNTRIES = {
    "anguilla", "antigua and barbuda", "aruba", "barbados", "bermuda", "bonaire",
    "british virgin islands", "caribbean netherlands", "cayman islands", "cuba", "curaçao",
    "curacao", "dominica", "dominican republic", "grenada", "guadeloupe", "haiti", "jamaica",
    "martinique", "montserrat", "netherlands antilles", "puerto rico", "saba", "saint barthelemy",
    "saint barthélemy", "saint kitts and nevis", "saint lucia", "saint martin", "saint-martin",
    "saint vincent and the grenadines", "sint eustatius", "sint maarten", "the bahamas",
    "bahamas", "trinidad and tobago", "turks and caicos islands", "united states virgin islands",
    "us virgin islands",
}

ABBREV_MAP = [
    (re.compile(r"\bgral\.?\b", re.I), "general"),
    (re.compile(r"\bpte\.?\b", re.I), "presidente"),
    (re.compile(r"\bprofr\.?\b|\bprof\.?\b", re.I), "profesor"),
    (re.compile(r"\blic\.?\b", re.I), "licenciado"),
    (re.compile(r"\bing\.?\b", re.I), "ingeniero"),
    (re.compile(r"\bdr\.?\b", re.I), "doctor"),
    (re.compile(r"\bsta\.?\b", re.I), "santa"),
    (re.compile(r"\bsto\.?\b", re.I), "santo"),
    (re.compile(r"\bsn\.?\b", re.I), "san"),
    (re.compile(r"\bfco\.?\b", re.I), "francisco"),
    (re.compile(r"\bgpe\.?\b", re.I), "guadalupe"),
    (re.compile(r"\bcd\.?\b", re.I), "ciudad"),
    (re.compile(r"\bcol\.?\b", re.I), "colonia"),
    (re.compile(r"\bej\.?\b", re.I), "ejido"),
    (re.compile(r"\bfracc\.?\b", re.I), "fraccionamiento"),
    (re.compile(r"\bsecc\.?\b", re.I), "seccion"),
    (re.compile(r"\b(?:1ra|1a|1o|1ro|primera|primero|i)\b", re.I), "1"),
    (re.compile(r"\b(?:2da|2do|2a|2o|segunda|segundo|ii|il)\b", re.I), "2"),
    (re.compile(r"\b(?:3ra|3er|3a|3o|tercera|tercero|iii)\b", re.I), "3"),
    (re.compile(r"\b(?:4ta|4to|4a|4o|cuarta|cuarto|iv)\b", re.I), "4"),
    (re.compile(r"\b(?:5ta|5to|5a|5o|quinta|quinto|v)\b", re.I), "5"),
]


def haversine_km (lat1, lng1, lat2, lng2):
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * r * math.asin(min(1.0, math.sqrt(max(0.0, a))))


def normalise_entity_stem (name):
    """Matches viscount_entity_and_continuity_audit.normaliseEntityStem exactly."""
    s = UNCLOSED_PAREN_RE.sub("", PAREN_RE.sub("", str(name or ""))).strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower()
    s = s.replace("ł", "l").replace("đ", "d").replace("ø", "o").replace("ß", "ss").replace("æ", "ae").replace("œ", "oe")
    s = re.sub(r"^(?:st\.?|saint|san|santa|sao|al-|el-)\s+", "saint ", s)
    for a, b in [("kh", "k"), ("gh", "g"), ("ph", "f"), ("dj", "j"), ("ou", "u"), ("ts", "c")]:
        s = s.replace(a, b)
    s = re.sub(r"[jy]", "i", s)
    s = re.sub(r"[cq]", "k", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def normalise_merge_name (name):
    """Matches merge_city_metadata.normaliseName exactly."""
    s = UNCLOSED_PAREN_RE.sub("", PAREN_RE.sub("", str(name or ""))).strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn").lower()
    for a, b in [("j", "y"), ("ya", "a"), ("ye", "e"), ("yo", "o"), ("yu", "u"), ("ch", "c"), ("sh", "s"), ("zh", "z")]:
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", s)


def ahl_variant_key (name):
    """Normalises articles, INEGI abbreviations, ordinals, and spacing to collapse trivial census variants."""
    s = UNCLOSED_PAREN_RE.sub("", PAREN_RE.sub("", str(name or ""))).strip()
    s = s.replace('"', "").replace("'", "").replace(")", "").replace("(", "")
    s = "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn").lower()
    s = re.sub(r"^(?:el|la|los|las|del|de\s+la|de\s+los|de\s+las)\s+", "", s)
    s = re.sub(r"\s+cab(?:ecera)?\.?\s*$", "", s).strip()
    for rx, rep in ABBREV_MAP:
        s = rx.sub(rep, s)
    s = re.sub(r"\b(?:de|del|la|las|el|los)\b", " ", s)
    s = re.sub(r"[jy]", "i", s)
    s = re.sub(r"[cq]", "k", s)
    s = re.sub(r"[sz]", "s", s)
    s = re.sub(r"[bv]", "b", s)
    s = s.replace("h", "")
    return re.sub(r"[^a-z0-9]+", "", s)


def edit_distance_le (a, b, max_d=2):
    """Fast bounded Levenshtein distance check (returns True if dist <= max_d)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > max_d:
        return False
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        row_min = i
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            cur[j] = v
            if v < row_min:
                row_min = v
        if row_min > max_d:
            return False
        prev = cur
    return prev[lb] <= max_d


def is_trivial_variant (name_a, name_b):
    """Returns True when two names are orthographic/article/abbrev/ordinal/1-edit variants rather than a substantive rename."""
    if not name_a or not name_b:
        return False
    if name_a == name_b:
        return True
    es_a, es_b = normalise_entity_stem(name_a), normalise_entity_stem(name_b)
    if es_a and es_b and es_a == es_b:
        return True
    vk_a, vk_b = ahl_variant_key(name_a), ahl_variant_key(name_b)
    if vk_a and vk_b and vk_a == vk_b:
        return True
    if len(vk_a) >= 5 and len(vk_b) >= 5:
        thresh = 2 if min(len(vk_a), len(vk_b)) >= 9 else 1
        if edit_distance_le(vk_a, vk_b, thresh):
            return True
    return False


def clean_toponym (name, strip_arch_qual=False):
    s = UNCLOSED_PAREN_RE.sub("", PAREN_RE.sub("", str(name or ""))).strip()
    s = s.replace("`", "'").replace("?", "").replace("\ufffd", "").replace("ï¿½", "ç").replace('"', "").replace(")", "").replace("(", "").strip()
    m = ARTICLE_INVERT_RE.match(s)
    if m:
        art = m.group(2)
        base = m.group(1).strip()
        s = f"{art}{base}" if art.endswith("'") else f"{art} {base}"
    alpha = [c for c in s if c.isalpha()]
    if len(alpha) >= 4 and all(c.isupper() for c in alpha) and not re.search(r"[A-Z]{2,3}-[A-Z]{1,5}-\d+", s):
        words = s.split()
        out_w = []
        for idx, w in enumerate(words):
            if re.match(r"^[IVXLCDM]+$", w) and idx > 0:
                out_w.append(w)
            else:
                wl = w.lower()
                out_w.append(wl if (idx > 0 and wl in SMALL_WORDS) else wl.capitalize())
        s = " ".join(out_w)
    if strip_arch_qual:
        stripped = ARCH_QUAL_RE.sub("", s).strip()
        if len(stripped) >= 3:
            s = stripped
    return re.sub(r"\s+", " ", s).strip()


def valid_date_str (d):
    s = str(d or "").strip()
    if not DATE_RE.match(s):
        return None
    parts = s.split(".")
    y, m, day = int(parts[0]), int(parts[1]), int(parts[2])
    if y == 0:
        y = -1
    y = max(-10000, min(2026, y))
    m = max(1, min(12, m))
    day = max(1, min(28 if m == 2 else (30 if m in (4, 6, 9, 11) else 31), day))
    return f"{y}.{m}.{day}"


def date_tuple (d):
    parts = str(d or "0.1.1").split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def contact_year_for_country (country):
    return 1492 if str(country or "").strip().lower() in CARIBBEAN_COUNTRIES else 1519


def is_colonial_name (name):
    return bool(COLONIAL_PREFIX_RE.search(str(name or "").strip()))


def extract_indigenous_tail (name):
    """For Mesoamerican syncretic saint+indigenous names (e.g. 'San Mateo Ixtatán'), returns indigenous tail ('Ixtatán')."""
    s = str(name or "").strip()
    m = re.match(
        r"^(?:San|Santa|Santo|Santiago|La\s+Magdalena|La\s+Candelaria)\s+(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:[a-z\s'-]+)?)$",
        s,
    )
    if not m:
        return None
    tail = m.group(1).strip()
    # Accept only clearly indigenous Nahuatl/Maya/Otomanguean roots (not Spanish saints/generic nouns)
    if re.search(r"(?:tl|tz|ch|hu|cu|co$|can$|pan$|lan$|pec$|tenango$|tepec$|titlan$|catlan$|zintla$|milpa$|xoch|ixt|toton|cotzum|pango$|pala$|noaya$|manca$|xom|tec|tlan$|tla$|cuaro$|huacan$|xil|yuc|zac|atz|itz)", tail, re.I):
        if len(tail) >= 5 and not is_colonial_name(tail):
            return tail
    return None


def sanitise_record (rec, preserve_flash=False, strip_arch=False):
    raw_name = str(rec.get("canonical_name") or rec.get("name") or "").strip()
    clean_nm = clean_toponym(raw_name, strip_arch_qual=strip_arch)
    if not clean_nm or clean_nm in ("0", "Unknown", "Settlement"):
        clean_nm = clean_toponym(rec.get("name", ""), strip_arch_qual=False)
    ey = rec.get("earliest_year")
    ly = rec.get("latest_year")
    is_extant = (ly is not None and int(ly) >= 1950)
    other = []
    for o in (rec.get("other_names") or []) + (rec.get("known_aliases") or []):
        co = clean_toponym(o)
        if co and co != clean_nm and not FOREIGN_RE.search(co):
            other.append(co)

    valid_h = []
    for h in rec.get("historical_names") or []:
        if not isinstance(h, dict):
            continue
        vd = valid_date_str(h.get("date"))
        hn = clean_toponym(h.get("name"), strip_arch_qual=strip_arch)
        if vd and hn and hn not in ("0", "Unknown", "Settlement") and not FOREIGN_RE.search(hn):
            valid_h.append({"date": vd, "name": hn})

    if not valid_h:
        sy = int(ey) if ey is not None else 1900
        if sy == 0:
            sy = -1
        valid_h = [{"date": f"{sy}.1.1", "name": clean_nm}]

    valid_h.sort(key=lambda x: date_tuple(x["date"]))

    # Deduplicate exact same dates (keep the last/most canonical entry for that date; archive earlier to other_names)
    by_date = []
    for h in valid_h:
        if by_date and by_date[-1]["date"] == h["date"]:
            # Prefer the entry matching canonical_name if one does, otherwise keep the more modern/second
            if normalise_merge_name(by_date[-1]["name"]) == normalise_merge_name(clean_nm):
                if h["name"] != clean_nm:
                    other.append(h["name"])
            else:
                if by_date[-1]["name"] != clean_nm:
                    other.append(by_date[-1]["name"])
                by_date[-1] = h
        else:
            by_date.append(h)

    # Collapse consecutive same-stem / leading-article variants (for Flash: entity-stem + leading article; for Tier 2: full AHL collapse)
    def same_flash_article_or_stem (a, b):
        if a == b or normalise_entity_stem(a) == normalise_entity_stem(b):
            return True
        sa = re.sub(r"^(?:el|la|los|las)\s+", "", a.strip(), flags=re.I)
        sb = re.sub(r"^(?:el|la|los|las)\s+", "", b.strip(), flags=re.I)
        return bool(sa and sb and normalise_entity_stem(sa) == normalise_entity_stem(sb))

    dedup = []
    for h in by_date:
        if dedup:
            same = (
                same_flash_article_or_stem(dedup[-1]["name"], h["name"])
                if preserve_flash
                else is_trivial_variant(dedup[-1]["name"], h["name"])
            )
            if same:
                # If the newer variant matches canonical_name more closely, prefer its spelling at the earlier date!
                if h["name"] == clean_nm and dedup[-1]["name"] != clean_nm:
                    other.append(dedup[-1]["name"])
                    dedup[-1] = {"date": dedup[-1]["date"], "name": clean_nm}
                else:
                    if h["name"] != clean_nm:
                        other.append(h["name"])
                continue
        dedup.append(h)

    # Collapse A -> B -> A oscillations created by article flips or minor census spelling flips
    if len(dedup) >= 3:
        collapsed = []
        for h in dedup:
            cmp_fn = same_flash_article_or_stem if preserve_flash else is_trivial_variant
            if len(collapsed) >= 2 and cmp_fn(collapsed[-2]["name"], h["name"]) and cmp_fn(collapsed[-1]["name"], h["name"]):
                other.append(collapsed.pop()["name"])
                continue
            collapsed.append(h)
        dedup = collapsed

    # Ensure terminal name matches canonical_name EXACTLY for extant modern settlements (latest_year >= 1950)
    if is_extant and dedup:
        last_nm = dedup[-1]["name"]
        if last_nm != clean_nm:
            if is_trivial_variant(last_nm, clean_nm) or normalise_entity_stem(last_nm) == normalise_entity_stem(clean_nm) or normalise_merge_name(last_nm) == normalise_merge_name(clean_nm):
                other.append(last_nm)
                dedup[-1]["name"] = clean_nm
            else:
                last_y = date_tuple(dedup[-1]["date"])[0]
                term_y = max(last_y + 1, min(2025, int(ly) if ly else 2000))
                if term_y == 0:
                    term_y = 1
                dedup.append({"date": f"{term_y}.1.1", "name": clean_nm})

    out = dict(rec)
    if isinstance(out.get("country"), str) and "ï¿½" in out["country"]:
        out["country"] = out["country"].replace("ï¿½", "ç")
    if isinstance(out.get("key"), str) and "ï¿½" in out["key"]:
        out["key"] = out["key"].replace("ï¿½", "ç")
    out["canonical_name"] = clean_nm
    out["historical_names"] = dedup
    out["other_names"] = sorted(set(x for x in other if x and x != clean_nm))
    out["verified_settlement"] = True
    return out


def load_ahl_lookup ():
    hist_by_cvegeo = json.load(open(AHL_HIST, encoding="utf-8"))
    grid = {}
    with open(AHL_CSV, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cg = row.get("cvegeo", "").strip()
            if cg not in hist_by_cvegeo:
                continue
            try:
                lat, lon = float(row["lat"]), float(row["lon"])
            except Exception:
                continue
            grid.setdefault((round(lat * 4), round(lon * 4)), []).append({
                "lat": lat, "lon": lon,
                "stem": normalise_merge_name(row.get("nom_loc", "")),
                "history": hist_by_cvegeo[cg],
            })
    return grid


def find_ahl_history (lat, lng, name, ahl_grid):
    c_stem = normalise_merge_name(name)
    gx, gy = round(lat * 4), round(lng * 4)
    best, best_d = None, 5.0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for rec in ahl_grid.get((gx + dx, gy + dy), []):
                d = haversine_km(lat, lng, rec["lat"], rec["lon"])
                if d <= best_d and (d <= 0.8 or (c_stem and rec["stem"] == c_stem)):
                    best_d, best = d, rec
    return best


def main ():
    # 1. Load existing 00_capitals + 12_jaguar metadata to build spatial index
    existing_recs = {}
    meta_grid = {}

    def add_node (node):
        gk = (round(node["lat"] * 5), round(node["lng"] * 5))
        meta_grid.setdefault(gk, []).append(node)

    for fn in ("00_capitals.json", "12_jaguar.json"):
        fp = os.path.join(META_DIR, fn)
        if not os.path.exists(fp):
            continue
        arr = json.load(open(fp, encoding="utf-8"))
        for idx, rec in enumerate(arr):
            coords = rec.get("coords")
            if not isinstance(coords, list) or len(coords) < 2:
                continue
            lat, lng = float(coords[1]), float(coords[0])
            if fn == "12_jaguar.json" and rec.get("name") == "Mata de Plátano" and rec.get("country") == "Costa Rica":
                lat, lng = 9.95514, -83.99792
            node = {
                "source": "existing",
                "shard_file": fn,
                "idx": idx,
                "lat": lat,
                "lng": lng,
                "name": str(rec.get("name", "")),
                "stem": normalise_entity_stem(rec.get("name", "")),
                "rec": rec,
                "patch_rec": None,
                "is_flash": False,
            }
            existing_recs[(fn, idx)] = node
            add_node(node)

    def find_conflict (lat, lng, stem, ignore_ref=None):
        gx, gy = round(lat * 5), round(lng * 5)
        best, best_d = None, 999999.0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for nd in meta_grid.get((gx + dx, gy + dy), []):
                    if ignore_ref and nd.get("shard_file") == ignore_ref[0] and nd.get("idx") == ignore_ref[1]:
                        continue
                    d = haversine_km(lat, lng, nd["lat"], nd["lng"])
                    if d <= 1.55 or (d <= 15.2 and stem and nd["stem"] and stem == nd["stem"]):
                        if d < best_d:
                            best_d, best = d, nd
        return (best, best_d) if best is not None else None

    def attach_alias_safely (nd, alias_name, extra_aliases, earliest_yr, country):
        """Attaches co-located alias to parent's other_names WITHOUT ever back-clamping colonial names before contact!"""
        clean_al = clean_toponym(alias_name)
        all_al = [clean_al] + [clean_toponym(x) for x in (extra_aliases or [])]
        all_al = [x for x in all_al if x and not FOREIGN_RE.search(x)]

        if nd["source"] in ("tier1", "tier2"):
            target = nd["rec"]
            cur_o = set(target.get("other_names") or [])
            for a in all_al:
                if a != target["canonical_name"]:
                    cur_o.add(a)
            target["other_names"] = sorted(cur_o)
            # NEVER mutate historical_names of a Flash-approved Tier 1 record!
            if nd.get("is_flash"):
                return
            # For Tier 2 non-Flash records, only extend earliest date if NOT back-projecting a colonial name before contact
            if earliest_yr is not None and int(earliest_yr) < 1850 and target.get("historical_names"):
                sy = int(earliest_yr) if int(earliest_yr) != 0 else -1
                fy = date_tuple(target["historical_names"][0]["date"])[0]
                c_yr = contact_year_for_country(country or target.get("country", ""))
                first_nm = target["historical_names"][0]["name"]
                if fy > sy + 100:
                    if sy >= c_yr or not is_colonial_name(first_nm):
                        target["historical_names"][0]["date"] = f"{sy}.1.1"
                    else:
                        indig = extract_indigenous_tail(first_nm)
                        if indig and normalise_entity_stem(indig) != normalise_entity_stem(first_nm):
                            target["historical_names"].insert(0, {"date": f"{sy}.1.1", "name": indig})
        else:
            orig = nd["rec"]
            # Skip patching known intra-municipal districts in existing metadata
            if (orig.get("name", ""), orig.get("country", "")) in INTRA_MUNICIPAL_PATCH_NAMES:
                return
            if nd["patch_rec"] is None:
                orig_nm = clean_toponym(orig.get("name", ""), strip_arch_qual=True)
                orig_hist = list(orig.get("historical_names") or [])
                first_orig_yr = date_tuple(orig_hist[0]["date"])[0] if orig_hist and orig_hist[0].get("date") else 2000
                nd["patch_rec"] = sanitise_record({
                    "key": f"existing_patch_{nd['shard_file']}_{nd['idx']}",
                    "name": orig_nm,
                    "canonical_name": orig_nm,
                    "country": orig.get("country", ""),
                    "coords_lat_lng": [nd["lat"], nd["lng"]],
                    "existing_meta_index": nd["idx"],
                    "existing_shard_file": nd["shard_file"],
                    "is_capital": nd["shard_file"] == "00_capitals.json",
                    "historical_names": orig_hist,
                    "other_names": list(orig.get("other_names") or []),
                    "earliest_year": first_orig_yr,
                    "latest_year": 2025,
                }, preserve_flash=False)
            target = nd["patch_rec"]
            cur_o = set(target.get("other_names") or [])
            for a in all_al:
                if a != target["canonical_name"]:
                    cur_o.add(a)
            target["other_names"] = sorted(cur_o)
            # Only prepend indigenous endonym if pre-contact & not colonial!
            if earliest_yr is not None and int(earliest_yr) < 1850 and target.get("historical_names"):
                sy = int(earliest_yr) if int(earliest_yr) != 0 else -1
                fy = date_tuple(target["historical_names"][0]["date"])[0]
                c_yr = contact_year_for_country(country or target.get("country", ""))
                first_nm = target["historical_names"][0]["name"]
                if fy > sy + 100:
                    if sy >= c_yr or not is_colonial_name(first_nm):
                        target["historical_names"][0]["date"] = f"{sy}.1.1"
                    else:
                        indig = extract_indigenous_tail(first_nm)
                        if indig and normalise_entity_stem(indig) != normalise_entity_stem(first_nm):
                            target["historical_names"].insert(0, {"date": f"{sy}.1.1", "name": indig})

    # 2. Load ALL 64 auditor-approved Tier 1 Flash records (preserving timelines verbatim!)
    flash_files = sorted(glob.glob(os.path.join(FLASH_DIR, "resolved_batch_*.json")))
    tier1_raw = []
    for fp in flash_files:
        d = json.load(open(fp, encoding="utf-8"))
        assert d.get("approved_by_auditor") is True, f"Unapproved Flash batch: {fp}"
        for rec in d.get("settlements", []):
            if rec.get("key") in INTRA_MUNICIPAL_DROP_KEYS:
                continue
            tier1_raw.append(sanitise_record(rec, preserve_flash=True, strip_arch=True))

    # Deduplicate Tier 1 against existing (upgrading existing record in-place rather than dropping Flash!) and against earlier Tier 1
    kept_tier1 = []
    tier1_keys = set()
    t1_upgraded_existing = 0
    t1_merged_dup_t1 = 0

    for rec in tier1_raw:
        lat, lng = float(rec["coords_lat_lng"][0]), float(rec["coords_lat_lng"][1])
        stem = normalise_entity_stem(rec["canonical_name"])
        ign = (rec["existing_shard_file"], rec["existing_meta_index"]) if rec.get("existing_meta_index") is not None else None

        conf = find_conflict(lat, lng, stem, ignore_ref=ign)
        if conf:
            parent_nd, dist_km = conf
            if parent_nd["source"] == "existing" and not parent_nd.get("is_flash"):
                # Upgrade the existing metadata entry IN-PLACE with the Flash-approved timeline!
                rec["existing_shard_file"] = parent_nd["shard_file"]
                rec["existing_meta_index"] = parent_nd["idx"]
                # Preserve existing name as alias if different
                if parent_nd["name"] and parent_nd["name"] != rec["canonical_name"]:
                    o = set(rec.get("other_names") or [])
                    o.add(clean_toponym(parent_nd["name"]))
                    rec["other_names"] = sorted(o)
                parent_nd["source"] = "tier1"
                parent_nd["rec"] = rec
                parent_nd["is_flash"] = True
                parent_nd["name"] = rec["canonical_name"]
                parent_nd["stem"] = stem
                kept_tier1.append(rec)
                tier1_keys.add(rec["key"])
                t1_upgraded_existing += 1
                continue
            else:
                # Conflicts with an already-accepted higher-priority Flash record (e.g. Mitla vs Mitla Early Settlement)
                attach_alias_safely(parent_nd, rec["canonical_name"], rec.get("other_names"), rec.get("earliest_year"), rec.get("country"))
                t1_merged_dup_t1 += 1
                tier1_keys.add(rec["key"])
                continue

        if ign and ign in existing_recs:
            existing_recs[ign]["source"] = "tier1"
            existing_recs[ign]["rec"] = rec
            existing_recs[ign]["is_flash"] = True
            existing_recs[ign]["name"] = rec["canonical_name"]
            existing_recs[ign]["stem"] = stem
        else:
            add_node({
                "source": "tier1",
                "shard_file": None,
                "idx": None,
                "lat": lat,
                "lng": lng,
                "name": rec["canonical_name"],
                "stem": stem,
                "rec": rec,
                "is_flash": True,
            })
        kept_tier1.append(rec)
        tier1_keys.add(rec["key"])

    print(f"Tier 1 Flash records: {len(tier1_raw)} loaded -> {len(kept_tier1)} emitted ({t1_upgraded_existing} upgraded existing records in-place, {t1_merged_dup_t1} co-located dup pairs merged cleanly).")

    # 3. Process Tier 2a (pre-1900 < 5k) + Tier 2b (post-1900 < 5k with >=2 substantive INEGI AHL renames)
    bfiles = sorted(glob.glob(os.path.join(RAW_BATCH_DIR, "batch_*.json")))
    raw_items = [it for f in bfiles for it in json.load(open(f, encoding="utf-8")).get("settlements", [])]
    ahl_grid = load_ahl_lookup()

    tier2_standalone = []
    t2_attached = 0
    t2_skipped_trivial_ahl = 0

    for item in raw_items:
        k = item.get("key")
        if k in tier1_keys or k in INTRA_MUNICIPAL_DROP_KEYS or item.get("is_capital") or (item.get("max_pop") or 0) >= 5000:
            continue
        ey = item.get("earliest_year")
        is_pre1900 = (ey is not None and int(ey) < 1900)
        lat, lng = float(item["coords_lat_lng"][0]), float(item["coords_lat_lng"][1])
        ahl_rec = find_ahl_history(lat, lng, item.get("name", ""), ahl_grid) if item.get("country") == "Mexico" else None

        if not is_pre1900 and not (ahl_rec and len(ahl_rec["history"]) >= 2):
            continue

        ly = item.get("latest_year")
        is_extant = (ly is not None and int(ly) >= 1950)
        clean_nm = clean_toponym(item.get("name", ""), strip_arch_qual=True)
        if not clean_nm or len(clean_nm) < 2 or clean_nm.lower() in COUNTRY_STUB_NAMES:
            continue
        stem = normalise_entity_stem(clean_nm)

        ign = (item["existing_shard_file"], item["existing_meta_index"]) if item.get("existing_meta_index") is not None else None
        conf = find_conflict(lat, lng, stem, ignore_ref=ign)
        if conf:
            parent_nd, dist_km = conf
            if dist_km <= 1.55 or is_pre1900:
                attach_alias_safely(parent_nd, clean_nm, item.get("known_aliases"), ey, item.get("country"))
            t2_attached += 1
            continue

        # Build clean archival historical_names timeline
        hist = []
        sy = int(ey) if ey is not None else 1900
        if sy == 0:
            sy = -1
        c_yr = contact_year_for_country(item.get("country", ""))

        for eh in item.get("existing_historical_names") or []:
            vd = valid_date_str(eh.get("date"))
            en = clean_toponym(eh.get("name", ""))
            if not vd or not en:
                continue
            if vd in ("1900.1.1", "1950.1.1") and (sy < int(vd.split(".")[0]) or ahl_rec):
                continue
            hist.append({"date": vd, "name": en})

        if ahl_rec:
            for ah in ahl_rec["history"]:
                ay = int(ah.get("year") or 0)
                an = clean_toponym(ah.get("name", ""))
                if ay and an:
                    hist.append({"date": f"{ay}.1.1", "name": an})

        if not hist or min(date_tuple(h["date"])[0] for h in hist) > sy:
            if sy < c_yr and is_colonial_name(clean_nm):
                indig = extract_indigenous_tail(clean_nm)
                if indig:
                    hist.insert(0, {"date": f"{sy}.1.1", "name": indig})
                    hist.append({"date": f"{max(c_yr + 5, 1570)}.1.1", "name": clean_nm})
                else:
                    # Do NOT back-project European saint/colonial name before contact; anchor at colonial era if extant, else site name
                    hist.insert(0, {"date": f"{(1570 if is_extant else sy)}.1.1", "name": clean_nm})
            else:
                hist.insert(0, {"date": f"{sy}.1.1", "name": clean_nm})

        rec = dict(item)
        rec["canonical_name"] = clean_nm
        rec["historical_names"] = hist
        rec["other_names"] = list(item.get("known_aliases") or [])
        rec = sanitise_record(rec, preserve_flash=False, strip_arch=True)
        # Keep rec["earliest_year"] aligned with authentic earliest attested historical_names year so colonial towns aren't rejected for pre-contact neighbour dates
        if rec.get("historical_names"):
            first_h_yr = date_tuple(rec["historical_names"][0]["date"])[0]
            if rec.get("earliest_year") is None or first_h_yr > int(rec["earliest_year"]) + 100:
                rec["earliest_year"] = first_h_yr

        # For Tier 2b (post-1900 < 5k), only keep if a SUBSTANTIVE legal rename survived AHL noise filtering!
        if not is_pre1900 and len(rec["historical_names"]) < 2:
            t2_skipped_trivial_ahl += 1
            continue

        tier2_standalone.append(rec)
        if ign and ign in existing_recs:
            existing_recs[ign]["source"] = "tier2"
            existing_recs[ign]["rec"] = rec
        else:
            add_node({
                "source": "tier2",
                "shard_file": None,
                "idx": None,
                "lat": lat,
                "lng": lng,
                "name": rec["canonical_name"],
                "stem": normalise_entity_stem(rec["canonical_name"]),
                "rec": rec,
                "is_flash": False,
            })

    # Collect clean existing metadata patches
    existing_patches = []
    for nd in existing_recs.values():
        if nd.get("patch_rec") is not None and not nd.get("is_flash"):
            existing_patches.append(sanitise_record(nd["patch_rec"], preserve_flash=False, strip_arch=True))

    print(f"Tier 2 standalone/updates: {len(tier2_standalone)}, co-located alias attachments: {t2_attached}, trivial-only AHL skipped: {t2_skipped_trivial_ahl}, existing patches: {len(existing_patches)}")

    # 4. Final internal pairwise spatial collision audit (guarantee 0 collisions <= 1.55 km or <= 15.2 km same-stem)
    all_out = kept_tier1 + existing_patches + tier2_standalone
    final_out = []
    f_grid = {}
    internal_dedup = 0
    for rec in all_out:
        lat, lng = float(rec["coords_lat_lng"][0]), float(rec["coords_lat_lng"][1])
        stem = normalise_entity_stem(rec["canonical_name"])
        gx, gy = round(lat * 5), round(lng * 5)
        dup_parent = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for prev in f_grid.get((gx + dx, gy + dy), []):
                    d = haversine_km(lat, lng, prev["lat"], prev["lng"])
                    if d <= 1.55 or (d <= 15.2 and stem and prev["stem"] and stem == prev["stem"]):
                        dup_parent = prev["rec"]
                        break
                if dup_parent:
                    break
            if dup_parent:
                break
        if dup_parent:
            o = set(dup_parent.get("other_names") or [])
            if rec["canonical_name"] != dup_parent["canonical_name"]:
                o.add(rec["canonical_name"])
            for x in rec.get("other_names") or []:
                if x != dup_parent["canonical_name"]:
                    o.add(x)
            dup_parent["other_names"] = sorted(o)
            internal_dedup += 1
            continue
        final_out.append(rec)
        f_grid.setdefault((gx, gy), []).append({"lat": lat, "lng": lng, "stem": stem, "rec": rec})

    print(f"Final collision-free merge set: {len(final_out)} records (internal collisions collapsed: {internal_dedup})")

    # 5. Write unified resolved batches to MERGE_DIR
    os.makedirs(MERGE_DIR, exist_ok=True)
    for old in glob.glob(os.path.join(MERGE_DIR, "resolved_batch_*.json")):
        os.remove(old)

    chunk = 500
    n_files = 0
    for i in range(0, len(final_out), chunk):
        n_files += 1
        sl = final_out[i : i + chunk]
        out_p = os.path.join(MERGE_DIR, f"resolved_batch_{n_files:03d}.json")
        with open(out_p, "w", encoding="utf-8") as fh:
            json.dump({
                "batch_index": n_files,
                "count": len(sl),
                "project": "JAGUAR",
                "settlements": sl,
            }, fh, ensure_ascii=False, indent=2)

    print(f"Wrote {len(final_out)} clean merge-ready records across {n_files} files in {MERGE_DIR}")


if __name__ == "__main__":
    main()
