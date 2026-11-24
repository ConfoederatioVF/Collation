import glob, json

targets = [
  ("La Esmeralda-Colombia_2", "La Esmeralda", [4.03, -74.96]),
  ("Las Ollas-Argentina", "Las Ollas", [-30.24792, -64.43868]),
  ("Sinsacate-Argentina", "Sinsacate", [-30.94285, -64.09397]),
  ("Barabara-Venezuela", "Barabara", [11.342, -68.975]),
  ("Pacocha-Peru", "Pacocha", [-17.61083, -71.34028]),
  ("Vichuquén-Chile", "Vichuquén", [-34.82954, -72.00987]),
  ("Paraíso de San José-Venezuela", "Paraíso de San José", [9.80517, -69.50698]),
  ("Cochamó-Chile", "Cochamó", [-41.75191, -72.19424]),
  ("La Gabarra-Colombia", "La Gabarra", [8.99726, -72.89728]),
  ("Charape-Peru", "Charape", [-5.3274, -79.1215]),
  ("Kuntursenka-Peru", "Kuntursenka", [-13.67449, -71.51573]),
  ("San Lucas-Ecuador", "San Lucas", [-3.75305, -79.24415]),
  ("Camarones-Chile_2", "Camarones", [-19.015, -69.861]),
  ("Mucuchies-Venezuela", "Mucuchies", [8.748, -70.921]),
  ("Tablazo Norte (tablazo)-Peru", "Tablazo Norte (tablazo)", [-5.3808, -80.7625]),
  ("Colonia El Simbolar-Argentina", "Colonia El Simbolar", [-27.72481, -63.86288]),
  ("Laguna Empedrada-Peru", "Laguna Empedrada", [-7.68458, -77.49033]),
  ("El algarrobal de Moro-Peru", "El algarrobal de Moro", [-7.1711, -79.42165]),
  ("Nelson-Argentina", "Nelson", [-31.2677, -60.76206]),
  ("La Margarita-Colombia_2", "La Margarita", [3.76, -76.38]),
  ("Los Laureles-Chile_2", "Los Laureles", [-36.83282, -72.12598]),
  ("Soledad-Argentina", "Soledad", [-30.61953, -60.91457]),
  ("Colaisaca-Ecuador", "Colaisaca", [-4.244, -79.68256]),
  ("Pacobamba-Peru", "Pacobamba", [-13.61528, -73.08389]),
  ("Isinlivi-Ecuador", "Isinlivi", [-0.78143, -78.85611]),
  ("Uia (na_magdalena_cauca_muisca)-Colombia", "Uia", [6.35958, -74.41776]),
  ("Qenqoraqay-Peru", "Qenqoraqay", [-13.4988, -71.78017]),
  ("Cayastá-Argentina", "Cayastá", [-31.19867, -60.15938]),
  ("Enciso-Colombia", "Enciso", [6.66803, -72.69965]),
  ("Pomacancha-Peru_2", "Pomacancha", [-11.736, -76.27]),
  ("Santa Rosa del Rio Primero-Argentina", "Santa Rosa del Rio Primero", [-31.153, -63.399]),
  ("Polígono Tolú-Colombia", "Polígono Tolú", [9.50811, -75.58769]),
  ("Almafuerte Sitio-Argentina", "Almafuerte Sitio", [-32.19136, -64.25577]),
  ("Ocros (per_ancash)-Peru", "Ocros", [-10.40333, -77.39667]),
  ("Almafuerte-Argentina_2", "Almafuerte", [-32.1585, -64.24557]),
  ("Pantoño-Venezuela", "Pantoño", [10.51556, -63.575]),
  ("Bowen-Argentina", "Bowen", [-35.00042, -67.51046]),
  ("Calzada-Peru", "Calzada", [-6.03028, -77.06667]),
  ("Fundición-Peru", "Fundición", [-17.60721, -71.24302]),
  ("Huata-Peru_2", "Huata", [-9.3598, -76.80832]),
  ("Sauce (ury_rio_negro)-Uruguay", "Sauce", [-32.90179, -57.73823]),
  ("Costa Rica-Colombia", "Costa Rica", [3.75178, -76.23411]),
  ("Villa Unión-Argentina", "Villa Unión", [-29.31776, -68.22776]),
  ("Cocaniguas-Ecuador", "Cocaniguas", [-0.115, -78.953]),
  ("Cruzorqo-Peru", "Cruzorqo", [-15.71255, -70.21291]),
  ("Pambay-Ecuador", "Pambay", [-1.4693, -78.0035]),
  ("Santa Ana (col_bolivar)-Colombia", "Santa Ana", [10.2389, -75.55575]),
  ("Cinto-Peru", "Cinto", [-17.51044, -70.71353]),
  ("Punto (na_magdalena_cauca_muisca)-Colombia", "Punto", [3.39, -76.35]),
  ("Garmendia-Argentina", "Garmendia", [-26.57412, -64.55867]),
  ("San Fernando Chile-Chile", "San Fernando Chile", [-34.584, -70.989]),
  ("En Proceso (inca_chinchaysuyu_6)-Peru", "En Proceso", [-6.4847, -77.81333]),
  ("La Chokta-Peru", "La Chokta", [-7.08688, -78.03974]),
  ("Santa Maria de Los Lagos-Chile", "Santa Maria de Los Lagos", [-39.85319, -72.72986]),
  ("Pampa Blanca-Argentina", "Pampa Blanca", [-24.53522, -65.07181]),
  ("Chivor-Colombia", "Chivor", [4.88817, -73.3684]),
  ("Santo Tomas de Pata-Peru", "Santo Tomas de Pata", [-13.11306, -74.41889]),
  ("Alcalá-Bolivia", "Alcalá", [-19.36753, -64.39105]),
  ("Yacimiento 1. Raíz arbol-Colombia", "Yacimiento 1. Raíz arbol", [4.33823, -74.69124]),
  ("Margarita-Argentina", "Margarita", [-29.69249, -60.25222]),
  ("Pacarní-Colombia", "Pacarní", [2.60843, -75.69836]),
  ("Puerto Cayo-Ecuador", "Puerto Cayo", [-1.32359, -80.70451]),
  ("Umamac-Argentina", "Umamac", [-28.677, -63.597]),
  ("Charapaya-Bolivia", "Charapaya", [-17.369, -66.755]),
  ("Jama-Ecuador_2", "Jama", [-0.203, -80.264]),
  ("San Roque Cañaverales-Colombia", "San Roque Cañaverales", [7.55, -73.544]),
  ("Chalán-Colombia", "Chalán", [9.54535, -75.3127]),
  ("Corpus-Argentina", "Corpus", [-27.1278, -55.50942]),
  ("San Diego de Alcala de la Sabana de Ocumare del Tuy-Venezuela", "San Diego de Alcala de la Sabana de Ocumare del Tuy", [10.115, -66.778]),
  ("Carlos Julio Arosemena Tola-Ecuador", "Carlos Julio Arosemena Tola", [-1.16859, -77.93139]),
  ("El Maitén-Argentina", "El Maitén", [-42.05031, -71.16779]),
  ("Sotoca-Chile", "Sotoca", [-19.583, -69.201]),
  ("La Aguadita-Argentina", "La Aguadita", [-30.77751, -64.67521]),
  ("Pulan-Peru", "Pulan", [-6.73889, -78.92028]),
  ("Río San Juan-Colombia", "Río San Juan", [6.44, -74.23]),
  ("Boyacá-Ecuador", "Boyacá", [-0.53787, -80.16201]),
  ("Hualcas I-Peru", "Hualcas I", [-5.5116, -79.7065]),
  ("La Dormida-Argentina_2", "La Dormida", [-30.354, -63.949]),
  ("Chiribaya Alta-Peru", "Chiribaya Alta", [-17.63201, -71.29556]),
  ("Cicasos-Peru", "Cicasos", [-12.36052, -76.704]),
  ("La Luz-Venezuela", "La Luz", [8.39556, -69.82389]),
  ("Central Queneque-Peru", "Central Queneque", [-14.2791, -69.4477]),
  ("Pulido Méndez-Venezuela", "Pulido Méndez", [8.62389, -71.61944]),
  ("Páez (col_boyaca)-Colombia", "Páez", [5.09732, -73.05274]),
  ("Membrillo-Ecuador", "Membrillo", [-0.8715, -79.95263]),
  ("General Lavalle-Argentina", "General Lavalle", [-36.40635, -56.94324]),
  ("Loc-Colombia", "Loc", [6.35143, -74.49296]),
  ("Güéjar-Colombia", "Güéjar", [3.47844, -73.7542]),
  ("Rio Seco-Peru", "Rio Seco", [-5.1386, -80.6148]),
  ("Alero el Verano-Argentina", "Alero el Verano", [-48.7116, -69.1919]),
]

target_keys = {k: (tn, tll) for k, tn, tll in targets}
for p in sorted(glob.glob("histmap/1.data_raw/population_regional/QUIPU/**/*_settlements.json", recursive=True)):
    with open(p, "r", encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict) and "settlements" in d:
        d = d["settlements"]
    rows = d.values() if isinstance(d, dict) else d
    fn = p.replace("\\", "/").split("/")[-1]
    for r in rows:
        if not isinstance(r, dict):
            continue
        k = r.get("key") or ""
        n = r.get("name") or r.get("n") or ""
        c = r.get("coords") or r.get("ll") or []
        matched_k = None
        if k in target_keys:
            matched_k = k
        elif len(c) >= 2:
            for tk, (tn, tll) in target_keys.items():
                if tn == n and abs(float(c[0]) - tll[0]) < 0.05 and abs(float(c[1]) - tll[1]) < 0.05:
                    matched_k = tk
                    break
        if matched_k:
            extra = {kk: vv for kk, vv in r.items() if kk not in ("population", "coords", "ll")}
            print(f"{matched_k} [{fn}]: {json.dumps(extra, ensure_ascii=False)}")
