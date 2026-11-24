import urllib.request, urllib.parse, json

items = [
('San Juan de la Virgen-Peru', -3.62778, -80.43361),
('Huancane-Bolivia_2', -18.706, -66.876),
('Guaraunos-Venezuela', 10.55689, -63.12233),
('Manglares-Colombia', 1.62, -78.992),
('Placilla (chl_region_de_valparaiso)-Chile', -32.44827, -71.28449),
('Médanos-Argentina', -38.8292, -62.69355),
('Tamarindo-Peru', -4.87833, -80.97583),
('Comanche-Bolivia', -17.06667, -68.41667),
('Vallecito-Argentina_2', -27.704, -64.287),
('Buena Vista Alta-Peru', -9.4325, -78.20694),
('Naranjal-Colombia_2', 4.797, -75.962),
('Manú-Ecuador', -3.52636, -79.42559),
('Dos Caminos-Colombia', 4.642, -74.449),
('Muyupampa-Bolivia', -19.89614, -63.75353),
('Puerto Misahuallí-Ecuador', -1.03387, -77.66862),
('Santiago de las Montañas-Peru', -4.435, -77.645),
('Villagómez-Colombia', 5.27302, -74.19514),
('Uverito (ven_anzoategui)-Venezuela', 8.11406, -64.68459),
('Añancusi-Peru', -12.587, -74.7154),
('Nenegal-Colombia', 0.885, -77.682),
('Pumpuentsa-Ecuador', -2.57864, -77.27424),
('Quíbor Guadalupe-Venezuela', 9.93, -69.62),
('General Morales-Ecuador', -2.36311, -79.06106),
('Pujili-Ecuador', -0.955, -78.696),
('Cajatambo-Peru', -10.47306, -76.99306),
('Uchuytambo-Peru', -14.861, -74.529),
('San Miguel De Sema-Colombia', 5.51808, -73.72201),
('Progreso-Ecuador', -3.25379, -79.66037),
('Camilo Aldao-Argentina', -33.1279, -62.09431),
('Chichinales-Argentina', -39.11488, -66.94252),
('Llorente-Colombia', 1.39134, -78.51932),
('Los Menucos-Argentina', -40.84277, -68.08587),
('Cabanillas-Peru', -15.64444, -70.35389),
('Aculeo-Chile', -33.868, -70.921),
('Francisco Aniceto Lugo-Venezuela', 8.27356, -60.29671),
('Los Piscontes-Peru', -14.1153, -75.6756),
('Río Blanco-Colombia', 2.08723, -76.66955),
('San Pedro de Arimena-Colombia', 4.60811, -71.62171),
('General Lagos-Argentina', -33.10994, -60.56463),
('Paccha-Peru', -6.4975, -78.42361),
('Suscal-Ecuador', -2.46333, -79.07108),
('Villa del Dique-Argentina', -32.17646, -64.45686),
('Guanarito (Paso Real de Papelón)-Venezuela', 8.70901, -69.21501),
('Huaranchal-Peru', -7.68972, -78.4425),
('Oyolo-Peru', -15.18, -73.18528),
('Parcelas-Colombia', 4.66126, -74.24149),
('Cerinza-Colombia', 5.95594, -72.94792),
('Campohermoso-Colombia', 5.03168, -73.10417),
('Mallares-Peru', -4.8583, -80.7619),
('Campeche-Colombia', 10.7265, -74.9136),
('Amaluza-Ecuador', -4.58003, -79.36431),
('Huimbayoc-Peru', -6.41778, -75.76806),
('Cacha-Ecuador', -1.71016, -78.70425),
('Chuin-Peru', -7.7502, -79.2788),
('Surcubamba-Peru', -12.11639, -74.63056),
('Santa María (ven_nueva_esparta)-Venezuela', 10.95056, -64.09944),
('Japio-Colombia', 3.047, -76.443),
('Santiago de Quirahuara-Peru', -14.05611, -74.97639),
('Buga-Colombia', 3.901, -76.298),
('Montalvo (ecu_pastaza)-Ecuador', -2.0617, -76.96491),
('Secocha-Peru', -15.9825, -73.1706)
]

for chunk_idx in range(0, len(items), 10):
    sub = items[chunk_idx:chunk_idx+10]
    values = ' '.join([f'("{k}" "Point({lng} {lat})"^^geo:wktLiteral)' for k, lat, lng in sub])
    q = f'''SELECT ?key ?item ?itemLabel ?itemDescription ?inception ?officialName ?dist ?article WHERE {{
      VALUES (?key ?pt) {{ {values} }}
      SERVICE wikibase:around {{
        ?item wdt:P625 ?loc .
        bd:serviceParam wikibase:center ?pt .
        bd:serviceParam wikibase:radius "3" .
        bd:serviceParam wikibase:distance ?dist .
      }}
      OPTIONAL {{ ?item wdt:P571 ?inception }}
      OPTIONAL {{ ?item wdt:P1448 ?officialName }}
      OPTIONAL {{ ?article schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
    }}'''
    url = 'https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(q)
    try:
        res = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'OperationViscount/1.0'}), timeout=30).read().decode('utf-8'))
        for b in res['results']['bindings']:
            lbl = b.get('itemLabel',{}).get('value','')
            desc = b.get('itemDescription',{}).get('value','')
            inc = b.get('inception',{}).get('value','')
            off = b.get('officialName',{}).get('value','')
            art = b.get('article',{}).get('value','')
            if inc or off or art or any(w in lbl.lower() for w in b['key']['value'].split('-')[0].lower().split()):
                print(b['key']['value'], '|', lbl, '|', desc, '|', inc, '|', off, '|', round(float(b['dist']['value']),2), '|', art)
    except Exception as e:
        print('ERR', chunk_idx, e)
