import json, urllib.request, urllib.parse, time, re

HEADERS = {"User-Agent": "SVEAHistoricalResearch/1.0 (contact@example.org)"}

def wiki_search_and_summary(query, lang="es"):
    q = urllib.parse.quote(query)
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    hits = data.get("query", {}).get("search", [])
    results = []
    for h in hits[:2]:
        title = h["title"]
        t_enc = urllib.parse.quote(title)
        url2 = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&exintro=1&explaintext=1&titles={t_enc}&format=json"
        req2 = urllib.request.Request(url2, headers=HEADERS)
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            d2 = json.loads(resp2.read().decode("utf-8"))
        pages = d2.get("query", {}).get("pages", {})
        for pid, pinfo in pages.items():
            results.append({
                "title": title,
                "coords": pinfo.get("coordinates"),
                "extract": (pinfo.get("extract") or "")[:600]
            })
    return results

# Test non-arch settlements (we will expand or customize list based on raw_sites output)
QUERIES = [
  ("Medina-Argentina", "Medina Tucuman Chicligasta"),
  ("Medialuna-Colombia", "Medialuna Pivijay Magdalena"),
  ("Quiaca-Peru", "Distrito de Quiaca Sandia Puno"),
  ("Cucuta-Bolivia", "Cucuta Laja La Paz Bolivia"),
  ("La Estrella-Chile", "La Estrella Chile"),
  ("Pichinde-Colombia", "Pichinde Cali"),
  ("San Jacinto Gaira-Colombia", "Gaira Santa Marta"),
  ("Plaza-Chile", "La Ligua Chile"),
  ("Sección Capital Sucre-Venezuela", "Maripa Bolivar Venezuela"),
  ("Filas de Mariches-Venezuela", "Filas de Mariches"),
  ("María Susana-Argentina", "Maria Susana Santa Fe"),
  ("General Vedia-Argentina", "General Vedia"),
  ("Coate-Bolivia", "Coate La Paz Bolivia"),
  ("Manuel Cornejo Astorga-Ecuador", "Manuel Cornejo Astorga Tandapi"),
  ("Mancopa-Argentina", "Mancopa Tucuman"),
  ("San Juan Bautista Carache-Venezuela", "Carache Trujillo Venezuela"),
  ("Tacocumo-Bolivia", "Tacocumo Cochabamba"),
  ("Pucchun-Peru", "Pucchun Camana"),
  ("Cipriano Castro-Venezuela", "Cipriano Castro Tachira Independencia Capacho"),
  ("Inchupalla-Peru", "Distrito de Inchupalla"),
  ("Totora (vp_intendencia_cochabamba)-Bolivia", "Totora Cochabamba"),
  ("San Francisco (ven_anzoategui)-Venezuela", "San Francisco Anzoategui"),
  ("Lehmann-Argentina", "Lehmann Santa Fe"),
  ("Chilla-Ecuador", "Canton Chilla El Oro"),
  ("Toko-Bolivia", "Toco Cochabamba"),
  ("Valle Hermoso-Chile", "Valle Hermoso La Ligua"),
  ("Itacaruaré-Argentina", "Itacaruare"),
  ("Tango-Chile", "Calera de Tango"),
  ("Rumicucho-Ecuador", "Rumicucho"),
  ("General Lucio Victorio Mansilla-Argentina", "General Lucio Victorio Mansilla Formosa"),
  ("Gobernador Piedrabuena-Argentina", "Gobernador Piedrabuena Tucuman"),
  ("Enace I II III-Peru", "Talara Enace Piura"),
  ("Pujato-Argentina", "Pujato Santa Fe"),
  ("Camsana-Chile", "Camsana Tarapaca"),
  ("Crucero de Pescador-Colombia", "Pescador Caldono Cauca"),
  ("Progreso-Peru", "Distrito de Progreso Grau Apurimac"),
  ("Antonio Nicolás Briceño-Venezuela", "Antonio Nicolas Briceno Trujillo"),
  ("Cerca de Piedra-Colombia", "Cerca de Piedra Chia Cundinamarca"),
  ("Choros-Peru", "Distrito de Choros Cutervo"),
  ("Los Cerrillos-Uruguay", "Los Cerrillos Uruguay"),
  ("Villa Parque Síquiman-Argentina", "Villa Parque Siquiman"),
  ("Toquepala-Peru", "Toquepala"),
  ("Los Naranjos-Venezuela", "Los Naranjos Zulia Francisco Javier Pulgar"),
  ("Ciudad del Carmen-Uruguay", "Villa del Carmen Durazno"),
  ("Palmales-Ecuador", "Palmales Arenillas El Oro"),
  ("Cerro Sota-Chile", "Cerro Sota"),
  ("Chugur-Peru", "Distrito de Chugur Hualgayoc"),
  ("Huambi-Ecuador", "Huambi Sucua Morona Santiago"),
  ("Selva-Argentina", "Selva Santiago del Estero"),
  ("Choroma-Bolivia", "Choroma Potosi"),
  ("Londres-Argentina", "Londres Catamarca"),
  ("Arroyo de Piedra-Colombia", "Arroyo de Piedra Luruaco Atlantico"),
  ("Yamon-Peru", "Distrito de Yamon Utcubamba"),
  ("Bombal-Argentina", "Bombal Santa Fe"),
  ("Bilován-Ecuador", "Bilovan San Miguel Bolivar"),
  ("Choquecota-Bolivia", "Choquecota Oruro"),
  ("Pueblo Independencia-Argentina", "Pueblo Independencia Tucuman"),
  ("El Cabo-Ecuador", "El Cabo Paute Azuay Canar"),
  ("Alicia-Argentina", "Alicia Cordoba"),
  ("Monte Comán-Argentina", "Monte Coman Mendoza"),
]

out = {}
for key, q in QUERIES:
    try:
        res = wiki_search_and_summary(q, "es")
        out[key] = res
        top = res[0] if res else {}
        print(f"=== {key} | {top.get('title')} ===")
        print("  ", top.get("extract", "")[:260].replace("\n", " "))
    except Exception as e:
        print(f"=== {key} ERROR: {e} ===")
    time.sleep(0.1)

with open("tests/_wiki_results_chunk047.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
