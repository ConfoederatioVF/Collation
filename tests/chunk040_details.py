import urllib.request, urllib.parse, json, time, re

UA = "SVEAToponymyResearch/1.0 (https://confoederatio.org; research@confoederatio.org)"

# Read items from tests/chunk040_research.py? No, define full list cleanly.
items = [
  {"key": "Tambería del Inca-Argentina", "n": "Tambería del Inca", "c": "Argentina", "ll": [-29.17, -67.508], "t": "Tamberías del Inca"},
  {"key": "San Jose Pelarco-Chile", "n": "San Jose Pelarco", "c": "Chile", "ll": [-35.384, -71.447], "t": "Pelarco"},
  {"key": "Picún Leufú-Argentina", "n": "Picún Leufú", "c": "Argentina", "ll": [-39.51866, -69.29114], "t": "Picún Leufú"},
  {"key": "Quemú Quemú-Argentina", "n": "Quemú Quemú", "c": "Argentina", "ll": [-36.05482, -63.56586], "t": "Quemú Quemú"},
  {"key": "Loma-Bolivia", "n": "Loma", "c": "Bolivia", "ll": [-20.917, -64.767], "t": "Pilaya"},
  {"key": "El Hoyo-Argentina", "n": "El Hoyo", "c": "Argentina", "ll": [-42.06413, -71.51921], "t": "El Hoyo (Argentina)"},
  {"key": "Los Andes (col_magdalena)-Colombia", "n": "Los Andes", "c": "Colombia", "ll": [9.58124, -74.35367], "t": "Nueva Granada (Magdalena)"},
  {"key": "Relleno Sanitario de Girardot-Colombia", "n": "Relleno Sanitario de Girardot", "c": "Colombia", "ll": [4.32685, -74.85935], "t": "Girardot"},
  {"key": "San José de Tocomita-Venezuela", "n": "San José de Tocomita", "c": "Venezuela", "ll": [7.42764, -63.27507], "t": "Tocomita"},
  {"key": "San Pedro (ven_zulia)-Venezuela", "n": "San Pedro", "c": "Venezuela", "ll": [9.78733, -70.8957], "t": "Municipio Baralt"},
  {"key": "Sacháyoj-Argentina", "n": "Sacháyoj", "c": "Argentina", "ll": [-26.67542, -61.81511], "t": "Sacháyoj"},
  {"key": "Obonuco-Colombia", "n": "Obonuco", "c": "Colombia", "ll": [1.19015, -77.30681], "t": "Obonuco"},
  {"key": "Mámbita-Colombia", "n": "Mámbita", "c": "Colombia", "ll": [4.76523, -73.32422], "t": "Mámbita"},
  {"key": "Curaco de Vélez-Chile", "n": "Curaco de Vélez", "c": "Chile", "ll": [-42.42745, -73.56814], "t": "Curaco de Vélez"},
  {"key": "Contratación-Colombia", "n": "Contratación", "c": "Colombia", "ll": [6.29056, -73.47443], "t": "Contratación"},
  {"key": "Lita-Ecuador", "n": "Lita", "c": "Ecuador", "ll": [0.76488, -78.38831], "t": "Parroquia Lita"},
  {"key": "San Agustin de Huaychao-Peru", "n": "San Agustin de Huaychao", "c": "Peru", "ll": [-10.9895, -76.4307], "t": "Distrito de Huayllay"},
  {"key": "Sausal-Peru", "n": "Sausal", "c": "Peru", "ll": [-7.734, -79.0045], "t": "Sausal (Ascope)"},
  {"key": "Guaqui-Bolivia", "n": "Guaqui", "c": "Bolivia", "ll": [-16.59751, -68.83693], "t": "Guaqui"},
  {"key": "Palma Real-Ecuador", "n": "Palma Real", "c": "Ecuador", "ll": [1.131, -78.978], "t": "Cantón San Lorenzo"},
  {"key": "Sicaya-Bolivia", "n": "Sicaya", "c": "Bolivia", "ll": [-17.79964, -66.33421], "t": "Sicaya (Bolivia)"},
  {"key": "Santa Rosalía-Colombia", "n": "Santa Rosalía", "c": "Colombia", "ll": [5.13639, -70.8595], "t": "Santa Rosalía (Vichada)"},
  {"key": "Llica-Bolivia", "n": "Llica", "c": "Bolivia", "ll": [-19.85066, -68.24847], "t": "Llica"},
  {"key": "Huertos Familiares-Chile", "n": "Huertos Familiares", "c": "Chile", "ll": [-33.13896, -70.80308], "t": "Huertos Familiares (Tiltil)"},
  {"key": "Chinavita-Colombia", "n": "Chinavita", "c": "Colombia", "ll": [5.16749, -73.36848], "t": "Chinavita"},
  {"key": "Rio Segundo-Argentina", "n": "Rio Segundo", "c": "Argentina", "ll": [-31.553, -63.532], "t": "Villa del Rosario (Córdoba)"},
  {"key": "Loreto - Molino-Chile", "n": "Loreto - Molino", "c": "Chile", "ll": [-34.26396, -71.02206], "t": "Coltauco"},
  {"key": "Churidó-Colombia", "n": "Churidó", "c": "Colombia", "ll": [7.86546, -76.66717], "t": "Apartadó"},
  {"key": "Ascensión-Argentina", "n": "Ascensión", "c": "Argentina", "ll": [-34.23082, -61.10342], "t": "Ascensión (Buenos Aires)"},
  {"key": "La Peaña-Ecuador", "n": "La Peaña", "c": "Ecuador", "ll": [-3.31278, -79.85481], "t": "La Peaña"},
  {"key": "San José de Unare-Venezuela", "n": "San José de Unare", "c": "Venezuela", "ll": [9.46944, -65.23222], "t": "San José de Unare"},
  {"key": "Tahuamanu-Peru", "n": "Tahuamanu", "c": "Peru", "ll": [-11.45472, -69.32139], "t": "Distrito de Tahuamanu"},
  {"key": "José Manuel Quiroz-Peru", "n": "José Manuel Quiroz", "c": "Peru", "ll": [-7.34944, -78.04778], "t": "Distrito de José Manuel Quiroz"},
  {"key": "Carpintería-Argentina", "n": "Carpintería", "c": "Argentina", "ll": [-32.4101, -65.01001], "t": "Carpintería (San Luis)"},
  {"key": "Altagracia Pedraza-Venezuela", "n": "Altagracia Pedraza", "c": "Venezuela", "ll": [8.412, -70.651], "t": "Ciudad Bolivia"},
  {"key": "San Lucas de Amboca-Ecuador", "n": "San Lucas de Amboca", "c": "Ecuador", "ll": [-3.732, -79.276], "t": "San Lucas (Loja)"},
  {"key": "Tres De Noviembre-Ecuador", "n": "Tres De Noviembre", "c": "Ecuador", "ll": [-0.15883, -76.94979], "t": "Cantón Shushufindi"},
  {"key": "La Francia-Argentina", "n": "La Francia", "c": "Argentina", "ll": [-31.40635, -62.63324], "t": "La Francia (Córdoba)"},
  {"key": "Chulumani Yungas-Bolivia", "n": "Chulumani Yungas", "c": "Bolivia", "ll": [-16.41, -67.526], "t": "Chulumani"},
  {"key": "Pajchiri-Bolivia", "n": "Pajchiri", "c": "Bolivia", "ll": [-16.369, -68.615], "t": "Pajchiri"},
  {"key": "Gorgor-Peru", "n": "Gorgor", "c": "Peru", "ll": [-10.62111, -77.04139], "t": "Distrito de Gorgor"},
  {"key": "Huatasani-Peru", "n": "Huatasani", "c": "Peru", "ll": [-15.05944, -69.80194], "t": "Distrito de Huatasani"},
  {"key": "Cibaya-Chile", "n": "Cibaya", "c": "Chile", "ll": [-19.782, -69.173], "t": "Sibaya"},
  {"key": "Atahualpa (ecu_santa_elena)-Ecuador", "n": "Atahualpa", "c": "Ecuador", "ll": [-2.32102, -80.77561], "t": "Parroquia Atahualpa (Santa Elena)"},
  {"key": "Huayrapata-Peru", "n": "Huayrapata", "c": "Peru", "ll": [-15.32139, -69.34111], "t": "Distrito de Huayrapata"},
  {"key": "La Clotilde-Argentina", "n": "La Clotilde", "c": "Argentina", "ll": [-27.17741, -60.63256], "t": "La Clotilde"},
  {"key": "Capiñata-Bolivia", "n": "Capiñata", "c": "Bolivia", "ll": [-17.133, -66.983], "t": "Capiñata"},
  {"key": "Sativanorte-Colombia", "n": "Sativanorte", "c": "Colombia", "ll": [6.13113, -72.70846], "t": "Sativanorte"},
  {"key": "Tingo-Ecuador", "n": "Tingo", "c": "Ecuador", "ll": [-0.93659, -79.11649], "t": "El Tingo (Cotopaxi)"},
  {"key": "El Dorado-Colombia", "n": "El Dorado", "c": "Colombia", "ll": [3.73998, -73.83526], "t": "El Dorado (Meta)"},
  {"key": "El Pedregal-Colombia", "n": "El Pedregal", "c": "Colombia", "ll": [6.18966, -75.61742], "t": "Itagüí"},
  {"key": "Pueblo Andino-Argentina", "n": "Pueblo Andino", "c": "Argentina", "ll": [-32.6699, -60.87553], "t": "Pueblo Andino"},
  {"key": "Daniel Córdova Toral-Ecuador", "n": "Daniel Córdova Toral", "c": "Ecuador", "ll": [-2.87785, -78.72053], "t": "Daniel Córdova Toral (parroquia)"},
  {"key": "San Rafael de Palo Alzado-Venezuela", "n": "San Rafael de Palo Alzado", "c": "Venezuela", "ll": [9.31444, -70.05611], "t": "Municipio Sucre (Portuguesa)"},
  {"key": "Colonia Valdense-Uruguay", "n": "Colonia Valdense", "c": "Uruguay", "ll": [-34.34194, -57.2636], "t": "Colonia Valdense"},
  {"key": "Herradura-Argentina", "n": "Herradura", "c": "Argentina", "ll": [-26.48985, -58.31173], "t": "Herradura (Formosa)"},
  {"key": "Santiago (col_norte_de_santander)-Colombia", "n": "Santiago", "c": "Colombia", "ll": [7.86586, -72.7162], "t": "Santiago (Norte de Santander)"},
  {"key": "María Teresa-Argentina", "n": "María Teresa", "c": "Argentina", "ll": [-34.00483, -61.90159], "t": "María Teresa (Santa Fe)"},
  {"key": "San Salvador del Rio de la Plata-Uruguay", "n": "San Salvador del Rio de la Plata", "c": "Uruguay", "ll": [-33.672, -58.352], "t": "Dolores (Uruguay)"},
  {"key": "Santa Rosa Calamuchita-Argentina", "n": "Santa Rosa Calamuchita", "c": "Argentina", "ll": [-32.069, -64.538], "t": "Santa Rosa de Calamuchita"},
]

def api(params):
  url = "https://es.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
  req = urllib.request.Request(url, headers={"User-Agent": UA})
  with urllib.request.urlopen(req, timeout=20) as r:
    return json.loads(r.read().decode("utf-8"))

titles = list(dict.fromkeys([x["t"] for x in items]))
by_title = {}
for i in range(0, len(titles), 25):
  chunk = titles[i:i+25]
  p = api({"action":"query","titles":"|".join(chunk),"prop":"revisions|coordinates","rvprop":"content","rvslots":"main","colimit":"max","redirects":"1","format":"json"})
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
  if not pg:
    print(f"MISS | {it['key']} | {it['t']}")
    continue
  coords = pg.get("coordinates",[{}])[0]
  clat, clng = coords.get("lat"), coords.get("lon")
  wtxt = pg["revisions"][0]["slots"]["main"]["*"]
  # Extract infobox founding/name lines and Historia section
  info_lines = []
  for line in wtxt.splitlines()[:120]:
    low = line.lower()
    if any(k in low for k in ["fundac", "creac", "nombre", "erig", "fecha", "historia", "fundador", "otros_nombres", "antiguo"]):
      info_lines.append(line.strip())
  m = re.search(r'==+\s*(Historia|Toponimia|Etimolog[ií]a|Rese[ñn]a hist[óo]rica|Fundaci[óo]n).*?==+(.*?)(?:\n==|\Z)', wtxt, re.S | re.I)
  hist = m.group(2).strip().replace("\n"," ")[:900] if m else wtxt[:900].replace("\n"," ")
  print(f"=== {it['key']} | [{pg['title']}] ({clat},{clng})")
  if info_lines:
    print("  INFO:", " ; ".join(info_lines[:8]))
  print("  HIST:", hist)
