import json, math

research = json.load(open("tests/chunk026_research.json", encoding="utf-8"))
local_arch = json.load(open("tests/chunk026_local.json", encoding="utf-8"))
setts = json.load(open("tests/chunk026_setts.json", encoding="utf-8"))

print("research len:", len(research))
has_ex = sum(1 for r in research if r.get("extracts"))
print("research with extracts:", has_ex)

# Summarize items 39..90 from research + local_arch + setts
for i, r in enumerate(research):
    k = r["key"]
    loc = local_arch.get(k, [])
    st = setts.get(k, [])
    ex_titles = list(r.get("extracts", {}).keys())
    if i >= 38 or not ex_titles:
        print(f"{i+1}. {k} | n={r['n']} | c={r['c']} | r={r['r']} | ey={r['ey']} | ly={r['ly']}")
        if ex_titles:
            for t, txt in r["extracts"].items():
                print(f"   EXT[{t}]: {txt.replace(chr(10), ' ')[:300]}")
        if r.get("geo_es"):
            print("   GEO:", "; ".join(f"{g['title']}({g['dist']}m)" for g in r["geo_es"][:4]))
        if r.get("search_es"):
            print("   SRCH:", "; ".join(f"{s['title']}" for s in r["search_es"][:3]))
        if loc:
            names = list(dict.fromkeys(x.get("name","") + " [" + str(x.get("period","")) + "|" + str(x.get("source",""))[:25] + "]" for x in loc))
            print("   LOC:", "; ".join(names[:4]))
        if st:
            print("   SETT:", "; ".join(f"{x.get('name')}({x.get('source','')})" for x in st[:4]))
