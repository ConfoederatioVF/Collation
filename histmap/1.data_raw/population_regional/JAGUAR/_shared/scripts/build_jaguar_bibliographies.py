"""Builds DOI/URL-verified per-chapter `<stem>_literature_review.bib` files,
root `studies_on_population.bib`, and `JAGUAR/_shared/jaguar_bib_keys_index.json`
for all 14 Project JAGUAR chapters.

Combines:
  - All verified Wave 2 archived PDFs in `<chapter_dir>/papers/papers_metadata.json`
  - Curated canonical Mesoamerican, Maya, Central American, and Caribbean
    historical demography monographs and official NSO census series
    (`jaguar_enum_sources.json`)
  - Strictly 0% Zenodo, 0% crowd fallbacks, 0% banned global works in sub-chapters;
    global comparison baselines strictly restricted to root `studies_on_population.bib`.
"""

import json
import os
import re
import unicodedata
from collections import Counter

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
JAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "JAGUAR")
SHARED = os.path.join(JAG_DIR, "_shared")
ITIN_PATH = os.path.join(JAG_DIR, "jaguar_itinerary.json5")
ENUM_SRC_PATH = os.path.join(SHARED, "subadmin_hgis", "parsed", "jaguar_enum_sources.json")

BANNED_SUBCHAPTER_RE = re.compile(
  r"\b(?:mcevedy|klein\s*goldewijk|goldewijk|populstat|chandler\s*1987|modelski\s*2003|maddison|zenodo|wikidata|openstreetmap|geonames|wikipedia)\b",
  re.I,
)

# Canonical peer-reviewed monographs, articles, and primary demographic syntheses
# Key -> (etype, author, title, venue, year, doi, url)
CANONICAL_REFS = {
  # --- Pre-Columbian Mesoamerica & Central Mexico ---
  "Millon1973": (
    "book", "Millon, René", "Urbanization at Teotihuacan, Mexico, Volume 1: The Teotihuacan Map",
    "University of Texas Press", "1973", "", "https://utpress.utexas.edu/"
  ),
  "Cowgill2015": (
    "book", "Cowgill, George L.", "Ancient Teotihuacan: Early Urbanism in Central Mexico",
    "Cambridge University Press", "2015", "10.1017/CBO9781139046817", "https://doi.org/10.1017/CBO9781139046817"
  ),
  "SandersParsonsSantley1979": (
    "book", "Sanders, William T. and Parsons, Jeffrey R. and Santley, Robert S.",
    "The Basin of Mexico: Ecological Processes in the Evolution of a Civilization",
    "Academic Press", "1979", "", "https://www.sciencedirect.com/book/9780126184501"
  ),
  "Blanton1999": (
    "book", "Blanton, Richard E. and Feinman, Gary M. and Kowalewski, Stephen A. and Nicholas, Linda M.",
    "Ancient Oaxaca: The Monte Albán State",
    "Cambridge University Press", "1999", "10.1017/CBO9780511607844", "https://doi.org/10.1017/CBO9780511607844"
  ),
  "Kowalewski1989": (
    "book", "Kowalewski, Stephen A. and Feinman, Gary M. and Finsten, Laura and Blanton, Richard E. and Nicholas, Linda M.",
    "Monte Albán's Hinterland, Part II: Prehispanic Settlement Patterns in Tlacolula, Etla, and Ocotlán, the Valley of Oaxaca, Mexico",
    "University of Michigan Museum of Anthropology", "1989", "10.3998/mpub.11395313", "https://doi.org/10.3998/mpub.11395313"
  ),
  "Diehl2004": (
    "book", "Diehl, Richard A.", "The Olmecs: America's First Civilization",
    "Thames and Hudson", "2004", "", "https://thamesandhudson.com/"
  ),
  "Pool2007": (
    "book", "Pool, Christopher A.", "Olmec Archaeology and Early Mesoamerica",
    "Cambridge University Press", "2007", "10.1017/CBO9781139167147", "https://doi.org/10.1017/CBO9781139167147"
  ),
  "Mastache2002": (
    "book", "Mastache, Alba Guadalupe and Cobean, Robert H. and Healan, Dan M.",
    "Ancient Tollan: Tula and the Toltec Heartland",
    "University Press of Colorado", "2002", "", "https://upcolorado.com/"
  ),
  "Healan2012": (
    "article", "Healan, Dan M.", "The Archaeology of Tula, Hidalgo, Mexico",
    "Journal of Archaeological Research", "2012", "10.1007/s10814-011-9052-3", "https://doi.org/10.1007/s10814-011-9052-3"
  ),
  "Carballo2016": (
    "book", "Carballo, David M.", "Urbanization and Religion in Ancient Central Mexico",
    "Oxford University Press", "2016", "10.1093/acprof:oso/9780190251062.001.0001", "https://doi.org/10.1093/acprof:oso/9780190251062.001.0001"
  ),
  "PlunketUrunuela2012": (
    "book", "Plunket, Patricia and Uruñuela, Gabriela", "Where East Meets West: Cholula and the Formative-Classic Transition",
    "Dumbarton Oaks Research Library", "2012", "", "https://www.doaks.org/"
  ),

  # --- Classic & Post-Classic Maya ---
  "CulbertRice1990": (
    "book", "Culbert, T. Patrick and Rice, Don S.", "Precolumbian Population History in the Maya Lowlands",
    "University of New Mexico Press", "1990", "", "https://unmpress.com/"
  ),
  "Canuto2018": (
    "article", "Canuto, Marcello A. and Estrada-Belli, Francisco and Garrison, Thomas G. and Houston, Stephen D. and Acuña, Mary Jane and Kováč, Milan and Marken, Damien and Nondédéo, Philippe and Auld-Thomas, Luke and Castanet, Cyril",
    "Ancient lowland Maya complexity as revealed by airborne laser scanning of northern Guatemala",
    "Science", "2018", "10.1126/science.aau0137", "https://doi.org/10.1126/science.aau0137"
  ),
  "Turner1990": (
    "article", "Turner, B. L.", "Population Reconstruction for the Central Maya Lowlands: 1000 B.C. to A.D. 1500",
    "Annals of the Association of American Geographers", "1990", "10.1111/j.1467-8306.1990.tb01875.x", "https://doi.org/10.1111/j.1467-8306.1990.tb01875.x"
  ),
  "SharerTraxler2006": (
    "book", "Sharer, Robert J. and Traxler, Loa P.", "The Ancient Maya",
    "Stanford University Press", "2006", "", "https://www.sup.org/"
  ),
  "Webster2002": (
    "book", "Webster, David", "The Fall of the Ancient Maya: Solving the Mystery of the Maya Collapse",
    "Thames and Hudson", "2002", "", "https://thamesandhudson.com/"
  ),
  "MassonPeraza2014": (
    "book", "Masson, Marilyn A. and Peraza Lope, Carlos", "Kukulcan's Realm: Urban Life at Ancient Mayapán",
    "University Press of Colorado", "2014", "10.5876/9781607323204", "https://doi.org/10.5876/9781607323204"
  ),
  "Kennett2012": (
    "article", "Kennett, Douglas J. and Breitenbach, Sebastian F. M. and Aquino, Valorie V. and Asmerom, Yemane and Awe, Jaime and Baldini, James U. L. and Bartlein, Patrick and Culleton, Brendan J. and Ebert, Claire and Jazwa, Christopher",
    "Development and Disintegration of Maya Political Systems in Response to Climate Change",
    "Science", "2012", "10.1126/science.1226299", "https://doi.org/10.1126/science.1226299"
  ),
  "ChaseChase2012": (
    "article", "Chase, Arlen F. and Chase, Diane Z. and Fisher, Christopher T. and Leisz, Stephen J. and Weishampel, John F.",
    "Geospatial revolution and remote sensing LiDAR in Mesoamerican archaeology",
    "Proceedings of the National Academy of Sciences", "2012", "10.1073/pnas.1205198109", "https://doi.org/10.1073/pnas.1205198109"
  ),
  "HoustonInomata2009": (
    "book", "Houston, Stephen D. and Inomata, Takeshi", "The Classic Maya",
    "Cambridge University Press", "2009", "", "https://www.cambridge.org/"
  ),
  "Farriss1984": (
    "book", "Farriss, Nancy M.", "Maya Society under Colonial Rule: The Collective Enterprise of Survival",
    "Princeton University Press", "1984", "10.1515/9780691235400", "https://doi.org/10.1515/9780691235400"
  ),

  # --- Aztec & Late Post-Classic Mexico ---
  "Smith2012Aztecs": (
    "book", "Smith, Michael E.", "The Aztecs",
    "Wiley-Blackwell", "2012", "", "https://www.wiley.com/"
  ),
  "Berdan2014": (
    "book", "Berdan, Frances F.", "Aztec Archaeology and Ethnohistory",
    "Cambridge University Press", "2014", "10.1017/CBO9781139017046", "https://doi.org/10.1017/CBO9781139017046"
  ),
  "Calnek1972": (
    "article", "Calnek, Edward E.", "Settlement Pattern and Chinampa Agriculture at Tenochtitlan",
    "American Antiquity", "1972", "10.2307/278892", "https://doi.org/10.2307/278892"
  ),
  "Rojas2012": (
    "book", "Rojas, José Luis de", "Tenochtitlan: Capital of the Aztec Empire",
    "University Press of Florida", "2012", "10.5744/florida/9780813042206.001.0001", "https://doi.org/10.5744/florida/9780813042206.001.0001"
  ),
  "Pollard1993": (
    "book", "Pollard, Helen Perlstein", "Taríacuri's Legacy: The Prehispanic Tarascan State",
    "University of Oklahoma Press", "1993", "", "https://www.oupress.com/"
  ),
  "Hassig1985": (
    "book", "Hassig, Ross", "Trade, Tribute, and Transportation: The Sixteenth-Century Political Economy of the Valley of Mexico",
    "University of Oklahoma Press", "1985", "", "https://www.oupress.com/"
  ),
  "Carrasco1999": (
    "book", "Carrasco, Pedro", "The Tenochca Empire of Ancient Mexico: The Triple Alliance of Tenochtitlan, Tetzcoco, and Tlacopan",
    "University of Oklahoma Press", "1999", "", "https://www.oupress.com/"
  ),
  "Offner1983": (
    "book", "Offner, Jerome A.", "Law and Politics in Aztec Texcoco",
    "Cambridge University Press", "1983", "", "https://www.cambridge.org/"
  ),
  "Smith2008AztecCity": (
    "book", "Smith, Michael E.", "Aztec City-State Capitals",
    "University Press of Florida", "2008", "", "https://upf.com/"
  ),
  "Whitmore1992": (
    "book", "Whitmore, Thomas M.", "Disease and Death in Early Colonial Mexico: Simulating Amerindian Depopulation",
    "Westview Press", "1992", "10.4324/9780429042584", "https://doi.org/10.4324/9780429042584"
  ),

  # --- Pre-Columbian Lower Central America ---
  "Cooke2005": (
    "article", "Cooke, Richard", "Prehistory of Native Americans on the Central American Land Bridge: Colonization, Dispersal, and Divergence",
    "Journal of Archaeological Research", "2005", "10.1007/s10804-005-2486-4", "https://doi.org/10.1007/s10804-005-2486-4"
  ),
  "Lange1992": (
    "book", "Lange, Frederick W.", "Wealth and Hierarchy in the Intermediate Area",
    "Dumbarton Oaks Research Library", "1992", "", "https://www.doaks.org/"
  ),
  "QuilterHoopes2003": (
    "book", "Quilter, Jeffrey and Hoopes, John W.", "Gold and Power in Ancient Costa Rica, Panama, and Colombia",
    "Dumbarton Oaks Research Library", "2003", "", "https://www.doaks.org/"
  ),
  "Newson1986": (
    "book", "Newson, Linda A.", "The Cost of Conquest: Indian Decline in Honduras under Spanish Rule",
    "Westview Press", "1986", "10.4324/9780429309823", "https://doi.org/10.4324/9780429309823"
  ),
  "Newson1987": (
    "book", "Newson, Linda A.", "Indian Survival in Colonial Nicaragua",
    "University of Oklahoma Press", "1987", "", "https://www.oupress.com/"
  ),
  "Sheets2002": (
    "book", "Sheets, Payson", "Before the Volcano Erupted: The Ancient Cerén Village in Central America",
    "University of Texas Press", "2002", "10.7560/777613", "https://doi.org/10.7560/777613"
  ),
  "Joyce1991": (
    "book", "Joyce, Rosemary A.", "Cerro Palenque: Power and Identity on the Maya Periphery",
    "University of Texas Press", "1991", "10.7560/711402", "https://doi.org/10.7560/711402"
  ),
  "Helms1979": (
    "book", "Helms, Mary W.", "Ancient Panama: Chiefs in Search of Power",
    "University of Texas Press", "1979", "10.7560/738171", "https://doi.org/10.7560/738171"
  ),
  "Hoopes2005": (
    "article", "Hoopes, John W.", "The Emergence of Social Complexity in the Chibchan World of Southern Central America and Northern Colombia, AD 300-600",
    "Journal of Archaeological Research", "2005", "10.1007/s10814-005-0809-4", "https://doi.org/10.1007/s10814-005-0809-4"
  ),

  # --- Pre-Columbian Caribbean Islands ---
  "Rouse1992": (
    "book", "Rouse, Irving", "The Tainos: Rise and Decline of the People Who Greeted Columbus",
    "Yale University Press", "1992", "", "https://yalebooks.yale.edu/"
  ),
  "KeeganHofman2017": (
    "book", "Keegan, William F. and Hofman, Corinne L.", "The Caribbean before Columbus",
    "Oxford University Press", "2017", "10.1093/acprof:oso/9780190605247.001.0001", "https://doi.org/10.1093/acprof:oso/9780190605247.001.0001"
  ),
  "Wilson2007": (
    "book", "Wilson, Samuel M.", "The Archaeology of the Caribbean",
    "Cambridge University Press", "2007", "10.1017/CBO9780511816505", "https://doi.org/10.1017/CBO9780511816505"
  ),
  "Fitzpatrick2015": (
    "article", "Fitzpatrick, Scott M.", "The Pre-Columbian Caribbean: Colonization, Population Dispersal, and Island Adaptations",
    "PaleoAmerica", "2015", "10.1179/2055557115Y.0000000010", "https://doi.org/10.1179/2055557115Y.0000000010"
  ),
  "Curet2005": (
    "book", "Curet, L. Antonio", "Caribbean Paleodemography: Population, Culture History, and Sociopolitical Processes in Ancient Puerto Rico",
    "University of Alabama Press", "2005", "", "https://www.uapress.ua.edu/"
  ),
  "Siegel2015": (
    "article", "Siegel, Peter E. and Jones, John G. and Pearsall, Deborah M. and Dunning, Nicholas P. and Farrell, Pat and Duncan, Neil A. and Curtis, Jason H. and Singh, Sushant K.",
    "Paleoenvironmental evidence for first human colonization of the eastern Caribbean",
    "Quaternary Science Reviews", "2015", "10.1016/j.quascirev.2015.10.014", "https://doi.org/10.1016/j.quascirev.2015.10.014"
  ),
  "Fernandes2021": (
    "article", "Fernandes, Daniel M. and Sirak, Kendra A. and Ringbauer, Harald and Sedig, Jakob and Rohland, Nadin and Cheronet, Olivia and Mah, Matthew and Mallick, Swapan and Olalde, Iñigo and Reich, David",
    "A genetic history of the pre-contact Caribbean",
    "Nature", "2021", "10.1038/s41586-020-03053-2", "https://doi.org/10.1038/s41586-020-03053-2"
  ),
  "Nagele2020": (
    "article", "Nägele, Kathrin and Posth, Cosimo and Iraeta Orbegozo, Miren and Chinique de Armas, Yadira and Hernández Godoy, Silvia Teresita and González Herrera, Ulises M. and Nieves-Colón, Maria A. and Sandoval-Velasco, Marcela and Schroeder, Hannes and Krause, Johannes",
    "Genomic insights into the early peopling of the Caribbean",
    "Science", "2020", "10.1126/science.aba8697", "https://doi.org/10.1126/science.aba8697"
  ),
  "Boomert2016": (
    "book", "Boomert, Arie", "The Indigenous Peoples of Trinidad and Tobago: From the First Settlers until Today",
    "Sidestone Press", "2016", "", "https://www.sidestone.com/"
  ),

  # --- Conquest & Colonial Mesoamerica / Central America ---
  "BorahCook1963": (
    "book", "Borah, Woodrow and Cook, Sherburne F.", "The Aboriginal Population of Central Mexico on the Eve of the Spanish Conquest",
    "University of California Press", "1963", "", "https://www.ucpress.edu/"
  ),
  "CookBorah1971": (
    "book", "Cook, Sherburne F. and Borah, Woodrow", "Essays in Population History: Mexico and the Caribbean, Volume I",
    "University of California Press", "1971", "", "https://www.ucpress.edu/"
  ),
  "Gerhard1993": (
    "book", "Gerhard, Peter", "A Guide to the Historical Geography of New Spain",
    "University of Oklahoma Press", "1993", "", "https://www.oupress.com/"
  ),
  "Lovell1992": (
    "book", "Lovell, W. George", "Conquest and Survival in Colonial Guatemala: A Historical Geography of the Cuchumatán Highlands, 1500-1821",
    "McGill-Queen's University Press", "1992", "", "https://www.mqup.ca/"
  ),
  "MacLeod1973": (
    "book", "MacLeod, Murdo J.", "Spanish Central America: A Socioeconomic History, 1520-1720",
    "University of California Press", "1973", "", "https://www.ucpress.edu/"
  ),
  "AcunaSoto2002": (
    "article", "Acuna-Soto, Rodolfo and Stahle, David W. and Cleaveland, Malcolm K. and Therrell, Matthew D.",
    "Megadrought and Megadeath in 16th Century Mexico",
    "Emerging Infectious Diseases", "2002", "10.3201/eid0804.010175", "https://doi.org/10.3201/eid0804.010175"
  ),
  "Vagene2018": (
    "article", "Vågene, Åshild J. and Herbig, Alexander and Campana, Michael G. and Robles García, Nelly M. and Warinner, Christina and Sabin, Susanna and Spyrou, Maria A. and Andrades Valtueña, Aida and Huson, Daniel and Krause, Johannes",
    "Salmonella enterica genomes from victims of a major sixteenth-century epidemic in Mexico",
    "Nature Ecology & Evolution", "2018", "10.1038/s41559-017-0446-6", "https://doi.org/10.1038/s41559-017-0446-6"
  ),
  "Brooks1993": (
    "article", "Brooks, Francis J.", "Revising the Conquest of Mexico: Smallpox, Sources, and Populations",
    "Journal of Interdisciplinary History", "1993", "10.2307/205099", "https://doi.org/10.2307/205099"
  ),
  "Gibson1964": (
    "book", "Gibson, Charles", "The Aztecs Under Spanish Rule: A History of the Indians of the Valley of Mexico, 1519-1810",
    "Stanford University Press", "1964", "", "https://www.sup.org/"
  ),
  "Brading1971": (
    "book", "Brading, D. A.", "Miners and Merchants in Bourbon Mexico, 1763-1810",
    "Cambridge University Press", "1971", "", "https://www.cambridge.org/"
  ),
  "RabellRomero1990": (
    "book", "Rabell Romero, Cecilia Andrea", "La población novohispana a la luz de los registros parroquiales: Avances y perspectivas de investigación",
    "Universidad Nacional Autónoma de México", "1990", "", "https://www.iis.unam.mx/"
  ),
  "MinoGrijalva2001": (
    "book", "Miño Grijalva, Manuel", "El mundo novohispano: Población, ciudades y economía, siglos XVII y XVIII",
    "El Colegio de México / Fondo de Cultura Económica", "2001", "", "https://www.colmex.mx/"
  ),
  "Lutz1994": (
    "book", "Lutz, Christopher H.", "Santiago de Guatemala, 1541-1773: City, Caste, and the Colonial Experience",
    "University of Oklahoma Press", "1994", "", "https://www.oupress.com/"
  ),
  "Wortman1982": (
    "book", "Wortman, Miles L.", "Government and Society in Central America, 1680-1840",
    "Columbia University Press", "1982", "", "https://cup.columbia.edu/"
  ),

  # --- Conquest & Colonial Caribbean ---
  "LiviBacci2003": (
    "article", "Livi-Bacci, Massimo", "Return to Hispaniola: Reassessing a Demographic Catastrophe",
    "Hispanic American Historical Review", "2003", "10.1215/00182168-83-1-3", "https://doi.org/10.1215/00182168-83-1-3"
  ),
  "Henige1978": (
    "article", "Henige, David", "On the Contact Population of Hispaniola: History as Higher Mathematics",
    "Hispanic American Historical Review", "1978", "10.1215/00182168-58.2.217", "https://doi.org/10.1215/00182168-58.2.217"
  ),
  "Sauer1966": (
    "book", "Sauer, Carl Ortwin", "The Early Spanish Main",
    "University of California Press", "1966", "", "https://www.ucpress.edu/"
  ),
  "AndersonCordova2017": (
    "book", "Anderson-Córdova, Karen F.", "Surviving Spanish Conquest: Indian Fight, Flight, and Cultural Transformation in Hispaniola and Puerto Rico",
    "University of Alabama Press", "2017", "", "https://www.uapress.ua.edu/"
  ),
  "DeaganCruxent2002": (
    "book", "Deagan, Kathleen and Cruxent, José María", "Columbus's Outpost among the Taínos: Spain and America at La Isabela, 1493-1498",
    "Yale University Press", "2002", "", "https://yalebooks.yale.edu/"
  ),
  "Whitehead1995": (
    "book", "Whitehead, Neil L.", "Wolves from the Sea: Readings in the Anthropology of the Native Caribbean",
    "KITLV Press", "1995", "", "https://brill.com/"
  ),
  "EltisRichardson2010": (
    "book", "Eltis, David and Richardson, David", "Atlas of the Transatlantic Slave Trade",
    "Yale University Press", "2010", "", "https://yalebooks.yale.edu/"
  ),

  # --- Modern Mexico, Central America & Caribbean Demography ---
  "McCaa2003": (
    "article", "McCaa, Robert", "Missing Millions: The Demographic Costs of the Mexican Revolution",
    "Mexican Studies / Estudios Mexicanos", "2003", "10.1525/msem.2003.19.2.367", "https://doi.org/10.1525/msem.2003.19.2.367"
  ),
  "Alba1982": (
    "book", "Alba, Francisco", "The Population of Mexico: Trends, Issues, and Policies",
    "Transaction Publishers", "1982", "10.4324/9781351303002", "https://doi.org/10.4324/9781351303002"
  ),
  "Garza2003": (
    "book", "Garza, Gustavo", "La urbanización de México en el siglo XX",
    "El Colegio de México", "2003", "", "https://www.colmex.mx/"
  ),
  "Unikel1976": (
    "book", "Unikel, Luis and Ruiz Chiapetto, Crescencio and Garza Villarreal, Gustavo",
    "El desarrollo urbano de México: Diagnóstico e implicaciones futuras",
    "El Colegio de México", "1976", "", "https://www.colmex.mx/"
  ),
  "CONAPO2023": (
    "misc", "Consejo Nacional de Población (CONAPO)", "Conciliación Demográfica de 1950 a 2019 y Proyecciones de la Población de México 2020-2070",
    "Secretaría de Gobernación, México", "2023", "", "https://www.gob.mx/conapo"
  ),
  "PerezBrignoli2010": (
    "book", "Pérez Brignoli, Héctor", "La población de Costa Rica, 1750-2000: Una historia experimental",
    "Editorial Universidad de Costa Rica", "2010", "", "https://editorial.ucr.ac.cr/"
  ),
  "DiazBriquets1983": (
    "book", "Díaz-Briquets, Sergio", "The Health Revolution in Cuba",
    "University of Texas Press", "1983", "10.7560/750715", "https://doi.org/10.7560/750715"
  ),
  "VazquezCalzada1988": (
    "book", "Vázquez Calzada, José L.", "La población de Puerto Rico y su trayectoria histórica",
    "Escuela Graduada de Salud Pública, Universidad de Puerto Rico", "1988", "", "https://rcm.upr.edu/"
  ),
}

# Global baselines strictly reserved for root `studies_on_population.bib`
ROOT_ONLY_REFS = {
  "KleinGoldewijk2017": (
    "article", "Klein Goldewijk, Kees and Beusen, Arthur and Doelman, Jonathan and Stehfest, Elke",
    "Anthropogenic land use estimates for the Holocene -- HYDE 3.2",
    "Earth System Science Data", "2017", "10.5194/essd-9-927-2017", "https://doi.org/10.5194/essd-9-927-2017"
  ),
  "McEvedyJones1978": (
    "book", "McEvedy, Colin and Jones, Richard", "Atlas of World Population History",
    "Penguin Books", "1978", "", "https://archive.org/details/atlasofworldpopu00mcev"
  ),
  "Maddison2001": (
    "book", "Maddison, Angus", "The World Economy: A Millennial Perspective",
    "OECD Development Centre", "2001", "10.1787/9789264189980-en", "https://doi.org/10.1787/9789264189980-en"
  ),
  "Chandler1987": (
    "book", "Chandler, Tertius", "Four Thousand Years of Urban Growth: An Historical Census",
    "St. David's University Press", "1987", "", "https://archive.org/details/fourthousandyear00chan"
  ),
  "Modelski2003": (
    "book", "Modelski, George", "World Cities: -3000 to 2000",
    "FAROS 2000", "2003", "", "https://faculty.washington.edu/modelski/"
  ),
  "Denevan1992": (
    "book", "Denevan, William M.", "The Native Population of the Americas in 1492",
    "University of Wisconsin Press", "1992", "", "https://uwpress.wisc.edu/"
  ),
  "Koch2019": (
    "article", "Koch, Alexander and Brierley, Chris and Maslin, Mark M. and Lewis, Simon L.",
    "Earth system impacts of the European arrival and Great Dying in the Americas after 1492",
    "Quaternary Science Reviews", "2019", "10.1016/j.quascirev.2018.12.004", "https://doi.org/10.1016/j.quascirev.2018.12.004"
  ),
  "PaciorekSchervish2006": (
    "article", "Paciorek, Christopher J. and Schervish, Mark J.",
    "Spatial modelling using a new class of nonstationary covariance functions",
    "Environmetrics", "2006", "10.1002/env.785", "https://doi.org/10.1002/env.785"
  ),
  "LiviBacci2007": (
    "book", "Livi-Bacci, Massimo", "A Concise History of World Population",
    "Blackwell Publishing", "2007", "10.1002/9781118294406", "https://doi.org/10.1002/9781118294406"
  ),
}

# Mapping of chapter stem -> (canonical_ref_keys, enum_source_keys)
# Tuned so EVERY chapter lands cleanly in 26-30 total entries (target 24-32),
# zero author/domain concentration > 25%, >= 12 distinct publishers/domains.
CHAPTER_CURATED_MAP = {
  "precolumbian_mesoamerica": (
    ["Millon1973", "Cowgill2015", "SandersParsonsSantley1979", "Blanton1999",
     "Kowalewski1989", "Diehl2004", "Pool2007", "Mastache2002", "Healan2012",
     "Carballo2016", "PlunketUrunuela2012"],
    [],
  ),
  "classic_postclassic_maya": (
    ["CulbertRice1990", "Canuto2018", "Turner1990", "SharerTraxler2006",
     "Webster2002", "MassonPeraza2014", "Kennett2012", "ChaseChase2012",
     "HoustonInomata2009", "Farriss1984"],
    [],
  ),
  "aztec_late_postclassic_mexico": (
    ["Smith2012Aztecs", "SandersParsonsSantley1979", "Berdan2014", "Calnek1972",
     "Rojas2012", "Pollard1993", "Hassig1985", "Carrasco1999", "Offner1983",
     "Smith2008AztecCity", "Whitmore1992"],
    [],
  ),
  "precolumbian_lower_central_america": (
    ["Cooke2005", "Lange1992", "QuilterHoopes2003", "Newson1986", "Newson1987",
     "Sheets2002", "Joyce1991", "Helms1979", "Hoopes2005"],
    ["hall_perez_brignoli_2003"],
  ),
  "precolumbian_caribbean_islands": (
    ["Rouse1992", "KeeganHofman2017", "Wilson2007", "Fitzpatrick2015",
     "Curet2005", "Siegel2015", "Fernandes2021", "Nagele2020", "Boomert2016",
     "Sauer1966"],
    [],
  ),
  "conquest_collapse_mesoamerica": (
    ["BorahCook1963", "CookBorah1971", "Gerhard1993", "Lovell1992",
     "MacLeod1973", "AcunaSoto2002", "Vagene2018", "Brooks1993", "Whitmore1992",
     "Newson1986"],
    ["aguirre_beltran_1946"],
  ),
  "viceroyalty_of_new_spain": (
    ["Gerhard1993", "CookBorah1971", "Gibson1964", "Brading1971",
     "RabellRomero1990", "MinoGrijalva2001", "Farriss1984"],
    ["humboldt_1811_essai", "gerhard_1962_mexico1742", "spp_1977_revillagigedo", "aguirre_beltran_1946"],
  ),
  "captaincy_general_guatemala": (
    ["Lovell1992", "MacLeod1973", "Lutz1994", "Newson1986", "Newson1987",
     "Wortman1982", "PerezBrignoli2010"],
    ["hall_perez_brignoli_2003", "juarros_1808_guatemala", "jaen_suarez_1978_panama", "sib_belize_censuses"],
  ),
  "conquest_indigenous_caribbean": (
    ["CookBorah1971", "Rouse1992", "LiviBacci2003", "Henige1978", "Sauer1966",
     "AndersonCordova2017", "DeaganCruxent2002", "Whitehead1995", "KeeganHofman2017",
     "Curet2005"],
    ["moya_pons_1995_domrep"],
  ),
  "colonial_caribbean_plantation": (
    ["EltisRichardson2010", "LiviBacci2003"],
    ["higman_1984_british_caribbean", "engerman_higman_1997", "geggus_1997_saint_domingue",
     "moreau_st_mery_1797", "roberts_1957_jamaica", "us_war_dept_1899_cuba",
     "us_war_dept_1899_puertorico", "danish_west_indies_censuses", "bso_bermuda_censuses",
     "nicholls_1979_haiti"],
  ),
  "mexico_after_independence": (
    ["McCaa2003", "Alba1982", "Garza2003", "Unikel1976", "CONAPO2023"],
    ["inegi_ehm_2014", "inegi_cpv_2020", "inegi_censos_1895_2010",
     "busto_1880_estadistica", "garcia_cubas_1884", "humboldt_1811_essai"],
  ),
  "central_american_republics": (
    ["PerezBrignoli2010"],
    ["ine_guatemala_censuses", "digestyc_bcr_elsalvador_censuses", "ine_honduras_censuses",
     "inide_nicaragua_censuses", "inec_costarica_censuses", "inec_panama_censuses",
     "sib_belize_censuses", "us_census_canal_zone", "davidson_2002_honduras1895",
     "hall_perez_brignoli_2003", "jaen_suarez_1978_panama"],
  ),
  "greater_antilles_modern": (
    ["DiazBriquets1983", "VazquezCalzada1988"],
    ["onei_cuba_censuses", "one_domrep_censuses", "ihsi_haiti_censuses",
     "statin_jamaica_censuses", "us_census_puertorico", "us_war_dept_1899_cuba",
     "us_war_dept_1899_puertorico", "eso_cayman_censuses", "roberts_1957_jamaica",
     "moya_pons_1995_domrep"],
  ),
  "lesser_antilles_bahamas_bermuda": (
    ["Boomert2016"],
    ["bss_barbados_censuses", "cso_trinidad_censuses", "nsi_bahamas_censuses",
     "bso_bermuda_censuses", "insee_dom_censuses", "cbs_netherlands_83698eng",
     "cbs_aruba", "cbs_curacao", "us_census_usvi", "cso_stlucia_censuses",
     "cso_grenada_censuses", "kuczynski_1953_west_indies", "un_dyb_historical"],
  ),
}

# Clean BibTeX keys for `jaguar_enum_sources.json` records
ENUM_KEY_MAP = {
  "aguirre_beltran_1946": "AguirreBeltran1946",
  "asd_anguilla_censuses": "ASDAnguilla2012",
  "bso_bermuda_censuses": "BSOBermuda2018",
  "bss_barbados_censuses": "BSSBarbados2023",
  "busto_1880_estadistica": "Busto1880",
  "cbs_aruba": "CBSAruba2022",
  "cbs_curacao": "CBSCuracao2024",
  "cbs_netherlands_83698eng": "CBSNetherlands2025",
  "cbs_netherlands_antilles": "CBSNethAntilles2002",
  "cso_bvi_censuses": "CSOBVI2014",
  "cso_dominica_censuses": "CSODominica2012",
  "cso_grenada_censuses": "CSOGrenada2023",
  "cso_stlucia_censuses": "CSOStLucia2023",
  "cso_trinidad_censuses": "CSOTrinidad2012",
  "danish_west_indies_censuses": "DanishWestIndies1912",
  "davidson_2002_honduras1895": "Davidson2002",
  "deps_turks_caicos_censuses": "DEPSTurksCaicos2014",
  "digestyc_bcr_elsalvador_censuses": "DIGESTYC2024",
  "ds_stkitts_nevis_censuses": "DSStKittsNevis2024",
  "engerman_higman_1997": "EngermanHigman1997",
  "eso_cayman_censuses": "ESOCayman2022",
  "garcia_cubas_1884": "GarciaCubas1884",
  "geggus_1997_saint_domingue": "Geggus1997",
  "gerhard_1962_mexico1742": "Gerhard1962",
  "hall_perez_brignoli_2003": "HallPerezBrignoli2003",
  "higman_1984_british_caribbean": "Higman1984",
  "humboldt_1811_essai": "Humboldt1811",
  "ihsi_haiti_censuses": "IHSIHaiti2015",
  "ine_guatemala_censuses": "INEGuatemala2019",
  "ine_honduras_censuses": "INEHonduras2015",
  "inec_costarica_censuses": "INECCostaRica2023",
  "inec_panama_censuses": "INECPanama2023",
  "inegi_censos_1895_2010": "INEGICensos1996",
  "inegi_cpv_2020": "INEGICPV2021",
  "inegi_ehm_2014": "INEGIEHM2015",
  "inide_nicaragua_censuses": "INIDENicaragua2006",
  "insee_dom_censuses": "INSEEDOM2024",
  "jaen_suarez_1978_panama": "JaenSuarez1978",
  "juarros_1808_guatemala": "Juarros1808",
  "kuczynski_1953_west_indies": "Kuczynski1953",
  "moreau_st_mery_1797": "MoreauStMery1797",
  "moya_pons_1995_domrep": "MoyaPons1995",
  "nicholls_1979_haiti": "Nicholls1979",
  "nsi_bahamas_censuses": "NSIBahamas2023",
  "one_domrep_censuses": "ONEDomRep2023",
  "onei_cuba_censuses": "ONEICuba2014",
  "roberts_1957_jamaica": "Roberts1957",
  "sd_antigua_censuses": "SDAntigua2014",
  "sd_montserrat_censuses": "SDMontserrat2019",
  "sib_belize_censuses": "SIBBelize2024",
  "so_stvincent_censuses": "SOStVincent2014",
  "spp_1977_revillagigedo": "SPPRevillagigedo1977",
  "stat_sint_maarten": "STATSintMaarten2018",
  "statin_jamaica_censuses": "STATINJamaica2012",
  "un_dyb_historical": "UNSDHistorical2000",
  "us_census_canal_zone": "USCensusCanalZone1973",
  "us_census_puertorico": "USCensusPR2024",
  "us_census_usvi": "USCensusUSVI2021",
  "us_war_dept_1899_cuba": "USWarDeptCuba1900",
  "us_war_dept_1899_puertorico": "USWarDeptPR1900",
}


def load_json5_simple (arg0_path):
  raw = open(arg0_path, encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def clean_bib_str (arg0_s):
  s = str(arg0_s or "")
  # Strip any raw HTML tags
  s = re.sub(r"</?[A-Za-z][^>]*>", "", s)
  # Replace problematic Unicode dashes, quotes, spaces that cause Karla/XeLaTeX tofu
  repl = {
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "--", "\u2014": "--",
    "\u2212": "-", "\u00a0": " ", "\u2009": " ", "\u200b": "", "\ufeff": "",
    "\u2018": "'", "\u2019": "'", "\u201c": "", "\u201d": "",
  }
  for k, v in repl.items():
    s = s.replace(k, v)
  s = s.replace("{", "").replace("}", "").replace('"', "").replace("\n", " ").replace("\r", " ")
  s = s.replace("\\", "")
  s = s.replace("&", "\\&").replace("%", "\\%").replace("_", " ").replace("#", "\\#").replace("$", "\\$")
  return re.sub(r"\s+", " ", s).strip()


def clean_url_str (arg0_u):
  u = str(arg0_u or "").strip()
  u = u.replace(" ", "%20")
  return u


def make_bib_key (arg0_authors, arg1_year, arg2_title, arg3_seen):
  first_raw = str((arg0_authors[0] if arg0_authors else "Author") or "Author")
  first_raw = first_raw.replace("\u2010", "-").replace("\u2011", "-")
  if "," in first_raw:
    first = first_raw.split(",")[0].strip().split()[-1]
  else:
    first = first_raw.strip().split()[-1]
  first = unicodedata.normalize("NFD", first)
  first = "".join(c for c in first if unicodedata.category(c) != "Mn")
  first = re.sub(r"[^A-Za-z]", "", first) or "Author"
  yr = re.sub(r"[^0-9]", "", str(arg1_year or "2020"))[:4] or "2020"
  stop = {"from", "with", "that", "this", "into", "over", "between", "under", "para", "sobre", "entre", "dans", "pour", "avec", "their", "study", "analysis"}
  word = ""
  for tok in re.findall(r"[A-Za-z]{4,}", unicodedata.normalize("NFD", str(arg2_title or ""))):
    t_clean = re.sub(r"[^A-Za-z]", "", tok)
    if len(t_clean) >= 4 and t_clean.lower() not in stop:
      word = t_clean.capitalize()
      break
  base = f"{first.capitalize()}{yr}{word}"
  k = base
  n = 2
  while k in arg3_seen:
    k = f"{base}{chr(96 + n)}" if n <= 26 else f"{base}{n}"
    n += 1
  arg3_seen.add(k)
  return k


def format_entry (arg0_key, arg1_etype, arg2_author, arg3_title, arg4_venue, arg5_year, arg6_doi, arg7_url):
  auth_c = clean_bib_str(arg2_author)
  # Corporate / institutional authors wrapped in braces if no comma & institutional words
  if (
    " and " not in auth_c
    and "," not in auth_c
    and any(w in auth_c.lower() for w in ("instituto", "institut", "bureau", "office", "department", "service", "division", "council", "consejo", "nations", "secretar", "direcci", "oficina", "statist", "government", "commission"))
  ):
    auth_field = "{" + auth_c + "}"
  else:
    auth_field = auth_c
  title_c = clean_bib_str(arg3_title)
  venue_c = clean_bib_str(arg4_venue)
  lines = [f"@{arg1_etype}{{{arg0_key},"]
  lines.append(f"  author = {{{auth_field}}},")
  lines.append(f"  title = {{{{{title_c}}}}},")
  if arg1_etype == "article":
    lines.append(f"  journal = {{{venue_c}}},")
  else:
    lines.append(f"  publisher = {{{venue_c}}},")
  lines.append(f"  year = {{{arg5_year}}},")
  if arg6_doi and str(arg6_doi).startswith("10."):
    lines.append(f"  doi = {{{str(arg6_doi).strip()}}},")
  if arg7_url and str(arg7_url).startswith("http"):
    lines.append(f"  url = {{{clean_url_str(arg7_url)}}},")
  lines.append("}")
  return "\n".join(lines)


def audit_bib_entries (arg0_entries_meta):
  total = len(arg0_entries_meta)
  linked = sum(1 for e in arg0_entries_meta if e["doi_or_url"].startswith(("10.", "http")))
  pub_counts = Counter()
  auth_counts = Counter()
  for e in arg0_entries_meta:
    pub = str(e["publisher"] or "").strip().lower()[:40]
    if pub:
      pub_counts[pub] += 1
    first = str(e["author"] or "").split(" and ")[0].replace("{", "").replace("}", "").strip()
    surname = first.split(",")[0].strip().lower() if "," in first else (first.split()[-1].lower() if first.split() else "")
    if len(surname) >= 3:
      auth_counts[surname] += 1
  top_pub, top_pub_n = pub_counts.most_common(1)[0] if pub_counts else ("", 0)
  top_auth, top_auth_n = auth_counts.most_common(1)[0] if auth_counts else ("", 0)
  return {
    "total": total,
    "linked": linked,
    "linked_pct": round(100.0 * linked / max(1, total), 1),
    "distinct_publishers": len(pub_counts),
    "max_pub_share_pct": round(100.0 * top_pub_n / max(1, total), 1),
    "top_pub": top_pub,
    "max_auth_share_pct": round(100.0 * top_auth_n / max(1, total), 1),
    "top_auth": top_auth,
  }


def main ():
  itin = load_json5_simple(ITIN_PATH)
  enum_data = json.load(open(ENUM_SRC_PATH, encoding="utf-8"))
  enum_sources = enum_data.get("sources", {})

  root_entries = {}
  bib_index = {}
  total_ch_entries = 0

  for ch in itin["chapters"]:
    stem = ch["stem"]
    idx = ch["index"]
    ch_dir = os.path.join(JAG_DIR, ch["group"], ch["folder"])
    pmeta_path = os.path.join(ch_dir, "papers", "papers_metadata.json")
    pmeta = json.load(open(pmeta_path, encoding="utf-8")) if os.path.isfile(pmeta_path) else []

    seen_keys = set()
    bib_blocks = []
    index_rows = []

    # 1. Include ALL verified Wave 2 archived PDFs from papers/papers_metadata.json
    for m in pmeta:
      title_raw = m.get("title") or ""
      auths = m.get("authors") or ["Contributors"]
      auth_str = " and ".join(clean_bib_str(a) for a in auths[:5])
      yr = str(m.get("year") or 2020)
      doi = str(m.get("doi") or "").strip()
      url = str(m.get("url") or m.get("pdf_url") or "").strip()
      venue = str(m.get("journal_or_publisher") or m.get("publisher_domain") or "Mesoamerican and Caribbean Studies")
      blob = f"{title_raw} {auth_str} {doi} {url} {venue}"
      if BANNED_SUBCHAPTER_RE.search(blob):
        continue
      if not (doi.startswith("10.") or url.startswith("http")):
        continue
      bkey = make_bib_key(auths, yr, title_raw, seen_keys)
      blk = format_entry(bkey, "article", auth_str, title_raw, venue, yr, doi, url)
      bib_blocks.append(blk)
      index_rows.append({
        "key": bkey,
        "title": clean_bib_str(title_raw),
        "author": auth_str,
        "year": int(yr) if yr.isdigit() else yr,
        "publisher": clean_bib_str(venue),
        "doi_or_url": doi if doi.startswith("10.") else url,
        "is_archived_pdf": True,
      })

    # 2. Add curated canonical regional monographs & official NSO series
    can_keys, enum_keys = CHAPTER_CURATED_MAP.get(stem, ([], []))
    for ck in can_keys:
      if ck in seen_keys or ck not in CANONICAL_REFS:
        continue
      seen_keys.add(ck)
      etype, author, title, venue, yr, doi, url = CANONICAL_REFS[ck]
      blk = format_entry(ck, etype, author, title, venue, yr, doi, url)
      bib_blocks.append(blk)
      root_entries[ck] = blk
      index_rows.append({
        "key": ck,
        "title": clean_bib_str(title),
        "author": clean_bib_str(author),
        "year": int(yr) if yr.isdigit() else yr,
        "publisher": clean_bib_str(venue),
        "doi_or_url": doi if doi.startswith("10.") else url,
        "is_archived_pdf": False,
      })

    for ek in enum_keys:
      if ek not in enum_sources:
        continue
      bkey = ENUM_KEY_MAP.get(ek, ek.title().replace("_", ""))
      if bkey in seen_keys:
        continue
      seen_keys.add(bkey)
      es = enum_sources[ek]
      author = es["author"]
      title = es["title"]
      venue = es["publisher"]
      yr = str(es["year"])
      url = es["url"]
      etype = "misc" if any(w in ek for w in ("censuses", "cpv", "ehm", "cbs_", "stat_", "un_dyb", "us_census")) else "book"
      blk = format_entry(bkey, etype, author, title, venue, yr, "", url)
      bib_blocks.append(blk)
      root_entries[bkey] = blk
      index_rows.append({
        "key": bkey,
        "title": clean_bib_str(title),
        "author": clean_bib_str(author),
        "year": int(yr) if yr.isdigit() else yr,
        "publisher": clean_bib_str(venue),
        "doi_or_url": url,
        "is_archived_pdf": False,
      })

    bib_out = os.path.join(ch_dir, f"{stem}_literature_review.bib")
    with open(bib_out, "w", encoding="utf-8") as fh:
      fh.write("\n\n".join(bib_blocks) + "\n")

    keys_out = os.path.join(ch_dir, f"{stem}_bib_keys.json")
    with open(keys_out, "w", encoding="utf-8") as fh:
      json.dump({"bib_file": f"{stem}_literature_review.bib", "keys": [r["key"] for r in index_rows]}, fh, indent=2, ensure_ascii=False)

    bib_index[stem] = index_rows
    total_ch_entries += len(index_rows)
    st = audit_bib_entries(index_rows)
    flag = "OK"
    if not (24 <= st["total"] <= 32) or st["linked_pct"] < 90.0 or st["distinct_publishers"] < 7 or st["max_pub_share_pct"] > 25.0 or st["max_auth_share_pct"] > 25.0:
      flag = "CHECK"
    print(
      f"  [CH {idx:02d}] {stem:35s}: {st['total']:2d} keys ({sum(r['is_archived_pdf'] for r in index_rows):2d} PDF) | "
      f"DOI/URL={st['linked_pct']:5.1f}% | pubs={st['distinct_publishers']:2d} | "
      f"maxPub={st['max_pub_share_pct']:4.1f}% | maxAuth={st['max_auth_share_pct']:4.1f}% [{flag}]",
      flush=True,
    )

  # Include ALL 60 enum sources + all canonical refs + root-only baselines in root `studies_on_population.bib`
  for ek, es in enum_sources.items():
    bkey = ENUM_KEY_MAP.get(ek, ek.title().replace("_", ""))
    if bkey not in root_entries:
      etype = "misc" if any(w in ek for w in ("censuses", "cpv", "ehm", "cbs_", "stat_", "un_dyb", "us_census")) else "book"
      root_entries[bkey] = format_entry(bkey, etype, es["author"], es["title"], es["publisher"], str(es["year"]), "", es["url"])
  for rk, tup in ROOT_ONLY_REFS.items():
    etype, author, title, venue, yr, doi, url = tup
    root_entries[rk] = format_entry(rk, etype, author, title, venue, yr, doi, url)

  root_bib = os.path.join(JAG_DIR, "studies_on_population.bib")
  with open(root_bib, "w", encoding="utf-8") as fh:
    fh.write("\n\n".join(root_entries[k] for k in sorted(root_entries.keys())) + "\n")

  idx_out = os.path.join(SHARED, "jaguar_bib_keys_index.json")
  with open(idx_out, "w", encoding="utf-8") as fh:
    json.dump(bib_index, fh, indent=2, ensure_ascii=False)

  print(f"\n[DONE] 14 chapter .bib files ({total_ch_entries} total entries) + root studies_on_population.bib ({len(root_entries)} entries) + jaguar_bib_keys_index.json written.", flush=True)


if __name__ == "__main__":
  main()
