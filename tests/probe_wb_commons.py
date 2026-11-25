import json
import re
import urllib.request
import urllib.parse

# 1. Check CityPopulation LT & LV all sub-indexes
for u in ["https://www.citypopulation.de/en/lithuania/", "https://www.citypopulation.de/en/latvia/"]:
  h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8", errors="replace")
  links = sorted(set(re.findall(r'href=["\'](/en/(?:lithuania|latvia)/[^"\']+)["\']', h)))
  print("CP", u, links)

# 2. Check Wayback Machine for stat.gov.lv tautas skaitisana PDFs/pages
for pattern in [
  "stat.gov.lv/lv/statistikas-temas/iedzivotaji/iedzivotaju-skaits/publikacijas-un-infografikas/*tautas*",
  "stat.gov.lv/sites/default/files/*tautas*",
  "csb.gov.lv/*tautas_skaitisana*",
  "csp.gov.lv/*tautas*",
]:
  u = "https://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(pattern) + "&output=json&limit=20&filter=statuscode:200"
  try:
    res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode("utf-8"))
    print("WB:", pattern, "->", len(res), res[1:6] if len(res) > 1 else [])
  except Exception as e:
    print("WB ERR:", pattern, e)

# 3. Check Wikimedia Commons for 1920/1925/1930/1935 Latvian census & 1897 & 1923
for q in ["tautas skaitisana Latvija 1935", "Otrā tautas skaitīšana Latvijā", "Trešā tautas skaitīšana Latvijā", "Latvijas statistiskā gada grāmata"]:
  u = "https://commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=6&srsearch=" + urllib.parse.quote(q) + "&format=json"
  j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SVEA-Bot/1.0"}), timeout=20).read().decode("utf-8"))
  hits = [x["title"] for x in j.get("query", {}).get("search", [])]
  print("COMMONS:", q, "->", hits[:8])
