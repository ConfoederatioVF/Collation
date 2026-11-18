import json, shapefile
from shapely.geometry import shape

sf = shapefile.Reader("histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/hydrobasins/hybas_na_lev04_v1c.shp")
print("=== NA_L4 Maritimes / St Lawrence / Hudson ===")
for rec in sf.iterShapeRecords():
  pf = int(rec.record["PFAF_ID"])
  if 7210 <= pf <= 7319:
    s = shape(rec.shape.__geo_interface__)
    print(f"  HYBAS={rec.record['HYBAS_ID']} PFAF={pf} cen=({s.centroid.x:.2f},{s.centroid.y:.2f}) area={rec.record['SUB_AREA']:.0f}")

# Check NE10 NL polygons (Island of Newfoundland vs Labrador mainland)
ne1 = json.loads(open("histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/ne_10m_admin_1_states_provinces.geojson", encoding="utf-8").read())
for ft in ne1["features"]:
  if ft["properties"].get("adm0_a3") == "CAN" and "Newfoundland" in ft["properties"].get("name", ""):
    g = shape(ft["geometry"])
    parts = [g] if g.geom_type == "Polygon" else list(g.geoms)
    parts.sort(key=lambda p: -p.area)
    for idx, p in enumerate(parts[:6]):
      print(f"  NL part {idx}: area={p.area:.3f}, cen=({p.centroid.x:.2f},{p.centroid.y:.2f}), bounds={[round(x,2) for x in p.bounds]}")
