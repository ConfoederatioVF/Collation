"""Renders a 3x3 mosaic of all 9 CASTLE kriged archaeological horizons and a 2x3 mosaic of
historical population benchmarks (-5000, 0, 700, 1600, 1850, 2000) into diagnostics_visual/
for comprehensive optical verification.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

DOMAIN_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\CASTLE\_shared\sites_korea_japan"
K_DIR = os.path.join(DOMAIN_DIR, "1.kriged_rasters")
P_DIR = os.path.join(DOMAIN_DIR, "2.population_rasters")
VIS_DIR = os.path.join(DOMAIN_DIR, "diagnostics_visual")
os.makedirs(VIS_DIR, exist_ok=True)


def decode_f32(path):
  raw = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  valid = np.isfinite(f32) & (f32 > 0.0)
  return np.where(valid, f32, np.nan), valid


def main():
  plt.rcdefaults()
  plt.style.use("default")
  k_files = sorted(f for f in os.listdir(K_DIR) if f.endswith(".png"))
  sample, valid = decode_f32(os.path.join(K_DIR, k_files[0]))
  rs, cs = np.where(valid)
  r0, r1 = max(0, int(rs.min()) - 8), min(sample.shape[0], int(rs.max()) + 9)
  c0, c1 = max(0, int(cs.min()) - 8), min(sample.shape[1], int(cs.max()) + 9)
  lon0 = -180.0 + c0 * (360.0 / 4320.0)
  lon1 = -180.0 + c1 * (360.0 / 4320.0)
  lat1 = 90.0 - r0 * (180.0 / 2160.0)
  lat0 = 90.0 - r1 * (180.0 / 2160.0)
  ext = [lon0, lon1, lat0, lat1]

  fig, axes = plt.subplots(3, 3, figsize=(15, 13.5), dpi=200)
  for ax, fn in zip(axes.flat, k_files[:9]):
    arr, v = decode_f32(os.path.join(K_DIR, fn))
    crop = arr[r0:r1, c0:c1]
    nz = crop[np.isfinite(crop)]
    vmin = max(0.05, float(np.percentile(nz, 2)))
    vmax = float(np.percentile(nz, 99.5))
    ax.imshow(crop, extent=ext, origin="upper", cmap="viridis", norm=mcolors.LogNorm(vmin=vmin, vmax=vmax), interpolation="nearest")
    ax.set_title(fn.replace(".png", ""), fontsize=9, fontweight="bold")
    ax.set_xlabel("Lon", fontsize=7)
    ax.set_ylabel("Lat", fontsize=7)
    ax.tick_params(labelsize=7)
  fig.suptitle("CASTLE All 9 Kriged Archaeological Horizons (H1-H9)", fontsize=13, fontweight="bold")
  fig.tight_layout(rect=[0, 0, 1, 0.96])
  out1 = os.path.join(VIS_DIR, "all_9_kriged_horizons_overview.png")
  fig.savefig(out1, dpi=200)
  plt.close(fig)

  years = [-5000, 0, 700, 1600, 1850, 2000]
  fig, axes = plt.subplots(2, 3, figsize=(15, 9.2), dpi=200)
  for ax, yr in zip(axes.flat, years):
    p = os.path.join(P_DIR, f"popc_{yr}.png")
    if not os.path.exists(p):
      ax.set_title(f"Missing {yr}")
      continue
    arr, v = decode_f32(p)
    crop = arr[r0:r1, c0:c1]
    nz = crop[np.isfinite(crop)]
    vmin = max(1.0, float(np.percentile(nz, 2)))
    vmax = float(np.percentile(nz, 99.5))
    ax.imshow(crop, extent=ext, origin="upper", cmap="magma", norm=mcolors.LogNorm(vmin=vmin, vmax=vmax), interpolation="nearest")
    lbl = f"{abs(yr)} BC" if yr < 0 else (f"AD {yr}" if yr > 0 else "AD 0")
    ax.set_title(f"Population Benchmark: {lbl} (sum={float(np.nansum(crop))/1e6:.2f}M)", fontsize=9.5, fontweight="bold")
    ax.tick_params(labelsize=7)
  fig.suptitle("CASTLE Historical Population Raster Progression (-5000 BC to AD 2000)", fontsize=13, fontweight="bold")
  fig.tight_layout(rect=[0, 0, 1, 0.95])
  out2 = os.path.join(VIS_DIR, "historical_population_benchmarks_grid.png")
  fig.savefig(out2, dpi=200)
  plt.close(fig)
  print("Wrote:", out1, out2)


if __name__ == "__main__":
  main()
