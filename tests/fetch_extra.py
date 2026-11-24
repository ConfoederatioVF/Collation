import json
import urllib.request
import urllib.parse
import concurrent.futures
import time

data = json.load(open("tests/quipu_detailed.json", encoding="utf-8"))

# Also query es.wikipedia for alternate names / region-specific terms for tricky ones
EXTRA_QUERIES = {
    "Puán-Argentina": ["San Germán (Buenos Aires)", "Partido de Puan"],
    "Pueblo Nuevo (col_arauca)-Colombia": ["Puerto Jordán", "Tame"],
    "San Bartolome de Buena vista-Colombia": ["Maceo (Antioquia)", "Puerto Berrío", "Yolombó", "Caracolí"],
    "Sapse-Bolivia": ["Sapsi", "Poroma"],
    "Sipisa-Chile": ["Sipiza", "Camiña"],
    "Chalgayaco-Colombia": ["Mercaderes (Cauca)", "Balboa (Cauca)", "Patía"],
    "Mopora-Colombia": ["Saboyá", "Chiquinquirá"],
    "San Juan de Oro-Argentina": ["Santa Catalina (Jujuy)", "San Juan y Oros", "Río San Juan de Oro"],
    "Inambari-Peru_2": ["Distrito de Inambari", "Camanti", "Marcapata", "Carabaya"],
    "Chanabaya-Chile": ["Chanavaya", "Chanavayita", "Pabellón de Pica"],
    "Guantajaya-Chile": ["Huantajaya", "San Agustín de Huantajaya"],
    "La Lagunita (ven_yaracuy)-Venezuela": ["Nirgua", "Salom (Yaracuy)"],
    "Campo Elías (ven_trujillo)-Venezuela": ["Campo Elías (Trujillo)", "Municipio Juan Vicente Campo Elías"],
    "Agua Santa-Venezuela": ["Agua Santa (Trujillo)", "Municipio Miranda (Trujillo)"],
    "Sabana de La Plata-Venezuela": ["Municipio Simón Bolívar (Zulia)", "Tía Juana"],
    "Taganga-Colombia": ["Taganga", "Santa Marta"],
    "Cavari-Bolivia": ["Cavari", "Inquisivi"],
    "Quilanga-Ecuador": ["Cantón Quilanga", "Quilanga"],
    "Abdón Calderón (ecu_azuay)-Ecuador": ["Abdón Calderón (Santa Isabel)", "Cantón Santa Isabel"],
    "Chura-Ecuador": ["Chura (Quinindé)", "Cantón Quinindé"],
    "San Simón-Ecuador": ["San Simón (Guaranda)", "Cantón Guaranda"],
    "Bachillero-Ecuador": ["Bachillero", "Cantón Tosagua"],
    "Chontaduro-Ecuador": ["Chontaduro (Rioverde)", "Cantón Rioverde"],
    "Simón Bolívar (ecu_santa_elena)-Ecuador": ["Simón Bolívar (Santa Elena)", "Julio Moreno (Santa Elena)"],
    "El Chical-Ecuador": ["El Chical", "Chical"],
    "El Retiro-Ecuador": ["El Retiro (Machala)", "Cantón Machala"],
    "Santa Clara-Ecuador": ["Santa Clara (Pastaza)", "Cantón Santa Clara"],
    "Viviate-Peru": ["Viviate", "Distrito de La Huaca"],
    "Santiago de Vado-Peru": ["Santiago de Vado", "Distrito de San Pedro (Lucanas)"],
    "Francisco Bolognesi (per_piura)-Peru": ["Distrito de Pacaipampa", "Cumbicos"],
    "Abelardo Pardo Lezameta-Peru": ["Distrito de Abelardo Pardo Lezameta", "Llaclla"],
    "Huasco Bajo-Chile": ["Huasco Bajo", "Huasco"],
    "Copequén-Chile": ["Copequén", "Coinco"],
    "La Milagrosa-Colombia": ["Inzá", "San Pedro de Guanacas", "Guanacas"],
    "Buenavista (col_norte_de_santander)-Colombia": ["Buenavista (Ocaña)", "Ocaña (Colombia)"],
    "Las Piedras-Colombia": ["San Estanislao (Bolívar)", "Las Piedras (Bolívar)"],
    "Loma de Arena-Colombia": ["Loma de Arena", "Santa Catalina (Bolívar)"],
    "Santa Clara-Peru": ["Santa Clara (Maynas)", "Distrito de San Juan Bautista (Maynas)"],
    "Pobreza Baudo-Colombia": ["Medio Baudó", "Bajo Baudó", "Puerto Meluk"],
    "Villa Pasco-Peru": ["Villa de Pasco", "Distrito de Tinyahuarco", "Pasco"],
    "Sama Grande-Peru": ["Sama (Tacna)", "Distrito de Sama"],
    "Chairama-Colombia": ["Pueblito Chairama", "Chairama", "Parque nacional natural Tayrona"],
    "La Cueva de Ya-Argentina": ["Yavi", "Cueva de Yavi"],
    "Paclín-Argentina": ["Departamento Paclín", "La Merced (Catamarca)"],
    "Pomán-Argentina": ["Pomán", "Villa de Pomán"],
    "Los Antiguos-Argentina": ["Los Antiguos"],
}

HEADERS = {'User-Agent': 'HistoricalToponymyResearch/1.0 (https://example.org)'}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        return json.loads(resp.read().decode('utf-8'))

def fetch_extra(item):
    key, titles = item
    t_param = urllib.parse.quote('|'.join(titles[:5]))
    url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates&explaintext=1&exchars=4000&titles={t_param}&format=json"
    res = []
    try:
        pages = fetch_json(url).get('query', {}).get('pages', {})
        for pid, p in pages.items():
            if 'missing' not in p:
                res.append({
                    'title': p.get('title'),
                    'coords': p.get('coordinates', []),
                    'extract': p.get('extract', '')
                })
    except Exception as e:
        res.append({'err': str(e)})
    return key, res

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    extra_res = dict(ex.map(fetch_extra, EXTRA_QUERIES.items()))

with open('tests/quipu_extra.json', 'w', encoding='utf-8') as f:
    json.dump(extra_res, f, ensure_ascii=False, indent=2)

# Print readable digest of all 90 items
lines = []
for i, d in enumerate(data):
    lines.append(f"=== {i+1:02d}. {d['key']} | n={d['n']} | c={d['c']} | r={d['r']} | ll={d['ll']} | ey={d['ey']}..{d['ly']} ===")
    for a in d['articles']:
        if a['dist_km'] is None or a['dist_km'] <= 15.0 or a['title'].lower().startswith(d['n'].lower()[:5]):
            ext = a['extract'].replace('\n', ' ')[:1200]
            lines.append(f"  [{a['lang']}] {a['title']} (dist={a['dist_km']}km): {ext}")
    if d['key'] in extra_res:
        for e in extra_res[d['key']]:
            if 'title' in e:
                ext = e['extract'].replace('\n', ' ')[:1200]
                lines.append(f"  [EXTRA] {e['title']} (coords={e.get('coords')}): {ext}")

with open('tests/quipu_digest.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("Wrote tests/quipu_digest.txt, lines:", len(lines))
