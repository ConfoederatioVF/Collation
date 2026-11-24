"""Generates `histmap/1.data_raw/population_regional/QUIPU/quipu_gazetteers.json5`
matching the canonical Operation Viscount manifest schema (with annual_continuity_span,
border_splice_years, chronology_targets, regime_transitions, geography_profile,
script_profile, and all 17 chapter gazetteers).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quipu_stage_c_utils import QUIPU_DIR, load_quipu_chapter_configs


def build_quipu_gazetteers_manifest():
    areal = json.load(open(os.path.join(QUIPU_DIR, "quipu_areal_masks.json5"), "r", encoding="utf-8"))
    cfgs = load_quipu_chapter_configs()

    gazetteers = []
    for ch in cfgs:
        j5 = json.load(open(ch["json5_path"], "r", encoding="utf-8"))
        gazetteers.append({
            "domain": ch["domain"],
            "itinerary_title": j5.get("title", ch["id"]),
            "key": ch["id"],
            "path": ch["settlements_rel_path"],
            "priority": ch["priority"],
            "region_group": ch["region_group"],
        })

    manifest = {
        "annual_continuity_span": [1876, 2025],
        "border_splice_years": [1883, 1903, 1938],
        "chronology_targets": {
            "pre_columbian": [-10000, 1532],
            "colonial": [1525, 1830],
            "post_independence": [1810, 2026],
            "modern_census_baseline": 1876,
            "annual_continuity": [1876, 2025],
        },
        "regime_transitions": areal["regime_transitions"],
        "geography_profile": areal["geography_profile"],
        "script_profile": areal["script_profile"],
        "gazetteers": gazetteers,
    }

    out_path = os.path.join(QUIPU_DIR, "quipu_gazetteers.json5")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[MANIFEST] Wrote {out_path} with {len(gazetteers)} chapter gazetteers.")


if __name__ == "__main__":
    build_quipu_gazetteers_manifest()
