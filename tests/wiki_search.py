import json, time, urllib.parse, urllib.request, re

HEADERS = {'User-Agent': 'SVEA-Toponymy-Research/1.0 (https://example.org; contact@example.org)'}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode('utf-8', errors='replace')

queries = [
    ("Bolognes", "Bolognesi Andoas Datem del Marañon Loreto"),
    ("Guañape", "Guañape Virú historia colonial"),
    ("Arrayan", "La Peca Bagua Amazonas historia"),
    ("Lagarto", "Lagarto Rioverde Esmeraldas parroquia"),
    ("Guatases", "Guatases Chordeleg Azuay"),
    ("Pilpichaca", "Distrito de Pilpichaca"),
    ("Mira", "Cantón Mira Carchi Chontahuasi"),
    ("Puntales", "Bolívar Carchi El Puntal"),
    ("Santiago de Callapa", "Santiago de Callapa Pacajes"),
    ("Chaucayan", "Chaucayan Llacllin Recuay"),
    ("Queros", "Queros Parcoy Pataz"),
    ("Llanca", "Llanca Choco Castilla Arequipa"),
    ("Llauta", "Distrito de Llauta"),
    ("Riochico", "Riochico Entrerríos Antioquia"),
    ("La Morita", "La Morita Independencia Yaracuy"),
]

# Query Wikidata API (wbsearchentities) and es.wikipedia search sequentially with polite delay
for name, q in queries:
    print(f"=== {name}: {q} ===")
    try:
        url = "https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch=" + urllib.parse.quote(q) + "&srlimit=3&format=json"
        data = json.loads(fetch(url))
        for hit in data.get("query", {}).get("search", []):
            snip = re.sub(r'<[^>]+>', '', hit.get('snippet', ''))
            print(f"  [eswiki] {hit['title']}: {snip}")
    except Exception as e:
        print(f"  [eswiki err] {e}")
    time.sleep(1.5)
