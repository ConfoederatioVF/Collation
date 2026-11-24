import json
import sys
import urllib.parse

start = int(sys.argv[1])
end = int(sys.argv[2])

setts = json.load(open("tests/settlements_045.json", encoding="utf-8"))
wiki = json.load(open("tests/chunk045_wiki.json", encoding="utf-8"))
pages = json.load(open("tests/chunk045_pages.json", encoding="utf-8"))
wd = json.load(open("tests/chunk045_wd.json", encoding="utf-8"))

es_p = pages.get("es_pages", {})
en_p = pages.get("en_pages", {})
matched = pages.get("matched", {})

def url_to_title(url):
    if not url:
        return None
    t = urllib.parse.unquote(url.split("/wiki/")[-1]).replace("_", " ")
    return t

for idx, s in enumerate(setts[start:end], start):
    k = s["key"]
    w = wiki.get(k, {})
    m = matched.get(k, [])
    print(f"=== [{idx}] {k} | c={s['c']} | r={s['r']} | ll={s['ll']} | ey={s['ey']} | ly={s['ly']} | al={s.get('al')} | ex={s.get('ex')} ===")
    seen_es = set()
    seen_en = set()
    if w.get("page_es"):
        t = w["page_es"].get("title")
        seen_es.add(t)
        ex = (w["page_es"].get("extract") or "").replace("\n", " ")[:1200]
        print(f"  ES ({t}): {ex}")
    if w.get("page_en"):
        t = w["page_en"].get("title")
        seen_en.add(t)
        ex = (w["page_en"].get("extract") or "").replace("\n", " ")[:800]
        print(f"  EN ({t}): {ex}")
    for item in (m if isinstance(m, list) else []):
        if not isinstance(item, dict):
            continue
        es_t = url_to_title(item.get("es"))
        en_t = url_to_title(item.get("en"))
        if es_t and es_t not in seen_es and es_t in es_p:
            seen_es.add(es_t)
            txt = (es_p[es_t].get("extract") or "").replace("\n", " ")[:1200]
            print(f"  ES_M ({es_t}): {txt}")
        if en_t and en_t not in seen_en and en_t in en_p:
            seen_en.add(en_t)
            txt = (en_p[en_t].get("extract") or "").replace("\n", " ")[:800]
            print(f"  EN_M ({en_t}): {txt}")
    if not seen_es and not seen_en:
        wd_items = wd.get(k, [])
        print("  NO_WIKI_MATCH. WD:", [(x.get("label"), x.get("desc"), x.get("inception")) for x in wd_items[:4]])
