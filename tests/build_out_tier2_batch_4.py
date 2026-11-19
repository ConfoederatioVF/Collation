import json

# Load input batch
input_path = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\tier2_batch_4.json'
with open(input_path, 'r', encoding='utf-8') as f:
    input_clusters = json.load(f)

print(f"Total clusters in input: {len(input_clusters)}")

# Dictionary of cluster decisions
# cluster_id -> (actions_list, clean_names_dict)
DECISIONS = {}

def add_junk_cluster(cid, junk_key, junk_reason, modern_key, modern_clean_name):
    DECISIONS[cid] = {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": junk_key,
                "reason": junk_reason
            }
        ],
        "clean_names": {
            modern_key: modern_clean_name
        }
    }

def add_arch_mod_cluster(cid, arch_key, arch_clean_name, arch_reason, mod_key, mod_clean_name, mod_rename_reason=None):
    actions = [
        {
            "op": "RENAME_META",
            "key": arch_key,
            "new_name": arch_clean_name,
            "reason": arch_reason
        }
    ]
    if mod_rename_reason:
        actions.append({
            "op": "RENAME_META",
            "key": mod_key,
            "new_name": mod_clean_name,
            "reason": mod_rename_reason
        })
    DECISIONS[cid] = {
        "actions": actions,
        "clean_names": {
            arch_key: arch_clean_name,
            mod_key: mod_clean_name
        }
    }

def add_arch_arch_cluster(cid, k0, name0, reason0, k1, name1, reason1):
    DECISIONS[cid] = {
        "actions": [
            {
                "op": "RENAME_META",
                "key": k0,
                "new_name": name0,
                "reason": reason0
            },
            {
                "op": "RENAME_META",
                "key": k1,
                "new_name": name1,
                "reason": reason1
            }
        ],
        "clean_names": {
            k0: name0,
            k1: name1
        }
    }

# 1. 6 JUNK CLUSTERS
add_junk_cluster(
    "C0937",
    "Sudislavskiy kreml-Russia",
    "Fabricated medieval date (600..1240) on 1536 wooden kremlin",
    "Sudislavl'-Russia",
    "Sudislavl"
)
# Add rename for Sudislavl to ensure clean name without apostrophe
DECISIONS["C0937"]["actions"].append({
    "op": "RENAME_META",
    "key": "Sudislavl'-Russia",
    "new_name": "Sudislavl",
    "reason": "Clean display name for historic town"
})

add_junk_cluster(
    "C0955",
    "Ternopil Castle-Ukraine",
    "Fabricated prehistoric date (-3000..-2500) on 1540 castle",
    "Ternopil'-Ukraine",
    "Ternopil"
)
DECISIONS["C0955"]["actions"].append({
    "op": "RENAME_META",
    "key": "Ternopil'-Ukraine",
    "new_name": "Ternopil",
    "reason": "Clean modern display name for regional centre"
})

add_junk_cluster(
    "C0960",
    "Tiraspol Fortress-Moldova",
    "Fabricated medieval date (800..1300) on 1792 modern fortress",
    "Tiraspol-Moldova",
    "Tiraspol"
)

add_junk_cluster(
    "C1001",
    "Valuyskaya krepost-Russia",
    "Fabricated medieval date (800..1300) on 1593 modern frontier fortress",
    "Valuyki-Russia",
    "Valuyki"
)

add_junk_cluster(
    "C1060",
    "Zaliztsi Castle-Ukraine",
    "Fabricated prehistoric date (-3000..-2500) on 1516 castle",
    "Zaliztsi-Ukraine",
    "Zaliztsi"
)

add_junk_cluster(
    "C1084",
    "Zolotyy Potik Castle-Ukraine",
    "Fabricated prehistoric date (-3000..-2500) on 1608 castle",
    "Zolotyi Potik-Ukraine",
    "Zolotyi Potik"
)

# 2. CHUNK 1 (0 to 24)
add_arch_mod_cluster(
    "C0873",
    "Shagonar I-Russia", "Shagonar I", "8th-century Uyghur fortified settlement distinct from modern town",
    "Shagonar-Russia", "Shagonar"
)
add_arch_mod_cluster(
    "C0874",
    "Shakhtarsk Neolithic Settlement-Ukraine", "Shakhtarsk (Neolithic)", "Prehistoric Neolithic settlement distinct from modern city",
    "`Sachtars'k-Ukraine", "Shakhtarsk", "Clean modern display name for primary city"
)
add_arch_mod_cluster(
    "C0875",
    "Shalazhi Bronze Age Site-Russia", "Shalazhi (Bronze Age)", "Bronze Age settlement distinct from modern town",
    "Shalazhi-Russia", "Shalazhi"
)
add_arch_arch_cluster(
    "C0878",
    "Sharpivka Iron Age Site-Ukraine", "Sharpivka (Iron Age)", "Scythian Iron Age settlement",
    "Sharpivka-Ukraine", "Sharpivka (Chernyakhov)", "Chernyakhov migration-period settlement"
)
add_arch_arch_cluster(
    "C0879",
    "Dolina 1 Eneolithic Hillfort-Ukraine", "Dolina 1", "Trypillia Eneolithic hillfort",
    "Shcherbanivka-Ukraine", "Shcherbanivka", "Medieval settlement distinct from prehistoric hillfort"
)
add_arch_mod_cluster(
    "C0881",
    "Shepsi Bronze Age Site-Russia", "Shepsi (Bronze Age)", "Bronze Age dolmen and settlement site distinct from modern town",
    "Shepsi-Russia", "Shepsi"
)
add_arch_mod_cluster(
    "C0883",
    "Shilovo-Russia_2", "Shilovo (Early Medieval)", "Ryazan-Oka culture settlement distinct from modern town",
    "Shilovo-Russia", "Shilovo"
)
add_arch_mod_cluster(
    "C0884",
    "Shinaz Medieval Gorodishche-Russia", "Shinaz (Medieval)", "Medieval Dagestani fortified site distinct from modern village",
    "Shinaz-Russia", "Shinaz"
)
add_arch_arch_cluster(
    "C0886",
    "Shypyntsi Bronze Age Site-Ukraine", "Shypyntsi (Eneolithic)", "Cucuteni-Trypillia settlement site",
    "Shypyntsi-Ukraine", "Shypyntsi (Rus)", "Medieval Rus settlement"
)
add_arch_mod_cluster(
    "C0888",
    "Skadovsk Karkinit-Ukraine", "Karkinit", "Classical coastal chora settlement distinct from modern port",
    "Skadovsk-Ukraine", "Skadovsk"
)
add_arch_arch_cluster(
    "C0891",
    "Selishcha Kavaltsy-4 Mediaeval Hillfort-Belarus", "Kavaltsy-4", "Medieval hillfort site",
    "Slavichy Stone Age Settlement Site 1023-Belarus", "Slavichi (Stone Age)", "Stone age campsite"
)
add_arch_mod_cluster(
    "C0892",
    "Sleptsovskaya Medieval Gorodishche-Russia", "Sunzha (Medieval)", "Early medieval Alanic fortified settlement distinct from modern city",
    "Sunzha-Russia", "Sunzha"
)
add_arch_mod_cluster(
    "C0894",
    "Smotrych-Ukraine_2", "Smotrych (Rus)", "Medieval chronicle Rus town distinct from modern settlement",
    "Smotrych-Ukraine", "Smotrych"
)
add_arch_arch_cluster(
    "C0895",
    "Klochkiv-1 Rus Settlement-Ukraine", "Klochkiv (Rus)", "Medieval Rus settlement",
    "Snovsk Iron Age Site 2-Ukraine", "Snovsk (Iron Age)", "Iron Age settlement"
)
add_arch_mod_cluster(
    "C0897",
    "Sobych Bronze Age Settlement-Ukraine", "Sobych (Bronze Age)", "Bronze Age settlement distinct from modern village",
    "Sobych-Ukraine", "Sobych"
)
add_arch_arch_cluster(
    "C0901",
    "Sokol-on-Dniester Iron Age Site-Ukraine", "Sokil (Iron Age)", "Chernyakhov iron age settlement",
    "Sokol-on-Dniester-Ukraine", "Sokil (Rus)", "Medieval Rus settlement on Dniester"
)
add_arch_arch_cluster(
    "C0905",
    "Sosnytsia Bronze Age Type-Site-Ukraine", "Sosnytsia (Bronze Age)", "Sosnytsia culture Bronze Age type-site",
    "Sosnytsia Iron Age Site 2-Ukraine", "Sosnytsia (Iron Age)", "Iron Age settlement"
)
add_arch_arch_cluster(
    "C0906",
    "Sosnytsia Bronze Age Site 2-Ukraine", "Sosnytsia II (Bronze Age)", "Bronze Age settlement site 2",
    "Sosnytsia Iron Age Site 3-Ukraine", "Sosnytsia III (Iron Age)", "Iron Age settlement site 3"
)
add_arch_mod_cluster(
    "C0908",
    "Sozh Terrace Bronze Age Site-Belarus", "Vetka (Bronze Age)", "Bronze Age river terrace settlement distinct from modern town",
    "Vetka-Belarus", "Vetka"
)
add_arch_mod_cluster(
    "C0909",
    "Spiridonovka IV Bronze Age Settlement-Russia", "Spiridonovka IV", "Bronze Age settlement distinct from modern village",
    "Spiridonovka-Russia", "Spiridonovka"
)
add_arch_mod_cluster(
    "C0910",
    "Stanislav Classical Polis-Ukraine", "Stanislav (Ancient)", "Classical coastal settlement distinct from modern village",
    "Stanislav-Ukraine", "Stanislav"
)
add_arch_mod_cluster(
    "C0912",
    "Staraya Poltavka-Bronze-Russia", "Staraya Poltavka (Bronze Age)", "Bronze Age settlement distinct from modern village",
    "Staraya Poltavka-Russia", "Staraya Poltavka"
)
add_arch_mod_cluster(
    "C0913",
    "Starobin-Belarus_2", "Starobin (Rus)", "Medieval Rus settlement distinct from modern town",
    "Starobin-Belarus", "Starobin"
)
add_arch_mod_cluster(
    "C0917",
    "Staryye Atagi Medieval Gorodishche-Russia", "Staryye Atagi (Medieval)", "Medieval fortified settlement distinct from modern town",
    "Staryye Atagi-Russia", "Staryye Atagi"
)
add_arch_arch_cluster(
    "C0920",
    "Garadzishcha peryyadu rannyaga syarednyavechcha Site 106-Belarus", "Zagoriny (Early Medieval)", "Early medieval hillfort",
    "Stayanka peryyadu mezalitu nealitu bronzavaga veku-Belarus", "Zagoriny (Bronze Age)", "Stone and Bronze Age settlement"
)

# 3. CHUNK 2 (25 to 49)
add_arch_mod_cluster(
    "C0927",
    "Stetskivka Iron Age Hillfort-Ukraine", "Stetskivka (Iron Age)", "Scythian Iron Age hillfort distinct from modern village",
    "Stetskivka-Ukraine", "Stetskivka"
)
add_arch_arch_cluster(
    "C0928",
    "Stina Bronze Age Site-Ukraine", "Stina (Bronze Age)", "Bronze Age settlement",
    "Stina-Ukraine", "Stina (Iron Age)", "Iron Age settlement"
)
add_arch_mod_cluster(
    "C0930",
    "Stoyanka 1 u s. Borovoe-Russia", "Borovoe 1", "Medieval campsite at Borovoe distinct from Somovo",
    "Somovo-Russia", "Somovo"
)
add_arch_mod_cluster(
    "C0932",
    "Stoyanka Tavatuy-VI (Kalinovo)-Russia", "Tavatuy-VI", "Medieval campsite on Lake Tavatuy distinct from modern town",
    "Kalinovo-Russia", "Kalinovo"
)
add_arch_arch_cluster(
    "C0934",
    "Strilcha Skelya 1 Stone Age Hillfort-Ukraine", "Strilcha Skelya (Mesolithic)", "Mesolithic stone age site",
    "Strilcha Skelya Neolithic Settlement-Ukraine", "Strilcha Skelya (Neolithic)", "Neolithic settlement"
)
add_arch_mod_cluster(
    "C0936",
    "Subotiv-Ukraine_2", "Subotiv (Chernyakhov)", "Chernyakhov migration-period settlement distinct from Cossack town",
    "Subotiv-Ukraine", "Subotiv"
)
add_arch_mod_cluster(
    "C0938",
    "Sudzha-Russia_2", "Sudzha (Medieval)", "Early medieval Severian hillfort distinct from modern city",
    "Sudza-Russia", "Sudzha", "Clean modern display name for primary city"
)
add_arch_mod_cluster(
    "C0939",
    "Sumka Valley Severian Settlement-Ukraine", "Sumka (Severian)", "Severian settlement in Sumka valley distinct from modern town",
    "Stepanivka-Ukraine", "Stepanivka"
)
add_arch_mod_cluster(
    "C0940",
    "Surazh-on-Dvina-Belarus", "Surazh (Rus)", "Medieval Rus fortified settlement on Dvina distinct from modern town",
    "Surazh-Belarus", "Surazh"
)
add_arch_mod_cluster(
    "C0941",
    "Surkhakhi Medieval Gorodishche-Russia", "Surkhakhi (Medieval)", "Early medieval Alanic fortified settlement distinct from modern town",
    "Surkhakhi-Russia", "Surkhakhi"
)
add_arch_arch_cluster(
    "C0942",
    "Susuya Iron Age Site-Russia", "Susuya (Iron Age)", "Iron Age settlement on Sakhalin",
    "Susuya-Russia", "Susuya (Okhotsk)", "Okhotsk culture shell-midden settlement on Sakhalin"
)
add_arch_arch_cluster(
    "C0951",
    "Konstantinovka-Tashlik 2 Eneolithic Hillfort-Ukraine", "Tashlyk (Eneolithic)", "Trypillia Eneolithic hillfort",
    "Tashlyk Bronze-Ukraine", "Tashlyk (Bronze Age)", "Sabatinovka Bronze Age settlement"
)
add_arch_mod_cluster(
    "C0956",
    "Ternovka Bronze Age Settlement-Russia", "Ternovka (Bronze Age)", "Bronze Age settlement distinct from modern village",
    "Ternovka-Russia", "Ternovka"
)
add_arch_mod_cluster(
    "C0958",
    "Tindi Bronze Age Site-Russia", "Tindi (Bronze Age)", "Bronze Age settlement in Dagestan distinct from modern village",
    "Tindi-Russia", "Tindi"
)
add_arch_mod_cluster(
    "C0959",
    "Tinit Medieval Gorodishche-Russia", "Tinit (Medieval)", "Medieval fortified mountain settlement distinct from modern village",
    "Tinit-Russia", "Tinit"
)
add_arch_arch_cluster(
    "C0964",
    "Torpakh-Kala Bronze Age Site-Russia", "Torpakh-Kala (Bronze Age)", "Early Bronze Age settlement",
    "Torpakh-Kala-Russia", "Torpakh-Kala (Early Medieval)", "Sasanian-Khazar period fortified city"
)
add_arch_arch_cluster(
    "C0965",
    "Trakhtemyriv Iron Age Site-Ukraine", "Trakhtemyriv (Iron Age)", "Scythian Iron Age hillfort",
    "Trakhtemyriv-Ukraine", "Trakhtemyriv (Chernyakhov)", "Chernyakhov migration-period settlement"
)
add_arch_mod_cluster(
    "C0967",
    "Troitskaya Medieval Gorodishche-Russia", "Troitskaya (Medieval)", "Medieval Alanic fortified site distinct from modern stanitsa",
    "Troitskaya-Russia", "Troitskaya"
)
add_arch_mod_cluster(
    "C0969",
    "Troyitske Bronze Age Settlement-Ukraine", "Troitske (Bronze Age)", "Bronze Age settlement distinct from modern town",
    "Troitske-Ukraine", "Troitske"
)
add_arch_mod_cluster(
    "C0970",
    "Trudy Iron Age Hillfort-Belarus", "Trudy (Iron Age)", "Iron Age hillfort distinct from modern village",
    "Trudy-Belarus", "Trudy"
)
add_arch_mod_cluster(
    "C0972",
    "Tsarevskoe gorodishche-Russia", "Tsarevskoe Gorodishche", "Pre-hiatus medieval archaeological city distinct from modern village",
    "Tsarev-Russia", "Tsarev"
)
add_arch_mod_cluster(
    "C0973",
    "Tsarichanka Orel-Ukraine", "Tsarychanka (Pre-modern)", "Bronze Age and medieval river settlement distinct from modern town",
    "Tsarychanka-Ukraine", "Tsarychanka"
)

# 4. CHUNK 3 (50 to 74)
add_arch_arch_cluster(
    "C0975",
    "Tsepan Iron Age Site-Russia", "Tsepan (Iron Age)", "Ananyino Iron Age settlement",
    "Tsepan-Russia", "Tsepan (Mazunino)", "Mazunino migration-period settlement"
)
add_arch_mod_cluster(
    "C0979",
    "Turysk-Ukraine", "Turiisk (Rus)", "Medieval chronicle Rus town distinct from modern settlement",
    "Turiisk-Ukraine", "Turiisk"
)
add_arch_mod_cluster(
    "C0982",
    "Tuzly Burnas Liman-Ukraine", "Burnas (Tuzly)", "Pre-modern lagoon settlement distinct from modern village",
    "Tuzly-Ukraine", "Tuzly"
)
add_arch_mod_cluster(
    "C0987",
    "Ulla-Belarus_2", "Ulla (Rus)", "Medieval Rus hillfort at Ulla-Dvina confluence distinct from modern town",
    "Ulla-Belarus", "Ulla"
)
add_arch_mod_cluster(
    "C0988",
    "Unava-Fastovets-Ukraine", "Unava (Fastivets)", "Medieval Rus settlement on Unava distinct from modern village",
    "Fastivets-Ukraine", "Fastivets"
)
add_arch_mod_cluster(
    "C0989",
    "Untsukul Medieval Gorodishche-Russia", "Untsukul (Medieval)", "Medieval fortified mountain settlement distinct from modern town",
    "Untsukul-Russia", "Untsukul"
)
add_arch_arch_cluster(
    "C0995",
    "Ust-Belaia Palaeolithic Camp-Russia", "Ust-Belaya (Palaeolithic)", "Upper Palaeolithic campsite",
    "Ust-Belaia-Russia", "Ust-Belaya (Neolithic)", "Holocene Neolithic stratified campsite"
)
add_arch_arch_cluster(
    "C0997",
    "Ust-Mil II Stone Age Site-Russia", "Ust-Mil II (Stone Age)", "Neolithic stone age site on Aldan",
    "Ust-Mil II-Russia", "Ust-Mil II (Bronze Age)", "Bronze Age Ust-Mil culture type-site"
)
add_arch_mod_cluster(
    "C0998",
    "Ust-Polui-Russia", "Ust-Polui", "Famous Iron Age archaeological site distinct from modern city",
    "Salechard-Russia", "Salekhard", "Clean modern display name for regional centre"
)
add_arch_mod_cluster(
    "C1000",
    "Valentin-Peresheyek Bronze Age Site-Russia", "Valentin-Peresheyek", "Bronze Age archaeological site distinct from modern village",
    "Valentin-Russia", "Valentin"
)
add_arch_mod_cluster(
    "C1004",
    "Vasilishki-Belarus_2", "Vasilishki (Rus)", "Medieval Rus settlement on Lebeda distinct from modern town",
    "Vasilishki-Belarus", "Vasilishki"
)
add_arch_mod_cluster(
    "C1005",
    "Velikaya Lepetikha Eneolithic Hillfort-Ukraine", "Velyka Lepetykha (Eneolithic)", "Trypillia Eneolithic hillfort distinct from modern town",
    "Velyka Lepetykha-Ukraine", "Velyka Lepetykha"
)
add_arch_mod_cluster(
    "C1008",
    "Velyka Bilozerka Iron Age Hillfort-Ukraine", "Velyka Bilozerka (Iron Age)", "Scythian Iron Age hillfort distinct from modern town",
    "Velyka Bilozerka-Ukraine", "Velyka Bilozerka"
)
add_arch_mod_cluster(
    "C1009",
    "Velyka Oleksandrivka Iron Age Hillfort-Ukraine", "Velyka Oleksandrivka (Iron Age)", "Scythian Iron Age hillfort distinct from modern town",
    "Velyka Oleksandrivka-Ukraine", "Velyka Oleksandrivka"
)
add_arch_mod_cluster(
    "C1010",
    "Velyka Pysarivka Iron Age Hillfort-Ukraine", "Velyka Pysarivka (Iron Age)", "Scythian Iron Age hillfort distinct from modern town",
    "Velyka Pysarivka-Ukraine", "Velyka Pysarivka"
)
add_arch_arch_cluster(
    "C1011",
    "5/Velyka Rybytsya Early Rus Settlement-Ukraine", "Velyka Rybytsia (Early Rus)", "Severian early Rus settlement",
    "Velyka Rybytsya Iron Age Hillfort-Ukraine", "Velyka Rybytsia (Iron Age)", "Scythian Iron Age hillfort"
)
add_arch_arch_cluster(
    "C1012",
    "Velyki Budky Bronze Age Settlement-Ukraine", "Velyki Budky (Bronze Age)", "Bronze Age settlement",
    "Velyki Budky Khmeliv-Ukraine", "Velyki Budky (Rus)", "Romny-Rus hillfort complex"
)
add_arch_mod_cluster(
    "C1013",
    "Velykodolynske Bronze Age Settlement-Ukraine", "Velykodolynske (Bronze Age)", "Bronze Age settlement distinct from modern town",
    "Velykodolynske-Ukraine", "Velykodolynske"
)
add_arch_mod_cluster(
    "C1014",
    "Velykonovosilkivskyy rayon Bronze Age Settlement-Ukraine", "Velyka Novosilka (Bronze Age)", "Bronze Age settlement distinct from modern town",
    "Velyka Novosilka-Ukraine", "Velyka Novosilka"
)
add_arch_mod_cluster(
    "C1016",
    "Verkhniy Baksan Medieval Gorodishche-Russia", "Verkhniy Baksan (Medieval)", "Medieval Alanic fortified site distinct from modern village",
    "Verkhniy Baksan-Russia", "Verkhniy Baksan"
)
add_arch_mod_cluster(
    "C1018",
    "Verkhniy Koban Iron Age Site-Russia", "Koban (Iron Age)", "Koban culture type-site distinct from modern village",
    "Verkhniy Koban-Russia", "Verkhniy Koban", "Clean display name for historic Ossetian village"
)
add_arch_mod_cluster(
    "C1022",
    "Viazniki Medieval Gorodishche-Russia", "Yaropolch-Zalesskiy", "Medieval chronicle Rus city distinct from modern Vyazniki",
    "Vyazniki-Russia", "Vyazniki"
)
add_arch_mod_cluster(
    "C1024",
    "Vilshana Bronze Age Settlement-Ukraine", "Vilshana (Bronze Age)", "Bronze Age settlement distinct from modern town",
    "Vilshana_UA_21-Ukraine", "Vilshana"
)
add_arch_mod_cluster(
    "C1026",
    "Vitsebsk Iron Age Hillfort-Belarus", "Vitebsk (Iron Age)", "Dnieper-Dvina Iron Age hillfort distinct from historic city",
    "Vicebsk-Belarus", "Vitebsk", "Clean modern display name for regional centre"
)

# 5. CHUNK 4 (75 to 99)
add_arch_mod_cluster(
    "C1027",
    "Vitskhi Medieval Gorodishche-Russia", "Vitskhi (Medieval)", "Medieval fortified mountain site distinct from modern village",
    "Vitskhi-Russia", "Vitskhi"
)
add_arch_arch_cluster(
    "C1029",
    "Dzaudzhikau Alanic Settlement-Russia", "Vladikavkaz (Alanic)", "Medieval Alanic settlement",
    "Vladikavkaz Koban Site-Russia", "Vladikavkaz (Koban)", "Koban culture Iron Age site"
)
add_arch_arch_cluster(
    "C1030",
    "Vodiane Ancient Gord-Ukraine", "Vodiane (Medieval)", "Early medieval Saltovo / Rus hillfort",
    "Vodyane Iron Age Hillfort-Ukraine", "Vodiane (Iron Age)", "Scythian Iron Age hillfort"
)
add_arch_mod_cluster(
    "C1031",
    "Vodyanoye Classical Polis-Ukraine", "Vodiane (Ancient)", "Classical coastal settlement distinct from modern village",
    "Vodiane-Ukraine", "Vodiane"
)
add_arch_mod_cluster(
    "C1038",
    "Voronizh-Ukraine_2", "Voronizh (Rus)", "Medieval 1177 chronicle Rus town distinct from modern settlement",
    "Voronizh-Ukraine", "Voronizh"
)
add_arch_mod_cluster(
    "C1040",
    "Vorozhba-Ukraine_2", "Vorozhba (Rus)", "Medieval Rus portage settlement distinct from modern town",
    "Vorozhba-Ukraine", "Vorozhba"
)
add_arch_mod_cluster(
    "C1041",
    "Vorzel-Irpin-Ukraine", "Vorzel-Irpin", "Medieval Rus settlement on Irpin distinct from modern Bucha",
    "Bucha-Ukraine", "Bucha"
)
add_arch_mod_cluster(
    "C1044",
    "Voznesensk Bug Ford-Ukraine", "Voznesensk (Bug Ford)", "Pre-modern river crossing settlement distinct from modern city",
    "Voznesensk-Ukraine", "Voznesensk"
)
add_arch_mod_cluster(
    "C1045",
    "Vradiyivka-V Bronze Age Settlement-Ukraine", "Vradiyivka (Bronze Age)", "Bronze Age settlement distinct from modern town",
    "Vradiyivka-Ukraine", "Vradiyivka"
)
add_arch_arch_cluster(
    "C1050",
    "Vinogradnyy Sad Bronze Age Settlement-Ukraine", "Vynohradny Sad (Bronze Age)", "Sabatinovka Bronze Age settlement",
    "Vynohradnyy Sad VIII Migration Period Settlement-Ukraine", "Vynohradny Sad (Migration Period)", "Chernyakhov migration-period settlement"
)
add_arch_mod_cluster(
    "C1052",
    "Vysunsk Iron Age Hillfort-Ukraine", "Vysunsk (Iron Age)", "Scythian Iron Age hillfort distinct from modern village",
    "Vysunsk-Ukraine", "Vysunsk"
)
add_arch_mod_cluster(
    "C1053",
    "Yampil-Ivot Wooded Terrace Settlement-Ukraine", "Ivot (Medieval)", "Medieval Severian settlement at Ivot distinct from modern town",
    "Yampil_UA_21-Ukraine", "Yampil"
)
add_arch_mod_cluster(
    "C1059",
    "Zalishchyky Bronze Age Site-Ukraine", "Zalishchyky (Bronze Age)", "Trypillia and Bronze Age settlement on Dniester distinct from modern town",
    "Zalishchyky-Ukraine", "Zalishchyky"
)
add_arch_mod_cluster(
    "C1061",
    "Zalukokoazhskoe gorodishche Chernaya gora-Russia", "Chernaya Gora", "Medieval hillfort Chernaya Gora distinct from modern town",
    "Zalukokoazhe-Russia", "Zalukokoazhe"
)
add_arch_mod_cluster(
    "C1064",
    "Zandak Iron Age Site-Russia", "Zandak (Iron Age)", "Iron Age settlement in Chechnya distinct from modern village",
    "Zandak-Russia", "Zandak"
)
add_arch_mod_cluster(
    "C1066",
    "Zaraysk Palaeolithic-Russia", "Zaraysk (Palaeolithic)", "Famous Upper Palaeolithic site distinct from historic city",
    "Zaraysk-Russia", "Zaraysk"
)
add_arch_arch_cluster(
    "C1067",
    "Zarichne-Bogodukhov Trostyanets Vorskla Hillfort Iron Age Site-Ukraine", "Zarichne (Iron Age)", "Scythian Iron Age hillfort on Vorskla",
    "Zarichne-Bogodukhov Trostyanets Vorskla Hillfort-Ukraine", "Zarichne (Rus)", "Severian / Rus hillfort"
)
add_arch_arch_cluster(
    "C1068",
    "Zarub Iron Age Site-Ukraine", "Zarub (Chernyakhov)", "Chernyakhov Iron Age settlement",
    "Zarub-Ukraine", "Zarub (Rus)", "Medieval Rus chronicle town on Dnieper"
)
add_arch_arch_cluster(
    "C1073",
    "Stayanka-1 peryyadu nealitu-Belarus_3", "Zdzitava (Rus)", "Medieval Rus settlement at Zdzitava",
    "Zdzitava Bronze Age Settlement-Belarus", "Zdzitava (Bronze Age)", "Bronze Age settlement"
)
add_arch_mod_cluster(
    "C1077",
    "Zhvaniets Neolithic Settlement-Ukraine", "Zhvanets (Neolithic)", "Trypillia Neolithic settlement distinct from historic town",
    "Zhvanets-Ukraine", "Zhvanets"
)
add_arch_mod_cluster(
    "C1079",
    "Zmeyskaya Medieval Gorodishche-Russia", "Zmeyskaya (Alanic)", "Alanic medieval city and necropolis distinct from modern stanitsa",
    "Zmeyskaya-Russia", "Zmeyskaya"
)
add_arch_arch_cluster(
    "C1080",
    "Mokhnach-Ukraine", "Mokhnach", "Saltovo and Rus frontier hillfort",
    "Zmiyinets Bronze Age Settlement-Ukraine", "Zmiyinets", "Bronze Age settlement distinct from Mokhnach"
)
add_arch_mod_cluster(
    "C1082",
    "Zolotarevskoe settlement-Russia", "Zolotarevskoe Gorodishche", "Famous medieval fortified city distinct from modern settlement",
    "Zolotaryovka-Russia", "Zolotaryovka"
)

# 6. CHUNK 5 (100 to 126)
add_arch_arch_cluster(
    "C1086",
    "Zymne Bronze Age Site-Ukraine", "Zymne (Eneolithic)", "Early agricultural Eneolithic settlement",
    "Zymne-Ukraine", "Zymne (Early Slavic)", "Famous early Slavic fortified hillfort"
)
add_arch_mod_cluster(
    "C1087",
    "Zymohirya Iron Age Hillfort-Ukraine", "Zymohirya (Iron Age)", "Scythian Iron Age hillfort distinct from modern city",
    "Zymohirya-Ukraine", "Zymohirya"
)
add_arch_arch_cluster(
    "C1088",
    "Karolino-Bugaz 1 Eneolithic Hillfort-Ukraine", "Karolino-Buhaz (Eneolithic)", "Usatove Eneolithic hillfort",
    "antychnoho chasu Buhaz V Classical Polis-Ukraine", "Buhaz V", "Classical Greek settlement on Dniester Liman"
)
add_arch_mod_cluster(
    "C1089",
    "antychnoho chasu Classical Polis II-Ukraine", "Serhiyivka (Ancient)", "Classical Greek settlement distinct from modern resort town",
    "Serhiyivka-Ukraine", "Serhiyivka"
)
add_arch_mod_cluster(
    "C1096",
    "chernyakhivske Dmytrivka Chernyakhov Settlement-Ukraine", "Dmytrivka (Chernyakhov)", "Chernyakhov settlement distinct from modern village",
    "Dmytrivka_UA_17-Ukraine", "Dmytrivka"
)
add_arch_arch_cluster(
    "C1097",
    "Khadzhyder Neolithic Settlement-Ukraine", "Hadzhyder (Neolithic)", "Neolithic settlement",
    "chernyakhivske Khadzhyder I Chernyakhov Settlement-Ukraine", "Hadzhyder (Chernyakhov)", "Chernyakhov settlement"
)
add_arch_mod_cluster(
    "C1102",
    "chernyakhivskoyi kultury Chernyakhov Settlement-Ukraine_2", "Yaruha (Chernyakhov)", "Chernyakhov settlement distinct from modern village",
    "Yaruha-Ukraine", "Yaruha"
)
add_arch_arch_cluster(
    "C1103",
    "chernyakhivske Chervone II-a Chernyakhov Settlement-Ukraine", "Chervone (Chernyakhov)", "Chernyakhov settlement",
    "dvosharove Chervone II doby bronzy ta rymskoho chasu Bronze Age Settlement-Ukraine", "Chervone (Bronze Age)", "Bronze Age settlement"
)
add_arch_arch_cluster(
    "C1104",
    "chernyakhivske Delen IV Chernyakhov Settlement-Ukraine", "Delen (Chernyakhov)", "Chernyakhov settlement",
    "dvosharove Delen I doby piznoyi bronzy ta piznorymskoho chasu Bronze Age Settlement-Ukraine", "Delen (Bronze Age)", "Bronze Age settlement"
)
add_arch_arch_cluster(
    "C1105",
    "chernyakhivske Mykolayivka-Novorosiyska V Chernyakhov Settlement-Ukraine", "Mykolayivka-Novorosiyska (Chernyakhov)", "Chernyakhov settlement",
    "dvosharove Mykolayivka-Novorosiyska I doby piznoyi bronzy ta chernyakhivske Bronze Age Settlement-Ukraine", "Mykolayivka-Novorosiyska (Bronze Age)", "Bronze Age settlement"
)
add_arch_arch_cluster(
    "C1106",
    "chernyakhivske Myrnopillya Chernyakhov Settlement-Ukraine", "Myrnopillya (Chernyakhov)", "Chernyakhov settlement",
    "dvosharove Myrnopillya II sabatynivske ta rymskoho chasu Bronze Age Settlement-Ukraine", "Myrnopillya (Bronze Age)", "Sabatinovka Bronze Age settlement"
)
add_arch_arch_cluster(
    "C1107",
    "chernyakhivske Bannivka I Chernyakhov Settlement-Ukraine", "Bannivka (Chernyakhov)", "Chernyakhov settlement",
    "dvosharove doby piznoyi bronzy ta chernyakhivske Bannivka VII Bronze Age Settlement-Ukraine", "Bannivka (Bronze Age)", "Bronze Age settlement"
)
add_arch_arch_cluster(
    "C1108",
    "Novokamyanka Eneolithic Hillfort-Ukraine", "Novokamyanka (Eneolithic)", "Usatove Eneolithic hillfort",
    "dvosharove doby piznoyi bronzy ta chernyakhivske Novokamyanka Bronze Age Settlement II-Ukraine", "Novokamyanka (Bronze Age)", "Bronze Age settlement"
)
add_arch_arch_cluster(
    "C1113",
    "chernyakhivske Yosypivka I Chernyakhov Settlement-Ukraine", "Yosypivka (Chernyakhov)", "Chernyakhov settlement",
    "dvosharove doby piznoyi bronzy ta rymskoho chasu Yosypivka Bronze Age Settlement-Ukraine", "Yosypivka (Bronze Age)", "Bronze Age settlement"
)
add_arch_arch_cluster(
    "C1116",
    "Kyslytsya Eneolithic Hillfort-Ukraine", "Kyslytsya (Eneolithic)", "Gumelnita Eneolithic hillfort",
    "dvosharove sabatynivske ta balkano-dunayske pivdennykh slovyan Kyslytsya Bronze Age Settlement-Ukraine", "Kyslytsya (Bronze Age)", "Sabatinovka Bronze Age settlement"
)
add_arch_arch_cluster(
    "C1117",
    "chernyakhivske Hrybivka III Chernyakhov Settlement-Ukraine", "Hrybivka (Chernyakhov)", "Chernyakhov settlement",
    "dvosharove sabatynivske ta skifske Hrybivka II Iron Age Hillfort-Ukraine", "Hrybivka (Iron Age)", "Scythian Iron Age hillfort"
)
add_arch_mod_cluster(
    "C1118",
    "dvosharove skifske ta chernyakhivske Troyitske III Iron Age Hillfort-Ukraine", "Troyitske (Iron Age)", "Scythian Iron Age hillfort distinct from modern village",
    "Troyitske-Ukraine", "Troyitske"
)
add_arch_mod_cluster(
    "C1120",
    "kamyanoho viku Kominternivske II Stone Age Settlement-Ukraine", "Dobroslav (Stone Age)", "Stone Age settlement distinct from modern town",
    "Dobroslav-Ukraine", "Dobroslav"
)
add_arch_mod_cluster(
    "C1121",
    "kurahn Bronze Age Settlement-Ukraine", "Staryi Krym (Bronze Age)", "Bronze Age settlement distinct from modern town",
    "Staryi Krym-Ukraine", "Staryi Krym"
)
add_arch_arch_cluster(
    "C1124",
    "chernyakhivske Kostyantynivka IV Chernyakhov Settlement-Ukraine", "Kostyantynivka (Chernyakhov)", "Chernyakhov settlement",
    "mezolitychna Kostyantynivka III Mesolithic Camp-Ukraine", "Kostyantynivka (Mesolithic)", "Mesolithic campsite"
)
add_arch_arch_cluster(
    "C1125",
    "dvosharove sabatynivske ta chernyakhivske Markivka Chernyakhov Settlement-Ukraine", "Markivka (Chernyakhov)", "Chernyakhov settlement",
    "mezolitychna Markivka Mesolithic Camp-Ukraine", "Markivka (Mesolithic)", "Mesolithic campsite"
)
add_arch_mod_cluster(
    "C1128",
    "mistseznakhodzhennya paleolitu KhKh-Kh tys do. n.e Palaeolithic Camp-Ukraine", "Kuriachivka (Palaeolithic)", "Palaeolithic campsite distinct from modern village",
    "Kuriachivka-Ukraine", "Kuriachivka"
)
add_arch_arch_cluster(
    "C1132",
    "dvosharove Valya-Perzhey I doby piznoyi bronzy ta chernyakhivske Bronze Age Settlement-Ukraine", "Valya-Perzhey (Bronze Age)", "Late Bronze Age settlement",
    "rymskoho chasu Valya-Perzhey-Stavky II Classical Polis-Ukraine", "Valya-Perzhey (Classical)", "Classical / Roman era settlement"
)
add_arch_arch_cluster(
    "C1134",
    "piznopaleolitychna Kamyanka II Palaeolithic Camp-Ukraine", "Kamyanka (Palaeolithic)", "Late Palaeolithic campsite",
    "sabatynivske Kamyanka II Bronze Age Settlement-Ukraine", "Kamyanka (Bronze Age)", "Sabatinovka Bronze Age settlement"
)
add_arch_arch_cluster(
    "C1135",
    "rymskoho chasu Kolisne III Classical Polis-Ukraine", "Kolisne (Classical)", "Classical / Roman era settlement",
    "sabatynivske Kolisne II Bronze Age Settlement-Ukraine", "Kolisne (Bronze Age)", "Sabatinovka Bronze Age settlement"
)
add_arch_arch_cluster(
    "C1137",
    "Mistseznakhodzhennya paleolitu. Poselennya Palaeolithic Camp-Ukraine", "Oleksapil (Palaeolithic)", "Palaeolithic campsite",
    "selyshche Mediaeval Hillfort-Ukraine", "Oleksapil (Medieval)", "Early medieval Slavic settlement"
)
add_arch_arch_cluster(
    "C1139",
    "Gomolsha Scythian-Ukraine", "Gomolsha (Hillfort)", "Scythian and Saltovo hillfort",
    "ta kurhannyy mohylnyk Bronze Age Hillfort-Ukraine", "Gomolsha (Bronze Age)", "Bronze Age settlement"
)

# BUILD OUTPUT LIST
output_list = []
for c in input_clusters:
    cid = c['cluster_id']
    if cid not in DECISIONS:
        raise ValueError(f"Missing decision for cluster {cid}!")
    entry = {
        "cluster_id": cid,
        "actions": DECISIONS[cid]["actions"],
        "clean_names": DECISIONS[cid]["clean_names"]
    }
    output_list.append(entry)

print(f"Built {len(output_list)} output entries.")

# Write output file
out_path = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\out_tier2_batch_4.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output_list, f, indent=2, ensure_ascii=False)

print(f"Successfully wrote output to {out_path}")
