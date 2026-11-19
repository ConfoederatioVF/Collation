# Part A: Clusters C0001 to C0025 (20 clusters)

PART_A = {
    "C0001": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Alkhan-Kala-Russia_2",
                "target_key": "Alkhan-Kala Medieval Gorodishche-Russia",
                "reason": "Alkhan-Kala-Russia_2 represents the same Alanic-Khazar fortified gorodishche as Alkhan-Kala Medieval Gorodishche"
            },
            {
                "op": "MERGE",
                "source_key": "Alkhan-Yurt Iron Age Site-Russia",
                "target_key": "Alkhan-Yurt Medieval Gorodishche-Russia",
                "reason": "Same multi-period archaeological settlement complex at Alkhan-Yurt"
            },
            {
                "op": "MERGE",
                "source_key": "Alkhan-Yurt Medieval Gorodishche-Russia",
                "target_key": "Alkhan-Yurt-Russia",
                "reason": "Alkhan-Yurt-Russia already encompasses the continuous settlement trajectory spanning -300 to modern"
            },
            {
                "op": "RENAME_META",
                "key": "Alkhan-Kala Medieval Gorodishche-Russia",
                "new_name": "Alkhan-Kala (Medieval)",
                "reason": "Pre-hiatus medieval fortified settlement separated by >600 years from 19th-century stanitsa"
            },
            {
                "op": "RENAME_META",
                "key": "Alkhan-Kala Iron Age Site-Russia",
                "new_name": "Alkhan-Kala (Iron Age)",
                "reason": "Pre-hiatus Iron Age site at Alkhan-Kala"
            }
        ],
        "clean_names": {
            "Alkhan-Kala-Russia": "Alkhan-Kala",
            "Alkhan-Kala Medieval Gorodishche-Russia": "Alkhan-Kala (Medieval)",
            "Alkhan-Kala Iron Age Site-Russia": "Alkhan-Kala (Iron Age)",
            "Alkhan-Yurt-Russia": "Alkhan-Yurt"
        }
    },
    "C0002": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Nemirov Hillfort Iron Age Site 2-Ukraine",
                "target_key": "Nemyriv Hillfort Iron Age Site 2-Ukraine",
                "reason": "Duplicate transliteration twin of Roman-period hillfort phase"
            },
            {
                "op": "MERGE",
                "source_key": "Nemirov Hillfort Iron Age Site-Ukraine",
                "target_key": "Nemyriv Hillfort Iron Age Site-Ukraine",
                "reason": "Duplicate transliteration twin of Scythian rampart hillfort phase"
            },
            {
                "op": "MERGE",
                "source_key": "Nemirov Hillfort-Ukraine",
                "target_key": "Nemyriv-Ukraine",
                "reason": "Old Rus medieval hillfort continuous with modern town of Nemyriv"
            },
            {
                "op": "RENAME_META",
                "key": "Nemyriv Hillfort Bronze Age Site-Ukraine",
                "new_name": "Nemyriv (Bronze Age)",
                "reason": "Pre-hiatus Bronze Age settlement phase at Nemyriv hillfort"
            },
            {
                "op": "RENAME_META",
                "key": "Nemyriv Hillfort Iron Age Site-Ukraine",
                "new_name": "Nemyriv (Iron Age)",
                "reason": "Scythian-era Great Hillfort rampart complex at Nemyriv"
            },
            {
                "op": "RENAME_META",
                "key": "Nemyriv Hillfort Iron Age Site 2-Ukraine",
                "new_name": "Nemyriv (Roman Period)",
                "reason": "Chernyakhov / Roman-period settlement phase at Nemyriv hillfort"
            }
        ],
        "clean_names": {
            "Nemyriv-Ukraine": "Nemyriv",
            "Nemyriv Hillfort Bronze Age Site-Ukraine": "Nemyriv (Bronze Age)",
            "Nemyriv Hillfort Iron Age Site-Ukraine": "Nemyriv (Iron Age)",
            "Nemyriv Hillfort Iron Age Site 2-Ukraine": "Nemyriv (Roman Period)"
        }
    },
    "C0003": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Arkheolohichnyy obyekt Mediaeval Hillfort II-Ukraine",
                "target_key": "Svyatohirsk-Ukraine",
                "reason": "Medieval hillfort at Svyatohirsk continuous within 171-year gap of modern settlement series"
            },
            {
                "op": "KEEP_HOMONYM",
                "key": "Teplinskoye-Ukraine",
                "reason": "Distinct modern settlement in Luhansk Oblast 175 km away legitimately sharing name"
            },
            {
                "op": "RENAME_META",
                "key": "Teplinskoye-Ukraine_2",
                "new_name": "Teplinske",
                "reason": "Saltovo-Mayaki fortress and gorodishche near Bogorodichnoye on Seversky Donets"
            },
            {
                "op": "RENAME_META",
                "key": "Novoselovka Donets-Ukraine",
                "new_name": "Novoselivka (Saltovo)",
                "reason": "Early medieval Saltovo metallurgical settlement on Seversky Donets"
            },
            {
                "op": "RENAME_META",
                "key": "Svyatohorske Iron Age Hillfort-Ukraine",
                "new_name": "Svyatohirsk (Iron Age)",
                "reason": "Pre-hiatus Iron Age hillfort site at Svyatohirsk"
            }
        ],
        "clean_names": {
            "Svyatohirsk-Ukraine": "Svyatohirsk",
            "Novoselivka-Ukraine": "Novoselivka",
            "Teplinskoye-Ukraine": "Teplinskoye",
            "Teplinskoye-Ukraine_2": "Teplinske",
            "Novoselovka Donets-Ukraine": "Novoselivka (Saltovo)",
            "Svyatohorske Iron Age Hillfort-Ukraine": "Svyatohirsk (Iron Age)"
        }
    },
    "C0004": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Ushki I-Russia",
                "new_name": "Ushki I (Medieval)",
                "reason": "Medieval Itelmen archaeological layer at Ushki Lake site I"
            },
            {
                "op": "RENAME_META",
                "key": "Ushki I Iron Age Site-Russia",
                "new_name": "Ushki I (Iron Age)",
                "reason": "Iron Age cultural layer at Ushki Lake site I"
            },
            {
                "op": "RENAME_META",
                "key": "Ushki I Bronze Age Site-Russia",
                "new_name": "Ushki I (Bronze Age)",
                "reason": "Bronze Age cultural layer at Ushki Lake site I"
            },
            {
                "op": "RENAME_META",
                "key": "Ushki I Stone Age Site 2-Russia",
                "new_name": "Ushki I (Neolithic)",
                "reason": "Neolithic cultural layer at Ushki Lake site I"
            },
            {
                "op": "RENAME_META",
                "key": "Ushki I Stone Age Site-Russia",
                "new_name": "Ushki I (Palaeolithic)",
                "reason": "Terminal Palaeolithic cultural layer at Ushki Lake site I"
            },
            {
                "op": "RENAME_META",
                "key": "Ushki V Palaeolithic Camp-Russia",
                "new_name": "Ushki V",
                "reason": "Distinct archaeological site complex V at Ushki Lake"
            }
        ],
        "clean_names": {
            "Ushki I-Russia": "Ushki I (Medieval)",
            "Ushki I Iron Age Site-Russia": "Ushki I (Iron Age)",
            "Ushki I Bronze Age Site-Russia": "Ushki I (Bronze Age)",
            "Ushki I Stone Age Site 2-Russia": "Ushki I (Neolithic)",
            "Ushki I Stone Age Site-Russia": "Ushki I (Palaeolithic)",
            "Ushki V Palaeolithic Camp-Russia": "Ushki V"
        }
    },
    "C0005": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Vasil evka, Vasilyevka III Palaeolithic Camp-Ukraine",
                "new_name": "Vasylivka III",
                "reason": "Epipalaeolithic/Mesolithic cemetery and campsite Vasylivka III on Dnieper Rapids"
            },
            {
                "op": "RENAME_META",
                "key": "Vasilyevka II Mesolithic Settlement-Ukraine",
                "new_name": "Vasylivka II",
                "reason": "Mesolithic cemetery and settlement Vasylivka II on Dnieper Rapids"
            },
            {
                "op": "RENAME_META",
                "key": "Vasilievka 2 Stone Age Hillfort-Ukraine",
                "new_name": "Vasylivka 2",
                "reason": "Stone Age settlement site Vasylivka 2"
            },
            {
                "op": "RENAME_META",
                "key": "Vasilyevka 5 Mesolithic Settlement-Ukraine",
                "new_name": "Vasylivka 5",
                "reason": "Mesolithic settlement site Vasylivka 5"
            },
            {
                "op": "RENAME_META",
                "key": "Vasylivka Neolithic Settlement-Ukraine",
                "new_name": "Vasylivka (Neolithic)",
                "reason": "Neolithic settlement site near Vasylivka on Dnieper Rapids"
            },
            {
                "op": "RENAME_META",
                "key": "Paleolitychna stoyanka Palaeolithic Camp-Ukraine",
                "new_name": "Vasylivka (Palaeolithic)",
                "reason": "Palaeolithic campsite near Voroniy island at Vasylivka"
            }
        ],
        "clean_names": {
            "Vasil evka, Vasilyevka III Palaeolithic Camp-Ukraine": "Vasylivka III",
            "Vasilyevka II Mesolithic Settlement-Ukraine": "Vasylivka II",
            "Vasilievka 2 Stone Age Hillfort-Ukraine": "Vasylivka 2",
            "Vasilyevka 5 Mesolithic Settlement-Ukraine": "Vasylivka 5",
            "Vasylivka Neolithic Settlement-Ukraine": "Vasylivka (Neolithic)",
            "Paleolitychna stoyanka Palaeolithic Camp-Ukraine": "Vasylivka (Palaeolithic)"
        }
    },
    "C0006": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Surskij ostrov 1 1 Mesolithic Camp Hillfort-Ukraine",
                "target_key": "Surskoy Island-Ukraine",
                "reason": "Duplicate scrape of Sursky Island Mesolithic-Neolithic site on Dnieper Rapids"
            },
            {
                "op": "MERGE",
                "source_key": "Surskij ostrov I Mesolithic Settlement-Ukraine",
                "target_key": "Surskoy Island-Ukraine",
                "reason": "Duplicate scrape of Sursky Island Mesolithic-Neolithic type-site"
            },
            {
                "op": "RENAME_META",
                "key": "Surskoy Island-Ukraine",
                "new_name": "Surskyi Ostriv",
                "reason": "Standard Ukrainian archaeological toponym for Sursky Island type-site"
            },
            {
                "op": "RENAME_META",
                "key": "Voloshskoye Penkovka-Ukraine",
                "new_name": "Voloske (Penkovka)",
                "reason": "Early Slavic Penkovka-culture settlement at Voloske with >900-year hiatus to modern village"
            },
            {
                "op": "RENAME_META",
                "key": "Voloske Mesolithic-Ukraine",
                "new_name": "Voloske (Mesolithic)",
                "reason": "Pre-hiatus Mesolithic burial and campsite on Dnieper Rapids at Voloske"
            }
        ],
        "clean_names": {
            "Voloske-Ukraine": "Voloske",
            "Surskoy Island-Ukraine": "Surskyi Ostriv",
            "Voloshskoye Penkovka-Ukraine": "Voloske (Penkovka)",
            "Voloske Mesolithic-Ukraine": "Voloske (Mesolithic)"
        }
    },
    "C0007": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "dvosharove doby piznoyi bronzy ta rymskoho chasu Kalcheva IV Bronze Age Settlement-Ukraine",
                "new_name": "Kalcheva IV",
                "reason": "Numbered multi-period archaeological settlement site IV at Kalcheva"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove doby piznoyi bronzy ta rymskoho chasu Kalcheva VI Bronze Age Settlement-Ukraine",
                "new_name": "Kalcheva VI",
                "reason": "Numbered multi-period archaeological settlement site VI at Kalcheva"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove doby piznoyi bronzy ta balkano-dunayskoyi k-ry Kalcheva VIII Bronze Age Settlement-Ukraine",
                "new_name": "Kalcheva VIII",
                "reason": "Numbered multi-period archaeological settlement site VIII at Kalcheva"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove doby piznoyi bronzy ta chernyakhivske Kalcheva KhII Bronze Age Settlement-Ukraine",
                "new_name": "Kalcheva XII",
                "reason": "Numbered multi-period archaeological settlement site XII at Kalcheva"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove doby piznoyi bronzy ta chernyakhivske Kalcheva Bronze Age Settlement II-Ukraine",
                "new_name": "Kalcheva II",
                "reason": "Numbered multi-period archaeological settlement site II at Kalcheva"
            },
            {
                "op": "RENAME_META",
                "key": "bahatosharove doby piznoyi bronzy Bronze Age Settlement-Ukraine",
                "new_name": "Kalcheva (Bronze Age)",
                "reason": "Late Bronze Age settlement site near Kalcheva"
            }
        ],
        "clean_names": {
            "dvosharove doby piznoyi bronzy ta rymskoho chasu Kalcheva IV Bronze Age Settlement-Ukraine": "Kalcheva IV",
            "dvosharove doby piznoyi bronzy ta rymskoho chasu Kalcheva VI Bronze Age Settlement-Ukraine": "Kalcheva VI",
            "dvosharove doby piznoyi bronzy ta balkano-dunayskoyi k-ry Kalcheva VIII Bronze Age Settlement-Ukraine": "Kalcheva VIII",
            "dvosharove doby piznoyi bronzy ta chernyakhivske Kalcheva KhII Bronze Age Settlement-Ukraine": "Kalcheva XII",
            "dvosharove doby piznoyi bronzy ta chernyakhivske Kalcheva Bronze Age Settlement II-Ukraine": "Kalcheva II",
            "bahatosharove doby piznoyi bronzy Bronze Age Settlement-Ukraine": "Kalcheva (Bronze Age)"
        }
    },
    "C0008": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "mezolitychna Vasylivka Mesolithic Camp II-Ukraine",
                "target_key": "Vasylivka Stone Age Hillfort-Ukraine",
                "reason": "Duplicate scrape of prehistoric campsite near Kiliya/Danube"
            },
            {
                "op": "RENAME_META",
                "key": "Vasylivka Stone Age Hillfort-Ukraine",
                "new_name": "Vasylivka (Stone Age)",
                "reason": "Stone Age campsite near Kiliya, 26 km southeast of Vasylivka village"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove doby piznoyi bronzy ta chernyakhivske Vasylivka Bronze Age Settlement-Ukraine",
                "new_name": "Vasylivka (Bronze Age)",
                "reason": "Late Bronze Age and Chernyakhov settlement site at Vasylivka"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove doby piznoyi bronzy ta chernyakhivske Vasylivka VIII Bronze Age Settlement-Ukraine",
                "new_name": "Vasylivka VIII",
                "reason": "Numbered archaeological settlement site VIII at Vasylivka"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove rymskoho chasu ta balkano-dunayskoyi kultury pivdennykh slovyan Vasylivka VI Classical Polis-Ukraine",
                "new_name": "Vasylivka VI",
                "reason": "Numbered Roman-period and early Slavic settlement site VI at Vasylivka"
            }
        ],
        "clean_names": {
            "Vasylivka_UA_17-Ukraine": "Vasylivka",
            "Vasylivka Stone Age Hillfort-Ukraine": "Vasylivka (Stone Age)",
            "dvosharove doby piznoyi bronzy ta chernyakhivske Vasylivka Bronze Age Settlement-Ukraine": "Vasylivka (Bronze Age)",
            "dvosharove doby piznoyi bronzy ta chernyakhivske Vasylivka VIII Bronze Age Settlement-Ukraine": "Vasylivka VIII",
            "dvosharove rymskoho chasu ta balkano-dunayskoyi kultury pivdennykh slovyan Vasylivka VI Classical Polis-Ukraine": "Vasylivka VI"
        }
    },
    "C0009": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Suvorovo Katlabukh-Ukraine",
                "new_name": "Katlabukh",
                "reason": "Ancient and medieval multi-period settlement on Lake Katlabukh"
            },
            {
                "op": "RENAME_META",
                "key": "balkano-dunayske pivdennykh slovyan Suvorove Mediaeval Hillfort-Ukraine",
                "new_name": "Suvorove (Medieval)",
                "reason": "Balkan-Danubian South Slavic medieval hillfort near Suvorove"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove sabatynivske ta chernyakhivske Suvorove VII Chernyakhov Settlement-Ukraine",
                "new_name": "Suvorove VII",
                "reason": "Numbered Sabatynivka and Chernyakhov settlement site VII at Suvorove"
            },
            {
                "op": "RENAME_META",
                "key": "sabatynivske Suvorove VIII Bronze Age Settlement-Ukraine",
                "new_name": "Suvorove VIII",
                "reason": "Numbered Bronze Age Sabatynivka settlement site VIII at Suvorove"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove sabatynivske ta rymskoho chasu Katlabukh Bronze Age Settlement-Ukraine",
                "new_name": "Katlabukh (Bronze Age)",
                "reason": "Sabatynivka Bronze Age settlement on Lake Katlabukh"
            }
        ],
        "clean_names": {
            "Katlabuh-Ukraine": "Katlabuh",
            "Suvorovo Katlabukh-Ukraine": "Katlabukh",
            "balkano-dunayske pivdennykh slovyan Suvorove Mediaeval Hillfort-Ukraine": "Suvorove (Medieval)",
            "dvosharove sabatynivske ta chernyakhivske Suvorove VII Chernyakhov Settlement-Ukraine": "Suvorove VII",
            "sabatynivske Suvorove VIII Bronze Age Settlement-Ukraine": "Suvorove VIII",
            "dvosharove sabatynivske ta rymskoho chasu Katlabukh Bronze Age Settlement-Ukraine": "Katlabukh (Bronze Age)"
        }
    },
    "C0010": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Andreyaul-Russia",
                "target_key": "Endirey-Russia",
                "reason": "Andreyaul is the historical Russian name and earlier series of the town Endirey"
            },
            {
                "op": "MERGE",
                "source_key": "Andreyaul-Russia_2",
                "target_key": "Andreyaul Medieval Gorodishche-Russia",
                "reason": "Duplicate node of early medieval Andreyaul gorodishche complex"
            },
            {
                "op": "RENAME_META",
                "key": "Andreyaul Medieval Gorodishche-Russia",
                "new_name": "Endirey (Early Medieval)",
                "reason": "Pre-hiatus Khazar-period fortified centre with >400-year hiatus to modern Endirey"
            },
            {
                "op": "RENAME_META",
                "key": "Andreyaul Iron Age Site-Russia",
                "new_name": "Endirey (Iron Age)",
                "reason": "Pre-hiatus Iron Age settlement phase at Endirey"
            }
        ],
        "clean_names": {
            "Endirey-Russia": "Endirey",
            "Andreyaul Medieval Gorodishche-Russia": "Endirey (Early Medieval)",
            "Andreyaul Iron Age Site-Russia": "Endirey (Iron Age)"
        }
    },
    "C0012": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Ground wall of Ryazan Kremlin-Russia",
                "reason": "Defensive earthwork wall heritage registry feature inside Ryazan kremlin with fabricated dates"
            },
            {
                "op": "MERGE",
                "source_key": "Pereyaslavl-Ryazansky Gorodishche-Russia",
                "target_key": "R'azan'-Russia",
                "reason": "Pereyaslavl-Ryazansky is the historic fortified core and historic name of Ryazan"
            },
            {
                "op": "MERGE",
                "source_key": "Borki-Oka-Russia",
                "target_key": "Borki-Ryazan Gorodishche-Russia",
                "reason": "Duplicate coordinate scrape of Borki archaeological complex near Ryazan"
            },
            {
                "op": "RENAME_META",
                "key": "Borki-Ryazan Gorodishche-Russia",
                "new_name": "Borki (Ryazan)",
                "reason": "Oka-Ryazan culture early medieval gorodishche and burial ground at Borki"
            }
        ],
        "clean_names": {
            "R'azan'-Russia": "Ryazan",
            "Borki-Ryazan Gorodishche-Russia": "Borki (Ryazan)"
        }
    },
    "C0013": {
        "actions": [
            {
                "op": "KEEP_HOMONYM",
                "key": "Horodnytsia-Ukraine",
                "reason": "Distinct modern urban settlement in Zhytomyr Oblast 269 km away legitimately sharing name"
            },
            {
                "op": "RENAME_META",
                "key": "Horodenka-Ukraine_2",
                "new_name": "Horodenka (Medieval)",
                "reason": "Old Rus fortress of Horodenka separated by >370-year hiatus from modern town records"
            },
            {
                "op": "RENAME_META",
                "key": "Horodnytsia-Ukraine_2",
                "new_name": "Horodnytsia-on-Dniester",
                "reason": "Medieval Old Rus hillfort at Horodnytsia village on Dniester, Ivano-Frankivsk Oblast"
            },
            {
                "op": "RENAME_META",
                "key": "Horodnytsia Bronze Age Site-Ukraine",
                "new_name": "Horodnytsia (Bronze Age)",
                "reason": "Bronze Age / Trypillia settlement site at Horodnytsia on Dniester"
            }
        ],
        "clean_names": {
            "Horodenka-Ukraine": "Horodenka",
            "Horodenka-Ukraine_2": "Horodenka (Medieval)",
            "Horodnytsia-Ukraine": "Horodnytsia",
            "Horodnytsia-Ukraine_2": "Horodnytsia-on-Dniester",
            "Horodnytsia Bronze Age Site-Ukraine": "Horodnytsia (Bronze Age)"
        }
    },
    "C0014": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Lysaya Gora Stone Age Hillfort-Ukraine",
                "target_key": "Lysaya Gora Neolithic-Ukraine",
                "reason": "Overlapping Stone Age settlement phase at Lysa Hora Vasylivka"
            },
            {
                "op": "RENAME_META",
                "key": "Balky Iron Age Hillfort-Ukraine",
                "new_name": "Balky (Iron Age)",
                "reason": "Pre-hiatus Scythian Iron Age hillfort at Balky village"
            },
            {
                "op": "RENAME_META",
                "key": "Lysaya Gora Classical Polis-Ukraine",
                "new_name": "Lysa Hora (Classical)",
                "reason": "Classical / Roman-period settlement site at Lysa Hora on Kakhovka Reservoir"
            },
            {
                "op": "RENAME_META",
                "key": "Lysaya Gora Neolithic-Ukraine",
                "new_name": "Lysa Hora (Neolithic)",
                "reason": "Famous Azov-Dnieper culture Neolithic type-site at Lysa Hora"
            }
        ],
        "clean_names": {
            "Balky-Ukraine": "Balky",
            "Balky Iron Age Hillfort-Ukraine": "Balky (Iron Age)",
            "Lysaya Gora Classical Polis-Ukraine": "Lysa Hora (Classical)",
            "Lysaya Gora Neolithic-Ukraine": "Lysa Hora (Neolithic)"
        }
    },
    "C0015": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Marianivka Neolithic Bronze Age Type-Site-Ukraine",
                "new_name": "Marianivka (Neolithic)",
                "reason": "Famous Marianivka culture Neolithic-Bronze Age type-site on Seym river"
            },
            {
                "op": "RENAME_META",
                "key": "Marianivka Bronze Age Site-Ukraine",
                "new_name": "Marianivka (Bronze Age)",
                "reason": "Bronze Age settlement site at Marianivka"
            },
            {
                "op": "RENAME_META",
                "key": "Marianivka Iron Age Site-Ukraine",
                "new_name": "Marianivka (Iron Age)",
                "reason": "Early Iron Age Scythian-era settlement at Marianivka"
            },
            {
                "op": "RENAME_META",
                "key": "Marianivka Iron Age Site 2-Ukraine",
                "new_name": "Marianivka (Roman Period)",
                "reason": "Late Iron Age / Roman-period Chernyakhov settlement at Marianivka"
            },
            {
                "op": "RENAME_META",
                "key": "Marianivka Medieval Settlement-Ukraine",
                "new_name": "Marianivka (Medieval)",
                "reason": "Early medieval Slavic / Old Rus settlement at Marianivka"
            }
        ],
        "clean_names": {
            "Marianivka Neolithic Bronze Age Type-Site-Ukraine": "Marianivka (Neolithic)",
            "Marianivka Bronze Age Site-Ukraine": "Marianivka (Bronze Age)",
            "Marianivka Iron Age Site-Ukraine": "Marianivka (Iron Age)",
            "Marianivka Iron Age Site 2-Ukraine": "Marianivka (Roman Period)",
            "Marianivka Medieval Settlement-Ukraine": "Marianivka (Medieval)"
        }
    },
    "C0016": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Mezin Stone Age Site-Ukraine",
                "new_name": "Mezyn (Palaeolithic)",
                "reason": "World-famous Mezyn Upper Palaeolithic mammoth-bone campsite"
            },
            {
                "op": "RENAME_META",
                "key": "Mezin Iron Age Site-Ukraine",
                "new_name": "Mezyn (Iron Age)",
                "reason": "Early Iron Age settlement at Mezyn on Desna river"
            },
            {
                "op": "RENAME_META",
                "key": "Mezin Iron Age Site 2-Ukraine",
                "new_name": "Mezyn (Roman Period)",
                "reason": "Roman-period / late antique settlement phase at Mezyn"
            },
            {
                "op": "RENAME_META",
                "key": "Khoromky Iron Age Hillfort-Ukraine",
                "new_name": "Khoromky",
                "reason": "Distinct Yukhnovo culture Iron Age hillfort at Khoromky near Mezyn"
            }
        ],
        "clean_names": {
            "Mezin-Ukraine": "Mezyn",
            "Mezin Stone Age Site-Ukraine": "Mezyn (Palaeolithic)",
            "Mezin Iron Age Site-Ukraine": "Mezyn (Iron Age)",
            "Mezin Iron Age Site 2-Ukraine": "Mezyn (Roman Period)",
            "Khoromky Iron Age Hillfort-Ukraine": "Khoromky"
        }
    },
    "C0017": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Rakushecnyj Jar Neolithic Settlement-Russia",
                "target_key": "Rakushechny Yar-Russia",
                "reason": "Duplicate scrape of Rakushechny Yar Neolithic shell-mound type-site"
            },
            {
                "op": "RENAME_META",
                "key": "Rakushechny Yar-Russia",
                "new_name": "Rakushechny Yar",
                "reason": "World-famous Neolithic shell-mound type-site on Porechny island"
            },
            {
                "op": "RENAME_META",
                "key": "Razdorskaya-1-Russia",
                "new_name": "Razdorskaya I",
                "reason": "Multi-stratum Neolithic and Eneolithic settlement Razdorskaya I"
            },
            {
                "op": "RENAME_META",
                "key": "Razdorskaya-2-Russia",
                "new_name": "Razdorskaya 2",
                "reason": "Mesolithic settlement and campsite Razdorskaya 2 on Don river"
            }
        ],
        "clean_names": {
            "Razdorskaya-Russia": "Razdorskaya",
            "Rakushechny Yar-Russia": "Rakushechny Yar",
            "Razdorskaya-1-Russia": "Razdorskaya I",
            "Razdorskaya-2-Russia": "Razdorskaya 2"
        }
    },
    "C0021": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Berezyne Eneolithic Hillfort-Ukraine",
                "new_name": "Berezyne (Eneolithic)",
                "reason": "Pre-hiatus Eneolithic / Usatovo hillfort site at Berezyne"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove Berezyne VII doby piznoyi bronzy ta chernyakhivske Bronze Age Settlement-Ukraine",
                "new_name": "Berezyne VII",
                "reason": "Numbered Late Bronze Age and Chernyakhov settlement site VII at Berezyne"
            },
            {
                "op": "RENAME_META",
                "key": "rymskoho chasu Berezyne IV Classical Polis-Ukraine",
                "new_name": "Berezyne IV",
                "reason": "Numbered Roman-period settlement site IV at Berezyne"
            },
            {
                "op": "RENAME_META",
                "key": "chernyakhivske Berezyne I Chernyakhov Settlement-Ukraine",
                "new_name": "Berezyne I",
                "reason": "Numbered Chernyakhov settlement site I at Berezyne"
            },
            {
                "op": "RENAME_META",
                "key": "chernyakhivske Berezyne-Pivnichne Chernyakhov Settlement-Ukraine",
                "new_name": "Berezyne Pivnichne",
                "reason": "Northern Chernyakhov settlement site at Berezyne"
            }
        ],
        "clean_names": {
            "Berezyne Eneolithic Hillfort-Ukraine": "Berezyne (Eneolithic)",
            "dvosharove Berezyne VII doby piznoyi bronzy ta chernyakhivske Bronze Age Settlement-Ukraine": "Berezyne VII",
            "rymskoho chasu Berezyne IV Classical Polis-Ukraine": "Berezyne IV",
            "chernyakhivske Berezyne I Chernyakhov Settlement-Ukraine": "Berezyne I",
            "chernyakhivske Berezyne-Pivnichne Chernyakhov Settlement-Ukraine": "Berezyne Pivnichne"
        }
    },
    "C0022": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "balkano-dunayskoyi k-ry pivdennykh slovyan Stari Troyany Rus Hillfort-Ukraine",
                "new_name": "Stari Troyany (Rus)",
                "reason": "Balkan-Danubian early medieval South Slavic hillfort at Stari Troyany"
            },
            {
                "op": "RENAME_META",
                "key": "bahatosharove sabatynivske Chernyakhov Settlement II-Ukraine",
                "new_name": "Stari Troyany (Chernyakhov)",
                "reason": "Multi-period Sabatynivka and Chernyakhov settlement at Stari Troyany"
            },
            {
                "op": "RENAME_META",
                "key": "rymskoho chasu Stari Troyany Classical Polis-Ukraine",
                "new_name": "Stari Troyany (Classical)",
                "reason": "Roman-era settlement site near Stari Troyany"
            },
            {
                "op": "RENAME_META",
                "key": "bahatosharove sabatynivske Rus Hillfort-Ukraine",
                "new_name": "Pryozerne (Rus)",
                "reason": "Multi-period Sabatynivka and Rus hillfort near Pryozerne village"
            },
            {
                "op": "RENAME_META",
                "key": "dvosharove sabatynivske ta chernyakhivske Pryozerne Chernyakhov Settlement-Ukraine",
                "new_name": "Pryozerne (Chernyakhov)",
                "reason": "Two-layer Sabatynivka and Chernyakhov settlement near Pryozerne"
            }
        ],
        "clean_names": {
            "balkano-dunayskoyi k-ry pivdennykh slovyan Stari Troyany Rus Hillfort-Ukraine": "Stari Troyany (Rus)",
            "bahatosharove sabatynivske Chernyakhov Settlement II-Ukraine": "Stari Troyany (Chernyakhov)",
            "rymskoho chasu Stari Troyany Classical Polis-Ukraine": "Stari Troyany (Classical)",
            "bahatosharove sabatynivske Rus Hillfort-Ukraine": "Pryozerne (Rus)",
            "dvosharove sabatynivske ta chernyakhivske Pryozerne Chernyakhov Settlement-Ukraine": "Pryozerne (Chernyakhov)"
        }
    },
    "C0024": {
        "actions": [
            {
                "op": "MERGE",
                "source_key": "Barsova Gora Iron Age Site 2-Russia",
                "target_key": "Barsova Gora 2-Russia",
                "reason": "Overlapping cultural layer of archaeological site Barsova Gora 2"
            },
            {
                "op": "RENAME_META",
                "key": "Barsova Gora 2-Russia",
                "new_name": "Barsova Gora (Medieval)",
                "reason": "Early medieval fortified centre at Barsova Gora on Ob river"
            },
            {
                "op": "RENAME_META",
                "key": "Barsova Gora Iron Age Site-Russia",
                "new_name": "Barsova Gora (Iron Age)",
                "reason": "Early Iron Age Kulay culture fortified settlement at Barsova Gora"
            }
        ],
        "clean_names": {
            "Barsovo-Russia": "Barsovo",
            "Barsova Gora 2-Russia": "Barsova Gora (Medieval)",
            "Barsova Gora Iron Age Site-Russia": "Barsova Gora (Iron Age)"
        }
    },
    "C0025": {
        "actions": [
            {
                "op": "KEEP_HOMONYM",
                "key": "Belgatoy-Russia",
                "reason": "Distinct modern village in Shali Raion 18 km north of Belgatoy in Vedeno Raion"
            },
            {
                "op": "KEEP_HOMONYM",
                "key": "Belgatoy-Russia_2",
                "reason": "Historical highland village Belgatoy in Vedeno Raion"
            },
            {
                "op": "RENAME_META",
                "key": "Belgatoy Medieval Gorodishche-Russia",
                "new_name": "Belgatoy (Medieval)",
                "reason": "Medieval highland hillfort near Belgatoy in Vedeno Raion"
            },
            {
                "op": "RENAME_META",
                "key": "Belgatoy Bronze Age Site-Russia",
                "new_name": "Belgatoy (Bronze Age)",
                "reason": "Koban Bronze Age settlement site near Belgatoy in Vedeno Raion"
            }
        ],
        "clean_names": {
            "Belgatoy-Russia": "Belgatoy",
            "Belgatoy-Russia_2": "Belgatoy",
            "Belgatoy Medieval Gorodishche-Russia": "Belgatoy (Medieval)",
            "Belgatoy Bronze Age Site-Russia": "Belgatoy (Bronze Age)"
        }
    }
}
