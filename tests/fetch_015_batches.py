import json
import re
import time
import urllib.parse
import urllib.request

# 1. Exact eswiki and enwiki titles from chunk015_wd_summary.txt + targeted direct titles
es_titles = [
  "Distrito_de_Luya_Viejo",
  "Luya_Viejo",
  "Distrito_de_Huaquirca",
  "Huaquirca",
  "Distrito_de_Chisquilla",
  "Distrito_de_Umachiri",
  "El_%C3%81ngel_(Ecuador)",
  "Cant%C3%B3n_Espejo",
  "Distrito_de_Mariscal_Gamarra",
  "Distrito_de_Quinjalca",
  "Distrito_de_Cochabamba_(Huaraz)",
  "L%C3%A1mud",
  "Distrito_de_L%C3%A1mud",
  "Luya",
  "Archidona_(Ecuador)",
  "Distrito_de_Quinocay",
  "Distrito_de_Chachas",
  "Cubij%C3%ADes",
  "Distrito_de_Huacll%C3%A1n",
  "Ventarr%C3%B3n",
  "Distrito_de_Turpo",
  "Huayllati",
  "Distrito_de_Huayllati",
  "Distrito_de_Cupisnique",
  "Distrito_de_San_Salvador_de_Quije",
  "Cojitambo",
  "Distrito_de_Succha",
  "Yumbo",
  "Molleturo",
  "Distrito_de_Caja",
  "Distrito_de_Coya",
  "Coya_(Cusco)",
  "Distrito_de_Huampar%C3%A1",
  "Moruy",
  "P%C3%A1ez_(Cauca)",
  "Distrito_de_Ichu%C3%B1a",
  "Ichu%C3%B1a",
  "Rere",
  "Zona_Bananera",
  "Timar",
  "Candelaria_(Valle_del_Cauca)",
  "Caype",
  "Distrito_de_Circa",
  "Coper",
  "Mutca",
  "N%C3%A1nchoc",
  "Distrito_de_N%C3%A1nchoc",
  "%C3%91anchoc_(sitio_arqueol%C3%B3gico)",
  "San_Francisco_del_Vergel",
  "Sisicaya",
  "Distrito_de_Antioqu%C3%ADa",
  "Chinchao",
  "Distrito_de_Chinchao",
  "El_Morro_(Guayas)",
  "Dureno",
  "Jad%C3%A1n",
  "Chiguaza",
  "El_Eno",
  "San_Crist%C3%B3bal_(Paute)",
  "Guacamayal",
  "El_Carmelo_(Candelaria)",
  "Tuama",
  "Villanueva_de_Tuama",
  "Ayal%C3%A1n",
  "Pepa_de_Huso",
  "Inguap%C3%AD",
  "Bat%C3%A1n_Grande",
  "Santuario_hist%C3%B3rico_Bosque_de_P%C3%B3mac",
  "Wamanmarka",
  "Distrito_de_V%C3%ADtor",
  "Cambio_Puente",
  "Chimbote",
  "Sopetr%C3%A1n",
  "C%C3%B3rdoba_(Sopetr%C3%A1n)",
  "Caparrap%C3%AD",
  "Tenjo",
  "Buenaventura_(Valle_del_Cauca)",
  "Distrito_de_Paccho",
  "Distrito_de_Checras",
  "Distrito_de_Santa_Leonor",
  "Vitoc",
  "Distrito_de_V%C3%ADtoc",
  "Huari",
  "Distrito_de_Colca_(Ayacucho)",
  "Distrito_de_Sarhua",
  "Distrito_de_Putinza",
  "Distrito_de_Accha",
  "Distrito_de_Huaso",
  "Distrito_de_Ccatca",
  "Distrito_de_Lambrama",
  "Malambo_(Atl%C3%A1ntico)",
  "Municipio_San_Francisco_(Zulia)",
  "Municipio_Federaci%C3%B3n",
  "Municipio_Rafael_Rangel",
  "Betijoque",
  "Isnot%C3%BA",
  "Challapata",
  "Santuario_de_Quillacas",
  "Distrito_de_San_Antonio_(Huarochir%C3%AD)",
  "Caral",
  "Bandurria_(sitio_arqueol%C3%B3gico)",
  "V%C3%A9gueta",
  "Huaura",
  "Huacho",
  "Cultura_Tumaco-La_Tolita",
  "Novirao",
  "Totor%C3%B3_(Cauca)",
  "Distrito_de_Sartimbamba",
  "Distrito_de_Marcabal",
  "Distrito_de_Huamachuco",
  "Distrito_de_Laredo",
  "Complejo_arqueol%C3%B3gico_Caballo_Muerto",
  "Huaca_de_los_Reyes"
]

en_titles = [
  "Luya_Viejo_District",
  "Huaquirca_District",
  "Chisquilla_District",
  "Umachiri_District",
  "El_%C3%81ngel,_Ecuador",
  "Mariscal_Gamarra_District",
  "Quinjalca_District",
  "Cochabamba_District,_Huaraz",
  "Lamud",
  "L%C3%A1mud_District",
  "Archidona,_Ecuador",
  "Quinocay_District",
  "Chachas_District",
  "Huacllan_District",
  "Ventarron",
  "Turpo_District",
  "Huayllati_District",
  "Cupisnique_District",
  "San_Salvador_de_Quije_District",
  "Cojitambo",
  "Succha_District",
  "Yumbo",
  "Molleturo",
  "Caja_District",
  "Coya_District",
  "Huampara_District",
  "P%C3%A1ez,_Cauca",
  "Belalc%C3%A1zar,_Cauca",
  "Ichu%C3%B1a_District",
  "Rere,_Chile",
  "Timar",
  "Circa_District",
  "Coper,_Boyac%C3%A1",
  "Nanchoc_District",
  "Ayalan"
]

def fetch_batch(lang, titles):
  results = {}
  for i in range(0, len(titles), 25):
    batch = [urllib.parse.unquote(t) for t in titles[i:i+25]]
    params = urllib.parse.urlencode({
      "action": "query",
      "prop": "extracts|revisions",
      "exintro": "0",
      "explaintext": "1",
      "exsectionformat": "plain",
      "rvprop": "content",
      "rvslots": "main",
      "titles": "|".join(batch),
      "redirects": "1",
      "format": "json"
    })
    # Actually extracts alone with explaintext=1 for 25 pages is very fast and clean
    params_ext = urllib.parse.urlencode({
      "action": "query",
      "prop": "extracts",
      "explaintext": "1",
      "titles": "|".join(batch),
      "redirects": "1",
      "format": "json"
    })
    url = f"https://{lang}.wikipedia.org/w/api.php?{params_ext}"
    req = urllib.request.Request(url, headers={"User-Agent": "QuipuHistoricalToponymy/1.0 (academic research)"})
    try:
      with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
      pages = data.get("query", {}).get("pages", {})
      for pid, p in pages.items():
        if int(pid) > 0 and "extract" in p:
          results[p["title"]] = p["extract"]
    except Exception as e:
      print(f"Error batch {lang} {i}: {e}")
    time.sleep(0.5)
  return results

es_res = fetch_batch("es", es_titles)
en_res = fetch_batch("en", en_titles)

with open("tests/chunk015_wiki_extracts.json", "w", encoding="utf-8") as f:
  json.dump({"es": es_res, "en": en_res}, f, ensure_ascii=False, indent=2)

print(f"Fetched {len(es_res)} eswiki and {len(en_res)} enwiki pages.")
