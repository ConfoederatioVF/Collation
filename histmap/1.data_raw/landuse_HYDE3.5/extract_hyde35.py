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

def encode_percentage_geopng(arr):
    max_val = np.max(arr)
    pct_rgba = np.zeros((*arr.shape, 4), dtype=np.uint8)
    if max_val > 0:
        norm = np.clip(np.round((arr / max_val) * 255.0), 0, 255).astype(np.uint8)
        mask = arr > 0
        pct_rgba[:, :, 1] = np.where(mask, norm, 0)
        pct_rgba[:, :, 3] = np.where(mask, 255, 0)
    return Image.fromarray(pct_rgba, mode="RGBA")

def get_hyde_year_name(year):
    return f"{abs(year)}{'AD' if year >= 0 else 'BC'}"

def get_hyde_years():
    return (
        [-10000 + i * 1000 for i in range(10)] +  # -10000 to -1000 (10)
        [i * 100 for i in range(18)] +             # 0 to 1700 (18)
        [1710 + i * 10 for i in range(25)] +       # 1710 to 1950 (25)
        [1951 + i for i in range(75)]              # 1951 to 2025 (75)
    )

VAR_SPECS = [
    ("cropland.nc", "cropland", "cropland"),
    ("grazing_land.nc", "grazing_land", "grazing"),
    ("irrigated_not_rice.nc", "irrigated_not_rice", "ir_norice"),
    ("irrigated_rice.nc", "irrigated_rice", "ir_rice"),
    ("pasture.nc", "pasture", "pasture"),
    ("population.nc", "population", "popc_"),
    ("population_density.nc", "population_density", "popd_"),
    ("rainfed_not_rice.nc", "rainfed_not_rice", "rf_norice"),
    ("rainfed_rice.nc", "rainfed_rice", "rf_rice"),
    ("rangeland.nc", "rangeland", "rangeland"),
    ("rural_population.nc", "rural_population", "rurc_"),
    ("total_irrigated.nc", "total_irrigated", "tot_irri"),
    ("total_rainfed.nc", "total_rainfed", "tot_rainfed"),
    ("total_rice.nc", "total_rice", "tot_rice"),
    ("urban_area.nc", "urban_area", "uopp_"),
    ("urban_population.nc", "urban_population", "urbc_"),
]

def _process_timestep_batch(args):
    raw_dir, output_dir, t_indices, years = args
    
    # Open datasets once per worker process
    datasets = {}
    for nc_file, var_name, prefix in VAR_SPECS:
        full_nc = os.path.join(raw_dir, nc_file)
        if os.path.exists(full_nc):
            datasets[prefix] = (nc.Dataset(full_nc, "r"), var_name)
            
    processed_count = 0
    for t_idx in t_indices:
        y = years[t_idx]
        y_name = get_hyde_year_name(y)
        
        # Check if all files for this timestep already exist
        all_exist = True
        for _, _, prefix in VAR_SPECS:
            num_path = os.path.join(output_dir, f"{prefix}{y_name}_number.png")
            pct_path = os.path.join(output_dir, f"{prefix}{y_name}_percentage.png")
            if not (os.path.exists(num_path) and os.path.exists(pct_path)):
                all_exist = False
                break
        conv_num_path = os.path.join(output_dir, f"conv_rangeland{y_name}_number.png")
        conv_pct_path = os.path.join(output_dir, f"conv_rangeland{y_name}_percentage.png")
        if not (os.path.exists(conv_num_path) and os.path.exists(conv_pct_path)):
            all_exist = False
            
        if all_exist:
            processed_count += 1
            continue
            
        cached_slices = {}
        for prefix, (ds, var_name) in datasets.items():
            raw_slice = ds.variables[var_name][t_idx, :, :]
            if hasattr(raw_slice, "mask"):
                arr = np.where(raw_slice.mask, 0.0, raw_slice.data)
            else:
                arr = np.where(raw_slice < 0, 0.0, raw_slice)
            arr = arr.astype(np.float32)
            cached_slices[prefix] = arr
            
            num_path = os.path.join(output_dir, f"{prefix}{y_name}_number.png")
            pct_path = os.path.join(output_dir, f"{prefix}{y_name}_percentage.png")
            
            encode_float32_geopng(arr).save(num_path)
            encode_percentage_geopng(arr).save(pct_path)
            
        # Compute derived conv_rangeland
        if "grazing" in cached_slices and "pasture" in cached_slices and "rangeland" in cached_slices:
            conv_arr = np.maximum(
                0.0,
                cached_slices["grazing"] - cached_slices["pasture"] - cached_slices["rangeland"]
            ).astype(np.float32)
            
            encode_float32_geopng(conv_arr).save(conv_num_path)
            encode_percentage_geopng(conv_arr).save(conv_pct_path)
            
        processed_count += 1
        
    for ds, _ in datasets.values():
        ds.close()
        
    return processed_count

def extract_all_hyde_parallel(raw_dir, output_dir, num_workers=10):
    os.makedirs(output_dir, exist_ok=True)
    years = get_hyde_years()
    assert len(years) == 128
    
    total_timesteps = len(years)
    # Partition timesteps into batches for workers
    batches = [[] for _ in range(num_workers)]
    for i in range(total_timesteps):
        batches[i % num_workers].append(i)
        
    tasks = [(raw_dir, output_dir, batch, years) for batch in batches if len(batch) > 0]
    
    print(f"[HYDE3.5] Launching parallel extraction for 128 timesteps across {len(tasks)} workers...")
    with ProcessPoolExecutor(max_workers=len(tasks)) as executor:
        results = list(executor.map(_process_timestep_batch, tasks))
        
    print(f"[HYDE3.5] Completed extracting all timesteps (batches: {results}).")

if __name__ == "__main__":
    t0 = time.time()
    raw_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(os.path.join(raw_dir, "../../2.data_cleaning/landuse_HYDE/rasters"))
    extract_all_hyde_parallel(raw_dir, output_dir, num_workers=10)
    print(f"Extraction completed in {time.time() - t0:.2f} seconds.")
