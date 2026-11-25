import json
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 1. Check pop-stat.mashke.org for Lithuania & Latvia
for u in [
  "http://pop-stat.mashke.org/lithuania-cities.htm",
  "http://pop-stat.mashke.org/latvia-cities.htm",
  "http://pop-stat.mashke.org/lithuania-places.htm",
  "http://pop-stat.mashke.org/latvia-places.htm",
  "http://pop-stat.mashke.org/",
]:
  try:
    h = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20).read().decode("utf-8", errors="replace")
    print("POP-STAT:", u, "len:", len(h), "title:", re.findall(r"<title>(.*?)</title>", h, re.S))
    if u.endswith("/"):
      links = [x for x in re.findall(r'href=["\']([^"\']+)["\']', h) if any(k in x.lower() for k in ["lith", "latv", "balt", "russ", "1897"])]
      print("  index links:", links[:25])
    else:
      print("  sample:", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))[:600])
  except Exception as e:
    print("POP-STAT ERR:", u, e)

# 2. Check citypopulation.de all 10 LT counties row counts
counties = ["alytus", "kaunas", "klaipeda", "marijampole", "panevezys", "siauliai", "taurage", "telsiai", "utena", "vilnius"]
tot_lt = 0
for c in counties:
  u = f"https://www.citypopulation.de/en/lithuania/{c}/"
  try:
    h = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20).read().decode("utf-8", errors="replace")
    trs = len(re.findall(r"<tr[^>]*>", h))
    tot_lt += trs
    print("CP LT:", c, "trs:", trs)
  except Exception as e:
    print("CP LT ERR:", c, e)
print("CP LT total trs:", tot_lt)
