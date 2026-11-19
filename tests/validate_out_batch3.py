import json
import os

INPUT_PATH = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\tier2_batch_3.json'
OUTPUT_PATH = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\out_tier2_batch_3.json'

with open(INPUT_PATH, 'r', encoding='utf-8') as f:
    in_data = json.load(f)

with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
    out_data = json.load(f)

print(f"Input clusters: {len(in_data)}")
print(f"Output clusters: {len(out_data)}")

assert len(in_data) == len(out_data) == 130, f"Length mismatch: {len(in_data)} vs {len(out_data)}"

in_cids = [c['cluster_id'] for c in in_data]
out_cids = [c['cluster_id'] for c in out_data]
assert in_cids == out_cids, "Cluster IDs order/content mismatch!"

in_map = {c['cluster_id']: c for c in in_data}

total_actions = 0
op_counts = {}

for idx, rec in enumerate(out_data):
    cid = rec.get('cluster_id')
    assert cid in in_map, f"Unknown cluster_id {cid}"
    orig = in_map[cid]
    orig_keys = {n['key'] for n in orig['nodes']}
    
    actions = rec.get('actions', [])
    clean_names = rec.get('clean_names', {})
    
    assert isinstance(actions, list), f"actions not a list in {cid}"
    assert isinstance(clean_names, dict), f"clean_names not a dict in {cid}"
    
    dropped = set()
    merged = set()
    renamed = {}
    
    for act in actions:
        total_actions += 1
        op = act.get('op')
        op_counts[op] = op_counts.get(op, 0) + 1
        reason = act.get('reason', '')
        assert len(reason) > 5, f"Short reason in {cid}: {act}"
        
        if op == 'DROP_JUNK':
            k = act.get('key')
            assert k in orig_keys, f"Dropped key {k} not in cluster {cid}"
            dropped.add(k)
        elif op == 'RENAME_META':
            k = act.get('key')
            nn = act.get('new_name')
            assert k in orig_keys, f"Renamed key {k} not in cluster {cid}"
            assert nn and isinstance(nn, str), f"Invalid new_name in {cid}: {act}"
            renamed[k] = nn
        elif op == 'MERGE':
            sk = act.get('source_key')
            tk = act.get('target_key')
            assert sk in orig_keys, f"Merge source {sk} not in cluster {cid}"
            assert tk in orig_keys, f"Merge target {tk} not in cluster {cid}"
            merged.add(sk)
        else:
            raise AssertionError(f"Unknown op: {op} in {cid}")
            
    surviving = orig_keys - dropped - merged
    assert set(clean_names.keys()) == surviving, f"Surviving keys mismatch in {cid}: {set(clean_names.keys())} vs {surviving}"
    
    # Check that any renamed key matches clean_names
    for rk, rnn in renamed.items():
        if rk in surviving:
            assert clean_names[rk] == rnn, f"Renamed name mismatch for {rk} in {cid}: {clean_names[rk]} vs {rnn}"
            
    # Check for duplicate clean names within cluster
    names = list(clean_names.values())
    assert len(names) == len(set(names)), f"Duplicate clean name in {cid}: {names}"

print("ALL VALIDATION CHECKS PASSED PERFECTLY!")
print(f"Total clusters: {len(out_data)}")
print(f"Total actions: {total_actions}")
print(f"Action breakdown: {op_counts}")
