import json, time, urllib.request, urllib.parse

UA = "OperationViscountHistoricalResearch/1.0 (https://confoederatio.org; contact@confoederatio.org)"

queries = [
    ("Misaray-Venezuela", "Misaray Venezuela Falcon"),
    ("Los Reartes-Argentina", "Los Reartes Cordoba historia"),
    ("Choro-Venezuela", "Choro Portuguesa Venezuela"),
    ("San Isidro (ecu_carchi)-Ecuador", "San Isidro Espejo Carchi Ecuador"),
    ("Feliu-Argentina", "Feliu Santa Fe Sunchales"),
    ("Batan Grande-Peru", "Batan Grande Lambayeque"),
    ("Tilali-Peru", "Distrito de Tilali"),
    ("El Trapiche-Argentina", "El Trapiche San Luis"),
    ("Santa Cruz de Flores-Peru", "Distrito de Santa Cruz de Flores"),
    ("Centeno-Argentina", "Centeno Santa Fe"),
    ("Sevilla Don Bosco (ecu_morona_santiago)-Ecuador", "Sevilla Don Bosco"),
    ("Monbuco-Colombia", "Monbuco Narino"),
    ("San Eduardo-Colombia", "San Eduardo Boyaca"),
    ("Rodriguez-Uruguay", "Rodriguez San Jose Uruguay"),
    ("Seclantás-Argentina", "Seclantas Salta"),
    ("Taurija-Peru", "Distrito de Taurija"),
    ("Charat-Peru", "Distrito de Charat"),
    ("Cusca-Peru", "Distrito de Cusca"),
    ("Caraguatay-Argentina", "Caraguatay Misiones"),
    ("Gloria Pata-Peru", "Gloria Pata Ayacucho"),
    ("Agua de Castilla-Bolivia", "Agua de Castilla Potosi"),
    ("San Miguel-Argentina_2", "San Miguel del Carcarana"),
    ("Cupira-Venezuela", "Cupira Miranda"),
    ("Rumipamba-Ecuador", "Rumipamba Quero Tungurahua"),
    ("Humaya-Peru", "Humaya Huaura"),
    ("Laza-Bolivia", "Laza Sud Yungas Bolivia"),
    ("Chillar-Argentina", "Chillar Buenos Aires"),
    ("Pavón-Argentina", "Pavon Santa Fe"),
    ("Tululbí-Ecuador", "Tululbi Esmeraldas"),
    ("Rocha-Colombia", "Rocha Arjona Bolivar"),
    ("Huallaga-Peru", "Distrito de Huallaga"),
    ("Villa Rosa-Colombia", "Villa Rosa Repelon Atlantico"),
    ("Chorocopte-Ecuador", "Chorocopte Canar"),
    ("Curadidal-Venezuela", "Curadidal Curaridal Zulia"),
    ("Churoc-Peru", "Churoc Apurimac Cusco"),
    ("Chuica-Bolivia", "Chuica Cheucha Potosi"),
    ("Collicate-Peru", "Collicate Amazonas Peru"),
    ("Nanegalito-Ecuador", "Nanegalito"),
    ("Ñacoreque Grande-Peru", "Nacoreque Puno"),
    ("Villa Pacheco-Bolivia", "Villa Pacheco Livilivi"),
    ("Huata-Bolivia", "Huata Chuquisaca Bolivia"),
    ("Los Nevados-Venezuela", "Los Nevados Merida Venezuela"),
    ("Punta de Araya-Venezuela", "Punta de Araya Sucre"),
    ("La Herradura (vng_santafe_tunja_highlands)-Colombia", "La Herradura Cundinamarca"),
    ("Villa Kintiarina-Peru", "Distrito de Villa Kintiarina"),
    ("Asunción-Ecuador", "La Asuncion Chimbo Bolivar Ecuador"),
    ("Varela-Colombia", "Varela Zona Bananera Magdalena"),
    ("Suquistaca-Bolivia", "Suquistaca Chuquisaca"),
    ("La Esmeralda-Venezuela", "La Esmeralda Sucre Venezuela"),
    ("Sansahuari-Ecuador", "Sansahuari Sucumbios"),
    ("Cashapampa-Peru", "Distrito de Cashapampa"),
    ("Malalhue-Chile", "Malalhue"),
    ("Acopampa-Peru", "Distrito de Acopampa"),
    ("Tumbia-Colombia", "Tumbia Cundinamarca"),
    ("Tuqui-Chile", "Tuqui Ovalle"),
    ("Olof Palme-Peru", "Olof Palme Chilca Lima"),
    ("Sijcha-Bolivia", "Sijcha Potosi Chuquisaca"),
    ("Canoas-Colombia", "Canoas Tuso Soacha"),
    ("El Talar-Argentina", "El Talar Jujuy"),
    ("San Pablo-Argentina", "San Pablo Santiago del Estero"),
    ("Pajarito-Colombia", "Pajarito Boyaca"),
]

results = {}
for key, q in queries:
    try:
        url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=2&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
        hits = data.get("query", {}).get("search", [])
        if hits:
            title = hits[0]["title"]
            time.sleep(0.15)
            url2 = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exchars=1500&titles={urllib.parse.quote(title)}&format=json"
            req2 = urllib.request.Request(url2, headers={"User-Agent": UA})
            d2 = json.loads(urllib.request.urlopen(req2, timeout=10).read().decode("utf-8"))
            pages = d2.get("query", {}).get("pages", {})
            ext = next(iter(pages.values())).get("extract", "").replace("\n", " ")
            results[key] = {"title": title, "extract": ext[:1200]}
        else:
            results[key] = {"title": None, "extract": ""}
    except Exception as e:
        results[key] = {"error": str(e)}
    time.sleep(0.2)

with open("tests/wiki_054_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Done:", len(results), "errors:", sum(1 for v in results.values() if "error" in v))
