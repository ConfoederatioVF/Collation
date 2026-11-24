import json, glob, os
from collections import Counter

bdir = r"f:\Active Projects\Project 1509 - SVEA\tests\toponymy_batches\austral"
items = []
for p in sorted(glob.glob(os.path.join(bdir, "batch_*.json"))):
  d = json.load(open(p, encoding="utf-8"))
  items.extend(d.get("settlements", []))

print("Total candidates:", len(items))
print("By reason:", Counter(it.get("reason") for it in items))
print("Capitals:", sum(1 for it in items if it.get("is_capital")))
print("max_pop >= 10000:", sum(1 for it in items if (it.get("max_pop") or 0) >= 10000))
print("max_pop >= 5000:", sum(1 for it in items if (it.get("max_pop") or 0) >= 5000))
print("earliest_year < 1850:", sum(1 for it in items if (it.get("earliest_year") or 9999) < 1850))
print("earliest_year < 1900:", sum(1 for it in items if (it.get("earliest_year") or 9999) < 1900))
print("earliest_year < 1950:", sum(1 for it in items if (it.get("earliest_year") or 9999) < 1950))
print("By country (top 15):", Counter(it.get("country") for it in items).most_common(15))
print("Sample first 10:", [(it["key"], it["reason"], it["earliest_year"], it["max_pop"], it["is_capital"]) for it in items[:10]])
