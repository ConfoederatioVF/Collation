import urllib.request, urllib.parse, json

q = '''SELECT ?item ?itemLabel ?inception ?eswiki WHERE {
  ?item wdt:P17 wd:Q414 .
  ?item rdfs:label "San Antonio de Arredondo"@es .
  OPTIONAL { ?item wdt:P571 ?inception . }
  OPTIONAL { ?eswiki schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en" . }
} LIMIT 5'''
url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})
req = urllib.request.Request(url, headers={'User-Agent': 'SVEA-Toponymy/1.0 (research)'})
with urllib.request.urlopen(req, timeout=15) as r:
    print(r.read().decode('utf-8'))
