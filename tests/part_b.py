# Part B: Clusters C0026 to C0050 (24 clusters)

PART_B = {
    "C0026": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Belynichi kamennyy krest Mediaeval Hillfort-Belarus",
                "reason": "Memorial stone cross monument with fabricated hillfort label"
            },
            {
                "op": "MERGE",
                "source_key": "Beragavy (arkhealagichnyya pomniki)-Belarus",
                "target_key": "Beragavy Mediaeval Hillfort-Belarus",
                "reason": "Duplicate coordinate scrape of medieval fortified site at Beragavy"
            },
            {
                "op": "RENAME_META",
                "key": "Beragavy Mediaeval Hillfort-Belarus",
                "new_name": "Beragavy",
                "reason": "Medieval hillfort site at Beragavy on Neman river"
            },
            {
                "op": "RENAME_META",
                "key": "Shchachynova Bronze Age Settlement-Belarus",
                "new_name": "Shchechinovo",
                "reason": "Bronze Age settlement site near Shchechinovo"
            }
        ],
        "clean_names": {
            "Beragavy Mediaeval Hillfort-Belarus": "Beragavy",
            "Shchachynova Bronze Age Settlement-Belarus": "Shchechinovo"
        }
    },
    "C0027": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Bilozerka Eneolithic Hillfort-Ukraine",
                "new_name": "Bilozirka (Trypillia)",
                "reason": "Distinct Trypillia culture settlement at Bilozirka in Vinnytsia Oblast, 443 km away"
            },
            {
                "op": "RENAME_META",
                "key": "Bilozerske poselennya Bronze Age Settlement-Ukraine",
                "new_name": "Bilozerka (Bronze Age)",
                "reason": "Famous Belozerka culture Late Bronze Age type-site on Lake Bilozerka, Kherson Oblast"
            },
            {
                "op": "RENAME_META",
                "key": "Bilozerka Eneolithic Hillfort-Ukraine_2",
                "new_name": "Bilozerka (Eneolithic)",
                "reason": "Pre-hiatus Eneolithic settlement on Lake Bilozerka, Kherson Oblast"
            }
        ],
        "clean_names": {
            "Bilozerka-Ukraine": "Bilozerka",
            "Bilozerske poselennya Bronze Age Settlement-Ukraine": "Bilozerka (Bronze Age)",
            "Bilozerka Eneolithic Hillfort-Ukraine_2": "Bilozerka (Eneolithic)",
            "Bilozerka Eneolithic Hillfort-Ukraine": "Bilozirka (Trypillia)"
        }
    },
    "C0028": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Chirkey Medieval Gorodishche-Russia",
                "target_key": "Chirkey-Russia",
                "reason": "Medieval fortified settlement continuous with Chirkey settlement series"
            },
            {
                "op": "RENAME_META",
                "key": "Chirkey Bronze Age Site 2-Russia",
                "new_name": "Chirkey (Late Bronze Age)",
                "reason": "Late Bronze Age settlement site at Chirkey"
            },
            {
                "op": "RENAME_META",
                "key": "Chirkey Bronze Age Site-Russia",
                "new_name": "Chirkey (Bronze Age)",
                "reason": "Middle Bronze Age settlement site at Chirkey"
            }
        ],
        "clean_names": {
            "Chirkey-Russia": "Chirkey",
            "Chirkey Bronze Age Site 2-Russia": "Chirkey (Late Bronze Age)",
            "Chirkey Bronze Age Site-Russia": "Chirkey (Bronze Age)"
        }
    },
    "C0029": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Gagatli Medieval Gorodishche-Russia",
                "new_name": "Gagatli (Medieval)",
                "reason": "Medieval mountain hillfort at Gagatli with >400-year hiatus to modern aul"
            },
            {
                "op": "RENAME_META",
                "key": "Gagatli Bronze Age Site 2-Russia",
                "new_name": "Gagatli (Late Bronze Age)",
                "reason": "Late Bronze Age settlement site at Gagatli"
            },
            {
                "op": "RENAME_META",
                "key": "Gagatli Bronze Age Site-Russia",
                "new_name": "Gagatli (Bronze Age)",
                "reason": "Middle Bronze Age settlement site at Gagatli"
            }
        ],
        "clean_names": {
            "Gagatli-Russia": "Gagatli",
            "Gagatli Medieval Gorodishche-Russia": "Gagatli (Medieval)",
            "Gagatli Bronze Age Site 2-Russia": "Gagatli (Late Bronze Age)",
            "Gagatli Bronze Age Site-Russia": "Gagatli (Bronze Age)"
        }
    },
    "C0030": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Gazi-Yurt Medieval Gorodishche-Russia",
                "target_key": "Gazi-Yurt-Russia",
                "reason": "Duplicate node of early medieval Alanic gorodishche at Gazi-Yurt"
            },
            {
                "op": "RENAME_META",
                "key": "Gazi-Yurt-Russia",
                "new_name": "Gazi-Yurt",
                "reason": "Alanic early medieval fortified town centre of Gazi-Yurt"
            },
            {
                "op": "RENAME_META",
                "key": "Ekazhevo Medieval Gorodishche-Russia",
                "new_name": "Ekazhevo (Medieval)",
                "reason": "Medieval fortified gorodishche with >500-year hiatus to modern Ekazhevo"
            }
        ],
        "clean_names": {
            "Ekazhevo-Russia": "Ekazhevo",
            "Ekazhevo Medieval Gorodishche-Russia": "Ekazhevo (Medieval)",
            "Gazi-Yurt-Russia": "Gazi-Yurt"
        }
    },
    "C0031": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Igren Mesolithic Settlement-Ukraine",
                "target_key": "Igren VIII-Ukraine",
                "reason": "Duplicate scrape of Igren VIII Mesolithic campsite on Samara-Dnieper confluence"
            },
            {
                "op": "RENAME_META",
                "key": "Igren VIII-Ukraine",
                "new_name": "Igren VIII",
                "reason": "Famous multi-period Mesolithic-Neolithic campsite Igren VIII"
            },
            {
                "op": "RENAME_META",
                "key": "Ihren Neolithic Settlement-Ukraine",
                "new_name": "Ihren (Neolithic)",
                "reason": "Neolithic settlement site at Ihren"
            }
        ],
        "clean_names": {
            "Ihren-Ukraine": "Ihren",
            "Igren VIII-Ukraine": "Igren VIII",
            "Ihren Neolithic Settlement-Ukraine": "Ihren (Neolithic)"
        }
    },
    "C0032": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Irganay Medieval Gorodishche-Russia",
                "new_name": "Irganay (Medieval)",
                "reason": "Medieval fortified mountain settlement with >400-year hiatus to modern aul"
            },
            {
                "op": "RENAME_META",
                "key": "Irganay Bronze Age Site 2-Russia",
                "new_name": "Irganay (Late Bronze Age)",
                "reason": "Late Bronze Age settlement site at Irganay"
            },
            {
                "op": "RENAME_META",
                "key": "Irganay Bronze Age Site-Russia",
                "new_name": "Irganay (Bronze Age)",
                "reason": "Middle Bronze Age settlement site at Irganay"
            }
        ],
        "clean_names": {
            "Irganay-Russia": "Irganay",
            "Irganay Medieval Gorodishche-Russia": "Irganay (Medieval)",
            "Irganay Bronze Age Site 2-Russia": "Irganay (Late Bronze Age)",
            "Irganay Bronze Age Site-Russia": "Irganay (Bronze Age)"
        }
    },
    "C0033": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kayakent Gorodishche-Russia",
                "new_name": "Kayakent (Early Medieval)",
                "reason": "Khazar-era early medieval gorodishche with >900-year hiatus to modern town"
            },
            {
                "op": "RENAME_META",
                "key": "Kayakent Bronze Age Site 2-Russia",
                "new_name": "Kayakent (Late Bronze Age)",
                "reason": "Kayakent-Khorochoi Late Bronze Age type-site phase 2"
            },
            {
                "op": "RENAME_META",
                "key": "Kayakent Bronze Age Site-Russia",
                "new_name": "Kayakent (Bronze Age)",
                "reason": "Early Bronze Age settlement site at Kayakent"
            }
        ],
        "clean_names": {
            "Kayakent-Russia": "Kayakent",
            "Kayakent Gorodishche-Russia": "Kayakent (Early Medieval)",
            "Kayakent Bronze Age Site 2-Russia": "Kayakent (Late Bronze Age)",
            "Kayakent Bronze Age Site-Russia": "Kayakent (Bronze Age)"
        }
    },
    "C0034": {
        "actions": [
            {
                "op": "KEEP_HOMONYM",
                "key": "Kazachka-Russia",
                "reason": "Distinct modern settlement in Tula Oblast 3407 km away from Siberian Yenisei sites"
            },
            {
                "op": "RENAME_META",
                "key": "Kazachka-Russia_2",
                "new_name": "Kazachka (Late Bronze Age)",
                "reason": "Late Bronze Age Kan-Yenisei settlement on Kazachka river, Siberia"
            },
            {
                "op": "RENAME_META",
                "key": "Kazachka Bronze Age Site-Russia",
                "new_name": "Kazachka (Bronze Age)",
                "reason": "Early Bronze Age settlement site on Kazachka river, Siberia"
            },
            {
                "op": "RENAME_META",
                "key": "Kazachka Stone Age Site-Russia",
                "new_name": "Kazachka (Stone Age)",
                "reason": "Neolithic stone age campsite on Kazachka river, Siberia"
            }
        ],
        "clean_names": {
            "Kazachka-Russia": "Kazachka",
            "Kazachka-Russia_2": "Kazachka (Late Bronze Age)",
            "Kazachka Bronze Age Site-Russia": "Kazachka (Bronze Age)",
            "Kazachka Stone Age Site-Russia": "Kazachka (Stone Age)"
        }
    },
    "C0035": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Bolgary Village-Russia",
                "target_key": "Bolgary-Russia",
                "reason": "Russian settlement Bolgary continuous with Bolgar historic town complex"
            },
            {
                "op": "RENAME_META",
                "key": "Balymery-Russia",
                "new_name": "Balymery",
                "reason": "Distinct early medieval Bulgar gorodishche and burial ground at Balymery"
            },
            {
                "op": "RENAME_META",
                "key": "Kuybyshevskoe gorodishche-Russia",
                "new_name": "Kuybyshevskoe Gorodishche",
                "reason": "Distinct medieval Volga Bulgarian fortified settlement 23 km away"
            }
        ],
        "clean_names": {
            "Bolgary-Russia": "Bolgar",
            "Balymery-Russia": "Balymery",
            "Kuybyshevskoe gorodishche-Russia": "Kuybyshevskoe Gorodishche"
        }
    },
    "C0037": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Kalmius Porto Pisano Approach-Ukraine",
                "target_key": "Mariupol'-Ukraine",
                "reason": "Medieval Kalmius mouth anchorage and Cossack outpost continuous with Mariupol"
            },
            {
                "op": "RENAME_META",
                "key": "Mariupol Bronze Age Settlement-Ukraine",
                "new_name": "Mariupol (Bronze Age)",
                "reason": "Bronze Age settlement site on Kalmius river near Mariupol"
            },
            {
                "op": "RENAME_META",
                "key": "Mariupol Stone Age Hillfort-Ukraine",
                "new_name": "Mariupol (Stone Age)",
                "reason": "World-famous Neolithic cemetery and Stone Age site at Mariupol"
            }
        ],
        "clean_names": {
            "Mariupol'-Ukraine": "Mariupol",
            "Mariupol Bronze Age Settlement-Ukraine": "Mariupol (Bronze Age)",
            "Mariupol Stone Age Hillfort-Ukraine": "Mariupol (Stone Age)"
        }
    },
    "C0038": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Mayaki Eneolithic Hillfort-Ukraine",
                "target_key": "Mayaki Eneolithic-Ukraine",
                "reason": "Duplicate scrape of Usatovo culture fortified ditched settlement at Mayaky"
            },
            {
                "op": "RENAME_META",
                "key": "Mayaki Eneolithic-Ukraine",
                "new_name": "Mayaky (Eneolithic)",
                "reason": "Famous Usatovo-culture Eneolithic fortified settlement on Dniester"
            },
            {
                "op": "RENAME_META",
                "key": "Mayaky-Ukraine_2",
                "new_name": "Mayaky (Medieval)",
                "reason": "Medieval town and crossing on Dniester with >390-year hiatus to modern settlement"
            }
        ],
        "clean_names": {
            "Mayaky-Ukraine": "Mayaky",
            "Mayaki Eneolithic-Ukraine": "Mayaky (Eneolithic)",
            "Mayaky-Ukraine_2": "Mayaky (Medieval)"
        }
    },
    "C0039": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mikhailovka-Ukraine",
                "new_name": "Mykhailivka (Yamnaya)",
                "reason": "World-famous Lower Dnieper Yamnaya-culture fortified citadel type-site"
            },
            {
                "op": "RENAME_META",
                "key": "Mihajlovka Bronze Age Settlement-Ukraine",
                "new_name": "Mykhailivka (Bronze Age)",
                "reason": "Late Bronze Age settlement site near Mykhailivka"
            },
            {
                "op": "RENAME_META",
                "key": "Mikhaylovka Classical Polis-Ukraine",
                "new_name": "Mykhailivka (Classical)",
                "reason": "Classical / Roman-period settlement site near Mykhailivka"
            },
            {
                "op": "RENAME_META",
                "key": "Hoty 911 Chernyakhov Settlement-Ukraine",
                "new_name": "Mykhailivka (Chernyakhov)",
                "reason": "Chernyakhov culture settlement site near Mykhailivka"
            }
        ],
        "clean_names": {
            "Mikhailovka-Ukraine": "Mykhailivka (Yamnaya)",
            "Mihajlovka Bronze Age Settlement-Ukraine": "Mykhailivka (Bronze Age)",
            "Mikhaylovka Classical Polis-Ukraine": "Mykhailivka (Classical)",
            "Hoty 911 Chernyakhov Settlement-Ukraine": "Mykhailivka (Chernyakhov)"
        }
    },
    "C0040": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mogokh Medieval Gorodishche-Russia",
                "new_name": "Mogokh (Medieval)",
                "reason": "Medieval mountain hillfort at Mogokh with >370-year hiatus to modern aul"
            },
            {
                "op": "RENAME_META",
                "key": "Mogokh Bronze Age Site 2-Russia",
                "new_name": "Mogokh (Late Bronze Age)",
                "reason": "Late Bronze Age settlement site at Mogokh"
            },
            {
                "op": "RENAME_META",
                "key": "Mogokh Bronze Age Site-Russia",
                "new_name": "Mogokh (Bronze Age)",
                "reason": "Middle Bronze Age settlement site at Mogokh"
            }
        ],
        "clean_names": {
            "Mogokh-Russia": "Mogokh",
            "Mogokh Medieval Gorodishche-Russia": "Mogokh (Medieval)",
            "Mogokh Bronze Age Site 2-Russia": "Mogokh (Late Bronze Age)",
            "Mogokh Bronze Age Site-Russia": "Mogokh (Bronze Age)"
        }
    },
    "C0041": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Lida zamok Gedimina Mediaeval Hillfort-Belarus",
                "reason": "Historic castle ruin building inside Lida with fabricated early medieval dates"
            },
            {
                "op": "MERGE",
                "source_key": "Garadzishcha i selishcha Myto-Belarus",
                "target_key": "Myto Mediaeval Hillfort-Belarus",
                "reason": "Duplicate archaeological scrape of medieval hillfort and settlement at Myto"
            },
            {
                "op": "RENAME_META",
                "key": "Myto Mediaeval Hillfort-Belarus",
                "new_name": "Myto",
                "reason": "Distinct medieval hillfort and settlement at Myto village in Lida Raion"
            }
        ],
        "clean_names": {
            "Lida-Belarus": "Lida",
            "Myto Mediaeval Hillfort-Belarus": "Myto"
        }
    },
    "C0042": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Novgorod-Seversk Iron Age Site-Ukraine",
                "target_key": "Novhorod-Siverskyi-Ukraine",
                "reason": "Continuous early settlement phase overlapping with historic Novhorod-Siverskyi"
            },
            {
                "op": "RENAME_META",
                "key": "Novgorod-Seversky Bronze Age Site-Ukraine",
                "new_name": "Novhorod-Siverskyi (Bronze Age)",
                "reason": "Sosnitsa Bronze Age settlement site at Novhorod-Siverskyi"
            },
            {
                "op": "RENAME_META",
                "key": "Novgorod-Seversky Palaeolithic Cliff Shelter-Ukraine",
                "new_name": "Novhorod-Siverskyi (Palaeolithic)",
                "reason": "Famous Desna cliff shelter Upper Palaeolithic campsite"
            }
        ],
        "clean_names": {
            "Novhorod-Siverskyi-Ukraine": "Novhorod-Siverskyi",
            "Novgorod-Seversky Bronze Age Site-Ukraine": "Novhorod-Siverskyi (Bronze Age)",
            "Novgorod-Seversky Palaeolithic Cliff Shelter-Ukraine": "Novhorod-Siverskyi (Palaeolithic)"
        }
    },
    "C0043": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Bip Fortress-Russia",
                "reason": "Pavilion-fortress folly architectural building in Pavlovsk palace park"
            },
            {
                "op": "DROP_JUNK",
                "key": "Novoe Shale-Russia",
                "reason": "Chalet pavilion architectural feature in Pavlovsk palace park"
            },
            {
                "op": "DROP_JUNK",
                "key": "Pavilon Khram Rozy bez shipov-Russia",
                "reason": "Temple of the Rose without Thorns park pavilion in Pavlovsk palace park"
            }
        ],
        "clean_names": {
            "Pavlovsk_RU_66-Russia": "Pavlovsk"
        }
    },
    "C0044": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Kursk Kremlin-Russia",
                "target_key": "Kursk-Russia",
                "reason": "Citadel kremlin fortress of Kursk"
            },
            {
                "op": "MERGE",
                "source_key": "Old Kursk Gorodishche-Russia",
                "target_key": "Kursk-Russia",
                "reason": "Old Rus fortified core of Kursk"
            },
            {
                "op": "MERGE",
                "source_key": "Kursk Romny Gorodishche-Russia",
                "target_key": "Kursk-Russia",
                "reason": "Continuous Romny culture early Slav settlement phase at Kursk"
            }
        ],
        "clean_names": {
            "Kursk-Russia": "Kursk"
        }
    },
    "C0045": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Pastyrske Hill Fort-Ukraine",
                "new_name": "Pastyrske",
                "reason": "Famous early medieval Slavic hillfort and Pastyr culture type-site"
            },
            {
                "op": "RENAME_META",
                "key": "Dva skifskykh horodyshcha Iron Age Hillfort-Ukraine",
                "new_name": "Pastyrske (Iron Age)",
                "reason": "Pre-hiatus Scythian Iron Age twin hillforts at Pastyrske"
            },
            {
                "op": "RENAME_META",
                "key": "Pastyrskoye Iron Age Site-Ukraine",
                "new_name": "Pastyrske (Scythian)",
                "reason": "Scythian-era settlement site near Pastyrske"
            },
            {
                "op": "RENAME_META",
                "key": "Pastyrskoye Iron Age Site 2-Ukraine",
                "new_name": "Pastyrske (Roman Period)",
                "reason": "Roman-period Chernyakhov settlement site near Pastyrske"
            }
        ],
        "clean_names": {
            "Pastyrske Hill Fort-Ukraine": "Pastyrske",
            "Dva skifskykh horodyshcha Iron Age Hillfort-Ukraine": "Pastyrske (Iron Age)",
            "Pastyrskoye Iron Age Site-Ukraine": "Pastyrske (Scythian)",
            "Pastyrskoye Iron Age Site 2-Ukraine": "Pastyrske (Roman Period)"
        }
    },
    "C0046": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Ostatki Setunskogo kirpichnogo zavoda-Russia",
                "reason": "Remains of Setun brick factory in Moscow with fabricated medieval dates"
            },
            {
                "op": "DROP_JUNK",
                "key": "Selishche 1-e u Leninskikh gor (nizhnee) (Ramenki)-Russia",
                "reason": "Heritage registry cultural layer zone in Moscow with fabricated medieval dates"
            },
            {
                "op": "DROP_JUNK",
                "key": "Selishche Kamennaya plotina (zona kulturnogo sloya) (Ramenki)-Russia",
                "reason": "Heritage registry cultural layer zone in Moscow with fabricated medieval dates"
            },
            {
                "op": "DROP_JUNK",
                "key": "Selo Troitskoe-Golenishchevo (mesto drevnego poseleniya s zonoy kulturnogo sloya) (Ramenki)-Russia",
                "reason": "Heritage registry cultural layer zone in Moscow with fabricated medieval dates"
            }
        ],
        "clean_names": {}
    },
    "C0047": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Snigirevka Eneolithic Hillfort-Ukraine",
                "new_name": "Snihurivka (Eneolithic)",
                "reason": "Pre-hiatus Eneolithic / Usatovo hillfort site on Ingulets river at Snihurivka"
            },
            {
                "op": "RENAME_META",
                "key": "Snihurivka Ingulets-Ukraine",
                "new_name": "Snihurivka (Iron Age)",
                "reason": "Scythian-Chernyakhov multi-period settlement on Ingulets-Visun confluence"
            },
            {
                "op": "RENAME_META",
                "key": "Aleksandrovka Chernyakhov-Ukraine",
                "new_name": "Oleksandrivka (Chernyakhov)",
                "reason": "Chernyakhov culture settlement at Oleksandrivka near Snihurivka"
            }
        ],
        "clean_names": {
            "Snihurivka-Ukraine": "Snihurivka",
            "Snigirevka Eneolithic Hillfort-Ukraine": "Snihurivka (Eneolithic)",
            "Snihurivka Ingulets-Ukraine": "Snihurivka (Iron Age)",
            "Aleksandrovka Chernyakhov-Ukraine": "Oleksandrivka (Chernyakhov)"
        }
    },
    "C0048": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Sosnytsia Medieval Settlement-Ukraine",
                "target_key": "Sosnytsia-Ukraine",
                "reason": "Old Rus medieval settlement continuous with historic town of Sosnytsia"
            },
            {
                "op": "RENAME_META",
                "key": "Sosnytsia Iron Age Site-Ukraine",
                "new_name": "Sosnytsia (Iron Age)",
                "reason": "Early Iron Age Yukhnovo culture settlement site at Sosnytsia"
            },
            {
                "op": "RENAME_META",
                "key": "Sosnytsia Bronze Age Site-Ukraine",
                "new_name": "Sosnytsia (Bronze Age)",
                "reason": "Famous Sosnitsa culture Bronze Age type-site on Ubid river"
            }
        ],
        "clean_names": {
            "Sosnytsia-Ukraine": "Sosnytsia",
            "Sosnytsia Iron Age Site-Ukraine": "Sosnytsia (Iron Age)",
            "Sosnytsia Bronze Age Site-Ukraine": "Sosnytsia (Bronze Age)"
        }
    },
    "C0049": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Suzgun-Russia_2",
                "target_key": "Suzgun Medieval Gorodishche-Russia",
                "reason": "Duplicate early medieval phase of Suzgun fortified centre near Tobolsk"
            },
            {
                "op": "MERGE",
                "source_key": "Suzgun Medieval Gorodishche-Russia",
                "target_key": "Suzgun-Russia",
                "reason": "Medieval fortified settlement continuous within 150-year gap of Siberian Tatar town Suzgun"
            },
            {
                "op": "RENAME_META",
                "key": "Suzgun Bronze Age Site-Russia",
                "new_name": "Suzgun (Bronze Age)",
                "reason": "Famous Suzgun culture Late Bronze Age type-site near Tobolsk"
            }
        ],
        "clean_names": {
            "Suzgun-Russia": "Suzgun",
            "Suzgun Bronze Age Site-Russia": "Suzgun (Bronze Age)"
        }
    },
    "C0050": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Targay Iron Age Site-Russia",
                "target_key": "Targay-Russia",
                "reason": "Iron Age cultural layer continuous with Tarya pit-village settlement series"
            },
            {
                "op": "RENAME_META",
                "key": "Targay Bronze Age Site 2-Russia",
                "new_name": "Targay (Late Bronze Age)",
                "reason": "Late Bronze Age settlement site at Targay in Avacha Bay"
            },
            {
                "op": "RENAME_META",
                "key": "Targay Bronze Age Site-Russia",
                "new_name": "Targay (Bronze Age)",
                "reason": "Early Bronze Age settlement site at Targay in Avacha Bay"
            }
        ],
        "clean_names": {
            "Targay-Russia": "Targay",
            "Targay Bronze Age Site 2-Russia": "Targay (Late Bronze Age)",
            "Targay Bronze Age Site-Russia": "Targay (Bronze Age)"
        }
    }
}
