import json, glob, math

with open('tests/chunk025_input.json', encoding='utf-8') as f:
    inp = json.load(f)

with open('tests/toponymy_batches/quipu_approved_cache.json', encoding='utf-8') as f:
    cache = json.load(f)

print("Approved cache count:", len(cache))

# Check if any input name (or ex name) matches keys in approved cache
for item in inp:
    n_low = item['n'].lower()
    ex_names = [e['name'].lower() for e in item.get('ex', [])]
    hits = []
    for ck, cv in cache.items():
        cn = cv.get('canonical_name', '').lower()
        if n_low in ck.lower() or any(en in ck.lower() for en in ex_names):
            hits.append((ck, cv))
    if hits:
        print(f"\n=== INPUT: {item['key']} (c={item['c']}, r={item['r']}, ll={item['ll']}) ===")
        for ck, cv in hits[:4]:
            print(f"  CACHE {ck}: {json.dumps(cv, ensure_ascii=False)}")
