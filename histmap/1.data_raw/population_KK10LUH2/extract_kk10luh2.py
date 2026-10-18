import os
import sys
import time
import numpy as np
import netCDF4 as nc
from PIL import Image
from concurrent.futures import ProcessPoolExecutor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

def encode_float32_geopng(arr):
    arr_f32 = arr.astype(np.float32)
    rgba = arr_f32.byteswap().view(np.uint8).reshape((*arr_f32.shape, 4))
    return Image.fromarray(rgba, mode="RGBA")

def is_valid_geopng(path):
    if not os.path.exists(path):
        return False
    try:
        with Image.open(path) as im:
            return im.mode == "RGBA" and im.size == (4320, 2160)
    except Exception:
        return False

def load_5arcmin_land_mask(base_dir):
    land_area_path = os.path.abspath(os.path.join(base_dir, "..", "..", "1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png"))
    if not os.path.exists(land_area_path):
        land_area_path = os.path.abspath(os.path.join(base_dir, "..", "metadata_HYDE", "general_rasters", "land_area.png"))
    if os.path.exists(land_area_path):
        try:
            with Image.open(land_area_path) as im:
                arr = np.array(im, dtype=np.uint32)
                int32_arr = (arr[:, :, 0] << 24) | (arr[:, :, 1] << 16) | (arr[:, :, 2] << 8) | arr[:, :, 3]
                return int32_arr > 0
        except Exception as e:
            print(f"[Warning] Failed to load land area mask from {land_area_path}: {e}")
    return None

def extract_kk10(base_dir, land_mask=None, force=False):
    kk10_nc_path = os.path.join(base_dir, "KK10.nc")
    output_dir = os.path.join(base_dir, "KK10")
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(kk10_nc_path):
        print(f"[KK10] File not found: {kk10_nc_path}")
        return
        
    print(f"[KK10] Checking KK10 rasters in {output_dir} ...")
    ds = None
    
    hyde_years_kk10 = [
        -6000, -5000, -4000, -3000, -2000, -1000,
        0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
        1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790, 1800, 1810, 1820, 1830, 1840, 1850
    ]
    
    rendered_count = 0
    for y in hyde_years_kk10:
        out_path = os.path.join(output_dir, f"KK10_{y}.png")
        if not force and is_valid_geopng(out_path):
            continue
            
        if ds is None:
            print(f"[KK10] Opening {kk10_nc_path} ...")
            ds = nc.Dataset(kk10_nc_path, "r")
            year_var = list(ds.variables["year"][:])
            land_use_var = ds.variables["land_use"]
            
        lookup_year = -1 if y == 0 else y
        if lookup_year not in year_var:
            print(f"[KK10] Warning: Year {y} (lookup {lookup_year}) not in dataset, skipping.")
            continue
            
        t_idx = year_var.index(lookup_year)
        raw_slice = land_use_var[t_idx, :, :]
        
        if hasattr(raw_slice, "mask"):
            arr = np.where(raw_slice.mask, 0.0, raw_slice.data)
        else:
            arr = np.where(raw_slice < 0, 0.0, raw_slice)
            
        arr = np.clip(arr, 0.0, 1.0).astype(np.float32)
        arr = np.flipud(arr)
        if land_mask is not None:
            arr = np.where(land_mask, arr, 0.0)
        
        img = encode_float32_geopng(arr)
        img.save(out_path)
        rendered_count += 1
        print(f"[KK10] Rendered {out_path} (sum: {np.sum(arr):.4f}, max: {np.max(arr):.4f})")
        
    if ds is not None:
        ds.close()
    print(f"[KK10] KK10 rasters verified ({rendered_count} newly rendered).")

def _process_single_luh2_variable(args):
    nc_path, nc_var, folder_name, luh2_dir, hyde_years, land_mask, force = args
    sub_dir = os.path.join(luh2_dir, folder_name)
    os.makedirs(sub_dir, exist_ok=True)
    
    ds = nc.Dataset(nc_path, "r")
    var_obj = ds.variables[nc_var]
    
    count = 0
    for y in hyde_years:
        out_path = os.path.join(sub_dir, f"LUH2_{folder_name}_{y}.png")
        if not force and is_valid_geopng(out_path):
            continue
            
        t_idx = y - 850
        if t_idx < 0 or t_idx >= var_obj.shape[2]:
            continue
            
        raw_slice = var_obj[:, :, t_idx]
        if hasattr(raw_slice, "mask"):
            arr = np.where(raw_slice.mask, 0.0, raw_slice.data)
        else:
            arr = np.where(raw_slice < 0, 0.0, raw_slice)
            
        arr = arr.astype(np.float32)
        arr = np.flipud(arr)
        
        im_temp = Image.fromarray(arr, mode="F")
        im_resized = im_temp.resize((4320, 2160), resample=Image.BILINEAR)
        arr_up = np.clip(np.array(im_resized, dtype=np.float32), 0.0, 1.0)
        if land_mask is not None:
            arr_up = np.where(land_mask, arr_up, 0.0)
        
        img_out = encode_float32_geopng(arr_up)
        img_out.save(out_path)
        count += 1
        
    ds.close()
    return folder_name, count

def extract_luh2_parallel(base_dir, land_mask=None, force=False):
    luh2_nc_path = os.path.join(base_dir, "LUH2_GCB2019_states.nc4")
    luh2_dir = os.path.join(base_dir, "LUH2")
    os.makedirs(luh2_dir, exist_ok=True)
    
    if not os.path.exists(luh2_nc_path):
        print(f"[LUH2] File not found: {luh2_nc_path}")
        return
        
    var_map = {
        "c3ann": "c3ann",
        "c3nfx": "c3nfx",
        "c3per": "c3per",
        "c4ann": "c4ann",
        "c4per": "c4per",
        "pastr": "pasture",
        "urban": "urban"
    }
    
    hyde_years_luh2 = [
        900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
        1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790, 1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940, 1950,
        *list(range(1951, 2019))
    ]
    
    tasks = [
        (luh2_nc_path, nc_var, folder_name, luh2_dir, hyde_years_luh2, land_mask, force)
        for nc_var, folder_name in var_map.items()
    ]
    
    print(f"[LUH2] Launching parallel extraction for 7 variables across 7 workers (force={force})...")
    with ProcessPoolExecutor(max_workers=7) as executor:
        for folder_name, count in executor.map(_process_single_luh2_variable, tasks):
            print(f"[LUH2] Finished {folder_name} ({count} rasters rendered).")
            
    print("[LUH2] Finished extracting all LUH2 rasters.")

if __name__ == "__main__":
    t0 = time.time()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    force = ("--force" in sys.argv or "--overwrite" in sys.argv)
    land_mask = load_5arcmin_land_mask(script_dir)
    if land_mask is not None:
        print(f"[LandMask] Successfully loaded 5-arcminute land mask ({np.sum(land_mask)} land cells).")
    else:
        print("[LandMask] Warning: 5-arcminute land mask could not be loaded!")
    extract_kk10(script_dir, land_mask=land_mask, force=force)
    extract_luh2_parallel(script_dir, land_mask=land_mask, force=force)
    print(f"Extraction completed in {time.time() - t0:.2f} seconds.")
