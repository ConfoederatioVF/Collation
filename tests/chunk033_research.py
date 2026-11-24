import json
import os
import time
import math
import urllib.request
import urllib.parse
import concurrent.futures

INPUT = [
  {"key": "La Esmeralda-Colombia_2", "n": "La Esmeralda", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.03, -74.96], "ey": -855, "ly": 974, "p": 4995, "al": ["uf4 yacimiento bocas de lemayá", "uf4 yacimiento la esmeralda", "UF4 Yacimiento Bocas de Lemayá"]},
  {"key": "Las Ollas-Argentina", "n": "Las Ollas", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.24792, -64.43868], "ey": 80, "ly": 1500, "p": 4994},
  {"key": "Sinsacate-Argentina", "n": "Sinsacate", "c": "Argentina", "r": "arg_cordoba", "ll": [-30.94285, -64.09397], "ey": 1536, "ly": 2022, "p": 4992},
  {"key": "Barabara-Venezuela", "n": "Barabara", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [11.342, -68.975], "ey": 1538, "ly": 1830, "p": 4992},
  {"key": "Pacocha-Peru", "n": "Pacocha", "c": "Peru", "r": "per_moquegua", "ll": [-17.61083, -71.34028], "ey": 1850, "ly": 2025, "p": 4991, "al": ["pueblo nuevo", "Pueblo Nuevo"]},
  {"key": "Vichuquén-Chile", "n": "Vichuquén", "c": "Chile", "r": "chl_region_del_maule", "ll": [-34.82954, -72.00987], "ey": 1850, "ly": 2025, "p": 4991, "al": ["vichuquen"]},
  {"key": "Paraíso de San José-Venezuela", "n": "Paraíso de San José", "c": "Venezuela", "r": "ven_lara", "ll": [9.80517, -69.50698], "ey": 1850, "ly": 2025, "p": 4989},
  {"key": "Cochamó-Chile", "n": "Cochamó", "c": "Chile", "r": "chl_region_de_los_lagos", "ll": [-41.75191, -72.19424], "ey": 1850, "ly": 2025, "p": 4987},
  {"key": "La Gabarra-Colombia", "n": "La Gabarra", "c": "Colombia", "r": "col_norte_de_santander", "ll": [8.99726, -72.89728], "ey": 1850, "ly": 2018, "p": 4986},
  {"key": "Charape-Peru", "n": "Charape", "c": "Peru", "r": "per_cajamarca", "ll": [-5.3274, -79.1215], "ey": 1525, "ly": 2017, "p": 4986},
  {"key": "Kuntursenka-Peru", "n": "Kuntursenka", "c": "Peru", "r": "inca_collasuyu", "ll": [-13.67449, -71.51573], "ey": 1000, "ly": 1530, "p": 4986, "al": ["cerro atocctocclla", "llaulicancha", "pichiumarca"]},
  {"key": "San Lucas-Ecuador", "n": "San Lucas", "c": "Ecuador", "r": "ecu_loja", "ll": [-3.75305, -79.24415], "ey": 1850, "ly": 2025, "p": 4983},
  {"key": "Camarones-Chile_2", "n": "Camarones", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.015, -69.861], "ey": 1525, "ly": 1825, "p": 4982},
  {"key": "Mucuchies-Venezuela", "n": "Mucuchies", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [8.748, -70.921], "ey": 600, "ly": 1830, "p": 4980, "al": ["mucuchíes", "timoto-cuica", "Timoto-Cuica"]},
  {"key": "Tablazo Norte (tablazo)-Peru", "n": "Tablazo Norte (tablazo)", "c": "Peru", "r": "per_piura", "ll": [-5.3808, -80.7625], "ey": 1850, "ly": 2017, "p": 4979, "al": ["tablazo norte", "tablazo sur", "Tablazo Sur"]},
  {"key": "Colonia El Simbolar-Argentina", "n": "Colonia El Simbolar", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-27.72481, -63.86288], "ey": 1850, "ly": 2022, "p": 4979},
  {"key": "Laguna Empedrada-Peru", "n": "Laguna Empedrada", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.68458, -77.49033], "ey": -2000, "ly": 1532, "p": 4976, "al": ["puerta de monte", "cerro central", "ciudadela y fortaleza del gran pajatén"]},
  {"key": "El algarrobal de Moro-Peru", "n": "El algarrobal de Moro", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.1711, -79.42165], "ey": 1438, "ly": 1530, "p": 4970, "al": ["alg. moro", "huaca guanilo", "huaca huerta"]},
  {"key": "Nelson-Argentina", "n": "Nelson", "c": "Argentina", "r": "arg_santa_fe", "ll": [-31.2677, -60.76206], "ey": 1850, "ly": 2022, "p": 4969},
  {"key": "La Margarita-Colombia_2", "n": "La Margarita", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [3.76, -76.38], "ey": 862, "ly": 1500, "p": 4968, "al": ["el jordán", "guabas", "El Jordán"]},
  {"key": "Los Laureles-Chile_2", "n": "Los Laureles", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-36.83282, -72.12598], "ey": 0, "ly": 1500, "p": 4967},
  {"key": "Soledad-Argentina", "n": "Soledad", "c": "Argentina", "r": "arg_santa_fe", "ll": [-30.61953, -60.91457], "ey": 1793, "ly": 2022, "p": 4964, "al": ["arredondo", "Arredondo"]},
  {"key": "Colaisaca-Ecuador", "n": "Colaisaca", "c": "Ecuador", "r": "ecu_loja", "ll": [-4.244, -79.68256], "ey": 1525, "ly": 2025, "p": 4963, "al": ["colaisacapi", "Colaisacapi"]},
  {"key": "Pacobamba-Peru", "n": "Pacobamba", "c": "Peru", "r": "per_apurimac", "ll": [-13.61528, -73.08389], "ey": 1850, "ly": 2025, "p": 4961},
  {"key": "Isinlivi-Ecuador", "n": "Isinlivi", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-0.78143, -78.85611], "ey": 1525, "ly": 2025, "p": 4960, "al": ["ysinlihui", "Ysinlihui"]},
  {"key": "Uia (na_magdalena_cauca_muisca)-Colombia", "n": "Uia", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.35958, -74.41776], "ey": 1300, "ly": 1500, "p": 4957},
  {"key": "Qenqoraqay-Peru", "n": "Qenqoraqay", "c": "Peru", "r": "inca_antisuyu", "ll": [-13.4988, -71.78017], "ey": 500, "ly": 1530, "p": 4955, "al": ["q'enqo raqay", "Q'enqo Raqay"]},
  {"key": "Cayastá-Argentina", "n": "Cayastá", "c": "Argentina", "r": "arg_santa_fe", "ll": [-31.19867, -60.15938], "ey": 1850, "ly": 2022, "p": 4951},
  {"key": "Enciso-Colombia", "n": "Enciso", "c": "Colombia", "r": "col_santander", "ll": [6.66803, -72.69965], "ey": 1773, "ly": 2025, "p": 4950, "al": ["llano de enciso", "Llano de Enciso"]},
  {"key": "Pomacancha-Peru_2", "n": "Pomacancha", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.736, -76.27], "ey": 1525, "ly": 1825, "p": 4949},
  {"key": "Santa Rosa del Rio Primero-Argentina", "n": "Santa Rosa del Rio Primero", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-31.153, -63.399], "ey": 1536, "ly": 1830, "p": 4948, "al": ["chamasacate", "rio de cordoba", "Chamasacate"]},
  {"key": "Polígono Tolú-Colombia", "n": "Polígono Tolú", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [9.50811, -75.58769], "ey": 1300, "ly": 1500, "p": 4946},
  {"key": "Almafuerte Sitio-Argentina", "n": "Almafuerte Sitio", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.19136, -64.25577], "ey": 80, "ly": 1500, "p": 4945},
  {"key": "Ocros (per_ancash)-Peru", "n": "Ocros", "c": "Peru", "r": "per_ancash", "ll": [-10.40333, -77.39667], "ey": 1525, "ly": 2025, "p": 4943},
  {"key": "Almafuerte-Argentina_2", "n": "Almafuerte", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.1585, -64.24557], "ey": 80, "ly": 1500, "p": 4943, "al": ["piedras moras"]},
  {"key": "Pantoño-Venezuela", "n": "Pantoño", "c": "Venezuela", "r": "ven_sucre", "ll": [10.51556, -63.575], "ey": 1850, "ly": 2011, "p": 4939},
  {"key": "Bowen-Argentina", "n": "Bowen", "c": "Argentina", "r": "arg_mendoza", "ll": [-35.00042, -67.51046], "ey": 1850, "ly": 2010, "p": 4939},
  {"key": "Calzada-Peru", "n": "Calzada", "c": "Peru", "r": "per_san_martin", "ll": [-6.03028, -77.06667], "ey": 1900, "ly": 2025, "p": 4938},
  {"key": "Fundición-Peru", "n": "Fundición", "c": "Peru", "r": "inca_contisuyu", "ll": [-17.60721, -71.24302], "ey": 1438, "ly": 1530, "p": 4938, "al": ["chiribaya baja", "el algodonal", "el descanso"]},
  {"key": "Huata-Peru_2", "n": "Huata", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.3598, -76.80832], "ey": 0, "ly": 1530, "p": 4937, "al": ["antarraga", "arqueológico jocoto machay", "callashirca"]},
  {"key": "Sauce (ury_rio_negro)-Uruguay", "n": "Sauce", "c": "Uruguay", "r": "ury_rio_negro", "ll": [-32.90179, -57.73823], "ey": 1900, "ly": 2023, "p": 4932},
  {"key": "Costa Rica-Colombia", "n": "Costa Rica", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.75178, -76.23411], "ey": 1850, "ly": 2018, "p": 4931},
  {"key": "Villa Unión-Argentina", "n": "Villa Unión", "c": "Argentina", "r": "arg_la_rioja", "ll": [-29.31776, -68.22776], "ey": 1850, "ly": 2010, "p": 4931},
  {"key": "Cocaniguas-Ecuador", "n": "Cocaniguas", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-0.115, -78.953], "ey": 1525, "ly": 1830, "p": 4928},
  {"key": "Cruzorqo-Peru", "n": "Cruzorqo", "c": "Peru", "r": "inca_collasuyu", "ll": [-15.71255, -70.21291], "ey": 1300, "ly": 1530, "p": 4925, "al": ["alqamarine", "cerro calvario", "jich´"]},
  {"key": "Pambay-Ecuador", "n": "Pambay", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-1.4693, -78.0035], "ey": -1593, "ly": -693, "p": 4925},
  {"key": "Santa Ana (col_bolivar)-Colombia", "n": "Santa Ana", "c": "Colombia", "r": "col_bolivar", "ll": [10.2389, -75.55575], "ey": 1774, "ly": 2018, "p": 4923, "al": ["santa ana de baru", "Santa Ana de Baru"]},
  {"key": "Cinto-Peru", "n": "Cinto", "c": "Peru", "r": "inca_collasuyu", "ll": [-17.51044, -70.71353], "ey": -2000, "ly": 1530, "p": 4921},
  {"key": "Punto (na_magdalena_cauca_muisca)-Colombia", "n": "Punto", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [3.39, -76.35], "ey": 831, "ly": 1500, "p": 4921},
  {"key": "Garmendia-Argentina", "n": "Garmendia", "c": "Argentina", "r": "arg_tucuman", "ll": [-26.57412, -64.55867], "ey": 1850, "ly": 2022, "p": 4920},
  {"key": "San Fernando Chile-Chile", "n": "San Fernando Chile", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-34.584, -70.989], "ey": 1742, "ly": 1813, "p": 4920, "ex": [{"date": "1865.1.1", "name": "San Fernando"}], "al": ["san fernando de tinguiririca", "san fernando el real", "San Fernando de Tinguiririca"]},
  {"key": "En Proceso (inca_chinchaysuyu_6)-Peru", "n": "En Proceso", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.4847, -77.81333], "ey": 600, "ly": 1532, "p": 4920, "al": ["casa redonda", "la jalca grande", "ollape"]},
  {"key": "La Chokta-Peru", "n": "La Chokta", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.08688, -78.03974], "ey": -1000, "ly": 1530, "p": 4920, "al": ["cerro el callejon", "cerro tinajas", "la conga"]},
  {"key": "Santa Maria de Los Lagos-Chile", "n": "Santa Maria de Los Lagos", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.85319, -72.72986], "ey": 1000, "ly": 1500, "p": 4915, "ex": [{"date": "1950.1.1", "name": "Los Lagos"}]},
  {"key": "Pampa Blanca-Argentina", "n": "Pampa Blanca", "c": "Argentina", "r": "arg_jujuy", "ll": [-24.53522, -65.07181], "ey": 1850, "ly": 2022, "p": 4907},
  {"key": "Chivor-Colombia", "n": "Chivor", "c": "Colombia", "r": "col_cundinamarca", "ll": [4.88817, -73.3684], "ey": 1850, "ly": 2025, "p": 4904},
  {"key": "Santo Tomas de Pata-Peru", "n": "Santo Tomas de Pata", "c": "Peru", "r": "per_huancavelica", "ll": [-13.11306, -74.41889], "ey": 1525, "ly": 2025, "p": 4903, "al": ["pata", "santo tomás de pata", "Pata"]},
  {"key": "Alcalá-Bolivia", "n": "Alcalá", "c": "Bolivia", "r": "bol_chuquisaca", "ll": [-19.36753, -64.39105], "ey": 1750, "ly": 2024, "p": 4902, "al": ["alcala", "Alcala"]},
  {"key": "Yacimiento 1. Raíz arbol-Colombia", "n": "Yacimiento 1. Raíz arbol", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.33823, -74.69124], "ey": -1000, "ly": 1500, "p": 4901, "al": ["yacimiento", "Yacimiento"]},
  {"key": "Margarita-Argentina", "n": "Margarita", "c": "Argentina", "r": "arg_santa_fe", "ll": [-29.69249, -60.25222], "ey": 1850, "ly": 2022, "p": 4900},
  {"key": "Pacarní-Colombia", "n": "Pacarní", "c": "Colombia", "r": "col_huila", "ll": [2.60843, -75.69836], "ey": 1525, "ly": 2018, "p": 4899, "al": ["pacarni", "Pacarni"]},
  {"key": "Puerto Cayo-Ecuador", "n": "Puerto Cayo", "c": "Ecuador", "r": "ecu_manabi", "ll": [-1.32359, -80.70451], "ey": 1850, "ly": 2025, "p": 4897},
  {"key": "Umamac-Argentina", "n": "Umamac", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.677, -63.597], "ey": 1536, "ly": 1830, "p": 4893, "al": ["umama", "umamaq", "Umama"]},
  {"key": "Charapaya-Bolivia", "n": "Charapaya", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.369, -66.755], "ey": 1525, "ly": 1825, "p": 4892, "al": ["palca chiquito", "Palca chiquito"]},
  {"key": "Jama-Ecuador_2", "n": "Jama", "c": "Ecuador", "r": "na_pacific_equatorial_valdivia", "ll": [-0.203, -80.264], "ey": -400, "ly": 1400, "p": 4890, "al": ["jama-coaque", "Jama-Coaque"]},
  {"key": "San Roque Cañaverales-Colombia", "n": "San Roque Cañaverales", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [7.55, -73.544], "ey": 1525, "ly": 1830, "p": 4889, "al": ["puerto de botijas", "Puerto de Botijas"]},
  {"key": "Chalán-Colombia", "n": "Chalán", "c": "Colombia", "r": "col_sucre", "ll": [9.54535, -75.3127], "ey": 1850, "ly": 2025, "p": 4888},
  {"key": "Corpus-Argentina", "n": "Corpus", "c": "Argentina", "r": "arg_misiones", "ll": [-27.1278, -55.50942], "ey": 1622, "ly": 2010, "p": 4887},
  {"key": "San Diego de Alcala de la Sabana de Ocumare del Tuy-Venezuela", "n": "San Diego de Alcala de la Sabana de Ocumare del Tuy", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [10.115, -66.778], "ey": 1538, "ly": 1830, "p": 4887, "ex": [{"date": "1921.1.1", "name": "Ocumare del Tuy"}]},
  {"key": "Carlos Julio Arosemena Tola-Ecuador", "n": "Carlos Julio Arosemena Tola", "c": "Ecuador", "r": "ecu_napo", "ll": [-1.16859, -77.93139], "ey": 1850, "ly": 2025, "p": 4885},
  {"key": "El Maitén-Argentina", "n": "El Maitén", "c": "Argentina", "r": "arg_rio_negro", "ll": [-42.05031, -71.16779], "ey": 1900, "ly": 2022, "p": 4885},
  {"key": "Sotoca-Chile", "n": "Sotoca", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.583, -69.201], "ey": 1525, "ly": 1825, "p": 4883, "al": ["satoca", "Satoca"]},
  {"key": "La Aguadita-Argentina", "n": "La Aguadita", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.77751, -64.67521], "ey": 80, "ly": 1500, "p": 4882},
  {"key": "Pulan-Peru", "n": "Pulan", "c": "Peru", "r": "per_cajamarca", "ll": [-6.73889, -78.92028], "ey": 1850, "ly": 2025, "p": 4881, "al": ["pulán", "Pulán"]},
  {"key": "Río San Juan-Colombia", "n": "Río San Juan", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.44, -74.23], "ey": 811, "ly": 1500, "p": 4880},
  {"key": "Boyacá-Ecuador", "n": "Boyacá", "c": "Ecuador", "r": "ecu_manabi", "ll": [-0.53787, -80.16201], "ey": 1850, "ly": 2025, "p": 4879},
  {"key": "Hualcas I-Peru", "n": "Hualcas I", "c": "Peru", "r": "per_piura", "ll": [-5.5116, -79.7065], "ey": 0, "ly": 2017, "p": 4879, "al": ["hualcas", "paur", "Hualcas"]},
  {"key": "La Dormida-Argentina_2", "n": "La Dormida", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-30.354, -63.949], "ey": 1536, "ly": 1830, "p": 4879},
  {"key": "Chiribaya Alta-Peru", "n": "Chiribaya Alta", "c": "Peru", "r": "inca_contisuyu", "ll": [-17.63201, -71.29556], "ey": 900, "ly": 1530, "p": 4879, "al": ["curuhuas", "la cara", "petroglífos de canicora"]},
  {"key": "Cicasos-Peru", "n": "Cicasos", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.36052, -76.704], "ey": 0, "ly": 1530, "p": 4876, "al": ["los cicasos", "no registrado", "quebrada cruz de hueso a"]},
  {"key": "La Luz-Venezuela", "n": "La Luz", "c": "Venezuela", "r": "ven_barinas", "ll": [8.39556, -69.82389], "ey": 1538, "ly": 2025, "p": 4874},
  {"key": "Central Queneque-Peru", "n": "Central Queneque", "c": "Peru", "r": "per_puno", "ll": [-14.2791, -69.4477], "ey": 1525, "ly": 2017, "p": 4874, "al": ["alto queneque", "queneque", "ura queneque"]},
  {"key": "Pulido Méndez-Venezuela", "n": "Pulido Méndez", "c": "Venezuela", "r": "ven_merida", "ll": [8.62389, -71.61944], "ey": 1850, "ly": 2025, "p": 4871},
  {"key": "Páez (col_boyaca)-Colombia", "n": "Páez", "c": "Colombia", "r": "col_boyaca", "ll": [5.09732, -73.05274], "ey": 1850, "ly": 2025, "p": 4870},
  {"key": "Membrillo-Ecuador", "n": "Membrillo", "c": "Ecuador", "r": "ecu_manabi", "ll": [-0.8715, -79.95263], "ey": 1850, "ly": 2025, "p": 4870},
  {"key": "General Lavalle-Argentina", "n": "General Lavalle", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-36.40635, -56.94324], "ey": 1850, "ly": 2022, "p": 4870},
  {"key": "Loc-Colombia", "n": "Loc", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.35143, -74.49296], "ey": 1300, "ly": 1500, "p": 4868},
  {"key": "Güéjar-Colombia", "n": "Güéjar", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [3.47844, -73.7542], "ey": 500, "ly": 1500, "p": 4867},
  {"key": "Rio Seco-Peru", "n": "Rio Seco", "c": "Peru", "r": "per_piura", "ll": [-5.1386, -80.6148], "ey": 1850, "ly": 2017, "p": 4865, "al": ["los ejidos del norte", "Los Ejidos del Norte"]},
  {"key": "Alero el Verano-Argentina", "n": "Alero el Verano", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-48.7116, -69.1919], "ey": -8234, "ly": -5655, "p": 4864}
]

GAZ_PATHS = [
  "histmap/1.data_raw/population_regional/QUIPU/1.pre_columbian/1.pre_columbian_northern_andes/pre_columbian_northern_andes_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/1.pre_columbian/2.pre_columbian_central_andes/pre_columbian_central_andes_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/1.pre_columbian/3.inca_empire_tawantinsuyu/inca_empire_tawantinsuyu_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/1.pre_columbian/4.pre_columbian_southern_cone/pre_columbian_southern_cone_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/2.colonial/1.spanish_conquest_andes_collapse/spanish_conquest_andes_collapse_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/2.colonial/2.viceroyalty_peru_upper_peru/viceroyalty_peru_upper_peru_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/2.colonial/3.viceroyalty_new_granada/viceroyalty_new_granada_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/2.colonial/4.chile_rio_plata_banda_oriental/chile_rio_plata_banda_oriental_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/3.post_independence/1.colombia_after_independence/colombia_after_independence_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/3.post_independence/2.venezuela_after_independence/venezuela_after_independence_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/3.post_independence/3.ecuador_after_independence/ecuador_after_independence_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/3.post_independence/4.peru_after_independence/peru_after_independence_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/3.post_independence/5.andean_bolivia_independence/andean_bolivia_independence_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/3.post_independence/6.chile_after_independence/chile_after_independence_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/3.post_independence/7.argentina_after_independence/argentina_after_independence_settlements.json",
  "histmap/1.data_raw/population_regional/QUIPU/3.post_independence/8.uruguay_after_independence/uruguay_after_independence_settlements.json",
]

def load_gaz_matches():
    by_region = {}
    for item in INPUT:
        by_region.setdefault(item['r'], []).append(item)
    matches = {item['key']: [] for item in INPUT}
    for p in GAZ_PATHS:
        if not os.path.exists(p):
            continue
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            continue
        for region_key, region_val in data.items():
            if not isinstance(region_val, dict):
                continue
            for sname, sdata in region_val.items():
                if not isinstance(sdata, dict):
                    continue
                coords = sdata.get('coords') or sdata.get('ll')
                if not coords or len(coords) != 2:
                    continue
                slat, slng = float(coords[0]), float(coords[1])
                for item in INPUT:
                    ilat, ilng = item['ll']
                    if abs(slat - ilat) < 0.015 and abs(slng - ilng) < 0.015:
                        info = {
                            'gaz': os.path.basename(p),
                            'region_key': region_key,
                            'entry_name': sname,
                            'coords': coords,
                            'source': sdata.get('source'),
                            'sources': sdata.get('sources'),
                            'notes': sdata.get('notes'),
                            'note': sdata.get('note'),
                            'description': sdata.get('description'),
                            'alt_names': sdata.get('alt_names') or sdata.get('other_names'),
                            'years': sorted([int(k) for k in sdata.keys() if k.lstrip('-').isdigit()])[:5]
                        }
                        # remove None
                        info = {k: v for k, v in info.items() if v is not None}
                        matches[item['key']].append(info)
    return matches

HEADERS = {'User-Agent': 'SVEA-Research/1.0 (https://confoederatio.org)'}

def fetch_json(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt == 3:
                raise
            time.sleep(0.5)
    return {}

def wiki_lookup(item):
    lat, lng = item['ll']
    name = item['n']
    country = item['c']
    res = {'key': item['key'], 'n': name, 'c': country, 'r': item['r'], 'll': item['ll'], 'ey': item['ey'], 'ly': item['ly']}
    if 'ex' in item:
        res['ex'] = item['ex']
    if 'al' in item:
        res['al'] = item['al']
    try:
        geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        geo = fetch_json(geo_url).get('query', {}).get('geosearch', [])
        res['es_geo'] = [{'title': g['title'], 'dist': g['dist']} for g in geo]
    except Exception as e:
        res['es_geo_err'] = str(e)

    try:
        clean_name = name.split('(')[0].strip()
        q = urllib.parse.quote(f"{clean_name} {country}")
        sr_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sr = fetch_json(sr_url).get('query', {}).get('search', [])
        res['es_search'] = [{'title': s['title'], 'snippet': s['snippet']} for s in sr]
    except Exception as e:
        res['es_search_err'] = str(e)

    # Pick best titles to fetch extract (first 2500 chars)
    titles = []
    for g in res.get('es_geo', [])[:2]:
        if g['title'] not in titles:
            titles.append(g['title'])
    for s in res.get('es_search', [])[:2]:
        if s['title'] not in titles:
            titles.append(s['title'])
    if titles:
        try:
            t_param = urllib.parse.quote('|'.join(titles[:3]))
            ext_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exchars=2000&titles={t_param}&format=json"
            pages = fetch_json(ext_url).get('query', {}).get('pages', {})
            res['es_extracts'] = {p.get('title'): p.get('extract', '') for p in pages.values() if p.get('extract')}
        except Exception as e:
            res['es_ext_err'] = str(e)
    time.sleep(0.05)
    return res

if __name__ == '__main__':
    print("Loading local QUIPU gazetteer matches...")
    gaz_matches = load_gaz_matches()
    print(f"Found local matches for {sum(1 for v in gaz_matches.values() if v)}/{len(INPUT)} items")
    print("Querying es.wikipedia.org...")
    wiki_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        for r in ex.map(wiki_lookup, INPUT):
            r['gaz_matches'] = gaz_matches.get(r['key'], [])
            wiki_results[r['key']] = r
    out_path = 'tests/chunk033_digest.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(wiki_results, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(wiki_results)} items to {out_path}")
