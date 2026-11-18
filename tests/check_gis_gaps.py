import json
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import shape

W, H = 4320, 2160
CENTAUR = "histmap/1.data_raw/population_regional/CENTAUR"
la = np.asarray(Image.open("histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png").convert("RGBA"), dtype=np.uint8)
land_area = (la[:,:,0].astype(np.uint32)<<24)|(la[:,:,1].astype(np.uint32)<<16)|(la[:,:,2].astype(np.uint32)<<8)|la[:,:,3].astype(np.uint32)

iso_img = np.asarray(Image.open("histmap/1.data_raw/admin_modern/iso2.png").convert("RGBA"), dtype=np.uint8)
iso_rgb = {}
with open("histmap/1.data_raw/admin_modern/iso2_geocodes.csv", encoding="utf-8") as fh:
  next(fh)
  for line in fh:
    parts = line.strip().split(";")
    if len(parts) >= 4 and parts[3]:
      rgb = tuple(int(x) for x in parts[3].split(","))
      iso_rgb[rgb] = parts[0]

packed = (iso_img[:,:,0].astype(np.int32)<<16)|(iso_img[:,:,1].astype(np.int32)<<8)|iso_img[:,:,2].astype(np.int32)
alpha_ok = iso_img[:,:,3] > 0
cent_iso = np.zeros((H, W), dtype=bool)
other_iso = np.zeros((H, W), dtype=bool)
for rgb, code in iso_rgb.items():
  val = (rgb[0]<<16)|(rgb[1]<<8)|rgb[2]
  m = alpha_ok & (packed == val)
  if code.startswith("US-") or code in ("CA", "GL", "PM", "AS", "BM"):
    cent_iso |= m
  else:
    other_iso |= m

# Rasterise NE10 countries for Canada, United States of America (excl PR/VI/GU/MP via bbox), Greenland, Saint Pierre and Miquelon, American Samoa
ne0 = json.loads(open(f"{CENTAUR}/_shared/_gis_cache/ne_10m_admin_0_countries.geojson", encoding="utf-8").read())
im_ne = Image.new("L", (W, H), 0)
dr = ImageDraw.Draw(im_ne)
target_admins = {"Canada", "United States of America", "Greenland", "Saint Pierre and Miquelon", "American Samoa", "Bermuda"}
for feat in ne0["features"]:
  adm = feat["properties"].get("ADMIN")
  if adm in target_admins:
    g = shape(feat["geometry"])
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    for p in polys:
      # Exclude Caribbean PR/VI & Guam/MP in NE USA
      if adm == "United States of America" and p.centroid.x > -68.0:
        continue
      if adm == "United States of America" and 10.0 <= p.centroid.y <= 21.0 and p.centroid.x > 140.0:
        continue
      pts = [((x + 180.0)*12.0, (90.0 - y)*12.0) for x, y in p.exterior.coords]
      if len(pts) >= 3:
        dr.polygon(pts, fill=1)
        for hole in p.interiors:
          hpts = [((x + 180.0)*12.0, (90.0 - y)*12.0) for x, y in hole.coords]
          if len(hpts) >= 3:
            dr.polygon(hpts, fill=0)

ne_mask = np.asarray(im_ne, dtype=bool)
holes = (land_area > 0) & ne_mask & (~cent_iso) & (~other_iso)
print("Old iso2 CENTAUR px:", int((cent_iso & (land_area > 0)).sum()))
print("NE10 unowned holes with land_area > 0:", int(holes.sum()))
rs, cs = np.where(holes)
if len(rs):
  print("Sample hole lat/lon:", [(round(90-(r+0.5)/12, 2), round(-180+(c+0.5)/12, 2)) for r, c in list(zip(rs, cs))[:15]])

# Check historical colonial polygons
for tag in ["1750", "1754_mid", "1763_mid", "1775_mid", "1850_mid"]:
  gj = json.load(open(f"{CENTAUR}/_shared/_gis_cache/historical_layers/atlas_na_{tag}.geojson", encoding="utf-8"))
  print(f"=== {tag} NA polities ===")
  for ft in gj["features"]:
    nm = ft["properties"]["name"]
    pid = ft["properties"]["id"]
    s = shape(ft["geometry"])
    if s.bounds[0] < -45 or s.bounds[2] > -75 and s.bounds[3] > 25:
      if any(k in nm for k in ["France", "British", "Spanish", "Iroquois", "Wabash", "Virginia", "Carolina", "Georgia", "York", "Jersey", "Pennsylvania", "Delaware", "Maryland", "Hampshire", "Massachusetts", "Connecticut", "Rhode", "Florida", "Greenland", "Red River", "United", "Russian", "Transylvania", "Vermont", "Pontiac", "Hawaii", "Powhatan"]):
        print(f"  {pid}: {nm} area={s.area:.2f} bounds={[round(x,1) for x in s.bounds]}")
