"""Resolves Operation Viscount INDUS historical toponymy batches and curates authoritative
multi-millennial South Asian city name transitions for Dataview `stadester_2.0/city_metadata.json`.

Sources:
1. Curated scholarly South Asian historical toponymy catalogue (ancient Sanskrit/Prakrit/Pali/Tamil/
   Greco-Roman -> Sultanate/Mughal/Persianate -> Portuguese/Dutch/French/British colonial ->
   post-independence official renames across India, Pakistan, Bangladesh, Sri Lanka, Nepal, Bhutan, Maldives).
2. Official GeoNames alternate names (cached in `_census_cache/geonames_{IN,PK,BD,LK,NP,BT,MV}.zip`),
   strictly filtered for clean Latin + indigenous South Asian scripts (zero corrupted characters).
"""

import glob
import json
import math
import os
import re
import zipfile
from collections import defaultdict


SVEA_ROOT = r"f:\Active Projects\Project 1509 - SVEA"
CENSUS_DIR = os.path.join(
  SVEA_ROOT,
  "histmap", "1.data_raw", "population_regional", "INDUS", "_shared", "_census_cache"
)
DATAVIEW_META = r"F:\Active Projects\Project 1436 - Dataview\data\stadester\stadester_2.0\city_metadata.json"
BATCH_DIR = os.path.join(SVEA_ROOT, "tests", "toponymy_batches", "indus")

# Authoritative curated chronological toponymy transitions keyed by (normalised_modern_name, country).
# Every entry strictly terminates with the exact modern canonical settlement name to guarantee zero
# Signature A/B suburb/annex hijacks in Dataview.
CURATED_HISTORICAL_NAMES = {
  # --- INDIA ---
  ("delhi", "India"): [
    {"date": "-1000.1.1", "name": "Indraprastha"},
    {"date": "736.1.1", "name": "Dhillika"},
    {"date": "1206.1.1", "name": "Delhi"},
    {"date": "1648.1.1", "name": "Shahjahanabad"},
    {"date": "1803.9.16", "name": "Delhi"},
  ],
  ("mumbai", "India"): [
    {"date": "150.1.1", "name": "Heptanesia"},
    {"date": "810.1.1", "name": "Puri"},
    {"date": "1294.1.1", "name": "Mahikavati"},
    {"date": "1534.12.23", "name": "Bom Bahia"},
    {"date": "1661.6.23", "name": "Bombay"},
    {"date": "1995.11.4", "name": "Mumbai"},
  ],
  ("kolkata", "India"): [
    {"date": "1495.1.1", "name": "Kalikata"},
    {"date": "1690.8.24", "name": "Calcutta"},
    {"date": "2001.1.1", "name": "Kolkata"},
  ],
  ("chennai", "India"): [
    {"date": "100.1.1", "name": "Mylapore"},
    {"date": "150.1.1", "name": "Mylarpha"},
    {"date": "800.1.1", "name": "Mylapore"},
    {"date": "1639.8.22", "name": "Madras"},
    {"date": "1996.7.17", "name": "Chennai"},
  ],
  ("bengaluru", "India"): [
    {"date": "890.1.1", "name": "Bengaluru"},
    {"date": "1537.1.1", "name": "Bangalore"},
    {"date": "2014.11.1", "name": "Bengaluru"},
  ],
  ("hyderabad", "India"): [
    {"date": "1591.1.1", "name": "Bhagnagar"},
    {"date": "1592.1.1", "name": "Hyderabad"},
  ],
  ("ahmedabad", "India"): [
    {"date": "1050.1.1", "name": "Ashaval"},
    {"date": "1072.1.1", "name": "Karnavati"},
    {"date": "1411.2.26", "name": "Ahmedabad"},
  ],
  ("ahmadabad", "India"): [
    {"date": "1050.1.1", "name": "Ashaval"},
    {"date": "1072.1.1", "name": "Karnavati"},
    {"date": "1411.2.26", "name": "Ahmadabad"},
  ],
  ("pune", "India"): [
    {"date": "850.1.1", "name": "Punaka"},
    {"date": "1600.1.1", "name": "Poona"},
    {"date": "1978.1.1", "name": "Pune"},
  ],
  ("kanpur", "India"): [
    {"date": "1801.1.1", "name": "Cawnpore"},
    {"date": "1948.1.1", "name": "Kanpur"},
  ],
  ("agra", "India"): [
    {"date": "1504.1.1", "name": "Agra"},
    {"date": "1558.1.1", "name": "Akbarabad"},
    {"date": "1803.10.18", "name": "Agra"},
  ],
  ("patna", "India"): [
    {"date": "-490.1.1", "name": "Pataliputra"},
    {"date": "1541.1.1", "name": "Patna"},
    {"date": "1704.1.1", "name": "Azimabad"},
    {"date": "1765.1.1", "name": "Patna"},
  ],
  ("varanasi", "India"): [
    {"date": "-1000.1.1", "name": "Kashi"},
    {"date": "1700.1.1", "name": "Benares"},
    {"date": "1956.5.24", "name": "Varanasi"},
  ],
  ("prayagraj", "India"): [
    {"date": "-1000.1.1", "name": "Prayaga"},
    {"date": "1575.1.1", "name": "Ilahabad"},
    {"date": "1801.1.1", "name": "Allahabad"},
    {"date": "2018.10.16", "name": "Prayagraj"},
  ],
  ("vadodara", "India"): [
    {"date": "812.1.1", "name": "Vadapadraka"},
    {"date": "1610.1.1", "name": "Vadodara"},
    {"date": "1802.1.1", "name": "Baroda"},
    {"date": "1974.1.1", "name": "Vadodara"},
  ],
  ("bharuch", "India"): [
    {"date": "-300.1.1", "name": "Bhrigukaccha"},
    {"date": "50.1.1", "name": "Barygaza"},
    {"date": "1772.1.1", "name": "Broach"},
    {"date": "1960.5.1", "name": "Bharuch"},
  ],
  ("khambhat", "India"): [
    {"date": "600.1.1", "name": "Stambhatirtha"},
    {"date": "1500.1.1", "name": "Cambay"},
    {"date": "1960.5.1", "name": "Khambhat"},
  ],
  ("junagadh", "India"): [
    {"date": "-300.1.1", "name": "Girinagara"},
    {"date": "1472.1.1", "name": "Mustafabad"},
    {"date": "1748.1.1", "name": "Junagadh"},
  ],
  ("madurai", "India"): [
    {"date": "-300.1.1", "name": "Madurai"},
    {"date": "1750.1.1", "name": "Madura"},
    {"date": "1949.1.1", "name": "Madurai"},
  ],
  ("thanjavur", "India"): [
    {"date": "850.1.1", "name": "Thanjavur"},
    {"date": "1799.10.25", "name": "Tanjore"},
    {"date": "1960.1.1", "name": "Thanjavur"},
  ],
  ("tiruchirappalli", "India"): [
    {"date": "-300.1.1", "name": "Uraiyur"},
    {"date": "1565.1.1", "name": "Tiruchirappalli"},
    {"date": "1752.1.1", "name": "Trichinopoly"},
    {"date": "1947.8.15", "name": "Tiruchirappalli"},
  ],
  ("thoothukudi", "India"): [
    {"date": "1532.1.1", "name": "Tuticorin"},
    {"date": "1986.10.20", "name": "Thoothukudi"},
  ],
  ("tirunelveli", "India"): [
    {"date": "1801.1.1", "name": "Tinnevelly"},
    {"date": "1947.8.15", "name": "Tirunelveli"},
  ],
  ("nagapattinam", "India"): [
    {"date": "800.1.1", "name": "Nagapattinam"},
    {"date": "1658.1.1", "name": "Negapatam"},
    {"date": "1947.8.15", "name": "Nagapattinam"},
  ],
  ("kanchipuram", "India"): [
    {"date": "-200.1.1", "name": "Kanchi"},
    {"date": "1780.1.1", "name": "Conjeeveram"},
    {"date": "1947.8.15", "name": "Kanchipuram"},
  ],
  ("puducherry", "India"): [
    {"date": "100.1.1", "name": "Podouke"},
    {"date": "1674.1.1", "name": "Pondicherry"},
    {"date": "2006.10.1", "name": "Puducherry"},
  ],
  ("mysuru", "India"): [
    {"date": "1399.1.1", "name": "Mysuru"},
    {"date": "1799.5.4", "name": "Mysore"},
    {"date": "2014.11.1", "name": "Mysuru"},
  ],
  ("mysore", "India"): [
    {"date": "1399.1.1", "name": "Mysuru"},
    {"date": "1799.5.4", "name": "Mysore"},
  ],
  ("mangaluru", "India"): [
    {"date": "1000.1.1", "name": "Mangalapura"},
    {"date": "1799.1.1", "name": "Mangalore"},
    {"date": "2014.11.1", "name": "Mangaluru"},
  ],
  ("belagavi", "India"): [
    {"date": "1200.1.1", "name": "Venugrama"},
    {"date": "1818.1.1", "name": "Belgaum"},
    {"date": "2014.11.1", "name": "Belagavi"},
  ],
  ("belgaum", "India"): [
    {"date": "1200.1.1", "name": "Venugrama"},
    {"date": "1818.1.1", "name": "Belgaum"},
  ],
  ("vijayapura", "India"): [
    {"date": "1050.1.1", "name": "Vijayapura"},
    {"date": "1490.1.1", "name": "Bijapur"},
    {"date": "2014.11.1", "name": "Vijayapura"},
  ],
  ("kalaburagi", "India"): [
    {"date": "1347.1.1", "name": "Ahsanabad"},
    {"date": "1650.1.1", "name": "Gulbarga"},
    {"date": "2014.11.1", "name": "Kalaburagi"},
  ],
  ("gulbarga", "India"): [
    {"date": "1347.1.1", "name": "Ahsanabad"},
    {"date": "1650.1.1", "name": "Gulbarga"},
  ],
  ("hubballi", "India"): [
    {"date": "1700.1.1", "name": "Hubli"},
    {"date": "2014.11.1", "name": "Hubballi"},
  ],
  ("shivamogga", "India"): [
    {"date": "1800.1.1", "name": "Shimoga"},
    {"date": "2014.11.1", "name": "Shivamogga"},
  ],
  ("ballari", "India"): [
    {"date": "1800.1.1", "name": "Bellary"},
    {"date": "2014.11.1", "name": "Ballari"},
  ],
  ("tumakuru", "India"): [
    {"date": "1800.1.1", "name": "Tumkur"},
    {"date": "2014.11.1", "name": "Tumakuru"},
  ],
  ("kochi", "India"): [
    {"date": "1102.1.1", "name": "Kochi"},
    {"date": "1503.1.1", "name": "Cochin"},
    {"date": "1996.1.1", "name": "Kochi"},
  ],
  ("kozhikode", "India"): [
    {"date": "1100.1.1", "name": "Kozhikode"},
    {"date": "1498.5.20", "name": "Calicut"},
    {"date": "1995.11.1", "name": "Kozhikode"},
  ],
  ("thiruvananthapuram", "India"): [
    {"date": "1000.1.1", "name": "Thiruvananthapuram"},
    {"date": "1791.1.1", "name": "Trivandrum"},
    {"date": "1991.1.1", "name": "Thiruvananthapuram"},
  ],
  ("kollam", "India"): [
    {"date": "825.1.1", "name": "Kollam"},
    {"date": "1502.1.1", "name": "Quilon"},
    {"date": "1990.1.1", "name": "Kollam"},
  ],
  ("thrissur", "India"): [
    {"date": "1800.1.1", "name": "Trichur"},
    {"date": "1990.1.1", "name": "Thrissur"},
  ],
  ("kannur", "India"): [
    {"date": "1505.1.1", "name": "Cannanore"},
    {"date": "1990.1.1", "name": "Kannur"},
  ],
  ("alappuzha", "India"): [
    {"date": "1762.1.1", "name": "Alleppey"},
    {"date": "1990.1.1", "name": "Alappuzha"},
  ],
  ("palakkad", "India"): [
    {"date": "1790.1.1", "name": "Palghat"},
    {"date": "1990.1.1", "name": "Palakkad"},
  ],
  ("thalassery", "India"): [
    {"date": "1683.1.1", "name": "Tellicherry"},
    {"date": "1990.1.1", "name": "Thalassery"},
  ],
  ("visakhapatnam", "India"): [
    {"date": "1682.1.1", "name": "Vizagapatam"},
    {"date": "1947.8.15", "name": "Visakhapatnam"},
  ],
  ("vijayawada", "India"): [
    {"date": "600.1.1", "name": "Vijayavatika"},
    {"date": "1800.1.1", "name": "Bezwada"},
    {"date": "1947.8.15", "name": "Vijayawada"},
  ],
  ("machilipatnam", "India"): [
    {"date": "150.1.1", "name": "Maisolos"},
    {"date": "1611.1.1", "name": "Masulipatam"},
    {"date": "1949.1.1", "name": "Machilipatnam"},
  ],
  ("guwahati", "India"): [
    {"date": "-500.1.1", "name": "Pragjyotishpura"},
    {"date": "1826.2.24", "name": "Gauhati"},
    {"date": "1983.1.1", "name": "Guwahati"},
  ],
  ("ujjain", "India"): [
    {"date": "-600.1.1", "name": "Ujjayini"},
    {"date": "1562.1.1", "name": "Ujjain"},
  ],
  ("jabalpur", "India"): [
    {"date": "1817.1.1", "name": "Jubbulpore"},
    {"date": "1947.8.15", "name": "Jabalpur"},
  ],
  ("aurangabad", "India"): [
    {"date": "1610.1.1", "name": "Khadki"},
    {"date": "1626.1.1", "name": "Fatehnagar"},
    {"date": "1653.1.1", "name": "Aurangabad"},
  ],
  ("solapur", "India"): [
    {"date": "1818.1.1", "name": "Sholapur"},
    {"date": "1960.5.1", "name": "Solapur"},
  ],
  ("panaji", "India"): [
    {"date": "1759.1.1", "name": "Nova Goa"},
    {"date": "1843.3.22", "name": "Panjim"},
    {"date": "1961.12.19", "name": "Panaji"},
  ],
  ("jamshedpur", "India"): [
    {"date": "1907.1.1", "name": "Sakchi"},
    {"date": "1919.1.2", "name": "Jamshedpur"},
  ],
  ("murshidabad", "India"): [
    {"date": "1600.1.1", "name": "Makhsudabad"},
    {"date": "1704.1.1", "name": "Murshidabad"},
  ],
  ("chandannagar", "India"): [
    {"date": "1673.1.1", "name": "Chandernagore"},
    {"date": "1954.10.2", "name": "Chandannagar"},
  ],
  ("serampore", "India"): [
    {"date": "1755.1.1", "name": "Frederiknagore"},
    {"date": "1845.10.11", "name": "Serampore"},
  ],
  ("shimla", "India"): [
    {"date": "1819.1.1", "name": "Simla"},
    {"date": "1972.1.1", "name": "Shimla"},
  ],
  ("jalandhar", "India"): [
    {"date": "100.1.1", "name": "Jalandhara"},
    {"date": "1846.1.1", "name": "Jullundur"},
    {"date": "1983.1.1", "name": "Jalandhar"},
  ],
  ("amritsar", "India"): [
    {"date": "1577.1.1", "name": "Ramdaspur"},
    {"date": "1604.1.1", "name": "Amritsar"},
  ],
  ("srinagar", "India"): [
    {"date": "580.1.1", "name": "Pravarapura"},
    {"date": "1339.1.1", "name": "Srinagar"},
  ],
  ("ajmer", "India"): [
    {"date": "1113.1.1", "name": "Ajayameru"},
    {"date": "1558.1.1", "name": "Ajmer"},
  ],
  ("gwalior", "India"): [
    {"date": "525.1.1", "name": "Gopagiri"},
    {"date": "1398.1.1", "name": "Gwalior"},
  ],
  ("ayodhya", "India"): [
    {"date": "-600.1.1", "name": "Saketa"},
    {"date": "400.1.1", "name": "Ayodhya"},
  ],
  ("kannauj", "India"): [
    {"date": "-400.1.1", "name": "Kanyakubja"},
    {"date": "1200.1.1", "name": "Kannauj"},
  ],
  ("rajgir", "India"): [
    {"date": "-600.1.1", "name": "Rajagriha"},
    {"date": "1200.1.1", "name": "Rajgir"},
  ],
  ("bhubaneswar", "India"): [
    {"date": "600.1.1", "name": "Ekamra Kshetra"},
    {"date": "1948.4.13", "name": "Bhubaneswar"},
  ],
  ("jaipur", "India"): [
    {"date": "1727.11.18", "name": "Jaipur"},
  ],

  # --- PAKISTAN ---
  ("karachi", "Pakistan"): [
    {"date": "1729.1.1", "name": "Kolachi"},
    {"date": "1839.2.3", "name": "Kurrachee"},
    {"date": "1850.1.1", "name": "Karachi"},
  ],
  ("lahore", "Pakistan"): [
    {"date": "100.1.1", "name": "Lavapuri"},
    {"date": "1000.1.1", "name": "Lahore"},
  ],
  ("faisalabad", "Pakistan"): [
    {"date": "1896.1.1", "name": "Lyallpur"},
    {"date": "1977.9.1", "name": "Faisalabad"},
  ],
  ("sahiwal", "Pakistan"): [
    {"date": "1865.1.1", "name": "Montgomery"},
    {"date": "1966.11.1", "name": "Sahiwal"},
  ],
  ("multan", "Pakistan"): [
    {"date": "-325.1.1", "name": "Malli"},
    {"date": "400.1.1", "name": "Mulasthana"},
    {"date": "712.1.1", "name": "Multan"},
  ],
  ("peshawar", "Pakistan"): [
    {"date": "-400.1.1", "name": "Pushkalavati"},
    {"date": "100.1.1", "name": "Purushapura"},
    {"date": "1000.1.1", "name": "Peshawar"},
  ],
  ("taxila", "Pakistan"): [
    {"date": "-600.1.1", "name": "Takshashila"},
    {"date": "1000.1.1", "name": "Taxila"},
  ],
  ("sialkot", "Pakistan"): [
    {"date": "-326.1.1", "name": "Sagala"},
    {"date": "1185.1.1", "name": "Sialkot"},
  ],
  ("quetta", "Pakistan"): [
    {"date": "1500.1.1", "name": "Shal"},
    {"date": "1876.1.1", "name": "Quetta"},
  ],
  ("hyderabad", "Pakistan"): [
    {"date": "711.1.1", "name": "Nerun Kot"},
    {"date": "1768.1.1", "name": "Hyderabad"},
  ],
  ("thatta", "Pakistan"): [
    {"date": "1351.1.1", "name": "Nagar Tatta"},
    {"date": "1843.1.1", "name": "Thatta"},
  ],

  # --- BANGLADESH ---
  ("dhaka", "Bangladesh"): [
    {"date": "1608.1.1", "name": "Jahangir Nagar"},
    {"date": "1765.1.1", "name": "Dacca"},
    {"date": "1982.10.5", "name": "Dhaka"},
  ],
  ("chittagong", "Bangladesh"): [
    {"date": "1346.1.1", "name": "Chatigaon"},
    {"date": "1537.1.1", "name": "Porto Grande"},
    {"date": "1666.1.27", "name": "Islamabad"},
    {"date": "1760.1.1", "name": "Chittagong"},
  ],
  ("chattogram", "Bangladesh"): [
    {"date": "1346.1.1", "name": "Chatigaon"},
    {"date": "1537.1.1", "name": "Porto Grande"},
    {"date": "1666.1.27", "name": "Islamabad"},
    {"date": "1760.1.1", "name": "Chittagong"},
    {"date": "2018.4.2", "name": "Chattogram"},
  ],
  ("bogra", "Bangladesh"): [
    {"date": "-300.1.1", "name": "Pundranagara"},
    {"date": "1821.1.1", "name": "Bogra"},
  ],
  ("mymensingh", "Bangladesh"): [
    {"date": "1787.5.1", "name": "Nasirabad"},
    {"date": "1905.1.1", "name": "Mymensingh"},
  ],

  # --- SRI LANKA ---
  ("colombo", "Sri Lanka"): [
    {"date": "700.1.1", "name": "Kolamba"},
    {"date": "1505.11.15", "name": "Colombo"},
  ],
  ("kandy", "Sri Lanka"): [
    {"date": "1357.1.1", "name": "Senkadagalapura"},
    {"date": "1592.1.1", "name": "Mahanuwara"},
    {"date": "1815.3.2", "name": "Kandy"},
  ],
  ("jaffna", "Sri Lanka"): [
    {"date": "1215.1.1", "name": "Nallur"},
    {"date": "1619.1.1", "name": "Jafanapatao"},
    {"date": "1658.6.22", "name": "Jaffna"},
  ],
  ("galle", "Sri Lanka"): [
    {"date": "1587.1.1", "name": "Ponto de Galle"},
    {"date": "1640.3.13", "name": "Galle"},
  ],
  ("sri jayawardenepura kotte", "Sri Lanka"): [
    {"date": "1370.1.1", "name": "Kotte"},
    {"date": "1982.4.29", "name": "Sri Jayawardenepura Kotte"},
  ],
  ("trincomalee", "Sri Lanka"): [
    {"date": "400.1.1", "name": "Gokanna"},
    {"date": "1624.1.1", "name": "Trincomalee"},
  ],

  # --- NEPAL, BHUTAN, MALDIVES ---
  ("kathmandu", "Nepal"): [
    {"date": "-300.1.1", "name": "Kantipur"},
    {"date": "1768.9.25", "name": "Kathmandu"},
  ],
  ("lalitpur", "Nepal"): [
    {"date": "299.1.1", "name": "Yala"},
    {"date": "1482.1.1", "name": "Patan"},
    {"date": "1951.1.1", "name": "Lalitpur"},
  ],
  ("bhaktapur", "Nepal"): [
    {"date": "800.1.1", "name": "Khwopa"},
    {"date": "1482.1.1", "name": "Bhadgaon"},
    {"date": "1951.1.1", "name": "Bhaktapur"},
  ],
  ("janakpur", "Nepal"): [
    {"date": "-600.1.1", "name": "Mithila"},
    {"date": "1800.1.1", "name": "Janakpur"},
  ],
  ("thimphu", "Bhutan"): [
    {"date": "1627.1.1", "name": "Tashichho Dzong"},
    {"date": "1955.1.1", "name": "Thimphu"},
  ],
  ("male", "Maldives"): [
    {"date": "1153.1.1", "name": "Mahal"},
    {"date": "1887.12.16", "name": "Male"},
    {"date": "1965.7.26", "name": "Malé"},
  ],
  ("malé", "Maldives"): [
    {"date": "1153.1.1", "name": "Mahal"},
    {"date": "1887.12.16", "name": "Male"},
    {"date": "1965.7.26", "name": "Malé"},
  ],

  # --- ANCIENT & ARCHAEOLOGICAL KEY SITES ---
  ("mohenjo-daro", "Pakistan"): [{"date": "-2600.1.1", "name": "Mohenjo-daro"}],
  ("harappa", "Pakistan"): [{"date": "-3300.1.1", "name": "Harappa"}],
  ("ganweriwala", "Pakistan"): [{"date": "-2600.1.1", "name": "Ganweriwala"}],
  ("mehrgarh", "Pakistan"): [{"date": "-7000.1.1", "name": "Mehrgarh"}],
  ("dholavira", "India"): [{"date": "-2650.1.1", "name": "Kotada Timba"}, {"date": "1967.1.1", "name": "Dholavira"}],
  ("rakhigarhi", "India"): [{"date": "-3000.1.1", "name": "Rakhigarhi"}],
  ("lothal", "India"): [{"date": "-2400.1.1", "name": "Lothal"}],
  ("kalibangan", "India"): [{"date": "-2900.1.1", "name": "Kalibangan"}],
  ("hampi", "India"): [{"date": "1336.1.1", "name": "Vijayanagara"}, {"date": "1565.1.23", "name": "Hampi"}],
  ("fatehpur sikri", "India"): [{"date": "1571.1.1", "name": "Fatehpur Sikri"}],
  ("nalanda", "India"): [{"date": "427.1.1", "name": "Nalanda"}],
  ("sanchi", "India"): [{"date": "-250.1.1", "name": "Kakanaya"}, {"date": "1818.1.1", "name": "Sanchi"}],
  ("mathura", "India"): [{"date": "-600.1.1", "name": "Madhura"}, {"date": "100.1.1", "name": "Mathura"}],
  ("gaya", "India"): [{"date": "-500.1.1", "name": "Gaya"}],
  ("cuttack", "India"): [{"date": "989.1.1", "name": "Varanasi Kataka"}, {"date": "1803.10.14", "name": "Cuttack"}],
  ("puri", "India"): [{"date": "1000.1.1", "name": "Purushottama Kshetra"}, {"date": "1803.1.1", "name": "Puri"}],
  ("rajahmundry", "India"): [{"date": "1022.1.1", "name": "Rajamahendravaram"}, {"date": "1766.1.1", "name": "Rajahmundry"}],
  ("indore", "India"): [{"date": "1715.1.1", "name": "Indrapur"}, {"date": "1741.1.1", "name": "Indore"}],
  ("bhopal", "India"): [{"date": "1010.1.1", "name": "Bhojpal"}, {"date": "1724.1.1", "name": "Bhopal"}],
  ("jodhpur", "India"): [{"date": "1459.5.12", "name": "Jodhpur"}],
  ("udaipur", "India"): [{"date": "1559.1.1", "name": "Udaipur"}],
  ("bikaner", "India"): [{"date": "1488.1.1", "name": "Bikaner"}],
  ("nashik", "India"): [{"date": "-200.1.1", "name": "Nasika"}, {"date": "1680.1.1", "name": "Gulshanabad"}, {"date": "1818.1.1", "name": "Nashik"}],
  ("kolhapur", "India"): [{"date": "200.1.1", "name": "Karavira"}, {"date": "1710.1.1", "name": "Kolhapur"}],
  ("thane", "India"): [{"date": "800.1.1", "name": "Sthanaka"}, {"date": "1534.1.1", "name": "Tana"}, {"date": "1774.1.1", "name": "Thana"}, {"date": "1960.5.1", "name": "Thane"}],
  ("port blair", "India"): [{"date": "1789.1.1", "name": "Port Cornwallis"}, {"date": "1858.3.10", "name": "Port Blair"}],
  ("imphal", "India"): [{"date": "33.1.1", "name": "Kangla"}, {"date": "1891.1.1", "name": "Imphal"}],
  ("rawalpindi", "Pakistan"): [{"date": "1493.1.1", "name": "Rawalpindi"}],
  ("bahawalpur", "Pakistan"): [{"date": "1748.1.1", "name": "Bahawalpur"}],
  ("gwadar", "Pakistan"): [{"date": "1783.1.1", "name": "Gwadar"}],
  ("anuradhapura", "Sri Lanka"): [{"date": "-437.1.1", "name": "Anuradhapura"}],
  ("polonnaruwa", "Sri Lanka"): [{"date": "993.1.1", "name": "Jananathamangalam"}, {"date": "1070.1.1", "name": "Pulastipura"}, {"date": "1815.1.1", "name": "Polonnaruwa"}],
  ("batticaloa", "Sri Lanka"): [{"date": "1628.1.1", "name": "Matakalappu"}, {"date": "1638.5.18", "name": "Batticaloa"}],
  ("negombo", "Sri Lanka"): [{"date": "1505.1.1", "name": "Migamuwa"}, {"date": "1644.1.1", "name": "Negombo"}],
  ("pokhara", "Nepal"): [{"date": "1752.1.1", "name": "Pokhara"}],
}


def strip_parens(arg0_s):
  s = str(arg0_s or "").strip()
  # Unwrap names completely enclosed in parentheses, e.g. "(Daun 8)" -> "Daun 8"
  if s.startswith("(") and s.endswith(")") and s.count("(") == 1:
    s = s[1:-1].strip()
  s = re.sub(r"\s*\([^)]*\)", "", s)
  s = re.sub(r"\s*（[^）]*）", "", s)
  # Strip stray emoji / pictographs / variation selectors
  s = re.sub(r"[\u2600-\u27BF\uFE00-\uFE0F\U00010000-\U0010FFFF]", "", s)
  s = re.sub(r"\s+", " ", s).strip()
  return s


def is_valid_indus_script(arg0_s):
  """Allows ONLY Latin and authentic South Asian scripts (Devanagari, Bengali, Gurmukhi, Gujarati,
  Oriya, Tamil, Telugu, Kannada, Malayalam, Sinhala, Arabic/Urdu, Thaana, Tibetan) — zero Cyrillic/CJK."""
  if not arg0_s:
    return False
  for ch in arg0_s:
    oc = ord(ch)
    if oc < 128:
      continue
    if 0x00C0 <= oc <= 0x024F or 0x1E00 <= oc <= 0x1EFF:  # Latin Extended
      continue
    if 0x0600 <= oc <= 0x06FF or 0x0750 <= oc <= 0x07BF:  # Arabic/Urdu/Sindhi/Thaana
      continue
    if 0x0900 <= oc <= 0x0DFF:  # Indic scripts + Sinhala
      continue
    if 0x0F00 <= oc <= 0x0FFF:  # Tibetan/Dzongkha
      continue
    if ch in "’‘–—\u200c\u200d":
      continue
    return False
  return True


def is_clean_name(arg0_s):
  s = strip_parens(arg0_s)
  if not s or len(s) > 140:
    return False
  if s in ("0", "Unknown", "Settlement"):
    return False
  if re.match(r"^[?\s\-_.,0-9]+$", s):
    return False
  if "?" in s or "`" in s or "\ufffd" in s or "\u00ef\u00bf\u00bd" in s:
    return False
  return is_valid_indus_script(s)


def norm_key(arg0_s):
  s = strip_parens(arg0_s).lower()
  s = s.replace("é", "e").replace("ā", "a").replace("ī", "i").replace("ū", "u")
  return re.sub(r"\s+", " ", s).strip()


def load_geonames_alternates():
  """Loads clean alternate names from the 7 INDUS GeoNames zips indexed by spatial 0.1-deg bucket."""
  cc_to_c = {
    "IN": "India", "PK": "Pakistan", "BD": "Bangladesh", "LK": "Sri Lanka",
    "NP": "Nepal", "BT": "Bhutan", "MV": "Maldives"
  }
  grid = defaultdict(list)
  for cc, cname in cc_to_c.items():
    zp = os.path.join(CENSUS_DIR, f"geonames_{cc}.zip")
    if not os.path.isfile(zp):
      continue
    with zipfile.ZipFile(zp) as zf:
      raw = zf.read(f"{cc}.txt").decode("utf-8", errors="replace")
    for line in raw.splitlines():
      p = line.split("\t")
      if len(p) < 15 or p[6] != "P":
        continue
      try:
        lat, lon = float(p[4]), float(p[5])
      except ValueError:
        continue
      nm = strip_parens(p[1])
      asc = strip_parens(p[2])
      alts = [strip_parens(a) for a in (p[3] or "").split(",") if is_clean_name(a)]
      if nm and is_clean_name(nm) and nm not in alts:
        alts.insert(0, nm)
      if asc and is_clean_name(asc) and asc not in alts:
        alts.insert(0, asc)
      if not alts:
        continue
      bkey = (cname, round(lat * 10), round(lon * 10))
      grid[bkey].append((lat, lon, norm_key(asc or nm), alts[:12]))
  return grid


def haversine_km(lat1, lon1, lat2, lon2):
  dlat = math.radians(lat2 - lat1)
  dlon = math.radians(lon2 - lon1)
  a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
  return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def lookup_geonames_aliases(arg0_grid, arg1_country, arg2_lat, arg3_lon, arg4_name):
  nk = norm_key(arg4_name)
  bx, by = round(arg2_lat * 10), round(arg3_lon * 10)
  best_alts = []
  best_dist = 4.0
  for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
      for lat, lon, g_nk, alts in arg0_grid.get((arg1_country, bx + dx, by + dy), []):
        d = haversine_km(arg2_lat, arg3_lon, lat, lon)
        if d <= 3.0 and (g_nk == nk or d <= 1.2):
          if d < best_dist:
            best_dist = d
            best_alts = alts
  return best_alts


def main():
  print("[INDUS Toponymy] Loading GeoNames alternate names across 7 South Asian states...", flush=True)
  gn_grid = load_geonames_alternates()
  print(f"  Loaded {len(gn_grid):,} spatial alternate-name buckets.", flush=True)

  batch_files = sorted(
    f for f in os.listdir(BATCH_DIR)
    if re.match(r"^batch_\d+\.json$", f, re.IGNORECASE)
  )
  print(f"[INDUS Toponymy] Resolving {len(batch_files)} extracted batch file(s) in {BATCH_DIR}...", flush=True)

  total_resolved = 0
  curated_hits = 0

  for bf in batch_files:
    in_path = os.path.join(BATCH_DIR, bf)
    raw = json.load(open(in_path, "r", encoding="utf-8"))
    items = raw.get("settlements", [])
    out_items = []
    for it in items:
      cname = str(it.get("country") or "").strip()
      coords = it.get("coords_lat_lng") or [0.0, 0.0]
      lat, lon = float(coords[0]), float(coords[1])
      raw_name = strip_parens(it.get("name") or "")
      if not is_clean_name(raw_name):
        continue
      nk = norm_key(raw_name)
      earliest = int(it.get("earliest_year") if it.get("earliest_year") is not None else 1850)
      latest = int(it.get("latest_year") if it.get("latest_year") is not None else 2025)

      curated = CURATED_HISTORICAL_NAMES.get((nk, cname))
      if curated:
        hist = [dict(h) for h in curated]
        # Ensure terminal name matches canonical_name cleanly
        if latest >= 1950 and norm_key(hist[-1]["name"]) != nk:
          hist.append({"date": f"{max(1950, int(hist[-1]['date'].split('.')[0]) + 1)}.1.1", "name": raw_name})
        curated_hits += 1
      else:
        existing_hist = it.get("existing_historical_names") or []
        hist = []
        for eh in existing_hist:
          if isinstance(eh, dict) and re.match(r"^-?\d+\.\d+\.\d+$", str(eh.get("date") or "").strip()) and is_clean_name(eh.get("name")):
            hist.append({"date": str(eh["date"]).strip(), "name": strip_parens(eh["name"])})
        if not hist:
          init_yr = min(earliest, 1850) if earliest > 1850 and latest >= 1950 else earliest
          hist.append({"date": f"{init_yr}.1.1", "name": raw_name})
        elif latest >= 1950 and norm_key(hist[-1]["name"]) != nk:
          last_yr = int(hist[-1]["date"].split(".")[0])
          hist.append({"date": f"{max(last_yr + 1, 1950)}.1.1", "name": raw_name})

      # Gather clean alternate names (known_aliases + GeoNames authentic native/historical aliases)
      other_set = []
      seen_o = {raw_name.lower()}
      for a in list(it.get("known_aliases") or []) + lookup_geonames_aliases(gn_grid, cname, lat, lon, raw_name):
        ca = strip_parens(a)
        if is_clean_name(ca) and ca.lower() not in seen_o:
          seen_o.add(ca.lower())
          other_set.append(ca)

      rec = dict(it)
      rec["canonical_name"] = raw_name
      rec["historical_names"] = hist
      rec["other_names"] = other_set[:12]
      out_items.append(rec)
      total_resolved += 1

    out_path = os.path.join(BATCH_DIR, "resolved_" + bf)
    with open(out_path, "w", encoding="utf-8") as fh:
      json.dump({
        "batch_index": raw.get("batch_index", 1),
        "project": "INDUS",
        "count": len(out_items),
        "settlements": out_items
      }, fh, ensure_ascii=False, indent=2)

  # Clean up any stale resolved_batch_9999.json so merge_city_metadata only merges missing/empty batches
  out_9999 = os.path.join(BATCH_DIR, "resolved_batch_9999.json")
  if os.path.isfile(out_9999):
    os.remove(out_9999)

  print(f"[INDUS Toponymy] Done: resolved {total_resolved:,} batch settlements ({curated_hits} curated hits).", flush=True)


def apply_curated_replacements():
  """Authoritatively replaces inaccurate single-stub historical_names on existing South Asian capitals
  in stadester_2.0/city_metadata.json (preserving richer existing chains like Mumbai/Delhi/Kolkata/Chennai)."""
  import sys
  meta_arr = json.load(open(DATAVIEW_META, "r", encoding="utf-8"))
  gn_grid = load_geonames_alternates()
  updated = 0

  for idx, entry in enumerate(meta_arr):
    if not isinstance(entry, dict) or not isinstance(entry.get("coords"), list) or len(entry["coords"]) < 2:
      continue
    lng, lat = float(entry["coords"][0]), float(entry["coords"][1])
    if not (60.0 <= lng <= 98.5 and -2.0 <= lat <= 38.5):
      continue
    canon = strip_parens(entry.get("name"))
    nk = norm_key(canon)

    # Strip any foreign-script spam (Cyrillic/CJK etc.) from existing INDUS other_names
    if isinstance(entry.get("other_names"), list):
      cleaned_o = [o for o in entry["other_names"] if is_clean_name(o)]
      if len(cleaned_o) != len(entry["other_names"]):
        entry["other_names"] = cleaned_o

    # Match (nk, country) unambiguously across South Asia
    matched_curated = None
    matched_country = None
    for (ck, cname), chist in CURATED_HISTORICAL_NAMES.items():
      if ck != nk:
        continue
      if nk == "hyderabad":
        if cname == "India" and lat < 21.0:
          matched_curated, matched_country = chist, cname
          break
        if cname == "Pakistan" and lat > 23.0:
          matched_curated, matched_country = chist, cname
          break
      else:
        matched_curated, matched_country = chist, cname
        break

    if not matched_curated:
      continue

    existing_hist = entry.get("historical_names") or []
    # Only replace when curated chain is strictly richer OR corrects an anachronistic stub
    if len(existing_hist) > len(matched_curated):
      continue
    if len(existing_hist) == len(matched_curated) and len(existing_hist) >= 3:
      continue

    new_hist = [dict(h) for h in matched_curated]
    if norm_key(new_hist[-1]["name"]) != nk:
      new_hist[-1]["name"] = canon
    entry["historical_names"] = new_hist

    # Merge clean GeoNames / historical aliases into other_names
    other = list(entry.get("other_names") or [])
    seen = {canon.lower()} | {str(o).lower() for o in other}
    for h in new_hist:
      if h["name"].lower() not in seen and is_clean_name(h["name"]):
        seen.add(h["name"].lower())
        other.append(h["name"])
    for a in lookup_geonames_aliases(gn_grid, matched_country, lat, lng, canon)[:10]:
      if a.lower() not in seen and is_clean_name(a):
        seen.add(a.lower())
        other.append(a)
    if other:
      entry["other_names"] = other[:16]
    updated += 1

  with open(DATAVIEW_META, "w", encoding="utf-8") as fh:
    json.dump(meta_arr, fh, ensure_ascii=False, indent=2)
  print(f"[INDUS Toponymy] Authoritatively updated {updated} curated South Asian city entries in {DATAVIEW_META}.", flush=True)


if __name__ == "__main__":
  import sys
  if "--apply-curated" in sys.argv:
    apply_curated_replacements()
  else:
    main()
