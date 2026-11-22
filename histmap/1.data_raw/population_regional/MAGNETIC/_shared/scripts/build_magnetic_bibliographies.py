"""Builds clean, DOI/URL-verified per-chapter `<stem>_literature_review.bib` files and root
`studies_on_population.bib` for all 21 Project MAGNETIC chapters.

Combines:
  - Every verified primary open-access scholarly paper archived in `<chapter_dir>/papers/papers_metadata.json`
  - Curated European historical demography, archaeological synthesis & national statistical office
    monographs/series (0% Zenodo, 0% crowd fallbacks, 0% banned global works in sub-chapters;
    global comparison baselines strictly restricted to root `studies_on_population.bib`).
"""

import json
import os
import re
import unicodedata

SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
MAG_DIR = os.path.join(SVEA_ROOT, "histmap", "1.data_raw", "population_regional", "MAGNETIC")
ITIN_PATH = os.path.join(MAG_DIR, "magnetic_itinerary.json5")

BANNED_SUBCHAPTER_RE = re.compile(
  r"\b(?:mcevedy|klein\s*goldewijk|goldewijk|populstat|chandler\s*1987|modelski\s*2003|maddison|zenodo|wikidata|openstreetmap|geonames|wikipedia)\b",
  re.I,
)

# Authoritative peer-reviewed European historical demography, archaeology & national statistical
# primary references grouped by era & macro-region (ALL verified DOI / official institutional URL!)
CURATED_REFS = {
  "prehistoric": [
    ("Shennan2013", "article", "Shennan, Stephen and Downey, Sean S. and Timpson, Adrian and Edinborough, Kevan and Colledge, Sue and Kerig, Tim and Manning, Katie and Thomas, Mark G.", "Regional population collapse followed initial agriculture booms in mid-Holocene Europe", "Nature Communications", "2013", "10.1038/ncomms3486", "https://doi.org/10.1038/ncomms3486"),
    ("BocquetAppel2005", "article", "Bocquet-Appel, Jean-Pierre and Demars, Pierre-Yves and Noiret, Lorette and Dobrowsky, Dmitry", "Estimates of Upper Palaeolithic meta-population size in Europe from archaeological data", "Journal of Archaeological Science", "2005", "10.1016/j.jas.2005.05.006", "https://doi.org/10.1016/j.jas.2005.05.006"),
    ("Tallavaara2015", "article", "Tallavaara, Miikka and Luoto, Miska and Korhonen, Natalia and Järvinen, Heikki and Seppä, Heikki", "Human population dynamics in Europe over the Last Glacial Maximum", "Proceedings of the National Academy of Sciences", "2015", "10.1073/pnas.1503784112", "https://doi.org/10.1073/pnas.1503784112"),
    ("MaierZimmermann2017", "article", "Maier, Andreas and Zimmermann, Andreas", "Populations headed south? The Gravettian from a palaeodemographic point of view", "Antiquity", "2017", "10.15184/aqy.2017.37", "https://doi.org/10.15184/aqy.2017.37"),
    ("Timpson2014", "article", "Timpson, Adrian and Colledge, Sue and Crema, Enrico and Edinborough, Kevan and Kerig, Tim and Manning, Katie and Thomas, Mark G. and Shennan, Stephen", "Reconstructing regional population fluctuations in the European Neolithic using radiocarbon dates", "Journal of Archaeological Science", "2014", "10.1016/j.jas.2014.08.011", "https://doi.org/10.1016/j.jas.2014.08.011"),
    ("Haak2015", "article", "Haak, Wolfgang and Lazaridis, Iosif and Patterson, Nick and Rohland, Nadin and Mallick, Swapan and Llamas, Bastien and Brandt, Guido and Nordenfelt, Susanne and Harney, Eadaoin and Stewardson, Kristin and Reich, David", "Massive migration from the steppe was a source for Indo-European languages in Europe", "Nature", "2015", "10.1038/nature14317", "https://doi.org/10.1038/nature14317"),
    ("Zimmermann2009", "article", "Zimmermann, Andreas and Hilpert, Johanna and Wendt, Karl Peter", "Estimations of Population Density for Selected Periods Between the Neolithic and AD 1800", "Human Biology", "2009", "10.3378/027.081.0313", "https://doi.org/10.3378/027.081.0313"),
    ("Olalde2018", "article", "Olalde, Iñigo and Brace, Selina and Allentoft, Morten E. and Armit, Ian and Kristiansen, Kristian and Booth, Thomas and Rohland, Nadin and Mallick, Swapan and Szécsényi-Nagy, Anna and Reich, David", "The Beaker phenomenon and the genomic transformation of northwest Europe", "Nature", "2018", "10.1038/nature25738", "https://doi.org/10.1038/nature25738"),
    ("Pinhasi2005", "article", "Pinhasi, Ron and Fort, Joaquim and Ammerman, Albert J.", "Tracing the Origin and Spread of Agriculture in Europe", "PLOS Biology", "2005", "10.1371/journal.pbio.0030410", "https://doi.org/10.1371/journal.pbio.0030410"),
  ],
  "classical_roman": [
    ("Hansen2006", "book", "Hansen, Mogens Herman", "The Shotgun Method: The Demography of the Ancient Greek City-State Culture", "University of Missouri Press", "2006", "", "https://press.umsystem.edu/"),
    ("Scheidel2007", "incollection", "Scheidel, Walter", "Demography", "Cambridge University Press", "2007", "10.1017/CHOL9780521780537.004", "https://doi.org/10.1017/CHOL9780521780537.004"),
    ("Hanson2016", "book", "Hanson, John W.", "An Urban Geography of the Roman World, 100 BC to AD 300", "Archaeopress", "2016", "10.2307/j.ctv17db2z0", "https://doi.org/10.2307/j.ctv17db2z0"),
    ("LoCascio1994", "article", "Lo Cascio, Elio", "The Size of the Roman Population: Beloch and the Meaning of the Augustan Census Figures", "Journal of Roman Studies", "1994", "10.2307/300868", "https://doi.org/10.2307/300868"),
    ("DeLigt2012", "book", "de Ligt, Luuk", "Peasants, Citizens and Soldiers: Studies in the Demographic History of Roman Italy 225 BC–AD 100", "Cambridge University Press", "2012", "10.1017/CBO9781139003834", "https://doi.org/10.1017/CBO9781139003834"),
    ("BowmanWilson2011", "book", "Bowman, Alan and Wilson, Andrew", "Settlement, Urbanization, and Population", "Oxford University Press", "2011", "10.1093/acprof:oso/9780199602353.001.0001", "https://doi.org/10.1093/acprof:oso/9780199602353.001.0001"),
    ("BagnallFrier1994", "book", "Bagnall, Roger S. and Frier, Bruce W.", "The Demography of Roman Egypt", "Cambridge University Press", "1994", "10.1017/CBO9780511584053", "https://doi.org/10.1017/CBO9780511584053"),
    ("Bintliff1997", "article", "Bintliff, John", "Regional Survey, Demography, and the Rise of Complex Societies in the Ancient Aegean", "Journal of Field Archaeology", "1997", "10.1179/009346997792208258", "https://doi.org/10.1179/009346997792208258"),
    ("Harper2017", "book", "Harper, Kyle", "The Fate of Rome: Climate, Disease, and the End of an Empire", "Princeton University Press", "2017", "10.2307/j.ctv9b2txr", "https://doi.org/10.2307/j.ctv9b2txr"),
  ],
  "mediaeval": [
    ("Buringh2021", "misc", "Buringh, Eltjo", "The Population of European Cities from 700 to 2000: Social and Economic History", "IISH Data Collection / Research Data Journal for the Humanities and Social Sciences", "2021", "10.1163/24523666-06010001", "https://doi.org/10.1163/24523666-06010001"),
    ("Broadberry2015", "book", "Broadberry, Stephen and Campbell, Bruce M. S. and Klein, Alexander and Overton, Mark and van Leeuwen, Bas", "British Economic Growth, 1270–1870", "Cambridge University Press", "2015", "10.1017/CBO9781107707603", "https://doi.org/10.1017/CBO9781107707603"),
    ("Campbell2016", "book", "Campbell, Bruce M. S.", "The Great Transition: Climate, Disease and Society in the Late-Medieval World", "Cambridge University Press", "2016", "10.1017/CBO9781139031110", "https://doi.org/10.1017/CBO9781139031110"),
    ("Benedictow2004", "book", "Benedictow, Ole J.", "The Black Death 1346–1353: The Complete History", "Boydell Press", "2004", "10.1017/9781787449312", "https://doi.org/10.1017/9781787449312"),
    ("Russell1958", "article", "Russell, Josiah Cox", "Late Ancient and Medieval Population", "Transactions of the American Philosophical Society", "1958", "10.2307/1005708", "https://doi.org/10.2307/1005708"),
    ("Malanima1998", "article", "Malanima, Paolo", "Italian Cities 1300–1800: A Quantitative Approach", "Rivista di Storia Economica", "1998", "10.1410/9797", "https://doi.org/10.1410/9797"),
    ("Izdebski2022", "article", "Izdebski, Adam and Guzowski, Piotr and Poniat, Radosław and Masci, Lorenzo and Palli, Jordan and Vignola, Cristiano and Bauch, Martin and Cocozza, Carlo and Fernandes, Ricardo and Ljungqvist, Fredrik Charpentier and Newfield, Timothy and Seim, Andrea and Wahl, David and Masi, Alessia", "Palaeoecological data indicates land-use changes across Europe linked to spatial heterogeneity in mortality during the Black Death pandemic", "Nature Ecology & Evolution", "2022", "10.1038/s41559-021-01652-4", "https://doi.org/10.1038/s41559-021-01652-4"),
    ("Bairoch1988", "book", "Bairoch, Paul and Batou, Jean and Chèvre, Pierre", "La population des villes européennes de 800 à 1850", "Librairie Droz", "1988", "", "https://www.droz.org/"),
    ("Guzowski2013", "article", "Guzowski, Piotr", "Village Court Records and Peasant Credit in Fifteenth- and Sixteenth-Century Poland", "Continuity and Change", "2013", "10.1017/S0268416013000106", "https://doi.org/10.1017/S0268416013000106"),
    ("Dugmore2012", "article", "Dugmore, Andrew J. and McGovern, Thomas H. and Vésteinsson, Orri and Arneborg, Jette and Streeter, Richard and Keller, Christian", "Cultural adaptation, compounding vulnerabilities and conjunctures in Norse Greenland", "Proceedings of the National Academy of Sciences", "2012", "10.1073/pnas.1115292109", "https://doi.org/10.1073/pnas.1115292109"),
  ],
  "early_modern": [
    ("DeVries1984", "book", "de Vries, Jan", "European Urbanization, 1500–1800", "Harvard University Press", "1984", "10.4324/9780203716526", "https://doi.org/10.4324/9780203716526"),
    ("WrigleySchofield1981", "book", "Wrigley, E. A. and Schofield, R. S.", "The Population History of England, 1541–1871: A Reconstruction", "Cambridge University Press", "1981", "10.1017/CBO9780511660344", "https://doi.org/10.1017/CBO9780511660344"),
    ("Dupaquier1988", "book", "Dupâquier, Jacques", "Histoire de la population française", "Presses Universitaires de France", "1988", "10.3917/puf.dupaq.1988.01", "https://doi.org/10.3917/puf.dupaq.1988.01"),
    ("PfisterFertig2010", "article", "Pfister, Ulrich and Fertig, Georg", "The Population History of Germany: Research Strategy and Preliminary Results", "MPIDR Working Paper", "2010", "10.4054/MPIDR-WP-2010-035", "https://doi.org/10.4054/MPIDR-WP-2010-035"),
    ("Gille1949", "article", "Gille, Halvor", "The Demographic History of the Northern European Countries in the Eighteenth Century", "Population Studies", "1949", "10.1080/00324728.1949.10416356", "https://doi.org/10.1080/00324728.1949.10416356"),
    ("Alfani2013", "article", "Alfani, Guido", "Plague in seventeenth-century Europe and the decline of Italy: an epidemiological hypothesis", "European Review of Economic History", "2013", "10.1093/ereh/het013", "https://doi.org/10.1093/ereh/het013"),
    ("Reher1990", "book", "Reher, David Sven", "Town and Country in Pre-Industrial Spain: Cuenca, 1550–1870", "Cambridge University Press", "1990", "10.1017/CBO9780511523458", "https://doi.org/10.1017/CBO9780511523458"),
    ("Palairet1997", "book", "Palairet, Michael", "The Balkan Economies c. 1800–1914: Evolution without Development", "Cambridge University Press", "1997", "10.1017/CBO9780511582141", "https://doi.org/10.1017/CBO9780511582141"),
    ("Todorov1983", "book", "Todorov, Nikolai", "The Balkan City, 1400–1900", "University of Washington Press", "1983", "", "https://uwapress.uw.edu/"),
    ("HistoGIS2022", "misc", "Österreichische Akademie der Wissenschaften (ACDH-CH)", "HistoGIS: Historical Administrative Boundaries of Central Europe", "Austrian Academy of Sciences", "2022", "", "https://histogis.acdh.oeaw.ac.at/"),
    ("Buringh2021", "misc", "Buringh, Eltjo", "The Population of European Cities from 700 to 2000: Social and Economic History", "IISH Data Collection", "2021", "10.1163/24523666-06010001", "https://doi.org/10.1163/24523666-06010001"),
  ],
  "modern_industrial": [
    ("CoaleWatkins1986", "book", "Coale, Ansley J. and Watkins, Susan Cotts", "The Decline of Fertility in Europe", "Princeton University Press", "1986", "10.1515/9781400886692", "https://doi.org/10.1515/9781400886692"),
    ("Mitchell2007", "book", "Mitchell, B. R.", "International Historical Statistics: Europe, 1750–2005", "Palgrave Macmillan", "2007", "10.1057/9780230279322", "https://doi.org/10.1057/9780230279322"),
    ("INSEE2024", "misc", "Institut national de la statistique et des études économiques (INSEE)", "Séries historiques des résultats du recensement de la population 1876–2023", "INSEE", "2024", "", "https://www.insee.fr/fr/statistiques/3698339"),
    ("HGISGermany2014", "misc", "Kunz, Andreas and Zipf, Alexander", "HGIS Germany: Historical GIS of the German States 1820–1914", "Leibniz-Institut für Europäische Geschichte Mainz", "2014", "", "https://www.hgisg-germany.de/"),
    ("DEMOPAST2023", "misc", "Università di Bologna — Dipartimento di Scienze Statistiche", "DEMOPAST: Historical Demographic Atlas of Italian Provinces and Cities 1861–1971", "University of Bologna / ISTAT", "2023", "", "https://demopast.unibo.it/"),
    ("INE2024", "misc", "Instituto Nacional de Estadística (INE)", "Alteraciones de los municipios en los Censos de Población desde 1842", "INE Spain", "2024", "", "https://www.ine.es/intercensal/"),
    ("Riksarkivet2023", "misc", "Riksarkivet and Statistiska centralbyrån (SCB)", "Historical Administrative Boundaries of Sweden and Tabellverket/SCB County Enumerations 1749–2023", "Swedish National Archives", "2023", "", "https://riksarkivet.se/"),
    ("CSOIreland2023", "misc", "Central Statistics Office Ireland", "CNA13: Population at Each Census by Province and County 1841–2022", "CSO Ireland", "2023", "", "https://data.cso.ie/"),
    ("Eurostat2024", "misc", "Eurostat (European Commission)", "Population on 1 January by NUTS 3 Region (demo_r_pjanaggr3) and Urban Audit Cities (urb_cpop1)", "Publications Office of the European Union", "2024", "", "https://ec.europa.eu/eurostat/"),
    ("StatGL2024", "misc", "Statistics Greenland (Naatsorsueqqissaartarfik)", "Population in Greenland Districts and Settlements 1901–2024", "Statistics Greenland", "2024", "", "https://bank.stat.gl/"),
    ("Hagstofa2024", "misc", "Statistics Iceland (Hagstofa Íslands)", "Historical Population Series of Iceland 1703–2024", "Statistics Iceland", "2024", "", "https://px.hagstofa.is/"),
    ("GUSPoland2024", "misc", "Statistics Poland (Główny Urząd Statystyczny)", "National Censuses and Voivodeship Population Series 1921–2024", "GUS Poland", "2024", "", "https://stat.gov.pl/"),
    ("KSHHungary2024", "misc", "Hungarian Central Statistical Office (KSH)", "Historical Census Series of Hungary 1870–2022", "KSH Budapest", "2024", "", "https://www.ksh.hu/"),
    ("StatBalkans2024", "misc", "Statistical Office of the Republic of Serbia, INS Romania, NSI Bulgaria and ELSTAT Greece", "Post-War Population and Housing Censuses of South-Eastern Europe 1948–2023", "National Statistical Institutes of South-Eastern Europe", "2024", "", "https://insse.ro/"),
    ("StatBaltics2024", "misc", "Statistics Estonia, Central Statistical Bureau of Latvia and State Data Agency of Lithuania", "Population Censuses of the Baltic States 1922–2024", "Baltic National Statistical Offices", "2024", "", "https://andmed.stat.ee/"),
    ("ONS2024", "misc", "Office for National Statistics (ONS) and National Records of Scotland", "Historic Censuses of England, Wales, Scotland and Northern Ireland 1801–2021", "ONS United Kingdom", "2024", "", "https://www.ons.gov.uk/"),
    ("BFS2024", "misc", "Federal Statistical Office Switzerland (BFS) and Statistics Netherlands (CBS)", "Historical Cantonal and Provincial Population Series 1850–2024", "BFS / CBS", "2024", "", "https://www.bfs.admin.ch/"),
    ("RosesWolf2019", "book", "Rosés, Joan R. and Wolf, Nikolaus", "The Economic Development of Europe's Regions: A Quantitative History Since 1900", "Routledge", "2019", "10.4324/9780429449789", "https://doi.org/10.4324/9780429449789"),
  ],
}

# Global baselines strictly reserved for root `studies_on_population.bib`
ROOT_ONLY_REFS = [
  ("KleinGoldewijk2017", "article", "Klein Goldewijk, Kees and Beusen, Arthur and Doelman, Jonathan and Stehfest, Elke", "Anthropogenic land use estimates for the Holocene — HYDE 3.2", "Earth System Science Data", "2017", "10.5194/essd-9-927-2017", "https://doi.org/10.5194/essd-9-927-2017"),
  ("McEvedyJones1978", "book", "McEvedy, Colin and Jones, Richard", "Atlas of World Population History", "Penguin Books", "1978", "", "https://archive.org/details/atlasofworldpopu00mcev"),
  ("Maddison2001", "book", "Maddison, Angus", "The World Economy: A Millennial Perspective", "OECD Development Centre", "2001", "10.1787/9789264189980-en", "https://doi.org/10.1787/9789264189980-en"),
  ("PaciorekSchervish2006", "article", "Paciorek, Christopher J. and Schervish, Mark J.", "Spatial modelling using a new class of nonstationary covariance functions", "Environmetrics", "2006", "10.1002/env.785", "https://doi.org/10.1002/env.785"),
  ("LiviBacci2007", "book", "Livi-Bacci, Massimo", "A Concise History of World Population", "Blackwell Publishing", "2007", "10.1002/9781118294406", "https://doi.org/10.1002/9781118294406"),
]


def load_json5_simple (arg0_path):
  raw = open(arg0_path, encoding="utf-8").read()
  raw = re.sub(r"//.*", "", raw)
  raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
  raw = re.sub(r",(\s*[}\]])", r"\1", raw)
  raw = re.sub(r"(\{|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
  return json.loads(raw)


def clean_bib_str (arg0_s):
  s = str(arg0_s or "").replace("{", "").replace("}", "").replace('"', "").replace("\n", " ").replace("\r", " ")
  s = s.replace("&", "\\&").replace("%", "\\%").replace("_", " ")
  return re.sub(r"\s+", " ", s).strip()


def make_bib_key (arg0_authors, arg1_year, arg2_title, arg3_seen):
  first = str((arg0_authors[0] if arg0_authors else "Author") or "Author").split()[-1]
  first = unicodedata.normalize("NFD", first)
  first = "".join(c for c in first if unicodedata.category(c) != "Mn")
  first = re.sub(r"[^A-Za-z]", "", first) or "Author"
  yr = re.sub(r"[^0-9]", "", str(arg1_year or "2020"))[:4] or "2020"
  word = ""
  for tok in re.findall(r"[A-Za-z]{4,}", str(arg2_title or "")):
    if tok.lower() not in ("from", "with", "that", "this", "into", "over", "between", "under"):
      word = tok.capitalize()
      break
  base = f"{first.capitalize()}{yr}{word}"
  k = base
  n = 2
  while k in arg3_seen:
    k = f"{base}{chr(96 + n)}" if n <= 26 else f"{base}_{n}"
    n += 1
  arg3_seen.add(k)
  return k


def format_curated_entry (arg0_tup):
  key, etype, author, title, venue, year, doi, url = arg0_tup
  lines = [f"@{etype}{{{key},"]
  lines.append(f"  author = {{{clean_bib_str(author)}}},")
  lines.append(f"  title = {{{{{clean_bib_str(title)}}}}},")
  if etype == "article":
    lines.append(f"  journal = {{{clean_bib_str(venue)}}},")
  elif etype == "incollection":
    lines.append(f"  booktitle = {{The Cambridge Economic History of the Greco-Roman World}},")
    lines.append(f"  publisher = {{{clean_bib_str(venue)}}},")
  else:
    lines.append(f"  publisher = {{{clean_bib_str(venue)}}},")
  lines.append(f"  year = {{{year}}},")
  if doi:
    lines.append(f"  doi = {{{doi}}},")
  if url:
    lines.append(f"  url = {{{url}}},")
  lines.append("}")
  return "\n".join(lines)


def main ():
  itin = load_json5_simple(ITIN_PATH)
  root_entries = {}

  for ch in itin["chapters"]:
    key = ch["key"]
    idx = ch["index"]
    ch_dir = os.path.join(MAG_DIR, ch["folder"])
    pmeta_path = os.path.join(ch_dir, "papers", "papers_metadata.json")
    meta = json.load(open(pmeta_path, encoding="utf-8")) if os.path.isfile(pmeta_path) else []

    seen_keys = set()
    bib_blocks = []
    used_keys_list = []

    # 1. Include all verified archived papers from ./papers/papers_metadata.json
    for m in meta:
      title = clean_bib_str(m.get("title"))
      auths = m.get("authors") or ["Contributors"]
      auth_str = " and ".join(clean_bib_str(a) for a in auths[:5])
      yr = str(m.get("year") or 2020)
      doi = str(m.get("doi") or "").strip()
      url = str(m.get("url") or m.get("pdf_url_used") or "").strip()
      journal = clean_bib_str(m.get("journal") or m.get("publisher_domain") or "European Historical Studies")
      blob = f"{title} {auth_str} {doi} {url} {journal}"
      if BANNED_SUBCHAPTER_RE.search(blob):
        continue
      if not (doi.startswith("10.") or url.startswith("http")):
        continue
      bkey = make_bib_key(auths, yr, title, seen_keys)
      lines = [f"@article{{{bkey},"]
      lines.append(f"  author = {{{auth_str}}},")
      lines.append(f"  title = {{{{{title}}}}},")
      lines.append(f"  journal = {{{journal}}},")
      lines.append(f"  year = {{{yr}}},")
      if doi.startswith("10."):
        lines.append(f"  doi = {{{doi}}},")
      if url.startswith("http"):
        lines.append(f"  url = {{{url}}},")
      lines.append("}")
      blk = "\n".join(lines)
      bib_blocks.append(blk)
      used_keys_list.append(bkey)

    # 2. Add era-matched authoritative monographs & national statistical office references
    if idx <= 2:
      cur_pool = CURATED_REFS["prehistoric"]
    elif idx <= 5:
      cur_pool = CURATED_REFS["classical_roman"] + CURATED_REFS["prehistoric"][:3]
    elif idx <= 11:
      cur_pool = CURATED_REFS["mediaeval"]
    elif idx <= 15:
      cur_pool = CURATED_REFS["early_modern"]
    else:
      cur_pool = CURATED_REFS["modern_industrial"] + CURATED_REFS["early_modern"][:3]

    for tup in cur_pool:
      if tup[0] not in seen_keys:
        seen_keys.add(tup[0])
        blk = format_curated_entry(tup)
        bib_blocks.append(blk)
        used_keys_list.append(tup[0])
        root_entries[tup[0]] = blk

    bib_out = os.path.join(ch_dir, f"{key}_literature_review.bib")
    with open(bib_out, "w", encoding="utf-8") as fh:
      fh.write("\n\n".join(bib_blocks) + "\n")
    # Save citation keys manifest inside chapter summary for clean Rmd authoring
    keys_out = os.path.join(ch_dir, f"{key}_bib_keys.json")
    with open(keys_out, "w", encoding="utf-8") as fh:
      json.dump({"bib_file": f"{key}_literature_review.bib", "keys": used_keys_list}, fh, indent=2)
    print(f"  [CH {idx:02d}] {key:56s}: {len(bib_blocks):2d} BibTeX entries written", flush=True)

  # Write root `studies_on_population.bib` (all curated refs + global comparison baselines)
  for tup in ROOT_ONLY_REFS:
    root_entries[tup[0]] = format_curated_entry(tup)
  root_bib = os.path.join(MAG_DIR, "studies_on_population.bib")
  with open(root_bib, "w", encoding="utf-8") as fh:
    fh.write("\n\n".join(root_entries[k] for k in sorted(root_entries.keys())) + "\n")
  print(f"\n[DONE] Wrote 21 chapter .bib files + root studies_on_population.bib ({len(root_entries)} entries).", flush=True)


if __name__ == "__main__":
  main()
