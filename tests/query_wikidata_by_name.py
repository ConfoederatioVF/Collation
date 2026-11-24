import urllib.request, urllib.parse, json, time

names = [
    "Nambacola", "Calacalí", "Cochapamba", "Paquisha", "Chobo", "San Javier de Cachaví",
    "Tucurinca", "Labarcés", "Zaragoza", "Magangué", "Ipiales", "Ricaurte",
    "Mojotoro", "Catacora", "Malla", "Villa Abecia",
    "Guaibacoa", "Cacute", "Padre Noguera", "Héctor Amable Mora", "Tucupido",
    "La Emilia", "Lamadrid", "Villa General Güemes", "El Alcázar", "Las Toninas",
    "Mayor Buratovich", "La Ciénaga", "Villa Borjas", "El Zanjón",
    "Marindia", "Teno", "Bollenar",
    "Antauta", "Acos Vinchos", "Cuyocuyo", "Manuel Antonio Mesones Muro", "Machupicchu",
    "Aguas Calientes", "Charcana", "Bellavista de la Unión", "Mocan", "San Andrés de Cutervo",
    "Miracosta", "Matapalo", "San Miguel de Corpanqui", "Jeberos", "Yauya", "Lucre", "Paratía",
    "Alejandría", "Macanal", "Jesús María", "Angamarca", "San Miguelito"
]

# Query Wikidata for exact eswiki articles via MediaWiki API search or Wikidata SPARQL
# Let's use Spanish Wikipedia opensearch/search in 1 batch? Better: Wikidata SPARQL VALUES ?lbl
vals = ' '.join(f'"{n}"@es' for n in names[:28])
q1 = f'''
SELECT ?lbl ?item ?itemLabel ?desc ?inception ?eswiki ?coord WHERE {{
  VALUES ?lbl {{ {vals} }}
  ?item rdfs:label ?lbl .
  ?item wdt:P625 ?coord .
  OPTIONAL {{ ?item wdt:P571 ?inception . }}
  OPTIONAL {{ ?eswiki schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> . }}
  OPTIONAL {{ ?item schema:description ?desc . FILTER(LANG(?desc) = "es") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
}}
'''
vals2 = ' '.join(f'"{n}"@es' for n in names[28:])
q2 = f'''
SELECT ?lbl ?item ?itemLabel ?desc ?inception ?eswiki ?coord WHERE {{
  VALUES ?lbl {{ {vals2} }}
  ?item rdfs:label ?lbl .
  ?item wdt:P625 ?coord .
  OPTIONAL {{ ?item wdt:P571 ?inception . }}
  OPTIONAL {{ ?eswiki schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> . }}
  OPTIONAL {{ ?item schema:description ?desc . FILTER(LANG(?desc) = "es") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
}}
'''

out = {}
for idx, q in enumerate([q1, q2]):
    data = urllib.parse.urlencode({'query': q, 'format': 'json'}).encode()
    req = urllib.request.Request('https://query.wikidata.org/sparql', data=data, headers={'User-Agent': 'QuipuResearch/1.0 (mailto:research@confoederatio.org)'})
    res = json.loads(urllib.request.urlopen(req, timeout=45).read().decode())
    for b in res['results']['bindings']:
        lbl = b['lbl']['value']
        out.setdefault(lbl, []).append({
            'desc': b.get('desc',{}).get('value',''),
            'inception': b.get('inception',{}).get('value',''),
            'eswiki': b.get('eswiki',{}).get('value',''),
            'coord': b.get('coord',{}).get('value',''),
        })
    time.sleep(1)

with open('tests/wikidata_by_name.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('Matched labels:', len(out))
