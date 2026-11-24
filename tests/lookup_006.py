import json
import time
import urllib.parse
import urllib.request

SETTLEMENTS = [
  {"key": "Corma-Peru", "n": "Corma", "c": "Peru", "r": "per_cusco", "ll": [-13.8854, -71.754], "ey": 1525, "ly": 2017},
  {"key": "San Juan (per_cusco)-Peru", "n": "San Juan", "c": "Peru", "r": "per_cusco", "ll": [-14.1156, -71.6645], "ey": 1525, "ly": 2017},
  {"key": "Yanampampa-Peru", "n": "Yanampampa", "c": "Peru", "r": "per_cusco", "ll": [-14.0036, -71.5213], "ey": 500, "ly": 2017, "al": ["yanapampa", "k'ullupata", "espillicu"]},
  {"key": "Chíquiza-Colombia", "n": "Chíquiza", "c": "Colombia", "r": "col_boyaca", "ll": [5.63983, -73.44946], "ey": 1525, "ly": 2025},
  {"key": "Marcaconga-Peru", "n": "Marcaconga", "c": "Peru", "r": "per_cusco", "ll": [-13.9754, -71.5631], "ey": 1525, "ly": 2017, "al": ["ihuina", "Ihuina"]},
  {"key": "Sayhua (per_cusco)-Peru", "n": "Sayhua", "c": "Peru", "r": "per_cusco", "ll": [-14.1385, -71.6021], "ey": 1525, "ly": 2017},
  {"key": "Acopia-Peru", "n": "Acopia", "c": "Peru", "r": "per_cusco", "ll": [-14.0575, -71.49333], "ey": 1525, "ly": 2025},
  {"key": "Machin-Peru", "n": "Machin", "c": "Peru", "r": "per_pasco", "ll": [-10.415, -76.3643], "ey": 1525, "ly": 2017, "al": ["huachon", "ranra"]},
  {"key": "Muquiyauyo-Peru", "n": "Muquiyauyo", "c": "Peru", "r": "per_junin", "ll": [-11.81389, -75.45389], "ey": 1525, "ly": 2025, "al": ["muquianyo"]},
  {"key": "San Juan de Quihuares-Peru", "n": "San Juan de Quihuares", "c": "Peru", "r": "per_cusco", "ll": [-13.7448, -71.7968], "ey": 1525, "ly": 2017, "al": ["quishuares"]},
  {"key": "Choras-Peru", "n": "Choras", "c": "Peru", "r": "per_huanuco", "ll": [-9.91028, -76.60583], "ey": 0, "ly": 2025, "al": ["chacabamba", "choduevado", "corral corral"]},
  {"key": "La Mesa-Venezuela", "n": "La Mesa", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.03488, -70.71625], "ey": 1538, "ly": 2025},
  {"key": "Ninacaca-Peru", "n": "Ninacaca", "c": "Peru", "r": "per_pasco", "ll": [-10.85556, -76.11306], "ey": 1525, "ly": 2025},
  {"key": "Tuti-Peru", "n": "Tuti", "c": "Peru", "r": "per_arequipa", "ll": [-15.53306, -71.55306], "ey": 1525, "ly": 2025},
  {"key": "Papres-Peru", "n": "Papres", "c": "Peru", "r": "per_cusco", "ll": [-13.8331, -71.777], "ey": 1525, "ly": 2017},
  {"key": "Checacupe-Peru", "n": "Checacupe", "c": "Peru", "r": "per_cusco", "ll": [-14.02528, -71.45389], "ey": 1525, "ly": 2025},
  {"key": "Sincos-Peru", "n": "Sincos", "c": "Peru", "r": "per_junin", "ll": [-11.89139, -75.38694], "ey": 1525, "ly": 2025},
  {"key": "Rio Negro (ven_merida)-Venezuela", "n": "Rio Negro", "c": "Venezuela", "r": "ven_merida", "ll": [8.16222, -71.64889], "ey": 1850, "ly": 2025},
  {"key": "Magdalena de Cao-Peru", "n": "Magdalena de Cao", "c": "Peru", "r": "per_la_libertad", "ll": [-7.87639, -79.29583], "ey": 1525, "ly": 2025},
  {"key": "Huaychao (per_ayacucho)-Peru", "n": "Huaychao", "c": "Peru", "r": "per_ayacucho", "ll": [-13.1702, -74.0382], "ey": 1525, "ly": 2017},
  {"key": "Santa Cruz (per_lima)-Peru", "n": "Santa Cruz", "c": "Peru", "r": "per_lima", "ll": [-13.078, -76.4426], "ey": 1525, "ly": 2017},
  {"key": "Pancan-Peru", "n": "Pancan", "c": "Peru", "r": "per_junin", "ll": [-11.74889, -75.48611], "ey": 1525, "ly": 2025, "al": ["mojon", "pancán"]},
  {"key": "Vichuquen-Chile", "n": "Vichuquen", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-34.884, -71.993], "ey": 1536, "ly": 1830},
  {"key": "Augusto N. Martínez-Ecuador", "n": "Augusto N. Martínez", "c": "Ecuador", "r": "ecu_tungurahua", "ll": [-1.1764, -78.61996], "ey": 1850, "ly": 2025},
  {"key": "Cochela-Peru", "n": "Cochela", "c": "Peru", "r": "inca_collasuyu", "ll": [-15.64991, -70.20162], "ey": 0, "ly": 1530, "al": ["tambo cucho"]},
  {"key": "Canoa-Ecuador", "n": "Canoa", "c": "Ecuador", "r": "ecu_manabi", "ll": [-0.38248, -80.40049], "ey": 1525, "ly": 2025},
  {"key": "Orcotuna-Peru", "n": "Orcotuna", "c": "Peru", "r": "per_junin", "ll": [-11.96722, -75.3075], "ey": 1525, "ly": 2025},
  {"key": "Quintero-Venezuela", "n": "Quintero", "c": "Venezuela", "r": "ven_barinas", "ll": [7.79167, -69.81111], "ey": 1850, "ly": 2025},
  {"key": "Acos-Peru", "n": "Acos", "c": "Peru", "r": "per_cusco", "ll": [-13.95111, -71.73806], "ey": 1525, "ly": 2025},
  {"key": "Sabanilla-Ecuador", "n": "Sabanilla", "c": "Ecuador", "r": "ecu_guayas", "ll": [-1.94886, -80.29455], "ey": 1850, "ly": 2025},
  {"key": "Lucma-Peru", "n": "Lucma", "c": "Peru", "r": "per_la_libertad", "ll": [-7.64056, -78.55222], "ey": 1525, "ly": 2025},
  {"key": "Cangari-Peru", "n": "Cangari", "c": "Peru", "r": "per_huancavelica", "ll": [-12.9882, -74.2848], "ey": 1525, "ly": 2017, "al": ["viru viru", "viroviro", "vivovivo"]},
  {"key": "Mito-Peru", "n": "Mito", "c": "Peru", "r": "per_junin", "ll": [-11.93722, -75.33917], "ey": 1525, "ly": 2025},
  {"key": "Sabana Larga-Venezuela", "n": "Sabana Larga", "c": "Venezuela", "r": "ven_falcon", "ll": [11.44333, -69.59667], "ey": 1850, "ly": 2011},
  {"key": "Colcamar-Peru", "n": "Colcamar", "c": "Peru", "r": "per_amazonas", "ll": [-6.29944, -77.97306], "ey": 1525, "ly": 2025},
  {"key": "Julquilla-Peru", "n": "Julquilla", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.534, -77.721], "ey": 1525, "ly": 1825},
  {"key": "Ponaya-Peru", "n": "Ponaya", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-6.299, -77.938], "ey": 1525, "ly": 1825},
  {"key": "El Pilar (ven_sucre)-Venezuela", "n": "El Pilar", "c": "Venezuela", "r": "ven_sucre", "ll": [10.56667, -63.17222], "ey": 1850, "ly": 2025},
  {"key": "Aláquez-Ecuador", "n": "Aláquez", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-0.84677, -78.49914], "ey": 1850, "ly": 2025},
  {"key": "Chacayan-Peru", "n": "Chacayan", "c": "Peru", "r": "per_pasco", "ll": [-10.43444, -76.43722], "ey": 1525, "ly": 2025, "al": ["chacayán", "mito"]},
  {"key": "Leonor Ordoñez-Peru", "n": "Leonor Ordoñez", "c": "Peru", "r": "per_junin", "ll": [-11.85944, -75.4175], "ey": 1525, "ly": 2025, "al": ["huancani", "san antonio de huancani"]},
  {"key": "Matehuaca-Peru", "n": "Matehuaca", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.395, -76.349], "ey": 1525, "ly": 1825, "al": ["marcan"]},
  {"key": "Mauk'allaqta-Peru", "n": "Mauk'allaqta", "c": "Peru", "r": "inca_cuzco_heartland", "ll": [-13.70422, -71.96774], "ey": 1438, "ly": 1530, "al": ["hera moqo", "llamapinta", "paucarpata"]},
  {"key": "San Francisco De Natabuela-Ecuador", "n": "San Francisco De Natabuela", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.30724, -78.19467], "ey": 1850, "ly": 2025},
  {"key": "San José de Ticllas-Peru", "n": "San José de Ticllas", "c": "Peru", "r": "per_huancavelica", "ll": [-13.13222, -74.33306], "ey": 1525, "ly": 2025, "al": ["ticllas"]},
  {"key": "Chonta-Peru", "n": "Chonta", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.551, -72.468], "ey": 1525, "ly": 1825, "al": ["chota"]},
  {"key": "Fortaleza de Acaray-Peru", "n": "Fortaleza de Acaray", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.05929, -77.5349], "ey": -1000, "ly": 1530, "al": ["balconcillo", "cejetuto", "domingo cerro"]},
  {"key": "Miguel Iglesias-Peru", "n": "Miguel Iglesias", "c": "Peru", "r": "per_cajamarca", "ll": [-6.65028, -78.2325], "ey": 1525, "ly": 2025, "al": ["chala", "chalan"]},
  {"key": "Cochacalla-Peru", "n": "Cochacalla", "c": "Peru", "r": "per_huanuco", "ll": [-10.3591, -76.2089], "ey": 1525, "ly": 2017},
  {"key": "Huallanda-Peru", "n": "Huallanda", "c": "Peru", "r": "per_cajamarca", "ll": [-5.446, -78.5803], "ey": 1535, "ly": 2017, "al": ["jaen"]},
  {"key": "Huaricanga-Peru", "n": "Huaricanga", "c": "Peru", "r": "per_lima", "ll": [-10.4879, -77.7493], "ey": 500, "ly": 2017, "al": ["san juan huaricanga"]},
  {"key": "Paucar-Peru", "n": "Paucar", "c": "Peru", "r": "per_pasco", "ll": [-10.37111, -76.44333], "ey": 1525, "ly": 2025},
  {"key": "Gachantivá-Colombia", "n": "Gachantivá", "c": "Colombia", "r": "col_boyaca", "ll": [5.75189, -73.54909], "ey": 1300, "ly": 2025},
  {"key": "Talaigua Viejo-Colombia", "n": "Talaigua Viejo", "c": "Colombia", "r": "col_bolivar", "ll": [9.31215, -74.58569], "ey": 1525, "ly": 2018},
  {"key": "Chango-Peru", "n": "Chango", "c": "Peru", "r": "per_pasco", "ll": [-10.4151, -76.4114], "ey": 1525, "ly": 2017, "al": ["andapirca", "andaspaca"]},
  {"key": "San Juan de Yacan (yacan)-Peru", "n": "San Juan de Yacan (yacan)", "c": "Peru", "r": "per_pasco", "ll": [-10.3946, -76.4416], "ey": 1525, "ly": 2017, "al": ["san juan de yacan", "yacan", "llacan"]},
  {"key": "El Mantaro-Peru", "n": "El Mantaro", "c": "Peru", "r": "per_junin", "ll": [-11.82222, -75.39194], "ey": 1525, "ly": 2025, "al": ["huamali", "pucucho", "huamal"]},
  {"key": "Quinua-Peru", "n": "Quinua", "c": "Peru", "r": "per_ayacucho", "ll": [-13.04917, -74.13917], "ey": 1440, "ly": 2025},
  {"key": "Henderson-Argentina", "n": "Henderson", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-36.29813, -61.71851], "ey": 1850, "ly": 2010},
  {"key": "Tenza-Colombia", "n": "Tenza", "c": "Colombia", "r": "col_cundinamarca", "ll": [5.07678, -73.42118], "ey": 1525, "ly": 2025},
  {"key": "Guambaló-Ecuador", "n": "Guambaló", "c": "Ecuador", "r": "ecu_tungurahua", "ll": [-1.39987, -78.52563], "ey": 1850, "ly": 2025},
  {"key": "San Luis De Pambil-Ecuador", "n": "San Luis De Pambil", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.24315, -79.21633], "ey": 1850, "ly": 2025},
  {"key": "Juncalejo-Colombia", "n": "Juncalejo", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [10.71, -74.749], "ey": 1525, "ly": 1830},
  {"key": "Tacasaluma-Colombia", "n": "Tacasaluma", "c": "Colombia", "r": "col_sucre", "ll": [9.10617, -74.8027], "ey": 1525, "ly": 2018},
  {"key": "San Pedro-Colombia_3", "n": "San Pedro", "c": "Colombia", "r": "na_nw_amazon_foothills", "ll": [0.63, -76.58], "ey": 710, "ly": 1500},
  {"key": "Roco-Peru", "n": "Roco", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.416, -76.432], "ey": 1525, "ly": 1825, "al": ["huaylashirca", "huaylashuaca", "raco"]},
  {"key": "Canocota-Peru", "n": "Canocota", "c": "Peru", "r": "vp_intendencia_arequipa", "ll": [-15.561, -71.563], "ey": 1525, "ly": 1825},
  {"key": "Arismendi (ven_apure)-Venezuela", "n": "Arismendi", "c": "Venezuela", "r": "ven_apure", "ll": [7.50135, -70.01009], "ey": 1850, "ly": 2025},
  {"key": "San Juan el Alto-Peru", "n": "San Juan el Alto", "c": "Peru", "r": "per_arequipa", "ll": [-16.3683, -72.1633], "ey": 1525, "ly": 2017, "al": ["alto siguas", "santa isabel sihuas"]},
  {"key": "San Sebastian de Collpa (collpa Grande)-Peru", "n": "San Sebastian de Collpa (collpa Grande)", "c": "Peru", "r": "per_junin", "ll": [-11.4023, -75.6274], "ey": 1525, "ly": 2017, "al": ["san sebastian de collpa", "santo domingo de menahermosa"]},
  {"key": "Rinconada-Peru_2", "n": "Rinconada", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.084, -76.927], "ey": 1525, "ly": 1825},
  {"key": "Ticoporo-Venezuela", "n": "Ticoporo", "c": "Venezuela", "r": "ven_barinas", "ll": [8.0871, -70.6138], "ey": 1850, "ly": 2025},
  {"key": "Ciudad de Dios-Peru", "n": "Ciudad de Dios", "c": "Peru", "r": "per_la_libertad", "ll": [-7.3038, -79.48], "ey": 1850, "ly": 2017, "al": ["faclo chico"]},
  {"key": "Cayna-Peru", "n": "Cayna", "c": "Peru", "r": "per_huanuco", "ll": [-10.2725, -76.38833], "ey": 1525, "ly": 2025},
  {"key": "Ibin-Peru", "n": "Ibin", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.668, -72.357], "ey": 1525, "ly": 1825},
  {"key": "Tapuc-Peru", "n": "Tapuc", "c": "Peru", "r": "per_pasco", "ll": [-10.45472, -76.4625], "ey": 1525, "ly": 2025},
  {"key": "Llamor-Peru", "n": "Llamor", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.279, -76.443], "ey": 1525, "ly": 1825},
  {"key": "Tacaloa-Colombia", "n": "Tacaloa", "c": "Colombia", "r": "col_magdalena", "ll": [9.41314, -74.75589], "ey": 1525, "ly": 2018},
  {"key": "Cheto-Peru", "n": "Cheto", "c": "Peru", "r": "per_amazonas", "ll": [-6.25556, -77.70083], "ey": 1525, "ly": 2025},
  {"key": "Villa Los Álamos - El Congreso - Las Tunas - Los Pinares - Los Olmos-Argentina", "n": "Villa Los Álamos - El Congreso - Las Tunas - Los Pinares - Los Olmos", "c": "Argentina", "r": "arg_salta", "ll": [-24.85806, -65.45028], "ey": 1850, "ly": 2010},
  {"key": "San Pedro de la Tablada-Colombia", "n": "San Pedro de la Tablada", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [7.97, -73.868], "ey": 1525, "ly": 1830},
  {"key": "Chaspaya-Peru", "n": "Chaspaya", "c": "Peru", "r": "vp_intendencia_arequipa", "ll": [-17.614, -71.254], "ey": 1525, "ly": 1825},
  {"key": "San Rafael de Atamaica-Venezuela", "n": "San Rafael de Atamaica", "c": "Venezuela", "r": "ven_apure", "ll": [7.41123, -66.88231], "ey": 1850, "ly": 2025},
  {"key": "Vilcabamba (per_pasco)-Peru", "n": "Vilcabamba", "c": "Peru", "r": "per_pasco", "ll": [-10.47861, -76.44694], "ey": 1525, "ly": 2025},
  {"key": "Ate-Peru", "n": "Ate", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.028, -76.926], "ey": 1525, "ly": 1825, "al": ["late"]},
  {"key": "San Marcos Cihua-Peru", "n": "San Marcos Cihua", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.013, -74.245], "ey": 1525, "ly": 1825, "al": ["chigua"]},
  {"key": "Huarocondo-Peru", "n": "Huarocondo", "c": "Peru", "r": "per_cusco", "ll": [-13.41583, -72.2075], "ey": 1525, "ly": 2025},
  {"key": "San Francisco-Peru", "n": "San Francisco", "c": "Peru", "r": "per_pasco", "ll": [-10.34278, -76.29194], "ey": 1525, "ly": 2025, "al": ["mosca", "san francisco de mosca"]},
  {"key": "Picha-Peru", "n": "Picha", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.263, -74.351], "ey": 1525, "ly": 1825, "al": ["piccha"]},
  {"key": "San Cristobal de Chaupimarca (chaupimarca)-Peru", "n": "San Cristobal de Chaupimarca (chaupimarca)", "c": "Peru", "r": "per_pasco", "ll": [-10.4065, -76.4615], "ey": 1525, "ly": 2017, "al": ["san cristobal de chaupimarca", "chaupimarca"]}
]

def wiki_get(url):
  req = urllib.request.Request(url, headers={"User-Agent": "SVEA-Toponymy/1.0"})
  with urllib.request.urlopen(req, timeout=15) as r:
    return json.loads(r.read().decode("utf-8"))

out = []
for idx, s in enumerate(SETTLEMENTS):
  lat, lon = s["ll"]
  geo_url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
  try:
    g = wiki_get(geo_url)
    hits = g.get("query", {}).get("geosearch", [])
  except Exception as e:
    hits = [{"error": str(e)}]

  # Also try title search for Peru districts or exact name
  search_q = urllib.parse.quote(f"{s['n']} {s['c']}")
  srch_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={search_q}&srlimit=3&format=json"
  try:
    sr = wiki_get(srch_url)
    shits = [x["title"] for x in sr.get("query", {}).get("search", [])]
  except Exception:
    shits = []

  out.append({"key": s["key"], "n": s["n"], "r": s["r"], "ll": s["ll"], "geo": hits[:3], "srch": shits})
  if (idx + 1) % 15 == 0:
    time.sleep(0.3)

with open("tests/wiki_lookup_006.json", "w", encoding="utf-8") as f:
  json.dump(out, f, ensure_ascii=False, indent=2)
print(f"Done {len(out)} items")
