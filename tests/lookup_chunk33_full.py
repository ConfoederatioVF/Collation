import json
import time
import urllib.parse
import urllib.request

from lookup_chunk33 import ITEMS, wiki_get

with open("tests/chunk33_wiki.json", "r", encoding="utf-8") as f:
    prev = json.load(f)

def safe_wiki(lang, params):
    for attempt in range(4):
        try:
            return wiki_get(lang, params)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
    return {}

# Step 1: retry any items that got 429
for idx, it in enumerate(ITEMS):
    k = it["key"]
    rec = prev.get(k, {})
    if any("429" in str(x) for x in rec.get("geo", []) + rec.get("sr", [])):
        lat, lng = it["ll"]
        geo_hits = []
        try:
            g = safe_wiki("es", {
                "action": "query", "list": "geosearch",
                "gscoord": f"{lat}|{lng}", "gsradius": 10000, "gslimit": 5, "format": "json"
            })
            geo_hits = [x["title"] for x in g.get("query", {}).get("geosearch", [])]
        except Exception as e:
            geo_hits = [f"ERR:{e}"]
        time.sleep(0.35)
        sr_hits = []
        qname = it["n"].split("(")[0].strip()
        try:
            s = safe_wiki("es", {
                "action": "query", "list": "search",
                "srsearch": f"{qname} {it['c']}", "srlimit": 3, "format": "json"
            })
            sr_hits = [x["title"] for x in s.get("query", {}).get("search", [])]
        except Exception as e:
            sr_hits = [f"ERR:{e}"]
        time.sleep(0.35)
        rec["geo"] = geo_hits
        rec["sr"] = sr_hits
        prev[k] = rec

# Step 2: collect target Wikipedia titles that actually match the settlement or nearby town
# Skip generic non-matching hits like footballers/elections/rivers unless plausibly relevant
SKIP_PREFIXES = ("Selección", "Frontera", "Relaciones", "Copa Perú", "Oficina Nacional", "Serie numismática", "Visitas de Juan Pablo", "Medio ambiente", "Escudo", "Bandera", "Estadio", "Aeródromo", "Liceo", "Teatro", "Cárcel", "Catedral", "Universidad", "Accidente", "Masacre", "Escarapela", "Olla vaporera", "Esmeralda Arboleda")

titles_to_fetch = set()
item_targets = {}
for it in ITEMS:
    k = it["key"]
    rec = prev[k]
    qname_low = it["n"].split("(")[0].strip().lower()
    chosen = []
    for t in rec.get("geo", []) + rec.get("sr", []):
        if t.startswith("ERR:") or t.startswith(SKIP_PREFIXES):
            continue
        # keep all geo hits (max 2) and matching sr hits (max 2)
        if t in rec.get("geo", [])[:2] or qname_low in t.lower() or any(a.lower() in t.lower() for a in it.get("al", [])):
            if t not in chosen:
                chosen.append(t)
    item_targets[k] = chosen[:3]
    for t in item_targets[k]:
        titles_to_fetch.add(t)

# Batch fetch full text extracts (up to 4000 chars each, 5 titles per request)
title_list = sorted(titles_to_fetch)
full_texts = {}
for i in range(0, len(title_list), 5):
    batch = title_list[i:i+5]
    try:
        res = safe_wiki("es", {
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "exchars": 3500,
            "titles": "|".join(batch),
            "format": "json"
        })
        for p in res.get("query", {}).get("pages", {}).values():
            if "title" in p and "extract" in p:
                full_texts[p["title"]] = p["extract"]
    except Exception as e:
        print("Batch err:", e)
    time.sleep(0.4)

out = {}
for it in ITEMS:
    k = it["key"]
    out[k] = {
        "n": it["n"],
        "c": it["c"],
        "r": it["r"],
        "ey": it["ey"],
        "ly": it["ly"],
        "al": it.get("al", []),
        "ex": it.get("ex", []),
        "geo": prev[k].get("geo", []),
        "sr": prev[k].get("sr", []),
        "texts": {t: full_texts.get(t, "") for t in item_targets[k]}
    }

with open("tests/chunk33_full.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Full done:", len(out), "articles:", len(full_texts))
