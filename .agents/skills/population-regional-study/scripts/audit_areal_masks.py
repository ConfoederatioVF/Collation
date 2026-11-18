"""Gatekeeper A2: Audits Viscount regional areal masks across all 14 macro-regions for
ordered compositing survival, organic/GIS shape compliance (rejecting synthetic boxes),
chronological domain consistency, island/archipelago containment and overlay visual QA.
"""

import argparse
import glob
import json
import os
import re
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

try:
  import json5
except ImportError:
  json5 = None


def find_svea_root(arg0_start_path):
  """Locates SVEA root folder by walking parent directories."""
  cur = os.path.abspath(arg0_start_path or ".")
  if not os.path.isdir(cur):
    cur = os.path.dirname(cur)
  for _ in range(12):
    if os.path.isdir(os.path.join(cur, "histmap")) and os.path.isdir(os.path.join(cur, ".agents")):
      return cur
    parent = os.path.dirname(cur)
    if parent == cur:
      break
    cur = parent
  return None


def load_json_or_json5(arg0_path):
  """Loads JSON via stdlib first, falling back to json5 or stripped comments."""
  with open(arg0_path, "r", encoding="utf-8", errors="replace") as fh:
    text = fh.read()
  try:
    return json.loads(text)
  except (json.JSONDecodeError, ValueError):
    if json5 is not None:
      return json5.loads(text)
    cleaned = re.sub(r"//.*?$|/\*.*?\*/", "", text, flags=re.MULTILINE | re.DOTALL)
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    return json.loads(cleaned)


def load_skill_profiles(arg0_svea_root):
  """Loads config/viscount_skill_profiles.json5 relative to this script or SVEA root."""
  candidates = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config/viscount_skill_profiles.json5"),
  ]
  if arg0_svea_root:
    candidates.append(
      os.path.join(arg0_svea_root, ".agents/skills/population-regional-study/config/viscount_skill_profiles.json5")
    )
  for cand in candidates:
    if os.path.isfile(cand):
      return load_json_or_json5(cand)
  return {}


def resolve_project_key(arg0_target_path, arg1_svea_root):
  """Infers canonical Viscount project key from path or precedence manifest."""
  norm = os.path.abspath(arg0_target_path).replace("\\", "/")
  m = re.search(r"/population_regional/([A-Za-z0-9_]+)/", norm)
  if m:
    return m.group(1).upper()
  if arg1_svea_root:
    prec_p = os.path.join(arg1_svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5")
    if os.path.isfile(prec_p):
      prec = load_json_or_json5(prec_p)
      for p in prec.get("projects", []):
        k = str(p.get("key") or "").upper()
        if k and (f"/{k}/" in norm or f"/{k.lower()}" in norm.lower()):
          return k
  return None


def resolve_mask_manifest(arg0_target):
  """Resolves an areal-masks JSON5 manifest path from a project dir, file or single mask."""
  abs_p = os.path.abspath(arg0_target)
  if os.path.isfile(abs_p) and abs_p.lower().endswith(".json5"):
    return abs_p, "manifest"
  if os.path.isdir(abs_p):
    cands = sorted(glob.glob(os.path.join(abs_p, "*areal_masks*.json5")))
    if cands:
      return cands[0], "manifest"
    masks = sorted(glob.glob(os.path.join(abs_p, "*_areal_mask.png")))
    if masks:
      return masks[0], "single"
  if os.path.isfile(abs_p) and abs_p.lower().endswith("_areal_mask.png"):
    return abs_p, "single"
  return None, None


def render_overlay_png(arg0_mask_arr, arg1_settlements, arg2_in_mask, arg3_out_png, arg4_title):
  """Renders an equal-area/cos-lat overlay PNG of sub-masks and settlement points for read_file QA."""
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt

  plt.rcdefaults()
  plt.style.use("default")
  h, w = arg0_mask_arr.shape[:2]
  valid = (arg0_mask_arr[:, :, 3] > 0) & (arg0_mask_arr[:, :, :3].sum(axis=2) > 0)
  if not valid.any():
    return
  rs, cs = np.where(valid)
  r0, r1 = max(0, int(rs.min()) - 18), min(h, int(rs.max()) + 19)
  c0, c1 = max(0, int(cs.min()) - 24), min(w, int(cs.max()) + 25)
  lat_max = 90.0 - r0 * 180.0 / h
  lat_min = 90.0 - r1 * 180.0 / h
  lon_min = -180.0 + c0 * 360.0 / w
  lon_max = -180.0 + c1 * 360.0 / w
  mid_lat = 0.5 * (lat_min + lat_max)
  aspect = 1.0 / max(0.25, float(np.cos(np.radians(mid_lat))))

  fig, ax = plt.subplots(figsize=(10, 6), dpi=200)
  sub = arg0_mask_arr[r0:r1, c0:c1]
  ax.imshow(sub, extent=[lon_min, lon_max, lat_min, lat_max], origin="upper", interpolation="nearest", alpha=0.72)

  in_lats, in_lons, out_lats, out_lons = [], [], [], []
  for idx, entry in enumerate(arg1_settlements):
    coords = entry.get("coords")
    if not isinstance(coords, list) or len(coords) < 2:
      continue
    la, lo = float(coords[0]), float(coords[1])
    if arg2_in_mask[idx]:
      in_lats.append(la)
      in_lons.append(lo)
    else:
      out_lats.append(la)
      out_lons.append(lo)

  if in_lons:
    ax.scatter(in_lons, in_lats, s=8, c="#1f77b4", edgecolors="white", linewidths=0.3, label=f"Inside mask (n={len(in_lons)})")
  if out_lons:
    ax.scatter(out_lons, out_lats, s=16, c="#d62728", marker="x", linewidths=0.8, label=f"Outside belt (n={len(out_lons)})")
  ax.set_aspect(aspect)
  ax.set_xlim(lon_min, lon_max)
  ax.set_ylim(lat_min, lat_max)
  ax.set_title(arg4_title, fontsize=10)
  ax.legend(loc="best", frameon=True, fontsize=8)
  ax.grid(alpha=0.25)
  os.makedirs(os.path.dirname(arg3_out_png), exist_ok=True)
  fig.tight_layout()
  fig.savefig(arg3_out_png, dpi=200)
  plt.close(fig)


def audit_single_mask(arg0_mask_path, arg1_opts=None):
  """Audits one areal mask PNG + optional sibling JSON5 & settlements JSON."""
  opts = arg1_opts or {}
  has_micro_islands = bool(opts.get("has_micro_islands", False))
  errors, warnings = [], []
  if not os.path.isfile(arg0_mask_path):
    return [f"Missing mask PNG: {arg0_mask_path}"], warnings, {}

  arr = np.asarray(Image.open(arg0_mask_path).convert("RGBA"), dtype=np.uint8)
  valid = (arr[:, :, 3] > 0) & (arr[:, :, :3].sum(axis=2) > 0)
  active_px = int(valid.sum())
  if active_px == 0:
    return [f"Areal mask {os.path.basename(arg0_mask_path)} contains 0 active pixels."], warnings, {"active_px": 0}

  rs, cs = np.where(valid)
  bbox_area = int((int(rs.max()) - int(rs.min()) + 1) * (int(cs.max()) - int(cs.min()) + 1))
  bbox_fill = float(active_px) / max(1, bbox_area)
  is_micro_sheet = has_micro_islands and active_px < 1500
  is_admin1 = bool(opts.get("is_admin1", False))
  if active_px >= 100 and not is_micro_sheet and not is_admin1 and bbox_fill > 0.96:
    errors.append(
      f"[GEOMETRY] Mask {os.path.basename(arg0_mask_path)} has rectangular box fill ratio {bbox_fill:.3f} (> 0.96); "
      "natural/conflict masks must follow watersheds, contours, ecotone boundaries or real GIS layers."
    )

  # Check RGB sub-regions inside sibling <stem>.json5 if available
  cfg_path = re.sub(r"_areal_mask\.png$", ".json5", arg0_mask_path, flags=re.IGNORECASE)
  zero_rgb_regions = []
  if os.path.isfile(cfg_path):
    cfg = load_json_or_json5(cfg_path)
    sub_list = []
    for k in ("regions", "subregions", "sub_regions", "zones"):
      val_k = cfg.get(k)
      if isinstance(val_k, list):
        sub_list = val_k
        break
      if isinstance(val_k, dict):
        sub_list = [{"id": rk, **rv} for rk, rv in val_k.items() if isinstance(rv, dict)]
        break
    for sub in sub_list:
      if not isinstance(sub, dict):
        continue
      rgb = sub.get("rgb") or sub.get("color") or sub.get("colour")
      if isinstance(rgb, list) and len(rgb) >= 3:
        m_sub = valid & (arr[:, :, 0] == int(rgb[0])) & (arr[:, :, 1] == int(rgb[1])) & (arr[:, :, 2] == int(rgb[2]))
        sub_px = int(m_sub.sum())
        if sub_px == 0:
          zero_rgb_regions.append(sub.get("id") or sub.get("name") or str(rgb))
        elif sub_px >= 150 and not is_micro_sheet and not is_admin1:
          srs, scs = np.where(m_sub)
          sub_fill = float(sub_px) / max(1, int((srs.max() - srs.min() + 1) * (scs.max() - scs.min() + 1)))
          if sub_fill > 0.92:
            errors.append(
              f"[GEOMETRY] Sub-region {sub.get('id', rgb)!r} in {os.path.basename(arg0_mask_path)} "
              f"has synthetic box fill ratio {sub_fill:.3f} (> 0.92)."
            )
    if zero_rgb_regions:
      errors.append(
        f"[STARVATION] Sub-region(s) declared in {os.path.basename(cfg_path)} have 0 pixels in mask PNG: {zero_rgb_regions[:5]}"
      )

  # Containment vs sibling _settlements.json if present
  sett_path = re.sub(r"_areal_mask\.png$", "_settlements.json", arg0_mask_path, flags=re.IGNORECASE)
  inside_count, total_setts = 0, 0
  if os.path.isfile(sett_path):
    sdata = load_json_or_json5(sett_path)
    rows = list(sdata.values()) if isinstance(sdata, dict) else (sdata if isinstance(sdata, list) else [])
    h, w = arr.shape[:2]
    rad = 5 if has_micro_islands else 2
    in_flags = []
    for c in rows:
      coords = c.get("coords") if isinstance(c, dict) else None
      if not isinstance(coords, list) or len(coords) < 2:
        in_flags.append(False)
        continue
      total_setts += 1
      r = min(h - 1, max(0, int((90.0 - float(coords[0])) * h / 180.0)))
      col = min(w - 1, max(0, int((float(coords[1]) + 180.0) * w / 360.0)))
      hit = bool(valid[max(0, r - rad):min(h, r + rad + 1), max(0, col - rad):min(w, col + rad + 1)].any())
      in_flags.append(hit)
      if hit:
        inside_count += 1
    if total_setts > 0 and inside_count == 0:
      errors.append(f"[CONTAINMENT] 0/{total_setts} settlements fall inside {os.path.basename(arg0_mask_path)}.")
    if opts.get("render_overlays") and total_setts > 0:
      ov_dir = opts.get("overlay_dir") or os.path.join(os.path.dirname(arg0_mask_path), "overlays_qa")
      stem = re.sub(r"_areal_mask\.png$", "", os.path.basename(arg0_mask_path), flags=re.IGNORECASE)
      render_overlay_png(arr, rows, in_flags, os.path.join(ov_dir, f"verify_{stem}_overlay.png"), f"{stem} Mask & Settlements")

  return errors, warnings, {
    "active_px": active_px,
    "bbox_fill": round(bbox_fill, 4),
    "inside_settlements": inside_count,
    "total_settlements": total_setts,
  }


def audit_manifest(arg0_manifest_path, arg1_opts=None):
  """Audits an entire Viscount project areal-masks JSON5 manifest."""
  opts = arg1_opts or {}
  svea_root = opts.get("svea_root") or find_svea_root(arg0_manifest_path)
  profiles = load_skill_profiles(svea_root)
  proj_key = opts.get("project") or resolve_project_key(arg0_manifest_path, svea_root)
  defaults = (profiles.get("macro_region_defaults") or {}).get(proj_key or "", {})

  manifest = load_json_or_json5(arg0_manifest_path)
  geo_prof = manifest.get("geography_profile") or {}
  has_micro_islands = bool(
    opts.get("has_micro_islands")
    if opts.get("has_micro_islands") is not None
    else geo_prof.get("has_micro_islands", defaults.get("has_micro_islands", False))
  )

  errors, warnings = [], []
  gdims = manifest.get("grid_dimensions") or [4320, 2160]
  w, h = int(gdims[0]), int(gdims[1])
  claimed = np.zeros((h, w), dtype=bool)
  union_all = np.zeros((h, w), dtype=bool)

  # Check regime transitions if declared
  regimes = manifest.get("regime_transitions")
  if isinstance(regimes, dict):
    for rname, rcfg in regimes.items():
      if isinstance(rcfg, dict) and "pre_admin_end" in rcfg and "contemporary_start" in rcfg:
        if int(rcfg["pre_admin_end"]) > int(rcfg["contemporary_start"]):
          errors.append(
            f"[REGIME] {rname}: pre_admin_end ({rcfg['pre_admin_end']}) exceeds contemporary_start ({rcfg['contemporary_start']})."
          )

  # Ordered compositing across specialist_masks + macro_mask + national_epoch_masks
  mask_items = list(manifest.get("specialist_masks") or [])
  nat_items = list(manifest.get("national_epoch_masks") or [])
  macro = manifest.get("macro_mask")
  ordered = [(m, False, "specialist") for m in mask_items if isinstance(m, dict)]
  for m in nat_items:
    if isinstance(m, dict):
      ordered.append((m, True, "national"))
  if isinstance(macro, dict):
    ordered.append((macro, True, "macro"))

  if not ordered:
    return ["Manifest defines neither specialist_masks nor macro_mask."], warnings, {}

  mask_summaries = []
  child_opts = {**opts, "has_micro_islands": has_micro_islands}
  for item, is_macro, layer_kind in ordered:
    mid = item.get("id") or os.path.basename(str(item.get("mask_path", "")))
    dom = item.get("domain")
    if isinstance(dom, list) and len(dom) >= 2 and int(dom[0]) > int(dom[1]):
      errors.append(f"[TEMPORAL] Mask {mid!r} has inverted domain bookend {dom}.")

    m_rel = item.get("mask_path")
    if not m_rel:
      errors.append(f"Mask {mid!r} is missing `mask_path`.")
      continue
    m_abs = m_rel if os.path.isabs(m_rel) else os.path.join(svea_root or os.path.dirname(arg0_manifest_path), m_rel)
    item_opts = {**child_opts, "is_admin1": bool(item.get("is_admin1", False))}
    sub_e, sub_w, sub_s = audit_single_mask(m_abs, item_opts)
    errors.extend(sub_e)
    warnings.extend(sub_w)
    if os.path.isfile(m_abs):
      arr = np.asarray(Image.open(m_abs).convert("RGBA"), dtype=np.uint8)
      valid = (arr[:, :, 3] > 0) & (arr[:, :, :3].sum(axis=2) > 0)
      if layer_kind == "specialist":
        eff_px = int((valid & ~claimed).sum())
        claimed |= valid
        if eff_px == 0:
          errors.append(
            f"[STARVATION] Specialist mask {mid!r} retains 0 unclaimed pixels after higher-priority masks; fix manifest ordering or mask geometry."
          )
      else:
        eff_px = int(valid.sum()) if layer_kind == "national" else int((valid & ~claimed).sum())
      union_all |= valid
      mask_summaries.append({"id": mid, "effective_px": eff_px, **sub_s})

  # Project-union + 250 km frontier conditioning belt containment check
  belt = binary_dilation(union_all, iterations=(48 if has_micro_islands else 32))
  for item, _is_macro, _lk in ordered:
    m_rel = item.get("mask_path")
    if not m_rel:
      continue
    m_abs = m_rel if os.path.isabs(m_rel) else os.path.join(svea_root or os.path.dirname(arg0_manifest_path), m_rel)
    sp = re.sub(r"_areal_mask\.png$", "_settlements.json", m_abs, flags=re.IGNORECASE)
    if not os.path.isfile(sp):
      continue
    sdata = load_json_or_json5(sp)
    rows = list(sdata.values()) if isinstance(sdata, dict) else (sdata if isinstance(sdata, list) else [])
    if not rows:
      continue
    out_belt = 0
    for c in rows:
      coords = c.get("coords") if isinstance(c, dict) else None
      if not isinstance(coords, list) or len(coords) < 2:
        continue
      r = min(h - 1, max(0, int((90.0 - float(coords[0])) * h / 180.0)))
      col = min(w - 1, max(0, int((float(coords[1]) + 180.0) * w / 360.0)))
      if not belt[r, col]:
        out_belt += 1
    out_ratio = float(out_belt) / max(1, len(rows))
    if out_belt > 5 and out_ratio > 0.10:
      errors.append(
        f"[CONTAINMENT] Mask {item.get('id')!r}: {out_belt}/{len(rows)} ({out_ratio*100:.1f}% > 10%) settlements fall outside project union + frontier belt."
      )

  # Check substrata_sources post_domain_blend_years bounds
  for sname, scfg in (manifest.get("substrata_sources") or {}).items():
    if not isinstance(scfg, dict):
      continue
    sdom = scfg.get("domain")
    blends = scfg.get("post_domain_blend_years") or []
    if isinstance(sdom, list) and len(sdom) >= 2:
      if int(sdom[0]) > int(sdom[1]):
        errors.append(f"[TEMPORAL] substrata_sources.{sname} has inverted domain {sdom}.")
      for byr in blends:
        if int(byr) < int(sdom[0]) or int(byr) > int(sdom[1]) + 100:
          errors.append(f"[TEMPORAL] substrata_sources.{sname} blend year {byr} inconsistent with domain {sdom}.")

  return errors, warnings, {"project": proj_key, "masks_checked": len(mask_summaries), "has_micro_islands": has_micro_islands}


def main():
  parser = argparse.ArgumentParser(description="Gatekeeper A2: Audits Viscount areal masks across all 14 macro-regions.")
  parser.add_argument("target", help="Path to regional project dir, *_areal_masks.json5, or *_areal_mask.png")
  parser.add_argument("--project", default=None, help="Explicit Viscount project key (e.g. JADE, PRETA, AUSTRAL)")
  parser.add_argument("--render-overlays", action="store_true", help="Render verify_<stem>_overlay.png per mask with settlements")
  parser.add_argument("--overlay-dir", default=None, help="Output directory for rendered overlays")
  parser.add_argument("--has-micro-islands", action="store_true", default=None, help="Enable wider coastal/atoll pinning tolerance")
  parsed = parser.parse_args()

  resolved, mode = resolve_mask_manifest(parsed.target)
  if not resolved:
    print(f"[FAIL] Could not find *_areal_masks.json5 or *_areal_mask.png under {parsed.target}", file=sys.stderr)
    sys.exit(1)

  opts = vars(parsed)
  opts["svea_root"] = find_svea_root(resolved)
  if mode == "manifest":
    errors, warnings, stats = audit_manifest(resolved, opts)
  else:
    errors, warnings, stats = audit_single_mask(resolved, opts)

  for w in warnings[:30]:
    print(f"[WARN] {w}")
  for e in errors[:30]:
    print(f"[FAIL] {e}", file=sys.stderr)
  print(f"[audit_areal_masks] Summary: {json.dumps(stats)}")
  sys.exit(1 if errors else 0)


if __name__ == "__main__":
  main()
