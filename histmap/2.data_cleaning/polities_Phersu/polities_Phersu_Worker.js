global.polities_Phersu_Worker = class extends Blacktraffic.Worker {
	static bf = `F:/scrapes/phersu/`;
	static geojson_folder = path.join(this.bf, "geojson");
	static years_with_changes = JSON.parse('[-3499,-3249,-3149,-3099,-2999,-2899,-2749,-2699,-2689,-2659,-2649,-2599,-2588,-2549,-2499,-2459,-2449,-2415,-2399,-2379,-2357,-2349,-2339,-2333,-2331,-2299,-2289,-2278,-2269,-2229,-2217,-2215,-2199,-2198,-2182,-2169,-2153,-2123,-2118,-2111,-2069,-2049,-2046,-2024,-2003,-1999,-1939,-1931,-1919,-1899,-1893,-1880,-1875,-1819,-1817,-1814,-1809,-1808,-1807,-1806,-1801,-1799,-1794,-1791,-1780,-1779,-1776,-1775,-1774,-1769,-1764,-1763,-1762,-1761,-1760,-1759,-1753,-1751,-1740,-1735,-1727,-1726,-1720,-1704,-1699,-1693,-1680,-1659,-1650,-1649,-1647,-1642,-1621,-1599,-1595,-1594,-1593,-1589,-1569,-1559,-1549,-1529,-1526,-1523,-1516,-1504,-1503,-1499,-1492,-1456,-1449,-1446,-1428,-1424,-1419,-1415,-1399,-1391,-1369,-1359,-1351,-1349,-1329,-1321,-1319,-1318,-1311,-1299,-1294,-1289,-1287,-1286,-1279,-1274,-1273,-1271,-1269,-1268,-1262,-1259,-1257,-1243,-1234,-1229,-1226,-1224,-1214,-1212,-1206,-1199,-1196,-1194,-1180,-1179,-1177,-1174,-1165,-1154,-1149,-1136,-1119,-1111,-1110,-1108,-1103,-1099,-1076,-1075,-1069,-1068,-1055,-1045,-1044,-1042,-1041,-1040,-1039,-1038,-1029,-1019,-1005,-999,-979,-956,-949,-934,-933,-929,-921,-910,-899,-897,-894,-890,-889,-885,-883,-882,-877,-876,-875,-869,-862,-859,-857,-855,-854,-852,-849,-848,-841,-840,-836,-833,-824,-823,-814,-813,-807,-805,-804,-800,-799,-795,-787,-785,-782,-781,-780,-770,-769,-768,-767,-766,-762,-760,-755,-753,-752,-750,-749,-745,-742,-739,-737,-736,-735,-734,-733,-732,-731,-730,-729,-728,-727,-726,-723,-721,-720,-719,-717,-716,-714,-713,-712,-711,-710,-708,-707,-705,-703,-702,-700,-699,-689,-687,-686,-684,-683,-680,-679,-678,-677,-676,-675,-674,-673,-672,-670,-669,-668,-667,-663,-662,-660,-659,-658,-657,-656,-654,-653,-652,-650,-649,-647,-645,-643,-640,-639,-634,-632,-631,-630,-629,-626,-625,-624,-622,-621,-619,-618,-616,-615,-614,-613,-611,-610,-609,-608,-604,-603,-601,-600,-599,-597,-596,-591,-590,-587,-586,-585,-584,-580,-579,-574,-571,-570,-569,-566,-565,-562,-561,-560,-559,-555,-551,-550,-549,-548,-547,-546,-545,-544,-543,-542,-540,-539,-538,-537,-534,-530,-529,-527,-524,-523,-521,-520,-519,-517,-515,-513,-512,-511,-510,-509,-508,-507,-506,-505,-504,-503,-500,-499,-498,-497,-496,-495,-494,-492,-491,-490,-489,-488,-486,-485,-484,-482,-480,-479,-478,-477,-475,-474,-473,-472,-469,-468,-467,-465,-464,-462,-460,-459,-457,-456,-455,-454,-453,-452,-450,-449,-448,-447,-446,-445,-444,-443,-442,-439,-438,-437,-436,-434,-433,-432,-431,-430,-429,-428,-427,-426,-425,-424,-423,-422,-421,-420,-417,-415,-414,-413,-412,-411,-410,-409,-408,-407,-406,-405,-404,-403,-402,-401,-400,-399,-398,-397,-395,-394,-393,-392,-391,-390,-389,-388,-387,-386,-385,-384,-382,-380,-379,-378,-377,-376,-375,-374,-373,-372,-371,-370,-369,-368,-367,-366,-364,-363,-362,-361,-359,-358,-357,-356,-355,-354,-353,-352,-351,-350,-349,-348,-347,-346,-345,-344,-343,-342,-341,-340,-339,-338,-337,-336,-335,-334,-333,-332,-331,-330,-329,-328,-327,-326,-325,-322,-321,-319,-318,-317,-316,-315,-314,-313,-312,-311,-310,-309,-308,-307,-306,-305,-304,-303,-302,-301,-300,-299,-298,-297,-296,-295,-294,-293,-292,-291,-289,-288,-287,-286,-285,-284,-282,-281,-280,-279,-278,-276,-275,-274,-273,-272,-271,-270,-269,-268,-267,-266,-265,-264,-263,-262,-260,-259,-258,-257,-255,-254,-253,-251,-250,-249,-248,-246,-245,-244,-243,-242,-241,-240,-238,-237,-236,-235,-234,-232,-231,-230,-229,-228,-227,-226,-225,-224,-223,-222,-221,-220,-219,-218,-217,-216,-215,-214,-213,-212,-211,-210,-209,-208,-207,-206,-205,-204,-203,-202,-201,-200,-199,-197,-196,-195,-194,-193,-192,-191,-190,-189,-188,-187,-186,-184,-182,-181,-180,-179,-178,-177,-175,-174,-170,-169,-168,-167,-166,-163,-162,-161,-160,-159,-154,-153,-149,-148,-147,-146,-145,-144,-140,-139,-138,-137,-136,-134,-132,-131,-129,-128,-127,-126,-125,-124,-123,-122,-120,-119,-118,-117,-115,-113,-112,-111,-110,-109,-108,-107,-106,-105,-102,-100,-99,-95,-94,-92,-91,-90,-89,-88,-87,-86,-84,-83,-82,-81,-80,-79,-77,-76,-74,-73,-72,-71,-70,-69,-68,-67,-66,-65,-64,-63,-62,-61,-60,-59,-57,-56,-55,-54,-53,-52,-51,-50,-49,-48,-47,-46,-45,-43,-42,-40,-39,-38,-36,-35,-32,-31,-29,-28,-27,-25,-24,-23,-21,-19,-18,-17,-15,-14,-13,-11,-10,-8,-7,-3,1,2,7,9,10,11,12,13,14,18,20,21,23,26,29,31,35,36,37,38,39,40,41,42,43,44,45,47,48,49,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,69,70,72,73,74,75,76,77,79,80,81,82,83,84,85,86,87,89,90,92,93,94,101,102,103,105,106,111,112,115,116,117,118,119,120,123,126,128,131,145,151,156,161,162,163,164,165,166,167,168,169,170,173,174,176,179,180,181,186,191,193,194,197,198,200,201,204,205,209,211,212,214,215,217,220,221,222,224,226,228,231,233,235,237,238,239,240,241,243,244,245,246,249,250,251,252,253,255,257,260,261,263,264,265,266,268,270,271,272,273,274,276,280,281,284,285,286,287,294,297,298,299,300,301,303,305,306,307,308,309,311,312,313,314,315,317,320,321,325,329,331,332,333,335,336,337,338,339,341,342,346,347,348,351,352,353,357,358,359,360,361,363,364,365,367,368,370,371,372,374,375,376,377,379,380,382,384,385,386,387,388,389,392,394,395,396,397,398,399,401,402,403,404,406,407,408,409,410,411,412,413,414,415,416,417,418,419,420,421,422,423,424,426,427,429,430,431,432,433,434,436,437,439,440,441,442,443,444,446,447,448,449,451,452,453,455,456,457,458,460,461,463,464,465,467,468,469,470,471,474,475,476,477,478,479,480,481,485,486,487,488,489,490,491,492,493,495,496,497,501,502,503,505,506,507,508,509,510,511,513,519,520,523,524,525,526,527,528,529,530,531,532,533,534,535,536,537,538,539,540,541,542,543,544,547,548,549,550,551,552,553,554,555,556,557,558,560,561,563,566,568,569,570,571,572,573,574,575,576,577,578,579,580,581,582,583,584,585,586,587,588,589,590,591,593,594,595,596,597,598,599,600,601,602,603,604,605,606,607,609,610,611,613,614,615,616,617,618,619,620,621,622,623,624,625,626,627,628,629,630,631,632,633,634,635,636,637,638,639,640,641,642,643,644,645,646,647,648,649,650,651,652,653,654,655,656,657,658,659,660,661,662,663,664,665,666,668,669,670,671,672,673,674,675,676,677,678,679,680,681,682,683,684,685,686,687,689,690,691,692,693,695,696,698,699,700,701,702,703,704,705,706,708,709,710,711,712,713,714,715,716,717,718,719,720,721,722,723,724,725,726,727,728,729,730,731,732,733,734,735,736,737,738,739,740,741,742,743,744,745,746,747,748,749,750,751,752,753,754,755,756,757,758,759,760,761,762,763,764,765,766,767,768,769,770,771,772,773,774,775,776,777,778,779,782,783,784,786,787,788,789,791,792,793,794,795,796,797,799,800,801,802,803,804,805,806,807,809,810,811,812,813,814,815,816,818,819,820,821,822,823,824,826,827,828,829,830,831,832,834,837,838,839,840,841,842,843,844,846,847,848,849,850,851,852,853,854,855,856,857,858,859,860,861,862,863,864,865,866,867,868,869,870,871,872,873,874,875,876,877,878,879,880,881,882,883,884,885,886,887,888,889,890,891,892,893,894,895,896,897,898,899,900,901,902,903,904,905,906,907,908,909,910,911,912,913,914,915,916,917,918,919,920,921,922,923,924,925,926,927,928,929,930,931,932,933,934,935,936,937,938,939,940,941,942,943,944,945,946,947,948,949,950,951,952,953,954,955,956,958,959,960,961,962,963,964,965,966,968,969,970,971,972,973,974,975,976,977,978,979,980,981,982,983,984,985,986,987,988,989,990,991,992,993,994,995,996,997,998,999,1000,1001,1002,1003,1004,1005,1006,1007,1008,1009,1010,1011,1012,1013,1014,1015,1016,1017,1018,1019,1020,1021,1022,1023,1024,1025,1026,1027,1028,1029,1030,1031,1032,1033,1034,1035,1036,1037,1038,1039,1040,1041,1042,1043,1044,1045,1046,1047,1048,1049,1050,1051,1052,1053,1054,1055,1056,1057,1058,1059,1060,1061,1062,1063,1064,1065,1066,1067,1068,1069,1070,1071,1072,1073,1074,1075,1076,1077,1078,1079,1080,1081,1082,1083,1084,1085,1086,1087,1088,1089,1090,1091,1092,1093,1094,1095,1096,1097,1098,1099,1100,1101,1102,1103,1104,1105,1106,1107,1108,1109,1110,1111,1112,1113,1114,1115,1116,1117,1118,1119,1120,1121,1122,1123,1124,1125,1126,1127,1128,1129,1130,1131,1132,1133,1134,1135,1136,1137,1138,1139,1140,1141,1142,1143,1144,1145,1146,1147,1148,1149,1150,1151,1152,1153,1154,1155,1156,1157,1158,1159,1160,1161,1162,1163,1164,1165,1166,1167,1168,1169,1170,1171,1172,1173,1174,1175,1176,1177,1178,1179,1180,1181,1182,1183,1184,1185,1186,1187,1188,1189,1190,1191,1192,1193,1194,1195,1196,1197,1198,1199,1200,1201,1202,1203,1204,1205,1206,1207,1208,1209,1210,1211,1212,1213,1214,1215,1216,1217,1218,1219,1220,1221,1222,1223,1224,1225,1226,1227,1228,1229,1230,1231,1232,1233,1234,1235,1236,1237,1238,1239,1240,1241,1242,1243,1244,1245,1246,1247,1248,1249,1250,1251,1252,1253,1254,1255,1256,1257,1258,1259,1260,1261,1262,1263,1264,1265,1266,1267,1268,1269,1270,1271,1272,1273,1274,1275,1276,1277,1278,1279,1280,1281,1282,1283,1284,1285,1286,1287,1288,1289,1290,1291,1292,1293,1294,1295,1296,1297,1298,1299,1300,1301,1302,1303,1304,1305,1306,1307,1308,1309,1310,1311,1312,1313,1314,1315,1316,1317,1318,1319,1320,1321,1322,1323,1324,1325,1326,1327,1328,1329,1330,1331,1332,1333,1334,1335,1336,1337,1338,1339,1340,1341,1342,1343,1344,1345,1346,1347,1348,1349,1350,1351,1352,1353,1354,1355,1356,1357,1358,1359,1360,1361,1362,1363,1364,1365,1366,1367,1368,1369,1370,1371,1372,1373,1374,1375,1376,1377,1378,1379,1380,1381,1382,1383,1384,1385,1386,1387,1388,1389,1390,1391,1392,1393,1394,1395,1396,1397,1398,1399,1400,1401,1402,1403,1404,1405,1406,1407,1408,1409,1410,1411,1412,1413,1414,1415,1416,1417,1418,1419,1420,1421,1422,1423,1424,1425,1426,1427,1428,1429,1430,1431,1432,1433,1434,1435,1436,1437,1438,1439,1440,1441,1442,1443,1444,1445,1446,1447,1448,1449,1450,1451,1452,1453,1454,1455,1456,1457,1458,1459,1460,1461,1462,1463,1464,1465,1466,1467,1468,1469,1470,1471,1472,1473,1474,1475,1476,1477,1478,1479,1480,1481,1482,1483,1484,1485,1486,1487,1488,1489,1490,1491,1492,1493,1494,1495,1496,1497,1498,1499,1500,1501,1502,1503,1504,1505,1506,1507,1508,1509,1510,1511,1512,1513,1514,1515,1516,1517,1518,1519,1520,1521,1522,1523,1524,1525,1526,1527,1528,1529,1530,1531,1532,1533,1534,1535,1536,1537,1538,1539,1540,1541,1542,1543,1544,1545,1546,1547,1548,1549,1550,1551,1552,1553,1554,1555,1556,1557,1558,1559,1560,1561,1562,1563,1564,1565,1566,1567,1568,1569,1570,1571,1572,1573,1574,1575,1576,1577,1578,1579,1580,1581,1582,1583,1584,1585,1586,1587,1588,1589,1590,1591,1592,1593,1594,1595,1596,1597,1598,1599,1600,1601,1602,1603,1604,1605,1606,1607,1608,1609,1610,1611,1612,1613,1614,1615,1616,1617,1618,1619,1620,1621,1622,1623,1624,1625,1626,1627,1628,1629,1630,1631,1632,1633,1634,1635,1636,1637,1638,1639,1640,1641,1642,1643,1644,1645,1646,1647,1648,1649,1650,1651,1652,1653,1654,1655,1656,1657,1658,1659,1660,1661,1662,1663,1664,1665,1666,1667,1668,1669,1670,1671,1672,1673,1674,1675,1676,1677,1678,1679,1680,1681,1682,1683,1684,1685,1686,1687,1688,1689,1690,1691,1692,1693,1694,1695,1696,1697,1698,1699,1700,1701,1702,1703,1704,1705,1706,1707,1708,1709,1710,1711,1712,1713,1714,1715,1716,1717,1718,1719,1720,1721,1722,1723,1724,1725,1726,1727,1728,1729,1730,1731,1732,1733,1734,1735,1736,1737,1738,1739,1740,1741,1742,1743,1744,1745,1746,1747,1748,1749,1750,1751,1752,1753,1754,1755,1756,1757,1758,1759,1760,1761,1762,1763,1764,1765,1766,1767,1768,1769,1770,1771,1772,1773,1774,1775,1776,1777,1778,1779,1780,1781,1782,1783,1784,1785,1786,1787,1788,1789,1790,1791,1792,1793,1794,1795,1796,1797,1798,1799,1800,1801,1802,1803,1804,1805,1806,1807,1808,1809,1810,1811,1812,1813,1814,1815,1816,1817,1818,1819,1820,1821,1822,1823,1824,1825,1826,1827,1828,1829,1830,1831,1832,1833,1834,1835,1836,1837,1838,1839,1840,1841,1842,1843,1844,1845,1846,1847,1848,1849,1850,1851,1852,1853,1854,1855,1856,1857,1858,1859,1860,1861,1862,1863,1864,1865,1866,1867,1868,1869,1870,1871,1872,1873,1874,1875,1876,1877,1878,1879,1880,1881,1882,1883,1884,1885,1886,1887,1888,1889,1890,1891,1892,1893,1894,1895,1896,1897,1898,1899,1900,1901,1902,1903,1904,1905,1906,1907,1908,1909,1910,1911,1912,1913,1914,1915,1916,1917,1918,1919,1920,1921,1922,1923,1924,1925,1926,1927,1928,1929,1930,1931,1932,1933,1934,1935,1936,1937,1938,1939,1940,1941,1942,1943,1944,1945,1946,1947,1948,1949,1950,1951,1952,1953,1954,1955,1956,1957,1958,1959,1960,1961,1962,1963,1964,1965,1966,1967,1968,1969,1970,1971,1972,1973,1974,1975,1976,1977,1978,1979,1980,1981,1982,1983,1984,1985,1986,1987,1988,1989,1990,1991,1992,1993,1994,1995,1996,1997,1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022]');
	static scheduler = [
		/*
		"476.1.1",
		"1356.1.1",
		"1707.1.1",
		"1815.1.1",
		"1914.1.1",
		"1936.1.1",
		"1946.1.1",
		"1991.1.1",
		*/
		"2026.1.1"
	];
	
	constructor (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		options.interval = Math.returnSafeNumber(options.interval, 1e15);
		super("polities_Phersu", {
			...options,
			do_not_close_tab: true,
			log_channel: "Phersu_Scraper"
		});
		
		//Declare local instance variables
		this.options = options;
		this.static = polities_Phersu_Worker;
		
		//Start worker
		if (this.is_enabled && this.options.interval > 0)
			this.startInterval();
	}
	
	//[WIP] - This needs to output valid JSON and chunk it into 16 different JSON files.
	static async compile (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let fs = require('fs');
		let path = require('path');
		let dir_path = 'F:/scrapes/phersu/geojson/';
		let base_dir = path.resolve(dir_path, '..');
		let temp_dir = path.join(base_dir, 'temp_keyframes');
		
		if (!fs.existsSync(temp_dir)) fs.mkdirSync(temp_dir, { recursive: true });
		
		let parseDate = (file_name) => {
			let clean_name = file_name.replace(/\.json$/, '');
			let parts = clean_name.split('.');
			if (parts.length < 3) return { year: 0, month: 0, day: 0, string: clean_name };
			let day = parseInt(parts.pop(), 10);
			let month = parseInt(parts.pop(), 10);
			let year = parseInt(parts.join('.'), 10);
			return {
				year: isNaN(year) ? 0 : year,
				month: isNaN(month) ? 0 : month,
				day: isNaN(day) ? 0 : day,
				string: clean_name
			};
		};
		
		let compareDates = (date_a, date_b) => {
			if (date_a.year !== date_b.year) return date_a.year - date_b.year;
			if (date_a.month !== date_b.month) return date_a.month - date_b.month;
			return date_a.day - date_b.day;
		};
		
		let file_list = fs.readdirSync(dir_path).filter((file_name) => file_name.endsWith('.json'));
		file_list.sort((file_a, file_b) => compareDates(parseDate(file_a), parseDate(file_b)));
		
		let last_geom_map = {};
		let geom_props = {};
		let geom_ids = [];
		let active_geom_ids = {}; // Optimized tracker for non-null geometries
		let temp_path_map = {}; // Cache paths to avoid path.join in hot loops
		
		console.log('Starting Phase 1: Chronological Deduplication...');
		
		for (let i = 0; i < file_list.length; i++) {
			let file_name = file_list[i];
			if (i % 10 === 0 || i === file_list.length - 1)
				console.log('Reading file ' + (i + 1) + '/' + file_list.length + ': ' + file_name);
			
			let date_obj = parseDate(file_name);
			let date_key = date_obj.string;
			let geo_json = JSON.parse(fs.readFileSync(path.join(dir_path, file_name), 'utf8'));
			let feature_list = geo_json.features ? geo_json.features : [];
			let current_file_geom_ids = {};
			
			for (let j = 0; j < feature_list.length; j++) {
				let feature_item = feature_list[j];
				let geom_id = (feature_item.properties && feature_item.properties.state_id !== undefined) ? String(feature_item.properties.state_id) : null;
				if (geom_id === null) continue;
				
				current_file_geom_ids[geom_id] = true;
				let geom_str = JSON.stringify(feature_item.geometry);
				let temp_file = (temp_path_map[geom_id]) ? temp_path_map[geom_id] : path.join(temp_dir, geom_id + '.txt');
				if (!temp_path_map[geom_id]) temp_path_map[geom_id] = temp_file;
				
				if (!last_geom_map.hasOwnProperty(geom_id)) {
					geom_ids.push(geom_id);
					geom_props[geom_id] = Object.assign({}, feature_item.properties);
					delete geom_props[geom_id].keyframes;
					
					fs.writeFileSync(temp_file, JSON.stringify(date_key) + ': ' + geom_str, 'utf8');
					last_geom_map[geom_id] = geom_str;
					active_geom_ids[geom_id] = true;
				} else if (last_geom_map[geom_id] !== geom_str) {
					fs.appendFileSync(temp_file, ',\n' + JSON.stringify(date_key) + ': ' + geom_str, 'utf8');
					last_geom_map[geom_id] = geom_str;
					active_geom_ids[geom_id] = true;
				}
			}
			
			// Only iterate over geometries that were active to mark disappearances
			let active_keys = Object.keys(active_geom_ids);
			for (let m = 0; m < active_keys.length; m++) {
				let id = active_keys[m];
				if (!current_file_geom_ids[id]) {
					fs.appendFileSync(temp_path_map[id], ',\n' + JSON.stringify(date_key) + ': null', 'utf8');
					last_geom_map[id] = null;
					delete active_geom_ids[id];
				}
			}
		}
		
		console.log('Starting Phase 2: Distributing to scheduler slices...');
		let breakpoints = (this.scheduler) ? this.scheduler.map((date_str) => parseDate(date_str)) : [];
		breakpoints.sort(compareDates);
		
		let slice_count = breakpoints.length + 1;
		let slice_streams = [];
		let slice_geom_counts = [];
		
		for (let i = 0; i < slice_count; i++) {
			let stream = fs.createWriteStream(path.join(base_dir, 'phersu_' + i + '.json'));
			stream.write('{\n');
			slice_streams.push(stream);
			slice_geom_counts.push(0);
		}
		
		for (let k = 0; k < geom_ids.length; k++) {
			if (k % 500 === 0) console.log('Processing geometry ' + k + '/' + geom_ids.length + ' into slices...');
			let current_id = geom_ids[k];
			let raw_data = fs.readFileSync(temp_path_map[current_id], 'utf8');
			let entries = raw_data.split(',\n');
			
			for (let i = 0; i < slice_count; i++) {
				let start_bound = (i === 0) ? null : breakpoints[i - 1];
				let end_bound = (i === breakpoints.length) ? null : breakpoints[i];
				let valid_entries = [];
				let carry_over_val = null;
				
				for (let e = 0; e < entries.length; e++) {
					let line = entries[e];
					let split_idx = line.indexOf(': ');
					let entry_date = parseDate(JSON.parse(line.substring(0, split_idx)));
					let entry_val = line.substring(split_idx + 2);
					
					let is_after_start = (start_bound === null) ? true : compareDates(entry_date, start_bound) >= 0;
					let is_before_end = (end_bound === null) ? true : compareDates(entry_date, end_bound) < 0;
					
					if (is_after_start && is_before_end) {
						valid_entries.push(line);
					} else if (!is_after_start) {
						carry_over_val = entry_val;
					}
				}
				
				if (carry_over_val !== null && carry_over_val !== 'null') {
					let carry_line = JSON.stringify(start_bound.string) + ': ' + carry_over_val;
					if (valid_entries.length > 0) {
						let first_line = valid_entries[0];
						let first_val = first_line.substring(first_line.indexOf(': ') + 2);
						let first_date = JSON.parse(first_line.substring(0, first_line.indexOf(': ')));
						
						if (first_date !== start_bound.string && first_val !== carry_over_val)
							valid_entries.unshift(carry_line);
					} else {
						valid_entries.push(carry_line);
					}
				}
				
				// Deduplicate consecutive entries with identical geometry values
				let deduped_entries = [];
				let last_val = undefined;
				for (let e = 0; e < valid_entries.length; e++) {
					let cur_line = valid_entries[e];
					let cur_val = cur_line.substring(cur_line.indexOf(': ') + 2);
					if (cur_val !== last_val) {
						deduped_entries.push(cur_line);
						last_val = cur_val;
					}
				}
				valid_entries = deduped_entries;
				
				if (valid_entries.length > 0) {
					let output = (slice_geom_counts[i] > 0 ? ',\n' : '') + '  ' + JSON.stringify(current_id) + ': {\n';
					let props = geom_props[current_id];
					Object.keys(props).forEach((key) => { output += '    ' + JSON.stringify(key) + ': ' + JSON.stringify(props[key]) + ',\n'; });
					output += '    "keyframes": {\n      ' + valid_entries.join(',\n      ') + '\n    }\n  }';
					slice_streams[i].write(output);
					slice_geom_counts[i]++;
				}
			}
			fs.unlinkSync(temp_path_map[current_id]);
		}
		
		for (let i = 0; i < slice_count; i++) {
			slice_streams[i].write('\n}');
			slice_streams[i].end();
			console.log('Saved slice ' + i + ' with ' + slice_geom_counts[i] + ' geometries.');
		}
		if (fs.existsSync(temp_dir)) fs.rmdirSync(temp_dir);
	}
	
	/**
	 * Compiles a single temporal slice into Naissance FeatureLayers and Geometries.
	 *
	 * @param {number} [arg0_slice_index=0]
	 * @param {Object} [arg1_options]
	 *  @param {naissance.FeatureLayer} [arg1_options.feature_layer]
	 *  @param {boolean} [arg1_options.is_unified=false]
	 *  @param {string} [arg1_options.layer_name]
	 *
	 * @returns {naissance.FeatureLayer|void}
	 */
	static compileSliceToNaissance (arg0_slice_index, arg1_options) {
		//Convert from parameters
		let slice_index = (arg0_slice_index !== undefined) ? arg0_slice_index : 0;
		let options = (arg1_options) ? arg1_options : {};
		
		//Declare local instance variables
		let file_name = 'phersu_' + slice_index + '.json';
		let file_path = path.join(this.bf, file_name);
		
		if (!fs.existsSync(file_path)) return console.log('Slice file not found: ' + file_path);
		
		let split_date = (this.scheduler[slice_index]) ?
			this.scheduler[slice_index].split(".").map(Number) : null;
		
		let feature_layer = (options.feature_layer) ?
			options.feature_layer : new naissance.FeatureLayer();
		if (!options.feature_layer)
			feature_layer.name = (options.layer_name) ? options.layer_name : `Polities #${slice_index}`;
		
		console.log(`- Reading ${file_name} ..`);
		let json = JSON.parse(fs.readFileSync(file_path, "utf8"));
		let geom_keys = Object.keys(json);
		let geom_count = 0;
		
		//Iterate over all keys in json
		Object.iterate(json, (local_key, local_value) => {
			let geometry = (options.is_unified && naissance.Geometry.instances[local_key]) ?
				naissance.Geometry.instances[local_key] : null;
			let is_new = false;
			
			if (!geometry) {
				geometry = new naissance.GeometryPolygon({ is_import: true });
				geometry.setID(local_key);
				geometry.moveToFeature(feature_layer);
				is_new = true;
			}
			let first_timestamp;
			
			//Import geometry history
			if (local_value.keyframes) {
				let last_added_geom_str = undefined;
				
				// If geometry already has keyframes (e.g. unified mode importing across slices)
				if (geometry.history?.keyframes) {
					let existing_ts = geometry.history.getTimestamps();
					if (existing_ts.length > 0) {
						let last_kf = geometry.history.keyframes[existing_ts[existing_ts.length - 1]];
						if (last_kf && last_kf.value)
							last_added_geom_str = JSON.stringify(last_kf.value[0]);
					}
				}
				
				Object.iterate(local_value.keyframes, (local_timestamp, local_keyframe) => {
					let parse_date = local_timestamp.split(".").map(Number);
					let timestamp = Date.getTimestamp({
						year: parse_date[0], month: parse_date[1], day: parse_date[2] });
					if (first_timestamp === undefined) first_timestamp = timestamp;
					
					if (local_keyframe !== null) try {
						local_keyframe = turf.truncate(local_keyframe, { precision: 2, mutate: true });
						try { local_keyframe = turf.cleanCoords(local_keyframe, { mutate: true }); } catch (e) {}
					} catch (e) {}
					
					let current_geom_str = JSON.stringify(local_keyframe);
					if (current_geom_str === last_added_geom_str) return;
					
					geometry.history.addKeyframe(timestamp, local_keyframe);
					last_added_geom_str = current_geom_str;
				});
			}
			
			//Starting symbol and properties for newly instantiated geometry
			if (is_new || !options.is_unified) {
				let symbol_obj = {};
				let properties_obj = {};
				
				Object.iterate(local_value, (local_subkey, local_subvalue) => {
					if (local_subkey === "keyframes") return;
					let is_valid = (local_subvalue !== "nan" && local_subvalue !== "NaN" && local_subvalue !== null) ? true : false;
					
					if (is_valid)
						if (local_subkey === "colour") {
							symbol_obj.polygonFill = local_subvalue;
						} else if (local_subkey === "state") {
							properties_obj.name = local_subvalue;
						} else if (local_subkey === "descriptions") {
							if (!geometry.metadata) geometry.metadata = {};
							geometry.metadata.description = local_subvalue;
						} else {
							properties_obj[local_subkey] = local_subvalue;
						}
				});
				symbol_obj.lineWidth = 1;
				if (first_timestamp !== undefined)
					geometry.history.addKeyframe(first_timestamp, undefined, symbol_obj, properties_obj);
			}
			
			if (geometry.history && typeof geometry.history.cleanKeyframes === "function")
				geometry.history.cleanKeyframes();
			
			geom_count++;
			if (geom_count % 100 === 0 || geom_count === geom_keys.length)
				console.log(`- Added geometry ${geom_count}/${geom_keys.length} to naissance layer..`);
		});
		
		if (split_date && typeof UI_DateMenu !== "undefined" && UI_DateMenu.setDate)
			UI_DateMenu.setDate({ year: split_date[0], month: split_date[1], day: split_date[2], hour: 0, minute: 0 });
		
		console.log(`Finished processing slice ${slice_index}.`);
		return feature_layer;
	}
	
	/**
	 * Compiles Phersu polities to .naissance savefiles.
	 * Supports creating either individual slices or a single unified savefile.
	 *
	 * @param {Object|boolean} [arg0_options]
	 *  @param {boolean} [arg0_options.unified=false] - Whether to compile into a single unified .naissance savefile.
	 *  @param {boolean} [arg0_options.is_unified=false] - Alias for .unified.
	 *  @param {string} [arg0_options.file_path] - Target savefile path. Defaults to ./saves/phersu.naissance.
	 *  @param {string} [arg0_options.layer_name="Polities"] - Name of the unified feature layer.
	 *
	 * @returns {Promise<string|string[]>}
	 */
	static async compileToNaissance (arg0_options) {
		//Convert from parameters
		let options = (typeof arg0_options === "boolean") ?
			{ unified: arg0_options } :
			((arg0_options) ? arg0_options : {});
		
		let is_unified = (options.unified !== undefined) ? options.unified : (options.is_unified || false);
		
		//1. Unified compilation mode
		if (is_unified) {
			console.log("Compiling unified .naissance savefile across all slices...");
			if (typeof DALS !== "undefined" && DALS.clearMap) DALS.clearMap();
			
			let feature_layer = new naissance.FeatureLayer();
			feature_layer.name = (options.layer_name) ? options.layer_name : "Polities";
			
			//Discover all available slice files
			let total_slices = 0;
			while (fs.existsSync(path.join(this.bf, `phersu_${total_slices}.json`))) {
				total_slices++;
			}
			if (total_slices === 0) total_slices = this.scheduler.length;
			
			for (let i = 0; i < total_slices; i++) {
				console.log(`Importing slice ${i + 1}/${total_slices} into unified layer...`);
				this.compileSliceToNaissance(i, {
					...options,
					feature_layer: feature_layer,
					is_unified: true
				});
			}
			
			console.log("Cleaning keyframes across all unified geometries...");
			Object.iterate(naissance.Geometry.instances, (local_id, local_geom) => {
				if (local_geom?.history?.cleanKeyframes)
					local_geom.history.cleanKeyframes();
			});
			
			let output_path = options.file_path || options.target_path || "./saves/phersu.naissance";
			let output_dir = path.dirname(path.resolve(output_path));
			if (!fs.existsSync(output_dir)) fs.mkdirSync(output_dir, { recursive: true });
			
			console.log(`Writing unified .naissance file to: ${output_path} ..`);
			let save_json = DALS.toJSON();
			
			//Stream key-by-key to avoid V8 string length limits on large datasets
			let ws = fs.createWriteStream(output_path, { encoding: "utf8" });
			ws.write("{\n");
			let first = true;
			
			if (save_json.map_settings) {
				ws.write(`"map_settings":${JSON.stringify(save_json.map_settings)}`);
				first = false;
			}
			
			for (let key in save_json) {
				if (key === "map_settings") continue;
				if (!first) ws.write(",\n");
				ws.write(`"${key}":${JSON.stringify(save_json[key])}`);
				first = false;
			}
			
			ws.write("\n}");
			ws.end();
			await new Promise((resolve, reject) => {
				ws.on("finish", resolve);
				ws.on("error", reject);
			});
			
			console.log(`Successfully compiled unified savefile: ${output_path}`);
			return output_path;
		}
		
		//2. Slice-by-slice compilation mode (default)
		let output_files = [];
		for (let i = 0; i < this.scheduler.length; i++) {
			if (typeof DALS !== "undefined" && DALS.clearMap) DALS.clearMap();
			this.compileSliceToNaissance(i);
			let slice_save_path = `./saves/phersu/${i}.${this.scheduler[i]}.naissance`;
			let dir = path.dirname(path.resolve(slice_save_path));
			if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
			fs.writeFileSync(slice_save_path, JSON.stringify(DALS.toJSON()), "utf8");
			output_files.push(slice_save_path);
		}
		return output_files;
	}
	
	async execute (arg0_tab, arg1_instance) {
		//Convert from parameters
		let tab = arg0_tab;
		let instance = arg1_instance;
		
		//Declare local instance variables
		let geojson_cache = {};
		let last_geojson_string = "";
		let target_url = (this.options.url) ? this.options.url : "https://phersu-atlas.com/political-maps/global/standard_group/-3499/1/1";
		let years_list = (Array.isArray(this.static.years_with_changes) && this.static.years_with_changes.length > 0) ?
			this.static.years_with_changes : null;
		
		this.log(`Navigating to Phersu URL: ${target_url} ..`);
		await tab.goto(target_url, { waitUntil: "networkidle2" });
		
		//Wait for widget datepicker element
		await tab.waitForSelector("div.datepicker");
		
		//Ensure target geojson output directory exists
		if (!fs.existsSync(this.static.geojson_folder))
			fs.mkdirSync(this.static.geojson_folder, { recursive: true });
		
		let getDaysInMonth = (arg0_year, arg1_month) => {
			let m = Number(arg1_month);
			if ([1, 3, 5, 7, 8, 10, 12].includes(m)) return 31;
			if ([4, 6, 9, 11].includes(m)) return 30;
			if (m === 2) {
				let y = Number(arg0_year);
				let is_leap = (y % 4 === 0 && y % 100 !== 0) || (y % 400 === 0);
				return (is_leap) ? 29 : 28;
			}
			return 30;
		};
		
		//Helper to safely set cache entry with a maximum capacity of 100 items
		let setCacheEntry = (arg0_key, arg1_value) => {
			geojson_cache[arg0_key] = arg1_value;
			let cache_keys = Object.keys(geojson_cache);
			if (cache_keys.length > 100) {
				delete geojson_cache[cache_keys[0]];
			}
		};
		
		//Helper to fetch GeoJSON from local cache or browser tab
		let getGeoJSONForDate = async (arg0_year, arg1_month, arg2_day) => {
			let formatted_year = String(arg0_year).padStart(4, "0");
			let formatted_month = String(arg1_month).padStart(2, "0");
			let formatted_day = String(arg2_day).padStart(2, "0");
			let date_string = `${formatted_year}.${formatted_month}.${formatted_day}`;
			let file_path = path.join(this.static.geojson_folder, `${date_string}.json`);
			
			//Return from in-memory cache if available
			if (geojson_cache[date_string]) return geojson_cache[date_string];
			
			//Check local disk cache first
			if (fs.existsSync(file_path)) {
				try {
					let file_content = fs.readFileSync(file_path, "utf8");
					let parsed_obj = JSON.parse(file_content);
					
					let cache_entry = {
						data: parsed_obj,
						date_string: date_string,
						from_file: true,
						string: file_content
					};
					setCacheEntry(date_string, cache_entry);
					return cache_entry;
				} catch (e) {
					this.warn(`Failed reading cached file at ${file_path}, re-fetching ..`);
				}
			}
			
			//Navigate tab if not cached on disk
			await tab.evaluate((y, m, d) => {
				let year_ion = document.querySelector("ion-input[placeholder='Y']");
				let year_native = document.querySelector("ion-input[placeholder='Y'] input");
				let month_ion = document.querySelector("ion-input[placeholder='M']");
				let month_native = document.querySelector("ion-input[placeholder='M'] input");
				let day_ion = document.querySelector("ion-input[placeholder='D']");
				let day_native = document.querySelector("ion-input[placeholder='D'] input");
				
				if (year_ion) year_ion.value = String(y);
				if (year_native) {
					year_native.value = String(y);
					year_native.dispatchEvent(new Event("input", { bubbles: true }));
					year_native.dispatchEvent(new Event("change", { bubbles: true }));
				}
				if (month_ion) month_ion.value = String(m);
				if (month_native) {
					month_native.value = String(m);
					month_native.dispatchEvent(new Event("input", { bubbles: true }));
					month_native.dispatchEvent(new Event("change", { bubbles: true }));
				}
				if (day_ion) day_ion.value = String(d);
				if (day_native) {
					day_native.value = String(d);
					day_native.dispatchEvent(new Event("input", { bubbles: true }));
					day_native.dispatchEvent(new Event("change", { bubbles: true }));
				}
				
				let go_btn = document.querySelector("div.go-button");
				if (go_btn) go_btn.click();
			}, arg0_year, arg1_month, arg2_day);
			
			await tab.waitForFunction(() => !document.querySelector("div.loading"), { timeout: 30000 });
			await Blacktraffic.sleep(500);
			
			let geojson_data = await tab.evaluate(function () {
				let all_nodes = document.querySelectorAll("*");
				
				for (let i = 0; i < all_nodes.length; i++) {
					let node = all_nodes[i];
					
					if (node.__ngContext__) {
						let context_array = Array.isArray(node.__ngContext__) ? node.__ngContext__ : [node.__ngContext__];
						
						for (let j = 0; j < context_array.length; j++) {
							let item = context_array[j];
							
							if (item && typeof item === "object" && "politiesLayer" in item) {
								return item.polities_layer_geojson;
							}
						}
					}
				}
				
				return null;
			});
			
			let geojson_string = (geojson_data) ? JSON.stringify(geojson_data) : "";
			let cache_entry = {
				data: geojson_data,
				date_string: date_string,
				from_file: false,
				string: geojson_string
			};
			
			setCacheEntry(date_string, cache_entry);
			return cache_entry;
		};
		
		//Helper to record unique GeoJSON changes
		let saveGeoJSONEntry = (arg0_entry) => {
			if (!arg0_entry || !arg0_entry.data || !arg0_entry.string) return;
			
			let date_string = arg0_entry.date_string;
			let file_path = path.join(this.static.geojson_folder, `${date_string}.json`);
			
			if (arg0_entry.string !== last_geojson_string) {
				if (!fs.existsSync(file_path)) {
					fs.writeFileSync(file_path, arg0_entry.string);
					this.log(`Saved new polities layer GeoJSON for [${date_string}] to ${file_path}`);
				}
				last_geojson_string = arg0_entry.string;
			}
		};
		
		let years_to_process = (years_list) ? years_list : [0];
		
		for (let y = 0; y < years_to_process.length; y++) {
			let current_year = years_to_process[y];
			this.log(`Processing year: ${current_year} [${y + 1}/${years_to_process.length}] ..`);
			
			try {
				let year_start = await getGeoJSONForDate(current_year, 1, 1);
				let year_end = await getGeoJSONForDate(current_year, 12, 31);
				
				saveGeoJSONEntry(year_start);
				
				if (year_start.string === year_end.string) {
					continue;
				}
				
				for (let m = 1; m <= 12; m++) {
					let days_in_month = getDaysInMonth(current_year, m);
					
					let month_start = await getGeoJSONForDate(current_year, m, 1);
					let month_end = await getGeoJSONForDate(current_year, m, days_in_month);
					
					saveGeoJSONEntry(month_start);
					
					if (month_start.string === month_end.string) {
						continue;
					}
					
					//Recursive binary search range solver
					let binarySearchRange = async (arg0_start_day, arg1_end_day) => {
						let start_info = await getGeoJSONForDate(current_year, m, arg0_start_day);
						let end_info = await getGeoJSONForDate(current_year, m, arg1_end_day);
						
						saveGeoJSONEntry(start_info);
						
						if (start_info.string === end_info.string) return;
						
						if (arg1_end_day - arg0_start_day <= 1) {
							saveGeoJSONEntry(end_info);
							return;
						}
						
						let mid_day = Math.floor((arg0_start_day + arg1_end_day) / 2);
						await binarySearchRange(arg0_start_day, mid_day);
						await binarySearchRange(mid_day, arg1_end_day);
					};
					
					await binarySearchRange(1, days_in_month);
				}
			} catch (e) {
				this.error(`Error processing year ${current_year}:`, e);
			}
		}
		
		return [];
	}
};