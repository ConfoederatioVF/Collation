import json, urllib.request, urllib.parse, concurrent.futures

ITEMS = [
{"key": "Santa Lucia (per_ayacucho)-Peru", "n": "Santa Lucia", "c": "Peru", "r": "per_ayacucho", "ll": [-14.97833, -74.52389], "ey": 1525, "ly": 2025, "p": 5661, "al": ["santa lucía", "Santa Lucía"]},
{"key": "None-Chile", "n": "None", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-35.5551, -71.59431], "ey": 1525, "ly": 1830, "p": 5661, "al": ["duao", "pocoa", "Duao"]},
{"key": "Pantoja-Ecuador", "n": "Pantoja", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.97048, -75.17418], "ey": 1850, "ly": 2025, "p": 5660, "al": ["torres causana"]},
{"key": "Tuutinentsa-Ecuador", "n": "Tuutinentsa", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-2.54985, -77.47207], "ey": 1920, "ly": 2025, "p": 5658},
{"key": "Chimon-Colombia", "n": "Chimon", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [8.95786, -75.57976], "ey": 1300, "ly": 1500, "p": 5656},
{"key": "El Villar-Bolivia", "n": "El Villar", "c": "Bolivia", "r": "bol_chuquisaca", "ll": [-19.63345, -64.36866], "ey": 1750, "ly": 2026, "p": 5654},
{"key": "Huac-Huas-Peru", "n": "Huac-Huas", "c": "Peru", "r": "per_huancavelica", "ll": [-14.13167, -74.94222], "ey": 1525, "ly": 2025, "p": 5652, "al": ["guaguas", "huacas", "Guaguas"]},
{"key": "Cañada Rosquín-Argentina", "n": "Cañada Rosquín", "c": "Argentina", "r": "arg_santa_fe", "ll": [-32.05433, -61.60222], "ey": 1850, "ly": 2022, "p": 5649},
{"key": "Colnaca-Bolivia", "n": "Colnaca", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-20.732, -65.549], "ey": 1525, "ly": 1825, "p": 5648},
{"key": "Manuel J. Calle-Ecuador", "n": "Manuel J. Calle", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.38757, -79.39177], "ey": 1850, "ly": 2025, "p": 5642},
{"key": "Rurin Pillao-Peru", "n": "Rurin Pillao", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.78996, -75.95949], "ey": -2000, "ly": 1530, "p": 5641, "al": ["chinchupampa", "chuchuhuasin", "inca huasín"]},
{"key": "Tilcara-Argentina_2", "n": "Tilcara", "c": "Argentina", "r": "sc_gran_chaco_pilcomayo", "ll": [-23.588, -65.402], "ey": 1000, "ly": 1450, "p": 5640, "al": ["omaguaca", "Omaguaca"]},
{"key": "Aspásica-Colombia", "n": "Aspásica", "c": "Colombia", "r": "col_norte_de_santander", "ll": [8.28151, -73.19634], "ey": 1525, "ly": 2018, "p": 5638, "al": ["aspasica", "santa catarina espacica", "Aspasica"]},
{"key": "Rosaspata-Peru", "n": "Rosaspata", "c": "Peru", "r": "per_puno", "ll": [-15.23472, -69.5275], "ey": 1850, "ly": 2025, "p": 5637},
{"key": "Lascano-Ecuador", "n": "Lascano", "c": "Ecuador", "r": "ecu_manabi", "ll": [-1.51529, -80.2612], "ey": 1850, "ly": 2025, "p": 5634},
{"key": "Atanquez-Colombia", "n": "Atanquez", "c": "Colombia", "r": "col_cesar", "ll": [10.69691, -73.35399], "ey": 1525, "ly": 2018, "p": 5632, "al": ["san isidro atanques", "San Isidro Atanques"]},
{"key": "La Selva-Colombia_2", "n": "La Selva", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.9057, -75.64716], "ey": -8844, "ly": 1500, "p": 5632},
{"key": "Cusimini-Ecuador", "n": "Cusimini", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-4.093, -80.039], "ey": 1525, "ly": 1830, "p": 5631},
{"key": "Las Hernández-Venezuela", "n": "Las Hernández", "c": "Venezuela", "r": "ven_nueva_esparta", "ll": [10.92769, -64.02801], "ey": 1850, "ly": 2011, "p": 5629},
{"key": "Honoria-Peru", "n": "Honoria", "c": "Peru", "r": "per_huanuco", "ll": [-8.76944, -74.70917], "ey": 1850, "ly": 2025, "p": 5628},
{"key": "Chinca-Ecuador", "n": "Chinca", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.77064, -79.5705], "ey": 1850, "ly": 2025, "p": 5627},
{"key": "Barrancas-Argentina", "n": "Barrancas", "c": "Argentina", "r": "arg_santa_fe", "ll": [-32.23472, -60.98362], "ey": 1774, "ly": 2022, "p": 5622},
{"key": "Cuicas-Venezuela", "n": "Cuicas", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.70222, -70.29444], "ey": 1850, "ly": 2025, "p": 5621},
{"key": "Calcan-Colombia", "n": "Calcan", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [1.087, -77.671], "ey": 1525, "ly": 1830, "p": 5621},
{"key": "Bigand-Argentina", "n": "Bigand", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.37403, -61.18477], "ey": 1850, "ly": 2022, "p": 5620, "al": ["colonia bigand", "Colonia Bigand"]},
{"key": "Hasenkamp-Argentina", "n": "Hasenkamp", "c": "Argentina", "r": "arg_entre_rios", "ll": [-31.5121, -59.83536], "ey": 1850, "ly": 2022, "p": 5620},
{"key": "Wayrapitec-Peru", "n": "Wayrapitec", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.87517, -76.72205], "ey": 1300, "ly": 1532, "p": 5604, "al": ["angacharican", "el progreso", "millpo"]},
{"key": "La Vega-Colombia_2", "n": "La Vega", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.63407, -78.66904], "ey": 1000, "ly": 1500, "p": 5604, "al": ["almejero", "nueva creación", "Almejero"]},
{"key": "Cruz del Eje-Argentina_2", "n": "Cruz del Eje", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.72617, -64.80621], "ey": 80, "ly": 1500, "p": 5602},
{"key": "Villa Atamisqui-Argentina", "n": "Villa Atamisqui", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-28.49625, -63.81741], "ey": 1850, "ly": 2022, "p": 5600},
{"key": "Montevideo-Peru", "n": "Montevideo", "c": "Peru", "r": "per_amazonas", "ll": [-6.61806, -77.80222], "ey": 1750, "ly": 2025, "p": 5599, "al": ["san ildefonso", "San Ildefonso"]},
{"key": "San Nicolas-Venezuela", "n": "San Nicolas", "c": "Venezuela", "r": "ven_portuguesa", "ll": [8.80167, -69.75833], "ey": 1850, "ly": 2011, "p": 5598},
{"key": "Relbun-Chile", "n": "Relbun", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-36.89227, -72.35211], "ey": 0, "ly": 1500, "p": 5597, "al": ["liucura bocatoma", "planta hidroelectrica liucura", "Liucura Bocatoma"]},
{"key": "Eugenio Bustos-Argentina", "n": "Eugenio Bustos", "c": "Argentina", "r": "arg_mendoza", "ll": [-33.77954, -69.05488], "ey": 1850, "ly": 2010, "p": 5591},
{"key": "Puerto Claver-Colombia", "n": "Puerto Claver", "c": "Colombia", "r": "col_antioquia", "ll": [7.71155, -74.7525], "ey": 1850, "ly": 2018, "p": 5584},
{"key": "Pacomarca-Peru", "n": "Pacomarca", "c": "Peru", "r": "per_huancavelica", "ll": [-14.0055, -74.9578], "ey": 1525, "ly": 2017, "p": 5581},
{"key": "Matarredonda-Colombia", "n": "Matarredonda", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.728, -76.6], "ey": 1525, "ly": 1830, "p": 5581},
{"key": "Nangara-Ecuador", "n": "Nangara", "c": "Ecuador", "r": "vp_intendencia_trujillo", "ll": [-4.357, -79.771], "ey": 1525, "ly": 1825, "p": 5578},
{"key": "Casual-Peru", "n": "Casual", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-5.58223, -78.55827], "ey": -2000, "ly": 1530, "p": 5569, "al": ["aserrillo", "el salvador", "el triunfo"]},
{"key": "Tangani-Chile", "n": "Tangani", "c": "Chile", "r": "inca_collasuyu", "ll": [-18.53471, -69.93324], "ey": -3881, "ly": 1532, "p": 5567},
{"key": "Higueras-Chile", "n": "Higueras", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-29.513, -71.201], "ey": 1525, "ly": 1830, "p": 5566, "al": ["valle de las higuerillas", "valle de las Higuerillas"]},
{"key": "Purnio-Colombia", "n": "Purnio", "c": "Colombia", "r": "col_caldas", "ll": [5.41126, -74.68852], "ey": 1525, "ly": 2018, "p": 5562, "al": ["guarumo", "guarimo", "purmio"]},
{"key": "Calpa-Peru_2", "n": "Calpa", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.871, -77.182], "ey": 1525, "ly": 1825, "p": 5561, "al": ["colpa", "Colpa"]},
{"key": "Padre Márquez-Peru", "n": "Padre Márquez", "c": "Peru", "r": "per_loreto", "ll": [-7.94667, -74.84083], "ey": 1900, "ly": 2025, "p": 5560, "al": ["tiruntan", "Tiruntan"]},
{"key": "Cerro Norte-Argentina", "n": "Cerro Norte", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-51.92926, -70.1177], "ey": -532, "ly": 459, "p": 5560},
{"key": "Santa Catarina-Bolivia", "n": "Santa Catarina", "c": "Bolivia", "r": "vp_intendencia_puno", "ll": [-15.483, -69.302], "ey": 1525, "ly": 1825, "p": 5558},
{"key": "Calliri-Bolivia", "n": "Calliri", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.531, -66.485], "ey": 1525, "ly": 1825, "p": 5556},
{"key": "Pampa Siguas SA-Peru", "n": "Pampa Siguas SA", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.38819, -72.04144], "ey": 0, "ly": 1530, "p": 5556, "al": ["quebrada mollechico", "quebrada santa rosa", "Quebrada Mollechico"]},
{"key": "El palmar-Colombia", "n": "El palmar", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.01565, -74.90031], "ey": 500, "ly": 1500, "p": 5554},
{"key": "Tongoy-Chile", "n": "Tongoy", "c": "Chile", "r": "chl_region_de_coquimbo", "ll": [-30.26243, -71.48893], "ey": 1525, "ly": 2017, "p": 5552, "al": ["tongoi", "Tongoi"]},
{"key": "Vichaycocha-Peru", "n": "Vichaycocha", "c": "Peru", "r": "per_lima", "ll": [-11.1411, -76.6243], "ey": 1525, "ly": 2017, "p": 5549},
{"key": "Darregueira-Argentina", "n": "Darregueira", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-37.68941, -63.16111], "ey": 1850, "ly": 2010, "p": 5547},
{"key": "Bilaya-Peru", "n": "Bilaya", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-6.181, -78.22], "ey": 1525, "ly": 1830, "p": 5547, "al": ["bilalla", "vilalla", "vilaya"]},
{"key": "Villa Parque Santa Ana-Argentina", "n": "Villa Parque Santa Ana", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.58971, -64.35404], "ey": 1850, "ly": 2022, "p": 5543, "al": ["campos del virrey", "Campos del Virrey"]},
{"key": "Huanca-Huanca-Peru", "n": "Huanca-Huanca", "c": "Peru", "r": "per_huancavelica", "ll": [-12.91861, -74.61], "ey": 1525, "ly": 2025, "p": 5538, "al": ["huancahuaca", "huancahuanca", "Huancahuaca"]},
{"key": "Pii-Colombia", "n": "Pii", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.76, -75.12], "ey": -6877, "ly": 1500, "p": 5536},
{"key": "San Cristóbal de Rajan-Peru", "n": "San Cristóbal de Rajan", "c": "Peru", "r": "per_ancash", "ll": [-10.38694, -77.21944], "ey": 1525, "ly": 2025, "p": 5535, "al": ["rajan", "Rajan"]},
{"key": "Alto del Rosario-Colombia", "n": "Alto del Rosario", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.252, -74.788], "ey": 1525, "ly": 1830, "p": 5533},
{"key": "Yauyani-Bolivia", "n": "Yauyani", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.215, -66.655], "ey": 1525, "ly": 1825, "p": 5533, "al": ["yani", "Yani"]},
{"key": "Enokanqui-Ecuador", "n": "Enokanqui", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.22658, -76.84867], "ey": 1920, "ly": 2025, "p": 5529},
{"key": "Calana-Peru", "n": "Calana", "c": "Peru", "r": "per_tacna", "ll": [-17.94333, -70.18833], "ey": 1850, "ly": 2025, "p": 5527},
{"key": "San Antonio de los Caballeros-Colombia", "n": "San Antonio de los Caballeros", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.35391, -76.29767], "ey": 1850, "ly": 2018, "p": 5526},
{"key": "Collana-Bolivia", "n": "Collana", "c": "Bolivia", "r": "bol_la_paz", "ll": [-16.66899, -67.96636], "ey": 1525, "ly": 2026, "p": 5526, "al": ["santiago de collana", "Santiago de Collana"]},
{"key": "Togüí-Colombia", "n": "Togüí", "c": "Colombia", "r": "col_boyaca", "ll": [5.93744, -73.51365], "ey": 1850, "ly": 2025, "p": 5523},
{"key": "La Pintada-Colombia_2", "n": "La Pintada", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.0258, -74.5216], "ey": 1300, "ly": 1500, "p": 5523, "al": ["poco tiesto", "casa blanca", "morro caliente"]},
{"key": "San Diego de Muellamues-Colombia", "n": "San Diego de Muellamues", "c": "Colombia", "r": "col_narino", "ll": [0.9564, -77.77147], "ey": 1525, "ly": 2018, "p": 5521, "al": ["mullamues", "muellamues", "mullon"]},
{"key": "Playa Grande-Argentina", "n": "Playa Grande", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.19317, -64.45432], "ey": 80, "ly": 1500, "p": 5520, "al": ["isla ayampitin", "Isla Ayampitin"]},
{"key": "Tocópero-Venezuela", "n": "Tocópero", "c": "Venezuela", "r": "ven_falcon", "ll": [11.49114, -69.22807], "ey": 1538, "ly": 2025, "p": 5519, "al": ["tocopero", "Tocopero"]},
{"key": "Rauquin-Peru", "n": "Rauquin", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.17041, -76.29295], "ey": 0, "ly": 1530, "p": 5519},
{"key": "Chaipi-Peru", "n": "Chaipi", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-15.406, -73.965], "ey": 1525, "ly": 1825, "p": 5517, "al": ["chaypi", "Chaypi"]},
{"key": "Yacimiento (na_magdalena_cauca_muisca_2)-Colombia", "n": "Yacimiento", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.39879, -75.54711], "ey": 629, "ly": 1500, "p": 5514},
{"key": "Santa Rosa del Conlara-Argentina", "n": "Santa Rosa del Conlara", "c": "Argentina", "r": "arg_san_luis", "ll": [-32.34284, -65.20895], "ey": 1850, "ly": 2010, "p": 5511},
{"key": "Cristo Nos Valga-Peru", "n": "Cristo Nos Valga", "c": "Peru", "r": "per_piura", "ll": [-5.49306, -80.74111], "ey": 1850, "ly": 2025, "p": 5510, "al": ["san cristo", "San Cristo"]},
{"key": "Huaricucchis-Peru", "n": "Huaricucchis", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.69, -76.014], "ey": 1525, "ly": 1825, "p": 5508, "al": ["huaricuchis", "huariycurchis", "Huaricuchis"]},
{"key": "Ambatillo-Ecuador", "n": "Ambatillo", "c": "Ecuador", "r": "ecu_tungurahua", "ll": [-1.20341, -78.66446], "ey": 1850, "ly": 2025, "p": 5505},
{"key": "Aroma-Chile", "n": "Aroma", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.919, -69.783], "ey": 1525, "ly": 1825, "p": 5505},
{"key": "Macarapana-Venezuela", "n": "Macarapana", "c": "Venezuela", "r": "ven_sucre", "ll": [10.57474, -63.24978], "ey": 1850, "ly": 2025, "p": 5504},
{"key": "Piscoyacu-Peru", "n": "Piscoyacu", "c": "Peru", "r": "per_san_martin", "ll": [-6.98111, -76.76944], "ey": 1900, "ly": 2025, "p": 5503},
{"key": "Tana-Chile", "n": "Tana", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.461, -69.957], "ey": 1525, "ly": 1825, "p": 5502},
{"key": "Ichocan-Peru_3", "n": "Ichocan", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.17907, -78.41216], "ey": 500, "ly": 1532, "p": 5501, "al": ["el castillo", "grutas de huayrapongo", "iscoconga a"]},
{"key": "Villa Guillermina-Argentina", "n": "Villa Guillermina", "c": "Argentina", "r": "arg_santa_fe", "ll": [-28.24445, -59.45151], "ey": 1850, "ly": 2022, "p": 5500},
{"key": "Chontabamba-Peru", "n": "Chontabamba", "c": "Peru", "r": "per_pasco", "ll": [-10.60222, -75.43889], "ey": 1850, "ly": 2025, "p": 5498},
{"key": "Chipaomarca-Peru", "n": "Chipaomarca", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.37084, -73.88015], "ey": -1000, "ly": 1530, "p": 5498},
{"key": "Complejo La Uva-Peru", "n": "Complejo La Uva", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.89833, -77.0725], "ey": 0, "ly": 1530, "p": 5498, "al": ["chacra cerro", "collique", "collique bajo"]},
{"key": "Mariño (ven_sucre_2)-Venezuela", "n": "Mariño", "c": "Venezuela", "r": "ven_sucre", "ll": [10.505, -63.41278], "ey": 1538, "ly": 2025, "p": 5497, "al": ["santa cruz casanay", "Santa Cruz Casanay"]},
{"key": "Bahía Whitesand-Chile", "n": "Bahía Whitesand", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.71213, -70.59709], "ey": -2000, "ly": 1500, "p": 5497, "al": ["aguada oazy", "campamento", "Aguada Oazy"]},
{"key": "La Belleza-Ecuador", "n": "La Belleza", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.65673, -77.04684], "ey": 1920, "ly": 2025, "p": 5495},
{"key": "yacimiento 2 Km23+-Colombia", "n": "yacimiento 2 Km23+", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.17991, -74.76337], "ey": 1000, "ly": 1500, "p": 5495},
{"key": "Covarachía-Colombia", "n": "Covarachía", "c": "Colombia", "r": "col_boyaca", "ll": [6.50018, -72.73898], "ey": 1850, "ly": 2025, "p": 5494},
{"key": "Kunturkanki-Peru", "n": "Kunturkanki", "c": "Peru", "r": "per_cusco", "ll": [-14.53472, -71.30694], "ey": 1850, "ly": 2025, "p": 5494, "al": ["el descanso", "El Descanso"]}
]

def wiki_get(url):
  req = urllib.request.Request(url, headers={'User-Agent': 'ViscountToponymy/1.0'})
  with urllib.request.urlopen(req, timeout=12) as r:
    return json.loads(r.read().decode('utf-8'))

def lookup(item):
  lat, lng = item['ll']
  res = {'key': item['key'], 'n': item['n'], 'c': item['c'], 'r': item['r'], 'ey': item['ey'], 'ly': item['ly'], 'al': item.get('al', [])}
  try:
    geo = wiki_get(f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=3&format=json")
    hits = geo.get('query', {}).get('geosearch', [])
    res['es_geo'] = [h['title'] + f" ({h['dist']}m)" for h in hits]
    if hits:
      title = urllib.parse.quote(hits[0]['title'])
      ext = wiki_get(f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={title}&format=json")
      pages = ext.get('query', {}).get('pages', {})
      for p in pages.values():
        res['es_intro'] = p.get('extract', '')[:600]
    # also try search by name + country
    q = urllib.parse.quote(f"{item['n']} {item['c']}")
    sr = wiki_get(f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=2&format=json")
    shits = sr.get('query', {}).get('search', [])
    res['es_search'] = [h['title'] for h in shits]
    if shits and (not hits or hits[0]['title'] != shits[0]['title']):
      t2 = urllib.parse.quote(shits[0]['title'])
      ext2 = wiki_get(f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={t2}&format=json")
      for p in ext2.get('query', {}).get('pages', {}).values():
        res['es_search_intro'] = p.get('extract', '')[:450]
  except Exception as e:
    res['err'] = str(e)
  return res

with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
  out = list(ex.map(lookup, ITEMS))

with open('tests/tmp_wiki_028.json', 'w', encoding='utf-8') as f:
  json.dump(out, f, ensure_ascii=False, indent=2)
print("Done:", len(out))
