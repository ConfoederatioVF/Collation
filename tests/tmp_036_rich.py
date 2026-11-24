import json
import re
import time
import urllib.parse
import urllib.request

data = json.load(open("tests/tmp_036_data.json", encoding="utf-8"))
wd = json.load(open("tests/tmp_036_wd.json", encoding="utf-8"))
UA = "ViscountHistoricalResearch/1.0 (mailto:research@confoederatio.org)"

def fetch_extracts(lang, titles):
    titles = sorted(set(t for t in titles if t))
    out = {}
    for i in range(0, len(titles), 10):
        batch = titles[i:i+10]
        params = {
            "action": "query",
            "prop": "extracts",
            "explaintext": "1",
            "exlimit": "max",
            "titles": "|".join(batch),
            "format": "json"
        }
        url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                for pid, p in res.get("query", {}).get("pages", {}).items():
                    if int(pid) > 0 and p.get("extract"):
                        out[p["title"]] = p["extract"]
        except Exception as e:
            print(f"{lang} batch {i}: {e}")
        time.sleep(0.3)
    return out

es_titles = set()
en_titles = set()
item_titles = {}

for d in data:
    k = d["key"]
    n_low = d["n"].lower()
    es_t = []
    en_t = []
    for g in d.get("es_geo", [])[:2]:
        es_t.append(g["title"])
    for s in d.get("es_search", [])[:2]:
        if s["title"] not in es_t:
            # only add if name or country relates
            es_t.append(s["title"])
    for r in wd.get(k, []):
        if r.get("esTitle") and r["esTitle"] not in es_t:
            es_t.append(r["esTitle"])
        if r.get("enTitle") and r["enTitle"] not in en_t:
            en_t.append(r["enTitle"])
    item_titles[k] = {"es": es_t[:4], "en": en_t[:3]}
    es_titles.update(es_t[:4])
    en_titles.update(en_t[:3])

print(f"Fetching {len(es_titles)} eswiki and {len(en_titles)} enwiki full extracts...")
es_ext = fetch_extracts("es", es_titles)
en_ext = fetch_extracts("en", en_titles)

# Write clean compact summary per settlement (focusing on intro + Historia/Toponimia/Fundacion + local arch/hist notes)
out_lines = []
for idx, d in enumerate(data):
    k = d["key"]
    out_lines.append(f"=== [{idx}] {k} | n={d['n']} | c={d['c']} | r={d['r']} | ll={d['ll']} | ey={d['ey']} | ly={d['ly']} | al={d['al']} ===")
    for r in wd.get(k, [])[:3]:
        out_lines.append(f"  WD: {r['qid']} '{r['label']}' ({r['dist']}km) inc={r['inception']} desc={r['desc']} es={r['esTitle']} en={r['enTitle']}")
    # relevant local non-noisy hits
    for l in d.get("local", []):
        if "nso_argentina" not in l and "ine_ven_ccpp" not in l and "peru_censos_2007" not in l:
            out_lines.append(f"  LOC: {l[:220]}")
    for t in item_titles[k]["es"]:
        txt = es_ext.get(t, "")
        if txt:
            # extract intro + any Historia/Toponimia/Fundación/Origen/Etimología/Reseña
            parts = re.split(r"\n(==+[^=]+==+)\n", txt)
            selected = [parts[0][:700].replace("\n", " ")]
            for j in range(1, len(parts)-1, 2):
                hdr = parts[j].lower()
                if any(w in hdr for w in ["histor", "toponim", "etimolog", "fundac", "origen", "nombre", "reseña", "arqueol", "anteced", "creaci"]):
                    selected.append(f"[{parts[j].strip()}] {parts[j+1][:900].replace(chr(10), ' ')}")
            out_lines.append(f"  ES[{t}]: " + " | ".join(selected))
    for t in item_titles[k]["en"]:
        txt = en_ext.get(t, "")
        if txt:
            parts = re.split(r"\n(==+[^=]+==+)\n", txt)
            selected = [parts[0][:500].replace("\n", " ")]
            for j in range(1, len(parts)-1, 2):
                hdr = parts[j].lower()
                if any(w in hdr for w in ["histor", "etymolog", "topon", "found", "name", "origin", "arch"]):
                    selected.append(f"[{parts[j].strip()}] {parts[j+1][:600].replace(chr(10), ' ')}")
            out_lines.append(f"  EN[{t}]: " + " | ".join(selected))

# split into 3 files of 30 settlements each
text_all = "\n".join(out_lines)
blocks = text_all.split("\n=== [")
header_blocks = [blocks[0]] + ["=== [" + b for b in blocks[1:]]
for c_i in range(3):
    with open(f"tests/tmp_036_rich{c_i}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(header_blocks[c_i*30:(c_i+1)*30]))
print("Wrote rich0, rich1, rich2")
