import json
import os

input_path = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\tier2_batch_1.json'
output_path = r'f:\Active Projects\Project 1509 - SVEA\tests\polaris_batches\out_tier2_batch_1.json'

with open(input_path, 'r', encoding='utf-8') as f:
    input_data = json.load(f)

# Master decisions dict keyed by cluster_id
# Format:
# cid: {
#    "actions": [...],
#    "clean_names": { key: name, ... }
# }

d = {}

# C0011: Chokh
d["C0011"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Chokh Bronze Age Site-Russia", "new_name": "Chokh (Neolithic)", "reason": "Pre-hiatus Mesolithic/Neolithic rock shelter site distinct from modern aul Chokh"},
        {"op": "RENAME_META", "key": "Chokh Bronze Age Site 2-Russia", "new_name": "Chokh (Bronze Age)", "reason": "Pre-hiatus Bronze Age settlement site distinct from modern aul Chokh"},
        {"op": "RENAME_META", "key": "Chokh Gorodishche-Russia", "new_name": "Chokh Gorodishche", "reason": "Pre-hiatus Early Medieval hillfort site distinct from modern aul Chokh"},
        {"op": "RENAME_META", "key": "Chokh Medieval Gorodishche-Russia", "new_name": "Chokh Medieval Gorodishche", "reason": "Pre-hiatus High Medieval fortified site distinct from modern aul Chokh"}
    ],
    "clean_names": {
        "Chokh-Russia": "Chokh",
        "Chokh Bronze Age Site-Russia": "Chokh (Neolithic)",
        "Chokh Bronze Age Site 2-Russia": "Chokh (Bronze Age)",
        "Chokh Gorodishche-Russia": "Chokh Gorodishche",
        "Chokh Medieval Gorodishche-Russia": "Chokh Medieval Gorodishche"
    }
}

# C0018: Ust-Timpton
d["C0018"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Ust-Timpton Palaeolithic Camp-Russia", "new_name": "Ust-Timpton (Palaeolithic)", "reason": "Palaeolithic multilayer campsite on Timpton river"},
        {"op": "RENAME_META", "key": "Ust-Timpton Stone Age Site-Russia", "new_name": "Ust-Timpton (Mesolithic)", "reason": "Mesolithic occupation phase at Ust-Timpton"},
        {"op": "RENAME_META", "key": "Ust-Timpton Stone Age Site 2-Russia", "new_name": "Ust-Timpton (Neolithic)", "reason": "Neolithic occupation phase at Ust-Timpton"},
        {"op": "RENAME_META", "key": "Ust-Timpton Bronze Age Site-Russia", "new_name": "Ust-Timpton (Bronze Age)", "reason": "Bronze Age occupation phase at Ust-Timpton"}
    ],
    "clean_names": {
        "Ust-Timpton-Russia": "Ust-Timpton",
        "Ust-Timpton Palaeolithic Camp-Russia": "Ust-Timpton (Palaeolithic)",
        "Ust-Timpton Stone Age Site-Russia": "Ust-Timpton (Mesolithic)",
        "Ust-Timpton Stone Age Site 2-Russia": "Ust-Timpton (Neolithic)",
        "Ust-Timpton Bronze Age Site-Russia": "Ust-Timpton (Bronze Age)"
    }
}

# C0019: Utkonosivka
d["C0019"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Utkonosivka Neolithic Settlement-Ukraine", "new_name": "Utkonosivka (Neolithic)", "reason": "Neolithic settlement near Lake Katlabuh distinct from modern village Utkonosivka"},
        {"op": "RENAME_META", "key": "dvosharove humelnytske ta rymskoho chasu Utkonosivka Bronze Age Settlement-Ukraine", "new_name": "Utkonosivka (Bronze Age)", "reason": "Gumelnita/Bronze Age settlement distinct from modern village"},
        {"op": "RENAME_META", "key": "bahatosharove humelnytske Chernyakhov Settlement III-Ukraine", "new_name": "Utkonosivka (Chernyakhov)", "reason": "Chernyakhov culture phase near Utkonosivka"},
        {"op": "RENAME_META", "key": "dvosharove chernyakhivske ta slovyanske Utkonosivka Chernyakhov Settlement-Ukraine", "new_name": "Utkonosivka (Early Slavic)", "reason": "Early Slavic settlement phase near Utkonosivka"}
    ],
    "clean_names": {
        "Utkonosivka-Ukraine": "Utkonosivka",
        "Utkonosivka Neolithic Settlement-Ukraine": "Utkonosivka (Neolithic)",
        "dvosharove humelnytske ta rymskoho chasu Utkonosivka Bronze Age Settlement-Ukraine": "Utkonosivka (Bronze Age)",
        "bahatosharove humelnytske Chernyakhov Settlement III-Ukraine": "Utkonosivka (Chernyakhov)",
        "dvosharove chernyakhivske ta slovyanske Utkonosivka Chernyakhov Settlement-Ukraine": "Utkonosivka (Early Slavic)"
    }
}

# C0020: Krynychne
d["C0020"] = {
    "actions": [
        {"op": "RENAME_META", "key": "dvosharove doby piznoyi bronzy ta chernyakhivske Zhovtneve Bronze Age Settlement-Ukraine", "new_name": "Zhovtneve (Bronze Age)", "reason": "Distinct Bronze Age site at neighbouring Zhovtneve/Karakurt"},
        {"op": "RENAME_META", "key": "dvosharove sabatynivske ta chernyakhivske Krynychne V Chernyakhov Settlement-Ukraine", "new_name": "Krynychne V (Chernyakhov)", "reason": "Chernyakhov settlement site Krynychne V"},
        {"op": "RENAME_META", "key": "balkano-dunayske pivdennykh slovyan Krynychne Mediaeval Hillfort-Ukraine", "new_name": "Krynychne (Medieval Hillfort)", "reason": "Balkan-Danubian South Slavic medieval hillfort"},
        {"op": "RENAME_META", "key": "dvosharove sabatynivske ta rymskoho chasu Krynychne VI Late Mediaeval Settlement-Ukraine", "new_name": "Krynychne VI (Late Medieval)", "reason": "Late Medieval settlement site Krynychne VI"}
    ],
    "clean_names": {
        "Krynychne_UA_17-Ukraine": "Krynychne",
        "dvosharove doby piznoyi bronzy ta chernyakhivske Zhovtneve Bronze Age Settlement-Ukraine": "Zhovtneve (Bronze Age)",
        "dvosharove sabatynivske ta chernyakhivske Krynychne V Chernyakhov Settlement-Ukraine": "Krynychne V (Chernyakhov)",
        "balkano-dunayske pivdennykh slovyan Krynychne Mediaeval Hillfort-Ukraine": "Krynychne (Medieval Hillfort)",
        "dvosharove sabatynivske ta rymskoho chasu Krynychne VI Late Mediaeval Settlement-Ukraine": "Krynychne VI (Late Medieval)"
    }
}

# C0023: Avacha
d["C0023"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Avacha Bronze Age Site-Russia", "new_name": "Avacha (Bronze Age)", "reason": "Pre-hiatus Tar'ya Bronze Age campsite on Avacha bay"},
        {"op": "RENAME_META", "key": "Avacha Iron Age Site-Russia", "new_name": "Avacha (Iron Age)", "reason": "Pre-hiatus Iron Age campsite on Avacha bay"},
        {"op": "RENAME_META", "key": "Avacha Gorodishche-Russia", "new_name": "Avacha Gorodishche", "reason": "Pre-hiatus Early Medieval fortified site"}
    ],
    "clean_names": {
        "Avacha-Russia": "Avacha",
        "Avacha Bronze Age Site-Russia": "Avacha (Bronze Age)",
        "Avacha Iron Age Site-Russia": "Avacha (Iron Age)",
        "Avacha Gorodishche-Russia": "Avacha Gorodishche"
    }
}

# C0036: Kuzemyn
d["C0036"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Belsk Iron Age Site 2-Ukraine", "new_name": "Bilsk (Chernyakhov)", "reason": "Chernyakhov period iron age site belonging to Bilsk complex"},
        {"op": "RENAME_META", "key": "Kuzemyn Vorskla Northern Rampart Complex Iron Age Site-Ukraine", "new_name": "Kuzemyn Rampart (Iron Age)", "reason": "Iron Age rampart complex on Vorskla river"},
        {"op": "RENAME_META", "key": "Kuzemyn Vorskla Northern Rampart Complex-Ukraine", "new_name": "Kuzemyn Rampart (Medieval)", "reason": "Early medieval rampart complex on Vorskla river"}
    ],
    "clean_names": {
        "Kuzemyn-Ukraine": "Kuzemyn",
        "Belsk Iron Age Site 2-Ukraine": "Bilsk (Chernyakhov)",
        "Kuzemyn Vorskla Northern Rampart Complex Iron Age Site-Ukraine": "Kuzemyn Rampart (Iron Age)",
        "Kuzemyn Vorskla Northern Rampart Complex-Ukraine": "Kuzemyn Rampart (Medieval)"
    }
}

# C0053: Ust-Kova
d["C0053"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Ust-Kova Stone Age Site-Russia", "new_name": "Ust-Kova (Mesolithic)", "reason": "Mesolithic multi-layer site on Angara river"},
        {"op": "RENAME_META", "key": "Ust-Kova Stone Age Site 2-Russia", "new_name": "Ust-Kova (Neolithic)", "reason": "Neolithic multi-layer site on Angara river"},
        {"op": "RENAME_META", "key": "Ust-Kova Bronze Age Site-Russia", "new_name": "Ust-Kova (Bronze Age)", "reason": "Bronze Age multi-layer site on Angara river"}
    ],
    "clean_names": {
        "Ust-Kova-Russia": "Ust-Kova",
        "Ust-Kova Stone Age Site-Russia": "Ust-Kova (Mesolithic)",
        "Ust-Kova Stone Age Site 2-Russia": "Ust-Kova (Neolithic)",
        "Ust-Kova Bronze Age Site-Russia": "Ust-Kova (Bronze Age)"
    }
}

# C0061: Bahate
d["C0061"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bahate Eneolithic Hillfort-Ukraine", "new_name": "Bahate (Eneolithic)", "reason": "Eneolithic hillfort distinct from modern village"},
        {"op": "RENAME_META", "key": "bahatosharove humelnytske Bronze Age Settlement III-Ukraine", "new_name": "Bahate (Bronze Age)", "reason": "Gumelnita/Bronze Age settlement distinct from modern village"},
        {"op": "RENAME_META", "key": "chernyakhivske Bahate Chernyakhov Settlement-Ukraine", "new_name": "Bahate (Chernyakhov)", "reason": "Chernyakhov settlement distinct from modern village"}
    ],
    "clean_names": {
        "Bahate-Ukraine": "Bahate",
        "Bahate Eneolithic Hillfort-Ukraine": "Bahate (Eneolithic)",
        "bahatosharove humelnytske Bronze Age Settlement III-Ukraine": "Bahate (Bronze Age)",
        "chernyakhivske Bahate Chernyakhov Settlement-Ukraine": "Bahate (Chernyakhov)"
    }
}

# C0064: Hradenytsi
d["C0064"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Gradenitsy Eneolithic Hillfort-Ukraine", "new_name": "Hradenytsi (Eneolithic)", "reason": "Usatovo/Eneolithic hillfort near Dniester liman"},
        {"op": "RENAME_META", "key": "dvosharove doby piznoyi bronzy ta pershykh stolit n.e. Hradenytsi III Bronze Age Settlement-Ukraine", "new_name": "Hradenytsi III (Bronze Age)", "reason": "Late Bronze Age settlement phase"},
        {"op": "RENAME_META", "key": "Gradenitsy Classical Polis-Ukraine", "new_name": "Hradenytsi (Antiquity)", "reason": "Classical antiquity settlement on Dniester"}
    ],
    "clean_names": {
        "Hradenytsi-Ukraine": "Hradenytsi",
        "Gradenitsy Eneolithic Hillfort-Ukraine": "Hradenytsi (Eneolithic)",
        "dvosharove doby piznoyi bronzy ta pershykh stolit n.e. Hradenytsi III Bronze Age Settlement-Ukraine": "Hradenytsi III (Bronze Age)",
        "Gradenitsy Classical Polis-Ukraine": "Hradenytsi (Antiquity)"
    }
}

# C0074: Bamut
d["C0074"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bamut Bronze Age Site-Russia", "new_name": "Bamut (Early Bronze Age)", "reason": "Early Bronze Age Maykop-Novosvobodnaya settlement"},
        {"op": "RENAME_META", "key": "Bamut Bronze Age Site 2-Russia", "new_name": "Bamut (Late Bronze Age)", "reason": "Late Bronze Age settlement phase distinct from modern aul"}
    ],
    "clean_names": {
        "Bamut-Russia": "Bamut",
        "Bamut Bronze Age Site-Russia": "Bamut (Early Bronze Age)",
        "Bamut Bronze Age Site 2-Russia": "Bamut (Late Bronze Age)"
    }
}

# C0075: Belkachi I
d["C0075"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Belkachi I Stone Age Site-Russia", "new_name": "Belkachi I (Neolithic)", "reason": "Type site of Belkachi Neolithic culture on Aldan river"},
        {"op": "RENAME_META", "key": "Belkachi I Bronze Age Site-Russia", "new_name": "Belkachi I (Bronze Age)", "reason": "Bronze Age phase of Belkachi I"}
    ],
    "clean_names": {
        "Belkachi I-Russia": "Belkachi I",
        "Belkachi I Stone Age Site-Russia": "Belkachi I (Neolithic)",
        "Belkachi I Bronze Age Site-Russia": "Belkachi I (Bronze Age)"
    }
}

# C0077: Bilsk
d["C0077"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bilsk hillfort-Ukraine", "new_name": "Bilsk Hillfort", "reason": "Great Scythian-era fortified megasite / Gelonus"},
        {"op": "RENAME_META", "key": "Belsk-Ukraine", "new_name": "Bilsk (Early Medieval)", "reason": "Early medieval Slavic settlement on Bilsk hillfort plateau"}
    ],
    "clean_names": {
        "Bilsk-Ukraine": "Bilsk",
        "Bilsk hillfort-Ukraine": "Bilsk Hillfort",
        "Belsk-Ukraine": "Bilsk (Early Medieval)"
    }
}

# C0086: Gapshima
d["C0086"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Gapshima Bronze Age Site-Russia", "new_name": "Gapshima (Bronze Age)", "reason": "Pre-hiatus Bronze Age settlement site"},
        {"op": "RENAME_META", "key": "Gapshima Medieval Gorodishche-Russia", "new_name": "Gapshima Medieval Gorodishche", "reason": "High medieval fortified settlement distinct from modern village"}
    ],
    "clean_names": {
        "Gapshima-Russia": "Gapshima",
        "Gapshima Bronze Age Site-Russia": "Gapshima (Bronze Age)",
        "Gapshima Medieval Gorodishche-Russia": "Gapshima Medieval Gorodishche"
    }
}

# C0087: Gimry
d["C0087"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Gimry Bronze Age Site-Russia", "new_name": "Gimry (Bronze Age)", "reason": "Pre-hiatus Bronze Age settlement in Avar gorge"},
        {"op": "RENAME_META", "key": "Gimry Medieval Gorodishche-Russia", "new_name": "Gimry Medieval Gorodishche", "reason": "High medieval fortified settlement"}
    ],
    "clean_names": {
        "Gimry-Russia": "Gimry",
        "Gimry Bronze Age Site-Russia": "Gimry (Bronze Age)",
        "Gimry Medieval Gorodishche-Russia": "Gimry Medieval Gorodishche"
    }
}

# C0089: Hraniv
d["C0089"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Granov 1 Eneolithic Hillfort-Ukraine", "new_name": "Hraniv (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort near Hraniv"},
        {"op": "RENAME_META", "key": "Ancient settlement of pre-Scythian period in Hraniv-Ukraine", "new_name": "Hraniv (Pre-Scythian)", "reason": "Pre-Scythian / Chornolis culture settlement"}
    ],
    "clean_names": {
        "Hraniv-Ukraine": "Hraniv",
        "Granov 1 Eneolithic Hillfort-Ukraine": "Hraniv (Eneolithic)",
        "Ancient settlement of pre-Scythian period in Hraniv-Ukraine": "Hraniv (Pre-Scythian)"
    }
}

# C0090: Gubden
d["C0090"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Gubden Gorodishche-Russia", "new_name": "Gubden Gorodishche", "reason": "Early medieval fortified site distinct from modern aul"},
        {"op": "RENAME_META", "key": "Gubden Medieval Gorodishche-Russia", "new_name": "Gubden Medieval Gorodishche", "reason": "High medieval fortified site distinct from modern aul"}
    ],
    "clean_names": {
        "Gubden-Russia": "Gubden",
        "Gubden Gorodishche-Russia": "Gubden Gorodishche",
        "Gubden Medieval Gorodishche-Russia": "Gubden Medieval Gorodishche"
    }
}

# C0091: Horodnye
d["C0091"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Horodnye Eneolithic Hillfort-Ukraine", "new_name": "Horodnye (Eneolithic)", "reason": "Eneolithic hillfort near Horodnye"},
        {"op": "RENAME_META", "key": "Horodnye Bronze Age Settlement-Ukraine", "new_name": "Horodnye (Bronze Age)", "reason": "Bronze Age settlement near Horodnye"}
    ],
    "clean_names": {
        "Horodnye-Ukraine": "Horodnye",
        "Horodnye Eneolithic Hillfort-Ukraine": "Horodnye (Eneolithic)",
        "Horodnye Bronze Age Settlement-Ukraine": "Horodnye (Bronze Age)"
    }
}

# C0092: Chernihiv
d["C0092"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Horsad Bronze Age Settlement-Ukraine", "new_name": "Horsad", "reason": "Distinct Bronze Age settlement Horsad near Chernihiv"},
        {"op": "RENAME_META", "key": "Chernigov Iron Age Site-Ukraine", "new_name": "Chernihiv (Iron Age)", "reason": "Pre-hiatus Iron Age settlement on the Desna terrace"}
    ],
    "clean_names": {
        "`Cernihiv-Ukraine": "Chernihiv",
        "Horsad Bronze Age Settlement-Ukraine": "Horsad",
        "Chernigov Iron Age Site-Ukraine": "Chernihiv (Iron Age)"
    }
}

# C0094: Hryhorivka
d["C0094"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Hryhorivka Iron Age Site-Ukraine", "new_name": "Hryhorivka (Iron Age)", "reason": "Pre-Scythian/Iron Age site on Dniester"},
        {"op": "RENAME_META", "key": "Hryhorivka-Ukraine", "new_name": "Hryhorivka (Chernyakhov)", "reason": "Chernyakhov culture phase on Dniester"},
        {"op": "RENAME_META", "key": "Hryhorivske horodyshche-Ukraine", "new_name": "Hryhorivske Gorodishche", "reason": "Kievan Rus medieval hillfort"}
    ],
    "clean_names": {
        "Hryhorivka Iron Age Site-Ukraine": "Hryhorivka (Iron Age)",
        "Hryhorivka-Ukraine": "Hryhorivka (Chernyakhov)",
        "Hryhorivske horodyshche-Ukraine": "Hryhorivske Gorodishche"
    }
}

# C0096: Izyum
d["C0096"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Izyum Stone Age Hillfort-Ukraine", "new_name": "Izyum (Stone Age)", "reason": "Mesolithic/Neolithic camp on Siversky Donets"},
        {"op": "RENAME_META", "key": "Izyum Bronze Age Settlement-Ukraine", "new_name": "Izyum (Bronze Age)", "reason": "Bronze Age settlement near Mount Kremyanets"},
        {"op": "RENAME_META", "key": "Izyumskie stoyanki-Ukraine", "new_name": "Izyumskie Stoyanki", "reason": "Saltov/Medieval nomadic seasonal camps"}
    ],
    "clean_names": {
        "Izyum Stone Age Hillfort-Ukraine": "Izyum (Stone Age)",
        "Izyum Bronze Age Settlement-Ukraine": "Izyum (Bronze Age)",
        "Izyumskie stoyanki-Ukraine": "Izyumskie Stoyanki"
    }
}

# C0100: Karabudakhkent
d["C0100"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Karabudakhkent Iron Age Site-Russia", "new_name": "Karabudakhkent (Iron Age)", "reason": "Pre-hiatus Iron Age site"},
        {"op": "RENAME_META", "key": "Karabudakhkent Gorodishche-Russia", "new_name": "Karabudakhkent Gorodishche", "reason": "Khazar-era early medieval fortified site"}
    ],
    "clean_names": {
        "Karabudakhkent-Russia": "Karabudakhkent",
        "Karabudakhkent Iron Age Site-Russia": "Karabudakhkent (Iron Age)",
        "Karabudakhkent Gorodishche-Russia": "Karabudakhkent Gorodishche"
    }
}

# C0119: Kryvyi Rih
d["C0119"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Krivoj Rog Eneolithic Hillfort-Ukraine", "new_name": "Kryvyi Rih (Eneolithic)", "reason": "Eneolithic settlement site on Inhulets river"},
        {"op": "RENAME_META", "key": "Kryvyy Rih Bronze Age Settlement II-Ukraine", "new_name": "Kryvyi Rih (Bronze Age)", "reason": "Bronze Age settlement site on Saksahan river"}
    ],
    "clean_names": {
        "Kryvyi Rih-Ukraine": "Kryvyi Rih",
        "Krivoj Rog Eneolithic Hillfort-Ukraine": "Kryvyi Rih (Eneolithic)",
        "Kryvyy Rih Bronze Age Settlement II-Ukraine": "Kryvyi Rih (Bronze Age)"
    }
}

# C0121: Kullaty
d["C0121"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Kullaty Bronze Age Site-Russia", "new_name": "Kullaty (Early Bronze Age)", "reason": "Early Bronze Age phase of Kullaty site on Lena terrace"},
        {"op": "RENAME_META", "key": "Kullaty Bronze Age Site 2-Russia", "new_name": "Kullaty (Late Bronze Age)", "reason": "Late Bronze Age phase of Kullaty site"}
    ],
    "clean_names": {
        "Kullaty-Russia": "Kullaty",
        "Kullaty Bronze Age Site-Russia": "Kullaty (Early Bronze Age)",
        "Kullaty Bronze Age Site 2-Russia": "Kullaty (Late Bronze Age)"
    }
}

# C0122: Kulykivka
d["C0122"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Hlyboke Bronze Age Settlement-Ukraine", "new_name": "Hlyboke", "reason": "Distinct Bronze Age settlement Hlyboke near Kulykivka"},
        {"op": "RENAME_META", "key": "Kulykivka-Ukraine_2", "new_name": "Kulykivka (Rus)", "reason": "Kievan Rus rural craft settlement phase on Desna terrace"}
    ],
    "clean_names": {
        "Kulykivka-Ukraine": "Kulykivka",
        "Hlyboke Bronze Age Settlement-Ukraine": "Hlyboke",
        "Kulykivka-Ukraine_2": "Kulykivka (Rus)"
    }
}

# C0127: Lyady
d["C0127"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Lyady Iron Age Hillfort-Belarus", "new_name": "Lyady (Iron Age)", "reason": "Dnieper-Dvina / Iron Age hillfort near Lyady"},
        {"op": "RENAME_META", "key": "Lyady (garadzishcha)-Russia", "new_name": "Lyady Gorodishche", "reason": "Early medieval Rus garadzishcha near Lyady"}
    ],
    "clean_names": {
        "Lyady-Belarus": "Lyady",
        "Lyady Iron Age Hillfort-Belarus": "Lyady (Iron Age)",
        "Lyady (garadzishcha)-Russia": "Lyady Gorodishche"
    }
}

# C0131: Mekegi
d["C0131"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Mekegi Bronze Age Site-Russia", "new_name": "Mekegi (Bronze Age)", "reason": "Pre-hiatus Bronze Age settlement site"},
        {"op": "RENAME_META", "key": "Mekegi Medieval Gorodishche-Russia", "new_name": "Mekegi Medieval Gorodishche", "reason": "High medieval fortified settlement distinct from modern village"}
    ],
    "clean_names": {
        "Mekegi-Russia": "Mekegi",
        "Mekegi Bronze Age Site-Russia": "Mekegi (Bronze Age)",
        "Mekegi Medieval Gorodishche-Russia": "Mekegi Medieval Gorodishche"
    }
}

# C0135: Kurdyumivka
d["C0135"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Kurdyumivka Palaeolithic Camp-Ukraine", "new_name": "Kurdyumivka (Palaeolithic)", "reason": "Upper Palaeolithic camp near Bakhmutka valley"},
        {"op": "RENAME_META", "key": "Mistseznakhodzhennya znakhidky Neolithic Settlement II-Ukraine", "new_name": "Kurdyumivka (Neolithic)", "reason": "Neolithic settlement phase near Kurdyumivka"}
    ],
    "clean_names": {
        "Kurdyumivka-Ukraine": "Kurdyumivka",
        "Kurdyumivka Palaeolithic Camp-Ukraine": "Kurdyumivka (Palaeolithic)",
        "Mistseznakhodzhennya znakhidky Neolithic Settlement II-Ukraine": "Kurdyumivka (Neolithic)"
    }
}

# C0138: Myropillia
d["C0138"] = {
    "actions": [
        {"op": "RENAME_META", "key": "2 Myropillya Bronze Age Settlement-Ukraine", "new_name": "Myropillia (Bronze Age)", "reason": "Bronze Age settlement near Psyol river"},
        {"op": "RENAME_META", "key": "Myropillya-Ukraine", "new_name": "Myropillia (Rus)", "reason": "Romny-Rus hillfort complex on Studenok/Psyol"}
    ],
    "clean_names": {
        "Myropillia-Ukraine": "Myropillia",
        "2 Myropillya Bronze Age Settlement-Ukraine": "Myropillia (Bronze Age)",
        "Myropillya-Ukraine": "Myropillia (Rus)"
    }
}

# C0140: Nesterovskaya
d["C0140"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Nesterovskaya Iron Age Site-Russia", "new_name": "Nesterovskaya (Iron Age)", "reason": "Koban Iron Age settlement in Sunzha valley"},
        {"op": "RENAME_META", "key": "Nesterovskaya Medieval Gorodishche-Russia", "new_name": "Nesterovskaya Medieval Gorodishche", "reason": "Alanic/Early medieval hillfort site"}
    ],
    "clean_names": {
        "Nesterovskaya-Russia": "Nesterovskaya",
        "Nesterovskaya Iron Age Site-Russia": "Nesterovskaya (Iron Age)",
        "Nesterovskaya Medieval Gorodishche-Russia": "Nesterovskaya Medieval Gorodishche"
    }
}

# C0146: Nyzy
d["C0146"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Nyzy Iron Age Hillfort-Ukraine", "new_name": "Nyzy (Iron Age)", "reason": "Scythian-era Iron Age hillfort on Psyol terrace"},
        {"op": "RENAME_META", "key": "Nyzy-Ukraine_2", "new_name": "Nyzy (Rus)", "reason": "Romny Kievan Rus gorodishche"}
    ],
    "clean_names": {
        "Nyzy-Ukraine": "Nyzy",
        "Nyzy Iron Age Hillfort-Ukraine": "Nyzy (Iron Age)",
        "Nyzy-Ukraine_2": "Nyzy (Rus)"
    }
}

# C0155: Pisky
d["C0155"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Pisky Neolithic Settlement-Ukraine", "new_name": "Pisky (Neolithic)", "reason": "Neolithic settlement near Seym river"},
        {"op": "RENAME_META", "key": "Pisky Iron Age Hillfort-Ukraine", "new_name": "Pisky (Iron Age)", "reason": "Iron Age hillfort near Seym river"},
        {"op": "RENAME_META", "key": "2 Pisky Mediaeval Hillfort-Ukraine", "new_name": "Pisky (Medieval Hillfort)", "reason": "Kievan Rus medieval hillfort"}
    ],
    "clean_names": {
        "Pisky Neolithic Settlement-Ukraine": "Pisky (Neolithic)",
        "Pisky Iron Age Hillfort-Ukraine": "Pisky (Iron Age)",
        "2 Pisky Mediaeval Hillfort-Ukraine": "Pisky (Medieval Hillfort)"
    }
}

# C0160: Pushkari
d["C0160"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Pushkari I Stone Age Site-Ukraine", "new_name": "Pushkari (Neolithic)", "reason": "Neolithic campsite on Desna bluff"},
        {"op": "RENAME_META", "key": "Pushkari I Medieval Settlement-Ukraine", "new_name": "Pushkari (Medieval)", "reason": "Early medieval Slavic settlement on Desna bluff"}
    ],
    "clean_names": {
        "Pushkari I-Ukraine": "Pushkari I",
        "Pushkari I Stone Age Site-Ukraine": "Pushkari (Neolithic)",
        "Pushkari I Medieval Settlement-Ukraine": "Pushkari (Medieval)"
    }
}

# C0164: Romny
d["C0164"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Romny Iron Age Site-Ukraine", "new_name": "Romny (Iron Age)", "reason": "Scythian Iron Age settlement on Sula river"},
        {"op": "RENAME_META", "key": "Romny Iron Age Site 2-Ukraine", "new_name": "Romny (Chernyakhov)", "reason": "Chernyakhov settlement phase at Romny"}
    ],
    "clean_names": {
        "Romny-Ukraine": "Romny",
        "Romny Iron Age Site-Ukraine": "Romny (Iron Age)",
        "Romny Iron Age Site 2-Ukraine": "Romny (Chernyakhov)"
    }
}

# C0166: Sagan-Zaba
d["C0166"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Sagan-Zaba II Bronze Age Site-Russia", "new_name": "Sagan-Zaba (Neolithic-Bronze Age)", "reason": "Neolithic and Bronze Age petroglyph cliff campsite on Lake Baikal"},
        {"op": "RENAME_META", "key": "Sagan-Zaba II Iron Age Site-Russia", "new_name": "Sagan-Zaba (Iron Age)", "reason": "Iron Age campsite at Sagan-Zaba cove"}
    ],
    "clean_names": {
        "Sagan-Zaba II-Russia": "Sagan-Zaba II",
        "Sagan-Zaba II Bronze Age Site-Russia": "Sagan-Zaba (Neolithic-Bronze Age)",
        "Sagan-Zaba II Iron Age Site-Russia": "Sagan-Zaba (Iron Age)"
    }
}

# C0173: Serzhen-Yurt
d["C0173"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Serzhen-Yurt Bronze Age Site-Russia", "new_name": "Serzhen-Yurt (Bronze Age)", "reason": "Maykop/Bronze Age settlement phase"},
        {"op": "RENAME_META", "key": "Serzhen-Yurt Iron Age Site-Russia", "new_name": "Serzhen-Yurt (Iron Age)", "reason": "Koban Iron Age settlement and metallurgical center"}
    ],
    "clean_names": {
        "Serzhen-Yurt-Russia": "Serzhen-Yurt",
        "Serzhen-Yurt Bronze Age Site-Russia": "Serzhen-Yurt (Bronze Age)",
        "Serzhen-Yurt Iron Age Site-Russia": "Serzhen-Yurt (Iron Age)"
    }
}

# C0176: Siktyakh
d["C0176"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Siktyakh Bronze Age Site-Russia", "new_name": "Siktyakh (Bronze Age)", "reason": "Arctic Lena Bronze Age campsite"},
        {"op": "RENAME_META", "key": "Siktyakh Iron Age Site-Russia", "new_name": "Siktyakh (Iron Age)", "reason": "Arctic Lena Iron Age campsite"}
    ],
    "clean_names": {
        "Siktyakh-Russia": "Siktyakh",
        "Siktyakh Bronze Age Site-Russia": "Siktyakh (Bronze Age)",
        "Siktyakh Iron Age Site-Russia": "Siktyakh (Iron Age)"
    }
}

# C0177: Khalch
d["C0177"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Sozh Terrace Neolithic Radimichi Settlement-Belarus", "new_name": "Sozh Terrace (Neolithic)", "reason": "Neolithic settlement on Sozh river terrace near Vetka"},
        {"op": "RENAME_META", "key": "Khalch Iron Age Site-Belarus", "new_name": "Khalch (Iron Age)", "reason": "Milograd Iron Age settlement on Sozh bluff"},
        {"op": "RENAME_META", "key": "Khalch-Belarus", "new_name": "Khalch (Rus)", "reason": "Kolochin and Rus princely manor phase on Sozh bluff"}
    ],
    "clean_names": {
        "Khalch-Belarus": "Khalch (Rus)",
        "Khalch Iron Age Site-Belarus": "Khalch (Iron Age)",
        "Sozh Terrace Neolithic Radimichi Settlement-Belarus": "Sozh Terrace (Neolithic)"
    }
}

# C0181: Sumnagin I
d["C0181"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Sumnagin I Stone Age Site-Russia", "new_name": "Sumnagin (Mesolithic)", "reason": "Type site of Sumnagin Mesolithic culture on Aldan river"},
        {"op": "RENAME_META", "key": "Sumnagin I Bronze Age Site-Russia", "new_name": "Sumnagin (Bronze Age)", "reason": "Bronze Age phase of Sumnagin site"}
    ],
    "clean_names": {
        "Sumnagin I-Russia": "Sumnagin I",
        "Sumnagin I Stone Age Site-Russia": "Sumnagin (Mesolithic)",
        "Sumnagin I Bronze Age Site-Russia": "Sumnagin (Bronze Age)"
    }
}

# C0201: Velikent
d["C0201"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Velikent Bronze Age Site-Russia", "new_name": "Velikent (Bronze Age)", "reason": "Kura-Araxes / Velikent Bronze Age culture megasite"},
        {"op": "RENAME_META", "key": "Velikent I Archaeological Site-Russia", "new_name": "Velikent (Early Medieval)", "reason": "Sasanian/Early medieval settlement phase Velikent I"}
    ],
    "clean_names": {
        "Velikent-Russia": "Velikent",
        "Velikent Bronze Age Site-Russia": "Velikent (Bronze Age)",
        "Velikent I Archaeological Site-Russia": "Velikent (Early Medieval)"
    }
}

# C0208: Okhtyrka
d["C0208"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Vorskla Okhtyrka Hillfort-Ukraine", "new_name": "Vorskla Hillfort", "reason": "Pre-Mongol Vorskla frontier hillfort"},
        {"op": "RENAME_META", "key": "Vorskla Okhtyrka Hillfort Iron Age Site-Ukraine", "new_name": "Vorskla Hillfort (Iron Age)", "reason": "Scythian-era iron age hillfort at Okhtyrka"}
    ],
    "clean_names": {
        "Ochtyrka-Ukraine": "Okhtyrka",
        "Vorskla Okhtyrka Hillfort-Ukraine": "Vorskla Hillfort",
        "Vorskla Okhtyrka Hillfort Iron Age Site-Ukraine": "Vorskla Hillfort (Iron Age)"
    }
}

# C0215: Zayukovo
d["C0215"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Zayukovo Bronze Age Site-Russia", "new_name": "Zayukovo (Bronze Age)", "reason": "Bronze Age settlement in Baksan valley"},
        {"op": "RENAME_META", "key": "Zayukovo Gorodishche-Russia", "new_name": "Zayukovo Gorodishche", "reason": "Early medieval fortified settlement"}
    ],
    "clean_names": {
        "Zayukovo-Russia": "Zayukovo",
        "Zayukovo Bronze Age Site-Russia": "Zayukovo (Bronze Age)",
        "Zayukovo Gorodishche-Russia": "Zayukovo Gorodishche"
    }
}

# C0218: Zhupanovo
d["C0218"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Zhupanovo Iron Age Site-Russia", "new_name": "Zhupanovo (Iron Age)", "reason": "Iron Age campsite in Kronotsky Gulf"},
        {"op": "RENAME_META", "key": "Zhupanovo Gorodishche-Russia", "new_name": "Zhupanovo Gorodishche", "reason": "Early medieval fortified settlement"}
    ],
    "clean_names": {
        "Zhupanovo-Russia": "Zhupanovo",
        "Zhupanovo Iron Age Site-Russia": "Zhupanovo (Iron Age)",
        "Zhupanovo Gorodishche-Russia": "Zhupanovo Gorodishche"
    }
}

# C0229: Baraboi
d["C0229"] = {
    "actions": [
        {"op": "RENAME_META", "key": "dvosharove doby piznoyi bronzy ta rymskoho chasu Baraboy I Bronze Age Settlement-Ukraine", "new_name": "Baraboi I (Bronze Age)", "reason": "Bronze Age settlement on Baraboi river"},
        {"op": "RENAME_META", "key": "chernyakhivske Baraboy II Chernyakhov Settlement-Ukraine", "new_name": "Baraboi II (Chernyakhov)", "reason": "Chernyakhov settlement phase Baraboi II"}
    ],
    "clean_names": {
        "Baraboi-Ukraine": "Baraboi",
        "dvosharove doby piznoyi bronzy ta rymskoho chasu Baraboy I Bronze Age Settlement-Ukraine": "Baraboi I (Bronze Age)",
        "chernyakhivske Baraboy II Chernyakhov Settlement-Ukraine": "Baraboi II (Chernyakhov)"
    }
}

# C0232: Novi Troyany
d["C0232"] = {
    "actions": [
        {"op": "RENAME_META", "key": "dvosharove doby piznoyi bronzy ta rymskoho chasu Novi Troyany Bronze Age Settlement-Ukraine", "new_name": "Novi Troyany (Bronze Age)", "reason": "Late Bronze Age settlement near Novi Troyany"},
        {"op": "RENAME_META", "key": "dvosharove sabatynivske ta chernyakhivske Novi Troyany Chernyakhov Settlement-Ukraine", "new_name": "Novi Troyany (Chernyakhov)", "reason": "Chernyakhov settlement near Novi Troyany"}
    ],
    "clean_names": {
        "Novi Troyany-Ukraine": "Novi Troyany",
        "dvosharove doby piznoyi bronzy ta rymskoho chasu Novi Troyany Bronze Age Settlement-Ukraine": "Novi Troyany (Bronze Age)",
        "dvosharove sabatynivske ta chernyakhivske Novi Troyany Chernyakhov Settlement-Ukraine": "Novi Troyany (Chernyakhov)"
    }
}

# C0233: Ozerne
d["C0233"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Ozerne Neolithic Settlement-Ukraine", "new_name": "Ozerne (Neolithic)", "reason": "Neolithic settlement near Lake Yalpug"},
        {"op": "RENAME_META", "key": "dvosharove sabatynivske ta chernyakhivske Ozerne Chernyakhov Settlement-Ukraine", "new_name": "Ozerne (Chernyakhov)", "reason": "Chernyakhov settlement near Lake Yalpug"}
    ],
    "clean_names": {
        "Ozerne_UA_17-Ukraine": "Ozerne",
        "Ozerne Neolithic Settlement-Ukraine": "Ozerne (Neolithic)",
        "dvosharove sabatynivske ta chernyakhivske Ozerne Chernyakhov Settlement-Ukraine": "Ozerne (Chernyakhov)"
    }
}

# C0235: Kamyanka
d["C0235"] = {
    "actions": [
        {"op": "RENAME_META", "key": "dvosharove sabatynivske ta pershykh stolit n.e. Kamyanka Bronze Age Settlement-Ukraine", "new_name": "Kamyanka (Bronze Age)", "reason": "Sabatinovka Bronze Age settlement near Kamyanka"},
        {"op": "RENAME_META", "key": "dvosharove sabatynivske ta antychne Kamyanka VI Classical Polis-Ukraine", "new_name": "Kamyanka VI (Antiquity)", "reason": "Classical antiquity polis/settlement Kamyanka VI"},
        {"op": "RENAME_META", "key": "bahatosharove sabatynivske Mediaeval Hillfort-Ukraine", "new_name": "Kamyanka (Medieval Hillfort)", "reason": "Early medieval hillfort near Kamyanka"}
    ],
    "clean_names": {
        "dvosharove sabatynivske ta pershykh stolit n.e. Kamyanka Bronze Age Settlement-Ukraine": "Kamyanka (Bronze Age)",
        "dvosharove sabatynivske ta antychne Kamyanka VI Classical Polis-Ukraine": "Kamyanka VI (Antiquity)",
        "bahatosharove sabatynivske Mediaeval Hillfort-Ukraine": "Kamyanka (Medieval Hillfort)"
    }
}

# C0239: Shyroke
d["C0239"] = {
    "actions": [
        {"op": "RENAME_META", "key": "mezolitychna Shyroke Mesolithic Camp-Ukraine", "new_name": "Shyroke (Mesolithic)", "reason": "Mesolithic camp near Shyroke"},
        {"op": "RENAME_META", "key": "dvosharove doby piznoyi bronzy ta pershykh stolit n.e. Shyroke I Bronze Age Settlement-Ukraine", "new_name": "Shyroke I (Bronze Age)", "reason": "Late Bronze Age settlement Shyroke I"},
        {"op": "RENAME_META", "key": "chernyakhivske Shyroke II Chernyakhov Settlement-Ukraine", "new_name": "Shyroke II (Chernyakhov)", "reason": "Chernyakhov settlement Shyroke II"}
    ],
    "clean_names": {
        "mezolitychna Shyroke Mesolithic Camp-Ukraine": "Shyroke (Mesolithic)",
        "dvosharove doby piznoyi bronzy ta pershykh stolit n.e. Shyroke I Bronze Age Settlement-Ukraine": "Shyroke I (Bronze Age)",
        "chernyakhivske Shyroke II Chernyakhov Settlement-Ukraine": "Shyroke II (Chernyakhov)"
    }
}

# C0240: Yasky
d["C0240"] = {
    "actions": [
        {"op": "RENAME_META", "key": "piznopaleolitychna Yasky Palaeolithic Camp-Ukraine", "new_name": "Yasky (Palaeolithic)", "reason": "Late Palaeolithic campsite on lower Dniester"},
        {"op": "RENAME_META", "key": "Yaski Eneolithic Hillfort-Ukraine", "new_name": "Yasky (Eneolithic)", "reason": "Usatovo/Eneolithic hillfort near Yasky"}
    ],
    "clean_names": {
        "Yasky-Ukraine": "Yasky",
        "piznopaleolitychna Yasky Palaeolithic Camp-Ukraine": "Yasky (Palaeolithic)",
        "Yaski Eneolithic Hillfort-Ukraine": "Yasky (Eneolithic)"
    }
}

# C0246: Ternove
d["C0246"] = {
    "actions": [
        {"op": "RENAME_META", "key": "chornoliske Malyy horodok Early Metal Hillfort-Ukraine", "new_name": "Malyy Horodok", "reason": "Chornolis culture fortified settlement Malyy Horodok"},
        {"op": "RENAME_META", "key": "skifske Iron Age Hillfort-Ukraine", "new_name": "Ternove (Scythian Hillfort)", "reason": "Scythian-era iron age hillfort near Ternove"},
        {"op": "RENAME_META", "key": "ranno-slovyanskoyi chernyakhivskoyi kultury Chernyakhov Settlement-Ukraine", "new_name": "Ternove (Chernyakhov)", "reason": "Chernyakhov early Slavic settlement near Ternove"}
    ],
    "clean_names": {
        "chornoliske Malyy horodok Early Metal Hillfort-Ukraine": "Malyy Horodok",
        "skifske Iron Age Hillfort-Ukraine": "Ternove (Scythian Hillfort)",
        "ranno-slovyanskoyi chernyakhivskoyi kultury Chernyakhov Settlement-Ukraine": "Ternove (Chernyakhov)"
    }
}

# C0247: Rudnieve
d["C0247"] = {
    "actions": [
        {"op": "RENAME_META", "key": "1 Rudnyeve Iron Age Hillfort-Ukraine", "new_name": "Rudnieve (Iron Age)", "reason": "Iron Age hillfort near Rudnieve"},
        {"op": "RENAME_META", "key": "3 Rudnyeve Mediaeval Hillfort-Ukraine", "new_name": "Rudnieve (Medieval Hillfort)", "reason": "Medieval hillfort near Rudnieve"}
    ],
    "clean_names": {
        "1 Rudnyeve Iron Age Hillfort-Ukraine": "Rudnieve (Iron Age)",
        "3 Rudnyeve Mediaeval Hillfort-Ukraine": "Rudnieve (Medieval Hillfort)"
    }
}

# C0250: Agvali
d["C0250"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Agvali Medieval Gorodishche-Russia", "new_name": "Agvali Medieval Gorodishche", "reason": "Medieval fortified site distinct from modern village"}
    ],
    "clean_names": {
        "Agvali-Russia": "Agvali",
        "Agvali Medieval Gorodishche-Russia": "Agvali Medieval Gorodishche"
    }
}

# C0251: Akhvakh
d["C0251"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Akhvakh Medieval Gorodishche-Russia", "new_name": "Akhvakh Medieval Gorodishche", "reason": "Medieval fortified site distinct from modern village"}
    ],
    "clean_names": {
        "Akhvakh-Russia": "Akhvakh",
        "Akhvakh Medieval Gorodishche-Russia": "Akhvakh Medieval Gorodishche"
    }
}

# C0252: Aldy
d["C0252"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Aldy Medieval Gorodishche-Russia", "new_name": "Aldy Medieval Gorodishche", "reason": "Medieval fortified site distinct from modern Aldy/Grozny"}
    ],
    "clean_names": {
        "Aldy-Russia": "Aldy",
        "Aldy Medieval Gorodishche-Russia": "Aldy Medieval Gorodishche"
    }
}

# C0253: Aleksandriya
d["C0253"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Aleksandriya Stone Age Hillfort-Ukraine", "new_name": "Aleksandriya (Stone Age)", "reason": "Mesolithic/Neolithic stone age site on Oskol"},
        {"op": "RENAME_META", "key": "Aleksandriya Oskol-Ukraine", "new_name": "Aleksandriya (Eneolithic)", "reason": "Sredny Stog Eneolithic type site on Oskol river"}
    ],
    "clean_names": {
        "Aleksandriya Stone Age Hillfort-Ukraine": "Aleksandriya (Stone Age)",
        "Aleksandriya Oskol-Ukraine": "Aleksandriya (Eneolithic)"
    }
}

# C0255: Oleksandrivka
d["C0255"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Aleksandrovka Eneolithic Hillfort-Ukraine", "new_name": "Oleksandrivka (Eneolithic)", "reason": "Eneolithic hillfort near Chornomorsk"}
    ],
    "clean_names": {
        "Oleksandrivka_UA_17-Ukraine": "Oleksandrivka",
        "Aleksandrovka Eneolithic Hillfort-Ukraine": "Oleksandrivka (Eneolithic)"
    }
}

# C0259: Ali-Yurt
d["C0259"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Ali-Yurt Medieval Gorodishche-Russia", "new_name": "Ali-Yurt Medieval Gorodishche", "reason": "Medieval fortified settlement in Sunzha region"}
    ],
    "clean_names": {
        "Ali-Yurt-Russia": "Ali-Yurt",
        "Ali-Yurt Medieval Gorodishche-Russia": "Ali-Yurt Medieval Gorodishche"
    }
}

# C0260: Aliobrix
d["C0260"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Aliobrix Classical Polis-Ukraine", "new_name": "Aliobrix", "reason": "Greco-Roman/Celtic polis on Danube at Orlivka"},
        {"op": "RENAME_META", "key": "Aliobrix-Ukraine", "new_name": "Aliobrix (Medieval)", "reason": "Medieval Danubian fortress and port settlement"}
    ],
    "clean_names": {
        "Aliobrix Classical Polis-Ukraine": "Aliobrix",
        "Aliobrix-Ukraine": "Aliobrix (Medieval)"
    }
}

# C0262: Amnya
d["C0262"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Amnya settlement-Russia", "new_name": "Amnya (Medieval)", "reason": "Medieval fortified settlement on Amnya river distinct from Mesolithic Amnya I"}
    ],
    "clean_names": {
        "Amnya I-Russia": "Amnya I",
        "Amnya settlement-Russia": "Amnya (Medieval)"
    }
}

# C0263: Amvrosiyivka
d["C0263"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Amvrosievka Palaeolithic-Ukraine", "new_name": "Amvrosiyivka (Palaeolithic)", "reason": "Famous Upper Palaeolithic bison kill site on Krynka river"}
    ],
    "clean_names": {
        "Amvrosiyivka-Ukraine": "Amvrosiyivka",
        "Amvrosievka Palaeolithic-Ukraine": "Amvrosiyivka (Palaeolithic)"
    }
}

# C0264: Lubny
d["C0264"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Ancient settlement in Lubny-Ukraine", "new_name": "Lubny (Bronze Age)", "reason": "Bronze Age settlement and barrow cemetery near Sula river"}
    ],
    "clean_names": {
        "Lubny-Ukraine": "Lubny",
        "Ancient settlement in Lubny-Ukraine": "Lubny (Bronze Age)"
    }
}

# C0265: Mykhailivka
d["C0265"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Ancient settlement of Chernyakhov culture No. 151, Mykhailivka-Ukraine", "new_name": "Mykhailivka (Chernyakhov)", "reason": "Chernyakhov culture settlement No. 151"},
        {"op": "RENAME_META", "key": "Dvosharove poselennya trypilskoyi ta chornoliskoyi kultur Rus Settlement-Ukraine", "new_name": "Mykhailivka (Rus)", "reason": "Kievan Rus medieval settlement phase"}
    ],
    "clean_names": {
        "Ancient settlement of Chernyakhov culture No. 151, Mykhailivka-Ukraine": "Mykhailivka (Chernyakhov)",
        "Dvosharove poselennya trypilskoyi ta chornoliskoyi kultur Rus Settlement-Ukraine": "Mykhailivka (Rus)"
    }
}

# C0267: Bakhmut
d["C0267"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Artemivs'k-Ukraine", "new_name": "Bakhmut", "reason": "Canonical modern Ukrainian name for Bakhmut"},
        {"op": "RENAME_META", "key": "Ancient settlement of late Bronze Age Chirkova-III, Bakhmut-Ukraine", "new_name": "Chirkova-III", "reason": "Late Bronze Age archaeological settlement Chirkova-III"}
    ],
    "clean_names": {
        "Artemivs'k-Ukraine": "Bakhmut",
        "Ancient settlement of late Bronze Age Chirkova-III, Bakhmut-Ukraine": "Chirkova-III"
    }
}

# C0268: Andi
d["C0268"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Andi Medieval Gorodishche-Russia", "new_name": "Andi Medieval Gorodishche", "reason": "Medieval fortified settlement distinct from modern aul Andi"}
    ],
    "clean_names": {
        "Andi-Russia": "Andi",
        "Andi Medieval Gorodishche-Russia": "Andi Medieval Gorodishche"
    }
}

# C0269: Andriivka
d["C0269"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Andriyivka Palaeolithic Camp-Ukraine", "new_name": "Andriivka (Palaeolithic)", "reason": "Late Palaeolithic campsite near Andriivka"},
        {"op": "RENAME_META", "key": "Andreevka Eneolithic Hillfort-Ukraine", "new_name": "Andriivka (Eneolithic)", "reason": "Eneolithic hillfort near Andriivka"}
    ],
    "clean_names": {
        "Andriyivka Palaeolithic Camp-Ukraine": "Andriivka (Palaeolithic)",
        "Andreevka Eneolithic Hillfort-Ukraine": "Andriivka (Eneolithic)"
    }
}

# C0274: Ardon
d["C0274"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Ardon Medieval Gorodishche-Russia", "new_name": "Ardon Medieval Gorodishche", "reason": "Early medieval Alanic gorodishche on Ardon river"}
    ],
    "clean_names": {
        "Ardon-Russia": "Ardon",
        "Ardon Medieval Gorodishche-Russia": "Ardon Medieval Gorodishche"
    }
}

# C0275: Volnovakha
d["C0275"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Arkheolohichnyy obyekt Mediaeval Hillfort III-Ukraine", "new_name": "Volnovakha (Medieval Hillfort)", "reason": "Medieval nomadic/Slavic hillfort near Volnovakha"}
    ],
    "clean_names": {
        "Volnovakha-Ukraine": "Volnovakha",
        "Arkheolohichnyy obyekt Mediaeval Hillfort III-Ukraine": "Volnovakha (Medieval Hillfort)"
    }
}

# C0276: Pisky
d["C0276"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Arkheolohichnyy obyekt Stone Age Settlement II-Ukraine", "new_name": "Pisky (Stone Age)", "reason": "Stone Age campsite near Pisky/Donetsk"},
        {"op": "RENAME_META", "key": "Arkheolohichnyy obyekt Mediaeval Hillfort-Ukraine", "new_name": "Pisky (Medieval Hillfort)", "reason": "Medieval hillfort near Pisky/Donetsk"}
    ],
    "clean_names": {
        "Arkheolohichnyy obyekt Stone Age Settlement II-Ukraine": "Pisky (Stone Age)",
        "Arkheolohichnyy obyekt Mediaeval Hillfort-Ukraine": "Pisky (Medieval Hillfort)"
    }
}

# C0277: Arkit
d["C0277"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Arkit Medieval Gorodishche-Russia", "new_name": "Arkit Medieval Gorodishche", "reason": "Medieval fortified settlement distinct from modern Arkit"}
    ],
    "clean_names": {
        "Arkit-Russia": "Arkit",
        "Arkit Medieval Gorodishche-Russia": "Arkit Medieval Gorodishche"
    }
}

# C0279: Arzamas
d["C0279"] = {
    "actions": [
        {"op": "DROP_JUNK", "key": "Arzamas Kremlin-Russia", "reason": "Heritage registry fortress built 1572 under Ivan IV with fabricated anachronistic 800..1300 scrape dates"}
    ],
    "clean_names": {
        "Arzamas-Russia": "Arzamas"
    }
}

# C0280: Ashilta
d["C0280"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Ashilta Medieval Gorodishche-Russia", "new_name": "Ashilta Medieval Gorodishche", "reason": "Medieval fortified settlement in Avar mountains"}
    ],
    "clean_names": {
        "Ashilta-Russia": "Ashilta",
        "Ashilta Medieval Gorodishche-Russia": "Ashilta Medieval Gorodishche"
    }
}

# C0281: Assinovskaya
d["C0281"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Assinovskaya Bronze Age Site-Russia", "new_name": "Assinovskaya (Bronze Age)", "reason": "Pre-hiatus Bronze Age settlement in Sunzha valley"}
    ],
    "clean_names": {
        "Assinovskaya-Russia": "Assinovskaya",
        "Assinovskaya Bronze Age Site-Russia": "Assinovskaya (Bronze Age)"
    }
}

# C0282: Atemar
d["C0282"] = {
    "actions": [
        {"op": "DROP_JUNK", "key": "Atemar defensive wall-Russia", "reason": "Heritage registry earthen rampart of 1638 Atemar frontier fortress with fabricated anachronistic 800..1300 scrape dates"}
    ],
    "clean_names": {
        "Atemar-Russia": "Atemar"
    }
}

# C0283: Babanka
d["C0283"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Babanka Palaeolithic Camp-Ukraine", "new_name": "Babanka (Palaeolithic)", "reason": "Upper Palaeolithic campsite on Revukha river"}
    ],
    "clean_names": {
        "Babanka-Ukraine": "Babanka",
        "Babanka Palaeolithic Camp-Ukraine": "Babanka (Palaeolithic)"
    }
}

# C0286: Tyvriv
d["C0286"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bakajka Eneolithic Hillfort-Ukraine", "new_name": "Bakajka", "reason": "Distinct Trypillia/Eneolithic hillfort Bakajka near Tyvriv"}
    ],
    "clean_names": {
        "Tyvriv-Ukraine": "Tyvriv",
        "Bakajka Eneolithic Hillfort-Ukraine": "Bakajka"
    }
}

# C0287: Bakota
d["C0287"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bakota Iron Age Site-Ukraine", "new_name": "Bakota (Iron Age)", "reason": "Chernyakhov iron age settlement on Dniester"},
        {"op": "RENAME_META", "key": "Bakota-Ukraine", "new_name": "Bakota (Medieval)", "reason": "Historic medieval regional capital of Ponyzia / Bakota monastery"}
    ],
    "clean_names": {
        "Bakota Iron Age Site-Ukraine": "Bakota (Iron Age)",
        "Bakota-Ukraine": "Bakota (Medieval)"
    }
}

# C0289: Balta
d["C0289"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Balta Bronze Age Settlement-Ukraine", "new_name": "Balta (Bronze Age)", "reason": "Bronze Age settlement in Kodyma valley"}
    ],
    "clean_names": {
        "Balta-Ukraine": "Balta",
        "Balta Bronze Age Settlement-Ukraine": "Balta (Bronze Age)"
    }
}

# C0290: Bancerovshchina
d["C0290"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bancerovshchina Iron Age Site-Belarus", "new_name": "Bancerovshchina (Iron Age)", "reason": "Early Iron Age phase of Bancerovshchina on Svisloch"}
    ],
    "clean_names": {
        "Bancerovshchina-Belarus": "Bancerovshchina",
        "Bancerovshchina Iron Age Site-Belarus": "Bancerovshchina (Iron Age)"
    }
}

# C0291: Banyliv
d["C0291"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Banyliv 1 Eneolithic Hillfort-Ukraine", "new_name": "Banyliv (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort near Cheremosh river"}
    ],
    "clean_names": {
        "Banyliv-Ukraine": "Banyliv",
        "Banyliv 1 Eneolithic Hillfort-Ukraine": "Banyliv (Eneolithic)"
    }
}

# C0293: Baranivka
d["C0293"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Baranivka Iron Age Hillfort-Ukraine", "new_name": "Baranivka (Iron Age)", "reason": "Iron Age hillfort on Sluch river"}
    ],
    "clean_names": {
        "Baranivka-Ukraine": "Baranivka",
        "Baranivka Iron Age Hillfort-Ukraine": "Baranivka (Iron Age)"
    }
}

# C0294: Barda
d["C0294"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bardymskoye-Russia", "new_name": "Bardymskoe Gorodishche", "reason": "Early medieval Lomovatovo/Nevolino hillfort on Tulva river"}
    ],
    "clean_names": {
        "Barda-Russia": "Barda",
        "Bardymskoye-Russia": "Bardymskoe Gorodishche"
    }
}

# C0295: Barsuki
d["C0295"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Barsuki Medieval Gorodishche-Russia", "new_name": "Barsuki Medieval Gorodishche", "reason": "Medieval fortified settlement in Sunzha valley"}
    ],
    "clean_names": {
        "Barsuki_RU_19-Russia": "Barsuki",
        "Barsuki Medieval Gorodishche-Russia": "Barsuki Medieval Gorodishche"
    }
}

# C0297: Baryshivka
d["C0297"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Baryshevka Eneolithic Hillfort-Ukraine", "new_name": "Baryshivka (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort on Trubizh river"}
    ],
    "clean_names": {
        "Baryshivka-Ukraine": "Baryshivka",
        "Baryshevka Eneolithic Hillfort-Ukraine": "Baryshivka (Eneolithic)"
    }
}

# C0298: Basivka
d["C0298"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Basovka Hillfort Iron Age Site-Ukraine", "new_name": "Basivka (Iron Age)", "reason": "Scythian-era iron age hillfort on Khmelyovka river"},
        {"op": "RENAME_META", "key": "Basovka Hillfort-Ukraine", "new_name": "Basivka (Chernyakhov)", "reason": "Chernyakhov culture phase of Basivka hillfort"}
    ],
    "clean_names": {
        "Basovka Hillfort Iron Age Site-Ukraine": "Basivka (Iron Age)",
        "Basovka Hillfort-Ukraine": "Basivka (Chernyakhov)"
    }
}

# C0300: Baturyn
d["C0300"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Baturin-Ukraine", "new_name": "Baturyn (Rus)", "reason": "Pre-Mongol Romny-Rus hillfort on Seym river"}
    ],
    "clean_names": {
        "Baturyn-Ukraine": "Baturyn",
        "Baturin-Ukraine": "Baturyn (Rus)"
    }
}

# C0302: Bayangol
d["C0302"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bayangol-Russia_2", "new_name": "Bayangol (Xiongnu)", "reason": "Xiongnu-era fortified settlement in Transbaikalia"}
    ],
    "clean_names": {
        "Bayangol-Russia": "Bayangol",
        "Bayangol-Russia_2": "Bayangol (Xiongnu)"
    }
}

# C0303: Bazaliivka
d["C0303"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bazaliyivka Iron Age Hillfort-Ukraine", "new_name": "Bazaliivka (Iron Age)", "reason": "Iron Age hillfort on Siversky Donets"}
    ],
    "clean_names": {
        "Bazaliivka-Ukraine": "Bazaliivka",
        "Bazaliyivka Iron Age Hillfort-Ukraine": "Bazaliivka (Iron Age)"
    }
}

# C0308: Berezivka
d["C0308"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Berezovka Neolithic Settlement-Ukraine", "new_name": "Berezivka (Neolithic)", "reason": "Neolithic settlement on Tylihul river"}
    ],
    "clean_names": {
        "Berezivka-Ukraine": "Berezivka",
        "Berezovka Neolithic Settlement-Ukraine": "Berezivka (Neolithic)"
    }
}

# C0309: Bershad
d["C0309"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bershad Eneolithic Hillfort-Ukraine", "new_name": "Bershad (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort on Dokhna river"}
    ],
    "clean_names": {
        "Bershad-Ukraine": "Bershad",
        "Bershad Eneolithic Hillfort-Ukraine": "Bershad (Eneolithic)"
    }
}

# C0310: Bersuat
d["C0310"] = {
    "actions": [
        {"op": "DROP_JUNK", "key": "Bersuat hillfort-Russia", "reason": "Heritage registry duplicate entry of Sintashta Bronze Age settlement Bersuat with fabricated anachronistic 800..1300 scrape dates"}
    ],
    "clean_names": {
        "Bersuat-Russia": "Bersuat"
    }
}

# C0311: Beryslav
d["C0311"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Beryslav Iron Age Hillfort-Ukraine", "new_name": "Beryslav (Iron Age)", "reason": "Late Scythian Iron Age hillfort on Dnieper bluff"}
    ],
    "clean_names": {
        "Beryslav-Ukraine": "Beryslav",
        "Beryslav Iron Age Hillfort-Ukraine": "Beryslav (Iron Age)"
    }
}

# C0312: Bezvodnoye
d["C0312"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bezvodinsko-Akhmylovsky krug pamyatnikov-Russia", "new_name": "Bezvodnoye (Early Medieval)", "reason": "Early medieval Volga Finn cemetery and settlement horizon on Volga river"}
    ],
    "clean_names": {
        "Bezvodnoye-Russia": "Bezvodnoye",
        "Bezvodinsko-Akhmylovsky krug pamyatnikov-Russia": "Bezvodnoye (Early Medieval)"
    }
}

# C0314: Bichura
d["C0314"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bichura (archaeological site)-Russia", "new_name": "Bichura (Archaeological Site)", "reason": "Medieval nomadic archaeological settlement site in Transbaikalia"}
    ],
    "clean_names": {
        "Bichura-Russia": "Bichura",
        "Bichura (archaeological site)-Russia": "Bichura (Archaeological Site)"
    }
}

# C0315: Smolyany
d["C0315"] = {
    "actions": [
        {"op": "DROP_JUNK", "key": "Biely Koviel Castle-Belarus", "reason": "Ruins of Prince Sanguszko castle built c. 1626 in Smolyany scraped with fabricated anachronistic 800..1300 dates"}
    ],
    "clean_names": {
        "Smolyany-Belarus": "Smolyany"
    }
}

# C0316: Bila Tserkva
d["C0316"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bila Tserkva-Paliyeva Gora Eneolithic Hillfort-Ukraine", "new_name": "Bila Tserkva (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort on Paliyeva Hora overlooking Ros river"}
    ],
    "clean_names": {
        "Bila Cerkva-Ukraine": "Bila Tserkva",
        "Bila Tserkva-Paliyeva Gora Eneolithic Hillfort-Ukraine": "Bila Tserkva (Eneolithic)"
    }
}

# C0317: Bili Oslavy
d["C0317"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bili Oslavy Bronze Age Settlement-Ukraine", "new_name": "Bili Oslavy (Bronze Age)", "reason": "Bronze Age settlement in Carpathian foothills on Oslava river"}
    ],
    "clean_names": {
        "Bili Oslavy-Ukraine": "Bili Oslavy",
        "Bili Oslavy Bronze Age Settlement-Ukraine": "Bili Oslavy (Bronze Age)"
    }
}

# C0319: Bilolissya
d["C0319"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bilolissya Mesolithic Camp Hillfort-Ukraine", "new_name": "Bilolissya (Mesolithic)", "reason": "Mesolithic camp in Sasyk liman basin"}
    ],
    "clean_names": {
        "Bilolissya-Ukraine": "Bilolissya",
        "Bilolissya Mesolithic Camp Hillfort-Ukraine": "Bilolissya (Mesolithic)"
    }
}

# C0320: Bilopillia
d["C0320"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bilopillya Iron Age Hillfort 2-Ukraine", "new_name": "Bilopillia (Iron Age)", "reason": "Iron Age hillfort on Vyr river"}
    ],
    "clean_names": {
        "Bilopillia-Ukraine": "Bilopillia",
        "Bilopillya Iron Age Hillfort 2-Ukraine": "Bilopillia (Iron Age)"
    }
}

# C0321: Bilshivtsi
d["C0321"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bilshivtsy Neolithic Settlement-Ukraine", "new_name": "Bilshivtsi (Neolithic)", "reason": "Linear Pottery/Neolithic settlement on Hnyla Lypa river"}
    ],
    "clean_names": {
        "Bilshivtsi-Ukraine": "Bilshivtsi",
        "Bilshivtsy Neolithic Settlement-Ukraine": "Bilshivtsi (Neolithic)"
    }
}

# C0322: Birsk
d["C0322"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Birsk Gorodishche-Russia", "new_name": "Birsk Gorodishche", "reason": "Bahmutino culture early medieval hillfort on Belaya river"}
    ],
    "clean_names": {
        "Birsk-Russia": "Birsk",
        "Birsk Gorodishche-Russia": "Birsk Gorodishche"
    }
}

# C0324: Blahovishchenka
d["C0324"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Blagoveshchenskoye Classical Polis-Ukraine", "new_name": "Blahovishchenka (Antiquity)", "reason": "Classical antiquity Greco-Scythian settlement on Dnieper"}
    ],
    "clean_names": {
        "Blahovishchenka-Ukraine": "Blahovishchenka",
        "Blagoveshchenskoye Classical Polis-Ukraine": "Blahovishchenka (Antiquity)"
    }
}

# C0328: Bohuslav
d["C0328"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bohuslav Neolithic Settlement-Ukraine", "new_name": "Bohuslav (Neolithic)", "reason": "Neolithic settlement in Samara river valley"}
    ],
    "clean_names": {
        "Bohuslav_UA_04-Ukraine": "Bohuslav",
        "Bohuslav Neolithic Settlement-Ukraine": "Bohuslav (Neolithic)"
    }
}

# C0329: Bolhrad
d["C0329"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bolhrad Eneolithic Hillfort-Ukraine", "new_name": "Bolhrad (Eneolithic)", "reason": "Gumelnita/Eneolithic hillfort on Lake Yalpug"}
    ],
    "clean_names": {
        "Bolhrad-Ukraine": "Bolhrad",
        "Bolhrad Eneolithic Hillfort-Ukraine": "Bolhrad (Eneolithic)"
    }
}

# C0332: Bondurivka
d["C0332"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bondurivka Eneolithic Hillfort-Ukraine", "new_name": "Bondurivka (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort near Bondurivka"}
    ],
    "clean_names": {
        "Bondurivka-Ukraine": "Bondurivka",
        "Bondurivka Eneolithic Hillfort-Ukraine": "Bondurivka (Eneolithic)"
    }
}

# C0333: Borch
d["C0333"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Borch Medieval Gorodishche-Russia", "new_name": "Borch Medieval Gorodishche", "reason": "Medieval Lezgin mountain fortified settlement"}
    ],
    "clean_names": {
        "Borch-Russia": "Borch",
        "Borch Medieval Gorodishche-Russia": "Borch Medieval Gorodishche"
    }
}

# C0334: Borodianka
d["C0334"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Borodyanka Mesolithic Camp Hillfort-Ukraine", "new_name": "Borodianka (Mesolithic)", "reason": "Mesolithic camp on Zdvyzh river"}
    ],
    "clean_names": {
        "Borodianka-Ukraine": "Borodianka",
        "Borodyanka Mesolithic Camp Hillfort-Ukraine": "Borodianka (Mesolithic)"
    }
}

# C0338: Borzna
d["C0338"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Borzna-Ukraine_2", "new_name": "Borzna (Rus)", "reason": "Pre-Mongol Romny-Rus rampart settlement on Borzenka river"}
    ],
    "clean_names": {
        "Borzna-Ukraine": "Borzna",
        "Borzna-Ukraine_2": "Borzna (Rus)"
    }
}

# C0339: Botlikh
d["C0339"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Botlikh Medieval Gorodishche-Russia", "new_name": "Botlikh Medieval Gorodishche", "reason": "Medieval fortified settlement in Andi Koysu valley"}
    ],
    "clean_names": {
        "Botlikh-Russia": "Botlikh",
        "Botlikh Medieval Gorodishche-Russia": "Botlikh Medieval Gorodishche"
    }
}

# C0340: Bovshiv
d["C0340"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bovshiv 1 Eneolithic Hillfort-Ukraine", "new_name": "Bovshiv (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort overlooking Dniester"},
        {"op": "RENAME_META", "key": "Bovshiv-Ukraine", "new_name": "Bovshiv (Medieval)", "reason": "Early medieval Slavic/Przeworsk settlement phase"}
    ],
    "clean_names": {
        "Bovshiv 1 Eneolithic Hillfort-Ukraine": "Bovshiv (Eneolithic)",
        "Bovshiv-Ukraine": "Bovshiv (Medieval)"
    }
}

# C0341: Boiany
d["C0341"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Boyany 1 Eneolithic Hillfort-Ukraine", "new_name": "Boiany (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort near Prut river"}
    ],
    "clean_names": {
        "Boiany-Ukraine": "Boiany",
        "Boyany 1 Eneolithic Hillfort-Ukraine": "Boiany (Eneolithic)"
    }
}

# C0342: Braguny
d["C0342"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Braguny Medieval Gorodishche-Russia", "new_name": "Braguny Medieval Gorodishche", "reason": "Medieval fortified settlement near Sunzha/Terek confluence"}
    ],
    "clean_names": {
        "Braguny-Russia": "Braguny",
        "Braguny Medieval Gorodishche-Russia": "Braguny Medieval Gorodishche"
    }
}

# C0343: Branytsia
d["C0343"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Branytsya-3 Bronze Age Settlement-Ukraine", "new_name": "Branytsia (Bronze Age)", "reason": "Bronze Age settlement near Branytsia"}
    ],
    "clean_names": {
        "Branytsia-Ukraine": "Branytsia",
        "Branytsya-3 Bronze Age Settlement-Ukraine": "Branytsia (Bronze Age)"
    }
}

# C0347: Brayiliv
d["C0347"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Brayiliv Bronze Age Settlement-Ukraine", "new_name": "Brayiliv (Bronze Age)", "reason": "Bronze Age settlement on Riv river"}
    ],
    "clean_names": {
        "Brayiliv-Ukraine": "Brayiliv",
        "Brayiliv Bronze Age Settlement-Ukraine": "Brayiliv (Bronze Age)"
    }
}

# C0349: Bryanka
d["C0349"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Brjanka-Ukraine", "new_name": "Bryanka", "reason": "Clean modern English name for Bryanka"},
        {"op": "RENAME_META", "key": "Bryanka Bronze Age Settlement-Ukraine", "new_name": "Bryanka (Bronze Age)", "reason": "Bronze Age settlement on Lozova river"}
    ],
    "clean_names": {
        "Brjanka-Ukraine": "Bryanka",
        "Bryanka Bronze Age Settlement-Ukraine": "Bryanka (Bronze Age)"
    }
}

# C0350: Bubnivska Slobidka
d["C0350"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bubnivska Slobidka Mediaeval Hillfort-Ukraine", "new_name": "Bubnivska Slobidka (Medieval Hillfort)", "reason": "Early medieval Rus hillfort near Dnieper"}
    ],
    "clean_names": {
        "Bubnivska Slobidka-Ukraine": "Bubnivska Slobidka",
        "Bubnivska Slobidka Mediaeval Hillfort-Ukraine": "Bubnivska Slobidka (Medieval Hillfort)"
    }
}

# C0351: Buchach
d["C0351"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Buchach Bronze Age Site-Ukraine", "new_name": "Buchach (Bronze Age)", "reason": "Bronze Age settlement on Strypa bluff"}
    ],
    "clean_names": {
        "Buchach-Ukraine": "Buchach",
        "Buchach Bronze Age Site-Ukraine": "Buchach (Bronze Age)"
    }
}

# C0352: Bohdanovshchyna / Budyshche
d["C0352"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bohdanovshchyna Bronze Age Settlement-Ukraine", "new_name": "Bohdanovshchyna", "reason": "Bronze Age settlement at Bohdanovshchyna"},
        {"op": "RENAME_META", "key": "Budyshche-2 Late Mediaeval Settlement-Ukraine", "new_name": "Budyshche", "reason": "Late medieval settlement Budyshche-2"}
    ],
    "clean_names": {
        "Bohdanovshchyna Bronze Age Settlement-Ukraine": "Bohdanovshchyna",
        "Budyshche-2 Late Mediaeval Settlement-Ukraine": "Budyshche"
    }
}

# C0353: Buky
d["C0353"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Buky Eneolithic Hillfort-Ukraine", "new_name": "Buky (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort on Hnylyi Tikych canyon"}
    ],
    "clean_names": {
        "Buky-Ukraine": "Buky",
        "Buky Eneolithic Hillfort-Ukraine": "Buky (Eneolithic)"
    }
}

# C0354: Buret
d["C0354"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Buret 2-Russia", "new_name": "Buret (Medieval)", "reason": "Medieval nomadic archaeological settlement Buret 2 on Angara river"}
    ],
    "clean_names": {
        "Buret-Russia": "Buret",
        "Buret 2-Russia": "Buret (Medieval)"
    }
}

# C0355: Burkhala
d["C0355"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Burkhala-Russia_2", "new_name": "Burkhala (Neolithic)", "reason": "Stone Age Neolithic camp on Kolyma terrace"}
    ],
    "clean_names": {
        "Burkhala-Russia": "Burkhala",
        "Burkhala-Russia_2": "Burkhala (Neolithic)"
    }
}

# C0356: Buzhanka
d["C0356"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Buzhanka-Sotnitske pole Eneolithic Hillfort-Ukraine", "new_name": "Buzhanka (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort at Sotnitske Pole"}
    ],
    "clean_names": {
        "Buzhanka-Ukraine": "Buzhanka",
        "Buzhanka-Sotnitske pole Eneolithic Hillfort-Ukraine": "Buzhanka (Eneolithic)"
    }
}

# C0358: Bykivka
d["C0358"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bykovka Eneolithic Hillfort-Ukraine", "new_name": "Bykivka (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort near Bykivka"}
    ],
    "clean_names": {
        "Bykivka-Ukraine": "Bykivka",
        "Bykovka Eneolithic Hillfort-Ukraine": "Bykivka (Eneolithic)"
    }
}

# C0359: Bykovo
d["C0359"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bykovo-Kurgans Iron Age Site-Russia", "new_name": "Bykovo (Iron Age)", "reason": "Sarmatian-era Iron Age kurgan settlement on Volga"}
    ],
    "clean_names": {
        "Bykovo-Russia": "Bykovo",
        "Bykovo-Kurgans Iron Age Site-Russia": "Bykovo (Iron Age)"
    }
}

# C0360: Bylym
d["C0360"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Bylym Bronze Age Site-Russia", "new_name": "Bylym (Bronze Age)", "reason": "Bronze Age settlement in Baksan gorge"}
    ],
    "clean_names": {
        "Bylym-Russia": "Bylym",
        "Bylym Bronze Age Site-Russia": "Bylym (Bronze Age)"
    }
}

# C0367: Tulchyn
d["C0367"] = {
    "actions": [
        {"op": "DROP_JUNK", "key": "Castle Tulczynie-Ukraine", "reason": "Early 17th-century castle/palace in Tulchyn scraped with fabricated anachronistic 800..1300 dates"}
    ],
    "clean_names": {
        "Tulchyn-Ukraine": "Tulchyn"
    }
}

# C0370: Chapli
d["C0370"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Chapli Palaeolithic Camp-Ukraine", "new_name": "Chapli (Palaeolithic)", "reason": "Mesolithic/Palaeolithic campsite on Dnieper rapids"}
    ],
    "clean_names": {
        "Chapli-Ukraine": "Chapli",
        "Chapli Palaeolithic Camp-Ukraine": "Chapli (Palaeolithic)"
    }
}

# C0371: Chaplynka
d["C0371"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Chaplynka Bronze Age Settlement-Ukraine", "new_name": "Chaplynka (Bronze Age)", "reason": "Bronze Age settlement in Black Sea steppe"}
    ],
    "clean_names": {
        "Chaplynka-Ukraine": "Chaplynka",
        "Chaplynka Bronze Age Settlement-Ukraine": "Chaplynka (Bronze Age)"
    }
}

# C0373: Chausy
d["C0373"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Chausy-Belarus_2", "new_name": "Chausy (Rus)", "reason": "Basya-Pronya Radimichi/Rus early medieval settlement"}
    ],
    "clean_names": {
        "Chausy-Belarus": "Chausy",
        "Chausy-Belarus_2": "Chausy (Rus)"
    }
}

# C0374: Chebarkul
d["C0374"] = {
    "actions": [
        {"op": "DROP_JUNK", "key": "Chebarkulskaya krepost-Russia", "reason": "Heritage registry fortress founded 1736 on Lake Chebarkul with fabricated anachronistic 800..1300 scrape dates"}
    ],
    "clean_names": {
        "`'Cebarkul'-Russia": "Chebarkul"
    }
}

# C0375: Chechelnyk
d["C0375"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Chechelnyk Eneolithic Hillfort-Ukraine", "new_name": "Chechelnyk (Eneolithic)", "reason": "Trypillia/Eneolithic hillfort on Savrynka river"}
    ],
    "clean_names": {
        "Chechelnyk-Ukraine": "Chechelnyk",
        "Chechelnyk Eneolithic Hillfort-Ukraine": "Chechelnyk (Eneolithic)"
    }
}

# C0376: Chechen-Aul
d["C0376"] = {
    "actions": [
        {"op": "RENAME_META", "key": "Chechen-Aul Medieval Gorodishche-Russia", "new_name": "Chechen-Aul Medieval Gorodishche", "reason": "Medieval fortified settlement on Argun river"}
    ],
    "clean_names": {
        "Chechen-Aul-Russia": "Chechen-Aul",
        "Chechen-Aul Medieval Gorodishche-Russia": "Chechen-Aul Medieval Gorodishche"
    }
}

# Assemble results in the EXACT order of input_data
output_list = []
total_clusters = len(input_data)
assert len(d) == total_clusters, f"Expected {total_clusters} clusters, got {len(d)}"

for c in input_data:
    cid = c['cluster_id']
    if cid not in d:
        raise ValueError(f"Missing decision for {cid}")
    res = {
        "cluster_id": cid,
        "actions": d[cid]["actions"],
        "clean_names": d[cid]["clean_names"]
    }
    output_list.append(res)

with open(output_path, 'w', encoding='utf-8') as out:
    json.dump(output_list, out, indent=2, ensure_ascii=False)

print(f"Successfully generated {output_path} with {len(output_list)} clusters.")
