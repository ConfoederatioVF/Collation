import json, pathlib, urllib.request, urllib.parse, time, math

INPUT = [
  {"key": "Amoca-Peru", "n": "Amoca", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-14.234, -73.061], "ey": 1525, "ly": 1825, "p": 6285},
  {"key": "Navan-Peru", "n": "Navan", "c": "Peru", "r": "per_lima", "ll": [-10.83778, -77.01444], "ey": 1525, "ly": 2025, "p": 6284, "al": ["naban", "naván", "Naban"]},
  {"key": "Boyaca Giralda Y2 T-Colombia", "n": "Boyaca Giralda Y2 T", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.10341, -74.58431], "ey": 792, "ly": 1500, "p": 6284, "al": ["aq pc", "inyc", "inyd"]},
  {"key": "Calcauso-Peru", "n": "Calcauso", "c": "Peru", "r": "per_apurimac", "ll": [-14.4517, -72.9128], "ey": 1525, "ly": 2017, "p": 6281, "al": ["calcauzo", "caleauzo", "Calcauzo"]},
  {"key": "Porococha-Peru", "n": "Porococha", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.572, -76.175], "ey": 1525, "ly": 1825, "p": 6281},
  {"key": "Chichopen-Peru", "n": "Chichopen", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-6.448, -79.178], "ey": 1525, "ly": 1830, "p": 6278, "al": ["checopon", "chinchopon", "Checopon"]},
  {"key": "Noasi-Argentina", "n": "Noasi", "c": "Argentina", "r": "crp_corregimiento_cuyo", "ll": [-32.313, -66.592], "ey": 1536, "ly": 1830, "p": 6278, "al": ["corral de gamas", "los corrales", "manantial de las gamas"]},
  {"key": "Guambia-Colombia", "n": "Guambia", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.624, -76.291], "ey": 1525, "ly": 1830, "p": 6277},
  {"key": "Tulumayo-Peru", "n": "Tulumayo", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.18369, -75.97946], "ey": -3000, "ly": 1530, "p": 6277},
  {"key": "Esteros-Ecuador", "n": "Esteros", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-0.57, -80.39], "ey": -804, "ly": 480, "p": 6276, "al": ["tarqui site", "Tarqui Site"]},
  {"key": "Lasco-Argentina", "n": "Lasco", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.515, -63.027], "ey": 1536, "ly": 1830, "p": 6271},
  {"key": "El Cañoncillo-Peru", "n": "El Cañoncillo", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.38494, -79.43502], "ey": -1000, "ly": 1530, "p": 6271, "al": ["cerro el molino de chocofan", "guereque norte", "huaca bolsa del diablo"]},
  {"key": "El Esfuerzo-Ecuador", "n": "El Esfuerzo", "c": "Ecuador", "r": "ecu_santo_domingo_de_los_tsachilas", "ll": [-0.44387, -79.19274], "ey": 1850, "ly": 2025, "p": 6270},
  {"key": "San Francisco Yaquiva-Colombia", "n": "San Francisco Yaquiva", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [2.566, -76.05], "ey": 1525, "ly": 1830, "p": 6270},
  {"key": "Concepcion Rio Cuarto-Argentina", "n": "Concepcion Rio Cuarto", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-33.124, -64.348], "ey": 1731, "ly": 1830, "p": 6270, "ex": [{"date": "1895.1.1", "name": "Río Cuarto"}]},
  {"key": "Bolognes-Peru", "n": "Bolognes", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-3.60828, -76.42395], "ey": -2000, "ly": 1530, "p": 6269},
  {"key": "Guañape-Peru", "n": "Guañape", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-8.44, -78.923], "ey": 1525, "ly": 1762, "p": 6265},
  {"key": "Arrayan-Peru", "n": "Arrayan", "c": "Peru", "r": "per_amazonas", "ll": [-5.5969, -78.4416], "ey": 1525, "ly": 2017, "p": 6260, "al": ["la peca", "peco", "La Peca"]},
  {"key": "Lagarto-Ecuador", "n": "Lagarto", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [1.00354, -79.20444], "ey": 1850, "ly": 2025, "p": 6255},
  {"key": "Guatases-Ecuador", "n": "Guatases", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.91, -78.774], "ey": 1525, "ly": 1830, "p": 6252},
  {"key": "Pilpichaca-Peru", "n": "Pilpichaca", "c": "Peru", "r": "per_huancavelica", "ll": [-13.33028, -74.97722], "ey": 1525, "ly": 2025, "p": 6246},
  {"key": "Mira-Ecuador_2", "n": "Mira", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [0.55, -78.042], "ey": 1525, "ly": 1830, "p": 6245, "al": ["miraflores", "Miraflores"]},
  {"key": "Puntales-Ecuador", "n": "Puntales", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [0.502, -77.905], "ey": 1525, "ly": 1830, "p": 6243, "al": ["puntal", "puntas", "Puntal"]},
  {"key": "Santiago de Callapa-Bolivia", "n": "Santiago de Callapa", "c": "Bolivia", "r": "bol_la_paz", "ll": [-17.47881, -68.35533], "ey": 1525, "ly": 2024, "p": 6241, "al": ["callapa", "Callapa"]},
  {"key": "Chaucayan-Peru", "n": "Chaucayan", "c": "Peru", "r": "per_ancash", "ll": [-10.1857, -77.5552], "ey": 1525, "ly": 2017, "p": 6240},
  {"key": "Queros-Peru", "n": "Queros", "c": "Peru", "r": "per_la_libertad", "ll": [-8.0246, -77.5342], "ey": 1525, "ly": 2017, "p": 6239},
  {"key": "Llanca-Peru", "n": "Llanca", "c": "Peru", "r": "vp_intendencia_arequipa", "ll": [-15.562, -72.047], "ey": 1525, "ly": 1825, "p": 6238},
  {"key": "Llauta-Peru", "n": "Llauta", "c": "Peru", "r": "per_ayacucho", "ll": [-14.24361, -74.92028], "ey": 1525, "ly": 2025, "p": 6234},
  {"key": "Riochico-Colombia", "n": "Riochico", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [6.51, -75.537], "ey": 1525, "ly": 1830, "p": 6234},
  {"key": "La Morita-Venezuela", "n": "La Morita", "c": "Venezuela", "r": "ven_yaracuy", "ll": [10.29241, -68.74363], "ey": 1850, "ly": 2011, "p": 6233},
  {"key": "Yantac-Peru", "n": "Yantac", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.344, -76.406], "ey": 1525, "ly": 1825, "p": 6232, "al": ["yanta", "Yanta"]},
  {"key": "Otas-Colombia", "n": "Otas", "c": "Colombia", "r": "col_huila", "ll": [2.60452, -75.33633], "ey": 1525, "ly": 2018, "p": 6230},
  {"key": "Vuelta Carmen-Colombia", "n": "Vuelta Carmen", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.61208, -78.67483], "ey": 1000, "ly": 1500, "p": 6230, "al": ["dos quebradas", "Dos Quebradas"]},
  {"key": "Huayllaripa-Peru", "n": "Huayllaripa", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-14.315, -73.321], "ey": 1525, "ly": 1825, "p": 6229, "al": ["huaillaripa", "Huaillaripa"]},
  {"key": "Ingeniero Luis A. Huergo-Argentina", "n": "Ingeniero Luis A. Huergo", "c": "Argentina", "r": "arg_rio_negro", "ll": [-39.07118, -67.23289], "ey": 1920, "ly": 2010, "p": 6227},
  {"key": "Huenchullami-Chile", "n": "Huenchullami", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-35.129, -72.189], "ey": 1525, "ly": 1830, "p": 6227, "al": ["puenchullami", "Puenchullami"]},
  {"key": "San Juan (ecu_azuay)-Ecuador", "n": "San Juan", "c": "Ecuador", "r": "ecu_azuay", "ll": [-2.96107, -78.82797], "ey": 1850, "ly": 2025, "p": 6226},
  {"key": "Valle De La Virgen-Ecuador", "n": "Valle De La Virgen", "c": "Ecuador", "r": "ecu_guayas", "ll": [-1.72262, -80.20101], "ey": 1850, "ly": 2025, "p": 6222},
  {"key": "Humocaro Bajo-Venezuela", "n": "Humocaro Bajo", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.68, -69.96722], "ey": 1538, "ly": 2025, "p": 6214, "al": ["rosario humocaro bajo", "humucaro bajo", "Rosario Humocaro bajo"]},
  {"key": "Gambote-Colombia", "n": "Gambote", "c": "Colombia", "r": "col_bolivar", "ll": [10.16297, -75.29914], "ey": 1525, "ly": 2018, "p": 6212, "al": ["paso de gambote", "Paso de Gambote"]},
  {"key": "Caujul-Peru", "n": "Caujul", "c": "Peru", "r": "per_lima", "ll": [-10.80583, -76.97917], "ey": 1525, "ly": 2025, "p": 6212, "al": ["caujal", "Caujal"]},
  {"key": "Rincón Hondo-Venezuela", "n": "Rincón Hondo", "c": "Venezuela", "r": "ven_apure", "ll": [7.41111, -69.08222], "ey": 1850, "ly": 2025, "p": 6209},
  {"key": "Bulo Bulo-Bolivia", "n": "Bulo Bulo", "c": "Bolivia", "r": "bol_cochabamba", "ll": [-17.25502, -64.36049], "ey": 1850, "ly": 2024, "p": 6202},
  {"key": "Alonso de Ojeda-Venezuela", "n": "Alonso de Ojeda", "c": "Venezuela", "r": "ven_zulia", "ll": [10.2, -71.30833], "ey": 1850, "ly": 2025, "p": 6199},
  {"key": "Sacsaquero-Peru", "n": "Sacsaquero", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.499, -75.235], "ey": 1525, "ly": 1825, "p": 6199},
  {"key": "Camarones-Colombia", "n": "Camarones", "c": "Colombia", "r": "col_la_guajira", "ll": [11.42388, -73.0633], "ey": 1525, "ly": 2018, "p": 6198},
  {"key": "Pampagrande-Peru_2", "n": "Pampagrande", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.76196, -79.48425], "ey": 1438, "ly": 1530, "p": 6195, "al": ["campo boris", "desaguadero", "Campo Boris"]},
  {"key": "Paguey-Colombia", "n": "Paguey", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [4.361, -74.535], "ey": 1525, "ly": 1830, "p": 6193, "al": ["limones", "Limones"]},
  {"key": "Yanamarca-Peru_2", "n": "Yanamarca", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.33686, -75.70126], "ey": 0, "ly": 1530, "p": 6191, "al": ["huancucro", "Huancucro"]},
  {"key": "San Andrés (col_cauca)-Colombia", "n": "San Andrés", "c": "Colombia", "r": "col_cauca", "ll": [2.58277, -76.04635], "ey": 1525, "ly": 2018, "p": 6187, "al": ["san andres pisimbala", "San Andres Pisimbala"]},
  {"key": "Limari-Chile", "n": "Limari", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-30.656, -71.481], "ey": 1585, "ly": 1830, "p": 6187},
  {"key": "Tambillo (ecu_esmeraldas)-Ecuador", "n": "Tambillo", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [1.19707, -78.88091], "ey": 1525, "ly": 2025, "p": 6186},
  {"key": "Villa de María-Argentina", "n": "Villa de María", "c": "Argentina", "r": "arg_cordoba", "ll": [-29.90649, -63.72261], "ey": 1786, "ly": 2022, "p": 6184, "al": ["villa de maria", "rosario rio seco", "Rosario Rio Seco"]},
  {"key": "SUA II - Cortes I-Colombia", "n": "SUA II - Cortes I", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.21671, -74.79737], "ey": 1000, "ly": 1500, "p": 6181, "al": ["finca el manso", "hacienda santa marta", "sa-abn"]},
  {"key": "Cotabambas-Peru", "n": "Cotabambas", "c": "Peru", "r": "per_apurimac", "ll": [-13.74556, -72.355], "ey": 1573, "ly": 2025, "p": 6180},
  {"key": "San Pedro de Atacama (chl_region_de_antofagasta)-Chile", "n": "San Pedro de Atacama", "c": "Chile", "r": "chl_region_de_antofagasta", "ll": [-22.90409, -68.19653], "ey": -800, "ly": 2017, "p": 6180, "al": ["ayllu condeduque", "cmn_registro_arqueológico_acreditado", "casa parroquial"]},
  {"key": "Zenúfana-Colombia", "n": "Zenúfana", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [7.624, -74.805], "ey": 200, "ly": 1500, "p": 6180, "al": ["nechí", "Nechí"]},
  {"key": "Concepcion Cayambe-Ecuador", "n": "Concepcion Cayambe", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [0.039, -78.145], "ey": 1525, "ly": 1830, "p": 6179, "ex": [{"date": "1962.1.1", "name": "Cayambe"}]},
  {"key": "Turco-Bolivia", "n": "Turco", "c": "Bolivia", "r": "bol_oruro", "ll": [-18.18216, -68.19211], "ey": 1525, "ly": 2026, "p": 6178},
  {"key": "Wheelwright-Argentina", "n": "Wheelwright", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.79228, -61.21075], "ey": 1850, "ly": 2022, "p": 6178},
  {"key": "Cerro Verde-Peru", "n": "Cerro Verde", "c": "Peru", "r": "per_arequipa", "ll": [-16.4515, -71.6137], "ey": 1850, "ly": 2017, "p": 6176, "al": ["congata", "Congata"]},
  {"key": "Roca-Peru", "n": "Roca", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.238, -77.211], "ey": 1525, "ly": 1825, "p": 6176},
  {"key": "El Palqui-Chile", "n": "El Palqui", "c": "Chile", "r": "chl_region_de_coquimbo", "ll": [-30.77541, -70.94283], "ey": 1850, "ly": 2017, "p": 6175},
  {"key": "Gualea-Ecuador", "n": "Gualea", "c": "Ecuador", "r": "ecu_pichincha", "ll": [0.1297, -78.74188], "ey": 1525, "ly": 2025, "p": 6172, "al": ["galea", "gualca", "guali"]},
  {"key": "Belmira-Colombia", "n": "Belmira", "c": "Colombia", "r": "col_antioquia", "ll": [6.60632, -75.66778], "ey": 1525, "ly": 2025, "p": 6171, "al": ["pecatacas", "petacas", "Pecatacas"]},
  {"key": "San José De Chamanga-Ecuador", "n": "San José De Chamanga", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.34477, -79.87494], "ey": 1850, "ly": 2025, "p": 6169},
  {"key": "Sincerín-Colombia", "n": "Sincerín", "c": "Colombia", "r": "col_bolivar", "ll": [10.14379, -75.2756], "ey": 1525, "ly": 2018, "p": 6166, "al": ["sincerin", "Sincerin"]},
  {"key": "Carangas-Bolivia", "n": "Carangas", "c": "Bolivia", "r": "bol_oruro", "ll": [-18.93333, -68.61667], "ey": 1525, "ly": 2026, "p": 6166},
  {"key": "Iscallani-Peru", "n": "Iscallani", "c": "Peru", "r": "vp_intendencia_puno", "ll": [-15.593, -69.88], "ey": 1525, "ly": 1825, "p": 6163},
  {"key": "Central Patani-Peru", "n": "Central Patani", "c": "Peru", "r": "per_puno", "ll": [-16.5798, -69.0573], "ey": 1525, "ly": 2017, "p": 6162, "al": ["desaguadero", "patani lupaca", "vizcachani"]},
  {"key": "Avipi-Colombia", "n": "Avipi", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.511, -74.062], "ey": 1525, "ly": 1830, "p": 6156, "al": ["abipique", "abypi", "Abipique"]},
  {"key": "Variante Tolú- Tramo-Colombia", "n": "Variante Tolú- Tramo", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [9.59633, -75.50669], "ey": 1300, "ly": 1500, "p": 6156, "al": ["yacimiento", "Yacimiento"]},
  {"key": "Macacara-Peru", "n": "Macacara", "c": "Peru", "r": "per_piura", "ll": [-4.9197, -80.8582], "ey": 1525, "ly": 2017, "p": 6154, "al": ["macacona", "Macacona"]},
  {"key": "San Isidro (ven_zulia)-Venezuela", "n": "San Isidro", "c": "Venezuela", "r": "ven_zulia", "ll": [10.65003, -71.75449], "ey": 1850, "ly": 2025, "p": 6151},
  {"key": "Laramarca-Peru", "n": "Laramarca", "c": "Peru", "r": "per_huancavelica", "ll": [-13.94861, -75.03556], "ey": 1525, "ly": 2025, "p": 6151, "al": ["lacramarca", "Lacramarca"]},
  {"key": "La Culebra-Colombia", "n": "La Culebra", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [8.012, -72.611], "ey": 1525, "ly": 1830, "p": 6150},
  {"key": "Cerro Azul-Argentina", "n": "Cerro Azul", "c": "Argentina", "r": "arg_misiones", "ll": [-27.63363, -55.49731], "ey": 1900, "ly": 2022, "p": 6148},
  {"key": "Jalima-Colombia", "n": "Jalima", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.863, -76.673], "ey": 1525, "ly": 1830, "p": 6147, "al": ["galima", "galinia", "gelinia"]},
  {"key": "Soublette-Venezuela", "n": "Soublette", "c": "Venezuela", "r": "ven_miranda", "ll": [9.91529, -66.09504], "ey": 1850, "ly": 2025, "p": 6146},
  {"key": "Cruzgai-Peru", "n": "Cruzgai", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-8.172, -78.352], "ey": 1525, "ly": 1825, "p": 6146},
  {"key": "Chumbes-Peru", "n": "Chumbes", "c": "Peru", "r": "per_ayacucho", "ll": [-13.4284, -73.9048], "ey": 1525, "ly": 2017, "p": 6145},
  {"key": "Tomependa-Peru", "n": "Tomependa", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-5.785, -78.707], "ey": 1525, "ly": 1830, "p": 6142},
  {"key": "Alto Paraná Guaraní-Argentina", "n": "Alto Paraná Guaraní", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-27.367, -55.896], "ey": 600, "ly": 1450, "p": 6140, "al": ["misiones guaraní", "Misiones Guaraní"]},
  {"key": "El Silencio-Peru", "n": "El Silencio", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.37707, -76.788], "ey": 1300, "ly": 1532, "p": 6139, "al": ["curayacu", "curayacu e", "curayacu f"]},
  {"key": "Andamarca-Bolivia", "n": "Andamarca", "c": "Bolivia", "r": "bol_oruro", "ll": [-18.78028, -67.50871], "ey": 1525, "ly": 2026, "p": 6138, "al": ["santiago de andamarca", "Santiago de Andamarca"]},
  {"key": "Chipana-Chile", "n": "Chipana", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-21.34, -70.094], "ey": 1525, "ly": 1825, "p": 6137},
  {"key": "Sancos (per_ayacucho)-Peru", "n": "Sancos", "c": "Peru", "r": "per_ayacucho", "ll": [-13.91972, -74.33417], "ey": 1525, "ly": 2025, "p": 6136, "al": ["huanca sancos", "zancos", "Huanca Sancos"]},
  {"key": "San Agustín (col_bolivar)-Colombia", "n": "San Agustín", "c": "Colombia", "r": "col_bolivar", "ll": [9.94139, -74.87236], "ey": 1779, "ly": 2018, "p": 6135, "al": ["san agustin", "San Agustin"]},
  {"key": "Nare-Colombia", "n": "Nare", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.35, -74.33], "ey": -9890, "ly": 1419, "p": 6135},
  {"key": "San Marcos de Rocchac-Peru", "n": "San Marcos de Rocchac", "c": "Peru", "r": "per_huancavelica", "ll": [-12.09389, -74.86389], "ey": 1525, "ly": 2025, "p": 6134, "al": ["roccha", "Roccha"]}
]

def hav(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

root = pathlib.Path("histmap/1.data_raw/population_regional/QUIPU")
local_hits = {x["key"]: [] for x in INPUT}

for f in root.rglob("*_settlements.json"):
    try:
        data = json.loads(f.read_text(encoding="utf8"))
    except Exception:
        continue
    rows = data if isinstance(data, list) else data.get("settlements", data.get("records", []))
    if not isinstance(rows, list):
        continue
    for row in rows:
        if not isinstance(row, dict): continue
        r_lat = row.get("lat") or (row.get("coords")[0] if isinstance(row.get("coords"), list) and len(row.get("coords"))==2 else None)
        r_lng = row.get("lng") or (row.get("coords")[1] if isinstance(row.get("coords"), list) and len(row.get("coords"))==2 else None)
        r_name = str(row.get("name") or row.get("canonical_name") or "").lower()
        for item in INPUT:
            if row.get("key") == item["key"] or (r_lat is not None and r_lng is not None and hav(float(r_lat), float(r_lng), item["ll"][0], item["ll"][1]) < 2.0):
                slim = {k: v for k, v in row.items() if k not in ("populations", "population_series", "yearly_populations")}
                slim["_src"] = str(f.relative_to(root))
                local_hits[item["key"]].append(slim)

# Also check hgis_indias/da_dem_lugares.csv
import csv
da_csv = root / "_shared/subadmin_hgis/raw_sources/hgis_indias/da_dem_lugares.csv"
if da_csv.exists():
    with open(da_csv, encoding="utf8", errors="ignore") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                rlat = float(row.get("lat") or row.get("LAT") or 999)
                rlng = float(row.get("lon") or row.get("lng") or row.get("LON") or 999)
            except Exception:
                continue
            for item in INPUT:
                if hav(rlat, rlng, item["ll"][0], item["ll"][1]) < 3.0:
                    local_hits[item["key"]].append({"_src": "da_dem_lugares.csv", **{k:v for k,v in row.items() if v}})

pathlib.Path("tests/tmp_local_hits_024.json").write_text(json.dumps(local_hits, ensure_ascii=False, indent=2), encoding="utf8")
print("Local hits found for", sum(1 for v in local_hits.values() if v), "of", len(INPUT))
