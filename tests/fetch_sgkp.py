import json
import os
import urllib.request
import urllib.parse

SGKP_DIR = "tests/dl/sgkp"
os.makedirs(SGKP_DIR, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}

u = "https://archive.org/advancedsearch.php?q=" + urllib.parse.quote("identifier:slownik-*") + "&fl[]=identifier,title&rows=60&output=json"
res = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25).read().decode("utf-8"))
docs = sorted(res["response"]["docs"], key=lambda x: x["identifier"])
for d in docs:
  ident = d["identifier"]
  if not ident.startswith("slownik-"):
    continue
  # Filter to the 15-volume canonical set (slownik-1..slownik-15 or slownik-geograficzny-...-15-cz-1/2)
  if not (ident[8:].isdigit() or "15" in ident):
    continue
  meta = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://archive.org/metadata/{ident}", headers=UA), timeout=25).read().decode("utf-8"))
  files = meta.get("files", [])
  # Prefer _hocr_searchtext.txt.gz (small!), else _djvu.txt
  target = None
  for f in files:
    if f["name"].endswith("_hocr_searchtext.txt.gz"):
      target = f["name"]
      break
  if not target:
    for f in files:
      if f["name"].endswith("_djvu.txt"):
        target = f["name"]
        break
  if not target:
    print("NO TEXT:", ident)
    continue
  out_name = ident + "_" + os.path.basename(target).replace(" ", "_")
  fp = os.path.join(SGKP_DIR, out_name)
  if os.path.exists(fp) and os.path.getsize(fp) > 1000:
    print("SKIP", out_name, os.path.getsize(fp))
    continue
  dl_u = f"https://archive.org/download/{ident}/" + urllib.parse.quote(target)
  with urllib.request.urlopen(urllib.request.Request(dl_u, headers=UA), timeout=120) as r, open(fp, "wb") as out:
    while True:
      ch = r.read(262144)
      if not ch:
        break
      out.write(ch)
  print("OK", out_name, os.path.getsize(fp))
