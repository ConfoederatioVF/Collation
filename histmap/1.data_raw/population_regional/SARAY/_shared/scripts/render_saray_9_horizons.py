"""Renders all 9 SARAY kriged archaeological horizons (01..09) into a 3x3 300 DPI optical QA sheet."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

DOMAIN_DIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\SARAY\_shared\sites_saray_central_asia"
KDIR = os.path.join(DOMAIN_DIR, "1.kriged_rasters")
OUT_PNG = os.path.join(DOMAIN_DIR, "diagnostics_visual", "all_9_horizons_audit.png")

FILES = [
  ("01_epipalaeolithic_mesolithic_early_neolithic.png", "H1: Epipalaeolithic–Early Neolithic"),
  ("02_chalcolithic_namazga_sarazm_botai.png", "H2: Chalcolithic (Namazga–Sarazm–Botai)"),
  ("03_bronze_age_bmac_sintashta_andronovo.png", "H3: Bronze Age (BMAC–Sintashta–Andronovo)"),
  ("04_iron_age_saka_achaemenid_hellenistic.png", "H4: Iron Age (Saka–Achaemenid–Hellenistic)"),
  ("05_kushan_kangju_wusun_parthian_antiquity.png", "H5: Classical (Kushan–Kangju–Parthian)"),
  ("06_sogdian_turkic_early_islamic.png", "H6: Sogdian–Turkic–Early Islamic"),
  ("07_samanid_karakhanid_seljuk_khwarazmshah.png", "H7: Samanid–Karakhanid–Khwarazmshah"),
  ("08_mongol_chagatai_timurid.png", "H8: Mongol–Chagatai–Timurid"),
  ("09_uzbek_khanates_kazakh_zhuzes.png", "H9: Uzbek Khanates & Kazakh Zhuzes"),
]

plt.rcdefaults()
plt.style.use("default")
fig, axes = plt.subplots(3, 3, figsize=(15, 10), dpi=220)

# Central Asia pixel crop (46..88E, 35..56N)
r0, r1 = int((90 - 56) * 2160 / 180), int((90 - 35) * 2160 / 180)
c0, c1 = int((46 + 180) * 4320 / 360), int((88 + 180) * 4320 / 360)

for ax, (fn, title) in zip(axes.flat, FILES):
  raw = np.asarray(Image.open(os.path.join(KDIR, fn)).convert("RGBA"), dtype=np.uint8)
  f32 = raw.reshape(-1, 4).copy().view(">f4").reshape(raw.shape[:2])
  sub = np.where(np.isfinite(f32) & (f32 > 0), f32, np.nan)[r0:r1, c0:c1]
  vals = sub[np.isfinite(sub)]
  vmin = float(np.percentile(vals, 5)) if vals.size else 1e-4
  vmax = float(np.percentile(vals, 99)) if vals.size else 1.0
  ax.imshow(sub, extent=[46, 88, 35, 56], origin="upper", cmap="viridis", norm=mcolors.LogNorm(vmin=max(1e-5, vmin), vmax=max(vmin * 2, vmax)))
  ax.set_aspect(1.0 / np.cos(np.radians(45.5)))
  ax.set_title(title, fontsize=9)
  ax.tick_params(labelsize=7)

fig.suptitle("SARAY Central Asia: All 9 Non-Stationary Matérn Kriged Archaeological Horizons", fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(OUT_PNG, dpi=220)
plt.close(fig)
print("Saved", OUT_PNG)
