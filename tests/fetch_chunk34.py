import json
import time
import urllib.parse
import urllib.request

HEADERS = {
    "User-Agent": "SVEA-Project/1.0 (https://confoederatio.org; mailto:info@confoederatio.org)"
}

INPUT_DATA = [
    {"key": "Manchan-Peru", "n": "Manchan", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.51969, -78.27706], "ey": 1200, "ly": 1532, "p": 4860, "ex": [{"date": "1961.1.1", "name": "Casma"}], "al": ["arqueológico huarin", "cantina", "carrizal"]},
    {"key": "Bolo-Colombia", "n": "Bolo", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [3.46708, -76.33052], "ey": -200, "ly": 1500, "p": 4860, "ex": [{"date": "1793.1.1", "name": "Cali"}], "al": ["malagana", "calima-malagana", "yotoco"]},
    {"key": "Huentota Huarpe-Argentina", "n": "Huentota Huarpe", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-32.89, -68.845], "ey": 400, "ly": 1450, "p": 4860, "al": ["agua de la cueva", "agua de la tinaja", "arroyo malo"]},
    {"key": "La Peña (col_atlantico)-Colombia", "n": "La Peña", "c": "Colombia", "r": "col_atlantico", "ll": [10.58497, -75.02443], "ey": 1850, "ly": 2018, "p": 4859},
    {"key": "Lacramarca-Peru", "n": "Lacramarca", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-8.892, -78.269], "ey": 1525, "ly": 1825, "p": 4859},
    {"key": "Llacuabamba-Peru", "n": "Llacuabamba", "c": "Peru", "r": "per_la_libertad", "ll": [-8.0353, -77.4569], "ey": 1850, "ly": 2017, "p": 4857, "al": ["miraflores", "Miraflores"]},
    {"key": "Río Tambo-Peru_2", "n": "Río Tambo", "c": "Peru", "r": "inca_contisuyu", "ll": [-17.16761, -71.79405], "ey": -2000, "ly": 1532, "p": 4857, "al": ["el pino", "la curva", "El Pino"]},
    {"key": "El Limonar-Colombia", "n": "El Limonar", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.6094, -76.71028], "ey": 1525, "ly": 2018, "p": 4856, "al": ["limonar", "Limonar"]},
    {"key": "San Roque (ecu_sucumbios)-Ecuador", "n": "San Roque", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [-0.30414, -76.53672], "ey": 1920, "ly": 2025, "p": 4855},
    {"key": "Súa-Ecuador", "n": "Súa", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.76743, -79.89482], "ey": 1850, "ly": 2025, "p": 4855},
    {"key": "Aporoma-Peru", "n": "Aporoma", "c": "Peru", "r": "vp_intendencia_puno", "ll": [-14.017, -69.467], "ey": 1525, "ly": 1825, "p": 4855},
    {"key": "La Herradura K19-Colombia", "n": "La Herradura K19", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [7.0887, -73.71058], "ey": 1300, "ly": 1500, "p": 4850, "al": ["colibrí", "Colibrí"]},
    {"key": "San Isidro De Patulú-Ecuador", "n": "San Isidro De Patulú", "c": "Ecuador", "r": "ecu_tungurahua", "ll": [-1.54786, -78.67544], "ey": 1850, "ly": 2025, "p": 4849},
    {"key": "Bajo Calima-Colombia", "n": "Bajo Calima", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.99836, -76.97519], "ey": 1525, "ly": 2018, "p": 4846, "al": ["calima", "Calima"]},
    {"key": "San Jaime de la Frontera-Argentina", "n": "San Jaime de la Frontera", "c": "Argentina", "r": "arg_entre_rios", "ll": [-30.34027, -58.30707], "ey": 1850, "ly": 2022, "p": 4841},
    {"key": "Santa Cruz (per_ancash)-Peru", "n": "Santa Cruz", "c": "Peru", "r": "per_ancash", "ll": [-8.95194, -77.815], "ey": 1850, "ly": 2025, "p": 4840, "al": ["huaripampa", "Huaripampa"]},
    {"key": "Catriló-Argentina", "n": "Catriló", "c": "Argentina", "r": "arg_la_pampa", "ll": [-36.4067, -63.42325], "ey": 1900, "ly": 2022, "p": 4840},
    {"key": "América-Ecuador", "n": "América", "c": "Ecuador", "r": "ecu_manabi", "ll": [-1.43223, -80.52361], "ey": 1850, "ly": 2025, "p": 4839},
    {"key": "Concepcion El Sombrero-Venezuela", "n": "Concepcion El Sombrero", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [9.39, -67.062], "ey": 1729, "ly": 1830, "p": 4838},
    {"key": "Los Yaganes-Chile", "n": "Los Yaganes", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.6606, -69.48716], "ey": 1000, "ly": 1500, "p": 4836},
    {"key": "Yanabaya-Bolivia", "n": "Yanabaya", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-15.291, -68.803], "ey": 1525, "ly": 1825, "p": 4835},
    {"key": "HF-Ceramica-Liticos-Guaduales_Vda_El Limonal_Mcpio Suarez_Tolima-Colombia", "n": "HF-Ceramica-Liticos-Guaduales_Vda_El Limonal_Mcpio Suarez_Tolima", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.06764, -74.82238], "ey": 1300, "ly": 1500, "p": 4835},
    {"key": "Masparrito-Venezuela", "n": "Masparrito", "c": "Venezuela", "r": "ven_trujillo", "ll": [8.97167, -70.29167], "ey": 1850, "ly": 2025, "p": 4834},
    {"key": "Poco Poco-Bolivia", "n": "Poco Poco", "c": "Bolivia", "r": "bol_chuquisaca", "ll": [-19.37295, -65.0136], "ey": 1525, "ly": 2024, "p": 4831, "al": ["pocopoco"]},
    {"key": "Floresta-Colombia", "n": "Floresta", "c": "Colombia", "r": "col_boyaca", "ll": [5.85952, -72.91811], "ey": 1850, "ly": 2025, "p": 4829},
    {"key": "Hucan-Peru", "n": "Hucan", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-15.14, -71.823], "ey": 1525, "ly": 1825, "p": 4829},
    {"key": "Nariño (col_narino)-Colombia", "n": "Nariño", "c": "Colombia", "r": "col_narino", "ll": [1.28898, -77.35797], "ey": 1850, "ly": 2025, "p": 4828},
    {"key": "Monterrey-Chile", "n": "Monterrey", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-29.848, -71.253], "ey": 1525, "ly": 1830, "p": 4828, "al": ["la recoleta", "loma alta", "monte rey"]},
    {"key": "Caldas (col_boyaca)-Colombia", "n": "Caldas", "c": "Colombia", "r": "col_boyaca", "ll": [5.55458, -73.86555], "ey": 1850, "ly": 2025, "p": 4826},
    {"key": "Canayre-Peru", "n": "Canayre", "c": "Peru", "r": "per_junin", "ll": [-12.28222, -74.02306], "ey": 1850, "ly": 2025, "p": 4825},
    {"key": "San Cayetano (col_bolivar)-Colombia", "n": "San Cayetano", "c": "Colombia", "r": "col_bolivar", "ll": [10.08261, -75.14083], "ey": 1776, "ly": 2018, "p": 4824},
    {"key": "Casabindo-Argentina", "n": "Casabindo", "c": "Argentina", "r": "arg_jujuy", "ll": [-22.98679, -66.03293], "ey": 1525, "ly": 2022, "p": 4823, "al": ["casavindo", "casivindo", "Casavindo"]},
    {"key": "Rumipal-Argentina", "n": "Rumipal", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.19563, -64.48097], "ey": 80, "ly": 1500, "p": 4823},
    {"key": "Ayacucho (ven_trujillo)-Venezuela", "n": "Ayacucho", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.33944, -70.14056], "ey": 1850, "ly": 2025, "p": 4821},
    {"key": "Caspi-Peru", "n": "Caspi", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-14.385, -73.009], "ey": 1525, "ly": 1825, "p": 4821},
    {"key": "Pacto-Ecuador", "n": "Pacto", "c": "Ecuador", "r": "ecu_pichincha", "ll": [0.14867, -78.84577], "ey": 1850, "ly": 2025, "p": 4820},
    {"key": "Loreto Viejo-Peru", "n": "Loreto Viejo", "c": "Peru", "r": "inca_contisuyu", "ll": [-17.17253, -70.95086], "ey": 500, "ly": 1532, "p": 4819, "ex": [{"date": "1896.1.1", "name": "Moquegua"}], "al": ["alto calaluna", "cerro echenique m-2 y m", "cerro echenique m2 y m"]},
    {"key": "La Granja-Argentina", "n": "La Granja", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.00861, -64.26789], "ey": 1850, "ly": 2022, "p": 4818},
    {"key": "Boro Hue-Argentina", "n": "Boro Hue", "c": "Argentina", "r": "sc_pampas_salado_colorado", "ll": [-34.7913, -64.851], "ey": 80, "ly": 1500, "p": 4816},
    {"key": "Panduro-Bolivia", "n": "Panduro", "c": "Bolivia", "r": "bol_la_paz", "ll": [-17.49402, -67.44391], "ey": 1525, "ly": 2024, "p": 4815},
    {"key": "Cerro Santa María-Peru", "n": "Cerro Santa María", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.92991, -76.92481], "ey": -1000, "ly": 1530, "p": 4815, "al": ["adoratorio", "adoratorio jicamarca", "brazo babilonia sur"]},
    {"key": "Ciat-Colombia", "n": "Ciat", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [3.5, -76.38], "ey": -562, "ly": 1500, "p": 4815},
    {"key": "Ucuchacas-Peru", "n": "Ucuchacas", "c": "Peru", "r": "vp_intendencia_arequipa", "ll": [-15.539, -72.089], "ey": 1525, "ly": 1825, "p": 4813},
    {"key": "Sierra Chica-Argentina", "n": "Sierra Chica", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-37.12897, -60.40993], "ey": 1850, "ly": 2010, "p": 4812},
    {"key": "Santa Helena Del Opón-Colombia", "n": "Santa Helena Del Opón", "c": "Colombia", "r": "col_santander", "ll": [6.33957, -73.61672], "ey": 1850, "ly": 2025, "p": 4811},
    {"key": "Pukara Central de Laca Laca-Peru", "n": "Pukara Central de Laca Laca", "c": "Peru", "r": "inca_collasuyu", "ll": [-16.47287, -69.44514], "ey": 1438, "ly": 1530, "p": 4811, "al": ["wañaveq´o pukara", "Wañaveq´o Pukara"]},
    {"key": "Arroyo Leyes-Argentina", "n": "Arroyo Leyes", "c": "Argentina", "r": "arg_santa_fe", "ll": [-31.55906, -60.51763], "ey": 1850, "ly": 2022, "p": 4810},
    {"key": "Guacarhue-Chile", "n": "Guacarhue", "c": "Chile", "r": "chl_region_del_libertador_bernardo_o_higgins", "ll": [-34.35534, -71.0205], "ey": 1525, "ly": 2017, "p": 4807, "al": ["huacarhue", "Huacarhue"]},
    {"key": "Las Grutas-Argentina", "n": "Las Grutas", "c": "Argentina", "r": "arg_rio_negro", "ll": [-40.80609, -65.0847], "ey": 1920, "ly": 2010, "p": 4807},
    {"key": "Cajamarquilla de Gorgor-Peru", "n": "Cajamarquilla de Gorgor", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.59, -77.072], "ey": 1525, "ly": 1825, "p": 4806},
    {"key": "Hughes-Argentina", "n": "Hughes", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.80112, -61.33609], "ey": 1850, "ly": 2022, "p": 4805},
    {"key": "Guangopolo-Ecuador", "n": "Guangopolo", "c": "Ecuador", "r": "ecu_pichincha", "ll": [-0.25045, -78.437], "ey": 1850, "ly": 2025, "p": 4799},
    {"key": "Sa-Pbe-Colombia", "n": "Sa-Pbe", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.92931, -74.57141], "ey": 500, "ly": 1500, "p": 4799},
    {"key": "Calamarí-Colombia", "n": "Calamarí", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.423, -75.548], "ey": 800, "ly": 1500, "p": 4790, "ex": [{"date": "1968.1.1", "name": "Turbaco"}], "al": ["claustro de san francisco", "palacio de la inquisición", "teatro colón"]},
    {"key": "San Juan (per_cajamarca)-Peru", "n": "San Juan", "c": "Peru", "r": "per_cajamarca", "ll": [-7.29167, -78.4975], "ey": 1850, "ly": 2025, "p": 4789},
    {"key": "Yagen-Peru", "n": "Yagen", "c": "Peru", "r": "per_cajamarca", "ll": [-6.5106, -78.2575], "ey": 1525, "ly": 2017, "p": 4789},
    {"key": "Guecabelet-Colombia", "n": "Guecabelet", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [0.963, -77.836], "ey": 1525, "ly": 1830, "p": 4789, "al": ["paranma", "Paranma"]},
    {"key": "Moray-Peru", "n": "Moray", "c": "Peru", "r": "inca_cuzco_heartland", "ll": [-13.329, -72.196], "ey": 0, "ly": 1530, "p": 4787, "al": ["ch'eqoq", "kimsaera", "pulpituyoq"]},
    {"key": "Fundo Lo Videla-Chile", "n": "Fundo Lo Videla", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.87362, -72.65196], "ey": -300, "ly": 1500, "p": 4787, "al": ["fundo folilco", "Fundo Folilco"]},
    {"key": "Huaca Pucllana-Peru", "n": "Huaca Pucllana", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.11186, -77.03422], "ey": 1438, "ly": 1530, "p": 4786, "al": ["felicia gomez", "huaca la merced", "huaca san borja"]},
    {"key": "Mayasquer-Ecuador", "n": "Mayasquer", "c": "Ecuador", "r": "vng_antioquia_popayan_choco", "ll": [0.884, -78.036], "ey": 1525, "ly": 1830, "p": 4785},
    {"key": "Talora AIE-Colombia", "n": "Talora AIE", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.46832, -74.80016], "ey": 1000, "ly": 1500, "p": 4785},
    {"key": "San Luis (col_archipielago_de_san_andres_providencia_y_santa_catalina)-Colombia", "n": "San Luis", "c": "Colombia", "r": "col_archipielago_de_san_andres_providencia_y_santa_catalina", "ll": [12.52709, -81.71331], "ey": 1850, "ly": 2018, "p": 4782},
    {"key": "Ballesteros-Argentina", "n": "Ballesteros", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.54168, -62.98078], "ey": 1850, "ly": 2022, "p": 4782},
    {"key": "Iruya-Argentina", "n": "Iruya", "c": "Argentina", "r": "arg_jujuy", "ll": [-22.79274, -65.21908], "ey": 1536, "ly": 2022, "p": 4782},
    {"key": "San Felipe-Ecuador", "n": "San Felipe", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-0.932, -78.63], "ey": 1525, "ly": 1830, "p": 4782},
    {"key": "Churajon-Peru", "n": "Churajon", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.67275, -71.30602], "ey": 1000, "ly": 1530, "p": 4780, "al": ["churajón", "cerro chasca lloque b", "cerro chascalloque a"]},
    {"key": "Samaipata-Bolivia", "n": "Samaipata", "c": "Bolivia", "r": "inca_antisuyu", "ll": [-18.178, -63.82], "ey": 1480, "ly": 1530, "p": 4780, "al": ["el fuerte de samaipata", "El Fuerte de Samaipata"]},
    {"key": "Mult-Colombia", "n": "Mult", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [5.12654, -72.18904], "ey": 1000, "ly": 1500, "p": 4780},
    {"key": "Casa del Minero-Argentina", "n": "Casa del Minero", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-48.576, -68.9125], "ey": -10000, "ly": -8818, "p": 4780},
    {"key": "30 de Agosto-Argentina", "n": "30 de Agosto", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-36.27859, -62.54509], "ey": 1850, "ly": 2010, "p": 4777},
    {"key": "Huerta del Maule-Chile", "n": "Huerta del Maule", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-35.663, -71.946], "ey": 1754, "ly": 1830, "p": 4777, "al": ["huerta de maule", "san francisco de la huerta", "Huerta de Maule"]},
    {"key": "Carhuapampa (vp_intendencia_lima)-Peru", "n": "Carhuapampa", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.039, -76.12], "ey": 1525, "ly": 1825, "p": 4777},
    {"key": "Chiquinquira (ven_lara)-Venezuela", "n": "Chiquinquira", "c": "Venezuela", "r": "ven_lara", "ll": [10.24444, -70.02778], "ey": 1538, "ly": 2025, "p": 4771, "al": ["aregue", "Aregue"]},
    {"key": "Yacimiento El Mono San Onofre-Colombia", "n": "Yacimiento El Mono San Onofre", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [9.73716, -75.50503], "ey": 1300, "ly": 1500, "p": 4771, "ex": [{"date": "1968.1.1", "name": "San Onofre"}]},
    {"key": "Cruz Pampa-Yapatera-Peru", "n": "Cruz Pampa-Yapatera", "c": "Peru", "r": "per_piura", "ll": [-5.0576, -80.1355], "ey": 1525, "ly": 2017, "p": 4767, "al": ["yapatera", "Yapatera"]},
    {"key": "Arroyo Grande-Colombia", "n": "Arroyo Grande", "c": "Colombia", "r": "col_bolivar", "ll": [10.65629, -75.34769], "ey": 1793, "ly": 2018, "p": 4766, "al": ["arroyo de piedra", "Arroyo de Piedra"]},
    {"key": "Elías-Colombia", "n": "Elías", "c": "Colombia", "r": "col_huila", "ll": [2.01285, -75.9383], "ey": 1850, "ly": 2025, "p": 4766},
    {"key": "El Carmen-Colombia_2", "n": "El Carmen", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [3.79, -76.34], "ey": 478, "ly": 1500, "p": 4765, "al": ["la alsacia", "La Alsacia"]},
    {"key": "La Iberia-Ecuador", "n": "La Iberia", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.24265, -79.87809], "ey": 1850, "ly": 2025, "p": 4763},
    {"key": "V-Cai-EAl-1 Los Quingos-Colombia", "n": "V-Cai-EAl-1 Los Quingos", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.40976, -75.86648], "ey": 1300, "ly": 1500, "p": 4762},
    {"key": "Altamira-Colombia", "n": "Altamira", "c": "Colombia", "r": "col_huila", "ll": [2.06384, -75.78847], "ey": 1525, "ly": 2025, "p": 4760, "al": ["boqueron", "Boqueron"]},
    {"key": "Viluco-Chile", "n": "Viluco", "c": "Chile", "r": "chl_region_metropolitana_de_santiago", "ll": [-33.79347, -70.78009], "ey": 1850, "ly": 2017, "p": 4760},
    {"key": "Salgar (col_atlantico)-Colombia", "n": "Salgar", "c": "Colombia", "r": "col_atlantico", "ll": [11.01732, -74.92373], "ey": 1850, "ly": 2018, "p": 4759},
    {"key": "Tuñame-Venezuela", "n": "Tuñame", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.06389, -70.60389], "ey": 1850, "ly": 2025, "p": 4758},
    {"key": "Villa Paranacito-Argentina", "n": "Villa Paranacito", "c": "Argentina", "r": "arg_entre_rios", "ll": [-33.71468, -58.65859], "ey": 1850, "ly": 2022, "p": 4758},
    {"key": "Zenta de Vejoses-Argentina", "n": "Zenta de Vejoses", "c": "Argentina", "r": "crp_gran_chaco_frontier", "ll": [-23.294, -64.161], "ey": 1799, "ly": 1830, "p": 4756},
    {"key": "Cusipata-Peru", "n": "Cusipata", "c": "Peru", "r": "per_cusco", "ll": [-13.90694, -71.5025], "ey": 1850, "ly": 2025, "p": 4755},
    {"key": "Santa Ana (per_huancavelica)-Peru", "n": "Santa Ana", "c": "Peru", "r": "per_huancavelica", "ll": [-13.07194, -75.14028], "ey": 1525, "ly": 2025, "p": 4753},
    {"key": "Cajón de Piedra-Argentina", "n": "Cajón de Piedra", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.70009, -64.0816], "ey": 80, "ly": 1500, "p": 4750}
]

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

results = {}
for idx, item in enumerate(INPUT_DATA):
    key = item["key"]
    lat, lng = item["ll"]
    entry = {"name": item["n"], "c": item["c"], "r": item["r"], "ll": item["ll"], "ey": item["ey"], "ly": item["ly"]}
    # eswiki geosearch
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=8000&gslimit=5&format=json"
        data = fetch_json(u)
        entry["es_geo"] = [{"title": g["title"], "dist": round(g["dist"]), "pageid": g["pageid"]} for g in data.get("query", {}).get("geosearch", [])]
    except Exception as e:
        entry["es_geo_err"] = str(e)
    time.sleep(0.05)

    # enwiki geosearch
    try:
        u = f"https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=8000&gslimit=5&format=json"
        data = fetch_json(u)
        entry["en_geo"] = [{"title": g["title"], "dist": round(g["dist"]), "pageid": g["pageid"]} for g in data.get("query", {}).get("geosearch", [])]
    except Exception as e:
        entry["en_geo_err"] = str(e)
    time.sleep(0.05)

    # If neither had hits, do es.wiki text search
    if not entry.get("es_geo") and not entry.get("en_geo"):
        try:
            q = urllib.parse.quote(f"{item['n']} {item['c']}")
            u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
            data = fetch_json(u)
            entry["es_search"] = [{"title": s["title"], "pageid": s["pageid"]} for s in data.get("query", {}).get("search", [])]
        except Exception as e:
            entry["es_search_err"] = str(e)
        time.sleep(0.05)

    results[key] = entry
    if (idx + 1) % 15 == 0:
        print(f"Processed {idx+1}/90")

with open("tests/wiki_geo.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Done!")
