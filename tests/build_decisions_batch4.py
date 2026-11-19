import json

with open(r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\tier2_batch_4.json', 'r', encoding='utf-8') as f:
    clusters = json.load(f)

print(f"Loaded {len(clusters)} clusters.")
