import json, os, glob, urllib.request, urllib.parse, concurrent.futures, math

INPUT = [
  {"key": "Diguillin-Chile_2", "n": "Diguillin", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-36.87782, -72.30294], "ey": 0, "ly": 1500, "p": 5966},
  {"key": "La Florida-Argentina", "n": "La Florida", "c": "Argentina", "r": "arg_tucuman", "ll": [-26.81717, -65.08799], "ey": 1850, "ly": 2010, "p": 5959},
  {"key": "Caraqueño-Peru", "n": "Caraqueño", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.63481, -77.73521], "ey": -2000, "ly": 1530, "p": 5957, "ex": [{"date": "1940.1.1", "name": "Pativilca"}], "al": ["anexo lindero", "capitana", "caraqueño bajo"]},
  {"key": "Alto de los Ídolos-Colombia", "n": "Alto de los Ídolos", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [1.926, -76.224], "ey": -1000, "ly": 1500, "p": 5957, "al": ["alto de los idolos", "isnos", "meseta a"]},
  {"key": "Gps-Colombia", "n": "Gps", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.2002, -74.81536], "ey": 0, "ly": 1500, "p": 5952, "al": ["sua", "yacimiento 5 km 30+", "yacimiento 6 km. 30 +"]},
  {"key": "Insculas-Peru", "n": "Insculas", "c": "Peru", "r": "per_lambayeque", "ll": [-5.7566, -79.8592], "ey": 1525, "ly": 2017, "p": 5949, "al": ["las mercedes", "señor de los milagros", "Las Mercedes"]},
  {"key": "Moroturo-Venezuela", "n": "Moroturo", "c": "Venezuela", "r": "ven_lara", "ll": [10.60519, -69.27254], "ey": 1780, "ly": 2025, "p": 5947, "al": ["parupano", "valle de moroturo", "Parupano"]},
  {"key": "Santo Domingo Pocoto-Peru", "n": "Santo Domingo Pocoto", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.654, -76.155], "ey": 1525, "ly": 1825, "p": 5947, "al": ["picoto", "Picoto"]},
  {"key": "Uia-Colombia", "n": "Uia", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.1184, -74.55492], "ey": 1300, "ly": 1500, "p": 5947},
  {"key": "Quilaquila-Bolivia", "n": "Quilaquila", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-19.12, -65.377], "ey": 1525, "ly": 1825, "p": 5944, "al": ["qullaquila", "Qullaquila"]},
  {"key": "San Pedro (per_ancash)-Peru", "n": "San Pedro", "c": "Peru", "r": "per_ancash", "ll": [-10.37194, -77.48722], "ey": 1525, "ly": 2025, "p": 5942, "al": ["copa", "Copa"]},
  {"key": "Sillkinchan-Peru", "n": "Sillkinchan", "c": "Peru", "r": "inca_cuzco_heartland", "ll": [-13.56135, -71.84051], "ey": 1440, "ly": 1532, "p": 5940, "al": ["andenes de angostura", "andenes de roquepata", "andenes de leticia"]},
  {"key": "Tres de Febrero-Venezuela", "n": "Tres de Febrero", "c": "Venezuela", "r": "ven_zulia", "ll": [9.58389, -70.97389], "ey": 1900, "ly": 2025, "p": 5938},
  {"key": "Chocho-Colombia", "n": "Chocho", "c": "Colombia", "r": "col_sucre", "ll": [9.24772, -75.34227], "ey": 1850, "ly": 2018, "p": 5936},
  {"key": "José Gregorio Bastidas-Venezuela", "n": "José Gregorio Bastidas", "c": "Venezuela", "r": "ven_lara", "ll": [10.02278, -69.24444], "ey": 1850, "ly": 2025, "p": 5936},
  {"key": "Callapampa-Peru", "n": "Callapampa", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-11.73, -75.948], "ey": 1525, "ly": 1825, "p": 5933, "al": ["collapampa", "Collapampa"]},
  {"key": "Llangas-Peru", "n": "Llangas", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.852, -75.959], "ey": 1525, "ly": 1825, "p": 5933},
  {"key": "Palmar-Colombia_2", "n": "Palmar", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.62214, -78.72146], "ey": 1300, "ly": 1500, "p": 5933, "al": ["catalina", "Catalina"]},
  {"key": "San Pablo (ecu_bolivar)-Ecuador", "n": "San Pablo", "c": "Ecuador", "r": "ecu_bolivar", "ll": [-1.81698, -79.05473], "ey": 1850, "ly": 2025, "p": 5932},
  {"key": "San Antonio de Antaparco-Peru", "n": "San Antonio de Antaparco", "c": "Peru", "r": "per_huancavelica", "ll": [-13.07611, -74.41167], "ey": 1525, "ly": 2025, "p": 5931, "al": ["antaparco", "antarpanco", "Antaparco"]},
  {"key": "Sara Sara-Peru", "n": "Sara Sara", "c": "Peru", "r": "per_ayacucho", "ll": [-15.24528, -73.45306], "ey": -1000, "ly": 2025, "p": 5931, "al": ["quilcata", "pillullorqo", "huancopampa"]},
  {"key": "Huaca de Loro-Peru", "n": "Huaca de Loro", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.968, -74.87762], "ey": 500, "ly": 1530, "p": 5926},
  {"key": "Yacimiento 8 Km. 34 +-Colombia", "n": "Yacimiento 8 Km. 34 +", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.1887, -74.84353], "ey": 500, "ly": 1500, "p": 5925, "al": ["vergelito", "Vergelito"]},
  {"key": "La Punta-Peru", "n": "La Punta", "c": "Peru", "r": "per_junin", "ll": [-12.1171, -75.1801], "ey": 1850, "ly": 2017, "p": 5923, "al": ["azapampa", "Azapampa"]},
  {"key": "Los Caprichos-Venezuela", "n": "Los Caprichos", "c": "Venezuela", "r": "ven_trujillo", "ll": [9.84667, -70.66], "ey": 1850, "ly": 2025, "p": 5922},
  {"key": "Vilca-Peru", "n": "Vilca", "c": "Peru", "r": "per_huancavelica", "ll": [-12.47722, -75.18333], "ey": 1525, "ly": 2025, "p": 5921, "al": ["vilcabamba", "Vilcabamba"]},
  {"key": "Montalvo (ecu_esmeraldas)-Ecuador", "n": "Montalvo", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.90351, -79.26862], "ey": 1850, "ly": 2025, "p": 5920},
  {"key": "Gladiador-Colombia", "n": "Gladiador", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.26736, -74.7829], "ey": -1000, "ly": 1500, "p": 5917, "al": ["hf_ceramica_ aeropuerto_santiagovila_mcpio_flandes_tolima", "punto", "HF_Ceramica_ Aeropuerto_SantiagoVila_Mcpio_Flandes_Tolima"]},
  {"key": "Santiago Apostol del Cercado-Peru", "n": "Santiago Apostol del Cercado", "c": "Peru", "r": "vp_intendencia_lima", "ll": [-12.05, -77.012], "ey": 1525, "ly": 1825, "p": 5915, "al": ["santa ana", "Santa Ana"]},
  {"key": "San Miguel (col_santander)-Colombia", "n": "San Miguel", "c": "Colombia", "r": "col_santander", "ll": [6.57531, -72.64412], "ey": 1525, "ly": 2025, "p": 5910},
  {"key": "Ñomala-Peru", "n": "Ñomala", "c": "Peru", "r": "per_piura", "ll": [-5.0666, -80.2404], "ey": 1525, "ly": 2017, "p": 5909, "al": ["alto talarita", "nomala", "santa rosa de ñomala"]},
  {"key": "Globo Delta 1A- Yacimiento-Colombia", "n": "Globo Delta 1A- Yacimiento", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [10.51212, -75.45775], "ey": 1300, "ly": 1500, "p": 5902},
  {"key": "San Sebastián Del Coca-Ecuador", "n": "San Sebastián Del Coca", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.33868, -77.00428], "ey": 1920, "ly": 2025, "p": 5901},
  {"key": "Acostambo (vp_intendencia_huamanga_huancavelica_2)-Peru", "n": "Acostambo", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-13.286, -74.933], "ey": 1525, "ly": 1825, "p": 5901, "al": ["acostamba", "Acostamba"]},
  {"key": "Puerto Pechiche-Ecuador", "n": "Puerto Pechiche", "c": "Ecuador", "r": "ecu_los_rios", "ll": [-1.42696, -79.54025], "ey": 1850, "ly": 2025, "p": 5893},
  {"key": "Huaca El Milagro-Peru", "n": "Huaca El Milagro", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.79076, -79.69826], "ey": -2000, "ly": 1530, "p": 5892, "al": ["el arenal", "el combo", "huaca los chinos"]},
  {"key": "Concepcion de Caja-Peru", "n": "Concepcion de Caja", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-14.859, -74.349], "ey": 1525, "ly": 1825, "p": 5891},
  {"key": "Villa Ascasubi-Argentina", "n": "Villa Ascasubi", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.16279, -63.89241], "ey": 1536, "ly": 2022, "p": 5890, "ex": [{"date": "1947.1.1", "name": "Río Tercero"}], "al": ["rio tercero abajo", "Rio Tercero abajo"]},
  {"key": "Rapaz-Peru", "n": "Rapaz", "c": "Peru", "r": "per_lima", "ll": [-10.8739, -76.705], "ey": 1525, "ly": 2017, "p": 5887, "al": ["rapas", "Rapas"]},
  {"key": "Palagua-Colombia", "n": "Palagua", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.08097, -74.55943], "ey": 1300, "ly": 1500, "p": 5886},
  {"key": "Ciruelos-Chile_2", "n": "Ciruelos", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.81175, -72.73274], "ey": 1350, "ly": 1500, "p": 5886, "al": ["cuyincahuin", "Cuyincahuin"]},
  {"key": "Chapal-Colombia", "n": "Chapal", "c": "Colombia", "r": "col_narino", "ll": [0.94149, -77.45631], "ey": 1525, "ly": 2018, "p": 5884, "al": ["chaparral", "Chaparral"]},
  {"key": "Asogasta-Argentina", "n": "Asogasta", "c": "Argentina", "r": "crp_gran_chaco_frontier", "ll": [-27.739, -63.576], "ey": 1536, "ly": 1830, "p": 5883, "al": ["arsogasta", "Arsogasta"]},
  {"key": "Cisnes-Chile", "n": "Cisnes", "c": "Chile", "r": "chl_region_de_aysen_del_gral_ibanez_del_campo", "ll": [-44.65065, -73.16552], "ey": 1900, "ly": 2025, "p": 5878},
  {"key": "Uribe (col_narino)-Colombia", "n": "Uribe", "c": "Colombia", "r": "col_narino", "ll": [1.01988, -77.65243], "ey": 1525, "ly": 2018, "p": 5877, "al": ["malaver", "malave", "malhaber"]},
  {"key": "Bellavista (ecu_el_oro)-Ecuador", "n": "Bellavista", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.51228, -79.96752], "ey": 1850, "ly": 2025, "p": 5876},
  {"key": "Catanga-Colombia", "n": "Catanga", "c": "Colombia", "r": "na_orinoco_llanos_guayana", "ll": [5.15, -72.26], "ey": 1282, "ly": 1500, "p": 5874},
  {"key": "Cedros-Peru", "n": "Cedros", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.118, -71.611], "ey": 1525, "ly": 1825, "p": 5873},
  {"key": "Mangomarca-Peru", "n": "Mangomarca", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.01505, -76.98123], "ey": 1438, "ly": 1530, "p": 5873, "al": ["campo santo alto", "canto chico", "cerro gramal"]},
  {"key": "Estero Curaco-Chile", "n": "Estero Curaco", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-37.28283, -72.67216], "ey": 0, "ly": 1500, "p": 5871, "al": ["el crucero", "estero las toscas", "tapicura"]},
  {"key": "Matara-Argentina", "n": "Matara", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-28.177, -63.279], "ey": 1536, "ly": 1830, "p": 5869, "al": ["mathala", "Mathala"]},
  {"key": "Chirimoyo-Peru", "n": "Chirimoyo", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.1997, -76.80938], "ey": 0, "ly": 1532, "p": 5868, "al": ["amancaes c", "el volcan", "pueblo viejo pucará"]},
  {"key": "Chontamarca-Ecuador", "n": "Chontamarca", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.38244, -79.14674], "ey": 1850, "ly": 2025, "p": 5867},
  {"key": "Querco-Peru", "n": "Querco", "c": "Peru", "r": "per_huancavelica", "ll": [-13.97944, -74.97694], "ey": 1525, "ly": 2025, "p": 5867},
  {"key": "Llano de Jorge-Venezuela", "n": "Llano de Jorge", "c": "Venezuela", "r": "ven_tachira", "ll": [7.78833, -72.45389], "ey": 1850, "ly": 2011, "p": 5865},
  {"key": "Villacur-Peru", "n": "Villacur", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-13.88606, -75.9983], "ey": -3000, "ly": 1530, "p": 5864, "al": ["villacuri", "Villacuri"]},
  {"key": "Cahuayo-Bolivia", "n": "Cahuayo", "c": "Bolivia", "r": "bol_oruro", "ll": [-19.2822, -66.19638], "ey": 1525, "ly": 2024, "p": 5861},
  {"key": "Arroyo Fredes-Argentina", "n": "Arroyo Fredes", "c": "Argentina", "r": "sc_parana_uruguay_charrua", "ll": [-34.209, -58.568], "ey": 953, "ly": 1500, "p": 5861},
  {"key": "Sucre-Peru", "n": "Sucre", "c": "Peru", "r": "per_cajamarca", "ll": [-6.94278, -78.13528], "ey": 1850, "ly": 2025, "p": 5860},
  {"key": "Chimor-Peru_2", "n": "Chimor", "c": "Peru", "r": "vp_intendencia_cusco", "ll": [-13.143, -71.633], "ey": 1525, "ly": 1825, "p": 5854},
  {"key": "Itcacachi-Bolivia", "n": "Itcacachi", "c": "Bolivia", "r": "vp_intendencia_puno", "ll": [-15.995, -68.736], "ey": 1525, "ly": 1825, "p": 5854, "al": ["ilcacachi", "Ilcacachi"]},
  {"key": "Limoncito-Colombia", "n": "Limoncito", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [8.107, -72.568], "ey": 1785, "ly": 1830, "p": 5853},
  {"key": "Timborbamba-Peru", "n": "Timborbamba", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-5.735, -78.45], "ey": 1525, "ly": 1830, "p": 5851},
  {"key": "Barranca de Los Loros-Argentina", "n": "Barranca de Los Loros", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.71118, -64.82486], "ey": 80, "ly": 1500, "p": 5849},
  {"key": "Santa Elena-Ecuador_3", "n": "Santa Elena", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-2.12, -80.57], "ey": -8809, "ly": -3738, "p": 5845},
  {"key": "Tolhuin-Argentina", "n": "Tolhuin", "c": "Argentina", "r": "arg_tierra_del_fuego", "ll": [-54.51135, -67.19522], "ey": 1980, "ly": 2022, "p": 5843},
  {"key": "Guaraciña-Chile", "n": "Guaraciña", "c": "Chile", "r": "vp_intendencia_arequipa", "ll": [-19.95, -69.539], "ey": 1525, "ly": 1825, "p": 5840},
  {"key": "Paria Oruro-Bolivia", "n": "Paria Oruro", "c": "Bolivia", "r": "ca_titicaca_altiplano_tiwanaku", "ll": [-17.834, -66.985], "ey": 900, "ly": 1430, "p": 5840},
  {"key": "Cunchibamba-Ecuador", "n": "Cunchibamba", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-1.13031, -78.5933], "ey": 1850, "ly": 2025, "p": 5839},
  {"key": "Santa Lucia Yaritagua-Venezuela", "n": "Santa Lucia Yaritagua", "c": "Venezuela", "r": "vng_capitania_caracas_maracaibo", "ll": [10.08, -69.126], "ey": 1538, "ly": 1830, "p": 5836},
  {"key": "Oliveros-Argentina", "n": "Oliveros", "c": "Argentina", "r": "arg_santa_fe", "ll": [-32.57393, -60.85475], "ey": 1850, "ly": 2022, "p": 5835},
  {"key": "Ojo de Agua-Argentina", "n": "Ojo de Agua", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-29.501, -63.694], "ey": 1536, "ly": 1830, "p": 5831},
  {"key": "Colonia Santa Fe-Chile", "n": "Colonia Santa Fe", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-37.49089, -72.59966], "ey": 0, "ly": 1500, "p": 5831, "al": ["bocatoma santa fe", "Bocatoma Santa Fe"]},
  {"key": "Gancedo-Argentina", "n": "Gancedo", "c": "Argentina", "r": "arg_chaco", "ll": [-27.49084, -61.67649], "ey": 1900, "ly": 2022, "p": 5829},
  {"key": "San José de la Dormida-Argentina", "n": "San José de la Dormida", "c": "Argentina", "r": "arg_cordoba", "ll": [-30.35627, -63.95042], "ey": 1850, "ly": 2022, "p": 5828},
  {"key": "Colón (col_putumayo)-Colombia", "n": "Colón", "c": "Colombia", "r": "col_putumayo", "ll": [1.19013, -76.97257], "ey": 1900, "ly": 2025, "p": 5827},
  {"key": "Cotos-Peru", "n": "Cotos", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-8.203, -78.3], "ey": 1525, "ly": 1825, "p": 5827},
  {"key": "Colonia Benítez-Argentina", "n": "Colonia Benítez", "c": "Argentina", "r": "arg_chaco", "ll": [-27.32949, -58.95015], "ey": 1900, "ly": 2022, "p": 5824},
  {"key": "Ciénaga Honda-Colombia", "n": "Ciénaga Honda", "c": "Colombia", "r": "col_cauca", "ll": [3.09296, -76.41111], "ey": 1525, "ly": 2018, "p": 5823, "al": ["la dominga", "La Dominga"]},
  {"key": "Bella Unión-Peru", "n": "Bella Unión", "c": "Peru", "r": "per_arequipa", "ll": [-15.45056, -74.65833], "ey": 1850, "ly": 2025, "p": 5823},
  {"key": "Moralba-Colombia", "n": "Moralba", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [3.92, -76.34], "ey": -1259, "ly": 1500, "p": 5820},
  {"key": "General Levalle-Argentina", "n": "General Levalle", "c": "Argentina", "r": "arg_cordoba", "ll": [-34.00723, -63.92339], "ey": 1850, "ly": 2022, "p": 5815},
  {"key": "Naranjillo-Peru", "n": "Naranjillo", "c": "Peru", "r": "per_san_martin", "ll": [-5.8054, -77.3972], "ey": 1920, "ly": 2017, "p": 5814, "al": ["shampuyacu", "Shampuyacu"]},
  {"key": "Engativa-Colombia", "n": "Engativa", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [4.688, -74.145], "ey": 1525, "ly": 1830, "p": 5814},
  {"key": "La Jagua-Colombia", "n": "La Jagua", "c": "Colombia", "r": "col_huila", "ll": [2.16781, -75.67835], "ey": 0, "ly": 2018, "p": 5812, "al": ["jagua", "Jagua"]},
  {"key": "Chavin-Peru", "n": "Chavin", "c": "Peru", "r": "per_ica", "ll": [-13.07639, -75.91306], "ey": 1525, "ly": 2025, "p": 5812, "al": ["chavín", "Chavín"]},
  {"key": "Colimba-Colombia", "n": "Colimba", "c": "Colombia", "r": "col_narino", "ll": [1.0093, -77.76024], "ey": 1525, "ly": 2018, "p": 5811, "al": ["quetambúd", "Quetambúd"]},
  {"key": "Castro Barros-Argentina", "n": "Castro Barros", "c": "Argentina", "r": "arg_la_rioja", "ll": [-30.58, -65.72741], "ey": 1850, "ly": 2022, "p": 5810},
  {"key": "General Galarza-Argentina", "n": "General Galarza", "c": "Argentina", "r": "arg_entre_rios", "ll": [-32.7204, -59.39587], "ey": 1850, "ly": 2022, "p": 5808},
  {"key": "Matanza-Colombia", "n": "Matanza", "c": "Colombia", "r": "col_santander", "ll": [7.32317, -73.01557], "ey": 1720, "ly": 2025, "p": 5807, "al": ["la matanza", "La Matanza"]}
]

def wp_geo(lat, lng, lang="es"):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
  req = urllib.request.Request(url, headers={"User-Agent": "SVEA-Research/1.0"})
  try:
    with urllib.request.urlopen(req, timeout=10) as r:
      d = json.loads(r.read().decode())
      return [f"{x['title']} ({int(x['dist'])}m)" for x in d.get("query", {}).get("geosearch", [])]
  except Exception as e:
    return [f"ERR:{e}"]

def wp_search(q, lang="es"):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=3&format=json"
  req = urllib.request.Request(url, headers={"User-Agent": "SVEA-Research/1.0"})
  try:
    with urllib.request.urlopen(req, timeout=10) as r:
      d = json.loads(r.read().decode())
      return [x["title"] for x in d.get("query", {}).get("search", [])]
  except Exception as e:
    return [f"ERR:{e}"]

def lookup(item):
  lat, lng = item["ll"]
  geo_es = wp_geo(lat, lng, "es")
  srch_es = wp_search(f"{item['n']} {item['c']}", "es")
  return {"key": item["key"], "n": item["n"], "c": item["c"], "r": item["r"], "ey": item["ey"], "ly": item["ly"], "geo_es": geo_es, "srch_es": srch_es}

with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
  res = list(ex.map(lookup, INPUT))

with open("tests/chunk026_wp.json", "w", encoding="utf-8") as f:
  json.dump(res, f, ensure_ascii=False, indent=2)
print("Saved", len(res), "entries")
