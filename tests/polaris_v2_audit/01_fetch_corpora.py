import os
import re
import sys
import time
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
MASHKE_DIR = os.path.join(CACHE_DIR, "mashke")
os.makedirs(MASHKE_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) POLARIS-Census-Audit/2.0"}
BOT_HEADERS = {"User-Agent": "POLARISBot/2.0 (https://confoederatio.org; academic historical demography)"}

# Transcaucasian governorates belong to HANDBOOK, not POLARIS
EXCLUDED_1897_GOVS = {
    "bakinskaja.htm",
    "jelisavetpolskaja.htm",
    "karsskaja.htm",
    "kutaisskaja.htm",
    "tiflisskaja.htm",
    "erivanskaja.htm",
}

STANDALONE_MASHKE = [
    "empire1897-lang-counties-cities.htm",
    "empire1897-religion-counties-cities.htm",
    "empire1897-cities-suburbs.htm",
    "empire-census-1897-religion/total.htm",
    "ussr-historic-partial/index.htm",
    "ussr-ethnic1926-north.htm",
    "ussr-ethnic1926-northwest.htm",
    "ussr-ethnic1926-west.htm",
    "ussr-ethnic1926-centre.htm",
    "ussr-ethnic1926-black-earth.htm",
    "ussr-ethnic1926-middle-volga.htm",
    "ussr-ethnic1926-lower-volga.htm",
    "ussr-ethnic1926-vyatka.htm",
    "ussr-ethnic1926-ural.htm",
    "ussr-ethnic1926-bashkiria.htm",
    "ussr-ethnic1926-crimea.htm",
    "ussr-ethnic1926-north-caucasus.htm",
    "ussr-ethnic1926-dagestan.htm",
    "ussr-ethnic1926-siberia.htm",
    "ussr-ethnic1926-buryatia.htm",
    "ussr-ethnic1926-far-east.htm",
    "ussr-ethnic1926-yakutia.htm",
    "ussr-ethnic1926-belarus.htm",
    "ussr-ethnic1926-ukraine.htm",
    "ussr-ethnic1939-districts.htm",
    "poland-comm1931.htm",
    "hungary-census-k.htm",
    "finland-divisionempire.htm",
    "finland-division.htm",
    "finland-lang1880.htm",
    "finland-lang1890.htm",
    "finland-lang1900.htm",
    "finland-lang1910.htm",
    "finland-lang1920.htm",
    "estonia-religion1881.htm",
    "estonia-religion-comm1922.htm",
    "latvia-ethnic1920.htm",
    "latvia-religion-comm1925.htm",
    "russia-cities.htm",
    "ukraine-cities.htm",
    "belarus-cities.htm",
    "estonia-cities.htm",
    "latvia-cities.htm",
    "lithuania-cities.htm",
    "moldova-cities.htm",
    "poland-cities.htm",
    "rk-gfzs-census.htm",
    "rk-gfzs-estimation-comm.htm",
    "russia-census-2002/total.htm",
    "russia-census-2010/total.htm",
    "russia-census-2021/total.htm",
    "belarus-census-2009/total.htm",
    "belarus-census-2019/total.htm",
    "ukraine-census-pres/total.htm",
    "ukraine-estimation-pres/total.htm",
]


def fetch_url(url, dest_path, headers=None, min_bytes=50, timeout=60):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) >= min_bytes:
        return (url, True, os.path.getsize(dest_path), "cached")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    last_err = None
    for attempt in range(4):
        try:
            r = requests.get(url, headers=headers or HEADERS, timeout=timeout)
            r.raise_for_status()
            tmp = dest_path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(r.content)
            os.replace(tmp, dest_path)
            return (url, True, len(r.content), "fetched")
        except Exception as e:
            last_err = str(e)
            time.sleep(1.5 * (attempt + 1))
    return (url, False, 0, last_err)


def extract_mashke_sublinks(index_rel):
    p = os.path.join(MASHKE_DIR, index_rel)
    if not os.path.exists(p):
        return []
    raw = open(p, "rb").read()
    txt = raw.decode("utf-8", errors="replace")
    base_sub = os.path.dirname(index_rel)
    found = set()
    for m in re.finditer(r'href\s*=\s*["\']?([^"\'\s>]+)', txt, flags=re.I):
        href = m.group(1)
        if not href.lower().endswith(".htm"):
            continue
        if href.startswith("http://pop-stat.mashke.org/"):
            rel = href[len("http://pop-stat.mashke.org/"):]
        elif href.startswith("https://pop-stat.mashke.org/"):
            rel = href[len("https://pop-stat.mashke.org/"):]
        elif href.startswith("http"):
            continue
        elif "/" in href:
            rel = href.lstrip("./")
        else:
            rel = f"{base_sub}/{href}" if base_sub else href
        if not rel.startswith(base_sub + "/"):
            continue
        bn = os.path.basename(rel)
        if bn in ("index.htm", "total.htm") or "statistics" in rel:
            continue
        if base_sub == "empire-census-1897-religion" and bn in EXCLUDED_1897_GOVS:
            continue
        found.add(rel)
    return sorted(found)


def fetch_esbe_wikisource():
    out_path = os.path.join(CACHE_DIR, "esbe_1897.json")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        print(f"ESBE 1897 cached: {os.path.getsize(out_path):,} bytes")
        return True
    q = urllib.parse.urlencode({
        "action": "parse",
        "page": "ЭСБЕ/Россия/Население/Статистика населения/Население городов, посадов и других важнейших населенных мест",
        "prop": "wikitext",
        "format": "json",
    })
    url = f"https://ru.wikisource.org/w/api.php?{q}"
    for attempt in range(4):
        try:
            r = requests.get(url, headers=BOT_HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            wt = data.get("parse", {}).get("wikitext", {}).get("*", "")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"wikitext": wt}, f, ensure_ascii=False)
            print(f"ESBE 1897 fetched: {len(wt):,} chars")
            return True
        except Exception as e:
            print(f"ESBE attempt {attempt+1} failed: {e}")
            time.sleep(2 * (attempt + 1))
    return False


def main():
    print("Stage 1a: Downloading standalone Mashke index & country pages...")
    jobs = [(f"http://pop-stat.mashke.org/{rel}", os.path.join(MASHKE_DIR, rel)) for rel in STANDALONE_MASHKE]
    jobs.append(("https://archive.org/download/nasmesta/nasmesta_djvu.txt", os.path.join(CACHE_DIR, "nasmesta_djvu.txt")))

    failures = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch_url, u, p, None, 50, 90): u for u, p in jobs}
        for fut in as_completed(futs):
            u, ok, sz, msg = fut.result()
            if not ok:
                failures.append((u, msg))
                print(f"  FAIL {u}: {msg}")
    print(f"Standalone downloads done (failures={len(failures)}).")

    fetch_esbe_wikisource()

    sub_indexes = [
        "empire-census-1897-religion/total.htm",
        "ussr-historic-partial/index.htm",
        "russia-census-2002/total.htm",
        "russia-census-2010/total.htm",
        "russia-census-2021/total.htm",
        "belarus-census-2009/total.htm",
        "belarus-census-2019/total.htm",
        "ukraine-census-pres/total.htm",
        "ukraine-estimation-pres/total.htm",
    ]
    sub_rels = set()
    for idx in sub_indexes:
        links = extract_mashke_sublinks(idx)
        print(f"  {idx}: {len(links)} subpages")
        sub_rels.update(links)

    print(f"Stage 1b: Downloading {len(sub_rels)} expanded Mashke subpages...")
    sub_jobs = [(f"http://pop-stat.mashke.org/{rel}", os.path.join(MASHKE_DIR, rel)) for rel in sorted(sub_rels)]
    sub_fails = []
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_url, u, p, None, 50, 60): u for u, p in sub_jobs}
        for fut in as_completed(futs):
            u, ok, sz, msg = fut.result()
            done += 1
            if not ok:
                sub_fails.append((u, msg))
                print(f"  SUB FAIL {u}: {msg}")
            elif done % 100 == 0:
                print(f"  Progress: {done}/{len(sub_jobs)}")
    print(f"Done! total_failures={len(failures) + len(sub_fails)}")
    if failures or sub_fails:
        sys.exit(1)


if __name__ == "__main__":
    main()
