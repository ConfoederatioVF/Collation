import glob, json, os

targets = [
    "Saquena", "Junín", "Pilar de Macapillo", "Juctacancha", "La Coquera",
    "Doradal", "Siete De Julio", "Chumbicha", "El Trebol", "Sobreancho Torre",
    "Anisacate", "La Caldera", "Norberto de la Riestra", "Michac",
    "Arnoldo Gabaldon", "La Cruz", "Raco", "Chiapa", "Chacance", "Villalonga",
    "Gochacalla", "San Antonio", "Karajía", "Sarayacu", "Santa Elena",
    "Seguí", "El Carmen", "La Arenosa", "Agua Caliente", "La Aguada",
    "Punta Teatinos", "Cañasgordas", "Tomay Kichwa", "La Morada", "Dichato",
    "Anchihuay", "Corani", "Retiro de los Indios", "El Pintor", "Burbusay",
    "Camaná", "Santa Cruz", "Codpa", "La Clarita", "Torre", "Macuira",
    "Minipi", "Boca Toma", "Villa El Salvador", "Coro", "San Pedro",
    "Río Verde", "Catac", "Puqueldón", "Moya", "Cuñumbuqui", "Yumbel",
    "Cumanagoto", "Pampa de Nerete", "Inkawasi", "Villacuri", "Punto",
    "Nariño", "Casbas", "El Pinto", "La Soledad", "Guimbi", "Playa Grande",
    "Cerro Suchiman", "Hernández", "Burruyacú", "Pisba", "Clúster",
    "Aguada de Pablo", "Valle de los Dinosaurios", "Paico", "San Buenaventura",
    "Marcella", "Quebrada Honda", "Gibraltar", "Trancas", "California",
    "Calquis", "Santa Ana", "Plaza del Mundo", "Kilo.coq", "Jibito",
    "Colonia Liebig", "Villa San Agustín", "Mindo"
]

# Search for exact coords in source_ledger.json5
coords_map = {
    "Juctacancha-Peru": (-10.2658, -76.45889),
    "La Coquera-Colombia": (5.78056, -74.67139),
    "El Trebol-Colombia": (0.93193, -76.40319),
    "Sobreancho Torre-Colombia": (3.89784, -73.65714),
    "Anisacate-Argentina_2": (-31.71191, -64.4137),
    "La Cruz-Argentina_2": (-32.3134, -64.42343),
    "Chacance-Chile": (-22.39556, -69.52756),
    "Gochacalla-Peru": (-9.84741, -75.9086),
    "Karajía-Peru": (-6.16178, -78.02438),
    "La Arenosa-Colombia": (10.93, -74.76),
    "Punta Teatinos-Chile": (-29.81778, -71.28851),
    "Cañasgordas y Abriaqu-Colombia": (6.76, -76.1),
    "Camaná Inca-Peru": (-16.623, -72.711),
    "Torre (na_magdalena_cauca_muisca)-Colombia": (7.96976, -75.56247),
    "Boca Toma-Argentina": (-31.65531, -63.96212),
    "Río Verde-Chile_2": (-52.65223, -71.46112),
    "Moya-Peru_2": (-12.46177, -76.69442),
    "Cumanagoto Píritu-Venezuela": (10.048, -65.036),
    "Pampa de Nerete-Colombia": (1.73959, -78.68807),
    "Punto (na_magdalena_cauca_muisca_2)-Colombia": (6.18675, -74.52851),
    "Area IV Qda. Playa Grande-Peru": (-8.26608, -78.8281),
    "Cerro Suchiman-Peru": (-8.72808, -78.42051),
    "Clúster-Colombia": (3.87884, -73.63734),
    "Valle de los Dinosaurios-Peru": (-5.74953, -78.51062),
    "Paico-Chile": (-39.60231, -73.08754),
    "Marcella-Colombia": (5.86125, -75.69394),
    "Quebrada Honda-Peru": (-16.5223, -71.4914),
    "Santa Ana-Peru_2": (-16.43912, -72.17488),
    "Plaza del Mundo-Colombia": (4.80128, -75.81081),
    "Kilo.coq-Chile": (-29.60765, -70.93735),
    "San Pedro (arg_cordoba)-Argentina": (-31.75524, -64.62779),
}

for p in glob.glob("histmap/1.data_raw/population_regional/QUIPU/**/*_source_ledger.json5", recursive=True):
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        continue
    rows = d.get("candidates", d.get("records", d.get("raw_candidates", [])))
    if not isinstance(rows, list):
        for v in d.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                rows = v
                break
    if not isinstance(rows, list): continue
    for r in rows:
        lat = r.get("lat") or (r.get("coords")[0] if isinstance(r.get("coords"), list) else None)
        lng = r.get("lng") or r.get("lon") or (r.get("coords")[1] if isinstance(r.get("coords"), list) else None)
        if lat is None or lng is None: continue
        for mk, (mlat, mlng) in coords_map.items():
            if abs(float(lat)-mlat) < 0.01 and abs(float(lng)-mlng) < 0.01:
                print(f"SL {mk} ({os.path.basename(p)}): { {k:v for k,v in r.items() if k in ('name','site_name','period','culture','date','year','earliest_year','latest_year','source','notes','description','municipality','department','province','district')} }")
