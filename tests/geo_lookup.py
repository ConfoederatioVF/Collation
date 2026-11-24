import json, time, urllib.parse, urllib.request

HEADERS = {'User-Agent': 'SVEA-Toponymy-Research/1.0 (historical-gazetteer-project)'}

settlements = [
  {"key": "Bolognes-Peru", "n": "Bolognes", "c": "Peru", "r": "inca_chinchaysuyu", "ll": [-3.60828, -76.42395], "ey": -2000, "ly": 1530, "p": 6269},
  {"key": "Guañape-Peru", "n": "Guañape", "c": "Peru", "r": "vp_intendencia_trujillo", "ll": [-8.44, -78.923], "ey": 1525, "ly": 1762, "p": 6265},
  {"key": "Arrayan-Peru", "n": "Arrayan", "c": "Peru", "r": "per_amazonas", "ll": [-5.5969, -78.4416], "ey": 1525, "ly": 2017, "p": 6260, "al": ["la peca", "peco", "La Peca"]},
  {"key": "Lagarto-Ecuador", "n": "Lagarto", "c": "Ecuador", "r": "ecu_esmeraldas", "ll": [1.00354, -79.20444], "ey": 1850, "ly": 2025, "p": 6255},
  {"key": "Guatases-Ecuador", "n": "Guatases", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [-2.91, -78.774], "ey": 1525, "ly": 1830, "p": 6252},
  {"key": "Pilpichaca-Peru", "n": "Pilpichaca", "c": "Peru", "r": "per_huancavelica", "ll": [-13.33028, -74.97722], "ey": 1525, "ly": 2025, "p": 6246},
  {"key": "Mira-Ecuador_2", "n": "Mira", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [0.55, -78.042], "ey": 1525, "ly": 1830, "p": 6245, "al": ["miraflores", "Miraflores"]},
  {"key": "Puntales-Ecuador", "n": "Puntales", "c": "Ecuador", "r": "vng_audiencia_quito_sierra", "ll": [0.502, -77.905], "ey": 1525, "ly": 1830, "p": 6243, "al": ["puntal", "puntas", "Puntal"]},
  {"key": "Santiago de Callapa-Bolivia", "n": "Santiago de Callapa", "c": "Bolivia", "r": "bol_la_paz", "ll": [-17.47881, -68.35533], "ey": 1525, "ly": 2024, "p": 6241, "al": ["callapa", "Callapa"]},
  {"key": "Chaucayan-Peru", "n": "Chaucayan", "c": "Peru", "r": "per_ancash", "ll": [-10.1857, -77.5552], "ey": 1525, "ly": 2017, "p": 6240},
  {"key": "Queros-Peru", "n": "Queros", "c": "Peru", "r": "per_la_libertad", "ll": [-8.0246, -77.5342], "ey": 1525, "ly": 2017, "p": 6239},
  {"key": "Llanca-Peru", "n": "Llanca", "c": "Peru", "r": "vp_intendencia_arequipa", "ll": [-15.562, -72.047], "ey": 1525, "ly": 1825, "p": 6238},
  {"key": "Llauta-Peru", "n": "Llauta", "c": "Peru", "r": "per_ayacucho", "ll": [-14.24361, -74.92028], "ey": 1525, "ly": 2025, "p": 6234},
  {"key": "Riochico-Colombia", "n": "Riochico", "c": "Colombia", "r": "vng_antioquia_popayan_choco", "ll": [6.51, -75.537], "ey": 1525, "ly": 1830, "p": 6234},
  {"key": "La Morita-Venezuela", "n": "La Morita", "c": "Venezuela", "r": "ven_yaracuy", "ll": [10.29241, -68.74363], "ey": 1850, "ly": 2011, "p": 6233},
]

def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))

for s in settlements:
    lat, lon = s['ll']
    print(f"=== {s['key']} ({lat}, {lon}) ===")
    try:
        nom = get_json(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=14&accept-language=es")
        print("  OSM:", nom.get('display_name'), "| addr:", nom.get('address'))
    except Exception as e:
        print("  OSM err:", e)
    try:
        geo = get_json(f"https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=10000&gslimit=5&format=json")
        print("  WikiGeo:", [x['title'] for x in geo.get('query', {}).get('geosearch', [])])
    except Exception as e:
        print("  WikiGeo err:", e)
    time.sleep(1.1)
