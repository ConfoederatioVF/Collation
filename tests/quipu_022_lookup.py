import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

INPUT = [
    {"key": "Santafé de Morichal-Colombia", "n": "Santafé de Morichal", "c": "Colombia", "r": "col_casanare", "ll": [5.22625, -72.38828], "ey": 1525, "ly": 2018, "p": 6552, "al": ["jesus taguana", "Jesus Taguana"]},
    {"key": "Santo Domingo de Capillas-Peru", "n": "Santo Domingo de Capillas", "c": "Peru", "r": "per_huancavelica", "ll": [-13.73722, -75.24361], "ey": 1525, "ly": 2025, "p": 6552, "al": ["capillas", "Capillas"]},
    {"key": "Pepinales-Ecuador", "n": "Pepinales", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.171, -78.959], "ey": 1525, "ly": 1830, "p": 6551},
    {"key": "Fernandez-Colombia", "n": "Fernandez", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [7.993, -73.667], "ey": 1525, "ly": 1830, "p": 6549, "al": ["diego hernández", "Diego Hernández"]},
    {"key": "Unamuncho-Ecuador", "n": "Unamuncho", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-1.16619, -78.5903], "ey": 1850, "ly": 2025, "p": 6547},
    {"key": "Verónica-Argentina", "n": "Verónica", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-35.3547, -57.30337], "ey": 1850, "ly": 2010, "p": 6546},
    {"key": "Orejas de Burro-Argentina", "n": "Orejas de Burro", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-51.89429, -69.59266], "ey": -2078, "ly": -1094, "p": 6546},
    {"key": "Buena Vista (ven_trujillo)-Venezuela", "n": "Buena Vista", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.3, -70.88333], "ey": 1850, "ly": 2025, "p": 6543},
    {"key": "Quizu-Peru", "n": "Quizu", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.655, -76.743], "ey": 1525, "ly": 1825, "p": 6538},
    {"key": "Salango-Ecuador", "n": "Salango", "c": "Ecuador", "r": "ecu_manabi", "ll": [-1.64041, -80.80045], "ey": 1850, "ly": 2025, "p": 6534},
    {"key": "Tupe-Peru", "n": "Tupe", "c": "Peru", "r": "per_lima", "ll": [-12.74111, -75.80944], "ey": 1525, "ly": 2025, "p": 6534, "al": ["tupi", "Tupi"]},
    {"key": "Llano del Muerto-Colombia", "n": "Llano del Muerto", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [3.302, -76.431], "ey": 1525, "ly": 1830, "p": 6534},
    {"key": "Mamblachi-Argentina", "n": "Mamblachi", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-27.735, -64.292], "ey": 1536, "ly": 1830, "p": 6532, "al": ["chañar pugio", "Chañar Pugio"]},
    {"key": "Ama-Peru", "n": "Ama", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.469, -76.886], "ey": 1525, "ly": 1825, "p": 6527},
    {"key": "Huancarama-Bolivia", "n": "Huancarama", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.85, -66.821], "ey": 1525, "ly": 1825, "p": 6527},
    {"key": "Oropesa (per_apurimac)-Peru", "n": "Oropesa", "c": "Peru", "r": "per_apurimac", "ll": [-14.26056, -72.56361], "ey": 1525, "ly": 2025, "p": 6526, "al": ["totora", "Totora"]},
    {"key": "Vuelta Larga-Colombia_2", "n": "Vuelta Larga", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.57309, -78.67418], "ey": 1000, "ly": 1500, "p": 6525, "al": ["zapotal", "Zapotal"]},
    {"key": "Carania-Peru", "n": "Carania", "c": "Peru", "r": "per_lima", "ll": [-12.34556, -75.86944], "ey": -1000, "ly": 2025, "p": 6524, "al": ["en proceso", "sinchimarca", "andenes de laraos"]},
    {"key": "Guayllang-Ecuador", "n": "Guayllang", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.179, -79.022], "ey": 1525, "ly": 1830, "p": 6524},
    {"key": "Caraybamba-Peru", "n": "Caraybamba", "c": "Peru", "r": "per_apurimac", "ll": [-14.37806, -73.16083], "ey": 1525, "ly": 2025, "p": 6522},
    {"key": "Chiuchiu-Chile", "n": "Chiuchiu", "c": "Chile", "r": "vp_intendencia_charcas_potosi", "ll": [-22.343, -68.65], "ey": -304, "ly": 1825, "p": 6522, "al": ["atacama la baja", "chiu chiu", "ranl"]},
    {"key": "Sayla-Peru", "n": "Sayla", "c": "Peru", "r": "per_ayacucho", "ll": [-15.32, -73.22194], "ey": 1525, "ly": 2025, "p": 6521, "al": ["zayla", "Zayla"]},
    {"key": "Vilcanchos-Peru", "n": "Vilcanchos", "c": "Peru", "r": "per_ayacucho", "ll": [-13.61139, -74.5325], "ey": 1525, "ly": 2025, "p": 6521, "al": ["vilcancho", "Vilcancho"]},
    {"key": "Mazo-Peru", "n": "Mazo", "c": "Peru", "r": "per_lima", "ll": [-11.024, -77.6069], "ey": 1542, "ly": 2017, "p": 6519},
    {"key": "Toraya-Peru", "n": "Toraya", "c": "Peru", "r": "per_apurimac", "ll": [-14.05306, -73.29389], "ey": 1525, "ly": 2025, "p": 6517},
    {"key": "Chelel-Peru", "n": "Chelel", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-6.333, -77.724], "ey": 0, "ly": 1825, "p": 6515, "al": ["en proceso", "arqueológico piscoyahuco", "arqueológico terrazas de molinopampa"]},
    {"key": "Chiris-Peru", "n": "Chiris", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.217, -75.367], "ey": 1525, "ly": 1825, "p": 6513},
    {"key": "Chumpi-Peru", "n": "Chumpi", "c": "Peru", "r": "per_ayacucho", "ll": [-15.09444, -73.74806], "ey": 1525, "ly": 2025, "p": 6510, "al": ["chumbi", "Chumbi"]},
    {"key": "Arévalo González-Venezuela", "n": "Arévalo González", "c": "Venezuela", "r": "ven_miranda", "ll": [10.22778, -66.17111], "ey": 1850, "ly": 2025, "p": 6509},
    {"key": "El Oro-Peru", "n": "El Oro", "c": "Peru", "r": "per_apurimac", "ll": [-14.20889, -73.05833], "ey": 1525, "ly": 2025, "p": 6509, "al": ["ayahuay", "ayahuasa", "ayahuaya"]},
    {"key": "Andaymarca-Peru_2", "n": "Andaymarca", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-13.928, -75.341], "ey": 1525, "ly": 1825, "p": 6507},
    {"key": "Lurihuas-Peru", "n": "Lurihuas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.87397, -77.55342], "ey": 1438, "ly": 1530, "p": 6506, "al": ["allpacoto", "caral", "cerro colorado"]},
    {"key": "Chotuna-Peru", "n": "Chotuna", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.71872, -79.953], "ey": -2000, "ly": 1530, "p": 6505, "al": ["chornancap", "huaca blanca norte", "huaca el mirador"]},
    {"key": "La Pastora-Venezuela", "n": "La Pastora", "c": "Venezuela", "r": "ven_falcon", "ll": [11.19056, -68.61556], "ey": 1850, "ly": 2025, "p": 6504},
    {"key": "Inta-Ecuador", "n": "Inta", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [0.268, -78.584], "ey": 1525, "ly": 1830, "p": 6502, "al": ["intag", "quilca", "quilcas"]},
    {"key": "Machaca-Bolivia", "n": "Machaca", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.122, -66.869], "ey": 1525, "ly": 1825, "p": 6499, "al": ["machacamarca", "Machacamarca"]},
    {"key": "Ambar-Peru", "n": "Ambar", "c": "Peru", "r": "per_lima", "ll": [-10.75611, -77.27194], "ey": 1525, "ly": 2025, "p": 6497, "al": ["ámbar", "Ámbar"]},
    {"key": "Viso-Peru", "n": "Viso", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.806, -76.325], "ey": 1525, "ly": 1825, "p": 6497},
    {"key": "Chacoche-Peru", "n": "Chacoche", "c": "Peru", "r": "per_apurimac", "ll": [-13.94111, -72.99111], "ey": 1525, "ly": 2025, "p": 6494},
    {"key": "San Francisco de Yavi-Argentina", "n": "San Francisco de Yavi", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-22.131, -65.462], "ey": 1525, "ly": 1830, "p": 6494},
    {"key": "Ancon-Peru", "n": "Ancon", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.774, -77.174], "ey": 1525, "ly": 1825, "p": 6494, "al": ["lancon", "Lancon"]},
    {"key": "Lamari-Peru", "n": "Lamari", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-14.061, -75.019], "ey": 1525, "ly": 1825, "p": 6494},
    {"key": "Conila-Peru", "n": "Conila", "c": "Peru", "r": "per_amazonas", "ll": [-6.15917, -78.14194], "ey": 1525, "ly": 2025, "p": 6493, "al": ["cohechan", "concha", "Cohechan"]},
    {"key": "Santa Rosalia-Venezuela", "n": "Santa Rosalia", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [10.502, -66.91], "ey": 1795, "ly": 1830, "p": 6492, "ex": [{"date": "1950.1.1", "name": "Santa Rosalia"}], "al": ["altagracia", "candelaria", "cuartel san carlos"]},
    {"key": "Julcamarca-Peru", "n": "Julcamarca", "c": "Peru", "r": "per_huancavelica", "ll": [-13.01472, -74.44444], "ey": 1525, "ly": 2025, "p": 6489},
    {"key": "Santa Ana de Briviesca-Chile", "n": "Santa Ana de Briviesca", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-32.252, -70.931], "ey": 1525, "ly": 1830, "p": 6488},
    {"key": "Tomanga-Peru_2", "n": "Tomanga", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.531, -74.644], "ey": 1525, "ly": 1825, "p": 6487},
    {"key": "Páramo-Colombia", "n": "Páramo", "c": "Colombia", "r": "col_santander", "ll": [6.41681, -73.17022], "ey": 1525, "ly": 2025, "p": 6485, "al": ["paramo", "Paramo"]},
    {"key": "Cabinda-Argentina", "n": "Cabinda", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-30.984, -63.833], "ey": 1536, "ly": 1749, "p": 6484},
    {"key": "Arajuno (ecu_napo)-Ecuador", "n": "Arajuno", "c": "Ecuador", "r": "ecu_napo", "ll": [-1.23321, -77.68919], "ey": 1850, "ly": 2025, "p": 6482},
    {"key": "Carhuapampa-Peru", "n": "Carhuapampa", "c": "Peru", "r": "per_ancash", "ll": [-10.4975, -77.24278], "ey": 1525, "ly": 2025, "p": 6481, "al": ["aco", "pimachi", "Aco"]},
    {"key": "Romeral (chl_region_del_maule)-Chile", "n": "Romeral", "c": "Chile", "r": "chl_region_del_maule", "ll": [-34.95693, -71.12337], "ey": 1525, "ly": 2017, "p": 6480, "ex": [{"date": "1950.1.1", "name": "Romeral"}]},
    {"key": "Caguán-Colombia", "n": "Caguán", "c": "Colombia", "r": "col_huila", "ll": [2.86408, -75.23275], "ey": 1525, "ly": 2018, "p": 6477, "al": ["caguan", "Caguan"]},
    {"key": "Ticllos-Peru", "n": "Ticllos", "c": "Peru", "r": "per_ancash", "ll": [-10.25306, -77.19083], "ey": 1525, "ly": 2025, "p": 6477},
    {"key": "Esmeralda-Peru", "n": "Esmeralda", "c": "Peru", "r": "per_huancavelica", "ll": [-13.3666, -75.339], "ey": 1525, "ly": 2017, "p": 6476, "al": ["sinto", "cinto", "Sinto"]},
    {"key": "Sageo-Ecuador", "n": "Sageo", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.722, -78.871], "ey": 1525, "ly": 1830, "p": 6476, "al": ["saxeo", "saxes", "Saxeo"]},
    {"key": "Warichupa-Peru", "n": "Warichupa", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.97402, -76.63575], "ey": 1438, "ly": 1530, "p": 6476, "al": ["pajchatuna", "patococha", "pirhua pirhua"]},
    {"key": "Chillogallo-Ecuador", "n": "Chillogallo", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-0.278, -78.557], "ey": 1525, "ly": 1830, "p": 6475, "al": ["chillogalle", "Chillogalle"]},
    {"key": "Huanacaure-Peru_2", "n": "Huanacaure", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.76097, -75.85113], "ey": -3000, "ly": 1530, "p": 6475},
    {"key": "Quisquis-Peru_2", "n": "Quisquis", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-9.516, -78.028], "ey": 1525, "ly": 1825, "p": 6474},
    {"key": "Belen-Chile", "n": "Belen", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-18.468, -69.515], "ey": 1525, "ly": 1825, "p": 6470, "al": ["beiten", "Beiten"]},
    {"key": "Cerro Gato-Peru", "n": "Cerro Gato", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.77947, -79.57578], "ey": 0, "ly": 1530, "p": 6469, "al": ["cerro el tigre", "cerros caballo blanco - el toro", "el progreso"]},
    {"key": "El Simbolar-Argentina", "n": "El Simbolar", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.63347, -64.90178], "ey": 80, "ly": 1500, "p": 6469},
    {"key": "Cunaviche-Venezuela", "n": "Cunaviche", "c": "Venezuela", "r": "ven_apure", "ll": [7.05839, -67.57996], "ey": 1850, "ly": 2025, "p": 6466},
    {"key": "Amparaes-Peru", "n": "Amparaes", "c": "Peru", "r": "per_cusco", "ll": [-13.0549, -71.9442], "ey": 1525, "ly": 2017, "p": 6466, "al": ["amparaez", "Amparaez"]},
    {"key": "Tambo (per_huancavelica)-Peru", "n": "Tambo", "c": "Peru", "r": "per_huancavelica", "ll": [-13.68944, -75.275], "ey": 1525, "ly": 2025, "p": 6466},
    {"key": "Bayas-Ecuador", "n": "Bayas", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.731, -78.832], "ey": 1525, "ly": 1830, "p": 6462, "al": ["opar", "upar", "Opar"]},
    {"key": "Santa Cruz (per_cajamarca)-Peru", "n": "Santa Cruz", "c": "Peru", "r": "per_cajamarca", "ll": [-6.095, -78.85278], "ey": 1525, "ly": 2025, "p": 6460, "al": ["la cruz", "La Cruz"]},
    {"key": "Yorongo-Peru", "n": "Yorongo", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-6.714, -77.144], "ey": 1525, "ly": 1825, "p": 6460},
    {"key": "Pasa-Ecuador", "n": "Pasa", "c": "Ecuador", "r": "ecu_tungurahua", "ll": [-1.22691, -78.76225], "ey": 1850, "ly": 2025, "p": 6458},
    {"key": "Para-Peru", "n": "Para", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-15.078, -73.893], "ey": 1525, "ly": 1825, "p": 6457},
    {"key": "Santa Rosa De Cuzubamba-Ecuador", "n": "Santa Rosa De Cuzubamba", "c": "Ecuador", "r": "ecu_pichincha", "ll": [-0.03439, -78.28179], "ey": 1850, "ly": 2025, "p": 6456},
    {"key": "Llocllo-Bolivia", "n": "Llocllo", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-16.486, -68.436], "ey": 1525, "ly": 1825, "p": 6456},
    {"key": "Huachacalla-Bolivia", "n": "Huachacalla", "c": "Bolivia", "r": "bol_oruro", "ll": [-18.79298, -68.26157], "ey": 1525, "ly": 2026, "p": 6453, "al": ["guachacalla", "Guachacalla"]},
    {"key": "Magdalena-Ecuador", "n": "Magdalena", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-0.234, -78.533], "ey": 1525, "ly": 1830, "p": 6453, "al": ["maria magdalena", "Maria Magdalena"]},
    {"key": "San Bartolome de Gamboa-Chile", "n": "San Bartolome de Gamboa", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-36.623, -72.132], "ey": 1580, "ly": 1830, "p": 6451},
    {"key": "Ambuquí-Ecuador", "n": "Ambuquí", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.38747, -78.00419], "ey": 1850, "ly": 2025, "p": 6450},
    {"key": "Subcunga-Peru", "n": "Subcunga", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.982, -73.024], "ey": 1525, "ly": 1825, "p": 6450, "al": ["subyunca", "Subyunca"]},
    {"key": "Villa de Belen-Uruguay", "n": "Villa de Belen", "c": "Uruguay", "r": "crp_banda_oriental_misiones", "ll": [-30.789, -57.779], "ey": 1801, "ly": 1830, "p": 6449},
    {"key": "Flores-Ecuador", "n": "Flores", "c": "Ecuador", "r": "ecu_chimborazo", "ll": [-1.83208, -78.65465], "ey": 1850, "ly": 2025, "p": 6445},
    {"key": "Colquioc-Peru", "n": "Colquioc", "c": "Peru", "r": "per_ancash", "ll": [-10.31222, -77.61528], "ey": -1000, "ly": 2025, "p": 6445, "al": ["chasquitambo", "cerro baúl", "Chasquitambo"]},
    {"key": "Canis-Peru", "n": "Canis", "c": "Peru", "r": "per_ancash", "ll": [-10.33889, -77.16889], "ey": 1525, "ly": 2025, "p": 6444},
    {"key": "Ávila-Ecuador", "n": "Ávila", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.64378, -77.3478], "ey": 1850, "ly": 2025, "p": 6441},
    {"key": "San José De Chimbo-Ecuador", "n": "San José De Chimbo", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.66729, -79.01351], "ey": 1534, "ly": 2025, "p": 6439, "al": ["san jose de chimbo", "San Jose de Chimbo"]},
    {"key": "Pocohuanca-Peru", "n": "Pocohuanca", "c": "Peru", "r": "per_apurimac", "ll": [-14.21833, -73.08694], "ey": 1525, "ly": 2025, "p": 6439, "al": ["pocoanca", "Pocoanca"]},
    {"key": "Estancopata-Peru", "n": "Estancopata", "c": "Peru", "r": "inca_collasuyu", "ll": [-13.72612, -71.55749], "ey": 1438, "ly": 1530, "p": 6436, "al": ["andenes de patapata", "cuncaccasa", "pata pata"]},
    {"key": "Salasaca-Ecuador", "n": "Salasaca", "c": "Ecuador", "r": "ecu_tungurahua", "ll": [-1.31546, -78.57617], "ey": 1850, "ly": 2025, "p": 6434},
    {"key": "Espite-Peru", "n": "Espite", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.568, -74.616], "ey": 1525, "ly": 1825, "p": 6433, "al": ["espiti", "Espiti"]},
    {"key": "Zumbi-Ecuador", "n": "Zumbi", "c": "Ecuador", "r": "ecu_zamora_chinchipe", "ll": [-3.89405, -78.77845], "ey": 1920, "ly": 2025, "p": 6431},
    {"key": "Congona - Cataneo Molinete-Peru", "n": "Congona - Cataneo Molinete", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.69473, -77.82981], "ey": -1000, "ly": 1530, "p": 6431, "al": ["san agustin de leymabamba", "tambo pomacochas", "San Agustin de Leymabamba"]}
]

HEADERS = {"User-Agent": "ViscountToponymyLookup/1.0 (https://confoederatio.org)"}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def lookup_item(it):
    lat, lng = it["ll"]
    name = it["n"]
    country = it["c"]
    res = {"key": it["key"], "n": name, "c": country, "r": it["r"], "ey": it["ey"], "ly": it["ly"], "ll": it["ll"], "al": it.get("al", []), "geo_es": [], "search_es": [], "extracts": {}}
    # 1. GeoSearch on es.wikipedia
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        d = fetch_json(u)
        res["geo_es"] = [{"title": x["title"], "dist": x["dist"]} for x in d.get("query", {}).get("geosearch", [])]
    except Exception as e:
        res["geo_err"] = str(e)
    # 2. Search on es.wikipedia for name + country
    try:
        q = urllib.parse.quote(f'"{name}" {country}')
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=4&format=json"
        d = fetch_json(u)
        res["search_es"] = [x["title"] for x in d.get("query", {}).get("search", [])]
    except Exception as e:
        res["search_err"] = str(e)
    # 3. Fetch extracts for top geo title + top search title
    titles = []
    for g in res["geo_es"][:2]:
        if g["title"] not in titles:
            titles.append(g["title"])
    for s in res["search_es"][:2]:
        if s not in titles:
            titles.append(s)
    if titles:
        try:
            t_param = urllib.parse.quote("|".join(titles))
            u = f"https://es.wikipedia.org/w/api.php?action=query&titles={t_param}&prop=extracts&exintro=1&explaintext=1&exchars=1200&format=json"
            d = fetch_json(u)
            for p in d.get("query", {}).get("pages", {}).values():
                if "title" in p and "extract" in p:
                    res["extracts"][p["title"]] = p["extract"]
        except Exception:
            pass
    return res

out = []
with ThreadPoolExecutor(max_workers=10) as ex:
    futs = {ex.submit(lookup_item, it): it["key"] for it in INPUT}
    for fut in as_completed(futs):
        out.append(fut.result())

by_key = {x["key"]: x for x in out}
ordered = [by_key[it["key"]] for it in INPUT]
with open(r"f:\Active Projects\Project 1509 - SVEA\tests\quipu_022_wiki.json", "w", encoding="utf-8") as f:
    json.dump(ordered, f, ensure_ascii=False, indent=2)
print("Done:", len(ordered))
