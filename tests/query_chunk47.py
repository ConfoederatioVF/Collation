import json
import urllib.request
import urllib.parse
import urllib.error
import time

SETTLEMENTS = [
  {"key": "Medina-Argentina", "n": "Medina", "c": "Argentina", "r": "arg_tucuman", "ll": [-27.42208, -65.53293], "ey": 1850, "ly": 2022, "p": 3613},
  {"key": "Choqeq-Peru", "n": "Choqeq", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.65441, -74.37126], "ey": 500, "ly": 1530, "p": 3613, "al": ["karwancho", "ranra", "yanaurqo"]},
  {"key": "Medialuna-Colombia", "n": "Medialuna", "c": "Colombia", "r": "col_magdalena", "ll": [10.51241, -74.50404], "ey": 1850, "ly": 2018, "p": 3612},
  {"key": "Quiaca-Peru", "n": "Quiaca", "c": "Peru", "r": "per_puno", "ll": [-14.42222, -69.345], "ey": 1525, "ly": 2025, "p": 3612},
  {"key": "Cucuta-Bolivia", "n": "Cucuta", "c": "Bolivia", "r": "bol_la_paz", "ll": [-16.46003, -68.30846], "ey": 1850, "ly": 2024, "p": 3612},
  {"key": "La Estrella-Chile", "n": "La Estrella", "c": "Chile", "r": "chl_region_del_libertador_bernardo_o_higgins", "ll": [-34.20575, -71.59075], "ey": 1525, "ly": 2025, "p": 3612},
  {"key": "Pichinde-Colombia", "n": "Pichinde", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.43815, -76.61526], "ey": 1525, "ly": 2018, "p": 3610, "al": ["anaconas", "yanaconas", "Anaconas"]},
  {"key": "San Jacinto Gaira-Colombia", "n": "San Jacinto Gaira", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [11.193, -74.224], "ey": 1525, "ly": 1830, "p": 3609},
  {"key": "Plaza-Chile", "n": "Plaza", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-32.399, -71.282], "ey": 1525, "ly": 1830, "p": 3609},
  {"key": "Sección Capital Sucre-Venezuela", "n": "Sección Capital Sucre", "c": "Venezuela", "r": "ven_bolivar", "ll": [7.41333, -65.18389], "ey": 1850, "ly": 2025, "p": 3605},
  {"key": "BADACOR. Base de Datos Arqueológica de Córdoba-Argentina", "n": "BADACOR. Base de Datos Arqueológica de Córdoba", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.8646, -63.80364], "ey": 1000, "ly": 1500, "p": 3601},
  {"key": "Filas de Mariches-Venezuela", "n": "Filas de Mariches", "c": "Venezuela", "r": "ven_la_guaira", "ll": [10.42192, -66.72305], "ey": 1850, "ly": 2025, "p": 3600},
  {"key": "María Susana-Argentina", "n": "María Susana", "c": "Argentina", "r": "arg_santa_fe", "ll": [-32.26672, -61.906], "ey": 1850, "ly": 2022, "p": 3597},
  {"key": "SAR Cruz del Borugo-Colombia", "n": "SAR Cruz del Borugo", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [3.93068, -74.82909], "ey": 1000, "ly": 1500, "p": 3597, "al": ["sar el borugo", "sar media luna", "SAR El Borugo"]},
  {"key": "Silla del Presidente-Chile", "n": "Silla del Presidente", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-41.41551, -72.91185], "ey": 500, "ly": 1500, "p": 3597},
  {"key": "Llaqtapata - Pajonal-Peru", "n": "Llaqtapata - Pajonal", "c": "Peru", "r": "inca_antisuyu", "ll": [-12.71036, -72.06754], "ey": -3000, "ly": 1530, "p": 3596, "al": ["hatun monte", "qorimayo", "Hatun Monte"]},
  {"key": "Sa-Pmn-Colombia", "n": "Sa-Pmn", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.34356, -75.50845], "ey": 1300, "ly": 1500, "p": 3595, "al": ["cospique", "Cospique"]},
  {"key": "General Vedia-Argentina", "n": "General Vedia", "c": "Argentina", "r": "arg_chaco", "ll": [-26.93744, -58.66116], "ey": 1900, "ly": 2022, "p": 3593},
  {"key": "Coate-Bolivia", "n": "Coate", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-15.765, -68.805], "ey": 1525, "ly": 1825, "p": 3593, "al": ["cumlili", "Cumlili"]},
  {"key": "Manuel Cornejo Astorga-Ecuador", "n": "Manuel Cornejo Astorga", "c": "Ecuador", "r": "ecu_santo_domingo_de_los_tsachilas", "ll": [-0.41385, -78.7808], "ey": 1850, "ly": 2025, "p": 3592},
  {"key": "Mancopa-Argentina", "n": "Mancopa", "c": "Argentina", "r": "arg_tucuman", "ll": [-27.02976, -65.15292], "ey": 1536, "ly": 2022, "p": 3591, "al": ["macopa", "Macopa"]},
  {"key": "San Juan Bautista Carache-Venezuela", "n": "San Juan Bautista Carache", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [9.628, -70.229], "ey": 1538, "ly": 1830, "p": 3591},
  {"key": "Tacocumo-Bolivia", "n": "Tacocumo", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.034, -66.869], "ey": 1525, "ly": 1825, "p": 3589, "al": ["cuti", "Cuti"]},
  {"key": "Pucchun-Peru", "n": "Pucchun", "c": "Peru", "r": "per_arequipa", "ll": [-16.5986, -72.7743], "ey": 1850, "ly": 2017, "p": 3588},
  {"key": "El Salado-Colombia_2", "n": "El Salado", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.91657, -73.75052], "ey": 1300, "ly": 1500, "p": 3588, "al": ["plataforma 2", "plataforma 3", "la forest"]},
  {"key": "Cipriano Castro-Venezuela", "n": "Cipriano Castro", "c": "Venezuela", "r": "ven_tachira", "ll": [7.87167, -72.37167], "ey": 1850, "ly": 2025, "p": 3586},
  {"key": "Inchupalla-Peru", "n": "Inchupalla", "c": "Peru", "r": "per_puno", "ll": [-15.00972, -69.68278], "ey": 1850, "ly": 2025, "p": 3586},
  {"key": "La Mireya-Colombia", "n": "La Mireya", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [8.05, -75.48], "ey": 645, "ly": 1500, "p": 3586},
  {"key": "Totora (vp_intendencia_cochabamba)-Bolivia", "n": "Totora", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.781, -66.454], "ey": 1525, "ly": 1825, "p": 3585, "al": ["comuna", "Comuna"]},
  {"key": "Huayrana Punta-Peru", "n": "Huayrana Punta", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.68978, -75.28976], "ey": -1000, "ly": 1530, "p": 3585, "al": ["andenes agrícolas prehispánicos de casa blanca", "aqchipunta", "arqueológico andenes agricolas prehispanicos de muchca"]},
  {"key": "Huagramona-Peru", "n": "Huagramona", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-3.08015, -76.43443], "ey": -3000, "ly": 1530, "p": 3584, "al": ["pirum", "Pirum"]},
  {"key": "San Francisco (ven_anzoategui)-Venezuela", "n": "San Francisco", "c": "Venezuela", "r": "ven_anzoategui", "ll": [9.83298, -65.05184], "ey": 1538, "ly": 2025, "p": 3583, "al": ["san francisco guere", "San Francisco Guere"]},
  {"key": "Lehmann-Argentina", "n": "Lehmann", "c": "Argentina", "r": "arg_santa_fe", "ll": [-31.12533, -61.45252], "ey": 1850, "ly": 2022, "p": 3583},
  {"key": "Chilla-Ecuador", "n": "Chilla", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.43962, -79.62908], "ey": 1525, "ly": 2025, "p": 3582, "al": ["chilloa", "Chilloa"]},
  {"key": "Toko-Bolivia", "n": "Toko", "c": "Bolivia", "r": "bol_cochabamba", "ll": [-17.62403, -65.92341], "ey": 1525, "ly": 2024, "p": 3582, "al": ["toco", "Toco"]},
  {"key": "Valle Hermoso-Chile", "n": "Valle Hermoso", "c": "Chile", "r": "chl_region_de_valparaiso", "ll": [-32.44708, -71.20078], "ey": 1525, "ly": 2017, "p": 3582, "al": ["none", "pueblo de valle hermoso", "None"]},
  {"key": "Itacaruaré-Argentina", "n": "Itacaruaré", "c": "Argentina", "r": "arg_misiones", "ll": [-27.87137, -55.26223], "ey": 1900, "ly": 2022, "p": 3582},
  {"key": "Cerro Wanina-Peru", "n": "Cerro Wanina", "c": "Peru", "r": "inca_collasuyu", "ll": [-15.63453, -69.9589], "ey": 500, "ly": 1530, "p": 3582, "al": ["cerro chupa", "cerro k'apis", "cerro llank'ako"]},
  {"key": "Tango-Chile", "n": "Tango", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-33.627, -70.777], "ey": 1525, "ly": 1830, "p": 3580, "ex": [{"date": "1950.1.1", "name": "Calera de Tango"}], "al": ["tanco", "Tanco"]},
  {"key": "Las Mellas-Peru", "n": "Las Mellas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.02922, -78.3016], "ey": -1000, "ly": 1530, "p": 3580, "al": ["abrigo quebrada las mellas", "cerro agujero", "cerro michiquillay"]},
  {"key": "Rumicucho-Ecuador", "n": "Rumicucho", "c": "Ecuador", "r": "inca_chinchaysuyu", "ll": [0.014, -78.442], "ey": 1490, "ly": 1530, "p": 3580},
  {"key": "General Lucio Victorio Mansilla-Argentina", "n": "General Lucio Victorio Mansilla", "c": "Argentina", "r": "arg_formosa", "ll": [-26.65496, -58.62509], "ey": 1900, "ly": 2022, "p": 3579, "al": ["general lucio v. mansilla", "puerto eva perón", "General Lucio V. Mansilla"]},
  {"key": "Gobernador Piedrabuena-Argentina", "n": "Gobernador Piedrabuena", "c": "Argentina", "r": "arg_tucuman", "ll": [-26.73986, -64.64934], "ey": 1850, "ly": 2022, "p": 3577, "al": ["piedrabuena", "Piedrabuena"]},
  {"key": "Tuluchuco (Tuluchucu-Peru", "n": "Tuluchuco (Tuluchucu", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.30201, -76.40916], "ey": 1438, "ly": 1530, "p": 3576, "al": ["otocayna", "tacta punta", "tangor punqu"]},
  {"key": "Enace I II III-Peru", "n": "Enace I II III", "c": "Peru", "r": "per_piura", "ll": [-4.5951, -81.18], "ey": 1850, "ly": 2017, "p": 3575},
  {"key": "Perfil (na_magdalena_cauca_muisca)-Colombia", "n": "Perfil", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.837, -75.73794], "ey": -1000, "ly": 1500, "p": 3575, "al": ["terraza 14 c", "terraza 24 c", "terraza 28 c"]},
  {"key": "Pujato-Argentina", "n": "Pujato", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.01765, -61.0431], "ey": 1850, "ly": 2022, "p": 3574},
  {"key": "Camsana-Chile", "n": "Camsana", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.857, -69.344], "ey": 1525, "ly": 1825, "p": 3574, "al": ["cansana", "Cansana"]},
  {"key": "Crucero de Pescador-Colombia", "n": "Crucero de Pescador", "c": "Colombia", "r": "col_cauca", "ll": [2.80591, -76.54741], "ey": 1525, "ly": 2018, "p": 3573, "al": ["pescador", "pulibio", "Pescador"]},
  {"key": "San Francisco-Chile_2", "n": "San Francisco", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.88304, -72.618], "ey": -300, "ly": 1500, "p": 3573},
  {"key": "Progreso-Peru", "n": "Progreso", "c": "Peru", "r": "per_apurimac", "ll": [-14.07222, -72.47667], "ey": 1850, "ly": 2025, "p": 3570},
  {"key": "Antonio Nicolás Briceño-Venezuela", "n": "Antonio Nicolás Briceño", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.37278, -70.575], "ey": 1850, "ly": 2025, "p": 3569},
  {"key": "Cerca de Piedra-Colombia", "n": "Cerca de Piedra", "c": "Colombia", "r": "col_cundinamarca", "ll": [4.84446, -74.0822], "ey": 1850, "ly": 2018, "p": 3568, "al": ["pueblo fuerte", "puente cacique", "santa bárbara"]},
  {"key": "Choros-Peru", "n": "Choros", "c": "Peru", "r": "per_cajamarca", "ll": [-5.9, -78.69389], "ey": 1850, "ly": 2025, "p": 3566},
  {"key": "Los Cerrillos-Uruguay", "n": "Los Cerrillos", "c": "Uruguay", "r": "ury_canelones", "ll": [-34.60625, -56.35921], "ey": 1850, "ly": 2023, "p": 3564},
  {"key": "Jagüey Hacha Pulida-Colombia", "n": "Jagüey Hacha Pulida", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [10.60275, -74.61662], "ey": 1000, "ly": 1500, "p": 3562},
  {"key": "Villa Parque Síquiman-Argentina", "n": "Villa Parque Síquiman", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.34735, -64.48282], "ey": 1850, "ly": 2022, "p": 3561, "al": ["villa parque siquimán", "Villa Parque Siquimán"]},
  {"key": "Toquepala-Peru", "n": "Toquepala", "c": "Peru", "r": "per_tacna", "ll": [-17.2795, -70.6321], "ey": 1850, "ly": 2017, "p": 3560},
  {"key": "Los Naranjos-Venezuela", "n": "Los Naranjos", "c": "Venezuela", "r": "ven_zulia", "ll": [8.74333, -71.655], "ey": 1850, "ly": 2011, "p": 3559},
  {"key": "Ciudad del Carmen-Uruguay", "n": "Ciudad del Carmen", "c": "Uruguay", "r": "ury_durazno", "ll": [-33.23664, -56.00321], "ey": 1880, "ly": 2023, "p": 3559},
  {"key": "Piedra Grande - Ayanquera-Peru", "n": "Piedra Grande - Ayanquera", "c": "Peru", "r": "inca_contisuyu", "ll": [-17.02078, -71.68639], "ey": 500, "ly": 1530, "p": 3559, "al": ["ayanquera", "Ayanquera"]},
  {"key": "Terraza El Capacho-Colombia", "n": "Terraza El Capacho", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.27712, -75.43023], "ey": 1000, "ly": 1500, "p": 3559, "al": ["terraza alto bosque", "terraza guayacán", "Terraza Alto Bosque"]},
  {"key": "Palmales-Ecuador", "n": "Palmales", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.69609, -80.0899], "ey": 1850, "ly": 2025, "p": 3556},
  {"key": "Algallama-Peru_2", "n": "Algallama", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.11691, -78.12572], "ey": 0, "ly": 1532, "p": 3555, "al": ["cerro blanco", "cerro calvario", "cerro campana"]},
  {"key": "Plaza Punta-Peru", "n": "Plaza Punta", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.03277, -75.94115], "ey": -2000, "ly": 1530, "p": 3555},
  {"key": "Cerro Sota-Chile", "n": "Cerro Sota", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.06667, -70.05], "ey": -2293, "ly": -969, "p": 3555},
  {"key": "Chugur-Peru", "n": "Chugur", "c": "Peru", "r": "per_cajamarca", "ll": [-6.67083, -78.73833], "ey": 1850, "ly": 2025, "p": 3553},
  {"key": "Quebrada Culebrillas-Peru", "n": "Quebrada Culebrillas", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.39344, -71.68925], "ey": 0, "ly": 1530, "p": 3553, "al": ["el arenal", "corralones", "El Arenal"]},
  {"key": "Yaunchu-Ecuador", "n": "Yaunchu", "c": "Ecuador", "r": "inca_chinchaysuyu", "ll": [-2.4667, -78.1667], "ey": 721, "ly": 1532, "p": 3552},
  {"key": "Huambi-Ecuador", "n": "Huambi", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-2.53615, -78.16265], "ey": 1920, "ly": 2025, "p": 3551},
  {"key": "El Venado-Colombia_2", "n": "El Venado", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.50003, -73.47771], "ey": 680, "ly": 1500, "p": 3551},
  {"key": "Selva-Argentina", "n": "Selva", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-29.76833, -62.04753], "ey": 1850, "ly": 2022, "p": 3547},
  {"key": "Cerro Ichal-Peru", "n": "Cerro Ichal", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.0191, -78.17785], "ey": -1000, "ly": 1530, "p": 3546, "al": ["catequil", "cerro icchal", "chulite"]},
  {"key": "Kimsapunku-Peru", "n": "Kimsapunku", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.8401, -76.20961], "ey": -1000, "ly": 1530, "p": 3546, "al": ["armoncalloq", "esperanza", "huarampay"]},
  {"key": "Choroma-Bolivia", "n": "Choroma", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-21.379, -65.715], "ey": 1525, "ly": 1825, "p": 3545, "al": ["coroma", "Coroma"]},
  {"key": "Dos Canoas-Chile", "n": "Dos Canoas", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.5738, -72.2427], "ey": 1232, "ly": 1500, "p": 3544, "al": ["los resfalines", "pitrén", "Los Resfalines"]},
  {"key": "Las Mercedes-Chile_2", "n": "Las Mercedes", "c": "Chile", "r": "inca_collasuyu", "ll": [-33.6066, -71.625], "ey": -4888, "ly": 1532, "p": 3543, "al": ["humedal río maipo", "tejas verdes", "cancha de golf"]},
  {"key": "Londres-Argentina", "n": "Londres", "c": "Argentina", "r": "arg_catamarca", "ll": [-27.71346, -67.13416], "ey": 1536, "ly": 2022, "p": 3542, "al": ["londres de la nueva inglaterra", "Londres de la Nueva Inglaterra"]},
  {"key": "Auquipunta-Peru", "n": "Auquipunta", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.53536, -76.69155], "ey": 1438, "ly": 1530, "p": 3541, "al": ["auquimarca", "castillo", "arqueológico ichay pintash o yachay pintash"]},
  {"key": "Arroyo de Piedra-Colombia", "n": "Arroyo de Piedra", "c": "Colombia", "r": "col_atlantico", "ll": [10.63095, -75.10514], "ey": 1850, "ly": 2018, "p": 3534},
  {"key": "Moyano-Argentina", "n": "Moyano", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.66459, -63.86053], "ey": 80, "ly": 1500, "p": 3533, "al": ["bujedo", "casanove", "Bujedo"]},
  {"key": "Yamon-Peru", "n": "Yamon", "c": "Peru", "r": "per_amazonas", "ll": [-6.05083, -78.52889], "ey": 1783, "ly": 2025, "p": 3532, "al": ["yamón", "jamon", "Yamón"]},
  {"key": "Bombal-Argentina", "n": "Bombal", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.45791, -61.31817], "ey": 1850, "ly": 2022, "p": 3532},
  {"key": "Bilován-Ecuador", "n": "Bilován", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.83204, -79.15296], "ey": 1850, "ly": 2025, "p": 3531},
  {"key": "Aranjuez-Colombia", "n": "Aranjuez", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [3.33444, -76.40276], "ey": 500, "ly": 1500, "p": 3531},
  {"key": "Choquecota-Bolivia", "n": "Choquecota", "c": "Bolivia", "r": "bol_oruro", "ll": [-18.25, -67.95], "ey": 1542, "ly": 2026, "p": 3530, "al": ["chuquicota", "Chuquicota"]},
  {"key": "Pueblo Independencia-Argentina", "n": "Pueblo Independencia", "c": "Argentina", "r": "arg_tucuman", "ll": [-27.22006, -65.52405], "ey": 1850, "ly": 2010, "p": 3530},
  {"key": "El Cabo-Ecuador", "n": "El Cabo", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.84232, -78.79719], "ey": 1850, "ly": 2025, "p": 3529},
  {"key": "Alicia-Argentina", "n": "Alicia", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.93885, -62.4642], "ey": 1850, "ly": 2022, "p": 3529},
  {"key": "Monte Comán-Argentina", "n": "Monte Comán", "c": "Argentina", "r": "arg_mendoza", "ll": [-34.59236, -67.86897], "ey": 1850, "ly": 2010, "p": 3529}
]

HEADERS = {'User-Agent': 'OperationViscountBot/1.0 (https://confoederatio.org; research@confoederatio.org)'}

def fetch_json(url):
  for attempt in range(4):
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
      if e.code in (429, 503):
        time.sleep(1.5 * (attempt + 1))
      else:
        return None
    except Exception:
      time.sleep(0.5)
  return None

def wiki_geosearch(lat, lon, lang='es'):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
  data = fetch_json(url)
  return data.get('query', {}).get('geosearch', []) if data else []

def wiki_search(q, lang='es'):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=3&format=json"
  data = fetch_json(url)
  return [x['title'] for x in data.get('query', {}).get('search', [])] if data else []

def wiki_extract(title, lang='es'):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exsectionformat=plain&titles={urllib.parse.quote(title)}&format=json"
  data = fetch_json(url)
  if not data:
    return ''
  pages = data.get('query', {}).get('pages', {})
  for pid, p in pages.items():
    if pid != '-1':
      return p.get('extract', '')[:4000]
  return ''

results = []
for idx, s in enumerate(SETTLEMENTS):
  lat, lon = s['ll']
  geo = wiki_geosearch(lat, lon, 'es')
  time.sleep(0.05)
  titles = wiki_search(f"{s['n']} {s['c']}", 'es')
  time.sleep(0.05)
  chosen_title = None
  for g in geo:
    if g['dist'] < 5000:
      chosen_title = g['title']
      break
  if not chosen_title and titles:
    chosen_title = titles[0]
  extract = wiki_extract(chosen_title, 'es') if chosen_title else ''
  extra_extract = ''
  if titles and titles[0] != chosen_title:
    extra_extract = wiki_extract(titles[0], 'es')[:2000]
  results.append({
    'key': s['key'],
    'n': s['n'],
    'c': s['c'],
    'r': s['r'],
    'ey': s['ey'],
    'geo': [(g['title'], g['dist']) for g in geo[:3]],
    'search': titles,
    'chosen': chosen_title,
    'extract': extract,
    'extra': extra_extract
  })
  if (idx + 1) % 15 == 0:
    print(f"Processed {idx+1}/90", flush=True)

with open('tests/chunk47_wiki.json', 'w', encoding='utf-8') as f:
  json.dump(results, f, ensure_ascii=False, indent=2)

print("All 90 done!")
