import json

with open('f:/Active Projects/Project 1509 - SVEA/tests/polaris_batches/tier1_batch_1.json', 'r', encoding='utf-8') as f:
    clusters = json.load(f)

print(f"Total clusters: {len(clusters)}")
c_map = {c['cluster_id']: c for c in clusters}

# Print summary of all cluster IDs
print("Cluster IDs:")
for i in range(0, len(clusters), 10):
    batch = [c['cluster_id'] for c in clusters[i:i+10]]
    print(f"  {i+1:3d}-{min(i+10, len(clusters)):3d}: {', '.join(batch)}")
