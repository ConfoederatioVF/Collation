import urllib.request, urllib.parse, re, time, html

queries = [
  ('46_Camarones', '"Camarones" "Riohacha" fundación historia'),
  ('48_Paguey', '"Pagüey" OR "Paguey" "Limones" Cundinamarca'),
  ('49_Yanamarca', '"Yanamarca" "Huancucro" OR "Yanamarka" Tarma Acobamba'),
  ('50_SanAndres', '"San Andrés de Pisimbalá" historia fundación'),
  ('51_Limari', '"Limarí" "Barraza" "pueblo de indios" OR fundación'),
  ('52_Tambillo', '"Tambillo" "San Lorenzo" "Esmeraldas" parroquia fundación'),
  ('54_SUAII', '"SUA II" "Cortes I" OR "Finca El Manso" Suárez arqueología'),
  ('55_Cotabambas', '"Cotabambas" 1573 Toledo reducción fundación'),
  ('57_Zenufana', '"Zenúfana" OR "Cenufaná" "Nechí" historia'),
  ('58_Cayambe', '"Concepción de Cayambe" OR "Concepcion de Cayambe" historia'),
  ('59_Turco', '"Turco" Oruro historia marka reducción Carangas'),
]

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

out = []
for key, q in queries:
    out.append(f'=== {key}: {q} ===')
    try:
        url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(q)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=12) as r:
            body = r.read().decode('utf-8', errors='ignore')
        snippets = re.findall(r'class="result__a"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', body, re.S)
        for title, snip in snippets[:6]:
            t = html.unescape(re.sub(r'<[^>]+>', '', title)).strip()
            s = html.unescape(re.sub(r'<[^>]+>', '', snip)).strip()
            out.append(f'- {t}: {s}')
        if not snippets:
            out.append('No snippets matched (len=' + str(len(body)) + ')')
    except Exception as e:
        out.append(f'ERR: {e}')
    time.sleep(0.6)

with open('tests/ddg_dump.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('Done ddg_dump.txt')
