"""Resolves Operation Viscount CASTLE historical toponymy batches and curates authoritative
multi-millennial Japanese & Korean city name transitions for Dataview `stadester_2.0/city_metadata.json`.

Sources:
1. Curated scholarly Japanese & Korean historical toponymy catalogue (ancient Yamato/Ritsuryo/Three Kingdoms/
   Gaya/Balhae -> Heian/Goryeo -> Sengoku/Edo jokamachi & Joseon Eight Provinces -> Meiji/Japanese Colonial
   exonyms -> post-1945/Heisei/ROK-DPRK official modern names).
2. Official GeoNames alternate names (cached in `_census_cache/geonames_{JP,KR,KP}.zip`), strictly filtered
   to clean Latin + authentic Japanese/Korean scripts (Hiragana, Katakana, Kanji/Hanja, Hangul; ZERO Cyrillic
   or foreign-script spam).
"""

import json
import math
import os
import re
import sys
import zipfile
from collections import defaultdict


SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CENSUS_DIR = os.path.join(
  SVEA_ROOT,
  "histmap", "1.data_raw", "population_regional", "CASTLE", "_shared", "_census_cache"
)
DATAVIEW_META = r"F:\Active Projects\Project 1436 - Dataview\data\stadester\stadester_2.0\city_metadata.json"
BATCH_DIR = os.path.join(SVEA_ROOT, "tests", "toponymy_batches", "castle")

# Authoritative curated chronological toponymy transitions keyed by (normalised_modern_name, country).
# Every entry strictly terminates with the exact modern canonical settlement name.
CURATED_HISTORICAL_NAMES = {
  # --- JAPAN ---
  ("tokyo", "Japan"): [
    {"date": "1457.1.1", "name": "Edo"},
    {"date": "1868.9.3", "name": "Tokyo"},
  ],
  ("kyoto", "Japan"): [
    {"date": "794.11.18", "name": "Heian-kyo"},
    {"date": "1868.9.3", "name": "Kyoto"},
  ],
  ("osaka", "Japan"): [
    {"date": "500.1.1", "name": "Naniwa"},
    {"date": "645.1.1", "name": "Naniwa-kyo"},
    {"date": "1496.1.1", "name": "Ishiyama"},
    {"date": "1583.1.1", "name": "Osaka"},
  ],
  ("nara", "Japan"): [
    {"date": "710.1.1", "name": "Heijo-kyo"},
    {"date": "784.1.1", "name": "Nara"},
  ],
  ("nagoya", "Japan"): [
    {"date": "1550.1.1", "name": "Kiyosu"},
    {"date": "1610.1.1", "name": "Nagoya"},
  ],
  ("yokohama", "Japan"): [
    {"date": "1601.1.1", "name": "Kanagawa-juku"},
    {"date": "1859.7.1", "name": "Yokohama"},
  ],
  ("kobe", "Japan"): [
    {"date": "750.1.1", "name": "Owada-no-Tomari"},
    {"date": "1180.6.1", "name": "Fukuhara"},
    {"date": "1185.1.1", "name": "Hyogo"},
    {"date": "1868.1.1", "name": "Kobe"},
  ],
  ("fukuoka", "Japan"): [
    {"date": "100.1.1", "name": "Na-no-tsu"},
    {"date": "750.1.1", "name": "Hakata"},
    {"date": "1601.1.1", "name": "Fukuoka"},
  ],
  ("sapporo", "Japan"): [
    {"date": "1869.9.1", "name": "Sapporo"},
  ],
  ("kanazawa", "Japan"): [
    {"date": "1546.1.1", "name": "Oyama Gobo"},
    {"date": "1583.1.1", "name": "Kanazawa"},
  ],
  ("shizuoka", "Japan"): [
    {"date": "700.1.1", "name": "Suruga Kokufu"},
    {"date": "1585.1.1", "name": "Sunpu"},
    {"date": "1869.6.1", "name": "Shizuoka"},
  ],
  ("fukui", "Japan"): [
    {"date": "1575.1.1", "name": "Kitanosho"},
    {"date": "1624.1.1", "name": "Fukui"},
  ],
  ("akita", "Japan"): [
    {"date": "733.1.1", "name": "Akita-jo"},
    {"date": "1604.1.1", "name": "Kubota"},
    {"date": "1871.8.29", "name": "Akita"},
  ],
  ("shimonoseki", "Japan"): [
    {"date": "1185.1.1", "name": "Akamagaseki"},
    {"date": "1902.6.1", "name": "Shimonoseki"},
  ],
  ("hakodate", "Japan"): [
    {"date": "1454.1.1", "name": "Usukeshi"},
    {"date": "1869.1.1", "name": "Hakodate"},
  ],
  ("matsumae", "Japan"): [
    {"date": "1450.1.1", "name": "Fukuyama"},
    {"date": "1869.1.1", "name": "Matsumae"},
  ],
  ("naha", "Japan"): [
    {"date": "1372.1.1", "name": "Shuri-Naha"},
    {"date": "1879.3.27", "name": "Naha"},
  ],
  ("kitakyushu", "Japan"): [
    {"date": "1602.1.1", "name": "Kokura"},
    {"date": "1963.2.10", "name": "Kitakyushu"},
  ],
  ("saitama", "Japan"): [
    {"date": "1601.1.1", "name": "Urawa"},
    {"date": "2001.5.1", "name": "Saitama"},
  ],
  ("sendai", "Japan"): [
    {"date": "724.1.1", "name": "Taga-jo"},
    {"date": "1600.12.24", "name": "Sendai"},
  ],
  ("kushiro", "Japan"): [
    {"date": "1869.1.1", "name": "Kusuri"},
    {"date": "1880.1.1", "name": "Kushiro"},
  ],
  ("maebashi", "Japan"): [
    {"date": "1490.1.1", "name": "Umayabashi"},
    {"date": "1649.1.1", "name": "Maebashi"},
  ],
  ("utsunomiya", "Japan"): [
    {"date": "1063.1.1", "name": "Utsunomiya"},
  ],
  ("kofu", "Japan"): [
    {"date": "1519.1.1", "name": "Kofu"},
  ],
  ("matsumoto", "Japan"): [
    {"date": "1504.1.1", "name": "Fukashi"},
    {"date": "1582.1.1", "name": "Matsumoto"},
  ],
  ("gifu", "Japan"): [
    {"date": "1201.1.1", "name": "Inokuchi"},
    {"date": "1567.1.1", "name": "Gifu"},
  ],
  ("otsu", "Japan"): [
    {"date": "667.1.1", "name": "Omi-kyo"},
    {"date": "1586.1.1", "name": "Otsu"},
  ],
  ("hamamatsu", "Japan"): [
    {"date": "1500.1.1", "name": "Hikuma"},
    {"date": "1570.1.1", "name": "Hamamatsu"},
  ],
  ("aizuwakamatsu", "Japan"): [
    {"date": "1384.1.1", "name": "Kurokawa"},
    {"date": "1592.1.1", "name": "Wakamatsu"},
    {"date": "1955.1.1", "name": "Aizuwakamatsu"},
  ],
  ("shunan", "Japan"): [
    {"date": "1617.1.1", "name": "Tokuyama"},
    {"date": "2003.4.21", "name": "Shunan"},
  ],
  ("echizen", "Japan"): [
    {"date": "700.1.1", "name": "Takefu"},
    {"date": "2005.10.1", "name": "Echizen"},
  ],
  ("iga", "Japan"): [
    {"date": "1585.1.1", "name": "Iga-Ueno"},
    {"date": "2004.11.1", "name": "Iga"},
  ],
  ("oshu", "Japan"): [
    {"date": "802.1.1", "name": "Isawa"},
    {"date": "1600.1.1", "name": "Mizusawa"},
    {"date": "2006.2.20", "name": "Oshu"},
  ],
  ("amakusa", "Japan"): [
    {"date": "1589.1.1", "name": "Hondo"},
    {"date": "2006.3.27", "name": "Amakusa"},
  ],
  ("chikusei", "Japan"): [
    {"date": "1478.1.1", "name": "Shimodate"},
    {"date": "2005.3.28", "name": "Chikusei"},
  ],
  ("shimanto", "Japan"): [
    {"date": "1468.1.1", "name": "Nakamura"},
    {"date": "2005.4.10", "name": "Shimanto"},
  ],
  ("minamisatsuma", "Japan"): [
    {"date": "1600.1.1", "name": "Kaseda"},
    {"date": "2005.11.7", "name": "Minamisatsuma"},
  ],
  ("asakura", "Japan"): [
    {"date": "1600.1.1", "name": "Amagi"},
    {"date": "2006.3.20", "name": "Asakura"},
  ],
  ("itoshima", "Japan"): [
    {"date": "1600.1.1", "name": "Maebaru"},
    {"date": "2010.1.1", "name": "Itoshima"},
  ],
  ("joso", "Japan"): [
    {"date": "1600.1.1", "name": "Mitsukaido"},
    {"date": "2006.1.1", "name": "Joso"},
  ],
  ("myoko", "Japan"): [
    {"date": "1600.1.1", "name": "Arai"},
    {"date": "2005.4.1", "name": "Myoko"},
  ],
  ("koshu", "Japan"): [
    {"date": "1600.1.1", "name": "Enzan"},
    {"date": "2005.11.1", "name": "Koshu"},
  ],
  ("fujimino", "Japan"): [
    {"date": "1972.4.10", "name": "Kamifukuoka"},
    {"date": "2005.10.1", "name": "Fujimino"},
  ],
  ("sanyoonoda", "Japan"): [
    {"date": "1940.11.3", "name": "Onoda"},
    {"date": "2005.3.22", "name": "San-yo-onoda"},
  ],
  ("sosa", "Japan"): [
    {"date": "1600.1.1", "name": "Yokaichiba"},
    {"date": "2006.1.23", "name": "Sosa"},
  ],
  ("chikuma", "Japan"): [
    {"date": "1959.6.1", "name": "Koshoku"},
    {"date": "2003.9.1", "name": "Chikuma"},
  ],
  ("isa", "Japan"): [
    {"date": "1600.1.1", "name": "Okuchi"},
    {"date": "2008.11.1", "name": "Isa"},
  ],
  # --- SOUTH KOREA ---
  ("seoul", "South Korea"): [
    {"date": "-18.1.1", "name": "Wiryeseong"},
    {"date": "1067.1.1", "name": "Namgyeong"},
    {"date": "1394.11.29", "name": "Hanseong"},
    {"date": "1910.10.1", "name": "Keijo"},
    {"date": "1945.8.15", "name": "Seoul"},
  ],
  ("gyeongju", "South Korea"): [
    {"date": "-57.1.1", "name": "Seorabeol"},
    {"date": "503.1.1", "name": "Geumseong"},
    {"date": "935.1.1", "name": "Gyeongju"},
    {"date": "1910.10.1", "name": "Keishu"},
    {"date": "1945.8.15", "name": "Gyeongju"},
  ],
  ("busan", "South Korea"): [
    {"date": "757.1.1", "name": "Dongnae"},
    {"date": "1407.1.1", "name": "Busan"},
    {"date": "1910.10.1", "name": "Fusan"},
    {"date": "1945.8.15", "name": "Busan"},
  ],
  ("daegu", "South Korea"): [
    {"date": "261.1.1", "name": "Dalgubeol"},
    {"date": "757.1.1", "name": "Daegu"},
    {"date": "1910.10.1", "name": "Taikyu"},
    {"date": "1945.8.15", "name": "Daegu"},
  ],
  ("incheon", "South Korea"): [
    {"date": "-18.1.1", "name": "Michuhol"},
    {"date": "1413.1.1", "name": "Incheon"},
    {"date": "1883.1.1", "name": "Jemulpo"},
    {"date": "1910.10.1", "name": "Jinsen"},
    {"date": "1945.8.15", "name": "Incheon"},
  ],
  ("gwangju", "South Korea"): [
    {"date": "685.1.1", "name": "Muju"},
    {"date": "940.1.1", "name": "Gwangju"},
    {"date": "1910.10.1", "name": "Koshu"},
    {"date": "1945.8.15", "name": "Gwangju"},
  ],
  ("daejeon", "South Korea"): [
    {"date": "1905.1.1", "name": "Hanbat"},
    {"date": "1910.10.1", "name": "Taiden"},
    {"date": "1945.8.15", "name": "Daejeon"},
  ],
  ("jeonju", "South Korea"): [
    {"date": "685.1.1", "name": "Wansanju"},
    {"date": "757.1.1", "name": "Jeonju"},
    {"date": "1910.10.1", "name": "Zenshu"},
    {"date": "1945.8.15", "name": "Jeonju"},
  ],
  ("gongju", "South Korea"): [
    {"date": "475.1.1", "name": "Ungjin"},
    {"date": "685.1.1", "name": "Ungju"},
    {"date": "940.1.1", "name": "Gongju"},
    {"date": "1910.10.1", "name": "Koshu"},
    {"date": "1945.8.15", "name": "Gongju"},
  ],
  ("buyeo", "South Korea"): [
    {"date": "538.1.1", "name": "Sabi"},
    {"date": "660.1.1", "name": "Buyeo"},
  ],
  ("gimhae", "South Korea"): [
    {"date": "42.1.1", "name": "Geumgwan Gaya"},
    {"date": "757.1.1", "name": "Gimhae"},
  ],
  ("goryeong", "South Korea"): [
    {"date": "100.1.1", "name": "Daegaya"},
    {"date": "757.1.1", "name": "Goryeong"},
  ],
  ("suwon", "South Korea"): [
    {"date": "940.1.1", "name": "Suwon"},
    {"date": "1796.1.1", "name": "Hwaseong"},
    {"date": "1910.10.1", "name": "Suigen"},
    {"date": "1945.8.15", "name": "Suwon"},
  ],
  ("gangneung", "South Korea"): [
    {"date": "-100.1.1", "name": "Haseulla"},
    {"date": "757.1.1", "name": "Myeongju"},
    {"date": "1308.1.1", "name": "Gangneung"},
  ],
  ("chungju", "South Korea"): [
    {"date": "557.1.1", "name": "Gukwon"},
    {"date": "757.1.1", "name": "Jungwon"},
    {"date": "940.1.1", "name": "Chungju"},
  ],
  ("andong", "South Korea"): [
    {"date": "100.1.1", "name": "Gochang"},
    {"date": "930.1.1", "name": "Andong"},
  ],
  ("jeju", "South Korea"): [
    {"date": "1.1.1", "name": "Tamna"},
    {"date": "1105.1.1", "name": "Jeju"},
  ],
  ("iksan", "South Korea"): [
    {"date": "100.1.1", "name": "Geumma"},
    {"date": "1912.1.1", "name": "Iri"},
    {"date": "1995.5.10", "name": "Iksan"},
  ],
  ("boryeong", "South Korea"): [
    {"date": "1986.1.1", "name": "Daecheon"},
    {"date": "1995.1.1", "name": "Boryeong"},
  ],
  ("mungyeong", "South Korea"): [
    {"date": "1986.1.1", "name": "Jeomchon"},
    {"date": "1995.1.1", "name": "Mungyeong"},
  ],
  ("namyangju", "South Korea"): [
    {"date": "1989.1.1", "name": "Migeum"},
    {"date": "1995.1.1", "name": "Namyangju"},
  ],
  ("sacheon", "South Korea"): [
    {"date": "1956.7.8", "name": "Samcheonpo"},
    {"date": "1995.5.10", "name": "Sacheon"},
  ],
  ("changwon", "South Korea"): [
    {"date": "1408.1.1", "name": "Changwon"},
    {"date": "1899.5.1", "name": "Masan"},
    {"date": "2010.7.1", "name": "Changwon"},
  ],
  # --- NORTH KOREA ---
  ("pyongyang", "North Korea"): [
    {"date": "-300.1.1", "name": "Wanggeom-seong"},
    {"date": "-108.1.1", "name": "Lelang"},
    {"date": "427.1.1", "name": "Pyongyang"},
    {"date": "918.1.1", "name": "Seogyeong"},
    {"date": "1392.1.1", "name": "Pyongyang"},
    {"date": "1910.10.1", "name": "Heijo"},
    {"date": "1945.8.15", "name": "Pyongyang"},
  ],
  ("kaesong", "North Korea"): [
    {"date": "919.1.1", "name": "Gaegyeong"},
    {"date": "1394.1.1", "name": "Kaesong"},
    {"date": "1910.10.1", "name": "Kaijo"},
    {"date": "1945.8.15", "name": "Kaesong"},
  ],
  ("hamhung", "North Korea"): [
    {"date": "1108.1.1", "name": "Hamhung"},
    {"date": "1910.10.1", "name": "Kanko"},
    {"date": "1945.8.15", "name": "Hamhung"},
  ],
  ("chongjin", "North Korea"): [
    {"date": "1908.1.1", "name": "Seishin"},
    {"date": "1945.8.15", "name": "Chongjin"},
  ],
  ("wonsan", "North Korea"): [
    {"date": "1880.1.1", "name": "Wonsan"},
    {"date": "1910.10.1", "name": "Genzan"},
    {"date": "1945.8.15", "name": "Wonsan"},
  ],
  ("nampo", "North Korea"): [
    {"date": "1897.1.1", "name": "Chinnampo"},
    {"date": "1945.8.15", "name": "Nampo"},
  ],
  ("sinuiju", "North Korea"): [
    {"date": "1910.1.1", "name": "Shingishu"},
    {"date": "1945.8.15", "name": "Sinuiju"},
  ],
  ("haeju", "North Korea"): [
    {"date": "940.1.1", "name": "Haeju"},
    {"date": "1910.10.1", "name": "Kaishu"},
    {"date": "1945.8.15", "name": "Haeju"},
  ],
  ("sariwon", "North Korea"): [
    {"date": "1906.1.1", "name": "Shariin"},
    {"date": "1945.8.15", "name": "Sariwon"},
  ],
  ("uiju", "North Korea"): [
    {"date": "1117.1.1", "name": "Uiju"},
    {"date": "1910.10.1", "name": "Gishu"},
    {"date": "1945.8.15", "name": "Uiju"},
  ],
  ("kimchaek", "North Korea"): [
    {"date": "1899.5.1", "name": "Songjin"},
    {"date": "1951.1.1", "name": "Kimchaek"},
  ],
  ("songrim", "North Korea"): [
    {"date": "1918.1.1", "name": "Kyomipo"},
    {"date": "1947.1.1", "name": "Songrim"},
  ],
  ("anju", "North Korea"): [
    {"date": "931.1.1", "name": "Anju"},
    {"date": "1910.10.1", "name": "Anshu"},
    {"date": "1945.8.15", "name": "Anju"},
  ],
  ("kanggye", "North Korea"): [
    {"date": "1369.1.1", "name": "Kanggye"},
    {"date": "1910.10.1", "name": "Kokai"},
    {"date": "1945.8.15", "name": "Kanggye"},
  ],
}


def strip_parens(s):
  t = str(s or "").strip()
  if t.startswith("(") and t.endswith(")") and t.count("(") == 1:
    t = t[1:-1].strip()
  t = re.sub(r"\s*\([^)]*\)", "", t)
  t = re.sub(r"\s*（[^）]*）", "", t)
  t = t.replace("？", "").replace("＝", "-").replace("・", " ").replace("･", " ")
  t = re.sub(r"[\u2600-\u27BF\uFE00-\uFE0F\U00010000-\U0010FFFF]", "", t)
  t = re.sub(r"\s+", " ", t).strip()
  return t


def norm_key(s):
  rep = {"ō":"o","Ō":"o","ū":"u","Ū":"u","ā":"a","ē":"e","ī":"i","ŏ":"o","ŭ":"u","ô":"o","û":"u","õ":"o","'":"","’":"","-":""," ":""}
  t = strip_parens(s).lower()
  for k, v in rep.items():
    t = t.replace(k, v)
  return re.sub(r"[^a-z0-9]", "", t)


def is_valid_castle_script(s):
  """Allows ONLY Latin, Japanese (Hiragana/Katakana/Kanji), and Korean (Hangul/Hanja) scripts — zero Cyrillic/Arabic/etc."""
  if not s:
    return False
  for ch in s:
    oc = ord(ch)
    if oc < 128:
      continue
    if 0x00C0 <= oc <= 0x024F:  # Latin Extended (macrons, etc.)
      continue
    if 0x1E00 <= oc <= 0x1EFF:  # Latin Extended Additional
      continue
    if 0x3040 <= oc <= 0x30FF:  # Hiragana & Katakana
      continue
    if 0x4E00 <= oc <= 0x9FFF:  # CJK Kanji / Hanja
      continue
    if 0xAC00 <= oc <= 0xD7AF:  # Hangul Syllables
      continue
    if ch in "・ー’‘–—":
      continue
    return False
  return True


def is_clean_name(s):
  t = str(s or "").strip()
  if not t or len(t) < 2:
    return False
  if any(ch in t for ch in ("?", "\ufffd", "`", "\u00ef\u00bf\u00bd")):
    return False
  if t.lower() in ("0", "unknown", "settlement", "japan", "korea", "south korea", "north korea"):
    return False
  return is_valid_castle_script(t)


def load_geonames_alternates():
  grid = defaultdict(list)
  for cc, cname in (("JP", "Japan"), ("KR", "South Korea"), ("KP", "North Korea")):
    zp = os.path.join(CENSUS_DIR, f"geonames_{cc}.zip")
    if not os.path.exists(zp):
      continue
    with zipfile.ZipFile(zp) as zf:
      for ln in zf.read(f"{cc}.txt").decode("utf-8", errors="replace").splitlines():
        cols = ln.split("\t")
        if len(cols) < 15 or cols[6] != "P":
          continue
        try:
          lat, lon = float(cols[4]), float(cols[5])
        except Exception:
          continue
        alts = []
        for a in [cols[1].strip(), cols[2].strip()] + [x.strip() for x in cols[3].split(",") if x.strip()]:
          if is_clean_name(a) and a not in alts:
            alts.append(a)
        if alts:
          gx, gy = int(math.floor(lon * 2.0)), int(math.floor(lat * 2.0))
          grid[(cname, gx, gy)].append((lat, lon, alts[:10]))
  return grid


def lookup_geonames_aliases(grid, cname, lat, lon, canon):
  gx, gy = int(math.floor(lon * 2.0)), int(math.floor(lat * 2.0))
  best_d = 0.08
  best_alts = []
  nk_c = norm_key(canon)
  for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
      for gla, glo, alts in grid.get((cname, gx + dx, gy + dy), []):
        d = math.hypot(lat - gla, lon - glo)
        if d < best_d:
          if any(norm_key(a) == nk_c for a in alts) or d < 0.025:
            best_d = d
            best_alts = alts
  return best_alts


def main():
  print("[CASTLE Toponymy] Loading GeoNames JP/KR/KP alternate names (strict CJK/Hangul/Latin filter)...", flush=True)
  gn_grid = load_geonames_alternates()
  batch_files = sorted(f for f in os.listdir(BATCH_DIR) if re.match(r"^batch_\d+\.json$", f, re.I))
  print(f"[CASTLE Toponymy] Resolving {len(batch_files)} batch file(s) in {BATCH_DIR}...", flush=True)

  total_res = 0
  curated_hits = 0

  for bf in batch_files:
    raw = json.load(open(os.path.join(BATCH_DIR, bf), "r", encoding="utf-8"))
    out_items = []
    for it in raw.get("settlements", []):
      cname = str(it.get("country") or "").strip()
      coords = it.get("coords_lat_lng") or [0.0, 0.0]
      lat, lon = float(coords[0]), float(coords[1])
      raw_name = strip_parens(it.get("name") or "")
      if not is_clean_name(raw_name):
        continue
      nk = norm_key(raw_name)
      earliest = int(it.get("earliest_year") if it.get("earliest_year") is not None else 1850)
      latest = int(it.get("latest_year") if it.get("latest_year") is not None else 2025)

      curated = CURATED_HISTORICAL_NAMES.get((nk, cname))
      if curated:
        hist = [dict(h) for h in curated]
        if latest >= 1950 and norm_key(hist[-1]["name"]) != nk:
          hist.append({"date": f"{max(1950, int(hist[-1]['date'].split('.')[0]) + 1)}.1.1", "name": raw_name})
        curated_hits += 1
      else:
        existing_hist = it.get("existing_historical_names") or []
        hist = []
        for eh in existing_hist:
          if isinstance(eh, dict) and re.match(r"^-?\d+\.\d+\.\d+$", str(eh.get("date") or "").strip()) and is_clean_name(eh.get("name")):
            hist.append({"date": str(eh["date"]).strip(), "name": strip_parens(eh["name"])})
        if not hist:
          init_yr = min(earliest, 1868) if earliest > 1868 and latest >= 1950 else earliest
          hist.append({"date": f"{init_yr}.1.1", "name": raw_name})
        elif latest >= 1950 and norm_key(hist[-1]["name"]) != nk:
          last_yr = int(hist[-1]["date"].split(".")[0])
          hist.append({"date": f"{max(last_yr + 1, 1950)}.1.1", "name": raw_name})

      other_set = []
      seen_o = {raw_name.lower()}
      for a in list(it.get("known_aliases") or []) + lookup_geonames_aliases(gn_grid, cname, lat, lon, raw_name):
        ca = strip_parens(a)
        if is_clean_name(ca) and ca.lower() not in seen_o:
          seen_o.add(ca.lower())
          other_set.append(ca)

      rec = dict(it)
      rec["canonical_name"] = raw_name
      rec["historical_names"] = hist
      rec["other_names"] = other_set[:12]
      out_items.append(rec)
      total_res += 1

    with open(os.path.join(BATCH_DIR, "resolved_" + bf), "w", encoding="utf-8") as fh:
      json.dump({"batch_index": raw.get("batch_index", 1), "project": "CASTLE", "count": len(out_items), "settlements": out_items}, fh, ensure_ascii=False, indent=2)

  print(f"[CASTLE Toponymy] Done: resolved {total_res:,} batch settlements ({curated_hits} curated hits).", flush=True)


def apply_curated_replacements():
  """Authoritatively updates historical_names & clean CJK/Hangul aliases on curated Japanese & Korean cities
  in stadester_2.0/city_metadata.json (fixing single-stub entries & stripping foreign-script spam)."""
  meta_arr = json.load(open(DATAVIEW_META, "r", encoding="utf-8"))
  gn_grid = load_geonames_alternates()
  updated = 0

  for entry in meta_arr:
    if not isinstance(entry, dict) or not isinstance(entry.get("coords"), list) or len(entry["coords"]) < 2:
      continue
    lng, lat = float(entry["coords"][0]), float(entry["coords"][1])
    if not (122.5 <= lng <= 147.0 and 23.5 <= lat <= 46.5):
      continue
    canon = strip_parens(entry.get("name"))
    nk = norm_key(canon)
    dmz_lat = 37.82 + 0.35 * (lng - 126.5)
    is_nk = (lng <= 131.0 and lat >= dmz_lat)
    is_sk = (not is_nk) and ((lat >= 33.1 and lng <= 129.55) or (37.3 <= lat <= 37.7 and 130.7 <= lng <= 131.1))
    ctry = "North Korea" if is_nk else ("South Korea" if is_sk else "Japan")

    # Strip any foreign-script spam (Cyrillic etc.) from existing CASTLE other_names
    if isinstance(entry.get("other_names"), list):
      cleaned_o = [o for o in entry["other_names"] if is_clean_name(o)]
      if len(cleaned_o) != len(entry["other_names"]):
        entry["other_names"] = cleaned_o

    matched_curated = CURATED_HISTORICAL_NAMES.get((nk, ctry))
    if not matched_curated:
      continue

    existing_hist = entry.get("historical_names") or []
    if len(existing_hist) > len(matched_curated):
      continue
    if len(existing_hist) == len(matched_curated) and len(existing_hist) >= 3:
      continue

    new_hist = [dict(h) for h in matched_curated]
    if norm_key(new_hist[-1]["name"]) != nk:
      new_hist[-1]["name"] = canon
    entry["historical_names"] = new_hist

    other = list(entry.get("other_names") or [])
    seen = {canon.lower()} | {str(o).lower() for o in other}
    for h in new_hist:
      if h["name"].lower() not in seen and is_clean_name(h["name"]):
        seen.add(h["name"].lower())
        other.append(h["name"])
    for a in lookup_geonames_aliases(gn_grid, ctry, lat, lng, canon)[:10]:
      if a.lower() not in seen and is_clean_name(a):
        seen.add(a.lower())
        other.append(a)
    if other:
      entry["other_names"] = other[:16]
    updated += 1

  with open(DATAVIEW_META, "w", encoding="utf-8") as fh:
    json.dump(meta_arr, fh, ensure_ascii=False, indent=2)
  print(f"[CASTLE Toponymy] Authoritatively updated {updated} curated Japanese/Korean city entries in {DATAVIEW_META}.", flush=True)


if __name__ == "__main__":
  if "--apply-curated" in sys.argv:
    apply_curated_replacements()
  else:
    main()
