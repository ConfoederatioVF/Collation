import json
import urllib.request
import urllib.parse
import time
import sys

SETTLEMENTS = [
  {"key": "San Juan de la Virgen-Peru", "n": "San Juan de la Virgen", "c": "Peru", "r": "per_tumbes", "ll": [-3.62778, -80.43361], "ey": 1850, "ly": 2025, "p": 5257},
  {"key": "Huancane-Bolivia_2", "n": "Huancane", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-18.706, -66.876], "ey": 1525, "ly": 1825, "p": 5257},
  {"key": "Guaraunos-Venezuela", "n": "Guaraunos", "c": "Venezuela", "r": "ven_sucre", "ll": [10.55689, -63.12233], "ey": 1850, "ly": 2025, "p": 5252},
  {"key": "Manglares-Colombia", "n": "Manglares", "c": "Colombia", "r": "vng_guayaquil_esmeraldas", "ll": [1.62, -78.992], "ey": 1525, "ly": 1830, "p": 5251},
  {"key": "Cerro Escute (escute)-Peru", "n": "Cerro Escute (escute)", "c": "Peru", "r": "per_lambayeque", "ll": [-6.4515, -79.843], "ey": -1000, "ly": 2017, "p": 5245, "al": ["cerro escute", "culpon bajo", "huaca riendero"]},
  {"key": "Placilla (chl_region_de_valparaiso)-Chile", "n": "Placilla", "c": "Chile", "r": "chl_region_de_valparaiso", "ll": [-32.44827, -71.28449], "ey": 1525, "ly": 2017, "p": 5245, "al": ["plazilla", "Plazilla"]},
  {"key": "Médanos-Argentina", "n": "Médanos", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-38.8292, -62.69355], "ey": 1850, "ly": 2010, "p": 5245},
  {"key": "Curipunta-Peru", "n": "Curipunta", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-9.69262, -76.66175], "ey": 500, "ly": 1530, "p": 5244, "al": ["estaca machay", "garo", "huarajirca"]},
  {"key": "Mogrovejo-Argentina", "n": "Mogrovejo", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.75696, -64.78418], "ey": 450, "ly": 1500, "p": 5244},
  {"key": "Tamarindo-Peru", "n": "Tamarindo", "c": "Peru", "r": "per_piura", "ll": [-4.87833, -80.97583], "ey": 1850, "ly": 2025, "p": 5243},
  {"key": "Amalia Site-Argentina", "n": "Amalia Site", "c": "Argentina", "r": "sc_pampas_salado_colorado", "ll": [-38.15794, -57.94306], "ey": -9919, "ly": -5885, "p": 5240},
  {"key": "Yotala Yampara-Bolivia", "n": "Yotala Yampara", "c": "Bolivia", "r": "ca_eastern_montana_yungas", "ll": [-19.16, -65.264], "ey": 900, "ly": 1430, "p": 5240, "al": ["yampara", "Yampara"]},
  {"key": "Comanche-Bolivia", "n": "Comanche", "c": "Bolivia", "r": "bol_la_paz", "ll": [-17.06667, -68.41667], "ey": 1750, "ly": 2026, "p": 5238},
  {"key": "Vallecito-Argentina_2", "n": "Vallecito", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-27.704, -64.287], "ey": 1536, "ly": 1830, "p": 5237, "al": ["laguna larga", "Laguna Larga"]},
  {"key": "Buena Vista Alta-Peru", "n": "Buena Vista Alta", "c": "Peru", "r": "per_ancash", "ll": [-9.4325, -78.20694], "ey": 1850, "ly": 2025, "p": 5233},
  {"key": "Naranjal-Colombia_2", "n": "Naranjal", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [4.797, -75.962], "ey": 1525, "ly": 1830, "p": 5232},
  {"key": "Manú-Ecuador", "n": "Manú", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.52636, -79.42559], "ey": 1525, "ly": 2025, "p": 5230, "al": ["manu", "mano", "Manu"]},
  {"key": "Agricola Quinchilca-Chile", "n": "Agricola Quinchilca", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-39.86634, -72.75552], "ey": 1350, "ly": 1500, "p": 5230, "al": ["cancura tampe", "el castaño", "Cancura Tampe"]},
  {"key": "Dos Caminos-Colombia", "n": "Dos Caminos", "c": "Colombia", "r": "vng_santafe_tunja_highlands", "ll": [4.642, -74.449], "ey": 1538, "ly": 1776, "p": 5226, "al": ["guayabal de la mesa", "mesa de juan diaz", "santa barbara guayabal"]},
  {"key": "Muyupampa-Bolivia", "n": "Muyupampa", "c": "Bolivia", "r": "bol_chuquisaca", "ll": [-19.89614, -63.75353], "ey": 1850, "ly": 2024, "p": 5221},
  {"key": "Puerto Misahuallí-Ecuador", "n": "Puerto Misahuallí", "c": "Ecuador", "r": "ecu_napo", "ll": [-1.03387, -77.66862], "ey": 1850, "ly": 2025, "p": 5220},
  {"key": "Santiago de las Montañas-Peru", "n": "Santiago de las Montañas", "c": "Peru", "r": "vng_audiencia_quito_sierra", "ll": [-4.435, -77.645], "ey": 1558, "ly": 1830, "p": 5219},
  {"key": "Villagómez-Colombia", "n": "Villagómez", "c": "Colombia", "r": "col_cundinamarca", "ll": [5.27302, -74.19514], "ey": 1850, "ly": 2025, "p": 5218},
  {"key": "Uverito (ven_anzoategui)-Venezuela", "n": "Uverito", "c": "Venezuela", "r": "ven_anzoategui", "ll": [8.11406, -64.68459], "ey": 1850, "ly": 2025, "p": 5217},
  {"key": "Cerro Mulato-Peru", "n": "Cerro Mulato", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-6.62757, -79.38856], "ey": -1000, "ly": 1530, "p": 5217, "al": ["huaca chaquiras", "huaca pais", "cerro fortaleza"]},
  {"key": "Punto arqueológico-Colombia", "n": "Punto arqueológico", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.49742, -74.64888], "ey": -280, "ly": 1500, "p": 5216, "al": ["salcedo", "quintas", "Quintas"]},
  {"key": "Añancusi-Peru", "n": "Añancusi", "c": "Peru", "r": "per_huancavelica", "ll": [-12.587, -74.7154], "ey": 1525, "ly": 2017, "p": 5214, "al": ["pallala", "pallalla", "Pallalla"]},
  {"key": "Nenegal-Colombia", "n": "Nenegal", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [0.885, -77.682], "ey": 1525, "ly": 1830, "p": 5214},
  {"key": "Rs W-Colombia", "n": "Rs W", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [4.26618, -74.8555], "ey": 500, "ly": 1500, "p": 5214, "al": ["rs g", "área de perforación kamala", "la rotonda"]},
  {"key": "Pumpuentsa-Ecuador", "n": "Pumpuentsa", "c": "Ecuador", "r": "ecu_morona_santiago", "ll": [-2.57864, -77.27424], "ey": 1920, "ly": 2025, "p": 5213},
  {"key": "Quíbor Guadalupe-Venezuela", "n": "Quíbor Guadalupe", "c": "Venezuela", "r": "na_caribbean_maracaibo_tairona", "ll": [9.93, -69.62], "ey": 0, "ly": 1500, "p": 5210, "ex": [{"date": "2005.1.1", "name": "Quíbor"}], "al": ["tocuyano", "Tocuyano"]},
  {"key": "Las Juntas-Peru_2", "n": "Las Juntas", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-5.64159, -78.54856], "ey": -1000, "ly": 1530, "p": 5209, "al": ["brujo pata", "brujopata", "huarango pampa"]},
  {"key": "General Morales-Ecuador", "n": "General Morales", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.36311, -79.06106], "ey": 1850, "ly": 2025, "p": 5208},
  {"key": "Pujili-Ecuador", "n": "Pujili", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-0.955, -78.696], "ey": 1525, "ly": 1830, "p": 5206},
  {"key": "Cajatambo-Peru", "n": "Cajatambo", "c": "Peru", "r": "per_lima", "ll": [-10.47306, -76.99306], "ey": 1525, "ly": 2025, "p": 5204, "al": ["astobambas", "Astobambas"]},
  {"key": "Uchuytambo-Peru", "n": "Uchuytambo", "c": "Peru", "r": "vp_intendencia_huamanga_huancavelica", "ll": [-14.861, -74.529], "ey": 1525, "ly": 1825, "p": 5204},
  {"key": "San Miguel De Sema-Colombia", "n": "San Miguel De Sema", "c": "Colombia", "r": "col_cundinamarca", "ll": [5.51808, -73.72201], "ey": 1850, "ly": 2025, "p": 5202},
  {"key": "Progreso-Ecuador", "n": "Progreso", "c": "Ecuador", "r": "ecu_el_oro", "ll": [-3.25379, -79.66037], "ey": 1850, "ly": 2025, "p": 5201},
  {"key": "Camilo Aldao-Argentina", "n": "Camilo Aldao", "c": "Argentina", "r": "arg_cordoba", "ll": [-33.1279, -62.09431], "ey": 1850, "ly": 2010, "p": 5197},
  {"key": "Chichinales-Argentina", "n": "Chichinales", "c": "Argentina", "r": "arg_rio_negro", "ll": [-39.11488, -66.94252], "ey": 1900, "ly": 2022, "p": 5197},
  {"key": "Coto Ulo-Peru", "n": "Coto Ulo", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-12.31276, -75.27816], "ey": 500, "ly": 1530, "p": 5191, "al": ["chacapampa", "llacctacancha", "antahuacay"]},
  {"key": "Pampa Katari Site-Bolivia", "n": "Pampa Katari Site", "c": "Bolivia", "r": "inca_antisuyu", "ll": [-16.4458, -68.60156], "ey": 650, "ly": 1532, "p": 5189, "al": ["pampa katari site 3 ck", "Pampa Katari Site 3 CK"]},
  {"key": "Llorente-Colombia", "n": "Llorente", "c": "Colombia", "r": "col_narino", "ll": [1.39134, -78.51932], "ey": 1850, "ly": 2018, "p": 5187},
  {"key": "Los Menucos-Argentina", "n": "Los Menucos", "c": "Argentina", "r": "arg_rio_negro", "ll": [-40.84277, -68.08587], "ey": 1920, "ly": 2010, "p": 5187},
  {"key": "La Clarita-Colombia_2", "n": "La Clarita", "c": "Colombia", "r": "na_pacific_equatorial_valdivia", "ll": [1.49146, -78.64974], "ey": 1000, "ly": 1500, "p": 5187, "al": ["espriella", "Espriella"]},
  {"key": "Angospata-Peru", "n": "Angospata", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.30631, -72.12289], "ey": 0, "ly": 1530, "p": 5186, "al": ["marka marka", "waninqaqa", "Marka Marka"]},
  {"key": "Bucarelia-Colombia", "n": "Bucarelia", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [9.68333, -74.8], "ey": 700, "ly": 1500, "p": 5185, "al": ["las mercedes", "Las Mercedes"]},
  {"key": "Cabanillas-Peru", "n": "Cabanillas", "c": "Peru", "r": "per_puno", "ll": [-15.64444, -70.35389], "ey": 1850, "ly": 2025, "p": 5180, "al": ["deustua", "Deustua"]},
  {"key": "Los Robles-Chile_2", "n": "Los Robles", "c": "Chile", "r": "sc_chile_central_araucania", "ll": [-36.84143, -72.16682], "ey": 0, "ly": 1500, "p": 5180},
  {"key": "Salango-Ecuador_2", "n": "Salango", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [-1.589, -80.844], "ey": -1200, "ly": 1400, "p": 5180},
  {"key": "Cerro Palpacala-Peru", "n": "Cerro Palpacala", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-10.41291, -76.21966], "ey": 0, "ly": 1530, "p": 5179, "al": ["galag marka", "guellay wasin", "huacach"]},
  {"key": "Aculeo-Chile", "n": "Aculeo", "c": "Chile", "r": "crp_obispado_santiago", "ll": [-33.868, -70.921], "ey": 1525, "ly": 1830, "p": 5178},
  {"key": "Francisco Aniceto Lugo-Venezuela", "n": "Francisco Aniceto Lugo", "c": "Venezuela", "r": "ven_delta_amacuro", "ll": [8.27356, -60.29671], "ey": 1920, "ly": 2025, "p": 5177},
  {"key": "Los Piscontes-Peru", "n": "Los Piscontes", "c": "Peru", "r": "per_ica", "ll": [-14.1153, -75.6756], "ey": 1850, "ly": 2017, "p": 5177, "al": ["pariña chico", "Pariña Chico"]},
  {"key": "Río Blanco-Colombia", "n": "Río Blanco", "c": "Colombia", "r": "col_cauca", "ll": [2.08723, -76.66955], "ey": 1525, "ly": 2018, "p": 5176, "al": ["rioblanco", "Rioblanco"]},
  {"key": "San Pedro de Arimena-Colombia", "n": "San Pedro de Arimena", "c": "Colombia", "r": "col_casanare", "ll": [4.60811, -71.62171], "ey": 1805, "ly": 2018, "p": 5174, "al": ["puerto gaitan", "san guillermo arimena", "San Guillermo Arimena"]},
  {"key": "General Lagos-Argentina", "n": "General Lagos", "c": "Argentina", "r": "arg_entre_rios", "ll": [-33.10994, -60.56463], "ey": 1850, "ly": 2022, "p": 5174},
  {"key": "Paccha-Peru", "n": "Paccha", "c": "Peru", "r": "per_cajamarca", "ll": [-6.4975, -78.42361], "ey": 1850, "ly": 2025, "p": 5165},
  {"key": "Suscal-Ecuador", "n": "Suscal", "c": "Ecuador", "r": "ecu_canar", "ll": [-2.46333, -79.07108], "ey": 1850, "ly": 2025, "p": 5164},
  {"key": "Villa del Dique-Argentina", "n": "Villa del Dique", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.17646, -64.45686], "ey": 1850, "ly": 2022, "p": 5162},
  {"key": "Guanarito (Paso Real de Papelón)-Venezuela", "n": "Guanarito (Paso Real de Papelón)", "c": "Venezuela", "r": "ven_portuguesa", "ll": [8.70901, -69.21501], "ey": 1772, "ly": 2011, "p": 5159, "al": ["guanarito", "paz guanarito", "Paz Guanarito"]},
  {"key": "San Carlos Sitio-Colombia", "n": "San Carlos Sitio", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [6.51844, -74.38061], "ey": 1300, "ly": 1500, "p": 5158, "al": ["yacimiento 142 \"torcoroma", "yacimiento 6 \"el aterrado 2", "Yacimiento 142 \"TORCOROMA"]},
  {"key": "Huaranchal-Peru", "n": "Huaranchal", "c": "Peru", "r": "per_la_libertad", "ll": [-7.68972, -78.4425], "ey": 1850, "ly": 2025, "p": 5157},
  {"key": "Oyolo-Peru", "n": "Oyolo", "c": "Peru", "r": "per_ayacucho", "ll": [-15.18, -73.18528], "ey": 1525, "ly": 2025, "p": 5156},
  {"key": "El Cabrero-Colombia", "n": "El Cabrero", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [8.14, -76.09], "ey": -27, "ly": 1500, "p": 5155},
  {"key": "Parcelas-Colombia", "n": "Parcelas", "c": "Colombia", "r": "col_bogota_capital_district", "ll": [4.66126, -74.24149], "ey": 1525, "ly": 2018, "p": 5146, "al": ["chipo", "Chipo"]},
  {"key": "Corral de la Bomba-Argentina", "n": "Corral de la Bomba", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-30.79859, -64.68659], "ey": 80, "ly": 1500, "p": 5143, "al": ["piedras moras", "Piedras Moras"]},
  {"key": "Cerinza-Colombia", "n": "Cerinza", "c": "Colombia", "r": "col_boyaca", "ll": [5.95594, -72.94792], "ey": 1525, "ly": 2025, "p": 5141, "al": ["zerinza pueblo", "zerinza", "Zerinza Pueblo"]},
  {"key": "Campohermoso-Colombia", "n": "Campohermoso", "c": "Colombia", "r": "col_boyaca", "ll": [5.03168, -73.10417], "ey": 1850, "ly": 2025, "p": 5140},
  {"key": "Mallares-Peru", "n": "Mallares", "c": "Peru", "r": "per_piura", "ll": [-4.8583, -80.7619], "ey": 1850, "ly": 2017, "p": 5140},
  {"key": "Campeche-Colombia", "n": "Campeche", "c": "Colombia", "r": "col_atlantico", "ll": [10.7265, -74.9136], "ey": 1850, "ly": 2018, "p": 5139},
  {"key": "Amaluza-Ecuador", "n": "Amaluza", "c": "Ecuador", "r": "ecu_loja", "ll": [-4.58003, -79.36431], "ey": 1850, "ly": 2025, "p": 5136},
  {"key": "Huimbayoc-Peru", "n": "Huimbayoc", "c": "Peru", "r": "per_san_martin", "ll": [-6.41778, -75.76806], "ey": 1900, "ly": 2025, "p": 5136},
  {"key": "Cmn_projecto_salitreras_wfl1-Chile", "n": "Cmn_projecto_salitreras_wfl1", "c": "Chile", "r": "inca_collasuyu", "ll": [-19.88885, -69.79041], "ey": 1300, "ly": 1530, "p": 5136},
  {"key": "Cacha-Ecuador", "n": "Cacha", "c": "Ecuador", "r": "ecu_chimborazo", "ll": [-1.71016, -78.70425], "ey": 1850, "ly": 2025, "p": 5132},
  {"key": "Chuin-Peru", "n": "Chuin", "c": "Peru", "r": "per_la_libertad", "ll": [-7.7502, -79.2788], "ey": -2000, "ly": 2017, "p": 5130, "ex": [{"date": "1961.1.1", "name": "Paiján"}], "al": ["licapa", "lacapa", "chavimochic-p-1-de"]},
  {"key": "Surcubamba-Peru", "n": "Surcubamba", "c": "Peru", "r": "per_huancavelica", "ll": [-12.11639, -74.63056], "ey": 1525, "ly": 2025, "p": 5129, "al": ["surcobamba", "Surcobamba"]},
  {"key": "Santa María (ven_nueva_esparta)-Venezuela", "n": "Santa María", "c": "Venezuela", "r": "ven_nueva_esparta", "ll": [10.95056, -64.09944], "ey": 1850, "ly": 2011, "p": 5128},
  {"key": "Japio-Colombia", "n": "Japio", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [3.047, -76.443], "ey": 1525, "ly": 1830, "p": 5127},
  {"key": "Santiago de Quirahuara-Peru", "n": "Santiago de Quirahuara", "c": "Peru", "r": "per_huancavelica", "ll": [-14.05611, -74.97639], "ey": 1525, "ly": 2025, "p": 5126, "al": ["santiago de quirehuara", "quirahuara", "Santiago de Quirehuara"]},
  {"key": "Pucara Winchaccalla-Peru", "n": "Pucara Winchaccalla", "c": "Peru", "r": "inca_collasuyu", "ll": [-16.29485, -69.15037], "ey": -2000, "ly": 1530, "p": 5126, "al": ["arqueológico cerro khapia", "monticulo queñuan", "nasaq´ara"]},
  {"key": "Puka Puka-Peru", "n": "Puka Puka", "c": "Peru", "r": "inca_contisuyu", "ll": [-14.20572, -72.08343], "ey": -1000, "ly": 1530, "p": 5126, "al": ["abrigos de puka puka", "abrigos de vista alegre", "iñapago"]},
  {"key": "Pukarqollu-Bolivia", "n": "Pukarqollu", "c": "Bolivia", "r": "inca_collasuyu", "ll": [-19.25611, -68.64606], "ey": 711, "ly": 1532, "p": 5123},
  {"key": "Buga-Colombia", "n": "Buga", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [3.901, -76.298], "ey": 1574, "ly": 1778, "p": 5120, "ex": [{"date": "1902.1.1", "name": "Buga"}]},
  {"key": "Catarpe-Chile", "n": "Catarpe", "c": "Chile", "r": "inca_collasuyu", "ll": [-22.863, -68.21], "ey": -4039, "ly": 1530, "p": 5120, "al": ["cmn_registro_arqueológico_acreditado", "casa parroquial", "catarpe (qñ: ch-cn"]},
  {"key": "Coquimbo Inca-Chile", "n": "Coquimbo Inca", "c": "Chile", "r": "inca_collasuyu", "ll": [-29.903, -71.252], "ey": 800, "ly": 1530, "p": 5120, "ex": [{"date": "1875.1.1", "name": "Coquimbo"}], "al": ["el olivar", "el olivar coquimbo", "diaguita chileno"]},
  {"key": "El Perico-Colombia", "n": "El Perico", "c": "Colombia", "r": "na_magdalena_cauca_muisca", "ll": [5.29, -74.79], "ey": 1282, "ly": 1500, "p": 5120},
  {"key": "Sunchituyoj-Argentina", "n": "Sunchituyoj", "c": "Argentina", "r": "sc_nw_andes_sierras_cuyo", "ll": [-28.034, -63.524], "ey": 800, "ly": 1450, "p": 5120, "al": ["averías", "tonocoté", "Averías"]},
  {"key": "Montalvo (ecu_pastaza)-Ecuador", "n": "Montalvo", "c": "Ecuador", "r": "ecu_pastaza", "ll": [-2.0617, -76.96491], "ey": 1920, "ly": 2025, "p": 5119},
  {"key": "Secocha-Peru", "n": "Secocha", "c": "Peru", "r": "per_arequipa", "ll": [-15.9825, -73.1706], "ey": 1850, "ly": 2017, "p": 5119},
]

UA = "ProjectSVEA/1.0 (https://confoederatio.org; research@confoederatio.org)"

def fetch_json(url):
  for attempt in range(3):
    try:
      req = urllib.request.Request(url, headers={"User-Agent": UA})
      with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))
    except Exception as e:
      if attempt == 2:
        print("ERR", url[:80], e, file=sys.stderr)
        return {}
      time.sleep(1.0 * (attempt + 1))
  return {}

def wiki_geosearch(lat, lng, lang="es"):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=15000&gslimit=5&format=json"
  return fetch_json(url).get("query", {}).get("geosearch", [])

def wiki_search(q, lang="es"):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=4&format=json"
  return [x["title"] for x in fetch_json(url).get("query", {}).get("search", [])]

def wiki_extract(title, lang="es"):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exchars=4000&titles={urllib.parse.quote(title)}&format=json"
  pages = fetch_json(url).get("query", {}).get("pages", {})
  for p in pages.values():
    return p.get("extract", "")
  return ""

out = {}
for idx, s in enumerate(SETTLEMENTS):
  k = s["key"]
  lat, lng = s["ll"]
  geo = wiki_geosearch(lat, lng, "es")
  clean_n = s["n"].split("(")[0].strip()
  srch = wiki_search(f"{clean_n} {s['c']}", "es")
  titles = []
  for g in geo[:2]:
    if g["title"] not in titles:
      titles.append(g["title"])
  for t in srch[:2]:
    if t not in titles:
      titles.append(t)
  extracts = {}
  for t in titles[:3]:
    ext = wiki_extract(t, "es")
    if ext:
      extracts[t] = ext[:2500]
  if not extracts:
    en_geo = wiki_geosearch(lat, lng, "en")
    en_srch = wiki_search(f"{clean_n} {s['c']}", "en")
    for t in ([g["title"] for g in en_geo[:2]] + en_srch[:2])[:2]:
      ext = wiki_extract(t, "en")
      if ext:
        extracts["en:" + t] = ext[:2000]
  out[k] = {
    "geo": [(g["title"], round(g["dist"])) for g in geo[:4]],
    "search": srch,
    "extracts": extracts,
  }
  if (idx + 1) % 15 == 0:
    print(f"Progress {idx + 1}/90", flush=True)
  time.sleep(0.1)

with open("tests/quipu_wiki_out.json", "w", encoding="utf-8") as f:
  json.dump(out, f, ensure_ascii=False, indent=2)
print("Done:", len(out))
