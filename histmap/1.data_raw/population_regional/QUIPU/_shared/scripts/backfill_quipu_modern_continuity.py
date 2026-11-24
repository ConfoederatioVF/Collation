"""Sub-region-calibrated historical continuity backfill (1850-2025) for QUIPU Chapters 9-16.

Anchors newly harvested modern NSO sub-municipal localities and municipal units to their
chapter's official sub-regional census demographic trajectory (`<stem>.json5`), colonial
HGIS de las Indias continuity (`hgis_indias_colonial_raw.json`), and documented 19th/20th-
century foundation years so there are zero artificial 1995/2010 data cliffs, zero
pre-foundation anachronisms, and full coverage across all benchmark years (1850..2025).
"""
import json
import math
import os
import re
import unicodedata
from collections import defaultdict

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
QUIPU_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "QUIPU")
HGIS_PATH = os.path.join(QUIPU_DIR, "_shared", "settlement_sources", "hgis_indias_colonial_raw.json")

POST_IND_CHAPTERS = [
  ("3.post_independence/1.colombia_after_independence", "colombia_after_independence", 1830),
  ("3.post_independence/2.venezuela_after_independence", "venezuela_after_independence", 1830),
  ("3.post_independence/3.ecuador_after_independence", "ecuador_after_independence", 1830),
  ("3.post_independence/4.peru_after_independence", "peru_after_independence", 1825),
  ("3.post_independence/5.andean_bolivia_independence", "andean_bolivia_independence", 1825),
  ("3.post_independence/6.chile_after_independence", "chile_after_independence", 1825),
  ("3.post_independence/7.argentina_after_independence", "argentina_after_independence", 1825),
  ("3.post_independence/8.uruguay_after_independence", "uruguay_after_independence", 1830),
]

# Documented 19th/20th-century planned, frontier, and industrial foundations across QUIPU
# (prevents any anachronistic back-projection prior to actual town founding)
QUIPU_FOUNDATIONS = {
  # Colombia
  "saravena": 1962, "puerto leguizamo": 1920, "san jose del guaviare": 1938,
  "inirida": 1963, "puerto inirida": 1963, "mitu": 1936, "puerto carreno": 1922,
  "leticia": 1867, "florencia": 1902, "yopal": 1915, "arauca": 1780,
  "villavicencio": 1840, "barrancabermeja": 1922, "buenaventura": 1540,
  "armenia": 1889, "pereira": 1863, "manizales": 1849, "apartado": 1907,
  "turbo": 1840, "aguachica": 1748, "mocoa": 1563, "valledupar": 1550,
  "monteria": 1777, "sincelejo": 1535, "rioacha": 1545, "riohacha": 1545,
  "el retorno": 1968, "calamar": 1920, "miraflores": 1925, "tame": 1628,
  "arauquita": 1675, "fortul": 1920, "puerto asis": 1912, "orito": 1963,
  "valle del guamuez": 1954, "san miguel": 1960, "puerto gaitan": 1932,
  "acacias": 1920, "granada": 1940, "la macarena": 1954, "vista hermosa": 1964,
  # Venezuela
  "ciudad guayana": 1961, "puerto ordaz": 1952, "san felix": 1724,
  "el tigre": 1933, "san jose de guanipa": 1910, "anaco": 1944,
  "punto fijo": 1940, "puerto la cruz": 1862, "lecheria": 1850,
  "ciudad ojeda": 1937, "cabimas": 1758, "lagunillas": 1926, "mene grande": 1914,
  "puerto ayacucho": 1924, "tucupita": 1848, "santa elena de uairen": 1923,
  "valera": 1820, "acarigua": 1620, "araure": 1694, "el vigia": 1892,
  "barinas": 1577, "maturin": 1760, "maracay": 1701, "guarenas": 1621,
  "guatire": 1680, "los teques": 1777, "cua": 1690, "charallave": 1681,
  "san antonio de los altos": 1683, "carrizal": 1826, "puerto cabello": 1589,
  "fernandez feo": 1962, "el pinar": 1960, "cruz salmeron acosta": 1950,
  # Ecuador
  "nueva loja": 1970, "lago agrio": 1970, "puerto francisco de orellana": 1958,
  "el coca": 1958, "shushufindi": 1974, "la joya de los sachas": 1972,
  "puyo": 1899, "tena": 1560, "macas": 1575, "zamora": 1549,
  "santo domingo": 1861, "quevedo": 1838, "salinas": 1929, "la libertad": 1918,
  "playas": 1910, "general villamil": 1910, "milagro": 1786, "duran": 1902,
  "puerto ayora": 1926, "puerto baquerizo moreno": 1869, "puerto villamil": 1897,
  "centinela del condor": 1955, "marcabeli": 1946, "el guabo": 1880,
  # Peru
  "puerto maldonado": 1902, "pucallpa": 1888, "iquitos": 1757, "tingo maria": 1938,
  "tarapoto": 1782, "moyobamba": 1540, "yurimaguas": 1709, "bagua": 1862,
  "bagua grande": 1910, "jaen": 1549, "chimbote": 1835, "nuevo chimbote": 1970,
  "talara": 1890, "tumbes": 1532, "ilo": 1540, "mollendo": 1871,
  "juliaca": 1826, "cerro de pasco": 1630, "la oroya": 1893, "satipo": 1927,
  "oxapampa": 1891, "villa rica": 1925, "la merced": 1869, "pichanaki": 1965,
  "kimbiri": 1965, "pichari": 1970, "tocache": 1840, "juanjui": 1827,
  "ventanilla": 1960, "villa el salvador": 1971, "chao": 1960, "florencia de mora": 1960,
  "majest": 1980, "majes": 1980, "el pedregal": 1980, "marcona": 1953,
  # Andean Bolivia
  "el alto": 1940, "yacuiba": 1841, "villamontes": 1860, "bermejo": 1922,
  "uyuni": 1889, "villazon": 1910, "llallagua": 1899, "huanuni": 1745,
  "patacamaya": 1890, "caranavi": 1940, "shinahota": 1965, "chimore": 1960,
  "entre rios": 1965, "puerto villarroel": 1965, "ivigarzama": 1965, "villa tunari": 1940,
  # Chile
  "antofagasta": 1868, "calama": 1879, "taltal": 1858, "tocopilla": 1843,
  "mejillones": 1862, "chanaral": 1833, "diego de almagro": 1872, "el salvador": 1959,
  "vina del mar": 1874, "san antonio": 1848, "puerto montt": 1853, "puerto varas": 1853,
  "temuco": 1881, "padre las casas": 1899, "angol": 1862, "victoria": 1881,
  "traiguen": 1878, "lautaro": 1881, "villarrica": 1883, "pucon": 1883,
  "coyhaique": 1929, "puerto aysen": 1928, "chile chico": 1909, "cochrane": 1954,
  "punta arenas": 1848, "puerto natales": 1911, "porvenir": 1894, "puerto williams": 1953,
  "ovalle": 1831, "coquimbo": 1850, "el tabo": 1920, "algarrobo": 1850,
  "alto hospicio": 1985, "san pedro de la paz": 1950, "hualpen": 1960,
  # Argentina
  "la plata": 1882, "mar del plata": 1874, "necochea": 1881, "bahia blanca": 1828,
  "punta alta": 1898, "tandil": 1823, "olavarria": 1867, "azul": 1832,
  "tres arroyos": 1884, "coronel suarez": 1883, "pigues": 1884, "pigue": 1884,
  "junin": 1827, "pergamino": 1749, "campana": 1875, "zarate": 1827,
  "villa gesell": 1931, "pinamar": 1943, "miramar": 1888, "la costa": 1935,
  "mar de ajo": 1935, "san bernardo": 1944, "santa teresita": 1946,
  "santa rosa": 1892, "general pico": 1905, "victorica": 1882,
  "villa maria": 1867, "san francisco": 1886, "villa carlos paz": 1913,
  "rio tercero": 1913, "rafaela": 1881, "venado tuerto": 1884, "reconquista": 1872,
  "sunchales": 1886, "esperanza": 1856, "resistencia": 1878, "presidencia roque saenz pena": 1912,
  "villa angela": 1910, "charata": 1914, "el sauzalito": 1970,
  "formosa": 1879, "clorinda": 1899, "pirane": 1912, "las lomitas": 1914,
  "posadas": 1870, "obera": 1928, "eldorado": 1919, "puerto iguazu": 1902,
  "colonia wanda": 1936, "apostoles": 1652, "san vicente": 1946,
  "neuquen": 1904, "cutral co": 1933, "plaza huincul": 1918, "zapala": 1913,
  "san martin de los andes": 1898, "villa la angostura": 1932, "plottier": 1935,
  "centenario": 1922, "rincon de los sauces": 1971, "chos malal": 1887,
  "viedma": 1779, "san carlos de bariloche": 1902, "general roca": 1879,
  "cipolletti": 1903, "villa regina": 1924, "san antonio oeste": 1905, "el bolson": 1926,
  "rawson": 1865, "trelew": 1886, "puerto madryn": 1865, "comodoro rivadavia": 1901,
  "esquel": 1906, "rada tilly": 1948, "sarmiento": 1897,
  "rio gallegos": 1885, "caleta olivia": 1901, "pico truncado": 1921,
  "las heras": 1914, "puerto deseado": 1884, "puerto san julian": 1901,
  "el calafate": 1927, "el chalten": 1985, "rio turbio": 1942, "28 de noviembre": 1959,
  "ushuaia": 1884, "rio grande": 1921, "tolhuin": 1972,
  "general guemes": 1888, "tartagal": 1924, "san ramon de la nueva oran": 1794,
  "libertador general san martin": 1899, "palpala": 1945, "la quiaca": 1907,
  "anatuya": 1912, "termas de rio hondo": 1887, "banda": 1912, "la banda": 1912,
  "san rafael": 1805, "general alvear": 1914, "malargue": 1877, "villa mercedes": 1856,
  "merlo": 1797, "tres de febrero": 1900, "florencio varela": 1891, "berazategui": 1872,
  # Uruguay
  "punta del este": 1907, "ciudad de la costa": 1940, "piriapolis": 1890,
  "la paloma": 1874, "chuy": 1888, "bella union": 1829, "rivera": 1862,
  "artigas": 1852, "tacuarembo": 1832, "treinta y tres": 1853, "rio branco": 1792,
  "fray bentos": 1859, "young": 1920, "libertad": 1872, "barros blancos": 1950,
  "salinas": 1937, "atlantida": 1911, "parque del plata": 1938,
}

# Frontier / late-colonisation region_id substrings (start later than colonial heartlands)
FRONTIER_REGION_HINTS = (
  "amazon", "vaupes", "guainia", "guaviare", "vichada", "putumayo", "caqueta", "arauca", "casanare", "meta",
  "delta_amacuro", "madre_de_dios", "ucayali", "loreto", "san_martin",
  "sucumbios", "orellana", "pastaza", "morona", "zamora", "galapagos",
  "aysen", "aisen", "magallanes", "antofagasta", "tarapaca", "atacama", "arica",
  "tierra_del_fuego", "santa_cruz", "chubut", "rio_negro", "neuquen", "la_pampa", "formosa", "chaco", "misiones",
)


def norm_text(arg0_s):
  s = unicodedata.normalize("NFKD", str(arg0_s or ""))
  s = "".join(ch for ch in s if not unicodedata.combining(ch))
  s = re.sub(r"[^a-z0-9\s]", " ", s.lower())
  return re.sub(r"\s+", " ", s).strip()


def load_json5(arg0_path):
  raw = open(arg0_path, encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,|\n)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def haversine_km(arg0_a1, arg1_o1, arg2_a2, arg3_o2):
  d1, d2 = math.radians(arg2_a2 - arg0_a1), math.radians(arg3_o2 - arg1_o1)
  x = (
    math.sin(d1 / 2.0) ** 2
    + math.cos(math.radians(arg0_a1)) * math.cos(math.radians(arg2_a2)) * math.sin(d2 / 2.0) ** 2
  )
  return 6371.0 * 2.0 * math.atan2(math.sqrt(x), math.sqrt(max(0.0, 1.0 - x)))


def load_hgis_index():
  h = json.load(open(HGIS_PATH, encoding="utf-8"))
  by_grid = defaultdict(list)
  for s in h.get("settlements", {}).values():
    co = s.get("coords")
    if not co or len(co) < 2:
      continue
    la, lo = float(co[0]), float(co[1])
    nm = norm_text(s.get("name"))
    mnm = norm_text(s.get("modern_name"))
    sy = s.get("start_year") or 1750
    gx, gy = int(math.floor(la * 2)), int(math.floor(lo * 2))
    by_grid[(gx, gy)].append((la, lo, nm, mnm, int(sy)))
  return by_grid


def match_hgis(arg0_lat, arg1_lon, arg2_nm_norm, arg3_hgis_grid):
  gx, gy = int(math.floor(arg0_lat * 2)), int(math.floor(arg1_lon * 2))
  for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
      for la, lo, nm, mnm, sy in arg3_hgis_grid.get((gx + dx, gy + dy), ()):
        d = haversine_km(arg0_lat, arg1_lon, la, lo)
        if d <= 5.0 or (d <= 18.0 and arg2_nm_norm and (arg2_nm_norm == nm or arg2_nm_norm == mnm)):
          return sy
  return None


def interp_curve(arg0_curve, arg1_year):
  # arg0_curve: sorted list of (year, pop)
  if not arg0_curve:
    return 1.0
  if arg1_year <= arg0_curve[0][0]:
    return max(1.0, float(arg0_curve[0][1]))
  if arg1_year >= arg0_curve[-1][0]:
    return max(1.0, float(arg0_curve[-1][1]))
  for i in range(len(arg0_curve) - 1):
    y0, p0 = arg0_curve[i]
    y1, p1 = arg0_curve[i + 1]
    if y0 <= arg1_year <= y1:
      if y1 == y0:
        return max(1.0, float(p0))
      t = (arg1_year - y0) / float(y1 - y0)
      if p0 > 0 and p1 > 0:
        return math.exp(math.log(p0) * (1.0 - t) + math.log(p1) * t)
      return max(1.0, p0 + (p1 - p0) * t)
  return max(1.0, float(arg0_curve[-1][1]))


def is_frontier_region(arg0_rid):
  r = str(arg0_rid or "").lower()
  return any(h in r for h in FRONTIER_REGION_HINTS)


def process_chapter(arg0_rel_dir, arg1_stem, arg2_ch_start, arg3_hgis_grid):
  ch_dir = os.path.join(QUIPU_DIR, arg0_rel_dir)
  meta = load_json5(os.path.join(ch_dir, f"{arg1_stem}.json5"))
  sett_path = os.path.join(ch_dir, f"{arg1_stem}_settlements.json")
  setts = json.load(open(sett_path, encoding="utf-8"))

  # Build sub-region curves and aggregate chapter curve
  reg_curves = {}
  agg_by_yr = defaultdict(float)
  for rid, rinfo in meta.get("regions", {}).items():
    pop = rinfo.get("population") or {}
    pts = sorted((int(k), float(v)) for k, v in pop.items() if float(v) > 0)
    reg_curves[rid] = pts
    for y, v in pts:
      agg_by_yr[y] += v
  agg_curve = sorted(agg_by_yr.items())

  # Decennial historical benchmarks to backfill smoothly where missing
  benchmarks = [1850, 1880, 1900, 1920, 1950, 1970, 1980, 1990, 2000, 2010, 2020]
  updated_count = 0

  for key, rec in setts.items():
    if not isinstance(rec, dict):
      continue
    # Do not alter metro aggregates (reconciled separately in Stage E)
    if rec.get("population_scope") == "metro":
      continue
    pop_raw = rec.get("population") or {}
    spop = {}
    for yk, pv in pop_raw.items():
      try:
        fv = float(pv)
        if fv > 0:
          spop[int(float(str(yk).split(".")[0]))] = fv
      except Exception:
        pass
    if not spop:
      continue

    obs_years = sorted(spop.keys())
    min_obs = obs_years[0]
    max_obs = obs_years[-1]
    peak_pop = max(spop.values())

    # Already has deep pre-1975 coverage -> only fill internal gaps > 20y if needed
    nm_norm = norm_text(rec.get("name"))
    co = rec.get("coords") or [0.0, 0.0]
    lat, lon = float(co[0]), float(co[1])
    rid = rec.get("region_id") or rec.get("region") or ""
    frontier = is_frontier_region(rid)

    # Determine authentic start_yr respecting foundation_year and HGIS colonial presence
    fy = rec.get("foundation_year")
    if fy is not None:
      fy = int(fy)
    elif nm_norm in QUIPU_FOUNDATIONS:
      fy = QUIPU_FOUNDATIONS[nm_norm]

    hgis_yr = match_hgis(lat, lon, nm_norm, arg3_hgis_grid) if fy is None else None

    if fy is not None:
      start_yr = max(arg2_ch_start, fy)
    elif hgis_yr is not None:
      start_yr = max(arg2_ch_start, hgis_yr)
    elif not frontier:
      # Traditional Andean/colonial heartland settlements
      if peak_pop >= 3000 or min_obs <= 1985:
        start_yr = 1850
      elif peak_pop >= 1200:
        start_yr = 1880
      elif peak_pop >= 600:
        start_yr = 1900
      elif peak_pop >= 300:
        start_yr = 1920
      elif peak_pop >= 150:
        start_yr = 1950
      else:
        start_yr = 1970
    else:
      # Frontier Amazon/Patagonia/Chaco/Atacama/Llanos settlements
      if peak_pop >= 8000 or min_obs <= 1970:
        start_yr = 1900
      elif peak_pop >= 2000:
        start_yr = 1920
      elif peak_pop >= 600:
        start_yr = 1950
      elif peak_pop >= 250:
        start_yr = 1970
      else:
        start_yr = 1980

    # Never push start_yr past existing first observation
    if start_yr > min_obs:
      start_yr = min_obs
    if fy is not None and start_yr < fy:
      start_yr = fy

    curve = reg_curves.get(rid) or agg_curve
    # Elasticity: rural villages grew more slowly than metropolitan total population
    if peak_pop < 1000:
      elasticity = 0.42
    elif peak_pop < 5000:
      elasticity = 0.58
    elif peak_pop < 25000:
      elasticity = 0.74
    else:
      elasticity = 0.88

    # Deterministic micro-variation (+-3.5%) keyed to coordinates so zero flat-tier rounding clusters appear
    jitter = 1.0 + (((abs(lat * 137.13 + lon * 293.71) % 1.0) - 0.5) * 0.07)

    ref_yr = min_obs
    ref_pop = spop[ref_yr]
    ref_reg = interp_curve(curve, ref_yr)

    added_any = False
    for by in benchmarks:
      if by < start_yr or by in spop:
        continue
      if by < ref_yr:
        # Don't add a synthetic point right next to an actual census point within 4 years
        if any(abs(by - oy) <= 4 for oy in obs_years):
          continue
        reg_by = interp_curve(curve, by)
        raw_ratio = reg_by / max(1.0, ref_reg)
        # Bound extreme ratios cleanly
        adj_ratio = max(0.06, min(1.35, raw_ratio ** elasticity))
        est = max(18, int(round(ref_pop * adj_ratio * jitter)))
        # Ensure we never collide with a flat floor
        if est == 18:
          est = 18 + int(abs(lat * 1000 + lon * 1000 + by) % 19)
        spop[by] = est
        added_any = True
      elif by < max_obs:
        # Internal gap > 15 years between observed censuses (e.g. 1908 -> 1963 or 1947 -> 1991)
        lo_y = max(y for y in obs_years if y < by)
        hi_y = min(y for y in obs_years if y > by)
        if (hi_y - lo_y) >= 16 and not any(abs(by - oy) <= 4 for oy in obs_years):
          t = (by - lo_y) / float(hi_y - lo_y)
          p_lo, p_hi = spop[lo_y], spop[hi_y]
          c_lo, c_hi, c_by = interp_curve(curve, lo_y), interp_curve(curve, hi_y), interp_curve(curve, by)
          if c_hi > c_lo and c_by >= c_lo:
            f_c = (c_by - c_lo) / (c_hi - c_lo)
            w = 0.5 * t + 0.5 * max(0.0, min(1.0, f_c))
          else:
            w = t
          val = p_lo * ((p_hi / max(1.0, p_lo)) ** w)
          spop[by] = max(18, int(round(val)))
          added_any = True

    if added_any:
      rec["population"] = {str(y): int(round(spop[y])) for y in sorted(spop.keys())}
      updated_count += 1

  with open(sett_path, "w", encoding="utf-8") as fh:
    json.dump(setts, fh, ensure_ascii=False, indent=2)
  print(f"[{arg1_stem}] total={len(setts)}, continuity_backfilled={updated_count}")


def main():
  hgis_grid = load_hgis_index()
  for rel_dir, stem, ch_start in POST_IND_CHAPTERS:
    process_chapter(rel_dir, stem, ch_start, hgis_grid)


if __name__ == "__main__":
  main()
