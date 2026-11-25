"""Fetches primary DOMM monastery detail pages from mongoliantemples.org for Phase 3 calibration."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HARVEST_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "_census_cache", "historical_harvest"))
IN_PATH = os.path.join(HARVEST_DIR, "domm_mongolian_monasteries.json")
OUT_PATH = os.path.join(HARVEST_DIR, "domm_mongolian_monasteries_enriched.json")


def parse_monks_count(arg0_text):
  """Extracts an integer monk count from DOMM 'Monks in Old Temple' text, or None if unquantified."""
  raw = str(arg0_text or "").strip()
  if not raw:
    return None
  low = raw.lower()
  if any(k in low for k in ("unknown", "no info", "n/a", "none", "not known")):
    return None
  range_m = re.search(r"(\d[\d,\.]*)\s*[-–to]+\s*(\d[\d,\.]*)", raw)
  if range_m:
    a = int(re.sub(r"[,\.]", "", range_m.group(1)))
    b = int(re.sub(r"[,\.]", "", range_m.group(2)))
    if 1 <= a <= 50000 and 1 <= b <= 50000:
      return int(round(0.5*(a + b)))
  num_m = re.search(r"(\d[\d,]*)", raw)
  if num_m:
    val = int(re.sub(r",", "", num_m.group(1)))
    if 1 <= val <= 50000:
      return val
  return None


def parse_year(arg0_text):
  """Extracts a 4-digit historical year (1500..1938) from DOMM establishment/closing text."""
  m = re.search(r"\b(1[5-9]\d{2})\b", str(arg0_text or ""))
  return int(m.group(1)) if m else None


def fetch_one(arg0_rec):
  """Fetches and parses one DOMM detail page."""
  rec = dict(arg0_rec)
  href_m = re.search(r'href="([^"]+)"', str(rec.get("raw_html") or ""))
  if not href_m:
    return rec
  url = "https://mongoliantemples.org" + href_m.group(1)
  rec["url"] = url
  try:
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
      rec["http_status"] = resp.status_code
      return rec
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", resp.text, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", "\n", txt)
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    fields = {}
    labels = (
      "Type of Monastery/Temple:",
      "Date of establishment of the monastery/temple :",
      "Date of closing and destroying the monastery :",
      "Monks in Old Temple :",
    )
    for idx, line in enumerate(lines):
      for lbl in labels:
        if line.startswith(lbl) and idx + 1 < len(lines):
          nxt = lines[idx + 1]
          if not any(nxt.startswith(other) for other in labels) and not nxt.endswith(":"):
            fields[lbl] = nxt
    rec["temple_type"] = fields.get("Type of Monastery/Temple:", "")
    rec["est_raw"] = fields.get("Date of establishment of the monastery/temple :", "")
    rec["established_year"] = parse_year(rec["est_raw"])
    rec["closed_raw"] = fields.get("Date of closing and destroying the monastery :", "")
    rec["closed_year"] = parse_year(rec["closed_raw"])
    rec["monks_raw"] = fields.get("Monks in Old Temple :", "")
    rec["monks_count"] = parse_monks_count(rec["monks_raw"])
  except Exception as err:
    rec["fetch_error"] = str(err)[:120]
  return rec


def main():
  rows = json.load(open(IN_PATH, encoding="utf-8"))
  out = [None]*len(rows)
  with ThreadPoolExecutor(max_workers=8) as pool:
    futs = {pool.submit(fetch_one, rows[i]): i for i in range(len(rows))}
    done = 0
    for fut in as_completed(futs):
      idx = futs[fut]
      out[idx] = fut.result()
      done += 1
      if done % 100 == 0 or done == len(rows):
        with_monks = sum(1 for r in out if r and r.get("monks_count"))
        print(f"Fetched {done}/{len(rows)} DOMM pages (with numeric monks_count={with_monks})", flush=True)
  with open(OUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)
  with_monks = sum(1 for r in out if r and r.get("monks_count"))
  print(f"Saved {len(out)} enriched DOMM records ({with_monks} with numeric monks_count) to {OUT_PATH}", flush=True)


if __name__ == "__main__":
  main()
