"""Resolution script for batches 001 to 008."""

import json
import os
import re
import unicodedata

DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")

# Script purity regexes
LATIN_ONLY_RE = re.compile(r"^[\u0020-\u007E\u00A0-\u024F\u1E00-\u1EFF\u2010-\u2027]+$")
CAMBODIA_ALLOWED_RE = re.compile(r"^[\u0020-\u007E\u00A0-\u024F\u1E00-\u1EFF\u1780-\u17FF\u2010-\u2027]+$")

FORBIDDEN_ADMIN_PATTERNS = [
    r"\bDivision\b", r"\bRegency\b", r"\bResidency\b", r"\bProvince\b",
    r"\bDistrict\b", r"\bMunicipality\b", r"\bKingdom of\b", r"\bSultanate of\b",
    r"\bRepublic of\b", r"\bGemeente\b", r"\bKabupaten\b", r"\bAmphoe\b",
    r"\bTownship\b", r"Binh Tri Thien"
]
ADMIN_RE = re.compile("|".join(FORBIDDEN_ADMIN_PATTERNS), re.IGNORECASE)

MOJIBAKE_CHARS = ["?", "`", "\ufffd", "~"]

# Known historical sequences for key cities (canonical_name, historical_names, other_names)
KNOWN_HISTORICAL = {
    # Cambodia
    "Koh Ker-Cambodia": {
        "canonical_name": "Koh Ker",
        "historical_names": [
            {"date": "928.1.1", "name": "Lingapura"},
            {"date": "944.1.1", "name": "Koh Ker"}
        ],
        "other_names": ["Lingapura", "Chok Gargyar", "កោះកេរ"]
    },
    "Sambor Prei Kuk-Cambodia": {
        "canonical_name": "Sambor Prei Kuk",
        "historical_names": [
            {"date": "616.1.1", "name": "Isanapura"},
            {"date": "700.1.1", "name": "Sambor Prei Kuk"}
        ],
        "other_names": ["Isanapura", "Prasat Sambor Prei Kuk", "សំបូរព្រៃគុក"]
    },
    "Preah Khan of Kompong Svay-Cambodia": {
        "canonical_name": "Preah Khan of Kampong Svay",
        "historical_names": [
            {"date": "1100.1.1", "name": "Bakan"},
            {"date": "1200.1.1", "name": "Preah Khan of Kampong Svay"}
        ],
        "other_names": ["Bakan", "Prasat Bakan", "Preah Khan Kompong Svay", "ព្រះខ័នកំពង់ស្វាយ"]
    },
    "Banteay Chhmar-Cambodia_2": {
        "canonical_name": "Banteay Chhmar",
        "historical_names": [
            {"date": "1200.1.1", "name": "Banteay Chhmar"}
        ],
        "other_names": ["Banteai Chhmar", "Banteay Chmar", "បន្ទាយឆ្មារ"]
    },
    "Kampong Cham-Cambodia": {
        "canonical_name": "Kampong Cham",
        "historical_names": [
            {"date": "1907.1.1", "name": "Kampong Cham"}
        ],
        "other_names": ["Kompong Cham", "កំពង់ចាម"]
    },
    "Paoy Paet-Cambodia": {
        "canonical_name": "Paoy Paet",
        "historical_names": [
            {"date": "1907.1.1", "name": "Poipet"},
            {"date": "1993.1.1", "name": "Paoy Paet"}
        ],
        "other_names": ["Poipet", "Paoy Pet", "ប៉ោយប៉ែត"]
    },
    "Kampot-Cambodia": {
        "canonical_name": "Kampot",
        "historical_names": [
            {"date": "1840.1.1", "name": "Kampot"}
        ],
        "other_names": ["Kâmpôt", "កំពត", "Compong Bai"]
    },
    "Prey Veng-Cambodia": {
        "canonical_name": "Prey Veng",
        "historical_names": [
            {"date": "1500.1.1", "name": "Prey Veng"}
        ],
        "other_names": ["Prey Vêng", "ព្រៃវែង", "Ba Phnom"]
    },
    "Stung Treng-Cambodia": {
        "canonical_name": "Stung Treng",
        "historical_names": [
            {"date": "1893.1.1", "name": "Stung Treng"}
        ],
        "other_names": ["Stoeng Treng", "ស្ទឹងត្រែង", "Xieng Teng"]
    },
    "Svay Rieng-Cambodia": {
        "canonical_name": "Svay Rieng",
        "historical_names": [
            {"date": "1907.1.1", "name": "Svay Rieng"}
        ],
        "other_names": ["Svai Rieng", "ស្វាយរៀង", "Svay Teap"]
    },
    "Phanom Rung-Cambodia": {
        "canonical_name": "Phanom Rung",
        "historical_names": [
            {"date": "1000.1.1", "name": "Phanom Rung"}
        ],
        "other_names": ["Phnom Rung", "Prasat Phanom Rung"]
    },

    # East Timor
    "Baucau-East Timor": {
        "canonical_name": "Baucau",
        "historical_names": [
            {"date": "1936.1.1", "name": "Vila Salazar"},
            {"date": "1975.11.28", "name": "Baucau"}
        ],
        "other_names": ["Vila Salazar", "Baukau"]
    },
    "Dom Aleixo administrative post-East Timor": {
        "canonical_name": "Dom Aleixo",
        "historical_names": [
            {"date": "1975.1.1", "name": "Dom Aleixo"}
        ],
        "other_names": ["Posto Administrativo de Dom Aleixo"]
    },
    "Bobonaro-East Timor": {
        "canonical_name": "Bobonaro",
        "historical_names": [
            {"date": "1936.1.1", "name": "Vila Armindo Monteiro"},
            {"date": "1975.11.28", "name": "Bobonaro"}
        ],
        "other_names": ["Vila Armindo Monteiro", "Bobonaru"]
    },

    # Indonesia
    "Medan-Indonesia": {
        "canonical_name": "Medan",
        "historical_names": [
            {"date": "1590.7.1", "name": "Medan Putri"},
            {"date": "1869.1.1", "name": "Medan"}
        ],
        "other_names": ["Medan Putri", "Kota Medan", "Deli Medan"]
    },
    "Deli Serdang-Indonesia": {
        "canonical_name": "Deli Serdang",
        "historical_names": [
            {"date": "1632.1.1", "name": "Deli"},
            {"date": "1946.7.1", "name": "Deli Serdang"}
        ],
        "other_names": ["Deli", "Serdang", "Lubuk Pakam"]
    },
    "Tangerang-Indonesia": {
        "canonical_name": "Tangerang",
        "historical_names": [
            {"date": "1654.1.1", "name": "Tangerang"}
        ],
        "other_names": ["Tangierang", "Kota Tangerang"]
    },
    "Semarang-Indonesia": {
        "canonical_name": "Semarang",
        "historical_names": [
            {"date": "1476.5.2", "name": "Bergota"},
            {"date": "1547.5.2", "name": "Semarang"},
            {"date": "1678.1.1", "name": "Samarang"},
            {"date": "1942.3.9", "name": "Semarang"}
        ],
        "other_names": ["Samarang", "Bergota", "Pragota", "Kota Semarang"]
    },
    "Semarang-Indonesia_2": {
        "canonical_name": "Semarang",
        "historical_names": [
            {"date": "1547.5.2", "name": "Semarang"},
            {"date": "1678.1.1", "name": "Samarang"},
            {"date": "1942.3.9", "name": "Semarang"}
        ],
        "other_names": ["Samarang", "Kota Semarang"]
    },
    "Palembang-Indonesia": {
        "canonical_name": "Palembang",
        "historical_names": [
            {"date": "683.6.16", "name": "Sriwijaya"},
            {"date": "1659.1.1", "name": "Palembang"}
        ],
        "other_names": ["Srivijaya", "Sriwijaya", "Kota Palembang"]
    },
    "Sidoarjo-Indonesia": {
        "canonical_name": "Sidoarjo",
        "historical_names": [
            {"date": "1020.1.1", "name": "Kahuripan"},
            {"date": "1851.1.1", "name": "Sidokare"},
            {"date": "1859.5.28", "name": "Sidoarjo"}
        ],
        "other_names": ["Sidokare", "Sidoardjo", "Kahuripan"]
    },
    "Tambaksari-Indonesia": {
        "canonical_name": "Tambaksari",
        "historical_names": [
            {"date": "1949.1.1", "name": "Tambaksari"}
        ],
        "other_names": ["Kecamatan Tambaksari"]
    },
    "Malang-Indonesia": {
        "canonical_name": "Malang",
        "historical_names": [
            {"date": "760.1.1", "name": "Kanjuruhan"},
            {"date": "1767.1.1", "name": "Malang"}
        ],
        "other_names": ["Kanjuruhan", "Kota Malang"]
    },
    "Pekalongan-Indonesia": {
        "canonical_name": "Pekalongan",
        "historical_names": [
            {"date": "1622.1.1", "name": "Pekalongan"}
        ],
        "other_names": ["Kota Pekalongan", "Kota Batik"]
    },
    "Gowa-Indonesia": {
        "canonical_name": "Gowa",
        "historical_names": [
            {"date": "1320.1.1", "name": "Gowa"}
        ],
        "other_names": ["Sungguminasa", "Goa"]
    },
    "Gowa-Indonesia_2": {
        "canonical_name": "Gowa",
        "historical_names": [
            {"date": "1320.1.1", "name": "Gowa"}
        ],
        "other_names": ["Sungguminasa", "Goa"]
    },
    "Banjarmasin-Indonesia": {
        "canonical_name": "Banjarmasin",
        "historical_names": [
            {"date": "1526.9.24", "name": "Bandar Masih"},
            {"date": "1606.1.1", "name": "Bandjermasin"},
            {"date": "1947.1.1", "name": "Banjarmasin"}
        ],
        "other_names": ["Bandjermasin", "Bandar Masih", "Kota Banjarmasin"]
    },
    "Pontianak-Indonesia": {
        "canonical_name": "Pontianak",
        "historical_names": [
            {"date": "1771.10.23", "name": "Pontianak"}
        ],
        "other_names": ["Kota Pontianak", "Pontijanak"]
    },
    "Jambi-Indonesia": {
        "canonical_name": "Jambi",
        "historical_names": [
            {"date": "686.1.1", "name": "Melayu"},
            {"date": "1401.1.1", "name": "Jambi"}
        ],
        "other_names": ["Melayu", "Djambi", "Telanaipura", "Kota Jambi"]
    },
    "Jambi-Indonesia_2": {
        "canonical_name": "Jambi",
        "historical_names": [
            {"date": "686.1.1", "name": "Melayu"},
            {"date": "1401.1.1", "name": "Jambi"}
        ],
        "other_names": ["Melayu", "Djambi", "Telanaipura"]
    },
    "Surabaya-Indonesia": {
        "canonical_name": "Surabaya",
        "historical_names": [
            {"date": "1037.1.1", "name": "Hujung Galuh"},
            {"date": "1293.5.31", "name": "Surabaya"},
            {"date": "1600.1.1", "name": "Soerabaja"},
            {"date": "1942.3.9", "name": "Surabaya"}
        ],
        "other_names": ["Soerabaja", "Hujung Galuh", "Ujung Galuh", "Kota Surabaya"]
    },
    "Yogyakarta-Indonesia": {
        "canonical_name": "Yogyakarta",
        "historical_names": [
            {"date": "1755.10.7", "name": "Ngayogyakarta Hadiningrat"},
            {"date": "1942.3.9", "name": "Djokjakarta"},
            {"date": "1972.8.17", "name": "Yogyakarta"}
        ],
        "other_names": ["Jogja", "Jogjakarta", "Ngayogyakarta Hadiningrat", "Kota Yogyakarta"]
    },
    "Cirebon-Indonesia": {
        "canonical_name": "Cirebon",
        "historical_names": [
            {"date": "1445.1.1", "name": "Caruban"},
            {"date": "1681.1.1", "name": "Cheribon"},
            {"date": "1942.3.9", "name": "Cirebon"}
        ],
        "other_names": ["Cheribon", "Caruban", "Tjirebon", "Kota Cirebon"]
    },
    "Kediri-Indonesia": {
        "canonical_name": "Kediri",
        "historical_names": [
            {"date": "879.1.1", "name": "Kediri"},
            {"date": "1042.1.1", "name": "Panjalu"},
            {"date": "1046.1.1", "name": "Daha"},
            {"date": "1222.1.1", "name": "Kediri"}
        ],
        "other_names": ["Panjalu", "Daha", "Kadiri", "Kota Kediri"]
    },
    "Tegal-Indonesia": {
        "canonical_name": "Tegal",
        "historical_names": [
            {"date": "1580.4.12", "name": "Tegal"}
        ],
        "other_names": ["Kota Tegal", "Taggal"]
    },
    "Banda Aceh-Indonesia": {
        "canonical_name": "Banda Aceh",
        "historical_names": [
            {"date": "1205.4.22", "name": "Bandar Aceh Darussalam"},
            {"date": "1874.1.24", "name": "Kutaraja"},
            {"date": "1962.12.28", "name": "Banda Aceh"}
        ],
        "other_names": ["Bandar Aceh Darussalam", "Kutaraja", "Kota Radja", "Kota Banda Aceh"]
    },
    "Ternate-Indonesia": {
        "canonical_name": "Ternate",
        "historical_names": [
            {"date": "1257.1.1", "name": "Gapi"},
            {"date": "1607.1.1", "name": "Ternate"}
        ],
        "other_names": ["Gapi", "Kota Ternate"]
    },
    "Singaraja-Indonesia": {
        "canonical_name": "Singaraja",
        "historical_names": [
            {"date": "1604.1.1", "name": "Singaraja"}
        ],
        "other_names": ["Buleleng", "Singaradja"]
    },
    "Wirobrajan-Indonesia": {
        "canonical_name": "Wirobrajan",
        "historical_names": [
            {"date": "1949.1.1", "name": "Wirobrajan"}
        ],
        "other_names": ["Kecamatan Wirobrajan"]
    },
    "Magelang-Indonesia": {
        "canonical_name": "Magelang",
        "historical_names": [
            {"date": "907.4.11", "name": "Mantyasih"},
            {"date": "1810.1.1", "name": "Magelang"}
        ],
        "other_names": ["Mantyasih", "Kota Magelang"]
    },
    "Magelang-Indonesia_2": {
        "canonical_name": "Magelang",
        "historical_names": [
            {"date": "907.4.11", "name": "Mantyasih"},
            {"date": "1810.1.1", "name": "Magelang"}
        ],
        "other_names": ["Mantyasih", "Kota Magelang"]
    },
    "Kotagede, Plered-Indonesia": {
        "canonical_name": "Kotagede",
        "historical_names": [
            {"date": "1587.1.1", "name": "Kotagede"},
            {"date": "1647.1.1", "name": "Plered"},
            {"date": "1755.1.1", "name": "Kotagede"}
        ],
        "other_names": ["Kota Gede", "Plered", "Kutha Gede"]
    },
    "Kubu Raya-Indonesia": {
        "canonical_name": "Kubu Raya",
        "historical_names": [
            {"date": "1772.1.1", "name": "Kubu"},
            {"date": "2007.8.10", "name": "Kubu Raya"}
        ],
        "other_names": ["Sungai Raya", "Kubu"]
    },
    "Mempawah-Indonesia": {
        "canonical_name": "Mempawah",
        "historical_names": [
            {"date": "1740.1.1", "name": "Mempawah"}
        ],
        "other_names": ["Mampawah", "Mampawa"]
    },
    "Mempawah-Indonesia_2": {
        "canonical_name": "Mempawah",
        "historical_names": [
            {"date": "1740.1.1", "name": "Mempawah"}
        ],
        "other_names": ["Mampawah", "Mampawa"]
    },
    "Pesisir Selatan-Indonesia": {
        "canonical_name": "Pesisir Selatan",
        "historical_names": [
            {"date": "1663.1.1", "name": "Painan"},
            {"date": "1956.1.1", "name": "Pesisir Selatan"}
        ],
        "other_names": ["Painan", "Salido"]
    },
    "Tanah Datar-Indonesia_2": {
        "canonical_name": "Tanah Datar",
        "historical_names": [
            {"date": "1347.1.1", "name": "Pagaruyung"},
            {"date": "1824.1.1", "name": "Fort van der Capellen"},
            {"date": "1945.8.17", "name": "Tanah Datar"}
        ],
        "other_names": ["Pagaruyung", "Batusangkar", "Fort van der Capellen"]
    },
    "Central Tapanuli-Indonesia": {
        "canonical_name": "Central Tapanuli",
        "historical_names": [
            {"date": "800.1.1", "name": "Barus"},
            {"date": "1840.1.1", "name": "Sibolga"},
            {"date": "1956.1.1", "name": "Central Tapanuli"}
        ],
        "other_names": ["Tapanuli Tengah", "Barus", "Sibolga", "Fansur"]
    },
    "Soreang-Indonesia": {
        "canonical_name": "Soreang",
        "historical_names": [
            {"date": "1950.1.1", "name": "Soreang"}
        ],
        "other_names": ["Kecamatan Soreang"]
    },
    "Dramaga-Indonesia": {
        "canonical_name": "Dramaga",
        "historical_names": [
            {"date": "1950.1.1", "name": "Dramaga"}
        ],
        "other_names": ["Dermaga", "Kecamatan Dramaga"]
    },
    "Cipanas-Indonesia": {
        "canonical_name": "Cipanas",
        "historical_names": [
            {"date": "1742.1.1", "name": "Cipanas"}
        ],
        "other_names": ["Tjipanas"]
    },
    "Pangkalanbuun-Indonesia": {
        "canonical_name": "Pangkalanbuun",
        "historical_names": [
            {"date": "1602.1.1", "name": "Kotawaringin"},
            {"date": "1950.1.1", "name": "Pangkalanbuun"}
        ],
        "other_names": ["Pangkalan Bun", "Kotawaringin", "Pangkalanboeoen"]
    },
    "Pelabuhanratu-Indonesia": {
        "canonical_name": "Pelabuhanratu",
        "historical_names": [
            {"date": "1850.1.1", "name": "Palabuhanratu"},
            {"date": "1975.1.1", "name": "Pelabuhanratu"}
        ],
        "other_names": ["Palabuhanratu", "Palaboehanratoe"]
    },
    "Singkawang-Indonesia": {
        "canonical_name": "Singkawang",
        "historical_names": [
            {"date": "1777.1.1", "name": "San Khew Khok"},
            {"date": "1950.1.1", "name": "Singkawang"}
        ],
        "other_names": ["San Khew Khok", "Kota Singkawang"]
    },
    "Toli-Toli-Indonesia": {
        "canonical_name": "Toli-Toli",
        "historical_names": [
            {"date": "1850.1.1", "name": "Toli-Toli"}
        ],
        "other_names": ["Tolitoli", "Baolan"]
    },
    "Labuan Bajo-Indonesia": {
        "canonical_name": "Labuan Bajo",
        "historical_names": [
            {"date": "1920.1.1", "name": "Labuan Bajo"}
        ],
        "other_names": ["Labuhan Bajo", "Laboean Bajo"]
    },
    "Buleleng-Indonesia_2": {
        "canonical_name": "Buleleng",
        "historical_names": [
            {"date": "1604.1.1", "name": "Buleleng"}
        ],
        "other_names": ["Singaraja", "Boelèlèng"]
    },
    "Asahan-Indonesia_2": {
        "canonical_name": "Asahan",
        "historical_names": [
            {"date": "1630.1.1", "name": "Asahan"}
        ],
        "other_names": ["Tanjungbalai Asahan", "Assahan"]
    },
    "Simalungun-Indonesia_2": {
        "canonical_name": "Simalungun",
        "historical_names": [
            {"date": "1300.1.1", "name": "Nagur"},
            {"date": "1850.1.1", "name": "Simalungun"}
        ],
        "other_names": ["Tanah Simalungun", "Nagur", "Simeloengoen"]
    },
    "Bantul-Indonesia": {
        "canonical_name": "Bantul",
        "historical_names": [
            {"date": "1831.7.20", "name": "Bantul"}
        ],
        "other_names": ["Bantoel"]
    },
    "Brebes-Indonesia": {
        "canonical_name": "Brebes",
        "historical_names": [
            {"date": "1678.1.18", "name": "Brebes"}
        ],
        "other_names": ["Berbes"]
    },
    "Banyumas-Indonesia": {
        "canonical_name": "Banyumas",
        "historical_names": [
            {"date": "1582.4.6", "name": "Banyumas"}
        ],
        "other_names": ["Banjoemas", "Purwokerto"]
    },
    "Grobogan-Indonesia": {
        "canonical_name": "Grobogan",
        "historical_names": [
            {"date": "1726.3.4", "name": "Grobogan"}
        ],
        "other_names": ["Purwodadi"]
    },
    "Klaten-Indonesia": {
        "canonical_name": "Klaten",
        "historical_names": [
            {"date": "1804.7.28", "name": "Klaten"}
        ],
        "other_names": ["Klathen"]
    },
    "Lebak-Indonesia": {
        "canonical_name": "Lebak",
        "historical_names": [
            {"date": "1828.10.29", "name": "Lebak"}
        ],
        "other_names": ["Rangkasbitung"]
    },
    "Lebak-Indonesia_2": {
        "canonical_name": "Lebak",
        "historical_names": [
            {"date": "1828.10.29", "name": "Lebak"}
        ],
        "other_names": ["Rangkasbitung"]
    },
    "Pemalang-Indonesia": {
        "canonical_name": "Pemalang",
        "historical_names": [
            {"date": "1575.1.24", "name": "Pemalang"}
        ],
        "other_names": []
    },
    "Jombang-Indonesia": {
        "canonical_name": "Jombang",
        "historical_names": [
            {"date": "1910.10.21", "name": "Jombang"}
        ],
        "other_names": ["Djombang"]
    },
    "Lamongan-Indonesia": {
        "canonical_name": "Lamongan",
        "historical_names": [
            {"date": "1569.5.26", "name": "Lamongan"}
        ],
        "other_names": []
    },
    "Tuban-Indonesia": {
        "canonical_name": "Tuban",
        "historical_names": [
            {"date": "1293.11.12", "name": "Tuban"}
        ],
        "other_names": ["Toeban"]
    },
    "Kuningan-Indonesia": {
        "canonical_name": "Kuningan",
        "historical_names": [
            {"date": "1132.9.1", "name": "Kuningan"}
        ],
        "other_names": ["Koeningan", "Kajene"]
    },
    "Bangkalan-Indonesia": {
        "canonical_name": "Bangkalan",
        "historical_names": [
            {"date": "1531.10.24", "name": "Bangkalan"}
        ],
        "other_names": ["Bangkalan Madura"]
    },
    "Sampang-Indonesia": {
        "canonical_name": "Sampang",
        "historical_names": [
            {"date": "1624.1.1", "name": "Sampang"}
        ],
        "other_names": []
    },
    "Boyolali-Indonesia": {
        "canonical_name": "Boyolali",
        "historical_names": [
            {"date": "1847.6.5", "name": "Boyolali"}
        ],
        "other_names": ["Bojolali"]
    },
    "Kendal-Indonesia": {
        "canonical_name": "Kendal",
        "historical_names": [
            {"date": "1605.7.28", "name": "Kendal"}
        ],
        "other_names": ["Bahurekso Kendal"]
    },
    "Kendal-Indonesia_2": {
        "canonical_name": "Kendal",
        "historical_names": [
            {"date": "1605.7.28", "name": "Kendal"}
        ],
        "other_names": ["Bahurekso Kendal"]
    },
    "Ponorogo-Indonesia": {
        "canonical_name": "Ponorogo",
        "historical_names": [
            {"date": "1496.8.11", "name": "Ponorogo"}
        ],
        "other_names": ["Panaraga", "Poenorogo"]
    },
    "Cianjur-Indonesia": {
        "canonical_name": "Cianjur",
        "historical_names": [
            {"date": "1677.7.12", "name": "Cianjur"}
        ],
        "other_names": ["Tjiandjoer"]
    },
    "Wonosobo-Indonesia": {
        "canonical_name": "Wonosobo",
        "historical_names": [
            {"date": "1825.7.24", "name": "Wonosobo"}
        ],
        "other_names": ["Wanasaba"]
    },
    "Karanganyar-Indonesia": {
        "canonical_name": "Karanganyar",
        "historical_names": [
            {"date": "1917.11.18", "name": "Karanganyar"}
        ],
        "other_names": ["Karanganjar"]
    },
    "Sukoharjo-Indonesia": {
        "canonical_name": "Sukoharjo",
        "historical_names": [
            {"date": "1946.7.15", "name": "Sukoharjo"}
        ],
        "other_names": ["Soekohardjo"]
    },
    "Blora-Indonesia": {
        "canonical_name": "Blora",
        "historical_names": [
            {"date": "1749.12.11", "name": "Blora"}
        ],
        "other_names": []
    },
    "Temanggung-Indonesia": {
        "canonical_name": "Temanggung",
        "historical_names": [
            {"date": "1834.11.10", "name": "Temanggung"}
        ],
        "other_names": ["Temanggoeng"]
    },
    "Temanggung-Indonesia_2": {
        "canonical_name": "Temanggung",
        "historical_names": [
            {"date": "1834.11.10", "name": "Temanggung"}
        ],
        "other_names": ["Temanggoeng"]
    },
    "Magetan-Indonesia": {
        "canonical_name": "Magetan",
        "historical_names": [
            {"date": "1675.10.12", "name": "Magetan"}
        ],
        "other_names": []
    },
    "Rembang-Indonesia": {
        "canonical_name": "Rembang",
        "historical_names": [
            {"date": "1741.7.27", "name": "Rembang"}
        ],
        "other_names": []
    },
    "Banyuwangi-Indonesia": {
        "canonical_name": "Banyuwangi",
        "historical_names": [
            {"date": "1771.12.18", "name": "Banyuwangi"}
        ],
        "other_names": ["Banjoewangi", "Blambangan"]
    },
    "Pacitan-Indonesia": {
        "canonical_name": "Pacitan",
        "historical_names": [
            {"date": "1745.2.19", "name": "Pacitan"}
        ],
        "other_names": ["Patjitan"]
    },
    "Bengkalis-Indonesia": {
        "canonical_name": "Bengkalis",
        "historical_names": [
            {"date": "1678.1.1", "name": "Bengkalis"}
        ],
        "other_names": []
    },
    "Gianyar-Indonesia": {
        "canonical_name": "Gianyar",
        "historical_names": [
            {"date": "1687.1.1", "name": "Gianyar"}
        ],
        "other_names": ["Gianjar", "Ubud"]
    },
    "Bondowoso-Indonesia": {
        "canonical_name": "Bondowoso",
        "historical_names": [
            {"date": "1819.1.1", "name": "Bondowoso"}
        ],
        "other_names": ["Bandawasa"]
    },
    "Sintang-Indonesia": {
        "canonical_name": "Sintang",
        "historical_names": [
            {"date": "1362.1.1", "name": "Sintang"}
        ],
        "other_names": []
    },
    "Ende-Indonesia": {
        "canonical_name": "Ende",
        "historical_names": [
            {"date": "1638.1.1", "name": "Ende"}
        ],
        "other_names": ["Endeh"]
    },
    "Bangli-Indonesia": {
        "canonical_name": "Bangli",
        "historical_names": [
            {"date": "1204.1.1", "name": "Bangli"}
        ],
        "other_names": []
    },
    "Bangli-Indonesia_2": {
        "canonical_name": "Bangli",
        "historical_names": [
            {"date": "1204.1.1", "name": "Bangli"}
        ],
        "other_names": []
    },
    "Sinjai-Indonesia": {
        "canonical_name": "Sinjai",
        "historical_names": [
            {"date": "1564.1.1", "name": "Sinjai"}
        ],
        "other_names": ["Sindjai"]
    },
    "Soppeng-Indonesia": {
        "canonical_name": "Soppeng",
        "historical_names": [
            {"date": "1261.1.1", "name": "Soppeng"}
        ],
        "other_names": ["Watansoppeng"]
    },
    "Soppeng-Indonesia_2": {
        "canonical_name": "Soppeng",
        "historical_names": [
            {"date": "1261.1.1", "name": "Soppeng"}
        ],
        "other_names": ["Watansoppeng"]
    },
    "Barru-Indonesia": {
        "canonical_name": "Barru",
        "historical_names": [
            {"date": "1586.1.1", "name": "Barru"}
        ],
        "other_names": ["Barroe"]
    },
    "Ungaran-Indonesia": {
        "canonical_name": "Ungaran",
        "historical_names": [
            {"date": "1602.1.1", "name": "Ungaran"}
        ],
        "other_names": ["Oengaran"]
    },
    "Rangkasbitung-Indonesia": {
        "canonical_name": "Rangkasbitung",
        "historical_names": [
            {"date": "1851.1.1", "name": "Rangkasbitung"}
        ],
        "other_names": ["Rangkasbitoeng"]
    },
    "Adiwerna-Indonesia": {
        "canonical_name": "Adiwerna",
        "historical_names": [
            {"date": "1950.1.1", "name": "Adiwerna"}
        ],
        "other_names": ["Adiverna"]
    },
    "Cisarua-Indonesia": {
        "canonical_name": "Cisarua",
        "historical_names": [
            {"date": "1950.1.1", "name": "Cisarua"}
        ],
        "other_names": ["Tjisaroea"]
    },
    "Parung-Indonesia": {
        "canonical_name": "Parung",
        "historical_names": [
            {"date": "1950.1.1", "name": "Parung"}
        ],
        "other_names": ["Paroeng"]
    },
    "Cikampek-Indonesia": {
        "canonical_name": "Cikampek",
        "historical_names": [
            {"date": "1950.1.1", "name": "Cikampek"}
        ],
        "other_names": ["Tjikampek"]
    },
    "Ciawi-Indonesia": {
        "canonical_name": "Ciawi",
        "historical_names": [
            {"date": "1950.1.1", "name": "Ciawi"}
        ],
        "other_names": ["Tjiawi"]
    },
    "Kedungwuni-Indonesia": {
        "canonical_name": "Kedungwuni",
        "historical_names": [
            {"date": "1930.1.1", "name": "Kedungwuni"}
        ],
        "other_names": ["Kedoengwoeni"]
    },
    "Lawang-Indonesia": {
        "canonical_name": "Lawang",
        "historical_names": [
            {"date": "1900.1.1", "name": "Lawang"}
        ],
        "other_names": []
    },
    "Majenang-Indonesia": {
        "canonical_name": "Majenang",
        "historical_names": [
            {"date": "1900.1.1", "name": "Majenang"}
        ],
        "other_names": ["Madjenang"]
    },
    "Pare-Indonesia": {
        "canonical_name": "Pare",
        "historical_names": [
            {"date": "1930.1.1", "name": "Pare"}
        ],
        "other_names": []
    },
    "Arjawinangun-Indonesia": {
        "canonical_name": "Arjawinangun",
        "historical_names": [
            {"date": "1950.1.1", "name": "Arjawinangun"}
        ],
        "other_names": ["Ardjawinangoen"]
    },
    "Jember-Indonesia": {
        "canonical_name": "Jember",
        "historical_names": [
            {"date": "1928.1.1", "name": "Jember"}
        ],
        "other_names": ["Djember"]
    }
}
