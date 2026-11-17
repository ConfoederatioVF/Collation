#!/usr/bin/env python3
"""
Step 2: Builds the clean, de-homonymised, spatially deduplicated master POLARIS settlement registry
(1815-2026) from all cached Russian Empire, Interwar, Soviet, Post-Soviet, GeoNames, and Wikidata corpora.
"""

import json
import math
import os
import re
import unicodedata
from collections import defaultdict
from shapely.geometry import Point, shape
from shapely.prepared import prep

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
MASHKE_DIR = os.path.join(CACHE_DIR, "mashke")
GN_DIR = os.path.join(CACHE_DIR, "geonames")
WD_DIR = os.path.join(CACHE_DIR, "wikidata")
POLARIS_DIR = os.path.join(BASE_DIR, "histmap", "1.data_raw", "population_regional", "POLARIS")
ENTIRE_DIR = os.path.join(POLARIS_DIR, "1.entire_country")
GIS_DIR = os.path.join(POLARIS_DIR, "_shared", "_gis_cache")
OUT_PATH = os.path.join(CACHE_DIR, "clean_master_registry.json")
BASELINE_A_PATH = os.path.join(CACHE_DIR, "baseline_phase_a.json")

# ---------------------------------------------------------------------------
# Normalisation & Transliteration
# ---------------------------------------------------------------------------

ORTHO_MAP = str.maketrans({
  "ѣ": "е", "і": "и", "ѳ": "ф", "ѵ": "и",
  "Ѣ": "Е", "І": "И", "Ѳ": "Ф", "Ѵ": "И",
  "ў": "у", "Ў": "У",
})

CYR_LAT = {
  "а": "a", "б": "b", "в": "v", "г": "g", "ґ": "g", "д": "d", "е": "e",
  "ё": "e", "є": "ye", "ж": "zh", "з": "z", "и": "i", "і": "i", "ї": "yi",
  "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
  "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
  "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e",
  "ю": "yu", "я": "ya",
}

SPECIAL_LAT = str.maketrans({
  "ł": "l", "Ł": "l", "ø": "o", "Ø": "o", "đ": "d", "Đ": "d",
  "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe", "ß": "ss",
  "`": "", "’": "", "'": "", "ʼ": "", "ʹ": "", "ʺ": "",
})

PREFIX_PAT = re.compile(
  r"^(?:"
  r"г\.|г\s+|город\s+|м\.|місто\s+|"
  r"пгт\.?|смт\.?|рп\.?|кп\.?|дп\.?|гп\.?|г\.п\.|р\.п\.|к\.п\.|"
  r"с\.|село\s+|д\.|дер\.|деревня\s+|"
  r"п\.|пос\.|посёлок\s+|поселок\s+|пос[.\s]+г\.?\s*т\.?\s+|"
  r"слб\.?|сл\.|слобода\s+|"
  r"ст-ца|ст\.|станица\s+|х\.|хутор\s+|"
  r"аул\s+|с-ще|сщ\.|псд\.?|посад\s+|"
  r"мст\.?|м-ко|местечко\s+|звд\.?|завод\s+|"
  r"клн\.?|колония\s+|выс\.?|уч\.?|ж\.?\s*д\.?\s*ст\.?\s+"
  r")",
  re.I,
)

STATUS_CITY_PAT = re.compile(r"^(?:г\.|г\s+|город\s+|м\.|місто\s+|гор\.)", re.I)
STATUS_PGT_PAT = re.compile(r"^(?:пгт|смт|рп|кп|дп|гп|г\.п\.|р\.п\.|к\.п\.|псд|посад|мст|м-ко|пос\.\s*г|рабочий\s+пос)", re.I)
STATUS_RURAL_PAT = re.compile(r"^(?:с\.|село|д\.|дер\.|деревн|п\.|пос\.|пос[её]лок|слб|сл\.|слобод|ст-ца|ст\.|станиц|х\.|хутор|аул|с-ще|клн)", re.I)

TAG_RE = re.compile(r"<[^>]+>")
TRAIL_PARENS_RE = re.compile(r"\s*\((?:[^)]*)\)\s*")


def strip_tags(s):
  return TAG_RE.sub("", s).replace("&nbsp;", " ").replace("&amp;", "&").strip()


def detect_status(raw_name):
  s = raw_name.strip().lower()
  if STATUS_CITY_PAT.match(s):
    return "city"
  if STATUS_PGT_PAT.match(s):
    return "pgt"
  if STATUS_RURAL_PAT.match(s):
    return "rural"
  return "unknown"


def clean_settlement_label(raw_name, strip_parens=True):
  s = strip_tags(raw_name).translate(ORTHO_MAP)
  s = re.sub(r"\s+", " ", s).strip()
  # Strip repeated prefixes
  for _ in range(2):
    m = PREFIX_PAT.match(s)
    if m:
      s = s[m.end():].strip()
  if strip_parens:
    s = TRAIL_PARENS_RE.sub(" ", s).strip()
  # Remove trailing comma + type in 1897 census tables e.g. "Архангельск, губ.г"
  s = re.sub(r",\s*(?:губ\.?\s*г\.?|у\.?\s*г\.?|з\.?\s*г\.?|б\.?\s*г\.?|г\.?|псд\.?|с\.|д\.|м\.|м-ко|мст\.?|слб\.?|сл\.|слц\.?|ст-ца|ст\.|х\.|хт\.?|пос\.?|п\.|дер\.|уч\.?|клн\.?|звд\.?|мон\.?|пгт\.?|ст\.).*$", "", s, flags=re.I)
  return re.sub(r"\s+", " ", s).strip(" .,;-")


def norm_cyr(s):
  s = clean_settlement_label(s).lower().replace("ё", "е")
  s = re.sub(r"([бвгджзклмнпрстфхцчшщ])ъ\b", r"\1", s)
  s = s.replace("'", "").replace("’", "").replace("`", "").replace("-", " ")
  return re.sub(r"\s+", " ", s).strip()


def cyr_to_lat(s):
  s = clean_settlement_label(s).translate(ORTHO_MAP).lower()
  out = []
  for ch in s:
    if ch in CYR_LAT:
      out.append(CYR_LAT[ch])
    else:
      out.append(ch)
  return "".join(out)


def norm_lat(s):
  if re.search(r"[а-яА-ЯёЁіїєґІЇЄҐѣѢ]", s):
    s = cyr_to_lat(s)
  else:
    s = clean_settlement_label(s).lower()
  s = s.translate(SPECIAL_LAT)
  s = unicodedata.normalize("NFD", s)
  s = "".join(c for c in s if unicodedata.category(c) != "Mn")
  s = s.replace("-", " ").replace("_", " ")
  s = re.sub(r"[^a-z0-9\s]", "", s)
  # Equate common East Slavic ending variations (ij/yy/y/i, ja/ya, sk/skij)
  return re.sub(r"\s+", " ", s).strip()


def fuzzy_stem(s):
  n = norm_lat(s)
  n = re.sub(r"\byi\b|\bi\b", "y", n)
  n = n.replace("y", "i").replace("kh", "h").replace("zh", "j").replace("ch", "c").replace("sh", "s").replace("ts", "c")
  n = re.sub(r"(.)\1+", r"\1", n)
  return n.replace(" ", "")


def parse_thousands_num(raw):
  s = strip_tags(raw).replace("\xa0", "").replace(" ", "").strip()
  if not s or s in ("…", "...", "-", "—", "–", "?", "N/A"):
    return None
  s = s.rstrip("*")
  try:
    if "," in s and "." not in s:
      val = float(s.replace(",", ".")) * 1000.0
    elif "." in s and "," not in s:
      val = float(s) * 1000.0
    else:
      val = float(s.replace(",", ""))
    return int(round(val)) if val > 0 else None
  except ValueError:
    return None


def parse_int_num(raw):
  s = strip_tags(raw).replace("\xa0", "").replace(" ", "").replace(",", "").replace(".", "").strip()
  s = re.sub(r"[^\d]", "", s)
  if not s:
    return None
  val = int(s)
  return val if val > 0 else None


def haversine_km(c1, c2):
  la1, lo1 = math.radians(c1[0]), math.radians(c1[1])
  la2, lo2 = math.radians(c2[0]), math.radians(c2[1])
  dl = la2 - la1
  dn = lo2 - lo1
  a = math.sin(dl / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dn / 2) ** 2
  return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))


def status_compatible(s1, s2):
  if s1 == "unknown" or s2 == "unknown" or s1 == s2:
    return True
  # city vs pgt can occasionally promote/demote over decades; city vs rural requires tight ratio
  if {s1, s2} == {"city", "pgt"}:
    return True
  if {s1, s2} == {"pgt", "rural"}:
    return True
  return False


# Bidirectional Ukrainian Decommunisation & Russian/Belarusian rename pairs
ALIAS_GROUPS = [
  ["Dnipro", "Dnipropetrovsk", "Dnepropetrovsk", "Yekaterinoslav", "Ekaterinoslav", "Екатеринослав", "Днепропетровск", "Дніпропетровськ", "Дніпро"],
  ["Kamianske", "Kamyanske", "Dniprodzerzhynsk", "Dneprodzerzhinsk", "Kamenskoye", "Каменское", "Кам'янське", "Дніпродзержинськ", "Днепродзержинск"],
  ["Kropyvnytskyi", "Kirovohrad", "Kirovograd", "Yelizavetgrad", "Elizavetgrad", "Zinovievsk", "Елизаветград", "Кіровоград", "Кировоград", "Кропивницький"],
  ["Bakhmut", "Artemivsk", "Artemovsk", "Бахмут", "Артемівськ", "Артемовск"],
  ["Kypuche", "Artemivsk_Luhansk", "Кипуче", "Артемівськ"],
  ["Khrustalnyi", "Krasnyi Luch", "Krasny Luch", "Krindachevka", "Хрустальний", "Красний Луч", "Красный Луч"],
  ["Kadiivka", "Stakhanov", "Sergo", "Кадіївка", "Стаханов", "Кадиевка", "Серго"],
  ["Dovzhansk", "Sverdlovsk", "Довжанськ", "Свердловськ", "Свердловск"],
  ["Chystiakove", "Chystyakove", "Torez", "Чистякове", "Торез", "Чистяково"],
  ["Myrnohrad", "Dymytrov", "Dimitrov", "Мирноград", "Димитров"],
  ["Pokrovsk", "Krasnoarmiisk", "Krasnoarmeysk", "Grishino", "Покровськ", "Красноармійськ", "Красноармейск", "Гришино"],
  ["Toretsk", "Dzerzhynsk", "Dzerzhinsk", "Shcherbinovka", "Торецьк", "Дзержинськ", "Дзержинск", "Щербиновка"],
  ["Holubivka", "Kirovsk", "Голубівка", "Кіровськ", "Кировск"],
  ["Lyman", "Krasnyi Lyman", "Krasny Lyman", "Лиман", "Красний Лиман", "Красный Лиман"],
  ["Kalmiuske", "Komsomolske", "Кальміуське", "Комсомольське"],
  ["Bunhe", "Yunokomunarivsk", "Бунге", "Юнокомунарівськ"],
  ["Zalizne", "Artemove", "Залізне", "Артемове"],
  ["Sorokyne", "Krasnodon", "Сорокине", "Краснодон"],
  ["Petrovo-Krasnosillia", "Petrovske", "Петрово-Красносілля", "Петровське"],
  ["Bokovo-Khrustalne", "Vakhrusheve", "Боково-Хрустальне", "Вахрушеве"],
  ["Voznesenivka", "Chervonopartyzansk", "Вознесенівка", "Червонопартизанськ"],
  ["Pokrov", "Ordzhonikidze", "Покров", "Орджонікідзе"],
  ["Chornomorsk", "Illichivsk", "Ilyichevsk", "Чорноморськ", "Іллічівськ", "Ильичевск"],
  ["Podilsk", "Kotovsk", "Birzula", "Подільськ", "Котовськ", "Бирзула", "Бірзула"],
  ["Horishni Plavni", "Komsomolsk", "Горішні Плавні", "Комсомольськ"],
  ["Varash", "Kuznetsovsk", "Вараш", "Кузнецовськ"],
  ["Oleshky", "Tsyurupynsk", "Tsjurupynsk", "Aleshki", "Олешки", "Цюрупинськ", "Алешки"],
  ["Zavodske", "Chervonozavodske", "Заводське", "Червонозаводське"],
  ["Snovsk", "Shchors", "Сновськ", "Щорс"],
  ["Pereiaslav", "Pereyaslav-Khmelnytskyi", "Переяслав", "Переяслав-Хмельницький"],
  ["Volodymyr", "Volodymyr-Volynskyi", "Владимир-Волынский", "Володимир", "Володимир-Волинський"],
  ["Zviahel", "Novohrad-Volynskyi", "Novograd-Volynsky", "Звягель", "Новоград-Волинський", "Новоград-Волынский"],
  ["Pivdennoukrainsk", "Yuzhnoukrainsk", "Південноукраїнськ", "Южноукраїнськ"],
  ["Pivdenne", "Yuzhne", "Південне", "Южне"],
  ["Sheptytskyi", "Chervonohrad", "Kristinopol", "Шептицький", "Червоноград", "Кристинополь"],
  ["Samar", "Novomoskovsk", "Самар", "Новомосковськ", "Новомосковск"],
  ["Shakhtarske", "Pershotravensk", "Шахтарське", "Першотравенськ"],
  ["Bahacheve", "Vatutine", "Багачеве", "Ватутіне"],
  ["Blahovishchenske", "Ulianovka", "Благовіщенське", "Ульяновка"],
  ["Berestyn", "Krasnohrad", "Konstantinograd", "Берестин", "Красноград", "Константиноград"],
  ["Zlatopil", "Pervomaiskyi", "Likhachevo", "Златопіль", "Первомайський"],
  ["Zmiiv", "Hotvald", "Зміїв", "Готвальд"],
  ["Slobozhanske", "Komsomolske", "Слобожанське", "Комсомольське"],
  ["Radyvyliv", "Chervonoarmiysk", "Radzivilov", "Радивилів", "Червоноармійськ", "Радзивилов"],
  ["Kyiv", "Kyjiv", "Kiev", "Київ", "Киев"],
  ["Kharkiv", "Charkiv", "Kharkov", "Харків", "Харьков"],
  ["Odesa", "Odessa", "Одеса", "Одесса"],
  ["Zaporizhzhia", "Zapori`z`ja", "Zaporozhye", "Aleksandrovsk", "Запоріжжя", "Запорожье", "Александровск"],
  ["Mykolaiv", "Mykolajiv", "Nikolaev", "Миколаїв", "Николаев"],
  ["Mariupol", "Zhdanov", "Маріуполь", "Мариуполь", "Жданов"],
  ["Luhansk", "Lugansk", "Voroshilovgrad", "Луганськ", "Луганск", "Ворошиловград"],
  ["Donetsk", "Donec'k", "Stalino", "Yuzovka", "Донецьк", "Донецк", "Сталино", "Юзовка"],
  ["Alchevsk", "Kommunarsk", "Voroshilovsk", "Алчевськ", "Коммунарск", "Ворошиловск"],
  ["Yenakiieve", "Yenakiyeve", "Jenakijeve", "Rykovo", "Енакиево", "Єнакієве", "Рыково"],
  ["Sloviansk", "Slavyansk", "Slov`janśk", "Слов'янськ", "Славянск"],
  ["Sievierodonetsk", "Severodonetsk", "Siverskodonetsk", "Сєвєродонецьк", "Северодонецк", "Сіверськодонецьк"],
  ["Berdiansk", "Berdjansk", "Osipenko", "Бердянськ", "Бердянск", "Осипенко"],
  ["Poltava", "Полтава"],
  ["Chernihiv", "Chernigov", "Чернігів", "Чернигов"],
  ["Sumy", "Суми", "Сумы"],
  ["Uzhhorod", "Uzhgorod", "Ungvar", "Ужгород"],
  ["Lviv", "Lvov", "Lwow", "Lemberg", "Львів", "Львов"],
  ["Ternopil", "Tarnopol", "Тернопіль", "Тарнополь"],
  ["Ivano-Frankivsk", "Stanislav", "Stanyslaviv", "Івано-Франківськ", "Станіслав", "Станислав"],
  ["Khmelnytskyi", "Proskurov", "Proskuriv", "Хмельницький", "Проскуров"],
  ["Bilhorod-Dnistrovskyi", "Akkerman", "Cetatea Alba", "Білгород-Дністровський", "Аккерман"],
  ["Chornomorske", "Ak-Mechet", "Чорноморське"],
  ["Feodosia", "Kefe", "Феодосія", "Феодосия"],
  ["Yalta", "Ялта"],
  ["Simferopol", "Akmescit", "Сімферополь", "Симферополь"],
  ["Saint Petersburg", "St Petersburg", "Leningrad", "Petrograd", "Sankt-Peterburg", "Санкт-Петербург", "Ленинград", "Петроград"],
  ["Nizhny Novgorod", "Nizhniy Novgorod", "Gorky", "Gorkiy", "Нижний Новгород", "Горький"],
  ["Samara", "Kuybyshev", "Kuibyshev", "Самара", "Куйбышев"],
  ["Yekaterinburg", "Ekaterinburg", "Sverdlovsk", "Екатеринбург", "Свердловск"],
  ["Volgograd", "Stalingrad", "Tsaritsyn", "Волгоград", "Сталинград", "Царицын"],
  ["Perm", "Molotov", "Пермь", "Молотов"],
  ["Tolyatti", "Togliatti", "Stavropol-on-Volga", "Тольятти", "Ставрополь"],
  ["Ulyanovsk", "Simbirsk", "Ульяновск", "Симбирск"],
  ["Izhevsk", "Ustinov", "Ижевск", "Устинов"],
  ["Kirov", "Vyatka", "Khlynov", "Киров", "Вятка"],
  ["Tver", "Kalinin", "Тверь", "Калинин"],
  ["Rybinsk", "Andropov", "Shcherbakov", "Рыбинск", "Андропов", "Щербаков"],
  ["Naberezhnye Chelny", "Brezhnev", "Набережные Челны", "Брежнев"],
  ["Orenburg", "Chkalov", "Оренбург", "Чкалов"],
  ["Vladikavkaz", "Ordzhonikidze", "Dzaudzhikau", "Владикавказ", "Орджоникидзе", "Дзауджикау"],
  ["Makhachkala", "Petrovsk-Port", "Petrovsk", "Махачкала", "Петровск-Порт", "Петровск"],
  ["Grozny", "Groznyy", "Грозный"],
  ["Kaliningrad", "Konigsberg", "Koenigsberg", "Калининград", "Кёнигсберг"],
  ["Vyborg", "Viipuri", "Viborg", "Выборг"],
  ["Sortavala", "Serdobol", "Сортавала", "Сердоболь"],
  ["Priozersk", "Kakisalmi", "Kexholm", "Приозерск", "Кексгольм"],
  ["Sovetsk", "Tilsit", "Советск", "Тильзит"],
  ["Chernyakhovsk", "Insterburg", "Черняховск", "Инстербург"],
  ["Gusev", "Gumbinnen", "Гусев", "Гумбиннен"],
  ["Baltiysk", "Pillau", "Балтийск", "Пиллау"],
  ["Krasnodar", "Yekaterinodar", "Ekaterinodar", "Краснодар", "Екатеринодар"],
  ["Novorossiysk", "Новороссийск"],
  ["Novocherkassk", "Новочеркасск"],
  ["Taganrog", "Таганрог"],
  ["Stavropol", "Voroshilovsk", "Ставрополь"],
  ["Budennovsk", "Svyatoi Krest", "Prikumsk", "Буденновск", "Святой Крест", "Прикумск"],
  ["Buynaksk", "Temir-Khan-Shura", "Буйнакск", "Темир-Хан-Шура"],
  ["Engels", "Pokrovsk", "Pokrovskaya Sloboda", "Энгельс", "Покровск"],
  ["Marks", "Yekaterinenshtadt", "Baronsk", "Marxstadt", "Маркс", "Екатериненштадт"],
  ["Pugachev", "Nikolayevsk", "Пугачев", "Николаевск"],
  ["Ulan-Ude", "Verkhneudinsk", "Улан-Удэ", "Верхнеудинск"],
  ["Ussuriysk", "Nikolsk-Ussuriysky", "Voroshilov", "Уссурийск", "Никольск-Уссурийский"],
  ["Partizansk", "Suchan", "Партизанск", "Сучан"],
  ["Dalnegorsk", "Tetyukhe", "Дальнегорск", "Тетюхе"],
  ["Yuzhno-Sakhalinsk", "Toyohara", "Vladimirovka", "Южно-Сахалинск"],
  ["Kholmsk", "Maoka", "Холмск"],
  ["Korsakov", "Otomari", "Korsakovsk", "Корсаков"],
  ["Aleksandrovsk-Sakhalinsky", "Aleksandrovsky Post", "Александровск-Сахалинский"],
  ["Kyzyl", "Belotsarsk", "Khem-Beldir", "Кызыл"],
  ["Novosibirsk", "Novonikolayevsk", "Новосибирск", "Новониколаевск"],
  ["Novokuznetsk", "Stalinsk", "Kuznetsk", "Новокузнецк", "Сталинск", "Кузнецк"],
  ["Kemerovo", "Shcheglovsk", "Кемерово", "Щегловск"],
  ["Mariinsk", "Мариинск"],
  ["Achinsk", "Ачинск"],
  ["Svobodny", "Alekseyevsk", "Свободный", "Алексеевск"],
  ["Belogorsk", "Aleksandrovskoye", "Kuybyshevka-Vostochnaya", "Белогорск"],
  ["Gatchina", "Krasnogvardeysk", "Trotsk", "Гатчина", "Троцк"],
  ["Pushkin", "Tsarskoye Selo", "Detskoye Selo", "Пушкин", "Царское Село"],
  ["Pavlovsk", "Slutsk", "Павловск", "Слуцк"],
  ["Kingisepp", "Yamburg", "Кингисепп", "Ямбург"],
  ["Lomonosov", "Oranienbaum", "Ломоносов", "Ораниенбаум"],
  ["Zelenogorsk", "Terijoki", "Зеленогорск", "Терийоки"],
  ["Kronstadt", "Кронштадт"],
  ["Petrodvorets", "Peterhof", "Петергоф"],
  ["Sergiyev Posad", "Zagorsk", "Сергиев Посад", "Загорск", "Сергиев"],
  ["Noginsk", "Bogorodsk", "Ногинск", "Богородск"],
  ["Orekhovo-Zuyevo", "Orekhovo", "Zuyevo", "Орехово-Зуево", "Никольское"],
  ["Shchyolkovo", "Shchelkovo", "Щёлково", "Щелково"],
  ["Korolyov", "Kaliningrad", "Podlipki", "Королёв", "Подлипки"],
  ["Dzerzhinsk", "Rastyapino", "Chernorechye", "Дзержинск", "Растяпино"],
  ["Novomoskovsk", "Stalinogorsk", "Bobriki", "Новомосковск", "Сталиногорск"],
  ["Shchyokino", "Shchekino", "Щёкино", "Щекино"],
  ["Azov", "Азов"],
  ["Gukovo", "Гуково"],
  ["Shakhty", "Aleksandrovsk-Grushevsky", "Шахты", "Александровск-Грушевский"],
  ["Krasny Sulin", "Sulin", "Красный Сулин", "Сулин"],
  ["Severomorsk", "Vayenga", "Североморск", "Ваенга"],
  ["Polyarny", "Aleksandrovsk", "Полярный"],
  ["Chapaevsk", "Trotsk", "Ivashchenkovo", "Чапаевск", "Иващенково"],
  ["Syzran", "Сызрань"],
  ["Penza", "Пенза"],
  ["Kuznetsk", "Кузнецк"],
  ["Michurinsk", "Kozlov", "Мичуринск", "Козлов"],
  ["Kotovsk", "Котовск"],
  ["Zheleznodorozhny", "Olgino", "Железнодорожный"],
  ["Chekhov", "Lopasnya", "Чехов", "Лопасня"],
  ["Istra", "Voskresensk", "Истра", "Воскресенск"],
  ["Klin", "Клин"],
  ["Solnechnogorsk", "Solnechnaya Gora", "Солнечногорск"],
  ["Dmitrov", "Дмитров"],
  ["Krasnogorsk", "Banki", "Pavshino", "Красногорск", "Павшино"],
  ["Lyubertsy", "Люберцы"],
  ["Mytishchi", "Мытищи"],
  ["Khimki", "Химки"],
  ["Odintsovo", "Одинцово"],
  ["Podolsk", "Подольск"],
  ["Serpukhov", "Серпухов"],
  ["Kolomna", "Коломна"],
  ["Yegoryevsk", "Егорьевск"],
  ["Pavlovsky Posad", "Pavlovo", "Павловский Посад"],
  ["Dzerzhinsk [BY]", "Kojdanava", "Koydanovo", "Dzyarzhynsk", "Дзяржынск", "Койданава", "Койданово"],
  ["Kalininkavichy", "Kalinkavichy", "Kalinkovichi", "Калінкавічы", "Калинковичи"],
  ["Zhlobin", "Жлобін", "Жлобин"],
  ["Svetlogorsk", "Svietlahorsk", "Shatilki", "Shatsilki", "Светлагорск", "Шацілкі"],
  ["Novopolotsk", "Navapołack", "Polotski", "Наваполацк"],
  ["Verkhnedvinsk", "Vierchniadzvinsk", "Drysa", "Drissa", "Верхнядзвінск", "Дрисса"],
  ["Chervyen", "Červień", "Ihumen", "Igumen", "Чэрвень", "Ігумен"],
  ["Kirovo", "Chausy", "Чаусы"],
  ["Krychaw", "Krichev", "Крычаў", "Кричев"],
  ["Dziarzhynsk", "Dzyarzhynsk", "Koidanova", "Koydanovo"],
  ["Krichev", "Krychaw"],
  ["Vilnius", "Wilno", "Vilna", "Вильна", "Вильнюс"],
  ["Kaunas", "Kovno", "Каунас", "Ковно"],
  ["Siauliai", "Shavli", "Шавли", "Шяуляй"],
  ["Panevezys", "Ponevezh", "Поневеж", "Паневежис"],
  ["Anyksciai", "Anykshchiai", "Onikshty", "Onikschty", "Оникшты", "Аникщяй"],
  ["Kedainiai", "Keydany", "Кейданы", "Кедайняй"],
  ["Ziezmariai", "Zhiezhmariai", "Zhizhmore", "Жижморы"],
  ["Gargzdai", "Gargzhdai", "Gorzhdy", "Горжды"],
  ["Rokiskis", "Rokishkis", "Rakishki", "Ракишки"],
  ["Joniskis", "Jonishkis", "Yanishki", "Янишки"],
  ["Vieksniai", "Viekshniai", "Vekshnya", "Векшня"],
  ["Tartu", "Yuryev", "Dorpat", "Derpt", "Тарту", "Юрьев", "Дерпт"],
  ["Tallinn", "Reval", "Revel", "Таллин", "Ревель"],
  ["Daugavpils", "Dvinsk", "Dunaburg", "Даугавпилс", "Двинск"],
  ["Kraslava", "Kreslavka", "Креславка", "Краслава"],
  ["Liepaja", "Libava", "Лиепая", "Либава"],
  ["Ventspils", "Vindava", "Виндава", "Вентспилс"],
  ["Jelgava", "Mitava", "Mitau", "Елгава", "Митава"],
  ["Rezekne", "Rezhitsa", "Резекне", "Режица"],
  ["Chisinau", "Kishinev", "Кишинёв", "Кишинев"],
  ["Balti", "Beltsy", "Бэлць", "Бельцы"],
  ["Cahul", "Kagul", "Кагул"],
  ["Orhei", "Orgeyev", "Оргеев", "Орхей"],
  ["Ceadir-Lunga", "Chadyr-Lunga", "Чадыр-Лунга"],
  ["Cimislia", "Chimishliya", "Чимишлия"],
  ["Edinet", "Edintsy", "Единцы"],
  ["Falesti", "Faleshty", "Фалешты"],
  ["Straseni", "Strasheny", "Страшены"],
  ["Tvardita", "Tvarditsa", "Твардица"],
  ["Vadul lui Voda", "Vaduluy-Vody", "Вадул-луй-Водэ"],
  ["Vulcanesti", "Volkaneshty", "Вулканешты"],
  ["Bender", "Bendery", "Tighina", "Бендеры", "Тигина"],
  ["Bilhorod-Dnistrovskyi", "Cetatea Alba", "Akkerman"],
  ["Helsinki", "Helsingfors", "Гельсингфорс"],
  ["Turku", "Abo", "Або"],
  ["Tampere", "Tammerfors", "Таммерфорс"],
  ["Vaasa", "Nikolaistad", "Nikolaystadt", "Vasa", "Николайстад"],
  ["Oulu", "Uleaborg", "Улеаборг"],
  ["Jyvaskyla", "Yuvyaskyulya", "Ювяскюля"],
  ["Nikolayevsk-on-Amur", "Nikolaevsk-on-Amur", "Nikolajevsk na Amure", "Николаевск-на-Амуре"],
  ["Pulawy", "Novo-Aleksandriya", "Ново-Александрия", "Пулавы"],
  ["Leczyca", "Lenchitsa", "Ленчица"],
  ["Gora Kalwaria", "Gora-Kalvariya", "Гора-Кальвария"],
  ["Belchatow", "Belkhatov", "Белхатов"],
  ["Klobuck", "Klobutsk", "Клобуцк"],
  ["Wloszczowa", "Vloshchova", "Влощова"],
  ["Leczna", "Lenchna", "Ленчна"],
  ["Wasilkow", "Vasilkov", "Васильков"],
  ["Bransk", "Bryansk", "Брянск"],
  ["Blonie", "Blone", "Блоне"],
  ["Zychlin", "Zhikhlin", "Жихлин"],
  ["Zuromin", "Zhuromin", "Журомин"],
  ["Klodawa", "Klodava", "Клодава"],
  ["Ilza", "Ilzha", "Илжа"],
  ["Zwolen", "Zvolen", "Зволень"],
  ["Dzialoszyce", "Dzyaloshitse", "Дзялошице"],
  ["Ogorodnya-Gomelskaya", "Agarodnya Gomelskaya", "Огородня-Гомельская", "Агародня-Гомельская"],
  ["Aksenovo-Zilovskoye", "Aksenovo-Zilovskoje", "Zilovo-Aksenovo", "Аксёново-Зиловское"],
  ["Antopol", "Antopal", "Антополь"],
]

ALIAS_LOOKUP = defaultdict(set)
for grp in ALIAS_GROUPS:
  norms = {norm_lat(g) for g in grp if norm_lat(g)} | {norm_cyr(g) for g in grp if re.search(r"[а-яА-ЯёЁіїєґ]", g)}
  for x in norms:
    ALIAS_LOOKUP[x].update(norms)


CHURCH_DEDICATION_RE = re.compile(
  r"^(?:архангельск|никольск|николаевск|покровск|троицк|рождественск|успенск|"
  r"вознесенск|преображенск|спасск|богородск|ильинск|введенск|знаменск|"
  r"благовещенск|богоявленск|воскресенск|сретенск|сергиевск|михайловск|"
  r"дмитриевск|георгиевск|петропавловск|казанск|крестовоздвиженск|"
  r"алексеевск|андреевск|афанасьевск|васильевск|владимирск|егорьевск|"
  r"ивановск|козьмодемьянск|константиновск|кузьминск|макарьевск|"
  r"павловск|петровск|семеновск|степановск|федоровск|фоминск|флоровск)[а-яё]*$",
  re.I,
)


def expand_name_forms(raw_name, extra_aliases=None):
  forms = set()
  parts = [raw_name]
  # Split Parentheticals & slashes if meaningful aliases (ignoring parish church dedications)
  for m in re.findall(r"\(([^)]+)\)", str(raw_name)):
    # e.g. "(до 2016 - Дніпродзержинськ)" or "(Юзовка)"
    cleaned_m = re.sub(r"^(?:до\s+\d{4}\s*[-–—]?\s*|бывш\.?\s+|until\s+\d{4}\s*)", "", m, flags=re.I).strip()
    if cleaned_m and not re.search(r"(?:рц|город|поселок|област|округ|район|смт)", cleaned_m, re.I):
      if not CHURCH_DEDICATION_RE.match(cleaned_m.replace("ё", "е")):
        parts.append(cleaned_m)
  for a in (extra_aliases or []):
    parts.append(a)
  for p in parts:
    nl = norm_lat(p)
    nc = norm_cyr(p)
    if nl:
      forms.add(nl)
      forms.update(ALIAS_LOOKUP.get(nl, ()))
    if nc:
      forms.add(nc)
      forms.update(ALIAS_LOOKUP.get(nc, ()))
  return forms


# ---------------------------------------------------------------------------
# Curated Founding Years & Pre-1975 Mergers / Abandonments
# ---------------------------------------------------------------------------

CURATED_FOUNDING = {
  # Russia post-1897 planned / industrial towns
  ("magnitogorsk", "Russia"): 1929,
  ("komsomolsk na amure", "Russia"): 1932,
  ("komsomolsk on amur", "Russia"): 1932,
  ("komsomolsk-on-amur", "Russia"): 1932,
  ("prokopyevsk", "Russia"): 1918,
  ("vorkuta", "Russia"): 1936,
  ("norilsk", "Russia"): 1935,
  ("inta", "Russia"): 1940,
  ("angarsk", "Russia"): 1948,
  ("mirny", "Russia"): 1955,
  ("mirnyy", "Russia"): 1955,
  ("nizhnekamsk", "Russia"): 1961,
  ("zelenograd", "Russia"): 1958,
  ("dubna", "Russia"): 1956,
  ("obninsk", "Russia"): 1946,
  ("pushchino", "Russia"): 1956,
  ("protvino", "Russia"): 1960,
  ("kurchatov", "Russia"): 1968,
  ("sosnovy bor", "Russia"): 1958,
  ("sosnovyy bor", "Russia"): 1958,
  ("kostomuksha", "Russia"): 1977,
  ("novovoronezh", "Russia"): 1957,
  ("volgodonsk", "Russia"): 1950,
  ("volzhsky", "Russia"): 1951,
  ("volzhskiy", "Russia"): 1951,
  ("novokuybyshevsk", "Russia"): 1946,
  ("nefteyugansk", "Russia"): 1961,
  ("nizhnevartovsk", "Russia"): 1909,
  ("novy urengoy", "Russia"): 1975,
  ("novyy urengoy", "Russia"): 1975,
  ("noyabrsk", "Russia"): 1976,
  ("muravlenko", "Russia"): 1982,
  ("gubkinsky", "Russia"): 1986,
  ("gubkinskiy", "Russia"): 1986,
  ("langepas", "Russia"): 1980,
  ("pokachi", "Russia"): 1984,
  ("kogalym", "Russia"): 1976,
  ("urai", "Russia"): 1922,
  ("uray", "Russia"): 1922,
  ("nyagan", "Russia"): 1965,
  ("raduzhny", "Russia"): 1973,
  ("pyt yakh", "Russia"): 1968,
  ("usinsk", "Russia"): 1966,
  ("vuktyl", "Russia"): 1968,
  ("pevek", "Russia"): 1933,
  ("bilibino", "Russia"): 1955,
  ("amursk", "Russia"): 1958,
  ("magas", "Russia"): 1995,
  ("innopolis", "Russia"): 2012,
  ("sayansk", "Russia"): 1970,
  ("ust ilimsk", "Russia"): 1966,
  ("zheleznogorsk", "Russia"): 1950,
  ("seversk", "Russia"): 1949,
  ("ozersk", "Russia"): 1945,
  ("snezhinsk", "Russia"): 1957,
  ("tryokhgorny", "Russia"): 1952,
  ("elektrostal", "Russia"): 1916,
  ("zhukovsky", "Russia"): 1935,
  ("zhukovskiy", "Russia"): 1935,
  ("apatity", "Russia"): 1926,
  ("kirovsk", "Russia"): 1929,
  ("monchegorsk", "Russia"): 1935,
  ("olenegorsk", "Russia"): 1949,
  ("zapolyarny", "Russia"): 1956,
  ("nikel", "Russia"): 1935,
  ("polyarnye zori", "Russia"): 1968,
  ("desnogorsk", "Russia"): 1974,
  ("igarka", "Russia"): 1929,
  ("dzerzhinsky", "Russia"): 1921,
  ("birobidzhan", "Russia"): 1912,
  ("tynda", "Russia"): 1917,
  ("nerungri", "Russia"): 1975,
  ("neryungri", "Russia"): 1975,
  ("krasnoturyinsk", "Russia"): 1944,
  ("kachkanar", "Russia"): 1957,
  ("novouralsk", "Russia"): 1941,
  ("lesnoy", "Russia"): 1947,
  ("kodinsk", "Russia"): 1977,
  ("kovdor", "Russia"): 1953,
  ("nadym", "Russia"): 1968,
  ("sosnogorsk", "Russia"): 1939,
  ("pechora", "Russia"): 1940,
  ("ukhta", "Russia"): 1929,
  ("zheleznogorsk ilimsky", "Russia"): 1948,
  ("raduzhnyy", "Russia"): 1973,
  ("pokachi", "Russia"): 1984,
  ("mezhgorye", "Russia"): 1979,
  # Ukraine post-1897 planned towns
  ("sievierodonetsk", "Ukraine"): 1934,
  ("severodonetsk", "Ukraine"): 1934,
  ("siverskodonetsk", "Ukraine"): 1934,
  ("nova kakhovka", "Ukraine"): 1952,
  ("enerhodar", "Ukraine"): 1970,
  ("dniprorudne", "Ukraine"): 1961,
  ("yuzhnoukrainsk", "Ukraine"): 1975,
  ("pivdennoukrainsk", "Ukraine"): 1975,
  ("varash", "Ukraine"): 1973,
  ("yuzhne", "Ukraine"): 1978,
  ("pivdenne", "Ukraine"): 1978,
  ("teplodar", "Ukraine"): 1981,
  ("slavutych", "Ukraine"): 1986,
  ("novyi rozdil", "Ukraine"): 1953,
  ("novovolynsk", "Ukraine"): 1950,
  ("horishni plavni", "Ukraine"): 1960,
  ("svitlovodsk", "Ukraine"): 1954,
  ("vilnohirsk", "Ukraine"): 1956,
  ("shakhtarske", "Ukraine"): 1954,
  ("vuhledar", "Ukraine"): 1964,
  ("svitlodarsk", "Ukraine"): 1968,
  ("molodohvardiisk", "Ukraine"): 1954,
  ("sukhodilsk", "Ukraine"): 1914,
  ("novodnistrovsk", "Ukraine"): 1973,
  ("pripyat", "Ukraine"): 1970,
  ("prypyat", "Ukraine"): 1970,
  ("ukrainsk", "Ukraine"): 1952,
  ("ukrayinsk", "Ukraine"): 1952,
  # Belarus post-1897 planned towns
  ("soligorsk", "Belarus"): 1958,
  ("salihorsk", "Belarus"): 1958,
  ("novopolotsk", "Belarus"): 1958,
  ("navapolatsk", "Belarus"): 1958,
  ("beloozyorsk", "Belarus"): 1958,
  ("beloozersk", "Belarus"): 1958,
  ("novolukoml", "Belarus"): 1964,
}

# Pre-1975 merged suburbs or abandoned cities
MERGED_OR_ABANDONED = {
  ("sormovo", "Russia"): 1928,
  ("kanavino", "Russia"): 1928,
  ("nakhichevan on don", "Russia"): 1928,
  ("nakhichevan-on-don", "Russia"): 1928,
  ("motovilikha", "Russia"): 1938,
  ("bezhitsa", "Russia"): 1956,
  ("krivoshchekovo", "Russia"): 1930,
  ("mologa", "Russia"): 1941,
  ("korcheva", "Russia"): 1937,
  ("pokrovskaya sloboda", "Russia"): 1914,
  ("petrovskoye", "Russia"): 1928,
  ("kuzminki", "Russia"): 1960,
  ("babushkin", "Russia"): 1960,
  ("kuntsevo", "Russia"): 1960,
  ("lyublino", "Russia"): 1960,
  ("tushino", "Russia"): 1960,
  ("perovo", "Russia"): 1960,
  ("pavshino", "Russia"): 1932,
  ("ilimsk", "Russia"): 1974,
  ("otrozhka", "Russia"): 1940,
  ("verkhnyaya kurya", "Russia"): 1940,
  ("verhnjaja kurja", "Russia"): 1940,
  ("krasnyy khimik", "Russia"): 1940,
  ("sokolniki", "Russia"): 1917,
  ("khatyn", "Belarus"): 1943,
  ("pripyat", "Ukraine"): 1986,
  ("prypyat", "Ukraine"): 1986,
}

# ---------------------------------------------------------------------------
# Spatial Boundaries (POLARIS chapter polygons) & GeoNames Index
# ---------------------------------------------------------------------------


def load_chapter_polygons():
  poly_files = {
    "ch4": "imperial_russia_post_1815_polygons.geojson",
    "ch5": "russian_civil_war_polygons.geojson",
    "ch6": "soviet_lenin_stalin_polygons.geojson",
    "ch7": "soviet_post_stalin_polygons.geojson",
    "ch8": "post_soviet_space_polygons.geojson",
    "ch9": "russian_invasion_of_ukraine_polygons.geojson",
  }
  out = {}
  for ch, fn in poly_files.items():
    with open(os.path.join(GIS_DIR, fn), encoding="utf-8") as fh:
      gj = json.load(fh)
    feats = []
    for fe in gj.get("features", []):
      geom = shape(fe["geometry"])
      props = fe.get("properties", {})
      rid = props.get("id") or props.get("region")
      ct = props.get("country")
      feats.append((rid, ct, geom.bounds, prep(geom), geom))
    out[ch] = feats
  return out


def point_in_chapter(lat, lng, ch_feats):
  pt = Point(lng, lat)
  for rid, ct, b, pgeom, geom in ch_feats:
    if lng < b[0] or lng > b[2] or lat < b[1] or lat > b[3]:
      continue
    if pgeom.contains(pt):
      return rid, ct
  # Nearest feature within 0.08 deg coastal tolerance (e.g. port piers)
  best = None
  best_d = 0.08
  for rid, ct, b, pgeom, geom in ch_feats:
    if lng < b[0] - 0.1 or lng > b[2] + 0.1 or lat < b[1] - 0.1 or lat > b[3] + 0.1:
      continue
    d = geom.distance(pt)
    if d < best_d:
      best_d = d
      best = (rid, ct)
  return best


def find_region_by_country(lat, lng, country, ch_feats):
  """Finds polygon matching both coords and country if possible (fixes border snaps in Ch9)."""
  pt = Point(lng, lat)
  same_c = []
  any_c = []
  for rid, ct, b, pgeom, geom in ch_feats:
    in_b = (lng >= b[0] - 0.12 and lng <= b[2] + 0.12 and lat >= b[1] - 0.12 and lat <= b[3] + 0.12)
    if not in_b:
      continue
    if pgeom.contains(pt):
      if not ct or ct == country:
        return rid
      same_c.append((0.0, rid))
    elif not ct or ct == country:
      same_c.append((geom.distance(pt), rid))
    else:
      any_c.append((geom.distance(pt), rid))
  if same_c:
    same_c.sort()
    if same_c[0][0] < 0.35:
      return same_c[0][1]
  # Fallback global min distance within same country
  if country:
    best = None
    best_d = 999.0
    for rid, ct, b, pgeom, geom in ch_feats:
      if ct and ct != country:
        continue
      d = geom.distance(pt)
      if d < best_d:
        best_d = d
        best = rid
    if best and best_d < 1.5:
      return best
  return any_c[0][1] if any_c else None


# Mashke / Imperial subject -> GeoNames admin1 code mappings
SUBJECT_TO_ADMIN1 = {
  # Belarus (Cyrillic Russian & Belarusian headers)
  "минск": "BY.04", "г. минск": "BY.04", "г. мінск": "BY.04", "мінск": "BY.04",
  "минская область": "BY.05", "мінская": "BY.05",
  "брестская область": "BY.01", "брэсцкая": "BY.01",
  "гомельская область": "BY.02", "гомельская": "BY.02",
  "гродненская область": "BY.03", "гродзенская": "BY.03",
  "могилевская область": "BY.06", "магілёўская": "BY.06",
  "витебская область": "BY.07", "віцебская": "BY.07",
  # Russia (all 85+ federal subjects & former okrugs in Cyrillic)
  "адыгея": "RU.01", "республика алтай": "RU.03", "алтайский край": "RU.04",
  "амурская": "RU.05", "архангельская": "RU.06", "астраханская": "RU.07",
  "башкортостан": "RU.08", "белгородская": "RU.09", "брянская": "RU.10",
  "бурятия": "RU.11", "чеченская": "RU.12", "чечня": "RU.12",
  "челябинская": "RU.13", "чукотский": "RU.15", "чувашская": "RU.16",
  "дагестан": "RU.17", "ингушетия": "RU.19", "иркутская": "RU.20",
  "усть-ордынский": "RU.20", "ивановская": "RU.21", "кабардино-балкар": "RU.22",
  "калининградская": "RU.23", "калмыкия": "RU.24", "калужская": "RU.25",
  "карачаево-черкес": "RU.27", "карелия": "RU.28", "кемеровская": "RU.29",
  "хабаровский": "RU.30", "хакасия": "RU.31", "ханты-мансийск": "RU.32",
  "кировская": "RU.33", "коми": "RU.34", "коми-пермяцкий": "RU.90",
  "костромская": "RU.37", "краснодарский": "RU.38", "курганская": "RU.40",
  "курская": "RU.41", "ленинградская": "RU.42", "липецкая": "RU.43",
  "магаданская": "RU.44", "марий эл": "RU.45", "мордовия": "RU.46",
  "московская": "RU.47", "г. москва": "RU.48", "мурманская": "RU.49",
  "ненецкий": "RU.50", "нижегородская": "RU.51", "новгородская": "RU.52",
  "новосибирская": "RU.53", "омская": "RU.54", "оренбургская": "RU.55",
  "орловская": "RU.56", "пензенская": "RU.57", "приморский": "RU.59",
  "псковская": "RU.60", "ростовская": "RU.61", "рязанская": "RU.62",
  "саха": "RU.63", "якутия": "RU.63", "сахалинская": "RU.64",
  "самарская": "RU.65", "г. санкт-петербург": "RU.66", "саратовская": "RU.67",
  "северная осетия": "RU.68", "смоленская": "RU.69", "ставропольский": "RU.70",
  "свердловская": "RU.71", "екатеринбургская": "RU.71", "тамбовская": "RU.72",
  "татарстан": "RU.73", "томская": "RU.75", "тульская": "RU.76",
  "тверская": "RU.77", "тюменская": "RU.78", "тыва": "RU.79",
  "удмуртская": "RU.80", "ульяновская": "RU.81", "владимирская": "RU.83",
  "волгоградская": "RU.84", "вологодская": "RU.85", "воронежская": "RU.86",
  "ямало-ненецкий": "RU.87", "ярославская": "RU.88", "еврейская": "RU.89",
  "пермский": "RU.90", "красноярский": "RU.91", "таймырский": "RU.91",
  "эвенкийский": "RU.91", "камчатский": "RU.92", "корякский": "RU.92",
  "забайкальский": "RU.93", "агинский": "RU.93",
  # Ukraine (Mashke filenames / headers -> UA.*)
  "cherkaska": "UA.01", "черкаська": "UA.01", "черкасская": "UA.01",
  "chernihivska": "UA.02", "чернігівська": "UA.02", "черниговская": "UA.02",
  "chernivetska": "UA.03", "чернівецька": "UA.03", "черновицкая": "UA.03",
  "dnipropetrovska": "UA.04", "дніпропетровська": "UA.04", "днепропетровская": "UA.04",
  "donetska": "UA.05", "донецька": "UA.05", "донецкая": "UA.05",
  "ivano-frankivska": "UA.06", "івано-франківська": "UA.06",
  "kharkivska": "UA.07", "харківська": "UA.07", "харьковская": "UA.07",
  "khersonska": "UA.08", "херсонська": "UA.08", "херсонская": "UA.08",
  "khmelnytska": "UA.09", "хмельницька": "UA.09", "хмельницкая": "UA.09",
  "kirovohradska": "UA.10", "кіровоградська": "UA.10", "кировоградская": "UA.10",
  "avtonomna respublika krym": "UA.11", "крым": "UA.11", "крим": "UA.11",
  "севастополь": "UA.20", "м. севастополь": "UA.20",
  "м. київ": "UA.12", "київська": "UA.13", "киевская": "UA.13",
  "luhanska": "UA.14", "луганська": "UA.14", "луганская": "UA.14",
  "lvivska": "UA.15", "львівська": "UA.15", "львовская": "UA.15",
  "mykolaivska": "UA.16", "миколаївська": "UA.16", "николаевская": "UA.16",
  "odeska": "UA.17", "одеська": "UA.17", "одесская": "UA.17",
  "poltavska": "UA.18", "полтавська": "UA.18", "полтавская": "UA.18",
  "rivnenska": "UA.19", "рівненська": "UA.19", "ровенская": "UA.19",
  "sumska": "UA.21", "сумська": "UA.21", "сумская": "UA.21",
  "ternopilska": "UA.22", "тернопільська": "UA.22", "тернопольская": "UA.22",
  "vinnytska": "UA.23", "вінницька": "UA.23", "винницкая": "UA.23",
  "volynska": "UA.24", "волинська": "UA.24", "волынская": "UA.24",
  "zakarpatska": "UA.25", "закарпатська": "UA.25", "закарпатская": "UA.25",
  "zaporizka": "UA.26", "запорізька": "UA.26", "запорожская": "UA.26",
  "zhytomyrska": "UA.27", "житомирська": "UA.27", "житомирская": "UA.27",
}

# Mashke filename stem -> admin1 code for ukraine & belarus & russia
UA_FILE_TO_ADMIN1 = {
  "avtonomna_respublika_krym": "UA.11", "cerkaska": "UA.01", "cernihivska": "UA.02",
  "cernivecka": "UA.03", "dnipropetrovska": "UA.04", "donecka": "UA.05",
  "charkivska": "UA.07", "chersonska": "UA.08", "chmelnycka": "UA.09",
  "ivano-frankivska": "UA.06", "kirovohradska": "UA.10", "kyjiv": "UA.12",
  "kyjivska": "UA.13", "luhanska": "UA.14", "lvivska": "UA.15",
  "mykolajivska": "UA.16", "odeska": "UA.17", "poltavska": "UA.18",
  "rivnenska": "UA.19", "sevastopol": "UA.20", "sumska": "UA.21",
  "ternopilska": "UA.22", "vinnycka": "UA.23", "volynska": "UA.24",
  "zakarpatska": "UA.25", "zaporizka": "UA.26", "zytomyrska": "UA.27",
}

BY_FILE_TO_ADMIN1 = {
  "bresckaja": "BY.01", "homielskaja": "BY.02", "hrodzienskaja": "BY.03",
  "miensk": "BY.04", "mienskaja": "BY.05", "mahilouskaja": "BY.06", "viciebskaja": "BY.07",
}

RU_FILE_TO_ADMIN1 = {
  "adygeja": "RU.01", "altaj": "RU.03", "altajskij-kraj": "RU.04", "amurskaja": "RU.05",
  "archangelskaja": "RU.06", "astrachanskaja": "RU.07", "baskortostan": "RU.08",
  "belgorodskaja": "RU.09", "brjanskaja": "RU.10", "burjatija": "RU.11",
  "cecnja": "RU.12", "celjabinskaja": "RU.13", "chukotka": "RU.15", "cuvasija": "RU.16",
  "dagestan": "RU.17", "ingusetija": "RU.19", "irkutskaja": "RU.20", "ivanovskaja": "RU.21",
  "jakutija": "RU.63", "jamal-nenec": "RU.87", "jaroslavskaja": "RU.88",
  "jekaterinburgskaja": "RU.71", "jevrejskaja": "RU.89", "juzno-sachalinskaja": "RU.64",
  "kabardino-balkarija": "RU.22", "kaliningradskaja": "RU.23", "kalmykija": "RU.24",
  "kaluzskaja": "RU.25", "kamcatskaja": "RU.92", "karacajevo-cerkesija": "RU.27",
  "karelija": "RU.28", "kemerovskaja": "RU.29", "chabarovskij": "RU.30",
  "chakasija": "RU.31", "chanty-mansi": "RU.32", "kirovskaja": "RU.33",
  "komi": "RU.34", "kostromskaja": "RU.37", "krasnodarskij": "RU.38",
  "krasnojarskij": "RU.91", "kurganskaja": "RU.40", "kurskaja": "RU.41",
  "leningradskaja": "RU.42", "lipeckaja": "RU.43", "magadanskaja": "RU.44",
  "marij-el": "RU.45", "mordovija": "RU.46", "moskovskaja": "RU.47", "moskva": "RU.48",
  "murmanskaja": "RU.49", "nenec": "RU.50", "nizegorodskaja": "RU.51",
  "novgorodskaja": "RU.52", "novosibirskaja": "RU.53", "omskaja": "RU.54",
  "orenburgskaja": "RU.55", "orlovskaja": "RU.56", "penzenskaja": "RU.57",
  "permskij": "RU.90", "primorskij": "RU.59", "pskovskaja": "RU.60",
  "rostovskaja": "RU.61", "rjazanskaja": "RU.62", "sachalinskaja": "RU.64",
  "saha": "RU.63", "samarskaja": "RU.65", "sankt-peterburg": "RU.66",
  "saratovskaja": "RU.67", "severnaja-osetija": "RU.68", "smolenskaja": "RU.69",
  "stavropolskij": "RU.70", "sverdlovskaja": "RU.71", "tambovskaja": "RU.72",
  "tatarstan": "RU.73", "tjumenskaja": "RU.78", "tomskaja": "RU.75",
  "tulskaja": "RU.76", "tuva": "RU.79", "tverskaja": "RU.77",
  "udmurtija": "RU.80", "uljanovskaja": "RU.81", "vladimirskaja": "RU.83",
  "volgogradskaja": "RU.84", "vologodskaja": "RU.85", "voronezskaja": "RU.86",
  "zabajkalskij": "RU.93",
}

# Governorate -> expected (Country, [admin1_codes], approx_lat_min, lat_max, lng_min, lng_max)
GOV_SPATIAL_SCOPE = {
  "архангельск": ("Russia", {"RU.06", "RU.49", "RU.50", "RU.28", "RU.34"}),
  "астрахан": ("Russia", {"RU.07", "RU.24", "RU.84"}),
  "бессараб": ("Moldova", {"MD.", "UA.17", "UA.03"}),
  "виленск": ("Lithuania", {"LT.", "BY.03", "BY.07", "BY.05"}),
  "витебск": ("Belarus", {"BY.07", "LV.", "RU.60"}),
  "владимир": ("Russia", {"RU.83", "RU.21", "RU.47", "RU.51"}),
  "вологод": ("Russia", {"RU.85", "RU.34", "RU.06"}),
  "волынск": ("Ukraine", {"UA.24", "UA.19", "UA.27", "UA.09", "UA.22"}),
  "воронеж": ("Russia", {"RU.86", "RU.09", "RU.43"}),
  "вятск": ("Russia", {"RU.33", "RU.80", "RU.73"}),
  "гроднен": ("Belarus", {"BY.03", "BY.01", "PL."}),
  "донск": ("Russia", {"RU.61", "RU.84", "RU.38", "UA.05", "UA.14"}),
  "екатеринослав": ("Ukraine", {"UA.04", "UA.05", "UA.26", "UA.14"}),
  "казан": ("Russia", {"RU.73", "RU.16", "RU.45"}),
  "калуж": ("Russia", {"RU.25"}),
  "киев": ("Ukraine", {"UA.12", "UA.13", "UA.01", "UA.27", "UA.23"}),
  "ковен": ("Lithuania", {"LT."}),
  "костром": ("Russia", {"RU.37", "RU.21", "RU.51", "RU.33"}),
  "кубан": ("Russia", {"RU.38", "RU.01", "RU.27"}),
  "курлянд": ("Latvia", {"LV."}),
  "курск": ("Russia", {"RU.41", "RU.09", "UA.21"}),
  "лифлянд": ("Latvia", {"LV.", "EE."}),
  "минск": ("Belarus", {"BY.04", "BY.05", "BY.02", "BY.01"}),
  "могилев": ("Belarus", {"BY.06", "BY.02", "BY.07"}),
  "москов": ("Russia", {"RU.47", "RU.48"}),
  "нижегород": ("Russia", {"RU.51", "RU.46"}),
  "новгород": ("Russia", {"RU.52", "RU.85", "RU.42"}),
  "олонец": ("Russia", {"RU.28", "RU.42", "RU.85"}),
  "оренбург": ("Russia", {"RU.55", "RU.13", "RU.08"}),
  "орлов": ("Russia", {"RU.56", "RU.10", "RU.43"}),
  "пенз": ("Russia", {"RU.57", "RU.46"}),
  "перм": ("Russia", {"RU.90", "RU.71", "RU.13"}),
  "подольск": ("Ukraine", {"UA.23", "UA.09", "UA.17", "UA.01", "MD."}),
  "полтав": ("Ukraine", {"UA.18", "UA.01", "UA.21", "UA.13", "UA.02"}),
  "псков": ("Russia", {"RU.60"}),
  "рязан": ("Russia", {"RU.62", "RU.43"}),
  "самар": ("Russia", {"RU.65", "RU.81", "RU.67", "RU.55", "RU.73"}),
  "санкт петербург": ("Russia", {"RU.66", "RU.42"}),
  "саратов": ("Russia", {"RU.67", "RU.84", "RU.57"}),
  "симбир": ("Russia", {"RU.81", "RU.16", "RU.46"}),
  "смолен": ("Russia", {"RU.69", "RU.77"}),
  "ставропол": ("Russia", {"RU.70", "RU.24"}),
  "таврич": ("Ukraine", {"UA.11", "UA.20", "UA.08", "UA.26"}),
  "тамбов": ("Russia", {"RU.72", "RU.43", "RU.57", "RU.46", "RU.86"}),
  "твер": ("Russia", {"RU.77"}),
  "терск": ("Russia", {"RU.12", "RU.19", "RU.22", "RU.68", "RU.70", "RU.17"}),
  "тульск": ("Russia", {"RU.76"}),
  "уфим": ("Russia", {"RU.08", "RU.73", "RU.13"}),
  "харьков": ("Ukraine", {"UA.07", "UA.21", "UA.05", "UA.14"}),
  "херсон": ("Ukraine", {"UA.08", "UA.16", "UA.17", "UA.10", "UA.04"}),
  "чернигов": ("Ukraine", {"UA.02", "UA.21", "RU.10"}),
  "черномор": ("Russia", {"RU.38"}),
  "дагестан": ("Russia", {"RU.17"}),
  "эстлянд": ("Estonia", {"EE."}),
  "ярослав": ("Russia", {"RU.88"}),
  "амур": ("Russia", {"RU.05", "RU.89"}),
  "енисей": ("Russia", {"RU.91", "RU.31"}),
  "иркутск": ("Russia", {"RU.20"}),
  "забайкал": ("Russia", {"RU.93", "RU.11"}),
  "примор": ("Russia", {"RU.59", "RU.30"}),
  "сахалин": ("Russia", {"RU.64"}),
  "тобольск": ("Russia", {"RU.78", "RU.32", "RU.87", "RU.40", "RU.54"}),
  "томск": ("Russia", {"RU.75", "RU.53", "RU.29", "RU.04", "RU.03"}),
  "якутск": ("Russia", {"RU.63"}),
  # Soviet 1920s-1930s krais & oblasts
  "урал": ("Russia", {"RU.90", "RU.71", "RU.13", "RU.40", "RU.78", "RU.32", "RU.87"}),
  "северо кавказ": ("Russia", {"RU.61", "RU.38", "RU.70", "RU.01", "RU.22", "RU.68", "RU.12", "RU.19", "RU.27"}),
  "центрально чернозем": ("Russia", {"RU.41", "RU.09", "RU.86", "RU.72", "RU.56", "RU.43"}),
  "средне волж": ("Russia", {"RU.65", "RU.81", "RU.57", "RU.46", "RU.55"}),
  "нижне волж": ("Russia", {"RU.67", "RU.84", "RU.07", "RU.24"}),
  "сталинград": ("Russia", {"RU.84", "RU.07", "RU.24"}),
  "куйбышев": ("Russia", {"RU.65", "RU.81"}),
  "горьков": ("Russia", {"RU.51", "RU.33", "RU.16", "RU.45"}),
  "калинин": ("Russia", {"RU.77", "RU.60"}),
  "чкалов": ("Russia", {"RU.55"}),
  "молотов": ("Russia", {"RU.90"}),
  "орджоникидз": ("Russia", {"RU.70", "RU.27"}),
  "западно сибир": ("Russia", {"RU.53", "RU.04", "RU.29", "RU.75", "RU.54"}),
  "восточно сибир": ("Russia", {"RU.20", "RU.91", "RU.11", "RU.93"}),
  "сибирск": ("Russia", {"RU.53", "RU.04", "RU.29", "RU.75", "RU.54", "RU.91", "RU.31"}),
  "дальне восточ": ("Russia", {"RU.59", "RU.30", "RU.05", "RU.89", "RU.64", "RU.44", "RU.92", "RU.15"}),
  "дальневосточ": ("Russia", {"RU.59", "RU.30", "RU.05", "RU.89", "RU.64", "RU.44", "RU.92", "RU.15"}),
  "ленинград": ("Russia", {"RU.66", "RU.42", "RU.52", "RU.60", "RU.49"}),
  "белорус": ("Belarus", {"BY."}),
  "украин": ("Ukraine", {"UA."}),
  "крым": ("Ukraine", {"UA.11", "UA.20"}),
}

FCODE_RANK = {"PPLC": 0, "PPLA": 1, "PPLA2": 2, "PPLA3": 3, "PPLA4": 4, "PPL": 5, "PPLL": 6, "PPLQ": 7, "PPLX": 9}


class GeoNamesIndex:
  def __init__(self, poly_ch4):
    self.by_norm = defaultdict(list)
    self.by_country_norm = defaultdict(list)
    self.by_admin1_norm = defaultdict(list)
    self.by_grid = defaultdict(list)
    self.coord_meta = {}
    self.admin_centroids = {}
    self._load(poly_ch4)

  def _load(self, poly_ch4):
    cc_map = {
      "RU": "Russia", "UA": "Ukraine", "BY": "Belarus",
      "PL": "Poland", "FI": "Finland", "EE": "Estonia",
      "LV": "Latvia", "LT": "Lithuania", "MD": "Moldova",
    }
    admin_pts = defaultdict(list)
    for cc, cname in cc_map.items():
      fp = os.path.join(GN_DIR, f"{cc}.txt")
      if not os.path.exists(fp):
        continue
      with open(fp, encoding="utf-8", errors="replace") as fh:
        for line in fh:
          cols = line.rstrip("\n").split("\t")
          if len(cols) < 15:
            continue
          if cols[6] != "P":
            continue
          fcode = cols[7]
          if fcode in ("PPLH", "PPLW"):
            continue
          lat = float(cols[4])
          lng = float(cols[5])
          # Verify inside broad POLARIS ch4 polygon (+ 0.1 deg coastal tolerance)
          if point_in_chapter(lat, lng, poly_ch4) is None:
            continue
          adm1 = f"{cc}.{cols[10]}" if cols[10] else cc
          pop = int(cols[14]) if cols[14].isdigit() else 0
          rank = FCODE_RANK.get(fcode, 8)
          prim_norms = set()
          for nm in (cols[1], cols[2]):
            nl = norm_lat(nm)
            if nl:
              prim_norms.add(nl)
            if re.search(r"[а-яА-ЯёЁіїєґ]", nm):
              nc = norm_cyr(nm)
              if nc:
                prim_norms.add(nc)
          names = {cols[1], cols[2]}
          if cols[3]:
            for alt in cols[3].split(","):
              if alt and len(alt) <= 45:
                names.add(alt)
          norms = set(prim_norms)
          for nm in names:
            nl = norm_lat(nm)
            if nl:
              norms.add(nl)
            if re.search(r"[а-яА-ЯёЁіїєґ]", nm):
              nc = norm_cyr(nm)
              if nc:
                norms.add(nc)
          rec = (pop, -rank, lat, lng, cname, adm1, cols[1], fcode, cols[0], prim_norms, norms)
          ckey = (round(lat, 5), round(lng, 5))
          if ckey not in self.coord_meta or pop > self.coord_meta[ckey][1]:
            self.coord_meta[ckey] = (fcode, pop, norms)
          for nf in norms:
            self.by_norm[nf].append(rec)
            self.by_country_norm[(cname, nf)].append(rec)
            self.by_admin1_norm[(adm1, nf)].append(rec)
          gk = (int(math.floor(lat * 2)), int(math.floor(lng * 2)))
          self.by_grid[gk].append((lat, lng, cname, adm1, pop, -rank, cols[1], norms))
          if pop > 0 or fcode in ("PPLA", "PPLA2"):
            admin_pts[adm1].append((lat, lng))
    for adm1, pts in admin_pts.items():
      if pts:
        self.admin_centroids[adm1] = (sum(x[0] for x in pts) / len(pts), sum(x[1] for x in pts) / len(pts))
    print(f"GeoNamesIndex loaded: {len(self.by_norm)} distinct name keys, {len(self.by_grid)} spatial cells")

  def get_coord_meta(self, lat, lng):
    return self.coord_meta.get((round(float(lat), 5), round(float(lng), 5)))

  def _pick_best(self, cands, forms, prefer_urban=True, claimed_fn=None):
    seen_ids = set()
    scored = []
    for rec in cands:
      gid = rec[8]
      if gid in seen_ids:
        continue
      seen_ids.add(gid)
      pop, nrank, lat, lng, cn, adm, gname, fcode, _, prim_norms, all_norms = rec
      is_prim = 1 if (forms & prim_norms) else 0
      is_pplx = (fcode == "PPLX")
      sc = (is_prim, 0 if is_pplx else 1, nrank, pop)
      scored.append((sc, lat, lng, cn, adm, gname, pop, all_norms))
    scored.sort(key=lambda x: x[0], reverse=True)
    for _, lat, lng, cn, adm, gname, pop, all_norms in scored:
      if claimed_fn and claimed_fn(lat, lng, cn, forms | all_norms):
        continue
      return (lat, lng, cn, adm, gname, pop)
    return None

  def lookup(self, name, country=None, admin1=None, aliases=None, prefer_urban=True, claimed_fn=None):
    forms = expand_name_forms(name, aliases)
    if admin1:
      cands_a = []
      for f in forms:
        cands_a.extend(self.by_admin1_norm.get((admin1, f), []))
      if cands_a:
        res = self._pick_best(cands_a, forms, prefer_urban=prefer_urban, claimed_fn=claimed_fn)
        if res:
          return res
        # If admin1 had candidates but ALL were claimed collisions on an exact coordinate, do not cross-obl collide!
        return None
    cands = []
    if country:
      for f in forms:
        cands.extend(self.by_country_norm.get((country, f), []))
    elif not country:
      for f in forms:
        cands.extend(self.by_norm.get(f, []))
    if not cands:
      return None
    return self._pick_best(cands, forms, prefer_urban=prefer_urban, claimed_fn=claimed_fn)

  def lookup_gov(self, name, gov_key, aliases=None, claimed_fn=None):
    gl = norm_cyr(gov_key or "")
    adm_exact = None
    for k, v in SUBJECT_TO_ADMIN1.items():
      if k in gl:
        adm_exact = v
        break
    scope = None
    if not adm_exact:
      for k, v in GOV_SPATIAL_SCOPE.items():
        if k in gl:
          scope = v
          break
    forms = expand_name_forms(name, aliases)
    cands = []
    if adm_exact:
      for f in forms:
        cands.extend(self.by_admin1_norm.get((adm_exact, f), []))
      if cands:
        res = self._pick_best(cands, forms, prefer_urban=True, claimed_fn=claimed_fn)
        if res:
          return res
        return None
    if scope:
      cname, adm_set = scope
      for f in forms:
        for rec in self.by_norm.get(f, []):
          adm = rec[5]
          if adm in adm_set or any(adm.startswith(a) for a in adm_set if a.endswith(".")):
            cands.append(rec)
    else:
      for f in forms:
        cands.extend(self.by_norm.get(f, []))
    if not cands:
      return None
    return self._pick_best(cands, forms, prefer_urban=True, claimed_fn=claimed_fn)

  def find_near_by_name(self, lat, lng, name, aliases=None, max_km=8.0):
    forms = expand_name_forms(name, aliases)
    gx, gy = int(math.floor(lat * 2)), int(math.floor(lng * 2))
    best = None
    best_sc = (0, -999.0)
    for dx in (-1, 0, 1):
      for dy in (-1, 0, 1):
        for rlat, rlng, cn, adm, pop, nrank, gname, rnorms in self.by_grid.get((gx + dx, gy + dy), ()):
          d = haversine_km((lat, lng), (rlat, rlng))
          if d <= max_km and (forms & rnorms):
            return (rlat, rlng, cn, adm, gname, pop)
    return best


# ---------------------------------------------------------------------------
# Wikidata Loader (inceptions + hist_pops indexed spatially)
# ---------------------------------------------------------------------------


def load_wikidata_spatial():
  """Loads Wikidata historical P1082 populations bucketed on a 0.2-deg spatial grid."""
  inc_grid = defaultdict(list)
  pop_grid = defaultdict(list)
  pt_re = re.compile(r"Point\(\s*([-\d.]+)\s+([-\d.]+)\s*\)")
  for fn in os.listdir(WD_DIR):
    fp = os.path.join(WD_DIR, fn)
    if not fn.endswith("_hist_pops.json"):
      continue
    with open(fp, encoding="utf-8") as fh:
      data = json.load(fh)
    records = data if isinstance(data, list) else data.get("pops", [])
    for rec in records:
      yr = rec.get("yr") if rec.get("yr") is not None else rec.get("year")
      pop = rec.get("pop")
      lat, lng = rec.get("lat"), rec.get("lng")
      if (lat is None or lng is None) and rec.get("coord"):
        m = pt_re.search(str(rec["coord"]))
        if m:
          lng = float(m.group(1))
          lat = float(m.group(2))
      if lat is None or lng is None or yr is None or not pop:
        continue
      gk = (int(math.floor(float(lat) * 5)), int(math.floor(float(lng) * 5)))
      pop_grid[gk].append((float(lat), float(lng), int(yr), int(round(float(pop)))))
  print(f"Wikidata spatial loaded: inc_cells={len(inc_grid)}, pop_cells={len(pop_grid)}")
  return inc_grid, pop_grid


# ---------------------------------------------------------------------------
# HTML / Text Corpus Parsers
# ---------------------------------------------------------------------------


def extract_remark_info(remark):
  info = {"aliases": [], "found_yr": None, "merged_yr": None, "became_village": False}
  if not remark:
    return info
  low = remark.lower()
  if "merged with" in low or "часть г." in low or "включен" in low:
    m = re.search(r"(?:in|с)\s+(\d{4})", low)
    if m:
      info["merged_yr"] = int(m.group(1))
  if "became a village" in low or "now is a village" in low or re.search(r"с\s+\d{4}\s*[-–]?\s*село", low):
    info["became_village"] = True
  m_f = re.search(r"(?:осн\.?|основан[ао]?|founded(?:\s+in)?)\s+(\d{4})", low)
  if m_f:
    fy = int(m_f.group(1))
    if 1898 <= fy <= 2024:
      info["found_yr"] = fy
  # Extract aliases like "до 2016 Дзержинск", "Drysa until 1962"
  for am in re.findall(r"(?:до\s+\d{4}|until\s+\d{4}|в\s+\d{4}[-–]\d{4})\s*[-–]?\s*([А-ЯЁІЇЄҐA-Z][а-яёіїєґa-z\-'\s]{2,30})", remark):
    info["aliases"].append(am.strip())
  for am in re.findall(r"([А-ЯЁІЇЄҐA-Z][а-яёіїєґa-z\-']{2,25})\s+(?:until\s+\d{4})", remark):
    info["aliases"].append(am.strip())
  return info


def parse_mashke_multi_cities(country_file_specs):
  """Parses *-cities.htm tables (units: thousands)."""
  rows_out = []
  for fn, country, has_latin_col, default_has_subj_hdr in country_file_specs:
    fp = os.path.join(MASHKE_DIR, fn)
    if not os.path.exists(fp):
      continue
    cols_yrs = []
    cur_subj = ""
    with open(fp, encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s.startswith("<tr>"):
          continue
        parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
        if not cols_yrs and "<th" in s:
          # Header row with dates
          text_cells = [strip_tags(p) for p in parts]
          start_c = 2 if has_latin_col else 1
          for idx, tc in enumerate(text_cells[start_c:], start=start_c):
            m = re.match(r"(\d{4})", tc)
            if m:
              cols_yrs.append((idx, int(m.group(1))))
          continue
        if "<th" in s and "<td" not in s:
          subj_txt = strip_tags(parts[0])
          if subj_txt and subj_txt not in ("…",):
            cur_subj = subj_txt
          continue
        if "<td" not in s:
          continue
        raw_c0 = parts[0]
        is_italic = raw_c0.lstrip().startswith("<nobr><i>") or "<i>" in raw_c0[:20]
        name_cyr = strip_tags(raw_c0)
        name_lat = strip_tags(parts[1]) if (has_latin_col and len(parts) > 1) else name_cyr
        if not name_cyr or name_cyr.startswith("*"):
          continue
        pops = {}
        remark = ""
        last_yr_idx = cols_yrs[-1][0] if cols_yrs else 1
        for idx, yr in cols_yrs:
          if idx < len(parts):
            v = parse_thousands_num(parts[idx])
            if v:
              pops[yr] = v
        if len(parts) > last_yr_idx + 1:
          remark = strip_tags(parts[last_yr_idx + 1])
        rinfo = extract_remark_info(remark)
        # Check inline italic or subordinate Moscow/Minsk/SPb district before skipping
        # Keep merged suburbs like Sormovo/Motovilikha/Bezhitsa/Bilychi if they have pre-1975 pops & merged_yr!
        # Skip unnamed urban districts with only modern pops or purely intra-city districts (* без...)
        if is_italic and not rinfo["merged_yr"] and not rinfo["became_village"] and (max(pops) if pops else 0) >= 1975:
          # Sub-unit like Сокал inside Minsk still might have own name, keep if merged/suburb; skip pure admin districts
          if re.search(r"район|округ", name_cyr, re.I):
            continue
        if not pops:
          continue
        rows_out.append({
          "country": country,
          "subject": cur_subj,
          "name": name_lat if has_latin_col else name_cyr,
          "name_cyr": name_cyr,
          "name_lat": name_lat,
          "aliases": rinfo["aliases"],
          "pops": pops,
          "remark": remark,
          "found_yr": rinfo["found_yr"],
          "merged_yr": rinfo["merged_yr"],
          "is_italic": is_italic,
          "source_table": fn,
        })
  print(f"Parsed *-cities.htm: {len(rows_out)} settlement series")
  return rows_out


def map_ru_subject_admin1(fn_stem, header_text):
  if fn_stem in RU_FILE_TO_ADMIN1:
    return RU_FILE_TO_ADMIN1[fn_stem]
  hl = header_text.lower()
  for k, v in SUBJECT_TO_ADMIN1.items():
    if k in hl:
      return v
  return None


def parse_russia_modern_censuses():
  """
  Parses russia-census-2002, 2010, 2021 by subject, keeping raion hierarchy, settlement status,
  and skipping intra-city rayons & municipality totals. Links 2002 <-> 2010 <-> 2021 safely.
  """
  era_dirs = [(2002, "russia-census-2002"), (2010, "russia-census-2010"), (2021, "russia-census-2021")]
  # subject adm1 -> yr -> list of {name, norm, stems, status, raion, pop}
  by_adm = defaultdict(lambda: defaultdict(list))
  for yr, dname in era_dirs:
    dp = os.path.join(MASHKE_DIR, dname)
    if not os.path.isdir(dp):
      continue
    for fn in sorted(os.listdir(dp)):
      if not fn.endswith(".htm") or fn == "index.htm":
        continue
      stem = fn[:-4]
      adm1 = RU_FILE_TO_ADMIN1.get(stem)
      if not adm1 or adm1 in ("RU.48", "RU.66"):
        continue
      cur_raion = ""
      with open(os.path.join(dp, fn), encoding="utf-8", errors="replace") as fh:
        for line in fh:
          s = line.strip()
          if not s.startswith("<tr>"):
            continue
          parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
          if "<th" in s and "<td" not in s:
            txt = strip_tags(parts[0])
            if txt and "всего" not in txt.lower() and not re.match(r"^\d{4}", txt):
              cur_raion = txt
            continue
          if "<td" not in s or len(parts) < 2:
            continue
          raw_c0 = parts[0]
          # Skip italic intra-city districts and municipality aggregate bold rows (поселение, округ, горсовет)
          if "<i>" in raw_c0[:25]:
            continue
          c0 = strip_tags(raw_c0)
          if re.search(r"(?:поселение|округ|сельсовет|муниципальн|внутригород|сельское\s+население|городское\s+население|итого|прочее\s+население)", c0, re.I):
            continue
          if "<b>" in raw_c0[:25] and "<a>" not in raw_c0[:25]:
            # Usually aggregate municipal header when not marked г./пгт
            if not re.match(r"^(?:г\.|город|пгт|рп)", c0.lower()):
              continue
          # Population cell is index 1 (or find first integer col after name; russia-census-2002/2010/2021 has [name, total, ...])
          pop = parse_int_num(parts[1])
          if not pop:
            continue
          st = detect_status(c0)
          nm = clean_settlement_label(c0)
          nc = norm_cyr(c0)
          if not nc or len(nc) < 2:
            continue
          by_adm[adm1][yr].append({
            "raw": c0, "name": nm, "norm": nc, "status": st,
            "raion": norm_cyr(cur_raion), "pop": pop,
          })

  # Link 2002 <-> 2010 <-> 2021 inside each admin1 safely
  linked_ru = []
  for adm1, yr_map in by_adm.items():
    clusters = []  # each: {name, norm, status, raion, adm1, pops:{yr:pop}}
    for yr in (2021, 2010, 2002):
      rows = yr_map.get(yr, [])
      for r in rows:
        best_c = None
        best_sc = (-1, -999)
        for c in clusters:
          if c["norm"] != r["norm"]:
            continue
          if yr in c["pops"]:
            continue
          if not status_compatible(c["status"], r["status"]):
            continue
          # Population ratio check against closest existing year
          ref_yr = min(c["pops"], key=lambda y: abs(y - yr))
          ref_pop = c["pops"][ref_yr]
          ratio = max(ref_pop, r["pop"]) / max(1, min(ref_pop, r["pop"]))
          if max(ref_pop, r["pop"]) >= 1500 and ratio > 3.5:
            continue
          if ratio > 5.0:
            continue
          r_sim = 1 if (c["raion"] and r["raion"] and (c["raion"] in r["raion"] or r["raion"] in c["raion"])) else 0
          sc = (r_sim, -abs(math.log(max(ref_pop, r["pop"]) / max(1, min(ref_pop, r["pop"])))))
          if sc > best_sc:
            best_sc = sc
            best_c = c
        if best_c is not None:
          best_c["pops"][yr] = r["pop"]
          if best_c["status"] == "unknown" and r["status"] != "unknown":
            best_c["status"] = r["status"]
        else:
          clusters.append({
            "adm1": adm1, "country": "Russia", "name": r["name"], "norm": r["norm"],
            "status": r["status"], "raion": r["raion"], "pops": {yr: r["pop"]},
          })
    linked_ru.extend(clusters)
  print(f"Linked Russia 2002/2010/2021 settlements: {len(linked_ru)}")
  return linked_ru


def parse_ukraine_modern_censuses():
  """
  Parses ukraine-census-pres (1989, 2001), ukraine-estimation-pres (2021, 2022), and rk-gfzs-census (Crimea 2001, 2014, 2021).
  Links across oblasts using UA_ALIAS_PAIRS + status + population ratio guards (eliminates 33->229k & 9696->3 collisions).
  """
  by_adm = defaultdict(list)  # adm1 -> records from 1989/2001
  est_by_adm = defaultdict(list)  # adm1 -> records from 2021/2022

  # 1. ukraine-census-pres (1989, 2001)
  dp1 = os.path.join(MASHKE_DIR, "ukraine-census-pres")
  if os.path.isdir(dp1):
    for fn in sorted(os.listdir(dp1)):
      if not fn.endswith(".htm") or fn == "index.htm":
        continue
      adm1 = UA_FILE_TO_ADMIN1.get(fn[:-4])
      if not adm1 or adm1 in ("UA.12", "UA.20"):
        continue
      cur_rada = ""
      with open(os.path.join(dp1, fn), encoding="utf-8", errors="replace") as fh:
        for line in fh:
          s = line.strip()
          if not s.startswith("<tr>"):
            continue
          parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
          if "<th" in s and "<td" not in s:
            cur_rada = strip_tags(parts[0])
            continue
          if "<td" not in s or len(parts) < 4:
            continue
          raw_c0 = parts[0]
          if "<i>" in raw_c0[:25]:
            continue
          c0 = strip_tags(raw_c0)
          c1 = strip_tags(parts[1])
          if re.search(r"(?:рада|район|райрада|міськрада|населення|всього)", c0, re.I):
            continue
          if "<b>" in raw_c0[:25] and "<a>" not in raw_c0[:25]:
            continue
          p89 = parse_int_num(parts[2])
          p01 = parse_int_num(parts[3])
          if not p89 and not p01:
            continue
          pops = {}
          if p89:
            pops[1989] = p89
          if p01:
            pops[2001] = p01
          forms = expand_name_forms(c0, [c1])
          by_adm[adm1].append({
            "adm1": adm1, "name": clean_settlement_label(c1), "name_cyr": clean_settlement_label(c0),
            "forms": forms, "status": detect_status(c0), "rada": norm_cyr(cur_rada), "pops": pops,
          })

  # 2. ukraine-estimation-pres (2021, 2022)
  dp2 = os.path.join(MASHKE_DIR, "ukraine-estimation-pres")
  if os.path.isdir(dp2):
    for fn in sorted(os.listdir(dp2)):
      if not fn.endswith(".htm") or fn == "index.htm":
        continue
      adm1 = UA_FILE_TO_ADMIN1.get(fn[:-4])
      if not adm1 or adm1 in ("UA.12", "UA.20"):
        continue
      cur_tg = ""
      with open(os.path.join(dp2, fn), encoding="utf-8", errors="replace") as fh:
        for line in fh:
          s = line.strip()
          if not s.startswith("<tr>"):
            continue
          parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
          if "<th" in s and "<td" not in s:
            cur_tg = strip_tags(parts[0])
            continue
          if "<td" not in s or len(parts) < 3:
            continue
          raw_c0 = parts[0]
          if "<i>" in raw_c0[:25]:
            continue
          c0 = strip_tags(raw_c0)
          if re.search(r"(?:громада|район|область|\bТГ\b|рада|всього)", c0, re.I):
            continue
          if "<b>" in raw_c0[:25] and "<a>" not in raw_c0[:25] and not re.match(r"^(?:м\.|смт)", c0.lower()):
            continue
          p21 = parse_int_num(parts[1])
          p22 = parse_int_num(parts[2])
          if not p21 and not p22:
            continue
          pops = {}
          if p21:
            pops[2021] = p21
          if p22:
            pops[2022] = p22
          forms = expand_name_forms(c0)
          est_by_adm[adm1].append({
            "adm1": adm1, "name": clean_settlement_label(cyr_to_lat(c0)).title(),
            "name_cyr": clean_settlement_label(c0),
            "forms": forms, "status": detect_status(c0), "tg": norm_cyr(cur_tg), "pops": pops,
          })

  # 3. rk-gfzs-census.htm (Crimea 2001, 2014, 2021)
  rk_fp = os.path.join(MASHKE_DIR, "rk-gfzs-census.htm")
  if os.path.exists(rk_fp):
    cur_adm = "UA.11"
    with open(rk_fp, encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s.startswith("<tr>"):
          continue
        parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
        if "<th" in s and "<td" not in s:
          hdr = strip_tags(parts[0]).lower()
          if "севастополь" in hdr:
            cur_adm = "UA.20"
          elif "крим" in hdr or "автономна" in hdr:
            cur_adm = "UA.11"
          continue
        if "<td" not in s or len(parts) < 5:
          continue
        raw_c0 = parts[0]
        if "<i>" in raw_c0[:25] or ("<b>" in raw_c0[:25] and "<a>" not in raw_c0[:25]):
          continue
        c0 = strip_tags(raw_c0)
        c1 = strip_tags(parts[1])
        if re.search(r"(?:рада|район|міськ|округ)", c0, re.I):
          continue
        p01 = parse_int_num(parts[2])
        p14 = parse_int_num(parts[3])
        p21 = parse_int_num(parts[4])
        pops = {}
        if p01:
          pops[2001] = p01
        if p14:
          pops[2014] = p14
        if p21:
          pops[2021] = p21
        if not pops:
          continue
        forms = expand_name_forms(c0, [c1])
        # Merge directly into by_adm[cur_adm] if matching by name+scale, else append
        matched = False
        for rec in by_adm[cur_adm]:
          if (rec["forms"] & forms) and status_compatible(rec["status"], detect_status(c0)):
            r01 = rec["pops"].get(2001)
            if r01 and p01 and max(r01, p01) / max(1, min(r01, p01)) > 2.5:
              continue
            rec["pops"].update(pops)
            matched = True
            break
        if not matched:
          by_adm[cur_adm].append({
            "adm1": cur_adm, "name": clean_settlement_label(c1), "name_cyr": clean_settlement_label(c0),
            "forms": forms, "status": detect_status(c0), "rada": "", "pops": pops,
          })

  # Safely link ukraine-census-pres (1989, 2001) with ukraine-estimation-pres (2021, 2022)
  linked_ua = []
  for adm1 in sorted(set(by_adm) | set(est_by_adm)):
    base_list = by_adm.get(adm1, [])
    est_list = est_by_adm.get(adm1, [])
    used_est = set()
    for b in base_list:
      ref_p = b["pops"].get(2001) or b["pops"].get(1989) or 1
      best_i = None
      best_sc = -999.0
      for idx, e in enumerate(est_list):
        if idx in used_est:
          continue
        if not (b["forms"] & e["forms"]):
          continue
        if not status_compatible(b["status"], e["status"]):
          continue
        ep = e["pops"].get(2021) or e["pops"].get(2022) or 1
        ratio = max(ref_p, ep) / max(1, min(ref_p, ep))
        if max(ref_p, ep) >= 1000 and ratio > 3.5:
          continue
        if ratio > 5.0:
          continue
        same_st = 1.0 if b["status"] == e["status"] else 0.0
        rada_sim = 0.5 if (b["rada"] and e["tg"] and b["rada"][:5] in e["tg"]) else 0.0
        sc = same_st + rada_sim - abs(math.log(max(ref_p, ep) / max(1, min(ref_p, ep))))
        if sc > best_sc:
          best_sc = sc
          best_i = idx
      if best_i is not None:
        used_est.add(best_i)
        b["pops"].update(est_list[best_i]["pops"])
      linked_ua.append(b)
    for idx, e in enumerate(est_list):
      if idx not in used_est:
        linked_ua.append({
          "adm1": adm1, "name": e["name"], "name_cyr": e["name_cyr"],
          "forms": e["forms"], "status": e["status"], "rada": e["tg"], "pops": e["pops"],
        })
  print(f"Linked Ukraine 1989/2001/2014/2021/2022 settlements: {len(linked_ua)}")
  return linked_ua


def parse_belarus_modern_censuses():
  by_adm = defaultdict(list)
  for dname, y0, y1 in [("belarus-census-2009", 1999, 2009), ("belarus-census-2019", 2009, 2019)]:
    dp = os.path.join(MASHKE_DIR, dname)
    if not os.path.isdir(dp):
      continue
    for fn in sorted(os.listdir(dp)):
      if not fn.endswith(".htm") or fn == "index.htm":
        continue
      adm1 = BY_FILE_TO_ADMIN1.get(fn[:-4])
      if not adm1 or adm1 == "BY.04":
        continue
      cur_raion = ""
      with open(os.path.join(dp, fn), encoding="utf-8", errors="replace") as fh:
        for line in fh:
          s = line.strip()
          if not s.startswith("<tr>"):
            continue
          parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
          if "<th" in s and "<td" not in s:
            cur_raion = strip_tags(parts[0])
            continue
          if "<td" not in s or len(parts) < 4:
            continue
          raw_c0 = parts[0]
          if "<i>" in raw_c0[:25]:
            continue
          c0 = strip_tags(raw_c0)
          c1 = strip_tags(parts[1])
          if re.search(r"(?:район|сельсовет|население|городское|сельское|горсовет|поссовет)", c0, re.I):
            continue
          p0 = parse_int_num(parts[2])
          p1 = parse_int_num(parts[3])
          if not p0 and not p1:
            continue
          st = detect_status(c0)
          forms = expand_name_forms(c0, [c1])
          matched = False
          for rec in by_adm[adm1]:
            if (rec["forms"] & forms) and status_compatible(rec["status"], st):
              rp = next(iter(rec["pops"].values()))
              np = p1 or p0
              if max(rp, np) / max(1, min(rp, np)) <= 3.0:
                if p0 and y0 not in rec["pops"]:
                  rec["pops"][y0] = p0
                if p1:
                  rec["pops"][y1] = p1
                matched = True
                break
          if not matched:
            pops = {}
            if p0:
              pops[y0] = p0
            if p1:
              pops[y1] = p1
            by_adm[adm1].append({
              "adm1": adm1, "name": clean_settlement_label(c0), "forms": forms,
              "status": st, "raion": norm_cyr(cur_raion), "pops": pops,
            })
  res = [r for lst in by_adm.values() for r in lst]
  print(f"Linked Belarus 1999/2009/2019 settlements: {len(res)}")
  return res


# ---------------------------------------------------------------------------
# 1897 Census Parsers (Mashke 38 Govs + Counties/Cities + ESBE + Troynitsky 1905)
# ---------------------------------------------------------------------------


def parse_empire_1897_mashke():
  out = []
  d = os.path.join(MASHKE_DIR, "empire-census-1897-religion")
  if os.path.isdir(d):
    for fn in sorted(os.listdir(d)):
      if not fn.endswith(".htm") or fn == "total.htm":
        continue
      cur_gov = ""
      cur_uezd = ""
      with open(os.path.join(d, fn), encoding="utf-8", errors="replace") as fh:
        for line in fh:
          s = line.strip()
          if not s.startswith("<tr>"):
            continue
          parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
          if "<th" in s and "<td" not in s:
            txt = strip_tags(parts[0])
            if "губерн" in txt.lower() or "област" in txt.lower():
              cur_gov = txt
            elif "уезд" in txt.lower() or "округ" in txt.lower() or "отдел" in txt.lower():
              cur_uezd = txt
            continue
          if "<td" not in s or len(parts) < 2:
            continue
          c0 = strip_tags(parts[0])
          if "прочее" in c0.lower() or "итого" in c0.lower():
            continue
          pop = parse_int_num(parts[1])
          if not pop or pop < 500:
            continue
          is_urban = "<b>" in parts[0][:25] or bool(re.search(r",\s*(?:губ\.?\s*г|у\.?\s*г|з\.?\s*г|б\.?\s*г|псд|м\.|м-ко)", c0, re.I))
          out.append({
            "gov": cur_gov, "uezd": cur_uezd, "raw": c0,
            "name": clean_settlement_label(c0), "pop": pop,
            "is_urban": is_urban, "forms": expand_name_forms(c0), "tier": 1,
          })

  # Also add all statutory cities from empire1897-lang-counties-cities.htm (covers ALL 89 governorates)
  cc_fp = os.path.join(MASHKE_DIR, "empire1897-lang-counties-cities.htm")
  if os.path.exists(cc_fp):
    cur_gov = ""
    with open(cc_fp, encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s.startswith("<tr>"):
          continue
        parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
        if "<th" in s and "<td" not in s:
          txt = strip_tags(parts[0])
          if "губерн" in txt.lower() or "област" in txt.lower():
            cur_gov = txt
          continue
        if "<td" not in s or len(parts) < 2:
          continue
        # Statutory cities are linked with <a>г. ... or contain г./посад/крепость and skip summary/прочее
        c0 = strip_tags(parts[0])
        if "<b>" in parts[0][:25] or "прочее" in c0.lower():
          continue
        if "без " in c0.lower() or "итого" in c0.lower():
          continue
        if not re.match(r"^(?:г\.|пос\.|крепост|м\.|слоб)", c0.strip().lower()):
          continue
        pop = parse_int_num(parts[1])
        if not pop or pop < 300:
          continue
        # Exclude Central Asia / Transcaucasia
        gl = cur_gov.lower()
        if any(x in gl for x in ["акмолин", "семипалат", "семиреч", "сыр-дарь", "самарканд", "ферган", "закаспий", "тургай", "уральск", "бакин", "елизаветпол", "елисаветпол", "карс", "кутаис", "тифлис", "эриван", "батум"]):
          continue
        out.append({
          "gov": cur_gov, "uezd": "", "raw": c0,
          "name": clean_settlement_label(c0), "pop": pop,
          "is_urban": True, "forms": expand_name_forms(c0), "tier": 1,
        })

  print(f"Parsed Mashke 1897 proofread settlements: {len(out)}")
  return out


def parse_esbe_1897():
  fp = os.path.join(CACHE_DIR, "esbe_1897.json")
  if not os.path.exists(fp):
    return []
  with open(fp, encoding="utf-8") as fh:
    txt = json.load(fh).get("wikitext", "")
  out = []
  for row in txt.split("|-"):
    cells = [c.strip() for c in row.split("||")]
    if len(cells) < 3:
      continue
    nm_raw = cells[0].lstrip("| ").replace("''", "").strip()
    gov_raw = cells[1].replace("''", "").strip()
    pop_raw = cells[2].replace("''", "").strip()
    m_p = re.search(r"(\d[\d\s]*)", pop_raw)
    if not m_p:
      continue
    pop = int(re.sub(r"\s+", "", m_p.group(1)))
    if pop < 400:
      continue
    gl = gov_raw.lower()
    if any(x in gl for x in ["акмол", "семип", "семир", "сыр-", "самарк", "ферган", "закасп", "тургай", "уральск", "бакин", "елизав", "елисав", "карс", "кутаис", "тифлис", "эриван"]):
      continue
    out.append({
      "gov": gov_raw, "uezd": "", "raw": nm_raw,
      "name": clean_settlement_label(nm_raw), "pop": pop,
      "is_urban": True, "forms": expand_name_forms(nm_raw), "tier": 2,
    })
  print(f"Parsed ESBE 1897 settlements: {len(out)}")
  return out


def _nasmesta_rel_sum(block_text):
  """Extracts sum of religious denomination counts inside a Troynitsky 1905 settlement text block."""
  # Religion tags in nasmesta: Прв., Стар., Кат., Прт., Лют., Рф., Мгм., Евр., Іуд., Буд., Бд., Арм., Крм., Инд., Инов., Без.
  tags = re.findall(
    r"(?:Прв|Стар|Кат|Прт|Лют|Рф|Мгм|Маг|Евр|Іуд|Иуд|Арм|Бд|Буд|Крм|Яз|Инд)[.,\s]*(?:\([^)]{1,20}\)\s*)?(\d(?:[\s.]?\d{3}|\d)*)",
    block_text,
  )
  tot = 0
  for t in tags:
    val = int(re.sub(r"[\s.]", "", t))
    if 1 <= val <= 500000:
      tot += val
  return tot


def parse_nasmesta_1897():
  """
  Parses Troynitsky 1905 (nasmesta_djvu.txt) across all POLARIS governorates, matching sequential
  or column-aligned M+F=Total triples against religion sums, and falling back to verified rel_sum >= 500.
  """
  fp = os.path.join(CACHE_DIR, "nasmesta_djvu.txt")
  if not os.path.exists(fp):
    return []
  with open(fp, encoding="utf-8") as fh:
    lines = fh.read().splitlines()

  # Identify governorate section boundaries (stop at Акмолинская line ~303421)
  excl_govs = ("акмолин", "закаспий", "самарканд", "семипалат", "семиреч", "сыр", "тургай", "уральск", "ферган",
               "бакин", "елисаветп", "карс", "кутаис", "тифлис", "эриван", "батум")
  gov_pat = re.compile(r"(губерния|область|остров сахалин)", re.I)
  sections = []
  for i, l in enumerate(lines):
    if i < 2500:
      continue
    s = norm_cyr(l.strip())
    if len(s) < 65 and "," not in s and gov_pat.search(s):
      if any(x in s for x in ["сокращения", "число", "пространство", "итого", "всего"]):
        continue
      # Map mangled Саратовская OCR header "0м|ттовская" around 165358
      if "ттовская" in s or "товская" in s:
        s = "саратовская губерния"
      sections.append((i, s))

  # Entry start pattern: "<Name>, <type>. <uezd>..." (e.g. "Авдѣевка, с. Бхмт. Прв. 4 526.")
  entry_start_re = re.compile(
    r"^([А-ЯѢІѲѴЁ][а-яѣіѳѵёА-ЯѢІѲѴЁ\-\s\(\)\./'\"`]+?),\s*(г\.|г\b|м\.|м-ко|мст\.?|с\.|д\.|слб\.?|сл\.|слц\.?|ст-ца|ст\.|пслк\.?|пос\.?|псд\.?|х\.|хт\.?|аул|клн\.?|звд\.?|манф\.?|вслк\.?|уч\.?)\s+(.+)$"
  )
  num_line_re = re.compile(r"^[\d][\d.\s]{0,10}$")

  out = []
  for idx, (st_line, gov_name) in enumerate(sections):
    if any(ex in gov_name for ex in excl_govs):
      continue
    end_line = sections[idx + 1][0] if idx + 1 < len(sections) else len(lines)
    if "акмолин" in gov_name:
      break
    # Collect sequential entry text blocks and floating number tokens within this governorate
    i = st_line + 1
    entries = []
    cur_text = ""
    num_tokens = []

    def parse_djvu_num(tok):
      clean = re.sub(r"[\s.]", "", tok)
      return int(clean) if clean.isdigit() else None

    pending = []
    while i < end_line:
      raw = lines[i].strip()
      i += 1
      if not raw or raw.startswith("Сокращен"):
        continue
      if raw in ("М.", "Ж.", "ОБ. П.", "Л.", "М", "Ж"):
        continue
      # Check if line has trailing M F Total inline (like Voronezh: "Айдарова, д. Врнж. Прв. 765 . 368 397 765")
      m_inline = re.search(r"(.+?)\s+(\d[\d.]*)\s+(\d[\d.]*)\s+(\d[\d.]*)$", raw)
      if m_inline:
        n1, n2, n3 = parse_djvu_num(m_inline.group(2)), parse_djvu_num(m_inline.group(3)), parse_djvu_num(m_inline.group(4))
        if n1 and n2 and n3 and abs(n1 + n2 - n3) <= 2 and n3 >= 450:
          raw_prefix = m_inline.group(1).strip()
          if cur_text and not entry_start_re.match(raw_prefix):
            cur_text += " " + raw_prefix
            pending.append({"text": cur_text, "total": n3})
            cur_text = ""
          elif entry_start_re.match(raw_prefix):
            if cur_text:
              pending.append({"text": cur_text, "total": None})
            pending.append({"text": raw_prefix, "total": n3})
            cur_text = ""
          continue

      if num_line_re.match(raw):
        v = parse_djvu_num(raw)
        if v:
          num_tokens.append(v)
          # When 3 recent numbers form M + F = T, attach to most recent unresolved entry in pending window!
          if len(num_tokens) >= 3:
            a, b, c = num_tokens[-3], num_tokens[-2], num_tokens[-1]
            if a >= 100 and b >= 100 and c >= 450 and abs(a + b - c) <= 3:
              # Try attaching to closest prior unresolved entry whose rel_sum fits
              for pe in reversed(pending[-8:]):
                if pe["total"] is None:
                  rs = pe.get("rel_sum") or _nasmesta_rel_sum(pe["text"])
                  pe["rel_sum"] = rs
                  if rs == 0 or (c >= rs * 0.92 and c <= max(1200, rs * 1.65)):
                    pe["total"] = c
                    num_tokens = []
                    break
        continue

      if entry_start_re.match(raw):
        if cur_text:
          pending.append({"text": cur_text, "total": None})
        cur_text = raw
      elif cur_text and len(cur_text) < 260:
        cur_text += " " + raw

    if cur_text:
      pending.append({"text": cur_text, "total": None})

    for pe in pending:
      m = entry_start_re.match(pe["text"])
      if not m:
        continue
      raw_name = m.group(1).strip()
      stype = m.group(2).strip()
      rel_sum = pe.get("rel_sum") or _nasmesta_rel_sum(pe["text"])
      pop = pe["total"] if pe["total"] else (rel_sum if rel_sum >= 500 else None)
      if not pop or pop < 500:
        continue
      nm_cyr = clean_settlement_label(raw_name)
      if len(nm_cyr) < 2:
        continue
      is_urb = bool(re.match(r"^(?:г|м|м-ко|мст|псд|слб|сл|звд)", stype.lower()))
      out.append({
        "gov": gov_name, "uezd": "", "raw": f"{raw_name}, {stype}",
        "name": nm_cyr, "pop": pop,
        "is_urban": is_urb, "forms": expand_name_forms(raw_name), "tier": 3,
      })

  print(f"Parsed Troynitsky nasmesta_djvu.txt verified 500+ settlements: {len(out)}")
  return out


# ---------------------------------------------------------------------------
# 1920, 1926, 1939 & Interwar Censuses
# ---------------------------------------------------------------------------


def parse_1920_urban_and_volosts():
  """Parses russia1920-counties-cities.htm + regional 1920 files for urban settlements."""
  out = []
  p = os.path.join(MASHKE_DIR, "ussr-historic-partial", "russia1920-counties-cities.htm")
  if os.path.exists(p):
    cur_gov = ""
    with open(p, encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s.startswith("<tr>"):
          continue
        parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
        if "<th" in s and "<td" not in s:
          continue
        c0 = strip_tags(parts[0])
        if "губерн" in c0.lower() or "област" in c0.lower() or "коммуна" in c0.lower():
          cur_gov = c0
          continue
        if len(parts) < 4:
          continue
        if any(x in c0.lower() for x in ["уезд", "район", "уточн", "прочие", "волост", "итого"]):
          continue
        p_urb = parse_int_num(parts[3]) or parse_int_num(parts[1])
        if p_urb and p_urb >= 300:
          out.append({
            "gov": cur_gov, "name": clean_settlement_label(c0),
            "pop": p_urb, "year": 1920, "forms": expand_name_forms(c0),
          })
  # Ukraine 1920 ethnic/town pages
  up_dir = os.path.join(MASHKE_DIR, "ussr-historic-partial")
  for fn in sorted(os.listdir(up_dir)):
    if not fn.startswith("ukraine1920-ethnic-comm") and not fn.startswith("russia1920-ethnic"):
      continue
    cur_gov = fn
    with open(os.path.join(up_dir, fn), encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s.startswith("<tr>") or "<td" not in s:
          continue
        parts = re.split(r"<td[^>]*>", s)[1:]
        if len(parts) < 2:
          continue
        c0 = strip_tags(parts[0])
        if not re.match(r"^(?:г\.|м\.|пгт|сл\.|пос\.)", c0.lower()):
          continue
        pop = parse_int_num(parts[1])
        if pop and pop >= 300:
          out.append({
            "gov": cur_gov, "name": clean_settlement_label(c0),
            "pop": pop, "year": 1920, "forms": expand_name_forms(c0),
          })
  print(f"Parsed 1920 census towns: {len(out)}")
  return out


def parse_1926_and_1939():
  """Parses all 19 ussr-ethnic1926-*.htm urban settlements and 1939 districts/urban/rt towns."""
  obs26 = []
  for fn in sorted(os.listdir(MASHKE_DIR)):
    if not fn.startswith("ussr-ethnic1926-") or not fn.endswith(".htm"):
      continue
    reg_file = fn[len("ussr-ethnic1926-"):-4]
    cur_okrug = ""
    with open(os.path.join(MASHKE_DIR, fn), encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s.startswith("<tr>"):
          continue
        parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
        if "<th" in s and "<td" not in s:
          cur_okrug = strip_tags(parts[0])
          continue
        if "<td" not in s or len(parts) < 2:
          continue
        raw_c0 = parts[0]
        if "<i>" in raw_c0[:25]:
          continue
        c0 = strip_tags(raw_c0)
        if re.search(r"(?:район|округ|поселения|итого|прочее|без\s+)", c0, re.I):
          continue
        pop = parse_int_num(parts[1])
        if not pop or pop < 300:
          continue
        is_linked = "<a>" in raw_c0[:25] or bool(re.match(r"^(?:г\.|пгт|п\.)", c0.lower()))
        if not is_linked:
          continue
        obs26.append({
          "scope": reg_file + " " + cur_okrug, "raw": c0,
          "name": clean_settlement_label(c0), "pop": pop,
          "forms": expand_name_forms(c0), "year": 1926, "is_urban": True,
        })

  obs39 = []
  p39 = os.path.join(MASHKE_DIR, "ussr-ethnic1939-districts.htm")
  if os.path.exists(p39):
    cur_rep = ""
    cur_obl = ""
    keep_rep = False
    with open(p39, encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s.startswith("<tr>"):
          continue
        parts = re.split(r"<th[^>]*>|<td[^>]*>", s)[1:]
        if "<th" in s and "<td" not in s:
          hdr = strip_tags(parts[0])
          if "сср" in hdr.lower() and "асср" not in hdr.lower():
            cur_rep = hdr
            keep_rep = any(x in cur_rep.lower() for x in ["российская", "украинская", "белорусская"])
          else:
            cur_obl = hdr
          continue
        if not keep_rep or "<td" not in s or len(parts) < 2:
          continue
        raw_c0 = parts[0]
        if "<i>" in raw_c0[:25]:
          continue
        c0 = strip_tags(raw_c0)
        # Keep ONLY explicit towns/pgts (г., пгт, рп, п.) or "(рц)" rural district centres!
        is_town = bool(re.match(r"^(?:<b>)?\s*(?:г\.|пгт|рп|кп|п\.)", c0.lower()))
        is_rc = "(рц)" in c0.lower()
        if not (is_town or is_rc):
          continue
        if "г. и пгт" in c0.lower() or "горсовет" in c0.lower() or "село" in c0.lower() and not is_rc:
          continue
        # Avoid duplicate bold summary row "<b>г. Барнаул</b>" when followed by identical "г. Барнаул"
        pop = parse_int_num(parts[1])
        if not pop or pop < 300:
          continue
        obs39.append({
          "scope": cur_obl, "raw": c0,
          "name": clean_settlement_label(c0), "pop": pop,
          "forms": expand_name_forms(c0), "year": 1939,
          "is_town": is_town,
        })

  print(f"Parsed 1926 towns: {len(obs26)}, 1939 towns/rc: {len(obs39)}")
  return obs26, obs39


def parse_poland_baltics_finland():
  """Parses interwar/pre-1920 tables for Poland, Finland, Estonia, Latvia."""
  extra = defaultdict(dict)  # (country, norm_lat) -> {yr: pop}
  # Poland 1921/1931
  p_pl = os.path.join(MASHKE_DIR, "poland-comm1931.htm")
  if os.path.exists(p_pl):
    with open(p_pl, encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s.startswith("<tr>") or "<td" not in s or "<i>" in s[:40]:
          continue
        parts = re.split(r"<td[^>]*>", s)[1:]
        if len(parts) < 3:
          continue
        c0 = strip_tags(parts[0])
        if "---" in c0 or c0.lower().startswith("m. ") and "warszawa" not in c0.lower():
          continue
        p21 = parse_int_num(parts[1])
        p31 = parse_int_num(parts[2])
        nl = norm_lat(c0)
        if p21 and nl:
          extra[("Poland", nl)][1921] = p21
          # also allow Belarus/Ukraine western oblast matching for former Eastern Poland!
          extra[("Belarus", nl)][1921] = p21
          extra[("Ukraine", nl)][1921] = p21
          extra[("Lithuania", nl)][1921] = p21
        if p31 and nl:
          extra[("Poland", nl)][1931] = p31
          extra[("Belarus", nl)][1931] = p31
          extra[("Ukraine", nl)][1931] = p31
          extra[("Lithuania", nl)][1931] = p31
  # Finland 1880..1920
  for yr in (1880, 1890, 1900, 1910, 1920):
    fp = os.path.join(MASHKE_DIR, f"finland-lang{yr}.htm")
    if not os.path.exists(fp):
      continue
    with open(fp, encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s.startswith("<tr>") or "<td" not in s:
          continue
        parts = re.split(r"<td[^>]*>", s)[1:]
        if len(parts) < 2:
          continue
        c0 = strip_tags(parts[0]).split("ynnä")[0].strip()
        pop = parse_int_num(parts[1])
        nl = norm_lat(c0)
        if pop and nl:
          extra[("Finland", nl)][yr] = pop
  # Estonia 1881, 1922 & Latvia 1920, 1925
  for fn, cn, yr in [("estonia-religion1881.htm", "Estonia", 1881), ("estonia-religion-comm1922.htm", "Estonia", 1922),
                     ("latvia-ethnic1920.htm", "Latvia", 1920), ("latvia-religion-comm1925.htm", "Latvia", 1925)]:
    fp = os.path.join(MASHKE_DIR, fn)
    if not os.path.exists(fp):
      continue
    with open(fp, encoding="utf-8", errors="replace") as fh:
      for line in fh:
        s = line.strip()
        if not s.startswith("<tr>") or "<td" not in s or "<i>" in s[:40]:
          continue
        parts = re.split(r"<td[^>]*>", s)[1:]
        if len(parts) < 2:
          continue
        c0 = strip_tags(parts[0])
        if re.search(r"(?:iecirknis|osa|vallad|kokku|total)", c0.lower()):
          continue
        pop = parse_int_num(parts[1])
        nl = norm_lat(c0)
        if pop and nl:
          extra[(cn, nl)][yr] = pop
  print(f"Parsed Poland/Finland/Baltic interwar extra series: {len(extra)}")
  return extra


# ---------------------------------------------------------------------------
# Master Registry Assembly
# ---------------------------------------------------------------------------


def main():
  polys = load_chapter_polygons()
  gn = GeoNamesIndex(polys["ch4"])
  inc_grid, pop_grid = load_wikidata_spatial()

  # Parse all primary censuses
  multi_cities = parse_mashke_multi_cities([
    ("russia-cities.htm", "Russia", True, True),
    ("ukraine-cities.htm", "Ukraine", True, True),
    ("belarus-cities.htm", "Belarus", True, True),
    ("poland-cities.htm", "Poland", False, True),
    ("estonia-cities.htm", "Estonia", False, False),
    ("latvia-cities.htm", "Latvia", False, False),
    ("lithuania-cities.htm", "Lithuania", False, True),
    ("moldova-cities.htm", "Moldova", False, False),
  ])
  ru_modern = parse_russia_modern_censuses()
  ua_modern = parse_ukraine_modern_censuses()
  by_modern = parse_belarus_modern_censuses()
  emp_mashke = parse_empire_1897_mashke()
  emp_esbe = parse_esbe_1897()
  emp_nasmesta = parse_nasmesta_1897()
  obs20 = parse_1920_urban_and_volosts()
  obs26, obs39 = parse_1926_and_1939()
  extra_interwar = parse_poland_baltics_finland()

  # -------------------------------------------------------------------------
  # Build Clean Registry Entries with Spatial Grid Deduplication
  # -------------------------------------------------------------------------
  registry = []  # list of dicts
  grid_idx = defaultdict(list)  # (int(lat*10), int(lng*10)) -> list of indices

  def is_claimed_conflict(lat, lng, country, cand_forms):
    gx, gy = int(math.floor(lat * 10)), int(math.floor(lng * 10))
    for dx in (-1, 0, 1):
      for dy in (-1, 0, 1):
        for ri in grid_idx.get((gx + dx, gy + dy), ()):
          ex = registry[ri]
          if ex["country"] == country and haversine_km((lat, lng), ex["coords"]) <= 1.5:
            if not (cand_forms & ex["forms"]):
              return True
    return False

  def add_or_merge_entry(name, country, coords, pops, other_names=None, found_yr=None,
                         merged_yr=None, priority=2, adm1=None, is_curated=False,
                         curated_regions=None, is_war_curated=False):
    lat, lng = round(float(coords[0]), 5), round(float(coords[1]), 5)
    if point_in_chapter(lat, lng, polys["ch4"]) is None:
      return None
    forms = expand_name_forms(name, other_names)
    gx, gy = int(math.floor(lat * 10)), int(math.floor(lng * 10))
    match_idx = None
    best_dist = 999.0
    for dx in (-1, 0, 1):
      for dy in (-1, 0, 1):
        for ri in grid_idx.get((gx + dx, gy + dy), ()):
          ex = registry[ri]
          if ex["country"] != country:
            continue
          d = haversine_km((lat, lng), ex["coords"])
          max_name_d = 6.0 if (ex["is_curated"] or is_curated) else 3.0
          if d > max_name_d:
            continue
          name_hit = bool(forms & ex["forms"])
          if name_hit and d <= max_name_d:
            ex_p = ex["pops"]
            overlap_compat = True
            checked_overlap = False
            skip_war_yr = (country == "Ukraine" and (ex["is_war_curated"] or is_war_curated))
            for yr, val in pops.items():
              if skip_war_yr and yr >= 2022:
                continue
              if yr in ex_p and ex_p[yr] > 0 and val > 0:
                checked_overlap = True
                if max(val, ex_p[yr]) / max(1, min(val, ex_p[yr])) > 3.2:
                  overlap_compat = False
                  break
            if overlap_compat and not checked_overlap and pops and ex_p:
              # Compare closest pre-2022 pair to block merging tiny villages into cities across nearby census years!
              cand_yrs = [y for y in pops if not (skip_war_yr and y >= 2022)]
              ex_yrs = [y for y in ex_p if not (skip_war_yr and y >= 2022)]
              if cand_yrs and ex_yrs:
                best_pair = min(((abs(y1 - y2), y1, y2) for y1 in cand_yrs for y2 in ex_yrs))
                gap, cy, ey = best_pair
                max_r = 4.2 if gap <= 25 else 8.0
                if max(pops[cy], ex_p[ey]) / max(1, min(pops[cy], ex_p[ey])) > max_r:
                  overlap_compat = False
            if overlap_compat and d < best_dist:
              best_dist = d
              match_idx = ri
          elif d <= 0.6 and not (ex["is_war_curated"] and is_war_curated):
            # Merge co-located same-country entries ONLY if compatible pre-2022 scale (<= 3.5x)
            ex_p = ex["pops"]
            compat_coloc = True
            if pops and ex_p:
              cand_yrs = [y for y in pops if y < 2022]
              ex_yrs = [y for y in ex_p if y < 2022]
              if cand_yrs and ex_yrs:
                best_pair = min(((abs(y1 - y2), y1, y2) for y1 in cand_yrs for y2 in ex_yrs))
                if max(pops[best_pair[1]], ex_p[best_pair[2]]) / max(1, min(pops[best_pair[1]], ex_p[best_pair[2]])) > 3.5:
                  compat_coloc = False
            if compat_coloc and d < best_dist:
              best_dist = d
              match_idx = ri

    if match_idx is None:
      # Hard 1-to-1 coordinate uniqueness: never stack two distinct same-country settlements <= 1.5 km
      for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
          for ri in grid_idx.get((gx + dx, gy + dy), ()):
            ex = registry[ri]
            if ex["country"] == country and haversine_km((lat, lng), ex["coords"]) <= 1.5:
              return None

    if match_idx is not None:
      ex = registry[match_idx]
      for yr, val in pops.items():
        y_int = int(yr)
        if val > 0:
          if y_int not in ex["pops"] or priority > ex["pop_prio"].get(y_int, -1):
            ex["pops"][y_int] = int(round(val))
            ex["pop_prio"][y_int] = priority
      if other_names:
        for a in other_names:
          if a and a not in ex["other_names"]:
            ex["other_names"].append(a)
      ex["forms"].update(forms)
      if found_yr and (not ex["found_yr"] or found_yr < ex["found_yr"]):
        ex["found_yr"] = found_yr
      if merged_yr:
        ex["merged_yr"] = merged_yr if not ex["merged_yr"] else min(ex["merged_yr"], merged_yr)
      if adm1 and not ex["adm1"]:
        ex["adm1"] = adm1
      if curated_regions:
        ex["curated_regions"].update(curated_regions)
      if is_curated:
        ex["is_curated"] = True
      if is_war_curated:
        ex["is_war_curated"] = True
      return match_idx

    idx = len(registry)
    onames = []
    for a in (other_names or []):
      if a and a != name and a not in onames:
        onames.append(a)
    rec = {
      "name": name,
      "country": country,
      "coords": [lat, lng],
      "pops": {int(k): int(round(v)) for k, v in pops.items() if v and v > 0},
      "pop_prio": {int(k): priority for k, v in pops.items() if v and v > 0},
      "other_names": onames,
      "forms": forms,
      "found_yr": found_yr,
      "merged_yr": merged_yr,
      "adm1": adm1,
      "is_curated": is_curated,
      "is_war_curated": is_war_curated,
      "curated_regions": dict(curated_regions or {}),
    }
    registry.append(rec)
    grid_idx[(gx, gy)].append(idx)
    return idx

  # --- Phase A: Ingest all hand-curated regional benchmarks & Ch4-7 borderlands (idempotent snapshot) ---
  ch_specs = [
    (4, "4.imperial_russia_post_1815/imperial_russia_post_1815_settlements.json"),
    (5, "5.russian_civil_war/russian_civil_war_settlements.json"),
    (6, "6.soviet_lenin_stalin/soviet_lenin_stalin_settlements.json"),
    (7, "7.soviet_post_stalin/soviet_post_stalin_settlements.json"),
    (8, "8.post_soviet_space/post_soviet_space_settlements.json"),
    (9, "9.russian_invasion_of_ukraine/russian_invasion_of_ukraine_settlements.json"),
  ]
  if os.path.exists(BASELINE_A_PATH):
    with open(BASELINE_A_PATH, encoding="utf-8") as fh:
      base_entries = json.load(fh)
    for b in base_entries:
      pops_int = {int(k): int(v) for k, v in b.get("pops", {}).items() if v and int(v) > 0}
      prio_val = 5 if b.get("is_curated") else 4
      cregs = {int(k): v for k, v in b.get("curated_regions", {}).items()}
      lat, lng = round(float(b["coords"][0]), 5), round(float(b["coords"][1]), 5)
      rec = {
        "name": b["name"],
        "country": b["country"],
        "coords": [lat, lng],
        "pops": pops_int,
        "pop_prio": {y: prio_val for y in pops_int},
        "other_names": list(b.get("other_names", [])),
        "forms": set(b.get("forms", [])) | expand_name_forms(b["name"], b.get("other_names", [])),
        "found_yr": b.get("found_yr"),
        "merged_yr": b.get("merged_yr"),
        "adm1": b.get("adm1"),
        "is_curated": bool(b.get("is_curated")),
        "is_war_curated": bool(b.get("is_war_curated")),
        "curated_regions": cregs,
      }
      idx = len(registry)
      registry.append(rec)
      grid_idx[(int(math.floor(lat * 10)), int(math.floor(lng * 10)))].append(idx)
    print(f"After Phase A (loaded snapshot {len(registry)} benchmarks)")
  else:
    for ch_num, rel_p in ch_specs:
      with open(os.path.join(ENTIRE_DIR, rel_p), encoding="utf-8") as fh:
        data = json.load(fh)
      for k, v in data.items():
        reg = v.get("region")
        ct = v.get("country")
        is_ext_border = (ch_num <= 7 and ct in ("Poland", "Finland", "Estonia", "Latvia", "Lithuania", "Moldova"))
        if not reg and not is_ext_border:
          continue
        coords = v.get("coords")
        pops = {int(y): val for y, val in v.get("population", {}).items() if val and val > 0}
        if not coords or not pops:
          continue
        is_war_cur = (ch_num == 9 and ct == "Ukraine" and any(y >= 2023 for y in pops))
        add_or_merge_entry(
          name=v.get("name", k.split("-")[0]),
          country=ct,
          coords=coords,
          pops=pops,
          other_names=v.get("other_names", []),
          found_yr=v.get("found.yr"),
          priority=5 if reg else 4,
          is_curated=bool(reg),
          curated_regions={ch_num: reg} if reg else {},
          is_war_curated=is_war_cur,
        )
    print(f"After Phase A (curated Ch4-9 benchmarks): {len(registry)} settlements")

  # --- Phase B: Ingest *-cities.htm statutory urban series (Russia, Ukraine, Belarus, Baltics/Poland/Moldova) ---
  for row in multi_cities:
    cn = row["country"]
    # Keep RU/UA/BY exhaustively; for PL/EE/LV/LT/MD only merge/enrich existing Ch4-7 benchmarks so scope stays clean
    subj = row["subject"]
    adm1 = None
    sl = subj.lower()
    for k, v in SUBJECT_TO_ADMIN1.items():
      if k in sl:
        adm1 = v
        break
    if not adm1 and cn == "Russia":
      for rfn, radm in RU_FILE_TO_ADMIN1.items():
        if rfn[:6] in sl:
          adm1 = radm
          break
    # Match to GeoNames
    hit = gn.lookup(row["name_cyr"], country=cn, admin1=adm1, aliases=[row["name_lat"]] + row["aliases"], claimed_fn=is_claimed_conflict)
    if not hit:
      hit = gn.lookup(row["name_lat"], country=cn, admin1=adm1, aliases=row["aliases"], claimed_fn=is_claimed_conflict)
    if not hit:
      continue
    lat, lng, _, g_adm1, gname, _ = hit
    if cn in ("Poland", "Finland", "Estonia", "Latvia", "Lithuania", "Moldova"):
      # Only enrich existing curated settlements in Ch4-7
      gx, gy = int(math.floor(lat * 10)), int(math.floor(lng * 10))
      near_cur = False
      for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
          for ri in grid_idx.get((gx + dx, gy + dy), ()):
            if haversine_km((lat, lng), registry[ri]["coords"]) <= 3.0:
              near_cur = True
              break
      if not near_cur:
        continue
    clean_nm = row["name_lat"].split("(")[0].strip()
    if cn == "Russia":
      # Use clean English translit from GeoNames asciiname/name or Mashke lat without backticks
      clean_nm = clean_settlement_label(gname) if re.match(r"^[A-Za-z\s\-']+$", gname) else clean_settlement_label(row["name_lat"])
    elif cn == "Ukraine":
      clean_nm = clean_settlement_label(row["name_cyr"])
      # Prefer GeoNames English translit if ASCII clean
      if re.match(r"^[A-Za-z\s\-']+$", gname):
        clean_nm = gname
      else:
        clean_nm = cyr_to_lat(row["name_cyr"]).title()
    elif cn == "Belarus":
      clean_nm = gname if re.match(r"^[A-Za-z\s\-']+$", gname) else cyr_to_lat(row["name_cyr"]).title()
    add_or_merge_entry(
      name=clean_nm,
      country=cn,
      coords=(lat, lng),
      pops=row["pops"],
      other_names=[row["name_cyr"], row["name_lat"]] + row["aliases"],
      found_yr=row["found_yr"],
      merged_yr=row["merged_yr"],
      priority=4,
      adm1=g_adm1,
    )
  print(f"After Phase B (*-cities.htm multi-census spine): {len(registry)} settlements")

  # --- Phase C: Ingest clean Russia 2002/2010/2021, Ukraine 1989/2001/2014/2021/2022, Belarus 1999/2009/2019 ---
  # Russia: all city/pgt + rural/other >= 4000
  for rec in ru_modern:
    peak = max(rec["pops"].values())
    if rec["status"] not in ("city", "pgt") and peak < 4000:
      continue
    hit = gn.lookup(rec["name"], country="Russia", admin1=rec["adm1"], claimed_fn=is_claimed_conflict)
    if not hit:
      continue
    lat, lng, _, g_adm1, gname, _ = hit
    nm = gname if re.match(r"^[A-Za-z\s\-']+$", gname) else cyr_to_lat(rec["name"]).title()
    add_or_merge_entry(
      name=nm, country="Russia", coords=(lat, lng), pops=rec["pops"],
      other_names=[rec["name"]], priority=3, adm1=g_adm1,
    )

  # Ukraine: all city/pgt + rural/other >= 3500
  for rec in ua_modern:
    peak = max(rec["pops"].values())
    if rec["status"] not in ("city", "pgt") and peak < 3500:
      continue
    hit = gn.lookup(rec["name_cyr"], country="Ukraine", admin1=rec["adm1"], aliases=[rec["name"]] + list(rec["forms"]), claimed_fn=is_claimed_conflict)
    if not hit:
      continue
    lat, lng, _, g_adm1, gname, _ = hit
    nm = gname if re.match(r"^[A-Za-z\s\-']+$", gname) else rec["name"]
    add_or_merge_entry(
      name=nm, country="Ukraine", coords=(lat, lng), pops=rec["pops"],
      other_names=[rec["name_cyr"], rec["name"]], priority=3, adm1=g_adm1,
    )

  # Belarus: all city/pgt + rural/other >= 3500
  for rec in by_modern:
    peak = max(rec["pops"].values())
    if rec["status"] not in ("city", "pgt") and peak < 3500:
      continue
    hit = gn.lookup(rec["name"], country="Belarus", admin1=rec["adm1"], aliases=list(rec["forms"]), claimed_fn=is_claimed_conflict)
    if not hit:
      continue
    lat, lng, _, g_adm1, gname, _ = hit
    nm = gname if re.match(r"^[A-Za-z\s\-']+$", gname) else cyr_to_lat(rec["name"]).title()
    add_or_merge_entry(
      name=nm, country="Belarus", coords=(lat, lng), pops=rec["pops"],
      other_names=[rec["name"]], priority=3, adm1=g_adm1,
    )
  print(f"After Phase C (clean modern RU/UA/BY link): {len(registry)} settlements")

  # --- Phase D: Index existing registry by (adm1, form) and spatial grid for fast 1897-1939 matching ---
  # First enrich adm1 if missing via GeoNames nearest match
  for r in registry:
    if not r["adm1"]:
      nh = gn.find_near_by_name(r["coords"][0], r["coords"][1], r["name"], r["other_names"], max_km=8.0)
      if nh:
        r["adm1"] = nh[3]

  form_to_idxs = defaultdict(list)
  for i, r in enumerate(registry):
    for f in r["forms"]:
      form_to_idxs[f].append(i)

  def match_registry_by_scope(forms, scope_str, country_hint=None):
    cand_idxs = set()
    for f in forms:
      cand_idxs.update(form_to_idxs.get(f, ()))
    if not cand_idxs:
      return None
    # Filter by spatial/country/governorate compatibility
    sc_low = norm_cyr(scope_str or "")
    target_scope = None
    for k, v in GOV_SPATIAL_SCOPE.items():
      if k in sc_low:
        target_scope = v
        break
    adm_hint = None
    for k, v in SUBJECT_TO_ADMIN1.items():
      if k in sc_low:
        adm_hint = v
        break
    scored = []
    for ci in cand_idxs:
      r = registry[ci]
      if country_hint and r["country"] != country_hint:
        continue
      if adm_hint and r["adm1"] and r["adm1"] != adm_hint:
        continue
      if target_scope:
        tc, tadm = target_scope
        adm = r["adm1"] or ""
        if adm and not (adm in tadm or any(adm.startswith(a) for a in tadm if a.endswith("."))):
          continue
      peak = max(r["pops"].values()) if r["pops"] else 0
      scored.append((1 if r["adm1"] else 0, peak, ci))
    if not scored:
      return None
    scored.sort(reverse=True)
    return scored[0][2]

  # Helper to check if an 1897/1926/1939 row matches reasonably by population scale
  def backfill_obs(obs_list, year, allow_add_thresh=None, source_tag=""):
    matched_n = 0
    added_n = 0
    for rec in obs_list:
      pop = rec["pop"]
      forms = rec["forms"]
      scope = rec.get("gov") or rec.get("scope") or ""
      ci = match_registry_by_scope(forms, scope)
      if ci is not None:
        r = registry[ci]
        # Skip if entry founded after this year AND this isn't an earlier founding proof!
        if r["found_yr"] and year < r["found_yr"] and year <= 1897:
          #Wait: if Troynitsky 1897 has >=1500 for it AND it's not a Soviet planned town, Wikidata P571 was just promotion year!
          if pop >= 1200 and (norm_lat(r["name"]), r["country"]) not in CURATED_FOUNDING:
            r["found_yr"] = None
          else:
            continue
        # Don't accidentally put huge city pop onto tiny village or vice versa
        if r["pops"]:
          earliest_val = r["pops"][min(r["pops"])]
          min_val = min(r["pops"].values())
          if (min_val < 500 and (pop / max(1, min_val)) > 8.0) or (
            max(earliest_val, pop) / max(1, min(earliest_val, pop)) > 15.0 and earliest_val < 2000
          ):
            # Avoid corrupting a tiny modern hamlet with a major 1897/1926 homonym!
            continue
        if year not in r["pops"]:
          r["pops"][year] = pop
          r["pop_prio"][year] = 3
          matched_n += 1
      elif allow_add_thresh is not None and ((rec.get("is_urban") and pop >= 2000) or pop >= allow_add_thresh):
        # Add standalone pre-Soviet / early Soviet settlement ONLY within RU/UA/BY (borderlands complete in Phase A)
        hit = gn.lookup_gov(rec["name"], scope, aliases=list(forms), claimed_fn=is_claimed_conflict)
        if not hit:
          continue
        lat, lng, cname, adm1, gname, gpop = hit
        if cname not in ("Russia", "Ukraine", "Belarus"):
          continue
        # Skip intra-federal-city municipal districts unless in explicit MERGED_OR_ABANDONED
        if adm1 in ("RU.48", "RU.66", "UA.12", "UA.20", "BY.04") and not any(
          (f, cname) in MERGED_OR_ABANDONED for f in forms
        ):
          continue
        nm = gname if re.match(r"^[A-Za-z\s\-']+$", gname) else cyr_to_lat(rec["name"]).title()
        pops_init = {year: pop}
        idx_added = add_or_merge_entry(
          name=nm, country=cname, coords=(lat, lng), pops=pops_init,
          other_names=[rec["name"]], priority=2, adm1=adm1,
        )
        if idx_added is not None:
          added_n += 1
    print(f"Backfilled {source_tag} ({year}): matched={matched_n}, added={added_n}")

  # Apply 1897 censuses in strict reliability order (Mashke HTML -> ESBE -> Troynitsky 1905)
  backfill_obs(emp_mashke, 1897, allow_add_thresh=3500, source_tag="Mashke 1897")
  backfill_obs(emp_esbe, 1897, allow_add_thresh=3500, source_tag="ESBE 1897")
  backfill_obs(emp_nasmesta, 1897, allow_add_thresh=3500, source_tag="Troynitsky 1905 (1897)")
  # Backfill 1920, 1926, 1939
  backfill_obs(obs20, 1920, allow_add_thresh=3500, source_tag="1920 Census")
  backfill_obs(obs26, 1926, allow_add_thresh=3500, source_tag="1926 Census")
  backfill_obs(obs39, 1939, allow_add_thresh=3500, source_tag="1939 Census")

  # Trace standalone 1897/1920/1926/1939 entries missing modern years forward into ru_modern/ua_modern/by_modern
  # Include GeoNames alternate Cyrillic/local forms on the exact matched coord so Russian->Ukrainian spellings match cleanly!
  fwd_hits = 0
  adm_ru_idx = defaultdict(list)
  for rec in ru_modern:
    adm_ru_idx[(rec["adm1"], rec["norm"])].append(rec)
  adm_ua_idx = defaultdict(list)
  for rec in ua_modern:
    for f in rec["forms"]:
      adm_ua_idx[(rec["adm1"], f)].append(rec)
  adm_by_idx = defaultdict(list)
  for rec in by_modern:
    for f in rec["forms"]:
      adm_by_idx[(rec["adm1"], f)].append(rec)

  used_modern_ids = set()

  def best_scale_forward_match(r, cands):
    if not r["pops"]:
      return None
    ry = max(r["pops"])
    rp = r["pops"][ry]
    best = None
    best_log = 999.0
    for mrec in cands:
      if id(mrec) in used_modern_ids:
        continue
      mpops = mrec.get("pops") or {}
      if not mpops:
        continue
      m_peak = max(mpops.values())
      if rp >= 1000 and m_peak < 150:
        continue
      my = min(mpops)
      mp = mpops[my]
      gap = abs(my - ry)
      if gap >= 60 and rp >= m_peak and m_peak >= 150:
        max_r = 12.0
      elif gap > 25:
        max_r = 5.5
      else:
        max_r = 3.5
      ratio = max(rp, mp) / max(1, min(rp, mp))
      if ratio > max_r:
        continue
      ld = abs(math.log(ratio))
      if ld < best_log:
        best_log = ld
        best = mrec
    return best

  for r in registry:
    gn_meta = gn.get_coord_meta(r["coords"][0], r["coords"][1])
    search_forms = set(r["forms"])
    if gn_meta:
      search_forms.update(gn_meta[2])
    if r["country"] == "Russia" and r["adm1"] and 2021 not in r["pops"] and not r["merged_yr"]:
      cands = [m for f in search_forms for m in adm_ru_idx.get((r["adm1"], f), ())]
      mrec = best_scale_forward_match(r, cands)
      if mrec:
        used_modern_ids.add(id(mrec))
        r["pops"].update({y: p for y, p in mrec["pops"].items() if y not in r["pops"]})
        fwd_hits += 1
    elif r["country"] == "Ukraine" and r["adm1"] and 2001 not in r["pops"] and not r["merged_yr"]:
      cands = [m for f in search_forms for m in adm_ua_idx.get((r["adm1"], f), ())]
      mrec = best_scale_forward_match(r, cands)
      if mrec:
        used_modern_ids.add(id(mrec))
        r["pops"].update({y: p for y, p in mrec["pops"].items() if y not in r["pops"]})
        fwd_hits += 1
    elif r["country"] == "Belarus" and r["adm1"] and 2019 not in r["pops"] and not r["merged_yr"]:
      cands = [m for f in search_forms for m in adm_by_idx.get((r["adm1"], f), ())]
      mrec = best_scale_forward_match(r, cands)
      if mrec:
        used_modern_ids.add(id(mrec))
        r["pops"].update({y: p for y, p in mrec["pops"].items() if y not in r["pops"]})
        fwd_hits += 1
  print(f"Forward-linked standalone historical entries to modern censuses: {fwd_hits}")

  # Extra interwar (Poland 1921/31, Finland 1880-1920, Baltics 1881/1920/22/25)
  for r in registry:
    cn = r["country"]
    for f in list(r["forms"]):
      ex_d = extra_interwar.get((cn, f))
      if ex_d:
        for y, p in ex_d.items():
          if y not in r["pops"]:
            r["pops"][y] = p
        break

  # --- Phase E: Apply Curated Foundings / Wikidata P571 & Pre-1975 Lapsed Mergers + Wikidata P1082 Backfill ---
  wd_pop_hits = 0
  for r in registry:
    lat, lng = r["coords"]
    nl = norm_lat(r["name"])
    # Check curated founding / merger maps first
    for f in [nl] + [norm_lat(x) for x in r["other_names"]]:
      if (f, r["country"]) in CURATED_FOUNDING:
        r["found_yr"] = CURATED_FOUNDING[(f, r["country"])]
        break
    for f in [nl] + [norm_lat(x) for x in r["other_names"]]:
      if (f, r["country"]) in MERGED_OR_ABANDONED:
        my = MERGED_OR_ABANDONED[(f, r["country"])]
        r["merged_yr"] = my if not r["merged_yr"] else min(r["merged_yr"], my)
        break

    # Spatial Wikidata lookup within <= 2.0 km
    gk_x, gk_y = int(math.floor(lat * 5)), int(math.floor(lng * 5))
    min_wd_inc = None
    for dx in (-1, 0, 1):
      for dy in (-1, 0, 1):
        for wlat, wlng, wyr, is_diss in inc_grid.get((gk_x + dx, gk_y + dy), ()):
          if haversine_km((lat, lng), (wlat, wlng)) <= 1.5:
            if not is_diss and 1898 <= wyr <= 2020:
              if min_wd_inc is None or wyr < min_wd_inc:
                min_wd_inc = wyr
        for wlat, wlng, wyr, wpop in pop_grid.get((gk_x + dx, gk_y + dy), ()):
          if haversine_km((lat, lng), (wlat, wlng)) <= 1.8 and 1880 <= wyr <= 1950 and 200 <= wpop <= 250000:
            if wyr not in r["pops"]:
              # Verify tight scale compatibility so admin-centre P1082 never corrupts towns
              near_v = [p for p in r["pops"].values() if p > 0]
              if near_v:
                ref_v = min(near_v)
                if max(wpop, ref_v) / max(1, min(wpop, ref_v)) > 3.0:
                  continue
              r["pops"][wyr] = wpop
              wd_pop_hits += 1

    # Check GeoNames coordinate metadata for PPLQ abandoned localities & modern anchor
    gn_meta = gn.get_coord_meta(lat, lng)
    g_fcode = gn_meta[0] if gn_meta else None
    g_pop = gn_meta[1] if gn_meta else 0
    if g_fcode == "PPLQ" and not r["is_curated"] and r["pops"]:
      my_pplq = max(r["pops"])
      r["merged_yr"] = my_pplq if not r["merged_yr"] else min(r["merged_yr"], my_pplq)

    # Mark ephemeral 1926-1989 Soviet resource camps cleanly without back-casting to 1897
    if r["pops"] and not r["is_curated"] and not r["merged_yr"] and not r["found_yr"]:
      min_ep, max_ep = min(r["pops"]), max(r["pops"])
      if min_ep >= 1926 and max_ep <= 1989 and g_pop == 0 and r["country"] in ("Russia", "Ukraine", "Belarus"):
        if max(r["pops"].values()) < 3000:
          r["pops"] = {}
        else:
          r["found_yr"] = min_ep
          r["merged_yr"] = max_ep

    # Honour Wikidata P571 founding year ONLY if no empirical record exists before min_wd_inc
    min_emp_yr = min(r["pops"]) if r["pops"] else 9999
    if r["found_yr"] is None and min_wd_inc is not None and min_emp_yr >= min_wd_inc:
      # Guard: in RU/UA/BY/EE/LV/LT/MD/PL/FI only trust modern founding if >= 1915 and no pre-founding record
      if min_wd_inc >= 1915 and 1897 not in r["pops"] and 1900 not in r["pops"]:
        r["found_yr"] = min_wd_inc

    # Strip any erroneous pre-founding keys
    if r["found_yr"]:
      fy = r["found_yr"]
      r["pops"] = {y: p for y, p in r["pops"].items() if y >= fy}
      # Ensure found_yr itself has an entry if first Census is just a few years later (up to 1974 or any year)
      if r["pops"] and fy not in r["pops"]:
        y0 = min(r["pops"])
        if 0 < (y0 - fy) <= 15:
          r["pops"][fy] = max(50, int(round(r["pops"][y0] * 0.35)))

    # Mark lapsed abandonments/mergers cleanly (<= 1989 for verified PPLQ / ephemeral camps or <= 1974 / 1986)
    if r["merged_yr"] and (r["merged_yr"] <= 1974 or r["merged_yr"] == 1986 or g_fcode == "PPLQ" or (r["found_yr"] and r["merged_yr"] <= 1989)):
      r["pops"] = {y: p for y, p in r["pops"].items() if y <= r["merged_yr"]}
      r["_raw_lapsed"] = True
    else:
      r["_raw_lapsed"] = False
  # Scrub isolated post-1953 homonym outlier points (e.g. 1989=1 next to 2021=1567)
  for r in registry:
    p = r["pops"]
    if len(p) >= 2 and not r.get("is_war_curated"):
      late = sorted((y, v) for y, v in p.items() if y >= 1953)
      if len(late) >= 2:
        med_late = sorted(v for _, v in late)[len(late) // 2]
        if med_late >= 500:
          bad_yrs = [y for y, v in late if v < 100 and (med_late / max(1, v)) >= 10.0]
          for y in bad_yrs:
            del p[y]
  registry = [r for r in registry if r["pops"] and (max(r["pops"].values()) >= 200 or r["is_curated"] or r["merged_yr"])]
  print(f"Applied founding/lapsed rules + Wikidata historical pops ({wd_pop_hits} points added)")

  # --- Phase F: Cohort-Calibrated Continuity Back-Cast to 1897 & Forward Continuity for Living RU/UA/BY ---
  def compute_cohort_ratio(y_early, y_late):
    by_c = defaultdict(list)
    by_adm = defaultdict(list)
    for r in registry:
      if r["found_yr"] and r["found_yr"] > y_early:
        continue
      p = r["pops"]
      if y_early in p and y_late in p and p[y_early] >= 100 and p[y_late] >= 100:
        ratio = min(1.5, max(0.20, p[y_early] / p[y_late]))
        by_c[r["country"]].append(ratio)
        if r["adm1"]:
          by_adm[r["adm1"]].append(ratio)
    med_c = {k: sorted(v)[len(v) // 2] for k, v in by_c.items() if v}
    med_a = {k: sorted(v)[len(v) // 2] for k, v in by_adm.items() if len(v) >= 5}
    return med_a, med_c

  def compute_forward_cohort_ratio(y_early, y_late):
    by_c = defaultdict(list)
    by_adm = defaultdict(list)
    for r in registry:
      if r["is_curated"] or r.get("_raw_lapsed"):
        continue
      p = r["pops"]
      if y_early in p and y_late in p and p[y_early] >= 100 and p[y_late] >= 100:
        ratio = min(2.2, max(0.45, p[y_late] / p[y_early]))
        by_c[r["country"]].append(ratio)
        if r["adm1"]:
          by_adm[r["adm1"]].append(ratio)
    med_c = {k: sorted(v)[len(v) // 2] for k, v in by_c.items() if v}
    med_a = {k: sorted(v)[len(v) // 2] for k, v in by_adm.items() if len(v) >= 5}
    return med_a, med_c

  ratios_cache = {}
  for y_late, y_early in [
    (2002, 1989), (2001, 1989), (1989, 1970), (1970, 1959), (1959, 1939),
    (1939, 1926), (1926, 1920), (1920, 1914), (1926, 1897),
  ]:
    ratios_cache[(y_late, y_early)] = compute_cohort_ratio(y_early, y_late)

  fwd_milestones = [(1897, 1926), (1926, 1939), (1939, 1959), (1959, 1970), (1970, 1989), (1989, 2001), (1989, 2002), (2001, 2010), (2002, 2010), (2010, 2021), (2009, 2019), (2019, 2021)]
  fwd_ratios_cache = {(ye, yl): compute_forward_cohort_ratio(ye, yl) for ye, yl in fwd_milestones}

  backcast_count = 0
  fwdcast_count = 0
  for r in registry:
    p = r["pops"]
    if not p:
      continue
    start_target = r["found_yr"] if r["found_yr"] else 1897
    min_y = min(p)
    cn = r["country"]
    adm = r["adm1"]
    def get_ratio(yl, ye):
      ma, mc = ratios_cache.get((yl, ye), ({}, {}))
      if adm and adm in ma:
        return ma[adm]
      return mc.get(cn, 0.72 if ye < 1926 else 0.85)

    def get_fwd_ratio(ye, yl, default_val=1.02):
      ma, mc = fwd_ratios_cache.get((ye, yl), ({}, {}))
      if adm and adm in ma:
        return ma[adm]
      return mc.get(cn, default_val)

    if min_y > start_target:
      # Only back-cast up to 1897 (or found_yr) so pre-1897 settlements don't pop into existence at 1939/1959/1975
      if min(p) >= 1998 and start_target <= 1989:
        yl = min(p)
        val = max(120, int(round(p[yl] * (get_ratio(2001, 1989) if cn == "Ukraine" else get_ratio(2002, 1989)))))
        p[1989] = val
      if min(p) > 1959 and start_target <= 1959:
        y0 = min(p)
        factor = 1.0
        if y0 >= 1985:
          factor *= get_ratio(1989, 1970) * get_ratio(1970, 1959)
        elif y0 >= 1968:
          factor *= get_ratio(1970, 1959)
        p[1959] = max(100, int(round(p[y0] * factor)))
      if min(p) > 1939 and start_target <= 1939:
        y0 = min(p)
        p[1939] = max(90, int(round(p[y0] * get_ratio(1959, 1939))))
      if min(p) > 1926 and start_target <= 1926:
        y0 = min(p)
        p[1926] = max(80, int(round(p[y0] * get_ratio(1939, 1926))))
      if start_target <= 1897 and 1897 not in p:
        y0 = min(p)
        factor = get_ratio(1926, 1897) if y0 >= 1920 else (0.90 if y0 >= 1910 else 0.96)
        p[1897] = max(60, int(round(p[y0] * factor)))
        backcast_count += 1
      elif start_target > 1897 and min(p) > start_target:
        # Newly founded town between 1898 and 2015: initialise conservative founding-era anchor at found_yr
        y0 = min(p)
        span = max(1, y0 - start_target)
        p[start_target] = max(50, int(round(p[y0] * max(0.15, 1.0 - 0.04 * min(18, span)))))
        backcast_count += 1

    # Forward continuity projection to 2021 for living non-lapsed RU/UA/BY settlements ending before 2021
    if cn in ("Russia", "Ukraine", "Belarus") and not r.get("_raw_lapsed") and max(p) < 2021:
      last_y = max(p)
      last_p = p[last_y]
      gn_m = gn.get_coord_meta(r["coords"][0], r["coords"][1])
      gpop_anchor = gn_m[1] if gn_m else 0
      # Step through milestone sequence toward 2021
      if last_y < 1926:
        p[1926] = max(50, int(round(p[max(p)] * get_fwd_ratio(1897, 1926, 1.08))))
      if max(p) < 1939:
        p[1939] = max(50, int(round(p[max(p)] * get_fwd_ratio(1926, 1939, 1.05))))
      if max(p) < 1959:
        p[1959] = max(50, int(round(p[max(p)] * get_fwd_ratio(1939, 1959, 0.95))))
      if max(p) < 1970:
        p[1970] = max(50, int(round(p[max(p)] * get_fwd_ratio(1959, 1970, 0.96))))
      if max(p) < 1989:
        p[1989] = max(50, int(round(p[max(p)] * get_fwd_ratio(1970, 1989, 0.94))))
      y_200x = 2001 if cn == "Ukraine" else (2009 if cn == "Belarus" else 2002)
      if max(p) < y_200x:
        if 100 <= gpop_anchor <= p[max(p)] * 3.0 and (p[max(p)] / max(1, gpop_anchor)) <= 10.0:
          p[y_200x] = max(50, int(round(0.65 * (p[max(p)] * get_fwd_ratio(1989, y_200x, 0.92)) + 0.35 * gpop_anchor)))
        else:
          p[y_200x] = max(50, int(round(p[max(p)] * get_fwd_ratio(1989, y_200x, 0.92))))
      if max(p) < 2021:
        y_prev = max(p)
        v_prev = p[y_prev]
        if y_prev < 2010 and cn != "Belarus":
          r_10 = get_fwd_ratio(2001 if cn == "Ukraine" else 2002, 2010, 0.95)
          v10 = max(40, int(round(v_prev * r_10)))
          if 100 <= gpop_anchor <= v_prev * 2.5 and (v_prev / max(1, gpop_anchor)) <= 8.0:
            v10 = max(40, int(round(0.5 * v10 + 0.5 * gpop_anchor)))
          p[2010] = v10
          y_prev = 2010
          v_prev = v10
        r_21 = get_fwd_ratio(2019 if cn == "Belarus" else 2010, 2021, 0.96)
        if y_prev > 2010 and y_prev < 2021 and cn != "Belarus":
          frac = (2021 - y_prev) / 11.0
          r_21 = r_21 ** frac
        p[2021] = max(40, int(round(v_prev * r_21)))
      fwdcast_count += 1

  # Bridge any missing 1914 / 1926 / 1953 / 1991 / 2021 boundary points ONLY inside empirical span
  print(f"Back-casted early continuity anchors for {backcast_count}, forward-projected living RU/UA/BY for {fwdcast_count}")

  # --- Phase G: Final Polish & Summary Diagnostics ---
  # Assign unique canonical keys "<CleanName>-<Country>" (disambiguating only genuine distinct homonyms >3km apart)
  used_keys = {}
  for r in registry:
    base_name = re.sub(r"[`]", "", r["name"]).strip()
    if not base_name or base_name == "0":
      base_name = "Settlement"
    r["name"] = base_name
    base_k = f"{base_name}-{r['country']}"
    if base_k not in used_keys:
      used_keys[base_k] = 1
      r["key"] = base_k
    else:
      used_keys[base_k] += 1
      adm_tag = (r["adm1"] or "reg").replace(".", "_")
      cand_k = f"{base_name}_{adm_tag}-{r['country']}"
      if cand_k in used_keys:
        idx = 2
        while f"{base_name}_{adm_tag}_{idx}-{r['country']}" in used_keys:
          idx += 1
        cand_k = f"{base_name}_{adm_tag}_{idx}-{r['country']}"
      used_keys[cand_k] = 1
      r["key"] = cand_k

  # Summary counts by country & year
  by_cn = defaultdict(int)
  c1897 = defaultdict(int)
  post75_jumps = []
  nonf_jumps = []
  for r in registry:
    by_cn[r["country"]] += 1
    if r["pops"] and min(r["pops"]) <= 1897:
      c1897[r["country"]] += 1
    pts = sorted(r["pops"].items())
    for (y0, p0), (y1, p1) in zip(pts, pts[1:]):
      ratio = max(p0, p1) / max(1, min(p0, p1))
      if y0 >= 1975 and not r.get("is_war_curated") and ratio >= 4.0:
        post75_jumps.append((ratio, r["key"], y0, p0, y1, p1))
      if not r.get("found_yr") and not r.get("is_war_curated") and ratio >= 10.0:
        nonf_jumps.append((ratio, r["key"], y0, p0, y1, p1))

  same_close_15 = 0
  chk_grid = defaultdict(list)
  for idx_r, r in enumerate(registry):
    la, lo = r["coords"]
    chk_grid[(int(math.floor(la * 10)), int(math.floor(lo * 10)))].append(idx_r)
  seen_chk = set()
  for (gx, gy), lst in chk_grid.items():
    for dx in (-1, 0, 1):
      for dy in (-1, 0, 1):
        for j in chk_grid.get((gx + dx, gy + dy), ()):
          for i in lst:
            if i >= j or (i, j) in seen_chk:
              continue
            seen_chk.add((i, j))
            if registry[i]["country"] == registry[j]["country"] and haversine_km(registry[i]["coords"], registry[j]["coords"]) <= 1.5:
              same_close_15 += 1

  print("\n=== Clean Master Registry Summary ===")
  print(f"Total unique deduplicated settlements: {len(registry)} (same-country pairs <=1.5 km: {same_close_15})")
  print(f"Post-1975 >=4x jumps: {len(post75_jumps)}, Non-founded >=10x jumps: {len(nonf_jumps)}")
  for x in sorted(post75_jumps, reverse=True)[:8]:
    print("  post75 jump:", x)
  for x in sorted(nonf_jumps, reverse=True)[:8]:
    print("  nonf jump:", x)
  for cn in sorted(by_cn, key=lambda c: -by_cn[c]):
    print(f"  {cn:12s}: total={by_cn[cn]:5d}, active_1897={c1897[cn]:5d}")

  serialisable = []
  for r in registry:
    rc = dict(r)
    rc["forms"] = sorted(rc["forms"])
    rc["pops"] = {str(k): v for k, v in sorted(rc["pops"].items())}
    rc["curated_regions"] = {str(k): v for k, v in rc["curated_regions"].items()}
    rc.pop("pop_prio", None)
    serialisable.append(rc)

  with open(OUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(serialisable, fh, ensure_ascii=False, indent=2)
  print(f"Wrote {OUT_PATH} ({os.path.getsize(OUT_PATH)} bytes)")


if __name__ == "__main__":
  main()
