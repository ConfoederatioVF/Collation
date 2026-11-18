import json, urllib.request, shapefile
from shapely.geometry import shape

# 1. Fetch USGS WBD HUC6 for 0902 and 1710 (MapServer/3)
out_feats = []
for h4 in ["0902", "1710"]:
  u = f"https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/3/query?where=huc6+LIKE+%27{h4}%25%27&outFields=huc6,name,areasqkm&maxAllowableOffset=0.015&f=geojson"
  gj = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "SVEA/1.0"}), timeout=15).read().decode("utf-8"))
  for f in gj.get("features", []):
    out_feats.append(f)
    print("HUC6:", f["properties"])
with open("histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/usgs_wbd_huc6_extra.geojson", "w", encoding="utf-8") as fh:
  json.dump({"type": "FeatureCollection", "features": out_feats}, fh)

# 2. Check 1782 State of Vermont & 1750 New France / British NA / Iroquois / Spanish America / 13 Colonies
for tag in ["1750", "1763_mid", "1775_mid", "1782"]:
  gj = json.load(open(f"histmap/1.data_raw/population_regional/CENTAUR/_shared/_gis_cache/historical_layers/atlas_na_{tag}.geojson", encoding="utf-8"))
  for ft in gj["features"]:
    pid = str(ft["properties"]["id"])
    if pid in ("5493", "5482", "5428", "5429", "4427", "4684", "4066", "5384"):
      print(tag, pid, ft["properties"]["name"], [round(x, 2) for x in shape(ft["geometry"]).bounds])
