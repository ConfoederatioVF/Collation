import json
import urllib.request
import urllib.parse
import time

SETTLEMENTS = [
  {"key": "Santa María (col_boyaca)-Colombia", "n": "Santa María", "c": "Colombia", "r": "col_boyaca", "ll": [4.85719, -73.26352], "ey": 1850, "ly": 2025, "p": 5807},
  {"key": "General Proaño-Ecuador", "n": "General Proaño", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-2.26596, -78.13169], "ey": 1525, "ly": 2025, "p": 5803, "al": ["copueno", "copuno", "Copueno"]},
  {"key": "Pampahura-Peru", "n": "Pampahura", "c": "Peru", "r": "per_apurimac", "ll": [-13.6547, -73.0444], "ey": 0, "ly": 2017, "p": 5803, "al": ["arcahua", "cochacajas", "matecclla"]},
  {"key": "San Pedro de Perico-Peru", "n": "San Pedro de Perico", "c": "Peru", "r": "per_cajamarca", "ll": [-5.3427, -78.7945], "ey": 1525, "ly": 2017, "p": 5802, "al": ["perico", "Perico"]},
  {"key": "Tilingo-Argentina", "n": "Tilingo", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.297, -63.908], "ey": 1536, "ly": 1830, "p": 5802},
  {"key": "Santiago de Pupuja-Peru", "n": "Santiago de Pupuja", "c": "Peru", "r": "per_puno", "ll": [-15.05278, -70.27806], "ey": 1850, "ly": 2025, "p": 5792},
  {"key": "Aynaca-Peru", "n": "Aynaca", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.873, -77.281], "ey": 1525, "ly": 1825, "p": 5791},
  {"key": "Aguincai-Peru", "n": "Aguincai", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-8.126, -78.298], "ey": 1525, "ly": 1825, "p": 5789},
  {"key": "Alto del Carmen-Chile", "n": "Alto del Carmen", "c": "Chile", "r": "chl_region_de_atacama", "ll": [-29.05441, -70.16403], "ey": 1900, "ly": 2025, "p": 5785},
  {"key": "Chirigua-Peru", "n": "Chirigua", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-5.734, -78.492], "ey": 1525, "ly": 1830, "p": 5785},
  {"key": "Yuluc-Ecuador", "n": "Yuluc", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-3.372, -79.441], "ey": 1525, "ly": 1830, "p": 5784, "al": ["yllolloeg", "Yllolloeg"]},
  {"key": "Hinchupalla-Peru", "n": "Hinchupalla", "c": "Peru", "r": "vp_intendencia_puno", "ll": [-15.184, -69.869], "ey": 1525, "ly": 1825, "p": 5784},
  {"key": "Imantag-Ecuador", "n": "Imantag", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.45813, -78.34436], "ey": 1850, "ly": 2025, "p": 5783},
  {"key": "El Guafal-Los Cedros-Venezuela", "n": "El Guafal-Los Cedros", "c": "Venezuela", "r": "ven_aragua", "ll": [9.91936, -67.29741], "ey": 1850, "ly": 2011, "p": 5781},
  {"key": "Ptacerr-Chile", "n": "Ptacerr", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.6051, -70.52039], "ey": -3000, "ly": 1500, "p": 5779},
  {"key": "San Antonio del Chami-Colombia", "n": "San Antonio del Chami", "c": "Colombia", "r": "col_risaralda", "ll": [5.41627, -75.90433], "ey": 1525, "ly": 2018, "p": 5778, "al": ["san juan del chami", "San Juan del Chami"]},
  {"key": "Jericó (col_boyaca)-Colombia", "n": "Jericó", "c": "Colombia", "r": "col_boyaca", "ll": [6.14574, -72.57112], "ey": 1850, "ly": 2025, "p": 5777},
  {"key": "El Junko-Venezuela", "n": "El Junko", "c": "Venezuela", "r": "ven_distrito_capital", "ll": [10.48239, -67.07908], "ey": 1850, "ly": 2025, "p": 5775},
  {"key": "Huayopata-Peru", "n": "Huayopata", "c": "Peru", "r": "per_cusco", "ll": [-13.00472, -72.55444], "ey": 1850, "ly": 2025, "p": 5772, "al": ["ipal", "Ipal"]},
  {"key": "Guaraní-Argentina", "n": "Guaraní", "c": "Argentina", "r": "arg_misiones", "ll": [-27.5234, -55.15763], "ey": 1900, "ly": 2022, "p": 5772},
  {"key": "Cajamarquilla (per_ancash)-Peru", "n": "Cajamarquilla", "c": "Peru", "r": "per_ancash", "ll": [-10.35417, -77.19917], "ey": 1525, "ly": 2025, "p": 5771},
  {"key": "San Antonio Rioseco-Colombia", "n": "San Antonio Rioseco", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.179, -74.687], "ey": 1525, "ly": 1830, "p": 5766},
  {"key": "Puerto Libertad-Argentina", "n": "Puerto Libertad", "c": "Argentina", "r": "arg_misiones", "ll": [-25.92167, -54.58212], "ey": 1920, "ly": 2010, "p": 5765},
  {"key": "Colonia Elisa-Argentina", "n": "Colonia Elisa", "c": "Argentina", "r": "arg_chaco", "ll": [-26.93164, -59.51879], "ey": 1900, "ly": 2022, "p": 5764},
  {"key": "Mani-Peru", "n": "Mani", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.894, -77.153], "ey": 1525, "ly": 1825, "p": 5763},
  {"key": "Noetinger-Argentina", "n": "Noetinger", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.36594, -62.30724], "ey": 1850, "ly": 2022, "p": 5762},
  {"key": "Puerto del Salto-Ecuador", "n": "Puerto del Salto", "c": "Ecuador", "r": "vng_guayaquil_esmeraldas", "ll": [-3.48, -80.23], "ey": 1525, "ly": 1830, "p": 5760},
  {"key": "Catahuas-Peru", "n": "Catahuas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.95257, -76.13811], "ey": 0, "ly": 1532, "p": 5760, "al": ["cerro riverón", "cerro suero", "colcas de lunahuana"]},
  {"key": "Paramonga Inca-Peru", "n": "Paramonga Inca", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.654, -77.841], "ey": 1200, "ly": 1530, "p": 5760, "al": ["anexo", "anexo cerro la horca", "arnolfo vega"]},
  {"key": "Villacuri-Peru", "n": "Villacuri", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.98128, -75.84862], "ey": -2000, "ly": 1530, "p": 5758},
  {"key": "Abanico-Colombia", "n": "Abanico", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.21373, -74.88439], "ey": 500, "ly": 1500, "p": 5753, "al": ["el paraíso", "El Paraíso"]},
  {"key": "Harpita-Bolivia", "n": "Harpita", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.583, -66.05], "ey": 1525, "ly": 1825, "p": 5752},
  {"key": "Santiago de Huayllamarca-Bolivia", "n": "Santiago de Huayllamarca", "c": "Bolivia", "r": "bol_oruro", "ll": [-17.83777, -67.94278], "ey": 1525, "ly": 2024, "p": 5750, "al": ["guayllamarca", "Guayllamarca"]},
  {"key": "San Francisco-Ecuador", "n": "San Francisco", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.71039, -79.9855], "ey": 1900, "ly": 2025, "p": 5749},
  {"key": "Salamanca-Peru", "n": "Salamanca", "c": "Peru", "r": "per_arequipa", "ll": [-15.50444, -72.83444], "ey": 1525, "ly": 2025, "p": 5744},
  {"key": "San Lazaro-Peru_2", "n": "San Lazaro", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.04, -77.029], "ey": 1525, "ly": 1825, "p": 5743},
  {"key": "Lambrama-Peru", "n": "Lambrama", "c": "Peru", "r": "per_apurimac", "ll": [-13.87083, -72.76972], "ey": 1525, "ly": 2025, "p": 5742, "al": ["lambrana", "lambranza", "Lambrana"]},
  {"key": "San Rafael-Ecuador", "n": "San Rafael", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.17301, -78.23607], "ey": 1850, "ly": 2025, "p": 5741},
  {"key": "Yangana-Ecuador", "n": "Yangana", "c": "Ecuador", "r": "ecu_loja", "ll": [-4.40021, -79.17986], "ey": 1525, "ly": 2025, "p": 5738},
  {"key": "Cargonacho-Peru", "n": "Cargonacho", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.299, -74.91], "ey": 1525, "ly": 1825, "p": 5738},
  {"key": "Acebal-Argentina", "n": "Acebal", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.24175, -60.83651], "ey": 1850, "ly": 2022, "p": 5737, "al": ["acébal", "Acébal"]},
  {"key": "San José De Dahuano-Ecuador", "n": "San José De Dahuano", "c": "Ecuador", "r": "ecu_napo", "ll": [-0.74778, -77.43328], "ey": 1850, "ly": 2025, "p": 5735},
  {"key": "Macachín-Argentina", "n": "Macachín", "c": "Argentina", "r": "arg_la_pampa", "ll": [-37.13697, -63.66678], "ey": 1900, "ly": 2022, "p": 5735},
  {"key": "Tocaría PS-Colombia", "n": "Tocaría PS", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [5.38829, -72.12133], "ey": 1300, "ly": 1500, "p": 5733},
  {"key": "La Balsa-Colombia", "n": "La Balsa", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.08922, -76.60041], "ey": 1525, "ly": 2018, "p": 5729, "al": ["la bolsa", "La Bolsa"]},
  {"key": "Sacsamarca (per_huancavelica)-Peru", "n": "Sacsamarca", "c": "Peru", "r": "per_huancavelica", "ll": [-12.7999, -74.992], "ey": 1525, "ly": 2017, "p": 5728, "al": ["saccsamarca", "Saccsamarca"]},
  {"key": "Quinancipi-Colombia", "n": "Quinancipi", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.477, -74.213], "ey": 1525, "ly": 1830, "p": 5727, "al": ["quinamacepi", "Quinamacepi"]},
  {"key": "Cheqnarap-Peru", "n": "Cheqnarap", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.69172, -70.52717], "ey": 1000, "ly": 1530, "p": 5727, "al": ["acnohuirecunca", "arqueológico camellones carmen alto", "aucantera cunca"]},
  {"key": "Puéllaro-Ecuador", "n": "Puéllaro", "c": "Ecuador", "r": "ecu_pichincha", "ll": [0.05892, -78.39624], "ey": 1850, "ly": 2025, "p": 5722},
  {"key": "Marona-Peru_2", "n": "Marona", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.24133, -75.9269], "ey": -3000, "ly": 1530, "p": 5719, "al": ["alto marona", "Alto Marona"]},
  {"key": "Ampe-Chile", "n": "Ampe", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.84912, -72.70149], "ey": 1350, "ly": 1500, "p": 5718, "al": ["fundo san pedro", "fundo santa maria", "fundo maria luisa"]},
  {"key": "Marulanda-Colombia", "n": "Marulanda", "c": "Colombia", "r": "col_caldas", "ll": [5.2843, -75.25972], "ey": 1850, "ly": 2025, "p": 5717},
  {"key": "Juan Antonio Rodríguez Domínguez-Venezuela", "n": "Juan Antonio Rodríguez Domínguez", "c": "Venezuela", "r": "ven_barinas", "ll": [8.56667, -70.34778], "ey": 1850, "ly": 2025, "p": 5714},
  {"key": "San Luis-Colombia_2", "n": "San Luis", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [4, -76.97], "ey": -57, "ly": 986, "p": 5714},
  {"key": "Qasa Corral-Peru", "n": "Qasa Corral", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.29346, -74.30998], "ey": 0, "ly": 1530, "p": 5713, "al": ["chaupi qasa", "huamani moqo", "llaqta qullusqa"]},
  {"key": "Santa Cruz-Chile_2", "n": "Santa Cruz", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-37.28449, -72.70327], "ey": 0, "ly": 1500, "p": 5712},
  {"key": "Puerto Santo-Venezuela", "n": "Puerto Santo", "c": "Venezuela", "r": "ven_sucre", "ll": [10.70611, -63.16667], "ey": 1538, "ly": 2025, "p": 5711, "al": ["el morro de puerto santo", "El Morro de Puerto Santo"]},
  {"key": "Puerto Giraldo-Colombia", "n": "Puerto Giraldo", "c": "Colombia", "r": "col_atlantico", "ll": [10.50495, -74.81601], "ey": 1850, "ly": 2018, "p": 5710},
  {"key": "Parque Norte - Ciudad de los Niños - Villa Pastora - Almirante Brown - Guiñazú N-Argentina", "n": "Parque Norte - Ciudad de los Niños - Villa Pastora - Almirante Brown - Guiñazú N", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.30757, -64.17634], "ey": 1850, "ly": 2010, "p": 5710},
  {"key": "Pueblo Arrua-Argentina", "n": "Pueblo Arrua", "c": "Argentina", "r": "crp_intendencia_buenos_aires", "ll": [-31.456, -59.598], "ey": 1774, "ly": 1830, "p": 5710, "al": ["dolores alcaraz", "Dolores Alcaraz"]},
  {"key": "Quibaya-Bolivia", "n": "Quibaya", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-15.638, -68.7], "ey": 1525, "ly": 1825, "p": 5709},
  {"key": "Palma Sola-Argentina", "n": "Palma Sola", "c": "Argentina", "r": "arg_jujuy", "ll": [-23.97687, -64.30541], "ey": 1850, "ly": 2022, "p": 5708},
  {"key": "Montalvo-Colombia", "n": "Montalvo", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.16863, -74.81894], "ey": 1000, "ly": 1500, "p": 5708, "al": ["la paulina", "La Paulina"]},
  {"key": "Poaló-Ecuador", "n": "Poaló", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-0.88969, -78.75726], "ey": 1850, "ly": 2025, "p": 5702},
  {"key": "Vilcabamba-Ecuador", "n": "Vilcabamba", "c": "Ecuador", "r": "ecu_loja", "ll": [-4.29597, -79.26903], "ey": 1525, "ly": 2025, "p": 5700},
  {"key": "Jambur-Peru", "n": "Jambur", "c": "Peru", "r": "per_piura", "ll": [-4.6082, -79.9445], "ey": 1525, "ly": 2017, "p": 5700, "al": ["quiroz", "Quiroz"]},
  {"key": "Shuquil-Peru", "n": "Shuquil", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.03002, -76.6551], "ey": 1438, "ly": 1530, "p": 5699, "al": ["concejo corral", "goguy", "gongu"]},
  {"key": "La Pesca-Colombia", "n": "La Pesca", "c": "Colombia", "r": "col_antioquia", "ll": [6.20596, -74.59113], "ey": 1525, "ly": 2018, "p": 5697, "al": ["puerto nare", "nares", "san jose de nare"]},
  {"key": "Coronel Moldes (arg_salta)-Argentina", "n": "Coronel Moldes", "c": "Argentina", "r": "arg_salta", "ll": [-25.28008, -65.47864], "ey": 1850, "ly": 2022, "p": 5695},
  {"key": "Tilcara-Argentina", "n": "Tilcara", "c": "Argentina", "r": "arg_jujuy", "ll": [-23.57694, -65.39337], "ey": 1850, "ly": 2022, "p": 5691},
  {"key": "Mompox Malibú-Colombia", "n": "Mompox Malibú", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [9.242, -74.426], "ey": 600, "ly": 1500, "p": 5690, "al": ["albarrada el campillo", "albarrada los ángeles", "albarrada norte"]},
  {"key": "Ibicuy-Argentina", "n": "Ibicuy", "c": "Argentina", "r": "arg_entre_rios", "ll": [-33.74237, -59.15769], "ey": 1850, "ly": 2022, "p": 5688},
  {"key": "Sevilla De Oro-Ecuador", "n": "Sevilla De Oro", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.70583, -78.60222], "ey": 1850, "ly": 2025, "p": 5687},
  {"key": "Cuzubamba-Ecuador", "n": "Cuzubamba", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-1.07, -78.701], "ey": 1525, "ly": 1830, "p": 5683, "al": ["curubamba", "custubamba", "Curubamba"]},
  {"key": "Quebrada Honda-Chile", "n": "Quebrada Honda", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-29.587, -71.199], "ey": 1525, "ly": 1830, "p": 5682},
  {"key": "Ohs-Colombia", "n": "Ohs", "c": "Colombia", "r": "na_nw_amazon_foothills", "ll": [0.61333, -76.82698], "ey": 500, "ly": 1500, "p": 5681, "al": ["ori", "pha", "Ori"]},
  {"key": "Pozo del Molle-Argentina", "n": "Pozo del Molle", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.02129, -62.91922], "ey": 1850, "ly": 2010, "p": 5680},
  {"key": "Pichacani-Peru", "n": "Pichacani", "c": "Peru", "r": "per_puno", "ll": [-16.15, -70.06333], "ey": 1850, "ly": 2025, "p": 5679, "al": ["laraqueri", "Laraqueri"]},
  {"key": "Cochas-Peru_2", "n": "Cochas", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.643, -77.542], "ey": 500, "ly": 1825, "p": 5679, "al": ["cerro grande alto", "cerro espachín alto", "cerro grande bajo"]},
  {"key": "Tancacha-Argentina", "n": "Tancacha", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.23755, -63.97977], "ey": 1850, "ly": 2022, "p": 5677},
  {"key": "Los Balsares-Peru", "n": "Los Balsares", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.68065, -79.43257], "ey": -3000, "ly": 1530, "p": 5677, "al": ["campamento lítico malabrigo", "carrazcal", "cerro malabrigo"]},
  {"key": "Caserones-Chile", "n": "Caserones", "c": "Chile", "r": "inca_collasuyu", "ll": [-19.9787, -69.56087], "ey": -1259, "ly": 1532, "p": 5674, "al": ["tarapaca", "caserones tarapacá", "tarapaca 14-a"]},
  {"key": "UF5 Yacimiento 3 El Tambo-Colombia", "n": "UF5 Yacimiento 3 El Tambo", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.17667, -74.87639], "ey": 0, "ly": 1500, "p": 5674, "al": ["uf4 yacimiento asociado al sitio montalvito", "uf5 yacimiento 1 - patio bonito", "UF4 Yacimiento asociado al sitio Montalvito"]},
  {"key": "Cajón-Chile", "n": "Cajón", "c": "Chile", "r": "chl_region_de_la_araucania", "ll": [-38.67857, -72.50539], "ey": 1920, "ly": 2017, "p": 5673},
  {"key": "Santiago de Chilcas-Peru", "n": "Santiago de Chilcas", "c": "Peru", "r": "per_ancash", "ll": [-10.43861, -77.36583], "ey": 1525, "ly": 2025, "p": 5670, "al": ["chilcas", "Chilcas"]},
  {"key": "Pirhuani-Bolivia", "n": "Pirhuani", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-20.303, -64.674], "ey": 1525, "ly": 1825, "p": 5669, "al": ["pirguani", "Pirguani"]},
  {"key": "San Francisco (col_putumayo)-Colombia", "n": "San Francisco", "c": "Colombia", "r": "col_putumayo", "ll": [1.17419, -76.87928], "ey": 1900, "ly": 2025, "p": 5668},
  {"key": "San Felipe-Peru", "n": "San Felipe", "c": "Peru", "r": "per_cajamarca", "ll": [-5.77028, -79.31389], "ey": 1525, "ly": 2025, "p": 5664},
  {"key": "San Jose Noanama-Colombia", "n": "San Jose Noanama", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [4.69, -76.936], "ey": 1525, "ly": 1830, "p": 5664},
  {"key": "Cerro Motete-Peru", "n": "Cerro Motete", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.88138, -79.44128], "ey": -1000, "ly": 1530, "p": 5662, "al": ["huaca la tendida 3 - kuchi gordo - pampa san pedro", "la viña", "pampas el examen"]}
]

def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SVEA-Quipu-Research/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def geosearch(lang, lat, lng, radius=10000):
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius={radius}&gslimit=5&format=json"
    try:
        data = api_get(url)
        return [x["title"] for x in data.get("query", {}).get("geosearch", [])]
    except Exception as e:
        return [f"ERR:{e}"]

def opensearch(lang, q):
    url = f"https://{lang}.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(q)}&limit=3&format=json"
    try:
        data = api_get(url)
        return data[1] if len(data) > 1 else []
    except Exception as e:
        return [f"ERR:{e}"]

out = []
for i, s in enumerate(SETTLEMENTS):
    lat, lng = s["ll"]
    gs_es = geosearch("es", lat, lng, 10000)
    os_es = opensearch("es", f"{s['n']} {s['c']}")
    out.append({
        "key": s["key"],
        "n": s["n"],
        "c": s["c"],
        "r": s["r"],
        "gs_es": gs_es,
        "os_es": os_es
    })
    if i % 10 == 0:
        print(f"Processed {i}/{len(SETTLEMENTS)}", flush=True)
    time.sleep(0.05)

with open("tests/chunk027_wiki_hits.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Done!")
