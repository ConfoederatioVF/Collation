import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ITEMS = [
  {"key": "Montalvito - sitio-Colombia", "n": "Montalvito - sitio", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.19778, -74.86778], "ey": -1000, "ly": 1500, "al": ["el espejo - sitio", "el espejo - sitios i", "patio bonito"]},
  {"key": "Las Cruces-Chile", "n": "Las Cruces", "c": "Chile", "r": "chl_region_de_valparaiso", "ll": [-33.50016, -71.61324], "ey": 1850, "ly": 2017},
  {"key": "San Jose del Naranjo-Colombia", "n": "San Jose del Naranjo", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [4.598, -75.948], "ey": 1525, "ly": 1830},
  {"key": "Esperanza Galicia-Colombia", "n": "Esperanza Galicia", "c": "Colombia", "r": "col_risaralda", "ll": [4.79983, -75.81491], "ey": 1525, "ly": 2018, "al": ["cerritos", "estación villegas", "pindana de los cerritos"]},
  {"key": "Santa Rosa (ven_lara)-Venezuela", "n": "Santa Rosa", "c": "Venezuela", "r": "ven_lara", "ll": [10.10107, -69.24574], "ey": 1538, "ly": 2025, "al": ["cerrito de santa rosa"]},
  {"key": "Chamalla-Peru", "n": "Chamalla", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-5.811, -78.717], "ey": 1525, "ly": 1830},
  {"key": "Chacas-Peru", "n": "Chacas", "c": "Peru", "r": "per_ancash", "ll": [-9.16222, -77.36583], "ey": 1525, "ly": 2025},
  {"key": "Huapula-Ecuador", "n": "Huapula", "c": "Ecuador", "r": "inca_chinchaysuyu", "ll": [-2.0747, -78.0458], "ey": -3361, "ly": 1532},
  {"key": "Manuel Manrique (ven_cojedes)-Venezuela", "n": "Manuel Manrique", "c": "Venezuela", "r": "ven_cojedes", "ll": [9.81629, -68.51306], "ey": 1850, "ly": 2025},
  {"key": "Q'espellaqta-Peru", "n": "Q'espellaqta", "c": "Peru", "r": "inca_collasuyu", "ll": [-13.93933, -71.62595], "ey": 500, "ly": 1530, "al": ["huanoqoto", "llanquepata", "Huanoqoto"]},
  {"key": "Guatraché-Argentina", "n": "Guatraché", "c": "Argentina", "r": "arg_la_pampa", "ll": [-37.67078, -63.53572], "ey": 1900, "ly": 2022},
  {"key": "Santo Domingo de la Capilla-Peru", "n": "Santo Domingo de la Capilla", "c": "Peru", "r": "per_cajamarca", "ll": [-6.24472, -78.85528], "ey": 1850, "ly": 2025},
  {"key": "Pinto-Argentina", "n": "Pinto", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-29.14168, -62.65463], "ey": 1850, "ly": 2022, "al": ["villa general mitre", "Villa General Mitre"]},
  {"key": "Vallenar-Chile_2", "n": "Vallenar", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-28.575, -70.756], "ey": 1525, "ly": 1830, "ex": [{"date": "1875.1.1", "name": "Vallenar"}], "al": ["ballenary", "paitanaza", "san ambrosio de vallenar"]},
  {"key": "San Sebastián-Ecuador", "n": "San Sebastián", "c": "Ecuador", "r": "ecu_manabi", "ll": [-1.06655, -79.96737], "ey": 1850, "ly": 2025},
  {"key": "Charquina 1 Bis-Argentina", "n": "Charquina 1 Bis", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.30333, -65.64333], "ey": 80, "ly": 1500},
  {"key": "Terama baja-Colombia", "n": "Terama baja", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.196, -74.451], "ey": 1525, "ly": 1830},
  {"key": "Naranjal (col_huila)-Colombia", "n": "Naranjal", "c": "Colombia", "r": "col_huila", "ll": [2.0158, -75.8509], "ey": 1525, "ly": 2018},
  {"key": "Wilfrido Loor Moreira-Ecuador", "n": "Wilfrido Loor Moreira", "c": "Ecuador", "r": "ecu_manabi", "ll": [-0.33595, -79.66068], "ey": 1850, "ly": 2025},
  {"key": "Rachacuain-Peru", "n": "Rachacuain", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.23594, -75.65014], "ey": 500, "ly": 1530, "al": ["chupas", "cumbre de huacuas", "paucarmarca"]},
  {"key": "Upito-Colombia", "n": "Upito", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [4.256, -74.885], "ey": 1758, "ly": 1830},
  {"key": "Llapa-Peru", "n": "Llapa", "c": "Peru", "r": "per_cajamarca", "ll": [-6.98083, -78.8075], "ey": 1850, "ly": 2025},
  {"key": "Ingeniero Forres-Argentina", "n": "Ingeniero Forres", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-27.87896, -63.98043], "ey": 1850, "ly": 2010},
  {"key": "Cerro Condorhuachana-Peru", "n": "Cerro Condorhuachana", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.96046, -70.34228], "ey": -1000, "ly": 1530, "al": ["caserio pampa", "cercopata", "cheq'a quichusa"]},
  {"key": "Antonio Díaz (ven_lara)-Venezuela", "n": "Antonio Díaz", "c": "Venezuela", "r": "ven_lara", "ll": [9.97778, -69.93833], "ey": 1538, "ly": 2025, "al": ["valle de curarigua de leal", "Valle de Curarigua de Leal"]},
  {"key": "Yacus-Peru", "n": "Yacus", "c": "Peru", "r": "per_huanuco", "ll": [-9.98611, -76.50583], "ey": 1850, "ly": 2025},
  {"key": "Huentota-Argentina", "n": "Huentota", "c": "Argentina", "r": "inca_collasuyu", "ll": [-32.89, -68.845], "ey": 1480, "ly": 1530, "ex": [{"date": "1770.1.1", "name": "Mendoza"}], "al": ["mendoza huarpe-inca", "Mendoza Huarpe-Inca"]},
  {"key": "Chiloé Castro-Chile", "n": "Chiloé Castro", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-42.48, -73.764], "ey": -4000, "ly": 1450, "ex": [{"date": "1895.1.1", "name": "Castro"}], "al": ["dalcahue huilliche", "Dalcahue Huilliche"]},
  {"key": "Choros-Chile", "n": "Choros", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-29.29, -71.313], "ey": 1525, "ly": 1830},
  {"key": "El Corozo-Los Cruces-Venezuela", "n": "El Corozo-Los Cruces", "c": "Venezuela", "r": "ven_tachira", "ll": [7.69013, -72.24261], "ey": 1850, "ly": 2011},
  {"key": "San Rafael-Colombia_2", "n": "San Rafael", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.01732, -74.85633], "ey": 1300, "ly": 1500, "al": ["quebrada batatas", "rincón de batatas", "Quebrada Batatas"]},
  {"key": "Badillo (col_bolivar)-Colombia", "n": "Badillo", "c": "Colombia", "r": "col_bolivar", "ll": [7.97471, -73.85438], "ey": 1772, "ly": 2018, "al": ["vadillo", "vadillos", "Vadillo"]},
  {"key": "Tacamoros-Ecuador", "n": "Tacamoros", "c": "Ecuador", "r": "ecu_loja", "ll": [-4.43319, -79.72442], "ey": 1525, "ly": 2025},
  {"key": "Huaros-Peru", "n": "Huaros", "c": "Peru", "r": "per_lima", "ll": [-11.40667, -76.57583], "ey": 1525, "ly": 2025},
  {"key": "Huaca Bobadilla-Peru", "n": "Huaca Bobadilla", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.59939, -79.79715], "ey": -1000, "ly": 1530, "al": ["cerro conejero la liebre", "cerro cristian", "huaca cocopiedra"]},
  {"key": "Paredones Nazca-Peru", "n": "Paredones Nazca", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.841, -74.933], "ey": 1438, "ly": 1532, "ex": [{"date": "1961.1.1", "name": "Nazca"}], "al": ["acueductos de achaco", "acueductos de callanal", "acueductos de cantalloc"]},
  {"key": "Mañazo-Peru", "n": "Mañazo", "c": "Peru", "r": "per_puno", "ll": [-15.80111, -70.34333], "ey": 1300, "ly": 2025, "al": ["paucarcolla", "cerro volcan", "cruz quer"]},
  {"key": "Canchay-Peru", "n": "Canchay", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.89217, -76.00671], "ey": -1000, "ly": 1530, "al": ["dos pozos", "goyar punta", "goyllar punta"]},
  {"key": "Todos Santos Calabozo-Venezuela", "n": "Todos Santos Calabozo", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [8.919, -67.43], "ey": 1724, "ly": 1830, "ex": [{"date": "1873.1.1", "name": "Calabozo"}]},
  {"key": "Yamane-Colombia", "n": "Yamane", "c": "Colombia", "r": "vng_llanos_caguan", "ll": [3.566, -72.364], "ey": 1525, "ly": 1830},
  {"key": "Providencia-Colombia_2", "n": "Providencia", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.6464, -78.73931], "ey": 1000, "ly": 1500},
  {"key": "Mineral de Ametistas-Peru", "n": "Mineral de Ametistas", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-6.289, -78.858], "ey": 1525, "ly": 1830},
  {"key": "Huayllay Grande-Peru", "n": "Huayllay Grande", "c": "Peru", "r": "per_huancavelica", "ll": [-12.94278, -74.70167], "ey": 1525, "ly": 2025, "al": ["ucchuhuaylluay", "huaylluay", "uchurguay"]},
  {"key": "Copani-Peru", "n": "Copani", "c": "Peru", "r": "per_puno", "ll": [-16.4, -69.04028], "ey": 1850, "ly": 2025},
  {"key": "Chañar Ladeado-Argentina", "n": "Chañar Ladeado", "c": "Argentina", "r": "arg_cordoba", "ll": [-33.32617, -62.03533], "ey": 1850, "ly": 2022},
  {"key": "La Concepción (ven_trujillo)-Venezuela", "n": "La Concepción", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.425, -70.46833], "ey": 1850, "ly": 2025},
  {"key": "Tambomarka-Peru", "n": "Tambomarka", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.45264, -76.35384], "ey": 0, "ly": 1530, "al": ["angawillca", "Angawillca"]},
  {"key": "None (crp_obispado_concepcion_chiloe)-Chile", "n": "None", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-35.90768, -71.71246], "ey": 1525, "ly": 1599, "al": ["catentoa", "catenzoa", "Catentoa"]},
  {"key": "Acoyte-Argentina", "n": "Acoyte", "c": "Argentina", "r": "arg_salta", "ll": [-22.28346, -65.01662], "ey": 1525, "ly": 2010},
  {"key": "Colimes-Ecuador_2", "n": "Colimes", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-1.59178, -80.28246], "ey": -3163, "ly": -2082},
  {"key": "Sabaletas (col_antioquia)-Colombia", "n": "Sabaletas", "c": "Colombia", "r": "col_antioquia", "ll": [5.91746, -75.54634], "ey": 1525, "ly": 2018, "al": ["concepcion zabaletas", "Concepcion Zabaletas"]},
  {"key": "Concepción (ven_zulia)-Venezuela", "n": "Concepción", "c": "Venezuela", "r": "ven_zulia", "ll": [10.41711, -71.6933], "ey": 1850, "ly": 2025},
  {"key": "Sastre-Argentina", "n": "Sastre", "c": "Argentina", "r": "arg_santa_fe", "ll": [-31.76747, -61.82899], "ey": 1850, "ly": 2010},
  {"key": "Las Toscas-Uruguay", "n": "Las Toscas", "c": "Uruguay", "r": "ury_canelones", "ll": [-34.76738, -55.74014], "ey": 1850, "ly": 2023},
  {"key": "Gultro-Chile", "n": "Gultro", "c": "Chile", "r": "chl_region_del_libertador_bernardo_o_higgins", "ll": [-34.20486, -70.76126], "ey": 1850, "ly": 2017},
  {"key": "Sa-Vsm-Colombia", "n": "Sa-Vsm", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.0714, -74.90584], "ey": 0, "ly": 1500, "al": ["santana"]},
  {"key": "Paqu-Colombia", "n": "Paqu", "c": "Colombia", "r": "na_nw_amazon_foothills", "ll": [-0.5747, -72.1129], "ey": -269, "ly": 1500},
  {"key": "Humedales del Río Maullín-Chile", "n": "Humedales del Río Maullín", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-41.51908, -73.36842], "ey": 1000, "ly": 1500, "ex": [{"date": "1950.1.1", "name": "Maullín"}]},
  {"key": "Algarrobo B-Peru", "n": "Algarrobo B", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.97312, -76.81151], "ey": 0, "ly": 1530, "ex": [{"date": "1961.1.1", "name": "Chaclacayo"}], "al": ["algarrobo", "algarrobo a", "algarrobo c"]},
  {"key": "Chapa-Colombia", "n": "Chapa", "c": "Colombia", "r": "col_cauca", "ll": [2.47135, -76.88196], "ey": 1525, "ly": 2018, "al": ["aires de occidente", "el crucero de pandiguando", "la chicueña"]},
  {"key": "Suárez (col_tolima)-Colombia", "n": "Suárez", "c": "Colombia", "r": "col_tolima", "ll": [4.04889, -74.83188], "ey": 1525, "ly": 2025, "al": ["balneario batatas", "batatas", "Balneario Batatas"]},
  {"key": "Acas-Peru", "n": "Acas", "c": "Peru", "r": "per_ancash", "ll": [-10.4575, -77.32778], "ey": 1525, "ly": 2025, "al": ["hacas", "Hacas"]},
  {"key": "Waqakunapata-Peru", "n": "Waqakunapata", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.87707, -73.72466], "ey": -1000, "ly": 1530, "al": ["arqueológico andenes de chilcayoc", "cerro masobamba", "cerro pampalla"]},
  {"key": "Toco Toco-Argentina", "n": "Toco Toco", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.76564, -64.75579], "ey": 80, "ly": 1500},
  {"key": "La Concepción (ven_trujillo_2)-Venezuela", "n": "La Concepción", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.50416, -70.21406], "ey": 1850, "ly": 2025},
  {"key": "Yerbabuena-Colombia", "n": "Yerbabuena", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [3.98416, -74.91407], "ey": 500, "ly": 1500},
  {"key": "Canchagua-Ecuador", "n": "Canchagua", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-0.79726, -78.71178], "ey": 1850, "ly": 2025},
  {"key": "Ciudad de Dios (per_tacna)-Peru", "n": "Ciudad de Dios", "c": "Peru", "r": "per_tacna", "ll": [-18.0687, -70.2995], "ey": 1850, "ly": 2017},
  {"key": "Los Juríes-Argentina", "n": "Los Juríes", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-28.46301, -62.11052], "ey": 1850, "ly": 2022},
  {"key": "San Faustino-Colombia", "n": "San Faustino", "c": "Colombia", "r": "col_norte_de_santander", "ll": [8.06253, -72.40533], "ey": 1525, "ly": 2018, "al": ["san faustino de los rios", "San Faustino de los Rios"]},
  {"key": "Tambo de Quilcata-Peru", "n": "Tambo de Quilcata", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.61759, -74.22907], "ey": -2000, "ly": 1532, "al": ["achalla", "arqueológico mullocorral", "arqueológico pachara"]},
  {"key": "San Gregorio-Argentina", "n": "San Gregorio", "c": "Argentina", "r": "arg_santa_fe", "ll": [-34.32536, -62.0359], "ey": 1850, "ly": 2022},
  {"key": "Pilar (arg_santa_fe)-Argentina", "n": "Pilar", "c": "Argentina", "r": "arg_santa_fe", "ll": [-31.4404, -61.25957], "ey": 1850, "ly": 2022},
  {"key": "Mopa-Argentina", "n": "Mopa", "c": "Argentina", "r": "crp_gran_chaco_frontier", "ll": [-28.176, -63.212], "ey": 1536, "ly": 1790},
  {"key": "Humboldt-Argentina", "n": "Humboldt", "c": "Argentina", "r": "arg_santa_fe", "ll": [-31.40084, -61.08226], "ey": 1850, "ly": 2022},
  {"key": "Itoco-Colombia", "n": "Itoco", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.557, -74.174], "ey": 1525, "ly": 1830},
  {"key": "Villa Caro-Colombia", "n": "Villa Caro", "c": "Colombia", "r": "col_norte_de_santander", "ll": [7.91424, -72.9736], "ey": 1850, "ly": 2025},
  {"key": "San Carlos (arg_misiones)-Argentina", "n": "San Carlos", "c": "Argentina", "r": "arg_misiones", "ll": [-27.7436, -55.89845], "ey": 1631, "ly": 2022},
  {"key": "Facala-Peru", "n": "Facala", "c": "Peru", "r": "per_la_libertad", "ll": [-7.7238, -79.1586], "ey": 1525, "ly": 2017, "al": ["tacala", "Tacala"]},
  {"key": "Itá Ibaté-Argentina", "n": "Itá Ibaté", "c": "Argentina", "r": "arg_corrientes", "ll": [-27.42595, -57.33812], "ey": 1536, "ly": 2022, "al": ["ita ibate", "tabacze", "tabazte"]},
  {"key": "Alto Saposoa-Peru", "n": "Alto Saposoa", "c": "Peru", "r": "per_san_martin", "ll": [-6.76472, -76.81361], "ey": 1900, "ly": 2025, "al": ["pasarraya", "Pasarraya"]},
  {"key": "Machupitumarka-Peru", "n": "Machupitumarka", "c": "Peru", "r": "inca_antisuyu", "ll": [-13.51645, -71.6073], "ey": 0, "ly": 1530, "al": ["huataorqo", "quisicancha", "saracmachay"]},
  {"key": "Gobernador Gregores-Argentina", "n": "Gobernador Gregores", "c": "Argentina", "r": "arg_santa_cruz", "ll": [-48.75085, -70.24852], "ey": 1900, "ly": 2022},
  {"key": "El Tigral O La Puntilla-Peru", "n": "El Tigral O La Puntilla", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.80762, -74.87368], "ey": -1000, "ly": 1530, "al": ["pampa de los camelidos", "acueductos de cantalloc", "la tiza"]},
  {"key": "Arqueológico Chaulla Pampa-Peru", "n": "Arqueológico Chaulla Pampa", "c": "Peru", "r": "inca_collasuyu", "ll": [-15.53534, -70.09785], "ey": 0, "ly": 1530, "al": ["cerro monos", "cerro cruz de taparach", "cerro espinal"]},
  {"key": "Tumusla-Bolivia", "n": "Tumusla", "c": "Bolivia", "r": "bol_potosi", "ll": [-20.48891, -65.61799], "ey": 1525, "ly": 2024, "al": ["tumula", "tomola", "Tomola"]},
  {"key": "Potrero de Payogasta-Argentina", "n": "Potrero de Payogasta", "c": "Argentina", "r": "inca_collasuyu", "ll": [-24.996, -66.101], "ey": 1475, "ly": 1530},
  {"key": "Terlen - La Bomba-Peru", "n": "Terlen - La Bomba", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.18379, -79.03142], "ey": 0, "ly": 1530, "al": ["yatahual", "Yatahual"]},
  {"key": "Pózul-Ecuador", "n": "Pózul", "c": "Ecuador", "r": "ecu_loja", "ll": [-4.12522, -80.04609], "ey": 1525, "ly": 2025, "al": ["san juan de pozul", "pozol", "San Juan de Pozul"]},
  {"key": "Las Perdices-Argentina", "n": "Las Perdices", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.69906, -63.70466], "ey": 1850, "ly": 2022}
]

HEADERS = {"User-Agent": "SVEA-Toponymy-Lookup/1.0 (contact@confoederatio.org)"}

def fetch_json(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=12) as resp:
    return json.loads(resp.read().decode("utf-8"))

def lookup_item(it):
  lat, lng = it["ll"]
  name = it["n"]
  country = it["c"]
  out = {"key": it["key"], "n": name, "c": country, "geo": [], "search": []}
  try:
    gurl = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}%7C{lng}&gsradius=10000&gslimit=5&format=json"
    gd = fetch_json(gurl)
    for g in gd.get("query", {}).get("geosearch", []):
      out["geo"].append({"title": g["title"], "dist": g["dist"]})
  except Exception as e:
    out["geo_err"] = str(e)
  try:
    q = urllib.parse.quote(f"{name} {country}")
    surl = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
    sd = fetch_json(surl)
    for s in sd.get("query", {}).get("search", []):
      out["search"].append({"title": s["title"], "snippet": s["snippet"]})
  except Exception as e:
    out["search_err"] = str(e)
  return out

with ThreadPoolExecutor(max_workers=10) as ex:
  results = list(ex.map(lookup_item, ITEMS))

with open("tests/tmp_quipu_029_wiki.json", "w", encoding="utf-8") as f:
  json.dump(results, f, ensure_ascii=False, indent=2)
print("Saved", len(results), "results")
