# Part D: Clusters C0088 to C0129 (31 clusters)

PART_D = {
    "C0088": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Gorgippia-Russia",
                "target_key": "Gorgippia-Anapa-Russia",
                "reason": "Duplicate node of ancient Bosporan city Gorgippia at modern Anapa"
            },
            {
                "op": "MERGE",
                "source_key": "Gorgippia Iron Age Site-Russia",
                "target_key": "Gorgippia-Anapa-Russia",
                "reason": "Duplicate scrape of Sindike and Gorgippia archaeological site"
            },
            {
                "op": "RENAME_META",
                "key": "Gorgippia-Anapa-Russia",
                "new_name": "Gorgippia",
                "reason": "Ancient Bosporan trade city and port of Gorgippia at Anapa"
            }
        ],
        "clean_names": {
            "Gorgippia-Anapa-Russia": "Gorgippia"
        }
    },
    "C0093": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Hoty 1021 Chernyakhov Hillfort-Ukraine",
                "target_key": "Bashmachka-Ukraine",
                "reason": "Duplicate scrape of fortified Chernyakhov citadel at Bashmachka"
            },
            {
                "op": "RENAME_META",
                "key": "Bashmachka-Ukraine",
                "new_name": "Bashmachka (Chernyakhov)",
                "reason": "Famous Chernyakhov-culture stone-built citadel and fortress on Dnieper"
            },
            {
                "op": "RENAME_META",
                "key": "Hill fort in Bashmachka-Ukraine",
                "new_name": "Bashmachka (Medieval)",
                "reason": "Early medieval Slavic hillfort at Bashmachka"
            }
        ],
        "clean_names": {
            "Bashmachka-Ukraine": "Bashmachka (Chernyakhov)",
            "Hill fort in Bashmachka-Ukraine": "Bashmachka (Medieval)"
        }
    },
    "C0095": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Ivye-Belarus",
                "target_key": "Iwye-Belarus",
                "reason": "Early medieval Gavya settlement continuous within 100-year gap of Iwye"
            },
            {
                "op": "MERGE",
                "source_key": "Chyrvonaya Gorka Hillfort-Belarus",
                "target_key": "Iwye-Belarus",
                "reason": "Chyrvonaya Gorka medieval hillfort continuous with settlement history of Iwye"
            }
        ],
        "clean_names": {
            "Iwye-Belarus": "Iwye"
        }
    },
    "C0097": {
        "actions": [
            {
                "op": "KEEP_HOMONYM",
                "key": "Kamenka-Russia",
                "reason": "Distinct modern town in Penza Oblast"
            },
            {
                "op": "KEEP_HOMONYM",
                "key": "Kamenka-Russia_2",
                "reason": "Distinct settlement in Primorsky Krai 6399 km to the east"
            },
            {
                "op": "KEEP_HOMONYM",
                "key": "Kamenka-Russia_2_2",
                "reason": "Distinct historic Volga German colony Bähr / Kamenka in Saratov region 306 km away"
            }
        ],
        "clean_names": {
            "Kamenka-Russia": "Kamenka",
            "Kamenka-Russia_2": "Kamenka",
            "Kamenka-Russia_2_2": "Kamenka"
        }
    },
    "C0098": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Kamennomostskoye-Russia_2",
                "target_key": "Kamennomostskoye-Russia",
                "reason": "Historic Karmovo village continuous with Kamennomostskoye modern settlement series"
            },
            {
                "op": "RENAME_META",
                "key": "Kamennomostskoye Bronze Age Site-Russia",
                "new_name": "Kamennomostskoye (Bronze Age)",
                "reason": "Pre-hiatus Koban Bronze Age settlement site at Kamennomostskoye"
            }
        ],
        "clean_names": {
            "Kamennomostskoye-Russia": "Kamennomostskoye",
            "Kamennomostskoye Bronze Age Site-Russia": "Kamennomostskoye (Bronze Age)"
        }
    },
    "C0099": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kamin-1 Iron Age Hillfort-Ukraine",
                "new_name": "Kamin 1",
                "reason": "Numbered Yukhnovo culture Iron Age hillfort site 1 at Kamin"
            },
            {
                "op": "RENAME_META",
                "key": "Kamin-2 Iron Age Hillfort-Ukraine",
                "new_name": "Kamin 2",
                "reason": "Numbered Yukhnovo culture Iron Age hillfort site 2 at Kamin"
            },
            {
                "op": "RENAME_META",
                "key": "Kamin-3 Bronze Age Settlement-Ukraine",
                "new_name": "Kamin 3",
                "reason": "Numbered Sosnitsa Bronze Age settlement site 3 at Kamin"
            }
        ],
        "clean_names": {
            "Kamin-1 Iron Age Hillfort-Ukraine": "Kamin 1",
            "Kamin-2 Iron Age Hillfort-Ukraine": "Kamin 2",
            "Kamin-3 Bronze Age Settlement-Ukraine": "Kamin 3"
        }
    },
    "C0101": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Katanda Iron Age Site 2-Russia",
                "target_key": "Katanda-Russia",
                "reason": "Iron Age cultural layer continuous with Katanda valley settlement series"
            },
            {
                "op": "RENAME_META",
                "key": "Katanda Iron Age Site-Russia",
                "new_name": "Katanda (Iron Age)",
                "reason": "Pazyryk culture Iron Age kurgan and settlement site at Katanda"
            }
        ],
        "clean_names": {
            "Katanda-Russia": "Katanda",
            "Katanda Iron Age Site-Russia": "Katanda (Iron Age)"
        }
    },
    "C0102": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Demidov Eneolithic Hillfort-Ukraine",
                "new_name": "Demydiv (Trypillia)",
                "reason": "Trypillia-culture Eneolithic fortified settlement at Demydiv on Irpin river"
            },
            {
                "op": "RENAME_META",
                "key": "Kazarovichi 1 Eneolithic Hillfort-Ukraine",
                "new_name": "Kozarovychi (Trypillia)",
                "reason": "Trypillia-culture Eneolithic settlement at Kozarovychi on Kyiv Reservoir"
            },
            {
                "op": "RENAME_META",
                "key": "Hoty 1026 Chernyakhov Settlement-Ukraine",
                "new_name": "Kozarovychi (Chernyakhov)",
                "reason": "Chernyakhov culture settlement site at Kozarovychi"
            }
        ],
        "clean_names": {
            "Demidov Eneolithic Hillfort-Ukraine": "Demydiv (Trypillia)",
            "Kazarovichi 1 Eneolithic Hillfort-Ukraine": "Kozarovychi (Trypillia)",
            "Hoty 1026 Chernyakhov Settlement-Ukraine": "Kozarovychi (Chernyakhov)"
        }
    },
    "C0103": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kharachoy Bronze Age Site 2-Russia",
                "new_name": "Kharachoy (Late Bronze Age)",
                "reason": "Kayakent-Khorochoi Late Bronze Age type-site phase 2"
            },
            {
                "op": "RENAME_META",
                "key": "Kharachoy Bronze Age Site-Russia",
                "new_name": "Kharachoy (Bronze Age)",
                "reason": "Middle Bronze Age settlement site at Kharachoy"
            }
        ],
        "clean_names": {
            "Kharachoy-Russia": "Kharachoy",
            "Kharachoy Bronze Age Site 2-Russia": "Kharachoy (Late Bronze Age)",
            "Kharachoy Bronze Age Site-Russia": "Kharachoy (Bronze Age)"
        }
    },
    "C0104": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Belgorod Medieval Gorodishche-Russia",
                "new_name": "Belgorod (Medieval)",
                "reason": "Early medieval Romny-period and Old Rus gorodishche with >340-year hiatus to modern fortress city"
            },
            {
                "op": "RENAME_META",
                "key": "Khitrovka-Russia",
                "new_name": "Khitrovka",
                "reason": "Distinct early medieval settlement at Khitrovka on Seversky Donets"
            }
        ],
        "clean_names": {
            "Belgorod-Russia": "Belgorod",
            "Belgorod Medieval Gorodishche-Russia": "Belgorod (Medieval)",
            "Khitrovka-Russia": "Khitrovka"
        }
    },
    "C0105": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Great Khodosivka hill fort-Ukraine",
                "target_key": "Khodosivka-Ukraine",
                "reason": "Great Khodosivka hillfort overlapping continuous medieval settlement of Khodosivka"
            },
            {
                "op": "RENAME_META",
                "key": "Khodosivka Iron Age Site-Ukraine",
                "new_name": "Khodosivka (Iron Age)",
                "reason": "Pre-hiatus Roman-period / Chernyakhov settlement site at Khodosivka"
            }
        ],
        "clean_names": {
            "Khodosivka-Ukraine": "Khodosivka",
            "Khodosivka Iron Age Site-Ukraine": "Khodosivka (Iron Age)"
        }
    },
    "C0106": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Khumara-Russia_2",
                "target_key": "Khumara Medieval Gorodishche-Russia",
                "reason": "Duplicate node of early medieval Khumarinskoe gorodishche"
            },
            {
                "op": "RENAME_META",
                "key": "Khumara Medieval Gorodishche-Russia",
                "new_name": "Khumara (Medieval)",
                "reason": "Famous early medieval Saltovo-Khazar stone fortress on Kuban river with >500-year hiatus to modern aul"
            }
        ],
        "clean_names": {
            "Khumara-Russia": "Khumara",
            "Khumara Medieval Gorodishche-Russia": "Khumara (Medieval)"
        }
    },
    "C0107": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Klimavichy Mediaeval Hillfort-Belarus",
                "target_key": "Klimovichi-Belarus_2",
                "reason": "Duplicate coordinate scrape of early medieval Old Rus fortified settlement at Klimavichy"
            },
            {
                "op": "RENAME_META",
                "key": "Klimovichi-Belarus_2",
                "new_name": "Klimovichi (Rus)",
                "reason": "Old Rus Ostyor basin medieval fortified settlement with >250-year hiatus to modern town"
            }
        ],
        "clean_names": {
            "Klimavicy-Belarus": "Klimovichi",
            "Klimovichi-Belarus_2": "Klimovichi (Rus)"
        }
    },
    "C0108": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Klin-Yar-Russia",
                "new_name": "Klin-Yar (Early Medieval)",
                "reason": "Early medieval Alanic fortified settlement and cemetery at Klin-Yar"
            },
            {
                "op": "RENAME_META",
                "key": "Klin-Yar Iron Age Site 2-Russia",
                "new_name": "Klin-Yar (Sarmatian)",
                "reason": "Sarmatian-era settlement and cemetery phase at Klin-Yar"
            },
            {
                "op": "RENAME_META",
                "key": "Klin-Yar Iron Age Site-Russia",
                "new_name": "Klin-Yar (Iron Age)",
                "reason": "Koban culture Late Bronze and Early Iron Age settlement phase at Klin-Yar"
            }
        ],
        "clean_names": {
            "Klin-Yar-Russia": "Klin-Yar (Early Medieval)",
            "Klin-Yar Iron Age Site 2-Russia": "Klin-Yar (Sarmatian)",
            "Klin-Yar Iron Age Site-Russia": "Klin-Yar (Iron Age)"
        }
    },
    "C0109": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Klishchiv-Ukraine",
                "new_name": "Klishchiv (Iron Age)",
                "reason": "Scythian Early Iron Age settlement on Southern Bug at Klishchiv"
            },
            {
                "op": "RENAME_META",
                "key": "Klishchiv Bronze Age Site-Ukraine",
                "new_name": "Klishchiv (Trypillia)",
                "reason": "Eneolithic Trypillia culture settlement site at Klishchiv"
            },
            {
                "op": "RENAME_META",
                "key": "KliAciv Neolithic Settlement-Ukraine",
                "new_name": "Klishchiv (Neolithic)",
                "reason": "Neolithic settlement site near Klishchiv"
            }
        ],
        "clean_names": {
            "Klishchiv-Ukraine": "Klishchiv (Iron Age)",
            "Klishchiv Bronze Age Site-Ukraine": "Klishchiv (Trypillia)",
            "KliAciv Neolithic Settlement-Ukraine": "Klishchiv (Neolithic)"
        }
    },
    "C0110": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Kobyakovo Gorodishche Iron Age Site-Russia",
                "target_key": "Kobyakovo Gorodishche-Russia",
                "reason": "Duplicate Iron Age phase within continuous Kobyakovo gorodishche sequence"
            },
            {
                "op": "RENAME_META",
                "key": "Kobyakovo Gorodishche-Russia",
                "new_name": "Kobyakovo",
                "reason": "Famous multi-period Meotian and medieval hillfort on Don river"
            },
            {
                "op": "RENAME_META",
                "key": "Kislyakovskoye-Russia",
                "new_name": "Kislyakovskoye",
                "reason": "Distinct Meotian fortified settlement on Don river near Aksay"
            }
        ],
        "clean_names": {
            "Kobyakovo Gorodishche-Russia": "Kobyakovo",
            "Kislyakovskoye-Russia": "Kislyakovskoye"
        }
    },
    "C0111": {
        "actions": [
            {
                "op": "KEEP_HOMONYM",
                "key": "Komariv-Ukraine",
                "reason": "Distinct modern village in Kelmentsi Raion, Chernivtsi Oblast 181 km away on Dniester"
            },
            {
                "op": "RENAME_META",
                "key": "Komariv Bronze Age Site-Ukraine",
                "new_name": "Komariv (Bronze Age)",
                "reason": "World-famous Komariv culture Middle Bronze Age type-site in Ivano-Frankivsk Oblast"
            },
            {
                "op": "RENAME_META",
                "key": "Komariv-Ukraine_2",
                "new_name": "Komariv (Roman Period)",
                "reason": "Famous Roman-era glass-manufacturing settlement and workshop at Komariv"
            }
        ],
        "clean_names": {
            "Komariv-Ukraine": "Komariv",
            "Komariv Bronze Age Site-Ukraine": "Komariv (Bronze Age)",
            "Komariv-Ukraine_2": "Komariv (Roman Period)"
        }
    },
    "C0112": {
        "actions": [
            {
                "op": "KEEP_HOMONYM",
                "key": "Konstantinovskoye-Russia",
                "reason": "Distinct settlement in Stavropol Krai 280 km away"
            },
            {
                "op": "RENAME_META",
                "key": "Konstantinovskoye-Russia_2",
                "new_name": "Konstantinovsk (Eneolithic)",
                "reason": "Famous Konstantinovskoye Eneolithic settlement on Lower Don"
            }
        ],
        "clean_names": {
            "Konstantinovsk-Russia": "Konstantinovsk",
            "Konstantinovskoye-Russia": "Konstantinovskoye",
            "Konstantinovskoye-Russia_2": "Konstantinovsk (Eneolithic)"
        }
    },
    "C0113": {
        "actions": [
            {
                "op": "KEEP_HOMONYM",
                "key": "Gorodishche-Russia",
                "reason": "Distinct modern urban locality in Volgograd Oblast 1022 km away"
            },
            {
                "op": "MERGE",
                "source_key": "Gorodishche-Russia_2",
                "target_key": "Kostroma-Russia",
                "reason": "Old Kostroma / Gorodishche early medieval fortified centre continuous with Kostroma"
            }
        ],
        "clean_names": {
            "Kostroma-Russia": "Kostroma",
            "Gorodishche-Russia": "Gorodishche"
        }
    },
    "C0114": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kotelva II Iron Age Hillfort-Ukraine",
                "new_name": "Kotelva II",
                "reason": "Numbered Scythian-era Iron Age hillfort site II at Kotelva"
            },
            {
                "op": "RENAME_META",
                "key": "Kotelevske horodyshche Iron Age Hillfort-Ukraine",
                "new_name": "Kotelevske",
                "reason": "Major Scythian-era fortified centre Kotelevske horodyshche on Vorskla river"
            }
        ],
        "clean_names": {
            "Kotelva-Ukraine": "Kotelva",
            "Kotelva II Iron Age Hillfort-Ukraine": "Kotelva II",
            "Kotelevske horodyshche Iron Age Hillfort-Ukraine": "Kotelevske"
        }
    },
    "C0115": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Horodyshche Hillfort 3-Ukraine",
                "new_name": "Kovchyn (Rus)",
                "reason": "Old Rus medieval hillfort on Desna river near Kovchyn"
            },
            {
                "op": "RENAME_META",
                "key": "Bor Bronze Age Hillfort-Ukraine",
                "new_name": "Bor (Kovchyn)",
                "reason": "Bronze Age fortified settlement at Bor near Kovchyn"
            },
            {
                "op": "RENAME_META",
                "key": "Kovchyn-3 Bronze Age Settlement-Ukraine",
                "new_name": "Kovchyn 3",
                "reason": "Numbered Sosnitsa Bronze Age settlement site 3 at Kovchyn"
            }
        ],
        "clean_names": {
            "Horodyshche Hillfort 3-Ukraine": "Kovchyn (Rus)",
            "Bor Bronze Age Hillfort-Ukraine": "Bor (Kovchyn)",
            "Kovchyn-3 Bronze Age Settlement-Ukraine": "Kovchyn 3"
        }
    },
    "C0116": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Kozyrka XII-Ukraine",
                "target_key": "Kozyrka-Ukraine",
                "reason": "Late Scythian and Roman-era fortified outpost of Olbian chora at Kozyrka"
            },
            {
                "op": "RENAME_META",
                "key": "Kozirske gorodishche-Ukraine",
                "new_name": "Kozyrka (Medieval)",
                "reason": "Early medieval Slavic hillfort on Bug Liman at Kozyrka"
            }
        ],
        "clean_names": {
            "Kozyrka-Ukraine": "Kozyrka",
            "Kozirske gorodishche-Ukraine": "Kozyrka (Medieval)"
        }
    },
    "C0117": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Gnidava-Ukraine",
                "new_name": "Hnidava",
                "reason": "Trypillia-culture Eneolithic settlement at Hnidava on Styr river, Lutsk"
            },
            {
                "op": "RENAME_META",
                "key": "Kichkarivka-Ukraine",
                "new_name": "Kichkarivka",
                "reason": "Trypillia-culture Eneolithic settlement at Kichkarivka, Lutsk"
            },
            {
                "op": "RENAME_META",
                "key": "Krasne-Ukraine_2",
                "new_name": "Krasne (Lutsk)",
                "reason": "Trypillia-culture Eneolithic settlement at Krasne, Lutsk"
            }
        ],
        "clean_names": {
            "Gnidava-Ukraine": "Hnidava",
            "Kichkarivka-Ukraine": "Kichkarivka",
            "Krasne-Ukraine_2": "Krasne (Lutsk)"
        }
    },
    "C0118": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Kreva Late Mediaeval Hillfort-Belarus",
                "reason": "Kreva Castle ruin building with fabricated medieval hillfort label"
            },
            {
                "op": "MERGE",
                "source_key": "Krevskoe gorodishche Mediaeval Hillfort-Belarus",
                "target_key": "Kreva-Belarus",
                "reason": "Early medieval fortified centre continuous with Kreva settlement series"
            }
        ],
        "clean_names": {
            "Kreva-Belarus": "Kreva"
        }
    },
    "C0120": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Kudymkarskoe gorodishche-Russia",
                "target_key": "Kudymkar-Russia",
                "reason": "Ancestral Komi-Permyak fortified centre continuous with historic Kudymkar"
            },
            {
                "op": "MERGE",
                "source_key": "Kudymkarskoye (17001900)-Russia",
                "target_key": "Kudymkar-Russia",
                "reason": "Historic settlement period continuous with Kudymkar series"
            }
        ],
        "clean_names": {
            "Kudymkar-Russia": "Kudymkar"
        }
    },
    "C0123": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Kuntsevo settlement-Russia",
                "target_key": "Kun`'cevo-Russia",
                "reason": "Famous Dyakovo culture hillfort at Kuntsevo continuous with Kuntsevo settlement series"
            },
            {
                "op": "RENAME_META",
                "key": "Krylatskoe-Russia",
                "new_name": "Krylatskoye",
                "reason": "Historic village and archaeological site of Krylatskoye on Moskva river"
            }
        ],
        "clean_names": {
            "Kun`'cevo-Russia": "Kuntsevo",
            "Krylatskoe-Russia": "Krylatskoye"
        }
    },
    "C0124": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Burshtyn-Ukraine_2",
                "new_name": "Burshtyn (Medieval)",
                "reason": "Old Rus medieval gorodishche with >250-year hiatus to modern town of Burshtyn"
            },
            {
                "op": "RENAME_META",
                "key": "Kuropatnyky-Ukraine",
                "new_name": "Kuropatnyky",
                "reason": "Distinct medieval settlement at Kuropatnyky 3 km north of Burshtyn"
            }
        ],
        "clean_names": {
            "Burshtyn-Ukraine": "Burshtyn",
            "Burshtyn-Ukraine_2": "Burshtyn (Medieval)",
            "Kuropatnyky-Ukraine": "Kuropatnyky"
        }
    },
    "C0125": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Laszki Murowane Castle-Ukraine",
                "reason": "Historic castle ruin building at Murovane with fabricated medieval dates"
            },
            {
                "op": "RENAME_META",
                "key": "Castle Felsztynie-Ukraine",
                "new_name": "Felsztyn",
                "reason": "Historic fortified settlement and castle of Felsztyn / Skelivka"
            }
        ],
        "clean_names": {
            "Murovane-Ukraine": "Murovane",
            "Castle Felsztynie-Ukraine": "Felsztyn"
        }
    },
    "C0126": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Garadzishcha rannyaga zhaleznaga veku i terytoryya byloga syarednyavechnaga gorada Loeva Mediaeval Hillfort-Belarus",
                "target_key": "Loyev-Ukraine",
                "reason": "Territory of medieval fortress town of Loyev continuous across Dnieper-Sozh confluence"
            },
            {
                "op": "RENAME_META",
                "key": "Loyev Iron Age Site-Ukraine",
                "new_name": "Loyev (Iron Age)",
                "reason": "Pre-hiatus Early Iron Age Milograd-culture hillfort site at Loyev"
            }
        ],
        "clean_names": {
            "Loyev-Ukraine": "Loyev",
            "Loyev Iron Age Site-Ukraine": "Loyev (Iron Age)"
        }
    },
    "C0128": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Lyubimovskoye Classical Polis-Ukraine",
                "target_key": "Lyubimovka Left-Bank Fort-Ukraine",
                "reason": "Overlapping Late Scythian / Roman-period fortified settlement phase at Lyubymivka"
            },
            {
                "op": "RENAME_META",
                "key": "Lyubimovka Left-Bank Fort-Ukraine",
                "new_name": "Lyubymivka (Late Scythian)",
                "reason": "Famous Late Scythian fortified fortress settlement on Dnieper left bank at Lyubymivka"
            }
        ],
        "clean_names": {
            "Lyubymivka_UA_08-Ukraine": "Lyubymivka",
            "Lyubimovka Left-Bank Fort-Ukraine": "Lyubymivka (Late Scythian)"
        }
    },
    "C0129": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Gruppa iz 4 sopok (odna iz nikh Polaya sopka Khodakovskogo) (Staraya Ladoga)-Russia",
                "reason": "Group of 4 burial mound barrows (sopki) at Staraya Ladoga with fabricated settlement population"
            },
            {
                "op": "RENAME_META",
                "key": "Lyubsha Fortress-Russia",
                "new_name": "Lyubsha",
                "reason": "Pre-Viking early medieval stone-and-timber fortress at mouth of Volkhov river"
            }
        ],
        "clean_names": {
            "Staraya Ladoga-Russia": "Staraya Ladoga",
            "Lyubsha Fortress-Russia": "Lyubsha"
        }
    }
}
