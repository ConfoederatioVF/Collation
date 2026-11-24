import json, os, csv, time, urllib.request, urllib.parse

# 1. HGIS de las Indias (semicolon-delimited)
hgis_dir = 'histmap/1.data_raw/population_regional/QUIPU/_shared/subadmin_hgis/raw_sources/hgis_indias'
search_terms = [
    'chamalla', 'chamaya', 'terama', 'upito', 'yamane', 'ametista', 'catentoa',
    'catenzoa', 'mopa', 'itoco', 'badillo', 'vadillo', 'vallenar', 'ballenary',
    'calabozo', 'chacas', 'huaros', 'huayllay', 'acas', 'facala', 'facalá',
    'tacala', 'tumusla', 'san carlos', 'ita ibate', 'itá ibaté', 'acoyte',
    'choros', 'naranjo', 'cerritos', 'santa rosa', 'curarigua', 'tacamoros',
    'pozul', 'pózul', 'san faustino', 'sabaletas', 'huentota', 'castro',
    'maullin', 'maullín', 'sangarara', 'sangarará', 'tomependa', 'suarez', 'suárez',
    'chapa', 'llapa'
]
hgis_out = {}
p_lug = os.path.join(hgis_dir, 'da_dem_lugares.csv')
if os.path.exists(p_lug):
    with open(p_lug, encoding='utf-8-sig', errors='ignore') as f:
        r = csv.DictReader(f, delimiter=';')
        for row in r:
            lbl = (row.get('Label') or '').strip()
            low = lbl.lower()
            for t in search_terms:
                if t in low:
                    hgis_out.setdefault(t, []).append({
                        'Label': lbl,
                        'GZ_ID': row.get('GZ_ID'),
                        'Ctx1': row.get('Contexto-Sup1'),
                        'Ctx2': row.get('Contexto-Sup2'),
                        'Ctx3': row.get('Contexto-Sup3'),
                        'REG': row.get('REG'),
                        'START': row.get('START_'),
                        'END': row.get('END_'),
                        'Fuente': row.get('Fuente'),
                        'Nota': row.get('Nota')
                    })
                    break
with open('tests/hgis_clean.json', 'w', encoding='utf-8') as f:
    json.dump(hgis_out, f, ensure_ascii=False, indent=2)
print("HGIS clean terms:", len(hgis_out))

# 2. Check _shared or c14 for archaeological sites
arch_names = [
    'Montalvito', 'Huapula', "Q'espellaqta", 'Charquina', 'Rachacuain',
    'Condorhuachana', 'Batatas', 'Bobadilla', 'Paredones', 'Canchay',
    'Tambomarka', 'Colimes', 'Sa-Vsm', 'Paqu', 'Maullín', 'Algarrobo B',
    'Waqakunapata', 'Toco Toco', 'Yerbabuena', 'Quilcata', 'Machupitumarka',
    'Puntilla', 'Chaulla Pampa', 'Payogasta', 'Terlen', 'Huentota', 'Chiloé'
]
arch_hits = {}
for root, _, files in os.walk('histmap/1.data_raw/population_regional/_shared'):
    for fn in files:
        if fn.endswith(('.csv', '.json', '.geojson')):
            fp = os.path.join(root, fn)
            if os.path.getsize(fp) < 50000000:
                with open(fp, encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        for a in arch_names:
                            if a.lower() in line.lower():
                                arch_hits.setdefault(a, []).append(line.strip()[:250])
                                if len(arch_hits[a]) >= 3:
                                    break
with open('tests/arch_hits.json', 'w', encoding='utf-8') as f:
    json.dump(arch_hits, f, ensure_ascii=False, indent=2)
print("Arch hits:", len(arch_hits))

# 3. Polite sequential Wikipedia search + summary/extract
headers = {'User-Agent': 'ProjectSVEA/1.0 (https://confoederatio.org; research@confoederatio.org)'}
queries = [
    ("Las Cruces-Chile", "es", "Las Cruces El Tabo"),
    ("San Jose del Naranjo-Colombia", "es", "San José del Naranjo Obando"),
    ("Esperanza Galicia-Colombia", "es", "Cerritos Pereira"),
    ("Santa Rosa (ven_lara)-Venezuela", "es", "Santa Rosa Barquisimeto"),
    ("Chamalla-Peru", "es", "Chamaya Jaén"),
    ("Chacas-Peru", "es", "Chacas"),
    ("Huapula-Ecuador", "en", "Upano Valley sites"),
    ("Manuel Manrique (ven_cojedes)-Venezuela", "es", "Manrique Cojedes"),
    ("Q'espellaqta-Peru", "es", "Sangarará"),
    ("Guatraché-Argentina", "es", "Guatraché"),
    ("Santo Domingo de la Capilla-Peru", "es", "Distrito de Santo Domingo de la Capilla"),
    ("Pinto-Argentina", "es", "Pinto Santiago del Estero"),
    ("Vallenar-Chile_2", "es", "Vallenar"),
    ("San Sebastián-Ecuador", "es", "San Sebastián Pichincha Manabí"),
    ("Terama baja-Colombia", "es", "Yacopí"),
    ("Naranjal (col_huila)-Colombia", "es", "El Naranjal Timaná"),
    ("Wilfrido Loor Moreira-Ecuador", "es", "Wilfrido Loor Moreira El Carmen"),
    ("Upito-Colombia", "es", "Coello Tolima"),
    ("Llapa-Peru", "es", "Distrito de Llapa"),
    ("Ingeniero Forres-Argentina", "es", "Ingeniero Forres"),
    ("Antonio Díaz (ven_lara)-Venezuela", "es", "Curarigua"),
    ("Yacus-Peru", "es", "Distrito de Yacus"),
    ("Huentota-Argentina", "es", "Mendoza Argentina historia"),
    ("Chiloé Castro-Chile", "es", "Castro Chile"),
    ("Choros-Chile", "es", "Los Choros La Higuera"),
    ("El Corozo-Los Cruces-Venezuela", "es", "El Corozo Táchira"),
    ("Badillo (col_bolivar)-Colombia", "es", "Badillo Valledupar"),
    ("Tacamoros-Ecuador", "es", "Tacamoros"),
    ("Huaros-Peru", "es", "Distrito de Huaros"),
    ("Paredones Nazca-Peru", "es", "Paredones Nazca"),
    ("Mañazo-Peru", "es", "Distrito de Mañazo"),
    ("Todos Santos Calabozo-Venezuela", "es", "Calabozo Venezuela"),
    ("Huayllay Grande-Peru", "es", "Distrito de Huayllay Grande"),
    ("Copani-Peru", "es", "Distrito de Copani"),
    ("Chañar Ladeado-Argentina", "es", "Chañar Ladeado"),
    ("La Concepción (ven_trujillo)-Venezuela", "es", "La Concepción Carache"),
    ("None (crp_obispado_concepcion_chiloe)-Chile", "es", "Catentoa"),
    ("Acoyte-Argentina", "es", "Acoyte Salta"),
    ("Colimes-Ecuador_2", "es", "Colimes"),
    ("Sabaletas (col_antioquia)-Colombia", "es", "Sabaletas Montebello"),
    ("Concepción (ven_zulia)-Venezuela", "es", "La Concepción Zulia"),
    ("Sastre-Argentina", "es", "Sastre Santa Fe"),
    ("Las Toscas-Uruguay", "es", "Las Toscas Canelones"),
    ("Gultro-Chile", "es", "Gultro"),
    ("Humedales del Río Maullín-Chile", "es", "Maullín"),
    ("Algarrobo B-Peru", "es", "Chaclacayo"),
    ("Chapa-Colombia", "es", "Chapa El Tambo Cauca"),
    ("Suárez (col_tolima)-Colombia", "es", "Suárez Tolima"),
    ("Acas-Peru", "es", "Distrito de Acas"),
    ("Toco Toco-Argentina", "es", "Cruz del Eje"),
    ("Canchagua-Ecuador", "es", "Canchagua"),
    ("Ciudad de Dios (per_tacna)-Peru", "es", "Ciudad Nueva Tacna"),
    ("Los Juríes-Argentina", "es", "Los Juríes"),
    ("San Faustino-Colombia", "es", "San Faustino Cúcuta"),
    ("San Gregorio-Argentina", "es", "San Gregorio Santa Fe"),
    ("Pilar (arg_santa_fe)-Argentina", "es", "Pilar Santa Fe"),
    ("Mopa-Argentina", "es", "Mopa"),
    ("Humboldt-Argentina", "es", "Humboldt Santa Fe"),
    ("Itoco-Colombia", "es", "Itoco Muzo"),
    ("Villa Caro-Colombia", "es", "Villa Caro"),
    ("San Carlos (arg_misiones)-Argentina", "es", "San Carlos Corrientes"),
    ("Facala-Peru", "es", "Facalá"),
    ("Itá Ibaté-Argentina", "es", "Itá Ibaté"),
    ("Alto Saposoa-Peru", "es", "Distrito de Alto Saposoa"),
    ("Gobernador Gregores-Argentina", "es", "Gobernador Gregores"),
    ("Tumusla-Bolivia", "es", "Tumusla"),
    ("Potrero de Payogasta-Argentina", "es", "Potrero de Payogasta"),
    ("Pózul-Ecuador", "es", "Pózul"),
    ("Las Perdices-Argentina", "es", "Las Perdices")
]

wiki_out = []
for key, lang, q in queries:
    try:
        url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=1&format=json"
        req = urllib.request.Request(url, headers=headers)
        data = json.loads(urllib.request.urlopen(req, timeout=8).read().decode('utf-8'))
        hits = data.get('query', {}).get('search', [])
        if not hits:
            wiki_out.append({"key": key, "title": None, "extract": ""})
        else:
            title = hits[0]['title']
            time.sleep(0.15)
            url2 = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={urllib.parse.quote(title)}&format=json"
            req2 = urllib.request.Request(url2, headers=headers)
            data2 = json.loads(urllib.request.urlopen(req2, timeout=8).read().decode('utf-8'))
            pages = data2.get('query', {}).get('pages', {})
            extract = ""
            for p in pages.values():
                extract = p.get('extract', '')[:1200]
            wiki_out.append({"key": key, "title": title, "extract": extract})
    except Exception as e:
        wiki_out.append({"key": key, "title": "ERR", "extract": str(e)})
    time.sleep(0.2)

with open('tests/wiki_hits.json', 'w', encoding='utf-8') as f:
    json.dump(wiki_out, f, ensure_ascii=False, indent=2)
print("Wiki sequential done:", len(wiki_out))
