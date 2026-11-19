import json

with open('tests/polaris_batches/tier2_batch_3.json', 'r', encoding='utf-8') as f:
    clusters = json.load(f)

print(f"Total clusters: {len(clusters)}")

# Let's verify cluster IDs
cluster_map = {c['cluster_id']: c for c in clusters}
assert len(cluster_map) == 130
