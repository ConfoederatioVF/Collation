"""Gatekeeper E2: Audits end-to-end Stadestér -> Velkscala raster reconciliation across any
Viscount macro-region: blocks big-endian IEEE-754 float32 alpha-byte bugs, circular
downstream rural reads in kriging, Swiss-cheese zero holes and sub-5k settlement drops.
"""

import argparse
import glob
import json
import os
import re
import sys

import numpy as np
from PIL import Image

try:
  import json5
except ImportError:
  json5 = None


FLOAT32_ALPHA_PAT = re.compile(r"(?:png|img)(?:_obj)?\.data\[[^\]]*\+\s*3\]\s*>\s*0")
CIRCULAR_RURAL_PAT = re.compile(r"stadester_rural_", re.IGNORECASE)


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
  """Loads JSON or JSON5 safely."""
  with open(arg0_path, "r", encoding="utf-8", errors="replace") as fh:
    txt = fh.read()
  try:
    return json.loads(txt)
  except (json.JSONDecodeError, ValueError):
    if json5 is not None:
      return json5.loads(txt)
    cleaned = re.sub(r"//.*?$|/\*.*?\*/", "", txt, flags=re.MULTILINE | re.DOTALL)
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    return json.loads(cleaned)


def decode_float32_png(arg0_png_path):
  """Decodes a Big-Endian IEEE-754 float32 RGBA GeoPNG (ignoring exact 0x00000000 zero pixels)."""
  raw = np.asarray(Image.open(arg0_png_path).convert("RGBA"), dtype=np.uint8)
  nonzero_bytes = (raw[:, :, 0] > 0) | (raw[:, :, 1] > 0) | (raw[:, :, 2] > 0) | (raw[:, :, 3] > 0)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  valid = nonzero_bytes & np.isfinite(f32) & (f32 > 0.0)
  return np.where(valid, f32, 0.0)


def scan_scripts_for_antipatterns(arg0_dirs):
  """Scans regional pipeline & kriging scripts for float32 alpha-byte bugs and circular reads."""
  errors = []
  for root_dir in arg0_dirs:
    if not root_dir or not os.path.isdir(root_dir):
      continue
    for cur_root, dirs, files in os.walk(root_dir):
      dirs[:] = sorted([d for d in dirs if d not in ("_gis_cache", "node_modules", ".git", "diagnostics_visual", "figures", "papers")])
      for fn in sorted(files):
        if not fn.lower().endswith((".js", ".py")):
          continue
        fp = os.path.join(cur_root, fn)
        try:
          txt = open(fp, "r", encoding="utf-8", errors="replace").read()
        except OSError:
          continue
        lines = txt.splitlines()
        is_krige_script = ("krige" in fn.lower()) or ("matern" in fn.lower())
        for idx, line in enumerate(lines, start=1):
          if FLOAT32_ALPHA_PAT.search(line) and "getFloat32" not in line and "|" not in line:
            errors.append(
              f"[FLOAT32_BUG] {os.path.relpath(fp, root_dir)}:{idx}: unsafe `png.data[... + 3] > 0` alpha check "
              "zeroes valid IEEE-754 float32 pixels with 0x00 low mantissa byte; use 4-byte OR + DataView.getFloat32."
            )
          if is_krige_script and CIRCULAR_RURAL_PAT.search(line):
            errors.append(
              f"[CIRCULAR_READ] {os.path.relpath(fp, root_dir)}:{idx}: kriging script reads downstream `stadester_rural_*` raster."
            )
  return errors


def resolve_project_context(arg0_project_key, arg1_svea_root):
  """Loads precedence entry, skill defaults, union mask and compiled shards for a Viscount project."""
  prec_path = os.path.join(arg1_svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5")
  prof_path = os.path.join(arg1_svea_root, ".agents/skills/population-regional-study/config/viscount_skill_profiles.json5")
  prec = load_json_or_json5(prec_path) if os.path.isfile(prec_path) else {}
  prof = load_json_or_json5(prof_path) if os.path.isfile(prof_path) else {}
  key = arg0_project_key.upper()
  proj_entry = next((p for p in prec.get("projects", []) if str(p.get("key") or "").upper() == key), None)
  defaults = (prof.get("macro_region_defaults") or {}).get(key, {})
  return proj_entry, defaults


def build_project_union_mask(arg0_proj, arg1_svea_root, arg2_shape=(2160, 4320)):
  """Builds boolean union mask from areal_masks_manifest if available."""
  h, w = arg2_shape
  union_m = np.zeros((h, w), dtype=bool)
  if not arg0_proj:
    return None
  am_rel = arg0_proj.get("areal_masks_manifest")
  if am_rel:
    am_abs = os.path.join(arg1_svea_root, am_rel)
    if os.path.isfile(am_abs):
      am = load_json_or_json5(am_abs)
      items = ([am["macro_mask"]] if isinstance(am.get("macro_mask"), dict) else []) + list(am.get("specialist_masks") or [])
      for it in items:
        mp = it.get("mask_path") if isinstance(it, dict) else None
        if not mp:
          continue
        m_abs = mp if os.path.isabs(mp) else os.path.join(arg1_svea_root, mp)
        if os.path.isfile(m_abs):
          arr = np.asarray(Image.open(m_abs).convert("RGBA"), dtype=np.uint8)
          union_m |= (arr[:, :, 3] > 0) & (arr[:, :, :3].sum(axis=2) > 0)
      if union_m.any():
        return union_m
  return None


def load_project_shards(arg0_proj, arg1_svea_root):
  """Loads compiled shard settlements for `arg0_proj` from Stadestér 2.0 visualisation outputs."""
  shard_dir = os.path.join(arg1_svea_root, "histmap/5.data_visualisation/stadester/stadester_2.0")
  man_path = os.path.join(shard_dir, "stadester_manifest.json")
  if not os.path.isfile(man_path) or not arg0_proj:
    return [], 0.0
  man = json.load(open(man_path, "r", encoding="utf-8"))
  reg = next((r for r in man.get("regions", []) if str(r.get("key") or "").upper() == str(arg0_proj.get("key", "")).upper()), None)
  if not reg:
    return [], 0.0
  cities = []
  newest_mtime = 0.0
  for fn in reg.get("files", []):
    fp = os.path.join(shard_dir, fn)
    if os.path.isfile(fp):
      newest_mtime = max(newest_mtime, os.path.getmtime(fp))
      data = json.load(open(fp, "r", encoding="utf-8"))
      if isinstance(data, dict):
        cities.extend(data.values())
  return cities, newest_mtime


def audit_velkscala(arg0_project, arg1_years, arg2_opts=None):
  """Runs static script checks and Velkscala raster reconciliation probes."""
  opts = arg2_opts or {}
  svea_root = opts.get("svea_root") or find_svea_root(os.getcwd())
  errors, warnings = [], []
  if not svea_root:
    return ["Unable to locate SVEA repository root."], warnings, {}

  proj_entry, defaults = resolve_project_context(arg0_project, svea_root)
  if not proj_entry and not opts.get("velkscala_dir"):
    return [f"Unknown Viscount project key: {arg0_project}"], warnings, {}

  # 1. Static script anti-pattern scan
  scan_dirs = [os.path.join(svea_root, "histmap/1.data_raw/population_regional", arg0_project.upper())]
  if opts.get("scan_dir"):
    scan_dirs.append(opts["scan_dir"])
  errors.extend(scan_scripts_for_antipatterns(scan_dirs))

  velk_dir = opts.get("velkscala_dir") or os.path.join(svea_root, "histmap/2.data_cleaning/population_Velkscala")
  pop_dir = os.path.join(velk_dir, "population_rasters")
  rur_dir = os.path.join(velk_dir, "population_rural_rasters")
  if not os.path.isdir(pop_dir) or not os.path.isdir(rur_dir):
    if opts.get("scan_only"):
      return errors, warnings, {"scripts_scanned": True, "rasters_checked": 0}
    return errors + [f"Missing Velkscala raster folders in {velk_dir}"], warnings, {}

  union_mask = build_project_union_mask(proj_entry, svea_root)
  cities, shard_mtime = load_project_shards(proj_entry, svea_root)
  has_micro_islands = bool(defaults.get("has_micro_islands", False))
  rad = 2 if has_micro_islands else 1

  land_p = os.path.join(svea_root, "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png")
  land_valid = None
  if os.path.isfile(land_p) and not opts.get("velkscala_dir"):
    land_valid = decode_float32_png(land_p) > 0.0

  yr_stats = []
  for yr in arg1_years:
    pop_p = os.path.join(pop_dir, f"population_{yr}.png")
    rur_p = os.path.join(rur_dir, f"population_rural_{yr}.png")
    if not os.path.isfile(pop_p) or not os.path.isfile(rur_p):
      warnings.append(f"Skipped missing Velkscala pair for yr={yr}.")
      continue
    pop = decode_float32_png(pop_p)
    rur = decode_float32_png(rur_p)
    h, w = pop.shape
    region_m = union_mask if (union_mask is not None and union_mask.shape == pop.shape) else np.ones(pop.shape, dtype=bool)
    if land_valid is not None and land_valid.shape == pop.shape:
      region_m = region_m & land_valid

    # Swiss-cheese zero-hole check: interior 0.0 pixels surrounded by 8 neighbours with rur > 5.0
    pos = rur > 5.0
    nbr_cnt = (
      pos[:-2, :-2].astype(np.int32) + pos[:-2, 1:-1] + pos[:-2, 2:]
      + pos[1:-1, :-2] + pos[1:-1, 2:]
      + pos[2:, :-2] + pos[2:, 1:-1] + pos[2:, 2:]
    )
    holes = (rur[1:-1, 1:-1] == 0.0) & (pop[1:-1, 1:-1] == 0.0) & region_m[1:-1, 1:-1] & (nbr_cnt == 8)
    hole_cnt = int(holes.sum())
    inhabited_px = int((pop[region_m] > 0.0).sum())
    max_allowed_holes = max(15, int(0.0005 * inhabited_px))
    if hole_cnt > max_allowed_holes:
      errors.append(
        f"[SWISS_CHEESE] yr={yr}: detected {hole_cnt} isolated exact-zero interior rural pixel(s) "
        f"(limit <= {max_allowed_holes}, indicates float32 alpha-byte decoding bug)."
      )

    # Sub-5k floor check
    sub5k_checked, sub5k_dropped = 0, 0
    if yr > 1 and cities:
      for c in cities:
        pv = (c.get("population") or {}).get(str(yr))
        if pv is None or not (0.0 < float(pv) < 5000.0):
          continue
        coords = c.get("coords")
        if not isinstance(coords, list) or len(coords) < 2:
          continue
        r = min(h - 1, max(0, int((90.0 - float(coords[0])) * h / 180.0)))
        col = min(w - 1, max(0, int((float(coords[1]) + 180.0) * w / 360.0)))
        if union_mask is not None and not union_mask[r, col]:
          continue
        sub5k_checked += 1
        win_max = float(pop[max(0, r - rad):min(h, r + rad + 1), max(0, col - rad):min(w, col + rad + 1)].max())
        if win_max < 0.5 * float(pv):
          sub5k_dropped += 1
      if sub5k_checked >= 20:
        drop_ratio = float(sub5k_dropped) / sub5k_checked
        velk_mtime = os.path.getmtime(pop_p)
        if drop_ratio > 0.05:
          msg = (
            f"[SUB5K_DROP] yr={yr}: {sub5k_dropped}/{sub5k_checked} ({drop_ratio*100:.1f}%) sub-5k settlements "
            "lack gridcell floor support in population_Velkscala."
          )
          if shard_mtime > velk_mtime + 60.0 and not opts.get("require_fresh_velkscala"):
            warnings.append(msg + " (Note: Velkscala PNG predates newest Stadestér shard; rebuild Velkscala to sync.)")
          else:
            errors.append(msg)

    yr_stats.append({
      "yr": yr,
      "holes": hole_cnt,
      "sub5k_checked": sub5k_checked,
      "sub5k_dropped": sub5k_dropped,
    })

  return errors, warnings, {"project": arg0_project.upper(), "years_checked": yr_stats}


def main():
  parser = argparse.ArgumentParser(description="Gatekeeper E2: End-to-end Velkscala reconciliation & float32 audit.")
  parser.add_argument("--project", required=True, help="Viscount macro-region key (e.g. POLARIS, PRETA, JADE)")
  parser.add_argument("--years", default="-2000,0,900,1400,1900", help="Comma-separated years to probe")
  parser.add_argument("--scan-dir", default=None, help="Additional script directory to scan")
  parser.add_argument("--velkscala-dir", default=None, help="Override Velkscala raster directory (for tests)")
  parser.add_argument("--scan-only", action="store_true", help="Only run static anti-pattern script scan")
  parser.add_argument("--require-fresh-velkscala", action="store_true", help="Fail even if Velkscala rasters are older than shards")
  parsed = parser.parse_args()

  years = [int(x.strip()) for x in parsed.years.split(",") if x.strip()]
  errors, warnings, summary = audit_velkscala(parsed.project, years, vars(parsed))
  for w in warnings[:30]:
    print(f"[WARN] {w}")
  for e in errors[:30]:
    print(f"[FAIL] {e}", file=sys.stderr)
  print(f"[audit_velkscala_reconciliation] Summary: {json.dumps(summary)}")
  sys.exit(1 if errors else 0)


if __name__ == "__main__":
  main()
