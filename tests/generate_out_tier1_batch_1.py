import json
import os
import sys

# Ensure tests/ directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from part_a import PART_A
from part_b import PART_B
from part_c import PART_C
from part_d import PART_D

INPUT_PATH = r"f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\tier1_batch_1.json"
OUTPUT_PATH = r"f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\out_tier1_batch_1.json"

with open(INPUT_PATH, "r", encoding="utf-8") as f:
    input_clusters = json.load(f)

all_decisions = {}
for p in [PART_A, PART_B, PART_C, PART_D]:
    for cid, dec in p.items():
        assert cid not in all_decisions, f"Duplicate cluster decision: {cid}"
        all_decisions[cid] = dec

assert len(all_decisions) == len(input_clusters), f"Count mismatch: {len(all_decisions)} vs {len(input_clusters)}"

output_data = []
counts = {"MERGE": 0, "DROP_JUNK": 0, "RENAME_META": 0, "KEEP_HOMONYM": 0}

for c in input_clusters:
    cid = c["cluster_id"]
    assert cid in all_decisions, f"Missing cluster {cid} in decisions"
    dec = all_decisions[cid]
    
    all_keys = {n["key"] for n in c["nodes"]}
    merged_sources = set()
    dropped = set()
    
    for act in dec["actions"]:
        op = act["op"]
        assert op in counts, f"Unknown op: {op}"
        counts[op] += 1
        if op == "MERGE":
            sk, tk = act["source_key"], act["target_key"]
            assert sk in all_keys, f"In {cid}, MERGE source {sk} not in cluster"
            assert tk in all_keys, f"In {cid}, MERGE target {tk} not in cluster"
            assert sk != tk, f"In {cid}, self-merge {sk}"
            merged_sources.add(sk)
        elif op == "DROP_JUNK":
            k = act["key"]
            assert k in all_keys, f"In {cid}, DROP_JUNK key {k} not in cluster"
            dropped.add(k)
        elif op in ("RENAME_META", "KEEP_HOMONYM"):
            k = act["key"]
            assert k in all_keys, f"In {cid}, {op} key {k} not in cluster"
            
    expected_surviving = all_keys - merged_sources - dropped
    actual_surviving = set(dec["clean_names"].keys())
    assert expected_surviving == actual_surviving, (
        f"Cluster {cid} surviving mismatch: expected {expected_surviving}, got {actual_surviving}"
    )
    
    homonym_keys = {act["key"] for act in dec["actions"] if act["op"] == "KEEP_HOMONYM"}
    seen_names = {}
    for k, name in dec["clean_names"].items():
        if name in seen_names and k not in homonym_keys and seen_names[name] not in homonym_keys:
            raise ValueError(f"Duplicate clean name '{name}' in {cid} between {k} and {seen_names[name]}")
        seen_names[name] = k
        
    output_data.append({
        "cluster_id": cid,
        "actions": dec["actions"],
        "clean_names": dec["clean_names"]
    })

print(f"Total clusters processed: {len(output_data)}")
print(f"Action counts: {counts}")

# Write output file
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f"Successfully written {OUTPUT_PATH}")
