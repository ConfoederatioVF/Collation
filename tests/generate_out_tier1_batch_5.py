import json

# Full decision generator for tier1_batch_5.json
raw_data = json.load(open('f:/Active Projects/Project 1509 - SVEA/tests/polaris_batches/tier1_batch_5.json', encoding='utf-8'))

decisions_list = []

# Mapping from cluster_id to decision specification
# Each spec has:
# actions: list of action dicts
# clean_names: dict of surviving_key -> clean display name

specs = {
    # 0: C0747
    "C0747": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Khadjibey Castle-Ukraine",
            "target_key": "Odesa-Ukraine",
            "reason": "Khadjibey Castle (Kotsiubiiv) was the direct Lithuanian and Ottoman predecessor fortress of Odesa on the same harbour site; continuous settlement series with zero gap at 1400."
        }],
        "clean_names": {"Odesa-Ukraine": "Odesa"}
    },
    # 1: C0748
    "C0748": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Oktjabr'skij-Russia",
            "new_name": "Oktyabrsky",
            "reason": "Distinct urban-type settlement in Komi Republic near Vorkuta, wrongly assigned metadata name of neighbouring city Vorkuta."
        }],
        "clean_names": {
            "Oktjabr'skij-Russia": "Oktyabrsky",
            "Vorkuta-Russia": "Vorkuta"
        }
    },
    # 2: C0749
    "C0749": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Oktjabr'skij_RU_93-Russia",
            "new_name": "Oktyabrsky",
            "reason": "Distinct urban-type settlement in Zabaykalsky Krai (former Tulukuy) located 15.35 km from Krasnokamensk, wrongly bound to Krasnokamensk metadata."
        }],
        "clean_names": {
            "Krasnokamensk-Russia": "Krasnokamensk",
            "Oktjabr'skij_RU_93-Russia": "Oktyabrsky"
        }
    },
    # 3: C0752
    "C0752": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Olonets Medieval Gorodishche-Russia",
            "target_key": "Olonets-Russia",
            "reason": "Medieval fortified gorodishche of Olonets representing the early phase of the continuous settlement of Olonets, overlapping 1400..1500."
        }],
        "clean_names": {"Olonets-Russia": "Olonets"}
    },
    # 4: C0757
    "C0757": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Orsk_RU_55-Russia",
            "target_key": "Orsk-Russia",
            "reason": "Displaced coordinate duplicate entry of the city of Orsk; merge into canonical Orsk series."
        }],
        "clean_names": {"Orsk-Russia": "Orsk"}
    },
    # 5: C0759
    "C0759": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Ostashkovo Fortress-Russia",
            "target_key": "Ostashkov-Russia",
            "reason": "Ostashkovo Fortress was the historical fortification of Ostashkov town; overlapping continuous settlement series."
        }],
        "clean_names": {"Ostashkov-Russia": "Ostashkov"}
    },
    # 6: C0761
    "C0761": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Ozerna Castle-Ukraine",
            "target_key": "Ozerna-Ukraine",
            "reason": "Medieval castle in Ozerna representing the fortified predecessor of the continuous settlement, with gap under 200 years (1300 to 1469)."
        }],
        "clean_names": {"Ozerna-Ukraine": "Ozerna"}
    },
    # 7: C0765
    "C0765": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Pamyatky_rannoho_mezolitu 112 Mesolithic Camp-Ukraine",
            "target_key": "Maryevka Mesolithic Settlement-Ukraine",
            "reason": "Overlapping Mesolithic archaeological sites of the Nenasytets / Maryevka rapids complex on the Dnieper; merge scraper duplicate into the named Maryevka settlement node."
        }],
        "clean_names": {"Maryevka Mesolithic Settlement-Ukraine": "Maryevka"}
    },
    # 8: C0767
    "C0767": {
        "actions": [{
            "op": "DROP_JUNK",
            "key": "Pamyatnoe mesto, gde nakhodilsya Sumskiy ostrog (Sumskiy Posad)-Russia",
            "reason": "Heritage registry commemorative marker for the 1580 ostrog with fabricated medieval date (800..1300) co-located inside active settlement Sumsky Posad."
        }],
        "clean_names": {"Sumskiy Posad-Russia": "Sumsky Posad"}
    },
    # 9: C0768
    "C0768": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Partenit-Ukraine_2",
            "new_name": "Partenit (Medieval)",
            "reason": "Early Byzantine Parthenitai / medieval settlement separated by a post-1400 hiatus of 248 years from the modern Crimean settlement of Partenit."
        }],
        "clean_names": {
            "Partenit-Ukraine": "Partenit",
            "Partenit-Ukraine_2": "Partenit (Medieval)"
        }
    },
    # 10: C0769
    "C0769": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Antychne poselennya Voloshska Kosa IV Classical Polis-Ukraine",
            "new_name": "Voloshska Kosa",
            "reason": "Distinct ancient rural settlement on Voloshska Kosa situated 2.29 km north of the main polis site of Olbia (Parutino)."
        }],
        "clean_names": {
            "Antychne poselennya Voloshska Kosa IV Classical Polis-Ukraine": "Voloshska Kosa",
            "Parutino-Ukraine": "Parutino"
        }
    },
    # 11: C0770
    "C0770": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Paselishcha peryyadu syarednyavechcha-Belarus",
            "target_key": "Garadzishcha-2 peryyadu rannyaga zhaleznaga veku-Belarus",
            "reason": "Overlapping Iron Age hillfort and medieval settlement components of the Mokhov archaeological complex in Belarus; merge into single complex entity."
        }],
        "clean_names": {"Garadzishcha-2 peryyadu rannyaga zhaleznaga veku-Belarus": "Mokhov"}
    },
    # 12: C0771
    "C0771": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Adnapolle Mediaeval Hillfort-Belarus",
                "new_name": "Adnapolle",
                "reason": "Medieval hillfort at Adnapolle village in Vetka District, distinct from neighbouring Khizy."
            },
            {
                "op": "RENAME_META",
                "key": "Paselishcha-Belarus",
                "new_name": "Khizy",
                "reason": "Medieval settlement at Khizy village in Vetka District, distinct from neighbouring Adnapolle."
            }
        ],
        "clean_names": {
            "Adnapolle Mediaeval Hillfort-Belarus": "Adnapolle",
            "Paselishcha-Belarus": "Khizy"
        }
    },
    # 13: C0772
    "C0772": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Paselishchy stayanki kremnezdabyvayuchyya shakhty maysterni peryyadu kamennaga bronzavaga i rannyaga zhaleznaga vyakou-Belarus",
            "target_key": "Krasnoselsky Bronze Age Site-Belarus",
            "reason": "Contiguous components of the famous Krasnoselsky flint extraction and workshop complex in Belarus spanning Neolithic to Bronze Age (-2500..-1000)."
        }],
        "clean_names": {"Krasnoselsky Bronze Age Site-Belarus": "Krasnoselsky"}
    },
    # 14: C0773
    "C0773": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Pavlinovo-Russia_2",
            "target_key": "Pavlinovo-Russia",
            "reason": "Displaced coordinate twin entries for the famous Sargatka culture Pavlinovo Gorodishche in the Trans-Ural forest-steppe representing consecutive phases (-400..100 and 100..350)."
        }],
        "clean_names": {"Pavlinovo-Russia": "Pavlinovo"}
    },
    # 15: C0774
    "C0774": {
        "actions": [{
            "op": "KEEP_HOMONYM",
            "key": "Pavlovo-Russia_2",
            "reason": "Distinct historical towns legitimately sharing the name Pavlovo (Pavlovo on Oka in Nizhny Novgorod Oblast vs Pavlovo in Leningrad Oblast, 836 km apart)."
        }],
        "clean_names": {
            "Pavlovo-Russia": "Pavlovo",
            "Pavlovo-Russia_2": "Pavlovo"
        }
    },
    # 16: C0778
    "C0778": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Peravoz Mediaeval Hillfort-Belarus",
            "target_key": "Peravoz Rasonskaga Mediaeval Hillfort-Belarus",
            "reason": "Duplicate archaeological entries for the medieval hillfort of Peravoz in Rasony District; merge into primary node."
        }],
        "clean_names": {"Peravoz Rasonskaga Mediaeval Hillfort-Belarus": "Peravoz"}
    },
    # 17: C0779
    "C0779": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Pereginskiy zamok-Ukraine",
            "target_key": "Perehinske-Ukraine",
            "reason": "Medieval castle in Perehinske representing the fortified predecessor of the town, with a gap under 200 years (1300 to 1400)."
        }],
        "clean_names": {"Perehinske-Ukraine": "Perehinske"}
    },
    # 18: C0780
    "C0780": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Perovo-Russia_2",
            "target_key": "Perovo-Russia",
            "reason": "Consecutive historical phases of Perovo settlement near Moscow (1600..1923 and 1936..1967); merge into canonical Perovo series."
        }],
        "clean_names": {"Perovo-Russia": "Perovo"}
    },
    # 19: C0781
    "C0781": {
        "actions": [{
            "op": "DROP_JUNK",
            "key": "Pervoposelenets-Russia",
            "reason": "The 1980 bronze sculpture 'Monument to the First Settler' in Penza, anachronistically scraped with fabricated medieval dates (800..1300) inside Penza."
        }],
        "clean_names": {"Penza-Russia": "Penza"}
    },
    # 20: C0783
    "C0783": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Petrovsk-Port Gorodishche-Russia",
            "target_key": "Macha`'ckala-Russia",
            "reason": "Ancient Khazar fortress of Anzhi-Kala / Petrovsk-Port Gorodishche representing the early fortified core of modern Makhachkala, overlapping 700..800."
        }],
        "clean_names": {"Macha`'ckala-Russia": "Makhachkala"}
    },
    # 21: C0786
    "C0786": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Chekhutove Iron Age Hillfort-Ukraine",
                "new_name": "Chekhutove",
                "reason": "Distinct fortified rural settlement of the Olbian chora on the Dnieper-Bug Liman at Chekhutove."
            },
            {
                "op": "RENAME_META",
                "key": "Petukhovka-Ukraine",
                "new_name": "Petukhovka",
                "reason": "Distinct fortified rural settlement of the Olbian chora on the Dnieper-Bug Liman at Petukhivka."
            }
        ],
        "clean_names": {
            "Chekhutove Iron Age Hillfort-Ukraine": "Chekhutove",
            "Petukhovka-Ukraine": "Petukhovka"
        }
    },
    # 22: C0789
    "C0789": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Plesozero 1 (stoyanka No 1 po G. I. Goretskomu)-Russia",
            "new_name": "Plesozero 1",
            "reason": "Prehistoric/medieval campsite on Lake Plesozero situated 5 km from the modern industrial settlement of Nivsky."
        }],
        "clean_names": {
            "Nivskiy-Russia": "Nivskiy",
            "Plesozero 1 (stoyanka No 1 po G. I. Goretskomu)-Russia": "Plesozero 1"
        }
    },
    # 23: C0792
    "C0792": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Pochinki, Pochinkovsky District, Nizhny Novgorod Oblast-Russia",
            "target_key": "Pochinki-Russia",
            "reason": "Duplicate contemporary entries for Pochinki in Pochinkovsky District, Nizhny Novgorod Oblast."
        }],
        "clean_names": {"Pochinki-Russia": "Pochinki"}
    },
    # 24: C0793
    "C0793": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Novomoskovsk-Kurgan Majdan Eneolithic Hillfort-Ukraine",
                "new_name": "Novomoskovsk Majdan",
                "reason": "Distinct Eneolithic kurgan sanctuary site located at Novomoskovsk, 8.88 km from Pidhorodne."
            },
            {
                "op": "RENAME_META",
                "key": "Podgorodnoe-Kurgan 3 Eneolithic Hillfort-Ukraine",
                "new_name": "Pidhorodne Kurgan 3",
                "reason": "Distinct Eneolithic kurgan site located at Pidhorodne, 8.88 km from Novomoskovsk."
            }
        ],
        "clean_names": {
            "Novomoskovsk-Kurgan Majdan Eneolithic Hillfort-Ukraine": "Novomoskovsk Majdan",
            "Podgorodnoe-Kurgan 3 Eneolithic Hillfort-Ukraine": "Pidhorodne Kurgan 3"
        }
    },
    # 25: C0794
    "C0794": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Pidhorivka Neolithic Settlement-Ukraine",
            "target_key": "Podgorovka Stone Age Hillfort-Ukraine",
            "reason": "Overlapping Stone Age and Neolithic archaeological settlement phases at Pidhorivka in Luhansk Oblast."
        }],
        "clean_names": {"Podgorovka Stone Age Hillfort-Ukraine": "Pidhorivka"}
    },
    # 26: C0797
    "C0797": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Polatskae garadzishcha-Belarus",
            "target_key": "Polack-Belarus",
            "reason": "Ancient fortified hillfort of Polotsk at the mouth of the Polota river representing the early fortified core of continuous Polotsk, overlapping 800..1200."
        }],
        "clean_names": {"Polack-Belarus": "Polotsk"}
    },
    # 27: C0798
    "C0798": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Dnistrivka-Govdochky Eneolithic Hillfort-Ukraine",
                "new_name": "Dnistrivka Hovdochky",
                "reason": "Distinct Eneolithic Trypillia hillfort on the Dniester at Dnistrivka."
            },
            {
                "op": "RENAME_META",
                "key": "Polivanov Yar-Ukraine",
                "new_name": "Polivanov Yar",
                "reason": "World-renowned eponymous multilayered Trypillia settlement site in the Dniester valley."
            }
        ],
        "clean_names": {
            "Dnistrivka-Govdochky Eneolithic Hillfort-Ukraine": "Dnistrivka Hovdochky",
            "Polivanov Yar-Ukraine": "Polivanov Yar"
        }
    },
    # 28: C0800
    "C0800": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Pomoriany Castle-Ukraine",
            "target_key": "Pomoriany-Ukraine",
            "reason": "Historic castle in Pomoriany representing the fortified predecessor of the town, with a gap under 200 years (1300 to 1500)."
        }],
        "clean_names": {"Pomoriany-Ukraine": "Pomoriany"}
    },
    # 29: C0803
    "C0803": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Popivka Bronze Age Settlement-Ukraine",
                "new_name": "Popivka (Bronze Age)",
                "reason": "Bronze Age settlement phase (-2200..-900) at Popivka, separated by distinct cultural era from the Iron Age site."
            },
            {
                "op": "RENAME_META",
                "key": "Popivka Iron Age Hillfort-Ukraine",
                "new_name": "Popivka (Iron Age)",
                "reason": "Iron Age hillfort phase (-700..-100) at Popivka, separated by distinct cultural era from the Bronze Age site."
            }
        ],
        "clean_names": {
            "Popivka Bronze Age Settlement-Ukraine": "Popivka (Bronze Age)",
            "Popivka Iron Age Hillfort-Ukraine": "Popivka (Iron Age)"
        }
    },
    # 30: C0804
    "C0804": {
        "actions": [{
            "op": "KEEP_HOMONYM",
            "key": "Popivka_UA_18-Ukraine",
            "reason": "Genuinely distinct Ukrainian villages legitimately sharing the name Popivka located 27.61 km apart."
        }],
        "clean_names": {
            "Popivka_UA_07-Ukraine": "Popivka",
            "Popivka_UA_18-Ukraine": "Popivka"
        }
    },
    # 31: C0805
    "C0805": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Porkhov Hillfort-Russia",
            "target_key": "Porkhov-Russia",
            "reason": "Porkhov Hillfort (Polyakova Myza) was the original fortified stronghold on the Shelon river founded by Alexander Nevsky, overlapping continuous Porkhov series (1239..1300)."
        }],
        "clean_names": {"Porkhov-Russia": "Porkhov"}
    },
    # 32: C0810
    "C0810": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Poshekhonye-Russia",
            "target_key": "Pošehon'je-Russia",
            "reason": "Displaced coordinate twin entries for the town of Poshekhonye (historical Pertoma); merge into canonical series."
        }],
        "clean_names": {"Pošehon'je-Russia": "Poshekhonye"}
    },
    # 33: C0811
    "C0811": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Pravoberezhnoye Tsimlyanskoye-Russia",
            "target_key": "Pravoberezhnoe Tsimlyanskoe gorodishche-Russia",
            "reason": "Duplicate entries for the Khazar white-stone fortress of Pravoberezhnoye Tsimlyanskoye gorodishche on the Don; merge into longest series."
        }],
        "clean_names": {"Pravoberezhnoe Tsimlyanskoe gorodishche-Russia": "Pravoberezhnoye Tsimlyanskoye"}
    },
    # 34: C0813
    "C0813": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Promyslovoye-Russia_2",
            "new_name": "Promyslovoye (Okhotsk)",
            "reason": "Okhotsk culture archaeological settlement on Sakhalin Island (Poronaysk Okhotsk Site), situated 6708 km from modern Promyslovoye village in Astrakhan Oblast."
        }],
        "clean_names": {
            "Promyslovoye-Russia": "Promyslovoye",
            "Promyslovoye-Russia_2": "Promyslovoye (Okhotsk)"
        }
    },
    # 35: C0814
    "C0814": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Pronskoye I Hillfort-Russia",
            "target_key": "Pronsk-Russia",
            "reason": "Pronskoye I Hillfort (Pronsky Kreml on Pokrovsky Bugor) was the fortified citadel of medieval Pronsk principality, overlapping continuous Pronsk series (1200..1501)."
        }],
        "clean_names": {"Pronsk-Russia": "Pronsk"}
    },
    # 36: C0815
    "C0815": {
        "actions": [{
            "op": "DROP_JUNK",
            "key": "Pruzhany kamennyy idol Mediaeval Hillfort-Belarus",
            "reason": "Pagan stone idol sculpture from Pruzhany ('Pruzhanski Idal'), falsely scraped as a mediaeval hillfort with fabricated population figures co-located with Pruzhany."
        }],
        "clean_names": {"Pru`zany-Belarus": "Pruzhany"}
    },
    # 37: C0818
    "C0818": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Pukhovichi-Belarus_2",
            "new_name": "Pukhovichi (Medieval)",
            "reason": "Medieval Titovka-Svisloch hillfort settlement in Pukhavichy District (Minsk Oblast), 268 km from modern Pukhovichi village in Vitebsk Oblast."
        }],
        "clean_names": {
            "Pukhovichi-Belarus": "Pukhovichi",
            "Pukhovichi-Belarus_2": "Pukhovichi (Medieval)"
        }
    },
    # 38: C0821
    "C0821": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Radun Castle-Belarus",
            "target_key": "Radun-Belarus",
            "reason": "Historic castle in Radun representing the 14th-century fortified predecessor of the town, with a gap of only 50 years (1350 to 1400)."
        }],
        "clean_names": {"Radun-Belarus": "Radun"}
    },
    # 39: C0824
    "C0824": {
        "actions": [{
            "op": "KEEP_HOMONYM",
            "key": "Revda-Russia_2",
            "reason": "Distinct historical industrial settlements legitimately sharing the name Revda (Revda in Sverdlovsk Oblast vs Revda in Murmansk Oblast, 1777 km apart)."
        }],
        "clean_names": {
            "Revda-Russia": "Revda",
            "Revda-Russia_2": "Revda"
        }
    },
    # 40: C0826
    "C0826": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Revnyanske gorodishche-Ukraine",
            "target_key": "Revne-Ukraine",
            "reason": "Duplicate entries for the major Early Slavic and Old Rus fortified sanctuary complex of Revne in Bukovina (600..1240)."
        }],
        "clean_names": {"Revne-Ukraine": "Revne"}
    },
    # 41: C0829
    "C0829": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Rodniki-Russia_2",
            "new_name": "Rodniki (Bronze Age)",
            "reason": "Sintashta/Arkaim Bronze Age fortified settlement of the Country of Towns in Chelyabinsk Oblast, located 1255 km from modern textile town of Rodniki in Ivanovo Oblast."
        }],
        "clean_names": {
            "Rodniki-Russia": "Rodniki",
            "Rodniki-Russia_2": "Rodniki (Bronze Age)"
        }
    },
    # 42: C0830
    "C0830": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Rogalik VII Palaeolithic Camp-Ukraine",
            "target_key": "Rohalyk Palaeolithic Camp-Ukraine",
            "reason": "Overlapping seasonal campsites of the Upper Palaeolithic Rohalyk complex in Luhansk Oblast; merge into longest series."
        }],
        "clean_names": {"Rohalyk Palaeolithic Camp-Ukraine": "Rohalyk"}
    },
    # 43: C0831
    "C0831": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Roishche-Ukraine",
            "target_key": "Roishche Medieval Settlement-Ukraine",
            "reason": "Consecutive Early Slavic and Old Rus settlement phases at Roishche in Chernihiv region, with gap of only 100 years (800 to 900)."
        }],
        "clean_names": {"Roishche Medieval Settlement-Ukraine": "Roishche"}
    },
    # 44: C0832
    "C0832": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Poselenie Rozhdestvenskiy ostrov (Rostov)-Russia",
            "target_key": "Rostov-Russia",
            "reason": "Archaeological settlement on Rozhdestvensky Island in Lake Nero representing an early fortified layer of ancient Rostov Veliky; continuous settlement."
        }],
        "clean_names": {"Rostov-Russia": "Rostov Veliky"}
    },
    # 45: C0835
    "C0835": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Kostyol Svyatykh Apostolov Petra i Pavla Mediaeval Hillfort-Belarus",
                "reason": "Church building ('Kostyol Svyatykh Apostolov Petra i Pavla') falsely scraped as a mediaeval hillfort with fabricated medieval dates and population."
            },
            {
                "op": "RENAME_META",
                "key": "Rozhanka kostel sv. Petra i Pavla Late Mediaeval Hillfort-Belarus",
                "new_name": "Rozhanka",
                "reason": "Surviving node accurately located at the historic settlement of Rozhanka in Shchuchyn District, cleaned from church scrape title."
            }
        ],
        "clean_names": {"Rozhanka kostel sv. Petra i Pavla Late Mediaeval Hillfort-Belarus": "Rozhanka"}
    },
    # 46: C0837
    "C0837": {
        "actions": [{
            "op": "DROP_JUNK",
            "key": "Ruiny knyazheskogo terema-Russia",
            "reason": "Architectural ruins of 12th-century princely palace inside Smolensk kremlin, anachronistically scraped as an independent settlement; explicit DROP_JUNK example."
        }],
        "clean_names": {"Smolensk-Russia": "Smolensk"}
    },
    # 47: C0840
    "C0840": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Sabulkovskoye Classical Polis-Ukraine",
            "target_key": "Sablukovka-Ukraine",
            "reason": "Overlapping Late Scythian / Classical settlement entries for Sablukivka on the Lower Dnieper; merge into primary Sablukovka series."
        }],
        "clean_names": {"Sablukovka-Ukraine": "Sablukivka"}
    },
    # 48: C0841
    "C0841": {
        "actions": [{
            "op": "KEEP_HOMONYM",
            "key": "Safonovo-Russia_2",
            "reason": "Distinct historical towns legitimately sharing the name Safonovo (Safonovo in Smolensk Oblast vs Safonovo in Murmansk Oblast, 1551 km apart)."
        }],
        "clean_names": {
            "Safonovo-Russia": "Safonovo",
            "Safonovo-Russia_2": "Safonovo"
        }
    },
    # 49: C0842
    "C0842": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Sahtysh 14 Palaeolithic Camp-Russia",
            "target_key": "Sakhtysh 14, Sahtysh 14 Palaeolithic Camp-Russia",
            "reason": "Duplicate entries for the Sakhtysh 14 Mesolithic campsite on Sakhtysh peat bog in Ivanovo Oblast."
        }],
        "clean_names": {"Sakhtysh 14, Sahtysh 14 Palaeolithic Camp-Russia": "Sakhtysh 14"}
    },
    # 50: C0844
    "C0844": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Samarskaya krepost-Russia",
            "target_key": "Samara-Russia",
            "reason": "Samara Fortress founded in 1586, representing the fortified core of the continuous city of Samara; explicit MERGE example."
        }],
        "clean_names": {"Samara-Russia": "Samara"}
    },
    # 51: C0846
    "C0846": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Sarom-Pugor Iron Age Site-Russia",
            "target_key": "Sarom-Pugor-Russia",
            "reason": "Continuous Iron Age and Early Medieval settlement layers at Sarom-Pugor on the Ob river in Western Siberia (gap <= 200 years)."
        }],
        "clean_names": {"Sarom-Pugor-Russia": "Sarom-Pugor"}
    },
    # 52: C0849
    "C0849": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Pamyatky_piznoho_mezolitu 142 Mesolithic Camp-Ukraine",
            "target_key": "Savran Mesolithic Settlement-Ukraine_2",
            "reason": "Overlapping Mesolithic campsite entries of the Savran / Poznanka complex on the Southern Bug; merge into named settlement node."
        }],
        "clean_names": {"Savran Mesolithic Settlement-Ukraine_2": "Savran"}
    },
    # 53: C0850
    "C0850": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Savran Mesolithic Settlement-Ukraine",
            "target_key": "Savran-Ukraine",
            "reason": "Prehistoric and medieval settlement series at Savran meeting continuous modern settlement series at 1400 with zero gap."
        }],
        "clean_names": {"Savran-Ukraine": "Savran"}
    },
    # 54: C0852
    "C0852": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Sebezhskaya krepost-Russia",
            "target_key": "Sebezh-Russia",
            "reason": "Medieval fortified fortress on Lake Sebezh (Zamkovaya Gora) representing the fortified predecessor of Sebezh town (gap 114 years <= 200 years)."
        }],
        "clean_names": {"Sebezh-Russia": "Sebezh"}
    },
    # 55: C0853
    "C0853": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Selenginsk-Russia_2",
            "new_name": "Novoselenginsk",
            "reason": "Historical site of Old Selenginsk / Novoselenginsk founded in 1665 in Selenginsky District, distinct from the modern industrial town of Selenginsk in Kabansky District (101 km apart)."
        }],
        "clean_names": {
            "Selenginsk-Russia": "Selenginsk",
            "Selenginsk-Russia_2": "Novoselenginsk"
        }
    },
    # 56: C0854
    "C0854": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Selishcha peryyadu rannyaga zhaleznaga veku Site 359-Belarus",
            "target_key": "Garadzishcha peryyadu rannyaga syarednyavechcha Site 102-Belarus",
            "reason": "Overlapping Iron Age settlement and early medieval hillfort components of the Otverzhichi archaeological complex in Stolin District, Belarus."
        }],
        "clean_names": {"Garadzishcha peryyadu rannyaga syarednyavechcha Site 102-Belarus": "Otverzhichi"}
    },
    # 57: C0855
    "C0855": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Chateau de Jaber-Belarus",
                "new_name": "Zhaber",
                "reason": "Historic Zhaber Castle bastion fortress on the Yaselda river near Zhaber village in Drogichin District."
            },
            {
                "op": "RENAME_META",
                "key": "Selishcha peryyadu rannyaga zhaleznaga veku Site 361-Belarus",
                "new_name": "Cherneyevichi",
                "reason": "Iron Age archaeological settlement located at Cherneyevichi village in Drogichin District."
            }
        ],
        "clean_names": {
            "Chateau de Jaber-Belarus": "Zhaber",
            "Selishcha peryyadu rannyaga zhaleznaga veku Site 361-Belarus": "Cherneyevichi"
        }
    },
    # 58: C0857
    "C0857": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Paselishcha-3 peryyadu nealitu 1-ga tysyachagoddzya n. e.-Belarus",
                "new_name": "Luben",
                "reason": "Distinct archaeological settlement at Luben village in Gomel Oblast."
            },
            {
                "op": "RENAME_META",
                "key": "Selishcha-1 peryyadu rannyaga zhaleznaga veku-Belarus",
                "new_name": "Moskalyovka",
                "reason": "Distinct archaeological settlement at Moskalyovka village in Gomel Oblast."
            }
        ],
        "clean_names": {
            "Paselishcha-3 peryyadu nealitu 1-ga tysyachagoddzya n. e.-Belarus": "Luben",
            "Selishcha-1 peryyadu rannyaga zhaleznaga veku-Belarus": "Moskalyovka"
        }
    },
    # 59: C0858
    "C0858": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Kideksha (11521500)-Russia",
                "new_name": "Kideksha",
                "reason": "Historic town of Kideksha on the Nerl river, princely seat of Yuri Dolgorukiy."
            },
            {
                "op": "RENAME_META",
                "key": "Selishche Krasnoe-IV (Krasnoe)-Russia",
                "new_name": "Krasnoye-na-Kamenke",
                "reason": "Distinct medieval rural settlement at Krasnoye village on the Kamenka river."
            }
        ],
        "clean_names": {
            "Kideksha (11521500)-Russia": "Kideksha",
            "Selishche Krasnoe-IV (Krasnoe)-Russia": "Krasnoye-na-Kamenke"
        }
    },
    # 60: C0859
    "C0859": {
        "actions": [
            {
                "op": "DROP_JUNK",
                "key": "Kultovyy kamen (Bungino)-Russia",
                "reason": "Sacred pagan cult boulder at Bungino falsely scraped as an independent settlement with fabricated medieval population figures."
            },
            {
                "op": "RENAME_META",
                "key": "Selishche Medvedkovo-Russia",
                "new_name": "Medvedkovo",
                "reason": "Surviving genuine medieval rural settlement at Medvedkovo."
            }
        ],
        "clean_names": {"Selishche Medvedkovo-Russia": "Medvedkovo"}
    },
    # 61: C0861
    "C0861": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Celishche Menchakovo-I (Menchakovo)-Russia",
                "new_name": "Menchakovo",
                "reason": "Distinct medieval rural settlement at Menchakovo in Suzdal Opolye."
            },
            {
                "op": "RENAME_META",
                "key": "Selishche Pantelikha-II (Pantelikha)-Russia",
                "new_name": "Pantelikha",
                "reason": "Distinct medieval rural settlement at Pantelikha in Suzdal Opolye."
            }
        ],
        "clean_names": {
            "Celishche Menchakovo-I (Menchakovo)-Russia": "Menchakovo",
            "Selishche Pantelikha-II (Pantelikha)-Russia": "Pantelikha"
        }
    },
    # 62: C0862
    "C0862": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Selishche Sharapovo 1-Russia",
            "target_key": "Sharapovo-Russia",
            "reason": "Medieval unfortified settlement (selishche) representing the predecessor of the continuous village of Sharapovo in Moscow Oblast (gap 200 years <= 200 years)."
        }],
        "clean_names": {"Sharapovo-Russia": "Sharapovo"}
    },
    # 63: C0868
    "C0868": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Serenskoe gorodishche ostatki drevnego goroda Serenska, upominaemogo v letopisi pod 1147 g. (Serensk)-Russia",
            "target_key": "Serensk-Russia",
            "reason": "Ancient chronicle city of Serensk (capital of the Vyatichi), overlapping archaeological and historical settlement series (1147..1200)."
        }],
        "clean_names": {"Serensk-Russia": "Serensk"}
    },
    # 64: C0869
    "C0869": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Selishche Serpukhovskoe Vysotskoe (Serpukhov)-Russia",
            "target_key": "Serpuchov-Russia",
            "reason": "Medieval settlement on Vysotsky hill representing the predecessor settlement of continuous Serpukhov, meeting the main series at 1300 with zero gap."
        }],
        "clean_names": {"Serpuchov-Russia": "Serpukhov"}
    },
    # 65: C0872
    "C0872": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Sevsk Medieval Gorodishche-Russia",
            "target_key": "Sevsk-Russia",
            "reason": "Medieval fortified gorodishche of Sevsk representing the fortified core of the continuous town of Sevsk, overlapping 1200..1500."
        }],
        "clean_names": {"Sevsk-Russia": "Sevsk"}
    },
    # 66: C0876
    "C0876": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Shali Medieval Gorodishche-Russia",
            "target_key": "Shali-Russia",
            "reason": "Medieval gorodishche of Shali in Chechnya representing the fortified predecessor of the continuous settlement, with gap under 200 years (1280 to 1400)."
        }],
        "clean_names": {"Shali-Russia": "Shali"}
    },
    # 67: C0877
    "C0877": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Shan Koba Palaeolithic Camp-Ukraine",
            "target_key": "Shan-Koba-Ukraine",
            "reason": "Displaced coordinate twin entries for the Shan-Koba Mesolithic / Upper Palaeolithic rock shelter site in the Crimean mountains; merge into primary series."
        }],
        "clean_names": {"Shan-Koba-Ukraine": "Shan-Koba"}
    },
    # 68: C0880
    "C0880": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Shcherbetskoe gorodishche-Russia",
            "target_key": "Shcherbet-Russia",
            "reason": "Overlapping settlement and gorodishche components of the Shcherbet archaeological complex in Tatarstan (800..900)."
        }],
        "clean_names": {"Shcherbet-Russia": "Shcherbet"}
    },
    # 69: C0882
    "C0882": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Shestakovo-Russia",
            "target_key": "Shestakovo_RU_20-Russia",
            "reason": "Displaced coordinate twin entries for Shestakovo on the Ilim river in Irkutsk Oblast; merge into longest continuous series."
        }],
        "clean_names": {"Shestakovo_RU_20-Russia": "Shestakovo"}
    },
    # 70: C0885
    "C0885": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Shuyskiy kreml-Russia",
            "target_key": "`'Suja-Russia",
            "reason": "Shuya Kremlin / fortress representing the fortified core of the continuous town of Shuya, overlapping 1501..1801."
        }],
        "clean_names": {"`'Suja-Russia": "Shuya"}
    },
    # 71: C0887
    "C0887": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Sireniki-Russia",
            "target_key": "Sireniki Medieval Gorodishche-Russia",
            "reason": "Historic Yupik Eskimo settlement and gorodishche of Sirinek in Chukotka; merge short series into longest continuous archaeological series."
        }],
        "clean_names": {"Sireniki Medieval Gorodishche-Russia": "Sireniki"}
    },
    # 72: C0889
    "C0889": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Meshoko-Russia",
                "new_name": "Meshoko",
                "reason": "Famous Eneolithic and Early Bronze Age fortified settlement on the Meshoko river near Kamennomostsky in Adygea."
            },
            {
                "op": "RENAME_META",
                "key": "Skala Bronze Age Site-Russia",
                "new_name": "Skala",
                "reason": "Distinct Bronze Age settlement site in the Aminovka gorge / Skala near Kamennomostsky."
            }
        ],
        "clean_names": {
            "Meshoko-Russia": "Meshoko",
            "Skala Bronze Age Site-Russia": "Skala"
        }
    },
    # 73: C0890
    "C0890": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Skalat Castle-Ukraine",
            "target_key": "Skalat-Ukraine",
            "reason": "Historic castle in Skalat representing the fortified core and continuous history of Skalat town."
        }],
        "clean_names": {"Skalat-Ukraine": "Skalat"}
    },
    # 74: C0893
    "C0893": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Slutsk Rus Hillfort-Belarus",
            "target_key": "Sluck-Belarus",
            "reason": "Old Rus fortified citadel hillfort of Slutsk representing the fortified core of the continuous city of Slutsk, overlapping 900..1300."
        }],
        "clean_names": {"Sluck-Belarus": "Slutsk"}
    },
    # 75: C0896
    "C0896": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Snovsk Iron Age Site-Ukraine",
            "target_key": "Sedniv-Ukraine",
            "reason": "Ancient chronicle city of Snovsk on the Snov river, direct predecessor of the continuous town of Sedniv, overlapping 1100..1400."
        }],
        "clean_names": {"Sedniv-Ukraine": "Sedniv"}
    },
    # 76: C0898
    "C0898": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Sochipsu Ubykh Aul-Russia",
            "target_key": "So`'ci-Russia",
            "reason": "Historic Ubykh aul of Sochipsu at the mouth of the Sochi river, direct predecessor of the continuous modern city of Sochi, overlapping 1400..1800."
        }],
        "clean_names": {"So`'ci-Russia": "Sochi"}
    },
    # 77: C0899
    "C0899": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Sofiysk-Russia_2",
            "new_name": "Sofiysk-na-Amure",
            "reason": "Historical village on the Amur River in Ulchsky District (former town of Sofiysk-na-Amure), 405 km from the gold-mining settlement of Sofiysk in Verkhnebureinsky District."
        }],
        "clean_names": {
            "Sofiysk-Russia": "Sofiysk",
            "Sofiysk-Russia_2": "Sofiysk-na-Amure"
        }
    },
    # 78: C0900
    "C0900": {
        "actions": [{
            "op": "KEEP_HOMONYM",
            "key": "Sokol-Russia_2",
            "reason": "Distinct towns legitimately sharing the name Sokol (city of Sokol in Vologda Oblast vs settlement of Sokol in Buryatia, 4121 km apart)."
        }],
        "clean_names": {
            "Sokol-Russia": "Sokol",
            "Sokol-Russia_2": "Sokol"
        }
    },
    # 79: C0902
    "C0902": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Soldyrskoe 1st hillfort-Russia",
            "target_key": "Idnakar-Russia",
            "reason": "Soldyrskoe 1st hillfort is the alternate archaeological name for the famous Cheptsa culture medieval fortified settlement of Idnakar in Udmurtia; identical site."
        }],
        "clean_names": {"Idnakar-Russia": "Idnakar"}
    },
    # 80: C0903
    "C0903": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Solikamsk, gorod-Russia",
            "target_key": "Solikamsk-Russia",
            "reason": "Medieval settlement layer at Solikamsk salt works representing the predecessor of the continuous city of Solikamsk (gap 100 years <= 200 years)."
        }],
        "clean_names": {"Solikamsk-Russia": "Solikamsk"}
    },
    # 81: C0904
    "C0904": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Solvychegodsk-Russia",
            "target_key": "Sol'vyčegodsk-Russia",
            "reason": "Displaced coordinate duplicate entry for the historic town of Solvychegodsk; explicit MERGE example."
        }],
        "clean_names": {"Sol'vyčegodsk-Russia": "Solvychegodsk"}
    },
    # 82: C0907
    "C0907": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Sosruco, Sosruko Palaeolithic Camp-Russia",
            "target_key": "Sosruko-Russia",
            "reason": "Duplicate entries for the Upper Palaeolithic and Mesolithic rock shelter site of Sosruko in Kabardino-Balkaria; merge into longest series."
        }],
        "clean_names": {"Sosruko-Russia": "Sosruko"}
    },
    # 83: C0911
    "C0911": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Antychne poselennya Stara Bohdanivka VII Classical Polis-Ukraine",
            "target_key": "Staraya Bogdanovka II-Ukraine",
            "reason": "Overlapping Olbian chora settlement entries of the Staraya Bogdanovka complex on the Bug Liman; merge into primary series."
        }],
        "clean_names": {"Staraya Bogdanovka II-Ukraine": "Staraya Bogdanovka"}
    },
    # 84: C0914
    "C0914": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Starocherkassk-Russia",
            "target_key": "Starocherkasskaya-Russia",
            "reason": "Historic Cossack capital of Starocherkassk and continuous stanitsa of Starocherkasskaya on the Don; continuous settlement."
        }],
        "clean_names": {"Starocherkasskaya-Russia": "Starocherkasskaya"}
    },
    # 85: C0915
    "C0915": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Starokorsunskoye-2-Russia",
            "target_key": "Starokorsunskoye Iron Age Site-Russia",
            "reason": "Overlapping Maeotian fortified settlements of the Starokorsunskoye complex on the Kuban river reservoir (-400..1)."
        }],
        "clean_names": {"Starokorsunskoye Iron Age Site-Russia": "Starokorsunskoye"}
    },
    # 86: C0916
    "C0916": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Staryy gorodok (Yarensk)-Russia",
            "target_key": "Yarensk-Russia",
            "reason": "Ancient fortified hillfort Stary Gorodok representing the predecessor settlement of continuous Yarensk (gap 100 years <= 200 years)."
        }],
        "clean_names": {"Yarensk-Russia": "Yarensk"}
    },
    # 87: C0918
    "C0918": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Selishcha Vasilevichy-1-Belarus",
                "new_name": "Vasilevichi",
                "reason": "Distinct archaeological settlement at Vasilevichi village in Belarus."
            },
            {
                "op": "RENAME_META",
                "key": "Stayanka Mitskavichy-1-Belarus",
                "new_name": "Mitkovichi",
                "reason": "Distinct archaeological settlement at Mitkovichi village in Belarus."
            }
        ],
        "clean_names": {
            "Selishcha Vasilevichy-1-Belarus": "Vasilevichi",
            "Stayanka Mitskavichy-1-Belarus": "Mitkovichi"
        }
    },
    # 88: C0919
    "C0919": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Garadzishcha Dzeraunaya - 1-Belarus",
                "new_name": "Dzerovnaya",
                "reason": "Distinct archaeological hillfort at Dzerovnaya village in Belarus."
            },
            {
                "op": "RENAME_META",
                "key": "Stayanka Vauchuny-1-Belarus",
                "new_name": "Volchuny",
                "reason": "Distinct archaeological settlement at Volchuny village in Belarus."
            }
        ],
        "clean_names": {
            "Garadzishcha Dzeraunaya - 1-Belarus": "Dzerovnaya",
            "Stayanka Vauchuny-1-Belarus": "Volchuny"
        }
    },
    # 89: C0921
    "C0921": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Selishcha Site 310-Belarus",
                "new_name": "Tsyakhtsin",
                "reason": "Distinct archaeological settlement at Tsyakhtsin village in Mogilev Oblast."
            },
            {
                "op": "RENAME_META",
                "key": "Stayanka peryyadu nealitu-Belarus",
                "new_name": "Ugolshchina",
                "reason": "Distinct archaeological campsite at Ugolshchina village in Mogilev Oblast."
            }
        ],
        "clean_names": {
            "Selishcha Site 310-Belarus": "Tsyakhtsin",
            "Stayanka peryyadu nealitu-Belarus": "Ugolshchina"
        }
    },
    # 90: C0922
    "C0922": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Selishcha-3 Site 387-Belarus",
                "new_name": "Bakov",
                "reason": "Distinct archaeological settlement at Bakov village in Gomel Oblast."
            },
            {
                "op": "RENAME_META",
                "key": "Stayanka-10-Belarus",
                "new_name": "Ushaki",
                "reason": "Distinct archaeological campsite at Ushaki village in Gomel Oblast."
            }
        ],
        "clean_names": {
            "Selishcha-3 Site 387-Belarus": "Bakov",
            "Stayanka-10-Belarus": "Ushaki"
        }
    },
    # 91: C0923
    "C0923": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Stayanka peryyadu nealitu i bronzavaga veku Site 446-Belarus",
                "new_name": "Lubyany",
                "reason": "Distinct Bronze Age settlement at Lubyany village in Belarus."
            },
            {
                "op": "RENAME_META",
                "key": "Stayanka-2 peryyadu nealitu i bronzavaga veku-Belarus_2",
                "new_name": "Kuntsy",
                "reason": "Distinct Bronze Age settlement at Kuntsy village in Belarus."
            }
        ],
        "clean_names": {
            "Stayanka peryyadu nealitu i bronzavaga veku Site 446-Belarus": "Lubyany",
            "Stayanka-2 peryyadu nealitu i bronzavaga veku-Belarus_2": "Kuntsy"
        }
    },
    # 92: C0924
    "C0924": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Stayanka Site 406-Belarus",
                "new_name": "Monastyrek",
                "reason": "Distinct archaeological campsite at Monastyrek village in Belarus."
            },
            {
                "op": "RENAME_META",
                "key": "Stayanka-9-Belarus",
                "new_name": "Zhuravel",
                "reason": "Distinct archaeological campsite at Zhuravel village in Belarus."
            }
        ],
        "clean_names": {
            "Stayanka Site 406-Belarus": "Monastyrek",
            "Stayanka-9-Belarus": "Zhuravel"
        }
    },
    # 93: C0925
    "C0925": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Balya Solnaya Bronze Age Hillfort-Belarus",
                "new_name": "Balya Solnaya",
                "reason": "Distinct Bronze Age hillfort at Balya Solnaya village in Grodno Oblast."
            },
            {
                "op": "RENAME_META",
                "key": "Stayanki peryyadu kamennaga bronzavaga vyakou-Belarus",
                "new_name": "Iskatel",
                "reason": "Distinct Bronze Age campsite at Iskatel in Grodno Oblast."
            }
        ],
        "clean_names": {
            "Balya Solnaya Bronze Age Hillfort-Belarus": "Balya Solnaya",
            "Stayanki peryyadu kamennaga bronzavaga vyakou-Belarus": "Iskatel"
        }
    },
    # 94: C0926
    "C0926": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Stepnoye-Russia_2",
            "new_name": "Stepnoye (Bronze Age)",
            "reason": "Sintashta Bronze Age fortified settlement of the Country of Towns in Chelyabinsk Oblast, located 964 km from the modern settlement of Stepnoye in Saratov Oblast."
        }],
        "clean_names": {
            "Stepnoye-Russia": "Stepnoye",
            "Stepnoye-Russia_2": "Stepnoye (Bronze Age)"
        }
    },
    # 95: C0929
    "C0929": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Storozhevoy oboronitelnyy val (Mokshan)-Russia",
            "target_key": "Mokshan-Russia",
            "reason": "Historic defensive rampart / abatis line of Mokshan representing the defense fortifications of continuous Mokshan town, overlapping 1676..1858."
        }],
        "clean_names": {"Mokshan-Russia": "Mokshan"}
    },
    # 96: C0931
    "C0931": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Stoyanka Pechenga I-Russia",
            "new_name": "Pechenga (Medieval)",
            "reason": "Medieval campsite on the Pechenga river, separated by a 250-year hiatus from the 16th-century monastery settlement of Pechenga."
        }],
        "clean_names": {
            "Pechenga-Russia": "Pechenga",
            "Stoyanka Pechenga I-Russia": "Pechenga (Medieval)"
        }
    },
    # 97: C0933
    "C0933": {
        "actions": [{
            "op": "DROP_JUNK",
            "key": "Kulturnyy sloy XVIII - XIX vv. imeniya A.D. Menshikova Favorit-Russia",
            "reason": "Heritage registry cultural layer entry for Menshikov estate 'Favorit', anachronistically scraped with fabricated dates (1350..1650) inside Strelna."
        }],
        "clean_names": {"Strel'na-Russia": "Strelna"}
    },
    # 98: C0935
    "C0935": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Beshenkovichskiy tet-de-pon Mediaeval Hillfort-Belarus",
                "new_name": "Strelka",
                "reason": "Distinct bridgehead fortification on Western Dvina at Strelka / Beshenkovichi."
            },
            {
                "op": "RENAME_META",
                "key": "Strizhev-Belarus",
                "new_name": "Strizhev",
                "reason": "Distinct medieval settlement on Western Dvina at Strizhevo."
            }
        ],
        "clean_names": {
            "Beshenkovichskiy tet-de-pon Mediaeval Hillfort-Belarus": "Strelka",
            "Strizhev-Belarus": "Strizhev"
        }
    },
    # 99: C0943
    "C0943": {
        "actions": [{
            "op": "RENAME_META",
            "key": "Suzdal Merya Gorodishche-Russia",
            "new_name": "Suzdal (Merya Gorodishche)",
            "reason": "Pre-Slavic Merya gorodishche separated by a 250-year hiatus (750 to 1000) from the continuous chronicle town of Suzdal; explicit RENAME_META example."
        }],
        "clean_names": {
            "Suzdal Merya Gorodishche-Russia": "Suzdal (Merya Gorodishche)",
            "Suzdal'-Russia": "Suzdal"
        }
    },
    # 100: C0944
    "C0944": {
        "actions": [
            {
                "op": "RENAME_META",
                "key": "Nisimkovichi-Belarus_2",
                "new_name": "Nisimkovichi",
                "reason": "Distinct 1st-millennium hillfort settlement at Nisimkovichi on the Besed river in Vetka District."
            },
            {
                "op": "RENAME_META",
                "key": "Svetilovichi-Besed Radimichi Barrow Hillfort Complex-Belarus",
                "new_name": "Svetilovichi",
                "reason": "Distinct Radimichi barrow and hillfort complex at Svetilovichi on the Besed river in Vetka District."
            }
        ],
        "clean_names": {
            "Nisimkovichi-Belarus_2": "Nisimkovichi",
            "Svetilovichi-Besed Radimichi Barrow Hillfort Complex-Belarus": "Svetilovichi"
        }
    },
    # 101: C0945
    "C0945": {
        "actions": [{
            "op": "KEEP_HOMONYM",
            "key": "Svetlogorsk-Russia_2",
            "reason": "Distinct historical towns legitimately sharing the name Svetlogorsk (Baltic resort town in Kaliningrad Oblast vs settlement in Krasnoyarsk Krai, 3692 km apart)."
        }],
        "clean_names": {
            "Svetlogorsk-Russia": "Svetlogorsk",
            "Svetlogorsk-Russia_2": "Svetlogorsk"
        }
    },
    # 102: C0946
    "C0946": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Svir Castle-Belarus",
            "target_key": "Svir-Belarus",
            "reason": "Historic 14th-century castle of the princes Svirsky on Lake Svir representing the fortified predecessor of the town (gap 200 years <= 200 years)."
        }],
        "clean_names": {"Svir-Belarus": "Svir"}
    },
    # 103: C0947
    "C0947": {
        "actions": [{
            "op": "MERGE",
            "source_key": "Syzran Kremlin-Russia",
            "target_key": "Syzran'-Russia",
            "reason": "Syzran Kremlin founded in 1683, representing the fortified core of continuous Syzran city; explicit MERGE example."
        }],
        "clean_names": {"Syzran'-Russia": "Syzran"}
    }
}

# Verify every cluster in raw_data is in specs
raw_cids = [c['cluster_id'] for c in raw_data]
missing = [cid for cid in raw_cids if cid not in specs]
extra = [cid for cid in specs if cid not in raw_cids]

if missing:
    print(f"ERROR: Missing specs for: {missing}")
if extra:
    print(f"ERROR: Extra specs for: {extra}")

out_list = []
for c in raw_data:
    cid = c['cluster_id']
    spec = specs[cid]
    out_list.append({
        "cluster_id": cid,
        "actions": spec["actions"],
        "clean_names": spec["clean_names"]
    })

out_path = 'f:/Active Projects/Project 1509 - SVEA/tests/polaris_batches/out_tier1_batch_5.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out_list, f, indent=2, ensure_ascii=False)

print(f"Successfully generated {out_path} with {len(out_list)} clusters.")
