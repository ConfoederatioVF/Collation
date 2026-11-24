import concurrent.futures
import json
import math
import urllib.parse
import urllib.request

INPUT_DATA = [
  {"key": "Santiago Temple-Argentina", "n": "Santiago Temple", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.38598, -63.41954], "ey": 1850, "ly": 2022, "p": 3298},
  {"key": "Mamas-Peru", "n": "Mamas", "c": "Peru", "r": "per_arequipa", "ll": [-16.1493, -72.4921], "ey": 1525, "ly": 2017, "p": 3297, "al": ["maran grande", "querulpa chico", "valle de majes"]},
  {"key": "San Fermin Parua-Peru", "n": "San Fermin Parua", "c": "Peru", "r": "vp_paititi_maynas_amazonia", "ll": [-11.977, -74.031], "ey": 1735, "ly": 1741, "p": 3297},
  {"key": "Tocuyito-Venezuela", "n": "Tocuyito", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [10.1, -68.087], "ey": 1538, "ly": 1830, "p": 3296},
  {"key": "Yanacancha (per_junin)-Peru", "n": "Yanacancha", "c": "Peru", "r": "per_junin", "ll": [-12.20111, -75.38667], "ey": 1850, "ly": 2025, "p": 3294},
  {"key": "Cerro Ñañañique-Peru", "n": "Cerro Ñañañique", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-5.09245, -80.15748], "ey": -1632, "ly": 1530, "p": 3294, "al": ["huaca el mono", "la encantada", "lagunas"]},
  {"key": "Quebrada La Santallana-Peru", "n": "Quebrada La Santallana", "c": "Peru", "r": "inca_collasuyu", "ll": [-17.60249, -70.80522], "ey": 1440, "ly": 1532, "p": 3294},
  {"key": "Agua Clara-Colombia", "n": "Agua Clara", "c": "Colombia", "r": "col_norte_de_santander", "ll": [8.2345, -72.42681], "ey": 1850, "ly": 2018, "p": 3293},
  {"key": "Guachanamá-Ecuador", "n": "Guachanamá", "c": "Ecuador", "r": "ecu_loja", "ll": [-4.02793, -79.83583], "ey": 1525, "ly": 2025, "p": 3293, "al": ["guachanama", "Guachanama"]},
  {"key": "Quebrada Andrespata-Peru", "n": "Quebrada Andrespata", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.0477, -74.11592], "ey": 1000, "ly": 1532, "p": 3293, "al": ["abra yanacocha", "cerro ñahuin puquio", "chiqchicancha"]},
  {"key": "Cerro El Aguila-Peru", "n": "Cerro El Aguila", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.79876, -79.29915], "ey": 0, "ly": 1530, "p": 3292, "al": ["campo nuevo", "cerro el buho", "huaca las delicias"]},
  {"key": "Las Trincheras-Venezuela", "n": "Las Trincheras", "c": "Venezuela", "r": "ven_carabobo", "ll": [10.30575, -68.0925], "ey": 1850, "ly": 2011, "p": 3290},
  {"key": "Nueva Braunau-Chile", "n": "Nueva Braunau", "c": "Chile", "r": "chl_region_de_los_lagos", "ll": [-41.32668, -73.07863], "ey": 1850, "ly": 2017, "p": 3290},
  {"key": "Puerto Mayor de Carabuco-Bolivia", "n": "Puerto Mayor de Carabuco", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-15.7585, -69.06439], "ey": 1525, "ly": 1825, "p": 3290, "al": ["carabuco", "Carabuco"]},
  {"key": "San Isidro-Peru", "n": "San Isidro", "c": "Peru", "r": "per_tumbes", "ll": [-3.6126, -80.5113], "ey": 1850, "ly": 2017, "p": 3287, "al": ["pampa san isidro", "Pampa San Isidro"]},
  {"key": "San Francisco Javier-Colombia", "n": "San Francisco Javier", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.66352, -77.02498], "ey": 1525, "ly": 2018, "p": 3286, "al": ["san francisco del raposo", "San Francisco del Raposo"]},
  {"key": "Buen Consejo del Mamon-Venezuela", "n": "Buen Consejo del Mamon", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [10.238, -67.269], "ey": 1777, "ly": 1830, "p": 3286, "al": ["mamon", "Mamon"]},
  {"key": "Hotel Volcán Puntiagudo-Chile", "n": "Hotel Volcán Puntiagudo", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-41.1246, -73.04245], "ey": 0, "ly": 1500, "p": 3286},
  {"key": "El Farsan-Colombia", "n": "El Farsan", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.755, -75.88722], "ey": 1300, "ly": 1500, "p": 3285},
  {"key": "Herrera-Argentina", "n": "Herrera", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-28.48616, -63.07063], "ey": 1850, "ly": 2022, "p": 3283},
  {"key": "Bahia Cracker-Argentina", "n": "Bahia Cracker", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-42.95056, -64.47778], "ey": -4322, "ly": -2676, "p": 3283},
  {"key": "Loma Colorada-Argentina", "n": "Loma Colorada", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.55783, -63.56213], "ey": 450, "ly": 1500, "p": 3281},
  {"key": "Shilla-Peru", "n": "Shilla", "c": "Peru", "r": "per_ancash", "ll": [-9.23167, -77.625], "ey": 1850, "ly": 2025, "p": 3280},
  {"key": "Autónomo Río Negro-Venezuela", "n": "Autónomo Río Negro", "c": "Venezuela", "r": "ven_amazonas", "ll": [1.76013, -66.24539], "ey": 1900, "ly": 2025, "p": 3279},
  {"key": "Solano-Venezuela", "n": "Solano", "c": "Venezuela", "r": "ven_amazonas", "ll": [1.7214, -66.25177], "ey": 1920, "ly": 2025, "p": 3279},
  {"key": "Esquiri-Bolivia", "n": "Esquiri", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-19.643, -65.219], "ey": 1525, "ly": 1825, "p": 3277, "al": ["mataca alta", "Mataca alta"]},
  {"key": "Cerro Combia grande-Colombia", "n": "Cerro Combia grande", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.90483, -75.67236], "ey": -1000, "ly": 1500, "p": 3277, "al": ["cristo rey", "Cristo Rey"]},
  {"key": "Killway-Peru", "n": "Killway", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.93187, -74.54295], "ey": -2000, "ly": 1530, "p": 3276},
  {"key": "El Palmar-Colombia_2", "n": "El Palmar", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.67, -75.15], "ey": -2457, "ly": 1500, "p": 3276},
  {"key": "Mallco Rancho-Bolivia", "n": "Mallco Rancho", "c": "Bolivia", "r": "bol_cochabamba", "ll": [-17.41749, -66.35536], "ey": 1850, "ly": 2024, "p": 3275},
  {"key": "Villa Tunari (bol_cochabamba)-Bolivia", "n": "Villa Tunari", "c": "Bolivia", "r": "bol_cochabamba", "ll": [-16.9759, -65.42321], "ey": 1950, "ly": 2024, "p": 3274},
  {"key": "La Toma-Argentina_2", "n": "La Toma", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.14258, -64.07485], "ey": 80, "ly": 1500, "p": 3274},
  {"key": "Cegarra-Venezuela", "n": "Cegarra", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.58611, -70.35], "ey": 1850, "ly": 2025, "p": 3273},
  {"key": "San Andres Malaga la Nueva de Mocoa-Colombia", "n": "San Andres Malaga la Nueva de Mocoa", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [1.176, -76.864], "ey": 1557, "ly": 1830, "p": 3273},
  {"key": "Milluaya-Bolivia", "n": "Milluaya", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-16.381, -67.616], "ey": 1525, "ly": 1825, "p": 3273, "al": ["milluhuay", "Milluhuay"]},
  {"key": "Santa Rosa de Mapiri-Bolivia", "n": "Santa Rosa de Mapiri", "c": "Bolivia", "r": "bol_la_paz", "ll": [-15.31629, -68.32505], "ey": 1850, "ly": 2024, "p": 3272},
  {"key": "Ventarrones-Peru_2", "n": "Ventarrones", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-5.52299, -78.54798], "ey": -2000, "ly": 1530, "p": 3271, "al": ["cerro colorado", "tomependa", "Cerro Colorado"]},
  {"key": "Sauce de Luna-Argentina", "n": "Sauce de Luna", "c": "Argentina", "r": "arg_entre_rios", "ll": [-31.23957, -59.21753], "ey": 1850, "ly": 2022, "p": 3270},
  {"key": "Santa Catarina-Colombia", "n": "Santa Catarina", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [10.58, -73.237], "ey": 1777, "ly": 1830, "p": 3270, "al": ["san francisco de asis", "San Francisco de Asis"]},
  {"key": "El Portal-Colombia_2", "n": "El Portal", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.29936, -74.75191], "ey": 500, "ly": 1500, "p": 3268},
  {"key": "Los Kilometros-Venezuela", "n": "Los Kilometros", "c": "Venezuela", "r": "ven_monagas", "ll": [10.02882, -63.1118], "ey": 1850, "ly": 2011, "p": 3267, "al": ["rio bonito", "Rio Bonito"]},
  {"key": "Balsapamba-Ecuador", "n": "Balsapamba", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.74987, -79.15576], "ey": 1850, "ly": 2025, "p": 3267},
  {"key": "La Lagunilla-Argentina", "n": "La Lagunilla", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-31.425, -64.305], "ey": 1536, "ly": 1830, "p": 3267},
  {"key": "Madrid-Argentina", "n": "Madrid", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-25.299, -64.864], "ey": 1592, "ly": 1608, "p": 3267},
  {"key": "Arroyo Cabral-Argentina", "n": "Arroyo Cabral", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.48948, -63.40237], "ey": 1850, "ly": 2022, "p": 3264},
  {"key": "Ancahuas-Peru", "n": "Ancahuas", "c": "Peru", "r": "inca_cuzco_heartland", "ll": [-13.45649, -72.36768], "ey": 0, "ly": 1532, "p": 3264, "al": ["andenes de pulla", "andenes de", "andenmayo"]},
  {"key": "28 De Mayo-Ecuador", "n": "28 De Mayo", "c": "Ecuador", "r": "ecu_azuay", "ll": [-3.63608, -78.92638], "ey": 1850, "ly": 2025, "p": 3263},
  {"key": "Chigmuni y Colpa-Bolivia", "n": "Chigmuni y Colpa", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.466, -66.67], "ey": 1525, "ly": 1825, "p": 3262, "al": ["escaleras y guayco", "Escaleras y Guayco"]},
  {"key": "Tastil Pre-Inca-Argentina", "n": "Tastil Pre-Inca", "c": "Argentina", "r": "sc_gran_chaco_pilcomayo", "ll": [-24.451, -65.957], "ey": 1100, "ly": 1430, "p": 3260},
  {"key": "Eduardo Villanueva-Peru", "n": "Eduardo Villanueva", "c": "Peru", "r": "per_cajamarca", "ll": [-7.46444, -78.13], "ey": 1850, "ly": 2025, "p": 3259, "al": ["la grama", "La Grama"]},
  {"key": "La Miranda-Colombia_2", "n": "La Miranda", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.46, -78.68], "ey": -593, "ly": 107, "p": 3259, "al": ["la corlina", "los guaduales", "La Corlina"]},
  {"key": "Julio E. Moreno-Ecuador", "n": "Julio E. Moreno", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.57413, -79.08936], "ey": 1850, "ly": 2025, "p": 3257},
  {"key": "Yura-Bolivia", "n": "Yura", "c": "Bolivia", "r": "bol_potosi", "ll": [-20.07386, -66.12547], "ey": 1525, "ly": 2024, "p": 3257, "al": ["yuta", "Yuta"]},
  {"key": "Santa Teresa-Argentina", "n": "Santa Teresa", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.43674, -60.79046], "ey": 1850, "ly": 2022, "p": 3257},
  {"key": "Cashash-Peru", "n": "Cashash", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.4204, -76.82555], "ey": 500, "ly": 1530, "p": 3257, "al": ["contan", "pincuyoj", "san pedro de marañon"]},
  {"key": "Altagracia-Colombia", "n": "Altagracia", "c": "Colombia", "r": "col_quindio", "ll": [4.74014, -75.71423], "ey": 1850, "ly": 2018, "p": 3255, "al": ["la cabañita", "La Cabañita"]},
  {"key": "Huaca El Ollero-Peru", "n": "Huaca El Ollero", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.82714, -79.29503], "ey": -2000, "ly": 1530, "p": 3255, "al": ["cajanleque b", "cajanleque c", "cajanleque d"]},
  {"key": "San Rafael (col_norte_de_santander)-Colombia", "n": "San Rafael", "c": "Colombia", "r": "col_norte_de_santander", "ll": [7.60765, -73.5763], "ey": 1850, "ly": 2018, "p": 3254},
  {"key": "San Roque (col_cesar)-Colombia", "n": "San Roque", "c": "Colombia", "r": "col_cesar", "ll": [9.29027, -73.51496], "ey": 1850, "ly": 2018, "p": 3254},
  {"key": "Dawson-Chile", "n": "Dawson", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-53.81855, -70.44671], "ey": 0, "ly": 1500, "p": 3254},
  {"key": "Isabela-Ecuador", "n": "Isabela", "c": "Ecuador", "r": "ecu_galapagos", "ll": [-0.44555, -91.0894], "ey": 1900, "ly": 2025, "p": 3253},
  {"key": "Huamanmarca-Peru", "n": "Huamanmarca", "c": "Peru", "r": "per_junin", "ll": [-12.1223, -75.2153], "ey": 1850, "ly": 2017, "p": 3253},
  {"key": "Araurima-Venezuela", "n": "Araurima", "c": "Venezuela", "r": "ven_falcon", "ll": [10.93996, -68.67398], "ey": 1850, "ly": 2025, "p": 3252},
  {"key": "Villa Eloísa-Argentina", "n": "Villa Eloísa", "c": "Argentina", "r": "arg_santa_fe", "ll": [-32.96393, -61.55108], "ey": 1850, "ly": 2022, "p": 3252},
  {"key": "Cabezas Largas-Peru", "n": "Cabezas Largas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-13.866, -76.27587], "ey": 1438, "ly": 1530, "p": 3252, "al": ["cerro colorado", "disco verde", "paracas"]},
  {"key": "Sonqoraqay-Peru", "n": "Sonqoraqay", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.29699, -72.95802], "ey": -2000, "ly": 1530, "p": 3252},
  {"key": "La Viña-Peru_2", "n": "La Viña", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.45368, -79.72665], "ey": -2000, "ly": 1532, "p": 3251, "al": ["arbejal a", "arbejal b", "arbejal c"]},
  {"key": "Coachaca Chico-Bolivia", "n": "Coachaca Chico", "c": "Bolivia", "r": "bol_cochabamba", "ll": [-17.41098, -66.34024], "ey": 1850, "ly": 2024, "p": 3250, "al": ["coachaca grande", "huañacahua", "mallco chapi"]},
  {"key": "San Pedro Carasi-Bolivia", "n": "San Pedro Carasi", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.319, -65.689], "ey": 1525, "ly": 1825, "p": 3250, "al": ["uru y carasi", "uruycarasi", "Uru y Carasi"]},
  {"key": "Santa Rosa (ecu_napo_3)-Ecuador", "n": "Santa Rosa", "c": "Ecuador", "r": "ecu_napo", "ll": [-0.97758, -77.45053], "ey": 1525, "ly": 2010, "p": 3249},
  {"key": "Los Barrancones-Venezuela", "n": "Los Barrancones", "c": "Venezuela", "r": "ven_anzoategui", "ll": [9.77187, -65.12184], "ey": 1538, "ly": 2011, "p": 3248, "al": ["san lorenzo guere", "San Lorenzo Guere"]},
  {"key": "Bodegas-Colombia_2", "n": "Bodegas", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.23139, -74.72056], "ey": 1000, "ly": 1500, "p": 3248, "al": ["las pavas", "Las pavas"]},
  {"key": "Aguaclara-Colombia_2", "n": "Aguaclara", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.7251, -78.77505], "ey": -1000, "ly": 1500, "p": 3246},
  {"key": "San Vicente de Piedra Rodada-Peru", "n": "San Vicente de Piedra Rodada", "c": "Peru", "r": "per_piura", "ll": [-4.8316, -80.5844], "ey": 1850, "ly": 2017, "p": 3245},
  {"key": "Cuiba-Venezuela", "n": "Cuiba", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [11.074, -70.029], "ey": 1538, "ly": 1830, "p": 3245},
  {"key": "San Pedro De La Bendita-Ecuador", "n": "San Pedro De La Bendita", "c": "Ecuador", "r": "ecu_loja", "ll": [-3.95935, -79.43585], "ey": 1525, "ly": 2025, "p": 3244},
  {"key": "La Garita-Peru", "n": "La Garita", "c": "Peru", "r": "per_lambayeque", "ll": [-6.796, -79.8811], "ey": 1850, "ly": 2017, "p": 3244, "al": ["la joyita", "las palmeras de la joyita", "La Joyita"]},
  {"key": "Solis de Mataojo-Uruguay", "n": "Solis de Mataojo", "c": "Uruguay", "r": "ury_canelones", "ll": [-34.59765, -55.45993], "ey": 1850, "ly": 2023, "p": 3244},
  {"key": "Cueva de Mito-Peru", "n": "Cueva de Mito", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.42772, -77.43136], "ey": -3000, "ly": 1530, "p": 3243, "al": ["elemento arqueológico aislado cueva de mito", "Elemento Arqueológico Aislado Cueva de Mito"]},
  {"key": "Agua de Oro-Argentina", "n": "Agua de Oro", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.06645, -64.30214], "ey": -1738, "ly": 2022, "p": 3242, "al": ["villa cerro azul", "morteros de chavascate", "Villa Cerro Azul"]},
  {"key": "La Múcura-Colombia", "n": "La Múcura", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.38672, -75.50857], "ey": 1300, "ly": 1500, "p": 3241},
  {"key": "Ubajay-Argentina", "n": "Ubajay", "c": "Argentina", "r": "arg_entre_rios", "ll": [-31.79512, -58.3151], "ey": 1850, "ly": 2022, "p": 3240},
  {"key": "Pichana-Argentina", "n": "Pichana", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.93447, -65.05005], "ey": 80, "ly": 1500, "p": 3238},
  {"key": "La Pila-Ecuador", "n": "La Pila", "c": "Ecuador", "r": "ecu_manabi", "ll": [-1.13431, -80.57602], "ey": 1850, "ly": 2025, "p": 3237},
  {"key": "ZODME El Bosque PS 6-Colombia", "n": "ZODME El Bosque PS 6", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.95063, -75.85515], "ey": 1300, "ly": 1500, "p": 3237, "ex": [{"date": "1973.1.1", "name": "La Virginia"}], "al": ["el bosque", "rs ruta 50 la virginia - asia", "El Bosque"]},
  {"key": "Paradero Indigena-Argentina", "n": "Paradero Indigena", "c": "Argentina", "r": "sc_pampas_salado_colorado", "ll": [-33.20991, -64.42813], "ey": 80, "ly": 1500, "p": 3237},
  {"key": "San Francisco (col_cauca)-Colombia", "n": "San Francisco", "c": "Colombia", "r": "col_cauca", "ll": [2.92451, -76.28863], "ey": 1525, "ly": 2018, "p": 3236, "al": ["caloto nuevo", "Caloto Nuevo"]},
  {"key": "Cecilia-Colombia", "n": "Cecilia", "c": "Colombia", "r": "col_meta", "ll": [4.08132, -73.69688], "ey": 1920, "ly": 2018, "p": 3235, "al": ["san luis de ocoa", "San Luis de Ocoa"]},
  {"key": "Pucacolpa-Peru", "n": "Pucacolpa", "c": "Peru", "r": "per_huancavelica", "ll": [-12.42056, -74.48917], "ey": 1850, "ly": 2025, "p": 3235, "al": ["huallhua", "Huallhua"]},
  {"key": "Unpuco-Peru", "n": "Unpuco", "c": "Peru", "r": "vp_intendencia_puno", "ll": [-15.315, -70.417], "ey": 1525, "ly": 1825, "p": 3235}
]

HEADERS = {"User-Agent": "SVEA-ToponymyResearch/1.0 (https://confoederatio.org)"}

def fetch_json(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=15) as resp:
    return json.loads(resp.read().decode("utf-8"))

def research_item(item):
  key = item["key"]
  name = item["n"]
  country = item["c"]
  region = item["r"]
  lat, lng = item["ll"]
  res = {"key": key, "n": name, "c": country, "r": region, "ll": item["ll"], "ey": item["ey"], "ly": item["ly"], "geo_hits": [], "search_hits": []}

  # 1. Geosearch es.wiki and en.wiki
  for lang in ("es", "en"):
    try:
      url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
      data = fetch_json(url)
      hits = data.get("query", {}).get("geosearch", [])
      if hits:
        titles = "|".join(h["title"] for h in hits[:3])
        ext_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&exchars=1200&titles={urllib.parse.quote(titles)}&format=json"
        ext_data = fetch_json(ext_url)
        pages = ext_data.get("query", {}).get("pages", {})
        by_title = {p.get("title"): p.get("extract", "") for p in pages.values()}
        for h in hits[:3]:
          res["geo_hits"].append({"lang": lang, "title": h["title"], "dist": h["dist"], "extract": by_title.get(h["title"], "")})
    except Exception as e:
      res["geo_hits"].append({"lang": lang, "error": str(e)})

  # 2. Title search on es.wiki (and en.wiki if needed)
  reg_hint = region.split("_", 1)[-1].replace("_", " ")
  q = f'"{name}" {country}'
  try:
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=3&format=json"
    data = fetch_json(url)
    hits = data.get("query", {}).get("search", [])
    if not hits:
      q2 = f"{name} {reg_hint}"
      url2 = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q2)}&srlimit=3&format=json"
      hits = fetch_json(url2).get("query", {}).get("search", [])
    if hits:
      titles = "|".join(h["title"] for h in hits[:2])
      ext_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&exintro=1&explaintext=1&exchars=1500&titles={urllib.parse.quote(titles)}&format=json"
      ext_data = fetch_json(ext_url)
      pages = ext_data.get("query", {}).get("pages", {})
      for p in pages.values():
        res["search_hits"].append({
          "lang": "es",
          "title": p.get("title"),
          "coords": p.get("coordinates"),
          "extract": p.get("extract", "")
        })
  except Exception as e:
    res["search_hits"].append({"lang": "es", "error": str(e)})

  return res

def main():
  results = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    for r in ex.map(research_item, INPUT_DATA):
      results.append(r)
  with open("tests/quipu_051_dossier.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
  print(f"Done: {len(results)} entries")

if __name__ == "__main__":
  main()
