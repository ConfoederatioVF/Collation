import json, glob, os, math

INPUT = [
  {"key": "Rio Muerto-Peru", "n": "Rio Muerto", "c": "Peru", "r": "inca_contisuyu", "ll": [-17.17124, -70.88248], "ey": 1438, "ly": 1532, "p": 3389, "al": ["chen chen", "Chen Chen"]},
  {"key": "Paccha (ecu_el_oro)-Ecuador", "n": "Paccha", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.5678, -79.67389], "ey": 1525, "ly": 2025, "p": 3388, "al": ["pagcha", "Pagcha"]},
  {"key": "Santa Sofia-Peru", "n": "Santa Sofia", "c": "Peru", "r": "per_piura", "ll": [-4.8854, -80.8405], "ey": 1850, "ly": 2017, "p": 3388, "al": ["tangarara", "Tangarara"]},
  {"key": "Chacarita-Ecuador", "n": "Chacarita", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.3761, -79.3474], "ey": 1850, "ly": 2025, "p": 3386},
  {"key": "Pocoto-Peru", "n": "Pocoto", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.89708, -76.2444], "ey": 0, "ly": 1530, "p": 3386},
  {"key": "Mariano Moreno-Argentina", "n": "Mariano Moreno", "c": "Argentina", "r": "arg_neuquen", "ll": [-38.76136, -70.03656], "ey": 1900, "ly": 2022, "p": 3382},
  {"key": "Recetor-Colombia", "n": "Recetor", "c": "Colombia", "r": "col_casanare", "ll": [5.22918, -72.76099], "ey": 1791, "ly": 2025, "p": 3381, "ex": [{"date": "2025.1.1", "name": "Recetor"}], "al": ["salinas de recetor", "receptor", "Salinas de Recetor"]},
  {"key": "Chimban-Peru", "n": "Chimban", "c": "Peru", "r": "per_cajamarca", "ll": [-6.25167, -78.47889], "ey": 1850, "ly": 2025, "p": 3380, "al": ["chimbán", "Chimbán"]},
  {"key": "Piaca-Peru", "n": "Piaca", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.51219, -71.37192], "ey": 0, "ly": 1532, "p": 3379, "al": ["campanayoc", "canispaya", "ccoloja"]},
  {"key": "Yanahuara-Peru", "n": "Yanahuara", "c": "Peru", "r": "vp_intendencia_arequipa", "ll": [-16.409, -71.569], "ey": 1542, "ly": 1825, "p": 3378, "ex": [{"date": "1961.1.1", "name": "Yanahuara"}]},
  {"key": "Catilluc-Peru", "n": "Catilluc", "c": "Peru", "r": "per_cajamarca", "ll": [-6.80167, -78.77917], "ey": 1850, "ly": 2025, "p": 3377},
  {"key": "Secclla-Peru", "n": "Secclla", "c": "Peru", "r": "per_huancavelica", "ll": [-13.05111, -74.48361], "ey": 1850, "ly": 2025, "p": 3377},
  {"key": "Lontue-Chile", "n": "Lontue", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-35.056, -71.271], "ey": 1525, "ly": 1830, "p": 3376, "al": ["peteroa", "villa de peteroa", "Peteroa"]},
  {"key": "Arrancaplumas-Colombia", "n": "Arrancaplumas", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.19965, -74.72306], "ey": 1000, "ly": 1500, "p": 3376, "al": ["la salada", "puerto bogotá", "La Salada"]},
  {"key": "La Sonadora (na_pacific_equatorial_valdivia)-Colombia", "n": "La Sonadora", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.39358, -78.68867], "ey": 500, "ly": 1500, "p": 3375, "al": ["restrepo", "Restrepo"]},
  {"key": "San Pablo-Bolivia", "n": "San Pablo", "c": "Bolivia", "r": "bol_potosi", "ll": [-22.17713, -67.23416], "ey": 1750, "ly": 2026, "p": 3371, "al": ["san pablo de lípez", "San Pablo de Lípez"]},
  {"key": "El Potrillo-Argentina", "n": "El Potrillo", "c": "Argentina", "r": "arg_formosa", "ll": [-23.16065, -62.0084], "ey": 1920, "ly": 2010, "p": 3371},
  {"key": "Choclococha-Peru", "n": "Choclococha", "c": "Peru", "r": "per_huancavelica", "ll": [-12.8505, -74.5431], "ey": 0, "ly": 2017, "p": 3370, "al": ["parcos", "parcostambo", "kunyar"]},
  {"key": "La Salamanca-Argentina", "n": "La Salamanca", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.82518, -64.66703], "ey": 80, "ly": 1500, "p": 3370, "al": ["rio quilpo", "agua de la pilona", "cañada del zorrino"]},
  {"key": "El Piquete-Argentina", "n": "El Piquete", "c": "Argentina", "r": "arg_jujuy", "ll": [-24.17845, -64.67906], "ey": 1850, "ly": 2022, "p": 3369},
  {"key": "Suypacha-Bolivia", "n": "Suypacha", "c": "Bolivia", "r": "crp_gobernacion_tucuman", "ll": [-21.566, -65.613], "ey": 1525, "ly": 1830, "p": 3369},
  {"key": "Uchaa Wanka-Peru", "n": "Uchaa Wanka", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.04887, -75.38432], "ey": 1000, "ly": 1530, "p": 3368, "al": ["barrio loma", "huatari joven", "huaturi viejo"]},
  {"key": "Estrella del Sur-Colombia", "n": "Estrella del Sur", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.54177, -76.01416], "ey": 500, "ly": 1500, "p": 3368},
  {"key": "Toma Luz-Peru", "n": "Toma Luz", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.54707, -75.61776], "ey": 0, "ly": 1530, "p": 3366, "al": ["animas altas", "paravientos pampa alto averia", "ánimas altas"]},
  {"key": "Lu-69. Tren Trenkuel-Chile", "n": "Lu-69. Tren Trenkuel", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-38.0955, -72.9021], "ey": -6699, "ly": 1500, "p": 3366, "al": ["lu 69 tren trenkuel", "lu-69 tren trenkuel", "Lu 69 Tren Trenkuel"]},
  {"key": "Santa Sofía-Colombia", "n": "Santa Sofía", "c": "Colombia", "r": "col_boyaca", "ll": [5.71327, -73.60271], "ey": 1850, "ly": 2025, "p": 3365},
  {"key": "Monte Castillo-Peru", "n": "Monte Castillo", "c": "Peru", "r": "per_piura", "ll": [-5.2813, -80.7147], "ey": 1850, "ly": 2017, "p": 3365},
  {"key": "San Ignacio-Argentina_2", "n": "San Ignacio", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.15101, -64.51197], "ey": 80, "ly": 1500, "p": 3365, "al": ["barranca lucas moreno", "Barranca Lucas Moreno"]},
  {"key": "Carampangue-Chile", "n": "Carampangue", "c": "Chile", "r": "chl_region_del_bio_bio", "ll": [-37.25651, -73.23107], "ey": 1850, "ly": 2017, "p": 3364, "al": ["conumo", "los maitenes", "Conumo"]},
  {"key": "Villa Yacanto-Argentina", "n": "Villa Yacanto", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.10604, -64.75439], "ey": 1850, "ly": 2022, "p": 3362},
  {"key": "San Pedro (arg_cordoba_2)-Argentina", "n": "San Pedro", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.9364, -65.21889], "ey": 1850, "ly": 2010, "p": 3361},
  {"key": "Cerro Colorado-Peru_2", "n": "Cerro Colorado", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.86555, -76.91796], "ey": -1000, "ly": 1530, "p": 3360, "al": ["adoratorio cadena norte", "campamento cerro colorado", "campamento n"]},
  {"key": "Cerro amarillo-Colombia", "n": "Cerro amarillo", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.75199, -75.58785], "ey": 0, "ly": 1500, "p": 3359},
  {"key": "Barro Blanco (col_antioquia_2)-Colombia", "n": "Barro Blanco", "c": "Colombia", "r": "col_antioquia", "ll": [6.23673, -75.47986], "ey": 1525, "ly": 2018, "p": 3358, "al": ["zona franca industrial", "cachafruto", "Zona franca industrial"]},
  {"key": "Vega de Aza-Venezuela", "n": "Vega de Aza", "c": "Venezuela", "r": "ven_tachira", "ll": [7.65565, -72.17775], "ey": 1850, "ly": 2011, "p": 3358},
  {"key": "La Laguna-Argentina_2", "n": "La Laguna", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.67873, -63.6923], "ey": 80, "ly": 1500, "p": 3358},
  {"key": "Laguna La Amistad-Argentina", "n": "Laguna La Amistad", "c": "Argentina", "r": "sc_pampas_salado_colorado", "ll": [-34.5462, -64.9115], "ey": 80, "ly": 1500, "p": 3358},
  {"key": "Putre-Chile", "n": "Putre", "c": "Chile", "r": "chl_region_de_arica_y_parinacota", "ll": [-18.49381, -69.34086], "ey": 1900, "ly": 2025, "p": 3356},
  {"key": "La Gruta-Argentina_2", "n": "La Gruta", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-48.8261, -69.3961], "ey": -10000, "ly": -1090, "p": 3355},
  {"key": "La Chorrera-Colombia", "n": "La Chorrera", "c": "Colombia", "r": "col_amazonas", "ll": [-1.44262, -72.79189], "ey": 1900, "ly": 2025, "p": 3353},
  {"key": "Jajo-Venezuela", "n": "Jajo", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.08167, -70.65], "ey": 1702, "ly": 2025, "p": 3353, "al": ["san pedro jajo", "jagi", "San Pedro Jajo"]},
  {"key": "Chilintomo-Ecuador", "n": "Chilintomo", "c": "Ecuador", "r": "vng_guayaquil_esmeraldas", "ll": [-1.901, -79.505], "ey": 1525, "ly": 1830, "p": 3352},
  {"key": "Turpo (vp_intendencia_huamanga_huancavelica)-Peru", "n": "Turpo", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-12.815, -75.515], "ey": 1525, "ly": 1825, "p": 3352},
  {"key": "Sma-Colombia", "n": "Sma", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.54, -75.33], "ey": 680, "ly": 1500, "p": 3352},
  {"key": "Tabay-Argentina", "n": "Tabay", "c": "Argentina", "r": "arg_corrientes", "ll": [-28.30596, -58.28494], "ey": 1850, "ly": 2022, "p": 3351},
  {"key": "Plataforma AB-K-Colombia", "n": "Plataforma AB-K", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.8296, -73.79337], "ey": 1300, "ly": 1500, "p": 3351},
  {"key": "Taco Ralo-Argentina", "n": "Taco Ralo", "c": "Argentina", "r": "arg_tucuman", "ll": [-27.83507, -65.1946], "ey": 1850, "ly": 2022, "p": 3348},
  {"key": "Agua Linda-Venezuela", "n": "Agua Linda", "c": "Venezuela", "r": "ven_falcon", "ll": [10.95556, -68.98889], "ey": 1850, "ly": 2025, "p": 3347},
  {"key": "Guayacancito-Venezuela", "n": "Guayacancito", "c": "Venezuela", "r": "ven_nueva_esparta", "ll": [10.94167, -64.215], "ey": 1538, "ly": 2011, "p": 3344, "al": ["gayacancito", "Gayacancito"]},
  {"key": "Sipí-Colombia", "n": "Sipí", "c": "Colombia", "r": "col_choco", "ll": [4.65262, -76.64345], "ey": 1596, "ly": 2025, "p": 3341, "al": ["san agustin zipi", "sipi", "zypy"]},
  {"key": "Monticulo Choquechamp-Peru", "n": "Monticulo Choquechamp", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.6491, -70.43591], "ey": 1300, "ly": 1530, "p": 3341, "al": ["hatun pucara choquechamp", "huchuy pucara choquechamp", "promontorio patabamba"]},
  {"key": "Reporte HF SAR (na_magdalena_cauca_muisca)-Colombia", "n": "Reporte HF SAR", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.34694, -74.76081], "ey": 500, "ly": 1500, "p": 3341, "al": ["reporte hf horno", "reporte hf roca con escalones", "Reporte HF Horno"]},
  {"key": "Choquequirao-Peru", "n": "Choquequirao", "c": "Peru", "r": "inca_cuzco_heartland", "ll": [-13.393, -72.874], "ey": 1460, "ly": 1530, "p": 3340},
  {"key": "Viña del Cerro-Chile", "n": "Viña del Cerro", "c": "Chile", "r": "inca_collasuyu", "ll": [-27.902, -70.036], "ey": 1480, "ly": 1530, "p": 3340, "al": ["copiapó inca", "Copiapó Inca"]},
  {"key": "Honcopampa-Peru_3", "n": "Honcopampa", "c": "Peru", "r": "ca_north_coast_moche_chimu", "ll": [-9.354, -77.523], "ey": 500, "ly": 1100, "p": 3340, "al": ["cerro negro", "cotu de vicos", "huamanvilca o huaman huilca"]},
  {"key": "Santa Cruz (per_ica)-Peru", "n": "Santa Cruz", "c": "Peru", "r": "per_ica", "ll": [-13.8306, -76.1456], "ey": 1850, "ly": 2017, "p": 3339},
  {"key": "Yanama (per_ayacucho)-Peru", "n": "Yanama", "c": "Peru", "r": "per_ayacucho", "ll": [-13.2083, -74.226], "ey": 1850, "ly": 2017, "p": 3336},
  {"key": "Viques-Peru", "n": "Viques", "c": "Peru", "r": "per_junin", "ll": [-12.15972, -75.23194], "ey": 1850, "ly": 2025, "p": 3335},
  {"key": "Monterralo-Colombia", "n": "Monterralo", "c": "Colombia", "r": "col_boyaca", "ll": [5.22677, -72.6738], "ey": 1525, "ly": 2018, "p": 3334, "al": ["san miguel sapatosa", "San Miguel Sapatosa"]},
  {"key": "Yunao-Colombia", "n": "Yunao", "c": "Colombia", "r": "vng_llanos_caguan", "ll": [5.684, -72.185], "ey": 1525, "ly": 1830, "p": 3334, "al": ["yunas", "Yunas"]},
  {"key": "Briceño (col_boyaca)-Colombia", "n": "Briceño", "c": "Colombia", "r": "col_boyaca", "ll": [5.69088, -73.92326], "ey": 1850, "ly": 2025, "p": 3333},
  {"key": "Villa Ana-Argentina", "n": "Villa Ana", "c": "Argentina", "r": "arg_santa_fe", "ll": [-28.49272, -59.61338], "ey": 1850, "ly": 2022, "p": 3331},
  {"key": "Cerro Shater-Peru", "n": "Cerro Shater", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.72423, -78.46141], "ey": 0, "ly": 1530, "p": 3330, "al": ["cerro china linda", "fila de atoshaico", "lanchecucho"]},
  {"key": "Santa Barbara-Peru_2", "n": "Santa Barbara", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-12.811, -74.974], "ey": 1525, "ly": 1825, "p": 3329},
  {"key": "Compositan V-Peru", "n": "Compositan V", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.51688, -78.81721], "ey": -2000, "ly": 1530, "p": 3329, "al": ["*compositan v", "cerro piñas", "cerro compositan b"]},
  {"key": "Hallonkora-Peru", "n": "Hallonkora", "c": "Peru", "r": "inca_collasuyu", "ll": [-16.11446, -70.04533], "ey": -1000, "ly": 1530, "p": 3328, "al": ["cueva pacallan", "Cueva Pacallan"]},
  {"key": "Hipodromo-Uruguay", "n": "Hipodromo", "c": "Uruguay", "r": "ury_maldonado", "ll": [-34.86685, -54.94645], "ey": 1850, "ly": 2023, "p": 3322},
  {"key": "Villa Belgrano-Argentina", "n": "Villa Belgrano", "c": "Argentina", "r": "arg_tucuman", "ll": [-27.5309, -65.61588], "ey": 1850, "ly": 2022, "p": 3320},
  {"key": "Mesa de las Palmas-Venezuela", "n": "Mesa de las Palmas", "c": "Venezuela", "r": "ven_merida", "ll": [8.40722, -71.56944], "ey": 1850, "ly": 2025, "p": 3319},
  {"key": "Corral Hotel-Chile", "n": "Corral Hotel", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.4175, -70.57417], "ey": -3000, "ly": 1500, "p": 3319},
  {"key": "Sab-Colombia", "n": "Sab", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.0574, -74.78508], "ey": 1000, "ly": 1500, "p": 3317, "al": ["hacienda bremen", "Hacienda Bremen"]},
  {"key": "Quichayá-Colombia", "n": "Quichayá", "c": "Colombia", "r": "col_cauca", "ll": [2.71862, -76.3824], "ey": 1525, "ly": 2018, "p": 3315, "al": ["pueblo nuevo", "quichaya", "Pueblo Nuevo"]},
  {"key": "Choropampa-Peru", "n": "Choropampa", "c": "Peru", "r": "per_cajamarca", "ll": [-6.37111, -78.41194], "ey": 1850, "ly": 2025, "p": 3314},
  {"key": "La Venta Baja (la Venta)-Peru", "n": "La Venta Baja (la Venta)", "c": "Peru", "r": "per_ica", "ll": [-14.2892, -75.6792], "ey": 1850, "ly": 2017, "p": 3314, "al": ["la venta baja"]},
  {"key": "Laguna Brava-Argentina", "n": "Laguna Brava", "c": "Argentina", "r": "arg_corrientes", "ll": [-27.49333, -58.71611], "ey": 1850, "ly": 2010, "p": 3314},
  {"key": "Terraza-Colombia", "n": "Terraza", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.25775, -75.41739], "ey": 500, "ly": 1500, "p": 3314},
  {"key": "Acaboa-Venezuela", "n": "Acaboa", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [12.017, -70.115], "ey": 1538, "ly": 1830, "p": 3312},
  {"key": "Villa Atuel-Argentina", "n": "Villa Atuel", "c": "Argentina", "r": "arg_mendoza", "ll": [-34.8316, -67.92286], "ey": 1850, "ly": 2010, "p": 3311},
  {"key": "Huenucheo-Chile", "n": "Huenucheo", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-36.90449, -72.4549], "ey": 0, "ly": 1500, "p": 3311},
  {"key": "Collpa Jahuira-Peru", "n": "Collpa Jahuira", "c": "Peru", "r": "inca_collasuyu", "ll": [-16.41886, -69.46916], "ey": 0, "ly": 1532, "p": 3309, "al": ["ccara circa", "huerta camaña", "jisca collpa jahuira"]},
  {"key": "Perico-Colombia_2", "n": "Perico", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.27361, -74.75917], "ey": 500, "ly": 1500, "p": 3309},
  {"key": "San Ramón (chl_region_de_la_araucania)-Chile", "n": "San Ramón", "c": "Chile", "r": "chl_region_de_la_araucania", "ll": [-38.86958, -72.39236], "ey": 1920, "ly": 2017, "p": 3307},
  {"key": "Murillo-Colombia_2", "n": "Murillo", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [4.7425, -76.83565], "ey": 650, "ly": 1500, "p": 3307},
  {"key": "El Campo Nuevo- Faltriquera- Trompillo-Venezuela", "n": "El Campo Nuevo- Faltriquera- Trompillo", "c": "Venezuela", "r": "ven_yaracuy", "ll": [10.21833, -68.79556], "ey": 1850, "ly": 2011, "p": 3302},
  {"key": "Ancasti-Argentina", "n": "Ancasti", "c": "Argentina", "r": "arg_catamarca", "ll": [-28.81249, -65.49974], "ey": 1740, "ly": 2022, "p": 3302, "al": ["anacaste", "anascate", "Anacaste"]},
  {"key": "Los Telares-Argentina", "n": "Los Telares", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-28.98498, -63.45056], "ey": 1850, "ly": 2022, "p": 3302},
  {"key": "La Victoria (col_cundinamarca)-Colombia", "n": "La Victoria", "c": "Colombia", "r": "col_cundinamarca", "ll": [5.52379, -74.23439], "ey": 1850, "ly": 2025, "p": 3301},
  {"key": "La Cumbre-Colombia_2", "n": "La Cumbre", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.705, -74.74611], "ey": 1300, "ly": 1500, "p": 3300},
  {"key": "Ite-Peru", "n": "Ite", "c": "Peru", "r": "per_tacna", "ll": [-17.86167, -70.96583], "ey": 1850, "ly": 2025, "p": 3299},
  {"key": "General Lagos-Chile", "n": "General Lagos", "c": "Chile", "r": "chl_region_de_arica_y_parinacota", "ll": [-17.83222, -69.55359], "ey": 1900, "ly": 2025, "p": 3299}
]

all_src = []
for p in glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json'):
    if 'wave1' in p: continue
    d = json.load(open(p, encoding='utf-8'))
    fn = os.path.basename(p)
    setts = d.get('settlements', [])
    if isinstance(setts, dict): setts = list(setts.values())
    for s in setts:
        if not isinstance(s, dict): continue
        lat = s.get('lat') or (s.get('coords')[1] if isinstance(s.get('coords'), list) and len(s.get('coords'))==2 else None)
        lng = s.get('lng') or s.get('lon') or (s.get('coords')[0] if isinstance(s.get('coords'), list) and len(s.get('coords'))==2 else None)
        if lat is None or lng is None: continue
        all_src.append((fn, float(lat), float(lng), s))

for item in INPUT:
    ilat, ilng = item['ll']
    matches = []
    for fn, slat, slng, s in all_src:
        if abs(slat - ilat) < 0.05 and abs(slng - ilng) < 0.05:
            dist = math.hypot(slat - ilat, slng - ilng)
            if dist < 0.02:
                matches.append((dist, fn, {k:v for k,v in s.items() if k not in ('population','years','timeseries')}))
    matches.sort(key=lambda x: x[0])
    if matches:
        print(f"=== {item['key']} ({item['n']}, {item['c']}) ===")
        for dist, fn, info in matches[:3]:
            print(f"  [{fn} d={dist:.4f}] {json.dumps(info, ensure_ascii=False)}")
