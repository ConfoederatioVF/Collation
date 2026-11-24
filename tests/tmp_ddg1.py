import re
import time
import urllib.parse
import urllib.request
from html import unescape

queries = [
  ("Areo-Venezuela", '"Areo" Monagas Venezuela fundacion "San Jose"'),
  ("Esquena-Peru", '"Esquena" Coasa Carabaya Puno Peru historia'),
  ("Serrano-Argentina", '"Serrano" Cordoba Argentina fundacion historia'),
  ("Barreal-Argentina", '"Barreal" Calingasta San Juan fundacion "Pituil"'),
  ("Antiguala-Chile", '"Antihuala" OR "Antiguala" Los Alamos Chile historia fundacion'),
  ("Miraflores-Peru", '"Miraflores" Huamalies Huanuco creacion "Pampas de Flores"'),
  ("Villa Santa Rosa-Argentina", '"Villa Santa Rosa" "25 de Mayo" San Juan Argentina fundacion'),
  ("Arteaga-Argentina", '"Arteaga" Santa Fe Argentina fundacion'),
  ("Mincha-Chile", '"Mincha" Canela Coquimbo fundacion historia 1692'),
  ("Portillo-Bolivia", '"Portillo" Tarija Bolivia historia'),
  ("Anchayacu-Ecuador", '"Anchayacu" Eloy Alfaro Esmeraldas parroquializacion fundacion'),
  ("El Cerrito I-Venezuela", '"Santa Ana" Paraguana Falcon fundacion 1538 "Cerrito"'),
  ("Antavilque-Peru", '"Antavilque" Puno Peru historia'),
  ("Villa Alfredo Fortabat-Argentina", '"Villa Alfredo Fortabat" OR "Loma Negra" Olavarria fundacion'),
  ("Hualqui-Chile", '"Hualqui" "San Juan Bautista" fundacion 1757'),
  ("Hersilia-Argentina", '"Hersilia" Santa Fe fundacion'),
  ("San Mateo-Venezuela", '"San Mateo" Anzoategui fundacion 1715 "Prepuntar"'),
  ("Sepulturas-Bolivia", '"Sepulturas" Oruro Bolivia historia'),
  ("Buta Ranquil-Argentina", '"Buta Ranquil" Neuquen fundacion'),
  ("Maximo Paz-Argentina", '"Maximo Paz" Santa Fe fundacion'),
  ("Chavarria-Argentina", '"Chavarria" Corrientes fundacion'),
  ("Yarumito-Colombia", '"Yarumito" Cauca Colombia historia'),
  ("La Victoria-Ecuador", '"La Victoria" "Santa Rosa" "El Oro" parroquializacion'),
  ("Hilario Ascasubi-Argentina", '"Hilario Ascasubi" Villarino Buenos Aires fundacion'),
  ("San Juan Ojiba-Ecuador", '"Ojiva" OR "Ujiva" OR "Puebloviejo" "Los Rios" Ecuador fundacion'),
  ("Santiago-Bolivia_2", '"Santiago de Huata" historia fundacion Bolivia'),
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
