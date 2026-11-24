import json
import time
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "OperationViscountResearch/1.0 (https://confoederatio.org)"}

def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == retries - 1:
                return {"error": str(e)}
            time.sleep(1.0)

def get_extracts(lang, titles):
    out = {}
    for i in range(0, len(titles), 5):
        batch = titles[i:i+5]
        t_param = urllib.parse.quote("|".join(batch))
        url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exchars=3500&redirects=1&titles={t_param}&format=json"
        data = fetch_json(url)
        pages = data.get("query", {}).get("pages", {})
        for p in pages.values():
            if "title" in p and "extract" in p:
                out[p["title"]] = p["extract"]
        time.sleep(0.2)
    return out

def search_wiki(lang, query):
    q = urllib.parse.quote(query)
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
    data = fetch_json(url)
    return [(s["title"], s.get("snippet", "")) for s in data.get("query", {}).get("search", [])]

EXACT_ES_TITLES = [
    "Santafé de Morichal",
    "Distrito de Santo Domingo de Capillas",
    "Verónica (Argentina)",
    "Salango",
    "Distrito de Oropesa (Antabamba)",
    "Distrito de Caraybamba",
    "Chiu Chiu",
    "Distrito de Vilcanchos",
    "Distrito de Toraya",
    "San Miguel de Viso",
    "Yavi",
    "Santa Rosalía (Caracas)",
    "Petorca",
    "El Caguán (Neiva)",
    "Romeral",
    "Distrito de Ticllos",
    "Chillogallo (parroquia)",
    "Bayas (Ecuador)",
    "Santa Rosa de Cuzubamba",
    "La Magdalena (Quito)",
    "Chillán",
    "Distrito de Canis",
    "San José de Chimbo",
    "Distrito de Pocohuanca",
    "Salasaka",
    "Zumbi (ciudad)",
    "Páramo (Santander)",
    "Distrito de Tambo (Huaytará)",
    "Unamuncho",
    "Pasa (Ecuador)",
    "Flores (Ecuador)",
    "Ávila (Orellana)",
    "Cunaviche",
    "Laja (Bolivia)",
    "Independencia (Bolivia)",
    "Distrito de Yorongos",
    "Amparaes",
    "Arévalo González",
    "El Clavo",
    "Belén (Chile)",
]

SEARCH_QUERIES = [
    ("es", '"Orejas de Burro" arqueología Santa Cruz'),
    ("es", '"Pepinales" Alausí OR Chimborazo'),
    ("es", '"Diego Hernández" Aguachica OR Cesar'),
    ("es", '"Buena Vista" "Monte Carmelo" OR "Trujillo" Venezuela'),
    ("es", '"Quizu" Canta OR Arahuay'),
    ("es", '"Llano del Muerto" Candelaria OR Jamundí OR Cali'),
    ("es", '"Mamblachi" OR "Chañar Pugio" Santiago del Estero'),
    ("es", '"Huancarama" Oruro OR Challapata OR Poopó'),
    ("es", '"Vuelta Larga" Tumaco OR Zapotal arqueología'),
    ("es", '"Guayllang" OR "Guayllanac" Chimborazo'),
    ("es", '"Chelel" Soloco OR Chachapoyas'),
    ("es", '"Chiris" Huancavelica OR Castrovirreyna'),
    ("es", '"Lurihuas" Supe OR Barranca'),
    ("es", '"La Pastora" Falcón OR Acosta Venezuela'),
    ("es", '"Intag" Cotacachi historia'),
    ("es", '"Lamari" Palpa OR Ocoyo'),
    ("es", '"Tomanga" Sarhua OR Fajardo'),
    ("es", '"Cabinda" Córdoba historia OR estancia'),
    ("es", '"Arajuno" historia fundación'),
    ("es", '"Carhuapampa" Bolognesi historia'),
    ("es", '"Sinto" Huancavelica OR Castrovirreyna OR Esmeralda'),
    ("es", '"Sageo" Biblián historia'),
    ("es", '"Warichupa" Huánuco OR Lauricocha'),
    ("es", '"Huanacaure" Huánuco OR Pachitea'),
    ("es", '"Quisquis" Yaután OR Casma'),
    ("es", '"Cerro Gato" Lambayeque OR Pucalá'),
    ("es", '"El Simbolar" Córdoba arqueología OR Cruz del Eje'),
    ("es", '"Santa Cruz" Cutervo Cajamarca distrito'),
    ("es", '"Para" Lucanas OR Parinacochas Ayacucho'),
    ("es", '"Llocllo" Laja OR Ingavi Bolivia'),
    ("es", '"Subcunga" OR "Subyunca" Apurímac'),
    ("es", '"Estancopata" Quispicanchi OR Urcos'),
    ("es", '"Espite" Paras Cangallo'),
    ("es", '"Congona" Leymebamba OR "Cataneo"'),
    ("en", '"Orejas de Burro" Patagonia cave'),
    ("en", '"Vuelta Larga" Colombia archaeology OR Tumaco'),
    ("en", '"Salango" Ecuador archaeology OR history'),
]

extracts = get_extracts("es", EXACT_ES_TITLES)
searches = {}
for lang, q in SEARCH_QUERIES:
    searches[f"{lang}:{q}"] = search_wiki(lang, q)
    time.sleep(0.15)

with open("tests/chunk022_targeted.json", "w", encoding="utf-8") as f:
    json.dump({"extracts": extracts, "searches": searches}, f, ensure_ascii=False, indent=2)

print(f"Got {len(extracts)} extracts and {len(searches)} search results.")
