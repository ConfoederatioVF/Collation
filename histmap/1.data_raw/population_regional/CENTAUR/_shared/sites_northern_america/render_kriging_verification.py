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
    ax.imshow(crop_bg, extent=ext, aspect="auto", origin="upper", interpolation="nearest")

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

    tot_sp = meta.get("total_unique_site_periods", "83,980")
    ax.set_title(f"CENTAUR-II Multi-Registry Archaeological Corpus & Voronoi Catchments\n(Unique Site-Periods: {tot_sp:,} | Domestic: {len(dom_lons):,} | Frontier: {len(fr_lons):,})" if isinstance(tot_sp, int) else "CENTAUR-II Composite Archaeological Corpus", fontsize=12, fontweight="bold")
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
    valid = mask & (land_area > 0)
    dens[valid] = np.maximum(1e-5, raster[valid] / land_area[valid])

    crop_d, ext = crop_extent(dens, lon_min, lon_max, lat_min, lat_max)
    crop_m, _ = crop_extent(mask.astype(np.float32), lon_min, lon_max, lat_min, lat_max)
    crop_l, _ = crop_extent((land_area > 0).astype(np.float32), lon_min, lon_max, lat_min, lat_max)

    bg = np.full((crop_d.shape[0], crop_d.shape[1], 3), [18, 22, 28], dtype=np.uint8)
    bg[crop_l > 0.5] = [44, 46, 52]
    ax.imshow(bg, extent=ext, aspect="auto", origin="upper", interpolation="nearest")

    vals = crop_d[crop_m > 0.5]
    hi = float(np.percentile(vals, 99.6)) if vmax is None and vals.size > 0 else (vmax or 1.0)
    hi = max(hi, 1e-3)
    lo = max(1e-5, hi * 1e-4)

    masked_d = np.ma.masked_where(crop_m <= 0.5, np.clip(crop_d, lo, hi))
    cmap = plt.get_cmap("magma").copy()
    im = ax.imshow(
        masked_d,
        extent=ext,
        aspect="auto",
        origin="upper",
        interpolation="nearest",
        cmap=cmap,
        norm=mcolors.LogNorm(vmin=lo, vmax=hi),
    )
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
        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
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
        fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    fig.suptitle("CENTAUR-II High-Resolution 5-Arcminute Regional Zooms — Fluvial/Coastal Sharpness Audit", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(IMG_DIR / "03_regional_zooms_1200ad.png", dpi=220)
    plt.close(fig)


def render_04_population(na_mask, land_area):
    specs = [
        (-8000, "popc_-8000.png (-8000 AD: Laurentide Retreat)"),
        (-1000, "popc_-1000.png (-1000 AD: Poverty Point / Late Archaic)"),
        (1000, "popc_1000.png (1000 AD: Chaco / Emergent Mississippian)"),
        (1500, "popc_1500.png (1500 AD: Pre-Contact Apex)"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), dpi=220)
    for ax, (yr, title) in zip(axes.ravel(), specs):
        p = NA_DIR / "2.population_rasters" / f"popc_{yr}.png"
        rast = load_float32_geopng(p) if p.exists() else np.zeros((2160, 4320), dtype=np.float32)
        im = plot_density_panel(ax, rast, na_mask, land_area, (-170, -12, 24, 83), title)
        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        cbar.set_label("Density (persons/km², log)", fontsize=8)
    fig.suptitle("CENTAUR-II 2.population_rasters/ Chronological Substrata Preview (-8000 to 1500 AD)", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
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
        fig.colorbar(im_hi, ax=axes[0, idx], fraction=0.035, pad=0.02)

    pop_specs = [
        (1200, "popc_1200.png (1200 AD)"),
        (1780, "popc_1780.png (1780 AD Contact Horizon)"),
    ]
    for idx, (yr, title) in enumerate(pop_specs):
        p = HI_DIR / "2.population_rasters" / f"popc_{yr}.png"
        rast = load_float32_geopng(p) if p.exists() else np.zeros((2160, 4320), dtype=np.float32)
        im_hi = plot_density_panel(axes[1, idx], rast, hi_mask, land_area, (-171.3, -169.3, -14.6, -13.9), f"American Samoa {title}")
        fig.colorbar(im_hi, ax=axes[1, idx], fraction=0.035, pad=0.02)

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
