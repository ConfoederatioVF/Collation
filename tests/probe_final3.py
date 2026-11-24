import json
import os
import re
import urllib.request

H = {"User-Agent": "Mozilla/5.0"}

snap = json.load(open(r"histmap\1.data_raw\population_regional\AUSTRAL\_shared\austral_enrichment_audit_snapshot.json", encoding="utf-8"))
print("LAW4:", json.dumps(snap["law4_verification"]))
for c in ("Papua New Guinea", "French Polynesia", "Fiji", "Vanuatu", "Marshall Islands", "Palau"):
  d = snap["per_country_modern_distribution"].get(c, {})
  print(f"  {c:18s}: n={d.get('modern_count'):4d} | max5={d.get('largest_5')}")

print("\nLocal _aus_r2_cache:", os.listdir(r"tests\_aus_r2_cache"))
print("Local _aus_r2_cache/pdfs:", os.listdir(r"tests\_aus_r2_cache\pdfs"))

# Probe ABS 2001 UCL (2016.02001) & 2006 Census UCL (2914.0.55.002 / 2068.0) & 2011 TSP UCL
for url in [
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2016.02001?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2016.12001?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2016.22001?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2016.32001?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2016.42001?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2016.52001?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2016.62001?OpenDocument",
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/2016.72001?OpenDocument",
  "https://www.abs.gov.au/census/find-census-data/datapacks/download/2011_TSP_UCL_for_AUS_short-header.zip",
  "https://www.abs.gov.au/census/find-census-data/datapacks/download/2011_TSP_SSC_for_AUS_short-header.zip",
]:
  try:
    req = urllib.request.Request(url, headers=H)
    if url.endswith(".zip"):
      req.method = "HEAD"
      with urllib.request.urlopen(req, timeout=12) as r:
        print("ZIP OK:", r.status, r.headers.get("Content-Length"), url)
    else:
      html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
      links = re.findall(r'href=["\']([^"\']*log\?openagent[^"\']*)["\']', html, re.I)
      print(f"PAGE {url.split('/')[-1]}: {len(links)} download links; sample={links[:3]}")
  except Exception as e:
    print("ERR", url.split("/")[-1], e)
