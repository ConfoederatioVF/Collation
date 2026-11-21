import os
import json

TARGET_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MANDALA\_shared\toponymy_batches"

b15_settlements = [
    {
        "key": "Bahnar people-Vietnam",
        "canonical_name": "Bahnar",
        "foundation_year": None,
        "historical_names": [
            {"date": "1000.1.1", "name": "Bahnar"}
        ],
        "other_names": ["Ba Na", "Người Ba Na", "Bahnar"]
    },
    {
        "key": "Vĩnh Phúc-Vietnam",
        "canonical_name": "Vinh Phuc",
        "foundation_year": 1950,
        "historical_names": [
            {"date": "1890.1.1", "name": "Vinh Yen"},
            {"date": "1950.2.12", "name": "Vinh Phuc"}
        ],
        "other_names": ["Vĩnh Phúc", "Vĩnh Yên", "Phúc Yên"]
    },
    {
        "key": "Cainta-Philippines",
        "canonical_name": "Cainta",
        "foundation_year": 1571,
        "historical_names": [
            {"date": "1571.1.1", "name": "Cainta"}
        ],
        "other_names": ["Municipality of Cainta", "Rizal"]
    },
    {
        "key": "Kayah State-Myanmar",
        "canonical_name": "Kayah State",
        "foundation_year": 1951,
        "historical_names": [
            {"date": "1875.6.21", "name": "Karenni States"},
            {"date": "1948.1.4", "name": "Karenni State"},
            {"date": "1951.10.5", "name": "Kayah State"}
        ],
        "other_names": ["ကယားပြည်နယ်", "Karenni State", "Loikaw"]
    },
    {
        "key": "Aceh Tamiang-Indonesia",
        "canonical_name": "Aceh Tamiang",
        "foundation_year": 2002,
        "historical_names": [
            {"date": "1225.1.1", "name": "Tumihang"},
            {"date": "1956.1.1", "name": "Aceh Timur"},
            {"date": "2002.4.10", "name": "Aceh Tamiang"}
        ],
        "other_names": ["Kabupaten Aceh Tamiang", "Tamiang", "Karang Baru"]
    },
    {
        "key": "Binjai-Indonesia",
        "canonical_name": "Binjai",
        "foundation_year": 1872,
        "historical_names": [
            {"date": "1872.1.1", "name": "Bindjai"},
            {"date": "1945.8.17", "name": "Binjai"}
        ],
        "other_names": ["Bindjai", "Kota Binjai"]
    },
    {
        "key": "Paser-Indonesia",
        "canonical_name": "Paser",
        "foundation_year": 1516,
        "historical_names": [
            {"date": "1516.1.1", "name": "Sadurengas"},
            {"date": "1959.1.1", "name": "Pasir"},
            {"date": "2007.2.14", "name": "Paser"}
        ],
        "other_names": ["Pasir", "Sadurengas", "Tanah Grogot", "Kabupaten Paser"]
    },
    {
        "key": "Bengkayang-Indonesia",
        "canonical_name": "Bengkayang",
        "foundation_year": 1999,
        "historical_names": [
            {"date": "1850.1.1", "name": "Bengkajang"},
            {"date": "1999.4.20", "name": "Bengkayang"}
        ],
        "other_names": ["Kabupaten Bengkayang"]
    },
    {
        "key": "Ba Vi-Vietnam",
        "canonical_name": "Ba Vi",
        "foundation_year": None,
        "historical_names": [
            {"date": "1000.1.1", "name": "Ba Vi"}
        ],
        "other_names": ["Ba Vì", "Núi Tản Viên", "Hà Tây"]
    },
    {
        "key": "Ulu Bedok-Singapore",
        "canonical_name": "Ulu Bedok",
        "foundation_year": None,
        "historical_names": [
            {"date": "1850.1.1", "name": "Bedok"},
            {"date": "1960.1.1", "name": "Ulu Bedok"}
        ],
        "other_names": ["Bedok", "Kampong Ulu Bedok"]
    },
    {
        "key": "Tana Toraja-Indonesia",
        "canonical_name": "Tana Toraja",
        "foundation_year": 1957,
        "historical_names": [
            {"date": "1906.1.1", "name": "Boven-Bidoeng"},
            {"date": "1957.1.1", "name": "Tana Toraja"}
        ],
        "other_names": ["Toraja", "Makale", "Rantepao", "Kabupaten Tana Toraja"]
    },
    {
        "key": "Pematangsiantar-Indonesia",
        "canonical_name": "Pematangsiantar",
        "foundation_year": 1871,
        "historical_names": [
            {"date": "1871.1.1", "name": "Siantar"},
            {"date": "1917.7.1", "name": "Pematang Siantar"},
            {"date": "1945.8.17", "name": "Pematangsiantar"}
        ],
        "other_names": ["Pematang Siantar", "Siantar", "Kota Pematangsiantar"]
    },
    {
        "key": "North Tapanuli-Indonesia",
        "canonical_name": "North Tapanuli",
        "foundation_year": 1956,
        "historical_names": [
            {"date": "1860.1.1", "name": "Silindoeng"},
            {"date": "1956.1.1", "name": "North Tapanuli"}
        ],
        "other_names": ["Tapanuli Utara", "Tarutung", "Silindung"]
    },
    {
        "key": "West Bekasi-Indonesia",
        "canonical_name": "West Bekasi",
        "foundation_year": 1981,
        "historical_names": [
            {"date": "1981.1.1", "name": "West Bekasi"}
        ],
        "other_names": ["Bekasi Barat", "Kota Bekasi"]
    },
    {
        "key": "East Flores-Indonesia",
        "canonical_name": "East Flores",
        "foundation_year": 1958,
        "historical_names": [
            {"date": "1600.1.1", "name": "Larantoeka"},
            {"date": "1958.1.1", "name": "East Flores"}
        ],
        "other_names": ["Flores Timur", "Larantuka"]
    },
    {
        "key": "Baleendah-Indonesia",
        "canonical_name": "Baleendah",
        "foundation_year": None,
        "historical_names": [
            {"date": "1970.1.1", "name": "Baleendah"}
        ],
        "other_names": ["Kecamatan Baleendah", "Bandung"]
    },
    {
        "key": "Suan Luang-Thailand",
        "canonical_name": "Suan Luang",
        "foundation_year": 1994,
        "historical_names": [
            {"date": "1994.1.14", "name": "Suan Luang"}
        ],
        "other_names": ["สวนหลวง", "Prawet"]
    },
    {
        "key": "Ende-Indonesia",
        "canonical_name": "Ende",
        "foundation_year": 1638,
        "historical_names": [
            {"date": "1638.1.1", "name": "Ende"},
            {"date": "1958.1.1", "name": "Ende"}
        ],
        "other_names": ["Kota Ende", "Kabupaten Ende"]
    },
    {
        "key": "Chukai-Malaysia",
        "canonical_name": "Chukai",
        "foundation_year": None,
        "historical_names": [
            {"date": "1850.1.1", "name": "Chukai"}
        ],
        "other_names": ["Cukai", "Kemaman"]
    },
    {
        "key": "Baguio-Philippines",
        "canonical_name": "Baguio",
        "foundation_year": 1900,
        "historical_names": [
            {"date": "1800.1.1", "name": "Kafagway"},
            {"date": "1900.1.1", "name": "Baguio"},
            {"date": "1909.9.1", "name": "City of Baguio"},
            {"date": "1946.7.4", "name": "Baguio"}
        ],
        "other_names": ["Baguio City", "Kafagway", "Summer Capital"]
    },
    {
        "key": "Xiangkhouang-Laos",
        "canonical_name": "Xiangkhouang",
        "foundation_year": None,
        "historical_names": [
            {"date": "1353.1.1", "name": "Muang Phuan"},
            {"date": "1893.1.1", "name": "Xieng Khouang"},
            {"date": "1975.12.2", "name": "Xiangkhouang"}
        ],
        "other_names": ["ຊຽງຂວາງ", "Xieng Khouang", "Xiengkhouang", "Phonsavan", "Muang Phuan"]
    },
    {
        "key": "Banda Aceh-Indonesia",
        "canonical_name": "Banda Aceh",
        "foundation_year": 1496,
        "historical_names": [
            {"date": "1496.4.22", "name": "Bandar Aceh Darussalam"},
            {"date": "1874.1.24", "name": "Kota Radja"},
            {"date": "1945.8.17", "name": "Kutaraja"},
            {"date": "1962.12.28", "name": "Banda Aceh"}
        ],
        "other_names": ["Kutaraja", "Kota Radja", "Bandar Aceh Darussalam", "Kota Banda Aceh"]
    },
    {
        "key": "Dairi-Indonesia",
        "canonical_name": "Dairi",
        "foundation_year": 1964,
        "historical_names": [
            {"date": "1947.1.1", "name": "Dairi"},
            {"date": "1964.1.1", "name": "Dairi"}
        ],
        "other_names": ["Kabupaten Dairi", "Sidikalang", "Pakpak"]
    },
    {
        "key": "Nong Khaem-Thailand",
        "canonical_name": "Nong Khaem",
        "foundation_year": 1902,
        "historical_names": [
            {"date": "1902.1.1", "name": "Nong Khaem"}
        ],
        "other_names": ["หนองแขม", "Nongkhem"]
    },
    {
        "key": "Malolos-Philippines",
        "canonical_name": "Malolos",
        "foundation_year": 1580,
        "historical_names": [
            {"date": "1580.1.1", "name": "Malolos"},
            {"date": "1898.9.15", "name": "Malolos"},
            {"date": "2001.12.18", "name": "Malolos"}
        ],
        "other_names": ["Malolos City", "City of Malolos", "Barasoain"]
    },
    {
        "key": "Kapar-Malaysia",
        "canonical_name": "Kapar",
        "foundation_year": None,
        "historical_names": [
            {"date": "1900.1.1", "name": "Kapar"}
        ],
        "other_names": ["Mukim Kapar", "Klang"]
    },
    {
        "key": "Mae Hong Son-Thailand",
        "canonical_name": "Mae Hong Son",
        "foundation_year": 1831,
        "historical_names": [
            {"date": "1831.1.1", "name": "Mae Rong Son"},
            {"date": "1874.1.1", "name": "Mae Hong Son"}
        ],
        "other_names": ["แม่ฮ่องสอน", "Maehongson", "Muang Mae Hong Son"]
    },
    {
        "key": "Rejang Lebong-Indonesia",
        "canonical_name": "Rejang Lebong",
        "foundation_year": 1956,
        "historical_names": [
            {"date": "1860.1.1", "name": "Redjang-Lebong"},
            {"date": "1956.1.1", "name": "Rejang Lebong"}
        ],
        "other_names": ["Kabupaten Rejang Lebong", "Curup"]
    },
    {
        "key": "Tampines Estate-Singapore",
        "canonical_name": "Tampines",
        "foundation_year": None,
        "historical_names": [
            {"date": "1828.1.1", "name": "Tampines"},
            {"date": "1978.1.1", "name": "Tampines"}
        ],
        "other_names": ["Tampines Estate", "Tampines New Town"]
    },
    {
        "key": "Ha Long-Vietnam",
        "canonical_name": "Ha Long",
        "foundation_year": 1993,
        "historical_names": [
            {"date": "1883.1.1", "name": "Hon Gai"},
            {"date": "1993.12.27", "name": "Ha Long"}
        ],
        "other_names": ["Hạ Long", "Hòn Gai", "Hồng Gai", "Ha Long City"]
    },
    {
        "key": "Ang Thong-Thailand",
        "canonical_name": "Ang Thong",
        "foundation_year": None,
        "historical_names": [
            {"date": "1350.1.1", "name": "Wiset Chai Chan"},
            {"date": "1782.1.1", "name": "Ang Thong"}
        ],
        "other_names": ["อ่างทอง", "Angthong", "Wiset Chai Chan"]
    },
    {
        "key": "Banjar Baru-Indonesia",
        "canonical_name": "Banjar Baru",
        "foundation_year": 1951,
        "historical_names": [
            {"date": "1951.7.9", "name": "Banjarbaru"},
            {"date": "1999.4.20", "name": "Banjar Baru"}
        ],
        "other_names": ["Banjarbaru", "Kota Banjarbaru"]
    },
    {
        "key": "Jurong Town-Singapore",
        "canonical_name": "Jurong",
        "foundation_year": 1961,
        "historical_names": [
            {"date": "1828.1.1", "name": "Jurong"},
            {"date": "1968.6.1", "name": "Jurong"}
        ],
        "other_names": ["Jurong Town", "Jurong Industrial Estate"]
    },
    {
        "key": "Kolaka-Indonesia",
        "canonical_name": "Kolaka",
        "foundation_year": 1960,
        "historical_names": [
            {"date": "1600.1.1", "name": "Mekongga"},
            {"date": "1960.2.8", "name": "Kolaka"}
        ],
        "other_names": ["Kabupaten Kolaka", "Mekongga"]
    },
    {
        "key": "Mantampay-Philippines",
        "canonical_name": "Mantampay",
        "foundation_year": None,
        "historical_names": [
            {"date": "1950.1.1", "name": "Mantampay"}
        ],
        "other_names": ["Barangay Mantampay", "Baloi"]
    },
    {
        "key": "Lam Luk Ka-Thailand",
        "canonical_name": "Lam Luk Ka",
        "foundation_year": 1902,
        "historical_names": [
            {"date": "1902.1.1", "name": "Lam Luk Ka"}
        ],
        "other_names": ["ลำลูกกา", "Lamlukka"]
    },
    {
        "key": "South Tapanuli-Indonesia",
        "canonical_name": "South Tapanuli",
        "foundation_year": 1956,
        "historical_names": [
            {"date": "1840.1.1", "name": "Residentie Tapanoeli"},
            {"date": "1956.1.1", "name": "South Tapanuli"}
        ],
        "other_names": ["Tapanuli Selatan", "Tapsel", "Sipirok"]
    },
    {
        "key": "Bang Bua Thong-Thailand",
        "canonical_name": "Bang Bua Thong",
        "foundation_year": 1902,
        "historical_names": [
            {"date": "1902.1.1", "name": "Bang Bua Thong"}
        ],
        "other_names": ["บางบัวทอง", "Bangbuathong"]
    },
    {
        "key": "North Padang Lawas-Indonesia",
        "canonical_name": "North Padang Lawas",
        "foundation_year": 2007,
        "historical_names": [
            {"date": "1025.1.1", "name": "Pannai"},
            {"date": "2007.8.10", "name": "North Padang Lawas"}
        ],
        "other_names": ["Paluta", "Padang Lawas Utara", "Gunung Tua"]
    },
    {
        "key": "Oddar Meanchey-Cambodia",
        "canonical_name": "Oddar Meanchey",
        "foundation_year": 1966,
        "historical_names": [
            {"date": "1966.1.1", "name": "Otdar Mean Chey"},
            {"date": "1995.1.1", "name": "Oddar Meanchey"}
        ],
        "other_names": ["ឧត្តរមានជ័យ", "Otdar Mean Chey", "Samraong"]
    },
    {
        "key": "Bagong Silang-Philippines",
        "canonical_name": "Bagong Silang",
        "foundation_year": 1971,
        "historical_names": [
            {"date": "1971.1.1", "name": "Bagong Silang"}
        ],
        "other_names": ["Barangay 176", "Caloocan"]
    },
    {
        "key": "Bangli-Indonesia",
        "canonical_name": "Bangli",
        "foundation_year": 1204,
        "historical_names": [
            {"date": "1204.1.1", "name": "Bangli"},
            {"date": "1958.1.1", "name": "Bangli"}
        ],
        "other_names": ["Kerajaan Bangli", "Kabupaten Bangli"]
    },
    {
        "key": "North Bengkulu-Indonesia",
        "canonical_name": "North Bengkulu",
        "foundation_year": 1956,
        "historical_names": [
            {"date": "1685.1.1", "name": "Bencoolen"},
            {"date": "1956.1.1", "name": "North Bengkulu"}
        ],
        "other_names": ["Bengkulu Utara", "Arga Makmur", "Bencoolen"]
    },
    {
        "key": "Phang Nga-Thailand",
        "canonical_name": "Phang Nga",
        "foundation_year": 1809,
        "historical_names": [
            {"date": "1809.1.1", "name": "Kraphu Nga"},
            {"date": "1840.1.1", "name": "Phang Nga"}
        ],
        "other_names": ["พังงา", "Phangnga", "Kraphu Nga"]
    },
    {
        "key": "Marawi City-Philippines",
        "canonical_name": "Marawi City",
        "foundation_year": 1639,
        "historical_names": [
            {"date": "1639.1.1", "name": "Marawi"},
            {"date": "1907.5.24", "name": "Dansalan"},
            {"date": "1956.6.16", "name": "Marawi City"}
        ],
        "other_names": ["Dansalan", "Marawi", "Islamic City of Marawi"]
    }
]

out_b15 = {
    "batch_index": 15,
    "settlements": b15_settlements
}

target_path_15 = os.path.join(TARGET_DIR, "resolved_batch_15.json")
with open(target_path_15, "w", encoding="utf-8") as f:
    json.dump(out_b15, f, indent=2, ensure_ascii=False)
print(f"Wrote resolved_batch_15.json with {len(b15_settlements)} settlements")
