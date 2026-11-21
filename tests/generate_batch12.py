import os
import json

TARGET_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MANDALA\_shared\toponymy_batches"

b12_settlements = [
    {
        "key": "Siak-Indonesia",
        "canonical_name": "Siak",
        "foundation_year": 1723,
        "historical_names": [
            {"date": "1723.1.1", "name": "Siak Sri Indrapura"},
            {"date": "1999.10.4", "name": "Siak"}
        ],
        "other_names": ["Siak Sri Indrapura", "Kabupaten Siak"]
    },
    {
        "key": "South Ogan Komering Ulu-Indonesia",
        "canonical_name": "South Ogan Komering Ulu",
        "foundation_year": 2003,
        "historical_names": [
            {"date": "2003.12.18", "name": "South Ogan Komering Ulu"}
        ],
        "other_names": ["OKU Selatan", "Muaradua", "Kabupaten Ogan Komering Ulu Selatan"]
    },
    {
        "key": "Jeneponto-Indonesia",
        "canonical_name": "Jeneponto",
        "foundation_year": None,
        "historical_names": [
            {"date": "1600.1.1", "name": "Binamu"},
            {"date": "1960.1.1", "name": "Jeneponto"}
        ],
        "other_names": ["Binamu", "Kabupaten Jeneponto"]
    },
    {
        "key": "Jagakarsa-Indonesia",
        "canonical_name": "Jagakarsa",
        "foundation_year": 1527,
        "historical_names": [
            {"date": "1527.1.1", "name": "Jagakarsa"}
        ],
        "other_names": ["Kecamatan Jagakarsa", "Jakarta Selatan"]
    },
    {
        "key": "Mandailing Natal-Indonesia",
        "canonical_name": "Mandailing Natal",
        "foundation_year": 1998,
        "historical_names": [
            {"date": "1838.1.1", "name": "Mandheling en Natal"},
            {"date": "1998.11.23", "name": "Mandailing Natal"}
        ],
        "other_names": ["Madina", "Panyabungan", "Kabupaten Mandailing Natal"]
    },
    {
        "key": "Bueng Kan-Thailand",
        "canonical_name": "Bueng Kan",
        "foundation_year": 2011,
        "historical_names": [
            {"date": "1916.1.1", "name": "Bueng Kan"},
            {"date": "2011.3.23", "name": "Bueng Kan"}
        ],
        "other_names": ["บึงกาฬ", "Bung Kan"]
    },
    {
        "key": "East Kotawaringin-Indonesia",
        "canonical_name": "East Kotawaringin",
        "foundation_year": None,
        "historical_names": [
            {"date": "1615.1.1", "name": "Kotawaringin"},
            {"date": "1950.1.1", "name": "East Kotawaringin"}
        ],
        "other_names": ["Kotawaringin Timur", "Sampit", "Kabupaten Kotawaringin Timur"]
    },
    {
        "key": "Pangandaran-Indonesia",
        "canonical_name": "Pangandaran",
        "foundation_year": None,
        "historical_names": [
            {"date": "1922.1.1", "name": "Pangandaran"},
            {"date": "2012.11.17", "name": "Pangandaran"}
        ],
        "other_names": ["Kabupaten Pangandaran", "Pananjung"]
    },
    {
        "key": "Tarlac City-Philippines",
        "canonical_name": "Tarlac City",
        "foundation_year": 1788,
        "historical_names": [
            {"date": "1788.1.1", "name": "Tarlac"},
            {"date": "1899.6.21", "name": "Tarlac"},
            {"date": "1998.4.18", "name": "Tarlac City"}
        ],
        "other_names": ["Tarlac", "City of Tarlac"]
    },
    {
        "key": "Pursat-Cambodia",
        "canonical_name": "Pursat",
        "foundation_year": 1907,
        "historical_names": [
            {"date": "1500.1.1", "name": "Pouthisat"},
            {"date": "1907.3.23", "name": "Pursat"}
        ],
        "other_names": ["ពោធិ៍សាត់", "Pouthisat", "Khaet Pouthisat"]
    },
    {
        "key": "Seremban-Malaysia",
        "canonical_name": "Seremban",
        "foundation_year": 1874,
        "historical_names": [
            {"date": "1840.1.1", "name": "Sungai Ujong"},
            {"date": "1896.1.1", "name": "Seremban"}
        ],
        "other_names": ["Sungai Ujong", "Sungei Ujong"]
    },
    {
        "key": "Lahat-Indonesia",
        "canonical_name": "Lahat",
        "foundation_year": 1869,
        "historical_names": [
            {"date": "1869.1.1", "name": "Lahat"}
        ],
        "other_names": ["Kabupaten Lahat", "Pasemah"]
    },
    {
        "key": "Sintang-Indonesia",
        "canonical_name": "Sintang",
        "foundation_year": 1362,
        "historical_names": [
            {"date": "1362.1.1", "name": "Sintang"}
        ],
        "other_names": ["Kerajaan Sintang", "Kabupaten Sintang"]
    },
    {
        "key": "Bondowoso-Indonesia",
        "canonical_name": "Bondowoso",
        "foundation_year": 1819,
        "historical_names": [
            {"date": "1819.1.1", "name": "Bondowoso"}
        ],
        "other_names": ["Bondowoso Regency", "Kabupaten Bondowoso"]
    },
    {
        "key": "Maros-Indonesia",
        "canonical_name": "Maros",
        "foundation_year": 1471,
        "historical_names": [
            {"date": "1471.1.1", "name": "Marusu"},
            {"date": "1960.1.1", "name": "Maros"}
        ],
        "other_names": ["Marusu", "Kabupaten Maros"]
    },
    {
        "key": "Lamphun-Thailand",
        "canonical_name": "Lamphun",
        "foundation_year": 661,
        "historical_names": [
            {"date": "661.1.1", "name": "Hariphunchai"},
            {"date": "1281.1.1", "name": "Lamphun"}
        ],
        "other_names": ["ลำพูน", "Haripunjaya", "Hariphunchai"]
    },
    {
        "key": "Landak-Indonesia",
        "canonical_name": "Landak",
        "foundation_year": 1292,
        "historical_names": [
            {"date": "1292.1.1", "name": "Landak"},
            {"date": "1999.10.4", "name": "Landak"}
        ],
        "other_names": ["Kerajaan Landak", "Ngabang", "Kabupaten Landak"]
    },
    {
        "key": "Kendari-Indonesia",
        "canonical_name": "Kendari",
        "foundation_year": 1831,
        "historical_names": [
            {"date": "1831.5.9", "name": "Vosmaersbaai"},
            {"date": "1964.9.22", "name": "Kendari"}
        ],
        "other_names": ["Vosmaersbaai", "Kota Kendari"]
    },
    {
        "key": "Solok-Indonesia",
        "canonical_name": "Solok",
        "foundation_year": 1913,
        "historical_names": [
            {"date": "1913.12.16", "name": "Solok"}
        ],
        "other_names": ["Kota Solok", "Kabupaten Solok"]
    },
    {
        "key": "Kebonjeruk-Indonesia",
        "canonical_name": "Kebon Jeruk",
        "foundation_year": None,
        "historical_names": [
            {"date": "1950.1.1", "name": "Kebon Jeruk"}
        ],
        "other_names": ["Kebonjeruk", "Jakarta Barat"]
    },
    {
        "key": "Kelapa Dua-Indonesia",
        "canonical_name": "Kelapa Dua",
        "foundation_year": None,
        "historical_names": [
            {"date": "1950.1.1", "name": "Kelapa Dua"}
        ],
        "other_names": ["Kecamatan Kelapa Dua", "Tangerang"]
    },
    {
        "key": "Roman Catholic Diocese of Larantuka-Indonesia",
        "canonical_name": "Larantuka",
        "foundation_year": 1951,
        "historical_names": [
            {"date": "1600.1.1", "name": "Larantoeka"},
            {"date": "1951.3.8", "name": "Larantuka"}
        ],
        "other_names": ["Larantoeka", "Keuskupan Larantuka", "Flores Timur"]
    },
    {
        "key": "Thanyaburi-Thailand",
        "canonical_name": "Thanyaburi",
        "foundation_year": 1901,
        "historical_names": [
            {"date": "1901.1.1", "name": "Thanyaburi"}
        ],
        "other_names": ["ธัญบุรี", "Thanya Buri"]
    },
    {
        "key": "Bang Khae-Thailand",
        "canonical_name": "Bang Khae",
        "foundation_year": 1998,
        "historical_names": [
            {"date": "1998.3.6", "name": "Bang Khae"}
        ],
        "other_names": ["บางแค", "Bangkae"]
    },
    {
        "key": "North Labuhanbatu-Indonesia",
        "canonical_name": "North Labuhanbatu",
        "foundation_year": 2008,
        "historical_names": [
            {"date": "2008.6.24", "name": "North Labuhanbatu"}
        ],
        "other_names": ["Labuhanbatu Utara", "Labura", "Aek Kanopan"]
    },
    {
        "key": "Hòa Hưng-Vietnam",
        "canonical_name": "Hoa Hung",
        "foundation_year": None,
        "historical_names": [
            {"date": "1800.1.1", "name": "Hoa Hung"}
        ],
        "other_names": ["Hòa Hưng", "Chí Hòa", "Chi Hoa"]
    },
    {
        "key": "Great Aceh-Indonesia",
        "canonical_name": "Aceh Besar",
        "foundation_year": 1956,
        "historical_names": [
            {"date": "1500.1.1", "name": "Aceh Besar"},
            {"date": "1956.1.1", "name": "Aceh Besar"}
        ],
        "other_names": ["Great Aceh", "Aceh Besar", "Kabupaten Aceh Besar", "Jantho"]
    },
    {
        "key": "Kulon Progo-Indonesia",
        "canonical_name": "Kulon Progo",
        "foundation_year": 1951,
        "historical_names": [
            {"date": "1951.10.15", "name": "Kulon Progo"}
        ],
        "other_names": ["Kabupaten Kulon Progo", "Wates"]
    },
    {
        "key": "Puchong-Malaysia",
        "canonical_name": "Puchong",
        "foundation_year": 1980,
        "historical_names": [
            {"date": "1900.1.1", "name": "Puchong"}
        ],
        "other_names": ["Puchong Jaya", "Bandar Puchong"]
    },
    {
        "key": "Palu-Indonesia",
        "canonical_name": "Palu",
        "foundation_year": 1978,
        "historical_names": [
            {"date": "1796.1.1", "name": "Palu"},
            {"date": "1978.9.27", "name": "Palu"}
        ],
        "other_names": ["Kota Palu"]
    },
    {
        "key": "Tawau-Malaysia",
        "canonical_name": "Tawau",
        "foundation_year": 1893,
        "historical_names": [
            {"date": "1893.1.1", "name": "Tawao"},
            {"date": "1963.9.16", "name": "Tawau"}
        ],
        "other_names": ["Tawao", "Bandar Tawau"]
    },
    {
        "key": "Sam Phran-Thailand",
        "canonical_name": "Sam Phran",
        "foundation_year": None,
        "historical_names": [
            {"date": "1896.1.1", "name": "Talat Mai"},
            {"date": "1917.1.1", "name": "Sam Phran"}
        ],
        "other_names": ["สามพราน", "Talat Mai"]
    },
    {
        "key": "Chatuchak-Thailand",
        "canonical_name": "Chatuchak",
        "foundation_year": 1989,
        "historical_names": [
            {"date": "1989.9.4", "name": "Chatuchak"}
        ],
        "other_names": ["จตุจักร", "Jatujak"]
    },
    {
        "key": "Butuan-Philippines",
        "canonical_name": "Butuan",
        "foundation_year": 800,
        "historical_names": [
            {"date": "800.1.1", "name": "Butuan"},
            {"date": "1596.1.1", "name": "Butuan"},
            {"date": "1950.8.2", "name": "Butuan"}
        ],
        "other_names": ["Rajahnate of Butuan", "Butuan City", "City of Butuan"]
    },
    {
        "key": "Luwu-Indonesia",
        "canonical_name": "Luwu",
        "foundation_year": None,
        "historical_names": [
            {"date": "1200.1.1", "name": "Luwu"},
            {"date": "1953.1.1", "name": "Luwu"}
        ],
        "other_names": ["Kedatuan Luwu", "Kabupaten Luwu", "Palopo"]
    },
    {
        "key": "Lima Puluh Kota-Indonesia",
        "canonical_name": "Lima Puluh Kota",
        "foundation_year": 1841,
        "historical_names": [
            {"date": "1841.1.1", "name": "Limapoeloeh Koto"},
            {"date": "1956.1.1", "name": "Lima Puluh Kota"}
        ],
        "other_names": ["Limapuluh Kota", "Luhak Limopuluah", "Sarilamak"]
    },
    {
        "key": "Cotabato-Philippines",
        "canonical_name": "Cotabato",
        "foundation_year": 1515,
        "historical_names": [
            {"date": "1515.1.1", "name": "Kota Wato"},
            {"date": "1861.1.1", "name": "Cotabato"},
            {"date": "1959.6.20", "name": "Cotabato"}
        ],
        "other_names": ["Kota Wato", "Cotabato City", "City of Cotabato"]
    },
    {
        "key": "Amnat Charoen-Thailand",
        "canonical_name": "Amnat Charoen",
        "foundation_year": 1858,
        "historical_names": [
            {"date": "1858.1.1", "name": "Amnat Charoen"},
            {"date": "1993.12.1", "name": "Amnat Charoen"}
        ],
        "other_names": ["อำนาจเจริญ", "Muang Amnat Charoen"]
    },
    {
        "key": "Cibinong-Indonesia",
        "canonical_name": "Cibinong",
        "foundation_year": None,
        "historical_names": [
            {"date": "1950.1.1", "name": "Cibinong"}
        ],
        "other_names": ["Tjibinong", "Bogor"]
    },
    {
        "key": "Kapuas-Indonesia",
        "canonical_name": "Kapuas",
        "foundation_year": 1881,
        "historical_names": [
            {"date": "1881.1.1", "name": "Kuala Kapuas"},
            {"date": "1950.1.1", "name": "Kapuas"}
        ],
        "other_names": ["Kabupaten Kapuas", "Kuala Kapuas"]
    },
    {
        "key": "Tanah Datar-Indonesia",
        "canonical_name": "Tanah Datar",
        "foundation_year": 1347,
        "historical_names": [
            {"date": "1347.1.1", "name": "Pagaruyung"},
            {"date": "1840.1.1", "name": "Fort van der Capellen"},
            {"date": "1945.8.17", "name": "Batusangkar"},
            {"date": "1956.1.1", "name": "Tanah Datar"}
        ],
        "other_names": ["Pagaruyung", "Batusangkar", "Kabupaten Tanah Datar"]
    },
    {
        "key": "Ben Cat-Vietnam",
        "canonical_name": "Ben Cat",
        "foundation_year": None,
        "historical_names": [
            {"date": "1956.1.1", "name": "Ben Cat"},
            {"date": "2024.5.1", "name": "Ben Cat"}
        ],
        "other_names": ["Bến Cát", "Bình Dương"]
    },
    {
        "key": "Cileungsi-Indonesia",
        "canonical_name": "Cileungsi",
        "foundation_year": None,
        "historical_names": [
            {"date": "1950.1.1", "name": "Cileungsi"}
        ],
        "other_names": ["Tjileungsi", "Cileungsi Bogor"]
    },
    {
        "key": "Pangkajene and Islands-Indonesia",
        "canonical_name": "Pangkajene and Kepulauan",
        "foundation_year": 1960,
        "historical_names": [
            {"date": "1960.2.8", "name": "Pangkajene and Kepulauan"}
        ],
        "other_names": ["Pangkep", "Pangkajene dan Kepulauan", "Pangkajene"]
    },
    {
        "key": "San Jose del Monte-Philippines",
        "canonical_name": "San Jose del Monte",
        "foundation_year": 1752,
        "historical_names": [
            {"date": "1752.3.2", "name": "San Jose del Monte"},
            {"date": "2000.9.10", "name": "San Jose del Monte"}
        ],
        "other_names": ["City of San Jose del Monte", "SJDM"]
    }
]

out_b12 = {
    "batch_index": 12,
    "settlements": b12_settlements
}

target_path_12 = os.path.join(TARGET_DIR, "resolved_batch_12.json")
with open(target_path_12, "w", encoding="utf-8") as f:
    json.dump(out_b12, f, indent=2, ensure_ascii=False)
print(f"Wrote resolved_batch_12.json with {len(b12_settlements)} settlements")
