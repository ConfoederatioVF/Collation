import os, re, json

TARGETS = [
  "Las Lajas", "Tarapoa", "Choquecancha", "Moretecocha", "Alto Jahuel", "Tumbabarreto",
  "Maucallacta", "Tocmoche", "Andajes", "Quípama", "Otoca", "Tangui", "Aquia",
  "San Juan de Viscas", "Chibunga", "Condormarca", "Viraco", "Socoroma", "La Capilla",
  "Anaica", "Cantagallo", "Auquimarca", "Juan Pablo Peñaloza", "Sabaino", "Malchinguí",
  "Pallac", "Puncurin", "Calpi", "Guayrapongo", "Menahermosa", "Pararin", "Zaacata",
  "Arahuay", "Mucuruba", "Nava", "Pampallacta", "Uchumarca", "Casiri", "Huataca",
  "Atiquipa", "Pariamarca", "Laraos", "Yamor", "Quintero", "Huanangui",
  "Santiago Apostol", "Anton Moreno", "Nanis", "Mercedes Díaz", "Huambacho",
  "Jorobamba", "Nonogasta", "Hunchos", "Apuri", "Tumbabiro", "San Buenaventura",
  "Coronado", "Choquekancha", "Mian", "Mangan", "Payandé", "Mamara", "Huayrahuacho",
  "Cotaruse", "Surco", "Pichanas", "Chingos", "Mangas", "Atabillos Altos",
  "San Pedro de Pilas", "Sangayaico", "Calacoto", "Arma", "Acotama"
]

root = r"histmap\1.data_raw\population_regional\QUIPU"
hits = {t: [] for t in TARGETS}
pat = re.compile("|".join(re.escape(t) for t in TARGETS), re.IGNORECASE)

for dirpath, dirnames, filenames in os.walk(root):
  dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "_gis_cache", "rasters", "figures")]
  for fn in filenames:
    if not fn.endswith((".json", ".json5", ".csv", ".tsv", ".txt", ".md", ".Rmd", ".py", ".js")):
      continue
    fp = os.path.join(dirpath, fn)
    try:
      if os.path.getsize(fp) > 25_000_000:
        continue
      with open(fp, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
          m = pat.search(line)
          if m:
            matched = m.group(0)
            for t in TARGETS:
              if t.lower() == matched.lower() and len(hits[t]) < 5:
                hits[t].append(f"{os.path.relpath(fp, root)}:{i}: {line.strip()[:220]}")
    except Exception:
      pass

with open("tests/quipu_local_hits.json", "w", encoding="utf-8") as out:
  json.dump(hits, out, ensure_ascii=False, indent=2)
print("Matched targets:", sum(1 for v in hits.values() if v), "/", len(TARGETS))
