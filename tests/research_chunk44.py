import json, urllib.request, urllib.parse, concurrent.futures, re

items = [
  {"key": "Sierras Bayas-Argentina", "n": "Sierras Bayas", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-36.84385, -60.22903], "ey": 1850},
  {"key": "Borrero Ayerbe-Colombia", "n": "Borrero Ayerbe", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.57229, -76.64649], "ey": 1850},
  {"key": "Trenel-Argentina", "n": "Trenel", "c": "Argentina", "r": "arg_la_pampa", "ll": [-35.69832, -64.13323], "ey": 1900},
  {"key": "Tránsito-Argentina", "n": "Tránsito", "c": "Argentina", "r": "arg_cordoba", "ll": [-31.42631, -63.19515], "ey": 80},
  {"key": "Huachac-Peru", "n": "Huachac", "c": "Peru", "r": "per_junin", "ll": [-12.02056, -75.34111], "ey": 1850},
  {"key": "Pueblo Libertador-Argentina", "n": "Pueblo Libertador", "c": "Argentina", "r": "arg_corrientes", "ll": [-30.22011, -59.38979], "ey": 1850},
  {"key": "Nono-Ecuador", "n": "Nono", "c": "Ecuador", "r": "ecu_pichincha", "ll": [-0.05994, -78.57493], "ey": 1525},
  {"key": "Unión Milagreña-Ecuador", "n": "Unión Milagreña", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.36381, -76.78347], "ey": 1920},
  {"key": "Basail-Argentina", "n": "Basail", "c": "Argentina", "r": "arg_chaco", "ll": [-27.88763, -59.28148], "ey": 1900},
  {"key": "Jesus Nanzueras-Colombia", "n": "Jesus Nanzueras", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [0.301, -76.738], "ey": 1693},
  {"key": "Ambargasta-Argentina_2", "n": "Ambargasta", "c": "Argentina", "r": "crp_gobernacion_tucuman", "ll": [-29.051, -63.959], "ey": 1536},
  {"key": "San Pedro De Los Cofánes-Ecuador", "n": "San Pedro De Los Cofánes", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [-0.13862, -76.85285], "ey": 1920},
  {"key": "Hinojo-Argentina", "n": "Hinojo", "c": "Argentina", "r": "arg_buenos_aires", "ll": [-36.41291, -60.67307], "ey": 1850},
  {"key": "La Unión (per_junin)-Peru", "n": "La Unión", "c": "Peru", "r": "per_junin", "ll": [-11.37722, -75.75194], "ey": 1850},
  {"key": "Sitabamba-Peru", "n": "Sitabamba", "c": "Peru", "r": "per_la_libertad", "ll": [-8.02222, -77.73], "ey": 1850},
  {"key": "San Joaquín-Colombia", "n": "San Joaquín", "c": "Colombia", "r": "col_santander", "ll": [6.42755, -72.86764], "ey": 1783},
  {"key": "Dolores-Venezuela", "n": "Dolores", "c": "Venezuela", "r": "ven_barinas", "ll": [8.31, -69.54333], "ey": 1850},
  {"key": "El Dorado-Ecuador", "n": "El Dorado", "c": "Ecuador", "r": "ecu_orellana", "ll": [-0.50223, -76.95238], "ey": 1920},
  {"key": "La Lucía-Venezuela", "n": "La Lucía", "c": "Venezuela", "r": "ven_portuguesa", "ll": [9.68543, -69.25716], "ey": 1850},
  {"key": "Salcahuasi-Peru", "n": "Salcahuasi", "c": "Peru", "r": "per_huancavelica", "ll": [-12.10417, -74.75167], "ey": 1850},
  {"key": "Tinco-Peru", "n": "Tinco", "c": "Peru", "r": "per_ancash", "ll": [-9.27083, -77.6775], "ey": 1850},
  {"key": "Teyuna-Colombia", "n": "Teyuna", "c": "Colombia", "r": "na_caribbean_maracaibo_tairona", "ll": [11.038, -73.925], "ey": 800},
  {"key": "Tulipe-Ecuador", "n": "Tulipe", "c": "Ecuador", "r": "ca_equatorial_sierra_canari", "ll": [0.095, -78.778], "ey": 800},
  {"key": "Palma Roja-Ecuador", "n": "Palma Roja", "c": "Ecuador", "r": "ecu_sucumbios", "ll": [0.1235, -76.0535], "ey": 1920},
  {"key": "Arcata-Peru", "n": "Arcata", "c": "Peru", "r": "per_arequipa", "ll": [-15.042, -72.2758], "ey": 1525},
  {"key": "Nueve de Julio-Peru", "n": "Nueve de Julio", "c": "Peru", "r": "per_junin", "ll": [-11.89778, -75.31806], "ey": 1850},
  {"key": "Latapuquio-Peru", "n": "Latapuquio", "c": "Peru", "r": "per_huancavelica", "ll": [-13.0003, -74.7142], "ey": 1525},
  {"key": "Uspallata-Argentina", "n": "Uspallata", "c": "Argentina", "r": "arg_mendoza", "ll": [-32.59139, -69.34443], "ey": 1850},
  {"key": "La Unión (ecu_esmeraldas)-Ecuador", "n": "La Unión", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.74126, -79.83271], "ey": 1850},
  {"key": "Arroyo Feo-Argentina", "n": "Arroyo Feo", "c": "Argentina", "r": "sc_patagonia_tierra_del_fuego", "ll": [-46.9333, -70.5], "ey": -8752},
  {"key": "Morelia-Colombia", "n": "Morelia", "c": "Colombia", "r": "col_caqueta", "ll": [1.48661, -75.72415], "ey": 1770},
  {"key": "San Antonio ( Yurumanguí )-Colombia", "n": "San Antonio ( Yurumanguí )", "c": "Colombia", "r": "col_valle_del_cauca", "ll": [3.26104, -77.25917], "ey": 1525},
  {"key": "Coroma-Bolivia", "n": "Coroma", "c": "Bolivia", "r": "bol_potosi", "ll": [-19.52905, -66.81295], "ey": 1525},
  {"key": "San Fernando-Peru", "n": "San Fernando", "c": "Peru", "r": "per_san_martin", "ll": [-5.90194, -77.26944], "ey": 1900},
  {"key": "Santa Clara-Venezuela", "n": "Santa Clara", "c": "Venezuela", "r": "ven_anzoategui", "ll": [8.50444, -64.60833], "ey": 1755},
  {"key": "El Encanto-Colombia", "n": "El Encanto", "c": "Colombia", "r": "col_amazonas", "ll": [-1.74806, -73.20711], "ey": 1900},
  {"key": "Hermílio Valdizan-Peru", "n": "Hermílio Valdizan", "c": "Peru", "r": "per_huanuco", "ll": [-9.20556, -75.83583], "ey": 1850},
  {"key": "Inriville-Argentina", "n": "Inriville", "c": "Argentina", "r": "arg_cordoba", "ll": [-32.94556, -62.23082], "ey": 1850},
  {"key": "Calcha-Bolivia", "n": "Calcha", "c": "Bolivia", "r": "vp_intendencia_charcas_potosi", "ll": [-20.369, -65.465], "ey": 1525},
  {"key": "San José De Payamino-Ecuador", "n": "San José De Payamino", "c": "Ecuador", "r": "ecu_napo", "ll": [-0.49014, -77.29376], "ey": 1525},
  {"key": "Minas De Corrales-Uruguay", "n": "Minas De Corrales", "c": "Uruguay", "r": "ury_rivera", "ll": [-31.57284, -55.47108], "ey": 1850},
  {"key": "Tálag-Ecuador", "n": "Tálag", "c": "Ecuador", "r": "ecu_napo", "ll": [-1.05091, -78.11127], "ey": 1850},
  {"key": "Patazcachi-Bolivia", "n": "Patazcachi", "c": "Bolivia", "r": "vp_intendencia_la_paz", "ll": [-15.433, -68.95], "ey": 1525},
  {"key": "Los Berros-Argentina", "n": "Los Berros", "c": "Argentina", "r": "arg_san_juan", "ll": [-31.95273, -68.65427], "ey": 1850},
  {"key": "Ocumal-Peru", "n": "Ocumal", "c": "Peru", "r": "per_amazonas", "ll": [-6.2825, -78.21083], "ey": 1525},
  {"key": "Río Colorado (arg_tucuman)-Argentina", "n": "Río Colorado", "c": "Argentina", "r": "arg_tucuman", "ll": [-27.14968, -65.35605], "ey": 1850},
  {"key": "Anganoy-Colombia", "n": "Anganoy", "c": "Colombia", "r": "col_narino", "ll": [1.21321, -77.30178], "ey": 1525},
  {"key": "Ronquín-Venezuela", "n": "Ronquín", "c": "Venezuela", "r": "na_orinoco_llanos_guayana", "ll": [7.817, -65.819], "ey": -269},
  {"key": "San Juan (ven_zulia)-Venezuela", "n": "San Juan", "c": "Venezuela", "r": "ven_zulia", "ll": [9.76514, -70.81289], "ey": 1850},
  {"key": "Guaseco-Colombia", "n": "Guaseco", "c": "Colombia", "r": "vng_llanos_caguan", "ll": [6.103, -72.027], "ey": 1525},
  {"key": "Fuerte Esperanza-Argentina", "n": "Fuerte Esperanza", "c": "Argentina", "r": "arg_chaco", "ll": [-25.1619, -61.84197], "ey": 1900},
  {"key": "Majua-Ecuador", "n": "Majua", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [0.66315, -79.50477], "ey": 1850},
  {"key": "Tinyash-Peru", "n": "Tinyash", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-8.94604, -77.00055], "ey": -1000},
  {"key": "Ventanillas de Combayo-Peru_2", "n": "Ventanillas de Combayo", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-7.04877, -78.40054], "ey": 500},
  {"key": "Rosal del Monte-Colombia", "n": "Rosal del Monte", "c": "Colombia", "r": "col_narino", "ll": [1.29021, -77.17489], "ey": 1525},
  {"key": "Tienditas-Venezuela", "n": "Tienditas", "c": "Venezuela", "r": "ven_tachira", "ll": [7.88611, -72.43944], "ey": 1850},
  {"key": "San Pablo De Tenta-Ecuador", "n": "San Pablo De Tenta", "c": "Ecuador", "r": "ecu_loja", "ll": [-3.6082, -79.28374], "ey": 1850},
  {"key": "Sotaquí-Chile", "n": "Sotaquí", "c": "Chile", "r": "chl_region_de_coquimbo", "ll": [-30.63439, -71.11251], "ey": 1525},
  {"key": "La Victoria (ecu_cotopaxi)-Ecuador", "n": "La Victoria", "c": "Ecuador", "r": "ecu_cotopaxi", "ll": [-0.9121, -78.70009], "ey": 1850},
  {"key": "Ciudad del Pescador-Peru", "n": "Ciudad del Pescador", "c": "Peru", "r": "per_piura", "ll": [-5.7657, -80.8545], "ey": 1850},
]

def wp_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ViscountToponymyBot/1.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))

def lookup(it):
    lat, lng = it["ll"]
    res = {"key": it["key"], "hits": []}
    for lang in ("es", "en"):
        # geosearch
        try:
            gs = wp_get(f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json")
            for g in gs.get("query", {}).get("geosearch", []):
                res["hits"].append((lang, "geo", g["title"], g["dist"]))
        except Exception as e:
            pass
        # title search
        try:
            q = urllib.parse.quote(f"{it['n']} {it['c']}")
            sr = wp_get(f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json")
            for s in sr.get("query", {}).get("search", []):
                res["hits"].append((lang, "sr", s["title"], None))
        except Exception as e:
            pass
    # Fetch extract for top geo hit or matching title
    chosen = None
    n_low = it["n"].lower()
    for lang, kind, title, dist in res["hits"]:
        if kind == "geo" and (n_low.split()[0] in title.lower() or (dist is not None and dist < 3000)):
            chosen = (lang, title)
            break
    if not chosen and res["hits"]:
        # check sr hit containing name
        for lang, kind, title, dist in res["hits"]:
            if n_low in title.lower():
                chosen = (lang, title)
                break
    if not chosen and res["hits"]:
        chosen = (res["hits"][0][0], res["hits"][0][2])
    res["chosen"] = chosen
    if chosen:
        lang, title = chosen
        try:
            tq = urllib.parse.quote(title)
            ex = wp_get(f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={tq}&prop=extracts|revisions&exintro=1&explaintext=1&rvprop=content&rvslots=main&rvsection=0&redirects=1&format=json")
            pages = ex.get("query", {}).get("pages", {})
            for pid, p in pages.items():
                res["title_final"] = p.get("title")
                res["intro"] = (p.get("extract") or "")[:900]
                revs = p.get("revisions", [])
                if revs:
                    txt = revs[0].get("slots", {}).get("main", {}).get("*", "")
                    # get infobox lines with fundac / creac / nombre / otro / fecha
                    lines = [ln.strip() for ln in txt.splitlines() if any(w in ln.lower() for w in ("fundac", "creac", "nombre", "fecha", "historia", "origen", "establec", "parroqu"))]
                    res["infobox"] = lines[:12]
        except Exception as e:
            res["err"] = str(e)
    return res

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    out = list(ex.map(lookup, items))

with open("tests/wp_chunk44.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("Done:", len(out))
