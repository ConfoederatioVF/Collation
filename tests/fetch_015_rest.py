import json
import re
import time
import urllib.parse
import urllib.request
from html import unescape

TITLES_ES = [
  "Distrito de Luya Viejo", "Luya Viejo",
  "Distrito de Huaquirca", "Huaquirca",
  "Distrito de Chisquilla",
  "Distrito de Umachiri",
  "El Ángel (Ecuador)", "Cantón Espejo",
  "Distrito de Mariscal Gamarra",
  "Distrito de Quinjalca",
  "Distrito de Cochabamba (Huaraz)",
  "Lámud", "Distrito de Lámud",
  "Archidona (Ecuador)",
  "Distrito de Quinocay",
  "Distrito de Chachas",
  "Cubijíes",
  "Distrito de Huacllán",
  "Ventarrón",
  "Distrito de Turpo",
  "Huayllati", "Distrito de Huayllati",
  "Distrito de Cupisnique",
  "Distrito de San Salvador de Quije",
  "Cojitambo",
  "Distrito de Succha",
  "Yumbo",
  "Molleturo",
  "Distrito de Caja",
  "Distrito de Coya", "Coya (Cusco)",
  "Distrito de Huampará",
  "Moruy",
  "Páez (Cauca)",
  "Distrito de Ichuña", "Ichuña",
  "Rere",
  "Zona Bananera",
  "Timar",
  "Candelaria (Valle del Cauca)",
  "Caype",
  "Distrito de Circa",
  "Coper",
  "Mutca",
  "Nánchoc", "Distrito de Nánchoc", "Ñanchoc (sitio arqueológico)",
  "San Francisco del Vergel",
  "Sisicaya", "Distrito de Antioquía",
  "Distrito de Chinchao", "Chinchao",
  "El Morro (Guayas)",
  "Jadán",
  "Dureno",
  "Chiguaza",
  "El Eno",
  "Guacamayal",
  "Tuama", "Villanueva de Tuama",
  "Ayalan", "Ayalán",
  "Batán Grande",
  "Distrito de Vítor",
  "Cambio Puente",
  "Córdoba (Sopetrán)", "Sopetrán",
  "Caparrapí",
  "Tenjo",
  "Distrito de Paccho",
  "Distrito de Checras",
  "Distrito de Vitoc",
  "Distrito de Sarhua",
  "Distrito de Accha",
  "Distrito de Huaso",
  "Distrito de Ccatca",
  "Distrito de Lambrama",
  "Municipio San Francisco (Zulia)",
  "Municipio Federación",
  "Municipio Rafael Rangel", "Isnotú",
  "Distrito de Huamachuco",
  "Distrito de Poroto",
  "Novirao", "Totoró (Cauca)",
  "Santuario de Quillacas", "Challapata",
  "Nieve Nieve"
]

TITLES_EN = [
  "Luya Viejo District", "Huaquirca District", "Chisquilla District",
  "Umachiri District", "El Ángel, Ecuador", "Mariscal Gamarra District",
  "Quinjalca District", "Cochabamba District, Huaraz", "Lamud",
  "Archidona, Ecuador", "Quinocay District", "Chachas District",
  "Huacllan District", "Ventarron", "Turpo District", "Huayllati District",
  "Cupisnique District", "San Salvador de Quije District", "Cojitambo",
  "Succha District", "Yumbo", "Molleturo", "Caja District", "Coya District",
  "Huampara District", "Páez, Cauca", "Belalcázar, Cauca", "Ichuña District",
  "Rere, Chile", "Circa District", "Coper, Boyacá", "Nanchoc District",
  "Ayalan", "Bucheli, Nariño"
]

def clean_html(raw):
  raw = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.S)
  raw = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.S)
  raw = re.sub(r"<sup[^>]*>.*?</sup>", "", raw, flags=re.S)
  # keep newlines at block tags
  raw = re.sub(r"</?(p|h[1-6]|tr|li|div|section)[^>]*>", "\n", raw)
  raw = re.sub(r"</?(td|th)[^>]*>", " | ", raw)
  raw = re.sub(r"<[^>]+>", " ", raw)
  raw = unescape(raw)
  lines = []
  for ln in raw.splitlines():
    ln = re.sub(r"\s+", " ", ln).strip()
    if ln:
      lines.append(ln)
  return "\n".join(lines)

def fetch_one(lang, title):
  enc = urllib.parse.quote(title.replace(" ", "_"))
  url = f"https://{lang}.wikipedia.org/api/rest_v1/page/html/{enc}"
  req = urllib.request.Request(url, headers={"User-Agent": "AntigravityAcademicBot/1.0 (mailto:research@example.org)"})
  try:
    with urllib.request.urlopen(req, timeout=12) as resp:
      html = resp.read().decode("utf-8")
    return clean_html(html)
  except urllib.error.HTTPError as e:
    return f"ERR:{e.code}"
  except Exception as e:
    return f"ERR:{e}"

out = {}
for t in TITLES_ES:
  txt = fetch_one("es", t)
  if not txt.startswith("ERR:404"):
    out[f"es:{t}"] = txt
  time.sleep(0.08)

for t in TITLES_EN:
  txt = fetch_one("en", t)
  if not txt.startswith("ERR:404"):
    out[f"en:{t}"] = txt
  time.sleep(0.08)

with open("tests/chunk015_wiki_rest.txt", "w", encoding="utf-8") as f:
  for k, v in out.items():
    f.write(f"================ {k} ================\n")
    if v.startswith("ERR:"):
      f.write(v + "\n")
    else:
      # Write first 3500 chars which covers infobox, intro, history, toponymy
      f.write(v[:4500] + "\n")

print(f"Done: {len(out)} articles.")
