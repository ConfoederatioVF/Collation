import json, urllib.request, urllib.parse, time, re

INPUT = json.load(open("tests/tmp_chunk054_input.json", encoding="utf-8"))
LOCAL = json.load(open("tests/tmp_chunk054_local.json", encoding="utf-8"))
WD = json.load(open("tests/tmp_chunk054_wd.json", encoding="utf-8"))
UA = "ViscountHistoricalResearch/1.0 (mailto:research@confoederatio.org)"

def norm(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

best_wd = {}
es_titles = set()
en_titles = set()

for it in INPUT:
    k = it["key"]
    nm_n = norm(it["n"])
    als = [norm(a) for a in it.get("al", [])]
    rows = WD.get(k, [])
    # Score by name match + dist
    scored = []
    for r in rows:
        lbl_n = norm(r.get("label"))
        es_n = norm(r.get("esTitle"))
        en_n = norm(r.get("enTitle"))
        match_score = 0
        if lbl_n == nm_n or es_n == nm_n or en_n == nm_n:
            match_score = 100
        elif nm_n in lbl_n or nm_n in es_n or lbl_n in nm_n:
            match_score = 60
        elif any(a and (a == lbl_n or a in lbl_n) for a in als):
            match_score = 50
        scored.append((match_score - r["dist"] * 2, r))
    scored.sort(key=lambda x: -x[0])
    top = [r for _, r in scored[:3]]
    best_wd[k] = top
    for r in top[:2]:
        if r.get("esTitle"):
            es_titles.add(r["esTitle"])
        if r.get("enTitle"):
            en_titles.add(r["enTitle"])

def fetch_wiki(lang, titles):
    out = {}
    tlist = sorted(titles)
    for i in range(0, len(tlist), 20):
        chunk = tlist[i:i+20]
        params = urllib.parse.urlencode({
            "action": "query",
            "titles": "|".join(chunk),
            "prop": "extracts",
            "explaintext": "1",
            "exchars": "3000",
            "exlimit": "20",
            "redirects": "1",
            "format": "json"
        })
        url = f"https://{lang}.wikipedia.org/w/api.php?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                for pid, p in pages.items():
                    if "title" in p and "extract" in p:
                        out[p["title"]] = p["extract"]
        except Exception as e:
            print(f"Wiki {lang} batch {i//20} err:", e)
        time.sleep(0.5)
    return out

es_extracts = fetch_wiki("es", es_titles)
en_extracts = fetch_wiki("en", en_titles)

digest = {}
for it in INPUT:
    k = it["key"]
    loc_summary = []
    for m in LOCAL.get(k, []):
        loc_summary.append({
            "file": m.get("_file"),
            "name": m.get("name"),
            "source": m.get("source"),
            "sources": m.get("sources"),
            "aliases": m.get("aliases"),
            "notes": m.get("notes"),
            "admin": m.get("admin1") or m.get("departamento") or m.get("provincia") or m.get("municipality") or m.get("adm1"),
            "extra": {kk: vv for kk, vv in m.items() if kk not in {"_file","name","source","sources","aliases","notes","coords","ll","country","region","key","historical_names"}}
        })
    wd_summary = []
    for r in best_wd.get(k, []):
        es_t = r.get("esTitle")
        en_t = r.get("enTitle")
        wd_summary.append({
            "qid": r["qid"],
            "label": r["label"],
            "desc": r["desc"],
            "dist": round(r["dist"], 2),
            "inception": r["inception"],
            "esTitle": es_t,
            "enTitle": en_t,
            "esExtract": es_extracts.get(es_t, "")[:1200] if es_t else "",
            "enExtract": en_extracts.get(en_t, "")[:800] if en_t else "",
        })
    digest[k] = {
        "input": it,
        "local": loc_summary,
        "wd": wd_summary
    }

with open("tests/tmp_chunk054_digest.json", "w", encoding="utf-8") as f:
    json.dump(digest, f, ensure_ascii=False, indent=2)
print("es_extracts:", len(es_extracts), "en_extracts:", len(en_extracts))
