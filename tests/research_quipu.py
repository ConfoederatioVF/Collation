import urllib.request
import urllib.parse
import json
import re

def ddg(q):
  url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
  req = urllib.request.Request(url, headers={
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  })
  html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="ignore")
  results = re.findall(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', html, re.S)
  print("=== DDG:", q, "count:", len(results))
  for href, t, s in results[:6]:
    t_clean = re.sub(r"<.*?>", "", t).strip()
    s_clean = re.sub(r"<.*?>", "", s).strip()
    m = re.search(r"uddg=([^&]+)", href)
    real_url = urllib.parse.unquote(m.group(1)) if m else href
    print(" *", t_clean, "|", real_url[:120])
    print("  ", s_clean)

queries = [
    'Tres de Diciembre Chupaca historia distrito',
    'Tres de Diciembre Junin antes anexo',
    'Lourdes Norte de Santander historia fundacion 1905',
    'Lourdes Norte de Santander antes caserio Raimundo Ordonez',
    'San Juan Bosco Morona Santiago historia fundacion salesianos',
    'Leonardo Ruiz Pineda Tucupita Delta Amacuro',
    'Parroquia Leonardo Ruiz Pineda Delta Amacuro creacion',
    'Reduccion Cordoba historia fundacion 1795 1885',
]
for q in queries:
  try:
    ddg(q)
  except Exception as e:
    print("ERR", q, e)

def fetch_text(url, label):
  try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="ignore")
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    print("=== PAGE:", label, "len:", len(txt))
    print(txt[:2500])
  except Exception as e:
    print("=== PAGE ERR:", label, e)

fetch_text("https://web.archive.org/web/20091223194510/http://www.reduccion.gov.ar/resena.html", "Reduccion resena")
fetch_text("https://web.archive.org/web/20170912152822/http://tresdediciembre.gob.pe/", "Tres de Diciembre")
