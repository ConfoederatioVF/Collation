import urllib.request, urllib.parse, json, time

UA = "SVEAToponymyResearch/1.0 (https://confoederatio.org; research@confoederatio.org)"

items = [
  {"key": "Tambería del Inca-Argentina", "n": "Tambería del Inca", "c": "Argentina", "ll": [-29.17, -67.508], "t": "Tambería del Inca"},
  {"key": "San Jose Pelarco-Chile", "n": "San Jose Pelarco", "c": "Chile", "ll": [-35.384, -71.447], "t": "Pelarco"},
  {"key": "Picún Leufú-Argentina", "n": "Picún Leufú", "c": "Argentina", "ll": [-39.51866, -69.29114], "t": "Picún Leufú"},
  {"key": "Quemú Quemú-Argentina", "n": "Quemú Quemú", "c": "Argentina", "ll": [-36.05482, -63.56586], "t": "Quemú Quemú"},
  {"key": "Loma-Bolivia", "n": "Loma", "c": "Bolivia", "ll": [-20.917, -64.767], "t": "Pilaya"},
  {"key": "El Hoyo-Argentina", "n": "El Hoyo", "c": "Argentina", "ll": [-42.06413, -71.51921], "t": "El Hoyo (Chubut)"},
  {"key": "RG02 - Jarana-Peru", "n": "RG02 - Jarana", "c": "Peru", "ll": [-15.93478, -73.10793], "t": "Jarana"},
  {"key": "Los Andes (col_magdalena)-Colombia", "n": "Los Andes", "c": "Colombia", "ll": [9.58124, -74.35367], "t": "Nueva Granada (Magdalena)"},
  {"key": "Relleno Sanitario de Girardot-Colombia", "n": "Relleno Sanitario de Girardot", "c": "Colombia", "ll": [4.32685, -74.85935], "t": "Girardot"},
  {"key": "Jatun Ushco-Peru", "n": "Jatun Ushco", "c": "Peru", "ll": [-10.13317, -76.20072], "t": "Jatun Ushco"},
  {"key": "San José de Tocomita-Venezuela", "n": "San José de Tocomita", "c": "Venezuela", "ll": [7.42764, -63.27507], "t": "Tocomita"},
  {"key": "San Pedro (ven_zulia)-Venezuela", "n": "San Pedro", "c": "Venezuela", "ll": [9.78733, -70.8957], "t": "San Pedro (Zulia)"},
  {"key": "Sacháyoj-Argentina", "n": "Sacháyoj", "c": "Argentina", "ll": [-26.67542, -61.81511], "t": "Sacháyoj"},
  {"key": "Obonuco-Colombia", "n": "Obonuco", "c": "Colombia", "ll": [1.19015, -77.30681], "t": "Obonuco"},
  {"key": "Mámbita-Colombia", "n": "Mámbita", "c": "Colombia", "ll": [4.76523, -73.32422], "t": "Mámbita"},
  {"key": "Curaco de Vélez-Chile", "n": "Curaco de Vélez", "c": "Chile", "ll": [-42.42745, -73.56814], "t": "Curaco de Vélez"},
  {"key": "Contratación-Colombia", "n": "Contratación", "c": "Colombia", "ll": [6.29056, -73.47443], "t": "Contratación (Santander)"},
  {"key": "Lita-Ecuador", "n": "Lita", "c": "Ecuador", "ll": [0.76488, -78.38831], "t": "Lita (Ecuador)"},
  {"key": "Ch´acco Kunca-Peru", "n": "Ch´acco Kunca", "c": "Peru", "ll": [-14.77684, -70.2869], "t": "Asillo"},
  {"key": "Sitios Las Águilas-Colombia", "n": "Sitios Las Águilas", "c": "Colombia", "ll": [10.32553, -75.45967], "t": "Turbaco"},
  {"key": "Caunapí-Colombia_2", "n": "Caunapí", "c": "Colombia", "ll": [1.44089, -78.61499], "t": "Caunapí"},
  {"key": "San Agustin de Huaychao-Peru", "n": "San Agustin de Huaychao", "c": "Peru", "ll": [-10.9895, -76.4307], "t": "Huaychao"},
  {"key": "Sausal-Peru", "n": "Sausal", "c": "Peru", "ll": [-7.734, -79.0045], "t": "Sausal"},
  {"key": "Sayani-Peru", "n": "Sayani", "c": "Peru", "ll": [-14.196, -69.47], "t": "Sayani"},
  {"key": "Guaqui-Bolivia", "n": "Guaqui", "c": "Bolivia", "ll": [-16.59751, -68.83693], "t": "Guaqui"},
  {"key": "Palma Real-Ecuador", "n": "Palma Real", "c": "Ecuador", "ll": [1.131, -78.978], "t": "Palma Real"},
  {"key": "San Isidro-Argentina_2", "n": "San Isidro", "c": "Argentina", "ll": [-31.82283, -64.39066], "t": "San Isidro"},
  {"key": "Sicaya-Bolivia", "n": "Sicaya", "c": "Bolivia", "ll": [-17.79964, -66.33421], "t": "Sicaya (Bolivia)"},
  {"key": "Granja La Fabiola-Colombia", "n": "Granja La Fabiola", "c": "Colombia", "ll": [4.7031, -75.85615], "t": "Obando (Valle del Cauca)"},
  {"key": "Santa Rosalía-Colombia", "n": "Santa Rosalía", "c": "Colombia", "ll": [5.13639, -70.8595], "t": "Santa Rosalía (Vichada)"},
  {"key": "Llica-Bolivia", "n": "Llica", "c": "Bolivia", "ll": [-19.85066, -68.24847], "t": "Llica"},
  {"key": "Huertos Familiares-Chile", "n": "Huertos Familiares", "c": "Chile", "ll": [-33.13896, -70.80308], "t": "Huertos Familiares (Tiltil)"},
  {"key": "Chinavita-Colombia", "n": "Chinavita", "c": "Colombia", "ll": [5.16749, -73.36848], "t": "Chinavita"},
  {"key": "Pasto Grande-Peru", "n": "Pasto Grande", "c": "Peru", "ll": [-14.09406, -71.4398], "t": "Pasto Grande"},
  {"key": "Huancarum-Peru", "n": "Huancarum", "c": "Peru", "ll": [-10.16735, -76.1086], "t": "Huancarum"},
  {"key": "Rio Segundo-Argentina", "n": "Rio Segundo", "c": "Argentina", "ll": [-31.553, -63.532], "t": "Villa del Rosario (Córdoba)"},
  {"key": "Loreto - Molino-Chile", "n": "Loreto - Molino", "c": "Chile", "ll": [-34.26396, -71.02206], "t": "Coltauco"},
  {"key": "Ayapata-Peru_2", "n": "Ayapata", "c": "Peru", "ll": [-14.24109, -74.0279], "t": "Ayapata"},
  {"key": "Caimani-Bolivia", "n": "Caimani", "c": "Bolivia", "ll": [-17.082, -66.919], "t": "Caimani"},
  {"key": "Churidó-Colombia", "n": "Churidó", "c": "Colombia", "ll": [7.86546, -76.66717], "t": "Churidó"},
  {"key": "Ascensión-Argentina", "n": "Ascensión", "c": "Argentina", "ll": [-34.23082, -61.10342], "t": "Ascensión (Buenos Aires)"},
  {"key": "La Peaña-Ecuador", "n": "La Peaña", "c": "Ecuador", "ll": [-3.31278, -79.85481], "t": "La Peaña"},
  {"key": "San Antonio Bebara-Colombia", "n": "San Antonio Bebara", "c": "Colombia", "ll": [6.091, -76.571], "t": "Bebará"},
  {"key": "Singapur-Colombia", "n": "Singapur", "c": "Colombia", "ll": [5.75889, -74.71833], "t": "Singapur"},
  {"key": "San José de Unare-Venezuela", "n": "San José de Unare", "c": "Venezuela", "ll": [9.46944, -65.23222], "t": "San José de Unare"},
  {"key": "Tahuamanu-Peru", "n": "Tahuamanu", "c": "Peru", "ll": [-11.45472, -69.32139], "t": "Distrito de Tahuamanu"},
  {"key": "Santa Rosa Chica-Chile", "n": "Santa Rosa Chica", "c": "Chile", "ll": [-40.17919, -72.56272], "t": "Lago Ranco"},
  {"key": "José Manuel Quiroz-Peru", "n": "José Manuel Quiroz", "c": "Peru", "ll": [-7.34944, -78.04778], "t": "Distrito de José Manuel Quiroz"},
  {"key": "Aji-Colombia", "n": "Aji", "c": "Colombia", "ll": [3.95, -77.103], "t": "Buenaventura (Valle del Cauca)"},
  {"key": "Tambillo (per_la_libertad)-Peru", "n": "Tambillo", "c": "Peru", "ll": [-7.8088, -78.5482], "t": "Tambillo"},
  {"key": "Huanifaya-Bolivia", "n": "Huanifaya", "c": "Bolivia", "ll": [-18.862, -65.246], "t": "Huanifaya"},
  {"key": "Hda La Cristalina-Colombia", "n": "Hda La Cristalina", "c": "Colombia", "ll": [5.901, -75.72908], "t": "Fredonia (Antioquia)"},
  {"key": "Carpintería-Argentina", "n": "Carpintería", "c": "Argentina", "ll": [-32.4101, -65.01001], "t": "Carpintería (San Luis)"},
  {"key": "Altagracia Pedraza-Venezuela", "n": "Altagracia Pedraza", "c": "Venezuela", "ll": [8.412, -70.651], "t": "Ciudad Bolivia"},
  {"key": "San Lucas de Amboca-Ecuador", "n": "San Lucas de Amboca", "c": "Ecuador", "ll": [-3.732, -79.276], "t": "San Lucas (Loja)"},
  {"key": "Manchac 2 - Pirushto-Peru", "n": "Manchac 2 - Pirushto", "c": "Peru", "ll": [-9.06748, -76.88647], "t": "Manchac"},
  {"key": "Tres De Noviembre-Ecuador", "n": "Tres De Noviembre", "c": "Ecuador", "ll": [-0.15883, -76.94979], "t": "Tres de Noviembre"},
  {"key": "La Francia-Argentina", "n": "La Francia", "c": "Argentina", "ll": [-31.40635, -62.63324], "t": "La Francia (Córdoba)"},
  {"key": "Duanga-Colombia", "n": "Duanga", "c": "Colombia", "ll": [10.021, -75.25], "t": "Duanga"},
  {"key": "El Riacho-Argentina", "n": "El Riacho", "c": "Argentina", "ll": [-42.20224, -64.91723], "t": "El Riacho"},
  {"key": "Chala Viejo-Peru", "n": "Chala Viejo", "c": "Peru", "ll": [-15.76454, -74.20481], "t": "Chala Viejo"},
  {"key": "Chulumani Yungas-Bolivia", "n": "Chulumani Yungas", "c": "Bolivia", "ll": [-16.41, -67.526], "t": "Chulumani"},
  {"key": "Pajchiri-Bolivia", "n": "Pajchiri", "c": "Bolivia", "ll": [-16.369, -68.615], "t": "Pajchiri"},
  {"key": "Gorgor-Peru", "n": "Gorgor", "c": "Peru", "ll": [-10.62111, -77.04139], "t": "Distrito de Gorgor"},
  {"key": "Huatasani-Peru", "n": "Huatasani", "c": "Peru", "ll": [-15.05944, -69.80194], "t": "Distrito de Huatasani"},
  {"key": "Cibaya-Chile", "n": "Cibaya", "c": "Chile", "ll": [-19.782, -69.173], "t": "Sibaya"},
  {"key": "Uia (na_magdalena_cauca_muisca_2)-Colombia", "n": "Uia", "c": "Colombia", "ll": [7.01817, -73.68181], "t": "San Vicente de Chucurí"},
  {"key": "Atahualpa (ecu_santa_elena)-Ecuador", "n": "Atahualpa", "c": "Ecuador", "ll": [-2.32102, -80.77561], "t": "Atahualpa (Santa Elena)"},
  {"key": "Huayrapata-Peru", "n": "Huayrapata", "c": "Peru", "ll": [-15.32139, -69.34111], "t": "Distrito de Huayrapata"},
  {"key": "La Clotilde-Argentina", "n": "La Clotilde", "c": "Argentina", "ll": [-27.17741, -60.63256], "t": "La Clotilde"},
  {"key": "Capiñata-Bolivia", "n": "Capiñata", "c": "Bolivia", "ll": [-17.133, -66.983], "t": "Capiñata"},
  {"key": "Timusi-Bolivia", "n": "Timusi", "c": "Bolivia", "ll": [-15.66851, -68.85771], "t": "Timusi"},
  {"key": "Sativanorte-Colombia", "n": "Sativanorte", "c": "Colombia", "ll": [6.13113, -72.70846], "t": "Sativanorte"},
  {"key": "Tingo-Ecuador", "n": "Tingo", "c": "Ecuador", "ll": [-0.93659, -79.11649], "t": "El Tingo (Cotopaxi)"},
  {"key": "El Dorado-Colombia", "n": "El Dorado", "c": "Colombia", "ll": [3.73998, -73.83526], "t": "El Dorado (Meta)"},
  {"key": "El Pedregal-Colombia", "n": "El Pedregal", "c": "Colombia", "ll": [6.18966, -75.61742], "t": "Itagüí"},
  {"key": "Tambo del Collao-Peru", "n": "Tambo del Collao", "c": "Peru", "ll": [-14.7675, -75.03895], "t": "Tambo del Collao"},
  {"key": "Pueblo Andino-Argentina", "n": "Pueblo Andino", "c": "Argentina", "ll": [-32.6699, -60.87553], "t": "Pueblo Andino"},
  {"key": "Inkavado-Peru", "n": "Inkavado", "c": "Peru", "ll": [-10.23122, -76.65346], "t": "Inkavado"},
  {"key": "Campo-Colombia", "n": "Campo", "c": "Colombia", "ll": [6.86544, -73.76683], "t": "Barrancabermeja"},
  {"key": "Daniel Córdova Toral-Ecuador", "n": "Daniel Córdova Toral", "c": "Ecuador", "ll": [-2.87785, -78.72053], "t": "Daniel Córdova Toral"},
  {"key": "La Esperanza-Chile_2", "n": "La Esperanza", "c": "Chile", "ll": [-40.14442, -72.52542], "t": "Futrono"},
  {"key": "San Rafael de Palo Alzado-Venezuela", "n": "San Rafael de Palo Alzado", "c": "Venezuela", "ll": [9.31444, -70.05611], "t": "San Rafael de Palo Alzado"},
  {"key": "Cem. A. Paicarabi y Fredes-Argentina", "n": "Cem. A. Paicarabi y Fredes", "c": "Argentina", "ll": [-34.2289, -58.5924], "t": "Paicarabí"},
  {"key": "Colonia Valdense-Uruguay", "n": "Colonia Valdense", "c": "Uruguay", "ll": [-34.34194, -57.2636], "t": "Colonia Valdense"},
  {"key": "Herradura-Argentina", "n": "Herradura", "c": "Argentina", "ll": [-26.48985, -58.31173], "t": "Herradura (Formosa)"},
  {"key": "Santiago (col_norte_de_santander)-Colombia", "n": "Santiago", "c": "Colombia", "ll": [7.86586, -72.7162], "t": "Santiago (Norte de Santander)"},
  {"key": "María Teresa-Argentina", "n": "María Teresa", "c": "Argentina", "ll": [-34.00483, -61.90159], "t": "María Teresa (Santa Fe)"},
  {"key": "San Salvador del Rio de la Plata-Uruguay", "n": "San Salvador del Rio de la Plata", "c": "Uruguay", "ll": [-33.672, -58.352], "t": "San Salvador (Uruguay)"},
  {"key": "Santa Rosa Calamuchita-Argentina", "n": "Santa Rosa Calamuchita", "c": "Argentina", "ll": [-32.069, -64.538], "t": "Santa Rosa de Calamuchita"},
]

def api(params):
  url = "https://es.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
  req = urllib.request.Request(url, headers={"User-Agent": UA})
  with urllib.request.urlopen(req, timeout=15) as r:
    return json.loads(r.read().decode("utf-8"))

titles = list(dict.fromkeys([x["t"] for x in items]))
by_title = {}
for i in range(0, len(titles), 45):
  chunk = titles[i:i+45]
  p = api({"action":"query","titles":"|".join(chunk),"prop":"extracts|coordinates","exintro":"1","explaintext":"1","exlimit":"max","colimit":"max","redirects":"1","format":"json"})
  norm = {x["from"]: x["to"] for x in p.get("query",{}).get("normalized",[])}
  redir = {x["from"]: x["to"] for x in p.get("query",{}).get("redirects",[])}
  pages = {}
  for pg in p.get("query",{}).get("pages",{}).values():
    if "missing" not in pg:
      pages[pg["title"]] = pg
  for t in chunk:
    cur = norm.get(t, t)
    cur = redir.get(cur, cur)
    if cur in pages:
      by_title[t] = pages[cur]
  time.sleep(0.5)

for it in items:
  pg = by_title.get(it["t"])
  if pg:
    coords = pg.get("coordinates",[{}])[0]
    clat, clng = coords.get("lat"), coords.get("lon")
    txt = pg.get("extract","").replace("\n"," ")[:500]
    print(f"OK | {it['key']} | [{pg['title']}] ({clat},{clng}) | {txt}")
  else:
    print(f"MISS | {it['key']} | {it['t']}")
