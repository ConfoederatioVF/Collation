import json
import glob
import os

INPUT_DATA = [
  {"key": "Matara (vp_intendencia_cusco)-Peru", "n": "Matara", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-14.351, -72.918], "ey": 1525, "ly": 1825, "p": 7245},
  {"key": "Pachangara-Peru", "n": "Pachangara", "c": "Peru", "r": "per_lima", "ll": [-10.81111, -76.875], "ey": 1525, "ly": 2025, "p": 7244, "al": ["churin", "Churin"]},
  {"key": "Ciudad de Nutrias-Venezuela", "n": "Ciudad de Nutrias", "c": "Venezuela", "r": "ven_barinas", "ll": [8.09444, -69.30389], "ey": 1774, "ly": 2025, "p": 7241, "al": ["nutrias", "Nutrias"]},
  {"key": "Huchupampa-Peru", "n": "Huchupampa", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.713, -76.549], "ey": 1525, "ly": 1825, "p": 7240},
  {"key": "San Cristobal Sora-Chile", "n": "San Cristobal Sora", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-18.349, -69.873], "ey": 1525, "ly": 1825, "p": 7238},
  {"key": "Soquiarcancha-Peru", "n": "Soquiarcancha", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.032, -76.409], "ey": 1525, "ly": 1825, "p": 7236, "al": ["soquiacancha", "Soquiacancha"]},
  {"key": "Campamento Pampa Lagunillas-Peru", "n": "Campamento Pampa Lagunillas", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.38722, -72.31325], "ey": 500, "ly": 1530, "p": 7236, "al": ["campamento litico quebrada crespon", "campamento quebrada crespon", "quebrada los molles"]},
  {"key": "Cajacay-Peru", "n": "Cajacay", "c": "Peru", "r": "per_ancash", "ll": [-10.15528, -77.43972], "ey": 1525, "ly": 2025, "p": 7235},
  {"key": "Wiracochapampa-Peru", "n": "Wiracochapampa", "c": "Peru", "r": "per_la_libertad", "ll": [-7.7748, -78.0477], "ey": 1542, "ly": 2017, "p": 7232, "al": ["payamarca", "puente piedra", "pumapampa"]},
  {"key": "Tapacocha-Peru", "n": "Tapacocha", "c": "Peru", "r": "per_ancash", "ll": [-10.01028, -77.56917], "ey": 1525, "ly": 2025, "p": 7231},
  {"key": "Yupan-Peru", "n": "Yupan", "c": "Peru", "r": "per_ancash", "ll": [-8.61444, -77.96861], "ey": 1525, "ly": 2025, "p": 7231, "al": ["yupán", "Yupán"]},
  {"key": "Oñamal-Ecuador", "n": "Oñamal", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.213, -78.954], "ey": 1525, "ly": 1830, "p": 7231},
  {"key": "Chauca-Peru", "n": "Chauca", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.812, -76.556], "ey": 1525, "ly": 1825, "p": 7231, "al": ["chauta", "Chauta"]},
  {"key": "Borojo-Venezuela", "n": "Borojo", "c": "Venezuela", "r": "ven_falcon", "ll": [11.06667, -70.80278], "ey": 1538, "ly": 2025, "p": 7230},
  {"key": "Quiparacra-Peru", "n": "Quiparacra", "c": "Peru", "r": "per_pasco", "ll": [-10.6425, -75.8698], "ey": 1525, "ly": 2017, "p": 7229},
  {"key": "Cormo-Peru", "n": "Cormo", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.282, -76.731], "ey": 1525, "ly": 1825, "p": 7229},
  {"key": "El Valle-Peru", "n": "El Valle", "c": "Peru", "r": "per_san_martin", "ll": [-7.5768, -76.7952], "ey": 1525, "ly": 2017, "p": 7226, "al": ["san buenaventura del valle", "San Buenaventura del Valle"]},
  {"key": "Sunicancha-Peru", "n": "Sunicancha", "c": "Peru", "r": "per_lima", "ll": [-12.047, -76.3744], "ey": 1525, "ly": 2017, "p": 7225, "al": ["sinicancha", "Sinicancha"]},
  {"key": "Chullisana-Peru", "n": "Chullisana", "c": "Peru", "r": "per_apurimac", "ll": [-13.813, -73.6265], "ey": 1525, "ly": 2017, "p": 7221, "al": ["chulisana", "Chulisana"]},
  {"key": "Cocas (per_ayacucho)-Peru", "n": "Cocas", "c": "Peru", "r": "per_ayacucho", "ll": [-13.6086, -74.4739], "ey": 1525, "ly": 2017, "p": 7221},
  {"key": "Santa Ana (per_ayacucho)-Peru", "n": "Santa Ana", "c": "Peru", "r": "per_ayacucho", "ll": [-14.747, -74.1211], "ey": 1525, "ly": 2017, "p": 7221},
  {"key": "Huarmacas-Peru", "n": "Huarmacas", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-5.704, -79.506], "ey": 1525, "ly": 1830, "p": 7221, "al": ["huarmaca", "Huarmaca"]},
  {"key": "Coto-Peru", "n": "Coto", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.208, -76.774], "ey": 1525, "ly": 1825, "p": 7221, "al": ["cotoc", "Cotoc"]},
  {"key": "San Andrés de Tupicocha-Peru", "n": "San Andrés de Tupicocha", "c": "Peru", "r": "per_lima", "ll": [-12.00222, -76.47472], "ey": 1525, "ly": 2025, "p": 7219, "al": ["tupicocha", "Tupicocha"]},
  {"key": "Cayara (per_apurimac)-Peru", "n": "Cayara", "c": "Peru", "r": "per_apurimac", "ll": [-13.563, -73.7241], "ey": 1525, "ly": 2017, "p": 7216, "al": ["cayera", "morochuco", "san lorenzo"]},
  {"key": "San Juan (per_ica)-Peru", "n": "San Juan", "c": "Peru", "r": "per_ica", "ll": [-13.20389, -75.63444], "ey": 1525, "ly": 2025, "p": 7216, "al": ["huanac", "huanaco", "Huanac"]},
  {"key": "Huaroquin-Peru", "n": "Huaroquin", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.273, -76.702], "ey": 1525, "ly": 1825, "p": 7214},
  {"key": "San José de Saguaz-Venezuela", "n": "San José de Saguaz", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.39314, -69.99611], "ey": 1850, "ly": 2025, "p": 7213},
  {"key": "Chalhuanca-Peru", "n": "Chalhuanca", "c": "Peru", "r": "per_apurimac", "ll": [-14.29444, -73.24472], "ey": 1525, "ly": 2025, "p": 7212, "al": ["chaluanca", "chuquinga", "paraica"]},
  {"key": "Chupas-Peru", "n": "Chupas", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.007, -76.313], "ey": 1525, "ly": 1825, "p": 7212},
  {"key": "El Batey-Venezuela", "n": "El Batey", "c": "Venezuela", "r": "ven_merida", "ll": [9.15833, -71.13111], "ey": 1850, "ly": 2025, "p": 7211},
  {"key": "Tambillo (vp_intendencia_lima)-Peru", "n": "Tambillo", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-13.721, -75.425], "ey": 1525, "ly": 1825, "p": 7211, "al": ["tavillo", "Tavillo"]},
  {"key": "Cabana (per_la_libertad)-Peru", "n": "Cabana", "c": "Peru", "r": "per_la_libertad", "ll": [-8.39306, -78.00889], "ey": 1525, "ly": 2025, "p": 7210},
  {"key": "Yauca-Peru", "n": "Yauca", "c": "Peru", "r": "per_arequipa", "ll": [-15.66194, -74.52722], "ey": -2000, "ly": 2025, "p": 7210, "al": ["tanaka", "Tanaka"]},
  {"key": "Nanegal-Ecuador", "n": "Nanegal", "c": "Ecuador", "r": "ecu_pichincha", "ll": [0.12325, -78.6332], "ey": 1525, "ly": 2025, "p": 7208},
  {"key": "Laraos-Peru", "n": "Laraos", "c": "Peru", "r": "per_lima", "ll": [-12.34667, -75.78583], "ey": 1525, "ly": 2025, "p": 7207},
  {"key": "Colca (per_huancavelica)-Peru", "n": "Colca", "c": "Peru", "r": "per_huancavelica", "ll": [-12.5207, -74.6721], "ey": 1525, "ly": 2017, "p": 7204, "al": ["santa clara cosme", "Santa Clara Cosme"]},
  {"key": "Pindilig-Ecuador", "n": "Pindilig", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.58832, -78.72531], "ey": 1525, "ly": 2025, "p": 7202, "al": ["pendeleg", "pendetel", "Pendeleg"]},
  {"key": "Umagata-Chile", "n": "Umagata", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-18.57, -69.778], "ey": 1525, "ly": 1825, "p": 7202, "al": ["umapata", "Umapata"]},
  {"key": "San Juan Bautista Tabacundo-Ecuador", "n": "San Juan Bautista Tabacundo", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [0.046, -78.201], "ey": 1525, "ly": 1830, "p": 7200},
  {"key": "Cupe-Peru", "n": "Cupe", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-15.297, -73.013], "ey": 1525, "ly": 1825, "p": 7200, "al": ["cupi", "Cupi"]},
  {"key": "Sumara-Peru", "n": "Sumara", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.619, -72.269], "ey": 1542, "ly": 1825, "p": 7197},
  {"key": "Checras-Peru", "n": "Checras", "c": "Peru", "r": "per_lima", "ll": [-10.91806, -76.82556], "ey": 1525, "ly": 2025, "p": 7196, "al": ["maray", "Maray"]},
  {"key": "Oña-Ecuador", "n": "Oña", "c": "Ecuador", "r": "ecu_azuay", "ll": [-3.49499, -79.10841], "ey": 1525, "ly": 2025, "p": 7195},
  {"key": "Cocharcas-Peru", "n": "Cocharcas", "c": "Peru", "r": "per_apurimac", "ll": [-13.61056, -73.74139], "ey": 1525, "ly": 2025, "p": 7194},
  {"key": "Silque-Peru", "n": "Silque", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.233, -72.333], "ey": 1542, "ly": 1825, "p": 7194},
  {"key": "Ilabaya-Peru", "n": "Ilabaya", "c": "Peru", "r": "per_tacna", "ll": [-17.41806, -70.51306], "ey": 1525, "ly": 2025, "p": 7190, "ex": [{"date": "1961.1.1", "name": "Ilabaya"}]},
  {"key": "Llaguen-Peru", "n": "Llaguen", "c": "Peru", "r": "per_la_libertad", "ll": [-7.7254, -78.7396], "ey": 1525, "ly": 2017, "p": 7189, "al": ["llaquen", "Llaquen"]},
  {"key": "Arirahua-Peru", "n": "Arirahua", "c": "Peru", "r": "vp_intendencia_arequipa", "ll": [-15.664, -72.937], "ey": 1525, "ly": 1825, "p": 7189},
  {"key": "Jaria-Peru", "n": "Jaria", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.296, -76.142], "ey": 1542, "ly": 1825, "p": 7189, "al": ["jarilla", "Jarilla"]},
  {"key": "Cajabamba-Ecuador", "n": "Cajabamba", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-1.701, -78.77], "ey": 1525, "ly": 1830, "p": 7187, "ex": [{"date": "1941.1.1", "name": "Cajabamba"}], "al": ["cicalpa", "sicalpa", "zicalpa"]},
  {"key": "Poconchile-Chile", "n": "Poconchile", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-18.452, -70.067], "ey": 1525, "ly": 1825, "p": 7181},
  {"key": "Hojas Anchas-Colombia", "n": "Hojas Anchas", "c": "Colombia", "r": "col_antioquia", "ll": [5.51365, -75.64844], "ey": 1525, "ly": 2018, "p": 7180, "al": ["la montaña", "La Montaña"]},
  {"key": "San Pedro de Casta-Peru", "n": "San Pedro de Casta", "c": "Peru", "r": "per_lima", "ll": [-11.75889, -76.59639], "ey": 1525, "ly": 2025, "p": 7180},
  {"key": "Pichacay-Ecuador", "n": "Pichacay", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.85, -78.985], "ey": 1525, "ly": 1830, "p": 7177},
  {"key": "San Lorenzo Tarapaca-Chile", "n": "San Lorenzo Tarapaca", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.925, -69.511], "ey": 1525, "ly": 1825, "p": 7176},
  {"key": "Los Cardales-Argentina", "n": "Los Cardales", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-34.32917, -58.98861], "ey": 1850, "ly": 2010, "p": 7174},
  {"key": "Cachuy-Peru", "n": "Cachuy", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.719, -75.914], "ey": 1525, "ly": 1825, "p": 7173},
  {"key": "Chocos-Peru", "n": "Chocos", "c": "Peru", "r": "per_lima", "ll": [-12.91444, -75.86278], "ey": 1525, "ly": 2025, "p": 7171},
  {"key": "Limoncocha-Ecuador", "n": "Limoncocha", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [-0.41001, -76.6235], "ey": 1752, "ly": 2025, "p": 7169, "al": ["trinidad de capucuy de encabellados", "capacui", "capicui"]},
  {"key": "Colcabamba (per_ancash)-Peru", "n": "Colcabamba", "c": "Peru", "r": "per_ancash", "ll": [-9.59472, -77.80861], "ey": 1525, "ly": 2025, "p": 7169, "al": ["colcahuanca", "Colcahuanca"]},
  {"key": "Chaca-Chile", "n": "Chaca", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-18.808, -70.158], "ey": 1525, "ly": 1825, "p": 7169},
  {"key": "Sabana Libre-Venezuela", "n": "Sabana Libre", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.34167, -70.64611], "ey": 1850, "ly": 2025, "p": 7168},
  {"key": "Tancayllo-Peru", "n": "Tancayllo", "c": "Peru", "r": "per_apurimac", "ll": [-13.6334, -73.6894], "ey": 500, "ly": 2017, "p": 7167, "al": ["uracmarca", "uranmarca", "incaraqay"]},
  {"key": "Bomboíza-Ecuador", "n": "Bomboíza", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-3.43825, -78.53851], "ey": 1920, "ly": 2025, "p": 7166},
  {"key": "Tibillo-Peru", "n": "Tibillo", "c": "Peru", "r": "per_ica", "ll": [-14.09389, -75.17167], "ey": 1525, "ly": 2025, "p": 7166, "al": ["tivillo", "truillo", "Tivillo"]},
  {"key": "Jesús María-Ecuador", "n": "Jesús María", "c": "Ecuador", "r": "ecu_guayas", "ll": [-2.609, -79.48775], "ey": 1850, "ly": 2025, "p": 7165},
  {"key": "Tantarica-Peru", "n": "Tantarica", "c": "Peru", "r": "per_cajamarca", "ll": [-7.30056, -78.93306], "ey": -2000, "ly": 2025, "p": 7165, "al": ["catan", "san francisco de catan", "arqueológico chacladen"]},
  {"key": "Llacllin-Peru", "n": "Llacllin", "c": "Peru", "r": "per_ancash", "ll": [-10.06917, -77.62167], "ey": 1525, "ly": 2025, "p": 7164, "al": ["llacllín", "Llacllín"]},
  {"key": "Menchiquejo-Colombia", "n": "Menchiquejo", "c": "Colombia", "r": "col_magdalena", "ll": [9.22445, -74.34936], "ey": 1611, "ly": 2018, "p": 7158, "al": ["san juan menchiquejo", "menchiguejo", "menebiquejo"]},
  {"key": "Alto Salaverry-Peru", "n": "Alto Salaverry", "c": "Peru", "r": "per_la_libertad", "ll": [-8.185, -78.9852], "ey": 1850, "ly": 2017, "p": 7156},
  {"key": "Quispas-Peru", "n": "Quispas", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-10.161, -76.737], "ey": 1525, "ly": 1825, "p": 7153},
  {"key": "San Pedro-Peru", "n": "San Pedro", "c": "Peru", "r": "per_ayacucho", "ll": [-14.76694, -74.09778], "ey": 1525, "ly": 2025, "p": 7151},
  {"key": "Collata-Peru_2", "n": "Collata", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.696, -76.681], "ey": 1525, "ly": 1825, "p": 7149},
  {"key": "Paccho-Peru", "n": "Paccho", "c": "Peru", "r": "per_lima", "ll": [-10.9575, -76.93333], "ey": 1525, "ly": 2025, "p": 7147, "al": ["pacho", "Pacho"]},
  {"key": "Chorrera-Colombia_2", "n": "Chorrera", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.55136, -78.6776], "ey": 1000, "ly": 1500, "p": 7147, "al": ["astorga", "estero tangareal", "ica"]},
  {"key": "Huantan-Peru", "n": "Huantan", "c": "Peru", "r": "per_lima", "ll": [-12.45639, -75.81167], "ey": 1525, "ly": 2025, "p": 7144},
  {"key": "Urcuquí-Ecuador", "n": "Urcuquí", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.41754, -78.16746], "ey": 1525, "ly": 2025, "p": 7140, "al": ["urcuqui", "Urcuqui"]},
  {"key": "Pacatnamu-Peru", "n": "Pacatnamu", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.30962, -79.58192], "ey": 600, "ly": 1530, "p": 7140, "al": ["dos cabezas", "pacatnamu a", "pacatnamú"]},
  {"key": "Santa Rosa de la Cañada-Colombia", "n": "Santa Rosa de la Cañada", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [2.585, -76.005], "ey": 1525, "ly": 1830, "p": 7131},
  {"key": "Matara (vp_intendencia_lima)-Peru", "n": "Matara", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.224, -76.443], "ey": 1525, "ly": 1825, "p": 7130},
  {"key": "San Salvador de Osno Alta-Peru", "n": "San Salvador de Osno Alta", "c": "Peru", "r": "per_ayacucho", "ll": [-12.9127, -74.0027], "ey": 1525, "ly": 2017, "p": 7128, "al": ["san salvador osno", "vicos", "San Salvador Osno"]},
  {"key": "Maray-Peru_2", "n": "Maray", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.719, -73.63], "ey": 1525, "ly": 1825, "p": 7127, "al": ["yasaray", "Yasaray"]},
  {"key": "San Damian-Peru", "n": "San Damian", "c": "Peru", "r": "per_lima", "ll": [-12.01778, -76.39194], "ey": 1525, "ly": 2025, "p": 7125, "al": ["san damián", "San Damián"]},
  {"key": "Niepos-Peru", "n": "Niepos", "c": "Peru", "r": "per_cajamarca", "ll": [-6.92667, -79.13], "ey": 1525, "ly": 2025, "p": 7124, "al": ["ñepos", "nepos", "nepus"]},
  {"key": "Andagua-Peru", "n": "Andagua", "c": "Peru", "r": "per_arequipa", "ll": [-15.49889, -72.35611], "ey": 1525, "ly": 2025, "p": 7121, "al": ["andahua", "Andahua"]},
  {"key": "Huayan-Peru", "n": "Huayan", "c": "Peru", "r": "per_ancash", "ll": [-9.87528, -77.70833], "ey": 1525, "ly": 2025, "p": 7121, "al": ["huayán", "Huayán"]},
  {"key": "Ramón Ignacio Méndez (ven_merida)-Venezuela", "n": "Ramón Ignacio Méndez", "c": "Venezuela", "r": "ven_merida", "ll": [7.68463, -71.39691], "ey": 1850, "ly": 2025, "p": 7120},
  {"key": "Huascoy-Peru", "n": "Huascoy", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.29, -76.761], "ey": 1525, "ly": 1825, "p": 7120},
  {"key": "Santiago Tucuma-Peru", "n": "Santiago Tucuma", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-12.579, -74.551], "ey": 1525, "ly": 1825, "p": 7120}
]

base = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\QUIPU"

# Load HGIS Indias
with open(os.path.join(base, "_shared", "settlement_sources", "hgis_indias_colonial_raw.json"), encoding="utf-8") as f:
    hgis = json.load(f)["settlements"]

# Index raw_setts by approx coords and name
raw_setts = []
for p in glob.glob(os.path.join(base, "_shared", "settlement_sources", "raw_setts_*.json")):
    with open(p, encoding="utf-8") as f:
        d = json.load(f)["settlements"]
        if isinstance(d, dict):
            for k, v in d.items():
                v["_key"] = k
                raw_setts.append(v)
        elif isinstance(d, list):
            raw_setts.extend(d)

# Also load chapter settlements
chap_matches = {}
for p in glob.glob(os.path.join(base, "*", "*", "*_settlements.json")):
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    setts = d.get("settlements", d) if isinstance(d, dict) else d
    if isinstance(setts, dict):
        for k, v in setts.items():
            chap_matches.setdefault(k, []).append((os.path.basename(p), v))
    elif isinstance(setts, list):
        for v in setts:
            k = v.get("key") or v.get("id") or v.get("name")
            if k:
                chap_matches.setdefault(k, []).append((os.path.basename(p), v))

out = []
for item in INPUT_DATA:
    lat, lng = item["ll"]
    # find nearby hgis
    h_near = []
    for hk, hv in hgis.items():
        c = hv.get("coords")
        if c and abs(c[0]-lat) < 0.05 and abs(c[1]-lng) < 0.05:
            h_near.append({
                "gz_id": hk,
                "name": hv.get("name"),
                "modern_name": hv.get("modern_name"),
                "variants": hv.get("variants"),
                "prov": hv.get("colonial_province"),
                "partido": hv.get("colonial_partido"),
                "cat": hv.get("categoria"),
                "start": hv.get("start_year"),
                "end": hv.get("end_year"),
                "coords": c
            })
    r_near = []
    for rv in raw_setts:
        c = rv.get("coords")
        if c and abs(c[0]-lat) < 0.02 and abs(c[1]-lng) < 0.02:
            r_near.append({
                "key": rv.get("_key") or rv.get("name"),
                "name": rv.get("name"),
                "admin1": rv.get("admin1"),
                "admin2": rv.get("admin2"),
                "other_names": rv.get("other_names"),
                "sources": rv.get("sources"),
                "coords": c
            })
    # Also check chap_matches by coords or name
    c_near = []
    for k, lst in chap_matches.items():
        for fn, v in lst:
            c = v.get("coords")
            if (c and abs(c[0]-lat) < 0.005 and abs(c[1]-lng) < 0.005) or item["n"].lower() == (v.get("name") or "").lower():
                if c and abs(c[0]-lat) < 0.05 and abs(c[1]-lng) < 0.05:
                    c_near.append({"file": fn, "key": k, "name": v.get("name"), "subregion": v.get("subregion"), "other_names": v.get("other_names"), "sources": v.get("sources"), "notes": v.get("notes")})
    out.append({
        "input_key": item["key"],
        "n": item["n"],
        "c": item["c"],
        "r": item["r"],
        "ll": item["ll"],
        "ey": item["ey"],
        "ly": item["ly"],
        "hgis": h_near,
        "raw": r_near[:3],
        "chap": c_near[:4]
    })

with open(r"f:\Active Projects\Project 1509 - SVEA\tests\chunk016_local_matches.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("Wrote", len(out), "entries. HGIS matches:", sum(1 for x in out if x["hgis"]), "Raw matches:", sum(1 for x in out if x["raw"]), "Chap matches:", sum(1 for x in out if x["chap"]))
