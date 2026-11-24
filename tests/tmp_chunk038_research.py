import glob
import json
import math
import os
import time
import urllib.parse
import urllib.request

SETTLEMENTS = [
  {"key": "Conima-Peru", "n": "Conima", "c": "Peru", "r": "per_puno", "ll": [-15.45778, -69.43778], "ey": 1525, "ly": 2025, "p": 4421},
  {"key": "Villa Ibáñez-Argentina", "n": "Villa Ibáñez", "c": "Argentina", "r": "arg_san_juan", "ll": [-31.46594, -68.73533], "ey": 1850, "ly": 2010, "p": 4421},
  {"key": "Matituy-Colombia", "n": "Matituy", "c": "Colombia", "r": "col_narino", "ll": [1.37135, -77.33667], "ey": 1525, "ly": 2018, "p": 4418},
  {"key": "Songo-Bolivia", "n": "Songo", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-15.723, -68.701], "ey": 1525, "ly": 1825, "p": 4418},
  {"key": "Pilaló-Ecuador", "n": "Pilaló", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-0.99523, -79.00839], "ey": 1525, "ly": 2025, "p": 4417, "al": ["pilalo", "pila-halo", "pilahalo"]},
  {"key": "Pampa Hermosa (per_san_martin)-Peru", "n": "Pampa Hermosa", "c": "Peru", "r": "per_san_martin", "ll": [-6.1091, -76.2705], "ey": 1920, "ly": 2017, "p": 4417, "al": ["alianza", "Alianza"]},
  {"key": "Pumachahuin-Peru", "n": "Pumachahuin", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.82819, -76.30306], "ey": 0, "ly": 1530, "p": 4417, "al": ["huancamarca", "oligas", "pintushgragra"]},
  {"key": "Chacra de La Merced-Argentina", "n": "Chacra de La Merced", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.40767, -64.06478], "ey": 80, "ly": 1500, "p": 4417},
  {"key": "Laguna San Fel-Argentina", "n": "Laguna San Fel", "c": "Argentina", "r": "sc_pampas_salado_colorado", "ll": [-34.7318, -64.864], "ey": 80, "ly": 1500, "p": 4417},
  {"key": "Santos de Abelgas-Venezuela", "n": "Santos de Abelgas", "c": "Venezuela", "r": "ven_delta_amacuro", "ll": [8.81952, -61.30478], "ey": 1920, "ly": 2025, "p": 4416},
  {"key": "Santa Rosa de Pilaguin-Ecuador", "n": "Santa Rosa de Pilaguin", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-1.282, -78.664], "ey": 1525, "ly": 1830, "p": 4415},
  {"key": "Medianía-Peru", "n": "Medianía", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.62121, -79.98963], "ey": 0, "ly": 1530, "p": 4415, "al": ["huaca blanca chica", "huaca blanca grande", "huaca grande"]},
  {"key": "Pampa Tolan-Peru", "n": "Pampa Tolan", "c": "Peru", "r": "inca_collasuyu", "ll": [-15.15153, -70.29303], "ey": 1440, "ly": 1532, "p": 4413},
  {"key": "Ventanillas de Apan-Peru", "n": "Ventanillas de Apan", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.71719, -78.54474], "ey": -2000, "ly": 1530, "p": 4409, "al": ["cerro mayordomo", "la hualanga", "ventanillas de arascorge"]},
  {"key": "Alejandra-Argentina", "n": "Alejandra", "c": "Argentina", "r": "arg_santa_fe", "ll": [-29.90915, -59.82715], "ey": 1850, "ly": 2022, "p": 4408},
  {"key": "Pueblo Nuevo (per_huanuco)-Peru", "n": "Pueblo Nuevo", "c": "Peru", "r": "per_huanuco", "ll": [-9.07861, -76.06056], "ey": 1850, "ly": 2025, "p": 4406},
  {"key": "San José De Morona-Ecuador", "n": "San José De Morona", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-2.881, -77.66763], "ey": 1920, "ly": 2025, "p": 4405},
  {"key": "Cumbaya-Ecuador", "n": "Cumbaya", "c": "Ecuador", "r": "na_pacific_equatorial_valdivia", "ll": [-0.11, -78.26], "ey": -915, "ly": 530, "p": 4404, "al": ["miraflores alto", "santa lucia ed", "Santa Lucia ED"]},
  {"key": "Huaviña-Chile", "n": "Huaviña", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.795, -69.223], "ey": 1525, "ly": 1825, "p": 4403},
  {"key": "Villa del Rosario (arg_entre_rios)-Argentina", "n": "Villa del Rosario", "c": "Argentina", "r": "arg_entre_rios", "ll": [-30.79565, -57.91467], "ey": 1850, "ly": 2022, "p": 4401},
  {"key": "San Francisco Hatillo-Colombia", "n": "San Francisco Hatillo", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [4.668, -76.03], "ey": 1525, "ly": 1830, "p": 4401, "al": ["atilio", "Atilio"]},
  {"key": "Cotacachi-Ecuador_2", "n": "Cotacachi", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [0.3, -78.265], "ey": 1525, "ly": 1830, "p": 4399, "al": ["cotacache", "Cotacache"]},
  {"key": "La Escondida-Argentina", "n": "La Escondida", "c": "Argentina", "r": "arg_chaco", "ll": [-27.10534, -59.44642], "ey": 1900, "ly": 2022, "p": 4397},
  {"key": "La Bomba-Argentina", "n": "La Bomba", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.25825, -64.49447], "ey": 80, "ly": 1500, "p": 4397, "al": ["central nuclear", "soja y metralla", "Central Nuclear"]},
  {"key": "Phc-Colombia", "n": "Phc", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.86136, -75.74257], "ey": -1000, "ly": 1500, "p": 4396, "al": ["terraza 9 c", "yacimiento", "zona b - río cauca - yacimiento 21 - la meseta"]},
  {"key": "recolección superficial-Colombia", "n": "recolección superficial", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.21336, -74.69188], "ey": -3000, "ly": 1500, "p": 4396},
  {"key": "Poroto-Peru", "n": "Poroto", "c": "Peru", "r": "per_la_libertad", "ll": [-8.01139, -78.76778], "ey": 1850, "ly": 2025, "p": 4394},
  {"key": "Nueva Troncal-Ecuador", "n": "Nueva Troncal", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [-0.01454, -77.16016], "ey": 1920, "ly": 2025, "p": 4392},
  {"key": "Huaca Solecape-Peru", "n": "Huaca Solecape", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.60463, -79.936], "ey": -1000, "ly": 1530, "p": 4391, "al": ["pueblo nuevo - muy finca - mochum", "huaca los perros", "huaca maravilla"]},
  {"key": "Pueblo Nuevo de Conta Roma-Peru", "n": "Pueblo Nuevo de Conta Roma", "c": "Peru", "r": "per_lima", "ll": [-13.018, -76.3395], "ey": 1850, "ly": 2017, "p": 4390},
  {"key": "Pitambala-Argentina", "n": "Pitambala", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.4, -63.956], "ey": 1536, "ly": 1830, "p": 4389},
  {"key": "La Cruz (vng_antioquia_popayan_choco)-Colombia", "n": "La Cruz", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [3.002, -76.362], "ey": 1525, "ly": 1830, "p": 4388},
  {"key": "Vergara-Peru", "n": "Vergara", "c": "Peru", "r": "vp_intendencia_puno", "ll": [-15.851, -70.736], "ey": 1525, "ly": 1825, "p": 4386},
  {"key": "Tongod-Peru", "n": "Tongod", "c": "Peru", "r": "per_cajamarca", "ll": [-6.7575, -78.825], "ey": 1850, "ly": 2025, "p": 4385},
  {"key": "La Sonadora-Colombia", "n": "La Sonadora", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.77611, -74.70194], "ey": 1300, "ly": 1500, "p": 4383},
  {"key": "Chiacani-Bolivia", "n": "Chiacani", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-15.733, -68.75], "ey": 1525, "ly": 1825, "p": 4382},
  {"key": "San Nicolas Ñausa-Ecuador", "n": "San Nicolas Ñausa", "c": "Ecuador", "r": "vng_guayaquil_esmeraldas", "ll": [-1.967, -79.6], "ey": 1525, "ly": 1830, "p": 4381},
  {"key": "Gaira-Colombia", "n": "Gaira", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [11.186, -74.222], "ey": 1000, "ly": 1500, "p": 4380},
  {"key": "Chinchihuasi-Peru", "n": "Chinchihuasi", "c": "Peru", "r": "per_huancavelica", "ll": [-12.51694, -74.54583], "ey": 1850, "ly": 2025, "p": 4378},
  {"key": "Isla Verde-Argentina", "n": "Isla Verde", "c": "Argentina", "r": "arg_cordoba", "ll": [-33.23981, -62.40163], "ey": 1850, "ly": 2022, "p": 4378},
  {"key": "Purun Marca-Peru", "n": "Purun Marca", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.22545, -75.71983], "ey": 500, "ly": 1530, "p": 4377, "al": ["quebrada calla", "sillagaga", "Quebrada Calla"]},
  {"key": "Cochamarca-Peru", "n": "Cochamarca", "c": "Peru", "r": "per_lima", "ll": [-10.86333, -77.12889], "ey": 1525, "ly": 2025, "p": 4374},
  {"key": "Magollo 1 C-Peru", "n": "Magollo 1 C", "c": "Peru", "r": "inca_collasuyu", "ll": [-18.08358, -70.31727], "ey": -1000, "ly": 1530, "p": 4374, "ex": [{"date": "1886.1.1", "name": "Tacna"}], "al": ["cerro de para", "cerro de para 1 c", "copare 1 c"]},
  {"key": "Sanipaya-Bolivia", "n": "Sanipaya", "c": "Bolivia", "r": "vp_intendencia_cochabamba", "ll": [-17.033, -66.945], "ey": 1525, "ly": 1825, "p": 4370},
  {"key": "Los Encuentros-Ecuador", "n": "Los Encuentros", "c": "Ecuador", "r": "ecu_zamora_chinchipe", "ll": [-3.75986, -78.6477], "ey": 1920, "ly": 2025, "p": 4369},
  {"key": "Curaray-Ecuador", "n": "Curaray", "c": "Ecuador", "r": "ecu_pastaza", "ll": [-1.37164, -76.94749], "ey": 1920, "ly": 2025, "p": 4366},
  {"key": "Los Delfines-Peru", "n": "Los Delfines", "c": "Peru", "r": "per_loreto", "ll": [-3.8448, -73.3394], "ey": 1920, "ly": 2017, "p": 4366},
  {"key": "La Florida-Peru", "n": "La Florida", "c": "Peru", "r": "per_arequipa", "ll": [-16.2264, -73.6141], "ey": 1850, "ly": 2017, "p": 4364},
  {"key": "Kuntur Was-Peru", "n": "Kuntur Was", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.12871, -78.84648], "ey": -1000, "ly": 1530, "p": 4364, "al": ["arqueológico cerro blanco", "arqueológico papayoloma", "arqueológico romero loma"]},
  {"key": "Ñaupallacta-Peru", "n": "Ñaupallacta", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.81658, -74.31307], "ey": -1000, "ly": 1530, "p": 4364, "al": ["paqolla", "ñawpa llaqta", "Paqolla"]},
  {"key": "Cuchiyaco-Argentina", "n": "Cuchiyaco", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.58339, -65.27996], "ey": 80, "ly": 1500, "p": 4364},
  {"key": "San José (ven_trujillo_2)-Venezuela", "n": "San José", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.19333, -70.32556], "ey": 1538, "ly": 2025, "p": 4361, "al": ["san jose tostoz", "San Jose Tostoz"]},
  {"key": "La Remigia-Colombia", "n": "La Remigia", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.52, -78.66], "ey": -330, "ly": 370, "p": 4361, "al": ["cebú", "cortadura", "el aguacate"]},
  {"key": "Taller-Chile", "n": "Taller", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.53285, -69.55332], "ey": 1000, "ly": 1500, "p": 4361, "al": ["con", "Con"]},
  {"key": "Piedra Grande-Venezuela", "n": "Piedra Grande", "c": "Venezuela", "r": "ven_falcon", "ll": [10.84333, -69.94333], "ey": 1850, "ly": 2025, "p": 4360},
  {"key": "Santander-Peru", "n": "Santander", "c": "Peru", "r": "per_lima", "ll": [-11.1993, -76.5211], "ey": 1525, "ly": 2017, "p": 4359, "al": ["alpamarca", "Alpamarca"]},
  {"key": "Rinconada-Argentina", "n": "Rinconada", "c": "Argentina", "r": "arg_jujuy", "ll": [-22.4407, -66.16715], "ey": 1525, "ly": 2022, "p": 4359, "al": ["valle rico de la rinconada", "Valle Rico de la Rinconada"]},
  {"key": "Madre Tierra-Ecuador", "n": "Madre Tierra", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-1.54194, -78.03459], "ey": 1920, "ly": 2025, "p": 4358},
  {"key": "Vista Flores-Argentina", "n": "Vista Flores", "c": "Argentina", "r": "arg_mendoza", "ll": [-33.6509, -69.15583], "ey": 1850, "ly": 2010, "p": 4358},
  {"key": "Arboleda-Colombia_2", "n": "Arboleda", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.01686, -73.85527], "ey": 1000, "ly": 1500, "p": 4358, "al": ["jerónimo martins", "Jerónimo Martins"]},
  {"key": "Izcuchaca-Peru_2", "n": "Izcuchaca", "c": "Peru", "r": "inca_cuzco_heartland", "ll": [-13.47616, -72.23212], "ey": 1440, "ly": 1532, "p": 4357, "al": ["ancachuro", "andenes de zurite", "quishuarpat"]},
  {"key": "San Hilarión-Peru", "n": "San Hilarión", "c": "Peru", "r": "per_san_martin", "ll": [-7.00389, -76.43944], "ey": 1900, "ly": 2025, "p": 4355, "al": ["san cristóbal de sisa", "San Cristóbal de Sisa"]},
  {"key": "El Morroso-Colombia", "n": "El Morroso", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [5.565, -74.097], "ey": 1525, "ly": 1830, "p": 4355},
  {"key": "La Portuguesa-Colombia", "n": "La Portuguesa", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [5.11854, -72.36265], "ey": 1000, "ly": 1500, "p": 4355},
  {"key": "Localidad-Colombia", "n": "Localidad", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.92, -75.18], "ey": -7394, "ly": 1500, "p": 4355, "al": ["piii op", "yacimiento", "yaximiento"]},
  {"key": "Cojata-Peru", "n": "Cojata", "c": "Peru", "r": "per_puno", "ll": [-15.01528, -69.36556], "ey": 1525, "ly": 2025, "p": 4354},
  {"key": "San José de Tiznados-Venezuela", "n": "San José de Tiznados", "c": "Venezuela", "r": "ven_guarico", "ll": [9.37851, -67.62143], "ey": 1786, "ly": 2025, "p": 4347, "al": ["san jose de tiznados"]},
  {"key": "Las Pirias-Peru", "n": "Las Pirias", "c": "Peru", "r": "per_cajamarca", "ll": [-5.62722, -78.85278], "ey": 1850, "ly": 2025, "p": 4344},
  {"key": "Constantino Fernández-Ecuador", "n": "Constantino Fernández", "c": "Ecuador", "r": "ecu_tungurahua", "ll": [-1.18714, -78.63769], "ey": 1850, "ly": 2025, "p": 4343},
  {"key": "San Antonio (per_lima_2)-Peru", "n": "San Antonio", "c": "Peru", "r": "per_lima", "ll": [-12.64222, -76.64944], "ey": 1850, "ly": 2025, "p": 4343},
  {"key": "Piedras Marcadas-Peru", "n": "Piedras Marcadas", "c": "Peru", "r": "inca_antisuyu", "ll": [-12.68732, -73.7326], "ey": -2000, "ly": 1530, "p": 4343, "al": ["anor", "Anor"]},
  {"key": "Huaca Las Estacas-Peru", "n": "Huaca Las Estacas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.03909, -79.62473], "ey": -1000, "ly": 1530, "p": 4341, "al": ["huaca blanca", "huaca blanca norte", "huaca jaime"]},
  {"key": "Cumbemayo-Peru", "n": "Cumbemayo", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.19055, -78.57671], "ey": 1438, "ly": 1530, "p": 4338, "ex": [{"date": "1800.1.1", "name": "Cajamarca"}], "al": ["cajamarca - magdalena", "Cajamarca - Magdalena"]},
  {"key": "Polig N-Peru", "n": "Polig N", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.45892, -78.71619], "ey": -2000, "ly": 1530, "p": 4336, "al": ["huaca bitin", "huaca don alfredo", "polig. n"]},
  {"key": "El Cangrejo-Colombia", "n": "El Cangrejo", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.55, -73.68], "ey": 1282, "ly": 1500, "p": 4336},
  {"key": "Complejo Miculla - Pachia Sector: C-Peru", "n": "Complejo Miculla - Pachia Sector: C", "c": "Peru", "r": "inca_collasuyu", "ll": [-17.884, -70.11705], "ey": 0, "ly": 1530, "p": 4334, "al": ["calientes - miculla", "complejo miculla - pachia", "complejo miculla - pachia sector: a"]},
  {"key": "La Para-Argentina", "n": "La Para", "c": "Argentina", "r": "arg_cordoba", "ll": [-30.89407, -63.00127], "ey": 1850, "ly": 2022, "p": 4333},
  {"key": "Pocpo-Bolivia", "n": "Pocpo", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.83333, -65.36667], "ey": 1525, "ly": 1825, "p": 4332, "al": ["pojpo", "poopo", "Pojpo"]},
  {"key": "Park-Peru", "n": "Park", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.94658, -71.40108], "ey": 0, "ly": 1530, "p": 4329},
  {"key": "Guanazán-Ecuador", "n": "Guanazán", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.45176, -79.48758], "ey": 1525, "ly": 2025, "p": 4327, "al": ["guanazan", "guanasan", "Guanazan"]},
  {"key": "Relave-Peru", "n": "Relave", "c": "Peru", "r": "per_ayacucho", "ll": [-15.6096, -74.0574], "ey": 1850, "ly": 2017, "p": 4327},
  {"key": "Huaca Molino Cajanleque-Peru", "n": "Huaca Molino Cajanleque", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.78104, -79.25184], "ey": 1438, "ly": 1530, "p": 4326},
  {"key": "Pansaleo-Ecuador", "n": "Pansaleo", "c": "Ecuador", "r": "ecu_tungurahua", "ll": [-1.09089, -78.57939], "ey": 1850, "ly": 2025, "p": 4325},
  {"key": "Usmagama-Chile", "n": "Usmagama", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.742, -69.22], "ey": 1525, "ly": 1825, "p": 4325},
  {"key": "Vereda Santa Clara-Colombia", "n": "Vereda Santa Clara", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.66071, -74.33165], "ey": 1300, "ly": 1500, "p": 4325},
  {"key": "Santa Isabel (col_cordoba)-Colombia", "n": "Santa Isabel", "c": "Colombia", "r": "col_cordoba", "ll": [8.54566, -75.95494], "ey": 500, "ly": 2018, "p": 4324},
  {"key": "Pílamo-Colombia", "n": "Pílamo", "c": "Colombia", "r": "col_cauca", "ll": [3.09385, -76.34377], "ey": 1525, "ly": 2018, "p": 4323, "al": ["pilamo", "Pilamo"]},
  {"key": "Solor-Chile", "n": "Solor", "c": "Chile", "r": "vp_intendencia_charcas_potosi", "ll": [-22.949, -68.186], "ey": -3000, "ly": 1825, "p": 4323, "al": ["ayllu solo", "yaye", "aldea de tulor; tulor"]},
  {"key": "Amaicha del Valle-Argentina", "n": "Amaicha del Valle", "c": "Argentina", "r": "arg_tucuman", "ll": [-26.59372, -65.92007], "ey": 1850, "ly": 2022, "p": 4320},
  {"key": "San Ignacio Miní-Argentina", "n": "San Ignacio Miní", "c": "Argentina", "r": "crp_banda_oriental_misiones", "ll": [-27.255, -55.532], "ey": 1632, "ly": 1768, "p": 4320, "al": ["san ignacio mini", "San Ignacio Mini"]}
]

HEADERS = {'User-Agent': 'SVEAToponymyBot/1.0 (https://confoederatio.org; research@confoederatio.org) python-urllib'}

def haversine(lat1, lon1, lat2, lon2):
  R = 6371.0
  p1, p2 = math.radians(lat1), math.radians(lat2)
  dp = math.radians(lat2 - lat1)
  dl = math.radians(lon2 - lon1)
  a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
  return 2 * R * math.asin(math.sqrt(a))

def fetch_json(url):
  for attempt in range(3):
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
      if "429" in str(e) and attempt < 2:
        time.sleep(1.5 * (attempt + 1))
      else:
        return {"_err": str(e)}

# 1. Index local settlement sources
local_hits = {s["key"]: [] for s in SETTLEMENTS}
src_dir = os.path.join("histmap", "1.data_raw", "population_regional", "QUIPU", "_shared", "settlement_sources")
for fp in glob.glob(os.path.join(src_dir, "*.json")):
  fn = os.path.basename(fp)
  if fn == "wave1_harvest_summary.json":
    continue
  try:
    with open(fp, "r", encoding="utf-8") as f:
      data = json.load(f)
    rows = data if isinstance(data, list) else data.get("settlements", data.get("records", []))
    if isinstance(rows, dict):
      rows = list(rows.values())
    for r in rows:
      if not isinstance(r, dict):
        continue
      rlat = r.get("lat") if r.get("lat") is not None else (r.get("ll", [None, None])[0] if isinstance(r.get("ll"), list) else None)
      rlng = r.get("lng") if r.get("lng") is not None else (r.get("lon") if r.get("lon") is not None else (r.get("ll", [None, None])[1] if isinstance(r.get("ll"), list) else None))
      rname = str(r.get("name") or r.get("n") or r.get("nombre") or "").strip().lower()
      for s in SETTLEMENTS:
        matched = False
        if r.get("key") == s["key"]:
          matched = True
        elif rlat is not None and rlng is not None:
          try:
            d = haversine(s["ll"][0], s["ll"][1], float(rlat), float(rlng))
            if d <= 2.5:
              matched = True
          except Exception:
            pass
        if matched:
          compact = {k: v for k, v in r.items() if k not in ("populations", "pop_series", "yearly")}
          compact["_src_file"] = fn
          local_hits[s["key"]].append(compact)
  except Exception as e:
    print(f"Error reading {fn}: {e}")

# 2. Query Wikipedia (es, en) for each settlement
out_data = []
for idx, s in enumerate(SETTLEMENTS):
  key = s["key"]
  n = s["n"]
  c = s["c"]
  lat, lng = s["ll"]
  rec = {
    "key": key, "n": n, "c": c, "r": s["r"], "ll": s["ll"],
    "ey": s["ey"], "ly": s["ly"], "al": s.get("al", []), "ex": s.get("ex", []),
    "local": local_hits[key][:5],
    "geo_es": [], "search_es": [], "wiki_es": None,
    "geo_en": [], "wiki_en": None
  }

  # ES geosearch
  gd = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json")
  rec["geo_es"] = [{"title": g["title"], "dist": round(g["dist"])} for g in gd.get("query", {}).get("geosearch", [])]

  # ES search
  q = urllib.parse.quote(f'"{n}" {c}')
  sd = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=5&format=json")
  rec["search_es"] = [h["title"] for h in sd.get("query", {}).get("search", [])]

  # Pick best ES title
  best_es = None
  n_low = n.lower()
  n_tok = n_low.split()[0] if n_low.split() else n_low
  for g in rec["geo_es"]:
    if len(n_tok) >= 3 and n_tok in g["title"].lower():
      best_es = g["title"]
      break
  if not best_es:
    for ht in rec["search_es"]:
      if len(n_tok) >= 3 and (n_low in ht.lower() or n_tok in ht.lower()):
        best_es = ht
        break
  if not best_es and rec["geo_es"] and rec["geo_es"][0]["dist"] <= 2000:
    best_es = rec["geo_es"][0]["title"]

  if best_es:
    t_enc = urllib.parse.quote(best_es)
    ed = fetch_json(f"https://es.wikipedia.org/w/api.php?action=query&titles={t_enc}&prop=extracts|coordinates&explaintext=1&exchars=3500&format=json")
    for pid, pdata in ed.get("query", {}).get("pages", {}).items():
      if pid != "-1":
        rec["wiki_es"] = {
          "title": pdata.get("title"),
          "coords": pdata.get("coordinates"),
          "extract": pdata.get("extract", "")[:3000]
        }

  # If no ES wiki, try EN geosearch/search
  if not rec["wiki_es"]:
    gd_en = fetch_json(f"https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json")
    rec["geo_en"] = [{"title": g["title"], "dist": round(g["dist"])} for g in gd_en.get("query", {}).get("geosearch", [])]
    best_en = None
    for g in rec["geo_en"]:
      if len(n_tok) >= 3 and n_tok in g["title"].lower():
        best_en = g["title"]
        break
    if not best_en:
      sd_en = fetch_json(f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json")
      for h in sd_en.get("query", {}).get("search", []):
        if len(n_tok) >= 3 and n_tok in h["title"].lower():
          best_en = h["title"]
          break
    if best_en:
      t_enc = urllib.parse.quote(best_en)
      ed = fetch_json(f"https://en.wikipedia.org/w/api.php?action=query&titles={t_enc}&prop=extracts|coordinates&explaintext=1&exchars=3000&format=json")
      for pid, pdata in ed.get("query", {}).get("pages", {}).items():
        if pid != "-1":
          rec["wiki_en"] = {
            "title": pdata.get("title"),
            "coords": pdata.get("coordinates"),
            "extract": pdata.get("extract", "")[:2500]
          }

  out_data.append(rec)
  if (idx + 1) % 15 == 0:
    print(f"Processed {idx+1}/90 (local hits={sum(1 for r in out_data if r['local'])}, wiki={sum(1 for r in out_data if r['wiki_es'] or r['wiki_en'])})", flush=True)
  time.sleep(0.05)

with open("tests/tmp_chunk038_data.json", "w", encoding="utf-8") as f:
  json.dump(out_data, f, ensure_ascii=False, indent=2)

# Write compact text digest
lines = []
for idx, r in enumerate(out_data):
  lines.append(f"=== [{idx+1}] {r['key']} | n={r['n']} | c={r['c']} | r={r['r']} | ll={r['ll']} | ey={r['ey']} ly={r['ly']} | al={r['al']} | ex={r['ex']} ===")
  if r["local"]:
    for loc in r["local"][:2]:
      lines.append(f"  LOCAL ({loc.get('_src_file')}): {json.dumps(loc, ensure_ascii=False)[:400]}")
  lines.append(f"  GEO_ES: {r['geo_es'][:3]} | SEARCH_ES: {r['search_es'][:3]}")
  if r["wiki_es"]:
    w = r["wiki_es"]
    ext = w["extract"].replace("\n", " ")[:1200]
    lines.append(f"  WIKI_ES [{w['title']}] coords={w['coords']}: {ext}")
  elif r["wiki_en"]:
    w = r["wiki_en"]
    ext = w["extract"].replace("\n", " ")[:1200]
    lines.append(f"  WIKI_EN [{w['title']}] coords={w['coords']}: {ext}")
  lines.append("")

with open("tests/tmp_chunk038_digest.txt", "w", encoding="utf-8") as f:
  f.write("\n".join(lines))

print("DONE! Saved tests/tmp_chunk038_data.json and tests/tmp_chunk038_digest.txt")
