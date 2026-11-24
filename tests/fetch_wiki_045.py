import json
import urllib.parse
import urllib.request
import time
import re

SETTLEMENTS = [
  {"key": "Pinto (chl_region_de_nuble)-Chile", "n": "Pinto", "c": "Chile", "r": "chl_region_de_nuble", "ll": [-36.70303, -71.89151], "ey": 1850, "ly": 2017, "p": 3766},
  {"key": "San Carlos (arg_salta)-Argentina", "n": "San Carlos", "c": "Argentina", "r": "arg_salta", "ll": [-25.89305, -65.92917], "ey": 1850, "ly": 2022, "p": 3766},
  {"key": "Pimienta-Colombia", "n": "Pimienta", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [8.66, -75.04], "ey": -1119, "ly": 1500, "p": 3765, "al": ["papayo", "Papayo"]},
  {"key": "Uchuhuma-Peru", "n": "Uchuhuma", "c": "Peru", "r": "per_puno", "ll": [-13.9469, -70.0439], "ey": 1525, "ly": 2017, "p": 3763, "al": ["campamento", "cuntuquitu", "Campamento"]},
  {"key": "Tajma-Bolivia", "n": "Tajma", "c": "Bolivia", "r": "bol_la_paz", "ll": [-16.37527, -67.47958], "ey": 1525, "ly": 2024, "p": 3761, "al": ["taxma", "Taxma"]},
  {"key": "Peñuelas-Chile_2", "n": "Peñuelas", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-33.128, -71.562], "ey": 1525, "ly": 1830, "p": 3761},
  {"key": "Wankarani-Bolivia", "n": "Wankarani", "c": "Bolivia", "r": "inca_collasuyu", "ll": [-17.2007, -67.9622], "ey": -1621, "ly": 1532, "p": 3761},
  {"key": "Adaure-Venezuela", "n": "Adaure", "c": "Venezuela", "r": "ven_falcon", "ll": [11.88222, -69.97222], "ey": 1538, "ly": 2025, "p": 3759},
  {"key": "Ricoa-Venezuela", "n": "Ricoa", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [11.483, -69.205], "ey": 1538, "ly": 1830, "p": 3759},
  {"key": "Huachis-Peru", "n": "Huachis", "c": "Peru", "r": "per_ancash", "ll": [-9.41, -77.1], "ey": 1850, "ly": 2025, "p": 3758, "al": ["san ildefonso", "San Ildefonso"]},
  {"key": "Jayllihuaya-Peru", "n": "Jayllihuaya", "c": "Peru", "r": "per_puno", "ll": [-15.8812, -69.9842], "ey": 1850, "ly": 2017, "p": 3758},
  {"key": "Chapuco-Chile", "n": "Chapuco", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.90681, -72.80675], "ey": 1350, "ly": 1500, "p": 3758, "al": ["lipingue", "Lipingue"]},
  {"key": "La Aguada-Argentina_2", "n": "La Aguada", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.00627, -64.40748], "ey": 80, "ly": 1500, "p": 3758},
  {"key": "Reporte mano_moler-Colombia", "n": "Reporte mano_moler", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.82208, -75.70463], "ey": -1000, "ly": 1500, "p": 3755, "al": ["reporte-ceramica-superficie_ceramicaperfil_sar", "reporte_acopio material ceramico desechado", "reporte_ceramica_perfil"]},
  {"key": "Facundo Vela-Ecuador", "n": "Facundo Vela", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.22039, -79.10123], "ey": 1850, "ly": 2025, "p": 3753},
  {"key": "Matara-Peru", "n": "Matara", "c": "Peru", "r": "per_cajamarca", "ll": [-7.25472, -78.25972], "ey": 1850, "ly": 2025, "p": 3752},
  {"key": "Cochrane-Chile", "n": "Cochrane", "c": "Chile", "r": "chl_region_de_aysen_del_gral_ibanez_del_campo", "ll": [-47.3974, -72.81512], "ey": 1970, "ly": 2025, "p": 3751},
  {"key": "Condine-Peru", "n": "Condine", "c": "Peru", "r": "inca_collasuyu", "ll": [-15.29728, -70.22338], "ey": -1000, "ly": 1530, "p": 3751},
  {"key": "Tabalí-Chile", "n": "Tabalí", "c": "Chile", "r": "chl_region_de_coquimbo", "ll": [-30.63671, -71.42562], "ey": 1525, "ly": 2017, "p": 3750, "al": ["tabali"]},
  {"key": "Huayrapata-Bolivia", "n": "Huayrapata", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-16.345, -67.605], "ey": 1525, "ly": 1825, "p": 3749},
  {"key": "Bahia de San Antonio-Argentina", "n": "Bahia de San Antonio", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-40.79795, -64.84075], "ey": -4028, "ly": 197, "p": 3749},
  {"key": "Nuevo Paraíso-Ecuador", "n": "Nuevo Paraíso", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.37728, -77.01382], "ey": 1920, "ly": 2025, "p": 3748},
  {"key": "Lacshagayan-Peru", "n": "Lacshagayan", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.81342, -76.56849], "ey": 1438, "ly": 1530, "p": 3748, "al": ["jarpo", "san juan de pajo", "Jarpo"]},
  {"key": "Purús-Peru", "n": "Purús", "c": "Peru", "r": "per_ucayali", "ll": [-9.77222, -70.70972], "ey": 1900, "ly": 2025, "p": 3746, "al": ["esperanza", "Esperanza"]},
  {"key": "Ancacata-Bolivia", "n": "Ancacata", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.817, -66.74], "ey": 1525, "ly": 1825, "p": 3746, "al": ["ancato", "Ancato"]},
  {"key": "Reloca-Chile_2", "n": "Reloca", "c": "Chile", "r": "crp_obispado_concepcion_chiloe", "ll": [-35.652, -72.533], "ey": 1525, "ly": 1830, "p": 3745, "al": ["riloca", "Riloca"]},
  {"key": "Urb. Desarrollo Camburito-Venezuela", "n": "Urb. Desarrollo Camburito", "c": "Venezuela", "r": "ven_portuguesa", "ll": [9.57984, -69.26946], "ey": 1850, "ly": 2011, "p": 3743},
  {"key": "Charta-Colombia", "n": "Charta", "c": "Colombia", "r": "col_santander", "ll": [7.28082, -72.9688], "ey": 1850, "ly": 2025, "p": 3741},
  {"key": "San Isidro Manabí-Ecuador", "n": "San Isidro Manabí", "c": "Ecuador", "r": "na_pacific_equatorial_valdivia", "ll": [-0.372, -80.184], "ey": -1500, "ly": 1100, "p": 3740},
  {"key": "Río Ibáñez-Chile", "n": "Río Ibáñez", "c": "Chile", "r": "chl_region_de_aysen_del_gral_ibanez_del_campo", "ll": [-46.30247, -72.38112], "ey": 1900, "ly": 2025, "p": 3736},
  {"key": "Limbani-Peru", "n": "Limbani", "c": "Peru", "r": "per_puno", "ll": [-14.14972, -69.69056], "ey": 1525, "ly": 2025, "p": 3734, "al": ["linba", "Linba"]},
  {"key": "San Cristóbal-Peru", "n": "San Cristóbal", "c": "Peru", "r": "per_moquegua", "ll": [-16.73917, -70.68333], "ey": 1525, "ly": 2025, "p": 3734, "al": ["calacoa", "cuchumbaya", "tijmilaca"]},
  {"key": "Chaloma-Peru", "n": "Chaloma", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-11.94257, -75.40515], "ey": 0, "ly": 1530, "p": 3734, "al": ["añashloma", "añasloma", "chaupiloma"]},
  {"key": "Muestreo 420-Colombia", "n": "Muestreo 420", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.50419, -75.79223], "ey": 1300, "ly": 1500, "p": 3734},
  {"key": "Intiwatana-Peru", "n": "Intiwatana", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.91414, -74.6985], "ey": -1000, "ly": 1530, "p": 3733, "al": ["chipta", "chiptan area", "Chipta"]},
  {"key": "La Carpa-Peru", "n": "La Carpa", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.92601, -78.24431], "ey": 0, "ly": 1530, "p": 3733, "al": ["la peña la yegua blanca", "abrigo del aluche", "cerro la fila"]},
  {"key": "San Francisco del Monte de Oro-Argentina", "n": "San Francisco del Monte de Oro", "c": "Argentina", "r": "arg_san_luis", "ll": [-32.60027, -66.12715], "ey": 1536, "ly": 2010, "p": 3732, "al": ["san francisco de monte de oro", "San Francisco de Monte de Oro"]},
  {"key": "Combaya-Bolivia", "n": "Combaya", "c": "Bolivia", "r": "bol_la_paz", "ll": [-15.80477, -68.75385], "ey": 1525, "ly": 2026, "p": 3731},
  {"key": "Cerro Tortolita-Peru", "n": "Cerro Tortolita", "c": "Peru", "r": "inca_contisuyu", "ll": [-13.89343, -75.64465], "ey": 0, "ly": 1530, "p": 3731, "al": ["casa blanca", "la banda", "las minas"]},
  {"key": "Ankasmarka-Peru", "n": "Ankasmarka", "c": "Peru", "r": "inca_antisuyu", "ll": [-13.23603, -71.90614], "ey": 0, "ly": 1530, "p": 3730, "al": ["llantusaya", "s.a. ranrapata", "Llantusaya"]},
  {"key": "Tucsumayo-Peru", "n": "Tucsumayo", "c": "Peru", "r": "inca_collasuyu", "ll": [-14.76358, -71.41939], "ey": 1000, "ly": 1530, "p": 3729},
  {"key": "Buenavista (col_quindio)-Colombia", "n": "Buenavista", "c": "Colombia", "r": "col_quindio", "ll": [4.36003, -75.73957], "ey": 1850, "ly": 2025, "p": 3727},
  {"key": "La Sirena-Colombia", "n": "La Sirena", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.40609, -76.57513], "ey": 1850, "ly": 2018, "p": 3727, "al": ["crucero alto de los mangos", "la luisa", "Crucero Alto de los Mangos"]},
  {"key": "Zona A - Sinifaná - Yacimiento 35 - Alto del Nudo-Colombia", "n": "Zona A - Sinifaná - Yacimiento 35 - Alto del Nudo", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.98269, -75.79707], "ey": 0, "ly": 1500, "p": 3725, "al": ["zona a - sinifaná - yacimiento 36 - alto del nevado", "Zona A - Sinifaná - Yacimiento 36 - Alto del Nevado"]},
  {"key": "Del Campillo-Argentina", "n": "Del Campillo", "c": "Argentina", "r": "arg_cordoba", "ll": [-34.37891, -64.49707], "ey": 1850, "ly": 2022, "p": 3721},
  {"key": "Acochaca-Peru", "n": "Acochaca", "c": "Peru", "r": "per_ancash", "ll": [-9.11472, -77.36833], "ey": 1850, "ly": 2025, "p": 3720},
  {"key": "San Jose Itacua-Argentina", "n": "San Jose Itacua", "c": "Argentina", "r": "crp_banda_oriental_misiones", "ll": [-27.771, -55.778], "ey": 1633, "ly": 1830, "p": 3720},
  {"key": "El Toronjil-Chile", "n": "El Toronjil", "c": "Chile", "r": "inca_collasuyu", "ll": [-33.13907, -71.56171], "ey": 0, "ly": 1532, "p": 3719, "al": ["casaloma", "el boldal", "el galpón"]},
  {"key": "Cluster 94. PS-Colombia", "n": "Cluster 94. PS", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [3.84702, -73.65673], "ey": 500, "ly": 1500, "p": 3719, "al": ["cluster 94. sitio arqueológico", "Cluster 94. Sitio arqueológico"]},
  {"key": "Huañagasta-Argentina", "n": "Huañagasta", "c": "Argentina", "r": "crp_gran_chaco_frontier", "ll": [-28.483, -63.067], "ey": 1741, "ly": 1830, "p": 3718},
  {"key": "Almirante Luis Brión-Venezuela", "n": "Almirante Luis Brión", "c": "Venezuela", "r": "ven_delta_amacuro", "ll": [8.19736, -61.52483], "ey": 1920, "ly": 2025, "p": 3715},
  {"key": "Carmen Alto (per_lima)-Peru", "n": "Carmen Alto", "c": "Peru", "r": "per_lima", "ll": [-13.033, -76.3323], "ey": 1850, "ly": 2017, "p": 3714},
  {"key": "Gaboto-Argentina", "n": "Gaboto", "c": "Argentina", "r": "arg_santa_fe", "ll": [-32.43252, -60.81788], "ey": 1850, "ly": 2022, "p": 3714},
  {"key": "Cocha Turiqu-Peru", "n": "Cocha Turiqu", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-3.78301, -76.56758], "ey": -1000, "ly": 1530, "p": 3714, "al": ["cocha tangarana", "santa maría", "Cocha Tangarana"]},
  {"key": "Rincón Hondo-Colombia", "n": "Rincón Hondo", "c": "Colombia", "r": "col_cesar", "ll": [9.39522, -73.48946], "ey": 1850, "ly": 2018, "p": 3713},
  {"key": "Quebrada Arrojadero-Peru", "n": "Quebrada Arrojadero", "c": "Peru", "r": "inca_collasuyu", "ll": [-17.78125, -70.62501], "ey": 1440, "ly": 1532, "p": 3713, "al": ["quebrada honda", "quebrada quebradilla", "cerro pelado"]},
  {"key": "General Campos-Argentina", "n": "General Campos", "c": "Argentina", "r": "arg_entre_rios", "ll": [-31.52339, -58.4058], "ey": 1850, "ly": 2022, "p": 3712},
  {"key": "Isla de San Antonio-Argentina", "n": "Isla de San Antonio", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.03334, -64.43333], "ey": 80, "ly": 1500, "p": 3712},
  {"key": "Kuywa Castillo-Peru", "n": "Kuywa Castillo", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.21857, -76.77871], "ey": 0, "ly": 1530, "p": 3711, "al": ["apu torre", "cerro portachuelo", "chaupis"]},
  {"key": "El Esfuerzo-Colombia", "n": "El Esfuerzo", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.6906, -78.78821], "ey": -1000, "ly": 1500, "p": 3711},
  {"key": "Cruz del Medano-Peru", "n": "Cruz del Medano", "c": "Peru", "r": "per_lambayeque", "ll": [-6.5134, -79.9591], "ey": 1850, "ly": 2017, "p": 3710, "al": ["lagartera", "las delicias", "san miguel"]},
  {"key": "Escaleras-Peru", "n": "Escaleras", "c": "Peru", "r": "inca_collasuyu", "ll": [-15.6611, -71.73082], "ey": 1000, "ly": 1530, "p": 3710, "al": ["aparaya", "malata", "putushina"]},
  {"key": "Francisco Fajardo-Venezuela", "n": "Francisco Fajardo", "c": "Venezuela", "r": "ven_nueva_esparta", "ll": [10.93856, -64.05181], "ey": 1850, "ly": 2025, "p": 3709},
  {"key": "Sapayurco-Colombia", "n": "Sapayurco", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [1.388, -77.493], "ey": 1525, "ly": 1830, "p": 3709, "al": ["sapallureo", "Sapallureo"]},
  {"key": "Unión Agua Blanca-Peru", "n": "Unión Agua Blanca", "c": "Peru", "r": "per_cajamarca", "ll": [-7.04667, -79.06056], "ey": 1850, "ly": 2025, "p": 3704, "al": ["agua blanca", "Agua Blanca"]},
  {"key": "Talale-Peru", "n": "Talale", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.39209, -74.79096], "ey": -1000, "ly": 1530, "p": 3704},
  {"key": "San Jose Arrecifes-Argentina", "n": "San Jose Arrecifes", "c": "Argentina", "r": "crp_intendencia_buenos_aires", "ll": [-34.067, -60.103], "ey": 1536, "ly": 1830, "p": 3703, "al": ["san jose fuerte de arrecifes", "San Jose Fuerte de Arrecifes"]},
  {"key": "El Volador-Colombia", "n": "El Volador", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.07142, -75.00187], "ey": -2000, "ly": 1500, "p": 3702, "al": ["lusiana", "rancho serrano", "Lusiana"]},
  {"key": "La Primavera-Argentina_2", "n": "La Primavera", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-47.804, -69.02144], "ey": -1307, "ly": -233, "p": 3702},
  {"key": "Collana (bol_la_paz)-Bolivia", "n": "Collana", "c": "Bolivia", "r": "bol_la_paz", "ll": [-16.90407, -68.28337], "ey": 1850, "ly": 2024, "p": 3701},
  {"key": "Los Helechos-Argentina", "n": "Los Helechos", "c": "Argentina", "r": "arg_misiones", "ll": [-27.55318, -55.07782], "ey": 1900, "ly": 2022, "p": 3701},
  {"key": "Mocha-Chile", "n": "Mocha", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.812, -69.276], "ey": 1525, "ly": 1825, "p": 3701},
  {"key": "Traful I Cave-Argentina", "n": "Traful I Cave", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-40.7166, -71.1138], "ey": -8774, "ly": 298, "p": 3701, "al": ["cueva traful", "Cueva Traful"]},
  {"key": "Lag. de los Gansos-Argentina", "n": "Lag. de los Gansos", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-32.5018, -60.645], "ey": 402, "ly": 1500, "p": 3700},
  {"key": "Chiquinquira Borotare-Colombia", "n": "Chiquinquira Borotare", "c": "Colombia", "r": "vng_cartagena_santa_marta", "ll": [8.4, -73.424], "ey": 1525, "ly": 1830, "p": 3699, "al": ["bororare", "Bororare"]},
  {"key": "Urundel-Argentina", "n": "Urundel", "c": "Argentina", "r": "arg_salta", "ll": [-23.55784, -64.39697], "ey": 1850, "ly": 2022, "p": 3697},
  {"key": "San Martin de Sechura-Peru", "n": "San Martin de Sechura", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-5.53858, -80.7771], "ey": -2000, "ly": 1530, "p": 3695, "ex": [{"date": "1961.1.1", "name": "Sechura"}], "al": ["chuchal", "chusis", "Chuchal"]},
  {"key": "Galán-Colombia", "n": "Galán", "c": "Colombia", "r": "col_santander", "ll": [6.63842, -73.28777], "ey": 1773, "ly": 2025, "p": 3693, "al": ["galan", "robadera", "rova"]},
  {"key": "Ccochaccasa-Peru", "n": "Ccochaccasa", "c": "Peru", "r": "per_huancavelica", "ll": [-12.92528, -74.77028], "ey": 1850, "ly": 2025, "p": 3693},
  {"key": "Buenos Aires (na_caribbean_maracaibo_tairona)-Colombia", "n": "Buenos Aires", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [9.38902, -75.66559], "ey": 1300, "ly": 1500, "p": 3693, "al": ["pozos de sondeo", "yacimiento", "abriles"]},
  {"key": "Pueblo Nuevo (col_norte_de_santander_2)-Colombia", "n": "Pueblo Nuevo", "c": "Colombia", "r": "col_norte_de_santander", "ll": [8.23122, -73.39171], "ey": 1525, "ly": 2018, "p": 3692, "al": ["san diego pueblo nuevo", "San Diego Pueblo Nuevo"]},
  {"key": "Sancti Spiritu-Argentina", "n": "Sancti Spiritu", "c": "Argentina", "r": "arg_santa_fe", "ll": [-34.00765, -62.24145], "ey": 1850, "ly": 2022, "p": 3692},
  {"key": "Chapinero-Colombia_2", "n": "Chapinero", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.57, -75.75], "ey": -1000, "ly": 1500, "p": 3692, "al": ["no informa", "No informa"]},
  {"key": "Guadalupe-Ecuador", "n": "Guadalupe", "c": "Ecuador", "r": "ecu_zamora_chinchipe", "ll": [-3.84443, -78.8896], "ey": 1920, "ly": 2025, "p": 3691},
  {"key": "Tarapaya-Bolivia", "n": "Tarapaya", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-19.475, -65.797], "ey": 1525, "ly": 1825, "p": 3691},
  {"key": "Ciudad de Dios (per_lambayeque)-Peru", "n": "Ciudad de Dios", "c": "Peru", "r": "per_lambayeque", "ll": [-6.7735, -79.921], "ey": 1850, "ly": 2017, "p": 3686},
  {"key": "Batatillo-Venezuela", "n": "Batatillo", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.75722, -70.42111], "ey": 1850, "ly": 2011, "p": 3685},
  {"key": "Vichacla-Bolivia", "n": "Vichacla", "c": "Bolivia", "r": "bol_potosi", "ll": [-20.63281, -65.58922], "ey": 1525, "ly": 2024, "p": 3684},
  {"key": "Wayawillka-Peru", "n": "Wayawillka", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.04425, -73.55888], "ey": 0, "ly": 1530, "p": 3682, "al": ["puito apupuyka", "Puito Apupuyka"]},
  {"key": "Pedro Briceño Méndez-Venezuela", "n": "Pedro Briceño Méndez", "c": "Venezuela", "r": "ven_barinas", "ll": [8.01167, -70.975], "ey": 1850, "ly": 2025, "p": 3681}
]

HEADERS = {'User-Agent': 'OperationViscountToponymy/1.0 (research)'}

def api_get(lang, params):
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

def fetch_page_info(lang, title):
    data = api_get(lang, {
        'action': 'query',
        'titles': title,
        'prop': 'extracts|revisions',
        'exintro': 'false',
        'explaintext': 'true',
        'exchars': '6000',
        'rvprop': 'content',
        'rvslots': 'main',
        'format': 'json'
    })
    pages = data.get('query', {}).get('pages', {})
    for pid, p in pages.items():
        if pid == '-1':
            continue
        extract = p.get('extract', '')
        wikitext = ''
        revs = p.get('revisions', [])
        if revs:
            wikitext = revs[0].get('slots', {}).get('main', {}).get('*', '')[:4000]
        return {'title': p.get('title'), 'extract': extract, 'wikitext_head': wikitext}
    return None

results = {}
for idx, s in enumerate(SETTLEMENTS):
    k = s['key']
    lat, lng = s['ll']
    n = s['n']
    c = s['c']
    entry = {'n': n, 'c': c, 'r': s['r'], 'll': s['ll'], 'ey': s['ey'], 'ly': s['ly'], 'al': s.get('al', []), 'ex': s.get('ex', [])}
    
    # Skip geosearch for obvious raw archaeological survey sample names if desired, or run geosearch on all
    try:
        geo = api_get('es', {
            'action': 'query',
            'list': 'geosearch',
            'gscoord': f'{lat}|{lng}',
            'gsradius': '10000',
            'gslimit': '5',
            'format': 'json'
        })
        geo_titles = [(g['title'], g['dist']) for g in geo.get('query', {}).get('geosearch', [])]
    except Exception as e:
        geo_titles = [('ERR', str(e))]
    
    # Text search on es.wikipedia
    r_clean = re.sub(r'^(chl_region_de_|arg_|per_|bol_|ven_|col_|ecu_|na_|sc_|inca_|crp_|vng_|vp_)', '', s['r']).replace('_', ' ')
    q = f'"{n}" {c}'
    try:
        sr = api_get('es', {
            'action': 'query',
            'list': 'search',
            'srsearch': q,
            'srlimit': '5',
            'format': 'json'
        })
        sr_titles = [x['title'] for x in sr.get('query', {}).get('search', [])]
    except Exception as e:
        sr_titles = []
    
    entry['geo_es'] = geo_titles
    entry['sr_es'] = sr_titles
    
    # Fetch best matching page
    chosen = None
    for gt, dist in geo_titles:
        if isinstance(dist, (int, float)) and (n.lower() in gt.lower() or dist < 3000):
            chosen = gt
            break
    if not chosen and sr_titles:
        for st in sr_titles:
            if n.lower() in st.lower():
                chosen = st
                break
    if chosen:
        try:
            entry['page_es'] = fetch_page_info('es', chosen)
        except Exception as e:
            entry['page_es'] = {'err': str(e)}
    
    results[k] = entry
    if idx % 15 == 0:
        print(f"Processed {idx}/90", flush=True)

with open(r'f:\Active Projects\Project 1509 - SVEA\tests\chunk045_wiki.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Done all 90")
