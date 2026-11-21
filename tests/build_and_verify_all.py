# -*- coding: utf-8 -*-
"""Master builder and validator for MANDALA toponymy batches 16-20."""

import json
import os
import re
import sys

# Import resolution dictionaries
from resolve_batch_16 import batch_16_resolutions
from resolve_batch_17 import batch_17_resolutions
from resolve_batch_18 import batch_18_resolutions
from resolve_batch_19 import batch_19_resolutions
from resolve_batch_20 import batch_20_resolutions

resolutions_map = {
    16: batch_16_resolutions,
    17: batch_17_resolutions,
    18: batch_18_resolutions,
    19: batch_19_resolutions,
    20: batch_20_resolutions
}

batch_dir = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\MANDALA\_shared\toponymy_batches"

date_regex = re.compile(r"^-?\d+\.\d+\.\d+$")

latin_only_countries = {
    "Indonesia", "Malaysia", "Singapore", "Brunei", "Philippines", "East Timor", "Timor-Leste"
}

def parse_date_tuple(d_str):
    parts = d_str.split(".")
    return int(parts[0]), int(parts[1]), int(parts[2])

def validate_settlement(s, country, key):
    # Rule 1: key exact match
    if s.get("key") != key:
        return f"Key mismatch: expected {key}, got {s.get('key')}"
    
    # Rule 2: canonical_name clean
    cname = s.get("canonical_name")
    if not cname or not isinstance(cname, str):
        return f"Invalid canonical_name for {key}: {cname}"
    if any(ch in cname for ch in ["(", ")", "`", "?"]):
        return f"Forbidden characters in canonical_name for {key}: {cname}"
    
    # Rule 3: foundation_year integer
    fyear = s.get("foundation_year")
    if not isinstance(fyear, int):
        return f"foundation_year not int for {key}: {fyear}"
        
    # Rule 4: historical_names
    hnames = s.get("historical_names")
    if not isinstance(hnames, list) or len(hnames) == 0:
        return f"historical_names empty or not list for {key}"
        
    last_dt = None
    for idx, h in enumerate(hnames):
        d = h.get("date")
        n = h.get("name")
        if not d or not date_regex.match(d):
            return f"Invalid date format '{d}' in {key}"
        if any(ch in n for ch in ["(", ")", "`", "?"]):
            return f"Forbidden characters in historical name '{n}' in {key}"
        cur_dt = parse_date_tuple(d)
        if last_dt is not None and cur_dt < last_dt:
            return f"Dates not chronological in {key}: {d} after previous"
        last_dt = cur_dt
        
    # Terminal check: must always match canonical_name
    last_h = hnames[-1]
    if last_h.get("name") != cname:
        return f"Terminal historical name '{last_h.get('name')}' != canonical_name '{cname}' for {key}"

    # Rule 5: other_names
    onames = s.get("other_names")
    if not isinstance(onames, list):
        return f"other_names not list for {key}"
        
    for on in onames:
        if any(ch in on for ch in ["`", "?"]):
            return f"Forbidden characters in other_name '{on}' for {key}"
        # If latin only country, check for non-latin characters
        if country in latin_only_countries:
            for ch in on:
                if ord(ch) > 0x024F and ord(ch) not in (0x2010, 0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x0027, 0x002D, 0x002E):
                    return f"Foreign non-latin script '{ch}' ({hex(ord(ch))}) found in {country} settlement '{on}' for {key}"
                    
    return None

all_errors = []

for b_idx in range(16, 21):
    in_file = os.path.join(batch_dir, f"batch_{b_idx}.json")
    out_file = os.path.join(batch_dir, f"resolved_batch_{b_idx}.json")
    
    with open(in_file, "r", encoding="utf-8") as f:
        in_data = json.load(f)
        
    input_settlements = in_data.get("settlements", [])
    resolved_res = resolutions_map[b_idx]
    
    out_settlements = []
    
    # Check 1-to-1 coverage
    for item in input_settlements:
        key = item["key"]
        country = item["country"]
        if key not in resolved_res:
            all_errors.append(f"Missing resolution for key: {key} in batch {b_idx}")
            continue
            
        r_info = resolved_res[key]
        resolved_item = {
            "key": key,
            "canonical_name": r_info["canonical_name"],
            "foundation_year": r_info["foundation_year"],
            "historical_names": r_info["historical_names"],
            "other_names": r_info["other_names"]
        }
        
        err = validate_settlement(resolved_item, country, key)
        if err:
            all_errors.append(f"Batch {b_idx} validation error: {err}")
            
        out_settlements.append(resolved_item)
        
    # Check if extra keys
    for k in resolved_res:
        if not any(it["key"] == k for it in input_settlements):
            all_errors.append(f"Extra key {k} in resolutions not in batch_{b_idx}.json")
            
    out_data = {
        "batch_index": b_idx,
        "settlements": out_settlements
    }
    
    with open(out_file, "w", encoding="utf-8") as f_out:
        json.dump(out_data, f_out, indent=2, ensure_ascii=False)
        
    print(f"Batch {b_idx}: processed and written {len(out_settlements)} settlements to {out_file}")

if all_errors:
    print(f"\nERRORS ENCOUNTERED ({len(all_errors)}):")
    for e in all_errors:
        print("  -", e)
    sys.exit(1)
else:
    print("\nSUCCESS: All batches 16-20 compiled and passed 100% strict verification!")
