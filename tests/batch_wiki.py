import json
import time
import urllib.parse
import urllib.request

with open("tests/lookup_chunk040.py", "r", encoding="utf-8") as f:
    src = f.read()

# Extract SETTLEMENTS from existing script
ns = {}
exec(src.split("def api_get")[0], ns)
SETTLEMENTS = ns["SETTLEMENTS"]

def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SVEA-Toponymy-Verifier/1.0 (https://confoederatio.org)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

# 1. Batch direct title lookup on es.wikipedia (20 at a time)
titles_found = {}
names = list({s["n"] for s in SETTLEMENTS})
for i in range(0, len(names), 20):
    batch = names[i:i+20]
    q = "|".join(batch)
    u = f"https://es.wikipedia.org/w/api.php?action=query&redirects=1&prop=extracts|coordinates&exintro=1&explaintext=1&titles={urllib.parse.quote(q)}&format=json"
    try:
        data = api_get(u)
        pages = data.get("query", {}).get("pages", {})
        for pid, p in pages.items():
            if int(pid) > 0:
                titles_found[p["title"]] = {
                    "coords": p.get("coordinates", []),
                    "extract": p.get("extract", "")[:1200]
                }
        time.sleep(0.3)
    except Exception as e:
        print("Batch err:", e)

with open("tests/chunk040_batch_es.json", "w", encoding="utf-8") as f:
    json.dump(titles_found, f, ensure_ascii=False, indent=2)
print("Direct hits:", len(titles_found))
