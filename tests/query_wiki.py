import urllib.request, urllib.parse, json

titles_batch1 = [
  "Presidencia Roca", "Jovita (Córdoba)", "El Sacrificio (Tucumán)", "San Roque (Maipú)",
  "Puesto Viejo (Jujuy)", "Azara (Misiones)", "Lucas González (Entre Ríos)",
  "Santa Catalina (Holmberg)", "Misión Tacaaglé", "Acheral", "La Reducción (Tucumán)",
  "Colonia Dora", "Huanguelén", "Ingeniero Luiggi", "María Juana", "Ulapes",
  "Huatajata", "Potobamba", "Chuquichambi", "Las Carreras (Bolivia)", "Eterazama",
  "Entre Lagos (Chile)", "Laraquete", "Maullín", "El Playón (Portuguesa)", "Curbatí",
  "Acacías", "Servitá", "Durania", "Tipacoque", "Quinamayó", "Charapotó",
  "Jenaro Herrera", "Congas", "Distrito de Lalaquiz", "Distrito de Phara",
  "Distrito de Quivilla", "Distrito de Samanco", "Distrito de El Algarrobal",
  "Distrito de Cáceres del Perú", "Distrito de Juan Guerra",
  "Distrito de Río Grande (Condesuyos)", "Huarautambo", "Distrito de Leoncio Prado (Lucanas)",
  "Distrito de Chinchipe", "Guale (Ecuador)", "Cochapata (Nabón)", "La Villegas"
]

url = "https://es.wikipedia.org/w/api.php?action=query&prop=extracts|coordinates|revisions&rvprop=content&rvslots=main&rvsection=0&exintro=1&explaintext=1&redirects=1&titles=" + urllib.parse.quote("|".join(titles_batch1)) + "&format=json"
req = urllib.request.Request(url, headers={"User-Agent": "ViscountToponymyBot/1.0"})
d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
for pid, p in d.get("query", {}).get("pages", {}).items():
  if int(pid) > 0:
    title = p.get("title")
    coords = p.get("coordinates")
    ext = (p.get("extract") or "").replace("\n", " ")[:450]
    revs = p.get("revisions", [])
    ib = ""
    if revs:
      txt = revs[0].get("slots", {}).get("main", {}).get("*", "")
      for line in txt.splitlines():
        if any(k in line.lower() for k in ["fundaci", "creaci", "erecci", "nombre", "otros_nombres", "fecha"]):
          ib += line.strip()[:100] + " | "
    print(f"=== {title} | {coords} ===")
    if ib:
      print("  IB:", ib[:300])
    print("  EX:", ext)
  else:
    print("MISSING:", p.get("title"))
