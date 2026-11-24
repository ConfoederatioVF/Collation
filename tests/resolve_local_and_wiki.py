import glob
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request

INPUT_DATA = [
  {"key": "Alto Huamuco-Peru", "n": "Alto Huamuco", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.71005, -76.36504], "ey": -3000, "ly": 1530, "p": 4319, "al": ["alto huamaco", "san miguel", "santa rosa de alto yanajanca"]},
  {"key": "Guayzimi-Ecuador", "n": "Guayzimi", "c": "Ecuador", "r": "ecu_zamora_chinchipe", "ll": [-4.04639, -78.68295], "ey": 1920, "ly": 2025, "p": 4316},
  {"key": "Julca-Peru", "n": "Julca", "c": "Peru", "r": "vp_intendencia_tarma", "ll": [-11.969, -75.8], "ey": 1525, "ly": 1825, "p": 4316, "al": ["jalca", "tulca", "Jalca"]},
  {"key": "Laqueyque-Peru", "n": "Laqueyque", "c": "Peru", "r": "vp_intendencia_puno", "ll": [-14.226, -69.47], "ey": 1525, "ly": 1825, "p": 4316, "al": ["chaquiminas", "Chaquiminas"]},
  {"key": "Cangrejos grandes-Argentina", "n": "Cangrejos grandes", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-22.473, -65.55], "ey": 1525, "ly": 1830, "p": 4315},
  {"key": "San Blas de los Sauces-Argentina", "n": "San Blas de los Sauces", "c": "Argentina", "r": "arg_la_rioja", "ll": [-28.54329, -67.15814], "ey": 1850, "ly": 2022, "p": 4314},
  {"key": "Marca Marca Quepayna-Peru", "n": "Marca Marca Quepayna", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.76718, -76.19172], "ey": 0, "ly": 1530, "p": 4313, "al": ["común corral", "consejo punta", "cruz misión alta"]},
  {"key": "Waqramarka-Peru", "n": "Waqramarka", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.34454, -72.046], "ey": 0, "ly": 1530, "p": 4313, "al": ["llonjaya", "socacheta", "Llonjaya"]},
  {"key": "Volcan uno - sitio uno-Colombia", "n": "Volcan uno - sitio uno", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.24, -74.98], "ey": 549, "ly": 1500, "p": 4312},
  {"key": "Colonias Unidas-Argentina", "n": "Colonias Unidas", "c": "Argentina", "r": "arg_chaco", "ll": [-26.7001, -59.62774], "ey": 1900, "ly": 2022, "p": 4308},
  {"key": "Pampas-Peru_2", "n": "Pampas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.89656, -76.45265], "ey": -2000, "ly": 1532, "p": 4307, "al": ["huamally", "mito", "Huamally"]},
  {"key": "Lumbaquí-Ecuador", "n": "Lumbaquí", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [0.04756, -77.32851], "ey": 1920, "ly": 2025, "p": 4305},
  {"key": "San Fernando del Guapo-Venezuela", "n": "San Fernando del Guapo", "c": "Venezuela", "r": "ven_miranda", "ll": [10.20333, -65.94722], "ey": 1850, "ly": 2025, "p": 4303},
  {"key": "Casca-Peru", "n": "Casca", "c": "Peru", "r": "per_ancash", "ll": [-8.85556, -77.39861], "ey": 1850, "ly": 2025, "p": 4301},
  {"key": "San Miguel (col_cundinamarca)-Colombia", "n": "San Miguel", "c": "Colombia", "r": "col_cundinamarca", "ll": [5.03405, -73.95783], "ey": 1970, "ly": 2018, "p": 4299, "al": ["barandillas", "el codito", "el kiosko la granja"]},
  {"key": "Ayata-Bolivia_2", "n": "Ayata", "c": "Bolivia", "r": "conq_audiencia_charcas_potosi", "ll": [-15.459, -68.836], "ey": 1525, "ly": 1650, "p": 4299},
  {"key": "Siquisique-Venezuela", "n": "Siquisique", "c": "Venezuela", "r": "ven_lara", "ll": [10.57056, -69.69778], "ey": 1538, "ly": 2025, "p": 4297},
  {"key": "Lauca-Peru", "n": "Lauca", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.71724, -71.48672], "ey": 1000, "ly": 1530, "p": 4296},
  {"key": "Complejo Murales de Ucupe - Chaquiras-Peru", "n": "Complejo Murales de Ucupe - Chaquiras", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.07354, -79.67219], "ey": -2000, "ly": 1530, "p": 4291, "al": ["cerro cherrepe", "cerro chinto", "huaca blanca conchal"]},
  {"key": "Las Lomas-Peru_2", "n": "Las Lomas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.3579, -78.82307], "ey": 1438, "ly": 1530, "p": 4291, "al": ["cerro queneto", "pur pur norte", "pur pur sur"]},
  {"key": "Canta-Peru", "n": "Canta", "c": "Peru", "r": "per_lima", "ll": [-11.46722, -76.62444], "ey": 1573, "ly": 2025, "p": 4290},
  {"key": "Simaña-Colombia", "n": "Simaña", "c": "Colombia", "r": "col_cesar", "ll": [8.61069, -73.73052], "ey": 1525, "ly": 2018, "p": 4289, "al": ["simaña de playa blanca", "Simaña de Playa Blanca"]},
  {"key": "Santa Marianita-Ecuador", "n": "Santa Marianita", "c": "Ecuador", "r": "ecu_manabi", "ll": [-1.01181, -80.84377], "ey": 1850, "ly": 2025, "p": 4289},
  {"key": "Santa Catalina de Mossa-Peru", "n": "Santa Catalina de Mossa", "c": "Peru", "r": "per_piura", "ll": [-5.10278, -79.885], "ey": 1850, "ly": 2025, "p": 4289, "al": ["paltashaco", "Paltashaco"]},
  {"key": "Soldini-Argentina", "n": "Soldini", "c": "Argentina", "r": "arg_santa_fe", "ll": [-33.02191, -60.75462], "ey": 1850, "ly": 2022, "p": 4286},
  {"key": "Conchas-Argentina", "n": "Conchas", "c": "Argentina", "r": "crp_intendencia_buenos_aires", "ll": [-34.416, -58.579], "ey": 1536, "ly": 1830, "p": 4286},
  {"key": "San Jose de Gualeguaychu-Argentina", "n": "San Jose de Gualeguaychu", "c": "Argentina", "r": "crp_intendencia_buenos_aires", "ll": [-33.008, -58.511], "ey": 1764, "ly": 1830, "p": 4286, "ex": [{"date": "1869.1.1", "name": "Gualeguaychú"}]},
  {"key": "Concepción-Ecuador", "n": "Concepción", "c": "Ecuador", "r": "ecu_carchi", "ll": [0.65701, -78.10722], "ey": 1850, "ly": 2025, "p": 4285},
  {"key": "Pambamarca-Ecuador", "n": "Pambamarca", "c": "Ecuador", "r": "inca_chinchaysuyu", "ll": [0.015, -78.208], "ey": 1490, "ly": 1530, "p": 4280, "al": ["quitoloma", "Quitoloma"]},
  {"key": "Barrancas-Venezuela_2", "n": "Barrancas", "c": "Venezuela", "r": "na_caribbean_maracaibo_tairona", "ll": [8.698, -62.189], "ey": -1000, "ly": 1500, "p": 4280, "al": ["los barrancos", "saladero", "Los Barrancos"]},
  {"key": "Pacoa-Colombia", "n": "Pacoa", "c": "Colombia", "r": "col_vaupes", "ll": [0.0207, -71.00434], "ey": 1900, "ly": 2025, "p": 4279},
  {"key": "Conduriri-Peru", "n": "Conduriri", "c": "Peru", "r": "per_puno", "ll": [-16.62194, -69.70861], "ey": 1850, "ly": 2025, "p": 4277},
  {"key": "El Pital (col_cauca)-Colombia", "n": "El Pital", "c": "Colombia", "r": "col_cauca", "ll": [2.86406, -76.5467], "ey": 1525, "ly": 2018, "p": 4273, "al": ["turco", "Turco"]},
  {"key": "Rio Chico-Chile", "n": "Rio Chico", "c": "Chile", "r": "sc_patagonia_tierra_del_fuego", "ll": [-52.06667, -70], "ey": -4737, "ly": 459, "p": 4272},
  {"key": "Colonia Segovia-Argentina", "n": "Colonia Segovia", "c": "Argentina", "r": "arg_mendoza", "ll": [-32.86608, -68.71677], "ey": 1850, "ly": 2010, "p": 4271},
  {"key": "Huigra-Ecuador", "n": "Huigra", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.2702, -79.00684], "ey": 1850, "ly": 2025, "p": 4267},
  {"key": "Yuracyacu-Peru", "n": "Yuracyacu", "c": "Peru", "r": "per_san_martin", "ll": [-5.93111, -77.22639], "ey": 1900, "ly": 2025, "p": 4267},
  {"key": "Patambuco-Peru", "n": "Patambuco", "c": "Peru", "r": "per_puno", "ll": [-14.36167, -69.61944], "ey": 1525, "ly": 2025, "p": 4266, "al": ["patanbuco"]},
  {"key": "Cherrepe-Peru", "n": "Cherrepe", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-7.178, -79.687], "ey": 0, "ly": 1825, "p": 4266},
  {"key": "Costa Rica-Colombia_2", "n": "Costa Rica", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [3.46139, -73.90361], "ey": 500, "ly": 1500, "p": 4266},
  {"key": "Manuel Morillo-Venezuela", "n": "Manuel Morillo", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.87444, -70.27889], "ey": 1850, "ly": 2025, "p": 4265},
  {"key": "Rio Tercero-Argentina", "n": "Rio Tercero", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.15167, -64.18807], "ey": 80, "ly": 1500, "p": 4265, "ex": [{"date": "1947.1.1", "name": "Río Tercero"}]},
  {"key": "Llaqtapata-Peru", "n": "Llaqtapata", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.64394, -74.58458], "ey": 0, "ly": 1530, "p": 4264, "al": ["llactapata", "Llactapata"]},
  {"key": "UIA 61 - Yacimiento-Colombia", "n": "UIA 61 - Yacimiento", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.47512, -74.26021], "ey": 1300, "ly": 1500, "p": 4264, "al": ["uia 170 - yacimiento", "uia 57 - yacimiento", "uia 68 - yacimiento"]},
  {"key": "Puente Sogamoso-Colombia", "n": "Puente Sogamoso", "c": "Colombia", "r": "col_santander", "ll": [7.24647, -73.78594], "ey": 1850, "ly": 2018, "p": 4263},
  {"key": "Cudico-Chile_2", "n": "Cudico", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.66261, -73.11566], "ey": 1350, "ly": 1500, "p": 4263, "al": ["fundo timonel", "Fundo Timonel"]},
  {"key": "Machu Pitumarka-Peru", "n": "Machu Pitumarka", "c": "Peru", "r": "inca_collasuyu", "ll": [-13.96434, -71.40065], "ey": 1000, "ly": 1530, "p": 4261},
  {"key": "La Tola-Ecuador", "n": "La Tola", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [1.13779, -79.05177], "ey": 1740, "ly": 2025, "p": 4260, "al": ["tola", "latola", "Latola"]},
  {"key": "Hato Viejo-Colombia", "n": "Hato Viejo", "c": "Colombia", "r": "col_bolivar", "ll": [10.30351, -75.03918], "ey": 1850, "ly": 2018, "p": 4259},
  {"key": "Gachgar-Peru", "n": "Gachgar", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.47579, -76.26206], "ey": 500, "ly": 1530, "p": 4258},
  {"key": "Aguas Vivas JRS-Colombia", "n": "Aguas Vivas JRS", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [8.84528, -75.5614], "ey": 1300, "ly": 1500, "p": 4257},
  {"key": "Guri-Venezuela", "n": "Guri", "c": "Venezuela", "r": "ven_bolivar", "ll": [7.75684, -63.03675], "ey": 1850, "ly": 2011, "p": 4255},
  {"key": "Amantani-Peru", "n": "Amantani", "c": "Peru", "r": "per_puno", "ll": [-15.65722, -69.71833], "ey": 1850, "ly": 2025, "p": 4255},
  {"key": "El Alcalde-Argentina_2", "n": "El Alcalde", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-31.15162, -63.42993], "ey": 80, "ly": 1500, "p": 4254},
  {"key": "Nuevo Andoas-Ecuador", "n": "Nuevo Andoas", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-2.80511, -76.4622], "ey": -2000, "ly": 2017, "p": 4253, "al": ["los brillantes", "nuevo andoas - los jardines", "titiyacu"]},
  {"key": "Bringamosal-Colombia", "n": "Bringamosal", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.03619, -74.98218], "ey": -3000, "ly": 1500, "p": 4252, "al": ["el badeo", "El Badeo"]},
  {"key": "Tamborajra-Peru", "n": "Tamborajra", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.92354, -76.77975], "ey": 1300, "ly": 1532, "p": 4250, "al": ["hierba buena", "warihuayin", "Hierba Buena"]},
  {"key": "Puerto Murialdo-Ecuador", "n": "Puerto Murialdo", "c": "Ecuador", "r": "ecu_napo", "ll": [-0.69142, -77.13622], "ey": 1850, "ly": 2025, "p": 4249},
  {"key": "Sierra de los Padres-Argentina", "n": "Sierra de los Padres", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-37.94564, -57.77452], "ey": 1850, "ly": 2010, "p": 4249},
  {"key": "Carasani-Bolivia", "n": "Carasani", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-15.738, -68.769], "ey": 1525, "ly": 1825, "p": 4249},
  {"key": "Murillo-Colombia", "n": "Murillo", "c": "Colombia", "r": "col_tolima", "ll": [4.87434, -75.17102], "ey": 1850, "ly": 2025, "p": 4248},
  {"key": "Urdaneta (ecu_azuay)-Ecuador", "n": "Urdaneta", "c": "Ecuador", "r": "ecu_azuay", "ll": [-3.65576, -79.16424], "ey": 1850, "ly": 2025, "p": 4247},
  {"key": "Naschel-Argentina", "n": "Naschel", "c": "Argentina", "r": "arg_san_luis", "ll": [-32.91528, -65.37595], "ey": 1850, "ly": 2022, "p": 4247},
  {"key": "Punama-Bolivia", "n": "Punama", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-15.53, -69.018], "ey": 1525, "ly": 1825, "p": 4246},
  {"key": "Alto Perú-Peru", "n": "Alto Perú", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.68968, -77.69499], "ey": 0, "ly": 1530, "p": 4245, "al": ["complejo cerro chiu chiu", "complejo cerro mirador", "conchitas"]},
  {"key": "Anguia-Peru", "n": "Anguia", "c": "Peru", "r": "per_cajamarca", "ll": [-6.34194, -78.60528], "ey": 1850, "ly": 2025, "p": 4244},
  {"key": "San Pedro de Coris-Peru", "n": "San Pedro de Coris", "c": "Peru", "r": "per_huancavelica", "ll": [-12.57806, -74.41167], "ey": 1850, "ly": 2025, "p": 4244},
  {"key": "Montículo Pampa Maravillas-Peru", "n": "Montículo Pampa Maravillas", "c": "Peru", "r": "inca_collasuyu", "ll": [-15.43866, -70.13103], "ey": 1000, "ly": 1530, "p": 4244, "al": ["arqueológico andenerias de arcopunco", "cerro chingora", "colina maravillas"]},
  {"key": "Juan Velasco Alvarado-Peru_2", "n": "Juan Velasco Alvarado", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-5.3205, -79.93555], "ey": -1000, "ly": 1530, "p": 4243, "al": ["cerro hualas", "el ala", "huaca polluco"]},
  {"key": "Cerro Baul-Peru", "n": "Cerro Baul", "c": "Peru", "r": "inca_contisuyu", "ll": [-17.1, -70.9], "ey": 0, "ly": 1532, "p": 4241, "al": ["torata alta", "alto paralaque", "arqueológico villa verde"]},
  {"key": "Angochagua-Ecuador", "n": "Angochagua", "c": "Ecuador", "r": "ecu_imbabura", "ll": [0.22026, -78.086], "ey": 1850, "ly": 2025, "p": 4237},
  {"key": "Muestreo 149-Colombia", "n": "Muestreo 149", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.46504, -75.80966], "ey": 1300, "ly": 1500, "p": 4234, "al": ["muestreo 222", "Muestreo 222"]},
  {"key": "El Pinar-Chile", "n": "El Pinar", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-36.8131, -72.03542], "ey": 0, "ly": 1500, "p": 4233, "al": ["estero colton", "Estero Colton"]},
  {"key": "Escara-Bolivia", "n": "Escara", "c": "Bolivia", "r": "bol_oruro", "ll": [-18.69445, -68.1594], "ey": 1750, "ly": 2026, "p": 4231},
  {"key": "La Jagua Del Pilar-Colombia", "n": "La Jagua Del Pilar", "c": "Colombia", "r": "col_la_guajira", "ll": [10.51186, -73.07264], "ey": 1850, "ly": 2025, "p": 4230},
  {"key": "Bariquí-Santo Domingo-Venezuela", "n": "Bariquí-Santo Domingo", "c": "Venezuela", "r": "ven_falcon", "ll": [11.43722, -69.35], "ey": 1538, "ly": 2011, "p": 4230, "al": ["bariquis", "Bariquis"]},
  {"key": "San José de la Costa-Venezuela", "n": "San José de la Costa", "c": "Venezuela", "r": "ven_falcon", "ll": [11.43833, -68.84667], "ey": 1850, "ly": 2025, "p": 4230},
  {"key": "Trompin Chico-Peru", "n": "Trompin Chico", "c": "Peru", "r": "inca_contisuyu", "ll": [-16.5455, -71.46813], "ey": 1438, "ly": 1530, "p": 4228, "al": ["cerro pajonal a", "cerro pajonal b", "chaclaya b"]},
  {"key": "Huayllabamba (per_ancash)-Peru", "n": "Huayllabamba", "c": "Peru", "r": "per_ancash", "ll": [-8.53472, -77.56694], "ey": 1850, "ly": 2025, "p": 4227},
  {"key": "Tababela-Ecuador", "n": "Tababela", "c": "Ecuador", "r": "ecu_pichincha", "ll": [-0.14986, -78.35086], "ey": 1850, "ly": 2025, "p": 4226},
  {"key": "Monte Sur-Bolivia", "n": "Monte Sur", "c": "Bolivia", "r": "bol_tarija", "ll": [-21.4927, -64.71715], "ey": 1850, "ly": 2024, "p": 4226},
  {"key": "Galicia Alta-Colombia", "n": "Galicia Alta", "c": "Colombia", "r": "col_risaralda", "ll": [4.80745, -75.8026], "ey": 1850, "ly": 2018, "p": 4225},
  {"key": "Gato Negro (Asentamiento J. A. Páez)-Venezuela", "n": "Gato Negro (Asentamiento J. A. Páez)", "c": "Venezuela", "r": "ven_portuguesa", "ll": [8.975, -69.70722], "ey": 1850, "ly": 2011, "p": 4225, "al": ["gato negro"]},
  {"key": "Irpa Irpa-Bolivia", "n": "Irpa Irpa", "c": "Bolivia", "r": "bol_cochabamba", "ll": [-17.72086, -66.28687], "ey": 1850, "ly": 2024, "p": 4224},
  {"key": "Quiabaya-Bolivia", "n": "Quiabaya", "c": "Bolivia", "r": "bol_la_paz", "ll": [-15.61667, -68.76667], "ey": 1750, "ly": 2026, "p": 4224},
  {"key": "Villa Carlina-Colombia", "n": "Villa Carlina", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.43907, -74.31796], "ey": 1300, "ly": 1500, "p": 4224, "al": ["uia 19 - yacimiento", "uia 22 - yacimiento", "uia 25 - yacimiento"]},
  {"key": "Charaña-Bolivia", "n": "Charaña", "c": "Bolivia", "r": "bol_la_paz", "ll": [-17.59268, -69.4454], "ey": 1750, "ly": 2026, "p": 4221},
  {"key": "Chaquena-Bolivia", "n": "Chaquena", "c": "Bolivia", "r": "inca_collasuyu", "ll": [-17.80377, -67.47768], "ey": 1438, "ly": 1500, "p": 4221, "al": ["achacana alta", "achacana este", "churu pampa"]},
  {"key": "Cerro Pilán-Peru", "n": "Cerro Pilán", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-5.15993, -80.06116], "ey": -2000, "ly": 1530, "p": 4220, "al": ["bocana", "complejo cerro verde", "el paso"]},
  {"key": "Pampa de Los Castillos-Peru", "n": "Pampa de Los Castillos", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.22441, -75.6071], "ey": -2000, "ly": 1530, "p": 4220, "al": ["cerro pico", "tingue", "ánimas altas"]}
]

def hav(lat1, lng1, lat2, lng2):
  r = 6371.0
  dlat = math.radians(lat2 - lat1)
  dlng = math.radians(lng2 - lng1)
  a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlng/2)**2
  return 2*r*math.atan2(math.sqrt(a), math.sqrt(1 - a))

base = "histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources"
with open(os.path.join(base, "hgis_indias_colonial_raw.json"), "r", encoding="utf-8") as f:
  hgis = json.load(f)["settlements"]
hgis_list = list(hgis.values())

with open("histmap/1.data_raw/population_regional/QUIPU/_shared/sites_quipu_andes_cone/config/documented_arch_sites.json", "r", encoding="utf-8") as f:
  doc_arch = json.load(f)["settlements"]

raw_sets = {}
for fn in glob.glob(os.path.join(base, "raw_setts_*.json")):
  with open(fn, "r", encoding="utf-8") as f:
    d = json.load(f)
    raw_sets[os.path.basename(fn)] = d.get("settlements", {})

def get_wiki_es(lat, lng, name):
  headers = {"User-Agent": "Project1509SVEA/1.0 (contact@confoederatio.org)"}
  out = {"geo": [], "search": []}
  try:
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
    req = urllib.request.Request(url, headers=headers)
    data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
    out["geo"] = [{"title": x["title"], "dist": x["dist"]} for x in data.get("query", {}).get("geosearch", [])]
  except Exception as e:
    out["geo_err"] = str(e)
  try:
    q = urllib.parse.quote(name)
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
    req = urllib.request.Request(url, headers=headers)
    data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
    out["search"] = [x["title"] for x in data.get("query", {}).get("search", [])]
  except Exception as e:
    out["search_err"] = str(e)
  return out

results = {}
for item in INPUT_DATA:
  lat, lng = item["ll"]
  rec = {"input": item, "hgis": [], "doc_arch": [], "raw_setts": []}
  for h in hgis_list:
    hc = h.get("coords")
    if isinstance(hc, list) and len(hc) == 2:
      d = hav(lat, lng, hc[0], hc[1])
      if d <= 8.0:
        rec["hgis"].append({
          "d_km": round(d, 2),
          "name": h.get("name"),
          "modern_name": h.get("modern_name"),
          "variants": h.get("variants"),
          "categoria": h.get("categoria"),
          "province": h.get("colonial_province"),
          "partido": h.get("colonial_partido"),
          "start_year": h.get("start_year"),
          "end_year": h.get("end_year"),
          "observations": h.get("observations")
        })
  for idx_d, dv in enumerate(doc_arch):
    if isinstance(dv, dict):
      dc = dv.get("coords") or dv.get("ll")
      if not dc and "lat" in dv and "lng" in dv:
        dc = [dv["lat"], dv["lng"]]
      if isinstance(dc, list) and len(dc) == 2:
        d = hav(lat, lng, dc[0], dc[1])
        if d <= 5.0:
          rec["doc_arch"].append({"d_km": round(d, 2), "k": idx_d, "v": dv})
  for fn, sd in raw_sets.items():
    if isinstance(sd, dict):
      for sk, sv in sd.items():
        sc = sv.get("coords")
        if isinstance(sc, list) and len(sc) == 2:
          d = hav(lat, lng, sc[0], sc[1])
          if d <= 3.0:
            rec["raw_setts"].append({"file": fn, "d_km": round(d, 2), "k": sk, "name": sv.get("name"), "notes": sv.get("notes") or sv.get("source") or sv.get("admin1") or sv.get("admin2"), "keys": list(sv.keys())})
  rec["wiki"] = get_wiki_es(lat, lng, f"{item['n']} {item['c']}")
  results[item["key"]] = rec
  time.sleep(0.05)

with open("tests/chunk39_evidence.json", "w", encoding="utf-8") as f:
  json.dump(results, f, ensure_ascii=False, indent=2)

print("Done:", len(results))
