import json
import math
import urllib.parse
import urllib.request

SETTLEMENTS = [
  {"key": "Tambería del Inca-Argentina", "n": "Tambería del Inca", "c": "Argentina", "r": "inca_collasuyu", "ll": [-29.17, -67.508], "ey": 1480, "ly": 1530, "p": 4220, "al": ["chilecito inca", "Chilecito Inca"]},
  {"key": "San Jose Pelarco-Chile", "n": "San Jose Pelarco", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-35.384, -71.447], "ey": 1525, "ly": 1830, "p": 4219, "ex": [{"date": "1950.1.1", "name": "Pelarco"}]},
  {"key": "Picún Leufú-Argentina", "n": "Picún Leufú", "c": "Argentina", "r": "arg_neuquen", "ll": [-39.51866, -69.29114], "ey": 1900, "ly": 2022, "p": 4216},
  {"key": "Quemú Quemú-Argentina", "n": "Quemú Quemú", "c": "Argentina", "r": "arg_la_pampa", "ll": [-36.05482, -63.56586], "ey": 1900, "ly": 2022, "p": 4215},
  {"key": "Loma-Bolivia", "n": "Loma", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-20.917, -64.767], "ey": 1525, "ly": 1825, "p": 4213, "al": ["pilaya", "estancia pilaya", "Pilaya"]},
  {"key": "El Hoyo-Argentina", "n": "El Hoyo", "c": "Argentina", "r": "arg_rio_negro", "ll": [-42.06413, -71.51921], "ey": 1900, "ly": 2022, "p": 4210},
  {"key": "RG02 - Jarana-Peru", "n": "RG02 - Jarana", "c": "Peru", "r": "inca_contisuyu", "ll": [-15.93478, -73.10793], "ey": -1000, "ly": 1530, "p": 4210, "al": ["callanga", "chillihuay", "rg01 - corral redondo"]},
  {"key": "Los Andes (col_magdalena)-Colombia", "n": "Los Andes", "c": "Colombia", "r": "col_magdalena", "ll": [9.58124, -74.35367], "ey": 1850, "ly": 2018, "p": 4209},
  {"key": "Relleno Sanitario de Girardot-Colombia", "n": "Relleno Sanitario de Girardot", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.32685, -74.85935], "ey": 500, "ly": 1500, "p": 4209, "ex": [{"date": "1928.1.1", "name": "Girardot"}]},
  {"key": "Jatun Ushco-Peru", "n": "Jatun Ushco", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.13317, -76.20072], "ey": 1438, "ly": 1530, "p": 4205, "al": ["cueva jatunshuco", "el morro", "tambopata"]},
  {"key": "San José de Tocomita-Venezuela", "n": "San José de Tocomita", "c": "Venezuela", "r": "ven_bolivar", "ll": [7.42764, -63.27507], "ey": 1850, "ly": 2011, "p": 4204},
  {"key": "San Pedro (ven_zulia)-Venezuela", "n": "San Pedro", "c": "Venezuela", "r": "ven_zulia", "ll": [9.78733, -70.8957], "ey": 1850, "ly": 2011, "p": 4204},
  {"key": "Sacháyoj-Argentina", "n": "Sacháyoj", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-26.67542, -61.81511], "ey": 1850, "ly": 2022, "p": 4203, "al": ["sachayoj", "Sachayoj"]},
  {"key": "Obonuco-Colombia", "n": "Obonuco", "c": "Colombia", "r": "col_narino", "ll": [1.19015, -77.30681], "ey": 1525, "ly": 2018, "p": 4202, "al": ["jongovito", "jongoyito", "ovonuco"]},
  {"key": "Mámbita-Colombia", "n": "Mámbita", "c": "Colombia", "r": "col_cundinamarca", "ll": [4.76523, -73.32422], "ey": 1525, "ly": 2018, "p": 4200, "al": ["mambita", "Mambita"]},
  {"key": "Curaco de Vélez-Chile", "n": "Curaco de Vélez", "c": "Chile", "r": "chl_region_de_los_lagos", "ll": [-42.42745, -73.56814], "ey": 1850, "ly": 2025, "p": 4200},
  {"key": "Contratación-Colombia", "n": "Contratación", "c": "Colombia", "r": "col_santander", "ll": [6.29056, -73.47443], "ey": 1850, "ly": 2025, "p": 4199},
  {"key": "Lita-Ecuador", "n": "Lita", "c": "Ecuador", "r": "ecu_carchi", "ll": [0.76488, -78.38831], "ey": 1850, "ly": 2025, "p": 4199},
  {"key": "Ch´acco Kunca-Peru", "n": "Ch´acco Kunca", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.77684, -70.2869], "ey": 1300, "ly": 1530, "p": 4199, "al": ["andenerias condorcuyo q’ocha", "cerro paraparan", "ch'aco wasi san miguel"]},
  {"key": "Sitios Las Águilas-Colombia", "n": "Sitios Las Águilas", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.32553, -75.45967], "ey": 1300, "ly": 1500, "p": 4199},
  {"key": "Caunapí-Colombia_2", "n": "Caunapí", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.44089, -78.61499], "ey": 500, "ly": 1500, "p": 4198},
  {"key": "San Agustin de Huaychao-Peru", "n": "San Agustin de Huaychao", "c": "Peru", "r": "per_pasco", "ll": [-10.9895, -76.4307], "ey": 1525, "ly": 2017, "p": 4197, "al": ["huaychao", "Huaychao"]},
  {"key": "Sausal-Peru", "n": "Sausal", "c": "Peru", "r": "per_la_libertad", "ll": [-7.734, -79.0045], "ey": 1850, "ly": 2017, "p": 4196},
  {"key": "Sayani-Peru", "n": "Sayani", "c": "Peru", "r": "vp_intendencia_puno", "ll": [-14.196, -69.47], "ey": 1525, "ly": 1825, "p": 4196, "al": ["pascata", "Pascata"]},
  {"key": "Guaqui-Bolivia", "n": "Guaqui", "c": "Bolivia", "r": "bol_la_paz", "ll": [-16.59751, -68.83693], "ey": 1525, "ly": 2024, "p": 4195, "al": ["puerto mayor de guaqui"]},
  {"key": "Palma Real-Ecuador", "n": "Palma Real", "c": "Ecuador", "r": "vng_guayaquil_esmeraldas", "ll": [1.131, -78.978], "ey": 1525, "ly": 1830, "p": 4193},
  {"key": "San Isidro-Argentina_2", "n": "San Isidro", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.82283, -64.39066], "ey": 80, "ly": 1500, "p": 4191},
  {"key": "Sicaya-Bolivia", "n": "Sicaya", "c": "Bolivia", "r": "bol_cochabamba", "ll": [-17.79964, -66.33421], "ey": 1525, "ly": 2026, "p": 4190, "al": ["panteon pampa", "Panteon Pampa"]},
  {"key": "Granja La Fabiola-Colombia", "n": "Granja La Fabiola", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.7031, -75.85615], "ey": 1000, "ly": 1500, "p": 4188},
  {"key": "Santa Rosalía-Colombia", "n": "Santa Rosalía", "c": "Colombia", "r": "col_casanare", "ll": [5.13639, -70.8595], "ey": 1900, "ly": 2025, "p": 4187},
  {"key": "Llica-Bolivia", "n": "Llica", "c": "Bolivia", "r": "bol_potosi", "ll": [-19.85066, -68.24847], "ey": 1525, "ly": 2026, "p": 4187, "al": ["lica", "Lica"]},
  {"key": "Huertos Familiares-Chile", "n": "Huertos Familiares", "c": "Chile", "r": "chl_region_metropolitana_de_santiago", "ll": [-33.13896, -70.80308], "ey": 1850, "ly": 2017, "p": 4186},
  {"key": "Chinavita-Colombia", "n": "Chinavita", "c": "Colombia", "r": "col_boyaca", "ll": [5.16749, -73.36848], "ey": 1850, "ly": 2025, "p": 4185},
  {"key": "Pasto Grande-Peru", "n": "Pasto Grande", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.09406, -71.4398], "ey": 1440, "ly": 1532, "p": 4185, "al": ["lloqllora", "Lloqllora"]},
  {"key": "Huancarum-Peru", "n": "Huancarum", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.16735, -76.1086], "ey": -1000, "ly": 1530, "p": 4184, "al": ["lomas", "ushnu urambiza", "Lomas"]},
  {"key": "Rio Segundo-Argentina", "n": "Rio Segundo", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-31.553, -63.532], "ey": 1778, "ly": 1830, "p": 4183, "al": ["los ranchos", "Los Ranchos"]},
  {"key": "Loreto - Molino-Chile", "n": "Loreto - Molino", "c": "Chile", "r": "chl_region_del_libertador_bernardo_o_higgins", "ll": [-34.26396, -71.02206], "ey": 1850, "ly": 2017, "p": 4181},
  {"key": "Ayapata-Peru_2", "n": "Ayapata", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.24109, -74.0279], "ey": 500, "ly": 1530, "p": 4181},
  {"key": "Caimani-Bolivia", "n": "Caimani", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.082, -66.919], "ey": 1525, "ly": 1825, "p": 4180, "al": ["fuisonga", "Fuisonga"]},
  {"key": "Churidó-Colombia", "n": "Churidó", "c": "Colombia", "r": "col_antioquia", "ll": [7.86546, -76.66717], "ey": 1850, "ly": 2018, "p": 4179},
  {"key": "Ascensión-Argentina", "n": "Ascensión", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-34.23082, -61.10342], "ey": 1850, "ly": 2010, "p": 4179},
  {"key": "La Peaña-Ecuador", "n": "La Peaña", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.31278, -79.85481], "ey": 1850, "ly": 2025, "p": 4178},
  {"key": "San Antonio Bebara-Colombia", "n": "San Antonio Bebara", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [6.091, -76.571], "ey": 1525, "ly": 1830, "p": 4177},
  {"key": "Singapur-Colombia", "n": "Singapur", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.75889, -74.71833], "ey": 1300, "ly": 1500, "p": 4177},
  {"key": "San José de Unare-Venezuela", "n": "San José de Unare", "c": "Venezuela", "r": "ven_anzoategui", "ll": [9.46944, -65.23222], "ey": 1850, "ly": 2025, "p": 4176},
  {"key": "Tahuamanu-Peru", "n": "Tahuamanu", "c": "Peru", "r": "per_madre_de_dios", "ll": [-11.45472, -69.32139], "ey": 1900, "ly": 2025, "p": 4171, "al": ["san lorenzo", "San Lorenzo"]},
  {"key": "Santa Rosa Chica-Chile", "n": "Santa Rosa Chica", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-40.17919, -72.56272], "ey": 1350, "ly": 1500, "p": 4171, "al": ["lr san pedro", "LR San Pedro"]},
  {"key": "José Manuel Quiroz-Peru", "n": "José Manuel Quiroz", "c": "Peru", "r": "per_cajamarca", "ll": [-7.34944, -78.04778], "ey": 1850, "ly": 2025, "p": 4170, "al": ["shirac", "Shirac"]},
  {"key": "Aji-Colombia", "n": "Aji", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [3.95, -77.103], "ey": 1525, "ly": 1830, "p": 4169, "al": ["concepcion", "Concepcion"]},
  {"key": "Tambillo (per_la_libertad)-Peru", "n": "Tambillo", "c": "Peru", "r": "per_la_libertad", "ll": [-7.8088, -78.5482], "ey": 1525, "ly": 2017, "p": 4165, "al": ["yaugueda", "Yaugueda"]},
  {"key": "Huanifaya-Bolivia", "n": "Huanifaya", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.862, -65.246], "ey": 1525, "ly": 1825, "p": 4165, "al": ["huanipaya", "Huanipaya"]},
  {"key": "Hda La Cristalina-Colombia", "n": "Hda La Cristalina", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.901, -75.72908], "ey": -1000, "ly": 1500, "p": 4165, "al": ["plan el limón", "Plan El Limón"]},
  {"key": "Carpintería-Argentina", "n": "Carpintería", "c": "Argentina", "r": "arg_san_luis", "ll": [-32.4101, -65.01001], "ey": 1850, "ly": 2022, "p": 4163},
  {"key": "Altagracia Pedraza-Venezuela", "n": "Altagracia Pedraza", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [8.412, -70.651], "ey": 1591, "ly": 1830, "p": 4163},
  {"key": "San Lucas de Amboca-Ecuador", "n": "San Lucas de Amboca", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-3.732, -79.276], "ey": 1525, "ly": 1830, "p": 4163},
  {"key": "Manchac 2 - Pirushto-Peru", "n": "Manchac 2 - Pirushto", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.06748, -76.88647], "ey": 0, "ly": 1530, "p": 4163, "al": ["castillo", "garajirca", "manchac"]},
  {"key": "Tres De Noviembre-Ecuador", "n": "Tres De Noviembre", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [-0.15883, -76.94979], "ey": 1920, "ly": 2025, "p": 4162},
  {"key": "La Francia-Argentina", "n": "La Francia", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.40635, -62.63324], "ey": 1850, "ly": 2022, "p": 4162},
  {"key": "Duanga-Colombia", "n": "Duanga", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [10.021, -75.25], "ey": 1525, "ly": 1693, "p": 4162},
  {"key": "El Riacho-Argentina", "n": "El Riacho", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-42.20224, -64.91723], "ey": -1689, "ly": 76, "p": 4162},
  {"key": "Chala Viejo-Peru", "n": "Chala Viejo", "c": "Peru", "r": "inca_contisuyu", "ll": [-15.76454, -74.20481], "ey": -1000, "ly": 1530, "p": 4160, "al": ["charcana", "josefita", "la banda"]},
  {"key": "Chulumani Yungas-Bolivia", "n": "Chulumani Yungas", "c": "Bolivia", "r": "inca_antisuyu", "ll": [-16.41, -67.526], "ey": 1470, "ly": 1530, "p": 4160, "al": ["yungas coca mitmaqkuna", "Yungas Coca Mitmaqkuna"]},
  {"key": "Pajchiri-Bolivia", "n": "Pajchiri", "c": "Bolivia", "r": "ca_titicaca_altiplano_tiwanaku", "ll": [-16.369, -68.615], "ey": 400, "ly": 1050, "p": 4160},
  {"key": "Gorgor-Peru", "n": "Gorgor", "c": "Peru", "r": "per_lima", "ll": [-10.62111, -77.04139], "ey": 500, "ly": 2025, "p": 4157, "al": ["cajatambo", "gorgorjirca", "maqchiqu"]},
  {"key": "Huatasani-Peru", "n": "Huatasani", "c": "Peru", "r": "per_puno", "ll": [-15.05944, -69.80194], "ey": 1850, "ly": 2025, "p": 4156},
  {"key": "Cibaya-Chile", "n": "Cibaya", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.782, -69.173], "ey": 1525, "ly": 1825, "p": 4156, "al": ["limacciña", "sibaya", "Limacciña"]},
  {"key": "Uia (na_magdalena_cauca_muisca_2)-Colombia", "n": "Uia", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [7.01817, -73.68181], "ey": 1300, "ly": 1500, "p": 4155},
  {"key": "Atahualpa (ecu_santa_elena)-Ecuador", "n": "Atahualpa", "c": "Ecuador", "r": "ecu_santa_elena", "ll": [-2.32102, -80.77561], "ey": 1850, "ly": 2025, "p": 4154},
  {"key": "Huayrapata-Peru", "n": "Huayrapata", "c": "Peru", "r": "per_puno", "ll": [-15.32139, -69.34111], "ey": 1850, "ly": 2025, "p": 4154},
  {"key": "La Clotilde-Argentina", "n": "La Clotilde", "c": "Argentina", "r": "arg_chaco", "ll": [-27.17741, -60.63256], "ey": 1900, "ly": 2022, "p": 4154},
  {"key": "Capiñata-Bolivia", "n": "Capiñata", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-17.133, -66.983], "ey": 1525, "ly": 1825, "p": 4154},
  {"key": "Timusi-Bolivia", "n": "Timusi", "c": "Bolivia", "r": "bol_la_paz", "ll": [-15.66851, -68.85771], "ey": 1525, "ly": 2024, "p": 4150},
  {"key": "Sativanorte-Colombia", "n": "Sativanorte", "c": "Colombia", "r": "col_boyaca", "ll": [6.13113, -72.70846], "ey": 1850, "ly": 2025, "p": 4147},
  {"key": "Tingo-Ecuador", "n": "Tingo", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-0.93659, -79.11649], "ey": 1850, "ly": 2025, "p": 4146},
  {"key": "El Dorado-Colombia", "n": "El Dorado", "c": "Colombia", "r": "col_meta", "ll": [3.73998, -73.83526], "ey": 1900, "ly": 2025, "p": 4145},
  {"key": "El Pedregal-Colombia", "n": "El Pedregal", "c": "Colombia", "r": "col_antioquia", "ll": [6.18966, -75.61742], "ey": 1980, "ly": 2018, "p": 4145, "al": ["los gómez", "Los Gómez"]},
  {"key": "Tambo del Collao-Peru", "n": "Tambo del Collao", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.7675, -75.03895], "ey": 1440, "ly": 1532, "p": 4143},
  {"key": "Pueblo Andino-Argentina", "n": "Pueblo Andino", "c": "Argentina", "r": "arg_santa_fe", "ll": [-32.6699, -60.87553], "ey": 1850, "ly": 2022, "p": 4142},
  {"key": "Inkavado-Peru", "n": "Inkavado", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.23122, -76.65346], "ey": 500, "ly": 1532, "p": 4142, "al": ["angalotuto", "yanagalgan", "shinga"]},
  {"key": "Campo-Colombia", "n": "Campo", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.86544, -73.76683], "ey": 1300, "ly": 1500, "p": 4140, "al": ["punto de interés arqueológico", "uia-49. yacimiento arqueológico", "uia-52. yacimiento arqueológico"]},
  {"key": "Daniel Córdova Toral-Ecuador", "n": "Daniel Córdova Toral", "c": "Ecuador", "r": "ecu_azuay", "ll": [-2.87785, -78.72053], "ey": 1850, "ly": 2025, "p": 4139},
  {"key": "La Esperanza-Chile_2", "n": "La Esperanza", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-40.14442, -72.52542], "ey": 0, "ly": 1500, "p": 4139},
  {"key": "San Rafael de Palo Alzado-Venezuela", "n": "San Rafael de Palo Alzado", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.31444, -70.05611], "ey": 1850, "ly": 2025, "p": 4136},
  {"key": "Cem. A. Paicarabi y Fredes-Argentina", "n": "Cem. A. Paicarabi y Fredes", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-34.2289, -58.5924], "ey": 1275, "ly": 1500, "p": 4136},
  {"key": "Colonia Valdense-Uruguay", "n": "Colonia Valdense", "c": "Uruguay", "r": "ury_colonia", "ll": [-34.34194, -57.2636], "ey": 1850, "ly": 2023, "p": 4135},
  {"key": "Herradura-Argentina", "n": "Herradura", "c": "Argentina", "r": "arg_formosa", "ll": [-26.48985, -58.31173], "ey": 1900, "ly": 2022, "p": 4133},
  {"key": "Santiago (col_norte_de_santander)-Colombia", "n": "Santiago", "c": "Colombia", "r": "col_norte_de_santander", "ll": [7.86586, -72.7162], "ey": 1541, "ly": 2025, "p": 4132},
  {"key": "María Teresa-Argentina", "n": "María Teresa", "c": "Argentina", "r": "arg_santa_fe", "ll": [-34.00483, -61.90159], "ey": 1850, "ly": 2022, "p": 4131},
  {"key": "San Salvador del Rio de la Plata-Uruguay", "n": "San Salvador del Rio de la Plata", "c": "Uruguay", "r": "crp_banda_oriental_misiones", "ll": [-33.672, -58.352], "ey": 1574, "ly": 1575, "p": 4131, "al": ["ciudad zaratina", "Ciudad Zaratina"]},
  {"key": "Santa Rosa Calamuchita-Argentina", "n": "Santa Rosa Calamuchita", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-32.069, -64.538], "ey": 1536, "ly": 1830, "p": 4129}
]

def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SVEA-Research/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def lookup_item(item):
    lat, lng = item["ll"]
    name = item["n"]
    country = item["c"]
    # Try es.wikipedia geosearch (10 km) and text search
    geo_es = []
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        geo_es = [x["title"] for x in api_get(u).get("query", {}).get("geosearch", [])]
    except Exception:
        pass
    search_es = []
    try:
        q = f"{name} {country}"
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=3&format=json"
        search_es = [x["title"] for x in api_get(u).get("query", {}).get("search", [])]
    except Exception:
        pass
    return {"key": item["key"], "geo_es": geo_es, "search_es": search_es}

import concurrent.futures
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(lookup_item, SETTLEMENTS))

with open("tests/chunk040_wiki_hits.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print("Done", len(res))
