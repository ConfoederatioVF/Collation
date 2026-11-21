import os
import json

TARGET_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MANDALA\_shared\toponymy_batches"

b13_settlements = [
    {
        "key": "Vũng Tàu-Vietnam",
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
        "key": "Bacoor-Philippines",
        "canonical_name": "Bacoor",
        "foundation_year": 1671,
        "historical_names": [
            {"date": "1671.1.1", "name": "Bakood"},
            {"date": "1898.6.23", "name": "Bacoor"},
            {"date": "2012.6.23", "name": "Bacoor"}
        ],
        "other_names": ["Bakood", "City of Bacoor"]
    },
    {
        "key": "Kratié-Cambodia",
        "canonical_name": "Kratie",
        "foundation_year": 1907,
        "historical_names": [
            {"date": "1800.1.1", "name": "Kracheh"},
            {"date": "1907.1.1", "name": "Kratie"}
        ],
        "other_names": ["ក្រចេះ", "Kratié", "Kracheh"]
    },
    {
        "key": "Chin State-Myanmar",
        "canonical_name": "Chin State",
        "foundation_year": 1948,
        "historical_names": [
            {"date": "1896.1.1", "name": "Chin Hills"},
            {"date": "1948.1.4", "name": "Chin Special Division"},
            {"date": "1974.1.3", "name": "Chin State"}
        ],
        "other_names": ["ချင်းပြည်နယ်", "Chin Hills", "Hakha"]
    },
    {
        "key": "Setapak-Malaysia",
        "canonical_name": "Setapak",
        "foundation_year": None,
        "historical_names": [
            {"date": "1880.1.1", "name": "Setapak"}
        ],
        "other_names": ["Mukim Setapak", "Kuala Lumpur"]
    },
    {
        "key": "North Luwu-Indonesia",
        "canonical_name": "North Luwu",
        "foundation_year": 1999,
        "historical_names": [
            {"date": "1999.4.27", "name": "North Luwu"}
        ],
        "other_names": ["Luwu Utara", "Kabupaten Luwu Utara", "Masamba"]
    },
    {
        "key": "Muaro Jambi-Indonesia",
        "canonical_name": "Muaro Jambi",
        "foundation_year": 700,
        "historical_names": [
            {"date": "700.1.1", "name": "Melayu"},
            {"date": "1999.10.4", "name": "Muaro Jambi"}
        ],
        "other_names": ["Candi Muaro Jambi", "Kabupaten Muaro Jambi", "Melayu"]
    },
    {
        "key": "Udomsai-Laos",
        "canonical_name": "Oudomxay",
        "foundation_year": 1958,
        "historical_names": [
            {"date": "1958.1.1", "name": "Ban Hin Heub"},
            {"date": "1969.1.1", "name": "Oudomxay"}
        ],
        "other_names": ["ອຸດົມໄຊ", "Udomxai", "Muang Xay", "Oudomxay"]
    },
    {
        "key": "Iligan-Philippines",
        "canonical_name": "Iligan",
        "foundation_year": 1609,
        "historical_names": [
            {"date": "1609.1.1", "name": "San Miguel de Iligan"},
            {"date": "1950.6.16", "name": "Iligan"}
        ],
        "other_names": ["Iligan City", "City of Iligan", "Bayug"]
    },
    {
        "key": "Bang Kapi-Thailand",
        "canonical_name": "Bang Kapi",
        "foundation_year": 1937,
        "historical_names": [
            {"date": "1937.1.1", "name": "Bang Kapi"}
        ],
        "other_names": ["บางกะปิ", "Bangkapi"]
    },
    {
        "key": "Merangin-Indonesia",
        "canonical_name": "Merangin",
        "foundation_year": 1999,
        "historical_names": [
            {"date": "1958.1.1", "name": "Sarolangun Bangko"},
            {"date": "1999.10.4", "name": "Merangin"}
        ],
        "other_names": ["Kabupaten Merangin", "Bangko"]
    },
    {
        "key": "Gombak-Malaysia",
        "canonical_name": "Gombak",
        "foundation_year": 1974,
        "historical_names": [
            {"date": "1880.1.1", "name": "Sungai Gombak"},
            {"date": "1974.2.1", "name": "Gombak"}
        ],
        "other_names": ["Daerah Gombak", "Batu Caves"]
    },
    {
        "key": "San Pedro-Philippines",
        "canonical_name": "San Pedro",
        "foundation_year": 1725,
        "historical_names": [
            {"date": "1725.1.1", "name": "San Pedro de Tunasang"},
            {"date": "1902.1.1", "name": "San Pedro"}
        ],
        "other_names": ["San Pedro Laguna", "San Pedro City"]
    },
    {
        "key": "Mandaue-Philippines",
        "canonical_name": "Mandaue",
        "foundation_year": 1599,
        "historical_names": [
            {"date": "1521.1.1", "name": "Mandani"},
            {"date": "1599.1.1", "name": "Mandaue"},
            {"date": "1969.6.21", "name": "Mandaue"}
        ],
        "other_names": ["Mandani", "Mandaue City", "City of Mandaue"]
    },
    {
        "key": "Batu Bara-Indonesia",
        "canonical_name": "Batu Bara",
        "foundation_year": 2007,
        "historical_names": [
            {"date": "1700.1.1", "name": "Batu Bara"},
            {"date": "2007.1.2", "name": "Batu Bara"}
        ],
        "other_names": ["Batubara", "Kabupaten Batu Bara", "Lima Laras"]
    },
    {
        "key": "Salavan-Laos",
        "canonical_name": "Salavan",
        "foundation_year": None,
        "historical_names": [
            {"date": "1893.1.1", "name": "Saravane"},
            {"date": "1949.7.19", "name": "Salavan"}
        ],
        "other_names": ["ສາລະວັນ", "Saravane", "Saravan"]
    },
    {
        "key": "Pasar Kemis-Indonesia",
        "canonical_name": "Pasar Kemis",
        "foundation_year": None,
        "historical_names": [
            {"date": "1950.1.1", "name": "Pasar Kemis"}
        ],
        "other_names": ["Pasarkemis", "Tangerang"]
    },
    {
        "key": "Long Bien-Vietnam",
        "canonical_name": "Long Bien",
        "foundation_year": 544,
        "historical_names": [
            {"date": "544.1.1", "name": "Long Bien"},
            {"date": "2003.11.6", "name": "Long Bien"}
        ],
        "other_names": ["Long Biên", "Longbian"]
    },
    {
        "key": "Cabanatuan City-Philippines",
        "canonical_name": "Cabanatuan",
        "foundation_year": 1777,
        "historical_names": [
            {"date": "1777.1.1", "name": "Cabanatuan"},
            {"date": "1950.6.16", "name": "Cabanatuan"}
        ],
        "other_names": ["Cabanatuan City", "City of Cabanatuan"]
    },
    {
        "key": "Tebet-Indonesia",
        "canonical_name": "Tebet",
        "foundation_year": 1960,
        "historical_names": [
            {"date": "1960.1.1", "name": "Tebet"}
        ],
        "other_names": ["Kecamatan Tebet", "Jakarta Selatan"]
    },
    {
        "key": "Chai Nat-Thailand",
        "canonical_name": "Chai Nat",
        "foundation_year": None,
        "historical_names": [
            {"date": "1357.1.1", "name": "Phraek Si Racha"},
            {"date": "1450.1.1", "name": "Chai Nat"}
        ],
        "other_names": ["ชัยนาท", "Chainat", "Phraek Si Racha"]
    },
    {
        "key": "Roman Catholic Diocese of Mindat-Myanmar",
        "canonical_name": "Mindat",
        "foundation_year": None,
        "historical_names": [
            {"date": "1948.1.1", "name": "Mindat"}
        ],
        "other_names": ["မင်းတပ်", "Mindat Chin Hills"]
    },
    {
        "key": "Mukdahan-Thailand",
        "canonical_name": "Mukdahan",
        "foundation_year": 1770,
        "historical_names": [
            {"date": "1770.1.1", "name": "Ban Luang Phonsai"},
            {"date": "1778.1.1", "name": "Mukdahan"},
            {"date": "1982.9.27", "name": "Mukdahan"}
        ],
        "other_names": ["มุกดาหาร", "Mookdahan"]
    },
    {
        "key": "Muar-Malaysia",
        "canonical_name": "Muar",
        "foundation_year": 1885,
        "historical_names": [
            {"date": "1365.1.1", "name": "Muar"},
            {"date": "1885.8.12", "name": "Bandar Maharani"},
            {"date": "1957.8.31", "name": "Muar"}
        ],
        "other_names": ["Bandar Maharani", "Bandar Maharani Bandar Diraja"]
    },
    {
        "key": "Bac Tu Liem-Vietnam",
        "canonical_name": "Bac Tu Liem",
        "foundation_year": 2013,
        "historical_names": [
            {"date": "1000.1.1", "name": "Tu Liem"},
            {"date": "2013.12.27", "name": "Bac Tu Liem"}
        ],
        "other_names": ["Bắc Từ Liêm", "Từ Liêm", "Tu Liem"]
    },
    {
        "key": "Tanah Laut-Indonesia",
        "canonical_name": "Tanah Laut",
        "foundation_year": 1965,
        "historical_names": [
            {"date": "1860.1.1", "name": "Tanah Laoet"},
            {"date": "1965.12.2", "name": "Tanah Laut"}
        ],
        "other_names": ["Tanah Laoet", "Kabupaten Tanah Laut", "Pelaihari"]
    },
    {
        "key": "Kotabaru-Indonesia",
        "canonical_name": "Kotabaru",
        "foundation_year": None,
        "historical_names": [
            {"date": "1850.1.1", "name": "Kota Baroe"},
            {"date": "1950.1.1", "name": "Kotabaru"}
        ],
        "other_names": ["Kota Baru", "Kota Baroe", "Pulau Laut"]
    },
    {
        "key": "Bangka-Indonesia",
        "canonical_name": "Bangka",
        "foundation_year": None,
        "historical_names": [
            {"date": "686.1.1", "name": "Kota Kapur"},
            {"date": "1710.1.1", "name": "Banka"},
            {"date": "1945.8.17", "name": "Bangka"}
        ],
        "other_names": ["Banka", "Pulau Bangka", "Sungailiat"]
    },
    {
        "key": "North Bekasi-Indonesia",
        "canonical_name": "North Bekasi",
        "foundation_year": 1981,
        "historical_names": [
            {"date": "1981.1.1", "name": "North Bekasi"}
        ],
        "other_names": ["Bekasi Utara", "Kota Bekasi"]
    },
    {
        "key": "Kluang-Malaysia",
        "canonical_name": "Kluang",
        "foundation_year": 1915,
        "historical_names": [
            {"date": "1915.1.1", "name": "Kluang"}
        ],
        "other_names": ["Kluang Johor", "Keluan"]
    },
    {
        "key": "Tebo-Indonesia",
        "canonical_name": "Tebo",
        "foundation_year": 1999,
        "historical_names": [
            {"date": "1800.1.1", "name": "Muara Tebo"},
            {"date": "1999.10.4", "name": "Tebo"}
        ],
        "other_names": ["Kabupaten Tebo", "Muara Tebo"]
    },
    {
        "key": "Tanza-Philippines",
        "canonical_name": "Tanza",
        "foundation_year": 1760,
        "historical_names": [
            {"date": "1760.1.1", "name": "Santa Cruz de Malabon"},
            {"date": "1914.2.28", "name": "Tanza"}
        ],
        "other_names": ["Santa Cruz de Malabon"]
    },
    {
        "key": "Kuantan Singingi-Indonesia",
        "canonical_name": "Kuantan Singingi",
        "foundation_year": 1999,
        "historical_names": [
            {"date": "1800.1.1", "name": "Teluk Kuantan"},
            {"date": "1999.10.4", "name": "Kuantan Singingi"}
        ],
        "other_names": ["Kuansing", "Teluk Kuantan", "Kabupaten Kuantan Singingi"]
    },
    {
        "key": "Empat Lawang-Indonesia",
        "canonical_name": "Empat Lawang",
        "foundation_year": 2007,
        "historical_names": [
            {"date": "1870.1.1", "name": "Tebing Tinggi"},
            {"date": "2007.1.2", "name": "Empat Lawang"}
        ],
        "other_names": ["Kabupaten Empat Lawang", "Tebing Tinggi"]
    },
    {
        "key": "Bolikhamsai-Laos",
        "canonical_name": "Bolikhamsai",
        "foundation_year": 1986,
        "historical_names": [
            {"date": "1986.1.1", "name": "Bolikhamsai"}
        ],
        "other_names": ["ບໍລິຄຳໄຊ", "Borikhamxay", "Paksan"]
    },
    {
        "key": "Sikka-Indonesia",
        "canonical_name": "Sikka",
        "foundation_year": 1607,
        "historical_names": [
            {"date": "1607.1.1", "name": "Sikka"},
            {"date": "1958.1.1", "name": "Sikka"}
        ],
        "other_names": ["Kabupaten Sikka", "Maumere"]
    },
    {
        "key": "Phra Pradaeng-Thailand",
        "canonical_name": "Phra Pradaeng",
        "foundation_year": 1815,
        "historical_names": [
            {"date": "1815.1.1", "name": "Nakhon Khuean Khan"},
            {"date": "1915.1.1", "name": "Phra Pradaeng"}
        ],
        "other_names": ["พระประแดง", "Nakhon Khuean Khan"]
    },
    {
        "key": "Pak Chong-Thailand",
        "canonical_name": "Pak Chong",
        "foundation_year": 1898,
        "historical_names": [
            {"date": "1898.1.1", "name": "Pak Chong"}
        ],
        "other_names": ["ปากช่อง", "Nakhon Ratchasima"]
    },
    {
        "key": "Bang Lamung-Thailand",
        "canonical_name": "Bang Lamung",
        "foundation_year": 1901,
        "historical_names": [
            {"date": "1901.1.1", "name": "Bang Lamung"}
        ],
        "other_names": ["บางละมุง", "Pattaya"]
    },
    {
        "key": "Pasar Minggu-Indonesia",
        "canonical_name": "Pasar Minggu",
        "foundation_year": None,
        "historical_names": [
            {"date": "1930.1.1", "name": "Pasar Minggoe"},
            {"date": "1950.1.1", "name": "Pasar Minggu"}
        ],
        "other_names": ["Pasar Minggoe", "Jakarta Selatan"]
    },
    {
        "key": "Sidenreng Rappang-Indonesia",
        "canonical_name": "Sidenreng Rappang",
        "foundation_year": 1400,
        "historical_names": [
            {"date": "1400.1.1", "name": "Sidenreng"},
            {"date": "1960.1.28", "name": "Sidenreng Rappang"}
        ],
        "other_names": ["Sidrap", "Kabupaten Sidenreng Rappang"]
    },
    {
        "key": "West Tanjung Jabung-Indonesia",
        "canonical_name": "West Tanjung Jabung",
        "foundation_year": 1999,
        "historical_names": [
            {"date": "1999.10.4", "name": "West Tanjung Jabung"}
        ],
        "other_names": ["Tanjung Jabung Barat", "Kuala Tungkal"]
    },
    {
        "key": "Hūaphan-Laos",
        "canonical_name": "Huaphan",
        "foundation_year": None,
        "historical_names": [
            {"date": "1479.1.1", "name": "Muang Phuan"},
            {"date": "1893.1.1", "name": "Houaphanh"},
            {"date": "1949.7.19", "name": "Huaphan"}
        ],
        "other_names": ["ຫົວພັນ", "Houaphanh", "Sam Neua", "Houa Phan"]
    },
    {
        "key": "Bắc Kạn-Vietnam",
        "canonical_name": "Bac Kan",
        "foundation_year": 1900,
        "historical_names": [
            {"date": "1900.4.11", "name": "Bac Kan"}
        ],
        "other_names": ["Bắc Kạn", "Bac Can", "Bắc Cạn"]
    },
    {
        "key": "Hoa Lu-Vietnam",
        "canonical_name": "Hoa Lu",
        "foundation_year": 968,
        "historical_names": [
            {"date": "968.1.1", "name": "Hoa Lu"},
            {"date": "1010.1.1", "name": "Hoa Lu"}
        ],
        "other_names": ["Hoa Lư", "Đại Cồ Việt", "Ninh Bình"]
    }
]

out_b13 = {
    "batch_index": 13,
    "settlements": b13_settlements
}

target_path_13 = os.path.join(TARGET_DIR, "resolved_batch_13.json")
with open(target_path_13, "w", encoding="utf-8") as f:
    json.dump(out_b13, f, indent=2, ensure_ascii=False)
print(f"Wrote resolved_batch_13.json with {len(b13_settlements)} settlements")
