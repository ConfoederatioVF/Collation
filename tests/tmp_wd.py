import json
import urllib.parse
import urllib.request

q = """
SELECT ?item ?itemLabel ?coord ?inception ?article WHERE {
  ?item wdt:P625 ?coord .
  FILTER(geof:distance(?coord, "Point(-72.315 7.825)"^^geo:wktLiteral) < 15)
  OPTIONAL { ?item wdt:P571 ?inception . }
  OPTIONAL {
    ?article schema:about ?item ;
             schema:isPartOf <https://es.wikipedia.org/> .
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". }
}
LIMIT 20
"""
u = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)
req = urllib.request.Request(u, headers={"User-Agent": "SVEA-Toponymy/1.0"})
data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
for b in data["results"]["bindings"]:
  print(b.get("itemLabel", {}).get("value"), "|", b.get("inception", {}).get("value"), "|", b.get("article", {}).get("value"))
