import json
import urllib.request
import urllib.parse
import time
import re

INPUT = [
  {"key": "Pangor-Ecuador", "n": "Pangor", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-1.82, -78.882], "ey": 1525, "ly": 1830, "p": 6427},
  {"key": "Palpas A-Peru", "n": "Palpas A", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.505, -77.095], "ey": 1525, "ly": 1825, "p": 6424},
  {"key": "Santa Cruz (vp_intendencia_lima)-Peru", "n": "Santa Cruz", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-13.024, -76.42], "ey": 1542, "ly": 1825, "p": 6423},
  {"key": "Salcabamba-Peru", "n": "Salcabamba", "c": "Peru", "r": "per_huancavelica", "ll": [-12.20167, -74.78056], "ey": 1525, "ly": 2025, "p": 6422, "al": ["silcabamba", "Silcabamba"]},
  {"key": "Santa Barbara (vng_santafe_tunja_highlands)-Colombia", "n": "Santa Barbara", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [4.592, -74.078], "ey": 1525, "ly": 1830, "p": 6421, "al": ["castrense", "Castrense"]},
  {"key": "Cochabamba (vp_intendencia_trujillo)-Peru", "n": "Cochabamba", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-6.922, -77.897], "ey": 0, "ly": 1825, "p": 6420, "al": ["chachapoyas cochabamba", "celendin", "lagunas"]},
  {"key": "Cerro Coronado-Peru", "n": "Cerro Coronado", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.47611, -71.45589], "ey": 500, "ly": 1530, "p": 6415, "al": ["cahuillacta", "cerro pajonal", "yumina"]},
  {"key": "Viche-Ecuador", "n": "Viche", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.60976, -79.54556], "ey": 1850, "ly": 2025, "p": 6414},
  {"key": "Gámbita-Colombia", "n": "Gámbita", "c": "Colombia", "r": "col_boyaca", "ll": [5.946, -73.34418], "ey": 1525, "ly": 2025, "p": 6411, "al": ["gambita", "Gambita"]},
  {"key": "Aricagua (ven_merida)-Venezuela", "n": "Aricagua", "c": "Venezuela", "r": "ven_merida", "ll": [8.14544, -71.15305], "ey": 1538, "ly": 2025, "p": 6411},
  {"key": "Chumillo-Peru", "n": "Chumillo", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-15.457, -73.693], "ey": 1525, "ly": 1825, "p": 6411, "al": ["chamillo", "chintillo", "Chamillo"]},
  {"key": "Tiaparo-Peru", "n": "Tiaparo", "c": "Peru", "r": "per_apurimac", "ll": [-14.1768, -73.0973], "ey": 1525, "ly": 2017, "p": 6410},
  {"key": "Chasqui-Peru", "n": "Chasqui", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.455, -76.598], "ey": 1525, "ly": 1825, "p": 6407},
  {"key": "Livilcar-Chile", "n": "Livilcar", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-18.498, -69.706], "ey": 1525, "ly": 1825, "p": 6407, "al": ["libilca", "Libilca"]},
  {"key": "Culluri-Bolivia", "n": "Culluri", "c": "Bolivia", "r": "bol_oruro", "ll": [-18.2874, -67.51702], "ey": 1525, "ly": 2024, "p": 6405},
  {"key": "Comandante Luis Piedrabuena-Argentina", "n": "Comandante Luis Piedrabuena", "c": "Argentina", "r": "arg_santa_cruz", "ll": [-49.98271, -68.91363], "ey": 1920, "ly": 2010, "p": 6405},
  {"key": "Juan Vicente Gómez-Venezuela", "n": "Juan Vicente Gómez", "c": "Venezuela", "r": "ven_tachira", "ll": [7.80833, -72.36222], "ey": 1850, "ly": 2025, "p": 6404},
  {"key": "La Dolores-Colombia", "n": "La Dolores", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.49768, -76.47615], "ey": 1525, "ly": 2018, "p": 6403, "al": ["caucaseco", "yunde", "Caucaseco"]},
  {"key": "San José Del Tambo-Ecuador", "n": "San José Del Tambo", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-2.031, -79.19628], "ey": 1850, "ly": 2025, "p": 6402},
  {"key": "Pichirhua-Peru", "n": "Pichirhua", "c": "Peru", "r": "per_apurimac", "ll": [-13.86083, -73.07333], "ey": 1525, "ly": 2025, "p": 6402},
  {"key": "Caracol-Colombia", "n": "Caracol", "c": "Colombia", "r": "col_sucre", "ll": [9.41785, -75.39745], "ey": 1776, "ly": 2018, "p": 6400, "al": ["san cristobal", "San Cristobal"]},
  {"key": "Canzacoto-Ecuador", "n": "Canzacoto", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-0.433, -78.75], "ey": 1525, "ly": 1830, "p": 6400, "al": ["cansacoto", "Cansacoto"]},
  {"key": "Pararca-Peru", "n": "Pararca", "c": "Peru", "r": "per_ayacucho", "ll": [-15.2175, -73.46472], "ey": 1525, "ly": 2025, "p": 6399},
  {"key": "Tauca-Peru", "n": "Tauca", "c": "Peru", "r": "per_ancash", "ll": [-8.47028, -78.03778], "ey": 1525, "ly": 2025, "p": 6399},
  {"key": "Jesus de Pajaten-Peru", "n": "Jesus de Pajaten", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-7.507, -77.332], "ey": 1525, "ly": 1825, "p": 6396, "al": ["ochanache", "Ochanache"]},
  {"key": "Río Frío-Colombia", "n": "Río Frío", "c": "Colombia", "r": "col_magdalena", "ll": [10.90511, -74.17263], "ey": 1850, "ly": 2018, "p": 6393},
  {"key": "Soconcho-Argentina", "n": "Soconcho", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.496, -63.817], "ey": 1536, "ly": 1830, "p": 6393},
  {"key": "Santa Rosa (ven_anzoategui)-Venezuela", "n": "Santa Rosa", "c": "Venezuela", "r": "ven_anzoategui", "ll": [9.58111, -64.29167], "ey": 1900, "ly": 2025, "p": 6391},
  {"key": "Santa Lucia-Peru_2", "n": "Santa Lucia", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.23601, -75.71901], "ey": -1000, "ly": 1530, "p": 6391, "al": ["tambo de mora", "venta de chagua", "Tambo de Mora"]},
  {"key": "Plataforma Obiwan A1 y su vía de acceso-Colombia", "n": "Plataforma Obiwan A1 y su vía de acceso", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [9.54133, -75.53149], "ey": 1300, "ly": 1500, "p": 6388},
  {"key": "Tinguizio-Colombia", "n": "Tinguizio", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [10.038, -75.148], "ey": 1525, "ly": 1693, "p": 6387, "al": ["heyama", "Heyama"]},
  {"key": "Atahualpa (ecu_el_oro)-Ecuador", "n": "Atahualpa", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.55836, -79.71035], "ey": 1850, "ly": 2025, "p": 6386},
  {"key": "Estero Calbureo-Chile", "n": "Estero Calbureo", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-37.47672, -72.57688], "ey": 0, "ly": 1500, "p": 6383, "al": ["cerro niuhueno", "sucesión moraga", "Cerro Niuhueno"]},
  {"key": "San Juan de Chacña-Peru", "n": "San Juan de Chacña", "c": "Peru", "r": "per_apurimac", "ll": [-13.92417, -73.18222], "ey": 1525, "ly": 2025, "p": 6380, "al": ["chacna", "chacña", "Chacna"]},
  {"key": "San Pablo (ecu_manabi)-Ecuador", "n": "San Pablo", "c": "Ecuador", "r": "ecu_manabi", "ll": [-1.22298, -80.06782], "ey": 1850, "ly": 2025, "p": 6377},
  {"key": "Macro-Peru", "n": "Macro", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.36529, -77.91513], "ey": 1000, "ly": 1530, "p": 6377, "al": ["loma pucara", "silic", "tuente"]},
  {"key": "Bituima-Colombia", "n": "Bituima", "c": "Colombia", "r": "col_cundinamarca", "ll": [4.87217, -74.53961], "ey": 1525, "ly": 2025, "p": 6372, "al": ["bigtuyma", "valle de bituima", "Bigtuyma"]},
  {"key": "Soro-Venezuela", "n": "Soro", "c": "Venezuela", "r": "ven_sucre", "ll": [10.54167, -62.44056], "ey": 1736, "ly": 2025, "p": 6372, "al": ["san juan bautista soro", "saro", "San Juan Bautista Soro"]},
  {"key": "Huarhua-Peru", "n": "Huarhua", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-15.188, -72.964], "ey": 1525, "ly": 1825, "p": 6371},
  {"key": "Huayronca-Peru", "n": "Huayronca", "c": "Peru", "r": "inca_cuzco_heartland", "ll": [-13.55962, -72.57094], "ey": -2000, "ly": 1532, "p": 6371, "al": ["pikiorcco", "playa inchis", "tablachaka"]},
  {"key": "Undavi-Bolivia", "n": "Undavi", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.108, -67.896], "ey": 1525, "ly": 1825, "p": 6364, "al": ["choquecota", "chuquicota", "Chuquicota"]},
  {"key": "Despeñaderos-Argentina_2", "n": "Despeñaderos", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.81138, -64.28245], "ey": 80, "ly": 1500, "p": 6364},
  {"key": "Sachacuy-Peru", "n": "Sachacuy", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.48944, -76.36391], "ey": -3000, "ly": 1530, "p": 6363, "al": ["avila", "oriol", "Avila"]},
  {"key": "Ayavi-Peru", "n": "Ayavi", "c": "Peru", "r": "per_huancavelica", "ll": [-13.70306, -75.35111], "ey": 1525, "ly": 2025, "p": 6362},
  {"key": "Huaylacucho-Peru", "n": "Huaylacucho", "c": "Peru", "r": "per_huancavelica", "ll": [-12.7945, -74.943], "ey": 0, "ly": 2017, "p": 6362, "al": ["chankilcocha", "hornos coloniales de ccoripacccha", "hornos coloniales de santa rosa"]},
  {"key": "Santo Domingo de los Olleros-Peru", "n": "Santo Domingo de los Olleros", "c": "Peru", "r": "per_lima", "ll": [-12.21889, -76.51417], "ey": 1525, "ly": 2025, "p": 6362, "al": ["olleros", "Olleros"]},
  {"key": "Callanmarca-Peru", "n": "Callanmarca", "c": "Peru", "r": "per_huancavelica", "ll": [-12.86667, -74.62333], "ey": 1525, "ly": 2025, "p": 6361},
  {"key": "Conayca-Peru", "n": "Conayca", "c": "Peru", "r": "per_huancavelica", "ll": [-12.52, -75.00667], "ey": 1525, "ly": 2025, "p": 6361, "al": ["conaica", "Conaica"]},
  {"key": "Arauca (col_caldas)-Colombia", "n": "Arauca", "c": "Colombia", "r": "col_caldas", "ll": [5.11073, -75.70292], "ey": 1850, "ly": 2018, "p": 6359},
  {"key": "Cahuasquí-Ecuador", "n": "Cahuasquí", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.53004, -78.23939], "ey": 1525, "ly": 2025, "p": 6358, "al": ["cahuasqui", "caguasqui", "Cahuasqui"]},
  {"key": "Choco-Peru", "n": "Choco", "c": "Peru", "r": "per_arequipa", "ll": [-15.57667, -72.12889], "ey": 1525, "ly": 2025, "p": 6358},
  {"key": "Suratá-Colombia", "n": "Suratá", "c": "Colombia", "r": "col_santander", "ll": [7.36658, -72.98423], "ey": 1525, "ly": 2025, "p": 6355, "al": ["surata", "santo ecce home cacota de surata", "Surata"]},
  {"key": "Huancapon-Peru", "n": "Huancapon", "c": "Peru", "r": "per_lima", "ll": [-10.54944, -77.1125], "ey": 1525, "ly": 2025, "p": 6354, "al": ["huancapón", "huncapon", "Huancapón"]},
  {"key": "Bosa-Colombia", "n": "Bosa", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [4.609, -74.186], "ey": 1000, "ly": 1830, "p": 6350, "al": ["boza", "Boza"]},
  {"key": "Huancaray (per_apurimac)-Peru", "n": "Huancaray", "c": "Peru", "r": "per_apurimac", "ll": [-14.2514, -73.0271], "ey": 1525, "ly": 2017, "p": 6347, "al": ["huancari", "Huancari"]},
  {"key": "Chupaca (per_huancavelica)-Peru", "n": "Chupaca", "c": "Peru", "r": "per_huancavelica", "ll": [-12.5227, -74.8306], "ey": 1525, "ly": 2017, "p": 6345},
  {"key": "Huacahuaca-Peru", "n": "Huacahuaca", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.283, -75.289], "ey": 1525, "ly": 1825, "p": 6344, "al": ["huallanto", "Huallanto"]},
  {"key": "Chacamarca-Peru", "n": "Chacamarca", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.00156, -76.20852], "ey": 500, "ly": 1532, "p": 6343, "al": ["ingapirca", "upamayo", "pumpu"]},
  {"key": "Cerro Tinoyo-Peru", "n": "Cerro Tinoyo", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.40251, -73.13111], "ey": -2000, "ly": 1532, "p": 6342, "al": ["la huerta", "la planchada b", "la planchada"]},
  {"key": "El Milagro (per_cajamarca)-Peru", "n": "El Milagro", "c": "Peru", "r": "per_cajamarca", "ll": [-5.63778, -78.55833], "ey": 1850, "ly": 2025, "p": 6341},
  {"key": "Chinchanga-Ecuador", "n": "Chinchanga", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-4.194, -79.743], "ey": 1525, "ly": 1830, "p": 6341},
  {"key": "Bello Horizonte-Colombia", "n": "Bello Horizonte", "c": "Colombia", "r": "na_nw_amazon_foothills", "ll": [0.40181, -76.52863], "ey": 1300, "ly": 1500, "p": 6341, "al": ["el prado", "El Prado"]},
  {"key": "Polindara-Colombia", "n": "Polindara", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.493, -76.421], "ey": 1525, "ly": 1830, "p": 6340},
  {"key": "Hijuela San Juan-Chile", "n": "Hijuela San Juan", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-37.47728, -72.4877], "ey": 0, "ly": 1500, "p": 6340},
  {"key": "Quives-Peru", "n": "Quives", "c": "Peru", "r": "per_lima", "ll": [-11.6677, -76.7874], "ey": 1525, "ly": 2017, "p": 6339},
  {"key": "Nueva Salamanca de la Ramada-Colombia", "n": "Nueva Salamanca de la Ramada", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [11.264, -73.303], "ey": 1561, "ly": 1625, "p": 6339},
  {"key": "Alto del Rey-Colombia", "n": "Alto del Rey", "c": "Colombia", "r": "col_cauca", "ll": [2.43878, -76.85435], "ey": 1525, "ly": 2018, "p": 6337},
  {"key": "Tunía-Colombia", "n": "Tunía", "c": "Colombia", "r": "col_cauca", "ll": [2.67581, -76.53387], "ey": 1525, "ly": 2018, "p": 6333, "al": ["tunia", "tunja", "Tunia"]},
  {"key": "Alaques-Ecuador", "n": "Alaques", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-0.866, -78.609], "ey": 1525, "ly": 1830, "p": 6333},
  {"key": "Calderas-Colombia", "n": "Calderas", "c": "Colombia", "r": "col_cauca", "ll": [2.63542, -76.04523], "ey": 1525, "ly": 2018, "p": 6330, "al": ["concepcion calderas", "Concepcion Calderas"]},
  {"key": "Llinque-Peru", "n": "Llinque", "c": "Peru", "r": "per_apurimac", "ll": [-14.0062, -73.2987], "ey": 1525, "ly": 2017, "p": 6329, "al": ["caracara", "Caracara"]},
  {"key": "Alagastine-Argentina", "n": "Alagastine", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.584, -63.005], "ey": 1536, "ly": 1830, "p": 6323},
  {"key": "Laguna del Juncal-Argentina", "n": "Laguna del Juncal", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-40.80611, -63.125], "ey": -1519, "ly": -88, "p": 6322},
  {"key": "Capacmarca-Peru", "n": "Capacmarca", "c": "Peru", "r": "per_apurimac", "ll": [-14.00722, -72.0025], "ey": 1525, "ly": 2025, "p": 6321, "al": ["capacmarco", "Capacmarco"]},
  {"key": "Belen (vp_intendencia_puno)-Bolivia", "n": "Belen", "c": "Bolivia", "r": "vp_intendencia_puno", "ll": [-15.995, -68.707], "ey": 1525, "ly": 1825, "p": 6321},
  {"key": "Santa Cruz del Valle-Peru", "n": "Santa Cruz del Valle", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.771, -76.161], "ey": 1525, "ly": 1825, "p": 6319},
  {"key": "Sabagasta-Argentina", "n": "Sabagasta", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-28.628, -63.495], "ey": 1536, "ly": 2022, "p": 6316},
  {"key": "Badillo-Colombia", "n": "Badillo", "c": "Colombia", "r": "col_la_guajira", "ll": [10.63088, -73.12823], "ey": 1528, "ly": 2018, "p": 6312, "al": ["san antonio vadillo", "san antonio de badillo", "vadillos"]},
  {"key": "Villa Libertador San Martín-Argentina", "n": "Villa Libertador San Martín", "c": "Argentina", "r": "arg_entre_rios", "ll": [-32.07622, -60.46595], "ey": 1850, "ly": 2010, "p": 6312},
  {"key": "San Jacinto-Ecuador", "n": "San Jacinto", "c": "Ecuador", "r": "ecu_guayas", "ll": [-1.62221, -80.11013], "ey": 1850, "ly": 2025, "p": 6311},
  {"key": "Choque-Peru_2", "n": "Choque", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.427, -77.492], "ey": 1525, "ly": 1825, "p": 6310},
  {"key": "San Miguel Guere-Venezuela", "n": "San Miguel Guere", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [9.838, -65.134], "ey": 1538, "ly": 1830, "p": 6304, "al": ["arabenicuar", "Arabenicuar"]},
  {"key": "Labranzagrande-Colombia", "n": "Labranzagrande", "c": "Colombia", "r": "col_boyaca", "ll": [5.56269, -72.57777], "ey": 1525, "ly": 2025, "p": 6301, "al": ["labranza grande", "Labranza grande"]},
  {"key": "Malaver-Colombia", "n": "Malaver", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [1.03, -77.657], "ey": 1538, "ly": 1830, "p": 6300, "al": ["malave", "malhaber", "Malave"]},
  {"key": "Chalhuani-Peru", "n": "Chalhuani", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.824, -73.043], "ey": 1525, "ly": 1825, "p": 6299, "al": ["chalguani", "chaluani", "chalvani"]},
  {"key": "Huayllacayan-Peru", "n": "Huayllacayan", "c": "Peru", "r": "per_ancash", "ll": [-10.245, -77.43472], "ey": 1525, "ly": 2025, "p": 6293, "al": ["huayllacayán", "huanchay", "huayllayan"]},
  {"key": "Camata-Bolivia", "n": "Camata", "c": "Bolivia", "r": "bol_la_paz", "ll": [-15.23965, -68.74776], "ey": 1525, "ly": 2024, "p": 6291},
  {"key": "Thoe-Peru", "n": "Thoe", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-6.22, -77.048], "ey": 1525, "ly": 1830, "p": 6288, "al": ["toe", "Toe"]},
  {"key": "Camanti-Peru", "n": "Camanti", "c": "Peru", "r": "per_cusco", "ll": [-13.23139, -70.75444], "ey": 1525, "ly": 2025, "p": 6285, "al": ["camanti-quincemil", "quince mil", "Camanti-Quincemil"]},
  {"key": "Lamas (per_la_libertad)-Peru", "n": "Lamas", "c": "Peru", "r": "per_la_libertad", "ll": [-8.0169, -77.4796], "ey": 1525, "ly": 2017, "p": 6285, "al": ["la soledad", "parcoy", "porcoy"]}
]

def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "QuipuToponymyResearch/1.0"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))

def wiki_geosearch(lang, lat, lng, radius=10000):
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius={radius}&gslimit=8&format=json"
    try:
        data = api_get(url)
        return data.get("query", {}).get("geosearch", [])
    except Exception as e:
        return []

def wiki_search(lang, query):
    q = urllib.parse.quote(query)
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=5&format=json"
    try:
        data = api_get(url)
        return data.get("query", {}).get("search", [])
    except Exception as e:
        return []

def wiki_extract(lang, titles):
    if not titles:
        return {}
    t = urllib.parse.quote("|".join(titles[:10]))
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={t}&format=json"
    try:
        data = api_get(url)
        pages = data.get("query", {}).get("pages", {})
        res = {}
        for p in pages.values():
            if "title" in p:
                res[p["title"]] = p.get("extract", "")
        return res
    except Exception:
        return {}

out = []
for idx, item in enumerate(INPUT):
    lat, lng = item["ll"]
    geo_es = wiki_geosearch("es", lat, lng, 10000)
    geo_en = wiki_geosearch("en", lat, lng, 10000)
    sr_es = wiki_search("es", f'"{item["n"]}" {item["c"]}')
    titles_es = [g["title"] for g in geo_es[:4]] + [s["title"] for s in sr_es[:3]]
    titles_es = list(dict.fromkeys(titles_es))
    ext_es = wiki_extract("es", titles_es[:5])
    out.append({
        "idx": idx,
        "key": item["key"],
        "n": item["n"],
        "c": item["c"],
        "r": item["r"],
        "ll": item["ll"],
        "ey": item["ey"],
        "ly": item["ly"],
        "al": item.get("al", []),
        "geo_es": [(g["title"], round(g["dist"])) for g in geo_es[:5]],
        "geo_en": [(g["title"], round(g["dist"])) for g in geo_en[:3]],
        "sr_es": [s["title"] for s in sr_es[:3]],
        "ext_es": {k: v[:500] for k, v in ext_es.items()}
    })
    if idx % 10 == 9:
        print(f"Processed {idx+1}/90", flush=True)

with open("tests/chunk023_wiki_dump.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("DONE")
