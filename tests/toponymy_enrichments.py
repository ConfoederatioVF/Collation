# -*- coding: utf-8 -*-
"""
Generator for MANDALA Toponymy Batches 057 to 064
Covers Thailand (part 2) and Vietnam.
"""
import json, re

HISTORICAL_ENRICHMENTS = {
    # THAILAND
    "Pak Phraek-Thailand": {
        "canonical_name": "Pak Phraek",
        "historical_names": [
            ("1831.1.1", "Pak Phraek")
        ],
        "other_names": ["ปากแพรก", "Ban Pak Phraek"]
    },
    "Rangsit-Thailand_2": {
        "canonical_name": "Rangsit",
        "historical_names": [
            ("1890.1.1", "Thanyaburi"),
            ("1994.1.1", "Rangsit")
        ],
        "other_names": ["รังสิต", "Nakhon Rangsit", "Muang Rangsit"]
    },
    "Wiang Chiang Rung-Thailand": {
        "canonical_name": "Wiang Chiang Rung",
        "historical_names": [
            ("-500.1.1", "Wiang Chiang Rung")
        ],
        "other_names": ["เวียงเชียงรุ้ง"]
    },
    "Phimai-Thailand_2": {
        "canonical_name": "Phimai",
        "historical_names": [
            ("1000.1.1", "Vimayapura"),
            ("1300.1.1", "Phimai")
        ],
        "other_names": ["พิมาย", "Vimayapura", "Muang Phimai"]
    },
    "U Thong-Thailand_2": {
        "canonical_name": "U Thong",
        "historical_names": [
            ("500.1.1", "Suvarnabhumi"),
            ("1000.1.1", "U Thong")
        ],
        "other_names": ["อู่ทอง", "Muang U Thong"]
    },
    "Muang Fa Daet-Thailand": {
        "canonical_name": "Fa Daet Song Yang",
        "historical_names": [
            ("700.1.1", "Fa Daet Song Yang")
        ],
        "other_names": ["เมืองฟ้าแดดสงยาง", "Muang Fa Daet", "Fa Daet"]
    },
    "Si Mahosot-Thailand_2": {
        "canonical_name": "Si Mahosot",
        "historical_names": [
            ("500.1.1", "Morokot"),
            ("1000.1.1", "Si Mahosot")
        ],
        "other_names": ["ศรีมโหสถ", "Muang Si Mahosot"]
    },
    "Ku Bua-Thailand": {
        "canonical_name": "Ku Bua",
        "historical_names": [
            ("600.1.1", "Ku Bua")
        ],
        "other_names": ["คูบัว", "Muang Ku Bua"]
    },
    "Ban Non Wat-Thailand": {
        "canonical_name": "Ban Non Wat",
        "historical_names": [
            ("-1000.1.1", "Ban Non Wat")
        ],
        "other_names": ["บ้านโนนวัด", "Non Wat"]
    },
    "Khlong Toei-Thailand_2": {
        "canonical_name": "Khlong Toei",
        "historical_names": [
            ("1000.1.1", "Khlong Toei")
        ],
        "other_names": ["คลองเตย"]
    },

    # VIETNAM - BATCH 59
    "Hai Phong-Vietnam": {
        "canonical_name": "Hai Phong",
        "historical_names": [
            ("1887.1.1", "Hai Phong")
        ],
        "other_names": ["Hải Phòng", "Haiphong"]
    },
    "Can Tho-Vietnam": {
        "canonical_name": "Can Tho",
        "historical_names": [
            ("1739.1.1", "Tran Giang"),
            ("1887.1.1", "Can Tho")
        ],
        "other_names": ["Cần Thơ", "Tay Do", "Tran Giang"]
    },
    "Huế-Vietnam": {
        "canonical_name": "Hue",
        "historical_names": [
            ("1306.1.1", "Thuan Hoa"),
            ("1687.1.1", "Phu Xuan"),
            ("1802.5.1", "Hue")
        ],
        "other_names": ["Huế", "Phú Xuân", "Thuận Hóa"]
    },
    "Khánh Hòa-Vietnam": {
        "canonical_name": "Nha Trang",
        "historical_names": [
            ("700.1.1", "Kauthara"),
            ("1653.1.1", "Nha Trang")
        ],
        "other_names": ["Khánh Hòa", "Nha Trang", "Kauthara"]
    },
    "Sóc Trăng-Vietnam": {
        "canonical_name": "Soc Trang",
        "historical_names": [
            ("1800.1.1", "Srok Khleang"),
            ("1956.10.22", "Khanh Hung"),
            ("1976.7.2", "Soc Trang")
        ],
        "other_names": ["Sóc Trăng", "Srok Khleang", "Ba Xuyen", "Khanh Hung"]
    },
    "Tây Ninh-Vietnam": {
        "canonical_name": "Tay Ninh",
        "historical_names": [
            ("1836.1.1", "Tay Ninh")
        ],
        "other_names": ["Tây Ninh"]
    },
    "Lâm Đồng-Vietnam": {
        "canonical_name": "Da Lat",
        "historical_names": [
            ("1899.1.1", "Da Lat")
        ],
        "other_names": ["Đà Lạt", "Dalat", "Lâm Đồng"]
    },
    "Bạc Liêu-Vietnam": {
        "canonical_name": "Bac Lieu",
        "historical_names": [
            ("1882.1.1", "Bac Lieu")
        ],
        "other_names": ["Bạc Liêu", "Po Leav"]
    },
    "Hà Nam-Vietnam": {
        "canonical_name": "Phu Ly",
        "historical_names": [
            ("1887.1.1", "Phu Ly")
        ],
        "other_names": ["Phủ Lý", "Hà Nam"]
    },
    "Nha Trang-Vietnam": {
        "canonical_name": "Nha Trang",
        "historical_names": [
            ("700.1.1", "Kauthara"),
            ("1653.1.1", "Nha Trang")
        ],
        "other_names": ["Nha Trang", "Kauthara"]
    },
    "Kon Tum-Vietnam": {
        "canonical_name": "Kon Tum",
        "historical_names": [
            ("1848.1.1", "Kon Tum")
        ],
        "other_names": ["Kontum"]
    },
    "Kon Tum-Vietnam_2": {
        "canonical_name": "Kon Tum",
        "historical_names": [
            ("1848.1.1", "Kon Tum")
        ],
        "other_names": ["Kontum"]
    },
    "Thủ Đức-Vietnam": {
        "canonical_name": "Thu Duc",
        "historical_names": [
            ("1698.1.1", "Thu Duc")
        ],
        "other_names": ["Thủ Đức"]
    },
    "Thu Duc-Vietnam": {
        "canonical_name": "Thu Duc",
        "historical_names": [
            ("1698.1.1", "Thu Duc")
        ],
        "other_names": ["Thủ Đức"]
    },
    "Thai Nguyen-Vietnam": {
        "canonical_name": "Thai Nguyen",
        "historical_names": [
            ("1000.1.1", "Thai Nguyen")
        ],
        "other_names": ["Thái Nguyên"]
    },
    "Hòa Hưng-Vietnam": {
        "canonical_name": "Hoa Hung",
        "historical_names": [
            ("1800.1.1", "Hoa Hung")
        ],
        "other_names": ["Hòa Hưng", "Chí Hòa", "Chi Hoa"]
    },
    "Thu Dau Mot-Vietnam": {
        "canonical_name": "Thu Dau Mot",
        "historical_names": [
            ("1887.1.1", "Phu Cuong"),
            ("1976.7.2", "Thu Dau Mot")
        ],
        "other_names": ["Thủ Dầu Một", "Phú Cường", "Phu Cuong"]
    },
    "Ben Cat-Vietnam": {
        "canonical_name": "Ben Cat",
        "historical_names": [
            ("1956.1.1", "Ben Cat")
        ],
        "other_names": ["Bến Cát"]
    },
    "Long Bien-Vietnam": {
        "canonical_name": "Long Bien",
        "historical_names": [
            ("544.1.1", "Long Bien")
        ],
        "other_names": ["Long Biên"]
    },
    "Bắc Kạn-Vietnam": {
        "canonical_name": "Bac Kan",
        "historical_names": [
            ("1900.4.11", "Bac Kan")
        ],
        "other_names": ["Bắc Kạn", "Bac Can", "Bắc Cạn"]
    },
    "Bac Kan-Vietnam": {
        "canonical_name": "Bac Kan",
        "historical_names": [
            ("1900.4.11", "Bac Kan")
        ],
        "other_names": ["Bắc Kạn", "Bac Can", "Bắc Cạn"]
    },
    "Thanh Xuan-Vietnam": {
        "canonical_name": "Thanh Xuan",
        "historical_names": [
            ("1996.11.22", "Thanh Xuan")
        ],
        "other_names": ["Thanh Xuân"]
    },
    "Cau Giay-Vietnam": {
        "canonical_name": "Cau Giay",
        "historical_names": [
            ("1873.12.21", "Cau Giay")
        ],
        "other_names": ["Cầu Giấy", "Pont de Papier"]
    },
    "Bahnar people-Vietnam": {
        "canonical_name": "Bahnar",
        "historical_names": [
            ("1000.1.1", "Bahnar")
        ],
        "other_names": ["Ba Na", "Người Ba Na", "Bahnar"]
    },
    "Ba Vi-Vietnam": {
        "canonical_name": "Ba Vi",
        "historical_names": [
            ("1000.1.1", "Ba Vi")
        ],
        "other_names": ["Ba Vì", "Núi Tản Viên"]
    },
    "Thanh Pho Ba Ria-Vietnam": {
        "canonical_name": "Ba Ria",
        "historical_names": [
            ("1887.1.1", "Ba Ria")
        ],
        "other_names": ["Bà Rịa", "Ba Ria"]
    },
    "My Tho-Vietnam": {
        "canonical_name": "My Tho",
        "historical_names": [
            ("1679.1.1", "My Tho Dai Pho"),
            ("1887.1.1", "My Tho")
        ],
        "other_names": ["Mỹ Tho", "Mytho"]
    },
    "Dong Trieu-Vietnam": {
        "canonical_name": "Dong Trieu",
        "historical_names": [
            ("1000.1.1", "Dong Trieu")
        ],
        "other_names": ["Đông Triều"]
    },
    "Lục Ngạn-Vietnam": {
        "canonical_name": "Luc Ngan",
        "historical_names": [
            ("1000.1.1", "Luc Ngan")
        ],
        "other_names": ["Lục Ngạn"]
    },

    # VIETNAM - BATCH 60
    "Pho Yen-Vietnam": {
        "canonical_name": "Pho Yen",
        "historical_names": [
            ("1000.1.1", "Pho Yen")
        ],
        "other_names": ["Phổ Yên"]
    },
    "Sơn Tây-Vietnam": {
        "canonical_name": "Son Tay",
        "historical_names": [
            ("1469.1.1", "Son Tay")
        ],
        "other_names": ["Sơn Tây", "Sontai"]
    },
    "Ninh Hoa-Vietnam": {
        "canonical_name": "Ninh Hoa",
        "historical_names": [
            ("1831.1.1", "Ninh Hoa")
        ],
        "other_names": ["Ninh Hòa"]
    },
    "Dien Ban-Vietnam": {
        "canonical_name": "Dien Ban",
        "historical_names": [
            ("1806.1.1", "Dien Ban")
        ],
        "other_names": ["Điện Bàn"]
    },
    "Chi Linh City-Vietnam": {
        "canonical_name": "Chi Linh",
        "historical_names": [
            ("1000.1.1", "Chi Linh")
        ],
        "other_names": ["Chí Linh"]
    },
    "Phú Mỹ-Vietnam": {
        "canonical_name": "Phu My",
        "historical_names": [
            ("1994.6.2", "Phu My")
        ],
        "other_names": ["Phú Mỹ"]
    },
    "Tan An-Vietnam": {
        "canonical_name": "Tan An",
        "historical_names": [
            ("1889.12.20", "Tan An")
        ],
        "other_names": ["Tân An"]
    },
    "Cao Lanh-Vietnam": {
        "canonical_name": "Cao Lanh",
        "historical_names": [
            ("1820.1.1", "Cao Lanh")
        ],
        "other_names": ["Cao Lãnh"]
    },
    "Viet Yen-Vietnam": {
        "canonical_name": "Viet Yen",
        "historical_names": [
            ("1000.1.1", "Viet Yen")
        ],
        "other_names": ["Việt Yên"]
    },
    "Lang Son-Vietnam": {
        "canonical_name": "Lang Son",
        "historical_names": [
            ("1000.1.1", "Lang Son")
        ],
        "other_names": ["Lạng Sơn"]
    },
    "Cẩm Phả-Vietnam": {
        "canonical_name": "Cam Pha",
        "historical_names": [
            ("1886.1.1", "Cam Pha")
        ],
        "other_names": ["Cẩm Phả"]
    },
    "Vinh Chau-Vietnam": {
        "canonical_name": "Vinh Chau",
        "historical_names": [
            ("1850.1.1", "Vinh Chau")
        ],
        "other_names": ["Vĩnh Châu"]
    },
    "Phuc Yen-Vietnam": {
        "canonical_name": "Phuc Yen",
        "historical_names": [
            ("1905.1.1", "Phuc Yen")
        ],
        "other_names": ["Phúc Yên"]
    },
    "Phú Quốc-Vietnam": {
        "canonical_name": "Phu Quoc",
        "historical_names": [
            ("1680.1.1", "Koh Trol"),
            ("1708.1.1", "Phu Quoc")
        ],
        "other_names": ["Phú Quốc", "Koh Trol"]
    },
    "B'Lao-Vietnam": {
        "canonical_name": "Bao Loc",
        "historical_names": [
            ("1899.1.1", "B Lao"),
            ("1958.1.1", "Bao Loc")
        ],
        "other_names": ["Bảo Lộc", "B Lao"]
    },
    "Dong Ha-Vietnam": {
        "canonical_name": "Dong Ha",
        "historical_names": [
            ("1950.1.1", "Dong Ha")
        ],
        "other_names": ["Đông Hà"]
    },
    "Trang Bang-Vietnam": {
        "canonical_name": "Trang Bang",
        "historical_names": [
            ("1867.1.1", "Trang Bang")
        ],
        "other_names": ["Trảng Bàng"]
    },
    "Duc Trong-Vietnam": {
        "canonical_name": "Duc Trong",
        "historical_names": [
            ("1958.1.1", "Lien Nghia"),
            ("1976.7.2", "Duc Trong")
        ],
        "other_names": ["Đức Trọng", "Liên Nghĩa", "Lien Nghia"]
    },
    "La Gi-Vietnam": {
        "canonical_name": "La Gi",
        "historical_names": [
            ("1956.1.1", "La Gi")
        ],
        "other_names": ["Lagi"]
    },
    "Châu Đốc-Vietnam": {
        "canonical_name": "Chau Doc",
        "historical_names": [
            ("1757.1.1", "Chau Doc")
        ],
        "other_names": ["Châu Đốc", "Chaudoc"]
    },
    "Chau Doc-Vietnam": {
        "canonical_name": "Chau Doc",
        "historical_names": [
            ("1757.1.1", "Chau Doc")
        ],
        "other_names": ["Châu Đốc", "Chaudoc"]
    },
    "Đồng Hới-Vietnam": {
        "canonical_name": "Dong Hoi",
        "historical_names": [
            ("1631.1.1", "Dong Hoi")
        ],
        "other_names": ["Đồng Hới"]
    },
    "Huyen Lam Ha-Vietnam": {
        "canonical_name": "Lam Ha",
        "historical_names": [
            ("1987.1.1", "Lam Ha")
        ],
        "other_names": ["Lâm Hà"]
    },
    "Phu Ly-Vietnam": {
        "canonical_name": "Phu Ly",
        "historical_names": [
            ("1887.1.1", "Phu Ly")
        ],
        "other_names": ["Phủ Lý"]
    },
    "Lao Cai-Vietnam": {
        "canonical_name": "Lao Cai",
        "historical_names": [
            ("1886.1.1", "Lao Cai")
        ],
        "other_names": ["Lào Cai", "Lao Kay"]
    },
    "Sam Son-Vietnam": {
        "canonical_name": "Sam Son",
        "historical_names": [
            ("1907.1.1", "Sam Son")
        ],
        "other_names": ["Sầm Sơn"]
    },
    "Thanh pho Song Cong-Vietnam": {
        "canonical_name": "Song Cong",
        "historical_names": [
            ("1985.1.1", "Song Cong")
        ],
        "other_names": ["Sông Công"]
    },

    # VIETNAM - BATCH 61
    "Vân Phong Economic Zone-Vietnam": {
        "canonical_name": "Van Phong",
        "historical_names": [
            ("1000.1.1", "Van Phong")
        ],
        "other_names": ["Vân Phong", "Vinh Van Phong"]
    },
    "Hội An-Vietnam": {
        "canonical_name": "Hoi An",
        "historical_names": [
            ("1595.1.1", "Faifo"),
            ("1954.7.21", "Hoi An")
        ],
        "other_names": ["Hội An", "Faifo"]
    },
    "Móng Cái-Vietnam": {
        "canonical_name": "Mong Cai",
        "historical_names": [
            ("1887.1.1", "Mong Cai")
        ],
        "other_names": ["Móng Cái", "Moncay"]
    },
    "Tuyen Quang-Vietnam": {
        "canonical_name": "Tuyen Quang",
        "historical_names": [
            ("1397.1.1", "Tuyen Quang")
        ],
        "other_names": ["Tuyên Quang"]
    },
    "Hà Tiên-Vietnam": {
        "canonical_name": "Ha Tien",
        "historical_names": [
            ("1708.1.1", "Peam"),
            ("1714.1.1", "Ha Tien")
        ],
        "other_names": ["Hà Tiên", "Peam"]
    },
    "Yen Bai-Vietnam": {
        "canonical_name": "Yen Bai",
        "historical_names": [
            ("1900.4.11", "Yen Bai")
        ],
        "other_names": ["Yên Bái"]
    },
    "Phu Tho-Vietnam": {
        "canonical_name": "Phu Tho",
        "historical_names": [
            ("1903.5.5", "Phu Tho")
        ],
        "other_names": ["Phú Thọ"]
    },
    "An Khe-Vietnam": {
        "canonical_name": "An Khe",
        "historical_names": [
            ("1771.1.1", "Tay Son Thuong Dao"),
            ("1900.1.1", "An Khe")
        ],
        "other_names": ["An Khê", "An Tuc"]
    },
    "Cu Chi-Vietnam": {
        "canonical_name": "Cu Chi",
        "historical_names": [
            ("1956.1.1", "Cu Chi")
        ],
        "other_names": ["Củ Chi"]
    },
    "Kien Hung-Vietnam": {
        "canonical_name": "Ha Dong",
        "historical_names": [
            ("1887.1.1", "Ha Dong")
        ],
        "other_names": ["Hà Đông", "Kiến Hưng", "Kien Hung"]
    },

    # VIETNAM - BATCH 62
    "Thanh Pho Uong Bi-Vietnam": {
        "canonical_name": "Uong Bi",
        "historical_names": [
            ("1950.1.1", "Uong Bi")
        ],
        "other_names": ["Uông Bí"]
    },
    "Xom Cai Nuoc-Vietnam": {
        "canonical_name": "Cai Nuoc",
        "historical_names": [
            ("1900.1.1", "Cai Nuoc")
        ],
        "other_names": ["Cái Nước"]
    },
    "Bim Son-Vietnam": {
        "canonical_name": "Bim Son",
        "historical_names": [
            ("1981.12.18", "Bim Son")
        ],
        "other_names": ["Bỉm Sơn"]
    },
    "Thai Binh-Vietnam": {
        "canonical_name": "Thai Binh",
        "historical_names": [
            ("1890.3.21", "Thai Binh")
        ],
        "other_names": ["Thái Bình"]
    },
    "Lai Chau-Vietnam": {
        "canonical_name": "Lai Chau",
        "historical_names": [
            ("1887.1.1", "Muang Lay"),
            ("1954.7.21", "Lai Chau")
        ],
        "other_names": ["Lai Châu", "Muang Lay"]
    },
    "Xa Long Hai-Vietnam": {
        "canonical_name": "Long Hai",
        "historical_names": [
            ("1900.1.1", "Long Hai")
        ],
        "other_names": ["Long Hải"]
    },
    "Ap Long Thanh-Vietnam": {
        "canonical_name": "Long Thanh",
        "historical_names": [
            ("1900.1.1", "Long Thanh")
        ],
        "other_names": ["Long Thạnh", "Long Thành"]
    },

    # VIETNAM - BATCH 63
    "Ecopark-Vietnam": {
        "canonical_name": "Ecopark",
        "historical_names": [
            ("2009.1.1", "Ecopark")
        ],
        "other_names": ["Ecopark"]
    },
    "thi xa Quang Tri-Vietnam": {
        "canonical_name": "Quang Tri",
        "historical_names": [
            ("1802.1.1", "Dinh Quang Tri"),
            ("1968.1.1", "Quang Tri")
        ],
        "other_names": ["Quảng Trị"]
    },
    "Ap Ho Phong-Vietnam": {
        "canonical_name": "Ho Phong",
        "historical_names": [
            ("1900.1.1", "Ho Phong")
        ],
        "other_names": ["Hộ Phòng", "Hô Phòng"]
    },
    "Ap Phuoc Tinh-Vietnam": {
        "canonical_name": "Phuoc Tinh",
        "historical_names": [
            ("1900.1.1", "Phuoc Tinh")
        ],
        "other_names": ["Phước Tĩnh"]
    },
    "Dien Thanh-Vietnam": {
        "canonical_name": "Dien Chau",
        "historical_names": [
            ("1900.1.1", "Dien Chau")
        ],
        "other_names": ["Diễn Châu", "Diễn Thành", "Dien Thanh"]
    },
    "Angkor Borei-Vietnam": {
        "canonical_name": "Angkor Borei",
        "historical_names": [
            ("69.1.1", "Vyadhapura"),
            ("600.1.1", "Angkor Borei")
        ],
        "other_names": ["Vyadhapura"]
    },
    "Co Loa Citadel-Vietnam": {
        "canonical_name": "Co Loa",
        "historical_names": [
            ("-257.1.1", "Co Loa")
        ],
        "other_names": ["Cổ Loa"]
    },
    "Ea T'ling-Vietnam": {
        "canonical_name": "Ea Tling",
        "historical_names": [
            ("1862.1.1", "Ea Tling")
        ],
        "other_names": ["Ea Tling"]
    },
    "Dong Duong-Vietnam": {
        "canonical_name": "Dong Duong",
        "historical_names": [
            ("875.1.1", "Indrapura"),
            ("1000.1.1", "Dong Duong")
        ],
        "other_names": ["Đồng Dương", "Indrapura"]
    },
    "Kauthara-Vietnam": {
        "canonical_name": "Kauthara",
        "historical_names": [
            ("700.1.1", "Kauthara")
        ],
        "other_names": ["Kauthara", "Nha Trang"]
    },
    "My Son Sanctuary-Vietnam": {
        "canonical_name": "My Son",
        "historical_names": [
            ("700.1.1", "My Son")
        ],
        "other_names": ["Mỹ Sơn"]
    },
    "Phong Chau-Vietnam_2": {
        "canonical_name": "Phong Chau",
        "historical_names": [
            ("1862.1.1", "Phong Chau")
        ],
        "other_names": ["Phong Châu"]
    },
    "Dong Son Type-Site-Vietnam": {
        "canonical_name": "Dong Son",
        "historical_names": [
            ("-500.1.1", "Dong Son")
        ],
        "other_names": ["Đông Sơn"]
    },
    "Oc Eo-Vietnam_2": {
        "canonical_name": "Oc Eo",
        "historical_names": [
            ("-500.1.1", "Oc Eo")
        ],
        "other_names": ["Óc Eo"]
    },

    # VIETNAM - BATCH 64
    "Hoa Lư Ancient Capital-Vietnam": {
        "canonical_name": "Hoa Lu",
        "historical_names": [
            ("968.1.1", "Hoa Lu")
        ],
        "other_names": ["Hoa Lư"]
    },
    "Sa Huynh-Vietnam": {
        "canonical_name": "Sa Huynh",
        "historical_names": [
            ("-500.1.1", "Sa Huynh")
        ],
        "other_names": ["Sa Huỳnh"]
    }
}
