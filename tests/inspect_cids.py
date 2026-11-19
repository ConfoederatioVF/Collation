import json
import sys

with open('f:/Active Projects/Project 1509 - SVEA/tests/polaris_batches/tier1_batch_1.json', 'r', encoding='utf-8') as f:
    clusters = json.load(f)

c_dict = {c['cluster_id']: c for c in clusters}
cids = sys.argv[1:] if len(sys.argv) > 1 else list(c_dict.keys())[:10]

for cid in cids:
    if cid not in c_dict:
        continue
    c = c_dict[cid]
    print(f"=== {cid} ({len(c['nodes'])} nodes, dist: {c.get('min_dist_km')}..{c.get('max_dist_km')}) reasons={c.get('reasons')} ===")
    for n in c['nodes']:
        m = [x.get('name') for x in (n.get('meta') or []) if isinstance(x, dict)]
        print(f"  * {n['key']} | raw='{n.get('raw_name')}' | yrs={n.get('min_y')}..{n.get('max_y')} | pk={n.get('peak')} | coords={n.get('coords')}")
        if m:
            print(f"    meta={m}")
        if n.get('other_names'):
            print(f"    other={n.get('other_names')[:3]}")
