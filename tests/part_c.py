# Part C: Clusters C0051 to C0085 (29 clusters)

PART_C = {
    "C0051": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Podvarantsy usadba usadebnyy dom Late Mediaeval Hillfort-Belarus",
                "reason": "Manor house estate building ruin with fabricated medieval hillfort label"
            },
            {
                "op": "DROP_JUNK",
                "key": "Turets kamennyy krest Mediaeval Hillfort-Belarus",
                "reason": "Memorial stone cross monument with fabricated medieval hillfort label"
            },
            {
                "op": "RENAME_META",
                "key": "Selishcha Site 326-Belarus",
                "new_name": "Selishcha (Irditsa)",
                "reason": "Medieval unfortified settlement site near Irditsa"
            },
            {
                "op": "RENAME_META",
                "key": "Stayanka peryyadu mezalitu seleshcha zhaleznaga veku-Belarus",
                "new_name": "Zayachenye",
                "reason": "Mesolithic camp and Iron Age settlement near Zayachenye"
            }
        ],
        "clean_names": {
            "Selishcha Site 326-Belarus": "Selishcha (Irditsa)",
            "Stayanka peryyadu mezalitu seleshcha zhaleznaga veku-Belarus": "Zayachenye"
        }
    },
    "C0052": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Usatove Eneolithic Hillfort-Ukraine",
                "target_key": "Usatovo-Ukraine",
                "reason": "Duplicate scrape of Usatovo culture fortified hillfort type-site"
            },
            {
                "op": "RENAME_META",
                "key": "Usatovo-Ukraine",
                "new_name": "Usatove (Eneolithic)",
                "reason": "World-famous Usatovo culture Eneolithic fortified type-site"
            },
            {
                "op": "RENAME_META",
                "key": "Usatove Neolithic Settlement-Ukraine",
                "new_name": "Usatove (Neolithic)",
                "reason": "Neolithic settlement site near Usatove"
            }
        ],
        "clean_names": {
            "Usatove-Ukraine": "Usatove",
            "Usatovo-Ukraine": "Usatove (Eneolithic)",
            "Usatove Neolithic Settlement-Ukraine": "Usatove (Neolithic)"
        }
    },
    "C0054": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Utamysh Gorodishche-Russia",
                "new_name": "Utamysh (Early Medieval)",
                "reason": "Khazar-era early medieval gorodishche with >700-year hiatus to modern aul"
            },
            {
                "op": "RENAME_META",
                "key": "Utamysh Bronze Age Site 2-Russia",
                "new_name": "Utamysh (Late Bronze Age)",
                "reason": "Kayakent-Khorochoi Late Bronze Age settlement site at Utamysh"
            },
            {
                "op": "RENAME_META",
                "key": "Utamysh Bronze Age Site-Russia",
                "new_name": "Utamysh (Bronze Age)",
                "reason": "Middle Bronze Age settlement site at Utamysh"
            }
        ],
        "clean_names": {
            "Utamysh-Russia": "Utamysh",
            "Utamysh Gorodishche-Russia": "Utamysh (Early Medieval)",
            "Utamysh Bronze Age Site 2-Russia": "Utamysh (Late Bronze Age)",
            "Utamysh Bronze Age Site-Russia": "Utamysh (Bronze Age)"
        }
    },
    "C0055": {
        "actions": [
            {
                "op": "KEEP_HOMONYM",
                "key": "Novyi Svit-Ukraine",
                "reason": "Distinct modern urban settlement in Donetsk Oblast 408 km away"
            },
            {
                "op": "RENAME_META",
                "key": "Novyi Svit-Ukraine_2",
                "new_name": "Novy Svet (Crimea)",
                "reason": "Historic Genoese/Crimean coastal settlement Paradiso at Novy Svet"
            },
            {
                "op": "RENAME_META",
                "key": "Karaul-Oba Archeological Complex-Ukraine",
                "new_name": "Karaul-Oba",
                "reason": "Taurian fortified refuge and archaeological complex on Mount Karaul-Oba"
            },
            {
                "op": "RENAME_META",
                "key": "Veseloye-Sudak-Ukraine",
                "new_name": "Kutlak",
                "reason": "Ancient Bosporan fortress of Kutlak / Athenaion near Veseloye, Sudak"
            }
        ],
        "clean_names": {
            "Novyi Svit-Ukraine": "Novyi Svit",
            "Novyi Svit-Ukraine_2": "Novy Svet (Crimea)",
            "Karaul-Oba Archeological Complex-Ukraine": "Karaul-Oba",
            "Veseloye-Sudak-Ukraine": "Kutlak"
        }
    },
    "C0056": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pustoviitivka Aksyntsi Sula Scythian Rus Complex Iron Age Site-Ukraine",
                "new_name": "Pustoviitivka (Iron Age)",
                "reason": "Scythian-era settlement and kurgan complex on Sula river at Pustoviitivka"
            },
            {
                "op": "RENAME_META",
                "key": "Vovkivtsi Iron Age Site-Ukraine",
                "new_name": "Vovkivtsi (Iron Age)",
                "reason": "Scythian-era settlement on Sula river at Vovkivtsi"
            }
        ],
        "clean_names": {
            "Pustoviitivka Aksyntsi Sula Scythian Rus Complex-Ukraine": "Pustoviitivka",
            "Vovkivtsi-Ukraine": "Vovkivtsi",
            "Pustoviitivka Aksyntsi Sula Scythian Rus Complex Iron Age Site-Ukraine": "Pustoviitivka (Iron Age)",
            "Vovkivtsi Iron Age Site-Ukraine": "Vovkivtsi (Iron Age)"
        }
    },
    "C0057": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Delyatyn XVII Hillfort-Ukraine",
                "target_key": "Delyatyn-Ukraine",
                "reason": "Medieval Old Rus hillfort continuous with settlement series of Delyatyn"
            },
            {
                "op": "RENAME_META",
                "key": "Delyatyn Bronze Age Settlement 2-Ukraine",
                "new_name": "Delyatyn (Bronze Age)",
                "reason": "Bronze Age Komariv-culture settlement site near Delyatyn"
            }
        ],
        "clean_names": {
            "Delyatyn-Ukraine": "Delyatyn",
            "Zarichchia-Ukraine": "Zarichchia",
            "Delyatyn Bronze Age Settlement 2-Ukraine": "Delyatyn (Bronze Age)"
        }
    },
    "C0058": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pereshchepyne Iron Age Hillfort-Ukraine",
                "new_name": "Pereshchepyne (Iron Age)",
                "reason": "Pre-hiatus Scythian Iron Age hillfort site on Orel river"
            },
            {
                "op": "RENAME_META",
                "key": "Perescepino Bronze Age Settlement-Ukraine",
                "new_name": "Pereshchepyne (Bronze Age)",
                "reason": "Late Bronze Age settlement site near Pereshchepyne"
            },
            {
                "op": "RENAME_META",
                "key": "Zasukha 1 Stone Age Hillfort-Ukraine",
                "new_name": "Zasukha 1",
                "reason": "Mesolithic/Neolithic stone age campsite at Zasukha near Pereshchepyne"
            }
        ],
        "clean_names": {
            "Pereshchepyne-Ukraine": "Pereshchepyne",
            "Pereshchepyne Iron Age Hillfort-Ukraine": "Pereshchepyne (Iron Age)",
            "Perescepino Bronze Age Settlement-Ukraine": "Pereshchepyne (Bronze Age)",
            "Zasukha 1 Stone Age Hillfort-Ukraine": "Zasukha 1"
        }
    },
    "C0059": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Slonim sinagoga Glavnaya Late Mediaeval Hillfort-Belarus",
                "reason": "Great Synagogue heritage building in Slonim with fabricated medieval hillfort label"
            },
            {
                "op": "DROP_JUNK",
                "key": "Zhirovichi monastyr zhiloy korpus Late Mediaeval Hillfort-Belarus",
                "reason": "Monastery residential building in Zhirovichi with fabricated medieval hillfort label"
            },
            {
                "op": "MERGE",
                "source_key": "Garadzishcha Slonim-Kosauski trakt-1-Belarus",
                "target_key": "Slonim-Belarus",
                "reason": "Early medieval hillfort continuous with historic town of Slonim"
            }
        ],
        "clean_names": {
            "Slonim-Belarus": "Slonim"
        }
    },
    "C0060": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Zatoka Classical Polis-Ukraine",
                "target_key": "Zatoka Tyras Spit-Ukraine",
                "reason": "Duplicate scrape of Classical / Roman-era anchorage settlement on Zatoka spit"
            },
            {
                "op": "MERGE",
                "source_key": "antychnoho chasu Zatoka I Classical Polis-Ukraine",
                "target_key": "Zatoka Tyras Spit-Ukraine",
                "reason": "Duplicate scrape of antique settlement Zatoka I on Dniester Liman mouth"
            },
            {
                "op": "RENAME_META",
                "key": "Zatoka Tyras Spit-Ukraine",
                "new_name": "Tyras Spit",
                "reason": "Ancient and medieval anchorage and settlement on Tyras / Zatoka spit"
            }
        ],
        "clean_names": {
            "Zatoka-Ukraine": "Zatoka",
            "Zatoka Tyras Spit-Ukraine": "Tyras Spit"
        }
    },
    "C0062": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "chernyakhovskoyi kultury Chernyakhov Settlement-Ukraine",
                "target_key": "Kamyanka III Migration Period Settlement-Ukraine",
                "reason": "Overlapping Chernyakhov / Migration Period settlement site at Kamyanka"
            },
            {
                "op": "RENAME_META",
                "key": "Kamyanka III Migration Period Settlement-Ukraine",
                "new_name": "Kamyanka III",
                "reason": "Numbered Chernyakhov and Migration Period settlement site III at Kamyanka"
            },
            {
                "op": "RENAME_META",
                "key": "Kamenka Classical Polis-Ukraine",
                "new_name": "Kamyanka (Classical)",
                "reason": "Classical / Roman-period settlement site near Kamyanka"
            },
            {
                "op": "RENAME_META",
                "key": "Kamyanka Bronze Age Settlement-Ukraine",
                "new_name": "Kamyanka (Bronze Age)",
                "reason": "Bronze Age settlement site near Kamyanka"
            }
        ],
        "clean_names": {
            "Kamyanka III Migration Period Settlement-Ukraine": "Kamyanka III",
            "Kamenka Classical Polis-Ukraine": "Kamyanka (Classical)",
            "Kamyanka Bronze Age Settlement-Ukraine": "Kamyanka (Bronze Age)"
        }
    },
    "C0063": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "dvosharove Plakhtiyivka doby piznoyi bronzy ta rymskoho chasu Bronze Age Settlement-Ukraine",
                "target_key": "dvosharove Plakhtiyivka I doby piznoyi bronzy ta rymskoho chasu Bronze Age Settlement-Ukraine",
                "reason": "Duplicate coordinate scrape of Bronze Age settlement Plakhtiyivka I"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove Plakhtiyivka I doby piznoyi bronzy ta rymskoho chasu Bronze Age Settlement-Ukraine",
                "new_name": "Plakhtiyivka I",
                "reason": "Numbered Late Bronze Age and Roman-period settlement site I at Plakhtiyivka"
            },
            {
                "op": "RENAME_META",
                "key": "chernyakhivske Plakhtiyivka II Chernyakhov Settlement-Ukraine",
                "new_name": "Plakhtiyivka II",
                "reason": "Numbered Chernyakhov settlement site II at Plakhtiyivka"
            }
        ],
        "clean_names": {
            "Plakhtiyivka-Ukraine": "Plakhtiyivka",
            "dvosharove Plakhtiyivka I doby piznoyi bronzy ta rymskoho chasu Bronze Age Settlement-Ukraine": "Plakhtiyivka I",
            "chernyakhivske Plakhtiyivka II Chernyakhov Settlement-Ukraine": "Plakhtiyivka II"
        }
    },
    "C0065": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kubei Karakurt-Ukraine",
                "new_name": "Kubey Karakurt",
                "reason": "Ancient and medieval steppe settlement complex on Yalpug river near Kubey"
            },
            {
                "op": "RENAME_META",
                "key": "bahatosharove bilozerske Chernyakhov Settlement-Ukraine",
                "new_name": "Kubey (Chernyakhov)",
                "reason": "Multi-period Belozerka and Chernyakhov settlement near Kubey"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove rymskoho chasu ta balkano-dunayske pivdennykh slovyan Chervonoarmiyske Classical Polis-Ukraine",
                "new_name": "Chervonoarmiyske",
                "reason": "Roman-period and South Slavic medieval settlement at Chervonoarmiyske"
            }
        ],
        "clean_names": {
            "Kubey-Ukraine": "Kubey",
            "Kubei Karakurt-Ukraine": "Kubey Karakurt",
            "bahatosharove bilozerske Chernyakhov Settlement-Ukraine": "Kubey (Chernyakhov)",
            "dvosharove rymskoho chasu ta balkano-dunayske pivdennykh slovyan Chervonoarmiyske Classical Polis-Ukraine": "Chervonoarmiyske"
        }
    },
    "C0066": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Halytsynivka Bronze Age Settlement-Ukraine",
                "new_name": "Halytsynove (Bronze Age)",
                "reason": "Bronze Age settlement site on Bug Liman near Halytsynove"
            },
            {
                "op": "RENAME_META",
                "key": "Halytsynivka IV Bronze Age Settlement-Ukraine",
                "new_name": "Halytsynove IV",
                "reason": "Numbered Bronze Age settlement site IV at Halytsynove"
            },
            {
                "op": "RENAME_META",
                "key": "katakombnoyi kultury Bronze Age Settlement-Ukraine",
                "new_name": "Halytsynove (Catacomb)",
                "reason": "Catacomb culture settlement site near Halytsynove"
            },
            {
                "op": "RENAME_META",
                "key": "Antychne poselennya Classical Polis-Ukraine",
                "new_name": "Halytsynove (Classical)",
                "reason": "Classical Olbian chora settlement site on Bug Liman near Halytsynove"
            }
        ],
        "clean_names": {
            "Halytsynivka Bronze Age Settlement-Ukraine": "Halytsynove (Bronze Age)",
            "Halytsynivka IV Bronze Age Settlement-Ukraine": "Halytsynove IV",
            "katakombnoyi kultury Bronze Age Settlement-Ukraine": "Halytsynove (Catacomb)",
            "Antychne poselennya Classical Polis-Ukraine": "Halytsynove (Classical)"
        }
    },
    "C0067": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "piznopaleolitychna Bilyayivka Palaeolithic Camp-Ukraine",
                "new_name": "Bilyayivka (Palaeolithic)",
                "reason": "Upper Palaeolithic campsite on Dniester at Bilyayivka"
            },
            {
                "op": "RENAME_META",
                "key": "antychnoho chasu Bilyayivka Classical Polis-Ukraine",
                "new_name": "Bilyayivka (Classical)",
                "reason": "Classical / Roman-period settlement site near Bilyayivka"
            },
            {
                "op": "RENAME_META",
                "key": "antychnoho chasu Bilyayivka IV Classical Polis II-Ukraine",
                "new_name": "Bilyayivka IV",
                "reason": "Numbered Classical-era settlement site IV at Bilyayivka"
            }
        ],
        "clean_names": {
            "Bilyayivka-Ukraine": "Bilyayivka",
            "piznopaleolitychna Bilyayivka Palaeolithic Camp-Ukraine": "Bilyayivka (Palaeolithic)",
            "antychnoho chasu Bilyayivka Classical Polis-Ukraine": "Bilyayivka (Classical)",
            "antychnoho chasu Bilyayivka IV Classical Polis II-Ukraine": "Bilyayivka IV"
        }
    },
    "C0068": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "ellinistychne ta rymske Moloha I Classical Polis-Ukraine",
                "target_key": "Mologa Dniester Liman-Ukraine",
                "reason": "Overlapping Hellenistic and Roman-era settlement phase on Dniester Liman at Moloha"
            },
            {
                "op": "RENAME_META",
                "key": "Mologa Dniester Liman-Ukraine",
                "new_name": "Moloha (Dniester Liman)",
                "reason": "Ancient and medieval multi-period coastal settlement on Dniester Liman"
            },
            {
                "op": "RENAME_META",
                "key": "piznopaleolitychna Moloha Palaeolithic Camp-Ukraine",
                "new_name": "Moloha (Palaeolithic)",
                "reason": "Upper Palaeolithic campsite near Moloha"
            }
        ],
        "clean_names": {
            "Moloha-Ukraine": "Moloha",
            "Mologa Dniester Liman-Ukraine": "Moloha (Dniester Liman)",
            "piznopaleolitychna Moloha Palaeolithic Camp-Ukraine": "Moloha (Palaeolithic)"
        }
    },
    "C0069": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "chernyakhivske Zadunayivka I Chernyakhov Settlement-Ukraine",
                "new_name": "Zadunayivka I",
                "reason": "Numbered Chernyakhov settlement site I at Zadunayivka"
            },
            {
                "op": "RENAME_META",
                "key": "chernyakhivske Zadunayivka IV Chernyakhov Settlement-Ukraine",
                "new_name": "Zadunayivka IV",
                "reason": "Numbered Chernyakhov settlement site IV at Zadunayivka"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove Zadunayivka V doby piznoyi bronzy ta rymskoho chasu Bronze Age Settlement-Ukraine",
                "new_name": "Zadunayivka V",
                "reason": "Numbered Late Bronze Age settlement site V at Zadunayivka"
            },
            {
                "op": "RENAME_META",
                "key": "piznoyi bronzy Zadunayivka Kh Bronze Age Settlement-Ukraine",
                "new_name": "Zadunayivka X",
                "reason": "Numbered Late Bronze Age settlement site X at Zadunayivka"
            }
        ],
        "clean_names": {
            "chernyakhivske Zadunayivka I Chernyakhov Settlement-Ukraine": "Zadunayivka I",
            "chernyakhivske Zadunayivka IV Chernyakhov Settlement-Ukraine": "Zadunayivka IV",
            "dvosharove Zadunayivka V doby piznoyi bronzy ta rymskoho chasu Bronze Age Settlement-Ukraine": "Zadunayivka V",
            "piznoyi bronzy Zadunayivka Kh Bronze Age Settlement-Ukraine": "Zadunayivka X"
        }
    },
    "C0070": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "dvosharove Kyrhyzh-Kytay I sabatynivske ta chernyakhivske Chernyakhov Settlement-Ukraine",
                "new_name": "Kyrhyzh-Kytay I",
                "reason": "Numbered Sabatynivka and Chernyakhov settlement site I on Kyrhyzh-Kytay river"
            },
            {
                "op": "RENAME_META",
                "key": "chernyakhivske Nova Ivanivka VI Chernyakhov Settlement-Ukraine",
                "new_name": "Nova Ivanivka VI",
                "reason": "Numbered Chernyakhov settlement site VI at Nova Ivanivka"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove Nova Ivanivka V sabatynivske ta chernyakhivske Chernyakhov Settlement-Ukraine",
                "new_name": "Nova Ivanivka V",
                "reason": "Numbered Sabatynivka and Chernyakhov settlement site V at Nova Ivanivka"
            },
            {
                "op": "RENAME_META",
                "key": "rymskoho chasu Nova Ivanivka III Classical Polis-Ukraine",
                "new_name": "Nova Ivanivka III",
                "reason": "Numbered Roman-period settlement site III at Nova Ivanivka"
            }
        ],
        "clean_names": {
            "dvosharove Kyrhyzh-Kytay I sabatynivske ta chernyakhivske Chernyakhov Settlement-Ukraine": "Kyrhyzh-Kytay I",
            "chernyakhivske Nova Ivanivka VI Chernyakhov Settlement-Ukraine": "Nova Ivanivka VI",
            "dvosharove Nova Ivanivka V sabatynivske ta chernyakhivske Chernyakhov Settlement-Ukraine": "Nova Ivanivka V",
            "rymskoho chasu Nova Ivanivka III Classical Polis-Ukraine": "Nova Ivanivka III"
        }
    },
    "C0071": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Afontova Gora 2 Palaeolithic Camp-Russia",
                "target_key": "Afontova Gora-Russia",
                "reason": "Duplicate scrape of world-famous Afontova Gora Upper Palaeolithic site on Yenisei"
            },
            {
                "op": "RENAME_META",
                "key": "Afontova Gora-Russia",
                "new_name": "Afontova Gora",
                "reason": "World-famous Upper Palaeolithic campsite complex on Yenisei at Krasnoyarsk"
            },
            {
                "op": "RENAME_META",
                "key": "Afontova Gora 2-Russia",
                "new_name": "Afontova Gora (Medieval)",
                "reason": "Medieval kurgan and settlement site at Afontova Gora"
            }
        ],
        "clean_names": {
            "Afontova Gora-Russia": "Afontova Gora",
            "Afontova Gora 2-Russia": "Afontova Gora (Medieval)"
        }
    },
    "C0072": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "BOROMLYa Iron Age Hillfort-Ukraine",
                "new_name": "Boromlia (Iron Age)",
                "reason": "Pre-hiatus Scythian Iron Age hillfort site on Boromlya river"
            },
            {
                "op": "RENAME_META",
                "key": "1 Boromlya Bronze Age Settlement-Ukraine",
                "new_name": "Boromlia (Bronze Age)",
                "reason": "Bronze Age settlement site near Boromlia"
            }
        ],
        "clean_names": {
            "Boromlia-Ukraine": "Boromlia",
            "BOROMLYa Iron Age Hillfort-Ukraine": "Boromlia (Iron Age)",
            "1 Boromlya Bronze Age Settlement-Ukraine": "Boromlia (Bronze Age)"
        }
    },
    "C0073": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Balaklava-Ukraine_2",
                "target_key": "Balaklava Symbolon-Ukraine",
                "reason": "Duplicate node of Genoese fortress Cembalo at Balaklava bay"
            },
            {
                "op": "RENAME_META",
                "key": "Balaklava Symbolon-Ukraine",
                "new_name": "Symbolon",
                "reason": "Ancient Greek port Symbolon and medieval fortress Cembalo at Balaklava"
            }
        ],
        "clean_names": {
            "Balaklava-Ukraine": "Balaklava",
            "Balaklava Symbolon-Ukraine": "Symbolon"
        }
    },
    "C0076": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Bilche-Zolote Hillfort-Ukraine",
                "target_key": "Bilche-Zolote-Ukraine",
                "reason": "Old Rus medieval hillfort continuous with settlement at Bilche-Zolote"
            },
            {
                "op": "RENAME_META",
                "key": "Bilche-Zolote-Ukraine",
                "new_name": "Bilche-Zolote",
                "reason": "Historic settlement and Old Rus centre at Bilche-Zolote"
            },
            {
                "op": "RENAME_META",
                "key": "Bilche-Zolote Bronze Age Site-Ukraine",
                "new_name": "Bilche-Zolote (Trypillia)",
                "reason": "World-famous Verteba Cave Trypillia settlement at Bilche-Zolote"
            }
        ],
        "clean_names": {
            "Bilche-Zolote-Ukraine": "Bilche-Zolote",
            "Bilche-Zolote Bronze Age Site-Ukraine": "Bilche-Zolote (Trypillia)"
        }
    },
    "C0078": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Bilyarskoe selishche I-Russia",
                "target_key": "Bilyar-Russia",
                "reason": "Unfortified suburban settlement part of Great City of Bilyar complex"
            },
            {
                "op": "MERGE",
                "source_key": "Bilyarsk Village-Russia",
                "target_key": "Bilyar-Russia",
                "reason": "Modern Russian village Bilyarsk continuous with historic Bilyar city complex"
            }
        ],
        "clean_names": {
            "Bilyar-Russia": "Bilyar"
        }
    },
    "C0079": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Bokhmach Rus Settlement-Ukraine",
                "target_key": "Bakhmach-Ukraine",
                "reason": "Old Rus chronicle settlement continuous with historic town of Bakhmach"
            },
            {
                "op": "RENAME_META",
                "key": "Bakhmach-2 Bronze Age Settlement-Ukraine",
                "new_name": "Bakhmach (Bronze Age)",
                "reason": "Pre-hiatus Bronze Age settlement site near Bakhmach"
            }
        ],
        "clean_names": {
            "Bakhmach-Ukraine": "Bakhmach",
            "Bakhmach-2 Bronze Age Settlement-Ukraine": "Bakhmach (Bronze Age)"
        }
    },
    "C0080": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Borisovka Sasyk-Ukraine",
                "new_name": "Borysivka (Sasyk)",
                "reason": "Multi-period Eneolithic to Byzantine settlement on Sasyk Lagoon"
            },
            {
                "op": "RENAME_META",
                "key": "Borysivka Bronze Age Settlement-Ukraine",
                "new_name": "Borysivka (Bronze Age)",
                "reason": "Late Bronze Age settlement site at Borysivka"
            },
            {
                "op": "RENAME_META",
                "key": "Borysivka Eneolithic Hillfort-Ukraine",
                "new_name": "Borysivka (Eneolithic)",
                "reason": "Usatovo-culture Eneolithic hillfort near Borysivka"
            }
        ],
        "clean_names": {
            "Borisovka Sasyk-Ukraine": "Borysivka (Sasyk)",
            "Borysivka Bronze Age Settlement-Ukraine": "Borysivka (Bronze Age)",
            "Borysivka Eneolithic Hillfort-Ukraine": "Borysivka (Eneolithic)"
        }
    },
    "C0081": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Buzhanka 2 Palaeolithic Camp-Ukraine",
                "target_key": "Buzhany Desna Terrace Palaeolithic Camp-Ukraine",
                "reason": "Duplicate scrape of Desna terrace Upper Palaeolithic campsite at Buzhanka"
            },
            {
                "op": "RENAME_META",
                "key": "Buzhany Desna Terrace Palaeolithic Camp-Ukraine",
                "new_name": "Buzhanka (Palaeolithic)",
                "reason": "Desna terrace Upper Palaeolithic campsite near Buzhanka"
            },
            {
                "op": "RENAME_META",
                "key": "Buzhany Medieval Settlement-Ukraine",
                "new_name": "Buzhanka (Medieval)",
                "reason": "Early medieval Slavic settlement site near Buzhanka"
            }
        ],
        "clean_names": {
            "Buzhany Desna Terrace Palaeolithic Camp-Ukraine": "Buzhanka (Palaeolithic)",
            "Buzhany Medieval Settlement-Ukraine": "Buzhanka (Medieval)"
        }
    },
    "C0082": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Chulatovo 1 - Khulatovo 1 - Tchoulatovo 1 Palaeolithic Camp-Ukraine",
                "target_key": "Chulatovo I-II-Ukraine",
                "reason": "Duplicate scrape of famous Chulatovo Upper Palaeolithic site on Desna"
            },
            {
                "op": "RENAME_META",
                "key": "Chulatovo I-II-Ukraine",
                "new_name": "Chulatovo (Palaeolithic)",
                "reason": "Famous Chulatovo I-II Upper Palaeolithic mammoth-hunting site on Desna"
            },
            {
                "op": "RENAME_META",
                "key": "Chulatovo I-II Iron Age Site-Ukraine",
                "new_name": "Chulatovo (Iron Age)",
                "reason": "Yukhnovo culture Iron Age settlement site at Chulatovo"
            }
        ],
        "clean_names": {
            "Chulatovo I-II-Ukraine": "Chulatovo (Palaeolithic)",
            "Chulatovo I-II Iron Age Site-Ukraine": "Chulatovo (Iron Age)"
        }
    },
    "C0083": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Deriyivka Neolithic Settlement-Ukraine",
                "target_key": "Dereivka-Ukraine",
                "reason": "Duplicate scrape of world-famous Dereivka Neolithic / Sredny Stog type-site"
            },
            {
                "op": "MERGE",
                "source_key": "Dereivka Neolithic Settlement II-Ukraine",
                "target_key": "Dereivka-Ukraine",
                "reason": "Duplicate scrape of Dereivka archaeological settlement complex on Dnieper"
            },
            {
                "op": "RENAME_META",
                "key": "Dereivka-Ukraine",
                "new_name": "Deriivka",
                "reason": "World-famous Sredny Stog culture horse-domestication type-site on Dnieper"
            }
        ],
        "clean_names": {
            "Dereivka-Ukraine": "Deriivka"
        }
    },
    "C0084": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "1 Dukhanivka Iron Age Hillfort-Ukraine",
                "new_name": "Dukhanivka (Iron Age)",
                "reason": "Pre-hiatus Yukhnovo Iron Age hillfort site at Dukhanivka"
            },
            {
                "op": "RENAME_META",
                "key": "2 Dukhanivka Bronze Age Settlement-Ukraine",
                "new_name": "Dukhanivka 2",
                "reason": "Numbered Sosnitsa Bronze Age settlement site 2 at Dukhanivka"
            },
            {
                "op": "RENAME_META",
                "key": "Dukhanivka Bronze Age Settlement 2-Ukraine",
                "new_name": "Dukhanivka (Bronze Age)",
                "reason": "Bronze Age settlement site near Dukhanivka"
            }
        ],
        "clean_names": {
            "1 Dukhanivka Iron Age Hillfort-Ukraine": "Dukhanivka (Iron Age)",
            "2 Dukhanivka Bronze Age Settlement-Ukraine": "Dukhanivka 2",
            "Dukhanivka Bronze Age Settlement 2-Ukraine": "Dukhanivka (Bronze Age)"
        }
    },
    "C0085": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Drevnee zakhoronenie u mesta byvshey tserkvi Paraskevy Pyatnitsy (Chekalin)-Russia",
                "reason": "Church cemetery burial ground heritage site with fabricated medieval dates"
            },
            {
                "op": "MERGE",
                "source_key": "Duna-Russia",
                "target_key": "Gorodishche Duna (Chekalin)-Russia",
                "reason": "Duplicate coordinate scrape of Dunskoe gorodishche near Chekalin"
            },
            {
                "op": "RENAME_META",
                "key": "Gorodishche Duna (Chekalin)-Russia",
                "new_name": "Duna",
                "reason": "Famous Moschiny and Vyatichi early medieval hillfort on Oka river"
            }
        ],
        "clean_names": {
            "Gorodishche Duna (Chekalin)-Russia": "Duna"
        }
    }
}
