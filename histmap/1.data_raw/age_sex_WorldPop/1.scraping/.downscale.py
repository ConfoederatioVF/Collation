import os
import glob
import subprocess

# --- PATH HELPER ---
conda_prefix = os.environ.get("CONDA_PREFIX")
gdalwarp_path = "gdalwarp"

if conda_prefix:
    possible_path = os.path.join(
        conda_prefix, "Library", "bin", "gdalwarp.exe"
    )
    if os.path.exists(possible_path):
        gdalwarp_path = possible_path

# --- SETTINGS ---
input_folder = "5arcmin"
output_folder = "5arcmin_out"
resolution = "0.083333333333333"

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

files = glob.glob(os.path.join(input_folder, "*.tif"))
print(f"Using GDAL from: {gdalwarp_path}")
print(f"Found {len(files)} files to process.")

for f in files:
    file_name = os.path.basename(f)
    out_name = file_name.replace(".tif", "_5arc.tif")
    output_path = os.path.join(output_folder, out_name)

    print(f"Processing: {file_name}...")

    cmd = [
        gdalwarp_path,
        "-tr", resolution, resolution,
        "-te", "-180", "-90", "180", "90",
        "-r", "sum",
        "-tap",
        "-multi",
        "-wo", "NUM_THREADS=ALL_CPUS",
        "-co", "COMPRESS=LZW",
        "-co", "PREDICTOR=2",
        f,
        output_path,
    ]

    try:
        subprocess.run(cmd, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error processing {file_name}: {e}")

print("Batch processing complete.")