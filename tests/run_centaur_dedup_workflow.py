"""
CENTAUR-II Duplicate Name Remediation Workflow (`run_workflow`).

Runs batched Gemini 3.8 Flash (`model="flash"`) agents over cluster-coherent duplicate
batches (`tests/toponymy_batches/centaur_dedup/batch_*.json`), enforcing ZERO cross-location
duplicate names, banning generic ethnonym/continental-river repetition, and prioritizing
accurate historically attested Indigenous village/landmark names (or clean unique site names
where no Indigenous name is attested for a prehistoric excavation).
"""

import json
import math
import os
import re
import unicodedata
from collections import defaultdict

SCHEMA = {
    "type": "object",
    "properties": {
        "settlements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "naming_tier": {
                        "type": "string",
                        "enum": [
                            "attested_indigenous_village",
                            "attested_indigenous_local_landmark",
                            "clean_distinctive_archaeological_site",
                            "historical_settler_name",
                        ],
                    },
                    "historical_names": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string"},
                                "name": {"type": "string"},
                            },
                            "required": ["date", "name"],
                        },
                    },
                    "other_names": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["key", "naming_tier", "historical_names"],
            },
        }
    },
    "required": ["settlements"],
}

DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")
FOREIGN_RE = re.compile(
    r"[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]"
)


def strip_paren(s):
    return re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", str(s or "")).strip()


def norm_phonetic(s):
    s = strip_paren(s).lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    for a, b in [
        ("ł", "l"), ("ɬ", "l"), ("đ", "d"), ("ø", "o"), ("ŋ", "n"),
        ("ʔ", ""), ("ʷ", "w"), ("š", "s"), ("č", "c"), ("ž", "z"),
        ("ȟ", "h"), ("ǧ", "g"), ("ʼ", ""), ("ʻ", ""),
        ("sh", "s"), ("ch", "c"), ("zh", "z"), ("kh", "k"), ("th", "t"), ("gh", "g"),
    ]:
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "", s)
    s = re.sub(r"(.)\1+", r"\1", s)
    return s


def haversine_km(lat1, lon1, lat2, lon2):
    rad = math.pi / 180.0
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def find_internal_dups(orig_by_key, resolved_list):
    by_phon = defaultdict(list)
    for rec in resolved_list:
        k = rec.get("key")
        hn = rec.get("historical_names") or []
        if not k or not hn or k not in orig_by_key:
            continue
        hn_s = sorted(hn, key=lambda x: [int(p) for p in str(x["date"]).split(".")])
        fn = strip_paren(hn_s[0]["name"])
        by_phon[norm_phonetic(fn)].append((k, fn, orig_by_key[k]))
    bad = []
    for ph, lst in by_phon.items():
        if len(lst) < 2:
            continue
        # Check if ALL pairs are <= 15 km and non-overlapping
        if len(lst) == 2:
            o1, o2 = lst[0][2], lst[1][2]
            d = haversine_km(o1["coords_lat_lng"][0], o1["coords_lat_lng"][1], o2["coords_lat_lng"][0], o2["coords_lat_lng"][1])
            ov = min(o1["max_year"], o2["max_year"]) - max(o1["min_year"], o2["min_year"])
            if d <= 15.0 and ov <= 10:
                continue
        bad.append((ph, [(x[0], x[1]) for x in lst]))
    return bad


def build_prompt(batch_idx, raw, extra_warning=""):
    items = raw.get("settlements", [])
    forbidden = raw.get("forbidden_already_used_in_region", [])
    clusters = raw.get("clusters", [])
    return f"""CENTAUR-II Duplicate Toponymy Remediation — Batch {batch_idx} ({len(items)} settlements; flagged duplicate clusters: {clusters})

PROBLEM TO FIX:
Earlier automated encoding stamped the SAME generic tribal ethnonym (e.g. `Sahnish` on 22 South Dakota sites, `Kitikiti'sh` on 53 Plains sites, `Bidanku` on 22 New Mexico sites, `Chíhéne` on 21 sites, `Wendat` on 17 Ontario sites, `Chikasha` on 29 sites) or the SAME major river/city name (`Mníšoše` on 11 Missouri River sites, `Ogha Po'oge` on 7 New Mexico sites, `Cuk Ṣon` on 8 Arizona sites) onto MULTIPLE DISTINCT SETTLEMENTS in different places!

YOUR MISSION:
Recode these {len(items)} settlements so that **EVERY distinct settlement (> 15 km apart or overlapping in time) has an ACCURATE, HISTORICALLY GROUNDED, AND GLOBALLY UNIQUE name** during its active period!

EXECUTION RULES:
- Do NOT call `run_command`, `read_file`, `write_file`, `search_marketplace`, or inspect local files. All data is below.
- Call `finish` in ONE turn returning ALL {len(items)} settlements with exact 1-to-1 `key` matches.
{extra_warning}
STRICT UNIQUENESS & ACCURACY LAWS:
1. **ZERO DUPLICATES**: No two settlements in this batch (> 15 km apart or overlapping in time) may share the same `historical_names[0].name` — NOT EVEN with different diacritics, apostrophes, or spelling variants (e.g. `Sahnish` and `Sáhniš` count as DUPLICATES; `Kitikiti'sh` and `Kitikitiʼsh` count as DUPLICATES; `Chikasha` and `Chikashsha` count as DUPLICATES!).
2. **NO COLLISIONS WITH REGIONAL BLOCKLIST**: Do NOT reuse any name in `forbidden_already_used_in_region` below!
3. **AT MOST ONE SETTLEMENT KEEPS THE FLAGGED NAME**:
   - If the flagged name genuinely belongs to ONE specific historic settlement/capital in this batch (e.g. `Ogha Po'oge` -> Santa Fe ONLY; `Cuk Ṣon` -> Tucson ONLY; `Tótaʼ` -> Farmington ONLY; `Quivira` -> Tobias/Etzanoa ONLY; `Opaskwayak` -> The Pas ONLY; `Kadohadacho` -> the Red River Bend Kadohadacho village ONLY), ONLY THAT ONE settlement may keep it.
   - If the flagged name is a bare continental river (`Mníšoše`, `Māta`) or generic nation ethnonym (`Sahnish`, `Kitikiti'sh`, `Wendat`, `Beothuk`, `Hisatsinom`, `Newe`) that was NOT the specific name of a single town, recode ALL of them to specific, accurate names!
4. **3-TIER SCHOLARLY ACCURACY HIERARCHY (NEVER INVENT FAKE INDIGENOUS WORDS!)**:
   - **Tier 1 (`attested_indigenous_village`)**: Assign the **specific, historically documented Indigenous village, pueblo, town, or band settlement name** genuinely associated with that exact site/locality in ethnohistory (e.g. documented Arikara villages `Hukawírat`, `Awáhu`, `Hokat`, `Ščiríhkux`, `Tukátakux`, `Tukstánu`, `Nakanústš`, `Nisapst`, `Nakáru`, `Sčiríhta`, `Tuhčiríhku`, `Štáwah`, `Páhat`; Mandan `Mitutanka`, `Nuptadi`, `Ruptare`, `Nuitadi`, `Is'topa`; Wendat `Ossossané`, `Cahiagué`, `Teanaostaiaé`, `Contarea`, `Scanonaenrat`, `Toanché`, `Ihonatiria`, `Carhagouha`, `Taenhatentaron`, `Angoutenc`, `Ouenrio`; Caddo `Hainai`, `Nabedache`, `Nacogdoche`, `Nasoni`, `Nadaco`, `Neches`, `Nacanish`, `Eyeish`, `Yatasi`, `Adai`, `Nanatsoho`, `Cahinnio`; Wichita `Etzanoa`, `Wíiko`, `Tawáakoni`, `Kítsaish`, `Iskáni`, `Haxa`, `Tabas`, `Tareque`; Pueblo sites `Kuaua`, `Puaray`, `Paako`, `Tunque`, `Pindi`, `Puye`, `Tsankawi`, `Tyuonyi`, `Sapawe`, `Poshuouinge`, `Kwastiyukwa`, `Giusewa`, `Unshagi`, `Awat'ovi`, `Homol'ovi`, `Kawaika'a`, `Chakpahu`, `Kintiel`, `Va'aki`, `Ska'kaik`, `Sivan Vah'ki`, etc.).
   - **Tier 2 (`attested_indigenous_local_landmark`)**: If no specific village name is recorded, assign the **historically attested Indigenous name of the exact local tributary creek, spring, hill, mesa, canyon, pass, or island** at `[lat, lng]` (used on AT MOST ONE settlement!).
   - **Tier 3 (`clean_distinctive_archaeological_site`)**: For ancient Paleoindian/Archaic sites (`< 0 CE`, e.g. `Jones-Miller` `-8200..-7800`) OR unrecorded archaeological excavations where NO specific attested Indigenous village or local landmark name genuinely exists in ethnohistory after Tier 1 & Tier 2 are honestly exhausted, **DO NOT fabricate fake Indigenous words and DO NOT repeat a generic tribal/river name!** Use the **clean, concise, distinctive archaeological site name** (stripping verbose suffixes like `Earthlodge Village`, `Pithouse Village`, `Site`, `Complex`, `Town`, `Settlement`, `Village` — e.g. `Jones-Miller`, `Nordvold`, `Demery`, `Shermer`, `Havens`, `Sommers`, `Ketchen`, `Durkin`, `Swanson`, `Arp`, `McClure`, `Heath`, `Sully`, `La Roche`, `Whistling Elk`, `Walth Bay`, `Stelzer`, `Uren`, `Damiani`).
   - **Tier 4 (`historical_settler_name`)**: If a settlement with `min_year >= 1800` was founded as a Euro-American settler town rather than an Indigenous settlement (e.g. `Buhl-Idaho`, `Allen-Nebraska`), use its accurate historical founding name.
5. **DATES & MODERN TRANSITIONS**:
   - All dates MUST match `^-?\\d+\\.\\d+\\.\\d+$`. First entry year MUST be `<= min_year`.
   - For extant modern cities (`max_year >= 1950`), preserve accurate colonial/modern transitions ending at the modern canonical `shard_name` (or official post-1950 Indigenous restoration).
   - NO parentheticals `(...)`, NO `[...]`, NO `?`, NO `\ufffd`, NO backticks `` ` ``, NO Cyrillic/CJK/Arabic/Indic characters.

Forbidden names already used elsewhere in these states/provinces (DO NOT REUSE):
{json.dumps(forbidden, ensure_ascii=False)}

Input colliding settlements ({len(items)} items):
{json.dumps(items, ensure_ascii=False)}
"""


async def process_batch(batch_path):
    raw = json.load(open(batch_path, "r", encoding="utf-8"))
    items = raw.get("settlements", [])
    batch_idx = int(raw.get("batch_index", 1))
    if not items:
        return {"batch_path": batch_path, "count": 0, "expected": 0, "skipped": True}

    out_dir = os.path.dirname(batch_path)
    out_path = os.path.join(out_dir, f"resolved_batch_{batch_idx:04d}.json")

    if os.path.exists(out_path):
        try:
            ex = json.load(open(out_path, "r", encoding="utf-8"))
            if len(ex.get("settlements", [])) == len(items):
                return {"batch_path": out_path, "count": len(items), "expected": len(items), "skipped": True}
        except Exception:
            pass

    orig_by_key = {str(it["key"]): it for it in items}
    primary_model = args.get("model", "flash")
    fallback_model = args.get("fallback_model", "inherit")

    extra_warning = ""
    result = None
    for attempt in range(2):
        prompt_text = build_prompt(batch_idx, raw, extra_warning)
        try:
            result = await agent(
                prompt=prompt_text,
                schema=SCHEMA,
                role=f"CENTAUR Dedup Flash {batch_idx:03d} ({len(items)})" + (f" [retry {attempt}]" if attempt else ""),
                type_name="self",
                model=primary_model if attempt == 0 else fallback_model,
            )
        except Exception as err:
            log(f"[retry] Batch {batch_idx} attempt {attempt} error: {err}")
            if attempt == 0:
                continue
            return {"batch_path": batch_path, "count": 0, "expected": len(items), "error": str(err)}

        res_list = result.get("settlements") or []
        internal_dups = find_internal_dups(orig_by_key, res_list)
        if not internal_dups and len(res_list) >= len(items):
            break
        if attempt == 0:
            dup_desc = "; ".join(f"{ph}: {pairs}" for ph, pairs in internal_dups[:10])
            log(f"[dedup-retry] Batch {batch_idx} had {len(internal_dups)} internal dup(s) ({len(res_list)}/{len(items)}): {dup_desc[:200]}")
            extra_warning = (
                f"\nPREVIOUS ATTEMPT FAILED UNIQUENESS CHECK! You STILL produced duplicate names inside this batch: {dup_desc}. "
                f"Fix EVERY single collision so ALL {len(items)} settlements have strictly distinct names!\n"
            )

    by_key = {str(it.get("key")): it for it in (result.get("settlements") or []) if it.get("key")}
    merged_settlements = []
    missing_keys = []

    for orig in items:
        k = str(orig["key"])
        r = by_key.get(k)
        if not r:
            missing_keys.append(k)
            continue
        hclean = []
        for h in (r.get("historical_names") or []):
            if not isinstance(h, dict):
                continue
            hd = str(h.get("date") or "").strip()
            hn = strip_paren(h.get("name") or "")
            if (
                DATE_RE.match(hd)
                and hn
                and hn not in {"0", "Unknown", "Settlement"}
                and "?" not in hn
                and "\ufffd" not in hn
                and "`" not in hn
                and not FOREIGN_RE.search(hn)
            ):
                hclean.append({"date": hd, "name": hn})
        if not hclean:
            missing_keys.append(k)
            continue

        m = dict(orig)
        m["naming_tier"] = str(r.get("naming_tier") or "")
        m["historical_names"] = hclean
        m["other_names"] = [
            strip_paren(a)
            for a in (r.get("other_names") or [])
            if strip_paren(a) and not FOREIGN_RE.search(str(a))
        ]
        merged_settlements.append(m)

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "batch_index": batch_idx,
                "count": len(merged_settlements),
                "expected": len(items),
                "missing_keys": missing_keys,
                "settlements": merged_settlements,
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )

    return {"batch_path": out_path, "count": len(merged_settlements), "expected": len(items), "missing": len(missing_keys)}


phase("Discover CENTAUR dedup batches")
in_dir = os.path.abspath(args.get("in_dir") or os.path.join("tests", "toponymy_batches", "centaur_dedup"))
start_batch = int(args.get("start_batch", 1))
end_batch = int(args.get("end_batch", 999999))

batch_files = []
for f in sorted(os.listdir(in_dir)):
    m = re.match(r"^batch_(\d+)\.json$", f, re.IGNORECASE)
    if m:
        idx = int(m.group(1))
        if start_batch <= idx <= end_batch:
            batch_files.append(os.path.join(in_dir, f))

log(f"Selected {len(batch_files)} dedup batch(es) [{start_batch}..{end_batch}] in {in_dir}")

WAVE_SIZE = int(args.get("wave_size", 25))
all_results = []
for start in range(0, len(batch_files), WAVE_SIZE):
    wave_idx = (start // WAVE_SIZE) + 1
    wave_files = batch_files[start : start + WAVE_SIZE]
    phase(f"Dedup wave {wave_idx} ({len(wave_files)} batches)")
    wave_res = await parallel(wave_files, process_batch)
    all_results.extend(wave_res)
    done_cnt = sum(r.get("count", 0) for r in wave_res)
    exp_cnt = sum(r.get("expected", 0) for r in wave_res)
    err_cnt = sum(1 for r in wave_res if r.get("error"))
    log(f"Wave {wave_idx} complete: {done_cnt}/{exp_cnt} resolved (errors={err_cnt}).")

total_res = sum(r.get("count", 0) for r in all_results)
total_exp = sum(r.get("expected", 0) for r in all_results)
total_err = sum(1 for r in all_results if r.get("error"))
total_missing = sum(r.get("missing", 0) for r in all_results)
log(f"TOTAL DEDUP RESOLVED: {total_res}/{total_exp} (batch_errors={total_err}, missing_keys={total_missing})")
{"resolved": total_res, "expected": total_exp, "batch_errors": total_err, "missing_keys": total_missing}
