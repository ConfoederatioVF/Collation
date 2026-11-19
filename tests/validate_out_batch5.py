import json

inp_path = 'f:/Active Projects/Project 1509 - SVEA/tests/polaris_batches/tier1_batch_5.json'
out_path = 'f:/Active Projects/Project 1509 - SVEA/tests/polaris_batches/out_tier1_batch_5.json'

raw_data = json.load(open(inp_path, encoding='utf-8'))
out_data = json.load(open(out_path, encoding='utf-8'))

print(f"Input clusters: {len(raw_data)}")
print(f"Output clusters: {len(out_data)}")
assert len(raw_data) == len(out_data), "Length mismatch!"

raw_map = {c['cluster_id']: c for c in raw_data}

counts = {"MERGE": 0, "DROP_JUNK": 0, "RENAME_META": 0, "KEEP_HOMONYM": 0}
errors = []

for i, out_c in enumerate(out_data):
    cid = out_c.get('cluster_id')
    if cid not in raw_map:
        errors.append(f"Cluster {cid} not in input!")
        continue
    
    raw_c = raw_map[cid]
    node_keys = set(n['key'] for n in raw_c['nodes'])
    
    actions = out_c.get('actions', [])
    if not actions:
        errors.append(f"Cluster {cid} has empty actions!")
    
    dropped_keys = set()
    has_homonym = False
    
    for act in actions:
        op = act.get('op')
        if op not in counts:
            errors.append(f"Cluster {cid} has invalid op: {op}")
            continue
        counts[op] += 1
        
        reason = act.get('reason', '')
        if not reason:
            errors.append(f"Cluster {cid} action {op} missing reason!")
            
        if op == 'MERGE':
            sk = act.get('source_key')
            tk = act.get('target_key')
            if sk not in node_keys:
                errors.append(f"Cluster {cid} MERGE source_key '{sk}' not in nodes!")
            if tk not in node_keys:
                errors.append(f"Cluster {cid} MERGE target_key '{tk}' not in nodes!")
            if sk == tk:
                errors.append(f"Cluster {cid} MERGE source_key equals target_key!")
            dropped_keys.add(sk)
            
        elif op == 'DROP_JUNK':
            k = act.get('key')
            if k not in node_keys:
                errors.append(f"Cluster {cid} DROP_JUNK key '{k}' not in nodes!")
            dropped_keys.add(k)
            
        elif op == 'RENAME_META':
            k = act.get('key')
            nn = act.get('new_name')
            if k not in node_keys:
                errors.append(f"Cluster {cid} RENAME_META key '{k}' not in nodes!")
            if not nn:
                errors.append(f"Cluster {cid} RENAME_META missing new_name!")
                
        elif op == 'KEEP_HOMONYM':
            k = act.get('key')
            if k not in node_keys:
                errors.append(f"Cluster {cid} KEEP_HOMONYM key '{k}' not in nodes!")
            has_homonym = True
            
    surviving_nodes = node_keys - dropped_keys
    clean_names = out_c.get('clean_names', {})
    
    if set(clean_names.keys()) != surviving_nodes:
        errors.append(f"Cluster {cid} clean_names keys {set(clean_names.keys())} != surviving {surviving_nodes}")
        
    for k, name in clean_names.items():
        if not name or not isinstance(name, str):
            errors.append(f"Cluster {cid} clean_name for '{k}' is empty or not string!")
            
    # Check duplicate clean_names
    vals = list(clean_names.values())
    if len(vals) != len(set(vals)) and not has_homonym:
        errors.append(f"Cluster {cid} has duplicate clean_names without KEEP_HOMONYM: {vals}")

if errors:
    print(f"FAILED with {len(errors)} errors:")
    for e in errors[:20]:
        print(" -", e)
else:
    print("ALL 104 CLUSTERS VALIDATED SUCCESSFULLY!")
    print("Action counts:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
