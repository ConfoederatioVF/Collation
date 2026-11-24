import json, urllib.request, urllib.parse, time

with open("tests/wiki_lookup.py", "r", encoding="utf-8") as f:
  src = f.read()

#Wait: let's define items directly cleanly
items = [
  {"key": "La Cueva de Ya-Argentina", "n": "La Cueva de Ya", "c": "Argentina", "r": "sc_gran_chaco_pilcomayo", "ll": [-22.1166, -65.4666], "ey": -9948, "ly": -6598},
  {"key": "Fundo Ainilebu-Chile", "n": "Fundo Ainilebu", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.84095, -72.77907], "ey": 0, "ly": 1500, "al": ["rancul", "tres montes"]},
  {"key": "La Milagrosa-Colombia", "n": "La Milagrosa", "c": "Colombia", "r": "col_cauca", "ll": [2.53303, -76.08593], "ey": 1525, "ly": 2018, "al": ["san pedro guanacas"]},
  {"key": "Santa Clara-Peru", "n": "Santa Clara", "c": "Peru", "r": "per_loreto", "ll": [-3.7853, -73.3393], "ey": 1920, "ly": 2017},
  {"key": "Santa Isabel-Argentina", "n": "Santa Isabel", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.88766, -61.69592], "ey": 1850, "ly": 2022},
  {"key": "Pueblo Nuevo (col_arauca)-Colombia", "n": "Pueblo Nuevo", "c": "Colombia", "r": "col_arauca", "ll": [6.68838, -71.34307], "ey": 1920, "ly": 2018},
  {"key": "Santa Clara-Ecuador", "n": "Santa Clara", "c": "Ecuador", "r": "ecu_napo", "ll": [-1.26455, -77.87546], "ey": 1850, "ly": 2025},
  {"key": "Puán-Argentina", "n": "Puán", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-38.3025, -62.98349], "ey": 1850, "ly": 2010},
  {"key": "Pica-Chile_2", "n": "Pica", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-20.49, -69.33], "ey": 590, "ly": 1825},
  {"key": "Cerro Chillin-Peru", "n": "Cerro Chillin", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.73723, -78.09914], "ey": 500, "ly": 1530},
  {"key": "Saisa-Peru", "n": "Saisa", "c": "Peru", "r": "per_ayacucho", "ll": [-14.94028, -74.41722], "ey": 1525, "ly": 2025, "al": ["cayza", "layza"]},
  {"key": "Nuestra Señora del Rosario de Caá Catí-Argentina", "n": "Nuestra Señora del Rosario de Caá Catí", "c": "Argentina", "r": "arg_corrientes", "ll": [-27.752, -57.62251], "ey": 1850, "ly": 2010},
  {"key": "Puntos 16 a-Colombia", "n": "Puntos 16 a", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.18175, -74.55938], "ey": 1000, "ly": 1500},
  {"key": "Villa Sarmiento-Argentina", "n": "Villa Sarmiento", "c": "Argentina", "r": "arg_cordoba", "ll": [-34.12283, -64.72519], "ey": 1850, "ly": 2022},
  {"key": "Fray Luis Beltrán (arg_mendoza)-Argentina", "n": "Fray Luis Beltrán", "c": "Argentina", "r": "arg_mendoza", "ll": [-33.0044, -68.64992], "ey": 1850, "ly": 2010},
  {"key": "Santa Ana de los Guácaras-Argentina", "n": "Santa Ana de los Guácaras", "c": "Argentina", "r": "arg_corrientes", "ll": [-27.45432, -58.68035], "ey": 1798, "ly": 2022},
  {"key": "Siswa-Peru", "n": "Siswa", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.95427, -76.03734], "ey": -1000, "ly": 1530},
  {"key": "El Chical-Ecuador", "n": "El Chical", "c": "Ecuador", "r": "ecu_carchi", "ll": [1.01152, -78.26861], "ey": 1850, "ly": 2025},
  {"key": "San Bartolome de Buena vista-Colombia", "n": "San Bartolome de Buena vista", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [6.635, -74.374], "ey": 1525, "ly": 1830},
  {"key": "Duna Grande-Peru", "n": "Duna Grande", "c": "Peru", "r": "inca_contisuyu", "ll": [-15.05314, -74.86202], "ey": 0, "ly": 1530},
  {"key": "Sabana de La Plata-Venezuela", "n": "Sabana de La Plata", "c": "Venezuela", "r": "ven_zulia", "ll": [10.32278, -71.28222], "ey": 1850, "ly": 2011},
  {"key": "Sapse-Bolivia", "n": "Sapse", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.724, -65.278], "ey": 1525, "ly": 1825, "al": ["sapci", "sapsi"]},
  {"key": "Sipisa-Chile", "n": "Sipisa", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.286, -69.475], "ey": 1525, "ly": 1825},
  {"key": "Paclín-Argentina", "n": "Paclín", "c": "Argentina", "r": "arg_catamarca", "ll": [-28.11032, -65.67432], "ey": 1850, "ly": 2022},
  {"key": "Paccha (per_piura)-Peru", "n": "Paccha", "c": "Peru", "r": "per_piura", "ll": [-5.0123, -80.2242], "ey": 1850, "ly": 2017},
  {"key": "Pobreza Baudo-Colombia", "n": "Pobreza Baudo", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [5.051, -77.044], "ey": 1525, "ly": 1830},
  {"key": "Chimpay-Argentina", "n": "Chimpay", "c": "Argentina", "r": "arg_rio_negro", "ll": [-39.16487, -66.14579], "ey": 1900, "ly": 2022},
  {"key": "Abdón Calderón (ecu_azuay)-Ecuador", "n": "Abdón Calderón", "c": "Ecuador", "r": "ecu_azuay", "ll": [-3.25889, -79.27108], "ey": 1850, "ly": 2025},
  {"key": "La Ramada-Peru", "n": "La Ramada", "c": "Peru", "r": "per_cajamarca", "ll": [-6.25333, -78.57556], "ey": 1850, "ly": 2025},
  {"key": "Santiago de Vado-Peru", "n": "Santiago de Vado", "c": "Peru", "r": "per_ayacucho", "ll": [-14.6045, -74.2732], "ey": 1525, "ly": 2017},
  {"key": "Pomán-Argentina", "n": "Pomán", "c": "Argentina", "r": "arg_catamarca", "ll": [-28.39673, -66.2185], "ey": 1850, "ly": 2022},
  {"key": "Pozo Hondo-Argentina", "n": "Pozo Hondo", "c": "Argentina", "r": "arg_santiago_del_estero", "ll": [-27.16718, -64.49087], "ey": 1850, "ly": 2022},
  {"key": "Coronel Juan Solá-Argentina", "n": "Coronel Juan Solá", "c": "Argentina", "r": "arg_salta", "ll": [-23.47051, -62.88788], "ey": 1850, "ly": 2010},
  {"key": "Chalgayaco-Colombia", "n": "Chalgayaco", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [1.896, -77.015], "ey": 1525, "ly": 1830},
  {"key": "Mopora-Colombia", "n": "Mopora", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.746, -73.97], "ey": 1525, "ly": 1830},
  {"key": "San Juan de Oro-Argentina", "n": "San Juan de Oro", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-22.216, -66.387], "ey": 1525, "ly": 1830},
  {"key": "El Retiro-Ecuador", "n": "El Retiro", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.37008, -79.9574], "ey": 1850, "ly": 2025},
  {"key": "Lomas Blancas-Chile", "n": "Lomas Blancas", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.89145, -72.77035], "ey": 1350, "ly": 1500},
  {"key": "Inambari-Peru_2", "n": "Inambari", "c": "Peru", "r": "vp_intendencia_puno", "ll": [-13.571, -70.133], "ey": 1525, "ly": 1825},
  {"key": "Chura-Ecuador", "n": "Chura", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.54316, -79.45972], "ey": 1850, "ly": 2025},
  {"key": "Altarani Llavinipunko-Peru", "n": "Altarani Llavinipunko", "c": "Peru", "r": "inca_collasuyu", "ll": [-16.17098, -69.54053], "ey": 1300, "ly": 1530},
  {"key": "San Simón-Ecuador", "n": "San Simón", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.63841, -78.92824], "ey": 1850, "ly": 2025},
  {"key": "Torre 301 Yacimiento-Colombia", "n": "Torre 301 Yacimiento", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.41, -75.58], "ey": 1215, "ly": 1500},
  {"key": "Chanabaya-Chile", "n": "Chanabaya", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-20.86, -70.152], "ey": 1525, "ly": 1825},
  {"key": "Abelardo Pardo Lezameta-Peru", "n": "Abelardo Pardo Lezameta", "c": "Peru", "r": "per_ancash", "ll": [-10.29917, -77.14639], "ey": 1525, "ly": 2025, "al": ["llaclla", "pacllon"]},
  {"key": "Sa-Sls-Colombia", "n": "Sa-Sls", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [7.19572, -72.64183], "ey": 500, "ly": 1500},
  {"key": "Sama Grande-Peru", "n": "Sama Grande", "c": "Peru", "r": "inca_collasuyu", "ll": [-17.79235, -70.48488], "ey": 1440, "ly": 1532},
  {"key": "Bachillero-Ecuador", "n": "Bachillero", "c": "Ecuador", "r": "ecu_manabi", "ll": [-0.75653, -80.1958], "ey": 1850, "ly": 2025},
  {"key": "Guantajaya-Chile", "n": "Guantajaya", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-20.215, -70.035], "ey": 1525, "ly": 1825},
  {"key": "Bss-Chile", "n": "Bss", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-53.1673, -68.70757], "ey": 0, "ly": 1500},
  {"key": "Campo Scodellaro-Argentina", "n": "Campo Scodellaro", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.65799, -64.00711], "ey": 80, "ly": 1500},
  {"key": "Las Piedras-Colombia", "n": "Las Piedras", "c": "Colombia", "r": "col_bolivar", "ll": [10.31377, -75.19576], "ey": 1850, "ly": 2018},
  {"key": "Arpichillo-Peru", "n": "Arpichillo", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.63155, -74.95861], "ey": 0, "ly": 1530},
  {"key": "Francisco Bolognesi (per_piura)-Peru", "n": "Francisco Bolognesi", "c": "Peru", "r": "per_piura", "ll": [-5.076, -79.7715], "ey": 1525, "ly": 2017},
  {"key": "Huasco Bajo-Chile", "n": "Huasco Bajo", "c": "Chile", "r": "chl_region_de_atacama", "ll": [-28.47538, -71.17631], "ey": 1525, "ly": 2017},
  {"key": "Puerto Rondón-Colombia", "n": "Puerto Rondón", "c": "Colombia", "r": "col_arauca", "ll": [6.28146, -71.10339], "ey": 1900, "ly": 2025},
  {"key": "Copequén-Chile", "n": "Copequén", "c": "Chile", "r": "chl_region_metropolitana_de_santiago", "ll": [-34.24608, -70.92233], "ey": 1525, "ly": 2017},
  {"key": "Pampa Soledad-Chile", "n": "Pampa Soledad", "c": "Chile", "r": "inca_collasuyu", "ll": [-21.38027, -69.45502], "ey": 1300, "ly": 1530},
  {"key": "Buenos Aires-Colombia_2", "n": "Buenos Aires", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [3.93013, -74.86916], "ey": 1000, "ly": 1500},
  {"key": "Chontaduro-Ecuador", "n": "Chontaduro", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.878, -79.41782], "ey": 1850, "ly": 2025},
  {"key": "La Capuera-Uruguay", "n": "La Capuera", "c": "Uruguay", "r": "ury_maldonado", "ll": [-34.86465, -55.08542], "ey": 1850, "ly": 2023},
  {"key": "Chiguirip-Peru", "n": "Chiguirip", "c": "Peru", "r": "per_cajamarca", "ll": [-6.42833, -78.72139], "ey": 1850, "ly": 2025},
  {"key": "Buenavista (col_norte_de_santander)-Colombia", "n": "Buenavista", "c": "Colombia", "r": "col_norte_de_santander", "ll": [8.18864, -73.34608], "ey": 1525, "ly": 2018},
  {"key": "Villa General Manuel Belgrano-Argentina", "n": "Villa General Manuel Belgrano", "c": "Argentina", "r": "arg_formosa", "ll": [-24.93853, -59.02642], "ey": 1920, "ly": 2010},
  {"key": "Villa Kilómetro 213-Argentina", "n": "Villa Kilómetro 213", "c": "Argentina", "r": "arg_formosa", "ll": [-26.18715, -59.36705], "ey": 1920, "ly": 2010},
  {"key": "Simón Bolívar (ecu_santa_elena)-Ecuador", "n": "Simón Bolívar", "c": "Ecuador", "r": "ecu_santa_elena", "ll": [-2.15413, -80.36274], "ey": 1850, "ly": 2025},
  {"key": "Gallipavo-Chile", "n": "Gallipavo", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-36.8281, -72.0982], "ey": 0, "ly": 1500},
  {"key": "Campo Elías (ven_trujillo)-Venezuela", "n": "Campo Elías", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.39167, -70.05722], "ey": 1850, "ly": 2025},
  {"key": "La Lagunita (ven_yaracuy)-Venezuela", "n": "La Lagunita", "c": "Venezuela", "r": "ven_yaracuy", "ll": [10.15594, -68.56435], "ey": 1625, "ly": 2011},
  {"key": "Loma de Arena-Colombia", "n": "Loma de Arena", "c": "Colombia", "r": "col_atlantico", "ll": [10.73414, -75.26417], "ey": 1850, "ly": 2018},
  {"key": "Mutiscua-Colombia", "n": "Mutiscua", "c": "Colombia", "r": "col_norte_de_santander", "ll": [7.30047, -72.74717], "ey": 1850, "ly": 2025},
  {"key": "Cavari-Bolivia", "n": "Cavari", "c": "Bolivia", "r": "bol_cochabamba", "ll": [-17.07912, -66.99162], "ey": 1525, "ly": 2024},
  {"key": "Zona A - Sinifaná - Yacimiento 18 - Cuevas de Santa Catalina-Colombia", "n": "Zona A - Sinifaná - Yacimiento 18 - Cuevas de Santa Catalina", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.96, -75.75], "ey": 1175, "ly": 1500},
  {"key": "Agua Santa-Venezuela", "n": "Agua Santa", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.51667, -70.66667], "ey": 1850, "ly": 2025},
  {"key": "Viviate-Peru", "n": "Viviate", "c": "Peru", "r": "per_piura", "ll": [-4.9204, -80.9192], "ey": 1850, "ly": 2017},
  {"key": "Tres Unidos-Peru", "n": "Tres Unidos", "c": "Peru", "r": "per_san_martin", "ll": [-6.80583, -76.23222], "ey": 1900, "ly": 2025},
  {"key": "Campos Elevados-Peru", "n": "Campos Elevados", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.48033, -78.36895], "ey": -3000, "ly": 1532},
  {"key": "Taganga-Colombia", "n": "Taganga", "c": "Colombia", "r": "col_magdalena", "ll": [11.26816, -74.1885], "ey": 1525, "ly": 2018},
  {"key": "Santa Cruz (per_loreto)-Peru", "n": "Santa Cruz", "c": "Peru", "r": "per_loreto", "ll": [-5.51333, -75.85889], "ey": 1900, "ly": 2025},
  {"key": "San Genaro Norte-Argentina", "n": "San Genaro Norte", "c": "Argentina", "r": "arg_santa_fe", "ll": [-32.3648, -61.33723], "ey": 1850, "ly": 2010},
  {"key": "Simbila-Peru", "n": "Simbila", "c": "Peru", "r": "per_piura", "ll": [-5.2444, -80.6497], "ey": 1850, "ly": 2017},
  {"key": "Jaiva-Peru", "n": "Jaiva", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.897, -77.37239], "ey": -2000, "ly": 1530},
  {"key": "Villa Pasco-Peru", "n": "Villa Pasco", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.77856, -76.25451], "ey": 0, "ly": 1532},
  {"key": "Los Antiguos-Argentina", "n": "Los Antiguos", "c": "Argentina", "r": "arg_santa_cruz", "ll": [-46.54957, -71.62512], "ey": 1900, "ly": 2022},
  {"key": "Ayallaqta-Peru", "n": "Ayallaqta", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.09031, -71.51206], "ey": 1000, "ly": 1530},
  {"key": "Marta-Colombia", "n": "Marta", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [9.48339, -75.59988], "ey": -501, "ly": 793},
  {"key": "Quilanga-Ecuador", "n": "Quilanga", "c": "Ecuador", "r": "ecu_loja", "ll": [-4.35293, -79.38157], "ey": 1850, "ly": 2025},
  {"key": "Gobernador Martínez-Argentina", "n": "Gobernador Martínez", "c": "Argentina", "r": "arg_corrientes", "ll": [-28.91231, -58.93607], "ey": 1850, "ly": 2022},
  {"key": "Chairama-Colombia", "n": "Chairama", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [11.3, -74.06], "ey": 900, "ly": 1500},
  {"key": "Catavi-Bolivia", "n": "Catavi", "c": "Bolivia", "r": "bol_potosi", "ll": [-18.41507, -66.56544], "ey": 1850, "ly": 2024}
]

def sparql_batch(batch):
  values = " ".join([f'("{it["key"]}" "Point({it["ll"][1]} {it["ll"][0]})"^^geo:wktLiteral)' for it in batch])
  q = f"""
  SELECT ?key ?place ?placeLabel ?inception ?eswiki ?enwiki WHERE {{
    VALUES (?key ?center) {{ {values} }}
    SERVICE wikibase:around {{
      ?place wdt:P625 ?loc .
      bd:serviceParam wikibase:center ?center .
      bd:serviceParam wikibase:radius "12" .
    }}
    OPTIONAL {{ ?place wdt:P571 ?inception . }}
    OPTIONAL {{ ?eswiki schema:about ?place ; schema:isPartOf <https://es.wikipedia.org/> . }}
    OPTIONAL {{ ?enwiki schema:about ?place ; schema:isPartOf <https://en.wikipedia.org/> . }}
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . }}
  }}
  """
  data = urllib.parse.urlencode({"query": q, "format": "json"}).encode("utf-8")
  req = urllib.request.Request("https://query.wikidata.org/sparql", data=data, headers={"User-Agent": "ViscountResearch/1.0 (https://confoederatio.org)"})
  with urllib.request.urlopen(req, timeout=45) as r:
    return json.loads(r.read().decode("utf-8"))

out = {}
for i in range(0, len(items), 15):
  batch = items[i:i+15]
  res = sparql_batch(batch)
  for b in res["results"]["bindings"]:
    k = b["key"]["value"]
    out.setdefault(k, []).append({
      "label": b.get("placeLabel", {}).get("value"),
      "inception": b.get("inception", {}).get("value"),
      "eswiki": b.get("eswiki", {}).get("value"),
      "enwiki": b.get("enwiki", {}).get("value"),
    })
  time.sleep(1.0)

with open("tests/wd_results.json", "w", encoding="utf-8") as f:
  json.dump(out, f, ensure_ascii=False, indent=2)
print("Matched keys:", len(out))
