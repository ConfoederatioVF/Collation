import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

HEADERS = {"User-Agent": "OperationViscountResearch/1.0 (https://confoederatio.org; research@confoederatio.org)"}

class TextExtractor(HTMLParser):
  def __init__(self):
    super().__init__()
    self.in_p = False
    self.skip = False
    self.blocks = []
    self.cur = []

  def handle_starttag(self, tag, attrs):
    if tag in ("style", "script", "table", "sup"):
      self.skip = True
    if tag in ("p", "h2", "h3", "li") and not self.skip:
      self.cur = []
      self.in_p = True

  def handle_endtag(self, tag):
    if tag in ("style", "script", "table", "sup"):
      self.skip = False
    if tag in ("p", "h2", "h3", "li") and self.in_p:
      txt = re.sub(r"\s+", " ", "".join(self.cur)).strip()
      if txt:
        self.blocks.append((tag, txt))
      self.in_p = False

  def handle_data(self, data):
    if self.in_p and not self.skip:
      self.cur.append(data)

def fetch_url(url, retries=2):
  for attempt in range(retries + 1):
    try:
      req = urllib.request.Request(url, headers=HEADERS)
      with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
      if e.code == 429 and attempt < retries:
        time.sleep(3 * (attempt + 1))
        continue
      raise

def extract_wiki_summary(url):
  if not url:
    return ""
  try:
    html = fetch_url(url)
    infobox_matches = re.findall(r'<tr[^>]*>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>\s*</tr>', html, re.S)
    info = []
    for k, v in infobox_matches:
      kk = re.sub(r"<[^>]+>", " ", k)
      kk = re.sub(r"\s+", " ", kk).strip()
      vv = re.sub(r"<[^>]+>", " ", v)
      vv = re.sub(r"\s+", " ", vv).strip()
      if len(kk) < 40 and any(w in kk.lower() for w in ["fund", "crea", "erecc", "nombre", "otros", "capital", "establec", "origen", "entidad", "departamento", "provincia", "región", "cantón", "estado", "municipio", "parroquia"]):
        info.append(f"{kk}: {vv[:120]}")
    p = TextExtractor()
    idx = html.find('class="mw-parser-output"')
    if idx != -1:
      html = html[idx:idx+120000]
    p.feed(html)
    out_lines = []
    if info:
      out_lines.append("INFOBOX: " + " | ".join(info[:10]))
    paras = [t for tag, t in p.blocks if tag == "p" and len(t) > 35]
    for pr in paras[:2]:
      out_lines.append("P: " + pr[:450])
    capture = False
    captured = 0
    for tag, t in p.blocks:
      if tag in ("h2", "h3"):
        tl = t.lower()
        capture = any(w in tl for w in ["histor", "toponim", "etimolog", "fundaci", "origen", "creaci", "denominaci", "nombre"])
      elif capture and tag in ("p", "li") and len(t) > 25 and captured < 5:
        out_lines.append("HIST: " + t[:450])
        captured += 1
    return "\n  ".join(out_lines)
  except Exception as e:
    return f"ERR: {e}"

def search_wd_clean(name):
  clean_n = re.sub(r"\(.*?\)", "", name).strip()
  url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={urllib.parse.quote(clean_n)}&language=es&limit=5&format=json"
  try:
    data = json.loads(fetch_url(url))
    return [{"id": x["id"], "label": x.get("label", ""), "desc": x.get("description", "")} for x in data.get("search", [])]
  except Exception as e:
    return []

def nominatim_rev(lat, lng):
  url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&zoom=14"
  try:
    data = json.loads(fetch_url(url))
    return data.get("display_name", "")
  except Exception as e:
    return f"NOM_ERR: {e}"

def main():
  data = json.load(open("tests/chunk020_enriched.json", encoding="utf-8"))
  # Fix a couple bad matches (where nearby picked a river/province/earthquake instead of the settlement)
  # Let's also fetch clean wikidata search and nominatim for items without direct settlement wiki
  lines = []
  for i, d in enumerate(data):
    url = d.get("picked_wiki")
    # check if url looks like a good match or generic feature
    bad = False
    if url and any(x in url for x in ["Terremoto", "Bosques_secos", "Cant%C3%B3n_Ca%C3%B1ar", "Provincia_del_Ca%C3%B1ar", "Cant%C3%B3n_Pedro_Moncayo", "Esp%C3%ADndola_(Per%C3%BA)", "Departamento_Sil%C3%ADpica", "Distrito_de_Lares", "Distrito_de_Caraybamba", "Distrito_de_%C3%81mbar"]):
      bad = True
    lines.append(f"=== {i+1:02d}. {d['key']} | n={d['n']} | c={d['c']} | r={d['r']} | ll={d['ll']} | ey={d['ey']} | ly={d['ly']} ===")
    if url and not bad:
      time.sleep(0.35)
      summary = extract_wiki_summary(url)
      lines.append(f"  WIKI: {url}")
      lines.append("  " + summary)
    else:
      # do nominatim + wd clean search
      time.sleep(0.35)
      wd = search_wd_clean(d["n"])
      nom = nominatim_rev(d["ll"][0], d["ll"][1])
      nb_str = ", ".join(f"{x['label']}({x['dist']:.1f}km,{x['eswiki']})" for x in d.get("nearby", [])[:4])
      wd_str = "; ".join(f"{x['label']}[{x['id']}]:{x['desc']}" for x in wd[:4])
      lines.append(f"  NOM: {nom}")
      lines.append(f"  NB: {nb_str}")
      lines.append(f"  WD: {wd_str}")
      # Also if wd has a strong match or we want the specific wiki for known entities, record QID
    if (i + 1) % 15 == 0:
      print(f"Processed {i+1}/90")
  with open("tests/chunk020_details.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
  print("Done writing tests/chunk020_details.txt")

if __name__ == "__main__":
  main()
