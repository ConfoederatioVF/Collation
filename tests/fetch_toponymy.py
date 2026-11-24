import json
import math
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {"User-Agent": "SVEA-Toponymy/1.0 (https://confoederatio.org)"}

SETTLEMENTS = [
    {"key": "Saquena-Peru", "n": "Saquena", "c": "Peru", "r": "per_loreto", "ll": [-4.725, -73.53306], "ey": 1900, "ly": 2025, "p": 4536, "al": ["bagazan", "Bagazan"]},
    {"key": "Junín (ven_trujillo)-Venezuela", "n": "Junín", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.48222, -70.86667], "ey": 1850, "ly": 2025, "p": 4534},
    {"key": "Pilar de Macapillo-Argentina", "n": "Pilar de Macapillo", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-25.403, -63.982], "ey": 1715, "ly": 1830, "p": 4534, "al": ["columna", "mecapillo", "Columna"]},
    {"key": "Juctacancha-Peru", "n": "Juctacancha", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.2658, -76.45889], "ey": 0, "ly": 1530, "p": 4534, "al": ["calapa", "chogya", "golgayana punta"]},
    {"key": "La Coquera-Colombia", "n": "La Coquera", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.78056, -74.67139], "ey": 1300, "ly": 1500, "p": 4533},
    {"key": "Doradal-Colombia", "n": "Doradal", "c": "Colombia", "r": "col_antioquia", "ll": [5.8999, -74.73523], "ey": 1850, "ly": 2018, "p": 4532},
    {"key": "Siete De Julio-Ecuador", "n": "Siete De Julio", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [-0.18619, -76.7807], "ey": 1920, "ly": 2025, "p": 4531},
    {"key": "Chumbicha-Argentina", "n": "Chumbicha", "c": "Argentina", "r": "arg_catamarca", "ll": [-28.85348, -66.23744], "ey": 1536, "ly": 2010, "p": 4531, "al": ["chumbica", "Chumbica"]},
    {"key": "El Trebol-Colombia", "n": "El Trebol", "c": "Colombia", "r": "na_nw_amazon_foothills", "ll": [0.93193, -76.40319], "ey": -1000, "ly": 1500, "p": 4529},
    {"key": "Sobreancho Torre-Colombia", "n": "Sobreancho Torre", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [3.89784, -73.65714], "ey": 500, "ly": 1500, "p": 4527},
    {"key": "Anisacate-Argentina_2", "n": "Anisacate", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.71191, -64.4137], "ey": 80, "ly": 1500, "p": 4527},
    {"key": "La Caldera-Argentina", "n": "La Caldera", "c": "Argentina", "r": "arg_salta", "ll": [-24.60268, -65.38066], "ey": 1850, "ly": 2022, "p": 4525},
    {"key": "Norberto de la Riestra-Argentina", "n": "Norberto de la Riestra", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-35.27332, -59.77564], "ey": 1850, "ly": 2010, "p": 4524},
    {"key": "Michac-Colombia", "n": "Michac", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [1.253, -77.679], "ey": 1525, "ly": 1830, "p": 4524, "al": ["manchay", "Manchay"]},
    {"key": "Arnoldo Gabaldon (ven_trujillo)-Venezuela", "n": "Arnoldo Gabaldon", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.36826, -70.07833], "ey": 1850, "ly": 2025, "p": 4522},
    {"key": "La Cruz-Argentina_2", "n": "La Cruz", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.3134, -64.42343], "ey": 80, "ly": 1500, "p": 4522},
    {"key": "Raco-Argentina", "n": "Raco", "c": "Argentina", "r": "arg_tucuman", "ll": [-26.67781, -65.42952], "ey": 1850, "ly": 2022, "p": 4519},
    {"key": "Chiapa-Chile", "n": "Chiapa", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.537, -69.204], "ey": 1525, "ly": 1825, "p": 4519},
    {"key": "Chacance-Chile", "n": "Chacance", "c": "Chile", "r": "inca_collasuyu", "ll": [-22.39556, -69.52756], "ey": 761, "ly": 1500, "p": 4518},
    {"key": "Villalonga-Argentina", "n": "Villalonga", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-39.91747, -62.6189], "ey": 1850, "ly": 2010, "p": 4517},
    {"key": "Gochacalla-Peru", "n": "Gochacalla", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.84741, -75.9086], "ey": -1000, "ly": 1530, "p": 4517, "al": ["arqueológico letra machay", "letra machay", "silla"]},
    {"key": "San Antonio (per_lima)-Peru", "n": "San Antonio", "c": "Peru", "r": "per_lima", "ll": [-11.74361, -76.65], "ey": 1850, "ly": 2025, "p": 4516, "al": ["chaclla", "Chaclla"]},
    {"key": "Karajía-Peru", "n": "Karajía", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.16178, -78.02438], "ey": -2000, "ly": 1530, "p": 4515, "al": ["caverna de quiocta", "valle alto del utcubamba", "Caverna de Quiocta"]},
    {"key": "Sarayacu-Ecuador", "n": "Sarayacu", "c": "Ecuador", "r": "ecu_pastaza", "ll": [-1.7323, -77.48711], "ey": 1920, "ly": 2025, "p": 4512},
    {"key": "Santa Elena-Ecuador_2", "n": "Santa Elena", "c": "Ecuador", "r": "vng_guayaquil_esmeraldas", "ll": [-2.227, -80.857], "ey": 1538, "ly": 1830, "p": 4512, "ex": [{"date": "1962.1.1", "name": "Santa Elena"}]},
    {"key": "Seguí-Argentina", "n": "Seguí", "c": "Argentina", "r": "arg_entre_rios", "ll": [-31.95435, -60.12566], "ey": 1850, "ly": 2022, "p": 4510},
    {"key": "El Carmen De Pijilí-Ecuador", "n": "El Carmen De Pijilí", "c": "Ecuador", "r": "ecu_azuay", "ll": [-2.97945, -79.54823], "ey": 1850, "ly": 2025, "p": 4509},
    {"key": "La Arenosa-Colombia", "n": "La Arenosa", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [10.93, -74.76], "ey": -774, "ly": 1500, "p": 4508, "al": ["microplanta gnl- la arenosa", "Microplanta GNL- La Arenosa"]},
    {"key": "Agua Caliente-Venezuela", "n": "Agua Caliente", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.63944, -70.62278], "ey": 1850, "ly": 2025, "p": 4502},
    {"key": "La Aguada-Bolivia", "n": "La Aguada", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.983, -65.283], "ey": 1525, "ly": 1825, "p": 4500},
    {"key": "Punta Teatinos-Chile", "n": "Punta Teatinos", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-29.81778, -71.28851], "ey": -3593, "ly": -540, "p": 4499},
    {"key": "Cañasgordas y Abriaqu-Colombia", "n": "Cañasgordas y Abriaqu", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [6.76, -76.1], "ey": -870, "ly": 1500, "p": 4489, "al": ["umg", "umg 12 la maria", "la oliva"]},
    {"key": "Tomay Kichwa-Peru", "n": "Tomay Kichwa", "c": "Peru", "r": "per_huanuco", "ll": [-10.0775, -76.2125], "ey": 1850, "ly": 2025, "p": 4488},
    {"key": "La Morada-Peru", "n": "La Morada", "c": "Peru", "r": "per_huanuco", "ll": [-8.79444, -76.24972], "ey": 1850, "ly": 2025, "p": 4486},
    {"key": "Dichato-Chile", "n": "Dichato", "c": "Chile", "r": "chl_region_del_bio_bio", "ll": [-36.54125, -72.93623], "ey": 1525, "ly": 2017, "p": 4486, "al": ["dichaco", "Dichaco"]},
    {"key": "Anchihuay-Peru", "n": "Anchihuay", "c": "Peru", "r": "per_ayacucho", "ll": [-12.86361, -73.5825], "ey": 1850, "ly": 2025, "p": 4483},
    {"key": "Corani-Peru", "n": "Corani", "c": "Peru", "r": "per_puno", "ll": [-13.86861, -70.60444], "ey": 1525, "ly": 2025, "p": 4483},
    {"key": "Retiro de los Indios-Colombia", "n": "Retiro de los Indios", "c": "Colombia", "r": "col_cordoba", "ll": [8.85621, -75.81639], "ey": 1850, "ly": 2018, "p": 4482, "al": ["buenavista del retiro", "Buenavista del Retiro"]},
    {"key": "El Pintor-Peru", "n": "El Pintor", "c": "Peru", "r": "per_amazonas", "ll": [-5.76, -78.5218], "ey": 1525, "ly": 2017, "p": 4482},
    {"key": "Burbusay-Venezuela", "n": "Burbusay", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.41944, -70.26556], "ey": 1538, "ly": 2025, "p": 4480, "al": ["burusai", "burusay", "Burusai"]},
    {"key": "Camaná Inca-Peru", "n": "Camaná Inca", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.623, -72.711], "ey": -3000, "ly": 1530, "p": 4480, "ex": [{"date": "1961.1.1", "name": "Camaná"}], "al": ["bodeguillas", "conjunto arqueologico pacaesitos", "conjunto arqueológico pacaesitos - huacapuy"]},
    {"key": "Santa Cruz-Colombia", "n": "Santa Cruz", "c": "Colombia", "r": "col_atlantico", "ll": [10.57341, -75.21295], "ey": 1850, "ly": 2018, "p": 4479},
    {"key": "Codpa-Chile", "n": "Codpa", "c": "Chile", "r": "chl_region_de_arica_y_parinacota", "ll": [-18.8301, -69.71428], "ey": 1792, "ly": 2017, "p": 4479, "al": ["copta", "Copta"]},
    {"key": "La Clarita-Colombia", "n": "La Clarita", "c": "Colombia", "r": "col_antioquia", "ll": [6.06909, -75.69942], "ey": 1850, "ly": 2018, "p": 4476, "al": ["la ferreira", "La Ferreira"]},
    {"key": "Torre (na_magdalena_cauca_muisca)-Colombia", "n": "Torre", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [7.96976, -75.56247], "ey": 1300, "ly": 1500, "p": 4474},
    {"key": "Macuira-Colombia", "n": "Macuira", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [12.251, -71.467], "ey": 1525, "ly": 1775, "p": 4473, "al": ["macuisa", "Macuisa"]},
    {"key": "Minipi-Colombia", "n": "Minipi", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.142, -74.413], "ey": 1525, "ly": 1830, "p": 4473},
    {"key": "Boca Toma-Argentina", "n": "Boca Toma", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.65531, -63.96212], "ey": 80, "ly": 1500, "p": 4473},
    {"key": "Villa El Salvador - Villa Sefair-Argentina", "n": "Villa El Salvador - Villa Sefair", "c": "Argentina", "r": "arg_san_juan", "ll": [-31.45354, -68.40363], "ey": 1850, "ly": 2010, "p": 4472, "al": ["villa del salvador", "Villa del Salvador"]},
    {"key": "Coro-Bolivia", "n": "Coro", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.354, -67.704], "ey": 1527, "ly": 1825, "p": 4472},
    {"key": "San Pedro (arg_cordoba)-Argentina", "n": "San Pedro", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.75524, -64.62779], "ey": 80, "ly": 2022, "p": 4469, "al": ["san pedro dique los molinos", "San Pedro Dique Los Molinos"]},
    {"key": "Río Verde-Chile_2", "n": "Río Verde", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.65223, -71.46112], "ey": -3000, "ly": 1500, "p": 4467, "al": ["ponsonby", "Ponsonby"]},
    {"key": "Catac-Peru", "n": "Catac", "c": "Peru", "r": "per_ancash", "ll": [-9.80167, -77.43056], "ey": 1850, "ly": 2025, "p": 4463, "al": ["cátac", "Cátac"]},
    {"key": "Puqueldón-Chile", "n": "Puqueldón", "c": "Chile", "r": "chl_region_de_los_lagos", "ll": [-42.63886, -73.64987], "ey": 1525, "ly": 2025, "p": 4463, "al": ["puquelon", "puqueldon", "Puqueldon"]},
    {"key": "Moya-Peru_2", "n": "Moya", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.46177, -76.69442], "ey": -1000, "ly": 1530, "p": 4463, "al": ["cerro belisario", "cerro dos rayas", "cerro san jose"]},
    {"key": "Cuñumbuqui-Peru", "n": "Cuñumbuqui", "c": "Peru", "r": "per_san_martin", "ll": [-6.51056, -76.48167], "ey": 1900, "ly": 2025, "p": 4461},
    {"key": "San Carlos de Austria Yumbel-Chile", "n": "San Carlos de Austria Yumbel", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-37.098, -72.562], "ey": 1603, "ly": 1830, "p": 4460, "ex": [{"date": "1950.1.1", "name": "Yumbel"}]},
    {"key": "Cumanagoto Píritu-Venezuela", "n": "Cumanagoto Píritu", "c": "Venezuela", "r": "na_caribbean_maracaibo_tairona", "ll": [10.048, -65.036], "ey": 800, "ly": 1500, "p": 4460, "al": ["píritu", "Píritu"]},
    {"key": "Pampa de Nerete-Colombia", "n": "Pampa de Nerete", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.73959, -78.68807], "ey": 1000, "ly": 1500, "p": 4458},
    {"key": "Inkawasi-Peru", "n": "Inkawasi", "c": "Peru", "r": "per_ayacucho", "ll": [-13.29, -73.26556], "ey": 1850, "ly": 2025, "p": 4453, "al": ["amaybamba", "Amaybamba"]},
    {"key": "Santa Cruz de Villacuri (villacuri)-Peru", "n": "Santa Cruz de Villacuri (villacuri)", "c": "Peru", "r": "per_ica", "ll": [-13.9298, -75.9223], "ey": 1850, "ly": 2017, "p": 4453, "al": ["santa cruz de villacuri"]},
    {"key": "Punto (na_magdalena_cauca_muisca_2)-Colombia", "n": "Punto", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.18675, -74.52851], "ey": 500, "ly": 1500, "p": 4453, "al": ["mor-ab", "Mor-Ab"]},
    {"key": "Nariño (col_cundinamarca)-Colombia", "n": "Nariño", "c": "Colombia", "r": "col_cundinamarca", "ll": [4.39984, -74.82473], "ey": 1850, "ly": 2025, "p": 4452},
    {"key": "Casbas-Argentina", "n": "Casbas", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-36.75765, -62.50434], "ey": 1850, "ly": 2010, "p": 4450},
    {"key": "El Pinto-Venezuela", "n": "El Pinto", "c": "Venezuela", "r": "ven_monagas", "ll": [9.98444, -63.31667], "ey": 1850, "ly": 2025, "p": 4448},
    {"key": "La Soledad-Venezuela", "n": "La Soledad", "c": "Venezuela", "r": "ven_falcon", "ll": [11.44444, -69.36667], "ey": 1850, "ly": 2025, "p": 4448},
    {"key": "Guimbi-Ecuador", "n": "Guimbi", "c": "Ecuador", "r": "vng_guayaquil_esmeraldas", "ll": [0.957, -78.772], "ey": 1525, "ly": 1830, "p": 4446},
    {"key": "Area IV Qda. Playa Grande-Peru", "n": "Area IV Qda. Playa Grande", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.26608, -78.8281], "ey": -2000, "ly": 1530, "p": 4446, "al": ["area v qda. la rinconada sur", "Area V Qda. La Rinconada Sur"]},
    {"key": "Cerro Suchiman-Peru", "n": "Cerro Suchiman", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.72808, -78.42051], "ey": -1000, "ly": 1530, "p": 4446},
    {"key": "Hernández-Venezuela", "n": "Hernández", "c": "Venezuela", "r": "ven_tachira", "ll": [8.39167, -71.83833], "ey": 1850, "ly": 2025, "p": 4442},
    {"key": "Burruyacú-Argentina", "n": "Burruyacú", "c": "Argentina", "r": "arg_tucuman", "ll": [-26.53055, -64.8196], "ey": 1850, "ly": 2022, "p": 4441},
    {"key": "Pisba-Colombia", "n": "Pisba", "c": "Colombia", "r": "col_boyaca", "ll": [5.72141, -72.48602], "ey": 1525, "ly": 2025, "p": 4440},
    {"key": "Clúster-Colombia", "n": "Clúster", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [3.87884, -73.63734], "ey": 1000, "ly": 1500, "p": 4438},
    {"key": "Aguada de Pablo-Colombia", "n": "Aguada de Pablo", "c": "Colombia", "r": "col_atlantico", "ll": [10.52188, -75.00549], "ey": 1850, "ly": 2018, "p": 4436, "al": ["villa juana", "Villa Juana"]},
    {"key": "Valle de los Dinosaurios-Peru", "n": "Valle de los Dinosaurios", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-5.74953, -78.51062], "ey": 500, "ly": 1530, "p": 4436},
    {"key": "Paico-Chile", "n": "Paico", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.60231, -73.08754], "ey": 1350, "ly": 1500, "p": 4436},
    {"key": "San Buenaventura-Bolivia", "n": "San Buenaventura", "c": "Bolivia", "r": "bol_la_paz", "ll": [-14.42852, -67.54462], "ey": 1850, "ly": 2024, "p": 4435},
    {"key": "Marcella-Colombia", "n": "Marcella", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.86125, -75.69394], "ey": 0, "ly": 1500, "p": 4435},
    {"key": "Quebrada Honda-Peru", "n": "Quebrada Honda", "c": "Peru", "r": "per_arequipa", "ll": [-16.5223, -71.4914], "ey": 1850, "ly": 2017, "p": 4434},
    {"key": "Gibraltar-Venezuela", "n": "Gibraltar", "c": "Venezuela", "r": "ven_zulia", "ll": [9.1905, -71.06969], "ey": 1850, "ly": 2025, "p": 4431},
    {"key": "Villa de Trancas-Argentina", "n": "Villa de Trancas", "c": "Argentina", "r": "arg_tucuman", "ll": [-26.23103, -65.28346], "ey": 1536, "ly": 2010, "p": 4429, "al": ["choromoros", "pozo del pescado", "san joaquin"]},
    {"key": "California-Colombia", "n": "California", "c": "Colombia", "r": "col_santander", "ll": [7.34799, -72.94649], "ey": 1525, "ly": 2025, "p": 4428, "al": ["vetas bajas", "montuosa baja", "real de la baja"]},
    {"key": "Calquis-Peru", "n": "Calquis", "c": "Peru", "r": "per_cajamarca", "ll": [-6.98028, -78.85], "ey": 1850, "ly": 2025, "p": 4426},
    {"key": "Santa Ana-Peru_2", "n": "Santa Ana", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.43912, -72.17488], "ey": 1300, "ly": 1530, "p": 4425, "al": ["gross munsa - cancha del inca", "higueritas", "las higueritas"]},
    {"key": "Plaza del Mundo-Colombia", "n": "Plaza del Mundo", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.80128, -75.81081], "ey": 1300, "ly": 1500, "p": 4425},
    {"key": "Kilo.coq-Chile", "n": "Kilo.coq", "c": "Chile", "r": "inca_collasuyu", "ll": [-29.60765, -70.93735], "ey": 500, "ly": 1530, "p": 4424},
    {"key": "Jibito-Peru", "n": "Jibito", "c": "Peru", "r": "per_piura", "ll": [-4.9043, -80.7467], "ey": 1850, "ly": 2017, "p": 4423},
    {"key": "Colonia Liebig-Argentina", "n": "Colonia Liebig", "c": "Argentina", "r": "arg_misiones", "ll": [-27.91334, -55.82424], "ey": 1900, "ly": 2022, "p": 4423, "al": ["colonia liebig's", "estación apóstoles", "Colonia Liebig's"]},
    {"key": "Villa San Agustín-Argentina", "n": "Villa San Agustín", "c": "Argentina", "r": "arg_san_juan", "ll": [-30.63453, -67.46789], "ey": 1779, "ly": 2010, "p": 4423, "al": ["villa san agustin", "san agustin del valle fertil", "San Agustin del Valle Fertil"]},
    {"key": "Mindo-Ecuador", "n": "Mindo", "c": "Ecuador", "r": "ecu_pichincha", "ll": [-0.05161, -78.73658], "ey": 1525, "ly": 2025, "p": 4421},
]

def api_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_one(s):
    lat, lng = s["ll"]
    name = s["n"]
    country = s["c"]
    region = s["r"]
    res = {"key": s["key"], "n": name, "c": country, "r": region, "ll": s["ll"], "ey": s["ey"], "ly": s["ly"]}
    pages = {}

    # 1. eswiki geosearch
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        d = api_get(u)
        res["es_geo"] = d.get("query", {}).get("geosearch", [])
        for g in res["es_geo"][:2]:
            pages[("es", g["title"])] = True
    except Exception as e:
        res["es_geo_err"] = str(e)

    # 2. eswiki search by name + country/region hint
    reg_hint = region.split("_", 1)[-1].replace("_", " ")
    q = f"{name} {country}"
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=3&format=json"
        d = api_get(u)
        res["es_search"] = [x["title"] for x in d.get("query", {}).get("search", [])]
        for t in res["es_search"][:2]:
            pages[("es", t)] = True
    except Exception as e:
        res["es_search_err"] = str(e)

    # 3. Also search with region hint if region looks modern
    if any(region.startswith(p) for p in ("per_", "col_", "arg_", "chl_", "ecu_", "ven_", "bol_")):
        q2 = f"{name} {reg_hint}"
        try:
            u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q2)}&srlimit=2&format=json"
            d = api_get(u)
            for x in d.get("query", {}).get("search", []):
                pages[("es", x["title"])] = True
        except Exception:
            pass

    # 4. Fetch extracts for candidate pages
    extracts = {}
    for lang, title in list(pages.keys())[:4]:
        try:
            u = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=1&exchars=3500&titles={urllib.parse.quote(title)}&format=json"
            d = api_get(u)
            for pid, pinfo in d.get("query", {}).get("pages", {}).items():
                if "extract" in pinfo:
                    extracts[f"{lang}:{title}"] = {
                        "coords": pinfo.get("coordinates"),
                        "extract": pinfo["extract"],
                    }
        except Exception as e:
            extracts[f"{lang}:{title}"] = {"err": str(e)}
    res["extracts"] = extracts
    return res

results = []
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(fetch_one, s): s["key"] for s in SETTLEMENTS}
    for fut in as_completed(futs):
        results.append(fut.result())

order = {s["key"]: i for i, s in enumerate(SETTLEMENTS)}
results.sort(key=lambda x: order[x["key"]])

with open("tests/chunk037_research.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Fetched {len(results)} settlements.")
