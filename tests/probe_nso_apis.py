import requests

H = {"User-Agent": "OperationViscount-QUIPU/1.0"}

def check(label, url):
    try:
        r = requests.get(url, headers=H, timeout=15)
        print(f"[{label}] HTTP {r.status_code} | len={len(r.text)} | {url}")
        if r.status_code == 200 and "json" in r.headers.get("content-type", "").lower():
            return r.json()
    except Exception as e:
        print(f"[{label}] ERR: {e}")
    return None

# 1. Colombia datos.gov.co & HDX
d = check("COL datos.gov.co", "https://api.us.socrata.com/api/catalog/v1?domains=www.datos.gov.co&q=poblacion+DANE&limit=10")
if d:
    for res in d.get("results", [])[:8]:
        rsrc = res.get("resource", {})
        print("   COL:", rsrc.get("id"), "|", rsrc.get("name"))

hcol = check("COL HDX", "https://data.humdata.org/api/3/action/package_search?q=colombia+population+dane&rows=10")
if hcol:
    for p in hcol.get("result", {}).get("results", [])[:5]:
        print("   HDX COL:", p["name"], "|", p["title"])
        for x in p.get("resources", [])[:4]:
            print("     ->", x.get("format"), x.get("name"), x.get("url"))

# 2. Argentina georef & datos.gob.ar
arg_loc = check("ARG georef localidades", "https://apis.datos.gob.ar/georef/api/localidades?max=5")
if arg_loc:
    print("   ARG georef total localidades:", arg_loc.get("total"))
arg_cen = check("ARG georef loc-censales", "https://apis.datos.gob.ar/georef/api/localidades-censales?max=5")
if arg_cen:
    print("   ARG georef total loc-censales:", arg_cen.get("total"))
arg_pkg = check("ARG datos.gob.ar", "https://datos.gob.ar/api/3/action/package_search?q=censo+poblacion+localidades&rows=10")
if arg_pkg:
    for p in arg_pkg.get("result", {}).get("results", [])[:6]:
        print("   ARG PKG:", p["name"], "|", p["title"])
        for x in p.get("resources", [])[:3]:
            print("     ->", x.get("format"), x.get("name"), x.get("url"))

# 3. Chile GitHub INE Censo 2024 & 2017 & MinCiencia
check("CHL censo2024 repo", "https://api.github.com/repos/bastianolea/censo_poblacion_consultar/contents")
check("CHL proyecciones repo", "https://api.github.com/repos/bastianolea/censo_proyecciones_poblacion/contents")
check("CHL datos.gob.cl", "https://datos.gob.cl/api/3/action/package_search?q=censo+poblacion+comuna&rows=5")

# 4. Uruguay catalogodatos.gub.uy
ury = check("URY catalogodatos", "https://catalogodatos.gub.uy/api/3/action/package_search?q=censo+localidades+poblacion&rows=10")
if ury:
    for p in ury.get("result", {}).get("results", [])[:6]:
        print("   URY PKG:", p["name"], "|", p["title"])
        for x in p.get("resources", [])[:3]:
            print("     ->", x.get("format"), x.get("name"), x.get("url"))

# 5. Peru datosabiertos.gob.pe
per = check("PER datosabiertos", "https://www.datosabiertos.gob.pe/api/3/action/package_search?q=censo+poblacion+distritos&rows=10")
if per:
    for p in per.get("result", {}).get("results", [])[:6]:
        print("   PER PKG:", p.get("name"), "|", p.get("title"))

# 6. Ecuador datosabiertos.gob.ec
ecu = check("ECU datosabiertos", "https://www.datosabiertos.gob.ec/api/3/action/package_search?q=censo+poblacion&rows=10")
if ecu:
    for p in ecu.get("result", {}).get("results", [])[:6]:
        print("   ECU PKG:", p.get("name"), "|", p.get("title"))
