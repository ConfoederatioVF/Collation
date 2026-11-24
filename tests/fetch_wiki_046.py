import concurrent.futures
import json
import urllib.parse
import urllib.request

ITEMS = [
  {"key": "Guachapala-Ecuador", "n": "Guachapala", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.76753, -78.71187], "ey": 1850, "ly": 2025, "p": 3681},
  {"key": "Entre Torre 77 y-Colombia", "n": "Entre Torre 77 y", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.89443, -74.85628], "ey": 1271, "ly": 1500, "p": 3681, "al": ["torre", "la curtiembre", "la sierra"]},
  {"key": "Valdivia-Chile_2", "n": "Valdivia", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-39.814, -73.246], "ey": 1555, "ly": 1813, "p": 3680, "ex": [{"date": "1865.1.1", "name": "Valdivia"}], "al": ["san francisco de la plaza de valdivia", "San Francisco de la plaza de Valdivia"]},
  {"key": "El Morro Tumaco-Colombia", "n": "El Morro Tumaco", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.812, -78.731], "ey": -400, "ly": 1100, "p": 3680, "ex": [{"date": "1902.1.1", "name": "Tumaco"}], "al": ["el morro", "exporcol", "tumaco"]},
  {"key": "Chavín de Huántar-Peru", "n": "Chavín de Huántar", "c": "Peru", "r": "ca_north_coast_moche_chimu", "ll": [-9.593, -77.177], "ey": -1000, "ly": -200, "p": 3680, "al": ["chavin de huantar", "chavín de huantar", "chuyopampa"]},
  {"key": "Huaca Santa Fe-Peru", "n": "Huaca Santa Fe", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-13.69862, -76.18095], "ey": -2000, "ly": 1530, "p": 3676, "al": ["alto el molino", "alto molino", "camacho"]},
  {"key": "San Isidro de la Sierra de las Minas-Argentina", "n": "San Isidro de la Sierra de las Minas", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-31.683, -66.583], "ey": 1536, "ly": 1830, "p": 3675, "al": ["minas de san isidro", "Minas de San Isidro"]},
  {"key": "Quebrada-Bolivia", "n": "Quebrada", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-19.258, -64.353], "ey": 1525, "ly": 1825, "p": 3675},
  {"key": "Confines-Colombia", "n": "Confines", "c": "Colombia", "r": "col_santander", "ll": [6.35733, -73.24055], "ey": 1773, "ly": 2025, "p": 3674, "al": ["culatas", "Culatas"]},
  {"key": "El Alamein-Peru", "n": "El Alamein", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-13.86288, -76.13961], "ey": -2000, "ly": 1530, "p": 3673},
  {"key": "Villa Santa Cruz del Lago-Argentina", "n": "Villa Santa Cruz del Lago", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.37028, -64.5175], "ey": 1850, "ly": 2022, "p": 3672, "al": ["estancia vieja", "Estancia Vieja"]},
  {"key": "El Tala-Argentina", "n": "El Tala", "c": "Argentina", "r": "arg_tucuman", "ll": [-26.11212, -65.2778], "ey": 1850, "ly": 2022, "p": 3671},
  {"key": "Constitucion-Uruguay", "n": "Constitucion", "c": "Uruguay", "r": "ury_salto", "ll": [-31.07599, -57.84605], "ey": 1850, "ly": 2023, "p": 3671, "al": ["barrio hipico", "Barrio Hipico"]},
  {"key": "Chalguani-Bolivia", "n": "Chalguani", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.89, -64.856], "ey": 1525, "ly": 1825, "p": 3671},
  {"key": "Belén de Andamarca-Bolivia", "n": "Belén de Andamarca", "c": "Bolivia", "r": "bol_oruro", "ll": [-18.81936, -67.64104], "ey": 1525, "ly": 2026, "p": 3670, "al": ["belen de andamarca", "belen", "Belen de Andamarca"]},
  {"key": "Andacollo-Argentina", "n": "Andacollo", "c": "Argentina", "r": "arg_neuquen", "ll": [-37.17968, -70.67002], "ey": 1900, "ly": 2022, "p": 3669},
  {"key": "Santa Clara De Olimar-Uruguay", "n": "Santa Clara De Olimar", "c": "Uruguay", "r": "ury_treinta_y_tres", "ll": [-32.92216, -54.94562], "ey": 1850, "ly": 2023, "p": 3669},
  {"key": "Corozal-Venezuela_2", "n": "Corozal", "c": "Venezuela", "r": "na_orinoco_llanos_guayana", "ll": [7.92, -65.697], "ey": -1000, "ly": 1500, "p": 3668, "al": ["parmana", "la gruta", "ronquín"]},
  {"key": "Riveras del San Juan-Colombia", "n": "Riveras del San Juan", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.57754, -74.20835], "ey": 1300, "ly": 1500, "p": 3668},
  {"key": "Huayllan-Peru", "n": "Huayllan", "c": "Peru", "r": "per_ancash", "ll": [-8.85806, -77.43556], "ey": 1850, "ly": 2025, "p": 3666, "al": ["huayllán", "Huayllán"]},
  {"key": "San Miguel (ven_anzoategui)-Venezuela", "n": "San Miguel", "c": "Venezuela", "r": "ven_anzoategui", "ll": [9.90904, -64.99078], "ey": 1970, "ly": 2025, "p": 3665},
  {"key": "Dominguillo-Ecuador", "n": "Dominguillo", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-4.143, -79.989], "ey": 1525, "ly": 1830, "p": 3665},
  {"key": "Bolivia-Venezuela", "n": "Bolivia", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.61222, -70.30833], "ey": 1850, "ly": 2025, "p": 3664},
  {"key": "San Blas-Ecuador", "n": "San Blas", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.42625, -78.26843], "ey": 1850, "ly": 2025, "p": 3664},
  {"key": "San Juan de Jarpa-Peru", "n": "San Juan de Jarpa", "c": "Peru", "r": "per_junin", "ll": [-12.12639, -75.43556], "ey": 1850, "ly": 2025, "p": 3664, "al": ["jarpa", "Jarpa"]},
  {"key": "Herradura-Colombia", "n": "Herradura", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.023, -77.178], "ey": 1525, "ly": 1830, "p": 3663},
  {"key": "Rondón-Colombia", "n": "Rondón", "c": "Colombia", "r": "col_boyaca", "ll": [5.35738, -73.20847], "ey": 1850, "ly": 2025, "p": 3662},
  {"key": "San José De Guayusa-Ecuador", "n": "San José De Guayusa", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.24751, -77.05971], "ey": 1920, "ly": 2025, "p": 3661},
  {"key": "Pueblo General Belgrano-Argentina", "n": "Pueblo General Belgrano", "c": "Argentina", "r": "arg_entre_rios", "ll": [-33.01715, -58.46843], "ey": 1850, "ly": 2022, "p": 3660},
  {"key": "Tío Pujio-Argentina", "n": "Tío Pujio", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.28707, -63.35368], "ey": 1850, "ly": 2022, "p": 3659},
  {"key": "Zona A - Sinifaná - Yacimiento 02 - Terraza-Colombia", "n": "Zona A - Sinifaná - Yacimiento 02 - Terraza", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.97211, -75.77323], "ey": -1000, "ly": 1500, "p": 3658, "al": ["zona a - sinifaná - el altar de los sacrificios", "zona a - sinifaná - la silla del cacique", "Zona A - Sinifaná - El Altar de los Sacrificios"]},
  {"key": "Antonio José Holguín-Ecuador", "n": "Antonio José Holguín", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-1.09742, -78.60045], "ey": 1850, "ly": 2025, "p": 3657},
  {"key": "San Pablo de Tiquina-Bolivia", "n": "San Pablo de Tiquina", "c": "Bolivia", "r": "bol_la_paz", "ll": [-16.21795, -68.8428], "ey": 1525, "ly": 2026, "p": 3657, "al": ["san pablo", "san pawlu tikina", "silaya"]},
  {"key": "El Toro-Colombia", "n": "El Toro", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [8.14208, -76.11376], "ey": 1300, "ly": 1500, "p": 3657},
  {"key": "El Café-Venezuela", "n": "El Café", "c": "Venezuela", "r": "ven_miranda", "ll": [10.41361, -66.28389], "ey": 1850, "ly": 2025, "p": 3655},
  {"key": "Colonia Alberdi-Argentina", "n": "Colonia Alberdi", "c": "Argentina", "r": "arg_misiones", "ll": [-27.36005, -55.23157], "ey": 1900, "ly": 2022, "p": 3655},
  {"key": "La Paz-Ecuador", "n": "La Paz", "c": "Ecuador", "r": "ecu_carchi", "ll": [0.51886, -77.8489], "ey": 1850, "ly": 2025, "p": 3654},
  {"key": "Arq-Colombia", "n": "Arq", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [5.49461, -71.86502], "ey": 500, "ly": 1500, "p": 3653},
  {"key": "La Unión (ven_trujillo)-Venezuela", "n": "La Unión", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.33, -70.67111], "ey": 1850, "ly": 2025, "p": 3651},
  {"key": "Pelingara-Peru", "n": "Pelingara", "c": "Peru", "r": "per_piura", "ll": [-4.7046, -80.3105], "ey": 1525, "ly": 2017, "p": 3651},
  {"key": "Isaías Medina Angarita-Venezuela", "n": "Isaías Medina Angarita", "c": "Venezuela", "r": "ven_tachira", "ll": [7.68847, -72.4215], "ey": 1850, "ly": 2025, "p": 3650},
  {"key": "Marca Marca-Peru", "n": "Marca Marca", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.84824, -76.51257], "ey": -1000, "ly": 1530, "p": 3650, "al": ["huarichaca", "pajonal", "pucushan"]},
  {"key": "Potrero de Párraga-Colombia", "n": "Potrero de Párraga", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [3.36606, -76.34875], "ey": 500, "ly": 1500, "p": 3649},
  {"key": "Aguas Blancas-Argentina", "n": "Aguas Blancas", "c": "Argentina", "r": "arg_salta", "ll": [-22.73509, -64.35521], "ey": 1850, "ly": 2022, "p": 3648},
  {"key": "Lahuachaca-Bolivia", "n": "Lahuachaca", "c": "Bolivia", "r": "bol_la_paz", "ll": [-17.37692, -67.67488], "ey": 1750, "ly": 2026, "p": 3646, "al": ["la wa cha ka", "لاہواچاکا"]},
  {"key": "Tres Cruces (vp_intendencia_cochabamba)-Bolivia", "n": "Tres Cruces", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.491, -66.476], "ey": 1525, "ly": 1825, "p": 3645},
  {"key": "Gonzalo Pizarro (ecu_sucumbios)-Ecuador", "n": "Gonzalo Pizarro", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [0.01615, -77.37723], "ey": 1920, "ly": 2025, "p": 3644},
  {"key": "Aigua-Uruguay", "n": "Aigua", "c": "Uruguay", "r": "ury_lavalleja", "ll": [-34.20586, -54.76154], "ey": 1850, "ly": 2023, "p": 3643},
  {"key": "Salinas de Garci Mendoza-Bolivia", "n": "Salinas de Garci Mendoza", "c": "Bolivia", "r": "bol_oruro", "ll": [-19.63721, -67.67468], "ey": 1604, "ly": 2024, "p": 3642, "al": ["salinas de garcimendoza", "salinas de garcí mendoza", "Salinas de Garcimendoza"]},
  {"key": "Piamonte-Argentina", "n": "Piamonte", "c": "Argentina", "r": "arg_santa_fe", "ll": [-32.14401, -61.98051], "ey": 1850, "ly": 2022, "p": 3642},
  {"key": "Ccenota-Peru", "n": "Ccenota", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.23935, -73.33812], "ey": -2000, "ly": 1530, "p": 3642},
  {"key": "Campamento Soronal-Chile", "n": "Campamento Soronal", "c": "Chile", "r": "sc_atacama_norte_grande", "ll": [-20.59602, -69.97481], "ey": -3000, "ly": 1500, "p": 3642, "al": ["cmn_projecto_salitreras_wfl1", "cmn_projecto_salitreras_wfl1_none", "Cmn_projecto_salitreras_wfl1"]},
  {"key": "Jambelí-Ecuador", "n": "Jambelí", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [0.08501, -77.07454], "ey": 1920, "ly": 2025, "p": 3641},
  {"key": "Ludo-Ecuador", "n": "Ludo", "c": "Ecuador", "r": "ecu_azuay", "ll": [-3.09366, -78.8912], "ey": 1850, "ly": 2025, "p": 3641},
  {"key": "Mal ubicado-Colombia", "n": "Mal ubicado", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.123, -74.77361], "ey": 1000, "ly": 1500, "p": 3641},
  {"key": "Cerro Chipa-Peru", "n": "Cerro Chipa", "c": "Peru", "r": "inca_contisuyu", "ll": [-15.42402, -74.70268], "ey": 1440, "ly": 1532, "p": 3640, "al": ["cerro batidero", "tambo viejo inca", "acari viejo"]},
  {"key": "Los Amarillos-Argentina", "n": "Los Amarillos", "c": "Argentina", "r": "sc_gran_chaco_pilcomayo", "ll": [-23.437, -65.382], "ey": 1000, "ly": 1400, "p": 3640},
  {"key": "Tagua Tagua-Chile", "n": "Tagua Tagua", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-34.482, -71.158], "ey": -9000, "ly": 1450, "p": 3640, "al": ["cachapoal", "santa inés", "taguatagua"]},
  {"key": "Miculpaya-Bolivia", "n": "Miculpaya", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-19.756, -65.376], "ey": 1525, "ly": 1825, "p": 3639},
  {"key": "Rabanal-Venezuela", "n": "Rabanal", "c": "Venezuela", "r": "ven_anzoategui", "ll": [9.76389, -65.05278], "ey": 1538, "ly": 2011, "p": 3638, "al": ["san pablo guere", "camaruco", "mataruco"]},
  {"key": "Chiquinquira Tinaco-Venezuela", "n": "Chiquinquira Tinaco", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [9.697, -68.434], "ey": 1754, "ly": 1830, "p": 3638},
  {"key": "Punkuri Alto-Peru", "n": "Punkuri Alto", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.15152, -78.29569], "ey": -2000, "ly": 1530, "p": 3638, "al": ["fortaleza de kiske", "punkuri bajo", "Fortaleza de Kiske"]},
  {"key": "Botijas-Argentina", "n": "Botijas", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.7906, -64.64019], "ey": 80, "ly": 1500, "p": 3638, "al": ["morteros ojos al cielo", "Morteros Ojos al Cielo"]},
  {"key": "Alto Salaverry-Peru_2", "n": "Alto Salaverry", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.24222, -78.95046], "ey": 1300, "ly": 1532, "p": 3637, "al": ["area viiia cerro la mina", "area viia punta uripe", "conchal alto salaverry"]},
  {"key": "El Quebracho-Argentina", "n": "El Quebracho", "c": "Argentina", "r": "arg_formosa", "ll": [-23.34003, -61.87333], "ey": -572, "ly": 2022, "p": 3635},
  {"key": "Real del Padre-Argentina", "n": "Real del Padre", "c": "Argentina", "r": "arg_mendoza", "ll": [-34.84257, -67.76897], "ey": 1850, "ly": 2010, "p": 3635},
  {"key": "Pucachupa-Peru", "n": "Pucachupa", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.8834, -70.5432], "ey": 500, "ly": 1530, "p": 3634, "al": ["oq'echupa", "pukachupa", "Oq'echupa"]},
  {"key": "La Amapola-Colombia", "n": "La Amapola", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [3.66, -76.56], "ey": 398, "ly": 1500, "p": 3631, "al": ["ermita", "espiral", "jaguar"]},
  {"key": "SAR Guarinocito-Colombia", "n": "SAR Guarinocito", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.38643, -74.71924], "ey": 1000, "ly": 1500, "p": 3631},
  {"key": "Italaque-Bolivia", "n": "Italaque", "c": "Bolivia", "r": "bol_la_paz", "ll": [-15.47752, -69.04396], "ey": 1525, "ly": 2024, "p": 3630},
  {"key": "Río Negro (chl_region_de_los_lagos)-Chile", "n": "Río Negro", "c": "Chile", "r": "chl_region_de_los_lagos", "ll": [-41.95989, -72.47255], "ey": 1850, "ly": 2017, "p": 3629},
  {"key": "Pacharraga-Peru", "n": "Pacharraga", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.3749, -76.75031], "ey": 1438, "ly": 1530, "p": 3628, "al": ["ini gulpsh", "pachorraga", "pijun"]},
  {"key": "None (crp_obispado_concepcion_chiloe_2)-Chile", "n": "None", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-35.59862, -72.51281], "ey": 1525, "ly": 1599, "p": 3627, "al": ["guelquine", "loanco", "luanco"]},
  {"key": "Unión (ven_sucre)-Venezuela", "n": "Unión", "c": "Venezuela", "r": "ven_sucre", "ll": [10.26444, -62.91833], "ey": 1850, "ly": 2025, "p": 3626},
  {"key": "Tabacal-Colombia_2", "n": "Tabacal", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [10.464, -75.282], "ey": 1693, "ly": 1694, "p": 3625},
  {"key": "Sonso-Colombia", "n": "Sonso", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.79972, -76.30652], "ey": 1850, "ly": 2018, "p": 3624},
  {"key": "Tintorero-Venezuela", "n": "Tintorero", "c": "Venezuela", "r": "ven_lara", "ll": [9.95218, -69.55944], "ey": 1850, "ly": 2025, "p": 3624},
  {"key": "Rocchacc-Peru", "n": "Rocchacc", "c": "Peru", "r": "per_apurimac", "ll": [-13.44056, -73.6], "ey": 1850, "ly": 2025, "p": 3624},
  {"key": "Alejo Ledesma-Argentina", "n": "Alejo Ledesma", "c": "Argentina", "r": "arg_cordoba", "ll": [-33.60547, -62.62601], "ey": 1850, "ly": 2022, "p": 3624},
  {"key": "Sierra Parima-Venezuela", "n": "Sierra Parima", "c": "Venezuela", "r": "ven_amazonas", "ll": [2.54589, -64.14689], "ey": 1920, "ly": 2025, "p": 3623},
  {"key": "Telimbela-Ecuador", "n": "Telimbela", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.68667, -79.19749], "ey": 1850, "ly": 2025, "p": 3623},
  {"key": "Geoglífos de Sacramento Reloj Solar-Peru", "n": "Geoglífos de Sacramento Reloj Solar", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.52518, -75.19281], "ey": -451, "ly": 1530, "p": 3622, "al": ["cerro mollake", "la cresta de sacramento", "pernil alto"]},
  {"key": "Las Catitas-Argentina", "n": "Las Catitas", "c": "Argentina", "r": "arg_mendoza", "ll": [-33.29386, -68.04861], "ey": 1850, "ly": 2010, "p": 3621},
  {"key": "Laguna Rali Co-Argentina", "n": "Laguna Rali Co", "c": "Argentina", "r": "sc_pampas_salado_colorado", "ll": [-34.8337, -64.8165], "ey": -2250, "ly": 1500, "p": 3621},
  {"key": "Once De Noviembre-Ecuador", "n": "Once De Noviembre", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-0.91892, -78.66768], "ey": 1850, "ly": 2025, "p": 3618},
  {"key": "Checua I-Colombia", "n": "Checua I", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.12333, -73.87194], "ey": 500, "ly": 1500, "p": 3617, "al": ["rasgatá", "Rasgatá"]},
  {"key": "Chicán-Ecuador", "n": "Chicán", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.81422, -78.7531], "ey": 1850, "ly": 2025, "p": 3616},
  {"key": "Gebe-Venezuela", "n": "Gebe", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [11.05, -70.086], "ey": 1538, "ly": 1830, "p": 3616},
  {"key": "Calabazo ( incl. Las Colinas de Calabazo )-Colombia", "n": "Calabazo ( incl. Las Colinas de Calabazo )", "c": "Colombia", "r": "col_magdalena", "ll": [11.28498, -74.00325], "ey": 1525, "ly": 2018, "p": 3615, "al": ["calabazo", "Calabazo"]},
  {"key": "Pampa de Layagache-Peru", "n": "Pampa de Layagache", "c": "Peru", "r": "inca_collasuyu", "ll": [-17.90545, -70.37962], "ey": 1440, "ly": 1532, "p": 3615, "al": ["quebrada honda", "restos de escalinata", "Quebrada Honda"]}
]

HEADERS = {"User-Agent": "SVEA-Toponymy-Research/1.0"}

def fetch_json(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=10) as resp:
    return json.loads(resp.read().decode("utf-8"))

def query_wiki(lang, query):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&srlimit=3&format=json"
  return fetch_json(url).get("query", {}).get("search", [])

def geosearch_wiki(lang, lat, lng):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=3&format=json"
  return fetch_json(url).get("query", {}).get("geosearch", [])

def get_extract(lang, pageid):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=false&explaintext=true&exchars=4000&pageids={pageid}&format=json"
  pages = fetch_json(url).get("query", {}).get("pages", {})
  p = pages.get(str(pageid), {})
  return {"title": p.get("title"), "extract": p.get("extract", "")[:3500]}

def process_item(item):
  key = item["key"]
  n = item["n"]
  c = item["c"]
  lat, lng = item["ll"]
  res = {"key": key, "es": [], "en": [], "geo_es": []}
  try:
    geo = geosearch_wiki("es", lat, lng)
    res["geo_es"] = [{"title": g["title"], "dist": g["dist"]} for g in geo]
  except Exception as e:
    res["geo_err"] = str(e)
  try:
    sr = query_wiki("es", f"{n} {c}")
    for s in sr[:2]:
      res["es"].append(get_extract("es", s["pageid"]))
  except Exception as e:
    res["es_err"] = str(e)
  return res

def main():
  out = {}
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for r in ex.map(process_item, ITEMS):
      out[r["key"]] = r
  with open("tests/wiki_046.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
  print("Done:", len(out))

if __name__ == "__main__":
  main()
