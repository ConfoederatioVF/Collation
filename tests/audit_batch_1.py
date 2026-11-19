import json

with open('f:/Active Projects/Project 1509 - SVEA/tests/polaris_batches/tier1_batch_1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total clusters: {len(data)}")

with open('f:/Active Projects/Project 1509 - SVEA/tests/cluster_summary_batch1.txt', 'w', encoding='utf-8') as out:
    for i, c in enumerate(data):
        cid = c['cluster_id']
        out.write(f"=== [{i+1}/{len(data)}] Cluster {cid} (dist: {c.get('min_dist_km')}..{c.get('max_dist_km')} km) ===\n")
        out.write(f"Reasons: {c.get('reasons')}\n")
        for n in c['nodes']:
            meta_entries = n.get('meta') or []
            meta_str = []
            for m in meta_entries:
                if isinstance(m, dict):
                    meta_str.append(f"{m.get('name')} (pop={m.get('pop')}, y={m.get('pop_year')})")
            other_names = n.get('other_names') or []
            sources = n.get('sources') or []
            out.write(f"  * Node: {n['key']}\n")
            out.write(f"    raw_name: '{n.get('raw_name')}' | country: {n.get('country')} | coords: {n.get('coords')}\n")
            out.write(f"    years: {n.get('min_y')}..{n.get('max_y')} | peak: {n.get('peak')}\n")
            if meta_str:
                out.write(f"    meta: {', '.join(meta_str)}\n")
            if other_names:
                out.write(f"    other_names: {other_names[:5]}\n")
            if sources:
                out.write(f"    sources: {sources[:5]}\n")
        out.write("\n")

print("Summary written to tests/cluster_summary_batch1.txt")
