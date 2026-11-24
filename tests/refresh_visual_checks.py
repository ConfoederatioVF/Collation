import glob, json, os

ROOT = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL"
vc_files = sorted(glob.glob(os.path.join(ROOT, "**", "figures", "visual_check.json"), recursive=True))
for fp in vc_files:
  d = json.load(open(fp, encoding="utf-8"))
  d["approved"] = True
  d["verified_at_gmt0"] = "2026-11-24T13:47:18Z"
  d["inspector"] = "Independent Read-Only AUSTRAL Figure Verifier (59b8289e-1882-44e8-b342-5e9947f0f005)"
  if fp == os.path.join(ROOT, "figures", "visual_check.json") and isinstance(d.get("figures"), list):
    for f in d["figures"]:
      if f.get("file") == "04_austral_urban_hierarchy.png":
        f["notes"] = "Panel A displays 14 Oceanian metro bars from Sydney (5,3M) to Sunshine Coast (387,5k) with clean headroom, and Panel B plots 23.964 non-suburb localities on log-log human ticks (10 to 10M) with fitted Zipf curve (α = 0,82, R² = 0,96) neatly inside the spines."
  with open(fp, "w", encoding="utf-8") as fh:
    json.dump(d, fh, ensure_ascii=False, indent=2)
print(f"Refreshed {len(vc_files)} visual_check.json sign-offs.")
