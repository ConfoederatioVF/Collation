import json, os, glob, math, urllib.request, urllib.parse, time

INPUT = [
  {"key": "Miraflores (vng_antioquia_popayan_choco)-Colombia", "n": "Miraflores", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.537, -76.421], "ey": 1525, "ly": 1830, "p": 4018},
  {"key": "San José De La Montaña-Colombia", "n": "San José De La Montaña", "c": "Colombia", "r": "col_antioquia", "ll": [6.85009, -75.68335], "ey": 1850, "ly": 2025, "p": 4017},
  {"key": "General Juan Facundo Quiroga-Argentina", "n": "General Juan Facundo Quiroga", "c": "Argentina", "r": "arg_la_rioja", "ll": [-30.80064, -66.86786], "ey": 1850, "ly": 2022, "p": 4017},
  {"key": "Tio Pugio-Argentina", "n": "Tio Pugio", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-32.288, -63.356], "ey": 1536, "ly": 1830, "p": 4017},
  {"key": "Chinauta-Colombia", "n": "Chinauta", "c": "Colombia", "r": "col_cundinamarca", "ll": [4.29414, -74.455], "ey": 1525, "ly": 2018, "p": 4016, "al": ["panchez", "Panchez"]},
  {"key": "Rómulo Gallegos (ven_delta_amacuro)-Venezuela", "n": "Rómulo Gallegos", "c": "Venezuela", "r": "ven_delta_amacuro", "ll": [8.54665, -61.81503], "ey": 1850, "ly": 2025, "p": 4015},
  {"key": "Villa Rumipal-Argentina", "n": "Villa Rumipal", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.18943, -64.47925], "ey": 1850, "ly": 2022, "p": 4015},
  {"key": "Charquina-Argentina", "n": "Charquina", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.21069, -65.65276], "ey": 80, "ly": 1500, "p": 4014},
  {"key": "Nuevo Rocafuerte-Ecuador", "n": "Nuevo Rocafuerte", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.91169, -75.58433], "ey": 1920, "ly": 2025, "p": 4013},
  {"key": "Cañon Rio Porce-Colombia", "n": "Cañon Rio Porce", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.95344, -75.109], "ey": -6244, "ly": 1500, "p": 4009, "al": ["t13 - entidad arqueológica", "T13 - Entidad Arqueológica"]},
  {"key": "Wiskachaqaqa-Peru", "n": "Wiskachaqaqa", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.71065, -70.43683], "ey": 1300, "ly": 1530, "p": 4008, "al": ["elemento arqueológico aislado huancasaya balsapata", "pucara ayacunca", "pucara onocora"]},
  {"key": "San Basilio-Argentina", "n": "San Basilio", "c": "Argentina", "r": "arg_cordoba", "ll": [-33.49848, -64.31468], "ey": 1850, "ly": 2022, "p": 4007},
  {"key": "Tierradentro-Colombia", "n": "Tierradentro", "c": "Colombia", "r": "col_cordoba", "ll": [7.81242, -75.87633], "ey": 1850, "ly": 2018, "p": 4006},
  {"key": "Timaukel-Chile_2", "n": "Timaukel", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-53.6875, -69.92584], "ey": 0, "ly": 1500, "p": 4006},
  {"key": "Acobambilla-Peru", "n": "Acobambilla", "c": "Peru", "r": "per_huancavelica", "ll": [-12.66444, -75.32417], "ey": 1525, "ly": 2025, "p": 4005},
  {"key": "Chetilla-Peru", "n": "Chetilla", "c": "Peru", "r": "per_cajamarca", "ll": [-7.14694, -78.67333], "ey": 1850, "ly": 2025, "p": 4005},
  {"key": "Buena Esperanza-Argentina", "n": "Buena Esperanza", "c": "Argentina", "r": "arg_san_luis", "ll": [-34.75787, -65.25359], "ey": 1850, "ly": 2022, "p": 4004},
  {"key": "Cerro Yaur-Peru", "n": "Cerro Yaur", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.88226, -71.8202], "ey": 500, "ly": 1530, "p": 4003},
  {"key": "Puerto Pizarro-Peru", "n": "Puerto Pizarro", "c": "Peru", "r": "per_tumbes", "ll": [-3.503, -80.3916], "ey": 1850, "ly": 2017, "p": 4000, "al": ["la victoria", "La Victoria"]},
  {"key": "Cmn_projecto_salitreras_wfl1 (inca_collasuyu_2)-Chile", "n": "Cmn_projecto_salitreras_wfl1", "c": "Chile", "r": "inca_collasuyu", "ll": [-20.83063, -69.54059], "ey": 1300, "ly": 1530, "p": 4000},
  {"key": "Divina Pastora Jobal-Venezuela", "n": "Divina Pastora Jobal", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [9.083, -68.583], "ey": 1757, "ly": 1830, "p": 3999, "al": ["divina pastora", "jovar", "lagunitas"]},
  {"key": "Izata-Bolivia", "n": "Izata", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.754, -66.073], "ey": 1525, "ly": 1825, "p": 3993, "al": ["isata", "Isata"]},
  {"key": "costayaco-Colombia", "n": "costayaco", "c": "Colombia", "r": "na_nw_amazon_foothills", "ll": [1.0012, -76.58668], "ey": 0, "ly": 1500, "p": 3993, "al": ["área arqueológica"]},
  {"key": "La Rancheria-Peru", "n": "La Rancheria", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.93877, -75.70079], "ey": 0, "ly": 1532, "p": 3991, "al": ["cerrillo", "cerrillo a", "cerrillos"]},
  {"key": "Menocucho-Peru", "n": "Menocucho", "c": "Peru", "r": "per_la_libertad", "ll": [-8.0228, -78.8389], "ey": 1525, "ly": 2017, "p": 3990, "al": ["catuay alto", "catuay bajo", "minocucho"]},
  {"key": "Santa Lucía-Peru", "n": "Santa Lucía", "c": "Peru", "r": "inca_contisuyu", "ll": [-15.01718, -73.3487], "ey": -2000, "ly": 1530, "p": 3990},
  {"key": "Car-Colombia", "n": "Car", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [12.04377, -72.13506], "ey": 1000, "ly": 1500, "p": 3990, "al": ["carrs", "Carrs"]},
  {"key": "Niebla-Chile", "n": "Niebla", "c": "Chile", "r": "chl_region_de_los_rios", "ll": [-39.84872, -73.39445], "ey": 1525, "ly": 2017, "p": 3989, "al": ["el palomar", "fuerte de niebla", "san pedro de alcantara"]},
  {"key": "Berástegui-Colombia", "n": "Berástegui", "c": "Colombia", "r": "col_cordoba", "ll": [8.877, -75.70811], "ey": 1850, "ly": 2018, "p": 3988, "al": ["la esperanza", "La Esperanza"]},
  {"key": "Cachenche-Colombia", "n": "Cachenche", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.30667, -75.44394], "ey": 1300, "ly": 1500, "p": 3988, "al": ["tegucigalpa", "yacimiento", "Tegucigalpa"]},
  {"key": "Casablanca-Colombia", "n": "Casablanca", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.35373, -74.66341], "ey": -1000, "ly": 1500, "p": 3988},
  {"key": "San Antonio-Venezuela_2", "n": "San Antonio", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [8.977, -67.59], "ey": 1538, "ly": 1830, "p": 3986},
  {"key": "Calipui-Peru", "n": "Calipui", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-8.417, -78.172], "ey": 1525, "ly": 1825, "p": 3984},
  {"key": "Taquil-Ecuador", "n": "Taquil", "c": "Ecuador", "r": "ecu_loja", "ll": [-3.90964, -79.29512], "ey": 1525, "ly": 2025, "p": 3983},
  {"key": "Ocalli-Peru", "n": "Ocalli", "c": "Peru", "r": "per_amazonas", "ll": [-6.23528, -78.26639], "ey": 1525, "ly": 2025, "p": 3982},
  {"key": "Rancul-Argentina", "n": "Rancul", "c": "Argentina", "r": "arg_la_pampa", "ll": [-35.06777, -64.68426], "ey": 1900, "ly": 2022, "p": 3981},
  {"key": "Carhuas-Peru", "n": "Carhuas", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.12018, -75.85567], "ey": -2000, "ly": 1530, "p": 3979, "ex": [{"date": "1961.1.1", "name": "Guadalupe"}], "al": ["dakar", "geoglífo antropomorfo pampa biocochino", "geoglífo portachuelo"]},
  {"key": "Cerro Cuichuro-Peru", "n": "Cerro Cuichuro", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.82556, -78.11502], "ey": 0, "ly": 1530, "p": 3979, "al": ["arqueológico el palluro", "arqueológico las cruces", "cerro campana"]},
  {"key": "Llallagua Pampa-Bolivia", "n": "Llallagua Pampa", "c": "Bolivia", "r": "inca_collasuyu", "ll": [-17.77328, -67.64687], "ey": 900, "ly": 1500, "p": 3977, "al": ["huari pampa", "lupi sirca", "machaj norte"]},
  {"key": "Carolina-Colombia", "n": "Carolina", "c": "Colombia", "r": "col_antioquia", "ll": [6.726, -75.28319], "ey": 1850, "ly": 2025, "p": 3976},
  {"key": "Ñuñoa-Peru", "n": "Ñuñoa", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.76867, -70.40291], "ey": 1440, "ly": 1532, "p": 3974},
  {"key": "La Rita-Peru", "n": "La Rita", "c": "Peru", "r": "per_piura", "ll": [-5.0073, -80.3037], "ey": 1850, "ly": 2017, "p": 3973},
  {"key": "valle de Guancocolla-Ecuador", "n": "valle de Guancocolla", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-4.297, -79.401], "ey": 1525, "ly": 1830, "p": 3972},
  {"key": "Inka Yarka-Peru", "n": "Inka Yarka", "c": "Peru", "r": "inca_cuzco_heartland", "ll": [-13.59549, -71.8977], "ey": 1300, "ly": 1530, "p": 3972, "al": ["caballo kancha", "lucerinas", "andenes de roquepata"]},
  {"key": "Laguna de Batavia-Argentina", "n": "Laguna de Batavia", "c": "Argentina", "r": "sc_pampas_salado_colorado", "ll": [-34.7724, -64.7175], "ey": -2250, "ly": 1500, "p": 3972},
  {"key": "Desvio Algarrobal-Peru", "n": "Desvio Algarrobal", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.17939, -79.35111], "ey": 0, "ly": 1532, "p": 3971, "al": ["huaca blanca", "huaca macines", "huaca palomino"]},
  {"key": "Villa del Carmen-Argentina", "n": "Villa del Carmen", "c": "Argentina", "r": "arg_formosa", "ll": [-26.25278, -58.25194], "ey": 1850, "ly": 2010, "p": 3970},
  {"key": "Sultana-Chile", "n": "Sultana", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.90227, -69.03689], "ey": 1300, "ly": 1500, "p": 3970},
  {"key": "Palca (per_huancavelica)-Peru", "n": "Palca", "c": "Peru", "r": "per_huancavelica", "ll": [-12.65694, -74.98028], "ey": 1525, "ly": 2025, "p": 3969},
  {"key": "Ccora-Peru", "n": "Ccora", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.25047, -71.63447], "ey": 1000, "ly": 1530, "p": 3969, "al": ["chiñisir", "ch´iñisir", "Chiñisir"]},
  {"key": "Baño Nuevo-Chile", "n": "Baño Nuevo", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-45.2644, -71.44275], "ey": -8890, "ly": -348, "p": 3968},
  {"key": "Dolavon-Argentina", "n": "Dolavon", "c": "Argentina", "r": "arg_chubut", "ll": [-43.3093, -65.70874], "ey": 1900, "ly": 2022, "p": 3967},
  {"key": "Castañeda-Venezuela", "n": "Castañeda", "c": "Venezuela", "r": "ven_lara", "ll": [10.08667, -69.81833], "ey": 1850, "ly": 2025, "p": 3965},
  {"key": "Victoria-Ecuador", "n": "Victoria", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.42553, -79.83673], "ey": 1900, "ly": 2025, "p": 3964},
  {"key": "Potrero de los Funes-Argentina", "n": "Potrero de los Funes", "c": "Argentina", "r": "arg_san_luis", "ll": [-33.22014, -66.22707], "ey": 1536, "ly": 2022, "p": 3963, "al": ["la dormida del carrizal", "potrero grande", "La Dormida del Carrizal"]},
  {"key": "Cerro Puntudo-Argentina", "n": "Cerro Puntudo", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-29.65, -64.1667], "ey": 80, "ly": 1500, "p": 3961},
  {"key": "Turi-Chile", "n": "Turi", "c": "Chile", "r": "inca_collasuyu", "ll": [-22.234, -68.273], "ey": -87, "ly": 1530, "p": 3960, "al": ["circulos de tur", "circulos de turi (qñ: ch-tn", "confluencia"]},
  {"key": "Yacimientos 1-Colombia", "n": "Yacimientos 1", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.09361, -74.95861], "ey": -3000, "ly": 1500, "p": 3960},
  {"key": "Melo-Argentina_2", "n": "Melo", "c": "Argentina", "r": "crp_intendencia_buenos_aires", "ll": [-30.691, -61.132], "ey": 1793, "ly": 1830, "p": 3959},
  {"key": "Gigante de Atacama-Chile", "n": "Gigante de Atacama", "c": "Chile", "r": "inca_collasuyu", "ll": [-19.94891, -69.63326], "ey": -3000, "ly": 1530, "p": 3959},
  {"key": "Nilahue-Chile", "n": "Nilahue", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-34.659, -71.739], "ey": 1525, "ly": 1830, "p": 3958},
  {"key": "Tingo de Ponasa-Peru", "n": "Tingo de Ponasa", "c": "Peru", "r": "per_san_martin", "ll": [-6.93611, -76.25389], "ey": 1900, "ly": 2025, "p": 3957},
  {"key": "Perallillo-Chile", "n": "Perallillo", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-36.80477, -72.00986], "ey": 0, "ly": 1500, "p": 3955},
  {"key": "San Jose-Peru", "n": "San Jose", "c": "Peru", "r": "per_la_libertad", "ll": [-8.449, -78.7361], "ey": 1850, "ly": 2017, "p": 3954},
  {"key": "El Pueblo-Peru", "n": "El Pueblo", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.44474, -76.97372], "ey": -2000, "ly": 1530, "p": 3953, "al": ["las trojas", "Las Trojas"]},
  {"key": "Pha-Colombia", "n": "Pha", "c": "Colombia", "r": "na_nw_amazon_foothills", "ll": [0.6724, -76.83402], "ey": 500, "ly": 1500, "p": 3953, "al": ["ori", "Ori"]},
  {"key": "San Luis de Lucma-Peru", "n": "San Luis de Lucma", "c": "Peru", "r": "per_cajamarca", "ll": [-6.29389, -78.60361], "ey": 1850, "ly": 2025, "p": 3951},
  {"key": "Arquitecto Sixto Durán Ballén-Ecuador", "n": "Arquitecto Sixto Durán Ballén", "c": "Ecuador", "r": "ecu_manabi", "ll": [-1.48968, -80.31373], "ey": 1850, "ly": 2025, "p": 3950},
  {"key": "El Playón (ven_carabobo)-Venezuela", "n": "El Playón", "c": "Venezuela", "r": "ven_carabobo", "ll": [10.48778, -67.7697], "ey": 1850, "ly": 2011, "p": 3947},
  {"key": "India Muerta-Argentina", "n": "India Muerta", "c": "Argentina", "r": "crp_intendencia_buenos_aires", "ll": [-33.416, -61.037], "ey": 1536, "ly": 1830, "p": 3947},
  {"key": "Pampa del Inca-Peru", "n": "Pampa del Inca", "c": "Peru", "r": "inca_contisuyu", "ll": [-15.18716, -74.85349], "ey": 1438, "ly": 1530, "p": 3947},
  {"key": "Monte Lima-Peru_2", "n": "Monte Lima", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-4.87177, -80.95748], "ey": -3000, "ly": 1530, "p": 3945, "al": ["cerro capullana", "libertad", "san jose"]},
  {"key": "Cupi-Peru", "n": "Cupi", "c": "Peru", "r": "per_puno", "ll": [-14.905, -70.86667], "ey": 1525, "ly": 2025, "p": 3944},
  {"key": "La Chimba-Chile", "n": "La Chimba", "c": "Chile", "r": "chl_region_de_coquimbo", "ll": [-30.64031, -71.23656], "ey": 1525, "ly": 2017, "p": 3944, "al": ["chimba", "limari", "Chimba"]},
  {"key": "Quilca-Peru", "n": "Quilca", "c": "Peru", "r": "per_arequipa", "ll": [-16.71694, -72.42556], "ey": -1000, "ly": 2025, "p": 3943, "al": ["aranta", "los gentiles", "arantas"]},
  {"key": "Capelo-Peru", "n": "Capelo", "c": "Peru", "r": "per_loreto", "ll": [-5.40528, -74.15778], "ey": 1900, "ly": 2025, "p": 3941, "al": ["flor de punga", "Flor de Punga"]},
  {"key": "El Rosario-Colombia_2", "n": "El Rosario", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [10.846, -73.179], "ey": 1525, "ly": 1830, "p": 3941},
  {"key": "Guamoco-Colombia", "n": "Guamoco", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [7.751, -74.441], "ey": 1525, "ly": 1830, "p": 3941},
  {"key": "Piedra del Águila-Argentina", "n": "Piedra del Águila", "c": "Argentina", "r": "arg_neuquen", "ll": [-40.04857, -70.07517], "ey": 1900, "ly": 2022, "p": 3940},
  {"key": "Torre 215 La Juana-Colombia", "n": "Torre 215 La Juana", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.49312, -74.68418], "ey": 963, "ly": 1500, "p": 3940},
  {"key": "Las Mercedes Salado-Argentina", "n": "Las Mercedes Salado", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-27.784, -64.264], "ey": 200, "ly": 1400, "p": 3940, "ex": [{"date": "1847.1.1", "name": "Santiago del Estero"}], "al": ["santiago del estero prehispanic", "Santiago del Estero Prehispanic"]},
  {"key": "Villa Trinidad-Argentina", "n": "Villa Trinidad", "c": "Argentina", "r": "arg_santa_fe", "ll": [-30.21765, -61.87757], "ey": 1850, "ly": 2022, "p": 3939},
  {"key": "Yaucapunta-Peru", "n": "Yaucapunta", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.13634, -77.131], "ey": -1000, "ly": 1530, "p": 3939, "al": ["huacauya", "petaca - quishuar punta", "targuy"]},
  {"key": "Ump-Colombia", "n": "Ump", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [6.77, -76.19], "ey": -380, "ly": 1500, "p": 3939, "al": ["tabladito", "Tabladito"]},
  {"key": "Vinará-Argentina", "n": "Vinará", "c": "Argentina", "r": "arg_tucuman", "ll": [-27.37994, -64.7947], "ey": 1536, "ly": 2022, "p": 3937, "al": ["vinara"]},
  {"key": "Chancaybaños-Peru", "n": "Chancaybaños", "c": "Peru", "r": "per_cajamarca", "ll": [-6.57611, -78.8675], "ey": 1850, "ly": 2025, "p": 3936},
  {"key": "Magmapunta-Peru", "n": "Magmapunta", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.9907, -76.51829], "ey": 0, "ly": 1530, "p": 3935, "al": ["arqueológico pacshaccho", "arqueológico piruro carpish", "arqueológico yurac ushno"]},
  {"key": "Chiclin-Peru", "n": "Chiclin", "c": "Peru", "r": "per_la_libertad", "ll": [-7.8357, -79.1605], "ey": 1850, "ly": 2017, "p": 3934},
  {"key": "Quebrada Chipana-Chile", "n": "Quebrada Chipana", "c": "Chile", "r": "inca_collasuyu", "ll": [-20.89917, -69.34722], "ey": -9482, "ly": 1532, "p": 3934, "al": ["challacollo", "Challacollo"]},
  {"key": "Carmelita A HA-Chile", "n": "Carmelita A HA", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.80309, -69.67588], "ey": 1000, "ly": 1500, "p": 3934}
]

print(f"Total items: {len(INPUT)}")

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SVEA-Toponymy/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

results = {}
for idx, item in enumerate(INPUT):
    key = item["key"]
    n = item["n"]
    lat, lng = item["ll"]
    rec = {"input": item, "es_geo": [], "es_search": [], "en_search": [], "extracts": {}}
    
    # 1. ES Wikipedia geosearch
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        d = fetch_json(u)
        rec["es_geo"] = d.get("query", {}).get("geosearch", [])
    except Exception as e:
        rec["es_geo_err"] = str(e)

    # 2. ES Wikipedia title/text search
    try:
        q = urllib.parse.quote(f"{n} {item['c']}")
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        d = fetch_json(u)
        rec["es_search"] = [s["title"] for s in d.get("query", {}).get("search", [])]
    except Exception as e:
        pass

    # Fetch summary for top geosearch hit (if < 5km) and top search hit
    titles_to_fetch = []
    for g in rec["es_geo"]:
        if g.get("dist", 99999) < 5000:
            titles_to_fetch.append(g["title"])
    for t in rec["es_search"][:2]:
        if t not in titles_to_fetch:
            titles_to_fetch.append(t)

    if titles_to_fetch:
        try:
            joined = urllib.parse.quote("|".join(titles_to_fetch[:4]))
            u = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={joined}&format=json"
            d = fetch_json(u)
            for pid, pdata in d.get("query", {}).get("pages", {}).items():
                if "extract" in pdata:
                    rec["extracts"][pdata["title"]] = pdata["extract"][:800]
        except Exception:
            pass

    results[key] = rec
    if (idx + 1) % 15 == 0:
        print(f"Processed {idx + 1}/90...")
    time.sleep(0.05)

with open("tests/tmp_c042_wiki.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Saved tests/tmp_c042_wiki.json")
