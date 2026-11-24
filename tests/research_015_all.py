import json
import math
import os
import re
import time
import urllib.parse
import urllib.request

INPUT = [
  {"key": "Luya Viejo-Peru", "n": "Luya Viejo", "c": "Peru", "r": "per_amazonas", "ll": [-6.1275, -78.085], "ey": 1525, "ly": 2025, "al": ["luya", "Luya"]},
  {"key": "Huaquirca-Peru", "n": "Huaquirca", "c": "Peru", "r": "per_apurimac", "ll": [-14.33944, -72.895], "ey": 1525, "ly": 2025},
  {"key": "San Isidro de Quiucmal-Peru", "n": "San Isidro de Quiucmal", "c": "Peru", "r": "per_amazonas", "ll": [-6.0858, -78.178], "ey": 1525, "ly": 2017, "al": ["jacapatos", "Jacapatos"]},
  {"key": "Gullancay-Ecuador", "n": "Gullancay", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.746, -78.918], "ey": 1525, "ly": 1830},
  {"key": "San Francisco Del Vergel-Ecuador", "n": "San Francisco Del Vergel", "c": "Ecuador", "r": "ecu_zamora_chinchipe", "ll": [-4.67794, -79.04476], "ey": 1525, "ly": 2025, "al": ["vergel", "vegel", "Vergel"]},
  {"key": "Chisquilla-Peru", "n": "Chisquilla", "c": "Peru", "r": "per_amazonas", "ll": [-5.8975, -77.78611], "ey": 1525, "ly": 2025},
  {"key": "Umachiri-Peru", "n": "Umachiri", "c": "Peru", "r": "per_puno", "ll": [-14.85389, -70.75389], "ey": 1525, "ly": 2025, "al": ["umachari", "Umachari"]},
  {"key": "El Ángel-Ecuador", "n": "El Ángel", "c": "Ecuador", "r": "ecu_carchi", "ll": [0.65299, -77.99179], "ey": 1850, "ly": 2025},
  {"key": "Sisicaya-Peru", "n": "Sisicaya", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.027, -76.631], "ey": 1525, "ly": 1825},
  {"key": "Gamarra-Peru", "n": "Gamarra", "c": "Peru", "r": "per_apurimac", "ll": [-13.87167, -72.50833], "ey": 1525, "ly": 2025, "al": ["palpacachi", "palpacchi", "Palpacachi"]},
  {"key": "Los Huacos-Peru", "n": "Los Huacos", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.09802, -77.61796], "ey": -2000, "ly": 1530},
  {"key": "El Bajo-Venezuela", "n": "El Bajo", "c": "Venezuela", "r": "ven_zulia", "ll": [10.52569, -71.63048], "ey": 1850, "ly": 2025},
  {"key": "Quinjalca-Peru", "n": "Quinjalca", "c": "Peru", "r": "per_amazonas", "ll": [-6.09139, -77.67861], "ey": 1525, "ly": 2025},
  {"key": "Cochabamba (per_ancash_2)-Peru", "n": "Cochabamba", "c": "Peru", "r": "per_ancash", "ll": [-9.495, -77.85944], "ey": 1525, "ly": 2025},
  {"key": "Lamud-Peru", "n": "Lamud", "c": "Peru", "r": "per_amazonas", "ll": [-6.13917, -77.95222], "ey": 1525, "ly": 2025, "al": ["lámud", "lamut", "Lámud"]},
  {"key": "Siccican-Peru", "n": "Siccican", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-9.308, -77.159], "ey": 1525, "ly": 1825},
  {"key": "Quilla-Peru", "n": "Quilla", "c": "Peru", "r": "per_ayacucho", "ll": [-13.6952, -74.0583], "ey": 1525, "ly": 2017},
  {"key": "Totora (vp_intendencia_cusco)-Peru", "n": "Totora", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-14.38, -71.583], "ey": 1525, "ly": 1825},
  {"key": "Archidona (ecu_napo)-Ecuador", "n": "Archidona", "c": "Ecuador", "r": "ecu_napo", "ll": [-0.91271, -77.80832], "ey": 1560, "ly": 2022, "al": ["ciudad de archidona", "la maravilla", "santa elena"]},
  {"key": "Capillucas-Peru", "n": "Capillucas", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.708, -75.97], "ey": 1525, "ly": 1825},
  {"key": "Quinocay-Peru", "n": "Quinocay", "c": "Peru", "r": "per_lima", "ll": [-12.36222, -76.22639], "ey": 1525, "ly": 2025, "al": ["quincocay", "Quincocay"]},
  {"key": "Inguap-Colombia", "n": "Inguap", "c": "Colombia", "r": "inca_chinchaysuyu", "ll": [1.7, -78.76], "ey": -794, "ly": 1532, "al": ["buchel", "el balsal", "inguapí"]},
  {"key": "Chachas-Peru", "n": "Chachas", "c": "Peru", "r": "per_arequipa", "ll": [-15.50139, -72.27056], "ey": 1525, "ly": 2025},
  {"key": "Novirao-Colombia", "n": "Novirao", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.544, -76.53], "ey": 1525, "ly": 1830},
  {"key": "Abra Cerro Salinas-Peru", "n": "Abra Cerro Salinas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.5049, -79.78804], "ey": -2000, "ly": 1532},
  {"key": "Cubijíes-Ecuador", "n": "Cubijíes", "c": "Ecuador", "r": "ecu_chimborazo", "ll": [-1.65713, -78.60213], "ey": 1525, "ly": 2025},
  {"key": "Pepa de Huso-Ecuador", "n": "Pepa de Huso", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-1.03, -80.34], "ey": -870, "ly": -170},
  {"key": "Huacllan-Peru", "n": "Huacllan", "c": "Peru", "r": "per_ancash", "ll": [-9.79806, -77.67528], "ey": 1525, "ly": 2025, "al": ["huacllán", "Huacllán"]},
  {"key": "Don Ariel-Argentina", "n": "Don Ariel", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-51.91456, -69.74166], "ey": -5900, "ly": -77, "al": ["el volcan", "El Volcan"]},
  {"key": "Ventarron-Peru_2", "n": "Ventarron", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.81199, -79.75419], "ey": -2000, "ly": 1530},
  {"key": "Wamanmarka-Peru", "n": "Wamanmarka", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.40324, -72.07734], "ey": -1000, "ly": 1530},
  {"key": "Turpo-Peru", "n": "Turpo", "c": "Peru", "r": "per_apurimac", "ll": [-13.78556, -73.47417], "ey": 1525, "ly": 2025},
  {"key": "Parcco-Peru", "n": "Parcco", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.999, -71.888], "ey": 1525, "ly": 1825},
  {"key": "Cancha Cancha-Peru", "n": "Cancha Cancha", "c": "Peru", "r": "per_ayacucho", "ll": [-13.6061, -74.313], "ey": 1525, "ly": 2017},
  {"key": "Huayllati-Peru", "n": "Huayllati", "c": "Peru", "r": "per_apurimac", "ll": [-13.92806, -72.48444], "ey": 1525, "ly": 2025},
  {"key": "Cupisnique-Peru", "n": "Cupisnique", "c": "Peru", "r": "per_cajamarca", "ll": [-7.34889, -79.02972], "ey": 1525, "ly": 2025, "al": ["trinidad", "trinidad de chetu", "Trinidad"]},
  {"key": "San Francisco-Peru_2", "n": "San Francisco", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-8.1, -77.936], "ey": 1525, "ly": 1825},
  {"key": "San Salvador de Quije-Peru", "n": "San Salvador de Quije", "c": "Peru", "r": "per_ayacucho", "ll": [-13.96833, -73.73472], "ey": 1525, "ly": 2025},
  {"key": "Cojitambo-Ecuador", "n": "Cojitambo", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.75609, -78.88715], "ey": 1525, "ly": 2025},
  {"key": "El Paují-Venezuela", "n": "El Paují", "c": "Venezuela", "r": "ven_falcon", "ll": [10.81833, -69.61556], "ey": 1850, "ly": 2025},
  {"key": "Succha-Peru", "n": "Succha", "c": "Peru", "r": "per_ancash", "ll": [-9.82306, -77.64972], "ey": 1525, "ly": 2025},
  {"key": "Guachipay-Colombia", "n": "Guachipay", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.269, -74.566], "ey": 1525, "ly": 1830},
  {"key": "San Sebastian Yumbo-Colombia", "n": "San Sebastian Yumbo", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [3.582, -76.493], "ey": 1525, "ly": 1830},
  {"key": "Aguaclara (col_valle_del_cauca)-Colombia", "n": "Aguaclara", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.67305, -76.94814], "ey": 1850, "ly": 2018},
  {"key": "Dureno-Ecuador", "n": "Dureno", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [0.05102, -76.6765], "ey": 1920, "ly": 2025},
  {"key": "Jadán-Ecuador", "n": "Jadán", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.89679, -78.85279], "ey": 1525, "ly": 2025},
  {"key": "Calicampo-Peru", "n": "Calicampo", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.90654, -77.48993], "ey": -3000, "ly": 1530},
  {"key": "Molleturo-Ecuador", "n": "Molleturo", "c": "Ecuador", "r": "ecu_azuay", "ll": [-2.71034, -79.35431], "ey": 1525, "ly": 2025},
  {"key": "San Pedro-Colombia_2", "n": "San Pedro", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [8.764, -73.798], "ey": 1525, "ly": 1830},
  {"key": "Caja-Peru", "n": "Caja", "c": "Peru", "r": "per_huancavelica", "ll": [-12.91722, -74.46583], "ey": 1525, "ly": 2025},
  {"key": "Coya-Peru", "n": "Coya", "c": "Peru", "r": "per_cusco", "ll": [-13.38639, -71.89833], "ey": 1525, "ly": 2025},
  {"key": "José Gregorio Hernández-Venezuela", "n": "José Gregorio Hernández", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.36012, -70.69755], "ey": 1850, "ly": 2025},
  {"key": "Huampara-Peru", "n": "Huampara", "c": "Peru", "r": "per_lima", "ll": [-12.36028, -76.16722], "ey": 1525, "ly": 2025},
  {"key": "San Nicolás (col_antioquia_2)-Colombia", "n": "San Nicolás", "c": "Colombia", "r": "col_antioquia", "ll": [6.47812, -75.8211], "ey": 1525, "ly": 2018},
  {"key": "Chiuchin-Peru", "n": "Chiuchin", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.927, -76.78], "ey": 1525, "ly": 1825},
  {"key": "San Teodoro Collac-Peru", "n": "San Teodoro Collac", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-11.176, -75.359], "ey": 1525, "ly": 1825},
  {"key": "Huacar-Peru_2", "n": "Huacar", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.967, -76.948], "ey": 1525, "ly": 1825},
  {"key": "Cascabamba-Peru", "n": "Cascabamba", "c": "Peru", "r": "per_apurimac", "ll": [-13.6984, -73.5871], "ey": 1525, "ly": 2017},
  {"key": "Cambio Puente-Peru", "n": "Cambio Puente", "c": "Peru", "r": "per_la_libertad", "ll": [-8.998, -78.5558], "ey": 1850, "ly": 2017},
  {"key": "Moruy-Venezuela", "n": "Moruy", "c": "Venezuela", "r": "ven_falcon", "ll": [11.82667, -69.98333], "ey": 1538, "ly": 2025},
  {"key": "San Antonio de Padua de la Sal-Colombia", "n": "San Antonio de Padua de la Sal", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.636, -75.964], "ey": 1538, "ly": 1830},
  {"key": "Muzga-Peru", "n": "Muzga", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.995, -76.977], "ey": 1525, "ly": 1825},
  {"key": "El Cerrito-Colombia_2", "n": "El Cerrito", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [10.829, -74.763], "ey": 1601, "ly": 1744},
  {"key": "San Pedro de Cusi-Peru", "n": "San Pedro de Cusi", "c": "Peru", "r": "per_lima", "ll": [-12.5633, -75.9075], "ey": 1525, "ly": 2017},
  {"key": "Caramarca-Peru", "n": "Caramarca", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-7.78, -78.024], "ey": 1542, "ly": 1825},
  {"key": "Gapal-Ecuador", "n": "Gapal", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.916, -78.99], "ey": 1525, "ly": 1830},
  {"key": "Castillo Jesus Maria-Peru", "n": "Castillo Jesus Maria", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.03198, -78.83355], "ey": -1000, "ly": 1530},
  {"key": "Puente Durand-Peru", "n": "Puente Durand", "c": "Peru", "r": "per_huanuco", "ll": [-9.5573, -76.0169], "ey": -2000, "ly": 2017},
  {"key": "Ichuña-Peru", "n": "Ichuña", "c": "Peru", "r": "per_moquegua", "ll": [-16.14056, -70.53556], "ey": 1525, "ly": 2025},
  {"key": "La Punta-Colombia", "n": "La Punta", "c": "Colombia", "r": "col_cundinamarca", "ll": [4.79587, -74.20759], "ey": 1850, "ly": 2018},
  {"key": "Chiguaza-Ecuador", "n": "Chiguaza", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-2.04416, -77.98309], "ey": 1920, "ly": 2025},
  {"key": "Uningambal-Peru", "n": "Uningambal", "c": "Peru", "r": "per_la_libertad", "ll": [-8.262, -78.3861], "ey": 1525, "ly": 2017},
  {"key": "Buena Esperanza de Rere-Chile", "n": "Buena Esperanza de Rere", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-37.132, -72.727], "ey": 1721, "ly": 1830},
  {"key": "Saywa - Yaccacheta-Peru", "n": "Saywa - Yaccacheta", "c": "Peru", "r": "inca_antisuyu", "ll": [-13.5939, -71.56647], "ey": 500, "ly": 1530},
  {"key": "Guacamayal-Colombia", "n": "Guacamayal", "c": "Colombia", "r": "col_magdalena", "ll": [10.75069, -74.15877], "ey": 1850, "ly": 2018},
  {"key": "Lucuchanga-Peru", "n": "Lucuchanga", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.751, -72.971], "ey": 1525, "ly": 1825},
  {"key": "Timar-Chile", "n": "Timar", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-18.75, -69.691], "ey": 1525, "ly": 1825},
  {"key": "El Carmelo-Colombia", "n": "El Carmelo", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.40261, -76.41644], "ey": 1850, "ly": 2018},
  {"key": "Santa Isabel de Caype-Peru", "n": "Santa Isabel de Caype", "c": "Peru", "r": "per_apurimac", "ll": [-13.7971, -72.8324], "ey": 1525, "ly": 2017},
  {"key": "Ayalan-Ecuador", "n": "Ayalan", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-2.58359, -80.26596], "ey": -2191, "ly": 76},
  {"key": "Challacota-Bolivia", "n": "Challacota", "c": "Bolivia", "r": "bol_oruro", "ll": [-19.25498, -67.75961], "ey": 1525, "ly": 2024},
  {"key": "Circa-Peru", "n": "Circa", "c": "Peru", "r": "per_apurimac", "ll": [-13.87833, -72.87583], "ey": 1525, "ly": 2025},
  {"key": "Coper-Colombia", "n": "Coper", "c": "Colombia", "r": "col_cundinamarca", "ll": [5.47507, -74.04564], "ey": 1525, "ly": 2025},
  {"key": "El Eno-Ecuador", "n": "El Eno", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [-0.06753, -76.87857], "ey": 1920, "ly": 2025},
  {"key": "San Cristóbal (ecu_canar)-Ecuador", "n": "San Cristóbal", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.83804, -78.84887], "ey": 1525, "ly": 2025},
  {"key": "Morro-Ecuador", "n": "Morro", "c": "Ecuador", "r": "ecu_guayas", "ll": [-2.56136, -80.30825], "ey": 1525, "ly": 2025},
  {"key": "Tuama-Argentina", "n": "Tuama", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.005, -64.107], "ey": 1536, "ly": 1830},
  {"key": "Millo-Peru", "n": "Millo", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.43601, -71.88495], "ey": -1000, "ly": 1530},
  {"key": "Mutca-Peru", "n": "Mutca", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-14.216, -73.308], "ey": 1525, "ly": 1825},
  {"key": "Nanchoc-Peru", "n": "Nanchoc", "c": "Peru", "r": "per_lambayeque", "ll": [-6.95944, -79.2425], "ey": 1525, "ly": 2025}
]

# 1. Check local archaeological site files for the arch/early entries
def haversine(lat1, lon1, lat2, lon2):
  R = 6371.0
  dlat = math.radians(lat2 - lat1)
  dlon = math.radians(lon2 - lon1)
  a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
  return 2 * R * math.asin(math.sqrt(a))

arch_targets = [x for x in INPUT if x["ey"] < 1000]
raw_dir = "histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/0.raw_sites"
arch_hits = {x["key"]: [] for x in arch_targets}

for fname in os.listdir(raw_dir):
  fpath = os.path.join(raw_dir, fname)
  if fname.endswith(".json") and os.path.getsize(fpath) < 40_000_000:
    try:
      with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
      items = data if isinstance(data, list) else data.get("features", data.get("sites", data.get("data", [])))
      if not isinstance(items, list):
        continue
      for it in items:
        if not isinstance(it, dict):
          continue
        lat = it.get("lat") or it.get("latitude") or it.get("y")
        lng = it.get("lng") or it.get("lon") or it.get("longitude") or it.get("x")
        if lat is None and "geometry" in it and isinstance(it["geometry"], dict):
          coords = it["geometry"].get("coordinates")
          if isinstance(coords, list) and len(coords) >= 2:
            lng, lat = coords[0], coords[1]
        if lat is None or lng is None:
          continue
        try:
          lat, lng = float(lat), float(lng)
        except:
          continue
        for t in arch_targets:
          d = haversine(t["ll"][0], t["ll"][1], lat, lng)
          if d <= 5.0:
            props = it.get("properties", it)
            snippet = {k: v for k, v in props.items() if k in ("name", "nombre", "site", "sitio", "NOMBRE", "Nombre", "culture", "cultura", "period", "periodo", "date", "age", "c14", "bp", "cal_bc_ad", "TIPO", "tipo", "categoria", "cr_bp") and v}
            if not snippet:
              snippet = {k: str(v)[:80] for k, v in list(props.items())[:6]}
            arch_hits[t["key"]].append((round(d, 2), fname, snippet))
    except Exception as e:
      pass

with open("tests/chunk015_arch_hits.txt", "w", encoding="utf-8") as f:
  for k, hits in arch_hits.items():
    f.write(f"=== {k} ===\n")
    for d, fn, sn in sorted(hits, key=lambda x: x[0])[:12]:
      f.write(f"  [{d} km | {fn}] {sn}\n")

print("Arch hits saved.")
