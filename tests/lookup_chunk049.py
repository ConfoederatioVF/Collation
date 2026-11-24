import json
import urllib.request
import urllib.parse
import concurrent.futures

SETTLEMENTS = [
  {"key": "Paris Pukara-Peru", "n": "Paris Pukara", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.88285, -71.59254], "ey": 1438, "ly": 1530, "p": 3469},
  {"key": "Fortín Carilafquén-Chile", "n": "Fortín Carilafquén", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.07122, -72.49971], "ey": 1282, "ly": 1500, "p": 3468},
  {"key": "Gachiná-Colombia", "n": "Gachiná", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.98356, -73.87478], "ey": 1000, "ly": 1500, "p": 3466},
  {"key": "Areo-Venezuela", "n": "Areo", "c": "Venezuela", "r": "ven_monagas", "ll": [9.75, -63.79444], "ey": 1760, "ly": 2025, "p": 3465, "al": ["san jose de ario", "San Jose de Ario"]},
  {"key": "Esquena-Peru", "n": "Esquena", "c": "Peru", "r": "per_puno", "ll": [-13.9418, -69.928], "ey": 1525, "ly": 2017, "p": 3465},
  {"key": "Abrigo Rafael Mache-Peru", "n": "Abrigo Rafael Mache", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.20951, -76.91602], "ey": -1000, "ly": 1530, "p": 3465, "al": ["cueva numero machay", "ruco castillo", "uscumachay"]},
  {"key": "Serrano-Argentina", "n": "Serrano", "c": "Argentina", "r": "arg_cordoba", "ll": [-34.47077, -63.54017], "ey": 1850, "ly": 2022, "p": 3464},
  {"key": "Barreal - Villa Pituil-Argentina", "n": "Barreal - Villa Pituil", "c": "Argentina", "r": "arg_san_juan", "ll": [-31.64934, -69.47636], "ey": 1850, "ly": 2010, "p": 3463},
  {"key": "Cueva Lago Sofia-Argentina", "n": "Cueva Lago Sofia", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-51.533, -71.5333], "ey": -10000, "ly": -5931, "p": 3462, "al": ["lago sofia", "Lago Sofia"]},
  {"key": "Antiguala-Chile", "n": "Antiguala", "c": "Chile", "r": "chl_region_del_bio_bio", "ll": [-37.66167, -73.39201], "ey": 1850, "ly": 2017, "p": 3461},
  {"key": "Punchao Chico-Peru", "n": "Punchao Chico", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.90709, -76.38872], "ey": -2000, "ly": 1532, "p": 3461, "al": ["chonta", "pirush punta", "wuiro wuiro"]},
  {"key": "Miraflores-Peru", "n": "Miraflores", "c": "Peru", "r": "per_huanuco", "ll": [-9.49389, -76.81861], "ey": 1950, "ly": 2025, "p": 3460, "al": ["pampas de flores", "Pampas de Flores"]},
  {"key": "Villa Santa Rosa (arg_san_juan)-Argentina", "n": "Villa Santa Rosa", "c": "Argentina", "r": "arg_san_juan", "ll": [-31.74481, -68.31424], "ey": 1850, "ly": 2010, "p": 3460},
  {"key": "Alto Molino-Peru", "n": "Alto Molino", "c": "Peru", "r": "inca_contisuyu", "ll": [-15.76665, -73.37637], "ey": -2000, "ly": 1530, "p": 3458, "al": ["abrigos de sondor", "alto molino hospital", "cerro chuicanito"]},
  {"key": "Arteaga-Argentina", "n": "Arteaga", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.09269, -61.79203], "ey": 1850, "ly": 2022, "p": 3457},
  {"key": "Mincha-Chile", "n": "Mincha", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-31.588, -71.445], "ey": 1692, "ly": 1830, "p": 3457},
  {"key": "Portillo-Bolivia", "n": "Portillo", "c": "Bolivia", "r": "bol_tarija", "ll": [-21.56146, -64.66518], "ey": 1850, "ly": 2024, "p": 3455},
  {"key": "Anchayacu-Ecuador", "n": "Anchayacu", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.9566, -79.09716], "ey": 1850, "ly": 2025, "p": 3453},
  {"key": "El Cerrito I-Venezuela", "n": "El Cerrito I", "c": "Venezuela", "r": "ven_falcon", "ll": [11.77167, -69.94056], "ey": 1538, "ly": 2011, "p": 3452, "al": ["el cerrito", "santa ana norte", "santa ana paraguana"]},
  {"key": "Antavilque-Peru", "n": "Antavilque", "c": "Peru", "r": "vp_intendencia_puno", "ll": [-14.868, -70.451], "ey": 1525, "ly": 1825, "p": 3452},
  {"key": "Villa Alfredo Fortabat-Argentina", "n": "Villa Alfredo Fortabat", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-36.92983, -60.16586], "ey": 1850, "ly": 2010, "p": 3451},
  {"key": "San Juan Bautista de Hualqui-Chile", "n": "San Juan Bautista de Hualqui", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-36.976, -72.939], "ey": 1757, "ly": 1830, "p": 3451, "ex": [{"date": "1950.1.1", "name": "Hualqui"}]},
  {"key": "Arenal Puerto Fiel-Peru", "n": "Arenal Puerto Fiel", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.86649, -76.50817], "ey": -2000, "ly": 1530, "p": 3450, "al": ["chepeconde", "evidencia arqueológica", "evidencias arqueológicas"]},
  {"key": "Hersilia-Argentina", "n": "Hersilia", "c": "Argentina", "r": "arg_santa_fe", "ll": [-30.0039, -61.8391], "ey": 1850, "ly": 2022, "p": 3449},
  {"key": "San Mateo Orituco-Venezuela", "n": "San Mateo Orituco", "c": "Venezuela", "r": "vng_cumana_guayana_margarita", "ll": [9.741, -64.55], "ey": 1715, "ly": 1830, "p": 3449, "al": ["prepuntar", "prepuntare", "Prepuntar"]},
  {"key": "Sepulturas-Bolivia", "n": "Sepulturas", "c": "Bolivia", "r": "bol_oruro", "ll": [-17.97813, -67.01364], "ey": 1525, "ly": 2024, "p": 3448, "al": ["sepolturas", "Sepolturas"]},
  {"key": "Buta Ranquil-Argentina", "n": "Buta Ranquil", "c": "Argentina", "r": "arg_neuquen", "ll": [-37.05168, -69.8779], "ey": 1900, "ly": 2022, "p": 3448},
  {"key": "El Milagro D-Peru", "n": "El Milagro D", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.7969, -79.38164], "ey": -3000, "ly": 1530, "p": 3443, "al": ["arqueológico huaca redonda", "arqueológico manco capac g", "el milagro b"]},
  {"key": "En Proceso (inca_chinchaysuyu_9)-Peru", "n": "En Proceso", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.20749, -75.24806], "ey": 500, "ly": 1532, "p": 3442, "al": ["coto coto", "Coto Coto"]},
  {"key": "Máximo Paz-Argentina", "n": "Máximo Paz", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.48311, -60.9561], "ey": 1850, "ly": 2010, "p": 3441},
  {"key": "Abrigos del Peral-Peru", "n": "Abrigos del Peral", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.32797, -71.51941], "ey": 0, "ly": 1530, "p": 3441, "al": ["andenerías del", "andenes y terrazas del valle del río chil", "chilina"]},
  {"key": "Corralones-Peru", "n": "Corralones", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.58548, -77.23865], "ey": -1000, "ly": 1530, "p": 3439, "al": ["ushnu colorado", "Ushnu Colorado"]},
  {"key": "Atuncela-Colombia", "n": "Atuncela", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [3.74, -76.67], "ey": 1282, "ly": 1500, "p": 3439, "al": ["planta dagua", "Planta Dagua"]},
  {"key": "Chavarría-Argentina", "n": "Chavarría", "c": "Argentina", "r": "arg_corrientes", "ll": [-28.95526, -58.57177], "ey": 1850, "ly": 2022, "p": 3438},
  {"key": "La Isla-Peru", "n": "La Isla", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.45891, -75.18767], "ey": 1438, "ly": 1530, "p": 3437, "al": ["laran", "larán", "Laran"]},
  {"key": "Pailapifil-Chile", "n": "Pailapifil", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.65284, -73.14434], "ey": 1350, "ly": 1500, "p": 3437},
  {"key": "El Gallo-Colombia", "n": "El Gallo", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [7.88, -76.29], "ey": 438, "ly": 1500, "p": 3436, "al": ["el gallo ii. sitio", "El Gallo II. Sitio"]},
  {"key": "Yarumito-Colombia", "n": "Yarumito", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.13, -77.107], "ey": 1525, "ly": 1830, "p": 3435},
  {"key": "Cerrillos Negros-Peru", "n": "Cerrillos Negros", "c": "Peru", "r": "inca_collasuyu", "ll": [-17.85948, -70.43226], "ey": 1000, "ly": 1532, "p": 3435, "al": ["marcador cerillos negros", "Marcador Cerillos Negros"]},
  {"key": "Begonia-Colombia", "n": "Begonia", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [2.07, -76.19], "ey": 196, "ly": 1500, "p": 3434, "al": ["morelia", "santa elena", "Morelia"]},
  {"key": "Campo Albano-Argentina", "n": "Campo Albano", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.59939, -63.72405], "ey": 450, "ly": 1500, "p": 3433, "al": ["potrero campo picatto", "Potrero Campo Picatto"]},
  {"key": "La Victoria (ecu_el_oro)-Ecuador", "n": "La Victoria", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.78238, -80.115], "ey": 1850, "ly": 2025, "p": 3432},
  {"key": "Bautismo-Chile", "n": "Bautismo", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.44945, -70.60667], "ey": -3000, "ly": 1500, "p": 3431},
  {"key": "Hilario Ascasubi-Argentina", "n": "Hilario Ascasubi", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-39.37562, -62.64743], "ey": 1850, "ly": 2010, "p": 3427},
  {"key": "San Juan Ojiba-Ecuador", "n": "San Juan Ojiba", "c": "Ecuador", "r": "vng_guayaquil_esmeraldas", "ll": [-1.571, -79.467], "ey": 1525, "ly": 1830, "p": 3425, "al": ["ujiva", "Ujiva"]},
  {"key": "Santiago-Bolivia_2", "n": "Santiago", "c": "Bolivia", "r": "vp_intendencia_puno", "ll": [-16.055, -68.818], "ey": 1541, "ly": 1825, "p": 3425},
  {"key": "Río Blanco-Ecuador", "n": "Río Blanco", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-2.34425, -78.36068], "ey": 1920, "ly": 2025, "p": 3424},
  {"key": "Laguna El Peral-Chile", "n": "Laguna El Peral", "c": "Chile", "r": "inca_collasuyu", "ll": [-33.50488, -71.60662], "ey": 1000, "ly": 1530, "p": 3424, "al": ["dunas de la chépica-gota de leche", "Dunas de la Chépica-Gota de Leche"]},
  {"key": "Vereda Guacana-Colombia", "n": "Vereda Guacana", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.47367, -74.61629], "ey": 500, "ly": 1500, "p": 3424, "al": ["barrio santa lucía", "Barrio Santa Lucía"]},
  {"key": "Esmeralda-Chile", "n": "Esmeralda", "c": "Chile", "r": "chl_region_del_libertador_bernardo_o_higgins", "ll": [-34.33201, -70.89287], "ey": 1850, "ly": 2017, "p": 3421, "al": ["esmeralda norte", "Esmeralda Norte"]},
  {"key": "Collacruz-Peru", "n": "Collacruz", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.30944, -77.90377], "ey": 900, "ly": 1532, "p": 3420, "al": ["arqueológico condechaca", "arqueológico pasabreve", "arqueológico yanamachay"]},
  {"key": "Casanare Achagua-Colombia", "n": "Casanare Achagua", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [5.337, -72.396], "ey": 800, "ly": 1500, "p": 3420, "ex": [{"date": "1968.1.1", "name": "Yopal"}], "al": ["yopal prehispanic", "Yopal Prehispanic"]},
  {"key": "Khonkho Wankane-Bolivia", "n": "Khonkho Wankane", "c": "Bolivia", "r": "ca_titicaca_altiplano_tiwanaku", "ll": [-16.759, -68.67], "ey": -200, "ly": 800, "p": 3420},
  {"key": "El Palo-Colombia", "n": "El Palo", "c": "Colombia", "r": "col_cauca", "ll": [3.065, -76.35354], "ey": 1525, "ly": 2018, "p": 3417, "al": ["alto el palo", "Alto El Palo"]},
  {"key": "Antaymarka-Peru", "n": "Antaymarka", "c": "Peru", "r": "inca_contisuyu", "ll": [-15.51412, -72.34339], "ey": -1000, "ly": 1530, "p": 3417},
  {"key": "Sortilegio-Peru_2", "n": "Sortilegio", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.18758, -75.86377], "ey": -3000, "ly": 1530, "p": 3416, "al": ["capitan marino bustamante", "capitán marino bustamante", "Capitan Marino Bustamante"]},
  {"key": "Parán-Peru", "n": "Parán", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.0203, -77.07324], "ey": 0, "ly": 1530, "p": 3415, "al": ["huaro", "pariacoto", "raniahuanco"]},
  {"key": "Kunstman 1 CGO-Chile", "n": "Kunstman 1 CGO", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.83554, -73.28508], "ey": 1350, "ly": 1500, "p": 3415, "al": ["el bayo", "fundo el bayo", "restaurant kunstmann"]},
  {"key": "Llanquera-Bolivia", "n": "Llanquera", "c": "Bolivia", "r": "bol_oruro", "ll": [-17.99004, -67.69312], "ey": 1525, "ly": 2024, "p": 3413},
  {"key": "Rocas de Suesca-Colombia", "n": "Rocas de Suesca", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.118, -73.78566], "ey": 1000, "ly": 1500, "p": 3413},
  {"key": "Gualmatán (col_narino)-Colombia", "n": "Gualmatán", "c": "Colombia", "r": "col_narino", "ll": [1.1725, -77.31623], "ey": 1525, "ly": 2018, "p": 3411, "al": ["gualmata", "gualmatan alto", "gualmatan"]},
  {"key": "Otón-Ecuador", "n": "Otón", "c": "Ecuador", "r": "ecu_pichincha", "ll": [-0.02162, -78.25523], "ey": 1850, "ly": 2025, "p": 3411},
  {"key": "Korichaca KCH-Bolivia", "n": "Korichaca KCH", "c": "Bolivia", "r": "inca_collasuyu", "ll": [-17.97381, -67.16572], "ey": -379, "ly": 1500, "p": 3410, "al": ["cochiraya kch", "iroco kch", "Cochiraya KCH"]},
  {"key": "Guarumo-Colombia", "n": "Guarumo", "c": "Colombia", "r": "col_antioquia", "ll": [7.85456, -75.2094], "ey": 1850, "ly": 2018, "p": 3405},
  {"key": "Guacamayas-Colombia_2", "n": "Guacamayas", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.53845, -74.58323], "ey": 500, "ly": 1500, "p": 3405},
  {"key": "Jenesano-Colombia_2", "n": "Jenesano", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [5.38194, -73.38333], "ey": 500, "ly": 1500, "p": 3405},
  {"key": "Villa Marina-El Pico-Venezuela", "n": "Villa Marina-El Pico", "c": "Venezuela", "r": "ven_falcon", "ll": [11.83885, -70.27722], "ey": 1850, "ly": 2011, "p": 3404},
  {"key": "Juan Bautista Alberdi (arg_santa_fe)-Argentina", "n": "Juan Bautista Alberdi", "c": "Argentina", "r": "arg_santa_fe", "ll": [-34.43879, -61.81219], "ey": 1850, "ly": 2010, "p": 3404},
  {"key": "La Hornillas-Peru", "n": "La Hornillas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.93475, -77.8965], "ey": -1000, "ly": 1530, "p": 3404, "al": ["gomispampa", "Gomispampa"]},
  {"key": "9 de Julio (arg_corrientes)-Argentina", "n": "9 de Julio", "c": "Argentina", "r": "arg_corrientes", "ll": [-28.84078, -58.83009], "ey": 1850, "ly": 2022, "p": 3402},
  {"key": "Sacanta-Argentina", "n": "Sacanta", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.66343, -63.04794], "ey": 1850, "ly": 2022, "p": 3401},
  {"key": "Santa Rosa-Colombia_3", "n": "Santa Rosa", "c": "Colombia", "r": "na_nw_amazon_foothills", "ll": [1.74, -76.46], "ey": 1205, "ly": 1500, "p": 3400},
  {"key": "Elena-Argentina", "n": "Elena", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.57041, -64.39391], "ey": 1850, "ly": 2022, "p": 3399},
  {"key": "Veracruz-Venezuela", "n": "Veracruz", "c": "Venezuela", "r": "ven_tachira", "ll": [7.65389, -72.25389], "ey": 1850, "ly": 2011, "p": 3398},
  {"key": "Río Grande (per_ica)-Peru", "n": "Río Grande", "c": "Peru", "r": "per_ica", "ll": [-14.52, -75.20111], "ey": 1950, "ly": 2025, "p": 3398},
  {"key": "Sina-Peru", "n": "Sina", "c": "Peru", "r": "per_puno", "ll": [-14.49667, -69.28028], "ey": 1525, "ly": 2025, "p": 3398},
  {"key": "Zodme-Colombia", "n": "Zodme", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [2.465, -75.6125], "ey": 500, "ly": 1500, "p": 3398, "al": ["lah-la hocha", "lah", "zodme z"]},
  {"key": "Cutusuma (bol_la_paz)-Bolivia", "n": "Cutusuma", "c": "Bolivia", "r": "bol_la_paz", "ll": [-16.44293, -67.50664], "ey": 1525, "ly": 2024, "p": 3397, "al": ["ocobaya", "Ocobaya"]},
  {"key": "UMP15 Yacimiento 7 Perfil estratigráfico-Colombia", "n": "UMP15 Yacimiento 7 Perfil estratigráfico", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [8.57423, -75.72717], "ey": 1300, "ly": 1500, "p": 3396},
  {"key": "Laguna de La Sal-Argentina", "n": "Laguna de La Sal", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-29.92488, -63.23048], "ey": 80, "ly": 1500, "p": 3396},
  {"key": "San Félix (ven_falcon)-Venezuela", "n": "San Félix", "c": "Venezuela", "r": "ven_falcon", "ll": [10.88, -71.12056], "ey": 1850, "ly": 2025, "p": 3395},
  {"key": "Carhuas 1 y-Peru", "n": "Carhuas 1 y", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.15278, -75.92454], "ey": -2000, "ly": 1530, "p": 3395, "al": ["pampa carhuas", "pampa la joya honda grande", "Pampa Carhuas"]},
  {"key": "Puente de Piedra-Colombia", "n": "Puente de Piedra", "c": "Colombia", "r": "col_cundinamarca", "ll": [4.81601, -74.22125], "ey": 1850, "ly": 2018, "p": 3394},
  {"key": "Topo-Colombia", "n": "Topo", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.5, -74.173], "ey": 1525, "ly": 1830, "p": 3394},
  {"key": "Turberas de Púlpito-Chile", "n": "Turberas de Púlpito", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-42.74998, -73.86838], "ey": 1000, "ly": 1500, "p": 3393},
  {"key": "Presidente Urbina-Ecuador", "n": "Presidente Urbina", "c": "Ecuador", "r": "ecu_tungurahua", "ll": [-1.14735, -78.55489], "ey": 1850, "ly": 2025, "p": 3391},
  {"key": "Alero Arias-Argentina", "n": "Alero Arias", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-40.05, -69.95], "ey": -1700, "ly": -800, "p": 3391},
  {"key": "Los Cóndores-Argentina", "n": "Los Cóndores", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.31748, -64.27398], "ey": 1850, "ly": 2022, "p": 3390},
  {"key": "San Sebastian de los Reyes-Venezuela", "n": "San Sebastian de los Reyes", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [9.946, -67.179], "ey": 1585, "ly": 1830, "p": 3390},
  {"key": "Yatay Ti Calle-Argentina", "n": "Yatay Ti Calle", "c": "Argentina", "r": "arg_corrientes", "ll": [-29.0283, -58.91225], "ey": 1850, "ly": 2022, "p": 3389, "al": ["yatayti calle", "Yatayti Calle"]},
]

HEADERS = {"User-Agent": "SVEA-QUIPU-Research/1.0 (contact@example.com)"}

def fetch_json(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=15) as resp:
    return json.loads(resp.read().decode("utf-8"))

def query_settlement(s):
  lat, lon = s["ll"]
  res = {"key": s["key"], "n": s["n"], "c": s["c"], "geo": [], "search": []}
  # 1. es.wikipedia geosearch
  try:
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=3&format=json"
    data = fetch_json(url)
    for g in data.get("query", {}).get("geosearch", []):
      res["geo"].append({"title": g["title"], "dist": g["dist"]})
  except Exception as e:
    res["geo_err"] = str(e)
  # 2. es.wikipedia search
  try:
    q = urllib.parse.quote(f'{s["n"]} {s["c"]}')
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=2&format=json"
    data = fetch_json(url)
    for item in data.get("query", {}).get("search", []):
      res["search"].append(item["title"])
  except Exception as e:
    res["search_err"] = str(e)
  return res

with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
  results = list(ex.map(query_settlement, SETTLEMENTS))

with open("tests/wiki_lookup_049.json", "w", encoding="utf-8") as f:
  json.dump(results, f, ensure_ascii=False, indent=2)
print(f"Done: {len(results)}")
