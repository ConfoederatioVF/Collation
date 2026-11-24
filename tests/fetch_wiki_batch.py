import json
import time
import urllib.parse
import urllib.request

from fetch_wiki_046 import ITEMS

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SVEAToponymyBot/1.0; +https://confoederatio.org)"}

def fetch_json(url):
  req = urllib.request.Request(url, headers=HEADERS)
  with urllib.request.urlopen(req, timeout=15) as resp:
    return json.loads(resp.read().decode("utf-8"))

def batch_titles(lang, titles):
  # Fetch up to 25 titles in one API call
  tparam = "|".join(titles)
  url = (
    f"https://{lang}.wikipedia.org/w/api.php?action=query&redirects=1"
    f"&prop=extracts&exintro=true&explaintext=true&exchars=1800"
    f"&titles={urllib.parse.quote(tparam)}&format=json"
  )
  return fetch_json(url)

def main():
  # First try exact names + "Name (Country)" for populated places and notable sites
  names = []
  for it in ITEMS:
    n = it["n"]
    if n not in ("None", "Mal ubicado", "Arq", "Entre Torre 77 y", "Zona A - Sinifaná - Yacimiento 02 - Terraza", "SAR Guarinocito"):
      names.append(n)
      if it["c"] in ("Ecuador", "Colombia", "Peru", "Bolivia", "Chile", "Argentina", "Uruguay", "Venezuela"):
        names.append(f"{n} ({it['c']})")
  names = list(dict.fromkeys(names))
  results = {}
  for i in range(0, len(names), 25):
    chunk = names[i:i+25]
    try:
      data = batch_titles("es", chunk)
      pages = data.get("query", {}).get("pages", {})
      for pid, p in pages.items():
        if int(pid) > 0 and p.get("extract"):
          results[p["title"]] = p["extract"]
      print(f"Batch {i//25+1}: got {len(pages)} pages")
    except Exception as e:
      print(f"Batch {i//25+1} err: {e}")
    time.sleep(1.0)
  with open("tests/wiki_batch_es.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
  print("Total saved:", len(results))

if __name__ == "__main__":
  main()
