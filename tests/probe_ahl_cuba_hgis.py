import urllib.request, urllib.parse, re, zipfile, struct, json
from collections import Counter

hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 1. Inspect AHL HTML tail & arbol.js tail for busqueda / download endpoint
html = urllib.request.urlopen(urllib.request.Request("https://www.inegi.org.mx/app/geo2/ahl/", headers=hdr), timeout=15).read().decode("utf-8", errors="replace")
print("=== AHL HTML TAIL ===")
print(html[4500:])
js_a = urllib.request.urlopen(urllib.request.Request("https://www.inegi.org.mx/app/geo2/ahl/js/arbol.js", headers=hdr), timeout=15).read().decode("utf-8", errors="replace")
print("=== ARBOL.JS TAIL ===")
print(js_a[4000:])
js_m = urllib.request.urlopen(urllib.request.Request("https://www.inegi.org.mx/app/geo2/ahl/js/mensajes-bootstrap.js", headers=hdr), timeout=15).read().decode("utf-8", errors="replace")
print("=== MENSAJES.JS endpoints ===", re.findall(r'[A-Za-z0-9_/-]+\.do\b', js_m))
# Check if cargaCatalogos.do works directly!
try:
  r = urllib.request.urlopen(urllib.request.Request("https://www.inegi.org.mx/app/geo2/ahl/cargaCatalogos.do?cat=entidades", headers=hdr), timeout=10).read().decode("utf-8", errors="replace")
  print("cargaCatalogos.do?cat=entidades ->", r[:300])
except Exception as e:
  print("cargaCatalogos ERR:", e)

# 2. Check Cuba, Honduras, Panama, Bahamas, Mexico citypop sublinks
print("\n=== CITYPOP FULL LINK TREE ===")
for sl in ["cuba", "honduras", "panama", "bahamas", "domrep", "mexico"]:
  u = f"https://www.citypopulation.de/en/{sl}/"
  h = urllib.request.urlopen(urllib.request.Request(u, headers=hdr), timeout=12).read().decode("utf-8", errors="replace")
  ls = sorted(set(re.findall(r'href="([^"]+)"', h)))
  ls = [l for l in ls if not l.startswith(("http", "#", "/css", "/js", "/img", "/en/world", "/en/america", "/en/africa", "/en/asia", "/en/europe", "/en/impressum", "/en/search")) and l != "/" and not l.endswith(".ico")]
  print(f"  {sl}: ({len(ls)}) {ls[:12]}")

# 3. Parse HGIS GZ.dbf JAGUAR counts by region & pais
zp = "histmap/1.data_raw/population_regional/JAGUAR/_shared/subadmin_hgis/raw_sources/hgis_indias/gazetteer-2023-10-26.zip"
with zipfile.ZipFile(zp) as zf:
  with zf.open("GZ.dbf") as f:
    header = f.read(32)
    num_records, header_len, rec_len = struct.unpack("<IHH", header[4:12])
    fields = []
    while True:
      fd = f.read(32)
      if not fd or fd[0] == 0x0D:
        break
      fields.append((fd[:11].split(b"\x00")[0].decode("latin-1"), chr(fd[11]), fd[16]))
    f.seek(header_len)
    offsets = {}
    pos = 1
    for nm, ft, fl in fields:
      offsets[nm] = (pos, fl)
      pos += fl
    reg_cnt = Counter()
    pais_cnt = Counter()
    jag_valid = 0
    for _ in range(num_records):
      rec = f.read(rec_len)
      if not rec or rec[0] == 0x2A:
        continue
      def g(k):
        o, l = offsets[k]
        return rec[o:o+l].decode("utf-8", errors="replace").strip()
      reg = g("region")
      pais = g("pais")
      try:
        lat = float(g("lat") or 0)
        lon = float(g("lon") or 0)
      except ValueError:
        lat, lon = 0.0, 0.0
      if reg in ("NES", "GDJ", "GUA", "SDO", "TFI") or (7.0 <= lat <= 32.8 and -118.5 <= lon <= -59.0):
        reg_cnt[reg] += 1
        pais_cnt[pais] += 1
        if 7.0 <= lat <= 32.8 and -118.5 <= lon <= -59.0:
          jag_valid += 1
    print(f"\n=== HGIS GZ.dbf IN JAGUAR: {jag_valid} geocoded colonial settlements ===")
    print("  By region:", reg_cnt.most_common(12))
    print("  By pais:", pais_cnt.most_common(18))
