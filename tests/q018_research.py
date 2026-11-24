import glob, json, math, os, time, urllib.parse, urllib.request

INPUT = [
  {"key": "Las Lajas-Colombia", "n": "Las Lajas", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.58273, -78.70609], "ey": 1000, "ly": 1500, "p": 7002, "al": ["cajapí", "franco", "juan domingo"]},
  {"key": "Tarapoa-Ecuador", "n": "Tarapoa", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [-0.1247, -76.34551], "ey": 1920, "ly": 2025, "p": 7001},
  {"key": "Choquecancha-Peru", "n": "Choquecancha", "c": "Peru", "r": "per_cusco", "ll": [-13.0397, -72.036], "ey": 1525, "ly": 2017, "p": 7001, "al": ["chuquicancha", "chuquicocha", "Chuquicancha"]},
  {"key": "La Libertad-Peru", "n": "La Libertad", "c": "Peru", "r": "per_ancash", "ll": [-9.63306, -77.74139], "ey": 1525, "ly": 2025, "p": 7001, "al": ["cajamarquilla", "Cajamarquilla"]},
  {"key": "Moretecocha-Ecuador_2", "n": "Moretecocha", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-1.61, -77.35], "ey": 357, "ly": 1438, "p": 7001},
  {"key": "Alto Jahuel-Chile", "n": "Alto Jahuel", "c": "Chile", "r": "chl_region_metropolitana_de_santiago", "ll": [-33.73753, -70.68519], "ey": 1850, "ly": 2017, "p": 7000},
  {"key": "Toro-Peru", "n": "Toro", "c": "Peru", "r": "per_arequipa", "ll": [-15.26444, -72.92833], "ey": 1525, "ly": 2025, "p": 6999},
  {"key": "Tumbabarreto-Colombia", "n": "Tumbabarreto", "c": "Colombia", "r": "col_caldas", "ll": [5.43811, -75.70027], "ey": 1525, "ly": 2018, "p": 6996, "al": ["quiebralomo", "san sebastian quiebralomo", "barrio de sevilla"]},
  {"key": "Maucallacta-Peru", "n": "Maucallacta", "c": "Peru", "r": "per_apurimac", "ll": [-13.5601, -73.4934], "ey": 1525, "ly": 2017, "p": 6996, "al": ["ataccara", "piscobamba", "Ataccara"]},
  {"key": "Tocmoche-Peru", "n": "Tocmoche", "c": "Peru", "r": "per_lambayeque", "ll": [-6.41278, -79.36083], "ey": 1525, "ly": 2025, "p": 6995},
  {"key": "Andajes-Peru", "n": "Andajes", "c": "Peru", "r": "per_lima", "ll": [-10.79278, -76.90917], "ey": 1000, "ly": 2025, "p": 6994, "al": ["chimba", "antashuay", "antashuay-poac guaranga"]},
  {"key": "Quípama-Colombia", "n": "Quípama", "c": "Colombia", "r": "col_cundinamarca", "ll": [5.52055, -74.18003], "ey": 1525, "ly": 2025, "p": 6990, "al": ["quipama", "Quipama"]},
  {"key": "La Punta-Chile", "n": "La Punta", "c": "Chile", "r": "chl_region_del_libertador_bernardo_o_higgins", "ll": [-34.01085, -70.64988], "ey": 1525, "ly": 2017, "p": 6990},
  {"key": "Otoca-Peru", "n": "Otoca", "c": "Peru", "r": "per_ayacucho", "ll": [-14.49, -74.68667], "ey": 1525, "ly": 2025, "p": 6989},
  {"key": "Tangui-Peru", "n": "Tangui", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.383, -76.383], "ey": 1525, "ly": 1825, "p": 6987, "al": ["tanqui", "Tanqui"]},
  {"key": "Aquia-Peru", "n": "Aquia", "c": "Peru", "r": "per_ancash", "ll": [-10.07444, -77.145], "ey": 1525, "ly": 2025, "p": 6986},
  {"key": "Pampas (vp_intendencia_lima)-Peru", "n": "Pampas", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.314, -76.777], "ey": 1525, "ly": 1825, "p": 6984},
  {"key": "San Juan de Viscas-Peru", "n": "San Juan de Viscas", "c": "Peru", "r": "per_lima", "ll": [-12.3273, -76.2787], "ey": 1525, "ly": 2017, "p": 6983, "al": ["viscas", "Viscas"]},
  {"key": "Chibunga-Ecuador", "n": "Chibunga", "c": "Ecuador", "r": "ecu_manabi", "ll": [-0.03782, -79.74084], "ey": 1850, "ly": 2025, "p": 6982},
  {"key": "Páez (ven_barinas)-Venezuela", "n": "Páez", "c": "Venezuela", "r": "ven_barinas", "ll": [8.03111, -70.00667], "ey": 1850, "ly": 2025, "p": 6981},
  {"key": "Condormarca-Peru", "n": "Condormarca", "c": "Peru", "r": "per_la_libertad", "ll": [-7.54667, -77.59972], "ey": 1440, "ly": 2025, "p": 6981, "al": ["cundurmarca", "condromarca", "cundarmarca"]},
  {"key": "Buena Vista (ven_lara)-Venezuela", "n": "Buena Vista", "c": "Venezuela", "r": "ven_lara", "ll": [9.88667, -69.48111], "ey": 1850, "ly": 2025, "p": 6979},
  {"key": "Viraco-Peru", "n": "Viraco", "c": "Peru", "r": "per_arequipa", "ll": [-15.65833, -72.525], "ey": 1525, "ly": 2025, "p": 6978},
  {"key": "San Francisco Socoroma-Chile", "n": "San Francisco Socoroma", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-18.264, -69.602], "ey": 1525, "ly": 1825, "p": 6978},
  {"key": "La Capilla-Colombia", "n": "La Capilla", "c": "Colombia", "r": "col_cundinamarca", "ll": [5.09569, -73.44435], "ey": 1793, "ly": 2025, "p": 6977, "al": ["la capilla de tenza", "La Capilla de Tenza"]},
  {"key": "Anaica-Peru", "n": "Anaica", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.583, -76.67], "ey": 1525, "ly": 1825, "p": 6977, "al": ["pampacocha", "Pampacocha"]},
  {"key": "Cantagallo-Venezuela", "n": "Cantagallo", "c": "Venezuela", "r": "ven_carabobo", "ll": [9.78852, -67.43191], "ey": 1850, "ly": 2025, "p": 6976},
  {"key": "Auquimarca-Peru_2", "n": "Auquimarca", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.951, -76.914], "ey": 1525, "ly": 1825, "p": 6976, "al": ["anquimarca", "Anquimarca"]},
  {"key": "San Ignacio (per_la_libertad)-Peru", "n": "San Ignacio", "c": "Peru", "r": "per_la_libertad", "ll": [-7.8312, -78.7152], "ey": 1525, "ly": 2017, "p": 6974, "al": ["chuite", "Chuite"]},
  {"key": "Juan Pablo Peñaloza-Venezuela", "n": "Juan Pablo Peñaloza", "c": "Venezuela", "r": "ven_tachira", "ll": [8.03722, -71.85444], "ey": 1850, "ly": 2025, "p": 6973},
  {"key": "Sabaino-Peru", "n": "Sabaino", "c": "Peru", "r": "per_apurimac", "ll": [-14.31333, -72.94528], "ey": 1525, "ly": 2025, "p": 6972, "al": ["sabayno", "Sabayno"]},
  {"key": "Malchinguí-Ecuador", "n": "Malchinguí", "c": "Ecuador", "r": "ecu_pichincha", "ll": [0.05794, -78.34935], "ey": 1850, "ly": 2025, "p": 6971},
  {"key": "Pallac-Peru_2", "n": "Pallac", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.349, -76.807], "ey": 1525, "ly": 1825, "p": 6970},
  {"key": "Puncurin-Peru", "n": "Puncurin", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.80468, -76.79086], "ey": 1438, "ly": 1530, "p": 6970, "al": ["carmen grande de quillin", "cochabamba", "nueva palestino"]},
  {"key": "Calpi-Ecuador", "n": "Calpi", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.61671, -78.75715], "ey": 1525, "ly": 2025, "p": 6969},
  {"key": "Guayrapongo-Ecuador", "n": "Guayrapongo", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.512, -78.927], "ey": 1525, "ly": 1830, "p": 6969},
  {"key": "Santo Domingo de Menahermosa-Peru", "n": "Santo Domingo de Menahermosa", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-11.391, -75.63], "ey": 1542, "ly": 1825, "p": 6969},
  {"key": "Pararin-Peru", "n": "Pararin", "c": "Peru", "r": "per_ancash", "ll": [-10.05, -77.65444], "ey": 1525, "ly": 2025, "p": 6967, "al": ["pararín", "Pararín"]},
  {"key": "Zaacata-Peru", "n": "Zaacata", "c": "Peru", "r": "vp_intendencia_puno", "ll": [-16.164, -69.515], "ey": 1525, "ly": 1825, "p": 6966},
  {"key": "Arahuay-Peru", "n": "Arahuay", "c": "Peru", "r": "per_lima", "ll": [-11.62139, -76.67028], "ey": 1525, "ly": 2025, "p": 6959},
  {"key": "San Lorenzo (vp_intendencia_lima)-Peru", "n": "San Lorenzo", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.553, -76.682], "ey": 1525, "ly": 1825, "p": 6959},
  {"key": "Mucuruba-Venezuela", "n": "Mucuruba", "c": "Venezuela", "r": "ven_merida", "ll": [8.71, -70.98833], "ey": 1538, "ly": 2025, "p": 6958},
  {"key": "Nava-Peru", "n": "Nava", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.731, -76.835], "ey": 1525, "ly": 1825, "p": 6958, "al": ["naba", "Naba"]},
  {"key": "Pampallacta (per_apurimac)-Peru", "n": "Pampallacta", "c": "Peru", "r": "per_apurimac", "ll": [-14.0043, -73.0969], "ey": 1525, "ly": 2017, "p": 6957, "al": ["pampayacta", "Pampayacta"]},
  {"key": "Uchumarca-Peru", "n": "Uchumarca", "c": "Peru", "r": "per_la_libertad", "ll": [-7.04722, -77.80556], "ey": 1525, "ly": 2025, "p": 6957},
  {"key": "Casiri-Peru", "n": "Casiri", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-15.33, -73.34], "ey": 1525, "ly": 1825, "p": 6957},
  {"key": "Tinta (per_lima)-Peru", "n": "Tinta", "c": "Peru", "r": "per_lima", "ll": [-10.6802, -76.8228], "ey": 1525, "ly": 2017, "p": 6956},
  {"key": "Huataca-Peru", "n": "Huataca", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-15.076, -73.331], "ey": 1525, "ly": 1825, "p": 6955},
  {"key": "Atiquipa-Peru", "n": "Atiquipa", "c": "Peru", "r": "per_arequipa", "ll": [-15.79611, -74.36361], "ey": 1525, "ly": 2025, "p": 6952},
  {"key": "Pariamarca (per_lima)-Peru", "n": "Pariamarca", "c": "Peru", "r": "per_lima", "ll": [-11.4919, -76.6295], "ey": 1525, "ly": 2017, "p": 6951},
  {"key": "San Pedro de Laraos-Peru", "n": "San Pedro de Laraos", "c": "Peru", "r": "per_lima", "ll": [-11.66444, -76.53944], "ey": 1525, "ly": 2025, "p": 6949, "al": ["laraos", "Laraos"]},
  {"key": "San Jose (vp_intendencia_lima)-Peru", "n": "San Jose", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.505, -76.675], "ey": 1525, "ly": 1825, "p": 6949},
  {"key": "Yamor-Peru", "n": "Yamor", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.199, -77.483], "ey": 1525, "ly": 1825, "p": 6949},
  {"key": "La Sierra (col_boyaca)-Colombia", "n": "La Sierra", "c": "Colombia", "r": "col_boyaca", "ll": [6.22731, -74.56735], "ey": 1525, "ly": 2018, "p": 6948, "al": ["carare", "puerto serviez", "Carare"]},
  {"key": "Quintero-Colombia_2", "n": "Quintero", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [4.472, -76.095], "ey": 1525, "ly": 1830, "p": 6947},
  {"key": "Sabaneta (ven_falcon)-Venezuela", "n": "Sabaneta", "c": "Venezuela", "r": "ven_falcon", "ll": [11.26, -69.98944], "ey": 1850, "ly": 2025, "p": 6946},
  {"key": "Huanangui-Peru", "n": "Huanangui", "c": "Peru", "r": "per_lima", "ll": [-11.1328, -77.0363], "ey": 1525, "ly": 2017, "p": 6946},
  {"key": "Santiago Apostol-Colombia", "n": "Santiago Apostol", "c": "Colombia", "r": "col_sucre", "ll": [9.0069, -74.92686], "ey": 1541, "ly": 2018, "p": 6944, "al": ["santiago", "Santiago"]},
  {"key": "Anton Moreno-Colombia", "n": "Anton Moreno", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.41, -76.62], "ey": 1525, "ly": 1830, "p": 6942},
  {"key": "Nanis-Peru", "n": "Nanis", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.383, -77.15], "ey": 1525, "ly": 1825, "p": 6942},
  {"key": "Loreto (crp_gobernacion_tucuman)-Argentina", "n": "Loreto", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.301, -64.184], "ey": 1536, "ly": 1830, "p": 6941},
  {"key": "Mercedes Díaz-Venezuela", "n": "Mercedes Díaz", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.30027, -70.63088], "ey": 1850, "ly": 2025, "p": 6940},
  {"key": "Huambacho Nueva (la Huaca)-Peru", "n": "Huambacho Nueva (la Huaca)", "c": "Peru", "r": "per_ancash", "ll": [-9.2589, -78.4352], "ey": -855, "ly": 2017, "p": 6939, "al": ["huambacho nueva", "huambacho", "huambacho pv31"]},
  {"key": "Jorobamba-Peru", "n": "Jorobamba", "c": "Peru", "r": "per_cajamarca", "ll": [-5.8533, -78.6166], "ey": 1525, "ly": 2017, "p": 6939, "al": ["balcho", "el rejo", "Balcho"]},
  {"key": "Nonogasta-Argentina", "n": "Nonogasta", "c": "Argentina", "r": "arg_la_rioja", "ll": [-29.30222, -67.50633], "ey": 1850, "ly": 2010, "p": 6937},
  {"key": "Hunchos-Peru", "n": "Hunchos", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-12.588, -74.535], "ey": 1525, "ly": 1825, "p": 6937},
  {"key": "Lampa (per_ayacucho)-Peru", "n": "Lampa", "c": "Peru", "r": "per_ayacucho", "ll": [-15.185, -73.34917], "ey": -2000, "ly": 2025, "p": 6935, "al": ["tinyanapampa", "colcabamba", "marcabamba"]},
  {"key": "Apuri-Peru", "n": "Apuri", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.882, -75.808], "ey": 1525, "ly": 1825, "p": 6935},
  {"key": "Tumbabiro-Ecuador", "n": "Tumbabiro", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.4628, -78.18135], "ey": 1525, "ly": 2025, "p": 6934, "al": ["tumbaviro", "Tumbaviro"]},
  {"key": "San Buenaventura (per_lima)-Peru", "n": "San Buenaventura", "c": "Peru", "r": "per_lima", "ll": [-11.48917, -76.66222], "ey": 1525, "ly": 2025, "p": 6934},
  {"key": "Coronado-Colombia", "n": "Coronado", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [3.552, -76.318], "ey": 1525, "ly": 1830, "p": 6934},
  {"key": "Choquekancha-Peru", "n": "Choquekancha", "c": "Peru", "r": "inca_antisuyu", "ll": [-13.03601, -72.03543], "ey": 0, "ly": 1530, "p": 6933, "al": ["hawk'an", "inka chaka", "pincullunca"]},
  {"key": "Mian-Peru", "n": "Mian", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-6.318, -77.43], "ey": 1525, "ly": 1825, "p": 6932},
  {"key": "Mangan-Ecuador", "n": "Mangan", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.711, -78.941], "ey": 1525, "ly": 1830, "p": 6931},
  {"key": "San Jose (vp_intendencia_lima_2)-Peru", "n": "San Jose", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-14.048, -75.274], "ey": 1525, "ly": 1825, "p": 6931},
  {"key": "Payandé-Colombia", "n": "Payandé", "c": "Colombia", "r": "col_tolima", "ll": [4.29758, -75.0984], "ey": 1775, "ly": 2018, "p": 6928, "al": ["santa barbara de la mina de la esmeralda", "la mina", "Santa Barbara de la Mina de la Esmeralda"]},
  {"key": "Mamara-Peru", "n": "Mamara", "c": "Peru", "r": "per_apurimac", "ll": [-14.22861, -72.59083], "ey": 0, "ly": 2025, "p": 6927, "al": ["ccap", "malapata", "utuara"]},
  {"key": "Huayrahuacho-Peru", "n": "Huayrahuacho", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.893, -72.96], "ey": 1525, "ly": 1825, "p": 6927, "al": ["huairaycho", "Huairaycho"]},
  {"key": "Cotaruse-Peru", "n": "Cotaruse", "c": "Peru", "r": "per_apurimac", "ll": [-14.41583, -73.205], "ey": -2000, "ly": 2025, "p": 6926, "al": ["pampamarca", "catarosi", "Catarosi"]},
  {"key": "Surco-Peru", "n": "Surco", "c": "Peru", "r": "per_lima", "ll": [-11.8825, -76.43611], "ey": 1525, "ly": 2025, "p": 6926},
  {"key": "Pichanas-Argentina", "n": "Pichanas", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-30.77, -65.192], "ey": 1536, "ly": 1830, "p": 6926, "al": ["pichana", "Pichana"]},
  {"key": "Chingos-Peru", "n": "Chingos", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.541, -77.186], "ey": 1525, "ly": 1825, "p": 6925},
  {"key": "Mangas-Peru", "n": "Mangas", "c": "Peru", "r": "per_ancash", "ll": [-10.36944, -77.10333], "ey": 1525, "ly": 2025, "p": 6924, "al": ["manas", "Manas"]},
  {"key": "Atabillos Altos-Peru", "n": "Atabillos Altos", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.254, -76.674], "ey": 1525, "ly": 1825, "p": 6921, "al": ["pasac", "Pasac"]},
  {"key": "San Pedro de Pilas-Peru", "n": "San Pedro de Pilas", "c": "Peru", "r": "per_lima", "ll": [-12.45444, -76.22694], "ey": 1525, "ly": 2025, "p": 6914, "al": ["tamara", "pilas", "Pilas"]},
  {"key": "San Francisco de Sangayaico-Peru", "n": "San Francisco de Sangayaico", "c": "Peru", "r": "per_huancavelica", "ll": [-13.79528, -75.24917], "ey": 1525, "ly": 2025, "p": 6911, "al": ["sangayayco", "Sangayayco"]},
  {"key": "Calacoto (bol_la_paz)-Bolivia", "n": "Calacoto", "c": "Bolivia", "r": "bol_la_paz", "ll": [-17.28359, -68.63476], "ey": 1525, "ly": 2024, "p": 6911},
  {"key": "San Benito-Colombia", "n": "San Benito", "c": "Colombia", "r": "col_santander", "ll": [6.12666, -73.50907], "ey": 1525, "ly": 2025, "p": 6910},
  {"key": "Arma-Peru", "n": "Arma", "c": "Peru", "r": "per_huancavelica", "ll": [-13.12639, -75.54194], "ey": 1525, "ly": 2025, "p": 6910},
  {"key": "Acotama-Peru", "n": "Acotama", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.142, -77.066], "ey": 1525, "ly": 1825, "p": 6910}
]

# 1. Local QUIPU gazetteers
files = glob.glob("histmap/1.data_raw/population_regional/QUIPU/**/*_settlements.json", recursive=True)
all_gaz = []
for fn in files:
    with open(fn, encoding="utf-8") as f:
        d = json.load(f)
    short = os.path.basename(fn).replace("_settlements.json", "")
    for k, v in d.items():
        if isinstance(v, dict):
            all_gaz.append((short, k, v))

# 2. HGIS Indias
hgis_path = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json"
hgis_setts = []
if os.path.exists(hgis_path):
    hgis = json.load(open(hgis_path, encoding="utf-8"))
    s_raw = hgis.get("settlements", [])
    hgis_setts = list(s_raw.values()) if isinstance(s_raw, dict) else s_raw

# 3. Documented arch sites
arch_path = "histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/config/documented_arch_sites.json"
arch_sites = []
if os.path.exists(arch_path):
    ad = json.load(open(arch_path, encoding="utf-8"))
    arch_sites = ad if isinstance(ad, list) else ad.get("sites", list(ad.values()) if isinstance(ad, dict) else [])

out = {}
for item in INPUT:
    key = item["key"]
    lat, lon = item["ll"]
    rec = {"input": item, "gaz_matches": [], "hgis_matches": [], "arch_matches": [], "wd": []}
    for short, k, v in all_gaz:
        vlat = v.get("lat") or (v.get("coords") or [None, None])[0]
        vlon = v.get("lng") or v.get("lon") or (v.get("coords") or [None, None])[1]
        if vlat is not None and vlon is not None:
            dist = math.hypot(lat - float(vlat), lon - float(vlon))
            if dist < 0.03:
                rec["gaz_matches"].append({
                    "dist": round(dist, 5),
                    "gaz": short,
                    "k": k,
                    "name": v.get("name"),
                    "subregion": v.get("subregion"),
                    "source": v.get("source"),
                    "notes": v.get("notes"),
                    "desc": v.get("description"),
                    "alt": v.get("other_names"),
                    "pop_keys": sorted(list(v.get("population", {}).keys()))[:10] if isinstance(v.get("population"), dict) else None
                })
    rec["gaz_matches"].sort(key=lambda x: x["dist"])
    rec["gaz_matches"] = rec["gaz_matches"][:5]

    for s in hgis_setts:
        c = s.get("coords") or [s.get("lat"), s.get("lon") or s.get("lng")]
        if c and c[0] is not None and c[1] is not None:
            dist = math.hypot(lat - float(c[0]), lon - float(c[1]))
            if dist < 0.03:
                rec["hgis_matches"].append({k: v for k, v in s.items() if k != "population"})

    for s in arch_sites:
        if isinstance(s, dict):
            slat = s.get("lat") or (s.get("coords") or [None, None])[0]
            slon = s.get("lng") or s.get("lon") or (s.get("coords") or [None, None])[1]
            if slat is not None and slon is not None:
                dist = math.hypot(lat - float(slat), lon - float(slon))
                if dist < 0.03:
                    rec["arch_matches"].append(s)
    out[key] = rec

# 4. Wikidata SPARQL
UA = {"User-Agent": "OperationViscountToponymy/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)"}
for batch_start in range(0, len(INPUT), 15):
    batch = INPUT[batch_start:batch_start+15]
    values = " ".join(f'("{d["key"]}" "Point({d["ll"][1]} {d["ll"][0]})"^^geo:wktLiteral)' for d in batch)
    sparql = f"""
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX bd: <http://www.bigdata.com/rdf#>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
SELECT DISTINCT ?key ?place ?placeLabel ?placeDesc ?inception ?adminLabel ?eswiki ?enwiki WHERE {{
  VALUES (?key ?loc) {{ {values} }}
  SERVICE wikibase:around {{
    ?place wdt:P625 ?coord .
    bd:serviceParam wikibase:center ?loc .
    bd:serviceParam wikibase:radius "5.0" .
  }}
  OPTIONAL {{ ?place wdt:P571 ?inception . }}
  OPTIONAL {{ ?place wdt:P131 ?admin . }}
  OPTIONAL {{ ?eswiki schema:about ?place ; schema:isPartOf <https://es.wikipedia.org/> . }}
  OPTIONAL {{ ?enwiki schema:about ?place ; schema:isPartOf <https://en.wikipedia.org/> . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . ?place rdfs:label ?placeLabel ; schema:description ?placeDesc . ?admin rdfs:label ?adminLabel . }}
}}
"""
    url = "https://query.wikidata.org/sparql"
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode({"query": sparql, "format": "json"}).encode(),
        headers={**UA, "Accept": "application/sparql-results+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            res = json.loads(r.read().decode("utf-8"))
            for b in res.get("results", {}).get("bindings", []):
                k = b["key"]["value"]
                out[k]["wd"].append({kk: vv["value"] for kk, vv in b.items() if kk != "key"})
        print(f"WD batch {batch_start//15+1} OK", flush=True)
    except Exception as e:
        print(f"WD batch {batch_start//15+1} ERR: {e}", flush=True)
    time.sleep(0.8)

with open("tests/q018_local_and_wd.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Saved tests/q018_local_and_wd.json", "HGIS:", sum(1 for v in out.values() if v["hgis_matches"]), "GAZ:", sum(1 for v in out.values() if v["gaz_matches"]), "WD:", sum(1 for v in out.values() if v["wd"]))
