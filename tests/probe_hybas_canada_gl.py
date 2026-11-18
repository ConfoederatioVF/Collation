import shapefile
from shapely.geometry import shape

for label, fname in [
  ("NA_L4", "hybas_na_lev04_v1c.shp"),
  ("AR_L4", "hybas_ar_lev04_v1c.shp"),
  ("GR_L4", "hybas_gr_lev04_v1c.shp"),
]:
  print(f"=== {label} ===")
  sf = shapefile.Reader(f"histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/hydrobasins/{fname}")
  for rec in sf.iterShapeRecords():
    s = shape(rec.shape.__geo_interface__)
    c = (round(s.centroid.x, 1), round(s.centroid.y, 1))
    if c[1] >= 41.0 or label == "GR_L4":
      print(f"  HYBAS={rec.record['HYBAS_ID']} PFAF={rec.record['PFAF_ID']} cen={c} area={round(rec.record['SUB_AREA'])}")
