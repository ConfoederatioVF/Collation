import json
import os
import re
import ssl
import urllib.request

ctx = ssl.create_default_context()


def fetch(url):
  req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
  with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
    return r.read().decode("utf-8", errors="replace")


print("--- ABS DATAPACKS PROBE ---")
for url in [
  "https://www.abs.gov.au/census/find-census-data/datapacks",
  "https://www.abs.gov.au/census/find-census-data/datapacks/download/2011_TSP_SSC_for_AUST_short-header.zip",
  "https://www.abs.gov.au/census/find-census-data/datapacks/download/2016_TSP_SSC_for_AUS_short-header.zip",
]:
  try:
    if url.endswith(".zip"):
      req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
      with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        print("HEAD OK:", r.status, r.headers.get("Content-Length"), url)
    else:
      html = fetch(url)
      zips = sorted(set(re.findall(r'https?://[^\s"\'<>]+\.zip', html, re.I)))
      rel = sorted(set(re.findall(r'/census/find-census-data/datapacks/download/[^\s"\'<>]+', html, re.I)))
      apis = sorted(set(re.findall(r'https?://[^\s"\'<>]*(?:datapack|census)[^\s"\'<>]*', html, re.I)))
      print("PAGE:", url, "len=", len(html), "zips=", zips[:8], "rel=", rel[:8])
      print("  apis:", [a for a in apis if "datapack" in a.lower()][:15])
      # Also look for drupalSettings or JS bundle URLs mentioning datapacks
      js = sorted(set(re.findall(r'src="([^"]*datapack[^"]*\.js[^"]*)"', html, re.I)))
      print("  js:", js[:10])
      # Check inline JSON/drupalSettings
      m = re.search(r'drupalSettings.*?datapacks[^<]{0,1500}', html, re.I | re.S)
      if m:
        print("  drupalSettings snippet:", m.group(0)[:800])
  except Exception as e:
    print("ERR:", url, e)

print("\n--- HCCDA PROBE ---")
try:
  html = fetch("https://hccda.ada.edu.au/")
  links = sorted(set(re.findall(r'href=["\']([^"\']+)["\']', html)))
  print("HCCDA links:", [l for l in links if not l.startswith("#")][:40])
except Exception as e:
  print("HCCDA ERR:", e)

print("\n--- ABS HISTORIC CENSUS PROBE ---")
for url in [
  "https://www.abs.gov.au/AUSSTATS/abs@.nsf/allprimarymainfeatures/475C8B5C5A79862BCA25784C00158F17",
  "https://www.abs.gov.au/statistics/people/population/historical-population",
  "https://www.abs.gov.au/census/about-census/history",
]:
  try:
    html = fetch(url)
    print("ABS page OK:", url, "len=", len(html))
  except Exception as e:
    print("ABS page ERR:", url, e)
