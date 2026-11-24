import json, os, math

chunk = [
  {"key": "Montalvito - sitio-Colombia", "n": "Montalvito - sitio", "c": "Colombia", "ll": [4.19778, -74.86778], "ey": -1000, "ly": 1500},
  {"key": "Las Cruces-Chile", "n": "Las Cruces", "c": "Chile", "ll": [-33.50016, -71.61324], "ey": 1850, "ly": 2017},
  {"key": "San Jose del Naranjo-Colombia", "n": "San Jose del Naranjo", "c": "Colombia", "ll": [4.598, -75.948], "ey": 1525, "ly": 1830},
  {"key": "Esperanza Galicia-Colombia", "n": "Esperanza Galicia", "c": "Colombia", "ll": [4.79983, -75.81491], "ey": 1525, "ly": 2018},
  {"key": "Santa Rosa (ven_lara)-Venezuela", "n": "Santa Rosa", "c": "Venezuela", "ll": [10.10107, -69.24574], "ey": 1538, "ly": 2025},
  {"key": "Chamalla-Peru", "n": "Chamalla", "c": "Peru", "ll": [-5.811, -78.717], "ey": 1525, "ly": 1830},
  {"key": "Chacas-Peru", "n": "Chacas", "c": "Peru", "ll": [-9.16222, -77.36583], "ey": 1525, "ly": 2025},
  {"key": "Huapula-Ecuador", "n": "Huapula", "c": "Ecuador", "ll": [-2.0747, -78.0458], "ey": -3361, "ly": 1532},
  {"key": "Manuel Manrique (ven_cojedes)-Venezuela", "n": "Manuel Manrique", "c": "Venezuela", "ll": [9.81629, -68.51306], "ey": 1850, "ly": 2025},
  {"key": "Q'espellaqta-Peru", "n": "Q'espellaqta", "c": "Peru", "ll": [-13.93933, -71.62595], "ey": 500, "ly": 1530},
  {"key": "Guatraché-Argentina", "n": "Guatraché", "c": "Argentina", "ll": [-37.67078, -63.53572], "ey": 1900, "ly": 2022},
  {"key": "Santo Domingo de la Capilla-Peru", "n": "Santo Domingo de la Capilla", "c": "Peru", "ll": [-6.24472, -78.85528], "ey": 1850, "ly": 2025},
  {"key": "Pinto-Argentina", "n": "Pinto", "c": "Argentina", "ll": [-29.14168, -62.65463], "ey": 1850, "ly": 2022},
  {"key": "Vallenar-Chile_2", "n": "Vallenar", "c": "Chile", "ll": [-28.575, -70.756], "ey": 1525, "ly": 1830},
  {"key": "San Sebastián-Ecuador", "n": "San Sebastián", "c": "Ecuador", "ll": [-1.06655, -79.96737], "ey": 1850, "ly": 2025},
  {"key": "Charquina 1 Bis-Argentina", "n": "Charquina 1 Bis", "c": "Argentina", "ll": [-31.30333, -65.64333], "ey": 80, "ly": 1500},
  {"key": "Terama baja-Colombia", "n": "Terama baja", "c": "Colombia", "ll": [5.196, -74.451], "ey": 1525, "ly": 1830},
  {"key": "Naranjal (col_huila)-Colombia", "n": "Naranjal", "c": "Colombia", "ll": [2.0158, -75.8509], "ey": 1525, "ly": 2018},
  {"key": "Wilfrido Loor Moreira-Ecuador", "n": "Wilfrido Loor Moreira", "c": "Ecuador", "ll": [-0.33595, -79.66068], "ey": 1850, "ly": 2025},
  {"key": "Rachacuain-Peru", "n": "Rachacuain", "c": "Peru", "ll": [-11.23594, -75.65014], "ey": 500, "ly": 1530},
  {"key": "Upito-Colombia", "n": "Upito", "c": "Colombia", "ll": [4.256, -74.885], "ey": 1758, "ly": 1830},
  {"key": "Llapa-Peru", "n": "Llapa", "c": "Peru", "ll": [-6.98083, -78.8075], "ey": 1850, "ly": 2025},
  {"key": "Ingeniero Forres-Argentina", "n": "Ingeniero Forres", "c": "Argentina", "ll": [-27.87896, -63.98043], "ey": 1850, "ly": 2010},
  {"key": "Cerro Condorhuachana-Peru", "n": "Cerro Condorhuachana", "c": "Peru", "ll": [-14.96046, -70.34228], "ey": -1000, "ly": 1530},
  {"key": "Antonio Díaz (ven_lara)-Venezuela", "n": "Antonio Díaz", "c": "Venezuela", "ll": [9.97778, -69.93833], "ey": 1538, "ly": 2025},
  {"key": "Yacus-Peru", "n": "Yacus", "c": "Peru", "ll": [-9.98611, -76.50583], "ey": 1850, "ly": 2025},
  {"key": "Huentota-Argentina", "n": "Huentota", "c": "Argentina", "ll": [-32.89, -68.845], "ey": 1480, "ly": 1530},
  {"key": "Chiloé Castro-Chile", "n": "Chiloé Castro", "c": "Chile", "ll": [-42.48, -73.764], "ey": -4000, "ly": 1450},
  {"key": "Choros-Chile", "n": "Choros", "c": "Chile", "ll": [-29.29, -71.313], "ey": 1525, "ly": 1830},
  {"key": "El Corozo-Los Cruces-Venezuela", "n": "El Corozo-Los Cruces", "c": "Venezuela", "ll": [7.69013, -72.24261], "ey": 1850, "ly": 2011},
  {"key": "San Rafael-Colombia_2", "n": "San Rafael", "c": "Colombia", "ll": [4.01732, -74.85633], "ey": 1300, "ly": 1500},
  {"key": "Badillo (col_bolivar)-Colombia", "n": "Badillo", "c": "Colombia", "ll": [7.97471, -73.85438], "ey": 1772, "ly": 2018},
  {"key": "Tacamoros-Ecuador", "n": "Tacamoros", "c": "Ecuador", "ll": [-4.43319, -79.72442], "ey": 1525, "ly": 2025},
  {"key": "Huaros-Peru", "n": "Huaros", "c": "Peru", "ll": [-11.40667, -76.57583], "ey": 1525, "ly": 2025},
  {"key": "Huaca Bobadilla-Peru", "n": "Huaca Bobadilla", "c": "Peru", "ll": [-6.59939, -79.79715], "ey": -1000, "ly": 1530},
  {"key": "Paredones Nazca-Peru", "n": "Paredones Nazca", "c": "Peru", "ll": [-14.841, -74.933], "ey": 1438, "ly": 1532},
  {"key": "Mañazo-Peru", "n": "Mañazo", "c": "Peru", "ll": [-15.80111, -70.34333], "ey": 1300, "ly": 2025},
  {"key": "Canchay-Peru", "n": "Canchay", "c": "Peru", "ll": [-9.89217, -76.00671], "ey": -1000, "ly": 1530},
  {"key": "Todos Santos Calabozo-Venezuela", "n": "Todos Santos Calabozo", "c": "Venezuela", "ll": [8.919, -67.43], "ey": 1724, "ly": 1830},
  {"key": "Yamane-Colombia", "n": "Yamane", "c": "Colombia", "ll": [3.566, -72.364], "ey": 1525, "ly": 1830},
  {"key": "Providencia-Colombia_2", "n": "Providencia", "c": "Colombia", "ll": [1.6464, -78.73931], "ey": 1000, "ly": 1500},
  {"key": "Mineral de Ametistas-Peru", "n": "Mineral de Ametistas", "c": "Peru", "ll": [-6.289, -78.858], "ey": 1525, "ly": 1830},
  {"key": "Huayllay Grande-Peru", "n": "Huayllay Grande", "c": "Peru", "ll": [-12.94278, -74.70167], "ey": 1525, "ly": 2025},
  {"key": "Copani-Peru", "n": "Copani", "c": "Peru", "ll": [-16.4, -69.04028], "ey": 1850, "ly": 2025},
  {"key": "Chañar Ladeado-Argentina", "n": "Chañar Ladeado", "c": "Argentina", "ll": [-33.32617, -62.03533], "ey": 1850, "ly": 2022},
  {"key": "La Concepción (ven_trujillo)-Venezuela", "n": "La Concepción", "c": "Venezuela", "ll": [9.425, -70.46833], "ey": 1850, "ly": 2025},
  {"key": "Tambomarka-Peru", "n": "Tambomarka", "c": "Peru", "ll": [-10.45264, -76.35384], "ey": 0, "ly": 1530},
  {"key": "None (crp_obispado_concepcion_chiloe)-Chile", "n": "None", "c": "Chile", "ll": [-35.90768, -71.71246], "ey": 1525, "ly": 1599},
  {"key": "Acoyte-Argentina", "n": "Acoyte", "c": "Argentina", "ll": [-22.28346, -65.01662], "ey": 1525, "ly": 2010},
  {"key": "Colimes-Ecuador_2", "n": "Colimes", "c": "Ecuador", "ll": [-1.59178, -80.28246], "ey": -3163, "ly": -2082},
  {"key": "Sabaletas (col_antioquia)-Colombia", "n": "Sabaletas", "c": "Colombia", "ll": [5.91746, -75.54634], "ey": 1525, "ly": 2018},
  {"key": "Concepción (ven_zulia)-Venezuela", "n": "Concepción", "c": "Venezuela", "ll": [10.41711, -71.6933], "ey": 1850, "ly": 2025},
  {"key": "Sastre-Argentina", "n": "Sastre", "c": "Argentina", "ll": [-31.76747, -61.82899], "ey": 1850, "ly": 2010},
  {"key": "Las Toscas-Uruguay", "n": "Las Toscas", "c": "Uruguay", "ll": [-34.76738, -55.74014], "ey": 1850, "ly": 2023},
  {"key": "Gultro-Chile", "n": "Gultro", "c": "Chile", "ll": [-34.20486, -70.76126], "ey": 1850, "ly": 2017},
  {"key": "Sa-Vsm-Colombia", "n": "Sa-Vsm", "c": "Colombia", "ll": [4.0714, -74.90584], "ey": 0, "ly": 1500},
  {"key": "Paqu-Colombia", "n": "Paqu", "c": "Colombia", "ll": [-0.5747, -72.1129], "ey": -269, "ly": 1500},
  {"key": "Humedales del Río Maullín-Chile", "n": "Humedales del Río Maullín", "c": "Chile", "ll": [-41.51908, -73.36842], "ey": 1000, "ly": 1500},
  {"key": "Algarrobo B-Peru", "n": "Algarrobo B", "c": "Peru", "ll": [-11.97312, -76.81151], "ey": 0, "ly": 1530},
  {"key": "Chapa-Colombia", "n": "Chapa", "c": "Colombia", "ll": [2.47135, -76.88196], "ey": 1525, "ly": 2018},
  {"key": "Suárez (col_tolima)-Colombia", "n": "Suárez", "c": "Colombia", "ll": [4.04889, -74.83188], "ey": 1525, "ly": 2025},
  {"key": "Acas-Peru", "n": "Acas", "c": "Peru", "ll": [-10.4575, -77.32778], "ey": 1525, "ly": 2025},
  {"key": "Waqakunapata-Peru", "n": "Waqakunapata", "c": "Peru", "ll": [-13.87707, -73.72466], "ey": -1000, "ly": 1530},
  {"key": "Toco Toco-Argentina", "n": "Toco Toco", "c": "Argentina", "ll": [-30.76564, -64.75579], "ey": 80, "ly": 1500},
  {"key": "La Concepción (ven_trujillo_2)-Venezuela", "n": "La Concepción", "c": "Venezuela", "ll": [9.50416, -70.21406], "ey": 1850, "ly": 2025},
  {"key": "Yerbabuena-Colombia", "n": "Yerbabuena", "c": "Colombia", "ll": [3.98416, -74.91407], "ey": 500, "ly": 1500},
  {"key": "Canchagua-Ecuador", "n": "Canchagua", "c": "Ecuador", "ll": [-0.79726, -78.71178], "ey": 1850, "ly": 2025},
  {"key": "Ciudad de Dios (per_tacna)-Peru", "n": "Ciudad de Dios", "c": "Peru", "ll": [-18.0687, -70.2995], "ey": 1850, "ly": 2017},
  {"key": "Los Juríes-Argentina", "n": "Los Juríes", "c": "Argentina", "ll": [-28.46301, -62.11052], "ey": 1850, "ly": 2022},
  {"key": "San Faustino-Colombia", "n": "San Faustino", "c": "Colombia", "ll": [8.06253, -72.40533], "ey": 1525, "ly": 2018},
  {"key": "Tambo de Quilcata-Peru", "n": "Tambo de Quilcata", "c": "Peru", "ll": [-14.61759, -74.22907], "ey": -2000, "ly": 1532},
  {"key": "San Gregorio-Argentina", "n": "San Gregorio", "c": "Argentina", "ll": [-34.32536, -62.0359], "ey": 1850, "ly": 2022},
  {"key": "Pilar (arg_santa_fe)-Argentina", "n": "Pilar", "c": "Argentina", "ll": [-31.4404, -61.25957], "ey": 1850, "ly": 2022},
  {"key": "Mopa-Argentina", "n": "Mopa", "c": "Argentina", "ll": [-28.176, -63.212], "ey": 1536, "ly": 1790},
  {"key": "Humboldt-Argentina", "n": "Humboldt", "c": "Argentina", "ll": [-31.40084, -61.08226], "ey": 1850, "ly": 2022},
  {"key": "Itoco-Colombia", "n": "Itoco", "c": "Colombia", "ll": [5.557, -74.174], "ey": 1525, "ly": 1830},
  {"key": "Villa Caro-Colombia", "n": "Villa Caro", "c": "Colombia", "ll": [7.91424, -72.9736], "ey": 1850, "ly": 2025},
  {"key": "San Carlos (arg_misiones)-Argentina", "n": "San Carlos", "c": "Argentina", "ll": [-27.7436, -55.89845], "ey": 1631, "ly": 2022},
  {"key": "Facala-Peru", "n": "Facala", "c": "Peru", "ll": [-7.7238, -79.1586], "ey": 1525, "ly": 2017},
  {"key": "Itá Ibaté-Argentina", "n": "Itá Ibaté", "c": "Argentina", "ll": [-27.42595, -57.33812], "ey": 1536, "ly": 2022},
  {"key": "Alto Saposoa-Peru", "n": "Alto Saposoa", "c": "Peru", "ll": [-6.76472, -76.81361], "ey": 1900, "ly": 2025},
  {"key": "Machupitumarka-Peru", "n": "Machupitumarka", "c": "Peru", "ll": [-13.51645, -71.6073], "ey": 0, "ly": 1530},
  {"key": "Gobernador Gregores-Argentina", "n": "Gobernador Gregores", "c": "Argentina", "ll": [-48.75085, -70.24852], "ey": 1900, "ly": 2022},
  {"key": "El Tigral O La Puntilla-Peru", "n": "El Tigral O La Puntilla", "c": "Peru", "ll": [-14.80762, -74.87368], "ey": -1000, "ly": 1530},
  {"key": "Arqueológico Chaulla Pampa-Peru", "n": "Arqueológico Chaulla Pampa", "c": "Peru", "ll": [-15.53534, -70.09785], "ey": 0, "ly": 1530},
  {"key": "Tumusla-Bolivia", "n": "Tumusla", "c": "Bolivia", "ll": [-20.48891, -65.61799], "ey": 1525, "ly": 2024},
  {"key": "Potrero de Payogasta-Argentina", "n": "Potrero de Payogasta", "c": "Argentina", "ll": [-24.996, -66.101], "ey": 1475, "ly": 1530},
  {"key": "Terlen - La Bomba-Peru", "n": "Terlen - La Bomba", "c": "Peru", "ll": [-7.18379, -79.03142], "ey": 0, "ly": 1530},
  {"key": "Pózul-Ecuador", "n": "Pózul", "c": "Ecuador", "ll": [-4.12522, -80.04609], "ey": 1525, "ly": 2025},
  {"key": "Las Perdices-Argentina", "n": "Las Perdices", "c": "Argentina", "ll": [-32.69906, -63.70466], "ey": 1850, "ly": 2022}
]

records = []
for root, _, files in os.walk('histmap/1.data_raw/population_regional/QUIPU'):
    for f in files:
        if f.endswith('_settlements.json'):
            p = os.path.join(root, f)
            data = json.load(open(p, encoding='utf-8'))
            if isinstance(data, dict):
                data = list(data.values())
            for r in data:
                if isinstance(r, dict) and 'coords' in r:
                    records.append((f, r))

out = {}
for item in chunk:
    lat, lng = item['ll']
    matches = []
    for fn, r in records:
        c = r.get('coords')
        if not c or len(c) < 2: continue
        d = ((float(c[0]) - lat)**2 + (float(c[1]) - lng)**2)**0.5
        if d < 0.05 or (r.get('name','').lower() == item['n'].lower() and d < 0.5):
            matches.append({
                'file': fn,
                'name': r.get('name'),
                'coords': c,
                'source': r.get('source'),
                'notes': r.get('notes'),
                'admin': r.get('admin_unit') or r.get('admin') or r.get('region'),
                'foundation': r.get('foundation_year') or r.get('founded'),
                'years': sorted([str(k) for k in (r.get('population') or {}).keys()])[:5]
            })
    out[item['key']] = matches

with open('tests/chunk029_quipu_hits.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Matched keys:", sum(1 for v in out.values() if v), "/", len(chunk))
