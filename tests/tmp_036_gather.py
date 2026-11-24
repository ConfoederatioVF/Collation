import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

INPUT = [
  {"key": "Mariangola-Colombia", "n": "Mariangola", "c": "Colombia", "r": "col_cesar", "ll": [10.18171, -73.58726], "ey": 1850, "ly": 2018, "p": 4645},
  {"key": "Ollaraya-Peru", "n": "Ollaraya", "c": "Peru", "r": "per_puno", "ll": [-16.21972, -68.99111], "ey": 1850, "ly": 2025, "p": 4644, "al": ["marcaja", "san miguel de ollaraya", "unicachi"]},
  {"key": "Avaria-Venezuela", "n": "Avaria", "c": "Venezuela", "r": "ven_falcon", "ll": [10.78333, -70.46], "ey": 1850, "ly": 2025, "p": 4642},
  {"key": "Ranracancha-Peru", "n": "Ranracancha", "c": "Peru", "r": "per_apurimac", "ll": [-13.5325, -73.60556], "ey": 1850, "ly": 2025, "p": 4642},
  {"key": "San Silvestre de Cochan-Peru", "n": "San Silvestre de Cochan", "c": "Peru", "r": "per_cajamarca", "ll": [-6.9775, -78.77389], "ey": 1850, "ly": 2025, "p": 4642, "al": ["san silvestre de cochán", "San Silvestre de Cochán"]},
  {"key": "Pila-Argentina", "n": "Pila", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-36.00422, -58.14126], "ey": 1850, "ly": 2022, "p": 4642, "al": ["casalins", "Casalins"]},
  {"key": "Puerchag-Colombia", "n": "Puerchag", "c": "Colombia", "r": "col_narino", "ll": [1.31531, -77.59245], "ey": 1525, "ly": 2018, "p": 4639, "al": ["obando", "turupamba", "Obando"]},
  {"key": "Yanaconas-Colombia", "n": "Yanaconas", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.455, -76.587], "ey": 1525, "ly": 1830, "p": 4638, "al": ["anaconas", "ananconas", "Anaconas"]},
  {"key": "Aguas Calientes-Argentina", "n": "Aguas Calientes", "c": "Argentina", "r": "arg_jujuy", "ll": [-24.58484, -64.92398], "ey": 1850, "ly": 2022, "p": 4635},
  {"key": "Angel-Ecuador", "n": "Angel", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [0.621, -77.94], "ey": 1525, "ly": 1830, "p": 4635},
  {"key": "Yacimiento 9 Km. 46 +-Colombia", "n": "Yacimiento 9 Km. 46 +", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.19557, -74.92973], "ey": -1000, "ly": 1500, "p": 4635},
  {"key": "Uchuraccay-Peru", "n": "Uchuraccay", "c": "Peru", "r": "per_ayacucho", "ll": [-12.76139, -74.14556], "ey": 1850, "ly": 2025, "p": 4630, "al": ["huaynacancha", "Huaynacancha"]},
  {"key": "Tolima - Milenion-Colombia", "n": "Tolima - Milenion", "c": "Colombia", "r": "col_cundinamarca", "ll": [4.96437, -73.93417], "ey": 1850, "ly": 2018, "p": 4628, "al": ["antonia santos", "caminos de sie", "chicalá"]},
  {"key": "San Francisco de Laishi-Argentina", "n": "San Francisco de Laishi", "c": "Argentina", "r": "arg_formosa", "ll": [-26.24389, -58.62965], "ey": 1920, "ly": 2010, "p": 4628},
  {"key": "San Carlos (ecu_orellana)-Ecuador", "n": "San Carlos", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.45631, -76.88638], "ey": 1920, "ly": 2025, "p": 4627},
  {"key": "El Chumbe-Peru", "n": "El Chumbe", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.10035, -77.35249], "ey": -2000, "ly": 1530, "p": 4627, "al": ["cementeio chambara", "chambara", "san jeronimo"]},
  {"key": "Marcapata-Peru", "n": "Marcapata", "c": "Peru", "r": "per_cusco", "ll": [-13.59167, -70.975], "ey": 1525, "ly": 2025, "p": 4624},
  {"key": "Caquingora-Bolivia", "n": "Caquingora", "c": "Bolivia", "r": "bol_la_paz", "ll": [-17.24604, -68.4955], "ey": 1525, "ly": 2024, "p": 4623},
  {"key": "Caqu-Peru", "n": "Caqu", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.50563, -77.14918], "ey": -2000, "ly": 1530, "p": 4622, "al": ["cerro andomas", "cerro culebra", "cerro la viña"]},
  {"key": "Primavera-Peru", "n": "Primavera", "c": "Peru", "r": "per_lima", "ll": [-11.0085, -77.5983], "ey": 1850, "ly": 2017, "p": 4621},
  {"key": "El Sueldo-Argentina", "n": "El Sueldo", "c": "Argentina", "r": "sc_pampas_salado_colorado", "ll": [-34.7628, -64.8705], "ey": 450, "ly": 1500, "p": 4620},
  {"key": "San Bernardo (col_cesar)-Colombia", "n": "San Bernardo", "c": "Colombia", "r": "col_cesar", "ll": [8.67683, -73.72486], "ey": 1525, "ly": 2018, "p": 4618},
  {"key": "Piñero-Argentina", "n": "Piñero", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.10909, -60.79619], "ey": 1850, "ly": 2022, "p": 4618},
  {"key": "Portachuelo San Antonio-Peru", "n": "Portachuelo San Antonio", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.66344, -79.01496], "ey": -2000, "ly": 1530, "p": 4618, "al": ["catanero", "la curva", "shimba"]},
  {"key": "La Lomita-Colombia_2", "n": "La Lomita", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [3.66931, -76.35142], "ey": 500, "ly": 1500, "p": 4617},
  {"key": "Santa Inés (ven_anzoategui)-Venezuela", "n": "Santa Inés", "c": "Venezuela", "r": "ven_anzoategui", "ll": [9.90687, -64.35348], "ey": 1850, "ly": 2025, "p": 4615},
  {"key": "Rumisapa-Peru", "n": "Rumisapa", "c": "Peru", "r": "per_san_martin", "ll": [-6.44889, -76.47167], "ey": 1900, "ly": 2025, "p": 4614},
  {"key": "General Enrique Godoy-Argentina", "n": "General Enrique Godoy", "c": "Argentina", "r": "arg_rio_negro", "ll": [-39.07955, -67.15755], "ey": 1900, "ly": 2022, "p": 4614},
  {"key": "Balneario Buenos Aires-Uruguay", "n": "Balneario Buenos Aires", "c": "Uruguay", "r": "ury_maldonado", "ll": [-34.88983, -54.79603], "ey": 1850, "ly": 2023, "p": 4612},
  {"key": "Etruria-Argentina", "n": "Etruria", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.93932, -63.24482], "ey": 1850, "ly": 2022, "p": 4609},
  {"key": "Diguillin-Chile", "n": "Diguillin", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-36.869, -72.33], "ey": 1795, "ly": 1830, "p": 4608},
  {"key": "Piedras Negras-Colombia", "n": "Piedras Negras", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.42956, -74.75664], "ey": 500, "ly": 1500, "p": 4608, "al": ["la ceiba", "La Ceiba"]},
  {"key": "El Timbó-Argentina", "n": "El Timbó", "c": "Argentina", "r": "arg_tucuman", "ll": [-26.64289, -65.18855], "ey": 1850, "ly": 2022, "p": 4606},
  {"key": "Leonardo Ruiz Pineda-Venezuela", "n": "Leonardo Ruiz Pineda", "c": "Venezuela", "r": "ven_delta_amacuro", "ll": [9.25599, -61.8062], "ey": 1920, "ly": 2025, "p": 4604},
  {"key": "Villa los Niches-Chile", "n": "Villa los Niches", "c": "Chile", "r": "chl_region_del_maule", "ll": [-35.06907, -71.15864], "ey": 1850, "ly": 2017, "p": 4604},
  {"key": "Las Torcazas-Chile", "n": "Las Torcazas", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.64603, -73.09294], "ey": 1350, "ly": 1500, "p": 4603, "al": ["fundo san miguel", "Fundo San Miguel"]},
  {"key": "Chauchamarca-Ecuador", "n": "Chauchamarca", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-3.11, -79.197], "ey": 1525, "ly": 1830, "p": 4602},
  {"key": "Machaca-Peru", "n": "Machaca", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.434, -77.316], "ey": 1525, "ly": 1825, "p": 4601},
  {"key": "CoCuChoZ4PiR-Colombia", "n": "CoCuChoZ4PiR", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [4.53962, -73.9102], "ey": 1000, "ly": 1500, "p": 4601},
  {"key": "La Agustina (col_cauca)-Colombia", "n": "La Agustina", "c": "Colombia", "r": "col_cauca", "ll": [2.91587, -76.54806], "ey": 1525, "ly": 2018, "p": 4600, "al": ["bellavista", "la chapa", "llanito"]},
  {"key": "Yaulis-Peru", "n": "Yaulis", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.73859, -74.50512], "ey": 0, "ly": 1530, "p": 4600},
  {"key": "Tres Lagunas-Argentina", "n": "Tres Lagunas", "c": "Argentina", "r": "arg_formosa", "ll": [-25.21582, -58.5132], "ey": 1900, "ly": 2022, "p": 4598},
  {"key": "Cruceta-Peru", "n": "Cruceta", "c": "Peru", "r": "per_piura", "ll": [-4.8383, -80.2649], "ey": 1850, "ly": 2017, "p": 4597},
  {"key": "Markapuchungo-Peru", "n": "Markapuchungo", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.11645, -72.25822], "ey": 0, "ly": 1530, "p": 4597, "al": ["acjchiñacha", "amayccasa a", "amayccasa b"]},
  {"key": "Tlp-Colombia", "n": "Tlp", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.47, -75.77], "ey": 791, "ly": 1500, "p": 4596, "al": ["city gate", "nuevo sol", "City Gate"]},
  {"key": "Rosario-Chile", "n": "Rosario", "c": "Chile", "r": "chl_region_del_libertador_bernardo_o_higgins", "ll": [-34.34986, -70.83914], "ey": 1850, "ly": 2017, "p": 4593},
  {"key": "San Lorenzo (arg_corrientes)-Argentina", "n": "San Lorenzo", "c": "Argentina", "r": "arg_corrientes", "ll": [-28.13812, -58.76824], "ey": 1536, "ly": 2022, "p": 4592},
  {"key": "Tunquiri-Bolivia", "n": "Tunquiri", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.34, -67.682], "ey": 1525, "ly": 1825, "p": 4592},
  {"key": "Barranca Vieja-Colombia", "n": "Barranca Vieja", "c": "Colombia", "r": "col_bolivar", "ll": [10.14981, -74.94973], "ey": 1525, "ly": 2018, "p": 4591},
  {"key": "Chinga (vng_santafe_tunja_highlands)-Colombia", "n": "Chinga", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.607, -74.128], "ey": 1525, "ly": 1830, "p": 4591},
  {"key": "Barranca Nueva-Colombia", "n": "Barranca Nueva", "c": "Colombia", "r": "col_bolivar", "ll": [10.19571, -74.93502], "ey": 1525, "ly": 2018, "p": 4584, "al": ["barranca", "barranca del rey", "Barranca"]},
  {"key": "Lourdes-Colombia", "n": "Lourdes", "c": "Colombia", "r": "col_norte_de_santander", "ll": [7.94563, -72.83238], "ey": 1850, "ly": 2025, "p": 4584},
  {"key": "Pedro Pablo Gómez-Ecuador", "n": "Pedro Pablo Gómez", "c": "Ecuador", "r": "ecu_santa_elena", "ll": [-1.66716, -80.58502], "ey": 1850, "ly": 2025, "p": 4584},
  {"key": "Letira-Peru", "n": "Letira", "c": "Peru", "r": "per_piura", "ll": [-5.4397, -80.8069], "ey": 1850, "ly": 2017, "p": 4584, "al": ["becara", "Becara"]},
  {"key": "Camarones-Ecuador", "n": "Camarones", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.96173, -79.52363], "ey": 1850, "ly": 2025, "p": 4583},
  {"key": "Tres de Diciembre-Peru", "n": "Tres de Diciembre", "c": "Peru", "r": "per_junin", "ll": [-12.10972, -75.24583], "ey": 1850, "ly": 2025, "p": 4581},
  {"key": "La Mendieta-Argentina", "n": "La Mendieta", "c": "Argentina", "r": "arg_jujuy", "ll": [-24.31434, -64.96663], "ey": 1850, "ly": 2022, "p": 4581},
  {"key": "Huachon-Peru", "n": "Huachon", "c": "Peru", "r": "per_pasco", "ll": [-10.63639, -75.95111], "ey": 1850, "ly": 2025, "p": 4579, "al": ["huachón", "Huachón"]},
  {"key": "Complejo Santa Maria-Peru", "n": "Complejo Santa Maria", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.11635, -79.55545], "ey": -1000, "ly": 1532, "p": 4579, "al": ["monticulo", "montículo", "santa rosa"]},
  {"key": "Sa-Tm-Colombia", "n": "Sa-Tm", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.44102, -74.82597], "ey": 1000, "ly": 1500, "p": 4579},
  {"key": "San Luis-Peru_2", "n": "San Luis", "c": "Peru", "r": "ca_equatorial_sierra_canari", "ll": [-3.69832, -76.40295], "ey": -2000, "ly": 1438, "p": 4579, "al": ["boca del loboyacu", "loboyacu", "Boca del Loboyacu"]},
  {"key": "El Sireno UMP-Colombia", "n": "El Sireno UMP", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [6.41, -76.29], "ey": 145, "ly": 1500, "p": 4578},
  {"key": "Reducción-Argentina", "n": "Reducción", "c": "Argentina", "r": "arg_cordoba", "ll": [-33.20319, -63.86259], "ey": 1751, "ly": 2022, "p": 4576, "al": ["villa reducción", "san francisco asis de los indios pampas", "reduccion"]},
  {"key": "Pueblo Nuevo-Ecuador", "n": "Pueblo Nuevo", "c": "Ecuador", "r": "ecu_manabi", "ll": [-0.97629, -80.30103], "ey": 1850, "ly": 2025, "p": 4575},
  {"key": "Santa Lucia (per_san_martin)-Peru", "n": "Santa Lucia", "c": "Peru", "r": "per_san_martin", "ll": [-8.3449, -76.3872], "ey": 1920, "ly": 2017, "p": 4575, "al": ["nueva union", "Nueva Union"]},
  {"key": "San Francisco (ven_falcon_2)-Venezuela", "n": "San Francisco", "c": "Venezuela", "r": "ven_falcon", "ll": [11.44778, -69.26722], "ey": 1538, "ly": 2011, "p": 4572, "al": ["turupia", "turupiza o turupiita", "Turupia"]},
  {"key": "Los Barriales-Argentina", "n": "Los Barriales", "c": "Argentina", "r": "arg_mendoza", "ll": [-33.10104, -68.56753], "ey": 1850, "ly": 2022, "p": 4572},
  {"key": "Pérez Millán-Argentina", "n": "Pérez Millán", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-33.7701, -60.09389], "ey": 1850, "ly": 2010, "p": 4570},
  {"key": "Los Lirios-Chile", "n": "Los Lirios", "c": "Chile", "r": "chl_region_del_libertador_bernardo_o_higgins", "ll": [-34.23003, -70.7802], "ey": 1850, "ly": 2017, "p": 4569},
  {"key": "La Tigra-Argentina", "n": "La Tigra", "c": "Argentina", "r": "arg_chaco", "ll": [-27.10954, -60.58734], "ey": 1900, "ly": 2022, "p": 4563},
  {"key": "Ugarteche-Argentina", "n": "Ugarteche", "c": "Argentina", "r": "arg_mendoza", "ll": [-33.2119, -68.88776], "ey": 1850, "ly": 2010, "p": 4561},
  {"key": "La Ramada-Bolivia", "n": "La Ramada", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.571, -66.461], "ey": 1525, "ly": 1825, "p": 4561},
  {"key": "La Torita-Peru", "n": "La Torita", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-5.73409, -78.43822], "ey": 500, "ly": 1530, "p": 4561},
  {"key": "La Paya-Argentina", "n": "La Paya", "c": "Argentina", "r": "inca_collasuyu", "ll": [-25.182, -66.178], "ey": 1475, "ly": 1530, "p": 4560},
  {"key": "Cotogchoa-Ecuador", "n": "Cotogchoa", "c": "Ecuador", "r": "ecu_pichincha", "ll": [-0.41123, -78.45233], "ey": 1850, "ly": 2025, "p": 4559},
  {"key": "José María Arguedas-Peru", "n": "José María Arguedas", "c": "Peru", "r": "per_apurimac", "ll": [-13.73417, -73.35056], "ey": 1850, "ly": 2025, "p": 4554, "al": ["huancabamba", "Huancabamba"]},
  {"key": "Wallpartasiri Pongo-Peru", "n": "Wallpartasiri Pongo", "c": "Peru", "r": "inca_collasuyu", "ll": [-16.04313, -69.47797], "ey": 1300, "ly": 1530, "p": 4552, "al": ["chejota pongo", "huancuni pongo", "llangamaya pongo"]},
  {"key": "José Felipe Márquez Cañizales-Venezuela", "n": "José Felipe Márquez Cañizales", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.8665, -70.57931], "ey": 1850, "ly": 2011, "p": 4551},
  {"key": "El Guásimo-Colombia", "n": "El Guásimo", "c": "Colombia", "r": "col_cauca", "ll": [3.06638, -76.41011], "ey": 1525, "ly": 2018, "p": 4550, "al": ["la quebrada", "el sauce", "La Quebrada"]},
  {"key": "San Juan Bosco-Ecuador", "n": "San Juan Bosco", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-3.25995, -78.38524], "ey": 1900, "ly": 2025, "p": 4550},
  {"key": "Olta-Argentina", "n": "Olta", "c": "Argentina", "r": "arg_la_rioja", "ll": [-30.63062, -66.26729], "ey": 1536, "ly": 2010, "p": 4547},
  {"key": "San Antonio-Colombia_2", "n": "San Antonio", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [7.07632, -73.73031], "ey": 1300, "ly": 1500, "p": 4546, "al": ["el campanario k16+", "galilea", "El Campanario K16+"]},
  {"key": "Quichuas-Peru", "n": "Quichuas", "c": "Peru", "r": "per_huancavelica", "ll": [-12.4725, -74.7675], "ey": 1850, "ly": 2025, "p": 4544},
  {"key": "Cochinoca-Argentina", "n": "Cochinoca", "c": "Argentina", "r": "arg_jujuy", "ll": [-22.74533, -65.89612], "ey": 1536, "ly": 2022, "p": 4544},
  {"key": "Cueva Mora-Argentina", "n": "Cueva Mora", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-46.90255, -68.89426], "ey": -2206, "ly": -1306, "p": 4543},
  {"key": "Córdoba (ven_portuguesa)-Venezuela", "n": "Córdoba", "c": "Venezuela", "r": "ven_portuguesa", "ll": [9.31722, -69.85], "ey": 1850, "ly": 2025, "p": 4541},
  {"key": "Villa Basilio Nievas-Argentina", "n": "Villa Basilio Nievas", "c": "Argentina", "r": "arg_san_juan", "ll": [-31.54855, -68.73082], "ey": 1850, "ly": 2010, "p": 4539},
  {"key": "Huelquén-Chile", "n": "Huelquén", "c": "Chile", "r": "chl_region_metropolitana_de_santiago", "ll": [-33.83282, -70.64198], "ey": 1850, "ly": 2017, "p": 4538},
  {"key": "Con-Chile", "n": "Con", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.70072, -69.51233], "ey": 1000, "ly": 1500, "p": 4538},
  {"key": "Yurumarca-Peru", "n": "Yurumarca", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-6.046, -77.804], "ey": 0, "ly": 1825, "p": 4537, "al": ["yurmarca", "en proceso", "Yurmarca"]}
]

UA = "ViscountHistoricalResearch/1.0 (mailto:research@confoederatio.org)"

# 1. Local QUIPU search
quipu_dir = "histmap/1.data_raw/population_regional/QUIPU"
local_hits = {}
names_lower = {it["n"].lower(): it["key"] for it in INPUT}
keys_set = {it["key"] for it in INPUT}

for root, dirs, files in os.walk(quipu_dir):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", "_gis_cache", "rasters", "figures", "subadmin_hgis")]
    for fn in files:
        if not fn.endswith((".json", ".json5", ".csv")):
            continue
        fp = os.path.join(root, fn)
        try:
            if os.path.getsize(fp) > 30_000_000:
                continue
            txt = open(fp, "r", encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for it in INPUT:
            n = it["n"]
            if n in txt or it["key"] in txt:
                for line in txt.splitlines():
                    if n in line or it["key"] in line:
                        local_hits.setdefault(it["key"], []).append(
                            f"{os.path.relpath(fp, quipu_dir)}: {line.strip()[:280]}"
                        )
                        if len(local_hits[it["key"]]) >= 6:
                            break

# 2. Query es.wikipedia.org geosearch & search + full extracts
def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def lookup_wiki(it):
    lat, lng = it["ll"]
    name = it["n"]
    country = it["c"]
    out = {"key": it["key"], "n": name, "c": country, "r": it["r"], "ll": it["ll"], "ey": it["ey"], "ly": it["ly"], "al": it.get("al", [])}
    
    # es.wikipedia geosearch
    try:
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
        gs = fetch_json(u).get("query", {}).get("geosearch", [])
        out["es_geo"] = [{"title": g["title"], "dist": round(g["dist"])} for g in gs]
    except Exception as e:
        out["es_geo_err"] = str(e)

    # es.wikipedia search
    try:
        q = urllib.parse.quote(f'"{name}" {country}')
        u = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sr = fetch_json(u).get("query", {}).get("search", [])
        out["es_search"] = [{"title": s["title"], "snippet": re.sub(r"<[^>]+>", "", s.get("snippet", ""))} for s in sr]
    except Exception as e:
        out["es_search_err"] = str(e)

    cand_titles = []
    for g in out.get("es_geo", [])[:2]:
        cand_titles.append(g["title"])
    for s in out.get("es_search", [])[:2]:
        if s["title"] not in cand_titles:
            cand_titles.append(s["title"])

    extracts = {}
    if cand_titles:
        try:
            titles_p = urllib.parse.quote("|".join(cand_titles[:3]))
            u = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=1&exchars=4000&titles={titles_p}&format=json"
            pages = fetch_json(u).get("query", {}).get("pages", {})
            for pid, p in pages.items():
                if int(pid) > 0:
                    extracts[p.get("title")] = {
                        "extract": p.get("extract", "")[:2500],
                        "coords": p.get("coordinates", [])
                    }
        except Exception as e:
            out["extract_err"] = str(e)
    out["es_extracts"] = extracts
    return out

results = []
with ThreadPoolExecutor(max_workers=6) as ex:
    for res in ex.map(lookup_wiki, INPUT):
        res["local"] = local_hits.get(res["key"], [])
        results.append(res)

with open("tests/tmp_036_data.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Done! Local hits: {len(local_hits)}/{len(INPUT)}; Total wiki records: {len(results)}")
