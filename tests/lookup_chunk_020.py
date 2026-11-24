import json
import glob
import os
import time
import urllib.request
import urllib.parse
import math

INPUT = [
  {"key": "Capaya-Peru", "n": "Capaya", "c": "Peru", "r": "per_apurimac", "ll": [-14.11778, -73.32111], "ey": 1525, "ly": 2025, "p": 6796},
  {"key": "Santa Cruz de Andamarca-Peru", "n": "Santa Cruz de Andamarca", "c": "Peru", "r": "per_lima", "ll": [-11.19472, -76.63444], "ey": 1525, "ly": 2025, "p": 6796, "al": ["chauca", "santa cruz", "Santa Cruz"]},
  {"key": "Juncales-Ecuador", "n": "Juncales", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.486, -78.971], "ey": 1525, "ly": 1830, "p": 6796},
  {"key": "El Overo ( Sector Poblado )-Colombia", "n": "El Overo ( Sector Poblado )", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [4.24328, -76.13357], "ey": 1525, "ly": 2018, "p": 6795, "al": ["el overo", "El Overo", "El Overo ( Sector La María )"]},
  {"key": "Pisuquia-Peru", "n": "Pisuquia", "c": "Peru", "r": "per_amazonas", "ll": [-6.45333, -78.09194], "ey": 1525, "ly": 2025, "p": 6794, "al": ["yomblon", "Yomblon"]},
  {"key": "Santa Barbara Lame-Colombia", "n": "Santa Barbara Lame", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.7, -76.086], "ey": 1525, "ly": 1830, "p": 6794},
  {"key": "Zirid-Ecuador", "n": "Zirid", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.51, -78.988], "ey": 1525, "ly": 1830, "p": 6793},
  {"key": "Chapis-Peru_2", "n": "Chapis", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.373, -76.781], "ey": 1525, "ly": 1825, "p": 6791},
  {"key": "Huaca (vp_intendencia_lima)-Peru", "n": "Huaca", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.777, -77.288], "ey": 1525, "ly": 1825, "p": 6789},
  {"key": "Lomas de Pacta B-Peru", "n": "Lomas de Pacta B", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.28378, -76.77949], "ey": 1438, "ly": 1530, "p": 6788, "al": ["conchales superficiales", "lomas de pacta c", "quebraleña alto"]},
  {"key": "valle de Jimbura-Ecuador", "n": "valle de Jimbura", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-4.63, -79.463], "ey": 1525, "ly": 1830, "p": 6787},
  {"key": "Zetaquira-Colombia", "n": "Zetaquira", "c": "Colombia", "r": "col_boyaca", "ll": [5.28344, -73.17098], "ey": 1525, "ly": 2025, "p": 6786},
  {"key": "Hongos-Peru", "n": "Hongos", "c": "Peru", "r": "per_lima", "ll": [-12.81083, -75.76528], "ey": 1525, "ly": 2025, "p": 6785, "al": ["ongos", "Ongos"]},
  {"key": "Conchao-Peru", "n": "Conchao", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.746, -76.887], "ey": 1525, "ly": 1825, "p": 6785},
  {"key": "Pampamarca (per_arequipa)-Peru", "n": "Pampamarca", "c": "Peru", "r": "per_arequipa", "ll": [-15.1825, -72.90528], "ey": 1525, "ly": 2025, "p": 6784, "al": ["mungui", "monguy", "Mungui"]},
  {"key": "Valencia de Jesús-Colombia", "n": "Valencia de Jesús", "c": "Colombia", "r": "col_cesar", "ll": [10.30156, -73.39459], "ey": 1590, "ly": 2018, "p": 6783, "al": ["valencia de jesus", "ciudad de nueva valencia", "nombre de jesus"]},
  {"key": "Yuraycoco-Peru", "n": "Yuraycoco", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-10.945, -76.835], "ey": 1525, "ly": 1825, "p": 6781, "al": ["yurayaco", "Yurayaco"]},
  {"key": "Manugasta-Argentina", "n": "Manugasta", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.029, -64.21], "ey": 1536, "ly": 1830, "p": 6780},
  {"key": "Congalla-Peru", "n": "Congalla", "c": "Peru", "r": "per_huancavelica", "ll": [-12.95583, -74.49222], "ey": 1525, "ly": 2025, "p": 6778},
  {"key": "Playa Unión-Argentina", "n": "Playa Unión", "c": "Argentina", "r": "arg_chubut", "ll": [-43.32194, -65.0476], "ey": 1920, "ly": 2010, "p": 6775},
  {"key": "Puerto Caldas-Colombia", "n": "Puerto Caldas", "c": "Colombia", "r": "col_risaralda", "ll": [4.76222, -75.90383], "ey": 1850, "ly": 2018, "p": 6774},
  {"key": "Cochapeti-Peru", "n": "Cochapeti", "c": "Peru", "r": "per_ancash", "ll": [-9.98722, -77.64611], "ey": 1525, "ly": 2025, "p": 6773, "al": ["cochapati", "Cochapati"]},
  {"key": "Cotahuasi-Peru", "n": "Cotahuasi", "c": "Peru", "r": "per_arequipa", "ll": [-15.21278, -72.88944], "ey": 0, "ly": 2025, "p": 6772, "al": ["cerro buena vista", "ciudadela de chalquima", "collota"]},
  {"key": "Huangala-Peru", "n": "Huangala", "c": "Peru", "r": "per_piura", "ll": [-4.8399, -80.6009], "ey": 1525, "ly": 2017, "p": 6772, "al": ["guangala", "Guangala"]},
  {"key": "Huandaro-Peru", "n": "Huandaro", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.394, -76.781], "ey": 1525, "ly": 1825, "p": 6771},
  {"key": "Colca (per_apurimac)-Peru", "n": "Colca", "c": "Peru", "r": "per_apurimac", "ll": [-14.3895, -73.1764], "ey": 1525, "ly": 2017, "p": 6769},
  {"key": "Huaca-Ecuador", "n": "Huaca", "c": "Ecuador", "r": "ecu_carchi", "ll": [0.64419, -77.71464], "ey": 1525, "ly": 2025, "p": 6765},
  {"key": "San Juan Talaga-Colombia", "n": "San Juan Talaga", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.691, -76.018], "ey": 1525, "ly": 1830, "p": 6765},
  {"key": "Huancaya-Peru", "n": "Huancaya", "c": "Peru", "r": "per_lima", "ll": [-12.20333, -75.79917], "ey": 1525, "ly": 2025, "p": 6763},
  {"key": "Puquian-Peru", "n": "Puquian", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.424, -77.092], "ey": 1525, "ly": 1825, "p": 6762, "al": ["pucquian", "Pucquian"]},
  {"key": "Somate Bajo-Peru", "n": "Somate Bajo", "c": "Peru", "r": "per_piura", "ll": [-4.7449, -80.534], "ey": 1525, "ly": 2017, "p": 6759, "al": ["somate", "Somate"]},
  {"key": "Santiago de Tuna-Peru", "n": "Santiago de Tuna", "c": "Peru", "r": "per_lima", "ll": [-11.98389, -76.52528], "ey": 1525, "ly": 2025, "p": 6757, "al": ["tuna", "Tuna"]},
  {"key": "Chapimarca-Peru", "n": "Chapimarca", "c": "Peru", "r": "per_apurimac", "ll": [-13.975, -73.065], "ey": 1525, "ly": 2025, "p": 6754},
  {"key": "Huañec-Peru", "n": "Huañec", "c": "Peru", "r": "per_lima", "ll": [-12.29389, -76.13861], "ey": 1525, "ly": 2025, "p": 6754, "al": ["san joaquín", "huanic", "San Joaquín"]},
  {"key": "Cayapas Viejo-Ecuador", "n": "Cayapas Viejo", "c": "Ecuador", "r": "vng_guayaquil_esmeraldas", "ll": [0.742, -78.668], "ey": 1525, "ly": 1830, "p": 6753, "al": ["cayapas", "Cayapas"]},
  {"key": "El Hato-Venezuela", "n": "El Hato", "c": "Venezuela", "r": "ven_falcon", "ll": [11.95, -69.83833], "ey": 1850, "ly": 2025, "p": 6748},
  {"key": "Salabina-Argentina", "n": "Salabina", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.804, -63.43], "ey": 1536, "ly": 1830, "p": 6748, "al": ["salavina", "Salavina"]},
  {"key": "General Daniel Cerri-Argentina", "n": "General Daniel Cerri", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-38.7148, -62.40115], "ey": 1850, "ly": 2010, "p": 6745},
  {"key": "Espiritu Santo Caguan-Colombia", "n": "Espiritu Santo Caguan", "c": "Colombia", "r": "vng_llanos_caguan", "ll": [1.383, -74.811], "ey": 1590, "ly": 1676, "p": 6745},
  {"key": "Leoncio Prado-Peru", "n": "Leoncio Prado", "c": "Peru", "r": "per_lima", "ll": [-11.06111, -76.93028], "ey": 1525, "ly": 2025, "p": 6744, "al": ["santa cruz", "Santa Cruz"]},
  {"key": "Galicia Parte Alta-Colombia", "n": "Galicia Parte Alta", "c": "Colombia", "r": "col_antioquia", "ll": [6.1944, -75.35982], "ey": 1525, "ly": 2018, "p": 6743, "al": ["galicia parte baja", "mosca", "Galicia Parte Baja"]},
  {"key": "San Pedro de Huacarpana-Peru", "n": "San Pedro de Huacarpana", "c": "Peru", "r": "per_lima", "ll": [-13.04917, -75.64778], "ey": 1525, "ly": 2025, "p": 6742, "al": ["huacar", "Huacar"]},
  {"key": "Vitis-Peru", "n": "Vitis", "c": "Peru", "r": "per_lima", "ll": [-12.22389, -75.80806], "ey": 1525, "ly": 2025, "p": 6742},
  {"key": "Pecaya-Venezuela", "n": "Pecaya", "c": "Venezuela", "r": "ven_falcon", "ll": [11.07652, -69.8659], "ey": 1538, "ly": 2025, "p": 6740, "al": ["toroy", "Toroy"]},
  {"key": "Chipao-Peru", "n": "Chipao", "c": "Peru", "r": "per_ayacucho", "ll": [-14.36583, -73.87611], "ey": 1525, "ly": 2025, "p": 6740, "al": ["chipau", "Chipau"]},
  {"key": "Malchingi-Ecuador", "n": "Malchingi", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [0.044, -78.349], "ey": 1525, "ly": 1830, "p": 6737},
  {"key": "Iscara-Bolivia", "n": "Iscara", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.836, -68.248], "ey": 1525, "ly": 1825, "p": 6736},
  {"key": "Antilla (per_apurimac)-Peru", "n": "Antilla", "c": "Peru", "r": "per_apurimac", "ll": [-14.3272, -72.9667], "ey": 1525, "ly": 2017, "p": 6734},
  {"key": "Ocoyo-Peru", "n": "Ocoyo", "c": "Peru", "r": "per_huancavelica", "ll": [-14.00806, -75.0225], "ey": 1525, "ly": 2025, "p": 6734},
  {"key": "Freirina (chl_region_de_atacama)-Chile", "n": "Freirina", "c": "Chile", "r": "chl_region_de_atacama", "ll": [-28.50992, -71.08109], "ey": 1752, "ly": 2017, "p": 6734, "al": ["santa rosa", "Santa Rosa"]},
  {"key": "Huanza-Peru", "n": "Huanza", "c": "Peru", "r": "per_lima", "ll": [-11.65611, -76.50361], "ey": 1525, "ly": 2025, "p": 6733, "al": ["carampoma", "carampona", "Carampoma"]},
  {"key": "Huaycho-Peru_2", "n": "Huaycho", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.17, -76.994], "ey": 1525, "ly": 1825, "p": 6733},
  {"key": "Cosma-Peru", "n": "Cosma", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-9.955, -76.651], "ey": 500, "ly": 1825, "p": 6732, "al": ["cashapampa", "agushpampa", "aparan punta"]},
  {"key": "Juan Espinoza Medrano-Peru", "n": "Juan Espinoza Medrano", "c": "Peru", "r": "per_apurimac", "ll": [-14.42833, -72.915], "ey": 1525, "ly": 2025, "p": 6731, "al": ["mollebamba", "mollobamba", "Mollebamba"]},
  {"key": "Picamaran A-Peru", "n": "Picamaran A", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.772, -76.052], "ey": 1525, "ly": 1825, "p": 6731},
  {"key": "Obrajillo-Peru", "n": "Obrajillo", "c": "Peru", "r": "per_lima", "ll": [-11.4522, -76.6204], "ey": 1525, "ly": 2017, "p": 6730, "al": ["san miguel", "obragillo", "San Miguel"]},
  {"key": "Tupigachi-Ecuador", "n": "Tupigachi", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.0907, -78.19073], "ey": 1525, "ly": 2025, "p": 6729},
  {"key": "Chamas-Peru", "n": "Chamas", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.434, -77.171], "ey": 1525, "ly": 1825, "p": 6728},
  {"key": "Ignacio Briceño-Venezuela", "n": "Ignacio Briceño", "c": "Venezuela", "r": "ven_barinas", "ll": [7.64778, -70.41444], "ey": 1850, "ly": 2025, "p": 6726},
  {"key": "Juan Millán-Venezuela", "n": "Juan Millán", "c": "Venezuela", "r": "ven_delta_amacuro", "ll": [9.24845, -61.44743], "ey": 1920, "ly": 2025, "p": 6725},
  {"key": "Antawala - Llaqtamarka-Peru", "n": "Antawala - Llaqtamarka", "c": "Peru", "r": "inca_antisuyu", "ll": [-13.09531, -72.03836], "ey": -1000, "ly": 1530, "p": 6722, "al": ["machu was", "waka wasi-trapiche", "Machu Was"]},
  {"key": "Santiago de Chocorvos-Peru", "n": "Santiago de Chocorvos", "c": "Peru", "r": "per_huancavelica", "ll": [-13.82528, -75.2575], "ey": 1525, "ly": 2025, "p": 6716, "al": ["santiago", "Santiago"]},
  {"key": "Ihuari-Peru", "n": "Ihuari", "c": "Peru", "r": "per_lima", "ll": [-11.18861, -76.95194], "ey": 1525, "ly": 2025, "p": 6715, "al": ["iguari", "Iguari"]},
  {"key": "Malay-Peru", "n": "Malay", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.812, -76.813], "ey": 1525, "ly": 1825, "p": 6712, "al": ["malsay", "Malsay"]},
  {"key": "Huamantanga-Peru", "n": "Huamantanga", "c": "Peru", "r": "per_lima", "ll": [-11.49917, -76.74944], "ey": 1525, "ly": 2025, "p": 6710},
  {"key": "Marco-Peru_2", "n": "Marco", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.439, -76.789], "ey": 1525, "ly": 1825, "p": 6710, "al": ["malco", "Malco"]},
  {"key": "Rocafuerte (ecu_esmeraldas)-Ecuador", "n": "Rocafuerte", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.94091, -79.38335], "ey": 1850, "ly": 2025, "p": 6706},
  {"key": "Andabamba-Peru", "n": "Andabamba", "c": "Peru", "r": "per_huancavelica", "ll": [-12.69361, -74.62333], "ey": 1525, "ly": 2025, "p": 6702},
  {"key": "Raclla-Peru", "n": "Raclla", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.49, -77.492], "ey": 1525, "ly": 1825, "p": 6702},
  {"key": "Sarayca-Peru", "n": "Sarayca", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-14.21, -73.134], "ey": 1525, "ly": 1825, "p": 6702, "al": ["saraico", "Saraico"]},
  {"key": "Tignamar-Chile", "n": "Tignamar", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-18.581, -69.494], "ey": 1525, "ly": 1825, "p": 6701, "al": ["tignabar", "tignabor", "Tignabar"]},
  {"key": "La Salina-Colombia", "n": "La Salina", "c": "Colombia", "r": "col_boyaca", "ll": [6.12776, -72.33498], "ey": 1525, "ly": 2025, "p": 6700, "al": ["las salinas", "Las Salinas"]},
  {"key": "Chota-Peru_2", "n": "Chota", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-7.934, -78.485], "ey": 1542, "ly": 1825, "p": 6698},
  {"key": "El Porvenir (col_valle_del_cauca)-Colombia", "n": "El Porvenir", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.8915, -76.34284], "ey": 1525, "ly": 2018, "p": 6696, "al": ["la palomera", "puerto bertin", "punta brava"]},
  {"key": "Pachaconas-Peru", "n": "Pachaconas", "c": "Peru", "r": "per_apurimac", "ll": [-14.22333, -73.01639], "ey": 1525, "ly": 2025, "p": 6694, "al": ["pachacona", "Pachacona"]},
  {"key": "Tapairihua-Peru", "n": "Tapairihua", "c": "Peru", "r": "per_apurimac", "ll": [-14.14139, -73.14028], "ey": 1525, "ly": 2025, "p": 6692, "al": ["tapayrihua", "Tapayrihua"]},
  {"key": "Uchuymarca-Peru", "n": "Uchuymarca", "c": "Peru", "r": "per_ayacucho", "ll": [-14.6562, -74.6964], "ey": 1525, "ly": 2017, "p": 6691},
  {"key": "Colonia-Peru", "n": "Colonia", "c": "Peru", "r": "per_lima", "ll": [-12.63389, -75.89028], "ey": 1525, "ly": 2025, "p": 6690, "al": ["pampas", "Pampas"]},
  {"key": "Mesa de Caloto-Colombia", "n": "Mesa de Caloto", "c": "Colombia", "r": "col_cauca", "ll": [2.7911, -76.06099], "ey": 1525, "ly": 2018, "p": 6682, "al": ["vuila", "guila", "huila"]},
  {"key": "Casabamba-Peru_2", "n": "Casabamba", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.531, -73.431], "ey": 1525, "ly": 1825, "p": 6682},
  {"key": "Huanchay-Peru", "n": "Huanchay", "c": "Peru", "r": "per_ancash", "ll": [-9.72361, -77.81861], "ey": 1525, "ly": 2025, "p": 6677},
  {"key": "Mariscal Sucre-Ecuador", "n": "Mariscal Sucre", "c": "Ecuador", "r": "ecu_guayas", "ll": [-2.07979, -79.50821], "ey": 1850, "ly": 2025, "p": 6673},
  {"key": "Uyumbicho-Ecuador", "n": "Uyumbicho", "c": "Ecuador", "r": "ecu_pichincha", "ll": [-0.41422, -78.51853], "ey": 1850, "ly": 2025, "p": 6673},
  {"key": "Coloya-Colombia", "n": "Coloya", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [4.884, -74.933], "ey": 1525, "ly": 1830, "p": 6672},
  {"key": "Chapío-Colombia", "n": "Chapío", "c": "Colombia", "r": "col_cauca", "ll": [2.38145, -76.44438], "ey": 1525, "ly": 2018, "p": 6671, "al": ["purace", "purase", "Purace"]},
  {"key": "Luis Cordero-Ecuador", "n": "Luis Cordero", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.74221, -78.81541], "ey": 1525, "ly": 2025, "p": 6671, "al": ["san marcos", "San Marcos"]},
  {"key": "El Pedral-Colombia", "n": "El Pedral", "c": "Colombia", "r": "col_santander", "ll": [7.22704, -73.84532], "ey": 1525, "ly": 2018, "p": 6667, "al": ["pedral", "Pedral"]},
  {"key": "Pitic-Peru", "n": "Pitic", "c": "Peru", "r": "per_apurimac", "ll": [-14.0509, -72.0753], "ey": 1525, "ly": 2017, "p": 6667, "al": ["pitij", "Pitij"]},
  {"key": "Tomollo Beach-Peru", "n": "Tomollo Beach", "c": "Peru", "r": "inca_collasuyu", "ll": [-18.12525, -70.7055], "ey": -2000, "ly": 1530, "p": 6667, "al": ["amapaya", "los hornos", "Amapaya"]},
  {"key": "Huantar-Peru", "n": "Huantar", "c": "Peru", "r": "per_ancash", "ll": [-9.45194, -77.17667], "ey": 1525, "ly": 2025, "p": 6666, "al": ["huántar", "Huántar"]}
]

# 1. Search local QUIPU settlements json files
base = "histmap/1.data_raw/population_regional/QUIPU"
files = glob.glob(os.path.join(base, "**", "*_settlements.json"), recursive=True)
local_hits = {item["key"]: [] for item in INPUT}

for fpath in files:
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            records = data.get("settlements", data.get("data", []))
            if not records and all(isinstance(v, dict) for v in data.values()):
                records = list(data.values())
        elif isinstance(data, list):
            records = data
        else:
            continue
        for rec in records:
            if not isinstance(rec, dict):
                continue
            lat = rec.get("lat") or rec.get("latitude") or (rec.get("coords") or [None, None])[0]
            lng = rec.get("lng") or rec.get("lon") or rec.get("longitude") or (rec.get("coords") or [None, None])[1]
            rname = (rec.get("name") or rec.get("settlement") or "").lower()
            for item in INPUT:
                if lat is not None and lng is not None:
                    try:
                        if abs(float(lat) - item["ll"][0]) < 0.02 and abs(float(lng) - item["ll"][1]) < 0.02:
                            local_hits[item["key"]].append({
                                "file": os.path.basename(fpath),
                                "name": rec.get("name"),
                                "notes": rec.get("notes") or rec.get("source_note") or rec.get("description") or "",
                                "foundation_year": rec.get("foundation_year"),
                                "earliest_year": rec.get("earliest_year"),
                                "historical_names": rec.get("historical_names"),
                                "other_names": rec.get("other_names"),
                                "region": rec.get("subregion") or rec.get("region") or rec.get("admin1"),
                                "sources": rec.get("sources") or rec.get("source"),
                                "years": sorted([k for k in (rec.get("populations") or rec.get("years") or {}).keys()])[:5] if isinstance(rec.get("populations") or rec.get("years"), dict) else None
                            })
                    except Exception:
                        pass
    except Exception as e:
        pass

with open("tests/local_hits_020.json", "w", encoding="utf-8") as f:
    json.dump(local_hits, f, ensure_ascii=False, indent=2)

print("Saved local_hits_020.json. Items with hits:", sum(1 for v in local_hits.values() if v))
