"""Recursive archive indexer for Africa Research Files (Operation Viscount / NICETHI).

Scans every file in `histmap/1.data_raw/population_regional/_references/Africa Research Files`,
extracts structured metadata for PDFs, images, KML/KMZ vector layers, and TXT/DOCX files,
exports consolidated KML/KMZ placemarks to GeoJSON, and writes both the full searchable
index and a concise NICETHI macro-subregion summary JSON.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image
import pymupdf

Image.MAX_IMAGE_PIXELS = None


SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
ARCHIVE_ROOT = os.path.join(
    SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "_references", "Africa Research Files"
)
NICETHI_SHARED = os.path.join(
    SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "NICETHI", "_shared"
)
INDEX_OUT_PATH = os.path.join(NICETHI_SHARED, "africa_research_files_index.json")
SUMMARY_OUT_PATH = os.path.join(NICETHI_SHARED, "africa_research_summary.json")
GEOJSON_OUT_PATH = os.path.join(NICETHI_SHARED, "_gis_cache", "africa_research_kml.geojson")

PDF_MAX_SCAN_PAGES = 40
AFRICA_BBOX = (-27.0, -41.0, 64.0, 28.0)  # min_lon, min_lat, max_lon, max_lat

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif"}
KML_EXTS = {".kml", ".kmz"}
TEXT_EXTS = {".txt", ".docx"}

POP_URBAN_KEYWORDS = [
    ("population", re.compile(r"\bpopulations?\b", re.IGNORECASE), 4),
    ("census", re.compile(r"\bcensus(?:es)?\b", re.IGNORECASE), 5),
    ("inhabitants", re.compile(r"\binhabitants?\b", re.IGNORECASE), 5),
    ("cities", re.compile(r"\bcit(?:y|ies)\b", re.IGNORECASE), 3),
    ("towns", re.compile(r"\btowns?\b", re.IGNORECASE), 3),
    ("households", re.compile(r"\bhouseholds?\b", re.IGNORECASE), 4),
    ("tax", re.compile(r"\btax(?:es|ation|payer|payers)?\b", re.IGNORECASE), 3),
    ("hearth", re.compile(r"\bhearths?\b", re.IGNORECASE), 4),
    ("archaeolog", re.compile(r"\barchaeolog\w*", re.IGNORECASE), 2),
    ("radiocarbon", re.compile(r"\bradiocarbon\b", re.IGNORECASE), 3),
    ("walls", re.compile(r"\bwalls?\b", re.IGNORECASE), 2),
    ("hectares", re.compile(r"\bhectares?\b|\bha\b", re.IGNORECASE), 4),
]

NICETHI_REGIONS = [
    "West Africa",
    "Sahel",
    "Nubia/Sudan",
    "Horn/Ethiopia",
    "East Africa/Swahili",
    "Central/Congo/Angola",
    "Southern Africa",
    "Madagascar/Islands",
]

REGION_PATTERNS = {
    "West Africa": re.compile(
        r"\b(west africa|senegambia|senegal|gambia|guinea|sierra leone|liberia|ivory coast|cote d'ivoire|"
        r"c[oô]te d'ivoire|upper volta|voltaic|gulf of guinea|gold coast|slave coast|ashanti|asante|"
        r"dahomey|abomey|yoruba\w*|oyo|ile-ife|ife|ijebu|benin city|edo|igbo\w*|nigeria|ghana|togo|"
        r"akan|fante|fanti|ewe|nupe|nupoid|mande|mandinka|malinke|wolof|serer|sine|saloum|jolof|"
        r"futa jallon|fouta djallon|kongo-?west|bight of benin|bight of biafra|calabar|bonny)\b",
        re.IGNORECASE,
    ),
    "Sahel": re.compile(
        r"\b(sahel\w*|western savanna|central savanna|eastern savanna|lake chad|kanem|bornu|borno|"
        r"hausa\w*|kano|katsina|sokoto|zaria|kebbi|songhai|songhay|mali empire|ancient ghana|"
        r"koumbi saleh|timbuktu|tombouctou|gao|jenne|djenne|djenn[eé]|segu|segou|kaarta|masina|"
        r"fulbe|fulani|peul|tukulor|toucouleur|burkina faso|mossi|yatenga|ouagadougou|niger bend|"
        r"inland niger delta|niger river|mauritania|wadai|ouaddai|bagirmi|kotoko|sao|tuareg|aoukar|"
        r"tekrur|takrur|darfur|sahara\w*)\b",
        re.IGNORECASE,
    ),
    "Nubia/Sudan": re.compile(
        r"\b(nubia\w*|kush\w*|meroe|meroitic|napata|kerma|makuria|alodia|nobatia|nobadia|"
        r"sennar|funj|dongola|soba|kordofan|khartoum|omdurman|blue nile|white nile|"
        r"upper nile|south sudan|anglo-egyptian sudan|mahdist|beja|fashoda|suakin)\b",
        re.IGNORECASE,
    ),
    "Horn/Ethiopia": re.compile(
        r"\b(ethiopia\w*|abyssinia\w*|aksum\w*|axum\w*|gondar|lalibela|tigray|amhara|shoa|shewa|"
        r"harar|oromo\w*|somalia\w*|somaliland|mogadishu|zeila|berbera|adal|eritrea\w*|asmara|"
        r"djibouti|horn of africa|zagwe|solomonic|addis ababa|kaffa|ennarea|damot|beta israel|"
        r"massawa|dahlak)\b",
        re.IGNORECASE,
    ),
    "East Africa/Swahili": re.compile(
        r"\b(swahili|kilwa|mombasa|lamu|pate|malindi|zanzibar|pemba|gedi|shanga|manda|sofal[ao]|"
        r"tanzania|tanganyika|kenya|uganda|buganda|bunyoro|nkore|ankole|rwanda|burundi|"
        r"great lakes|victoria nyanza|lake victoria|bigo|ntusi|nyamwezi|kamba|kikuyu|maasai|"
        r"east africa\w*|bagamoyo|tabora|ujiji|unyamwezi|karagwe|enga[rl]uka|engaruka)\b",
        re.IGNORECASE,
    ),
    "Central/Congo/Angola": re.compile(
        r"\b(kongo|congo|drc|zaire|angola|luanda|ndongo|matamba|kasanje|luba|lunda|kuba|"
        r"loango|cabinda|gabon|cameroon|bamum|bamileke|central african republic|equatorial guinea|"
        r"central africa\w*|equatoria|brazzaville|kinshasa|mbata|mbanza kongo|sao salvador|"
        r"benguela|ovimbundu|mongo|teke|tio|ubangi|kasai|katanga|shaba)\b",
        re.IGNORECASE,
    ),
    "Southern Africa": re.compile(
        r"\b(southern africa|south africa|zimbabwe|great zimbabwe|mutapa|monomotapa|mapungubwe|"
        r"khami|rozvi|torwa|zulu|ndebele|xhosa|sotho|tswana|shona|namibia|botswana|zambia|"
        r"malawi|maravi|lesotho|eswatini|swaziland|mozambique|cape colony|transvaal|natal|"
        r"orange free state|kalahari|limpopo|zambezi|ingombe ilede|toutswe|manyikeni|"
        r"delagoa bay|maputo|inhambane|tete|sena|barotse|lozi|bemba)\b",
        re.IGNORECASE,
    ),
    "Madagascar/Islands": re.compile(
        r"\b(madagascar|malagasy|merina|imamo|imerina|sakalava|antananarivo|betsileo|antsirabe|"
        r"tamatave|toamasina|mahajanga|majunga|comoros|comoro|mayotte|mauritius|reunion|r[eé]union|"
        r"seychelles|cabo verde|cape verde|sao tome|s[aã]o tom[eé]|principe|saint helena|"
        r"mascarene\w*|nosy be|fort dauphin|sainte marie)\b",
        re.IGNORECASE,
    ),
}


def compute_sha256_prefix(file_path, length=16):
    """Return the first `length` hex chars of the file's SHA-256 digest."""
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()[:length]


def clean_text(raw):
    """Collapse excessive whitespace into clean single spaces."""
    if not raw:
        return ""
    return re.sub(r"\s+", " ", raw).strip()


def infer_regions(rel_path, extra_text=""):
    """Infer matching NICETHI regions from folder hierarchy, filename, and text."""
    rel_lower = rel_path.lower().replace("\\", "/")
    matched = set()

    # Folder-level strong priors
    if rel_lower.startswith("1. west africa/"):
        if any(seg in rel_lower for seg in [
            "2. western savanna", "3. central savanna", "4. lake chad",
            "5. eastern savanna", "11. fulbe", "12. sahara"
        ]):
            matched.add("Sahel")
        if any(seg in rel_lower for seg in [
            "1. senegambia", "2. western savanna", "3. central savanna",
            "5. eastern savanna", "6. guinea", "7. ivory coast",
            "8. upper volta", "9. voltaic", "10. gulf of guinea",
            "11. fulbe", "13. west africa general", "14. atlantic world"
        ]):
            matched.add("West Africa")
    elif rel_lower.startswith("3. east africa/"):
        if "/sudan/" in rel_lower:
            matched.add("Nubia/Sudan")
        elif any(seg in rel_lower for seg in ["/ethiopia/", "/oromo/", "/somalia/"]):
            matched.add("Horn/Ethiopia")
        elif "/madagascar/" in rel_lower:
            matched.add("Madagascar/Islands")
        elif "/swahili coast/" in rel_lower:
            matched.add("East Africa/Swahili")
    elif rel_lower.startswith("4. central and southern africa/"):
        # Files here may belong to Central/Congo/Angola and/or Southern Africa
        pass

    # Keyword regex matching on path + filename + text snippet
    combined = f"{rel_path}\n{extra_text}"
    for region, pat in REGION_PATTERNS.items():
        if pat.search(combined):
            matched.add(region)

    # Disambiguate generic 'Sudan' mentions if not already matched
    if "Nubia/Sudan" not in matched and re.search(r"\bsudan\b", combined, re.IGNORECASE):
        if not re.search(r"\b(western|central|french|niger)\s+sudan\b", combined, re.IGNORECASE):
            if not rel_lower.startswith("1. west africa/"):
                matched.add("Nubia/Sudan")

    # If in 4. Central and Southern Africa and still unmatched, tag both Central & Southern
    if not matched and rel_lower.startswith("4. central and southern africa/"):
        matched.update(["Central/Congo/Angola", "Southern Africa"])

    return [r for r in NICETHI_REGIONS if r in matched]


def infer_scope(rel_path, regions):
    """Return a broad geographic/thematic scope label."""
    rel_lower = rel_path.lower().replace("\\", "/")
    if regions:
        return "regional"
    if rel_lower.startswith("2. north africa/"):
        return "north_africa"
    if rel_lower.startswith(("0. basemaps/", "5. general history/", "12. geography/")):
        return "pan_african_or_general"
    return "thematic_or_pan_african"


def classify_image(rel_path, filename):
    """Classify an image into one of the six canonical NICETHI archive categories."""
    rel_lower = rel_path.lower().replace("\\", "/")
    name_lower = filename.lower()

    # 1. City plans
    if "6. cities/city layouts/" in rel_lower:
        return "city_plan"
    if any(tok in name_lower for tok in [
        "city plan", "town plan", "site plan", "urban tell", "city walls", "walls over time",
        "defensive layout", "earthworks", "fortification", "citadel", "palace plan", "mosque plan",
        "layout of", "ruins of"
    ]) or re.search(r"\bplan\b", name_lower):
        return "city_plan"

    # 2. Population / ethnographic maps & reference tables
    if rel_lower.startswith("9. population/"):
        return "population_ethnographic_map"
    if any(tok in name_lower for tok in [
        "population", "inhabitants", "census", "density", "ethnographic", "ethnic",
        "linguistic", "language", "tribes", "peoples", "culture area", "migration",
        "clans", "nations of", "demograph"
    ]):
        return "population_ethnographic_map"

    # 3. Basemaps & physical geography
    if rel_lower.startswith(("0. basemaps/", "12. geography/")):
        return "basemap"
    if any(tok in name_lower for tok in [
        "basemap", "biome", "landform", "ecoregion", "topographic", "rivers map",
        "coastline", "trimmed rivers", "vegetation", "climate map", "rainfall", "elevation"
    ]):
        return "basemap"

    # 4. Trade & resource maps
    if rel_lower.startswith(("7. resources/", "11. maritime/")):
        return "trade_resource_map"
    if any(tok in name_lower for tok in [
        "trade", "caravan", "route", "salt", "gold", "copper", "iron", "slave",
        "textile", "resource", "mine", "maritime", "shipping", "ivory", "kola"
    ]):
        return "trade_resource_map"

    # 5. Historical maps
    if any(seg in rel_lower for seg in [
        "maps/", "6. cities/city maps/", "8. religion/religion maps/",
        "10. governance/", "13. primary sources/primary sources maps/",
        "5. general history/10. mapping/"
    ]):
        return "historical_map"
    if re.search(
        r"\b(empire|kingdom|state|states|conquest|expansion|war|battle|dynasty|"
        r"century|centuries|ce|bce|ad|bc|colonial|partition|expedition|map)\b",
        name_lower,
    ):
        return "historical_map"

    return "other"


def extract_pdf_metadata(file_path, rel_path):
    """Extract PDF metadata, first-page snippet, keyword hits, and NICETHI regions."""
    result = {
        "file_kind": "pdf",
        "page_count": 0,
        "pages_scanned": 0,
        "pdf_title": "",
        "pdf_author": "",
        "first_page_snippet": "",
        "keywords": {kw: False for kw, _, _ in POP_URBAN_KEYWORDS},
        "keyword_counts": {},
        "matched_keywords": [],
        "pop_urban_score": 0,
    }
    try:
        doc = pymupdf.open(file_path)
    except Exception as exc:
        result["pdf_error"] = str(exc)[:200]
        result["regions"] = infer_regions(rel_path)
        result["scope"] = infer_scope(rel_path, result["regions"])
        return result

    try:
        meta = doc.metadata or {}
        result["page_count"] = int(doc.page_count)
        result["pdf_title"] = clean_text(meta.get("title") or "")
        result["pdf_author"] = clean_text(meta.get("author") or "")

        scan_limit = min(doc.page_count, PDF_MAX_SCAN_PAGES)
        result["pages_scanned"] = scan_limit

        page_texts = []
        for idx in range(scan_limit):
            try:
                txt = doc[idx].get_text("text") or ""
            except Exception:
                txt = ""
            if idx == 0:
                result["first_page_snippet"] = clean_text(txt)[:500]
            page_texts.append(txt)

        # Include table of contents titles (covers chapters beyond page 40)
        toc_lines = []
        try:
            for item in doc.get_toc(simple=True):
                if len(item) >= 2 and item[1]:
                    toc_lines.append(str(item[1]))
        except Exception:
            pass

        full_scan_text = "\n".join(
            [result["pdf_title"], rel_path] + toc_lines + page_texts
        )

        kw_counts = {}
        matched = []
        score = 0
        for kw, pat, weight in POP_URBAN_KEYWORDS:
            hits = len(pat.findall(full_scan_text))
            if hits > 0:
                result["keywords"][kw] = True
                kw_counts[kw] = hits
                matched.append(kw)
                score += weight * min(hits, 25)

        # Bonus for explicit demographic/urban table indicators in title or text
        if re.search(r"\b(table|tables|census|population estimates?|urbani[sz]ation|city size)\b", full_scan_text, re.IGNORECASE):
            score += 10
        if re.search(r"\b(population|census|demograph\w*|urban|cities|inhabitants)\b", result["pdf_title"] + " " + rel_path, re.IGNORECASE):
            score += 20

        result["keyword_counts"] = kw_counts
        result["matched_keywords"] = matched
        result["pop_urban_score"] = score
        result["regions"] = infer_regions(rel_path, full_scan_text[:20000])
        result["scope"] = infer_scope(rel_path, result["regions"])
    except Exception as exc:
        result["pdf_error"] = str(exc)[:200]
        result["regions"] = infer_regions(rel_path)
        result["scope"] = infer_scope(rel_path, result["regions"])
    finally:
        doc.close()

    return result


def extract_image_metadata(file_path, rel_path, filename):
    """Extract image dimensions, classification, and geographic region."""
    info = {
        "file_kind": "image",
        "width": None,
        "height": None,
        "image_type": classify_image(rel_path, filename),
        "regions": infer_regions(rel_path),
    }
    info["scope"] = infer_scope(rel_path, info["regions"])
    try:
        with Image.open(file_path) as img:
            w, h = img.size
            info["width"] = int(w)
            info["height"] = int(h)
    except Exception as exc:
        info["image_error"] = str(exc)[:200]
    return info


def extract_docx_text(file_path):
    """Extract paragraph and table text from a DOCX file using stdlib zipfile + XML."""
    parts = []
    with zipfile.ZipFile(file_path) as zf:
        if "word/document.xml" not in zf.namelist():
            return ""
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "t" and elem.text:
            parts.append(elem.text)
        elif tag in ("p", "tr"):
            parts.append("\n")
        elif tag == "tc":
            parts.append(" | ")
    return "".join(parts)


def extract_text_file_metadata(file_path, rel_path, ext):
    """Extract snippet and content-type flags from .txt and .docx files."""
    raw = ""
    err = None
    try:
        if ext == ".docx":
            raw = extract_docx_text(file_path)
        else:
            with open(file_path, "rb") as fh:
                raw_bytes = fh.read()
            raw = raw_bytes.decode("utf-8", errors="replace")
    except Exception as exc:
        err = str(exc)[:200]

    cleaned = clean_text(raw)
    matched_kws = [kw for kw, pat, _ in POP_URBAN_KEYWORDS if pat.search(raw)]
    has_map_key = bool(
        re.search(r"\b(key|legend|brown\s*=|light blue\s*=|green\s*=|orange\s*=)\b", raw, re.IGNORECASE)
        or "key" in os.path.basename(rel_path).lower()
    )
    has_settlement_list = bool(
        re.search(r"\b(settlements?|cities|towns|capital|villages?|sites?)\b", raw, re.IGNORECASE)
    )
    has_pop_notes = bool(
        re.search(r"\b(population|inhabitants|census|demograph|climate|timeline|collapse|oyo)\b", raw, re.IGNORECASE)
    )

    info = {
        "file_kind": "text",
        "text_length": len(raw),
        "text_snippet": cleaned[:800],
        "has_settlement_list": has_settlement_list,
        "has_map_key": has_map_key,
        "has_population_notes": has_pop_notes,
        "matched_keywords": matched_kws,
        "regions": infer_regions(rel_path, raw[:12000]),
    }
    info["scope"] = infer_scope(rel_path, info["regions"])
    if err:
        info["text_error"] = err
    return info


def local_tag(elem):
    """Return XML tag without namespace prefix."""
    return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag


def parse_kml_coords(coord_text):
    """Parse KML coordinate tuples into [[lon, lat], ...] lists."""
    coords = []
    if not coord_text:
        return coords
    for tok in coord_text.strip().split():
        parts = tok.split(",")
        if len(parts) >= 2:
            try:
                lon = round(float(parts[0]), 6)
                lat = round(float(parts[1]), 6)
                coords.append([lon, lat])
            except ValueError:
                continue
    return coords


def parse_kml_geometry(elem):
    """Recursively convert a KML geometry element into a GeoJSON geometry dict."""
    tag = local_tag(elem)
    if tag == "Point":
        for child in elem:
            if local_tag(child) == "coordinates":
                pts = parse_kml_coords(child.text)
                if pts:
                    return {"type": "Point", "coordinates": pts[0]}
        return None

    if tag == "LineString":
        for child in elem:
            if local_tag(child) == "coordinates":
                pts = parse_kml_coords(child.text)
                if len(pts) >= 2:
                    return {"type": "LineString", "coordinates": pts}
        return None

    if tag == "Polygon":
        rings = []
        outer = None
        inners = []
        for child in elem:
            ctag = local_tag(child)
            if ctag == "outerBoundaryIs":
                for lr in child.iter():
                    if local_tag(lr) == "coordinates":
                        pts = parse_kml_coords(lr.text)
                        if len(pts) >= 3:
                            if pts[0] != pts[-1]:
                                pts.append(pts[0])
                            outer = pts
                        break
            elif ctag == "innerBoundaryIs":
                for lr in child.iter():
                    if local_tag(lr) == "coordinates":
                        pts = parse_kml_coords(lr.text)
                        if len(pts) >= 3:
                            if pts[0] != pts[-1]:
                                pts.append(pts[0])
                            inners.append(pts)
                        break
        if outer is None:
            return None
        rings.append(outer)
        rings.extend(inners)
        return {"type": "Polygon", "coordinates": rings}

    if tag == "MultiGeometry":
        geoms = []
        for child in elem:
            g = parse_kml_geometry(child)
            if g is not None:
                geoms.append(g)
        if not geoms:
            return None
        types = {g["type"] for g in geoms}
        if types == {"Polygon"}:
            return {"type": "MultiPolygon", "coordinates": [g["coordinates"] for g in geoms]}
        if types == {"Point"}:
            return {"type": "MultiPoint", "coordinates": [g["coordinates"] for g in geoms]}
        if types == {"LineString"}:
            return {"type": "MultiLineString", "coordinates": [g["coordinates"] for g in geoms]}
        return {"type": "GeometryCollection", "geometries": geoms}

    return None


def iter_all_coords(geom):
    """Yield every [lon, lat] pair from a GeoJSON geometry."""
    gtype = geom.get("type")
    if gtype == "GeometryCollection":
        for sub in geom.get("geometries", []):
            yield from iter_all_coords(sub)
        return
    coords = geom.get("coordinates")
    if gtype == "Point" and coords:
        yield coords
    elif gtype in ("LineString", "MultiPoint") and coords:
        for pt in coords:
            yield pt
    elif gtype in ("Polygon", "MultiLineString") and coords:
        for ring in coords:
            for pt in ring:
                yield pt
    elif gtype == "MultiPolygon" and coords:
        for poly in coords:
            for ring in poly:
                for pt in ring:
                    yield pt


def geom_in_africa_bbox(geom):
    """Return True if any vertex or bbox overlaps AFRICA_BBOX."""
    min_lon = float("inf")
    min_lat = float("inf")
    max_lon = float("-inf")
    max_lat = float("-inf")
    any_pt = False
    for pt in iter_all_coords(geom):
        any_pt = True
        lon, lat = pt[0], pt[1]
        if lon < min_lon:
            min_lon = lon
        if lon > max_lon:
            max_lon = lon
        if lat < min_lat:
            min_lat = lat
        if lat > max_lat:
            max_lat = lat
    if not any_pt:
        return False
    a_min_lon, a_min_lat, a_max_lon, a_max_lat = AFRICA_BBOX
    return not (max_lon < a_min_lon or min_lon > a_max_lon or max_lat < a_min_lat or min_lat > a_max_lat)


def parse_kml_xml(xml_bytes, rel_path, kml_member, features_out):
    """Parse Placemarks and GroundOverlays from KML bytes."""
    cleaned_xml = re.sub(rb'\sxmlns:xmlns="[^"]*"', b"", xml_bytes)
    root = ET.fromstring(cleaned_xml)
    stats = {
        "placemark_count": 0,
        "polygon_count": 0,
        "point_count": 0,
        "linestring_count": 0,
        "ground_overlay_count": 0,
        "ground_overlays": [],
    }

    def walk(node, folder_stack):
        tag = local_tag(node)
        if tag in ("Folder", "Document"):
            fname = ""
            for ch in node:
                if local_tag(ch) == "name" and ch.text:
                    fname = clean_text(ch.text)
                    break
            next_stack = folder_stack + ([fname] if fname else [])
            for ch in node:
                walk(ch, next_stack)
            return

        if tag == "GroundOverlay":
            stats["ground_overlay_count"] += 1
            ov = {"name": "", "href": "", "lat_lon_box": {}}
            for ch in node:
                ctag = local_tag(ch)
                if ctag == "name" and ch.text:
                    ov["name"] = clean_text(ch.text)
                elif ctag == "Icon":
                    for ic in ch:
                        if local_tag(ic) == "href" and ic.text:
                            ov["href"] = clean_text(ic.text)
                elif ctag == "LatLonBox":
                    for bc in ch:
                        btag = local_tag(bc)
                        if bc.text:
                            try:
                                ov["lat_lon_box"][btag] = float(bc.text.strip())
                            except ValueError:
                                pass
            stats["ground_overlays"].append(ov)
            return

        if tag == "Placemark":
            pm_idx = stats["placemark_count"]
            stats["placemark_count"] += 1
            name = ""
            desc = ""
            style_url = ""
            ext_data = {}
            geom = None

            for ch in node:
                ctag = local_tag(ch)
                if ctag == "name" and ch.text:
                    name = clean_text(ch.text)
                elif ctag == "description" and ch.text:
                    desc = clean_text(ch.text)[:1000]
                elif ctag == "styleUrl" and ch.text:
                    style_url = clean_text(ch.text)
                elif ctag == "ExtendedData":
                    for ed in ch.iter():
                        ed_tag = local_tag(ed)
                        if ed_tag in ("SimpleData", "Data") and ed.attrib.get("name"):
                            val = ed.text
                            if val is None:
                                for sub in ed:
                                    if local_tag(sub) == "value" and sub.text:
                                        val = sub.text
                                        break
                            if val is not None:
                                ext_data[ed.attrib["name"]] = clean_text(val)
                elif ctag in ("Point", "LineString", "Polygon", "MultiGeometry"):
                    geom = parse_kml_geometry(ch)

            if geom is not None:
                gtype = geom["type"]
                if "Polygon" in gtype:
                    stats["polygon_count"] += 1
                elif "Point" in gtype:
                    stats["point_count"] += 1
                elif "LineString" in gtype:
                    stats["linestring_count"] += 1

                features_out.append({
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {
                        "name": name,
                        "description": desc,
                        "source_file": rel_path,
                        "kml_member": kml_member,
                        "folder_path": " / ".join(folder_stack),
                        "placemark_index": pm_idx,
                        "style_url": style_url,
                        "extended_data": ext_data,
                        "in_africa_bbox": geom_in_africa_bbox(geom),
                    },
                })
            return

        for ch in node:
            walk(ch, folder_stack)

    walk(root, [])
    return stats


def extract_kml_kmz_metadata(file_path, rel_path, ext, features_out):
    """Parse a .kml or .kmz file, appending all placemarks into `features_out`."""
    agg = {
        "file_kind": ext.lstrip("."),
        "placemark_count": 0,
        "polygon_count": 0,
        "point_count": 0,
        "linestring_count": 0,
        "ground_overlay_count": 0,
        "ground_overlays": [],
        "kml_members": [],
        "regions": infer_regions(rel_path),
    }
    agg["scope"] = infer_scope(rel_path, agg["regions"])

    try:
        if ext == ".kml":
            with open(file_path, "rb") as fh:
                xml_bytes = fh.read()
            agg["kml_members"].append(os.path.basename(file_path))
            st = parse_kml_xml(xml_bytes, rel_path, os.path.basename(file_path), features_out)
            for k in ("placemark_count", "polygon_count", "point_count", "linestring_count", "ground_overlay_count"):
                agg[k] += st[k]
            agg["ground_overlays"].extend(st["ground_overlays"])
        else:
            with zipfile.ZipFile(file_path) as zf:
                for member in sorted(zf.namelist()):
                    if member.startswith("__MACOSX/") or os.path.basename(member).startswith("._"):
                        continue
                    if not member.lower().endswith(".kml"):
                        continue
                    agg["kml_members"].append(member)
                    xml_bytes = zf.read(member)
                    st = parse_kml_xml(xml_bytes, rel_path, member, features_out)
                    for k in ("placemark_count", "polygon_count", "point_count", "linestring_count", "ground_overlay_count"):
                        agg[k] += st[k]
                    agg["ground_overlays"].extend(st["ground_overlays"])
    except Exception as exc:
        agg["kml_error"] = str(exc)[:200]

    return agg


def build_summary(records, kml_features, dup_groups):
    """Build concise human-readable summary grouped by NICETHI macro-subregion."""
    counts_by_kind = Counter(r.get("file_kind", "other") for r in records)
    counts_by_ext = Counter(r["ext"] for r in records)
    counts_by_image_type = Counter(
        r["image_type"] for r in records if r.get("file_kind") == "image"
    )

    pdfs = [r for r in records if r.get("file_kind") == "pdf"]
    images = [r for r in records if r.get("file_kind") == "image"]
    texts = [r for r in records if r.get("file_kind") == "text"]
    kmls = [r for r in records if r.get("file_kind") in ("kml", "kmz")]

    def pdf_brief(r):
        return {
            "rel_path": r["rel_path"],
            "pdf_title": r.get("pdf_title", ""),
            "page_count": r.get("page_count", 0),
            "regions": r.get("regions", []),
            "matched_keywords": r.get("matched_keywords", []),
            "keyword_counts": r.get("keyword_counts", {}),
            "pop_urban_score": r.get("pop_urban_score", 0),
        }

    def img_brief(r):
        return {
            "rel_path": r["rel_path"],
            "image_type": r.get("image_type", "other"),
            "width": r.get("width"),
            "height": r.get("height"),
            "regions": r.get("regions", []),
        }

    def dedup_top_pdfs(pdf_list, limit):
        seen_sha = set()
        out = []
        for item in sorted(pdf_list, key=lambda x: (-x.get("pop_urban_score", 0), -len(x.get("matched_keywords", [])), x["rel_path"])):
            sha = item.get("sha256")
            if sha in seen_sha:
                continue
            seen_sha.add(sha)
            out.append(pdf_brief(item))
            if len(out) >= limit:
                break
        return out

    top_pdfs_overall = dedup_top_pdfs(pdfs, 40)

    city_plans_all = [
        img_brief(r)
        for r in sorted(
            [r for r in images if r.get("image_type") == "city_plan"],
            key=lambda x: x["rel_path"],
        )
    ]

    city_maps_and_pop_tables = [
        img_brief(r)
        for r in sorted(
            [
                r for r in images
                if "6. cities/city maps/" in r["rel_path"].lower()
                or "9. population/refrence tables/" in r["rel_path"].lower()
            ],
            key=lambda x: x["rel_path"],
        )
    ]

    by_region = {}
    for region in NICETHI_REGIONS:
        reg_recs = [r for r in records if region in r.get("regions", [])]
        reg_pdfs = [r for r in reg_recs if r.get("file_kind") == "pdf"]
        reg_imgs = [r for r in reg_recs if r.get("file_kind") == "image"]
        by_region[region] = {
            "total_files": len(reg_recs),
            "pdf_count": len(reg_pdfs),
            "image_count": len(reg_imgs),
            "city_plan_count": sum(1 for r in reg_imgs if r.get("image_type") == "city_plan"),
            "historical_map_count": sum(1 for r in reg_imgs if r.get("image_type") == "historical_map"),
            "population_ethnographic_map_count": sum(1 for r in reg_imgs if r.get("image_type") == "population_ethnographic_map"),
            "top_population_urban_pdfs": dedup_top_pdfs(reg_pdfs, 15),
            "city_plan_images": [
                img_brief(r)
                for r in sorted([r for r in reg_imgs if r.get("image_type") == "city_plan"], key=lambda x: x["rel_path"])[:30]
            ],
            "population_ethnographic_images": [
                img_brief(r)
                for r in sorted([r for r in reg_imgs if r.get("image_type") == "population_ethnographic_map"], key=lambda x: x["rel_path"])[:20]
            ],
        }

    # Unmapped / adjacent / pan-African bucket
    unmapped = [r for r in records if not r.get("regions")]
    by_region["Pan-African / Adjacent North Africa / General"] = {
        "total_files": len(unmapped),
        "pdf_count": sum(1 for r in unmapped if r.get("file_kind") == "pdf"),
        "image_count": sum(1 for r in unmapped if r.get("file_kind") == "image"),
        "top_population_urban_pdfs": dedup_top_pdfs(
            [r for r in unmapped if r.get("file_kind") == "pdf"], 15
        ),
    }

    africa_kml_count = sum(1 for f in kml_features if f["properties"].get("in_africa_bbox"))
    kml_summary = {
        "geojson_path": GEOJSON_OUT_PATH.replace("\\", "/"),
        "kml_kmz_file_count": len(kmls),
        "total_placemarks_exported": len(kml_features),
        "africa_bbox_placemarks": africa_kml_count,
        "files": [
            {
                "rel_path": r["rel_path"],
                "placemark_count": r.get("placemark_count", 0),
                "polygon_count": r.get("polygon_count", 0),
                "point_count": r.get("point_count", 0),
                "linestring_count": r.get("linestring_count", 0),
                "ground_overlay_count": r.get("ground_overlay_count", 0),
                "ground_overlays": r.get("ground_overlays", []),
            }
            for r in kmls
        ],
        "sample_africa_placemarks": [
            {
                "name": f["properties"].get("name"),
                "source_file": f["properties"].get("source_file"),
                "geometry_type": f["geometry"]["type"],
                "extended_data": f["properties"].get("extended_data"),
            }
            for f in kml_features
            if f["properties"].get("in_africa_bbox")
        ][:15],
    }

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "archive_root": ARCHIVE_ROOT.replace("\\", "/"),
        "total_files": len(records),
        "counts_by_kind": dict(counts_by_kind),
        "counts_by_extension": dict(counts_by_ext),
        "counts_by_image_type": dict(counts_by_image_type),
        "duplicate_groups_count": len(dup_groups),
        "duplicate_groups_top20": dup_groups[:20],
        "kml_kmz_summary": kml_summary,
        "by_nicethi_region": by_region,
        "top_population_urban_pdfs_overall": top_pdfs_overall,
        "city_plan_images_all": city_plans_all,
        "city_maps_and_population_tables": city_maps_and_pop_tables,
        "txt_and_docx_files": [
            {
                "rel_path": r["rel_path"],
                "ext": r["ext"],
                "text_length": r.get("text_length", 0),
                "has_settlement_list": r.get("has_settlement_list", False),
                "has_map_key": r.get("has_map_key", False),
                "has_population_notes": r.get("has_population_notes", False),
                "regions": r.get("regions", []),
                "text_snippet": r.get("text_snippet", ""),
            }
            for r in texts
        ],
    }


def main():
    if not os.path.isdir(ARCHIVE_ROOT):
        print(f"[ERROR] Archive root not found: {ARCHIVE_ROOT}", file=sys.stderr)
        return 1

    all_paths = []
    for dirpath, _, filenames in os.walk(ARCHIVE_ROOT):
        for fname in sorted(filenames):
            all_paths.append(os.path.join(dirpath, fname))
    all_paths.sort()

    total = len(all_paths)
    print(f"[index_africa_research_files] Found {total} files under {ARCHIVE_ROOT}")

    records = []
    kml_features = []
    sha_map = defaultdict(list)

    for idx, full_path in enumerate(all_paths, 1):
        rel_path = os.path.relpath(full_path, ARCHIVE_ROOT).replace("\\", "/")
        parts = rel_path.split("/")
        top_folder = parts[0] if len(parts) > 1 else ""
        subfolder = "/".join(parts[1:-1]) if len(parts) > 2 else ""
        filename = parts[-1]
        ext = os.path.splitext(filename)[1].lower()
        size_bytes = os.path.getsize(full_path)
        sha16 = compute_sha256_prefix(full_path, 16)
        sha_map[sha16].append(rel_path)

        rec = {
            "rel_path": rel_path,
            "top_folder": top_folder,
            "subfolder": subfolder,
            "filename": filename,
            "ext": ext,
            "size_bytes": size_bytes,
            "sha256": sha16,
        }

        if ext == ".pdf":
            rec.update(extract_pdf_metadata(full_path, rel_path))
        elif ext in IMAGE_EXTS:
            rec.update(extract_image_metadata(full_path, rel_path, filename))
        elif ext in KML_EXTS:
            rec.update(extract_kml_kmz_metadata(full_path, rel_path, ext, kml_features))
        elif ext in TEXT_EXTS:
            rec.update(extract_text_file_metadata(full_path, rel_path, ext))
        else:
            rec["file_kind"] = "other"
            rec["regions"] = infer_regions(rel_path)
            rec["scope"] = infer_scope(rel_path, rec["regions"])

        records.append(rec)
        if idx % 300 == 0 or idx == total:
            print(f"[index_africa_research_files] Processed {idx}/{total} files...")

    dup_groups = [
        {"sha256": sha, "count": len(paths), "rel_paths": paths}
        for sha, paths in sorted(sha_map.items())
        if len(paths) > 1
    ]

    dup_lookup = {}
    for grp in dup_groups:
        primary = grp["rel_paths"][0]
        for p in grp["rel_paths"][1:]:
            dup_lookup[p] = primary
    for rec in records:
        if rec["rel_path"] in dup_lookup:
            rec["duplicate_of"] = dup_lookup[rec["rel_path"]]

    # Write consolidated GeoJSON
    os.makedirs(os.path.dirname(GEOJSON_OUT_PATH), exist_ok=True)
    geojson_payload = {
        "type": "FeatureCollection",
        "metadata": {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "source_root": ARCHIVE_ROOT.replace("\\", "/"),
            "total_features": len(kml_features),
            "africa_bbox_features": sum(1 for f in kml_features if f["properties"].get("in_africa_bbox")),
        },
        "features": kml_features,
    }
    with open(GEOJSON_OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(geojson_payload, fh, ensure_ascii=False)

    # Write full searchable index
    counts_by_ext = dict(Counter(r["ext"] for r in records))
    counts_by_top = dict(Counter(r["top_folder"] for r in records))
    counts_by_reg = {
        reg: sum(1 for r in records if reg in r.get("regions", []))
        for reg in NICETHI_REGIONS
    }
    index_payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": ARCHIVE_ROOT.replace("\\", "/"),
        "total_files": len(records),
        "counts_by_extension": counts_by_ext,
        "counts_by_top_folder": counts_by_top,
        "counts_by_region": counts_by_reg,
        "duplicate_sha256_groups": dup_groups,
        "files": records,
    }
    with open(INDEX_OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(index_payload, fh, ensure_ascii=False, indent=2)

    # Write concise summary
    summary_payload = build_summary(records, kml_features, dup_groups)
    with open(SUMMARY_OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(summary_payload, fh, ensure_ascii=False, indent=2)

    print(f"[index_africa_research_files] Wrote GeoJSON ({len(kml_features)} features): {GEOJSON_OUT_PATH}")
    print(f"[index_africa_research_files] Wrote full index ({len(records)} files): {INDEX_OUT_PATH}")
    print(f"[index_africa_research_files] Wrote summary: {SUMMARY_OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
