import json
import sys

with open('f:/Active Projects/Project 1509 - SVEA/tests/polaris_batches/tier1_batch_1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
count = int(sys.argv[2]) if len(sys.argv) > 2 else 15

for i in range(start, min(start + count, len(data))):
    c = data[i]
    cid = c['cluster_id']
    nodes = c['nodes']
    print(f"\n[{i+1}/{len(data)}] Cluster {cid} ({len(nodes)} nodes, dist: {c.get('min_dist_km')}..{c.get('max_dist_km')} km)")
    print(f"Reasons: {c.get('reasons')}")
    for n in nodes:
        m_names = [m.get('name') for m in (n.get('meta') or []) if isinstance(m, dict)]
        print(f"  * {n['key']}")
        print(f"    raw='{n.get('raw_name')}' | country={n.get('country')} | yrs={n.get('min_y')}..{n.get('max_y')} | peak={n.get('peak')} | coords={n.get('coords')}")
        if m_names:
            print(f"    meta={m_names}")
        if n.get('other_names'):
            print(f"    other={n.get('other_names')[:4]}")
