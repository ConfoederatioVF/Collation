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

WORKER_SCHEMA_MAP = {
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
            "type": "object",
            "additionalProperties": {"type": "string"},
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
1. Occupying / De Facto Ruling Authority Rule:
   - Always use the name preferred by the de facto ruling or occupying authority for that period, rendered in the Latin script using the contemporaneous English-language transliteration for that time (e.g. `Keijo` under Japanese rule 1910-1945 -> `Seoul` 1945.8.15; `Kiev` under Russian/Soviet rule -> `Kyiv` 1991.8.24; `Constantinople` -> `Istanbul` 1930.3.28; `Danzig` -> `Gdansk` 1945.3.30; `Bombay` -> `Mumbai` 1995.11.4; `Batavia` -> `Jakarta` 1942.12.8; `Godthaab` -> `Nuuk` 1979.5.1; `Edo` -> `Tokyo` 1868.9.3; `Tenochtitlan` -> `Mexico City` 1521.8.13).
   - Pure Latin script ONLY (zero Cyrillic, Arabic, Greek, CJK, Hangul, Devanagari, Thai glyphs; zero ASCII backtick haceks `` ` ``; zero comma-inverted articles like `Mans, Le`; zero parentheticals like `(Russia)`).
2. Historical Period Accuracy Rule:
   - Use names historically accurate to each era rather than retrofitting modern names into earlier centuries. Pre-colonial settlements must carry their attested pre-colonial ruling-authority name prior to colonial founding/occupation.
3. Capital City Precedence Rule (`"cap": true`):
   - Any settlement flagged `"cap": true` MUST always carry the canonical contemporaneous name of that capital city across its full history (even if the seed/underlying record carries a ward, quarter, or sub-district name such as `Paris 05 Panthéon`, `Al-Dawâwîn`, `Kepos`, or `City of London`).
4. Full-History Simplification at `[lng, lat]`:
   - Take the ENTIRE existing `names` map at `[lng, lat]` into account and simplify it into one clean chronological timeline. Strip intra-municipal wards/arrondissements/districts (`5e Arrondissement`, `Paris 05 Panthéon`, `Shiyakha`, `-ku`), collapse orthographic/spelling-only consecutive duplicates, and preserve genuine historical renames.
5. Date Key Schema (`yyyy.m.d`):
   - Keys MUST match `^-?\\d+\\.\\d+\\.\\d+$` (`-10000 <= Y <= 2026`, `Y != 0`, `1 <= M <= 12`, `1 <= D <= 31`), ascending chronologically. Never fabricate generic `1900.1.1`/`1950.1.1` renames when authentic historical dates are known.
6. Knowledge-Base First:
   - Code historical timelines directly from your historical knowledge base without per-city web search loops (only verify an uncertain major capital rename date if genuinely unsure). Do NOT call `run_command` or `read_file`.
"""


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
          timeout=int(args.get("agent_timeout_s", 240)),
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
    fix_block += (
      "\nPREVIOUS DRAFT FOR REJECTED COORDINATES:\n"
      + json.dumps(prior_draft, ensure_ascii=False, separators=(",", ":"))
      + "\n"
    )

  return (
    f"Viscount Pass-1 Toponymy Worker — Batch {batch_idx:03d} ({len(items)} cities)\n\n"
    f"{STRUCTURAL_RULEBOOK}\n"
    f"{fix_block}\n"
    f"Return 1-to-1 entries in `cities` preserving exact `[lng, lat]` `coords` and simplified chronological `names` (`yyyy.m.d`: string map).\n"
    f"INPUT:\n{json.dumps(items, ensure_ascii=False, separators=(',', ':'))}\n"
  )


def build_auditor_prompt (batch_idx, orig_items, proposed_items):
  """Builds the strictly separate read-only zero-tolerance auditor prompt."""
  return (
    f"Viscount Pass-1 Toponymy Auditor (ZERO-TOLERANCE) — Batch {batch_idx:03d} ({len(proposed_items)} cities)\n\n"
    "You are an independent read-only historical toponymy auditor. Do NOT modify files or run commands.\n"
    f"{STRUCTURAL_RULEBOOK}\n\n"
    "Audit EVERY coordinate's `names` map against the rules above. Set `approved: false` and list every offending `coord_key` "
    "(`lng.toFixed(5),lat.toFixed(5)`) if even ONE historical, occupying-authority, capital-name, period-accuracy, Latin-script, "
    "or date error exists. Set `approved: true, errors: []` ONLY when 100% of items pass.\n\n"
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

  # Resume-skip if already auditor-approved
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
    except Exception:
      pass

  primary_model = args.get("model", "flash")
  escalate_model = args.get("escalate_model", "pro")
  auditor_model = args.get("auditor_model", "inherit")
  max_rounds = int(args.get("max_audit_rounds", 3))

  orig_by_ck = {coord_key(it["coords"]): it for it in items}
  pending_cks = [coord_key(it["coords"]) for it in items]
  resolved_by_ck = {}
  prior_errors = None
  approved = False
  last_errors = []
  round_num = 0

  for round_num in range(1, max_rounds + 1):
    use_pro = round_num >= 3
    w_models = [escalate_model, "inherit", primary_model] if use_pro else [primary_model, primary_model, "inherit"]
    req_items = [orig_by_ck[ck] for ck in pending_cks]
    prev_draft = [resolved_by_ck[ck] for ck in pending_cks if ck in resolved_by_ck] if round_num > 1 else None
    w_prompt = build_worker_prompt(batch_idx, req_items, prior_errors, prev_draft)

    w_res = await invoke_agent_bounded(
      sem=sem,
      prompt=w_prompt,
      schema=WORKER_SCHEMA_MAP,
      role=f"Pass1 {'Pro' if use_pro else 'Flash'} b{batch_idx:03d} r{round_num} ({len(req_items)})",
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
      log(f"[precheck] Batch {batch_idx:03d} r{round_num}: {len(prog_errs)} schema error(s) on {len(pending_cks)} coord(s).")
      continue

    # Strictly separate read-only auditor checks only pending_cks
    aud_orig = [orig_by_ck[ck] for ck in pending_cks]
    aud_prop = [resolved_by_ck[ck] for ck in pending_cks]
    aud_prompt = build_auditor_prompt(batch_idx, aud_orig, aud_prop)
    aud_res = await invoke_agent_bounded(
      sem=sem,
      prompt=aud_prompt,
      schema=AUDITOR_SCHEMA,
      role=f"Pass1 Auditor b{batch_idx:03d} r{round_num} ({len(pending_cks)})",
      type_name="research",
      models=[auditor_model, auditor_model, primary_model],
    )
    aud_errs = list(aud_res.get("errors") or [])
    if aud_res.get("approved") is True and len(aud_errs) == 0:
      approved = True
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
    log(f"[auditor] Batch {batch_idx:03d} r{round_num} rejected {len(aud_errs)} error(s) across {len(pending_cks)} coord(s); patching surgically.")

  final_cities = [resolved_by_ck[coord_key(it["coords"])] for it in items if coord_key(it["coords"]) in resolved_by_ck]
  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump({
      "approved_by_auditor": approved,
      "batch_index": batch_idx,
      "cities": final_cities,
      "count": len(final_cities),
      "errors_remaining": len(last_errors),
      "pass": 1,
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
results = await asyncio.gather(*(process_and_audit_batch(bp, sem) for bp in batch_files))
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
