import json
import sys

inp_path = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\tier2_batch_1.json'
out_path = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\out_tier2_batch_1.json'

with open(inp_path, 'r', encoding='utf-8') as f:
    inp = json.load(f)

with open(out_path, 'r', encoding='utf-8') as f:
    out = json.load(f)

print(f"Input clusters: {len(inp)}")
print(f"Output clusters: {len(out)}")

assert len(inp) == len(out), f"Count mismatch: {len(inp)} vs {len(out)}"

inp_map = {c['cluster_id']: c for c in inp}
out_map = {c['cluster_id']: c for c in out}

assert len(inp_map) == len(inp), "Duplicate cluster_ids in input"
assert len(out_map) == len(out), "Duplicate cluster_ids in output"

stats = {
    'total_clusters': len(out),
    'DROP_JUNK': 0,
    'RENAME_META': 0,
    'MERGE': 0,
    'total_surviving_nodes': 0
}

errors = []

for idx, (c_in, c_out) in enumerate(zip(inp, out)):
    cid = c_in['cluster_id']
    if cid != c_out['cluster_id']:
        errors.append(f"Cluster order mismatch at index {idx}: {cid} vs {c_out['cluster_id']}")
    
    in_keys = {n['key'] for n in c_in['nodes']}
    actions = c_out.get('actions', [])
    clean_names = c_out.get('clean_names', {})
    
    dropped_keys = set()
    merge_sources = set()
    renamed_keys = {}
    
    for a in actions:
        op = a.get('op')
        if op == 'DROP_JUNK':
            k = a.get('key')
            if k not in in_keys:
                errors.append(f"[{cid}] DROP_JUNK key '{k}' not in cluster nodes")
            dropped_keys.add(k)
            stats['DROP_JUNK'] += 1
        elif op == 'MERGE':
            sk = a.get('source_key')
            tk = a.get('target_key')
            if sk not in in_keys or tk not in in_keys:
                errors.append(f"[{cid}] MERGE keys '{sk}' -> '{tk}' not in cluster nodes")
            merge_sources.add(sk)
            stats['MERGE'] += 1
        elif op == 'RENAME_META':
            k = a.get('key')
            nn = a.get('new_name')
            if k not in in_keys:
                errors.append(f"[{cid}] RENAME_META key '{k}' not in cluster nodes")
            renamed_keys[k] = nn
            stats['RENAME_META'] += 1
        else:
            errors.append(f"[{cid}] Unknown op '{op}'")
            
    # Check dropped not in clean_names
    for dk in dropped_keys:
        if dk in clean_names:
            errors.append(f"[{cid}] Dropped key '{dk}' found in clean_names")
            
    # Check merge source not in clean_names
    for sk in merge_sources:
        if sk in clean_names:
            errors.append(f"[{cid}] Merge source '{sk}' found in clean_names")
            
    # Check expected surviving nodes
    expected_surviving = in_keys - dropped_keys - merge_sources
    actual_surviving = set(clean_names.keys())
    
    if expected_surviving != actual_surviving:
        errors.append(f"[{cid}] Surviving keys mismatch! Expected {expected_surviving}, got {actual_surviving}")
        
    stats['total_surviving_nodes'] += len(clean_names)
    
    # Check that rename matches clean_names
    for k, nn in renamed_keys.items():
        if k in clean_names and clean_names[k] != nn:
            errors.append(f"[{cid}] RENAME_META name '{nn}' != clean_names['{k}'] '{clean_names[k]}'")
            
    # Check duplicate clean_names
    names_seen = {}
    for k, name in clean_names.items():
        if name in names_seen:
            errors.append(f"[{cid}] Duplicate clean name '{name}' between '{k}' and '{names_seen[name]}'")
        names_seen[name] = k

if errors:
    print(f"Validation FAILED with {len(errors)} errors:")
    for e in errors[:20]:
        print("  -", e)
    sys.exit(1)
else:
    print("ALL VALIDATION CHECKS PASSED!")
    print(f"Statistics: {stats}")
