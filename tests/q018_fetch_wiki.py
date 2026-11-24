import json, time, urllib.parse, urllib.request

with open("tests/q018_local_and_wd.json", encoding="utf-8") as f:
    data = json.load(f)

# Collect unique eswiki and enwiki titles matching item name or closest place
es_titles = set()
en_titles = set()
for k, rec in data.items():
    n_low = rec["input"]["n"].lower().split("(")[0].strip()
    seen_es = []
    seen_en = []
    for w in rec.get("wd", []):
        lbl = w.get("placeLabel", "").lower()
        es = w.get("eswiki", "")
        en = w.get("enwiki", "")
        if es:
            t = urllib.parse.unquote(es.split("/wiki/")[-1]).replace("_", " ")
            if t not in seen_es:
                seen_es.append(t)
        if en:
            t = urllib.parse.unquote(en.split("/wiki/")[-1]).replace("_", " ")
            if t not in seen_en:
                seen_en.append(t)
    # Keep top 3 es/en titles per settlement, prioritizing name match
    seen_es.sort(key=lambda t: (0 if n_low in t.lower() else 1, len(t)))
    seen_en.sort(key=lambda t: (0 if n_low in t.lower() else 1, len(t)))
    for t in seen_es[:2]:
        es_titles.add(t)
    for t in seen_en[:2]:
        en_titles.add(t)

UA = {"User-Agent": "OperationViscountToponymy/1.0 (https://confoederatio.org; mailto:research@confoederatio.org)"}

def fetch_extracts(lang, titles_list):
    res = {}
    for i in range(0, len(titles_list), 20):
        batch = titles_list[i:i+20]
        params = urllib.parse.urlencode({
            "action": "query",
            "prop": "extracts",
            "exintro": "0",
            "explaintext": "1",
            "exchars": "2500",
            "titles": "|".join(batch),
            "format": "json"
        })
        url = f"https://{lang}.wikipedia.org/w/api.php?{params}"
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=20) as r:
                    d = json.loads(r.read().decode("utf-8"))
                for pid, p in d.get("query", {}).get("pages", {}).items():
                    if "extract" in p:
                        res[p["title"]] = p["extract"]
                break
            except Exception as e:
                print(f"{lang} batch {i//20+1} attempt {attempt+1} err: {e}", flush=True)
                time.sleep(3.0 * (attempt + 1))
        time.sleep(1.0)
    return res

es_ext = fetch_extracts("es", sorted(es_titles))
en_ext = fetch_extracts("en", sorted(en_titles))
with open("tests/q018_wiki_ext.json", "w", encoding="utf-8") as f:
    json.dump({"es": es_ext, "en": en_ext}, f, ensure_ascii=False, indent=2)
print(f"Fetched es={len(es_ext)}/{len(es_titles)}, en={len(en_ext)}/{len(en_titles)}")
