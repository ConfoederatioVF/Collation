import json

INPUT_PATH = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\tier2_batch_3.json'
OUTPUT_PATH = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\out_tier2_batch_3.json'

with open(INPUT_PATH, 'r', encoding='utf-8') as f:
    clusters = json.load(f)

# Verification map
DECISIONS = {
    "C0608": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Konsulovske Ancient settlement-Ukraine",
                "new_name": "Konsulovske (Rus)",
                "reason": "Pre-Mongol medieval settlement on the Lower Dnieper separated by >400y gap from Classical era fortified site"
            },
            {
                "op": "RENAME_META",
                "key": "Konsulovskoye Classical Polis-Ukraine",
                "new_name": "Konsulovske (Classical)",
                "reason": "Late Scythian fortified polis/settlement on the Lower Dnieper (-500..400)"
            }
        ],
        "clean_names": {
            "Konsulovske Ancient settlement-Ukraine": "Konsulovske (Rus)",
            "Konsulovskoye Classical Polis-Ukraine": "Konsulovske (Classical)"
        }
    },
    "C0610": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kopys-Belarus_2",
                "new_name": "Kopys (Rus)",
                "reason": "Pre-Mongol to early medieval Rus castle-town on the Dnieper, separated by >300y gap from modern Kopys"
            }
        ],
        "clean_names": {
            "Kopys-Belarus": "Kopys",
            "Kopys-Belarus_2": "Kopys (Rus)"
        }
    },
    "C0611": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kornyn Eneolithic Hillfort-Ukraine",
                "new_name": "Kornyn (Eneolithic)",
                "reason": "Cucuteni-Trypillia Eneolithic hillfort near modern Kornyn, separated by >4500y gap"
            }
        ],
        "clean_names": {
            "Kornyn-Ukraine": "Kornyn",
            "Kornyn Eneolithic Hillfort-Ukraine": "Kornyn (Eneolithic)"
        }
    },
    "C0612": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Korobchino Eneolithic Hillfort-Ukraine",
                "new_name": "Korobchyne (Eneolithic)",
                "reason": "Cucuteni-Trypillia Eneolithic hillfort near modern Korobchyne, separated by >4500y gap"
            }
        ],
        "clean_names": {
            "Korobchyne-Ukraine": "Korobchyne",
            "Korobchino Eneolithic Hillfort-Ukraine": "Korobchyne (Eneolithic)"
        }
    },
    "C0613": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Korolevo-Ukraine_2",
                "new_name": "Korolevo (Palaeolithic)",
                "reason": "Internationally significant Lower/Middle/Upper Palaeolithic site on the Tysa River, separated by millennia from modern Korolevo"
            }
        ],
        "clean_names": {
            "Korolevo-Ukraine": "Korolevo",
            "Korolevo-Ukraine_2": "Korolevo (Palaeolithic)"
        }
    },
    "C0614": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Korop Iron Age Site-Ukraine",
                "new_name": "Korop (Iron Age)",
                "reason": "Early Iron Age settlement on the Desna, separated by >1200y gap from modern Korop"
            }
        ],
        "clean_names": {
            "Korop-Ukraine": "Korop",
            "Korop Iron Age Site-Ukraine": "Korop (Iron Age)"
        }
    },
    "C0619": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kostenki (Kostienki) 11 (Anosovka 2) Palaeolithic Camp-Russia",
                "new_name": "Kostenki (Palaeolithic)",
                "reason": "Famous Upper Palaeolithic mammoth-bone dwelling site (Kostenki 11 / Anosovka 2) on the Don, separated by millennia from modern Kostenki"
            }
        ],
        "clean_names": {
            "Kostenki-Russia": "Kostenki",
            "Kostenki (Kostienki) 11 (Anosovka 2) Palaeolithic Camp-Russia": "Kostenki (Palaeolithic)"
        }
    },
    "C0620": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Kostyol Uspeniya Presvyatoy Devy Marii Mediaeval Hillfort-Belarus",
                "reason": "19th-century Catholic Church of the Assumption in Zhaludok misidentified in heritage registry scrape as a medieval hillfort with fabricated dates [850..1350]"
            }
        ],
        "clean_names": {
            "Zhaludok-Belarus": "Zhaludok"
        }
    },
    "C0622": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kotovka Neolithic Settlement-Ukraine",
                "new_name": "Kotovka (Neolithic)",
                "reason": "Neolithic settlement site near modern Kotovka, separated by millennia from modern village"
            }
        ],
        "clean_names": {
            "Kotovka-Ukraine": "Kotovka",
            "Kotovka Neolithic Settlement-Ukraine": "Kotovka (Neolithic)"
        }
    },
    "C0623": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Khybalivka-1 Rus Settlement-Ukraine",
                "new_name": "Khybalivka (Rus)",
                "reason": "Pre-Mongol medieval Rus rural settlement near Khybalivka"
            },
            {
                "op": "RENAME_META",
                "key": "Kozarovshchyna-2 Bronze Age Settlement-Ukraine",
                "new_name": "Kozarovshchyna",
                "reason": "Distinct Bronze Age settlement site Kozarovshchyna-2, separated from Khybalivka and given its attested toponym"
            }
        ],
        "clean_names": {
            "Khybalivka-1 Rus Settlement-Ukraine": "Khybalivka (Rus)",
            "Kozarovshchyna-2 Bronze Age Settlement-Ukraine": "Kozarovshchyna"
        }
    },
    "C0624": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kozatske Iron Age Hillfort-Ukraine",
                "new_name": "Kozatske (Iron Age)",
                "reason": "Early Iron Age / Scythian hillfort on the Lower Dnieper near modern Kozatske, separated by >1800y gap"
            }
        ],
        "clean_names": {
            "Kozatske-Ukraine": "Kozatske",
            "Kozatske Iron Age Hillfort-Ukraine": "Kozatske (Iron Age)"
        }
    },
    "C0625": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kozhanka Eneolithic Hillfort-Ukraine",
                "new_name": "Kozhanka (Eneolithic)",
                "reason": "Cucuteni-Trypillia Eneolithic hillfort near modern Kozhanka, separated by >4300y gap"
            }
        ],
        "clean_names": {
            "Kozhanka-Ukraine": "Kozhanka",
            "Kozhanka Eneolithic Hillfort-Ukraine": "Kozhanka (Eneolithic)"
        }
    },
    "C0628": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Krasni Okny Bronze Age Settlement-Ukraine",
                "new_name": "Okny (Bronze Age)",
                "reason": "Bronze Age settlement site near modern Okny, separated by >2600y gap"
            }
        ],
        "clean_names": {
            "Okny-Ukraine": "Okny",
            "Krasni Okny Bronze Age Settlement-Ukraine": "Okny (Bronze Age)"
        }
    },
    "C0629": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Krasnopillya Bronze Age Settlement-Ukraine",
                "new_name": "Krasnopillya (Bronze Age)",
                "reason": "Bronze Age settlement site near Krasnopillya, separated by >2500y gap from modern town"
            }
        ],
        "clean_names": {
            "Krasnopillya-Ukraine": "Krasnopillya",
            "Krasnopillya Bronze Age Settlement-Ukraine": "Krasnopillya (Bronze Age)"
        }
    },
    "C0634": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kormil Rus Settlement-Ukraine",
                "new_name": "Kormil",
                "reason": "Distinct pre-Mongol Rus settlement site with attested toponym Kormil"
            },
            {
                "op": "RENAME_META",
                "key": "Krasulka Bronze Age Settlement-Ukraine",
                "new_name": "Krasulka",
                "reason": "Distinct Bronze Age settlement site with attested toponym Krasulka"
            }
        ],
        "clean_names": {
            "Kormil Rus Settlement-Ukraine": "Kormil",
            "Krasulka Bronze Age Settlement-Ukraine": "Krasulka"
        }
    },
    "C0639": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kublichy (arkhealagichny pomnik)-Belarus",
                "new_name": "Kublichi (Early Medieval)",
                "reason": "Early medieval / Slavic hillfort and archaeological monument at Kublichi, separated by >600y gap from modern village"
            }
        ],
        "clean_names": {
            "Kublichi-Belarus": "Kublichi",
            "Kublichy (arkhealagichny pomnik)-Belarus": "Kublichi (Early Medieval)"
        }
    },
    "C0646": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kurchaloy Bronze Age Site-Russia",
                "new_name": "Kurchaloy (Bronze Age)",
                "reason": "Late Bronze Age / Koban culture settlement site near Kurchaloy, separated by >2400y gap from modern city"
            }
        ],
        "clean_names": {
            "Kurchaloy-Russia": "Kurchaloy",
            "Kurchaloy Bronze Age Site-Russia": "Kurchaloy (Bronze Age)"
        }
    },
    "C0648": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kurilskoe Ozero Gorodishche-Russia",
                "new_name": "Kurilskoye Lake (Early Medieval)",
                "reason": "Early medieval fortified archaeological site on Kurilskoye Lake (Kamchatka) dating 400..600 AD"
            },
            {
                "op": "RENAME_META",
                "key": "Kurilskoe Ozero Medieval Gorodishche-Russia",
                "new_name": "Kurilskoye Lake (Medieval)",
                "reason": "Medieval fortified archaeological site on Kurilskoye Lake dating 900..1100 AD"
            }
        ],
        "clean_names": {
            "Kurilskoe Ozero Gorodishche-Russia": "Kurilskoye Lake (Early Medieval)",
            "Kurilskoe Ozero Medieval Gorodishche-Russia": "Kurilskoye Lake (Medieval)"
        }
    },
    "C0649": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kurmanaevka III Neolithic Settlement-Russia",
                "new_name": "Kurmanayevka (Neolithic)",
                "reason": "Neolithic / Eneolithic settlement site Kurmanayevka III in Orenburg Oblast, separated by >4300y gap from modern Kurmanayevka"
            }
        ],
        "clean_names": {
            "Kurmanayevka-Russia": "Kurmanayevka",
            "Kurmanaevka III Neolithic Settlement-Russia": "Kurmanayevka (Neolithic)"
        }
    },
    "C0650": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kushnarenkovo-Russia_2",
                "new_name": "Kushnarenkovo (Early Medieval)",
                "reason": "Eponymous early medieval Kushnarenkovo culture fortified settlement on Mount Deva, separated by >800y gap from modern Kushnarenkovo"
            }
        ],
        "clean_names": {
            "Kushnarenkovo-Russia": "Kushnarenkovo",
            "Kushnarenkovo-Russia_2": "Kushnarenkovo (Early Medieval)"
        }
    },
    "C0651": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kvanada Medieval Gorodishche-Russia",
                "new_name": "Kvanada (Medieval)",
                "reason": "Medieval Dagestani fortified gorodishche at Kvanada, separated by >400y gap from early modern aul"
            }
        ],
        "clean_names": {
            "Kvanada-Russia": "Kvanada",
            "Kvanada Medieval Gorodishche-Russia": "Kvanada (Medieval)"
        }
    },
    "C0653": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kyondelen Bronze Age Site-Russia",
                "new_name": "Kyondelen (Bronze Age)",
                "reason": "Late Bronze Age / Koban culture settlement site in the Baksan gorge near Kyondelen, separated by >2400y gap"
            }
        ],
        "clean_names": {
            "Kyondelen-Russia": "Kyondelen",
            "Kyondelen Bronze Age Site-Russia": "Kyondelen (Bronze Age)"
        }
    },
    "C0655": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kytmanovo Bronze Age Settlement-Russia",
                "new_name": "Kytmanovo (Bronze Age)",
                "reason": "Andronovo culture Bronze Age settlement site on the Chumysh River near modern Kytmanovo, separated by >3100y gap"
            }
        ],
        "clean_names": {
            "Kytmanovo-Russia": "Kytmanovo",
            "Kytmanovo Bronze Age Settlement-Russia": "Kytmanovo (Bronze Age)"
        }
    },
    "C0659": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Lebyazhskoye Hillfort-Russia",
                "new_name": "Lebyazhskoye Hillfort",
                "reason": "Medieval Mari / Slavic hillfort on the Vyatka River near Lebyazhye, separated by >300y gap"
            }
        ],
        "clean_names": {
            "Lebjaž'je-Russia": "Lebyazhye",
            "Lebyazhskoye Hillfort-Russia": "Lebyazhskoye Hillfort"
        }
    },
    "C0665": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Lokachi-Ukraine_2",
                "new_name": "Lokachi (Rus)",
                "reason": "Pre-Mongol medieval Volhynian Rus hillfort and settlement at Lokachi, separated by >500y gap from modern town"
            }
        ],
        "clean_names": {
            "Lokachi-Ukraine": "Lokachi",
            "Lokachi-Ukraine_2": "Lokachi (Rus)"
        }
    },
    "C0666": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Loknya-Sudzha Portage Hillfort-Ukraine",
                "new_name": "Loknya Hillfort",
                "reason": "Severian / Rus portage hillfort on the Loknya River near Yunakivka, separated by >380y gap"
            }
        ],
        "clean_names": {
            "Yunakivka-Ukraine": "Yunakivka",
            "Loknya-Sudzha Portage Hillfort-Ukraine": "Loknya Hillfort"
        }
    },
    "C0667": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Luchek Medieval Gorodishche-Russia",
                "new_name": "Luchek (Medieval)",
                "reason": "Medieval fortified gorodishche at Luchek (Rutul district, Dagestan), separated by >400y gap from later aul"
            }
        ],
        "clean_names": {
            "Luchek-Russia": "Luchek",
            "Luchek Medieval Gorodishche-Russia": "Luchek (Medieval)"
        }
    },
    "C0668": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Lugovoye Bronze Age Site-Russia",
                "new_name": "Lugovoye (Bronze Age)",
                "reason": "Early Bronze Age settlement site at Lugovoye (-3500..-3000)"
            },
            {
                "op": "RENAME_META",
                "key": "Lugovoye Iron Age Site-Russia",
                "new_name": "Lugovoye (Iron Age)",
                "reason": "Ananyino / Early Iron Age settlement site at Lugovoye (-1000..-500), separated by 2000y gap from Bronze Age phase"
            }
        ],
        "clean_names": {
            "Lugovoye Bronze Age Site-Russia": "Lugovoye (Bronze Age)",
            "Lugovoye Iron Age Site-Russia": "Lugovoye (Iron Age)"
        }
    },
    "C0670": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Luhansk Bronze Age Settlement-Ukraine",
                "new_name": "Luhansk (Bronze Age)",
                "reason": "Bronze Age / Srubnaya settlement site in the Luhanka river valley, separated by >2600y gap from modern city of Luhansk"
            }
        ],
        "clean_names": {
            "Luhans'k-Ukraine": "Luhansk",
            "Luhansk Bronze Age Settlement-Ukraine": "Luhansk (Bronze Age)"
        }
    },
    "C0674": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Lystvyn Bronze Age Site-Ukraine",
                "new_name": "Lystvyn (Bronze Age)",
                "reason": "Eneolithic / Bronze Age settlement site at Lystvyn, separated by >3800y gap from medieval Rus town"
            },
            {
                "op": "RENAME_META",
                "key": "Lystvyn-Ukraine",
                "new_name": "Lystvyn (Rus)",
                "reason": "Medieval chronicle Rus fortified settlement of Lystvyn (Listvin) [800..1200]"
            }
        ],
        "clean_names": {
            "Lystvyn Bronze Age Site-Ukraine": "Lystvyn (Bronze Age)",
            "Lystvyn-Ukraine": "Lystvyn (Rus)"
        }
    },
    "C0676": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Lyuban-Belarus_2",
                "new_name": "Lyuban (Rus)",
                "reason": "Pre-Mongol medieval Rus settlement on the Oresa River, separated by >300y gap from modern Lyuban"
            }
        ],
        "clean_names": {
            "Lyuban-Belarus": "Lyuban",
            "Lyuban-Belarus_2": "Lyuban (Rus)"
        }
    },
    "C0677": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Lyubcha-Belarus_2",
                "new_name": "Lyubcha (Rus)",
                "reason": "Pre-Mongol medieval Rus settlement and Neman river crossing, separated by >340y gap from early modern castle-town"
            }
        ],
        "clean_names": {
            "Lyubcha-Belarus": "Lyubcha",
            "Lyubcha-Belarus_2": "Lyubcha (Rus)"
        }
    },
    "C0678": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Lyubech Iron Age Site-Ukraine",
                "new_name": "Liubech (Iron Age)",
                "reason": "Early Iron Age / Zarubintsy settlement site on the Dnieper bluffs at Liubech, separated by >500y gap from continuous medieval-to-modern town"
            }
        ],
        "clean_names": {
            "Liubech-Ukraine": "Liubech",
            "Lyubech Iron Age Site-Ukraine": "Liubech (Iron Age)"
        }
    },
    "C0679": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Lyzynovka Bronze Age Settlement-Ukraine",
                "new_name": "Lizinovka (Bronze Age)",
                "reason": "Bronze Age settlement site near Lizinovka, separated by >2600y gap from modern village"
            }
        ],
        "clean_names": {
            "Lizinovka-Russia": "Lizinovka",
            "Lyzynovka Bronze Age Settlement-Ukraine": "Lizinovka (Bronze Age)"
        }
    },
    "C0682": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Makeyevka Scythian Iron Age Site-Ukraine",
                "new_name": "Makiivka (Iron Age)",
                "reason": "Scythian Iron Age settlement site (-500..0) near Makiivka"
            },
            {
                "op": "RENAME_META",
                "key": "Makeyevka Scythian-Ukraine",
                "new_name": "Makiivka (Chernyakhov)",
                "reason": "Late Roman / Chernyakhov culture settlement site (300..400) near Makiivka, separated by 300y gap from Scythian phase"
            }
        ],
        "clean_names": {
            "Makeyevka Scythian Iron Age Site-Ukraine": "Makiivka (Iron Age)",
            "Makeyevka Scythian-Ukraine": "Makiivka (Chernyakhov)"
        }
    }
}

print(f"Loaded {len(DECISIONS)} decisions so far.")

DECISIONS.update({
    "C0683": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Malopoloveckoje Bronze Age Settlement-Ukraine",
                "new_name": "Malopolovetske (Bronze Age)",
                "reason": "Bronze Age settlement site near Malopolovetske, separated by >2900y gap"
            }
        ],
        "clean_names": {
            "Malopolovetske-Ukraine": "Malopolovetske",
            "Malopoloveckoje Bronze Age Settlement-Ukraine": "Malopolovetske (Bronze Age)"
        }
    },
    "C0684": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Malorita-Belarus_2",
                "new_name": "Malorita (Rus)",
                "reason": "Pre-Mongol medieval Rus settlement in the Malorita river basin, separated by >300y gap from modern town"
            }
        ],
        "clean_names": {
            "Malorita-Belarus": "Malorita",
            "Malorita-Belarus_2": "Malorita (Rus)"
        }
    },
    "C0686": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Malyj Dubovyj Stone Age Hillfort-Ukraine",
                "new_name": "Malyj Dubovyj",
                "reason": "Distinct Stone Age site on Malyj Dubovyj ravine near Sukhachivka (Dnipro)"
            }
        ],
        "clean_names": {
            "Sukhachivka-Ukraine": "Sukhachivka",
            "Malyj Dubovyj Stone Age Hillfort-Ukraine": "Malyj Dubovyj"
        }
    },
    "C0689": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Maykop Bronze Age Site-Russia",
                "new_name": "Maykop (Bronze Age)",
                "reason": "Eponymous Early Bronze Age Maykop culture kurgan and settlement site, separated by millennia from modern Maykop"
            }
        ],
        "clean_names": {
            "Majkop-Russia": "Maykop",
            "Maykop Bronze Age Site-Russia": "Maykop (Bronze Age)"
        }
    },
    "C0690": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Arkheolohichnyy obyekt Bronze Age Settlement III-Ukraine",
                "new_name": "Rai-Oleksandrivka (Bronze Age)",
                "reason": "Bronze Age settlement site near Rai-Oleksandrivka"
            },
            {
                "op": "RENAME_META",
                "key": "Maysternya Palaeolithic Camp II-Ukraine",
                "new_name": "Maysternya (Palaeolithic)",
                "reason": "Upper Palaeolithic flint workshop and campsite with attested toponym Maysternya"
            }
        ],
        "clean_names": {
            "Arkheolohichnyy obyekt Bronze Age Settlement III-Ukraine": "Rai-Oleksandrivka (Bronze Age)",
            "Maysternya Palaeolithic Camp II-Ukraine": "Maysternya (Palaeolithic)"
        }
    },
    "C0691": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mena Iron Age Site-Ukraine",
                "new_name": "Mena (Iron Age)",
                "reason": "Early Iron Age / Yukhnovo settlement on the Mena River, separated by 500y gap from continuous medieval-to-modern town"
            }
        ],
        "clean_names": {
            "Mena-Ukraine": "Mena",
            "Mena Iron Age Site-Ukraine": "Mena (Iron Age)"
        }
    },
    "C0701": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mistse znakhodzhennya paleolitu Palaeolithic Camp II-Ukraine",
                "new_name": "Pavlivka (Palaeolithic)",
                "reason": "Upper Palaeolithic camp site near Pavlivka, separated by millennia from modern village"
            }
        ],
        "clean_names": {
            "Pavlivka-Ukraine": "Pavlivka",
            "Mistse znakhodzhennya paleolitu Palaeolithic Camp II-Ukraine": "Pavlivka (Palaeolithic)"
        }
    },
    "C0702": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mistseznakhodzhennya znakhidky Stone Age Settlement III-Ukraine",
                "new_name": "Mykolaivka (Stone Age)",
                "reason": "Stone Age / Mesolithic site near Mykolaivka, separated by millennia from modern settlement"
            }
        ],
        "clean_names": {
            "Mykolaivka_UA_05_2-Ukraine": "Mykolaivka",
            "Mistseznakhodzhennya znakhidky Stone Age Settlement III-Ukraine": "Mykolaivka (Stone Age)"
        }
    },
    "C0703": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mitagi Gorodishche-Russia",
                "new_name": "Mitagi (Early Medieval)",
                "reason": "Sasanian / Early medieval fortification (Darbant defense wall system) at Mitagi, separated by >800y gap"
            }
        ],
        "clean_names": {
            "Mitagi-Russia": "Mitagi",
            "Mitagi Gorodishche-Russia": "Mitagi (Early Medieval)"
        }
    },
    "C0707": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mugi Medieval Gorodishche-Russia",
                "new_name": "Mugi (Medieval)",
                "reason": "Medieval fortified gorodishche at Mugi (Dagestan), separated by >400y gap from later settlement"
            }
        ],
        "clean_names": {
            "Mugi-Russia": "Mugi",
            "Mugi Medieval Gorodishche-Russia": "Mugi (Medieval)"
        }
    },
    "C0708": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mukhor-Tala (stoyanka)-Russia",
                "new_name": "Mukhor-Tala (Medieval)",
                "reason": "Medieval nomadic campsite at Mukhor-Tala, separated by millennia from Palaeolithic campsite"
            },
            {
                "op": "RENAME_META",
                "key": "Mukhor-Tala VII Palaeolithic Camp-Russia",
                "new_name": "Mukhor-Tala (Palaeolithic)",
                "reason": "Upper Palaeolithic camp site Mukhor-Tala VII in the Uda River basin"
            }
        ],
        "clean_names": {
            "Mukhor-Tala (stoyanka)-Russia": "Mukhor-Tala (Medieval)",
            "Mukhor-Tala VII Palaeolithic Camp-Russia": "Mukhor-Tala (Palaeolithic)"
        }
    },
    "C0712": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mykhaylivka Neolithic Settlement-Ukraine",
                "new_name": "Mykhailivka (Neolithic)",
                "reason": "Neolithic settlement site near Mykhailivka, separated by millennia from modern town"
            }
        ],
        "clean_names": {
            "Mykhailivka-Ukraine": "Mykhailivka",
            "Mykhaylivka Neolithic Settlement-Ukraine": "Mykhailivka (Neolithic)"
        }
    },
    "C0713": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mykulyntsi-Ukraine_2",
                "new_name": "Mykulyntsi (Rus)",
                "reason": "Pre-Mongol medieval Rus chronicle town of Mikulin on the Seret River, separated by >480y gap from later town"
            }
        ],
        "clean_names": {
            "Mykulyntsi-Ukraine": "Mykulyntsi",
            "Mykulyntsi-Ukraine_2": "Mykulyntsi (Rus)"
        }
    },
    "C0715": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Efimievka Eneolithic Hillfort-Ukraine",
                "new_name": "Efimievka",
                "reason": "Cucuteni-Trypillia Eneolithic hillfort with attested toponym Efimievka (Yefymivka)"
            },
            {
                "op": "RENAME_META",
                "key": "Nadlymanske Ancient Settlement-Ukraine",
                "new_name": "Nadlymanske (Early Medieval)",
                "reason": "Early medieval Slavic / Rus settlement at Nadlymanske on the Dniester Liman"
            }
        ],
        "clean_names": {
            "Efimievka Eneolithic Hillfort-Ukraine": "Efimievka",
            "Nadlymanske Ancient Settlement-Ukraine": "Nadlymanske (Early Medieval)"
        }
    },
    "C0716": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nadvirna-Ukraine_2",
                "new_name": "Nadvirna (Rus)",
                "reason": "Pre-Mongol medieval Rus fortified settlement at Nadvirna / Pniv, separated by >280y gap from modern town"
            }
        ],
        "clean_names": {
            "Nadvirna-Ukraine": "Nadvirna",
            "Nadvirna-Ukraine_2": "Nadvirna (Rus)"
        }
    },
    "C0717": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "23.297 Palaeolithic Camp-Ukraine",
                "new_name": "Nahuievychi (Palaeolithic)",
                "reason": "Upper Palaeolithic camp site at Nahuievychi, stripped of heritage registry catalog code"
            }
        ],
        "clean_names": {
            "Nahuievychi-Ukraine": "Nahuievychi",
            "23.297 Palaeolithic Camp-Ukraine": "Nahuievychi (Palaeolithic)"
        }
    },
    "C0718": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nalchik Bronze Age Site-Russia",
                "new_name": "Nalchik (Bronze Age)",
                "reason": "Early Bronze Age kurgan and settlement site at Nalchik, separated by millennia from modern city"
            }
        ],
        "clean_names": {
            "Nal'`'cik-Russia": "Nalchik",
            "Nalchik Bronze Age Site-Russia": "Nalchik (Bronze Age)"
        }
    },
    "C0719": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Naskalnye izobrazheniya 2-Russia",
                "reason": "Turochak rock art petroglyphs on Biya river cliff misclassified in heritage registry scrape as medieval settlement with fabricated dates [800..1300]"
            }
        ],
        "clean_names": {
            "Turochak-Russia": "Turochak"
        }
    },
    "C0720": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nasyr-Kort Medieval Gorodishche-Russia",
                "new_name": "Nasyr-Kort (Medieval)",
                "reason": "Medieval Alanic fortified gorodishche at Nasyr-Kort (Ingushetia), separated by >550y gap from later aul"
            }
        ],
        "clean_names": {
            "Nasyr-Kort-Russia": "Nasyr-Kort",
            "Nasyr-Kort Medieval Gorodishche-Russia": "Nasyr-Kort (Medieval)"
        }
    },
    "C0722": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nebelivka-Ukraine_2",
                "new_name": "Nebelivka (Eneolithic)",
                "reason": "Famous Trypillia mega-site of Nebelivka, separated by millennia from modern village"
            }
        ],
        "clean_names": {
            "Nebelivka-Ukraine": "Nebelivka",
            "Nebelivka-Ukraine_2": "Nebelivka (Eneolithic)"
        }
    },
    "C0723": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nedryhailiv-Ukraine_2",
                "new_name": "Nedryhailiv (Rus)",
                "reason": "Pre-Mongol Severian / Rus fortress on the Sula River, separated by >370y gap from modern town"
            }
        ],
        "clean_names": {
            "Nedryhailiv-Ukraine": "Nedryhailiv",
            "Nedryhailiv-Ukraine_2": "Nedryhailiv (Rus)"
        }
    },
    "C0726": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nezvysko Bronze Age Site-Ukraine",
                "new_name": "Nezvysko (Bronze Age)",
                "reason": "Eneolithic Cucuteni-Trypillia and Bronze Age settlement on the Dniester at Nezvysko"
            },
            {
                "op": "RENAME_META",
                "key": "Nezvysko-Ukraine",
                "new_name": "Nezvysko (Chernyakhov)",
                "reason": "Late Roman / Chernyakhov culture settlement at Nezvysko, separated by >1800y gap from Bronze Age phase"
            }
        ],
        "clean_names": {
            "Nezvysko Bronze Age Site-Ukraine": "Nezvysko (Bronze Age)",
            "Nezvysko-Ukraine": "Nezvysko (Chernyakhov)"
        }
    },
    "C0727": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nikolskoye Cemetery Bronze Age Settlement-Ukraine",
                "new_name": "Nikolskoye (Bronze Age)",
                "reason": "Bronze Age settlement and cemetery near Nikolskoye"
            },
            {
                "op": "RENAME_META",
                "key": "Nikolskoye Neolithic Settlement-Ukraine",
                "new_name": "Nikolskoye (Neolithic)",
                "reason": "Neolithic settlement on the Dnieper Rapids at Nikolskoye, separated by >1700y gap from Bronze Age phase"
            }
        ],
        "clean_names": {
            "Nikolskoye Cemetery Bronze Age Settlement-Ukraine": "Nikolskoye (Bronze Age)",
            "Nikolskoye Neolithic Settlement-Ukraine": "Nikolskoye (Neolithic)"
        }
    },
    "C0728": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nikolskoye-Sarmatian-Russia",
                "new_name": "Nikolskoye (Sarmatian)",
                "reason": "Famous Sarmatian burial and encampment complex near Nikolskoye on the Lower Volga, separated by >1600y gap from modern village"
            }
        ],
        "clean_names": {
            "Nikol'skoje-Russia": "Nikolskoye",
            "Nikolskoye-Sarmatian-Russia": "Nikolskoye (Sarmatian)"
        }
    },
    "C0729": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nikopol Bronze Age Settlement-Ukraine",
                "new_name": "Nikopol (Bronze Age)",
                "reason": "Bronze Age settlement site on the Dnieper near Nikopol, separated by >2600y gap from modern city"
            }
        ],
        "clean_names": {
            "Nikopol'-Ukraine": "Nikopol",
            "Nikopol Bronze Age Settlement-Ukraine": "Nikopol (Bronze Age)"
        }
    },
    "C0732": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Niva 9 (poselenie)-Russia",
                "new_name": "Niva-9",
                "reason": "Medieval Sami / White Sea coastal settlement on Lake Imandra with distinct toponym Niva-9"
            }
        ],
        "clean_names": {
            "Polyarnyye Zori-Russia": "Polyarnyye Zori",
            "Niva 9 (poselenie)-Russia": "Niva-9"
        }
    },
    "C0735": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nizhnyaya Ivolga-Russia_2",
                "new_name": "Ivolga (Xiongnu)",
                "reason": "Famous Xiongnu fortress and settlement (Ivolga Gorodishche) in Buryatia, separated by >1800y gap from modern village"
            }
        ],
        "clean_names": {
            "Nizhnyaya Ivolga-Russia": "Nizhnyaya Ivolga",
            "Nizhnyaya Ivolga-Russia_2": "Ivolga (Xiongnu)"
        }
    },
    "C0736": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nosachevo Iron Age Site-Ukraine",
                "new_name": "Nosachiv (Iron Age)",
                "reason": "Early Iron Age Scythian settlement on the Tyasmyn with distinct toponym Nosachiv (Nosachevo)"
            }
        ],
        "clean_names": {
            "Rotmistrivka-Ukraine": "Rotmistrivka",
            "Nosachevo Iron Age Site-Ukraine": "Nosachiv (Iron Age)"
        }
    },
    "C0737": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nosachevo Bronze Age Site-Ukraine",
                "new_name": "Nosachiv (Bronze Age)",
                "reason": "Bronze Age settlement site at Nosachiv (-2000..-1500)"
            },
            {
                "op": "RENAME_META",
                "key": "Nosachevo-Ukraine",
                "new_name": "Nosachiv (Chernyakhov)",
                "reason": "Chernyakhov culture / Late Roman settlement at Nosachiv (300..400), separated by >1800y gap from Bronze Age phase"
            }
        ],
        "clean_names": {
            "Nosachevo Bronze Age Site-Ukraine": "Nosachiv (Bronze Age)",
            "Nosachevo-Ukraine": "Nosachiv (Chernyakhov)"
        }
    },
    "C0738": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nova Odesa Iron Age Hillfort-Ukraine",
                "new_name": "Nova Odesa (Iron Age)",
                "reason": "Early Iron Age / Scythian hillfort on the Southern Buh, separated by >1800y gap from modern Nova Odesa"
            }
        ],
        "clean_names": {
            "Nova Odesa-Ukraine": "Nova Odesa",
            "Nova Odesa Iron Age Hillfort-Ukraine": "Nova Odesa (Iron Age)"
        }
    },
    "C0739": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Novgorod-Seversky Medieval Settlement-Ukraine",
                "new_name": "Novhorod-Siverskyi (Early Medieval)",
                "reason": "Early Slavic / Severian settlement at Novhorod-Siverskyi, correcting spurious Domotkaniv metadata name"
            },
            {
                "op": "RENAME_META",
                "key": "Novgorod-Seversky Stone Age Site-Ukraine",
                "new_name": "Novhorod-Siverskyi (Stone Age)",
                "reason": "Mesolithic/Neolithic stone age site at Novhorod-Siverskyi, correcting spurious Domotkaniv metadata name"
            }
        ],
        "clean_names": {
            "Novgorod-Seversky Medieval Settlement-Ukraine": "Novhorod-Siverskyi (Early Medieval)",
            "Novgorod-Seversky Stone Age Site-Ukraine": "Novhorod-Siverskyi (Stone Age)"
        }
    },
    "C0740": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Novomoskovsk Bronze Age Settlement-Ukraine",
                "new_name": "Novomoskovsk (Bronze Age)",
                "reason": "Bronze Age / Samara river valley settlement site near Novomoskovsk, separated by >2500y gap from modern city"
            }
        ],
        "clean_names": {
            "Novomoskovs'k-Ukraine": "Novomoskovsk",
            "Novomoskovsk Bronze Age Settlement-Ukraine": "Novomoskovsk (Bronze Age)"
        }
    },
    "C0741": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Novoselovo 6 Palaeolithic Camp-Russia",
                "new_name": "Novosyolovo (Palaeolithic)",
                "reason": "Late Palaeolithic campsite Novoselovo VI on the Yenisei River, separated by millennia from modern Novosyolovo"
            }
        ],
        "clean_names": {
            "Novosjolovo-Russia": "Novosyolovo",
            "Novoselovo 6 Palaeolithic Camp-Russia": "Novosyolovo (Palaeolithic)"
        }
    },
    "C0743": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nuzal Medieval Gorodishche-Russia",
                "new_name": "Nuzal (Medieval)",
                "reason": "Medieval Alanic fortified gorodishche and chapel site at Nuzal in North Ossetia, separated by >400y gap"
            }
        ],
        "clean_names": {
            "Nuzal-Russia": "Nuzal",
            "Nuzal Medieval Gorodishche-Russia": "Nuzal (Medieval)"
        }
    },
    "C0744": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nyzhnya Syrovatka Iron Age Hillfort-Ukraine",
                "new_name": "Nyzhnya Syrovatka (Iron Age)",
                "reason": "Early Iron Age / Scythian forest-steppe hillfort on the Syrovatka River, separated by >1700y gap from modern village"
            }
        ],
        "clean_names": {
            "Nyzhnya Syrovatka-Ukraine": "Nyzhnya Syrovatka",
            "Nyzhnya Syrovatka Iron Age Hillfort-Ukraine": "Nyzhnya Syrovatka (Iron Age)"
        }
    }
})

print(f"Loaded {len(DECISIONS)} decisions so far.")

DECISIONS.update({
    "C0750": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Olkhovatka Neolithic Settlement-Ukraine",
                "new_name": "Olkhovatka (Neolithic)",
                "reason": "Neolithic settlement site near Olkhovatka, separated by millennia from modern village"
            }
        ],
        "clean_names": {
            "Olkhovatka-Ukraine": "Olkhovatka",
            "Olkhovatka Neolithic Settlement-Ukraine": "Olkhovatka (Neolithic)"
        }
    },
    "C0751": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Olkhovets 1 Neolithic Settlement-Ukraine",
                "new_name": "Vilkhovets (Neolithic)",
                "reason": "Neolithic / Trypillia settlement Olkhovets 1 near Vilkhovets, separated by >4000y gap"
            }
        ],
        "clean_names": {
            "Vilkhovets_UA_01-Ukraine": "Vilkhovets",
            "Olkhovets 1 Neolithic Settlement-Ukraine": "Vilkhovets (Neolithic)"
        }
    },
    "C0753": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Olshana Lebedyn Psyol Hillfort Complex-Ukraine",
                "new_name": "Olshana Hillfort",
                "reason": "Severian / Rus hillfort complex on the Olshanka/Psyol River near Lebedyn, separated by >350y gap"
            }
        ],
        "clean_names": {
            "Lebedyn-Ukraine": "Lebedyn",
            "Olshana Lebedyn Psyol Hillfort Complex-Ukraine": "Olshana Hillfort"
        }
    },
    "C0754": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Olshana Neolithic Settlement-Ukraine",
                "new_name": "Vilshana (Neolithic)",
                "reason": "Cucuteni-Trypillia Neolithic settlement site near Vilshana, separated by >5000y gap"
            }
        ],
        "clean_names": {
            "Vilshana-Ukraine": "Vilshana",
            "Olshana Neolithic Settlement-Ukraine": "Vilshana (Neolithic)"
        }
    },
    "C0755": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Olyshivka-Ukraine_2",
                "new_name": "Olyshivka (Rus)",
                "reason": "Pre-Mongol Severian / Rus fortified settlement on the Smolyanka River, separated by >340y gap from modern town"
            }
        ],
        "clean_names": {
            "Olyshivka-Ukraine": "Olyshivka",
            "Olyshivka-Ukraine_2": "Olyshivka (Rus)"
        }
    },
    "C0756": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Ordzhonikidze-Krym-Ukraine",
                "new_name": "Ordzhonikidze (Medieval)",
                "reason": "Medieval Genoese / Byzantine port settlement (Proveditore / Kaygador) at Dvuyakornaya Bay, separated by >390y gap"
            }
        ],
        "clean_names": {
            "Kayhador-Ukraine": "Kayhador",
            "Ordzhonikidze-Krym-Ukraine": "Ordzhonikidze (Medieval)"
        }
    },
    "C0758": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Oshmyany-Belarus_2",
                "new_name": "Oshmyany (Rus)",
                "reason": "Pre-Mongol early medieval hillfort at Starye Oshmyany, separated by >490y gap from modern town"
            }
        ],
        "clean_names": {
            "Oshmyany-Belarus": "Oshmyany",
            "Oshmyany-Belarus_2": "Oshmyany (Rus)"
        }
    },
    "C0760": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Ozaryntsi Neolithic Settlement-Ukraine",
                "new_name": "Ozaryntsi (Neolithic)",
                "reason": "Cucuteni-Trypillia Neolithic settlement site near Ozaryntsi, separated by >5400y gap"
            }
        ],
        "clean_names": {
            "Ozaryntsi-Ukraine": "Ozaryntsi",
            "Ozaryntsi Neolithic Settlement-Ukraine": "Ozaryntsi (Neolithic)"
        }
    },
    "C0762": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Paleolitychna stoyanka Kodak Palaeolithic Camp-Ukraine",
                "new_name": "Kodak (Palaeolithic)",
                "reason": "Famous Kodak Palaeolithic camp site on the Dnieper, separated by millennia from 17th-century Kodak fortress"
            }
        ],
        "clean_names": {
            "Kodak-Ukraine": "Stari Kodaky",
            "Paleolitychna stoyanka Kodak Palaeolithic Camp-Ukraine": "Kodak (Palaeolithic)"
        }
    },
    "C0763": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Paleolitychne mistse znakhodzhennya poselennya selyshche KhKh - Kh tys. do n.e. Palaeolithic Camp-Ukraine",
                "new_name": "Bilokurakyne (Palaeolithic)",
                "reason": "Upper Palaeolithic camp site near Bilokurakyne, separated by millennia from modern town"
            }
        ],
        "clean_names": {
            "Bilokurakyne-Ukraine": "Bilokurakyne",
            "Paleolitychne mistse znakhodzhennya poselennya selyshche KhKh - Kh tys. do n.e. Palaeolithic Camp-Ukraine": "Bilokurakyne (Palaeolithic)"
        }
    },
    "C0764": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pamyatky_piznoho_mezolitu 148 Mesolithic Camp-Ukraine",
                "new_name": "Petrivske (Mesolithic)",
                "reason": "Late Mesolithic campsite near Petrivske, separated by millennia from modern village"
            }
        ],
        "clean_names": {
            "Petrivske-Ukraine": "Petrivske",
            "Pamyatky_piznoho_mezolitu 148 Mesolithic Camp-Ukraine": "Petrivske (Mesolithic)"
        }
    },
    "C0766": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pamyatky_rannoho_mezolitu 114 Mesolithic Camp-Ukraine",
                "new_name": "Sabivka (Mesolithic)",
                "reason": "Early Mesolithic campsite near Sabivka, separated by millennia from modern village"
            }
        ],
        "clean_names": {
            "Sabivka-Ukraine": "Sabivka",
            "Pamyatky_rannoho_mezolitu 114 Mesolithic Camp-Ukraine": "Sabivka (Mesolithic)"
        }
    },
    "C0775": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Ancient settlement of Chernyakhov culture, Pechera-Ukraine",
                "new_name": "Pechera (Chernyakhov)",
                "reason": "Chernyakhov culture settlement on the Southern Buh at Pechera (200..420)"
            },
            {
                "op": "RENAME_META",
                "key": "Pecera Mesolithic Settlement-Ukraine",
                "new_name": "Pechera (Mesolithic)",
                "reason": "Mesolithic settlement site at Pechera (-6435..-5835), separated by millennia from Chernyakhov phase"
            }
        ],
        "clean_names": {
            "Ancient settlement of Chernyakhov culture, Pechera-Ukraine": "Pechera (Chernyakhov)",
            "Pecera Mesolithic Settlement-Ukraine": "Pechera (Mesolithic)"
        }
    },
    "C0776": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pechenihy Bronze Age Settlement-Ukraine",
                "new_name": "Pechenihy (Bronze Age)",
                "reason": "Bronze Age / Srubnaya settlement site on the Seversky Donets near Pechenihy, separated by >2500y gap"
            }
        ],
        "clean_names": {
            "Pechenihy-Ukraine": "Pechenihy",
            "Pechenihy Bronze Age Settlement-Ukraine": "Pechenihy (Bronze Age)"
        }
    },
    "C0777": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pegtymel Iron Age Site 2-Russia",
                "new_name": "Pegtymel (Late Iron Age)",
                "reason": "Late Iron Age reindeer-hunter settlement site Pegtymel II (0..100 AD)"
            },
            {
                "op": "RENAME_META",
                "key": "Pegtymel Iron Age Site-Russia",
                "new_name": "Pegtymel (Early Iron Age)",
                "reason": "Early Iron Age settlement site Pegtymel I (-700..-300 BC), separated by 300y gap"
            }
        ],
        "clean_names": {
            "Pegtymel Iron Age Site 2-Russia": "Pegtymel (Late Iron Age)",
            "Pegtymel Iron Age Site-Russia": "Pegtymel (Early Iron Age)"
        }
    },
    "C0782": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Peshany V Neolithic Settlement-Russia",
                "new_name": "Peshany-V",
                "reason": "Neolithic / Eneolithic steppe settlement site with attested toponym Peshany V near Remontnoye"
            }
        ],
        "clean_names": {
            "Remontnoye-Russia": "Remontnoye",
            "Peshany V Neolithic Settlement-Russia": "Peshany-V"
        }
    },
    "C0784": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Horodok Iron Age Hillfort-Ukraine",
                "new_name": "Horodok",
                "reason": "Early Iron Age / Yukhnovo hillfort with attested toponym Horodok near Petrushyn"
            },
            {
                "op": "RENAME_META",
                "key": "Petrushyn-Ukraine",
                "new_name": "Petrushyn",
                "reason": "Pre-Mongol Severian / Rus settlement of Petrushyn [700..1300]"
            }
        ],
        "clean_names": {
            "Horodok Iron Age Hillfort-Ukraine": "Horodok",
            "Petrushyn-Ukraine": "Petrushyn"
        }
    },
    "C0785": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Petrykau Bronze Age Settlement-Belarus",
                "new_name": "Petrikov (Bronze Age)",
                "reason": "Bronze Age settlement on the Pripyat River near Petrikov, separated by >1900y gap from medieval-to-modern town"
            }
        ],
        "clean_names": {
            "Petrikov-Belarus": "Petrikov",
            "Petrykau Bronze Age Settlement-Belarus": "Petrikov (Bronze Age)"
        }
    },
    "C0787": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Davnoruske horodyshche Rus Hillfort 7-Ukraine",
                "new_name": "Keleberda (Rus)",
                "reason": "Pre-Mongol Rus chronicle fortified settlement on the Dnieper at Keleberda"
            },
            {
                "op": "RENAME_META",
                "key": "Pilipenkova Hora Iron Age Site 2-Ukraine",
                "new_name": "Pilipenkova Hora",
                "reason": "Famous Zarubintsy / Chernyakhov hillfort on Pilipenkova Hora near Kaniv, separated by 500y gap"
            }
        ],
        "clean_names": {
            "Davnoruske horodyshche Rus Hillfort 7-Ukraine": "Keleberda (Rus)",
            "Pilipenkova Hora Iron Age Site 2-Ukraine": "Pilipenkova Hora"
        }
    },
    "C0788": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Planerskoye-Krym-Ukraine",
                "new_name": "Koktebel (Prehistoric)",
                "reason": "Eneolithic and Bronze Age settlement at the foot of Karadag near Koktebel, separated by >1700y gap from medieval-to-modern settlement"
            }
        ],
        "clean_names": {
            "Koktebel-Ukraine": "Koktebel",
            "Planerskoye-Krym-Ukraine": "Koktebel (Prehistoric)"
        }
    },
    "C0790": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Plievo Medieval Gorodishche-Russia",
                "new_name": "Plievo (Medieval)",
                "reason": "Medieval Alanic fortified gorodishche at Plievo (Ingushetia), separated by >550y gap from later aul"
            }
        ],
        "clean_names": {
            "Plievo-Russia": "Plievo",
            "Plievo Medieval Gorodishche-Russia": "Plievo (Medieval)"
        }
    },
    "C0791": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Plyskiv-Cherniavka Neolithic Settlement-Ukraine",
                "new_name": "Plyskiv (Neolithic)",
                "reason": "Linear Pottery / Trypillia Neolithic settlement site near Plyskiv, separated by millennia from modern village"
            }
        ],
        "clean_names": {
            "Plyskiv-Ukraine": "Plyskiv",
            "Plyskiv-Cherniavka Neolithic Settlement-Ukraine": "Plyskiv (Neolithic)"
        }
    },
    "C0795": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pokrovsk-Srubnaya-Russia",
                "new_name": "Pokrovsk (Bronze Age)",
                "reason": "Eponymous Pokrovsk culture / Srubnaya Bronze Age settlement (-1800..-1200)"
            },
            {
                "op": "RENAME_META",
                "key": "Pokrovsk-Steppe-Russia",
                "new_name": "Pokrovsk (Early Medieval)",
                "reason": "Sarmatian-to-Khazar era nomadic settlement and kurgan group at Pokrovsk (100..750), separated by 1300y gap from Bronze Age phase"
            }
        ],
        "clean_names": {
            "Pokrovsk-Srubnaya-Russia": "Pokrovsk (Bronze Age)",
            "Pokrovsk-Steppe-Russia": "Pokrovsk (Early Medieval)"
        }
    },
    "C0796": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pokrovskoye-Don-Russia",
                "new_name": "Pokrovskoye (Bronze Age)",
                "reason": "Srubnaya Bronze Age settlement site on the Mius River near Pokrovskoye, separated by >2900y gap from modern settlement"
            }
        ],
        "clean_names": {
            "Pokrovskoye_RU_61-Russia": "Pokrovskoye",
            "Pokrovskoye-Don-Russia": "Pokrovskoye (Bronze Age)"
        }
    },
    "C0799": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Polohy Bronze Age Settlement-Ukraine",
                "new_name": "Polohy (Bronze Age)",
                "reason": "Bronze Age settlement site on the Konka River near Polohy, separated by >2600y gap from modern city"
            }
        ],
        "clean_names": {
            "Polohy-Ukraine": "Polohy",
            "Polohy Bronze Age Settlement-Ukraine": "Polohy (Bronze Age)"
        }
    },
    "C0801": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Ponornytsia-Ukraine_2",
                "new_name": "Ponornytsia (Rus)",
                "reason": "Pre-Mongol Severian / Rus fortified settlement on the Richytsia/Desna, separated by >370y gap from modern town"
            }
        ],
        "clean_names": {
            "Ponornytsia-Ukraine": "Ponornytsia",
            "Ponornytsia-Ukraine_2": "Ponornytsia (Rus)"
        }
    },
    "C0802": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Popasna Bronze Age Settlement-Ukraine",
                "new_name": "Popasna (Bronze Age)",
                "reason": "Bronze Age settlement site near Popasna, separated by >2700y gap from modern city"
            }
        ],
        "clean_names": {
            "Popasna-Ukraine": "Popasna",
            "Popasna Bronze Age Settlement-Ukraine": "Popasna (Bronze Age)"
        }
    },
    "C0806": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Poselenie 1 u s. Repnoe-Russia",
                "new_name": "Repnoye (Rus)",
                "reason": "Early medieval Slavic / Rus settlement Poselenie 1 on the Voronezh River near Repnoye, separated by >370y gap"
            }
        ],
        "clean_names": {
            "Repnoye-Russia": "Repnoye",
            "Poselenie 1 u s. Repnoe-Russia": "Repnoye (Rus)"
        }
    },
    "C0807": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Poselenie 1 u s. Rykan-Russia",
                "new_name": "Rykan (Rus)",
                "reason": "Early medieval Slavic / Rus settlement Poselenie 1 on the Usman River near Rykan, separated by >400y gap"
            }
        ],
        "clean_names": {
            "Rykan-Russia": "Rykan",
            "Poselenie 1 u s. Rykan-Russia": "Rykan (Rus)"
        }
    },
    "C0808": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Poselenie Ayatskoe-I (sovkhoz Ayatskiy)-Russia",
                "new_name": "Ayatskoye (Medieval)",
                "reason": "Medieval Uralian / Ugric settlement Ayatskoye I on the Ayat River, separated by >370y gap from modern Ayatskoye"
            }
        ],
        "clean_names": {
            "Ayatskoye-Russia": "Ayatskoye",
            "Poselenie Ayatskoe-I (sovkhoz Ayatskiy)-Russia": "Ayatskoye (Medieval)"
        }
    }
})

print(f"Loaded {len(DECISIONS)} decisions so far.")

DECISIONS.update({
    "C0809": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Poselenie u s. Otradnoe-Russia",
                "new_name": "Otradnoye (Rus)",
                "reason": "Early medieval Slavic / Rus settlement on the Usman River near Otradnoye, separated by >370y gap"
            }
        ],
        "clean_names": {
            "Otradnoye_RU_86-Russia": "Otradnoye",
            "Poselenie u s. Otradnoe-Russia": "Otradnoye (Rus)"
        }
    },
    "C0812": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Preobrazhenie-1 Bronze Age Settlement-Russia",
                "new_name": "Preobrazheniye (Bronze Age)",
                "reason": "Primorye coastal Bronze Age settlement Preobrazheniye-1, separated by >3400y gap from modern port town"
            }
        ],
        "clean_names": {
            "Preobrazheniye-Russia": "Preobrazheniye",
            "Preobrazhenie-1 Bronze Age Settlement-Russia": "Preobrazheniye (Bronze Age)"
        }
    },
    "C0816": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pryvilne Iron Age Hillfort-Ukraine",
                "new_name": "Pryvilne (Iron Age)",
                "reason": "Early Iron Age Scythian fortified hillfort near Pryvilne (-700..-100)"
            },
            {
                "op": "RENAME_META",
                "key": "Pryvilne Migration Period Settlement-Ukraine",
                "new_name": "Pryvilne (Migration Period)",
                "reason": "Migration Period / Early Slavic settlement at Pryvilne (250..700), separated by 350y gap from Iron Age phase"
            }
        ],
        "clean_names": {
            "Pryvilne Iron Age Hillfort-Ukraine": "Pryvilne (Iron Age)",
            "Pryvilne Migration Period Settlement-Ukraine": "Pryvilne (Migration Period)"
        }
    },
    "C0817": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pshada Bronze Age Site-Russia",
                "new_name": "Pshada (Bronze Age)",
                "reason": "Famous Black Sea coast megalithic dolmen and Bronze Age settlement complex in Pshada valley, separated by millennia from modern village"
            }
        ],
        "clean_names": {
            "Pshada-Russia": "Pshada",
            "Pshada Bronze Age Site-Russia": "Pshada (Bronze Age)"
        }
    },
    "C0819": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kamyanska Sloboda Stone Age Hillfort-Ukraine",
                "new_name": "Kamianska Sloboda (Stone Age)",
                "reason": "Mesolithic site on the high Desna terrace near Kamianska Sloboda"
            },
            {
                "op": "RENAME_META",
                "key": "Pushkari I Iron Age Site 2-Ukraine",
                "new_name": "Pushkari (Iron Age)",
                "reason": "Early Iron Age / Roman era settlement on famous Pushkari archaeological promontory, separated by millennia from Stone Age phase"
            }
        ],
        "clean_names": {
            "Kamyanska Sloboda Stone Age Hillfort-Ukraine": "Kamianska Sloboda (Stone Age)",
            "Pushkari I Iron Age Site 2-Ukraine": "Pushkari (Iron Age)"
        }
    },
    "C0820": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Radul-Ukraine_2",
                "new_name": "Radul (Rus)",
                "reason": "Pre-Mongol Rus Dnieper river port settlement, separated by >300y gap from modern town"
            }
        ],
        "clean_names": {
            "Radul-Ukraine": "Radul",
            "Radul-Ukraine_2": "Radul (Rus)"
        }
    },
    "C0822": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Ratlub Medieval Gorodishche-Russia",
                "new_name": "Ratlub (Medieval)",
                "reason": "Medieval Dagestani fortified gorodishche at Ratlub (Shamil district), separated by >420y gap from later aul"
            }
        ],
        "clean_names": {
            "Ratlub-Russia": "Ratlub",
            "Ratlub Medieval Gorodishche-Russia": "Ratlub (Medieval)"
        }
    },
    "C0823": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Retezh Krolevets Forest-Steppe Hillfort-Ukraine",
                "new_name": "Retezh",
                "reason": "Severian / Rus forest-steppe hillfort with distinct attested toponym Retezh (Retizh), separated by >300y gap from Krolevets"
            }
        ],
        "clean_names": {
            "Krolevets-Ukraine": "Krolevets",
            "Retezh Krolevets Forest-Steppe Hillfort-Ukraine": "Retezh"
        }
    },
    "C0825": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Revna-Snov Northern Forest Hillfort Iron Age Site-Ukraine",
                "new_name": "Revna (Iron Age)",
                "reason": "Early Iron Age / Yukhnovo forest hillfort on the Revna River (-500..0)"
            },
            {
                "op": "RENAME_META",
                "key": "Revna-Snov Northern Forest Hillfort-Ukraine",
                "new_name": "Revna (Rus)",
                "reason": "Pre-Mongol Rus fortified settlement on the Revna River (700..1300), separated by 700y gap from Iron Age phase"
            }
        ],
        "clean_names": {
            "Revna-Snov Northern Forest Hillfort Iron Age Site-Ukraine": "Revna (Iron Age)",
            "Revna-Snov Northern Forest Hillfort-Ukraine": "Revna (Rus)"
        }
    },
    "C0827": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Rim-Gora Iron Age Site-Russia",
                "new_name": "Rim-Gora (Iron Age)",
                "reason": "Koban culture Early Iron Age settlement on the Rim-Gora fortress plateau (-800..-200)"
            },
            {
                "op": "RENAME_META",
                "key": "Rim-Gora-Russia",
                "new_name": "Rim-Gora (Medieval)",
                "reason": "Major medieval Alanic capital fortress town on Rim-Gora (450..1200), separated by 650y gap from Koban phase"
            }
        ],
        "clean_names": {
            "Rim-Gora Iron Age Site-Russia": "Rim-Gora (Iron Age)",
            "Rim-Gora-Russia": "Rim-Gora (Medieval)"
        }
    },
    "C0828": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Ripky-Ukraine_2",
                "new_name": "Ripky (Rus)",
                "reason": "Pre-Mongol Severian / Rus settlement on the Zamglai bog margin, separated by >280y gap from modern town"
            }
        ],
        "clean_names": {
            "Ripky-Ukraine": "Ripky",
            "Ripky-Ukraine_2": "Ripky (Rus)"
        }
    },
    "C0833": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Rostovka-Russia_2",
                "new_name": "Rostovka (Bronze Age)",
                "reason": "World-renowned Seima-Turbino Bronze Age necropolis and settlement on the Om River, separated by >3100y gap from modern Rostovka"
            }
        ],
        "clean_names": {
            "Rostovka-Russia": "Rostovka",
            "Rostovka-Russia_2": "Rostovka (Bronze Age)"
        }
    },
    "C0834": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Rovnoye-Russia_2",
                "new_name": "Rovnoye (Early Medieval)",
                "reason": "Early medieval Sarmatian / Khazar settlement on the Volga at Rovnoye (Seelmann), separated by >860y gap from modern town"
            }
        ],
        "clean_names": {
            "Rovnoye-Russia": "Rovnoye",
            "Rovnoye-Russia_2": "Rovnoye (Early Medieval)"
        }
    },
    "C0836": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Rugudja Bronze Age Site-Russia",
                "new_name": "Rugudzha (Bronze Age)",
                "reason": "Neolithic / Early Bronze Age mountain settlement site at Rugudzha (-6000..-3000)"
            },
            {
                "op": "RENAME_META",
                "key": "Rugudja Medieval Gorodishche-Russia",
                "new_name": "Rugudzha (Medieval)",
                "reason": "Medieval fortified gorodishche at Rugudzha (1100..1280), separated by millennia from prehistoric phase"
            }
        ],
        "clean_names": {
            "Rugudja Bronze Age Site-Russia": "Rugudzha (Bronze Age)",
            "Rugudja Medieval Gorodishche-Russia": "Rugudzha (Medieval)"
        }
    },
    "C0838": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Rusakova (arkhealagichny pomnik)-Belarus",
                "new_name": "Rusakovo (Rus)",
                "reason": "Pre-Mongol medieval Rus settlement on the Shchara River at Rusakovo (800..1300)"
            },
            {
                "op": "RENAME_META",
                "key": "Rusakovo-Belarus",
                "new_name": "Rusakovo (Bronze Age)",
                "reason": "Late Bronze Age Lusatian-influenced settlement site at Rusakovo (-1200..-900), separated by 1700y gap"
            }
        ],
        "clean_names": {
            "Rusakova (arkhealagichny pomnik)-Belarus": "Rusakovo (Rus)",
            "Rusakovo-Belarus": "Rusakovo (Bronze Age)"
        }
    },
    "C0839": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Rymska_imperiya_ta_plemena_davnoyi_Ukrayiny 899 Classical Polis-Ukraine",
                "new_name": "Starobilsk (Classical)",
                "reason": "Classical antiquity / Sarmatian settlement on the Aidar River near Starobilsk, separated by >1200y gap from modern city"
            }
        ],
        "clean_names": {
            "Starobilsk-Ukraine": "Starobilsk",
            "Rymska_imperiya_ta_plemena_davnoyi_Ukrayiny 899 Classical Polis-Ukraine": "Starobilsk (Classical)"
        }
    },
    "C0843": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Davnoruske horodyshche - Chernyakhivske poselennya na Porossi Chernyakhov Hillfort-Ukraine",
                "new_name": "Sukholisy (Chernyakhov)",
                "reason": "Chernyakhov culture hillfort on the Ros River near Sukholisy (200..420)"
            },
            {
                "op": "RENAME_META",
                "key": "Sakkov-Ukraine",
                "new_name": "Sakkov",
                "reason": "Pre-Mongol chronicle Rus fortified border fortress-town of Sakkov on the Porossya defensive line (1100..1300), separated by 680y gap"
            }
        ],
        "clean_names": {
            "Davnoruske horodyshche - Chernyakhivske poselennya na Porossi Chernyakhov Hillfort-Ukraine": "Sukholisy (Chernyakhov)",
            "Sakkov-Ukraine": "Sakkov"
        }
    },
    "C0845": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Samus IV-Russia",
                "new_name": "Samus-IV",
                "reason": "Eponymous Bronze Age Samus culture settlement and bronze-casting centre Samus IV on the Tom River, separated by millennia from modern Samus"
            }
        ],
        "clean_names": {
            "Samus'-Russia": "Samus",
            "Samus IV-Russia": "Samus-IV"
        }
    },
    "C0847": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Sarovskoe gorodishche-Russia",
                "new_name": "Sarovskoe Gorodishche",
                "reason": "Pre-Mongol Mordvin and Rus fortified gorodishche at the confluence of Satis and Sarovka, separated by >450y gap from modern Sarov"
            }
        ],
        "clean_names": {
            "Sarov-Russia": "Sarov",
            "Sarovskoe gorodishche-Russia": "Sarovskoe Gorodishche"
        }
    },
    "C0848": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kizinka-Russia",
                "new_name": "Kizinka",
                "reason": "Major dolmen city and Bronze Age settlement in the Kizinka River basin"
            },
            {
                "op": "RENAME_META",
                "key": "Satanay-Russia",
                "new_name": "Satanay",
                "reason": "Famous Upper Palaeolithic / Mesolithic rockshelter (Naves Satanay / Gubsky Naves 7), separated by millennia from Bronze Age Kizinka"
            }
        ],
        "clean_names": {
            "Kizinka-Russia": "Kizinka",
            "Satanay-Russia": "Satanay"
        }
    },
    "C0851": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Saygatino Iron Age Site-Russia",
                "new_name": "Saygatino (Iron Age)",
                "reason": "Kulika culture Early Iron Age settlement on the Ob River at Saygatino (-200..200)"
            },
            {
                "op": "RENAME_META",
                "key": "Saygatino-Russia",
                "new_name": "Saygatino (Medieval)",
                "reason": "Medieval Ob-Ugric fortified settlement at Saygatino (800..1200), separated by 600y gap from Iron Age phase"
            }
        ],
        "clean_names": {
            "Saygatino Iron Age Site-Russia": "Saygatino (Iron Age)",
            "Saygatino-Russia": "Saygatino (Medieval)"
        }
    },
    "C0856": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Selishcha peryyadu rannyaga zhaleznaga veku-Belarus",
                "new_name": "Nosovichi (Iron Age)",
                "reason": "Early Iron Age / Milograd-Zarubintsy archaeological settlement at Nosovichi (Gomel Oblast), separated by >300y gap from modern village"
            }
        ],
        "clean_names": {
            "Nosovichi-Belarus": "Nosovichi",
            "Selishcha peryyadu rannyaga zhaleznaga veku-Belarus": "Nosovichi (Iron Age)"
        }
    },
    "C0860": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Selishche Naro-Fominsk (Naro-Fominsk)-Russia",
                "new_name": "Naro-Fominsk (Rus)",
                "reason": "Pre-Mongol medieval Rus unfortified settlement (selishche) on the Nara River, separated by >600y gap from modern Naro-Fominsk"
            }
        ],
        "clean_names": {
            "Naro-Fominsk-Russia": "Naro-Fominsk",
            "Selishche Naro-Fominsk (Naro-Fominsk)-Russia": "Naro-Fominsk (Rus)"
        }
    },
    "C0863": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Selitrennoye Gord-Russia",
                "new_name": "Selitrennoye Gorodishche",
                "reason": "Pre-Mongol / Golden Horde fortified capital site (Sarai / Selitrennoye gorodishche) on the Akhtuba, separated by >470y gap from modern village"
            }
        ],
        "clean_names": {
            "Selitrennoye-Russia": "Selitrennoye",
            "Selitrennoye Gord-Russia": "Selitrennoye Gorodishche"
        }
    },
    "C0864": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Daroshavichy Stone Age Settlement-Belarus",
                "new_name": "Daroshavichy",
                "reason": "Mesolithic settlement on the Pripyat River with distinct attested toponym Daroshavichy (Doroshevichi)"
            },
            {
                "op": "RENAME_META",
                "key": "Selyuki Mediaeval Hillfort-Belarus",
                "new_name": "Selyuki",
                "reason": "Pre-Mongol medieval Rus hillfort with distinct attested toponym Selyuki, separated by millennia from Stone Age site"
            }
        ],
        "clean_names": {
            "Daroshavichy Stone Age Settlement-Belarus": "Daroshavichy",
            "Selyuki Mediaeval Hillfort-Belarus": "Selyuki"
        }
    },
    "C0865": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Semender Khazar Capital-Russia",
                "new_name": "Semender (Khazar Capital)",
                "reason": "Historic early capital of the Khazar Khaganate (Samandar / Tarki gorodishche), separated by >640y gap from early modern-to-contemporary town"
            }
        ],
        "clean_names": {
            "Semender-Russia": "Semender",
            "Semender Khazar Capital-Russia": "Semender (Khazar Capital)"
        }
    },
    "C0866": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Semenivka Eneolithic Hillfort-Ukraine",
                "new_name": "Semenivka (Eneolithic)",
                "reason": "Cucuteni-Trypillia Eneolithic hillfort near Semenivka (-4500..-3000)"
            },
            {
                "op": "RENAME_META",
                "key": "Semenovka Classical Polis-Ukraine",
                "new_name": "Semenivka (Classical)",
                "reason": "Classical Greek / Scythian polis settlement at Semenivka (-500..400), separated by 2500y gap from Eneolithic phase"
            }
        ],
        "clean_names": {
            "Semenivka Eneolithic Hillfort-Ukraine": "Semenivka (Eneolithic)",
            "Semenovka Classical Polis-Ukraine": "Semenivka (Classical)"
        }
    },
    "C0867": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Semiluki Hillfort-Russia",
                "new_name": "Semiluki Hillfort",
                "reason": "Early medieval Slavic / Borshevo culture hillfort on the Don River, separated by >370y gap from modern Semiluki"
            }
        ],
        "clean_names": {
            "Semiluki-Russia": "Semiluki",
            "Semiluki Hillfort-Russia": "Semiluki Hillfort"
        }
    },
    "C0870": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Severka rock paintings-Russia",
                "reason": "Severskaya Pisanitsa cliff rock art paintings misclassified in heritage registry scrape as medieval settlement with fabricated dates [800..1300]"
            }
        ],
        "clean_names": {
            "Severka-Russia": "Severka"
        }
    },
    "C0871": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Severynivka Iron Age Site-Ukraine",
                "new_name": "Severynivka (Iron Age)",
                "reason": "Major Scythian fortified hillfort of the forest-steppe on the Rov River at Severynivka (-500..0)"
            },
            {
                "op": "RENAME_META",
                "key": "Severynivka-Ukraine",
                "new_name": "Severynivka (Chernyakhov)",
                "reason": "Chernyakhov culture / Late Roman settlement at Severynivka (300..400), separated by 300y gap from Scythian phase"
            }
        ],
        "clean_names": {
            "Severynivka Iron Age Site-Ukraine": "Severynivka (Iron Age)",
            "Severynivka-Ukraine": "Severynivka (Chernyakhov)"
        }
    }
})

print(f"Total DECISIONS configured: {len(DECISIONS)}")

# Validation and output writing
output_records = []
input_cluster_ids = [c['cluster_id'] for c in clusters]

assert len(DECISIONS) == len(input_cluster_ids) == 130

drop_count = 0
rename_count = 0
merge_count = 0

for c in clusters:
    cid = c['cluster_id']
    assert cid in DECISIONS, f"Missing decision for {cid}"
    d = DECISIONS[cid]
    
    # Check nodes vs clean_names and dropped keys
    node_keys = {n['key'] for n in c['nodes']}
    dropped_keys = {act['key'] for act in d['actions'] if act['op'] == 'DROP_JUNK'}
    merged_source_keys = {act['source_key'] for act in d['actions'] if act['op'] == 'MERGE'}
    surviving_keys = node_keys - dropped_keys - merged_source_keys
    
    # Check that clean_names exactly has surviving_keys
    assert set(d['clean_names'].keys()) == surviving_keys, f"clean_names keys mismatch in {cid}: {set(d['clean_names'].keys())} vs {surviving_keys}"
    
    # Check no duplicate clean names
    names = list(d['clean_names'].values())
    assert len(names) == len(set(names)), f"Duplicate clean_names in {cid}: {names}"
    
    for act in d['actions']:
        if act['op'] == 'DROP_JUNK':
            drop_count += 1
        elif act['op'] == 'RENAME_META':
            rename_count += 1
        elif act['op'] == 'MERGE':
            merge_count += 1
        else:
            raise ValueError(f"Unknown op {act['op']}")
            
    output_records.append({
        "cluster_id": cid,
        "actions": d["actions"],
        "clean_names": d["clean_names"]
    })

assert len(output_records) == 130

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(output_records, f, indent=2, ensure_ascii=False)

print(f"Successfully wrote {len(output_records)} records to {OUTPUT_PATH}")
print(f"Counts: RENAME_META={rename_count}, DROP_JUNK={drop_count}, MERGE={merge_count}")
