"""
Operation Viscount Pass-1 Historical Toponymy Swarm & Separate Read-Only Auditor (`run_workflow`).

Enforces strict resource & schema invariants:
1. PASS 1 ONLY: Operates exclusively on `pass1/batch_*.json` (settlements with peak pop > 10k or capitals).
   Residual settlements (<= 10k, non-capital) are handled deterministically by
   `resolve_residual_toponymy_whg_geohack.js` with ZERO LLM agents.
2. COMPACT SCHEMA: Consumes and emits minimal `{"coords": [lng, lat], "names": {"yyyy.m.d": "Name"}}`
   records (~80% fewer tokens than legacy verbose payloads).
3. HARD CONCURRENCY CAP (`n <= 24`): All worker and auditor `agent()` invocations share one global
   `asyncio.Semaphore(min(24, max_concurrency))`, guaranteeing <= 24 concurrent subagents at all times.
4. STRUCTURAL RULES FOR TOPONYMS:
   - De facto ruling/occupying authority's preferred name in contemporaneous English-language Latin script.
   - Period-accurate historical names rather than retrofitted modern names.
   - Capital cities (`"cap": true`) always carry the capital city's canonical contemporaneous name.
   - Simplify the entire existing history at each `[lng, lat]` coordinate without sub-district overrides.
"""

import asyncio
import datetime
import json
import os
import re

HARD_MAX_CONCURRENCY = 24
DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")
NON_LATIN_RE = re.compile(r"[\u0370-\u03FF\u0400-\u04FF\u0530-\u058F\u0590-\u05FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u10A0-\u10FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]")
ARTICLE_INVERT_RE = re.compile(r"^.+,\s*(?:Al|El|As|Ash|Ar|Az|Ad|An|At|Le|La|Les|L'|Los|Las|Il|Lo|De|Den|Het|Der|Die|Das|The)$", re.I)
INTRA_DISTRICT_RE = re.compile(r"(?:\b(?:arrondissement|borough|ward|stadtbezirk|bezirk|okrug|shiyakha|qism|kism|markaz|mahalle|alcaldia|delegacion|sub-?district)\b|^paris\s+\d{2}\b|\(mod_uk\)$|-(?:ku|gu|dong|quận)$)", re.I)
ENGLISH_EXONYM_OR_ASCII_RE = re.compile(r"^(?:Vienna|Munich|Muenchen|Munchen|Nuremberg|Cologne|Dusseldorf|Wurzburg|Luneburg|Lunen|Grunberg|Butow|Koslin|Prague|Warsaw|Cracow|Florence|Naples|Copenhagen|Gorzow Wielkopolski|Poznan|Wroclaw|Miedzyrzecz|Wrzesnia|Srem|Nowy Tomysl|Miedzychod|Ostrow Wielkopolski|Bytow|Zielona Gora)$", re.I)
GIS_ARCH_JUNK_RE = re.compile(r"(?:_wfl|_none|proyecto_|cmn_|SitioNN_Fase_|\b(?:petroglifos|petroglyph|parcela\s+[a-z0-9]|dhibi|rockshelter)\b|\\|\s\+\s|\b(?:a\.d\.|b\.Pr\.|i\.d\.OPf\.|v\.d\.|s\.r\.o\.|uniwersytet)\b|^(?:universitäts- und hansestadt|hansestadt|kreisfreie stadt|landeshauptstadt|bergstadt|stadt\s))", re.I)

WORKER_SCHEMA_ENTRIES = {
  "type": "object",
  "properties": {
    "cities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "coords": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 2,
            "maxItems": 2,
          },
          "names": {
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
        },
        "required": ["coords", "names"],
      },
    }
  },
  "required": ["cities"],
}

WORKER_SCHEMA_PAIRS = {
  "type": "object",
  "properties": {
    "cities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "coords": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 2,
            "maxItems": 2,
          },
          "names": {
            "type": "array",
            "items": {
              "type": "array",
              "items": {"type": "string"},
              "minItems": 2,
              "maxItems": 2,
            },
          },
        },
        "required": ["coords", "names"],
      },
    }
  },
  "required": ["cities"],
}

AUDITOR_SCHEMA = {
  "type": "object",
  "properties": {
    "approved": {"type": "boolean"},
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "coord_key": {"type": "string"},
          "rule": {"type": "string"},
          "detail": {"type": "string"},
          "fix": {"type": "string"},
        },
        "required": ["coord_key", "rule", "detail", "fix"],
      },
    },
  },
  "required": ["approved", "errors"],
}

STRUCTURAL_RULEBOOK = """STRUCTURAL HISTORICAL TOPONYMY RULES (PASS 1 — KNOWLEDGE BASE, ZERO TOLERANCE):
1. Occupying / De Facto Ruling Authority & Endonymic Latin-Script Diacritics Standard (`SC-01`, `SC-02`):
   - Always use the name preferred by the de facto ruling or occupying authority for that period, rendered in the Latin script with FULL native diacritics (NOT English exonyms or stripped ASCII!):
     - Germany/Austria/Switzerland: `Wien` (NOT `Vienna`), `München` (NOT `Munchen`/`Munich`), `Nürnberg` (NOT `Nuremberg`), `Köln` (NOT `Cologne`), `Düsseldorf`, `Würzburg`, `Lüneburg`, `Lünen`, `Zürich`.
     - Poland/Prussia/Partitions (`SC-01`): `Landsberg an der Warthe` -> `1945.5.8: Gorzów Wielkopolski` (NOT `Gorzow Wielkopolski`), `Rummelsburg` -> `1945.5.8: Miastko`, `Breslau` -> `1945.5.6: Wrocław`, `Posen` <-> `Poznań`, `Meseritz` -> `1945.1.1: Międzyrzecz`, `Schrimm` -> `1919.1.1: Śrem`, `Wreschen` -> `1919.1.1: Września`, `Grünberg` -> `1945.5.8: Zielona Góra`, `Köslin` -> `1945.5.8: Koszalin`, `Bütow` -> `1945.3.8: Bytów`, `Ostrowo` -> `1919.1.1: Ostrów Wielkopolski`, `Warszawa` (NOT `Warsaw`), `Kraków`.
     - Europe: `Praha` (NOT `Prague`), `Firenze` (NOT `Florence`), `Napoli` (NOT `Naples`), `København` (NOT `Copenhagen`), `Genève`, `Orléans`, `Nîmes`.
     - Global transfers: `Keijo` -> `Seoul` 1945.8.15; `Kiev` -> `Kyiv` 1991.8.24; `Constantinople` -> `Istanbul` 1930.3.28; `Danzig` -> `Gdańsk` 1945.3.30; `Bombay` -> `Mumbai` 1995.11.4; `Batavia` -> `Jakarta` 1942.12.8; `Edo` -> `Tokyo` 1868.9.3; `Tenochtitlan` -> `Ciudad de México` / `Mexico City` 1521.8.13.
   - Pure Latin script ONLY (zero Cyrillic, Arabic, Greek, CJK, Hangul, Devanagari, Thai glyphs; zero ASCII backtick haceks `` ` ``; zero comma-inverted articles like `Mans, Le`; zero parentheticals like `(Russia)`).
2. Historical Period Accuracy, Ancient Sunset (`SC-04`) & Colonial Floor (`SC-05`) Rules:
   - Ancient names MUST sunset at their historical transition (`Bagdata` -> `Baghdad` by `762.7.30`; `Birtha` -> `Tikrīt` by `637.1.1`; `Seleucia on the Tigris` -> `Ctesiphon` `-140.1.1` -> `Al-Mada'in` `637.1.1` -> `Salman Pak` `1700.1.1`; `Pataliputra` -> `Patna` by `1541.1.1`). Never leave Pleiades ancient names until `1900.1.1`.
   - Never backproject colonial/modern names (`Canning`, `Charfasson`, `English Bazar`, `Bakerganj`, `Berhampore`, `Mymensingh Sadar`, `Gaibandha Sadar`, `Bhola Sadar`) onto pre-colonial eras (`1400 AD`).
3. Capital City Precedence & Zero Suburb-Hijacking (`SC-03`):
   - Any settlement flagged `"cap": true` MUST always carry the canonical contemporaneous name of that capital city across its full history; strip suburbs/quarters (`Sotteville-lès-Rouen`, `Sainte-Foy-lès-Lyon`, `Weststadt`, `Montigny-lès-Metz`, `Delicias`, `Meckenbeuren`).
4. Zero GIS, Rock-Art, Survey, Title, or Abbreviation Junk (`SC-06`):
   - Never emit `_wfl`, `_none`, `Petroglifos`, `Parcela`, `Dhibi`, `\`, ` + `, `a.d.`, `b.Pr.`, `i.d.OPf.`, `v.d.`, `s.r.o.`, `Uniwersytet`, `Universitäts- und Hansestadt`, or ` Sadar`.
5. Date Key Schema (`yyyy.m.d`):
   - Keys MUST match `^-?\\d+\\.\\d+\\.\\d+$` (`-10000 <= Y <= 2026`, `Y != 0`, `1 <= M <= 12`, `1 <= D <= 31`), ascending chronologically.
6. Knowledge-Base First:
   - Code historical timelines directly from your historical knowledge base without per-city web search loops. Do NOT call `run_command` or `read_file`."""


def coord_key (coords):
  """Formats `[lng, lat]` into a canonical 5-decimal lookup signature."""
  return f"{float(coords[0]):.5f},{float(coords[1]):.5f}"


def parse_date_tuple (d_str):
  """Parses `yyyy.m.d` into integer tuple `(year, month, day)`."""
  parts = str(d_str or "").split(".")
  if len(parts) != 3:
    return None
  try:
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    if y == 0 or y < -10000 or y > 2026 or m < 1 or m > 12 or d < 1 or d > 31:
      return None
    return (y, m, d)
  except Exception:
    return None


def normalise_names_map (raw_names):
  """Normalises either a `{date: name}` dict or `[[date, name]]` pair list into a sorted `{date: name}` dict."""
  pairs = []
  if isinstance(raw_names, dict):
    for dk, nv in raw_names.items():
      pairs.append((str(dk or "").strip(), str(nv or "").strip()))
  elif isinstance(raw_names, list):
    for item in raw_names:
      if isinstance(item, (list, tuple)) and len(item) >= 2:
        pairs.append((str(item[0] or "").strip(), str(item[1] or "").strip()))
      elif isinstance(item, dict) and item.get("date") and item.get("name"):
        pairs.append((str(item["date"]).strip(), str(item["name"]).strip()))

  valid = []
  for dk, nv in pairs:
    dt = parse_date_tuple(dk)
    if dt is not None and nv:
      valid.append((dt, dk, nv))
  valid.sort(key=lambda x: x[0])

  out = {}
  prev_low = ""
  for _, dk, nv in valid:
    low = nv.lower()
    if low == prev_low:
      continue
    out[dk] = nv
    prev_low = low
  return out


def resolve_pass1_dir ():
  """Resolves the Pass-1 `toponymy_batches/<slug>/pass1` directory and rejects Pass-2 paths."""
  svea_root = args.get("svea_root") or (WORKSPACES[0] if WORKSPACES else os.getcwd())
  in_dir = args.get("in_dir")
  if in_dir:
    target = os.path.abspath(in_dir)
  else:
    slug = str(args.get("slug") or args.get("project") or "polaris").strip().lower()
    target = os.path.join(svea_root, "tests", "toponymy_batches", slug)

  if os.path.basename(target).lower() == "pass2":
    raise RuntimeError("Refusing to launch LLM swarm on Pass-2 residuals; run resolve_residual_toponymy_whg_geohack.js instead.")

  pass1_sub = os.path.join(target, "pass1")
  if os.path.isdir(pass1_sub):
    return pass1_sub
  return target


def programmatic_validate (input_items, resolved_by_ck):
  """Runs zero-cost programmatic schema, Latin-script, date, and duplicate checks prior to LLM auditing."""
  errors = []
  for orig in input_items:
    ck = coord_key(orig["coords"])
    entry = resolved_by_ck.get(ck)
    if not entry:
      errors.append({"coord_key": ck, "rule": "MISSING_COORD", "detail": f"Missing coordinate {ck} in output.", "fix": f"Emit entry for coords {orig['coords']}."})
      continue
    names_map = entry.get("names")
    if not isinstance(names_map, dict) or len(names_map) == 0:
      errors.append({"coord_key": ck, "rule": "EMPTY_NAMES", "detail": "names map must have >= 1 yyyy.m.d entry.", "fix": "Provide valid yyyy.m.d: name map."})
      continue

    prev_dt = None
    prev_low = ""
    for dk, nv in names_map.items():
      dt = parse_date_tuple(dk)
      nm = str(nv or "").strip()
      if dt is None or not DATE_RE.match(str(dk)):
        errors.append({"coord_key": ck, "rule": "BAD_DATE", "detail": f"Invalid date key {dk!r}.", "fix": "Use valid non-zero yyyy.m.d date."})
        break
      if prev_dt is not None and dt < prev_dt:
        errors.append({"coord_key": ck, "rule": "UNSORTED_DATE", "detail": f"Dates out of order at {dk}.", "fix": "Order date keys strictly ascending."})
        break
      if not nm or nm in ("0", "Unknown", "Settlement") or "?" in nm or "`" in nm or "(" in nm or ")" in nm:
        errors.append({"coord_key": ck, "rule": "CORRUPT_NAME", "detail": f"Invalid/corrupt name {nm!r}.", "fix": "Use clean Latin-script settlement name without backticks or parentheticals."})
        break
      if NON_LATIN_RE.search(nm):
        errors.append({"coord_key": ck, "rule": "NON_LATIN", "detail": f"Non-Latin glyph in {nm!r}.", "fix": "Transliterate into contemporaneous English-language Latin script."})
        break
      if ARTICLE_INVERT_RE.match(nm):
        errors.append({"coord_key": ck, "rule": "INVERTED_ARTICLE", "detail": f"Comma-inverted article in {nm!r}.", "fix": "Place definite article before the name."})
        break
      if INTRA_DISTRICT_RE.search(nm):
        errors.append({"coord_key": ck, "rule": "INTRA_MUNICIPAL", "detail": f"Intra-municipal ward/district name {nm!r}.", "fix": "Replace with parent municipal/capital city name."})
        break
      if ENGLISH_EXONYM_OR_ASCII_RE.match(nm):
        ctry_orig = str(orig.get("country") or "")
        is_us_ca_au = bool(re.search(r"^(?:United States|United States of America|Canada|Australia|Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)$", ctry_orig, re.I))
        if not is_us_ca_au:
          errors.append({"coord_key": ck, "rule": "NON_ENDONYMIC_OR_ASCII", "detail": f"English exonym or stripped-ASCII name {nm!r}.", "fix": "Cast to native endonymic Latin orthography with full diacritics (e.g. Wien, München, Praha, Warszawa, Wrocław, Gorzów Wielkopolski, Firenze, Napoli, København)."})
          break
      if GIS_ARCH_JUNK_RE.search(nm):
        errors.append({"coord_key": ck, "rule": "GIS_OR_ARCH_JUNK", "detail": f"GIS/arch/title/abbreviation junk {nm!r}.", "fix": "Use clean municipality name without titles, abbreviations, or GIS/arch suffixes."})
        break
      if prev_low and nm.lower() == prev_low:
        errors.append({"coord_key": ck, "rule": "CONSECUTIVE_DUP", "detail": f"Consecutive duplicate name {nm!r}.", "fix": "Remove consecutive identical name entry."})
        break
      prev_dt = dt
      prev_low = nm.lower()
  return errors


async def invoke_agent_bounded (sem, prompt, schema, role, type_name, models, fallback_schema=None):
  """Calls `agent()` strictly inside the shared n<=24 semaphore with exponential backoff and schema fallback."""
  backoffs = [15, 35, 75]
  active_schema = schema
  last_err = None

  for attempt in range(len(backoffs) + 1):
    m = models[min(attempt, len(models) - 1)]
    try:
      async with sem:
        return await asyncio.wait_for(
          agent(
            prompt=prompt,
            schema=active_schema,
            role=role if attempt == 0 else f"{role} r{attempt}",
            type_name=type_name,
            model=m,
          ),
          timeout=int(args.get("agent_timeout_s", 360)),
        )
    except Exception as err:
      last_err = err
      msg = str(err)
      if fallback_schema is not None and active_schema is schema and ("additionalProperties" in msg or "properties" in msg.lower() or "schema" in msg.lower()):
        log(f"[schema-fallback] {role}: switching worker schema from object map to [date,name] pair list at tool boundary.")
        active_schema = fallback_schema
        continue
      if attempt < len(backoffs):
        delay = backoffs[attempt]
        log(f"[retry {attempt + 1}/{len(backoffs)}] {role} ({m}): {msg[:90]}; waiting {delay}s")
        await asyncio.sleep(delay)
      else:
        raise last_err
  raise last_err


def build_worker_prompt (batch_idx, items, prior_errors=None, prior_draft=None):
  """Builds a minimal-token Pass-1 worker prompt using compact `[lng, lat]` + `date: string` maps."""
  fix_block = ""
  if prior_errors:
    fix_block = (
      "\nAUDITOR REJECTION — FIX EVERY LISTED COORDINATE SURGICALLY:\n"
      + json.dumps(prior_errors, ensure_ascii=False, separators=(",", ":"))
      + "\n"
    )
  if prior_draft:
    formatted_draft = []
    for dr in prior_draft:
      nm_raw = dr.get("names")
      if isinstance(nm_raw, dict):
        nm_list = [{"date": k, "name": v} for k, v in nm_raw.items()]
      else:
        nm_list = nm_raw
      formatted_draft.append({"coords": dr["coords"], "names": nm_list})
    fix_block += (
      "\nPREVIOUS DRAFT FOR REJECTED COORDINATES:\n"
      + json.dumps(formatted_draft, ensure_ascii=False, separators=(",", ":"))
      + "\n"
    )

  return (
    f"Viscount Pass-1 Toponymy Worker — Batch {batch_idx:03d} ({len(items)} cities)\n\n"
    f"{STRUCTURAL_RULEBOOK}\n"
    f"{fix_block}\n"
    f"Return 1-to-1 entries in `cities` preserving exact `[lng, lat]` `coords` and simplified chronological `names` as an array of `{{\"date\":\"yyyy.m.d\",\"name\":\"Name\"}}` objects.\n"
    f"INPUT:\n{json.dumps(items, ensure_ascii=False, separators=(',', ':'))}\n"
  )


def build_auditor_prompt (batch_idx, orig_items, proposed_items, prior_errors=None):
  """Builds the strictly separate read-only zero-tolerance auditor prompt."""
  prior_block = ""
  if prior_errors:
    prior_block = (
      "\nPRIOR AUDIT DIRECTIVE (do not contradict previous ruling-authority fixes if addressed):\n"
      + json.dumps(prior_errors, ensure_ascii=False, separators=(",", ":"))
      + "\n\n"
    )
  return (
    f"Viscount Pass-1 Toponymy Auditor (ZERO-TOLERANCE) — Batch {batch_idx:03d} ({len(proposed_items)} cities)\n\n"
    "You are an independent read-only historical toponymy auditor. Do NOT modify files or run commands.\n"
    f"{STRUCTURAL_RULEBOOK}\n\n"
    "Audit EVERY coordinate's `names` map against the rules above. Set `approved: false` and list every offending `coord_key` "
    "(`lng.toFixed(5),lat.toFixed(5)`) if even ONE historical, occupying-authority, capital-name, period-accuracy, Latin-script, "
    "or date error exists. Set `approved: true, errors: []` ONLY when 100% of items pass.\n\n"
    f"{prior_block}"
    f"INPUT:\n{json.dumps(orig_items, ensure_ascii=False, separators=(',', ':'))}\n\n"
    f"PROPOSED:\n{json.dumps(proposed_items, ensure_ascii=False, separators=(',', ':'))}\n"
  )


async def process_and_audit_batch (batch_path, sem):
  """Resolves and audits one compact Pass-1 batch with surgical error-only re-prompting."""
  with open(batch_path, "r", encoding="utf-8") as fh:
    raw = json.load(fh)

  items = raw if isinstance(raw, list) else raw.get("cities", raw.get("settlements", []))
  m_idx = re.search(r"batch_(\d+)\.json$", os.path.basename(batch_path), re.IGNORECASE)
  batch_idx = int(m_idx.group(1)) if m_idx else 1
  out_dir = os.path.dirname(batch_path)
  out_path = os.path.join(out_dir, "resolved_" + os.path.basename(batch_path))

  if not items:
    return {"approved": True, "batch_index": batch_idx, "batch_path": out_path, "count": 0, "errors_remaining": 0, "rounds": 0}

  # Resume-skip if already auditor-approved, or surgical resume for partial remaining_errors
  seed_resolved = {}
  seed_errors = None
  active_items = items
  if os.path.exists(out_path):
    try:
      prev = json.load(open(out_path, "r", encoding="utf-8"))
      if prev.get("approved_by_auditor") is True and len(prev.get("cities", [])) == len(items):
        return {
          "approved": True,
          "batch_index": batch_idx,
          "batch_path": out_path,
          "count": len(items),
          "errors_remaining": 0,
          "resumed": True,
          "rounds": 0,
        }
      rem_errs = prev.get("remaining_errors") or []
      if prev.get("approved_by_auditor") is False and len(prev.get("cities", [])) == len(items) and len(rem_errs) > 0:
        bad_cks = set(str(e.get("coord_key") or "").strip() for e in rem_errs if e.get("coord_key"))
        for c_entry in prev.get("cities", []):
          ck = coord_key(c_entry["coords"])
          seed_resolved[ck] = c_entry
        failed_subset = [it for it in items if coord_key(it["coords"]) in bad_cks]
        if failed_subset:
          active_items = failed_subset
          seed_errors = rem_errs
          log(f"[surgical-resume] Batch {batch_idx:03d}: resuming {len(failed_subset)} failed coord(s) out of {len(items)}.")
    except Exception:
      pass

  primary_model = args.get("model", "flash")
  escalate_model = args.get("escalate_model", "flash")
  auditor_model = args.get("auditor_model", "inherit")
  max_rounds = int(args.get("max_audit_rounds", 5))
  sub_chunk_size = max(1, int(args.get("sub_chunk_size", 50)))
  sub_chunks = [active_items[i:i + sub_chunk_size] for i in range(0, len(active_items), sub_chunk_size)]

  async def run_sub_chunk (sub_idx, sub_items):
    orig_by_ck = {coord_key(it["coords"]): it for it in sub_items}
    pending_cks = [coord_key(it["coords"]) for it in sub_items]
    resolved_by_ck = {ck: seed_resolved[ck] for ck in pending_cks if ck in seed_resolved} if seed_errors else {}
    prior_errors = seed_errors
    sub_approved = False
    last_errors = []
    sub_rounds = 0
    tag = f"b{batch_idx:03d}" if len(sub_chunks) == 1 else f"b{batch_idx:03d}s{sub_idx + 1}"

    for sub_rounds in range(1, max_rounds + 1):
      w_models = [primary_model, primary_model, primary_model]
      req_items = [orig_by_ck[ck] for ck in pending_cks]
      prev_draft = [resolved_by_ck[ck] for ck in pending_cks if ck in resolved_by_ck] if (sub_rounds > 1 or seed_errors) else None
      w_prompt = build_worker_prompt(batch_idx, req_items, prior_errors, prev_draft)

      w_res = await invoke_agent_bounded(
        sem=sem,
        prompt=w_prompt,
        schema=WORKER_SCHEMA_ENTRIES,
        role=f"Pass1 Flash {tag} r{sub_rounds} ({len(req_items)})",
        type_name="self",
        models=w_models,
        fallback_schema=WORKER_SCHEMA_PAIRS,
      )

      for city in (w_res.get("cities") or []):
        if not isinstance(city, dict) or not isinstance(city.get("coords"), list) or len(city["coords"]) < 2:
          continue
        ck = coord_key(city["coords"])
        if ck not in orig_by_ck:
          continue
        clean_map = normalise_names_map(city.get("names"))
        resolved_by_ck[ck] = {"coords": orig_by_ck[ck]["coords"], "names": clean_map}

      # Zero-cost programmatic pre-audit
      prog_errs = programmatic_validate(req_items, resolved_by_ck)
      if prog_errs:
        bad_cks = sorted(set(e["coord_key"] for e in prog_errs if e["coord_key"] in orig_by_ck))
        pending_cks = bad_cks if bad_cks else pending_cks
        prior_errors = prog_errs
        last_errors = prog_errs
        log(f"[precheck] Batch {tag} r{sub_rounds}: {len(prog_errs)} schema error(s) on {len(pending_cks)} coord(s).")
        continue

      # Strictly separate read-only auditor checks only pending_cks
      aud_orig = [orig_by_ck[ck] for ck in pending_cks]
      aud_prop = [resolved_by_ck[ck] for ck in pending_cks]
      aud_prompt = build_auditor_prompt(batch_idx, aud_orig, aud_prop, prior_errors)
      aud_res = await invoke_agent_bounded(
        sem=sem,
        prompt=aud_prompt,
        schema=AUDITOR_SCHEMA,
        role=f"Pass1 Auditor {tag} r{sub_rounds} ({len(pending_cks)})",
        type_name="research",
        models=[auditor_model, primary_model, auditor_model, primary_model],
      )
      aud_errs = list(aud_res.get("errors") or [])
      if aud_res.get("approved") is True and len(aud_errs) == 0:
        sub_approved = True
        last_errors = []
        break

      bad_cks = []
      for e in aud_errs:
        ek = str(e.get("coord_key") or "").strip()
        if ek in orig_by_ck and ek not in bad_cks:
          bad_cks.append(ek)
      if bad_cks:
        pending_cks = bad_cks
      prior_errors = aud_errs
      last_errors = aud_errs
      log(f"[auditor] Batch {tag} r{sub_rounds} rejected {len(aud_errs)} error(s) across {len(pending_cks)} coord(s); patching surgically.")

    return {
      "approved": sub_approved,
      "errors": last_errors,
      "resolved_by_ck": resolved_by_ck,
      "rounds": sub_rounds,
    }

  sub_results = await asyncio.gather(*(run_sub_chunk(idx, sc) for idx, sc in enumerate(sub_chunks)))
  merged_resolved = dict(seed_resolved) if seed_errors else {}
  all_sub_errors = []
  max_sub_round = 0
  approved = True
  for sr in sub_results:
    merged_resolved.update(sr["resolved_by_ck"])
    all_sub_errors.extend(sr["errors"])
    if sr["rounds"] > max_sub_round:
      max_sub_round = sr["rounds"]
    if not sr["approved"] or len(sr["errors"]) > 0:
      approved = False

  last_errors = all_sub_errors
  round_num = max_sub_round
  final_cities = [merged_resolved[coord_key(it["coords"])] for it in items if coord_key(it["coords"]) in merged_resolved]
  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump({
      "approved_by_auditor": approved,
      "batch_index": batch_idx,
      "cities": final_cities,
      "count": len(final_cities),
      "errors_remaining": len(last_errors),
      "pass": 1,
      "remaining_errors": last_errors,
      "schema_version": "3.0_compact_coord_map",
    }, fh, ensure_ascii=False, separators=(",", ":"))

  return {
    "approved": approved,
    "batch_index": batch_idx,
    "batch_path": out_path,
    "count": len(final_cities),
    "errors_remaining": len(last_errors),
    "expected": len(items),
    "rounds": round_num,
  }


async def safe_process_batch (bp, sem):
  """Crash-isolated batch wrapper so one transient error never aborts sibling batches."""
  m_idx = re.search(r"batch_(\d+)\.json$", os.path.basename(bp), re.IGNORECASE)
  batch_idx = int(m_idx.group(1)) if m_idx else 1
  out_path = os.path.join(os.path.dirname(bp), "resolved_" + os.path.basename(bp))
  try:
    return await process_and_audit_batch(bp, sem)
  except Exception as err:
    log(f"[batch-error] Batch {batch_idx:03d} failed: {str(err)[:200]}")
    return {
      "approved": False,
      "batch_index": batch_idx,
      "batch_path": out_path,
      "count": 0,
      "error": str(err)[:200],
      "errors_remaining": 1,
      "rounds": 0,
    }


phase("Discover Pass-1 compact batches")
batch_dir = resolve_pass1_dir()
if not os.path.isdir(batch_dir):
  raise RuntimeError(f"Pass-1 batch directory not found: {batch_dir}")

batch_files = sorted(
  os.path.join(batch_dir, f)
  for f in os.listdir(batch_dir)
  if re.match(r"^batch_\d+\.json$", f, re.IGNORECASE)
)
max_concurrency = min(HARD_MAX_CONCURRENCY, max(1, int(args.get("max_concurrency", HARD_MAX_CONCURRENCY))))
log(f"Found {len(batch_files)} Pass-1 compact batch file(s) in {batch_dir}; hard semaphore cap n={max_concurrency}")

phase(f"Run Pass-1 Flash + Read-Only Auditor swarm (capped at n={max_concurrency} concurrent)")
sem = asyncio.Semaphore(max_concurrency)
results = await asyncio.gather(*(safe_process_batch(bp, sem) for bp in batch_files))
results.sort(key=lambda r: r.get("batch_index", 0))

total_resolved = sum(r.get("count", 0) for r in results)
total_errors = sum(r.get("errors_remaining", 0) for r in results)
all_approved = all(r.get("approved", False) for r in results) and total_errors == 0

signoff_path = os.path.join(batch_dir, "auditor_signoff.json")
with open(signoff_path, "w", encoding="utf-8") as fh:
  json.dump({
    "approved": all_approved,
    "batches_audited": len(results),
    "errors_remaining": total_errors,
    "max_concurrency_enforced": max_concurrency,
    "pass": 1,
    "results": results,
    "schema_version": "3.0_compact_coord_map",
    "timestamp_gmt0": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "total_resolved": total_resolved,
  }, fh, ensure_ascii=False, indent=2)

log(f"Pass-1 swarm finished: {total_resolved} settlements across {len(results)} batch(es); approved={all_approved}, errors_remaining={total_errors}")
results
