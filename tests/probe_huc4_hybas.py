import json
import shapefile
from shapely.geometry import shape

h4 = json.load(open("histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/usgs_wbd_huc4.geojson", encoding="utf-8"))
for f in h4["features"]:
  p = f["properties"]
  if str(p["huc4"])[:2] in ("04", "09", "16", "18", "20"):
    s = shape(f["geometry"])
    b = [round(x, 2) for x in s.bounds]
    c = (round(s.centroid.x, 2), round(s.centroid.y, 2))
    print(f"HUC4 {p['huc4']} {p['name']}: area_deg2={s.area:.2f}, cen={c}, b={b}")

print("=== hybas_gr_lev04 ===")
sf = shapefile.Reader("histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/hydrobasins/hybas_gr_lev04_v1c.shp")
for rec in sf.iterShapeRecords():
  s = shape(rec.shape.__geo_interface__)
  c = (round(s.centroid.x, 2), round(s.centroid.y, 2))
  print(" ", rec.record.as_dict(), "cen=", c, "area_km2=", rec.record["SUB_AREA"])
