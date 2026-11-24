import urllib.request
import urllib.parse
import json
import time
import re

HDR = {"User-Agent": "SVEA-ToponymyResearch/1.0 (https://confoederatio.org; research@confoederatio.org)"}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HDR)
    return json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))

queries = [
  ("Quispe-Peru", "Quispe Ocalli Amazonas"),
  ("Carhuacucho-Peru", "Carhuacucho Huac-Huas Ayacucho"),
  ("Marazzi-Chile", "Marazzi Tierra del Fuego"),
  ("Huacanca-Peru", "Huacanca Challabamba Paucartambo"),
  ("José Nucete Sardi-Venezuela", "\"José Nucete Sardi\" Mérida"),
  ("San Antonio de Tatama-Colombia", "Tatamá Risaralda Chocó"),
  ("Pungalá-Ecuador", "Pungalá Riobamba Chimborazo"),
  ("Terrazas de Santo Domingo-Venezuela", "\"Terrazas de Santo Domingo\" Barinas"),
  ("Santa Ana (col_valle_del_cauca)-Colombia", "\"Santa Ana\" Miranda OR Florida \"Valle del Cauca\""),
  ("El Morado-Colombia", "\"El Morado\" Caramanta OR Supía"),
  ("Los Cerritos de San José-Venezuela", "\"Los Cerritos de San José\" Lara"),
  ("Diosan-Peru", "Diosan Olleros Chachapoyas"),
  ("Cerro La Pampa-Peru", "\"Cerro La Pampa\" OR \"Huaca Pinilla\" Ocucaje"),
  ("Quilcacé-Colombia", "Quilcacé Cauca"),
  ("Negrillos-Bolivia", "Negrillos Sabaya Oruro"),
  ("Atancama-Peru", "Atancama Lambrama Abancay"),
  ("Huacánduna-Peru", "Huacanduna Huaura"),
  ("Campamento Pan de Azucar-Chile", "\"Pan de Azúcar\" Pintados Tarapacá"),
  ("El Coco-Colombia_2", "\"El Coco\" Tumaco Nariño"),
  ("Taquilpon-Peru", "Taquilpón OR Taquilpon"),
  ("Wichu Pampa-Bolivia", "\"Wichu Pampa\" Oruro"),
  ("Aparicio-Venezuela", "Aparicio Piar Monagas"),
  ("Terraza Chumbe-Peru", "Zungache Loreto"),
  ("San Pablo De Ushpayacu-Ecuador", "\"San Pablo de Ushpayacu\" Archidona"),
  ("Yambajalca-Peru", "Yambajalca Olleros Chachapoyas"),
  ("Quebrada Honda-Venezuela", "\"Quebrada Honda\" Urdaneta Miranda"),
  ("San Mateo Cuturi-Peru", "Cuturi Arapa Puno"),
  ("Torre-Colombia", "Puerto Nare Antioquia"),
  ("Manco Kapac-Bolivia", "\"Manco Kapac\" Entre Ríos Cochabamba"),
  ("Cosapa-Bolivia", "Cosapa Turco Oruro"),
  ("Hualla (per_cusco)-Peru", "Hualla Paucartambo Cusco"),
  ("Huaca La Humedad-Peru", "\"Cojal\" OR \"Songoy\" Cayaltí Zaña"),
  ("Guainiamo-Venezuela", "Guainiamo Cedeño Bolívar"),
  ("Valle de Tunjuelo-Colombia", "Tunjuelo Usme Bogotá"),
  ("Molloqos-Peru", "Molloqos Pichigua Espinar"),
  ("Santa Rita (ven_trujillo)-Venezuela", "\"Santa Rita\" Escuque Valera Trujillo"),
  ("Paraná Miní-Argentina", "\"Paraná Miní\" Santa Fe"),
  ("Cerro Portachuelo-Peru", "\"Cerro Portachuelo\" Virú"),
  ("La Manuelita-Colombia", "\"La Manuelita\" Putumayo"),
  ("Casa Blanca-Peru", "\"Casa Blanca\" Santiago Ica"),
  ("Libertad de Cojedes-Venezuela", "Libertad de Cojedes"),
  ("En Proceso (inca_chinchaysuyu_7)-Peru", "\"Chacuas Pampa\" OR Churubamba Huánuco"),
  ("Parquin-Peru", "Parquin Santa Leonor Huaura"),
  ("Cerrillos-Argentina", "Cerrillos Rinconada Jujuy"),
  ("Llactaraccay-Peru", "Llactaraccay Rondocan"),
  ("Cancharani-Peru", "Cancharani Puno"),
  ("Andamarca (vp_intendencia_huamanga_huancavelica)-Peru", "Andamarca Charcana Cotahuasi OR Pausa"),
]

out_lines = []
for key, q in queries:
    url = "https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch=" + urllib.parse.quote(q) + "&srlimit=3&format=json"
    try:
        res = fetch_json(url)
        hits = [(h["title"], re.sub("<[^>]+>", "", h.get("snippet", ""))[:120]) for h in res.get("query", {}).get("search", [])]
        out_lines.append(f"ES {key} => {hits}")
    except Exception as e:
        out_lines.append(f"ES {key} ERR: {e}")
    time.sleep(0.12)

with open("tests/tmp_wiki_search.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
print("DONE", len(out_lines))
