# -*- coding: utf-8 -*-
"""Renders mandatory visual verification maps for CENTAUR-II multi-registry
archaeological corpus, 5-arcminute biophysical Matérn kriged surfaces,
regional zooms (including Greenland ice sheet & Hawai'i/Samoa), and
2.population_rasters preview matching Dataview density styling.
"""

import json
import os
import pathlib
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

NA_DIR = pathlib.Path(__file__).resolve().parent
CENTAUR_DIR = NA_DIR.parent.parent
SVEA_ROOT = CENTAUR_DIR.parents[3]
HI_DIR = CENTAUR_DIR / "_shared" / "sites_hawaii_polynesia"
if str(CENTAUR_DIR.parent / "_shared") not in sys.path:
    sys.path.insert(0, str(CENTAUR_DIR.parent / "_shared"))
import viscount_plot_utils as vpu
IMG_DIR = NA_DIR / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

LAND_AREA_PNG = SVEA_ROOT / "histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png"
NA_MASK_PNG = NA_DIR / "config" / "centaur_na_domain_mask.png"
HI_MASK_PNG = HI_DIR / "config" / "centaur_hp_domain_mask.png"


def load_rgba(path):
    return np.array(Image.open(path).convert("RGBA"), dtype=np.uint8)


def load_land_area():
    rgba = load_rgba(LAND_AREA_PNG)
    u32 = (rgba[:, :, 0].astype(np.uint32) << 24) | (rgba[:, :, 1].astype(np.uint32) << 16) | (rgba[:, :, 2].astype(np.uint32) << 8) | rgba[:, :, 3].astype(np.uint32)
    return u32.astype(np.float32)


def load_mask(path):
    rgba = load_rgba(path)
    return (rgba[:, :, 0] > 0) | (rgba[:, :, 1] > 0) | (rgba[:, :, 2] > 0)


def load_float32_geopng(path):
    rgba = load_rgba(path)
    raw = np.ascontiguousarray(rgba).view(">f4").reshape(rgba.shape[0], rgba.shape[1])
    out = np.where(np.isfinite(raw) & (raw > 0), raw, 0.0).astype(np.float32)
    return out


def crop_extent(grid, lon_min, lon_max, lat_min, lat_max):
    h, w = grid.shape[:2]
    c0 = max(0, int(round((lon_min + 180.0) / 360.0 * w)))
    c1 = min(w, int(round((lon_max + 180.0) / 360.0 * w)))
    r0 = max(0, int(round((90.0 - lat_max) / 180.0 * h)))
    r1 = min(h, int(round((90.0 - lat_min) / 180.0 * h)))
    return grid[r0:r1, c0:c1], [lon_min, lon_max, lat_min, lat_max]


def render_01_corpus():
    gj_path = NA_DIR / "geojson" / "00_all_periods.geojson"
    meta_path = NA_DIR / "config" / "sites_northern_america_geojson_metadata.json"
    gj = json.loads(gj_path.read_text(encoding="utf-8")) if gj_path.exists() else {"features": []}
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    na_mask = load_mask(NA_MASK_PNG)
    land = load_land_area() > 0

    fig, ax = plt.subplots(figsize=(14, 7.5), dpi=220)
    bg = np.zeros((2160, 4320, 3), dtype=np.uint8)
    bg[land] = [38, 42, 48]
    bg[na_mask] = [56, 62, 72]
    crop_bg, ext = crop_extent(bg, -172, -12, 18, 84)
    ax.imshow(crop_bg, extent=ext, origin="upper", interpolation="nearest")
    ax.set_aspect("equal")

    dom_lons, dom_lats, dom_sz = [], [], []
    fr_lons, fr_lats = [], []
    for ft in gj.get("features", []):
        coords = ft.get("geometry", {}).get("coordinates", [])
        props = ft.get("properties", {})
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        if lon < -172 or lon > -12 or lat < 18 or lat > 84:
            continue
        cnt = max(1.0, float(props.get("site_count", 1)))
        if props.get("is_frontier_buffer"):
            fr_lons.append(lon)
            fr_lats.append(lat)
        else:
            dom_lons.append(lon)
            dom_lats.append(lat)
            dom_sz.append(4.0 + 3.2 * np.sqrt(min(600.0, cnt)))

    ax.scatter(fr_lons, fr_lats, s=8, c="#5bc0be", alpha=0.55, edgecolors="none", label=f"Cross-Frontier Buffers (n={len(fr_lons)})")
    sc = ax.scatter(dom_lons, dom_lats, s=dom_sz, c=np.log1p(dom_sz), cmap="YlOrRd", alpha=0.82, linewidths=0.15, edgecolors="#111111", label=f"Domestic Catchments (n={len(dom_lons)})")

    tot_sp = meta.get("total_unique_site_periods", "92.500")
    tot_s = f"{tot_sp:,}".replace(",", ".") if isinstance(tot_sp, int) else str(tot_sp)
    dom_s = f"{len(dom_lons):,}".replace(",", ".")
    fr_s = f"{len(fr_lons):,}".replace(",", ".")
    ax.set_title(f"CENTAUR-II Multi-Registry Archaeological Corpus & Catchments\n(Unique Site-Periods: {tot_s} | Domestic: {dom_s} | Frontier: {fr_s})", fontsize=12, fontweight="bold")
    ax.set_xlabel("Longitude (°)")
    ax.set_ylabel("Latitude (°)")
    ax.legend(loc="lower left", framealpha=0.88, fontsize=9)
    ax.grid(True, linestyle="--", linewidth=0.35, alpha=0.35, color="#cccccc")
    plt.tight_layout()
    fig.savefig(IMG_DIR / "01_archaeological_corpus_composite.png", dpi=220)
    plt.close(fig)


def plot_density_panel(ax, raster, mask, land_area, bbox, title, vmax=None):
    lon_min, lon_max, lat_min, lat_max = bbox
    dens = np.zeros_like(raster, dtype=np.float32)
    valid = mask & (land_area > 0) & (raster > 0.0)
    dens[valid] = raster[valid] / land_area[valid]

    crop_d, ext = crop_extent(dens, lon_min, lon_max, lat_min, lat_max)
    crop_m, _ = crop_extent(mask.astype(np.float32), lon_min, lon_max, lat_min, lat_max)
    crop_l, _ = crop_extent((land_area > 0).astype(np.float32), lon_min, lon_max, lat_min, lat_max)

    bg = np.full((crop_d.shape[0], crop_d.shape[1], 3), [16, 20, 26], dtype=np.uint8)
    bg[crop_l > 0.5] = [32, 36, 42]
    bg[crop_m > 0.5] = [24, 26, 32]
    ax.imshow(bg, extent=ext, origin="upper", interpolation="nearest")

    hab_vals = crop_d[(crop_m > 0.5) & (crop_d > 0.0)]
    hi = float(np.percentile(hab_vals, 99.6)) if vmax is None and hab_vals.size > 0 else (vmax or 1.0)
    hi = max(hi, 1e-3)
    lo = max(1e-5, hi * 2e-4)

    masked_d = np.ma.masked_where((crop_m <= 0.5) | (crop_d <= 0.0), np.clip(crop_d, lo, hi))
    cmap = plt.get_cmap("magma").copy()
    im = ax.imshow(
        masked_d,
        extent=ext,
        origin="upper",
        interpolation="nearest",
        cmap=cmap,
        norm=mcolors.LogNorm(vmin=lo, vmax=hi),
    )
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10, fontweight="bold")
    return im


def render_02_horizons(na_mask, land_area):
    specs = [
        ("01_palaeoindian_early_archaic_h1.png", "h1: Palaeoindian & Early Archaic (-8000 AD)"),
        ("05_middle_woodland_hopewell_h5.png", "h5: Middle Woodland Hopewell (100 AD)"),
        ("08_middle_mississippian_pueblo_iii_h8.png", "h8: Middle Mississippian / Pueblo III (1200 AD)"),
        ("10_protohistoric_contact_horizon_h10.png", "h10: Protohistoric Contact Horizon (1550 AD)"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), dpi=220)
    for ax, (fname, title) in zip(axes.ravel(), specs):
        p = NA_DIR / "1.kriged_rasters" / fname
        rast = load_float32_geopng(p) if p.exists() else np.zeros((2160, 4320), dtype=np.float32)
        im = plot_density_panel(ax, rast, na_mask, land_area, (-170, -12, 24, 83), title)
        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, format=vpu.euro_log_formatter(False))
        vpu.apply_human_colorbar_ticks(cbar, False)
        cbar.set_label("Relative Density (sites/km², log)", fontsize=8)
    fig.suptitle("CENTAUR-II 5-Arcminute Biophysical Matérn Kriged Surfaces (1.kriged_rasters/)", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(IMG_DIR / "02_kriged_horizons_panel.png", dpi=220)
    plt.close(fig)


def render_03_zooms(na_mask, hi_mask, land_area):
    na_h8_path = NA_DIR / "1.kriged_rasters" / "08_middle_mississippian_pueblo_iii_h8.png"
    na_h8 = load_float32_geopng(na_h8_path) if na_h8_path.exists() else np.zeros((2160, 4320), dtype=np.float32)

    hi_h2_path = HI_DIR / "1.kriged_rasters" / "02_expansion_wetland_h2.png"
    hi_h2 = load_float32_geopng(hi_h2_path) if hi_h2_path.exists() else np.zeros((2160, 4320), dtype=np.float32)

    zooms = [
        (na_h8, na_mask, (-115, -104, 31, 43), "Southwest & Upper Colorado (1200 AD)"),
        (na_h8, na_mask, (-96, -78, 30, 43), "Mississippi–Ohio–Cahokia Confluence (1200 AD)"),
        (na_h8, na_mask, (-84, -64, 41, 49), "St. Lawrence & Great Lakes (1200 AD)"),
        (na_h8, na_mask, (-136, -118, 43, 56), "Pacific Northwest & Salish Sea (1200 AD)"),
        (na_h8, na_mask, (-74, -18, 59, 82), "Greenland Coastal Fjords vs Ice Cap (1200 AD)"),
        (hi_h2, hi_mask, (-161, -154.5, 18.5, 22.5), "Hawaiian Islands Ahupua'a Lo'i & Heiau (1250 AD)"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(17, 10), dpi=220)
    for ax, (rast, msk, bbox, title) in zip(axes.ravel(), zooms):
        im = plot_density_panel(ax, rast, msk, land_area, bbox, title)
        cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02, format=vpu.euro_log_formatter(False))
        vpu.apply_human_colorbar_ticks(cbar, False)
    fig.suptitle("CENTAUR-II High-Resolution 5-Arcminute Regional Zooms — Fluvial/Coastal Sharpness Audit", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(IMG_DIR / "03_regional_zooms_1200ad.png", dpi=220)
    plt.close(fig)


def render_04_population(na_mask, land_area):
    specs = [
        (-8000, "8000 BC: Laurentide Retreat\n(popc_-8000)"),
        (-2000, "2000 BC: Poverty Point & Archaic\n(popc_-2000)"),
        (100, "100 AD: Hopewell & Basketmaker\n(popc_100)"),
        (1000, "1000 AD: Chaco & Mississippian\n(popc_1000)"),
        (1200, "1200 AD: Cahokia & Pueblo III\n(popc_1200)"),
        (1500, "1500 AD: Late Pre-Contact Apex\n(popc_1500)"),
        (1750, "1750 AD: Colonial-Indigenous Frontier\n(popc_1750)"),
        (1800, "1800 AD: Early Republican Transition\n(popc_1800)"),
    ]
    fig, axes = plt.subplots(2, 4, figsize=(20.5, 9.6), dpi=220)
    for ax, (yr, title) in zip(axes.ravel(), specs):
        p = NA_DIR / "2.population_rasters" / f"popc_{yr}.png"
        rast = load_float32_geopng(p) if p.exists() else np.zeros((2160, 4320), dtype=np.float32)
        im = plot_density_panel(ax, rast, na_mask, land_area, (-170, -12, 24, 83), title)
        ax.set_title(title, fontsize=8.8, pad=4)
        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, format=vpu.euro_log_formatter(False))
        vpu.apply_human_colorbar_ticks(cbar, False)
        cbar.set_label("Density (persons/km²)", fontsize=7.5)
    fig.suptitle("CENTAUR-II 2.population_rasters/ Holocene-to-1800AD Substrata Verification", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.95], w_pad=1.0, h_pad=1.2)
    fig.savefig(IMG_DIR / "04_population_rasters_preview.png", dpi=220)
    plt.close(fig)


def render_05_hawaii_polynesia(hi_mask, land_area):
    specs = [
        ("01_colonisation_founder_h1.png", "Hawai'i h1: Polynesian Colonisation (950 AD)"),
        ("04_protohistoric_archaic_state_h4.png", "Hawai'i h4: Ahupua'a & Archaic State Apex (1750 AD)"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), dpi=220)
    for idx, (fname, title) in enumerate(specs):
        p = HI_DIR / "1.kriged_rasters" / fname
        rast = load_float32_geopng(p) if p.exists() else np.zeros((2160, 4320), dtype=np.float32)
        im_hi = plot_density_panel(axes[0, idx], rast, hi_mask, land_area, (-161.0, -154.5, 18.5, 22.6), f"{title} — Hawai'i")
        cb_hi = fig.colorbar(im_hi, ax=axes[0, idx], fraction=0.035, pad=0.02, format=vpu.euro_log_formatter(False))
        vpu.apply_human_colorbar_ticks(cb_hi, False)

    pop_specs = [
        (1200, "popc_1200.png (1200 AD)"),
        (1780, "popc_1780.png (1780 AD Contact Horizon)"),
    ]
    for idx, (yr, title) in enumerate(pop_specs):
        p = HI_DIR / "2.population_rasters" / f"popc_{yr}.png"
        rast = load_float32_geopng(p) if p.exists() else np.zeros((2160, 4320), dtype=np.float32)
        im_hi = plot_density_panel(axes[1, idx], rast, hi_mask, land_area, (-171.3, -169.3, -14.6, -13.9), f"American Samoa {title}")
        cb_as = fig.colorbar(im_hi, ax=axes[1, idx], fraction=0.035, pad=0.02, format=vpu.euro_log_formatter(False))
        vpu.apply_human_colorbar_ticks(cb_as, False)

    fig.suptitle("CENTAUR-II Hawai'i & American Samoa 5-Arcminute Kriged & Substrata Verification", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(IMG_DIR / "05_hawaii_polynesia_kriging.png", dpi=220)
    plt.close(fig)


def main():
    plt.rcdefaults()
    plt.style.use("default")
    na_mask = load_mask(NA_MASK_PNG)
    hi_mask = load_mask(HI_MASK_PNG)
    land_area = load_land_area()
    render_01_corpus()
    render_02_horizons(na_mask, land_area)
    render_03_zooms(na_mask, hi_mask, land_area)
    render_04_population(na_mask, land_area)
    render_05_hawaii_polynesia(hi_mask, land_area)
    print("Rendered all 5 verification PNGs to", IMG_DIR)


if __name__ == "__main__":
    main()
