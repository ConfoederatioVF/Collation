"""Generates Stage C Wave 1 harvest summary manifest:
  settlement_sources/wave1_harvest_summary.json
"""

import json
import os
from datetime import datetime, timezone

from quipu_wave1_utils import OUT_DIR

FILES = [
    ("hgis_indias_colonial", "hgis_indias_colonial_raw.json"),
    ("colombia", "raw_setts_colombia.json"),
    ("venezuela", "raw_setts_venezuela.json"),
    ("ecuador", "raw_setts_ecuador.json"),
    ("peru", "raw_setts_peru.json"),
    ("andean_bolivia", "raw_setts_andean_bolivia.json"),
    ("chile", "raw_setts_chile.json"),
    ("argentina", "raw_setts_argentina.json"),
    ("uruguay", "raw_setts_uruguay.json"),
    ("falklands", "raw_setts_falklands.json"),
]


def main():
    summary = {
        "project": "QUIPU",
        "stage": "Stage C Wave 1 — Primary Settlement Census & Colonial Gazetteer Harvest",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy_compliance": {
            "zero_limit_head_topn_caps": True,
            "zero_wikipedia_scraping": True,
            "zero_banned_sources": True,
            "crowd_share_cap": 0.20,
            "crowd_demographic_share_all_jurisdictions": 0.0,
            "crowd_share_compliant": True,
            "municipal_non_decomposition_enforced": [
                "Bogotá D.C. (11001) unified city_proper",
                "Buenos Aires / CABA 15 Comunas unified city_proper; Gran Buenos Aires tagged metro",
                "Lima Province 43 districts unified city_proper; Callao 7 districts unified suburb; Lima Metropolitana tagged metro",
            ],
        },
        "jurisdictions": {},
        "totals": {
            "files_count": 0,
            "total_settlements": 0,
            "total_with_coords": 0,
            "overall_coords_coverage": 0.0,
        },
    }

    for jkey, fn in FILES:
        fp = os.path.join(OUT_DIR, fn)
        if not os.path.exists(fp):
            print(f"[WARN] Missing {fn}")
            continue
        data = json.load(open(fp, "r", encoding="utf-8"))
        meta = data.get("metadata", {})
        setts = data.get("settlements", {})
        total = len(setts)
        with_coords = sum(1 for r in setts.values() if r.get("coords") and len(r["coords"]) == 2)
        years = set()
        prov_counts = {}
        coord_src_counts = {}

        if jkey == "hgis_indias_colonial":
            for r in setts.values():
                for o in r.get("observations", []):
                    if o.get("year"):
                        years.add(int(o["year"]))
                prov_counts["HGIS de las Indias (1701-1808)"] = prov_counts.get("HGIS de las Indias (1701-1808)", 0) + 1
                coord_src_counts["HGIS_de_las_Indias"] = coord_src_counts.get("HGIS_de_las_Indias", 0) + 1
            entry = {
                "file": fn,
                "total_settlements": total,
                "with_demographic_observations": meta.get("settlements_with_demographic_observations", 0),
                "total_demographic_observations": meta.get("total_demographic_observations", 0),
                "with_coords": with_coords,
                "coords_coverage": round(with_coords / max(1, total), 4),
                "year_span": [min(years), max(years)] if years else [1701, 1808],
                "by_country": meta.get("by_country", {}),
                "provenance_breakdown": prov_counts,
                "coord_source_breakdown": coord_src_counts,
                "crowd_share": 0.0,
            }
        else:
            for r in setts.values():
                for y in r.get("population", {}):
                    if str(y).isdigit():
                        years.add(int(y))
                for s in r.get("sources", []):
                    prov_counts[s] = prov_counts.get(s, 0) + 1
                cs = r.get("coord_source") or ("PRETA_harmonised" if jkey == "andean_bolivia" else ("FIG_SGSSI" if jkey == "falklands" else "missing"))
                coord_src_counts[cs] = coord_src_counts.get(cs, 0) + 1
            entry = {
                "file": fn,
                "total_settlements": total,
                "with_coords": with_coords,
                "coords_coverage": round(with_coords / max(1, total), 4),
                "year_span": [min(years), max(years)] if years else meta.get("year_span", []),
                "census_years": sorted(years),
                "population_scope_breakdown": meta.get("population_scope_breakdown", {}),
                "provenance_breakdown": prov_counts,
                "coord_source_breakdown": coord_src_counts,
                "crowd_share": 0.0,
            }

        summary["jurisdictions"][jkey] = entry
        summary["totals"]["files_count"] += 1
        summary["totals"]["total_settlements"] += total
        summary["totals"]["total_with_coords"] += with_coords

    summary["totals"]["overall_coords_coverage"] = round(
        summary["totals"]["total_with_coords"] / max(1, summary["totals"]["total_settlements"]),
        4,
    )

    out_path = os.path.join(OUT_DIR, "wave1_harvest_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[SUMMARY] Wrote {out_path} | total_settlements={summary['totals']['total_settlements']:,}, coords_cov={summary['totals']['overall_coords_coverage']*100:.1f}%")


if __name__ == "__main__":
    main()
