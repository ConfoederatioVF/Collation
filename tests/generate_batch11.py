import os
import json
import re

TARGET_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MANDALA\_shared\toponymy_batches"

# Batch 11 data
b11_settlements = [
    {
        "key": "Vung Tau-Vietnam",
        "canonical_name": "Vung Tau",
        "foundation_year": 1890,
        "historical_names": [
            {"date": "1822.1.1", "name": "Tam Thang"},
            {"date": "1895.5.1", "name": "Cap Saint-Jacques"},
            {"date": "1956.10.22", "name": "Vung Tau"}
        ],
        "other_names": ["Cap Saint-Jacques", "Vũng Tàu", "Tam Thắng"]
    },
    {
        "key": "Padang Pariaman-Indonesia",
        "canonical_name": "Padang Pariaman",
        "foundation_year": 1833,
        "historical_names": [
            {"date": "1833.1.1", "name": "Pariaman"},
            {"date": "1956.1.1", "name": "Padang Pariaman"}
        ],
        "other_names": ["Pariaman", "Kabupaten Padang Pariaman"]
    },
    {
        "key": "Tulangbawang-Indonesia",
        "canonical_name": "Tulangbawang",
        "foundation_year": None,
        "historical_names": [
            {"date": "600.1.1", "name": "Tulang Bawang"},
            {"date": "1997.3.20", "name": "Tulangbawang"}
        ],
        "other_names": ["Tulang Bawang", "Kabupaten Tulang Bawang", "Menggala"]
    },
    {
        "key": "Rạch Giá-Vietnam",
        "canonical_name": "Rach Gia",
        "foundation_year": None,
        "historical_names": [
            {"date": "1714.1.1", "name": "Kramuon Sar"},
            {"date": "1757.1.1", "name": "Rach Gia"},
            {"date": "1976.1.1", "name": "Rach Gia"}
        ],
        "other_names": ["Rạch Giá", "Kramuon Sar"]
    },
    {
        "key": "Bacolod-Philippines",
        "canonical_name": "Bacolod",
        "foundation_year": 1770,
        "historical_names": [
            {"date": "1770.1.1", "name": "Bakolod"},
            {"date": "1849.1.1", "name": "Bacolod"},
            {"date": "1938.6.18", "name": "Bacolod"}
        ],
        "other_names": ["Bakolod", "City of Bacolod"]
    },
    {
        "key": "Mansilingan-Philippines",
        "canonical_name": "Mansilingan",
        "foundation_year": None,
        "historical_names": [
            {"date": "1850.1.1", "name": "Mansilingan"}
        ],
        "other_names": ["Barangay Mansilingan"]
    },
    {
        "key": "Pringsewu-Indonesia",
        "canonical_name": "Pringsewu",
        "foundation_year": 1925,
        "historical_names": [
            {"date": "1925.9.9", "name": "Pringsewu"},
            {"date": "2008.10.29", "name": "Pringsewu"}
        ],
        "other_names": ["Kabupaten Pringsewu", "Margakaya"]
    },
    {
        "key": "Krabi-Thailand",
        "canonical_name": "Krabi",
        "foundation_year": 1872,
        "historical_names": [
            {"date": "1872.1.1", "name": "Pakasai"},
            {"date": "1875.1.1", "name": "Krabi"}
        ],
        "other_names": ["กระบี่", "Pakasai", "Muang Krabi"]
    },
    {
        "key": "Iloilo-Philippines",
        "canonical_name": "Iloilo",
        "foundation_year": 1566,
        "historical_names": [
            {"date": "1200.1.1", "name": "Irong-Irong"},
            {"date": "1566.1.1", "name": "Iloilo"},
            {"date": "1889.1.1", "name": "Iloilo"}
        ],
        "other_names": ["Irong-Irong", "Iloilo City", "City of Iloilo"]
    },
    {
        "key": "Marikina-Philippines",
        "canonical_name": "Marikina",
        "foundation_year": 1630,
        "historical_names": [
            {"date": "1630.1.1", "name": "Jesus de la Pena"},
            {"date": "1787.1.1", "name": "Mariquina"},
            {"date": "1901.6.11", "name": "Marikina"}
        ],
        "other_names": ["Mariquina", "Marikina City"]
    },
    {
        "key": "Kupang-Indonesia",
        "canonical_name": "Kupang",
        "foundation_year": 1653,
        "historical_names": [
            {"date": "1653.1.1", "name": "Fort Concordia"},
            {"date": "1756.1.1", "name": "Koepang"},
            {"date": "1945.8.17", "name": "Kupang"}
        ],
        "other_names": ["Koepang", "Kota Kupang"]
    },
    {
        "key": "Ampang Jaya-Malaysia",
        "canonical_name": "Ampang Jaya",
        "foundation_year": 1992,
        "historical_names": [
            {"date": "1857.1.1", "name": "Ampang"},
            {"date": "1992.7.1", "name": "Ampang Jaya"}
        ],
        "other_names": ["Ampang", "Majlis Perbandaran Ampang Jaya"]
    },
    {
        "key": "Bac Giang-Vietnam",
        "canonical_name": "Bac Giang",
        "foundation_year": None,
        "historical_names": [
            {"date": "1000.1.1", "name": "Lang Giang"},
            {"date": "1895.10.10", "name": "Phu Lang Thuong"},
            {"date": "1962.10.27", "name": "Bac Giang"}
        ],
        "other_names": ["Bắc Giang", "Phủ Lạng Thương", "Phu Lang Thuong"]
    },
    {
        "key": "Mandaluyong-Philippines",
        "canonical_name": "Mandaluyong",
        "foundation_year": 1841,
        "historical_names": [
            {"date": "1841.1.1", "name": "San Felipe Neri"},
            {"date": "1931.1.1", "name": "Mandaluyong"}
        ],
        "other_names": ["San Felipe Neri", "City of Mandaluyong"]
    },
    {
        "key": "Uttaradit-Thailand",
        "canonical_name": "Uttaradit",
        "foundation_year": None,
        "historical_names": [
            {"date": "1700.1.1", "name": "Bang Pho Tha It"},
            {"date": "1887.1.1", "name": "Uttaradit"}
        ],
        "other_names": ["อุตรดิตถ์", "Bang Pho Tha It"]
    },
    {
        "key": "Cilegon-Indonesia",
        "canonical_name": "Cilegon",
        "foundation_year": 1960,
        "historical_names": [
            {"date": "1816.1.1", "name": "Tjilegon"},
            {"date": "1945.8.17", "name": "Cilegon"}
        ],
        "other_names": ["Tjilegon", "Kota Cilegon"]
    },
    {
        "key": "Dasmarinas-Philippines",
        "canonical_name": "Dasmarinas",
        "foundation_year": 1867,
        "historical_names": [
            {"date": "1867.5.12", "name": "Perez-Dasmarinas"},
            {"date": "1901.1.1", "name": "Dasmarinas"}
        ],
        "other_names": ["Perez-Dasmarinas", "Dasmarinas City"]
    },
    {
        "key": "Khammouane-Laos",
        "canonical_name": "Khammouane",
        "foundation_year": None,
        "historical_names": [
            {"date": "1353.1.1", "name": "Sikhottabong"},
            {"date": "1893.10.3", "name": "Khammouane"}
        ],
        "other_names": ["ຄຳມ່ວນ", "Khammouan", "Thakhek"]
    },
    {
        "key": "Parigi Moutong-Indonesia",
        "canonical_name": "Parigi Moutong",
        "foundation_year": 2002,
        "historical_names": [
            {"date": "1850.1.1", "name": "Parigi"},
            {"date": "2002.4.10", "name": "Parigi Moutong"}
        ],
        "other_names": ["Kabupaten Parigi Moutong", "Parigi"]
    },
    {
        "key": "Pak Kret-Thailand",
        "canonical_name": "Pak Kret",
        "foundation_year": 1955,
        "historical_names": [
            {"date": "1722.1.1", "name": "Ban Talat Kret"},
            {"date": "1955.1.1", "name": "Pak Kret"}
        ],
        "other_names": ["ปากเกร็ด", "Pakkret"]
    },
    {
        "key": "Bang Khun Thian-Thailand",
        "canonical_name": "Bang Khun Thian",
        "foundation_year": None,
        "historical_names": [
            {"date": "1800.1.1", "name": "Bang Khun Thian"}
        ],
        "other_names": ["บางขุนเทียน", "Bang Khun Thien"]
    },
    {
        "key": "Brunei-Brunei",
        "canonical_name": "Bandar Seri Begawan",
        "foundation_year": 1888,
        "historical_names": [
            {"date": "1400.1.1", "name": "Kota Batu"},
            {"date": "1888.9.17", "name": "Brunei Town"},
            {"date": "1970.10.4", "name": "Bandar Seri Begawan"}
        ],
        "other_names": ["Brunei Town", "Bandar Brunei", "Bandar Seri Begawan"]
    },
    {
        "key": "Bulukumba-Indonesia",
        "canonical_name": "Bulukumba",
        "foundation_year": None,
        "historical_names": [
            {"date": "1667.11.18", "name": "Boeloekoemba"},
            {"date": "1945.8.17", "name": "Bulukumba"}
        ],
        "other_names": ["Boeloekoemba", "Kabupaten Bulukumba"]
    },
    {
        "key": "Manado-Indonesia",
        "canonical_name": "Manado",
        "foundation_year": 1623,
        "historical_names": [
            {"date": "1200.1.1", "name": "Wenang"},
            {"date": "1623.1.1", "name": "Manado"},
            {"date": "1658.1.1", "name": "Menado"},
            {"date": "1945.8.17", "name": "Manado"}
        ],
        "other_names": ["Menado", "Wenang", "Kota Manado"]
    },
    {
        "key": "Pasay-Philippines",
        "canonical_name": "Pasay",
        "foundation_year": 1863,
        "historical_names": [
            {"date": "1863.12.2", "name": "Pineda"},
            {"date": "1901.6.11", "name": "Pasay"}
        ],
        "other_names": ["Pineda", "Pasay City"]
    },
    {
        "key": "Sainyabūlī-Laos",
        "canonical_name": "Sainyabuli",
        "foundation_year": None,
        "historical_names": [
            {"date": "1353.1.1", "name": "Sayaboury"},
            {"date": "1949.7.19", "name": "Sainyabuli"}
        ],
        "other_names": ["ໄຊຍະບູລີ", "Xaignabouli", "Sayaboury", "Sainyabuly"]
    },
    {
        "key": "Ogan Ilir-Indonesia",
        "canonical_name": "Ogan Ilir",
        "foundation_year": 2003,
        "historical_names": [
            {"date": "2003.12.18", "name": "Ogan Ilir"}
        ],
        "other_names": ["Kabupaten Ogan Ilir", "Indralaya"]
    },
    {
        "key": "Roman Catholic Diocese of Banmaw-Myanmar",
        "canonical_name": "Banmaw",
        "foundation_year": 2006,
        "historical_names": [
            {"date": "1400.1.1", "name": "Manmaw"},
            {"date": "1885.1.1", "name": "Bhamo"},
            {"date": "2006.8.28", "name": "Banmaw"}
        ],
        "other_names": ["Bhamo", "ဗန်းမော်", "Manmaw"]
    },
    {
        "key": "Karo-Indonesia",
        "canonical_name": "Karo",
        "foundation_year": None,
        "historical_names": [
            {"date": "1906.1.1", "name": "Karoland"},
            {"date": "1946.1.1", "name": "Karo"}
        ],
        "other_names": ["Tanah Karo", "Kabupaten Karo", "Kabanjahe"]
    },
    {
        "key": "Kuala Terengganu-Malaysia",
        "canonical_name": "Kuala Terengganu",
        "foundation_year": None,
        "historical_names": [
            {"date": "1725.1.1", "name": "Kuala Terengganu"}
        ],
        "other_names": ["Kuala Trengganu", "Bandar Diraja Kuala Terengganu"]
    },
    {
        "key": "West Pasaman-Indonesia",
        "canonical_name": "West Pasaman",
        "foundation_year": 2004,
        "historical_names": [
            {"date": "2004.1.7", "name": "West Pasaman"}
        ],
        "other_names": ["Pasaman Barat", "Kabupaten Pasaman Barat", "Simpang Ampek"]
    },
    {
        "key": "Danau Sipin-Indonesia",
        "canonical_name": "Danau Sipin",
        "foundation_year": None,
        "historical_names": [
            {"date": "1200.1.1", "name": "Danau Sipin"}
        ],
        "other_names": ["Kecamatan Danau Sipin", "Jambi"]
    },
    {
        "key": "Taman Petaling-Malaysia",
        "canonical_name": "Taman Petaling",
        "foundation_year": None,
        "historical_names": [
            {"date": "1952.1.1", "name": "Petaling"},
            {"date": "1970.1.1", "name": "Taman Petaling"}
        ],
        "other_names": ["Petaling", "Petaling Jaya"]
    },
    {
        "key": "Central Maluku-Indonesia",
        "canonical_name": "Central Maluku",
        "foundation_year": None,
        "historical_names": [
            {"date": "1605.1.1", "name": "Amboina"},
            {"date": "1952.1.1", "name": "Central Maluku"}
        ],
        "other_names": ["Maluku Tengah", "Kabupaten Maluku Tengah", "Amboina"]
    },
    {
        "key": "Lat Krabang-Thailand",
        "canonical_name": "Lat Krabang",
        "foundation_year": None,
        "historical_names": [
            {"date": "1927.1.1", "name": "Lat Krabang"}
        ],
        "other_names": ["ลาดกระบัง", "Ladkrabang"]
    },
    {
        "key": "East Aceh-Indonesia",
        "canonical_name": "East Aceh",
        "foundation_year": 1956,
        "historical_names": [
            {"date": "840.1.1", "name": "Peureulak"},
            {"date": "1956.11.24", "name": "East Aceh"}
        ],
        "other_names": ["Aceh Timur", "Kabupaten Aceh Timur", "Idi Rayeuk"]
    },
    {
        "key": "Hat Yai-Thailand",
        "canonical_name": "Hat Yai",
        "foundation_year": 1917,
        "historical_names": [
            {"date": "1917.1.1", "name": "Khok Samet Chun"},
            {"date": "1922.1.1", "name": "Hat Yai"}
        ],
        "other_names": ["หาดใหญ่", "Haad Yai", "Khok Samet Chun"]
    },
    {
        "key": "Indragiri Hulu-Indonesia",
        "canonical_name": "Indragiri Hulu",
        "foundation_year": None,
        "historical_names": [
            {"date": "1298.1.1", "name": "Indragiri"},
            {"date": "1956.1.1", "name": "Indragiri Hulu"}
        ],
        "other_names": ["Kabupaten Indragiri Hulu", "Rengat"]
    },
    {
        "key": "Krathum Baen-Thailand",
        "canonical_name": "Krathum Baen",
        "foundation_year": None,
        "historical_names": [
            {"date": "1900.1.1", "name": "Krathum Baen"}
        ],
        "other_names": ["กระทุ่มแบน", "Kradum Baen"]
    },
    {
        "key": "Labuhanbatu-Indonesia",
        "canonical_name": "Labuhanbatu",
        "foundation_year": None,
        "historical_names": [
            {"date": "1865.1.1", "name": "Laboehan Batoe"},
            {"date": "1945.8.17", "name": "Labuhanbatu"}
        ],
        "other_names": ["Laboehan Batoe", "Labuhan Batu", "Rantau Prapat"]
    },
    {
        "key": "East Kutai-Indonesia",
        "canonical_name": "East Kutai",
        "foundation_year": 1999,
        "historical_names": [
            {"date": "400.1.1", "name": "Kutai"},
            {"date": "1999.10.4", "name": "East Kutai"}
        ],
        "other_names": ["Kutai Timur", "Kabupaten Kutai Timur", "Sangatta"]
    },
    {
        "key": "Kampung Kangkar Teberau-Malaysia",
        "canonical_name": "Kampung Kangkar Tebrau",
        "foundation_year": None,
        "historical_names": [
            {"date": "1844.1.1", "name": "Kangkar Tebrau"},
            {"date": "1957.8.31", "name": "Kampung Kangkar Tebrau"}
        ],
        "other_names": ["Kangkar Tebrau", "Kampung Kangkar Teberau"]
    },
    {
        "key": "Penajam-Indonesia",
        "canonical_name": "Penajam",
        "foundation_year": None,
        "historical_names": [
            {"date": "1700.1.1", "name": "Penajam"},
            {"date": "2002.4.10", "name": "Penajam"}
        ],
        "other_names": ["Penajam Paser Utara", "Kabupaten Penajam Paser Utara"]
    },
    {
        "key": "Pinrang-Indonesia",
        "canonical_name": "Pinrang",
        "foundation_year": None,
        "historical_names": [
            {"date": "1400.1.1", "name": "Sawitto"},
            {"date": "1960.1.28", "name": "Pinrang"}
        ],
        "other_names": ["Sawitto", "Kabupaten Pinrang"]
    },
    {
        "key": "Việt Trì-Vietnam",
        "canonical_name": "Viet Tri",
        "foundation_year": 1962,
        "historical_names": [
            {"date": "-700.1.1", "name": "Phong Chau"},
            {"date": "1940.1.1", "name": "Viet Tri"},
            {"date": "1962.6.4", "name": "Viet Tri"}
        ],
        "other_names": ["Việt Trì", "Phong Châu", "Phú Thọ"]
    }
]

out_b11 = {
    "batch_index": 11,
    "settlements": b11_settlements
}

target_path_11 = os.path.join(TARGET_DIR, "resolved_batch_11.json")
with open(target_path_11, "w", encoding="utf-8") as f:
    json.dump(out_b11, f, indent=2, ensure_ascii=False)
print(f"Wrote resolved_batch_11.json with {len(b11_settlements)} settlements")
