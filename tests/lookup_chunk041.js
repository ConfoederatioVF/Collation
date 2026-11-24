const fs = require("fs");
const JSON5 = require("json5");

const input = [
  {"key": "Cerro Redondo-Peru", "n": "Cerro Redondo", "c": "Peru", "r": "inca_contisuyu", "ll": [-17.75354, -71.17749], "ey": -2000, "ly": 1530, "p": 4128, "al": ["loma mostazal", "s.a. lomas de ilo", "pampa el palo"]},
  {"key": "Chadin-Peru", "n": "Chadin", "c": "Peru", "r": "per_cajamarca", "ll": [-6.47139, -78.41944], "ey": 1850, "ly": 2025, "p": 4124, "al": ["chadín", "Chadín"]},
  {"key": "Arcadis de la Esperanza-Chile", "n": "Arcadis de la Esperanza", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.0118, -70.0406], "ey": -3000, "ly": 1500, "p": 4124},
  {"key": "Laguna del-Argentina", "n": "Laguna del", "c": "Argentina", "r": "sc_pampas_salado_colorado", "ll": [-34.7413, -64.6887], "ey": -2250, "ly": 1500, "p": 4124},
  {"key": "Cayastá Chaná-Timbú-Argentina", "n": "Cayastá Chaná-Timbú", "c": "Argentina", "r": "sc_gran_chaco_pilcomayo", "ll": [-31.202, -60.163], "ey": 700, "ly": 1450, "p": 4120},
  {"key": "Iskanwaya-Bolivia", "n": "Iskanwaya", "c": "Bolivia", "r": "ca_titicaca_altiplano_tiwanaku", "ll": [-15.468, -68.764], "ey": 1100, "ly": 1430, "p": 4120, "al": ["mollo", "Mollo"]},
  {"key": "Voyaverla KM 2+-Colombia", "n": "Voyaverla KM 2+", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [9.46, -74.99], "ey": 811, "ly": 1500, "p": 4118},
  {"key": "Amuay-Venezuela", "n": "Amuay", "c": "Venezuela", "r": "ven_falcon", "ll": [11.78097, -70.23848], "ey": 1850, "ly": 2011, "p": 4116},
  {"key": "Culluay-Peru", "n": "Culluay", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.317, -76.55], "ey": 1525, "ly": 1825, "p": 4116},
  {"key": "Churuguara-Venezuela", "n": "Churuguara", "c": "Venezuela", "r": "ven_falcon", "ll": [10.81556, -69.53667], "ey": 1850, "ly": 2025, "p": 4113},
  {"key": "Santiago Berenguela-Bolivia", "n": "Santiago Berenguela", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.891, -66.418], "ey": 1525, "ly": 1825, "p": 4113},
  {"key": "Waqrapukara-Peru", "n": "Waqrapukara", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.01972, -71.69242], "ey": 0, "ly": 1530, "p": 4113, "al": ["llaqtapukara", "Llaqtapukara"]},
  {"key": "Perinao-Ecuador", "n": "Perinao", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-1.3, -80], "ey": -3146, "ly": -2190, "p": 4113, "al": ["el carmen", "El Carmen"]},
  {"key": "Chapadmalal-Argentina", "n": "Chapadmalal", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-38.1765, -57.65202], "ey": 1850, "ly": 2010, "p": 4112},
  {"key": "Posada del Parque-Chile", "n": "Posada del Parque", "c": "Chile", "r": "inca_collasuyu", "ll": [-32.88181, -71.49567], "ey": -300, "ly": 1500, "p": 4108, "al": ["mantagua", "Mantagua"]},
  {"key": "Astu Raqall-Peru", "n": "Astu Raqall", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.25943, -74.15122], "ey": 1438, "ly": 1530, "p": 4107, "al": ["potro sillana", "qatunushnu", "qera ccasa"]},
  {"key": "Pimpingos-Peru_2", "n": "Pimpingos", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-5.928, -78.843], "ey": 1525, "ly": 1830, "p": 4105, "al": ["pimpicos", "pinpicos", "Pimpicos"]},
  {"key": "San Rafael de Las Guasduas-Venezuela", "n": "San Rafael de Las Guasduas", "c": "Venezuela", "r": "ven_portuguesa", "ll": [9.14889, -69.605], "ey": 1748, "ly": 2011, "p": 4100, "al": ["san rafael guasguas", "San Rafael Guasguas"]},
  {"key": "Casa de Piedra de Ortega-Argentina", "n": "Casa de Piedra de Ortega", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-40.73028, -70.70583], "ey": -5002, "ly": 530, "p": 4099},
  {"key": "Totorilla-Argentina", "n": "Totorilla", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.90376, -64.36182], "ey": 80, "ly": 1500, "p": 4098},
  {"key": "La Pedrera-Colombia", "n": "La Pedrera", "c": "Colombia", "r": "col_vaupes", "ll": [-1.3203, -69.5855], "ey": 1900, "ly": 2025, "p": 4097},
  {"key": "Gotumarca-Peru", "n": "Gotumarca", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.78934, -76.84711], "ey": 500, "ly": 1530, "p": 4097, "al": ["arqueológico quinaya", "arqueológico toldorum", "mesapata"]},
  {"key": "Cruce San Martin de Porres (el Cruce)-Peru", "n": "Cruce San Martin de Porres (el Cruce)", "c": "Peru", "r": "per_la_libertad", "ll": [-7.3327, -79.4829], "ey": 1850, "ly": 2017, "p": 4095, "al": ["cruce san martin de porres"]},
  {"key": "Villcabamba-Bolivia", "n": "Villcabamba", "c": "Bolivia", "r": "bol_cochabamba", "ll": [-17.86966, -66.19085], "ey": 1525, "ly": 2024, "p": 4094, "al": ["vilcabamba"]},
  {"key": "San Pedro (chl_region_de_valparaiso)-Chile", "n": "San Pedro", "c": "Chile", "r": "chl_region_de_valparaiso", "ll": [-32.93761, -71.27626], "ey": 1850, "ly": 2017, "p": 4093, "al": ["cajón de san pedro", "Cajón de San Pedro"]},
  {"key": "Lipiche alero-Chile", "n": "Lipiche alero", "c": "Chile", "r": "inca_collasuyu", "ll": [-18.08144, -69.23156], "ey": -1587, "ly": 1532, "p": 4093},
  {"key": "San Jeronimo Mamatoco-Colombia", "n": "San Jeronimo Mamatoco", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [11.228, -74.167], "ey": 1525, "ly": 1830, "p": 4092},
  {"key": "Huaca La tuna-Peru", "n": "Huaca La tuna", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-13.06328, -76.34455], "ey": 500, "ly": 1530, "p": 4092, "al": ["huaca las ánimas", "san antonio", "hacienda montalvan"]},
  {"key": "Pueblo Nuevo (col_magdalena)-Colombia", "n": "Pueblo Nuevo", "c": "Colombia", "r": "col_magdalena", "ll": [9.90571, -74.10156], "ey": 1850, "ly": 2018, "p": 4091},
  {"key": "Serodino-Argentina", "n": "Serodino", "c": "Argentina", "r": "arg_santa_fe", "ll": [-32.60373, -60.94743], "ey": 1850, "ly": 2022, "p": 4090},
  {"key": "Minguimalo-Colombia", "n": "Minguimalo", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [4.89867, -76.8178], "ey": 509, "ly": 1500, "p": 4089},
  {"key": "Taravita-Bolivia", "n": "Taravita", "c": "Bolivia", "r": "crp_gran_chaco_frontier", "ll": [-19.934, -64.484], "ey": 1525, "ly": 1830, "p": 4088, "al": ["taraita", "tarayta", "Taraita"]},
  {"key": "Las Margaritas Sitio-Colombia", "n": "Las Margaritas Sitio", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.82469, -75.80448], "ey": 1300, "ly": 1500, "p": 4087},
  {"key": "San José De Chaltura-Ecuador", "n": "San José De Chaltura", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.3666, -78.19371], "ey": 1850, "ly": 2025, "p": 4086},
  {"key": "Pampa Rampal-Peru", "n": "Pampa Rampal", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-4.95485, -80.89965], "ey": -2000, "ly": 1530, "p": 4081, "al": ["miraflores", "Miraflores"]},
  {"key": "Ruinas de Tapahuacho-Peru", "n": "Ruinas de Tapahuacho", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.90748, -73.39203], "ey": 1438, "ly": 1530, "p": 4081, "al": ["upahuacho de maqueta", "ñawpallaqta", "Upahuacho de Maqueta"]},
  {"key": "Media Luna-Colombia", "n": "Media Luna", "c": "Colombia", "r": "col_cesar", "ll": [10.24429, -73.14473], "ey": 1525, "ly": 2018, "p": 4080, "al": ["rosario tuerto", "Rosario Tuerto"]},
  {"key": "UIA-18. Yacimiento Arqueológico-Colombia", "n": "UIA-18. Yacimiento Arqueológico", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.93217, -73.72321], "ey": 1300, "ly": 1500, "p": 4077, "al": ["uia-17. punto de interés arqueológico", "UIA-17. Punto de interés arqueológico"]},
  {"key": "Rio Vides-Colombia", "n": "Rio Vides", "c": "Colombia", "r": "na_nw_amazon_foothills", "ll": [0.9, -76.67], "ey": 500, "ly": 1500, "p": 4076, "al": ["santa teresa", "Santa Teresa"]},
  {"key": "Bocachica-Colombia", "n": "Bocachica", "c": "Colombia", "r": "col_bolivar", "ll": [10.32481, -75.58234], "ey": 1646, "ly": 2018, "p": 4075, "al": ["castillo de san fernando boca chica", "Castillo de San Fernando Boca Chica"]},
  {"key": "Río Grande-Colombia", "n": "Río Grande", "c": "Colombia", "r": "col_antioquia", "ll": [7.92901, -76.62431], "ey": 1950, "ly": 2018, "p": 4075},
  {"key": "Cerro Grande de Curgos-Peru", "n": "Cerro Grande de Curgos", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.87608, -77.95773], "ey": 500, "ly": 1530, "p": 4074, "al": ["cerro agua negra", "cerro hurtambo", "cerro la cruz"]},
  {"key": "Yambe-Ecuador", "n": "Yambe", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-0.091, -78.924], "ey": 1525, "ly": 1830, "p": 4073},
  {"key": "Puerto Nuevo-Chile_2", "n": "Puerto Nuevo", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-40.22357, -72.59706], "ey": 0, "ly": 1500, "p": 4071},
  {"key": "Trinidad de la Capilla-Venezuela", "n": "Trinidad de la Capilla", "c": "Venezuela", "r": "ven_portuguesa", "ll": [8.71842, -68.85795], "ey": 1850, "ly": 2025, "p": 4070},
  {"key": "Las Piedras-Venezuela", "n": "Las Piedras", "c": "Venezuela", "r": "ven_yaracuy", "ll": [10.09241, -69.06641], "ey": 1850, "ly": 2011, "p": 4066},
  {"key": "El Triunfo (ecu_orellana)-Ecuador", "n": "El Triunfo", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.70033, -77.31268], "ey": 1525, "ly": 2022, "p": 4066, "al": ["loreto", "Loreto"]},
  {"key": "Guasaganda-Ecuador", "n": "Guasaganda", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-0.81556, -79.13573], "ey": 1850, "ly": 2025, "p": 4066},
  {"key": "Carijana-Bolivia", "n": "Carijana", "c": "Bolivia", "r": "bol_la_paz", "ll": [-15.22234, -68.76965], "ey": 1718, "ly": 2024, "p": 4066, "al": ["carejana", "Carejana"]},
  {"key": "San Miguel-Peru_2", "n": "San Miguel", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.6935, -79.7754], "ey": -1000, "ly": 1530, "p": 4065, "al": ["de pics", "huaca abejeria", "huaca cacique"]},
  {"key": "Inclan-Peru", "n": "Inclan", "c": "Peru", "r": "per_tacna", "ll": [-17.79389, -70.49472], "ey": 1850, "ly": 2025, "p": 4064, "al": ["sama grande", "Sama Grande"]},
  {"key": "Chaclacayo-Peru", "n": "Chaclacayo", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.975, -76.783], "ey": 1525, "ly": 1825, "p": 4059, "ex": [{"date": "1961.1.1", "name": "Chaclacayo"}], "al": ["chacalacayo", "Chacalacayo"]},
  {"key": "Cueros-Peru", "n": "Cueros", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.279, -71.198], "ey": 1525, "ly": 1825, "p": 4058, "al": ["queros", "Queros"]},
  {"key": "Torre 78 RS-Colombia", "n": "Torre 78 RS", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [3.91069, -73.69022], "ey": 500, "ly": 1500, "p": 4056, "al": ["sao", "torre", "yacimiento"]},
  {"key": "El Espino-Colombia", "n": "El Espino", "c": "Colombia", "r": "col_boyaca", "ll": [6.48303, -72.49701], "ey": 1850, "ly": 2025, "p": 4055, "al": ["guacamayas", "Guacamayas"]},
  {"key": "Quinimari-Venezuela", "n": "Quinimari", "c": "Venezuela", "r": "ven_tachira", "ll": [7.50152, -72.34368], "ey": 1850, "ly": 2025, "p": 4054},
  {"key": "Verdal-Colombia", "n": "Verdal", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.47294, -74.71183], "ey": 1000, "ly": 1500, "p": 4054},
  {"key": "Casacara-Colombia", "n": "Casacara", "c": "Colombia", "r": "col_cesar", "ll": [9.83189, -73.26162], "ey": 1793, "ly": 2018, "p": 4052},
  {"key": "Tiquirpaya-Bolivia", "n": "Tiquirpaya", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.115, -66.73], "ey": 1525, "ly": 1825, "p": 4052},
  {"key": "Yascual-Colombia", "n": "Yascual", "c": "Colombia", "r": "col_narino", "ll": [1.20946, -77.64012], "ey": 1525, "ly": 2018, "p": 4051, "al": ["lasqual", "Lasqual"]},
  {"key": "Villa del Prado-Argentina", "n": "Villa del Prado", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.6203, -64.39145], "ey": 1850, "ly": 2022, "p": 4051},
  {"key": "Ruiz de Montoya-Argentina", "n": "Ruiz de Montoya", "c": "Argentina", "r": "arg_misiones", "ll": [-26.96868, -55.05318], "ey": 1900, "ly": 2022, "p": 4048},
  {"key": "Pucayacu-Peru", "n": "Pucayacu", "c": "Peru", "r": "per_huanuco", "ll": [-8.74972, -76.12111], "ey": 1850, "ly": 2025, "p": 4047},
  {"key": "Reporte HF SAR (na_orinoco_llanos_guayana)-Colombia", "n": "Reporte HF SAR", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [4.39994, -73.97333], "ey": 1000, "ly": 1500, "p": 4047},
  {"key": "Cueva de la Mesada de la Maria Quebrada-Argentina", "n": "Cueva de la Mesada de la Maria Quebrada", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-48.72831, -67.57237], "ey": -3135, "ly": -2235, "p": 4045},
  {"key": "Altos de Pindaná 66per-Colombia", "n": "Altos de Pindaná 66per", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.79545, -75.76578], "ey": 1300, "ly": 1500, "p": 4044},
  {"key": "Chupan - Llamarum-Peru", "n": "Chupan - Llamarum", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.66395, -74.8639], "ey": 1000, "ly": 1530, "p": 4043},
  {"key": "Taracoa-Ecuador", "n": "Taracoa", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.4931, -76.77622], "ey": 1920, "ly": 2025, "p": 4041},
  {"key": "Pampa Joya-Chile", "n": "Pampa Joya", "c": "Chile", "r": "inca_collasuyu", "ll": [-22.17048, -69.47344], "ey": 0, "ly": 1530, "p": 4040},
  {"key": "Pumanque-Chile", "n": "Pumanque", "c": "Chile", "r": "chl_region_del_libertador_bernardo_o_higgins", "ll": [-34.59269, -71.68184], "ey": 1525, "ly": 2025, "p": 4039},
  {"key": "Murphy-Argentina", "n": "Murphy", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.64227, -61.85841], "ey": 1850, "ly": 2022, "p": 4039},
  {"key": "Buenos Aires (per_san_martin_2)-Peru", "n": "Buenos Aires", "c": "Peru", "r": "per_san_martin", "ll": [-5.9163, -77.0797], "ey": 1538, "ly": 2017, "p": 4038, "al": ["avisado", "ciro alegria", "Avisado"]},
  {"key": "Chilcal-Ecuador", "n": "Chilcal", "c": "Ecuador", "r": "vng_antioquia_popayan_choco", "ll": [0.939, -78.185], "ey": 1525, "ly": 1830, "p": 4038},
  {"key": "Huito-Chile", "n": "Huito", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-41.70916, -73.15443], "ey": 1000, "ly": 1500, "p": 4038},
  {"key": "Sa-Vol-Colombia", "n": "Sa-Vol", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.99344, -74.84324], "ey": 1300, "ly": 1500, "p": 4037},
  {"key": "San Juan de Salinas-Peru", "n": "San Juan de Salinas", "c": "Peru", "r": "per_puno", "ll": [-14.99139, -70.10611], "ey": 1850, "ly": 2025, "p": 4034},
  {"key": "Ten-Colombia", "n": "Ten", "c": "Colombia", "r": "vng_llanos_caguan", "ll": [5.94, -72.096], "ey": 1525, "ly": 1830, "p": 4034, "al": ["teen", "Teen"]},
  {"key": "Tarapacá-Colombia", "n": "Tarapacá", "c": "Colombia", "r": "col_amazonas", "ll": [-2.89013, -69.74174], "ey": 1900, "ly": 2025, "p": 4033},
  {"key": "Padre Barral-Venezuela", "n": "Padre Barral", "c": "Venezuela", "r": "ven_delta_amacuro", "ll": [9.01832, -60.89492], "ey": 1920, "ly": 2025, "p": 4033},
  {"key": "Putumayo-Peru", "n": "Putumayo", "c": "Peru", "r": "per_loreto", "ll": [-2.44694, -72.66806], "ey": 1850, "ly": 2025, "p": 4032, "al": ["san antonio del estrecho", "San Antonio del Estrecho"]},
  {"key": "Villa de Leales-Argentina", "n": "Villa de Leales", "c": "Argentina", "r": "arg_tucuman", "ll": [-27.19386, -65.31032], "ey": 1850, "ly": 2022, "p": 4030},
  {"key": "Chawin Punta-Peru", "n": "Chawin Punta", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.41006, -76.48268], "ey": 0, "ly": 1530, "p": 4029, "al": ["ashtacoto", "gashián", "hongojirca"]},
  {"key": "Cholocal (inca_chinchaysuyu)-Peru", "n": "Cholocal", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.30161, -79.74425], "ey": -2000, "ly": 1532, "p": 4029, "al": ["apurlec", "briseño", "cruz de chalpón"]},
  {"key": "Cerro de las Cañas-Argentina", "n": "Cerro de las Cañas", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.38, -60.64], "ey": 720, "ly": 1500, "p": 4026},
  {"key": "Médanos del Águila-Peru", "n": "Médanos del Águila", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.98993, -75.94452], "ey": -1000, "ly": 1530, "p": 4025, "al": ["cerro el águila", "dakar", "matacaballo"]},
  {"key": "Las Conchitas-Argentina", "n": "Las Conchitas", "c": "Argentina", "r": "crp_intendencia_buenos_aires", "ll": [-31.731, -60.309], "ey": 1774, "ly": 1830, "p": 4024, "al": ["conchas", "rio conchas", "Conchas"]},
  {"key": "Nazacara de Pacajes-Bolivia", "n": "Nazacara de Pacajes", "c": "Bolivia", "r": "bol_la_paz", "ll": [-16.94074, -68.76995], "ey": 1750, "ly": 2026, "p": 4022, "al": ["nazacara", "Nazacara"]},
  {"key": "Santo Domingo De Onzole-Ecuador", "n": "Santo Domingo De Onzole", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.66924, -79.16211], "ey": 1850, "ly": 2025, "p": 4020},
  {"key": "Bacatá Sitio torre-Colombia", "n": "Bacatá Sitio torre", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.41107, -74.31626], "ey": 1300, "ly": 1500, "p": 4020},
  {"key": "Morrison-Argentina", "n": "Morrison", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.59284, -62.8334], "ey": 1850, "ly": 2022, "p": 4019}
];

const gaz = JSON5.parse(fs.readFileSync("histmap/1.data_raw/population_regional/QUIPU/quipu_gazetteers.json5", "utf8"));
const byKey = new Map();
for (const g of gaz.gazetteers) {
  if (!fs.existsSync(g.path)) continue;
  const data = JSON.parse(fs.readFileSync(g.path, "utf8"));
  for (const [k, v] of Object.entries(data)) {
    const matched = input.find(s => s.key === k || s.n === v.name || (v.coords && Math.abs(v.coords[0] - s.ll[0]) < 0.01 && Math.abs(v.coords[1] - s.ll[1]) < 0.01));
    if (matched) {
      if (!byKey.has(matched.key)) byKey.set(matched.key, []);
      byKey.get(matched.key).push({ gaz: g.key, rawKey: k, v });
    }
  }
}

const out = {};
for (const s of input) {
  out[s.key] = byKey.get(s.key) || [];
}
fs.writeFileSync("tests/chunk041_gaz_matches.json", JSON.stringify(out, null, 2));
console.log("Matched keys:", [...byKey.keys()].length, "of", input.length);
