"""Gatekeeper C3: Renders 300 DPI 4-panel cartographic verification PNGs for kriged substrata
domains (`1.kriged_rasters` + `2.population_rasters` + Natural Earth rivers/coastlines),
audits fluvial/topographic spatial detail against blurry Voronoi blobs, and enforces a signed
optical inspection manifest (`visual_verification_manifest.json`).
"""

import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.collections import LineCollection
import numpy as np
from PIL import Image
from scipy.ndimage import uniform_filter


def format_plain_linear_tick(arg0_value, arg1_pos=None):
  """Formats linear numeric ticks using EN-GB European decimal commas (no scientific notation)."""
  val = float(arg0_value)
  if not np.isfinite(val):
    return ""
  if abs(val) < 1e-12:
    return "0"
  if abs(val) >= 1000.0:
    return format_plain_log_tick(val)
  s = f"{val:.2f}".rstrip("0").rstrip(".")
  return s.replace(".", ",")


def format_plain_log_tick(arg0_value, arg1_pos=None):
  """Formats logarithmic axis or colorbar ticks using plain European numerals (`0,01`, `10`, `1k`, `1M`)."""
  val = float(arg0_value)
  if not np.isfinite(val) or val <= 0.0:
    return ""
  if val >= 1e9:
    s = f"{val / 1e9:.2f}".rstrip("0").rstrip(".")
    return f"{s.replace('.', ',')}B"
  if val >= 1e6:
    s = f"{val / 1e6:.2f}".rstrip("0").rstrip(".")
    return f"{s.replace('.', ',')}M"
  if val >= 1e3:
    s = f"{val / 1e3:.1f}".rstrip("0").rstrip(".")
    return f"{s.replace('.', ',')}k"
  if val >= 1.0:
    if abs(val - round(val)) < 1e-6:
      return str(int(round(val)))
    return f"{val:.2f}".rstrip("0").rstrip(".").replace(".", ",")
  if val >= 1e-4:
    digits = 2 if val >= 0.01 else (3 if val >= 0.001 else 4)
    return f"{val:.{digits}f}".rstrip("0").rstrip(".").replace(".", ",")
  return f"{val:.5f}".rstrip("0").rstrip(".").replace(".", ",")


def find_svea_root(arg0_start_path):
  """Locates SVEA root folder."""
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


def decode_float32_png(arg0_png_path):
  """Decodes a 4320x2160 big-endian float32 RGBA GeoPNG."""
  raw = np.asarray(Image.open(arg0_png_path).convert("RGBA"), dtype=np.uint8)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  valid = np.isfinite(f32) & (f32 > 0.0)
  return np.where(valid, f32, 0.0), valid


def compute_spatial_detail_metrics(arg0_png_path):
  """Computes high-pass 15x15 residual variance & 1px gradient metrics on log10 density."""
  field, valid = decode_float32_png(arg0_png_path)
  n_valid = int(valid.sum())
  if n_valid == 0:
    return {"n_valid": 0, "hp15_mean": 0.0, "dx_mean": 0.0, "p99_p50_ratio": 0.0}

  rs, cs = np.where(valid)
  r0, r1 = int(rs.min()), int(rs.max()) + 1
  c0, c1 = int(cs.min()), int(cs.max()) + 1
  sub_v = valid[r0:r1, c0:c1]
  sub_f = field[r0:r1, c0:c1]
  vals = sub_f[sub_v]
  log_f = np.where(sub_v, np.log10(np.maximum(1e-7, sub_f)), 0.0)
  w_m = sub_v.astype(float)
  lp_num = uniform_filter(log_f, size=15)
  lp_den = uniform_filter(w_m, size=15)
  lp = np.where(sub_v & (lp_den > 0.1), lp_num / np.maximum(1e-6, lp_den), log_f)
  hp = np.abs(log_f - lp)[sub_v]

  pair_h = sub_v[:, :-1] & sub_v[:, 1:]
  dx = np.abs(log_f[:, 1:] - log_f[:, :-1])[pair_h]

  return {
    "n_valid": n_valid,
    "bbox_rc": (r0, r1, c0, c1),
    "p99_p50_ratio": float(np.percentile(vals, 99) / max(1e-9, np.percentile(vals, 50))),
    "hp15_mean": float(np.mean(hp)) if hp.size > 0 else 0.0,
    "dx_mean": float(np.mean(dx)) if dx.size > 0 else 0.0,
  }


def extract_lines_from_geojson(arg0_path, arg1_lon_bounds, arg2_lat_bounds):
  """Extracts line segments inside a geographic bounding box from a Natural Earth GeoJSON."""
  if not arg0_path or not os.path.isfile(arg0_path):
    return []
  gj = json.loads(open(arg0_path, "r", encoding="utf-8").read())
  lon_min, lon_max = arg1_lon_bounds
  lat_min, lat_max = arg2_lat_bounds
  segs = []

  def accept_ring(coords):
    pts = [(float(p[0]), float(p[1])) for p in coords if len(p) >= 2]
    if len(pts) < 2:
      return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if max(xs) < lon_min or min(xs) > lon_max or max(ys) < lat_min or min(ys) > lat_max:
      return
    segs.append(pts)

  for feat in gj.get("features", []):
    geom = feat.get("geometry") or {}
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    if gtype == "LineString":
      accept_ring(coords)
    elif gtype == "MultiLineString":
      for line in coords:
        accept_ring(line)
    elif gtype == "Polygon":
      for ring in coords:
        accept_ring(ring)
    elif gtype == "MultiPolygon":
      for poly in coords:
        for ring in poly:
          accept_ring(ring)
  return segs


def load_site_points(arg0_domain_dir):
  """Loads observation centroids and intensities from geojson/*.geojson."""
  gdir = os.path.join(arg0_domain_dir, "geojson")
  if not os.path.isdir(gdir):
    return [], [], []
  candidates = [f for f in sorted(os.listdir(gdir)) if f.endswith(".geojson") and "all_periods" not in f]
  target = os.path.join(gdir, "00_all_periods.geojson")
  if not os.path.isfile(target) and candidates:
    target = os.path.join(gdir, candidates[len(candidates) // 2])
  if not os.path.isfile(target):
    return [], [], []

  gj = json.loads(open(target, "r", encoding="utf-8").read())
  lons, lats, weights = [], [], []
  for feat in gj.get("features", []):
    geom = feat.get("geometry") or {}
    props = feat.get("properties") or {}
    if props.get("is_unspecified_subregion") or geom.get("type") != "Point":
      continue
    coords = geom.get("coordinates") or []
    if len(coords) < 2:
      continue
    val = float(props.get("total_sites_all_periods") or props.get("site_count") or props.get("value") or 1.0)
    lons.append(float(coords[0]))
    lats.append(float(coords[1]))
    weights.append(max(1.0, val))
  return lons, lats, weights


def pick_representative_files(arg0_dir, arg1_ext=".png"):
  """Selects representative files spanning early, middle and peak periods/years."""
  if not os.path.isdir(arg0_dir):
    return []
  files = sorted(f for f in os.listdir(arg0_dir) if f.lower().endswith(arg1_ext))
  if not files:
    return []
  if len(files) <= 2:
    return [os.path.join(arg0_dir, f) for f in files]
  return [
    os.path.join(arg0_dir, files[0]),
    os.path.join(arg0_dir, files[len(files) // 2]),
    os.path.join(arg0_dir, files[-1]),
  ]


def render_overview_sheet(arg0_domain_dir, arg1_krig_path, arg2_pop_path, arg3_out_png, arg4_title):
  """Renders a 300 DPI 4-panel cartographic verification figure."""
  plt.rcdefaults()
  plt.style.use("default")
  k_field, k_valid = decode_float32_png(arg1_krig_path)
  if int(k_valid.sum()) == 0:
    return None

  rs, cs = np.where(k_valid)
  r0, r1 = max(0, int(rs.min()) - 6), min(2160, int(rs.max()) + 7)
  c0, c1 = max(0, int(cs.min()) - 6), min(4320, int(cs.max()) + 7)
  lon_min = -180.0 + c0 * 360.0 / 4320.0
  lon_max = -180.0 + c1 * 360.0 / 4320.0
  lat_max = 90.0 - r0 * 180.0 / 2160.0
  lat_min = 90.0 - r1 * 180.0 / 2160.0
  extent = [lon_min, lon_max, lat_min, lat_max]
  mid_lat = 0.5 * (lat_min + lat_max)
  geo_aspect = 1.0 / max(0.25, float(np.cos(np.radians(mid_lat))))

  svea_root = find_svea_root(arg0_domain_dir)
  rivers_segs = []
  coast_segs = []
  if svea_root:
    gis_cands = [
      os.path.join(svea_root, "histmap/1.data_raw/population_regional/_shared/_gis_cache"),
      os.path.join(svea_root, "histmap/1.data_raw/population_regional/POLARIS/_shared/_gis_cache"),
      os.path.join(svea_root, "histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache"),
    ]
    gcache = next((d for d in gis_cands if os.path.isdir(d)), None)
    if gcache:
      rivers_segs = extract_lines_from_geojson(os.path.join(gcache, "ne_50m_rivers_lake_centerlines.geojson"), (lon_min, lon_max), (lat_min, lat_max))
      coast_segs = extract_lines_from_geojson(os.path.join(gcache, "ne_50m_coastline.geojson"), (lon_min, lon_max), (lat_min, lat_max))

  fig, axes = plt.subplots(2, 2, figsize=(14, 9), dpi=300)
  log_fmt = mticker.FuncFormatter(format_plain_log_tick)
  lin_fmt = mticker.FuncFormatter(format_plain_linear_tick)

  k_raw = np.where(k_valid[r0:r1, c0:c1], np.maximum(1e-4, k_field[r0:r1, c0:c1]), np.nan)
  sub_k = np.where(k_valid[r0:r1, c0:c1], np.log10(np.maximum(1e-6, k_field[r0:r1, c0:c1])), np.nan)
  if arg2_pop_path and os.path.isfile(arg2_pop_path):
    p_field, p_valid = decode_float32_png(arg2_pop_path)
    p_raw = np.where(p_valid[r0:r1, c0:c1], np.maximum(1e-3, p_field[r0:r1, c0:c1]), np.nan)
  else:
    p_raw = k_raw

  log_zero = np.nan_to_num(sub_k, nan=float(np.nanmin(sub_k)))
  gy, gx = np.gradient(log_zero)
  grad_mag = np.where(np.isfinite(sub_k), np.sqrt(gx * gx + gy * gy), np.nan)

  lons, lats, wts = load_site_points(arg0_domain_dir)
  ax0, ax1, ax2, ax3 = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

  def add_basemap(ax):
    if coast_segs:
      ax.add_collection(LineCollection(coast_segs, colors="#333333", linewidths=0.45, alpha=0.75))
    if rivers_segs:
      ax.add_collection(LineCollection(rivers_segs, colors="#2b6cb0", linewidths=0.40, alpha=0.55))
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect(geo_aspect)
    ax.xaxis.set_major_formatter(lin_fmt)
    ax.yaxis.set_major_formatter(lin_fmt)
    ax.grid(True, alpha=0.25, linewidth=0.4)

  def apply_plain_log_cbar(cb, vmin_val, vmax_val):
    decades = [10.0 ** e for e in range(-4, 9) if vmin_val * 0.9 <= (10.0 ** e) <= vmax_val * 1.1]
    if len(decades) >= 2:
      cb.set_ticks(decades)
    cb.ax.yaxis.set_major_formatter(log_fmt)
    cb.ax.yaxis.set_minor_formatter(mticker.NullFormatter())

  # Panel A: Observation sites & catchment density
  add_basemap(ax0)
  if lons:
    w_arr = np.maximum(1.0, np.asarray(wts, dtype=float))
    w_vmax = max(10.0, float(np.nanpercentile(w_arr, 99)))
    norm_a = mcolors.LogNorm(vmin=1.0, vmax=w_vmax)
    sc = ax0.scatter(lons, lats, c=w_arr, norm=norm_a, s=8, cmap="plasma", alpha=0.85)
    cb0 = fig.colorbar(sc, ax=ax0, fraction=0.036, pad=0.02, format=log_fmt, label="Sites per Catchment")
    apply_plain_log_cbar(cb0, 1.0, w_vmax)
  ax0.set_title(f"(A) Observation Catchments & Rivers (n={len(lons)})")

  # Panel B: Kriged surface
  k_fin = k_raw[np.isfinite(k_raw)]
  vmin_k = max(1e-4, float(np.nanpercentile(k_fin, 2))) if k_fin.size > 0 else 1e-4
  vmax_k = max(vmin_k * 10.0, float(np.nanpercentile(k_fin, 99.5))) if k_fin.size > 0 else 10.0
  norm_b = mcolors.LogNorm(vmin=vmin_k, vmax=vmax_k)
  im1 = ax1.imshow(k_raw, origin="upper", extent=extent, cmap="viridis", norm=norm_b)
  add_basemap(ax1)
  cb1 = fig.colorbar(im1, ax=ax1, fraction=0.036, pad=0.02, format=log_fmt, label="Kriged Intensity")
  apply_plain_log_cbar(cb1, vmin_k, vmax_k)
  ax1.set_title(f"(B) Kriged Surface: {os.path.basename(arg1_krig_path)}")

  # Panel C: Population surface
  p_fin = p_raw[np.isfinite(p_raw)]
  vmin_p = max(1e-3, float(np.nanpercentile(p_fin, 2))) if p_fin.size > 0 else 1e-2
  vmax_p = max(vmin_p * 10.0, float(np.nanpercentile(p_fin, 99.5))) if p_fin.size > 0 else 1000.0
  norm_c = mcolors.LogNorm(vmin=vmin_p, vmax=vmax_p)
  im2 = ax2.imshow(p_raw, origin="upper", extent=extent, cmap="magma", norm=norm_c)
  add_basemap(ax2)
  cb2 = fig.colorbar(im2, ax=ax2, fraction=0.036, pad=0.02, format=log_fmt, label="Inhabitants per 5' Cell")
  apply_plain_log_cbar(cb2, vmin_p, vmax_p)
  ax2.set_title(f"(C) Population Benchmark: {os.path.basename(arg2_pop_path) if arg2_pop_path else 'N/A'}")

  # Panel D: Fluvial/topographic local sharpness magnitude
  vmax_g = float(np.nanpercentile(grad_mag, 98)) if np.isfinite(grad_mag).any() else 1.0
  im3 = ax3.imshow(grad_mag, origin="upper", extent=extent, cmap="inferno", vmin=0.0, vmax=max(0.05, vmax_g))
  add_basemap(ax3)
  cb3 = fig.colorbar(im3, ax=ax3, fraction=0.036, pad=0.02, format=lin_fmt, label=r"Gradient $|\nabla \log_{10}(D)|$")
  cb3.ax.yaxis.set_major_formatter(lin_fmt)
  ax3.set_title("(D) Local Spatial Gradient Sharpness")

  fig.suptitle(arg4_title, fontsize=12, fontweight="bold")
  fig.tight_layout(rect=[0, 0, 1, 0.96])
  os.makedirs(os.path.dirname(arg3_out_png), exist_ok=True)
  fig.savefig(arg3_out_png, dpi=300)
  plt.close(fig)
  return arg3_out_png


def audit_domain_visuals(arg0_domain_dir, arg1_render=False, arg2_require_manifest=True):
  """Renders (if requested), quantitatively audits, and validates optical verification manifest."""
  errors = []
  warnings = []
  domain_dir = os.path.abspath(arg0_domain_dir)
  k_dir = os.path.join(domain_dir, "1.kriged_rasters")
  p_dir = os.path.join(domain_dir, "2.population_rasters")
  vis_dir = os.path.join(domain_dir, "diagnostics_visual")
  manifest_path = os.path.join(domain_dir, "config", "visual_verification_manifest.json")

  k_files = sorted(os.path.join(k_dir, f) for f in os.listdir(k_dir) if f.lower().endswith(".png")) if os.path.isdir(k_dir) else []
  p_files = sorted(os.path.join(p_dir, f) for f in os.listdir(p_dir) if f.lower().endswith(".png")) if os.path.isdir(p_dir) else []
  if not k_files:
    errors.append(f"No GeoPNG rasters found in {k_dir}")
    return errors, warnings, {}

  # Pick representative files
  k_mid = k_files[len(k_files) // 2]
  k_peak = k_files[-2] if len(k_files) >= 2 else k_files[0]
  p_1000 = os.path.join(p_dir, "popc_1000.png")
  if not os.path.isfile(p_1000):
    p_1000 = p_files[len(p_files) // 2] if p_files else None

  sheet_a = os.path.join(vis_dir, "kriged_periods_overview.png")
  sheet_b = os.path.join(vis_dir, "population_benchmarks_overview.png")
  rendered = []
  if arg1_render or not os.path.isfile(sheet_a):
    r1 = render_overview_sheet(domain_dir, k_mid, p_1000, sheet_a, f"{os.path.basename(domain_dir)}: Mid-Period Kriging & Fluvial Alignment Audit")
    if r1:
      rendered.append(r1)
  if arg1_render or not os.path.isfile(sheet_b):
    r2 = render_overview_sheet(domain_dir, k_peak, p_files[-1] if p_files else None, sheet_b, f"{os.path.basename(domain_dir)}: Late-Period Kriging & Population Benchmark Audit")
    if r2:
      rendered.append(r2)

  k_metrics = compute_spatial_detail_metrics(k_mid)
  p_metrics = compute_spatial_detail_metrics(p_1000) if p_1000 and os.path.isfile(p_1000) else {}
  if k_metrics["n_valid"] >= 2000:
    if k_metrics["hp15_mean"] < 0.08 or k_metrics["dx_mean"] < 0.04:
      errors.append(
        f"[VISUAL_SHARPNESS] Kriged surface {os.path.basename(k_mid)} exhibits blurry isotropic halos without fine fluvial/topographic detail "
        f"(hp15_mean={k_metrics['hp15_mean']:.3f} < 0.08, dx_mean={k_metrics['dx_mean']:.3f} < 0.04; POLARIS baseline >= 0.18 / 0.10)."
      )
  if p_metrics and p_metrics.get("n_valid", 0) >= 2000:
    if p_metrics["hp15_mean"] < 0.06 or p_metrics["dx_mean"] < 0.03:
      errors.append(
        f"[VISUAL_SHARPNESS] Interpolated population raster {os.path.basename(p_1000)} is over-smoothed "
        f"(hp15_mean={p_metrics['hp15_mean']:.3f} < 0.06, dx_mean={p_metrics['dx_mean']:.3f} < 0.03)."
      )

  manifest_ok = False
  if arg2_require_manifest:
    png_list = [os.path.join(vis_dir, f) for f in sorted(os.listdir(vis_dir)) if f.lower().endswith(".png")] if os.path.isdir(vis_dir) else []
    if not png_list:
      errors.append(f"[VISUAL_GATE] No diagnostic PNGs exist in {vis_dir}; run with --render first.")
    elif not os.path.isfile(manifest_path):
      errors.append(
        f"[VISUAL_GATE] Mandatory optical inspection manifest missing: {manifest_path}. "
        "Inspect every PNG in diagnostics_visual/ with read_file and sign visual_verification_manifest.json."
      )
    else:
      max_png_mtime = max(os.path.getmtime(p) for p in png_list)
      man_mtime = os.path.getmtime(manifest_path)
      if man_mtime + 0.5 < max_png_mtime:
        errors.append(
          f"[VISUAL_GATE] visual_verification_manifest.json predates newest rendered PNG ({os.path.basename(vis_dir)}); re-inspect updated PNGs via read_file."
        )
      else:
        man = json.loads(open(manifest_path, "r", encoding="utf-8").read())
        inspected = man.get("inspected_sheets") if isinstance(man, dict) else None
        if not isinstance(inspected, list) or len(inspected) < len(png_list):
          errors.append("[VISUAL_GATE] visual_verification_manifest.json does not cover all rendered PNGs in diagnostics_visual/.")
        else:
          by_name = {os.path.basename(str(item.get("file", ""))): item for item in inspected if isinstance(item, dict)}
          all_valid = True
          for p in png_list:
            bn = os.path.basename(p)
            rec = by_name.get(bn)
            if not rec or not rec.get("inspected_via_read_file") or not rec.get("river_coastal_alignment_verified") or not rec.get("zero_isotropic_voronoi_blobs") or not rec.get("zero_modern_border_cliffs"):
              errors.append(f"[VISUAL_GATE] Manifest lacks verified boolean checkboxes for {bn}.")
              all_valid = False
            elif len(str(rec.get("cartographic_notes", "")).strip()) < 80:
              errors.append(f"[VISUAL_GATE] Manifest cartographic_notes for {bn} too brief (< 80 chars).")
              all_valid = False
          manifest_ok = all_valid

  return errors, warnings, {
    "domain": os.path.basename(domain_dir),
    "rendered_files": rendered,
    "kriged_hp15_mean": round(k_metrics.get("hp15_mean", 0.0), 4),
    "kriged_dx_mean": round(k_metrics.get("dx_mean", 0.0), 4),
    "pop_hp15_mean": round(p_metrics.get("hp15_mean", 0.0), 4) if p_metrics else None,
    "visual_manifest_verified": manifest_ok,
  }


def main():
  parser = argparse.ArgumentParser(description="Render 4-panel cartographic kriging audits & enforce visual sign-off.")
  parser.add_argument("domain_dir", help="Path to archaeological kriging domain (e.g. _shared/sites_IA_RAS)")
  parser.add_argument("--render", action="store_true", help="Render/refresh 300 DPI 4-panel audit PNGs in diagnostics_visual/")
  parser.add_argument("--render-only", action="store_true", help="Render PNGs and skip visual_verification_manifest.json gate")
  parser.add_argument("--require-visual-manifest", action="store_true", help="Explicitly require signed visual_verification_manifest.json (default unless --render-only)")
  parsed = parser.parse_args()

  require_man = not parsed.render_only
  errors, warnings, summary = audit_domain_visuals(parsed.domain_dir, parsed.render, require_man)
  for w in warnings:
    print(f"[WARN] {w}")
  for e in errors:
    print(f"[FAIL] {e}", file=sys.stderr)

  print(f"[render_and_audit_kriging_visuals] Summary: {json.dumps(summary)}")
  sys.exit(1 if errors else 0)


if __name__ == "__main__":
  main()
