import json
import sys

def validate_dict(dec_dict, clusters_map):
    for cid, dec in dec_dict.items():
        assert cid in clusters_map, f"Cluster {cid} not in input clusters"
        c = clusters_map[cid]
        all_keys = {n["key"] for n in c["nodes"]}
        merged_sources = set()
        dropped = set()
        for act in dec.get("actions", []):
            op = act["op"]
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
            else:
                raise ValueError(f"Unknown op {op} in {cid}")
        
        expected_surviving = all_keys - merged_sources - dropped
        actual_surviving = set(dec.get("clean_names", {}).keys())
        assert expected_surviving == actual_surviving, (
            f"Cluster {cid} surviving keys mismatch!\n"
            f"Expected: {expected_surviving}\n"
            f"Actual:   {actual_surviving}"
        )
        
        # Check duplicate clean_names
        clean_names = dec.get("clean_names", {})
        homonym_keys = {act["key"] for act in dec.get("actions", []) if act["op"] == "KEEP_HOMONYM"}
        seen_names = {}
        for k, name in clean_names.items():
            if name in seen_names and k not in homonym_keys and seen_names[name] not in homonym_keys:
                raise ValueError(f"Duplicate clean name '{name}' in {cid} between {k} and {seen_names[name]}")
            seen_names[name] = k
    print(f"Validated {len(dec_dict)} clusters successfully!")

if __name__ == "__main__":
    with open(r"f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\tier1_batch_1.json", "r", encoding="utf-8") as f:
        clusters_map = {c["cluster_id"]: c for c in json.load(f)}
    
    mod_name = sys.argv[1] if len(sys.argv) > 1 else "part_a"
    mod = __import__(mod_name)
    var_name = dir(mod)[-1]
    for name in dir(mod):
        if name.startswith("PART_"):
            var_name = name
            break
    dec_dict = getattr(mod, var_name)
    validate_dict(dec_dict, clusters_map)
