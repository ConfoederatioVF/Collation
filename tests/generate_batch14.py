import os
import json

TARGET_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MANDALA\_shared\toponymy_batches"

b14_settlements = [
    {
        "key": "South Labuhanbatu-Indonesia",
        "canonical_name": "South Labuhanbatu",
        "foundation_year": 2008,
        "historical_names": [
            {"date": "1800.1.1", "name": "Kotapinang"},
            {"date": "2008.6.24", "name": "South Labuhanbatu"}
        ],
        "other_names": ["Labuhanbatu Selatan", "Kotapinang", "Labusel"]
    },
    {
        "key": "Uthai Thani-Thailand",
        "canonical_name": "Uthai Thani",
        "foundation_year": None,
        "historical_names": [
            {"date": "1350.1.1", "name": "Muang U-Thai"},
            {"date": "1782.1.1", "name": "Uthai Thani"}
        ],
        "other_names": ["อุทัยธานี", "Muang Uthai"]
    },
    {
        "key": "Percut-Indonesia",
        "canonical_name": "Percut Sei Tuan",
        "foundation_year": None,
        "historical_names": [
            {"date": "1632.1.1", "name": "Pertjoet"},
            {"date": "1945.8.17", "name": "Percut Sei Tuan"}
        ],
        "other_names": ["Percut", "Deli Serdang"]
    },
    {
        "key": "Central Tapanuli-Indonesia",
        "canonical_name": "Central Tapanuli",
        "foundation_year": None,
        "historical_names": [
            {"date": "500.1.1", "name": "Barus"},
            {"date": "1840.1.1", "name": "Residentie Tapanoeli"},
            {"date": "1956.1.1", "name": "Central Tapanuli"}
        ],
        "other_names": ["Tapanuli Tengah", "Barus", "Sibolga", "Fansur"]
    },
    {
        "key": "Jembrana-Indonesia",
        "canonical_name": "Jembrana",
        "foundation_year": 1400,
        "historical_names": [
            {"date": "1400.1.1", "name": "Jembrana"},
            {"date": "1958.1.1", "name": "Jembrana"}
        ],
        "other_names": ["Kabupaten Jembrana", "Negara"]
    },
    {
        "key": "Cabuyao-Philippines",
        "canonical_name": "Cabuyao",
        "foundation_year": 1571,
        "historical_names": [
            {"date": "1571.1.1", "name": "Tabuco"},
            {"date": "1904.1.1", "name": "Cabuyao"}
        ],
        "other_names": ["Tabuco", "City of Cabuyao"]
    },
    {
        "key": "Babelan-Indonesia",
        "canonical_name": "Babelan",
        "foundation_year": None,
        "historical_names": [
            {"date": "1950.1.1", "name": "Babelan"}
        ],
        "other_names": ["Kecamatan Babelan", "Bekasi"]
    },
    {
        "key": "Santa Maria-Philippines",
        "canonical_name": "Santa Maria",
        "foundation_year": 1792,
        "historical_names": [
            {"date": "1792.1.1", "name": "Santa Maria de Pandi"},
            {"date": "1901.1.1", "name": "Santa Maria"}
        ],
        "other_names": ["Santa Maria Bulacan", "Santa Maria de Pandi"]
    },
    {
        "key": "Gia Lam-Vietnam",
        "canonical_name": "Gia Lam",
        "foundation_year": None,
        "historical_names": [
            {"date": "1000.1.1", "name": "Gia Lam"}
        ],
        "other_names": ["Gia Lâm", "Hà Nội"]
    },
    {
        "key": "Dumai-Indonesia",
        "canonical_name": "Dumai",
        "foundation_year": 1957,
        "historical_names": [
            {"date": "1800.1.1", "name": "Dumai"},
            {"date": "1957.1.1", "name": "Pelabuhan Dumai"},
            {"date": "1999.4.20", "name": "Dumai"}
        ],
        "other_names": ["Kota Dumai", "Riau"]
    },
    {
        "key": "Satun-Thailand",
        "canonical_name": "Satun",
        "foundation_year": 1808,
        "historical_names": [
            {"date": "1808.1.1", "name": "Setul Mambang Segara"},
            {"date": "1909.3.10", "name": "Satun"}
        ],
        "other_names": ["สตูล", "Setul", "Setul Mambang Segara"]
    },
    {
        "key": "Pamulang-Indonesia",
        "canonical_name": "Pamulang",
        "foundation_year": None,
        "historical_names": [
            {"date": "1980.1.1", "name": "Pamulang"}
        ],
        "other_names": ["Kecamatan Pamulang", "Tangerang Selatan"]
    },
    {
        "key": "Tanah Bumbu-Indonesia",
        "canonical_name": "Tanah Bumbu",
        "foundation_year": 2003,
        "historical_names": [
            {"date": "1775.1.1", "name": "Kerajaan Pagatan"},
            {"date": "2003.4.8", "name": "Tanah Bumbu"}
        ],
        "other_names": ["Pagatan", "Batulicin", "Kabupaten Tanah Bumbu"]
    },
    {
        "key": "An Nhon-Vietnam",
        "canonical_name": "An Nhon",
        "foundation_year": None,
        "historical_names": [
            {"date": "1000.1.1", "name": "Vijaya"},
            {"date": "1471.1.1", "name": "Binh Dinh"},
            {"date": "1778.1.1", "name": "Hoang De"},
            {"date": "1802.1.1", "name": "An Nhon"}
        ],
        "other_names": ["An Nhơn", "Vijaya", "Chà Bàn", "Đồ Bàn", "Hoàng Đế"]
    },
    {
        "key": "Donggala-Indonesia",
        "canonical_name": "Donggala",
        "foundation_year": None,
        "historical_names": [
            {"date": "1600.1.1", "name": "Banawa"},
            {"date": "1905.1.1", "name": "Donggala"}
        ],
        "other_names": ["Banawa", "Kabupaten Donggala"]
    },
    {
        "key": "Barito Kuala-Indonesia",
        "canonical_name": "Barito Kuala",
        "foundation_year": 1960,
        "historical_names": [
            {"date": "1800.1.1", "name": "Marabahan"},
            {"date": "1960.1.1", "name": "Barito Kuala"}
        ],
        "other_names": ["Kabupaten Barito Kuala", "Marabahan"]
    },
    {
        "key": "South Konawe-Indonesia",
        "canonical_name": "South Konawe",
        "foundation_year": 2003,
        "historical_names": [
            {"date": "1600.1.1", "name": "Konawe"},
            {"date": "2003.2.25", "name": "South Konawe"}
        ],
        "other_names": ["Konawe Selatan", "Andoolo"]
    },
    {
        "key": "Mesuji-Indonesia",
        "canonical_name": "Mesuji",
        "foundation_year": 2008,
        "historical_names": [
            {"date": "1865.1.1", "name": "Mesuji"},
            {"date": "2008.10.29", "name": "Mesuji"}
        ],
        "other_names": ["Kabupaten Mesuji"]
    },
    {
        "key": "Sarolangun-Indonesia",
        "canonical_name": "Sarolangun",
        "foundation_year": 1999,
        "historical_names": [
            {"date": "1906.1.1", "name": "Sarolangun"},
            {"date": "1999.10.4", "name": "Sarolangun"}
        ],
        "other_names": ["Kabupaten Sarolangun"]
    },
    {
        "key": "Puerto Princesa-Philippines",
        "canonical_name": "Puerto Princesa",
        "foundation_year": 1872,
        "historical_names": [
            {"date": "1872.3.4", "name": "Puerto de la Princesa"},
            {"date": "1902.1.1", "name": "Puerto Princesa"}
        ],
        "other_names": ["Puerto Princesa City", "City of Puerto Princesa"]
    },
    {
        "key": "Southwest Sumba-Indonesia",
        "canonical_name": "Southwest Sumba",
        "foundation_year": 2007,
        "historical_names": [
            {"date": "1850.1.1", "name": "Soemba"},
            {"date": "2007.1.2", "name": "Southwest Sumba"}
        ],
        "other_names": ["Sumba Barat Daya", "Waitabula"]
    },
    {
        "key": "Miri-Malaysia",
        "canonical_name": "Miri",
        "foundation_year": 1910,
        "historical_names": [
            {"date": "1910.8.10", "name": "Miri"},
            {"date": "2005.5.20", "name": "Miri"}
        ],
        "other_names": ["Bandar Raya Miri", "Miri City"]
    },
    {
        "key": "San Pablo-Philippines",
        "canonical_name": "San Pablo",
        "foundation_year": 1571,
        "historical_names": [
            {"date": "1571.1.1", "name": "Sampaloc"},
            {"date": "1586.1.1", "name": "San Pablo de los Montes"},
            {"date": "1940.5.7", "name": "San Pablo"}
        ],
        "other_names": ["San Pablo City", "City of San Pablo", "Sampaloc"]
    },
    {
        "key": "Binan-Philippines",
        "canonical_name": "Binan",
        "foundation_year": 1571,
        "historical_names": [
            {"date": "1571.1.1", "name": "Binan"}
        ],
        "other_names": ["Biñan", "Biñan City", "City of Biñan"]
    },
    {
        "key": "Nghi Son-Vietnam",
        "canonical_name": "Nghi Son",
        "foundation_year": 2020,
        "historical_names": [
            {"date": "1000.1.1", "name": "Tinh Gia"},
            {"date": "2020.4.22", "name": "Nghi Son"}
        ],
        "other_names": ["Nghi Sơn", "Tĩnh Gia", "Tinh Gia"]
    },
    {
        "key": "Mempawah-Indonesia",
        "canonical_name": "Mempawah",
        "foundation_year": 1740,
        "historical_names": [
            {"date": "1740.1.1", "name": "Mempawah"},
            {"date": "1950.1.1", "name": "Pontianak Regency"},
            {"date": "2014.7.21", "name": "Mempawah"}
        ],
        "other_names": ["Kerajaan Mempawah", "Kabupaten Mempawah"]
    },
    {
        "key": "Silang-Philippines",
        "canonical_name": "Silang",
        "foundation_year": 1595,
        "historical_names": [
            {"date": "1595.1.1", "name": "Silang"}
        ],
        "other_names": ["Silang Cavite"]
    },
    {
        "key": "Sunggal-Indonesia",
        "canonical_name": "Sunggal",
        "foundation_year": None,
        "historical_names": [
            {"date": "1600.1.1", "name": "Soenggal"},
            {"date": "1945.8.17", "name": "Sunggal"}
        ],
        "other_names": ["Urung Sunggal", "Deli Serdang"]
    },
    {
        "key": "Takalar-Indonesia",
        "canonical_name": "Takalar",
        "foundation_year": 1960,
        "historical_names": [
            {"date": "1600.1.1", "name": "Polongbangkeng"},
            {"date": "1960.2.10", "name": "Takalar"}
        ],
        "other_names": ["Kabupaten Takalar", "Pattallassang"]
    },
    {
        "key": "Bang Yai-Thailand",
        "canonical_name": "Bang Yai",
        "foundation_year": None,
        "historical_names": [
            {"date": "1917.1.1", "name": "Bang Mae Nang"},
            {"date": "1930.1.1", "name": "Bang Yai"}
        ],
        "other_names": ["บางใหญ่", "Bang Mae Nang"]
    },
    {
        "key": "Sihanoukville-Cambodia",
        "canonical_name": "Sihanoukville",
        "foundation_year": 1955,
        "historical_names": [
            {"date": "1800.1.1", "name": "Kampong Som"},
            {"date": "1955.1.1", "name": "Sihanoukville"},
            {"date": "1970.10.9", "name": "Kampong Som"},
            {"date": "1993.9.24", "name": "Sihanoukville"}
        ],
        "other_names": ["ក្រុងព្រះសីហនុ", "Kampong Som", "Kompong Som", "Preah Sihanouk"]
    },
    {
        "key": "West Lampung-Indonesia",
        "canonical_name": "West Lampung",
        "foundation_year": 1991,
        "historical_names": [
            {"date": "1200.1.1", "name": "Sekala Brak"},
            {"date": "1991.8.16", "name": "West Lampung"}
        ],
        "other_names": ["Lampung Barat", "Sekala Brak", "Liwa"]
    },
    {
        "key": "Banjarbaru-Indonesia",
        "canonical_name": "Banjarbaru",
        "foundation_year": 1951,
        "historical_names": [
            {"date": "1951.7.9", "name": "Banjarbaru"},
            {"date": "1999.4.20", "name": "Banjarbaru"}
        ],
        "other_names": ["Banjar Baru", "Kota Banjarbaru"]
    },
    {
        "key": "Cibitung-Indonesia",
        "canonical_name": "Cibitung",
        "foundation_year": None,
        "historical_names": [
            {"date": "1950.1.1", "name": "Cibitung"}
        ],
        "other_names": ["Tjibitoeng", "Bekasi"]
    },
    {
        "key": "Padang Lawas-Indonesia",
        "canonical_name": "Padang Lawas",
        "foundation_year": 1000,
        "historical_names": [
            {"date": "1025.1.1", "name": "Panai"},
            {"date": "2007.8.10", "name": "Padang Lawas"}
        ],
        "other_names": ["Pannai", "Candi Bahal", "Sibuhuan"]
    },
    {
        "key": "East Luwu-Indonesia",
        "canonical_name": "East Luwu",
        "foundation_year": 2003,
        "historical_names": [
            {"date": "2003.2.25", "name": "East Luwu"}
        ],
        "other_names": ["Luwu Timur", "Malili", "Sorowako"]
    },
    {
        "key": "Batang Hari-Indonesia",
        "canonical_name": "Batang Hari",
        "foundation_year": 1948,
        "historical_names": [
            {"date": "1948.1.1", "name": "Batang Hari"}
        ],
        "other_names": ["Batanghari", "Muara Bulian"]
    },
    {
        "key": "Thanh Xuan-Vietnam",
        "canonical_name": "Thanh Xuan",
        "foundation_year": 1996,
        "historical_names": [
            {"date": "1996.11.22", "name": "Thanh Xuan"}
        ],
        "other_names": ["Thanh Xuân", "Hà Nội"]
    },
    {
        "key": "South Nias-Indonesia",
        "canonical_name": "South Nias",
        "foundation_year": 2003,
        "historical_names": [
            {"date": "1850.1.1", "name": "Zuid-Nias"},
            {"date": "2003.2.25", "name": "South Nias"}
        ],
        "other_names": ["Nias Selatan", "Teluk Dalam", "Bawomataluo"]
    },
    {
        "key": "Cileungsir-Indonesia",
        "canonical_name": "Cileungsir",
        "foundation_year": None,
        "historical_names": [
            {"date": "1950.1.1", "name": "Cileungsir"}
        ],
        "other_names": ["Desa Cileungsir", "Ciamis"]
    },
    {
        "key": "Cau Giay-Vietnam",
        "canonical_name": "Cau Giay",
        "foundation_year": 1996,
        "historical_names": [
            {"date": "1873.12.21", "name": "Cau Giay"},
            {"date": "1996.11.22", "name": "Cau Giay"}
        ],
        "other_names": ["Cầu Giấy", "Pont de Papier"]
    },
    {
        "key": "Gunung Kaler-Indonesia",
        "canonical_name": "Gunung Kaler",
        "foundation_year": 2000,
        "historical_names": [
            {"date": "2000.1.1", "name": "Gunung Kaler"}
        ],
        "other_names": ["Kecamatan Gunung Kaler", "Tangerang"]
    },
    {
        "key": "South Cikarang-Indonesia",
        "canonical_name": "South Cikarang",
        "foundation_year": 1990,
        "historical_names": [
            {"date": "1990.1.1", "name": "South Cikarang"}
        ],
        "other_names": ["Cikarang Selatan", "Lippo Cikarang"]
    },
    {
        "key": "West Cikarang-Indonesia",
        "canonical_name": "West Cikarang",
        "foundation_year": 1990,
        "historical_names": [
            {"date": "1990.1.1", "name": "West Cikarang"}
        ],
        "other_names": ["Cikarang Barat", "Bekasi"]
    },
    {
        "key": "Phu My-Vietnam",
        "canonical_name": "Phu My",
        "foundation_year": 1994,
        "historical_names": [
            {"date": "1994.6.2", "name": "Phu My"},
            {"date": "2018.4.12", "name": "Phu My"}
        ],
        "other_names": ["Phú Mỹ", "Bà Rịa - Vũng Tàu", "Cái Mép"]
    }
]

out_b14 = {
    "batch_index": 14,
    "settlements": b14_settlements
}

target_path_14 = os.path.join(TARGET_DIR, "resolved_batch_14.json")
with open(target_path_14, "w", encoding="utf-8") as f:
    json.dump(out_b14, f, indent=2, ensure_ascii=False)
print(f"Wrote resolved_batch_14.json with {len(b14_settlements)} settlements")
