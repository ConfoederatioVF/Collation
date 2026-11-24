import re
import time
import urllib.parse
import urllib.request
from html import unescape

queries = [
  ("Rio Blanco-Ecuador", '"Rio Blanco" "Morona" parroquializacion Ecuador'),
  ("Esmeralda-Chile", '"Esmeralda" Rengo Chile historia'),
  ("Casanare Achagua-Colombia", '"Yopal" Casanare historia fundacion 1915 OR 1936 OR 1942'),
  ("El Palo-Colombia", '"El Palo" Caloto Cauca historia'),
  ("Llanquera-Bolivia", '"Llanquera" Oruro historia fundacion'),
  ("Gualmatan-Colombia", '"Gualmatan" Pasto corregimiento historia'),
  ("Oton-Ecuador", '"Oton" Cayambe Pichincha parroquializacion fundacion'),
  ("Guarumo-Colombia", '"Guarumo" Caceres Antioquia historia'),
  ("Jenesano-Colombia_2", '"Jenesano" Boyaca historia fundacion'),
  ("Villa Marina-El Pico-Venezuela", '"Villa Marina" "Los Taques" Falcon historia'),
  ("Juan Bautista Alberdi-Argentina", '"Juan Bautista Alberdi" "Leandro N. Alem" Buenos Aires fundacion'),
  ("9 de Julio-Argentina", '"9 de Julio" OR "Nueve de Julio" Corrientes fundacion'),
  ("Sacanta-Argentina", '"Sacanta" Cordoba fundacion'),
  ("Elena-Argentina", '"Elena" Cordoba Argentina fundacion'),
  ("Veracruz-Venezuela", '"Veracruz" Tachira Venezuela'),
  ("Rio Grande-Peru", '"Distrito de Rio Grande" Palpa creacion'),
  ("Sina-Peru", '"Distrito de Sina" Puno creacion historia'),
  ("Cutusuma-Bolivia", '"Cutusuma" OR "Ocobaya" Sud Yungas historia'),
  ("San Felix-Venezuela", '"San Felix" Mauroa Falcon fundacion historia'),
  ("Puente de Piedra-Colombia", '"Puente de Piedra" Madrid Cundinamarca historia'),
  ("Topo-Colombia", '"Topo" Muzo OR Quipama OR Paime Boyaca Cundinamarca historia'),
  ("Presidente Urbina-Ecuador", '"Presidente Urbina" Pillaro Tungurahua parroquializacion'),
  ("Los Condores-Argentina", '"Los Condores" Cordoba Argentina fundacion'),
  ("San Sebastian de los Reyes-Venezuela", '"San Sebastian de los Reyes" Aragua fundacion 1585'),
  ("Yatay Ti Calle-Argentina", '"Yatay Ti Calle" OR "Yatayti Calle" Corrientes fundacion'),
]

def ddg(q):
  data = urllib.parse.urlencode({"q": q}).encode("utf-8")
  req = urllib.request.Request(
    "https://lite.duckduckgo.com/lite/",
    data=data,
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
  )
  with urllib.request.urlopen(req, timeout=15) as r:
    html = r.read().decode("utf-8", errors="ignore")
  snippets = re.findall(r"<td class='result-snippet'>(.*?)</td>", html, re.S)
  clean = [re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s))).strip() for s in snippets[:3]]
  return clean

for k, q in queries:
  try:
    sn = ddg(q)
    print(f"=== {k} ===")
    for s in sn:
      print("  -", s[:260])
  except Exception as e:
    print(f"=== {k} ERR: {e} ===")
  time.sleep(0.6)
