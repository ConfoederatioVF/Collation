import json
import re
import time
import urllib.parse
import urllib.request

def fetch_wiki(lang, titles):
    u = (
        f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=revisions"
        f"&rvprop=content&rvslots=main&redirects=1&titles="
        + urllib.parse.quote("|".join(titles))
        + "&format=json"
    )
    req = urllib.request.Request(u, headers={"User-Agent": "SVEA-Research/1.0 (https://confoederatio.org)"})
    d = json.loads(urllib.request.urlopen(req, timeout=25).read().decode())
    for p in d.get("query", {}).get("pages", {}).values():
        t = p.get("title", "")
        if "revisions" not in p:
            print(f"[{lang}] MISSING: {t}")
            continue
        txt = p["revisions"][0]["slots"]["main"]["*"]
        txt = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^/]*/>", "", txt, flags=re.S)
        txt = re.sub(r"\[\[([^|\]]*\|)?([^\]]+)\]\]", r"\2", txt)
        lines = [
            l.strip()
            for l in txt.splitlines()[:110]
            if any(k in l.lower() for k in ["fundac", "creaci", "nombre", "topon", "otros", "fecha", "erecc", "pueblo", "established", "founded", "former"])
        ]
        hist = re.search(r"==\s*(?:Historia|Toponimia|Origen|History|Etymology).*?==(.*?)(?:\n==[^=]|$)", txt, re.S | re.I)
        hsnippet = re.sub(r"\s+", " ", hist.group(1))[:600] if hist else re.sub(r"\s+", " ", txt)[:400]
        print(f"=== [{lang}] {t} ===")
        if lines:
            print("  INFO:", " | ".join(lines[:7]))
        print("  HIST:", hsnippet)

titles_es = [
    "Lourdes (Norte de Santander)",
    "Letirá",
    "Becará",
    "La Mendieta",
    "Distrito de Santa Lucía (Tocache)",
    "Los Barriales",
    "Los Lirios (O'Higgins)",
    "Estación Los Lirios",
    "La Tigra (Chaco)",
    "Municipio José Felipe Márquez Cañizales",
    "Distrito de Quichuas",
    "Olta",
    "Huelquén",
    "La Paya",
    "Cochinoca",
    "Parroquia Cotogchoa",
    "San Juan Bosco (cantón)",
    "Cantón San Juan Bosco",
    "Corque",
    "Chauchamarca",
    "Yanaconas",
    "Puerchag",
    "Barranca Nueva",
    "Barranca Vieja",
    "Pueblo Nuevo (Portoviejo)",
    "Parroquia Pedro Pablo Gómez",
    "Camarones (Ecuador)",
    "San Francisco (Falcón)",
    "Santa Inés (Libertad)",
    "Avaria (Venezuela)",
    "Parroquia Leonardo Ruiz Pineda",
    "Córdoba (Sucre)",
    "El Ángel (Ecuador)",
    "Caquingora",
    "Pelaya",
    "Caloto",
    "Otanche",
    "Santander de Quilichao",
    "Chiliquín",
    "Piñero",
    "Pila (Buenos Aires)"
]

fetch_wiki("es", titles_es)
time.sleep(1.0)
fetch_wiki("en", [
    "Avaria, Venezuela",
    "San Juan Bosco Canton",
    "Cotogchoa",
    "Pedro Pablo Gómez",
    "Pueblo Nuevo, Manabí",
    "La Paya",
    "Cochinoca",
    "Caquingora",
    "Yanaconas",
    "San Carlos, Orellana",
    "Diguillín River",
    "Los Niches"
])
