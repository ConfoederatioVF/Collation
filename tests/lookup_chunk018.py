import json
import time
import urllib.parse
import urllib.request

ITEMS = [
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

UA = "SVEA-QuipuBot/1.0 (https://confoederatio.org; research@confoederatio.org)"

def fetch_json(url):
  for attempt in range(4):
    try:
      req = urllib.request.Request(url, headers={'User-Agent': UA})
      with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
      if '429' in str(e) and attempt < 3:
        time.sleep(2.0 * (attempt + 1))
        continue
      raise

results = []
all_titles = set()
for idx, item in enumerate(ITEMS):
  lat, lon = item['ll']
  rec = {'key': item['key'], 'es_geo': [], 'es_search': []}
  try:
    g = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json")
    rec['es_geo'] = [x['title'] for x in g.get('query', {}).get('geosearch', [])]
    time.sleep(0.15)
  except Exception as e:
    rec['es_geo_err'] = str(e)
  # Only search if geosearch returned nothing or generic
  if not rec['es_geo']:
    try:
      q = urllib.parse.quote(f"{item['n']} {item['c']}")
      s = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json")
      rec['es_search'] = [x['title'] for x in s.get('query', {}).get('search', [])]
      time.sleep(0.15)
    except Exception as e:
      rec['es_search_err'] = str(e)
  for t in rec['es_geo'][:2] + rec['es_search'][:2]:
    all_titles.add(t)
  results.append(rec)

# Batch fetch extracts 20 at a time
extracts = {}
title_list = sorted(all_titles)
for i in range(0, len(title_list), 20):
  batch = title_list[i:i+20]
  t_param = urllib.parse.quote("|".join(batch))
  try:
    ex = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={t_param}&format=json")
    for pid, p in ex.get('query', {}).get('pages', {}).items():
      if 'extract' in p and p['extract']:
        extracts[p['title']] = p['extract'][:800]
  except Exception as e:
    print("Extract batch err:", e)
  time.sleep(0.2)

for rec in results:
  rec['extracts'] = {}
  for t in rec['es_geo'][:2] + rec['es_search'][:2]:
    if t in extracts:
      rec['extracts'][t] = extracts[t]

with open('tests/chunk018_wiki.json', 'w', encoding='utf-8') as fh:
  json.dump(results, fh, ensure_ascii=False, indent=2)
print("Wiki done, extracts:", len(extracts))
