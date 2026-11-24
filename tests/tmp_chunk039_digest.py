import json
import time
import urllib.parse
import urllib.request

with open("tests/tmp_chunk039_enriched.json", "r", encoding="utf-8") as f:
    data = json.load(f)

UA = "ViscountHistoricalResearch/1.0 (mailto:research@confoederatio.org)"

# Find missing eswiki extracts on best match (#0 or #1) or search_hits
missing_es = set()
for item in data:
    for m in item["matches"][:2]:
        t = m.get("esTitle")
        if t and "es_extract" not in m:
            missing_es.add(t)
    for sh in item.get("search_hits", []):
        t = sh.get("title")
        if t and not sh.get("es_extract"):
            missing_es.add(t)

print(f"Missing top eswiki titles: {len(missing_es)}")
es_ext = {}
titles = sorted(missing_es)
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
    url = "https://es.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            for p in res.get("query", {}).get("pages", {}).values():
                if "title" in p and "extract" in p:
                    es_ext[p["title"]] = p["extract"]
    except Exception as e:
        print(f"Retry batch {i}: {e}")
    time.sleep(2.0)

for item in data:
    for m in item["matches"]:
        t = m.get("esTitle")
        if t and t in es_ext and "es_extract" not in m:
            m["es_extract"] = es_ext[t][:2200]
    for sh in item.get("search_hits", []):
        t = sh.get("title")
        if t and t in es_ext and not sh.get("es_extract"):
            sh["es_extract"] = es_ext[t][:2000]

with open("tests/tmp_chunk039_enriched.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Produce a compact readable digest in 3 parts (30 each)
lines = []
for idx, item in enumerate(data):
    lines.append(f"=== [{idx+1}] {item['key']} | n={item['n']} | c={item['c']} | r={item['r']} | ll={item['ll']} | ey={item['ey']} | ly={item['ly']} | al={item['al']} | ex={item['ex']} ===")
    for m in item["matches"][:2]:
        inc = (m.get("inception") or "")[:10]
        lines.append(f"  WD({m['dist']:.2f}km): {m.get('label')} [{m['qid']}] inc={inc} | desc={m.get('desc')} | es={m.get('esTitle')} | en={m.get('enTitle')}")
        if m.get("es_extract"):
            lines.append("    ES: " + m["es_extract"].replace("\n", " ")[:900])
        elif m.get("en_extract"):
            lines.append("    EN: " + m["en_extract"].replace("\n", " ")[:700])
    for sh in item.get("search_hits", [])[:1]:
        lines.append(f"  SEARCH: {sh.get('title')}")
        if sh.get("es_extract"):
            lines.append("    ES: " + sh["es_extract"].replace("\n", " ")[:700])

with open("tests/tmp_chunk039_digest.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Wrote digest ({len(lines)} lines)")
