import json
import time
import urllib.parse
import urllib.request

with open("tests/lookup_chunk055.py", "r", encoding="utf-8") as f:
  src = f.read()

# Extract ITEMS from lookup_chunk055.py
ns = {}
exec(src.split("def fetch_json")[0], ns)
ITEMS = ns["ITEMS"]

def fetch_json(url):
  req = urllib.request.Request(url, headers={
    "User-Agent": "SVEA-HistoricalToponymy/1.0 (https://confoederatio.org; research@confoederatio.org)",
    "Accept": "application/json"
  })
  with urllib.request.urlopen(req, timeout=20) as r:
    return json.loads(r.read().decode("utf-8"))

# Batch search using es.wikipedia sequential with 0.3s sleep
out = []
for idx, item in enumerate(ITEMS):
  n = item["n"].split("(")[0].strip()
  c = item["c"]
  r = item["r"]
  lat, lng = item["ll"]
  rec = {"key": item["key"], "n": item["n"], "c": c, "r": r, "ll": item["ll"], "ey": item["ey"]}

  # 1. es.wikipedia geosearch (only 5km)
  try:
    gurl = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
    gdata = fetch_json(gurl)
    rec["geo"] = [{"t": x["title"], "d": round(x["dist"])} for x in gdata.get("query", {}).get("geosearch", [])]
  except Exception as e:
    rec["geo_err"] = str(e)
  time.sleep(0.25)

  # 2. Only text-search if geo didn't find an exact/close match, or always for modern towns
  q = n
  if r.startswith(("per_", "ecu_", "col_", "arg_", "bol_", "chl_", "ven_", "ury_")):
    reg = r.split("_", 1)[1].replace("_", " ")
  else:
    reg = ""
  sq = f"{q} {c}"
  try:
    surl = "https://es.wikipedia.org/w/api.php?action=query&list=search&srlimit=3&format=json&srsearch=" + urllib.parse.quote(sq)
    sdata = fetch_json(surl)
    rec["hits"] = [x["title"] for x in sdata.get("query", {}).get("search", [])]
  except Exception as e:
    rec["search_err"] = str(e)
  time.sleep(0.25)

  out.append(rec)
  if (idx + 1) % 15 == 0:
    print(f"Processed {idx+1}/{len(ITEMS)}", flush=True)

with open("tests/chunk055_wiki_probe.json", "w", encoding="utf-8") as f:
  json.dump(out, f, ensure_ascii=False, indent=2)
print("Saved all 90.")
