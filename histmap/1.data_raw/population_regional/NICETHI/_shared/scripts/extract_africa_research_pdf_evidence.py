#!/usr/bin/env python3
"""
Parallel programmatic PDF & DOCX historical settlement & demographic evidence
extractor for Operation Viscount Project NICETHI (`Africa Research Files`).

Version 2 (audited & precision-hardened):
- Multiprocessing (max 4 workers, run via run_bounded.js)
- Deduplicates PDFs by BOTH sha256 AND normalized filename stem
- Fixes comma-thousands parsing in hectare/area conversions (e.g. `5,252.5 ha`)
- Fixes 3-digit year false matches (never extracts `:633` or `1,870` as years!)
- Eliminates false settlement collisions (`Marka` != `Merca`, TOC/Index lines,
  regional survey areas, modern Hong Kong/New York benchmark comparisons)
- Supports compound word numbers (`two hundred thousand`, `fifteen to twenty
  thousand`, `10-20,000`, `20 000 habitants`)
- Flags any passage/page citing banned global compendia (Chandler, Modelski,
  Populstat, McEvedy, Klein Goldewijk, HYDE, Bairoch, Lahmeyer)
"""

import json
import re
import time
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pymupdf


ARCHIVE_ROOT = Path(
    r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\_references\Africa Research Files"
)
INDEX_PATH = Path(
    r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\NICETHI\_shared\africa_research_files_index.json"
)
OUT_DIR = Path(
    r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\NICETHI\_shared\settlement_sources"
)
RAW_OUT_PATH = OUT_DIR / "africa_research_pdf_raw.json"


SETTLEMENTS = [
    # --- WEST AFRICA: GULF OF GUINEA / YORUBA / BENIN / DAHOMEY / NIGER DELTA / IGBO ---
    ("Benin City", "Nigeria (Edo)", "West Africa", 6.335, 5.627, r"\b(?:Benin City|Great Benin|City of Benin|Edo\s+city|Binni)\b"),
    ("Ile-Ife", "Nigeria (Yoruba)", "West Africa", 7.482, 4.560, r"\b(?:Ile[- ]?Ife|Il[eé][- ]?If[eẹ]|Old Ife|\bIfe\b)\b"),
    ("Old Oyo", "Nigeria (Yoruba)", "West Africa", 8.993, 4.331, r"\b(?:Old Oyo|Oyo[- ]?Ile|Ọyọ[- ]?Ile|Katunga)\b"),
    ("Ibadan", "Nigeria (Yoruba)", "West Africa", 7.377, 3.947, r"\bIbadan\b"),
    ("Abeokuta", "Nigeria (Yoruba)", "West Africa", 7.155, 3.345, r"\bAb[eẹ]okuta\b"),
    ("Ijebu-Ode", "Nigeria (Yoruba)", "West Africa", 6.820, 3.920, r"\bIjebu[- ]?Ode\b"),
    ("Ilesa", "Nigeria (Yoruba)", "West Africa", 7.628, 4.742, r"\b(?:Ilesa|Ilesha|Il[eé][sṣ]a)\b"),
    ("Ilorin", "Nigeria (Yoruba/Nupe)", "West Africa", 8.496, 4.542, r"\bIlorin\b"),
    ("Ogbomoso", "Nigeria (Yoruba)", "West Africa", 8.133, 4.244, r"\bOgbomo[sṣ]h?o\b"),
    ("Osogbo", "Nigeria (Yoruba)", "West Africa", 7.771, 4.557, r"\bOsh?ogbo\b"),
    ("Iwo", "Nigeria (Yoruba)", "West Africa", 7.635, 4.181, r"\bIwo(?:\s+town)?\b"),
    ("Iseyin", "Nigeria (Yoruba)", "West Africa", 7.976, 3.592, r"\bIseyin\b"),
    ("Igboho", "Nigeria (Yoruba)", "West Africa", 8.838, 3.756, r"\bIgboho\b"),
    ("Owo", "Nigeria (Yoruba)", "West Africa", 7.196, 5.587, r"\bOwo\b"),
    ("Ede", "Nigeria (Yoruba)", "West Africa", 7.736, 4.436, r"\bEde[- ]?Ile\b"),
    ("Modakeke", "Nigeria (Yoruba)", "West Africa", 7.474, 4.542, r"\bModakeke\b"),
    ("Ketu", "Benin (Yoruba)", "West Africa", 7.363, 2.599, r"\bK[eé]tou?\b"),
    ("Lagos", "Nigeria (Lagos)", "West Africa", 6.454, 3.395, r"\b(?:Lagos|Eko)\b"),
    ("Badagry", "Nigeria (Lagos)", "West Africa", 6.415, 2.881, r"\bBadagr[iy]\b"),
    ("Epe", "Nigeria (Ijebu)", "West Africa", 6.584, 3.983, r"\bEpe(?:\s+town)?\b"),
    ("Ughoton", "Nigeria (Edo)", "West Africa", 6.178, 5.398, r"\b(?:Ughoton|Gwato)\b"),
    ("Abomey", "Benin (Dahomey)", "West Africa", 7.183, 1.991, r"\bAbomey\b"),
    ("Allada", "Benin (Allada)", "West Africa", 6.665, 2.151, r"\b(?:Allada|Ardra|Ardrah)\b"),
    ("Savi", "Benin (Hueda)", "West Africa", 6.433, 2.117, r"\b(?:Savi|Sahe|Xavier)\b"),
    ("Ouidah", "Benin (Dahomey)", "West Africa", 6.363, 2.085, r"\b(?:Ouidah|Whydah|Glehue|Juda)\b"),
    ("Cana", "Benin (Dahomey)", "West Africa", 7.100, 2.083, r"\b(?:Cana|Calmina)\b"),
    ("Porto-Novo", "Benin (Hogbonu)", "West Africa", 6.497, 2.629, r"\b(?:Porto[- ]?Novo|Hogbonu|Ajase)\b"),
    ("Notse", "Togo (Ewe)", "West Africa", 6.950, 1.167, r"\b(?:Nots[eé]|Nuatja|Notsie)\b"),
    ("Tado", "Togo (Adja)", "West Africa", 7.157, 1.592, r"\bTado\b"),
    ("Old Calabar", "Nigeria (Cross River)", "West Africa", 4.952, 8.322, r"\b(?:Old Calabar|Calabar|Duke Town|Creek Town)\b"),
    ("Bonny", "Nigeria (Niger Delta)", "West Africa", 4.451, 7.170, r"\b(?:Bonny|Ibani)\b"),
    ("Elem Kalabari", "Nigeria (Niger Delta)", "West Africa", 4.533, 6.833, r"\b(?:Elem Kalabari|New Calabar)\b"),
    ("Nembe", "Nigeria (Niger Delta)", "West Africa", 4.539, 6.404, r"\b(?:Nembe|Brass)\b"),
    ("Warri", "Nigeria (Niger Delta)", "West Africa", 5.517, 5.750, r"\b(?:Warri|Ode[- ]?Itsekiri)\b"),
    ("Aboh", "Nigeria (Lower Niger)", "West Africa", 5.548, 6.526, r"\bAboh\b"),
    ("Onitsha", "Nigeria (Igbo)", "West Africa", 6.145, 6.788, r"\bOnitsha\b"),
    ("Igbo-Ukwu", "Nigeria (Igbo)", "West Africa", 6.017, 7.017, r"\bIgbo[- ]?Ukwu\b"),
    ("Arochukwu", "Nigeria (Igbo)", "West Africa", 5.389, 7.912, r"\bArochukwu\b"),
    ("Idah", "Nigeria (Igala)", "West Africa", 7.113, 6.738, r"\bIdah\b"),
    ("Bida", "Nigeria (Nupe)", "West Africa", 9.080, 6.010, r"\bBida\b"),
    ("Raba", "Nigeria (Nupe)", "West Africa", 9.217, 5.017, r"\b(?:Rabba|Raba)\b"),

    # --- WEST AFRICA: GOLD COAST / VOLTAIC / IVORY COAST ---
    ("Kumasi", "Ghana (Asante)", "West Africa", 6.688, -1.624, r"\b(?:Kumasi|Coomassie|Kumase)\b"),
    ("Elmina", "Ghana (Gold Coast)", "West Africa", 5.084, -1.351, r"\b(?:Elmina|Edina|S[aã]o Jorge da Mina)\b"),
    ("Cape Coast", "Ghana (Gold Coast)", "West Africa", 5.105, -1.246, r"\b(?:Cape Coast|Oguaa|Cabo Corso)\b"),
    ("Accra", "Ghana (Ga)", "West Africa", 5.556, -0.197, r"\b(?:Accra|Great Accra|Ayawaso)\b"),
    ("Begho", "Ghana (Brong)", "West Africa", 7.867, -2.533, r"\b(?:Begho|Bighu|Nsoko)\b"),
    ("Bono Manso", "Ghana (Bono)", "West Africa", 7.700, -1.833, r"\bBono[- ]?Manso\b"),
    ("Asantemanso", "Ghana (Asante)", "West Africa", 6.467, -1.583, r"\bAsantemanso\b"),
    ("Adansemanso", "Ghana (Adanse)", "West Africa", 6.267, -1.567, r"\bAdansemanso\b"),
    ("Salaga", "Ghana (Gonja)", "West Africa", 8.550, -0.519, r"\bSalaga\b"),
    ("Kintampo", "Ghana (Bono)", "West Africa", 8.056, -1.731, r"\bKintampo\b"),
    ("Yendi", "Ghana (Dagbon)", "West Africa", 9.443, -0.010, r"\bYendi\b"),
    ("Daboya", "Ghana (Gonja)", "West Africa", 9.533, -1.383, r"\bDaboya\b"),
    ("Eguafo", "Ghana (Gold Coast)", "West Africa", 5.150, -1.433, r"\bEguafo\b"),
    ("Komenda", "Ghana (Gold Coast)", "West Africa", 5.050, -1.483, r"\b(?:Komenda|Commenda)\b"),
    ("Anomabu", "Ghana (Fante)", "West Africa", 5.174, -1.119, r"\bAnomab[ou]\b"),
    ("Axim", "Ghana (Gold Coast)", "West Africa", 4.867, -2.241, r"\bAxim\b"),
    ("Kong", "Ivory Coast (Dyula)", "West Africa", 9.151, -4.610, r"\b(?:city of Kong|town of Kong|Kong\s+(?:city|town|had|was|contained|numbered))\b"),
    ("Bondoukou", "Ivory Coast (Gyaman)", "West Africa", 8.040, -2.800, r"\bBondoukou\b"),
    ("Bouna", "Ivory Coast", "West Africa", 9.267, -3.000, r"\bBouna\b"),
    ("Ouagadougou", "Burkina Faso (Mossi)", "West Africa", 12.371, -1.520, r"\b(?:Ouagadougou|Wagadugu)\b"),
    ("Bobo-Dioulasso", "Burkina Faso", "West Africa", 11.177, -4.298, r"\b(?:Bobo[- ]?Dioulasso|\bSya\b)\b"),
    ("Tenkodogo", "Burkina Faso (Mossi)", "West Africa", 11.780, -0.370, r"\bTenkodogo\b"),
    ("Ouahigouya", "Burkina Faso (Yatenga)", "West Africa", 13.583, -2.422, r"\bOuahigouya\b"),
    ("Loropeni", "Burkina Faso", "West Africa", 10.300, -3.550, r"\bLorop[eé]ni\b"),

    # --- WEST AFRICA: SENEGAMBIA / UPPER GUINEA / SIERRA LEONE ---
    ("Saint-Louis", "Senegal", "West Africa", 16.018, -16.490, r"\bSaint[- ]?Louis\b"),
    ("Goree", "Senegal", "West Africa", 14.667, -17.398, r"\bGor[eé]e\b"),
    ("Rufisque", "Senegal", "West Africa", 14.716, -17.273, r"\bRufisque\b"),
    ("Dakar", "Senegal", "West Africa", 14.717, -17.468, r"\bDakar\b"),
    ("Diakhao", "Senegal (Sine)", "West Africa", 14.377, -16.340, r"\bDiakhao\b"),
    ("Lambaye", "Senegal (Bawol)", "West Africa", 14.783, -16.483, r"\bLambaye\b"),
    ("Joal", "Senegal (Sine)", "West Africa", 14.167, -16.833, r"\bJoal\b"),
    ("Podor", "Senegal (Futa Tooro)", "West Africa", 16.652, -14.959, r"\bPodor\b"),
    ("Bakel", "Senegal (Gajaaga)", "West Africa", 14.901, -12.457, r"\bBakel\b"),
    ("Banjul", "The Gambia", "West Africa", 13.455, -16.579, r"\b(?:Banjul|Bathurst)\b"),
    ("Kansala", "Guinea-Bissau (Kaabu)", "West Africa", 12.400, -14.533, r"\bKansala\b"),
    ("Cacheu", "Guinea-Bissau", "West Africa", 12.274, -16.165, r"\bCacheu\b"),
    ("Bissau", "Guinea-Bissau", "West Africa", 11.864, -15.598, r"\bBissau\b"),
    ("Geba", "Guinea-Bissau", "West Africa", 12.200, -14.850, r"\bGeba\b"),
    ("Sonkunda", "The Gambia (Kantora)", "West Africa", 13.400, -13.900, r"\b(?:Sonkunda|Sunkunda|Song Kunda)\b"),
    ("Timbo", "Guinea (Futa Jallon)", "West Africa", 10.633, -11.833, r"\bTimbo\b"),
    ("Labe", "Guinea (Futa Jallon)", "West Africa", 11.318, -12.283, r"\bLab[eé]\b"),
    ("Kankan", "Guinea", "West Africa", 10.385, -9.306, r"\bKankan\b"),
    ("Niani", "Guinea/Mali (Mali Empire)", "West Africa", 11.383, -8.383, r"\bNiani\b"),
    ("Freetown", "Sierra Leone", "West Africa", 8.484, -13.234, r"\bFreetown\b"),
    ("Falaba", "Sierra Leone (Solima)", "West Africa", 9.855, -11.320, r"\bFalaba\b"),
    ("Port Loko", "Sierra Leone", "West Africa", 8.767, -12.787, r"\bPort Loko\b"),
    ("Monrovia", "Liberia", "West Africa", 6.315, -10.807, r"\bMonrovia\b"),

    # --- SAHEL / WESTERN & CENTRAL SUDAN / HAUSALAND / BORNO ---
    ("Timbuktu", "Mali (Sahel)", "Sahel", 16.767, -3.003, r"\b(?:Timbuktu|Timbuctoo|Tombouctou|Timbuctu)\b"),
    ("Gao", "Mali (Songhay)", "Sahel", 16.267, -0.050, r"\b(?:Gao(?:\s+Ancien)?|Kawkaw|Gawgaw)\b"),
    ("Gao Saney", "Mali (Songhay)", "Sahel", 16.290, 0.015, r"\bGao[- ]?Saney\b"),
    ("Jenne-Jeno", "Mali (Inland Niger Delta)", "Sahel", 13.888, -4.540, r"\b(?:Jenn[eé][- ]?Jeno|Djenn[eé][- ]?Jeno|Jenne[- ]?jeno)\b"),
    ("Djenne", "Mali (Inland Niger Delta)", "Sahel", 13.906, -4.555, r"\b(?:Djenn[eé]|Jenn[eé])(?!-?[Jj]eno)\b"),
    ("Dia", "Mali (Inland Niger Delta)", "Sahel", 14.383, -4.900, r"\b(?:Dia[- ]?(?:Shoma|Mara)|town of Dia|city of Dia|site of Dia|Dia,?\s+(?:which|covered|mound|complex|had|reached))\b"),
    ("Koumbi Saleh", "Mauritania (Ghana)", "Sahel", 15.765, -7.971, r"\b(?:Koumbi[- ]?Saleh|Kumbi[- ]?Saleh)\b"),
    ("Awdaghost", "Mauritania (Sahel)", "Sahel", 17.420, -10.420, r"\b(?:Awdaghost|Awdaghust|Tegdaoust)\b"),
    ("Walata", "Mauritania (Sahel)", "Sahel", 17.300, -7.024, r"\b(?:Walata|Oualata|Iwalatan)\b"),
    ("Tichitt", "Mauritania (Sahel)", "Sahel", 18.447, -9.498, r"\b(?:Tichitt?|Dhar Tichitt)\b"),
    ("Chinguetti", "Mauritania (Adrar)", "Sahel", 20.463, -12.362, r"\b(?:Chinguetti|Shinqit)\b"),
    ("Ouadane", "Mauritania (Adrar)", "Sahel", 20.931, -11.620, r"\b(?:Ouadane|Wadan)\b"),
    ("Essouk-Tadmekka", "Mali (Adrar des Ifoghas)", "Sahel", 18.767, 1.183, r"\b(?:Essouk|Es[- ]?Souk|Tadmekka|Tadmakka)\b"),
    ("Kukiya", "Mali (Songhay)", "Sahel", 15.350, 0.750, r"\b(?:Kukiya|Bentia|Koukiya)\b"),
    ("Segou", "Mali (Segou)", "Sahel", 13.440, -6.260, r"\b(?:S[eé]gou(?:-Sikoro)?|Segu(?:-Sikoro)?)\b"),
    ("San", "Mali (Bani)", "Sahel", 13.303, -4.896, r"\b(?:town of San|city of San|San(?:\s+and\s+the\s+Sank[eé])|San\s+(?:counted|had|contained|reached|was\s+a\s+town|[-–]\s*whose))\b"),
    ("Sansanding", "Mali (Middle Niger)", "Sahel", 13.743, -5.970, r"\b(?:Sansanding|Sinsani)\b"),
    ("Hamdallahi", "Mali (Masina)", "Sahel", 14.317, -4.100, r"\b(?:Hamdallahi|Hamdullahi)\b"),
    ("Bamako", "Mali", "Sahel", 12.639, -8.003, r"\bBamako\b"),
    ("Sikasso", "Mali (Kenedugu)", "Sahel", 11.318, -5.667, r"\bSikasso\b"),
    ("Mopti", "Mali", "Sahel", 14.496, -4.198, r"\bMopti\b"),
    ("Sorotomo", "Mali (Segou)", "Sahel", 13.433, -5.900, r"\bSorotomo\b"),
    ("Ton Masala", "Mali (Segou)", "Sahel", 13.450, -6.050, r"\bTon Masala\b"),
    ("Tendirma", "Mali (Songhay)", "Sahel", 15.950, -3.767, r"\bTendirma\b"),
    ("Nioro", "Mali (Kaarta)", "Sahel", 15.233, -9.583, r"\bNioro\b"),
    ("Diara", "Mali (Kingui)", "Sahel", 15.217, -9.317, r"\b(?:Diara|Dyara)\b"),
    ("Agadez", "Niger (Air)", "Sahel", 16.973, 7.991, r"\bAgade[zs]\b"),
    ("Takedda", "Niger (Azelik)", "Sahel", 17.217, 6.667, r"\b(?:Takedda|Tagidda|Azelik)\b"),
    ("Zinder", "Niger (Damagaram)", "Sahel", 13.805, 8.988, r"\bZinder\b"),
    ("Maradi", "Niger", "Sahel", 13.500, 7.102, r"\bMaradi\b"),
    ("Kano", "Nigeria (Hausa)", "Sahel", 12.002, 8.592, r"\bKano\b"),
    ("Katsina", "Nigeria (Hausa)", "Sahel", 12.991, 7.602, r"\bKatsina\b"),
    ("Zaria", "Nigeria (Hausa/Zazzau)", "Sahel", 11.085, 7.720, r"\b(?:Zaria|Birnin Zaria|Zazzau)\b"),
    ("Turunku", "Nigeria (Zazzau)", "Sahel", 10.800, 7.700, r"\bTurunku\b"),
    ("Kufena", "Nigeria (Zazzau)", "Sahel", 11.080, 7.670, r"\bKufena\b"),
    ("Sokoto", "Nigeria (Sokoto Caliphate)", "Sahel", 13.062, 5.234, r"\bSokoto\b"),
    ("Daura", "Nigeria (Hausa)", "Sahel", 13.033, 8.320, r"\bDaura\b"),
    ("Gobir (Alkalawa)", "Nigeria (Hausa)", "Sahel", 13.467, 5.883, r"\b(?:Alkalawa|Birnin Gobir)\b"),
    ("Surame", "Nigeria (Kebbi)", "Sahel", 13.095, 4.912, r"\bSurame\b"),
    ("Birnin Kebbi", "Nigeria (Kebbi)", "Sahel", 12.454, 4.198, r"\bBirnin Kebbi\b"),
    ("Gwandu", "Nigeria (Sokoto)", "Sahel", 12.502, 4.642, r"\bGwandu\b"),
    ("Birnin Gazargamo", "Nigeria (Borno)", "Sahel", 13.005, 12.310, r"\b(?:Birnin[- ]?Gazargamo|Ngazargamu|Gazargamo|Birni Ngazargamu)\b"),
    ("Kukawa", "Nigeria (Borno)", "Sahel", 12.925, 13.560, r"\b(?:Kukawa|Kuka)\b"),
    ("Nguru", "Nigeria (Borno/Yobe)", "Sahel", 12.877, 10.455, r"\bNguru\b"),
    ("Dikwa", "Nigeria (Borno)", "Sahel", 12.036, 13.918, r"\bDikwa\b"),
    ("Daima", "Nigeria (Lake Chad)", "Sahel", 12.200, 14.450, r"\bDaima\b"),
    ("Bauchi", "Nigeria (Sokoto)", "Sahel", 10.316, 9.844, r"\bBauchi\b"),
    ("Yola", "Nigeria (Adamawa)", "Sahel", 9.203, 12.495, r"\bYola\b"),
    ("Ngaoundere", "Cameroon (Adamawa)", "Central/Congo/Angola", 7.317, 13.583, r"\bNgaound[eé]r[eé]\b"),
    ("Wara", "Chad (Wadai)", "Sahel", 14.183, 20.700, r"\b(?:Wara|Ouara)\b"),
    ("Abeche", "Chad (Wadai)", "Sahel", 13.829, 20.832, r"\bAb[eé]ch[eé]\b"),
    ("Massenya", "Chad (Bagirmi)", "Sahel", 11.403, 16.170, r"\bMassenya\b"),
    ("Njimi", "Chad (Kanem)", "Sahel", 14.500, 15.500, r"\bNjimi\b"),
    ("Bussa", "Nigeria (Borgu)", "West Africa", 10.220, 4.580, r"\bBussa\b"),
    ("Nikki", "Benin (Borgu)", "West Africa", 9.940, 3.210, r"\bNikki\b"),
    ("Sijilmassa", "Morocco (Trans-Saharan)", "Sahel", 31.280, -4.277, r"\bSijilm[aā]ssa\b"),

    # --- NUBIA / SUDAN ---
    ("Sennar", "Sudan (Funj)", "Nubia/Sudan", 13.567, 33.567, r"\b(?:Sennar|Sinnar)\b"),
    ("Old Dongola", "Sudan (Makuria)", "Nubia/Sudan", 18.222, 30.744, r"\b(?:Old Dongola|Dongola)\b"),
    ("Soba", "Sudan (Alodia)", "Nubia/Sudan", 15.525, 32.677, r"\bSoba\b"),
    ("Meroe", "Sudan (Kush)", "Nubia/Sudan", 16.938, 33.749, r"\bMero[eë]\b"),
    ("Kerma", "Sudan (Nubia)", "Nubia/Sudan", 19.601, 30.410, r"\bKerma\b"),
    ("Napata", "Sudan (Kush)", "Nubia/Sudan", 18.533, 31.833, r"\bNapata\b"),
    ("Suakin", "Sudan (Red Sea)", "Nubia/Sudan", 19.106, 37.332, r"\b(?:Suakin|Sawakin)\b"),
    ("Shendi", "Sudan (Nile)", "Nubia/Sudan", 16.692, 33.434, r"\bShendi\b"),
    ("Khartoum", "Sudan", "Nubia/Sudan", 15.501, 32.560, r"\bKhartoum\b"),
    ("Omdurman", "Sudan", "Nubia/Sudan", 15.645, 32.478, r"\bOmdurman\b"),
    ("El Fasher", "Sudan (Darfur)", "Nubia/Sudan", 13.628, 25.349, r"\b(?:El[- ]?Fasher|Al[- ]?Fashir)\b"),
    ("Kobbei", "Sudan (Darfur)", "Nubia/Sudan", 14.083, 25.250, r"\b(?:Kobbei|Kobe)\b"),
    ("El Obeid", "Sudan (Kordofan)", "Nubia/Sudan", 13.183, 30.217, r"\bEl[- ]?Obeid\b"),
    ("Kassala", "Sudan", "Nubia/Sudan", 15.451, 36.400, r"\bKassala\b"),
    ("Qasr Ibrim", "Egypt/Nubia", "Nubia/Sudan", 22.650, 31.992, r"\bQasr Ibrim\b"),
    ("Faras", "Sudan (Nobadia)", "Nubia/Sudan", 22.217, 31.483, r"\bFaras\b"),

    # --- HORN OF AFRICA / ETHIOPIA / ERITREA / SOMALIA ---
    ("Aksum", "Ethiopia (Aksum)", "Horn/Ethiopia", 14.121, 38.723, r"\b(?:Aksum|Axum)\b"),
    ("Adulis", "Eritrea (Red Sea)", "Horn/Ethiopia", 15.263, 39.660, r"\bAdulis\b"),
    ("Matara", "Eritrea (Aksumite)", "Horn/Ethiopia", 14.700, 39.417, r"\bMatara\b"),
    ("Qohaito", "Eritrea (Aksumite)", "Horn/Ethiopia", 14.883, 39.433, r"\b(?:Qohaito|Kohaito)\b"),
    ("Yeha", "Ethiopia (Pre-Aksumite)", "Horn/Ethiopia", 14.283, 39.017, r"\bYeha\b"),
    ("Gondar", "Ethiopia", "Horn/Ethiopia", 12.603, 37.452, r"\bGond[ae]r\b"),
    ("Lalibela", "Ethiopia (Zagwe)", "Horn/Ethiopia", 12.032, 39.047, r"\b(?:Lalibela|Roha)\b"),
    ("Harar", "Ethiopia (Adal/Harar)", "Horn/Ethiopia", 9.313, 42.118, r"\bHarar\b"),
    ("Addis Ababa", "Ethiopia", "Horn/Ethiopia", 9.030, 38.740, r"\bAddis Ababa\b"),
    ("Ankober", "Ethiopia (Shoa)", "Horn/Ethiopia", 9.591, 39.733, r"\bAnkober\b"),
    ("Adwa", "Ethiopia (Tigray)", "Horn/Ethiopia", 14.167, 38.900, r"\bAdwa\b"),
    ("Massawa", "Eritrea (Red Sea)", "Horn/Ethiopia", 15.608, 39.474, r"\b(?:Massawa|Mitsiwa|Masawa)\b"),
    ("Zeila", "Somalia (Adal)", "Horn/Ethiopia", 11.354, 43.473, r"\b(?:Zeila|Zayla|Saylac)\b"),
    ("Berbera", "Somalia", "Horn/Ethiopia", 10.440, 45.014, r"\bBerbera\b"),
    ("Mogadishu", "Somalia (Banadir)", "Horn/Ethiopia", 2.047, 45.318, r"\b(?:Mogadishu|Maqdishu|Muqdisho)\b"),
    ("Brava", "Somalia (Banadir)", "Horn/Ethiopia", 1.113, 44.030, r"\b(?:Brava|Barawa|Baraawe)\b"),
    ("Merca", "Somalia (Banadir)", "Horn/Ethiopia", 1.716, 44.771, r"\bMerca\b"),
    ("Kismayo", "Somalia", "Horn/Ethiopia", -0.358, 42.545, r"\bKismay[ou]\b"),

    # --- EAST AFRICA / SWAHILI COAST / GREAT LAKES ---
    ("Kilwa Kisiwani", "Tanzania (Swahili)", "East Africa/Swahili", -8.960, 39.500, r"\b(?:Kilwa(?:\s+Kisiwani)?|Quiloa)\b"),
    ("Mombasa", "Kenya (Swahili)", "East Africa/Swahili", -4.043, 39.668, r"\bMombasa\b"),
    ("Malindi", "Kenya (Swahili)", "East Africa/Swahili", -3.219, 40.117, r"\bMalindi\b"),
    ("Gedi", "Kenya (Swahili)", "East Africa/Swahili", -3.309, 40.017, r"\b(?:Gedi|Gede)\b"),
    ("Lamu", "Kenya (Swahili)", "East Africa/Swahili", -2.272, 40.902, r"\bLamu\b"),
    ("Pate", "Kenya (Swahili)", "East Africa/Swahili", -2.141, 41.022, r"\bPate\b"),
    ("Shanga", "Kenya (Swahili)", "East Africa/Swahili", -2.117, 41.050, r"\bShanga\b"),
    ("Manda", "Kenya (Swahili)", "East Africa/Swahili", -2.250, 40.967, r"\bManda\b"),
    ("Siyu", "Kenya (Swahili)", "East Africa/Swahili", -2.094, 41.059, r"\bSiyu\b"),
    ("Takwa", "Kenya (Swahili)", "East Africa/Swahili", -2.300, 40.950, r"\bTakwa\b"),
    ("Ungwana", "Kenya (Swahili)", "East Africa/Swahili", -2.517, 40.200, r"\bUngwana\b"),
    ("Zanzibar", "Tanzania (Swahili)", "East Africa/Swahili", -6.165, 39.203, r"\b(?:Zanzibar(?:\s+Town|\s+City)?|Unguja)\b"),
    ("Unguja Ukuu", "Tanzania (Zanzibar)", "East Africa/Swahili", -6.317, 39.367, r"\bUnguja Ukuu\b"),
    ("Tumbatu", "Tanzania (Zanzibar)", "East Africa/Swahili", -5.817, 39.217, r"\bTumbatu\b"),
    ("Pemba", "Tanzania (Swahili)", "East Africa/Swahili", -5.032, 39.776, r"\b(?:Pemba|Chwaka|Mtambwe Mkuu|Ras Mkumbuu)\b"),
    ("Bagamoyo", "Tanzania (Swahili)", "East Africa/Swahili", -6.442, 38.904, r"\bBagamoyo\b"),
    ("Pangani", "Tanzania (Swahili)", "East Africa/Swahili", -5.425, 38.975, r"\bPangani\b"),
    ("Kaole", "Tanzania (Swahili)", "East Africa/Swahili", -6.467, 38.933, r"\bKaole\b"),
    ("Songo Mnara", "Tanzania (Swahili)", "East Africa/Swahili", -9.040, 39.555, r"\bSongo Mnara\b"),
    ("Kisimani Mafia", "Tanzania (Mafia Island)", "East Africa/Swahili", -7.950, 39.600, r"\b(?:Kisimani Mafia|Kua)\b"),
    ("Tabora", "Tanzania (Nyamwezi)", "East Africa/Swahili", -5.016, 32.827, r"\b(?:Tabora|Kazeh)\b"),
    ("Ujiji", "Tanzania (Lake Tanganyika)", "East Africa/Swahili", -4.916, 29.676, r"\bUjiji\b"),
    ("Bigo", "Uganda (Interlacustrine)", "East Africa/Swahili", 0.140, 31.260, r"\bBigo(?:\s+bya\s+Mugenyi)?\b"),
    ("Ntusi", "Uganda (Interlacustrine)", "East Africa/Swahili", 0.050, 31.217, r"\bNtusi\b"),
    ("Mengo (Kampala)", "Uganda (Buganda)", "East Africa/Swahili", 0.300, 32.556, r"\b(?:Mengo|Rubaga|Kampala|Kibuga)\b"),
    ("Nyanza", "Rwanda", "East Africa/Swahili", -2.352, 29.751, r"\bNyanza\b"),
    ("Sofala", "Mozambique (Swahili)", "Southern Africa", -20.150, 34.717, r"\bSofala\b"),
    ("Mozambique Island", "Mozambique", "Southern Africa", -15.034, 40.736, r"\b(?:Mozambique Island|Ilha de Mo[cç]ambique)\b"),
    ("Angoche", "Mozambique (Swahili)", "Southern Africa", -16.233, 39.908, r"\bAngoche\b"),
    ("Sena", "Mozambique (Zambezi)", "Southern Africa", -17.450, 35.033, r"\bSena\b"),
    ("Tete", "Mozambique (Zambezi)", "Southern Africa", -16.156, 33.587, r"\bTete\b"),
    ("Quelimane", "Mozambique", "Southern Africa", -17.879, 36.888, r"\bQuelimane\b"),
    ("Chibuene", "Mozambique", "Southern Africa", -22.033, 35.333, r"\bChibuene\b"),

    # --- CENTRAL AFRICA / KONGO / ANGOLA / CAMEROON ---
    ("Mbanza Kongo", "Angola (Kongo)", "Central/Congo/Angola", -6.267, 14.248, r"\b(?:Mbanza[- ]?Kongo|Mbanza[- ]?Congo|S[aã]o Salvador|San Salvador)\b"),
    ("Mbanza Soyo", "Angola (Soyo)", "Central/Congo/Angola", -6.135, 12.369, r"\b(?:Mbanza[- ]?Soyo|Mbanza[- ]?Nsoyo|Soyo|Mpinda)\b"),
    ("Luanda", "Angola", "Central/Congo/Angola", -8.839, 13.289, r"\b(?:Luanda|Loanda)\b"),
    ("Benguela", "Angola", "Central/Congo/Angola", -12.576, 13.405, r"\bBenguela\b"),
    ("Loango", "Republic of Congo (Loango)", "Central/Congo/Angola", -4.650, 11.817, r"\b(?:Buali|Mbanza Loango|Loango(?:\s+town|\s+city|\s+capital)?)\b"),
    ("Cabinda", "Angola (Ngoyo)", "Central/Congo/Angola", -5.550, 12.200, r"\b(?:Cabinda|Kabinda)\b"),
    ("Musumba", "DRC (Lunda)", "Central/Congo/Angola", -8.400, 23.167, r"\bMusumba\b"),
    ("Babungo", "Cameroon (Grassfields)", "Central/Congo/Angola", 6.067, 10.433, r"\bBabungo\b"),
    ("Foumban", "Cameroon (Bamum)", "Central/Congo/Angola", 5.727, 10.900, r"\bFoumban\b"),
    ("Douala", "Cameroon", "Central/Congo/Angola", 4.051, 9.768, r"\bDouala\b"),

    # --- SOUTHERN AFRICA ---
    ("Great Zimbabwe", "Zimbabwe", "Southern Africa", -20.267, 30.933, r"\bGreat Zimbabwe\b"),
    ("Khami", "Zimbabwe (Torwa)", "Southern Africa", -20.156, 28.404, r"\bKhami\b"),
    ("Mapungubwe", "South Africa (Limpopo)", "Southern Africa", -22.208, 29.373, r"\bMapungubwe\b"),
    ("Mapela Hill", "Zimbabwe", "Southern Africa", -21.950, 28.750, r"\bMapela(?:\s+Hill)?\b"),
    ("Danangombe", "Zimbabwe (Rozvi)", "Southern Africa", -19.933, 29.383, r"\b(?:Danangombe|Dhlo[- ]?Dhlo|Danamombe|Danan'ombe)\b"),
    ("Thulamela", "South Africa (Limpopo)", "Southern Africa", -22.430, 31.200, r"\b(?:Thulamela|Tulamela)\b"),
    ("Naletale", "Zimbabwe", "Southern Africa", -19.880, 29.530, r"\bNaletale\b"),
    ("K2 (Bambandyanalo)", "South Africa (Limpopo)", "Southern Africa", -22.217, 29.370, r"\b(?:Bambandyanalo|\bK2\b)\b"),
    ("Schroda", "South Africa (Limpopo)", "Southern Africa", -22.183, 29.433, r"\bSchroda\b"),
    ("Toutswemogala", "Botswana", "Southern Africa", -22.233, 27.183, r"\b(?:Toutswemogala|Toutswe)\b"),
    ("Bosutswe", "Botswana", "Southern Africa", -21.950, 26.617, r"\bBosutswe\b"),
    ("Ingombe Ilede", "Zambia (Zambezi)", "Southern Africa", -16.183, 28.917, r"\bIngombe Ilede\b"),
    ("Dithakong", "South Africa (Tswana)", "Southern Africa", -27.083, 23.917, r"\b(?:Dithakong|Lattakoo|Litaku)\b"),
    ("Kaditshwene", "South Africa (Tswana)", "Southern Africa", -25.350, 26.150, r"\b(?:Kaditshwene|Kurreechane)\b"),
    ("Molokwane", "South Africa (Tswana)", "Southern Africa", -25.633, 27.167, r"\bMolokwane\b"),
    ("Cape Town", "South Africa (Cape)", "Southern Africa", -33.925, 18.424, r"\b(?:Cape Town|Kaapstad)\b"),
    ("Stellenbosch", "South Africa (Cape)", "Southern Africa", -33.932, 18.860, r"\bStellenbosch\b"),
    ("Bulawayo", "Zimbabwe (Ndebele)", "Southern Africa", -20.150, 28.583, r"\bBulawayo\b"),
    ("Mankhamba", "Malawi (Maravi)", "Southern Africa", -14.233, 34.483, r"\bMankhamba\b"),

    # --- MADAGASCAR & ISLANDS ---
    ("Antananarivo", "Madagascar (Merina)", "Madagascar/Islands", -18.879, 47.508, r"\b(?:Antananarivo|Tananarive|Tananarivo)\b"),
    ("Mahilaka", "Madagascar (NW Coast)", "Madagascar/Islands", -13.917, 48.350, r"\bMahilaka\b"),
    ("Vohemar", "Madagascar (NE Coast)", "Madagascar/Islands", -13.359, 50.004, r"\b(?:Vohemar|Iharana)\b"),
    ("Toamasina", "Madagascar", "Madagascar/Islands", -18.149, 49.402, r"\b(?:Toamasina|Tamatave)\b"),
    ("Mahajanga", "Madagascar", "Madagascar/Islands", -15.717, 46.317, r"\b(?:Mahajanga|Majunga|Mazalagem)\b"),
    ("Fort Dauphin", "Madagascar", "Madagascar/Islands", -25.032, 46.983, r"\b(?:Fort[- ]?Dauphin|T[oô]lagnaro)\b"),
    ("Ambohimanga", "Madagascar (Merina)", "Madagascar/Islands", -18.759, 47.563, r"\bAmbohimanga\b"),
    ("Fianarantsoa", "Madagascar", "Madagascar/Islands", -21.453, 47.086, r"\bFianarantsoa\b"),
    ("Domoni", "Comoros (Anjouan)", "Madagascar/Islands", -12.257, 44.532, r"\bDomoni\b"),
    ("Moroni", "Comoros (Ngazidja)", "Madagascar/Islands", -11.702, 43.255, r"\bMoroni\b"),
]

COMPILED_SETTLEMENTS = [
    (name, country, region, lat, lon, re.compile(pat, re.IGNORECASE))
    for name, country, region, lat, lon, pat in SETTLEMENTS
]

BANNED_RE = re.compile(
    r"\b(?:Chandler|Modelski|Populstat|McEvedy|Klein\s+Goldewijk|HYDE\s*3|Bairoch|Lahmeyer|Tertius\s+Chandler)\b",
    re.IGNORECASE,
)

NUM_TOK = r"(?:\d{1,3}(?:[, ]\d{3})+|\d{1,6})"

POP_RANGE_RE = re.compile(
    rf"(?:between\s+|from\s+)?({NUM_TOK})\s*(?:-|–|—|to|and)\s*({NUM_TOK})\s*"
    r"(?:permanent\s+|total\s+|urban\s+)?"
    r"(inhabitants?|people|persons|residents?|souls|citizens|pop\.?|population|habitants?|âmes)\b",
    re.IGNORECASE,
)
POP_SINGLE_RE = re.compile(
    r"(?:population\s+(?:of\s+|at\s+|estimated\s+at\s+|reached\s+|was\s+|about\s+|around\s+|some\s+|nearly\s+|over\s+|roughly\s+|ca\.?\s+|c\.?\s+|between\s+)?|"
    r"populated\s+by\s+(?:about\s+|some\s+|over\s+)?|"
    r"inhabited\s+by\s+(?:about\s+|some\s+|over\s+)?|"
    r"estimated\s+at\s+(?:about\s+|between\s+)?)"
    rf"({NUM_TOK})(?:\s*(?:-|–|—|to|and)\s*({NUM_TOK}))?",
    re.IGNORECASE,
)
POP_FOLLOW_RE = re.compile(
    rf"\b({NUM_TOK})\s+"
    r"(?:permanent\s+|total\s+|adult\s+|urban\s+)?"
    r"(inhabitants?|people|persons|residents?|souls|citizens|habitants?|âmes)\b",
    re.IGNORECASE,
)

WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
    "eighteen": 18, "twenty": 20, "twenty-five": 25, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "one hundred": 100, "a hundred": 100, "hundred": 100, "two hundred": 200,
    "three hundred": 300,
}
WN_PAT = "|".join(sorted(WORD_NUMS.keys(), key=len, reverse=True))
POP_WORDS_RANGE_RE = re.compile(
    rf"\b({WN_PAT})\s*(?:to|-|–|and)\s*({WN_PAT})\s+thousand\s+"
    r"(inhabitants?|people|persons|residents?|souls|houses?|huts?|compounds?)\b",
    re.IGNORECASE,
)
POP_WORDS_RE = re.compile(
    rf"\b({WN_PAT})\s+thousand\s+"
    r"(inhabitants?|people|persons|residents?|souls|houses?|huts?|compounds?)\b",
    re.IGNORECASE,
)
# Handles English thousands commas `5,252.5 ha` and simple decimals `33.5 ha` cleanly!
AREA_HA_RE = re.compile(
    r"\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:-|–|—|to)?\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)?\s*"
    r"(hectares?|ha\.?|km2|km²|sq\.?\s*km|square\s+kilomet(?:er|re)s?|sq\.?\s*miles?|square\s+miles?|acres?)\b",
    re.IGNORECASE,
)
HOUSES_RE = re.compile(
    rf"\b({NUM_TOK})\s*(?:-|–|—|to)?\s*({NUM_TOK})?\s*"
    r"(?:stone\s+|mud\s+|thatched\s+|daga\s+|occupied\s+)?"
    r"(houses?|huts?|compounds?|households?|hearths?|dwellings?|maisons?|cases?|feux)\b",
    re.IGNORECASE,
)

# Precision-hardened year regex: NEVER matches `:633`, `1,870`, `71,856`, or `714 sq km`!
YEAR_RE = re.compile(
    r"(?<![0-9,:.-])\b(?:(?:AD|CE|c\.|ca\.|in|by|around|circa|from|until|to)\s*)?((?:1[0-9]|20)\d{2})\b(?![0-9,])"
    r"|\b(?:AD|CE|c\.|ca\.|circa)\s*([5-9]\d{2})\b(?![0-9,])"
    r"|\b(\d{1,2})(?:st|nd|rd|th)[- ]century\b"
    r"|\b(tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth)[- ]century\b",
    re.IGNORECASE,
)

CENTURY_MAP = {
    "tenth": 950, "eleventh": 1050, "twelfth": 1150, "thirteenth": 1250,
    "fourteenth": 1350, "fifteenth": 1450, "sixteenth": 1550,
    "seventeenth": 1650, "eighteenth": 1750, "nineteenth": 1850,
    "twentieth": 1950,
}

NON_AFRICAN_SKIP = [
    "Song China", "Brabant", "Early Modern Germany", "Early Modern Europe",
    "Medieval Europe", "London Steelyards", "Great Dying in the Americas",
    "Industrial Revolution", "Barima and Cuyuni", "Madeira and Porto Santo",
    "Africans on American Culture", "World History of Tax Rebellions",
]

NOISE_SENT_RE = re.compile(
    r"\b(?:Hong Kong|New York City|List of (?:Figures|Maps|Illustrations|Tables)|Table of Contents|"
    r"coastal zone from|survey of an area of|survey area of|per square kilometre|per sq\.? km|per km2)\b",
    re.IGNORECASE,
)

PRONOUN_CARRY_RE = re.compile(
    r"^\s*(?:It|Its|The\s+(?:city|town|site|capital|settlement|enclosure|tell|mound)|This\s+(?:city|town|site|capital|settlement)|There\s+were|By\s+\d{4},?\s+it)\b",
    re.IGNORECASE,
)


def parse_int(s):
    if not s:
        return None
    try:
        return int(s.replace(",", "").replace(" ", ""))
    except ValueError:
        return None


def normalize_range(v1, v2):
    if v1 is None:
        return None, None
    if v2 is None:
        return v1, None
    if v1 < 1000 and v2 >= 1000 and v1 * 1000 <= v2:
        v1 = v1 * 1000
    if v2 >= v1:
        return v1, v2
    return v1, None


def to_hectares(val_str, unit):
    try:
        # Remove thousands commas ONLY (e.g. `5,252.5` -> `5252.5`)
        cleaned = val_str.replace(",", "")
        v = float(cleaned)
    except ValueError:
        return None
    u = unit.lower().strip(".")
    if u in ("ha", "hectare", "hectares"):
        return round(v, 2)
    if "km" in u:
        return round(v * 100.0, 2)
    if "mile" in u:
        return round(v * 258.999, 2)
    if "acre" in u:
        return round(v * 0.4047, 2)
    return None


def extract_year(text):
    years = []
    for m in YEAR_RE.finditer(text):
        if m.group(1):
            y = int(m.group(1))
            if 1000 <= y <= 2020:
                # Avoid picking up modern publication citations like `(Author 1993)` or `(1987)`
                start = m.start(1)
                before = text[max(0, start - 25):start]
                after = text[m.end(1):m.end(1) + 6]
                if re.search(r"\([A-Z][a-z]+\s+$", before) or re.match(r"^\s*[:)]", after) and y >= 1955:
                    continue
                years.append(y)
        elif m.group(2):
            y = int(m.group(2))
            if 500 <= y <= 999:
                years.append(y)
        elif m.group(3):
            c = int(m.group(3))
            if 6 <= c <= 20:
                years.append((c - 1) * 100 + 50)
        elif m.group(4):
            y = CENTURY_MAP.get(m.group(4).lower())
            if y:
                years.append(y)
    if not years:
        return None, None
    hist = [y for y in years if y <= 1960]
    chosen = hist if hist else years
    if len(chosen) >= 2:
        lo, hi = min(chosen), max(chosen)
        return lo, (hi if 0 < hi - lo <= 500 else None)
    return chosen[0], None


def classify_evidence_type(snippet, rel_path, has_area, has_houses, has_pop):
    low = snippet.lower()
    rp = rel_path.lower()
    if has_area and not has_pop:
        return "archaeological_area"
    if has_houses and not has_pop:
        return "house_or_compound_count"
    if any(k in low for k in ["excavat", "archaeolog", "mound", "radiocarbon", "survey", "sherd", "tell", "ruin", "wall", "hectare"]):
        return "archaeological_estimate" if has_pop else "archaeological_area"
    if "13. primary sources" in rp or any(k in low for k in ["barth", "clapperton", "caillié", "caillie", "mungo park", "barbot", "dapper", "bowdich", "dupuis", "lander", "burton", "speke", "grant", "livingstone", "binger", "mage", "adanson", "moore", "rançon", "rancon", "pacheco", "pereira", "barbosa", "al-bakri", "ibn battuta", "leo africanus", "al-idrisi", "al-umari", "vasco da gama", "pigafetta", "cavazzi"]):
        if any(k in low for k in ["al-bakri", "ibn battuta", "al-idrisi", "al-umari", "al-sadi", "tarikh", "leo africanus"]):
            return "arabic_chronicle"
        return "traveller_eyewitness"
    if any(k in low for k in ["census", "tax roll", "colonial", "commissioner", "district officer", "enumeration", "poll tax", "recensement"]):
        return "colonial_census_or_report"
    if any(k in low for k in ["portuguese", "dutch", "monumenta", "missionar", "capuchin", "jesuit", "archive", "east india", "royal african"]):
        return "portuguese_or_european_record"
    return "historical_synthesis"


def split_sentences(text):
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'(])", text)


def extract_from_text_block(text, rel_path, page_label, page_has_banned):
    observations = []
    if not text or len(text) < 20:
        return observations
    # Reject Table of Contents / List of Figures pages
    if re.search(r"\b(?:List of (?:Illustrations|Figures|Maps|Tables)|Contents|Index)\b", text[:220], re.IGNORECASE):
        if len(re.findall(r"\b\d{1,3}\s*$", text, re.MULTILINE)) >= 8:
            return observations

    if not re.search(
        r"\b(?:inhabitants?|population|people|residents?|souls|habitants?|âmes|hectares?|ha\b|km2|km²|sq\.?\s*km|square\s+kilomet|square\s+mile|houses?|huts?|compounds?|households?|hearths?|maisons?|cases?|feux|thousand)\b",
        text,
        re.IGNORECASE,
    ):
        return observations

    sents = split_sentences(text)
    last_single_settlement = None

    for idx, sent in enumerate(sents):
        if len(sent) < 16 or len(sent) > 1300:
            last_single_settlement = None
            continue
        if NOISE_SENT_RE.search(sent):
            continue

        matched_settlements = []
        for name, country, region, lat, lon, cre in COMPILED_SETTLEMENTS:
            m = cre.search(sent)
            if m:
                matched_settlements.append((m.start(), name, country, region, lat, lon))

        carried = False
        if not matched_settlements and last_single_settlement and PRONOUN_CARRY_RE.search(sent):
            matched_settlements = [(0,) + last_single_settlement]
            carried = True

        if len(matched_settlements) == 1 and not carried:
            last_single_settlement = matched_settlements[0][1:]
        elif not matched_settlements:
            last_single_settlement = None
            continue
        else:
            last_single_settlement = matched_settlements[-1][1:]

        pop_val = None
        pop_range = None
        walled_ha = None
        houses_cnt = None
        q_pos = 0

        # 1. Word range ("fifteen to twenty thousand inhabitants")
        m_pwr = POP_WORDS_RANGE_RE.search(sent)
        if m_pwr:
            w1 = WORD_NUMS.get(m_pwr.group(1).lower(), 0) * 1000
            w2 = WORD_NUMS.get(m_pwr.group(2).lower(), 0) * 1000
            unit = m_pwr.group(3).lower()
            if w1 >= 1000 and w2 >= w1:
                if any(k in unit for k in ("house", "hut", "compound")):
                    houses_cnt = (w1 + w2) // 2
                else:
                    pop_range = [w1, w2]
                    pop_val = (w1 + w2) // 2
                q_pos = m_pwr.start()

        # 2. Numeric population range
        if pop_val is None:
            m_pr = POP_RANGE_RE.search(sent)
            if m_pr:
                v1, v2 = normalize_range(parse_int(m_pr.group(1)), parse_int(m_pr.group(2)))
                if v1 and v2 and 50 <= v1 <= 1500000 and 50 <= v2 <= 1500000:
                    if not (1400 <= v1 <= 2025 and 1400 <= v2 <= 2025 and v2 - v1 <= 150 and "people" in m_pr.group(3).lower()):
                        pop_range = [v1, v2]
                        pop_val = (v1 + v2) // 2
                        q_pos = m_pr.start()

        # 3. Population keyword + numeric
        if pop_val is None:
            m_ps = POP_SINGLE_RE.search(sent)
            if m_ps:
                v1, v2 = normalize_range(parse_int(m_ps.group(1)), parse_int(m_ps.group(2)))
                if v1 and 50 <= v1 <= 1500000:
                    if not (1400 <= v1 <= 2025 and v2 is None and re.search(rf"\b{v1}\b\s*(?:was|is|were|to|and\s+1[5-9]|CE|AD|s\b)", sent)):
                        if v2 and v2 <= 1500000:
                            pop_range = [v1, v2]
                            pop_val = (v1 + v2) // 2
                        else:
                            pop_val = v1
                        q_pos = m_ps.start()

        # 4. "<N> inhabitants/souls/residents"
        if pop_val is None:
            m_pf = POP_FOLLOW_RE.search(sent)
            if m_pf:
                v1 = parse_int(m_pf.group(1))
                if v1 and 50 <= v1 <= 1500000:
                    if not (1500 <= v1 <= 2025 and m_pf.group(2).lower() in ("people", "persons")):
                        pop_val = v1
                        q_pos = m_pf.start()

        # 5. Single word numbers ("two hundred thousand inhabitants", "twenty thousand people")
        if pop_val is None or houses_cnt is None:
            m_pw = POP_WORDS_RE.search(sent)
            if m_pw:
                wval = WORD_NUMS.get(m_pw.group(1).lower(), 0) * 1000
                unit = m_pw.group(2).lower()
                if wval >= 1000:
                    if any(k in unit for k in ("house", "hut", "compound")):
                        if houses_cnt is None:
                            houses_cnt = wval
                            q_pos = m_pw.start()
                    else:
                        if pop_val is None:
                            pop_val = wval
                            q_pos = m_pw.start()

        # 6. Area in hectares / km2 / sq miles (urban site bounds: 0.5 ha to 20,000 ha)
        m_ar = AREA_HA_RE.search(sent)
        if m_ar:
            if re.search(r"\b(?:site|city|town|wall|enclos|tell|mound|settlement|urban|capital|occupi|area|cover|span|extend|perimeter|moat|earthwork|ruin|core|palace|fortif|hectare)\b", sent, re.IGNORECASE):
                ha1 = to_hectares(m_ar.group(1), m_ar.group(3))
                if ha1 and 0.5 <= ha1 <= 20000:
                    walled_ha = ha1
                    if pop_val is None:
                        q_pos = m_ar.start()

        # 7. Houses / huts / compounds / hearths
        if houses_cnt is None:
            m_ho = HOUSES_RE.search(sent)
            if m_ho:
                h1, _ = normalize_range(parse_int(m_ho.group(1)), parse_int(m_ho.group(2)))
                if h1 and 15 <= h1 <= 250000:
                    if not (1700 <= h1 <= 2025 and re.search(rf"(?:in|by|around|since|from)\s+{h1}\b", sent, re.IGNORECASE)):
                        houses_cnt = h1
                        if pop_val is None and walled_ha is None:
                            q_pos = m_ho.start()

        if pop_val is None and walled_ha is None and houses_cnt is None:
            continue

        matched_settlements.sort(key=lambda z: abs(z[0] - q_pos))
        _, s_name, s_country, s_region, s_lat, s_lon = matched_settlements[0]

        if re.search(r"\bpp?\.\s*\d+\s*[-–]\s*\d+|\bISBN\b|\bVol\.\s*\d+|\bPress,\s*19\d\d|\bUniversity\s+Press", sent):
            if pop_val is None and walled_ha is None:
                continue

        ctx = (sents[idx - 1] + " " + sent) if (carried and idx > 0) else sent
        if idx + 1 < len(sents) and len(ctx) < 350:
            ctx_yr = ctx + " " + sents[idx + 1]
        else:
            ctx_yr = ctx

        yr, yr_end = extract_year(ctx_yr)
        if yr and yr >= 1970 and (yr_end is None or yr_end >= 1970):
            if not re.search(r"\b(?:archaeolog|excavat|mound|hectare|precolonial|pre-colonial|1[0-8]\d\d|19[0-5]\d|century)\b", ctx_yr, re.IGNORECASE):
                continue

        cites_banned = bool(BANNED_RE.search(ctx_yr)) or (
            page_has_banned and bool(re.search(r"\b(?:estimate|table|rank|largest|1500|1600|1700|1800|20,000|cities)\b", ctx, re.IGNORECASE))
        )

        ev_type = classify_evidence_type(
            ctx, rel_path, walled_ha is not None, houses_cnt is not None, pop_val is not None
        )

        observations.append({
            "settlement_name": s_name,
            "country_or_region": s_country,
            "nicethi_region": s_region,
            "lat": s_lat,
            "lon": s_lon,
            "year": yr,
            "year_end": yr_end,
            "population": pop_val,
            "population_range": pop_range,
            "walled_area_ha": walled_ha,
            "houses_or_compounds": houses_cnt,
            "evidence_type": ev_type,
            "source_file": rel_path,
            "page_or_image": page_label,
            "citation_short": Path(rel_path).stem[:95],
            "snippet": ctx[:460],
            "cites_banned_compendium": cites_banned,
        })

    return observations


def process_one_pdf(entry):
    rel_path = entry["rel_path"]
    top_folder = entry["top_folder"]
    pdf_path = ARCHIVE_ROOT / rel_path
    if not pdf_path.exists():
        return (rel_path, top_folder, 0, [], "missing")
    try:
        doc = pymupdf.open(pdf_path)
        n_pages = len(doc)
        obs_list = []
        for pno in range(n_pages):
            txt = doc[pno].get_text("text") or ""
            if len(txt) < 30:
                continue
            page_banned = bool(BANNED_RE.search(txt))
            obs = extract_from_text_block(txt, rel_path, f"p. {pno + 1}", page_banned)
            if obs:
                obs_list.extend(obs)
        doc.close()
        return (rel_path, top_folder, n_pages, obs_list, None)
    except Exception as e:
        return (rel_path, top_folder, 0, [], str(e)[:120])


def select_target_pdfs(index_data):
    seen_sha = set()
    seen_stem = set()
    unique_pdfs = []
    # Prefer canonical folders first when deduplicating identical filename stems
    folder_order = {
        "6. Cities": 1, "9. Population": 2, "3. East Africa": 3,
        "4. Central and Southern Africa": 4, "13. Primary Sources": 5,
        "1. West Africa": 6, "5. General History": 7, "10. Governance": 8,
        "11. Maritime": 9, "2. North Africa": 10,
    }
    all_pdf_entries = [x for x in index_data.get("files", []) if x.get("file_kind") == "pdf"]
    all_pdf_entries.sort(key=lambda z: (folder_order.get(z["top_folder"], 99), -z.get("pop_urban_score", 0)))

    for x in all_pdf_entries:
        sha = x.get("sha256", x["rel_path"])
        stem_norm = re.sub(r"[^a-z0-9]+", "", Path(x["rel_path"]).stem.lower())
        if sha in seen_sha or stem_norm in seen_stem:
            continue
        rp = x["rel_path"]
        if any(sk.lower() in rp.lower() for sk in NON_AFRICAN_SKIP):
            continue
        seen_sha.add(sha)
        seen_stem.add(stem_norm)
        unique_pdfs.append(x)

    selected = {}

    def add_pdf(entry, priority):
        rp = entry["rel_path"]
        if rp not in selected or priority < selected[rp][0]:
            selected[rp] = (priority, entry)

    for x in unique_pdfs:
        if x["top_folder"] in ("6. Cities", "9. Population", "3. East Africa", "4. Central and Southern Africa"):
            add_pdf(x, 1)

    for x in unique_pdfs:
        if x["top_folder"] == "13. Primary Sources":
            low = x["rel_path"].lower()
            if "photograph" in low or "postcards" in low or "alt.pdf" in low:
                continue
            add_pdf(x, 2)

    wa_by_sub = defaultdict(list)
    for x in unique_pdfs:
        if x["top_folder"] == "1. West Africa":
            parts = x["rel_path"].split("/")
            sub = parts[1] if len(parts) > 1 else "root"
            wa_by_sub[sub].append(x)

    for sub, items in wa_by_sub.items():
        items.sort(key=lambda z: z.get("pop_urban_score", 0), reverse=True)
        for x in items[:10]:
            if x.get("pop_urban_score", 0) >= 40:
                add_pdf(x, 3)

    all_wa = [x for x in unique_pdfs if x["top_folder"] == "1. West Africa"]
    all_wa.sort(key=lambda z: z.get("pop_urban_score", 0), reverse=True)
    for x in all_wa[:85]:
        add_pdf(x, 3)

    tier4_keywords = [
        "african civilizations", "african kingdoms", "history of west africa",
        "empires of medieval west africa", "golden rhinoceros",
        "cambridge history of africa volume 3", "cambridge history of africa volume 4",
        "cambridge history of africa volume 5", "general history africa 4",
        "general history africa 5", "general history africa 6",
        "portuguese fortresses in east africa", "warfare in the sokoto",
        "sijilmassa", "elmina", "ughoton", "great benin", "origin and organization",
    ]
    for x in unique_pdfs:
        if x["top_folder"] in ("5. General History", "10. Governance", "11. Maritime", "2. North Africa"):
            low = x["rel_path"].lower()
            if x.get("page_count", 0) <= 900 and (
                x.get("pop_urban_score", 0) >= 135
                or any(k in low for k in tier4_keywords)
            ):
                add_pdf(x, 4)

    ordered = sorted(selected.values(), key=lambda z: (z[0], -z[1].get("pop_urban_score", 0)))
    return [z[1] for z in ordered]


def parse_lovejoy_docx(docx_rel_path):
    docx_full = ARCHIVE_ROOT / docx_rel_path
    observations = []
    towns_table = []
    if not docx_full.exists():
        return observations, towns_table

    with zipfile.ZipFile(docx_full) as z:
        xml_data = z.read("word/document.xml")
    tree = ET.fromstring(xml_data)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    paras = []
    for p in tree.findall(".//w:p", ns):
        txt = "".join(t.text or "" for t in p.findall(".//w:t", ns)).strip()
        if txt:
            paras.append(txt)

    full_text = "\n".join(paras)
    doc_banned = bool(BANNED_RE.search(full_text))
    for i, para in enumerate(paras):
        observations.extend(extract_from_text_block(para, docx_rel_path, f"para {i + 1}", doc_banned))

    for tbl in tree.findall(".//w:tbl", ns):
        for r in tbl.findall(".//w:tr", ns):
            cells = ["".join(t.text or "" for t in c.findall(".//w:t", ns)).strip() for c in r.findall(".//w:tc", ns)]
            if any(cells):
                towns_table.append(cells)

    return observations, towns_table


def main():
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(INDEX_PATH, encoding="utf-8") as f:
        index_data = json.load(f)

    target_pdfs = select_target_pdfs(index_data)
    print(f"[INFO] Selected {len(target_pdfs)} unique deduplicated PDFs across all regions (4 workers).", flush=True)

    all_obs = []
    parsed_pdfs = []
    failed_pdfs = []

    done_cnt = 0
    with ProcessPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(process_one_pdf, entry) for entry in target_pdfs]
        for fut in as_completed(futs):
            rel_path, top_folder, n_pages, obs_list, err = fut.result()
            done_cnt += 1
            if err:
                failed_pdfs.append({"rel_path": rel_path, "error": err})
            else:
                all_obs.extend(obs_list)
                parsed_pdfs.append({
                    "rel_path": rel_path,
                    "top_folder": top_folder,
                    "page_count": n_pages,
                    "obs_count": len(obs_list),
                })
            if done_cnt % 40 == 0 or done_cnt == len(target_pdfs):
                elapsed = time.time() - t0
                print(
                    f"[PROGRESS] {done_cnt}/{len(target_pdfs)} PDFs mined ({elapsed:.1f}s) | "
                    f"obs={len(all_obs)} | unique_settlements={len(set(o['settlement_name'] for o in all_obs))}",
                    flush=True,
                )

    docx_rel = "1. West Africa/10. Gulf of Guinea/Gulf of Guinea Text/Lovejoy Mapping the Collapse of Oyo clean.docx"
    docx_obs, docx_table = parse_lovejoy_docx(docx_rel)
    all_obs.extend(docx_obs)
    print(f"[INFO] Lovejoy DOCX parsed: {len(docx_obs)} obs, {len(docx_table)} table rows.", flush=True)

    deduped = []
    seen_keys = set()
    for o in all_obs:
        key = (
            o["settlement_name"],
            o["citation_short"],
            o["year"],
            o["population"],
            o["walled_area_ha"],
            o["houses_or_compounds"],
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(o)

    region_counts = Counter(o["nicethi_region"] for o in deduped)
    unique_by_region = defaultdict(set)
    for o in deduped:
        unique_by_region[o["nicethi_region"]].add(o["settlement_name"])

    output = {
        "metadata": {
            "pdfs_targeted": len(target_pdfs),
            "pdfs_parsed": len(parsed_pdfs),
            "pdfs_failed": len(failed_pdfs),
            "docx_parsed": 1,
            "raw_observations_total": len(all_obs),
            "deduped_observations_total": len(deduped),
            "non_banned_observations": sum(1 for o in deduped if not o["cites_banned_compendium"]),
            "banned_flagged_observations": sum(1 for o in deduped if o["cites_banned_compendium"]),
            "unique_settlements_total": len(set(o["settlement_name"] for o in deduped)),
            "observations_by_region": dict(region_counts),
            "unique_settlements_by_region": {k: len(v) for k, v in unique_by_region.items()},
            "elapsed_seconds": round(time.time() - t0, 2),
        },
        "parsed_pdfs_summary": sorted([p for p in parsed_pdfs if p["obs_count"] > 0], key=lambda z: -z["obs_count"]),
        "docx_lovejoy_oyo_table": docx_table,
        "settlement_observations": deduped,
    }

    with open(RAW_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[DONE] Wrote {RAW_OUT_PATH}")
    print(json.dumps(output["metadata"], indent=2))


if __name__ == "__main__":
    main()
