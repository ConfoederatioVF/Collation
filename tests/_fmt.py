import json, sys
sys.path.append("tests")
d = json.load(open("tests/_chunk_019_research.json", encoding="utf-8"))
from research_chunk_019 import INPUT_DATA
for part, (a, b) in enumerate([(0,30),(30,60),(60,90)], 1):
  with open(f"tests/_c19_p{part}.txt", "w", encoding="utf-8") as f:
    for idx, item in enumerate(INPUT_DATA[a:b], a+1):
      k = item["key"]
      f.write(f"=== {idx}. {k} | n={item['n']} | c={item['c']} | r={item['r']} | ll={item['ll']} | ey={item['ey']} | ly={item['ly']} | al={item.get('al',[])} | ex={item.get('ex',[])}\n")
      loc = d["local"].get(k, [])
      for l in loc[:4]:
        f.write("  LOCAL[" + str(l.get("_file")) + "]: " + json.dumps({kk:vv for kk,vv in l.items() if kk!="_file"}, ensure_ascii=False)[:350] + "\n")
      w = d["wiki"].get(k, {})
      f.write("  GEO: " + str(w.get("es_geo", [])[:5]) + "\n")
      f.write("  SEARCH: " + str([x["title"] for x in w.get("es_search", [])[:4]]) + "\n")
      for t, ex in w.get("extracts", {}).items():
        clean = " ".join(ex.split())[:1000]
        f.write(f"  EX[{t}]: {clean}\n")
      f.write("\n")
print("WROTE 3 FILES")
