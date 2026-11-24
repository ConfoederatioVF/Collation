import json
import unicodedata
import urllib.request
import urllib.parse
import time

with open("tests/quipu_lookup.py", "r", encoding="utf-8") as f:
    src = f.read()
ns = {}
exec(src.split("HEADERS =")[0], ns)
INPUT = ns["INPUT"]

with open("tests/quipu_wikidata.json", "r", encoding="utf-8") as f:
    wd = json.load(f)

UA = "ViscountHistoricalResearch/1.0 (mailto:research@confoederatio.org)"

def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(s.replace("-", " ").replace("_", " ").split())

best_matches = {}
es_titles = set()
en_titles = set()

for item in INPUT:
    k = item["key"]
    rows = wd.get(k, [])
    names = [norm(item["n"])] + [norm(a) for a in item.get("al", [])]
    # score each row
    scored = []
    for r in rows:
        lbl = norm(r.get("label") or "")
        est = norm(r.get("esTitle") or "")
        ent = norm(r.get("enTitle") or "")
        score = 0
        for nm in names:
            if not nm:
                continue
            if nm == lbl or nm == est or nm == ent:
                score = max(score, 100)
            elif nm in lbl or nm in est or nm in ent:
                score = max(score, 60)
            elif lbl and lbl in nm:
                score = max(score, 50)
        if r.get("esTitle"):
            score += 10
        if r.get("enTitle"):
            score += 5
        scored.append((score, -r["dist"], r))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top = [x[2] for x in scored[:4]]
    best_matches[k] = top
    for r in top:
        if r.get("esTitle"):
            es_titles.add(r["esTitle"])
        if r.get("enTitle"):
            en_titles.add(r["enTitle"])

def fetch_extracts(lang, titles):
    titles = sorted(titles)
    out = {}
    for i in range(0, len(titles), 10):
        batch = titles[i:i+10]
        params = {
            "action": "query",
            "prop": "extracts",
            "explaintext": "1",
            "exchars": "3500",
            "titles": "|".join(batch),
            "format": "json"
        }
        url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for p in data.get("query", {}).get("pages", {}).values():
                    if "title" in p and "extract" in p:
                        out[p["title"]] = p["extract"]
        except Exception as e:
            print(f"{lang} batch {i}: {e}")
        time.sleep(0.8)
    return out

print(f"Fetching {len(es_titles)} eswiki and {len(en_titles)} enwiki pages...")
es_ext = fetch_extracts("es", es_titles)
en_ext = fetch_extracts("en", en_titles)

summary = []
for item in INPUT:
    k = item["key"]
    top = best_matches.get(k, [])
    entries = []
    for r in top:
        e = dict(r)
        if r.get("esTitle") and r["esTitle"] in es_ext:
            e["es_extract"] = es_ext[r["esTitle"]][:2200]
        if r.get("enTitle") and r["enTitle"] in en_ext:
            e["en_extract"] = en_ext[r["enTitle"]][:1500]
        entries.append(e)
    summary.append({
        "key": k,
        "n": item["n"],
        "c": item["c"],
        "r": item["r"],
        "ll": item["ll"],
        "ey": item["ey"],
        "ly": item["ly"],
        "al": item.get("al", []),
        "ex": item.get("ex", []),
        "matches": entries
    })

with open("tests/quipu_enriched.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print("Saved tests/quipu_enriched.json")
