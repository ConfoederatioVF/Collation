import json

d = json.load(open("tests/chunk022_wiki.json", encoding="utf-8"))
for idx_start, fname in [(0, "tests/part1.txt"), (45, "tests/part2.txt")]:
    with open(fname, "w", encoding="utf-8") as f:
        for i, x in enumerate(d[idx_start:idx_start+45], idx_start):
            f.write(f"=== [{i}] {x['key']} | n={x['n']} | c={x['c']} | r={x['r']} | ll={x['ll']} | ey={x['ey']}..{x['ly']}\n")
            f.write(f"  geo={x['es_geo']}\n  sr={x['es_search']}\n")
            for t, ex in x["extracts"].items():
                f.write(f"  --- {t} ---\n  {ex[:900].replace(chr(10), ' ')}\n")
            f.write("\n")
print("Wrote part1.txt and part2.txt")
