import json
import os

keys = [
  "San Pedro Capacho-Venezuela", "Cazorla-Venezuela", "Pocanchi-Bolivia", "Pichota-Ecuador",
  "Loreto (arg_corrientes)-Argentina", "Valle Sacta-Bolivia", "Campo Grande (arg_formosa)-Argentina",
  "Pucacaca-Peru", "Campo Grande-Bolivia", "Rosario Casigua-Venezuela",
  "Estructuras (inca_collasuyu)-Chile", "Torrejirca y Huancuyo-Peru", "Uvencio Antonio Velásquez-Venezuela",
  "Piedras Tacitas Fundo El Rebaño-Chile", "Yungar-Peru", "Piamonte-Colombia_2",
  "Tres Cruces Garnica-Bolivia", "Los Sunchales-Argentina", "Pampa Munipata-Peru",
  "Estero Meco-Chile", "Callelarga-Colombia", "Apillapampa-Bolivia", "Candua-Bolivia",
  "Loma China-Colombia", "Mateo Gómez-Colombia", "Calpamayo-Peru", "Jiskha-Bolivia",
  "Naranjales-Colombia_2", "Fortín Olmos-Argentina", "Fuerte de Lobos-Argentina",
  "Tirata-Bolivia_2", "Villa de Maria-Colombia", "Sucumbíos-Ecuador", "El Lucero-Ecuador",
  "Tapasa-Bolivia", "Majagual Yacimiento-Colombia", "Chiwaco Wayqo-Peru", "Los Potreros Y-Argentina",
  "Agua Larga-Venezuela", "Apiay-Colombia", "Cuenca-Peru", "Milagro-Argentina",
  "San Marcos Sierra-Argentina", "Zarapullo-Ecuador", "Yacimiento (na_magdalena_cauca_muisca_6)-Colombia",
  "HA1 Retamos Norte ZG-B-Chile", "Palca-Peru_2", "Guachipas-Argentina",
  "UIA 98 - Yacimiento-Colombia", "Estero Lumaco-Chile", "Villa Valeria-Argentina",
  "Kancha Kancha-Peru", "Pedregal Grande-Peru", "Pajcha-Bolivia", "Laguna La Angelita-Argentina",
  "San Marcos Sud-Argentina", "Las Velas-Venezuela", "Sajara-patac-Peru",
  "Rinconada Llicuar-Peru", "Cañada de Machado-Argentina", "Cerro Trinidad-Peru",
  "Lbp-Colombia", "Choromoro-Argentina", "La Aguada Ambato-Argentina", "Cerro Narrío-Ecuador",
  "Chancayllo-Peru_2", "Liticos-Colombia", "Campo Dos-Colombia", "San Gerardo-Ecuador",
  "Churumatas-Bolivia", "Garagay-Peru", "Catuaro-Venezuela", "Carolina-Ecuador",
  "El Castigo-Colombia", "Shincaspunta-Peru", "Pueblo Buho-Colombia", "Qollmay-Peru",
  "Naranjal-Peru_2", "El Calvario-Colombia", "El Salado (col_valle_del_cauca)-Colombia",
  "Santiago De Méndez-Ecuador", "Cuenda-Colombia", "Ponto-Peru", "Tomayrica-Peru",
  "San Antonio Pereira-Colombia", "Velásquez-San Juan-La Troja-Venezuela",
  "Puerto El Carmen De Putumayo-Ecuador", "Cl_1 y 2 Corte-Colombia",
  "Llano Grande (vng_antioquia_popayan_choco)-Colombia", "Cailloma-Chile"
]

root = "histmap/1.data_raw/population_regional/QUIPU"
found = {}
for dp, dn, fn in os.walk(root):
  for f in fn:
    if f.endswith("_settlements.json"):
      d = json.load(open(os.path.join(dp, f), encoding="utf-8"))
      for k in keys:
        if k in d:
          rec = dict(d[k])
          pop = rec.pop("population", {})
          rec["pop_years"] = sorted(pop.keys(), key=lambda x: int(x)) if isinstance(pop, dict) else []
          rec["_file"] = f
          found.setdefault(k, []).append(rec)

print(f"Matched {len(found)}/{len(keys)}")
for k in keys:
  recs = found.get(k, [])
  print(f"KEY: {k}")
  for r in recs:
    out = {x: r.get(x) for x in ["name", "other_names", "coords", "admin1", "admin2", "source", "foundation_year", "pop_years", "_file"] if r.get(x) is not None}
    print(" ", json.dumps(out, ensure_ascii=False))
