import json
import glob
import urllib.request
import urllib.parse
import time
import re

research = json.load(open('tests/chunk016_research.json', encoding='utf-8'))

# 1. Inspect HGIS Indias colonial raw
hgis = json.load(open('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/hgis_indias_colonial_raw.json', encoding='utf-8'))
hgis_setts = hgis['settlements']
print("HGIS settlements count:", len(hgis_setts), "sample keys:", list(hgis_setts[0].keys()) if isinstance(hgis_setts, list) else list(next(iter(hgis_setts.values())).keys()))

hgis_list = hgis_setts if isinstance(hgis_setts, list) else list(hgis_setts.values())
hgis_by_key = {}
for item in hgis_list:
    lat = item.get('lat') or (item.get('coords') or [None, None])[0]
    lon = item.get('lng') or item.get('lon') or (item.get('coords') or [None, None])[1]
    if lat is None or lon is None:
        continue
    for d in research:
        tlat, tlon = d['ll']
        if abs(float(lat) - tlat) < 0.03 and abs(float(lon) - tlon) < 0.03:
            hgis_by_key.setdefault(d['key'], []).append({k: v for k, v in item.items() if k not in ('population', 'pop', 'series')})

# 2. Check SIGDA / Peru / Ecuador / Colombia / Venezuela raw files for archaeological or other notes
raw_files = glob.glob('histmap/1.data_raw/population_regional/QUIPU/_shared/settlement_sources/*.json')
extra_local = {}
for rf in raw_files:
    if 'hgis_indias' in rf:
        continue
    try:
        rdata = json.load(open(rf, encoding='utf-8'))
        ritems = rdata.get('settlements', rdata) if isinstance(rdata, dict) else rdata
        if isinstance(ritems, dict):
            ritems = list(ritems.values())
        if not isinstance(ritems, list):
            continue
        for item in ritems:
            if not isinstance(item, dict):
                continue
            lat = item.get('lat') or (item.get('coords') or [None, None])[0]
            lon = item.get('lng') or item.get('lon') or (item.get('coords') or [None, None])[1]
            if lat is None or lon is None:
                continue
            for d in research:
                tlat, tlon = d['ll']
                if abs(float(lat) - tlat) < 0.015 and abs(float(lon) - tlon) < 0.015:
                    slim = {k: v for k, v in item.items() if k not in ('population', 'pop', 'series', 'yearly_populations')}
                    extra_local.setdefault(d['key'], []).append({rf.split('\\')[-1].split('/')[-1]: slim})
    except Exception:
        pass

HEADERS = {"User-Agent": "SVEA-HistoricalToponymy/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def api_get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2.0 * (attempt + 1)
                time.sleep(wait)
            else:
                return {"error": str(e)}
        except Exception as e:
            time.sleep(1.0)
    return {"error": "max_retries"}

# 3. Gentle sequential geosearch on es.wikipedia for all 90
all_titles = set()
for idx, d in enumerate(research):
    lat, lon = d['ll']
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json"
    gj = api_get(url)
    hits = gj.get("query", {}).get("geosearch", [])
    d["es_geo"] = [{"title": h["title"], "dist": round(h["dist"], 1)} for h in hits]
    # Also do a name search if no geo hit within 3km with similar name
    n_low = d["n"].lower().split()[0]
    has_close = any(n_low in h["title"].lower() or h["dist"] < 2500 for h in hits)
    if not has_close:
        q = urllib.parse.quote(f"{d['n']} {d['c']}")
        surl = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
        sj = api_get(surl)
        shits = sj.get("query", {}).get("search", [])
        d["es_search"] = [{"title": h["title"]} for h in shits]
        for h in shits[:1]:
            all_titles.add(h["title"])
        time.sleep(0.15)
    for h in hits[:2]:
        all_titles.add(h["title"])
    d["hgis_raw"] = hgis_by_key.get(d["key"], [])
    d["extra_local"] = extra_local.get(d["key"], [])
    time.sleep(0.15)

# 4. Batch fetch extracts from es.wikipedia (20 titles per batch; prop=extracts limits exlimit to 20)
title_list = sorted(all_titles)
extracts_map = {}
for i in range(0, len(title_list), 10):
    batch = title_list[i:i+10]
    tq = urllib.parse.quote("|".join(batch))
    url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=true&exchars=3000&titles={tq}&format=json"
    ej = api_get(url)
    pages = ej.get("query", {}).get("pages", {})
    for pid, pdata in pages.items():
        if "title" in pdata and "extract" in pdata:
            extracts_map[pdata["title"]] = pdata["extract"]
    time.sleep(0.2)

for d in research:
    d["extracts"] = {}
    cand = [h["title"] for h in d.get("es_geo", [])[:2]] + [h["title"] for h in d.get("es_search", [])[:1]]
    for t in cand:
        if t in extracts_map:
            d["extracts"][t] = extracts_map[t]

with open("tests/chunk016_research.json", "w", encoding="utf-8") as f:
    json.dump(research, f, ensure_ascii=False, indent=2)

print("Completed! Unique titles fetched:", len(extracts_map), "HGIS raw matches:", len(hgis_by_key))
