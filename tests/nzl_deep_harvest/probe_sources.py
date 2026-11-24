import os
import re
import requests
import pandas as pd

OUT_DIR = r"f:\Active Projects\Project 1509 - SVEA\tests\nzl_deep_harvest"
os.makedirs(OUT_DIR, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 1. Download LINZ Gazetteer CSV
gaz_path = os.path.join(OUT_DIR, "gaz.csv")
if not os.path.exists(gaz_path):
  print("Downloading LINZ gaz.csv...")
  r = requests.get("https://gazetteer.linz.govt.nz/gaz.csv", headers=HEADERS, timeout=60)
  r.raise_for_status()
  with open(gaz_path, "wb") as f:
    f.write(r.content)
  print("Saved gaz.csv:", len(r.content), "bytes")

df_gaz = pd.read_csv(gaz_path, low_memory=False)
print("LINZ Gazetteer rows:", len(df_gaz))
print("LINZ columns:", list(df_gaz.columns))
if "feat_type" in df_gaz.columns:
  print("Top 35 feat_type:\n", df_gaz["feat_type"].value_counts().head(35))

# 2. Crawl www3.stats.govt.nz/historic_publications/
base = "https://www3.stats.govt.nz/historic_publications/"
r = requests.get(base, headers=HEADERS, timeout=20)
print("\n=== HISTORIC PUBLICATIONS INDEX ===")
hrefs = re.findall(r'href=["\']([^"\']+)["\']', r.text, re.I)
for h in hrefs:
  print("  ", h)

# Follow any sub-index pages mentioning census
for h in hrefs:
  if "census" in h.lower() or "maori" in h.lower() or "historic" in h.lower():
    u = h if h.startswith("http") else (base + h.lstrip("/"))
    if u.startswith("https://www3.stats.govt.nz"):
      try:
        rr = requests.get(u, headers=HEADERS, timeout=20)
        if rr.status_code == 200:
          sub = re.findall(r'href=["\']([^"\']+)["\']', rr.text, re.I)
          print(f"\n--- Subpage {u} ({len(sub)} links) ---")
          for sh in sub:
            if any(k in sh.lower() for k in ("census", "maori", "vol", "185", "186", "187", "188", "189", "190", "191", "192", "193", "194", "195", "196", "197", "198", "199", "pdf", "html", "xls")):
              print("    ", sh)
      except Exception as e:
        print("ERR sub", u, e)
