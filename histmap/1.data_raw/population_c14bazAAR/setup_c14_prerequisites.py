import os
import sys
import json
import urllib.request
import numpy as np
import cv2
from PIL import Image

def download_and_parse_intcal(url, output_json_path):
    print(f"Downloading calibration curve from {url} ...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        raw_text = resp.read().decode('utf-8', errors='ignore')
    
    cal_bp = []
    c14_age = []
    sigma = []
    delta_14c = []
    delta_sigma = []
    
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.replace(',', ' ').split()]
        if len(parts) >= 3:
            try:
                cbp = float(parts[0])
                c14 = float(parts[1])
                sig = float(parts[2])
                cal_bp.append(cbp)
                c14_age.append(c14)
                sigma.append(sig)
                if len(parts) >= 5:
                    delta_14c.append(float(parts[3]))
                    delta_sigma.append(float(parts[4]))
            except ValueError:
                continue
                
    curve_data = {
        'cal_bp': cal_bp,
        'c14_age': c14_age,
        'sigma': sigma
    }
    if delta_14c:
        curve_data['delta_14c'] = delta_14c
        curve_data['delta_sigma'] = delta_sigma
        
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(curve_data, f)
    print(f"Saved {len(cal_bp)} calibration points to {output_json_path}")

def rasterize_wmobb(basins_geojson_path, output_png_path, output_meta_path):
    print(f"Loading WMO basins GeoJSON from {basins_geojson_path} ...")
    with open(basins_geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    width = 4320
    height = 2160
    img = np.zeros((height, width), dtype=np.int32)
    metadata = {}
    
    features = data.get('features', [])
    print(f"Processing {len(features)} watershed basin features ...")
    
    for f in features:
        props = f.get('properties', {})
        wmobb = int(props['WMOBB'])
        metadata[str(wmobb)] = {
            'objectid': int(props.get('OBJECTID') or 0),
            'wmobb': wmobb,
            'name': props.get('WMOBB_NAME') or '',
            'basin': props.get('WMOBB_BASIN') or '',
            'subbasin': props.get('WMOBB_SUBBASIN') or '',
            'region': props.get('REGNAME') or '',
            'region_num': int(props.get('REGNUMBER') or 0),
            'sub_area': float(props.get('SUM_SUB_AREA') or 0)
        }
        
        geom = f.get('geometry', {})
        gtype = geom.get('type')
        coords = geom.get('coordinates', [])
        
        def process_poly(poly):
            if not poly:
                return
            exterior = poly[0]
            pts = []
            for lon, lat in exterior:
                px = int(np.clip(np.round((lon + 180.0) / 360.0 * width), 0, width - 1))
                py = int(np.clip(np.round((90.0 - lat) / 180.0 * height), 0, height - 1))
                pts.append([px, py])
            if len(pts) >= 3:
                pts_arr = np.array([pts], dtype=np.int32)
                cv2.fillPoly(img, pts_arr, wmobb)
                
        if gtype == 'Polygon':
            process_poly(coords)
        elif gtype == 'MultiPolygon':
            for poly in coords:
                process_poly(poly)
                
    print(f"Unique rasterized basins: {len(np.unique(img))} (non-zero pixels: {np.sum(img > 0)})")
    
    # Save metadata JSON
    os.makedirs(os.path.dirname(output_meta_path), exist_ok=True)
    with open(output_meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved watershed metadata to {output_meta_path}")
    
    # Save int32 RGBA GeoPNG
    arr_u32 = img.astype(np.uint32)
    rgba = np.zeros((*img.shape, 4), dtype=np.uint8)
    rgba[..., 0] = (arr_u32 >> 24) & 0xFF
    rgba[..., 1] = (arr_u32 >> 16) & 0xFF
    rgba[..., 2] = (arr_u32 >> 8) & 0xFF
    rgba[..., 3] = arr_u32 & 0xFF
    
    os.makedirs(os.path.dirname(output_png_path), exist_ok=True)
    pil_img = Image.fromarray(rgba, mode="RGBA")
    pil_img.save(output_png_path, "PNG", optimize=True)
    print(f"Saved WMO basin raster to {output_png_path} ({os.path.getsize(output_png_path)} bytes)")

if __name__ == '__main__':
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    config_dir = os.path.join(base_dir, "histmap", "2.data_cleaning", "population_c14bazAAR", "config")
    
    # 1. IntCal20 & SHCal20
    intcal20_url = "https://intcal.org/curves/intcal20.14c"
    shcal20_url = "https://intcal.org/curves/shcal20.14c"
    download_and_parse_intcal(intcal20_url, os.path.join(config_dir, "intcal20.json"))
    download_and_parse_intcal(shcal20_url, os.path.join(config_dir, "shcal20.json"))
    
    # 2. Watershed Rasterization
    basins_path = os.path.join(base_dir, "histmap", "1.data_raw", "watersheds_WMO", "wmobb_basins.json")
    raster_path = os.path.join(config_dir, "wmobb_raster.png")
    meta_path = os.path.join(config_dir, "wmobb_metadata.json")
    rasterize_wmobb(basins_path, raster_path, meta_path)
    print("Prerequisites setup complete!")
