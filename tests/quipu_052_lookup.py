import json, urllib.request, urllib.parse, time

ITEMS = [
  {"key": "El Arenal-Chile_2", "n": "El Arenal", "c": "Chile", "ll": [-37.3715, -73.6124], "ey": 1022},
  {"key": "Nacimiento-Chile_2", "n": "Nacimiento", "c": "Chile", "ll": [-37.502, -72.673], "ey": 1603},
  {"key": "Chavimochic-P-10-DE-Peru", "n": "Chavimochic-P-10-DE", "c": "Peru", "ll": [-7.67818, -79.1764], "ey": 0},
  {"key": "Morela-Colombia", "n": "Morela", "c": "Colombia", "ll": [6.48604, -74.41563], "ey": -694},
  {"key": "Caruya-Peru", "n": "Caruya", "c": "Peru", "ll": [-13.40399, -75.91365], "ey": 0},
  {"key": "La Petrolea-Venezuela", "n": "La Petrolea", "c": "Venezuela", "ll": [7.68402, -72.35373], "ey": 1850},
  {"key": "Reyes Vargas-Venezuela", "n": "Reyes Vargas", "c": "Venezuela", "ll": [10.39889, -69.84889], "ey": 1850},
  {"key": "Jima-Ecuador", "n": "Jima", "c": "Ecuador", "ll": [-3.21376, -78.90943], "ey": 1850},
  {"key": "Piura la Vieja-Peru", "n": "Piura la Vieja", "c": "Peru", "ll": [-5.1523, -80.0763], "ey": -2000},
  {"key": "Las Totoritas-Peru", "n": "Las Totoritas", "c": "Peru", "ll": [-12.68872, -76.65219], "ey": -1000},
  {"key": "Las Cejas-Argentina", "n": "Las Cejas", "c": "Argentina", "ll": [-26.88843, -64.74114], "ey": 1850},
  {"key": "Cerro Castillo-Chile_2", "n": "Cerro Castillo", "c": "Chile", "ll": [-51.27304, -72.34055], "ey": 1000},
  {"key": "Sevilla-Ecuador", "n": "Sevilla", "c": "Ecuador", "ll": [0.08476, -77.12569], "ey": 1920},
  {"key": "Hacienda San Germán-Colombia", "n": "Hacienda San Germán", "c": "Colombia", "ll": [5.15371, -74.72979], "ey": 0},
  {"key": "Caracato-Bolivia", "n": "Caracato", "c": "Bolivia", "ll": [-16.99264, -67.80918], "ey": 1525},
  {"key": "Cerro Cajamarcaorco-Peru", "n": "Cerro Cajamarcaorco", "c": "Peru", "ll": [-6.89515, -78.17108], "ey": 1000},
  {"key": "Tablazo-Colombia", "n": "Tablazo", "c": "Colombia", "ll": [5.925, -75.562], "ey": 1525},
  {"key": "Llaqtapata (inca_contisuyu)-Peru", "n": "Llaqtapata", "c": "Peru", "ll": [-13.65743, -74.20548], "ey": 1438},
  {"key": "El Llano 1-Colombia", "n": "El Llano 1", "c": "Colombia", "ll": [6.29458, -75.64948], "ey": -1000},
  {"key": "Caracolí (col_atlantico)-Colombia", "n": "Caracolí", "c": "Colombia", "ll": [10.85942, -74.83406], "ey": 1850},
  {"key": "Rivera-Argentina", "n": "Rivera", "c": "Argentina", "ll": [-37.16052, -63.24176], "ey": 1880},
  {"key": "Las Juntas-Bolivia", "n": "Las Juntas", "c": "Bolivia", "ll": [-21.811, -64.798], "ey": 1525},
  {"key": "Ventilla-Peru", "n": "Ventilla", "c": "Peru", "ll": [-14.965, -70.5], "ey": 1525},
  {"key": "Calzón de Oro-Colombia", "n": "Calzón de Oro", "c": "Colombia", "ll": [5.12778, -74.73528], "ey": 0},
  {"key": "Carmen Nogoya-Argentina", "n": "Carmen Nogoya", "c": "Argentina", "ll": [-32.399, -59.788], "ey": 1760},
  {"key": "Ica-Peru_2", "n": "Ica", "c": "Peru", "ll": [-14.34632, -75.66277], "ey": 1440},
  {"key": "La Encantada-Peru", "n": "La Encantada", "c": "Peru", "ll": [-5.093, -80.1999], "ey": 1850},
  {"key": "Caimare Chico-Venezuela", "n": "Caimare Chico", "c": "Venezuela", "ll": [11.14889, -71.82056], "ey": 1850},
  {"key": "Buenos Aires (per_amazonas)-Peru", "n": "Buenos Aires", "c": "Peru", "ll": [-5.7364, -77.9068], "ey": 1538},
  {"key": "Mainqué-Argentina", "n": "Mainqué", "c": "Argentina", "ll": [-39.06376, -67.30428], "ey": 1900},
  {"key": "San Francisco de Asis de Pucara-Peru", "n": "San Francisco de Asis de Pucara", "c": "Peru", "ll": [-11.5946, -76.082], "ey": 1525},
  {"key": "Irique-Colombia", "n": "Irique", "c": "Colombia", "ll": [3.47844, -73.66213], "ey": -1000},
  {"key": "Sarapia-Peru", "n": "Sarapia", "c": "Peru", "ll": [-13.74532, -70.4622], "ey": -3000},
  {"key": "Vilcasmarca-Peru", "n": "Vilcasmarca", "c": "Peru", "ll": [-11.35453, -75.63342], "ey": 1000},
  {"key": "Paucara-Peru_2", "n": "Paucara", "c": "Peru", "ll": [-15.16987, -70.15869], "ey": 500},
  {"key": "SE Purnio Torre-Colombia", "n": "SE Purnio Torre", "c": "Colombia", "ll": [5.41082, -74.72267], "ey": 500},
  {"key": "San Fernando de Tataracual-Venezuela", "n": "San Fernando de Tataracual", "c": "Venezuela", "ll": [10.33311, -64.09016], "ey": 1850},
  {"key": "La Viña-Argentina", "n": "La Viña", "c": "Argentina", "ll": [-25.46806, -65.56563], "ey": 1850},
  {"key": "Ulapes-Argentina", "n": "Ulapes", "c": "Argentina", "ll": [-31.57272, -66.23758], "ey": 1536},
  {"key": "Almagro-Argentina", "n": "Almagro", "c": "Argentina", "ll": [-31.09, -60.594], "ey": 1793},
  {"key": "valle de San Andres-Argentina", "n": "valle de San Andres", "c": "Argentina", "ll": [-22.2, -65], "ey": 1525},
  {"key": "Caleta Huelen-Chile", "n": "Caleta Huelen", "c": "Chile", "ll": [-21.4319, -70.0487], "ey": -102},
  {"key": "Mariano Moreno-Ecuador", "n": "Mariano Moreno", "c": "Ecuador", "ll": [-2.84088, -78.72487], "ey": 1850},
  {"key": "Chunchunga-Peru", "n": "Chunchunga", "c": "Peru", "ll": [-5.201, -78.288], "ey": 1525},
  {"key": "Doa-Colombia", "n": "Doa", "c": "Colombia", "ll": [4.217, -74.492], "ey": 1525},
  {"key": "San Miguel (col_narino)-Colombia", "n": "San Miguel", "c": "Colombia", "ll": [1.18905, -77.94989], "ey": 1525},
  {"key": "Tres Algarrobos-Argentina", "n": "Tres Algarrobos", "c": "Argentina", "ll": [-35.19558, -62.77439], "ey": 1850},
  {"key": "Chámeza-Colombia", "n": "Chámeza", "c": "Colombia", "ll": [5.21453, -72.87016], "ey": 1525},
  {"key": "Napenay-Argentina", "n": "Napenay", "c": "Argentina", "ll": [-26.72957, -60.61678], "ey": 1900},
  {"key": "Tatacuá-Argentina", "n": "Tatacuá", "c": "Argentina", "ll": [-28.37428, -58.31978], "ey": 1850},
  {"key": "Zhidmad-Ecuador", "n": "Zhidmad", "c": "Ecuador", "ll": [-2.94201, -78.87775], "ey": 1850},
  {"key": "Lucma (per_ancash)-Peru", "n": "Lucma", "c": "Peru", "ll": [-8.91944, -77.41083], "ey": 1850},
  {"key": "Finca Canadá-Colombia", "n": "Finca Canadá", "c": "Colombia", "ll": [7.11019, -73.65226], "ey": 1300},
  {"key": "Achao-Chile", "n": "Achao", "c": "Chile", "ll": [-42.47104, -73.49062], "ey": 1525},
  {"key": "San Francisco del Chañar-Argentina", "n": "San Francisco del Chañar", "c": "Argentina", "ll": [-29.78639, -63.94167], "ey": 1850},
  {"key": "Mache-Peru", "n": "Mache", "c": "Peru", "ll": [-8.02917, -78.535], "ey": 1850},
  {"key": "Iguain-Peru", "n": "Iguain", "c": "Peru", "ll": [-12.9925, -74.20889], "ey": 1850},
  {"key": "Río Oscar-Chile", "n": "Río Oscar", "c": "Chile", "ll": [-52.8111, -69.7699], "ey": 1000},
  {"key": "Sebastián Elcano-Argentina", "n": "Sebastián Elcano", "c": "Argentina", "ll": [-30.16035, -63.59272], "ey": 1850},
  {"key": "Jose Batlle Y Ordoñez-Uruguay", "n": "Jose Batlle Y Ordoñez", "c": "Uruguay", "ll": [-33.52208, -55.11992], "ey": 1850},
  {"key": "Concentración (inca_collasuyu)-Chile", "n": "Concentración", "c": "Chile", "ll": [-19.22899, -68.75167], "ey": 1300},
  {"key": "Linau-Chile", "n": "Linau", "c": "Chile", "ll": [-41.966, -73.541], "ey": 1525},
  {"key": "Karaparial-Bolivia", "n": "Karaparial", "c": "Bolivia", "ll": [-18.03582, -64.96767], "ey": -653},
  {"key": "Tres Palmas-Colombia_2", "n": "Tres Palmas", "c": "Colombia", "ll": [8.48497, -75.95308], "ey": -2000},
  {"key": "San Francisco De Novillo-Ecuador", "n": "San Francisco De Novillo", "c": "Ecuador", "ll": [-0.19288, -79.84069], "ey": 1850},
  {"key": "Yanamilla-Peru", "n": "Yanamilla", "c": "Peru", "ll": [-13.1431, -74.1914], "ey": 1850},
  {"key": "Bandurria-Peru", "n": "Bandurria", "c": "Peru", "ll": [-11.18782, -77.58458], "ey": 1438},
  {"key": "Ipem-Argentina", "n": "Ipem", "c": "Argentina", "ll": [-29.91389, -63.72298], "ey": 80},
  {"key": "Berrugas-Colombia", "n": "Berrugas", "c": "Colombia", "ll": [9.69834, -75.61449], "ey": 1850},
  {"key": "Vetas-Colombia", "n": "Vetas", "c": "Colombia", "ll": [7.30981, -72.87104], "ey": 1525},
  {"key": "Cortaderas-Argentina", "n": "Cortaderas", "c": "Argentina", "ll": [-32.50523, -64.9922], "ey": 1850},
  {"key": "Cumarebo-Venezuela", "n": "Cumarebo", "c": "Venezuela", "ll": [11.486, -69.35], "ey": 1538},
  {"key": "Ingenio de Oro-Bolivia", "n": "Ingenio de Oro", "c": "Bolivia", "ll": [-21.309, -65.964], "ey": 1525},
  {"key": "El Milagro (per_cajamarca_2)-Peru", "n": "El Milagro", "c": "Peru", "ll": [-7.107, -78.5373], "ey": 1850},
  {"key": "Ucureña-Bolivia", "n": "Ucureña", "c": "Bolivia", "ll": [-17.5813, -65.91193], "ey": 1850},
  {"key": "La Pasera-Colombia", "n": "La Pasera", "c": "Colombia", "ll": [1.01314, -76.51068], "ey": 0},
  {"key": "Ángel Vicente Peñaloza-Argentina", "n": "Ángel Vicente Peñaloza", "c": "Argentina", "ll": [-30.3129, -66.66305], "ey": 1850},
  {"key": "Lusitania-Colombia_2", "n": "Lusitania", "c": "Colombia", "ll": [3.84987, -76.39338], "ey": 500},
  {"key": "Dos Arroyos-Argentina", "n": "Dos Arroyos", "c": "Argentina", "ll": [-27.69938, -55.25018], "ey": 1900},
  {"key": "Enea-Colombia", "n": "Enea", "c": "Colombia", "ll": [11.309, -73.206], "ey": 1525},
  {"key": "Conchal Duna Grande-Peru", "n": "Conchal Duna Grande", "c": "Peru", "ll": [-15.11718, -74.88374], "ey": 500},
  {"key": "Pucaran-Peru", "n": "Pucaran", "c": "Peru", "ll": [-14.87745, -70.23413], "ey": 1300},
  {"key": "Rebellín-Chile", "n": "Rebellín", "c": "Chile", "ll": [-39.72751, -73.19056], "ey": 0},
  {"key": "Ecilda Paullier-Uruguay", "n": "Ecilda Paullier", "c": "Uruguay", "ll": [-34.36089, -57.05339], "ey": 1850},
  {"key": "La Torre-Chile", "n": "La Torre", "c": "Chile", "ll": [-30.6159, -71.37315], "ey": 1525},
  {"key": "Tacaquira-Bolivia", "n": "Tacaquira", "c": "Bolivia", "ll": [-20.54, -65.149], "ey": 1525},
  {"key": "Pampa Tierra Firme-Peru", "n": "Pampa Tierra Firme", "c": "Peru", "ll": [-9.14894, -78.37245], "ey": -1000},
  {"key": "Vilcabamba-Peru_2", "n": "Vilcabamba", "c": "Peru", "ll": [-12.905, -73.208], "ey": 1470},
  {"key": "Concepción del Bermejo Prehispanic-Argentina", "n": "Concepción del Bermejo Prehispanic", "c": "Argentina", "ll": [-26.598, -60.432], "ey": 600},
  {"key": "Pampa de Reque-Peru", "n": "Pampa de Reque", "c": "Peru", "ll": [-6.88232, -79.77325], "ey": -3000}
]

HDR = {"User-Agent": "SVEA-Historical-Research/1.0 (https://confoederatio.org)"}

def fetch_json(url):
  req = urllib.request.Request(url, headers=HDR)
  with urllib.request.urlopen(req, timeout=12) as r:
    return json.loads(r.read().decode("utf-8"))

with open("tests/quipu_052_wiki.json", "r", encoding="utf-8") as f:
  prev = {r["key"]: r for r in json.load(f)}

out = []
for item in ITEMS:
  r = prev.get(item["key"], {"key": item["key"], "n": item["n"], "c": item["c"], "geo": [], "search": []})
  if "geo_err" in r or "search_err" in r or (not r["geo"] and not r["search"]):
    lat, lng = item["ll"]
    r = {"key": item["key"], "n": item["n"], "c": item["c"], "geo": [], "search": []}
    try:
      u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
      j = fetch_json(u)
      r["geo"] = [{"title": x["title"], "dist": x["dist"]} for x in j.get("query", {}).get("geosearch", [])]
    except Exception as e:
      r["geo_err"] = str(e)
    time.sleep(0.08)
    try:
      q = urllib.parse.quote(f'"{item["n"]}" {item["c"]}')
      u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
      j = fetch_json(u)
      r["search"] = [x["title"] for x in j.get("query", {}).get("search", [])]
    except Exception as e:
      r["search_err"] = str(e)
    time.sleep(0.08)
  out.append(r)

with open("tests/quipu_052_wiki.json", "w", encoding="utf-8") as f:
  json.dump(out, f, ensure_ascii=False, indent=2)

for r in out[35:]:
  geo_s = ", ".join(f"{g['title']}({int(g['dist'])}m)" for g in r["geo"][:3])
  print(f"{r['key']} | GEO: [{geo_s}] | SRCH: {r['search']}")
