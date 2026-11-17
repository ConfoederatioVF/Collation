import os
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
GEO_DIR = os.path.join(CACHE_DIR, "geonames")
WD_DIR = os.path.join(CACHE_DIR, "wikidata")
os.makedirs(GEO_DIR, exist_ok=True)
os.makedirs(WD_DIR, exist_ok=True)

COUNTRIES_GEO = ["RU", "UA", "BY", "PL", "LT", "LV", "EE", "MD", "FI"]
COUNTRIES_WD = {
    "Belarus": "Q184",
    "Estonia": "Q191",
    "Finland": "Q33",
    "Latvia": "Q211",
    "Lithuania": "Q37",
    "Moldova": "Q217",
    "Poland": "Q36",
    "Ukraine": "Q212",
    "Russia": "Q159",
}
UA_HDR = {"User-Agent": "POLARISBot/2.0 (https://confoederatio.org; historical demography audit)"}


def download_geonames():
    urls = [("https://download.geonames.org/export/dump/admin1CodesASCII.txt", os.path.join(GEO_DIR, "admin1CodesASCII.txt"))]
    for cc in COUNTRIES_GEO:
        urls.append((f"https://download.geonames.org/export/dump/{cc}.zip", os.path.join(GEO_DIR, f"{cc}.zip")))
    for u, dest in urls:
        if not os.path.exists(dest) or os.path.getsize(dest) <= 500:
            r = requests.get(u, headers=UA_HDR, timeout=90)
            r.raise_for_status()
            with open(dest, "wb") as f:
                f.write(r.content)
    for cc in COUNTRIES_GEO:
        tpath = os.path.join(GEO_DIR, f"{cc}.txt")
        if not os.path.exists(tpath):
            with zipfile.ZipFile(os.path.join(GEO_DIR, f"{cc}.zip")) as zf:
                zf.extract(f"{cc}.txt", GEO_DIR)
    print(f"GeoNames ready for {len(COUNTRIES_GEO)} countries.", flush=True)


def sparql_query(q):
    url = "https://query.wikidata.org/sparql"
    for att in range(4):
        try:
            r = requests.post(
                url,
                data={"query": q, "format": "json"},
                headers={**UA_HDR, "Accept": "application/sparql-results+json"},
                timeout=45,
            )
            if r.status_code in (429, 502, 503, 504):
                time.sleep(3 * (att + 1))
                continue
            r.raise_for_status()
            return r.json().get("results", {}).get("bindings", [])
        except Exception as e:
            print(f"  SPARQL retry {att+1}: {e}", flush=True)
            time.sleep(2 * (att + 1))
    return []


def fetch_country(cname, qid):
    out_inc = os.path.join(WD_DIR, f"{cname}_inceptions.json")
    if not (os.path.exists(out_inc) and os.path.getsize(out_inc) > 50):
        # All places founded >= 1895 OR dissolved/abolished
        q1 = f"""
        SELECT ?item ?coord ?inc WHERE {{
          ?item wdt:P17 wd:{qid} ;
                wdt:P625 ?coord ;
                wdt:P571 ?inc .
          FILTER(YEAR(?inc) >= 1895)
        }}
        """
        q2 = f"""
        SELECT ?item ?coord ?diss WHERE {{
          ?item wdt:P17 wd:{qid} ;
                wdt:P625 ?coord ;
                wdt:P576 ?diss .
        }}
        """
        r1 = sparql_query(q1)
        r2 = sparql_query(q2)
        inc_rows = [{"item": b["item"]["value"], "coord": b["coord"]["value"], "inc": b["inc"]["value"]} for b in r1]
        diss_rows = [{"item": b["item"]["value"], "coord": b["coord"]["value"], "diss": b["diss"]["value"]} for b in r2]
        with open(out_inc, "w", encoding="utf-8") as f:
            json.dump({"inceptions": inc_rows, "dissolved": diss_rows}, f)
        print(f"  {cname} inc>=1895: {len(inc_rows)}, diss: {len(diss_rows)}", flush=True)

    out_hp = os.path.join(WD_DIR, f"{cname}_hist_pops.json")
    if not (os.path.exists(out_hp) and os.path.getsize(out_hp) > 100):
        bands = [(1850, 1915), (1916, 1950)]
        if cname in ("Russia", "Ukraine"):
            bands = [(1850, 1904), (1905, 1924), (1925, 1945)]
        collected = []
        for y0, y1 in bands:
            q = f"""
            SELECT ?item ?coord ?yr ?pop WHERE {{
              ?item wdt:P17 wd:{qid} ;
                    wdt:P625 ?coord ;
                    p:P1082 ?st .
              ?st ps:P1082 ?pop ;
                  pq:P585 ?dt .
              BIND(YEAR(?dt) AS ?yr)
              FILTER(?yr >= {y0} && ?yr <= {y1} && ?pop >= 450)
            }}
            """
            res = sparql_query(q)
            for b in res:
                collected.append({
                    "item": b["item"]["value"],
                    "coord": b["coord"]["value"],
                    "yr": int(b["yr"]["value"]),
                    "pop": float(b["pop"]["value"]),
                })
            print(f"  {cname} pops [{y0}-{y1}]: {len(res)}", flush=True)
            time.sleep(0.25)
        with open(out_hp, "w", encoding="utf-8") as f:
            json.dump(collected, f)


def main():
    download_geonames()
    for cname, qid in COUNTRIES_WD.items():
        fetch_country(cname, qid)
    print("Stage 1b complete!", flush=True)


if __name__ == "__main__":
    main()
