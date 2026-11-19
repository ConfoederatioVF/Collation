import json

in_path = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\tier2_batch_4.json'
out_path = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\out_tier2_batch_4.json'

with open(in_path, 'r', encoding='utf-8') as f:
    in_data = json.load(f)

with open(out_path, 'r', encoding='utf-8') as f:
    out_data = json.load(f)

in_cids = [c['cluster_id'] for c in in_data]
out_cids = [c['cluster_id'] for c in out_data]

assert len(in_data) == len(out_data) == 127, f"Length mismatch: {len(in_data)} vs {len(out_data)}"
assert in_cids == out_cids, "Cluster IDs order/coverage mismatch!"

in_map = {c['cluster_id']: c for c in in_data}

counts = {
    "DROP_JUNK": 0,
    "RENAME_META": 0,
    "MERGE": 0
}

clusters_with_op = {
    "DROP_JUNK": 0,
    "RENAME_META": 0,
    "MERGE": 0
}

total_surviving_nodes = 0

for c in out_data:
    cid = c['cluster_id']
    in_c = in_map[cid]
    input_node_keys = {n['key'] for n in in_c['nodes']}
    
    actions = c['actions']
    assert isinstance(actions, list) and len(actions) > 0, f"{cid}: empty actions"
    
    clean_names = c['clean_names']
    assert isinstance(clean_names, dict) and len(clean_names) > 0, f"{cid}: empty clean_names"
    
    # Check duplicate clean_names
    names_list = list(clean_names.values())
    assert len(names_list) == len(set(names_list)), f"{cid}: duplicate clean names {names_list}"
    
    dropped_keys = set()
    ops_in_c = set()
    for act in actions:
        op = act['op']
        assert op in {"DROP_JUNK", "RENAME_META", "MERGE"}, f"{cid}: invalid op {op}"
        counts[op] += 1
        ops_in_c.add(op)
        
        if op == "DROP_JUNK":
            k = act['key']
            assert k in input_node_keys, f"{cid}: dropped key {k} not in input nodes"
            dropped_keys.add(k)
        elif op == "RENAME_META":
            k = act['key']
            assert k in input_node_keys, f"{cid}: renamed key {k} not in input nodes"
            assert isinstance(act['new_name'], str) and len(act['new_name'].strip()) > 0
        elif op == "MERGE":
            sk = act['source_key']
            tk = act['target_key']
            assert sk in input_node_keys and tk in input_node_keys
            dropped_keys.add(sk)
            
    for op in ops_in_c:
        clusters_with_op[op] += 1
        
    expected_surviving_keys = input_node_keys - dropped_keys
    assert set(clean_names.keys()) == expected_surviving_keys, f"{cid}: clean_names keys {set(clean_names.keys())} != expected {expected_surviving_keys}"
    total_surviving_nodes += len(clean_names)

print("VALIDATION PASSED PERFECTLY!")
print(f"Total clusters: {len(out_data)}")
print(f"Total action counts: {counts}")
print(f"Clusters with ops: {clusters_with_op}")
print(f"Total surviving nodes: {total_surviving_nodes}")
