import json, time, urllib.request, urllib.parse, os

INPUT = [
  {"key": "Luya Viejo-Peru", "n": "Luya Viejo", "c": "Peru", "r": "per_amazonas", "ll": [-6.1275, -78.085], "ey": 1525, "ly": 2025, "p": 7383, "al": ["luya", "Luya"]},
  {"key": "Huaquirca-Peru", "n": "Huaquirca", "c": "Peru", "r": "per_apurimac", "ll": [-14.33944, -72.895], "ey": 1525, "ly": 2025, "p": 7381},
  {"key": "San Isidro de Quiucmal-Peru", "n": "San Isidro de Quiucmal", "c": "Peru", "r": "per_amazonas", "ll": [-6.0858, -78.178], "ey": 1525, "ly": 2017, "p": 7376, "al": ["jacapatos", "Jacapatos"]},
  {"key": "Gullancay-Ecuador", "n": "Gullancay", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.746, -78.918], "ey": 1525, "ly": 1830, "p": 7374},
  {"key": "San Francisco Del Vergel-Ecuador", "n": "San Francisco Del Vergel", "c": "Ecuador", "r": "ecu_zamora_chinchipe", "ll": [-4.67794, -79.04476], "ey": 1525, "ly": 2025, "p": 7371, "al": ["vergel", "vegel", "Vergel"]},
  {"key": "Chisquilla-Peru", "n": "Chisquilla", "c": "Peru", "r": "per_amazonas", "ll": [-5.8975, -77.78611], "ey": 1525, "ly": 2025, "p": 7371},
  {"key": "Umachiri-Peru", "n": "Umachiri", "c": "Peru", "r": "per_puno", "ll": [-14.85389, -70.75389], "ey": 1525, "ly": 2025, "p": 7368, "al": ["umachari", "Umachari"]},
  {"key": "El Ángel-Ecuador", "n": "El Ángel", "c": "Ecuador", "r": "ecu_carchi", "ll": [0.65299, -77.99179], "ey": 1850, "ly": 2025, "p": 7367},
  {"key": "Sisicaya-Peru", "n": "Sisicaya", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.027, -76.631], "ey": 1525, "ly": 1825, "p": 7367},
  {"key": "Gamarra-Peru", "n": "Gamarra", "c": "Peru", "r": "per_apurimac", "ll": [-13.87167, -72.50833], "ey": 1525, "ly": 2025, "p": 7366, "al": ["palpacachi", "palpacchi", "Palpacachi"]},
  {"key": "Los Huacos-Peru", "n": "Los Huacos", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.09802, -77.61796], "ey": -2000, "ly": 1530, "p": 7362, "al": ["area 1 de retiro de condición parcial de cerro colorado parcela", "area 10 de retiro de condición de cerro colorado parcela", "area 11 de retiro de condición parcial de cerro colorado parcela"]},
  {"key": "El Bajo-Venezuela", "n": "El Bajo", "c": "Venezuela", "r": "ven_zulia", "ll": [10.52569, -71.63048], "ey": 1850, "ly": 2025, "p": 7361},
  {"key": "Quinjalca-Peru", "n": "Quinjalca", "c": "Peru", "r": "per_amazonas", "ll": [-6.09139, -77.67861], "ey": 1525, "ly": 2025, "p": 7361},
  {"key": "Cochabamba (per_ancash_2)-Peru", "n": "Cochabamba", "c": "Peru", "r": "per_ancash", "ll": [-9.495, -77.85944], "ey": 1525, "ly": 2025, "p": 7356, "al": ["na", "NA"]},
  {"key": "Lamud-Peru", "n": "Lamud", "c": "Peru", "r": "per_amazonas", "ll": [-6.13917, -77.95222], "ey": 1525, "ly": 2025, "p": 7355, "al": ["lámud", "lamut", "Lámud"]},
  {"key": "Siccican-Peru", "n": "Siccican", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-9.308, -77.159], "ey": 1525, "ly": 1825, "p": 7355},
  {"key": "Quilla-Peru", "n": "Quilla", "c": "Peru", "r": "per_ayacucho", "ll": [-13.6952, -74.0583], "ey": 1525, "ly": 2017, "p": 7354},
  {"key": "Totora (vp_intendencia_cusco)-Peru", "n": "Totora", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-14.38, -71.583], "ey": 1525, "ly": 1825, "p": 7354},
  {"key": "Archidona (ecu_napo)-Ecuador", "n": "Archidona", "c": "Ecuador", "r": "ecu_napo", "ll": [-0.91271, -77.80832], "ey": 1560, "ly": 2022, "p": 7353, "al": ["ciudad de archidona", "la maravilla", "santa elena"]},
  {"key": "Capillucas-Peru", "n": "Capillucas", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.708, -75.97], "ey": 1525, "ly": 1825, "p": 7353},
  {"key": "Quinocay-Peru", "n": "Quinocay", "c": "Peru", "r": "per_lima", "ll": [-12.36222, -76.22639], "ey": 1525, "ly": 2025, "p": 7348, "al": ["quincocay", "Quincocay"]},
  {"key": "Inguap-Colombia", "n": "Inguap", "c": "Colombia", "r": "inca_chinchaysuyu", "ll": [1.7, -78.76], "ey": -794, "ly": 1532, "p": 7348, "al": ["buchel", "el balsal", "inguapí"]},
  {"key": "Chachas-Peru", "n": "Chachas", "c": "Peru", "r": "per_arequipa", "ll": [-15.50139, -72.27056], "ey": 1525, "ly": 2025, "p": 7347},
  {"key": "Novirao-Colombia", "n": "Novirao", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.544, -76.53], "ey": 1525, "ly": 1830, "p": 7346},
  {"key": "Abra Cerro Salinas-Peru", "n": "Abra Cerro Salinas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.5049, -79.78804], "ey": -2000, "ly": 1532, "p": 7346, "al": ["batan grande", "bosque pomac", "cerro tambo real"]},
  {"key": "Cubijíes-Ecuador", "n": "Cubijíes", "c": "Ecuador", "r": "ecu_chimborazo", "ll": [-1.65713, -78.60213], "ey": 1525, "ly": 2025, "p": 7344, "al": ["cubijies", "Cubijies"]},
  {"key": "Pepa de Huso-Ecuador", "n": "Pepa de Huso", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-1.03, -80.34], "ey": -870, "ly": -170, "p": 7343},
  {"key": "Huacllan-Peru", "n": "Huacllan", "c": "Peru", "r": "per_ancash", "ll": [-9.79806, -77.67528], "ey": 1525, "ly": 2025, "p": 7342, "al": ["huacllán", "Huacllán"]},
  {"key": "Don Ariel-Argentina", "n": "Don Ariel", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-51.91456, -69.74166], "ey": -5900, "ly": -77, "p": 7342, "al": ["el volcan", "El Volcan"]},
  {"key": "Ventarron-Peru_2", "n": "Ventarron", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.81199, -79.75419], "ey": -2000, "ly": 1530, "p": 7341, "al": ["bola de oro", "boro", "casa blanca"]},
  {"key": "Wamanmarka-Peru", "n": "Wamanmarka", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.40324, -72.07734], "ey": -1000, "ly": 1530, "p": 7341, "al": ["coropuna", "qhawanamarka", "Coropuna"]},
  {"key": "Turpo-Peru", "n": "Turpo", "c": "Peru", "r": "per_apurimac", "ll": [-13.78556, -73.47417], "ey": 1525, "ly": 2025, "p": 7337},
  {"key": "Parcco-Peru", "n": "Parcco", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.999, -71.888], "ey": 1525, "ly": 1825, "p": 7331, "al": ["parco", "Parco"]},
  {"key": "Cancha Cancha-Peru", "n": "Cancha Cancha", "c": "Peru", "r": "per_ayacucho", "ll": [-13.6061, -74.313], "ey": 1525, "ly": 2017, "p": 7330, "al": ["canchacancha", "Canchacancha"]},
  {"key": "Huayllati-Peru", "n": "Huayllati", "c": "Peru", "r": "per_apurimac", "ll": [-13.92806, -72.48444], "ey": 1525, "ly": 2025, "p": 7330, "al": ["guaillate", "huayllay", "Guaillate"]},
  {"key": "Cupisnique-Peru", "n": "Cupisnique", "c": "Peru", "r": "per_cajamarca", "ll": [-7.34889, -79.02972], "ey": 1525, "ly": 2025, "p": 7328, "al": ["trinidad", "trinidad de chetu", "Trinidad"]},
  {"key": "San Francisco-Peru_2", "n": "San Francisco", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-8.1, -77.936], "ey": 1525, "ly": 1825, "p": 7328},
  {"key": "San Salvador de Quije-Peru", "n": "San Salvador de Quije", "c": "Peru", "r": "per_ayacucho", "ll": [-13.96833, -73.73472], "ey": 1525, "ly": 2025, "p": 7322, "al": ["quixe", "Quixe"]},
  {"key": "Cojitambo-Ecuador", "n": "Cojitambo", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.75609, -78.88715], "ey": 1525, "ly": 2025, "p": 7321, "al": ["cogitambo", "pillcomarca", "Cogitambo"]},
  {"key": "El Paují-Venezuela", "n": "El Paují", "c": "Venezuela", "r": "ven_falcon", "ll": [10.81833, -69.61556], "ey": 1850, "ly": 2025, "p": 7320},
  {"key": "Succha-Peru", "n": "Succha", "c": "Peru", "r": "per_ancash", "ll": [-9.82306, -77.64972], "ey": 1525, "ly": 2025, "p": 7319, "al": ["sudcha", "Sudcha"]},
  {"key": "Guachipay-Colombia", "n": "Guachipay", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.269, -74.566], "ey": 1525, "ly": 1830, "p": 7316},
  {"key": "San Sebastian Yumbo-Colombia", "n": "San Sebastian Yumbo", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [3.582, -76.493], "ey": 1525, "ly": 1830, "p": 7314, "ex": [{"date": "1968.1.1", "name": "Yumbo"}]},
  {"key": "Aguaclara (col_valle_del_cauca)-Colombia", "n": "Aguaclara", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.67305, -76.94814], "ey": 1850, "ly": 2018, "p": 7311},
  {"key": "Dureno-Ecuador", "n": "Dureno", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [0.05102, -76.6765], "ey": 1920, "ly": 2025, "p": 7308},
  {"key": "Jadán-Ecuador", "n": "Jadán", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.89679, -78.85279], "ey": 1525, "ly": 2025, "p": 7303, "al": ["jadan", "Jadan"]},
  {"key": "Calicampo-Peru", "n": "Calicampo", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.90654, -77.48993], "ey": -3000, "ly": 1530, "p": 7300, "al": ["cerro cazadores", "cerro orcón", "cerro peñico"]},
  {"key": "Molleturo-Ecuador", "n": "Molleturo", "c": "Ecuador", "r": "ecu_azuay", "ll": [-2.71034, -79.35431], "ey": 1525, "ly": 2025, "p": 7298},
  {"key": "San Pedro-Colombia_2", "n": "San Pedro", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [8.764, -73.798], "ey": 1525, "ly": 1830, "p": 7297},
  {"key": "Caja-Peru", "n": "Caja", "c": "Peru", "r": "per_huancavelica", "ll": [-12.91722, -74.46583], "ey": 1525, "ly": 2025, "p": 7296, "al": ["caja espirituo", "espiritucaja", "Caja Espirituo"]},
  {"key": "Coya-Peru", "n": "Coya", "c": "Peru", "r": "per_cusco", "ll": [-13.38639, -71.89833], "ey": 1525, "ly": 2025, "p": 7293},
  {"key": "José Gregorio Hernández-Venezuela", "n": "José Gregorio Hernández", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.36012, -70.69755], "ey": 1850, "ly": 2025, "p": 7291},
  {"key": "Huampara-Peru", "n": "Huampara", "c": "Peru", "r": "per_lima", "ll": [-12.36028, -76.16722], "ey": 1525, "ly": 2025, "p": 7291},
  {"key": "San Nicolás (col_antioquia_2)-Colombia", "n": "San Nicolás", "c": "Colombia", "r": "col_antioquia", "ll": [6.47812, -75.8211], "ey": 1525, "ly": 2018, "p": 7290, "al": ["obregon", "Obregon"]},
  {"key": "Chiuchin-Peru", "n": "Chiuchin", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.927, -76.78], "ey": 1525, "ly": 1825, "p": 7290, "al": ["chichin", "Chichin"]},
  {"key": "San Teodoro Collac-Peru", "n": "San Teodoro Collac", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-11.176, -75.359], "ey": 1525, "ly": 1825, "p": 7290, "al": ["fuerte de collac", "Fuerte de Collac"]},
  {"key": "Huacar-Peru_2", "n": "Huacar", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.967, -76.948], "ey": 1525, "ly": 1825, "p": 7288},
  {"key": "Cascabamba-Peru", "n": "Cascabamba", "c": "Peru", "r": "per_apurimac", "ll": [-13.6984, -73.5871], "ey": 1525, "ly": 2017, "p": 7286, "al": ["ccantupata", "ccollcca", "huallantay"]},
  {"key": "Cambio Puente-Peru", "n": "Cambio Puente", "c": "Peru", "r": "per_la_libertad", "ll": [-8.998, -78.5558], "ey": 1850, "ly": 2017, "p": 7284},
  {"key": "Moruy-Venezuela", "n": "Moruy", "c": "Venezuela", "r": "ven_falcon", "ll": [11.82667, -69.98333], "ey": 1538, "ly": 2025, "p": 7283},
  {"key": "San Antonio de Padua de la Sal-Colombia", "n": "San Antonio de Padua de la Sal", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.636, -75.964], "ey": 1538, "ly": 1830, "p": 7283, "al": ["belalcazar", "gal", "mesa de paez"]},
  {"key": "Muzga-Peru", "n": "Muzga", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.995, -76.977], "ey": 1525, "ly": 1825, "p": 7281, "al": ["lacsanga", "musca", "yacsanga"]},
  {"key": "El Cerrito-Colombia_2", "n": "El Cerrito", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [10.829, -74.763], "ey": 1601, "ly": 1744, "p": 7280},
  {"key": "San Pedro de Cusi-Peru", "n": "San Pedro de Cusi", "c": "Peru", "r": "per_lima", "ll": [-12.5633, -75.9075], "ey": 1525, "ly": 2017, "p": 7278, "al": ["cusi", "Cusi"]},
  {"key": "Caramarca-Peru", "n": "Caramarca", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-7.78, -78.024], "ey": 1542, "ly": 1825, "p": 7273},
  {"key": "Gapal-Ecuador", "n": "Gapal", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.916, -78.99], "ey": 1525, "ly": 1830, "p": 7272},
  {"key": "Castillo Jesus Maria-Peru", "n": "Castillo Jesus Maria", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.03198, -78.83355], "ey": -1000, "ly": 1530, "p": 7271, "al": ["cerro la cruz", "cerro la cruz o el palmo", "ciudad de dios b"]},
  {"key": "Puente Durand-Peru", "n": "Puente Durand", "c": "Peru", "r": "per_huanuco", "ll": [-9.5573, -76.0169], "ey": -2000, "ly": 2017, "p": 7269, "al": ["chinchao", "chincho", "Chinchao"]},
  {"key": "Ichuña-Peru", "n": "Ichuña", "c": "Peru", "r": "per_moquegua", "ll": [-16.14056, -70.53556], "ey": 1525, "ly": 2025, "p": 7267},
  {"key": "La Punta-Colombia", "n": "La Punta", "c": "Colombia", "r": "col_cundinamarca", "ll": [4.79587, -74.20759], "ey": 1850, "ly": 2018, "p": 7266},
  {"key": "Chiguaza-Ecuador", "n": "Chiguaza", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-2.04416, -77.98309], "ey": 1920, "ly": 2025, "p": 7266},
  {"key": "Uningambal-Peru", "n": "Uningambal", "c": "Peru", "r": "per_la_libertad", "ll": [-8.262, -78.3861], "ey": 1525, "ly": 2017, "p": 7266},
  {"key": "Buena Esperanza de Rere-Chile", "n": "Buena Esperanza de Rere", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-37.132, -72.727], "ey": 1721, "ly": 1830, "p": 7266, "al": ["buena esperanza", "estancia del rey", "Buena Esperanza"]},
  {"key": "Saywa - Yaccacheta-Peru", "n": "Saywa - Yaccacheta", "c": "Peru", "r": "inca_antisuyu", "ll": [-13.5939, -71.56647], "ey": 500, "ly": 1530, "p": 7266, "al": ["hatuncancha", "racayraniyoq", "raccaqniyoq"]},
  {"key": "Guacamayal-Colombia", "n": "Guacamayal", "c": "Colombia", "r": "col_magdalena", "ll": [10.75069, -74.15877], "ey": 1850, "ly": 2018, "p": 7265, "al": ["agustina", "estación sevilla", "paulina"]},
  {"key": "Lucuchanga-Peru", "n": "Lucuchanga", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.751, -72.971], "ey": 1525, "ly": 1825, "p": 7264},
  {"key": "Timar-Chile", "n": "Timar", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-18.75, -69.691], "ey": 1525, "ly": 1825, "p": 7263, "al": ["trinar", "Trinar"]},
  {"key": "El Carmelo-Colombia", "n": "El Carmelo", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.40261, -76.41644], "ey": 1850, "ly": 2018, "p": 7261, "al": ["cantalomota", "la gloria", "Cantalomota"]},
  {"key": "Santa Isabel de Caype-Peru", "n": "Santa Isabel de Caype", "c": "Peru", "r": "per_apurimac", "ll": [-13.7971, -72.8324], "ey": 1525, "ly": 2017, "p": 7261, "al": ["caypi", "Caypi"]},
  {"key": "Ayalan-Ecuador", "n": "Ayalan", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-2.58359, -80.26596], "ey": -2191, "ly": 76, "p": 7260},
  {"key": "Challacota-Bolivia", "n": "Challacota", "c": "Bolivia", "r": "bol_oruro", "ll": [-19.25498, -67.75961], "ey": 1525, "ly": 2024, "p": 7259, "al": ["challacata", "Challacata"]},
  {"key": "Circa-Peru", "n": "Circa", "c": "Peru", "r": "per_apurimac", "ll": [-13.87833, -72.87583], "ey": 1525, "ly": 2025, "p": 7254, "al": ["syrca", "Syrca"]},
  {"key": "Coper-Colombia", "n": "Coper", "c": "Colombia", "r": "col_cundinamarca", "ll": [5.47507, -74.04564], "ey": 1525, "ly": 2025, "p": 7253, "al": ["copere", "Copere"]},
  {"key": "El Eno-Ecuador", "n": "El Eno", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [-0.06753, -76.87857], "ey": 1920, "ly": 2025, "p": 7253},
  {"key": "San Cristóbal (ecu_canar)-Ecuador", "n": "San Cristóbal", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.83804, -78.84887], "ey": 1525, "ly": 2025, "p": 7252, "al": ["san cristobal", "San Cristobal"]},
  {"key": "Morro-Ecuador", "n": "Morro", "c": "Ecuador", "r": "ecu_guayas", "ll": [-2.56136, -80.30825], "ey": 1525, "ly": 2025, "p": 7251},
  {"key": "Tuama-Argentina", "n": "Tuama", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.005, -64.107], "ey": 1536, "ly": 1830, "p": 7251, "al": ["tocama", "Tocama"]},
  {"key": "Millo-Peru", "n": "Millo", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.43601, -71.88495], "ey": -1000, "ly": 1530, "p": 7249, "al": ["hacienda \"las canduelas\" ó \"pie de cuesta", "hacienda la suárez", "la calderón"]},
  {"key": "Mutca-Peru", "n": "Mutca", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-14.216, -73.308], "ey": 1525, "ly": 1825, "p": 7248, "al": ["muctu", "Muctu"]},
  {"key": "Nanchoc-Peru", "n": "Nanchoc", "c": "Peru", "r": "per_lambayeque", "ll": [-6.95944, -79.2425], "ey": 1525, "ly": 2025, "p": 7245, "al": ["nancho", "Nancho"]}
]

hgis_path = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json"
hgis_hits = {}
if os.path.exists(hgis_path):
    hgis = json.load(open(hgis_path, encoding="utf-8"))
    setts = hgis.get("settlements", [])
    if isinstance(setts, dict):
        setts = list(setts.values())
    for item in INPUT:
        lat, lon = item["ll"]
        hits = []
        for s in setts:
            c = s.get("coords") or [s.get("lat"), s.get("lon") or s.get("lng")]
            if c and c[0] is not None and c[1] is not None:
                if abs(float(c[0]) - lat) < 0.03 and abs(float(c[1]) - lon) < 0.03:
                    hits.append({k: v for k, v in s.items() if k != "population"})
        if hits:
            hgis_hits[item["key"]] = hits

with open("tests/chunk015_hgis.json", "w", encoding="utf-8") as f:
    json.dump(hgis_hits, f, ensure_ascii=False, indent=2)
print("HGIS matches:", len(hgis_hits))

HEADERS = {'User-Agent': 'SVEA-Toponymy-Research/1.0'}
def api_get(url):
    time.sleep(0.15)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

wiki_out = {}
for idx, item in enumerate(INPUT):
    key = item["key"]
    lat, lon = item["ll"]
    name = item["n"]
    country = item["c"]
    rec = {"n": name, "c": country, "r": item["r"], "ll": item["ll"], "ey": item["ey"], "ly": item["ly"]}
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
        d = api_get(u)
        rec["geo_es"] = [{"t": x["title"], "d": x["dist"]} for x in d.get("query", {}).get("geosearch", [])]
    except Exception as e:
        rec["geo_err"] = str(e)
    try:
        q = urllib.parse.quote(f"{name} {country}")
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        d = api_get(u)
        rec["sr_es"] = [x["title"] for x in d.get("query", {}).get("search", [])]
    except Exception as e:
        rec["sr_err"] = str(e)
    cands = []
    for g in rec.get("geo_es", []):
        if g["t"] not in cands:
            cands.append(g["t"])
    for s in rec.get("sr_es", []):
        if s not in cands:
            cands.append(s)
    cands = cands[:3]
    rec["extracts"] = {}
    if cands:
        try:
            t_param = urllib.parse.quote("|".join(cands))
            u = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=0&explaintext=1&exchars=1800&titles={t_param}&format=json"
            d = api_get(u)
            for pid, p in d.get("query", {}).get("pages", {}).items():
                if "extract" in p:
                    rec["extracts"][p["title"]] = p["extract"]
        except Exception as e:
            rec["ext_err"] = str(e)
    wiki_out[key] = rec
    if (idx + 1) % 15 == 0:
        print(f"Processed {idx+1}/90")
        with open("tests/chunk015_wiki.json", "w", encoding="utf-8") as f:
            json.dump(wiki_out, f, ensure_ascii=False, indent=2)

with open("tests/chunk015_wiki.json", "w", encoding="utf-8") as f:
    json.dump(wiki_out, f, ensure_ascii=False, indent=2)
print("Done all 90!")
