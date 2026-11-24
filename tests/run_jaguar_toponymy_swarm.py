"""
Project JAGUAR Stage F Historical Toponymy Swarm & Zero-Tolerance Separate Read-Only Auditor.

- Runs Tier 1 (all 103 capitals + all >= 5,000-pop settlements across Pre-Columbian, Colonial,
  and Modern eras) chunked into <= 30-city files across Gemini 3.8 Flash workers (`model="flash"`)
  in quota-safe waves (`wave_size=4`) with resume-skip and exponential-backoff retry on 429/transient errors.
- Strictly separate read-only `toponymy_auditor` (`type_name="research"`) reviews EVERY resolved
  chunk against the /population-regional-study structural toponymy rulebook. If it finds EVEN A
  SINGLE historical mistake, it reports a CRITICAL failure with exact line-item fixes back to
  that worker (alongside its prior output so fixes are surgical) until 0 errors remain,
  escalating to `pro` / Hydrogen on Round 3+ if needed.
- Writes per-batch `resolved_batch_NNN.json` and `auditor_signoff.json`.
"""

import asyncio
import json
import os
import re

WORKER_SCHEMA = {
  "type": "object",
  "properties": {
    "settlements": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "key": {"type": "string"},
          "canonical_name": {"type": "string"},
          "historical_names": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "date": {"type": "string"},
                "name": {"type": "string"}
              },
              "required": ["date", "name"]
            }
          },
          "other_names": {
            "type": "array",
            "items": {"type": "string"}
          }
        },
        "required": ["key", "canonical_name", "historical_names"]
      }
    }
  },
  "required": ["settlements"]
}

AUDITOR_SCHEMA = {
  "type": "object",
  "properties": {
    "approved": {"type": "boolean"},
    "severity": {"type": "string"},
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "key": {"type": "string"},
          "rule_violated": {"type": "string"},
          "detail": {"type": "string"},
          "required_fix": {"type": "string"}
        },
        "required": ["key", "rule_violated", "detail", "required_fix"]
      }
    }
  },
  "required": ["approved", "severity", "errors"]
}

JAGUAR_RULEBOOK = """OPERATION VISCOUNT PROJECT JAGUAR — HISTORICAL TOPONYMY RULEBOOK (ZERO TOLERANCE):
1. Regional Scope: Mexico, Central America (Guatemala, Belize, Honduras, El Salvador, Nicaragua, Costa Rica, Panama), Caribbean Islands (Greater & Lesser Antilles, Bahamas, Trinidad & Tobago), and Bermuda.
2. Endonymic Latin Script & Clean Diacritics:
   - Use standard endonymic Latin orthography with proper Unicode accents/diacritics (Spanish: `Ciudad de México`, `Pátzcuaro`, `San Luis Potosí`, `La Habana`, `San Juan`, `San José`, `Panamá`; French/Haitian: `Port-au-Prince`, `Cap-Haïtien`, `Fort-de-France`, `Jérémie`; Maya/Nahuatl: `Tenochtitlan`, `Tlacopan`, `Texcoco`, `Cholollan`, `Tzintzuntzan`, `Iximché`, `Q'umarkaj`, `Oxwitik`, `Lakam Ha`, `Baakal`, `Uxmal`, `Chichén Itzá`, `T'ho`, `Cuzcatlan`, `Borikén`/`Caparra`).
   - ZERO ALL-CAPS (`AGUATECA` -> `Aguateca`), ZERO ASCII backtick haceks (`` ` ``), ZERO comma-inverted articles (`Trinité, La` -> `La Trinité`), ZERO parentheticals `(Mexico)`, ZERO street addresses, ZERO `?`, `0`, `Unknown`, `Settlement`.
   - Strip trailing archaeological qualifiers (`Site`, `Complex`, `Chiefdom Settlement`) from `canonical_name` when an attested settlement/site proper name exists (`Cantona Site` -> `Cantona`, placing `Cantona Site` in `other_names`).
3. Mandatory Pre-Columbian & Indigenous Endonyms (NEVER back-project European colonial names into pre-contact centuries!):
   - Any settlement with `earliest_year < 1519` (Mexico/Central America) or `< 1492` (Caribbean) MUST begin with its attested indigenous/archaeological endonym at or before `earliest_year` (e.g., `Tenochtitlan` before `Ciudad de México` `1521.8.13`; `T'ho` before `Mérida` `1542.1.6`; `Huaxyacac` before `Antequera` `1529.1.1` -> `Oaxaca de Juárez` `1872.10.10`; `Cuzcatlan` before `San Salvador` `1525.4.1`; `Oxwitik` before `Copán`; `Lakam Ha` for `Palenque`; `Uxwitzá` for `Caracol`; `Ox Te' Tuun` for `Calakmul`; `Caparra` `1508.8.8` -> `San Juan` `1521.1.1`).
   - If a settlement has NO colonial renaming (it kept its indigenous Nahuatl/Maya/Purépecha/Zapotec/Mixtec/Taíno name like `Tlaquepaque`, `Tehuacán`, `Pátzcuaro`, `Tzintzuntzan`, `Tecomán`, `Umán`, `Tepotzotlán`, `Zacatlán`, `Cobá`, `Bayamo`, `Caguas`), record its authentic indigenous/modern name starting at `earliest_year` (never fabricate spelling-variant renames!).
4. Colonial & Republican Renamings (Use `official_ahl_history` when provided!):
   - Respect authentic Spanish colonial foundations/renamings (e.g., `Villa Rica de la Vera Cruz` `1519.4.22` -> `Veracruz`, `Valladolid` `1541.5.18` -> `Morelia` `1828.9.12`, `Antequera` -> `Oaxaca` -> `Oaxaca de Juárez` `1872.10.10`, `Santiago de los Caballeros de Guatemala` `1524.7.25` -> `Nueva Guatemala de la Asunción` `1776.1.2` -> `Ciudad de Guatemala`, `Port-Républicain` `1793.1.1` -> `Port-au-Prince`, `Ciudad Trujillo` `1936.1.11` -> `Santo Domingo` `1961.11.23`, `Belize Town` -> `Belize City`, `Villa Hermosa de San Juan Bautista` -> `San Juan Bautista` -> `Villahermosa` `1916.2.3`).
   - When `official_ahl_history` (official INEGI Archivo Histórico de Localidades legal rename dates) is provided on a Mexican item, incorporate those authentic legal rename events faithfully (without creating fake consecutive spelling-variant entries!).
5. Capitals (`is_capital=true`):
   - MUST have complete, historically accurate timelines spanning every pre-Columbian, colonial, and modern era in which they existed (`first_year <= earliest_year`).
6. Strict Chronology & Schema Invariants:
   - Dates MUST match `^-?\\d+\\.\\d+\\.\\d+$` (`-10000 <= Y <= 2026`, `Y != 0` — use `-1` instead of `0`, `1 <= M <= 12`, `1 <= D <= 31`).
   - Sorted strictly ascending by date.
   - Earliest entry year MUST be `<= earliest_year` (never lag by > 0 years; if `earliest_year == 0` use `-1.1.1`).
   - NEVER fabricate generic placeholder dates like `1950.1.1` or `1900.1.1` when the settlement is older or has an attested foundation/rename year (for modern post-1900 settlements first attested in a census with no earlier rename, use `earliest_year.1.1` or their actual foundation year).
   - Extant modern settlements (`latest_year >= 1950`) MUST have their terminal `historical_names` entry match `canonical_name` (normalised stem).
   - Collapse trivial accent/spelling/romanisation variants into `other_names` — NEVER put consecutive same-stem variants (like `Acambaro` -> `Acámbaro` or `Port au Prince` -> `Port-au-Prince`) as separate `historical_names` entries!
   - Preserve `canonical_name` clean and free of intra-municipal ward/borough/alcaldía suffixes.
"""


async def call_agent_with_retry (prompt, schema, role, type_name, models):
  """Calls `agent(...)` with exponential backoff on 429 / transient quota errors."""
  backoffs = [20, 45, 90, 150]
  last_err = None
  for attempt in range(len(backoffs) + 1):
    m = models[min(attempt, len(models) - 1)]
    try:
      return await agent(
        prompt=prompt,
        schema=schema,
        role=role if attempt == 0 else f"{role} retry{attempt}",
        type_name=type_name,
        model=m,
      )
    except Exception as err:
      last_err = err
      msg = str(err)
      if attempt < len(backoffs):
        delay = backoffs[attempt]
        log(f"[backoff] {role} ({m}) hit error ({msg[:120]}); sleeping {delay}s before retry {attempt + 1}/{len(backoffs)}...")
        await asyncio.sleep(delay)
      else:
        raise last_err


def build_worker_prompt (batch_idx, batch_items, prior_errors=None, prior_resolved=None):
  compact = []
  for it in batch_items:
    row = {
      "key": it.get("key"),
      "name": it.get("name"),
      "country": it.get("country"),
      "region": it.get("region"),
      "coords_lat_lng": it.get("coords_lat_lng"),
      "earliest_year": it.get("earliest_year"),
      "latest_year": it.get("latest_year"),
      "max_pop": it.get("max_pop"),
      "is_capital": bool(it.get("is_capital")),
      "known_aliases": (it.get("known_aliases") or [])[:8],
      "existing_historical_names": it.get("existing_historical_names") or [],
      "reason": it.get("reason"),
    }
    if it.get("official_ahl_history"):
      row["official_ahl_history"] = it["official_ahl_history"]
    compact.append(row)

  err_block = ""
  if prior_errors:
    err_block = (
      "\nCRITICAL AUDITOR FAILURE — FIX EVERY SINGLE ERROR BELOW SURGICALLY WHILE KEEPING ALL OTHER VALID ITEMS INTACT:\n"
      + json.dumps(prior_errors, ensure_ascii=False, indent=2)
      + "\n"
    )
  if prior_resolved:
    compact_prev = [
      {
        "key": r.get("key"),
        "canonical_name": r.get("canonical_name"),
        "historical_names": r.get("historical_names"),
        "other_names": r.get("other_names", []),
      }
      for r in prior_resolved
    ]
    err_block += (
      "\nYOUR PREVIOUS DRAFT (preserve all already-correct settlements and apply the required fixes above):\n"
      + json.dumps(compact_prev, ensure_ascii=False)
      + "\n"
    )

  return f"""JAGUAR Historical Toponymy Worker (Gemini 3.8 Flash) — Batch {batch_idx}

Resolve clean historical toponymy records for EVERY input settlement below.
Do NOT call `run_command`, `read_file`, or edit local files. Keep responses concise and strictly schema-valid.

{JAGUAR_RULEBOOK}
{err_block}
Return a 1-to-1 entry in `settlements` preserving the exact `key` for ALL {len(compact)} input items and call `finish`.

Input settlements ({len(compact)} items):
{json.dumps(compact, ensure_ascii=False)}
"""


def build_auditor_prompt (batch_idx, orig_items, resolved_items):
  compact_orig = [
    {
      "key": it.get("key"),
      "name": it.get("name"),
      "country": it.get("country"),
      "earliest_year": it.get("earliest_year"),
      "latest_year": it.get("latest_year"),
      "max_pop": it.get("max_pop"),
      "is_capital": bool(it.get("is_capital")),
      "official_ahl_history": it.get("official_ahl_history") or [],
    }
    for it in orig_items
  ]
  compact_res = [
    {
      "key": r.get("key"),
      "canonical_name": r.get("canonical_name"),
      "historical_names": r.get("historical_names"),
      "other_names": r.get("other_names", []),
    }
    for r in resolved_items
  ]
  return f"""JAGUAR Historical Toponymy Independent Auditor (ZERO-TOLERANCE) — Batch {batch_idx}

You are a strictly separate read-only historical auditor. Do NOT modify files or run commands.
Check EVERY SINGLE settlement in `resolved_settlements` against EVERY rule in the rulebook below.
If you detect EVEN ONE historical error — anachronistic colonial name before 1492/1519, missing attested pre-Columbian indigenous endonym for a major indigenous centre, wrong/fabricated rename date, missing official colonial/republican rename (e.g. Valladolid->Morelia, Ciudad Trujillo->Santo Domingo, Antequera->Oaxaca de Juárez), `first_year > earliest_year`, year `0`, unsorted dates, consecutive same-stem spelling variants, ALL-CAPS names, `Site` suffix left on `canonical_name`, parentheticals, inverted articles, missing item key, or terminal name mismatch for `latest_year >= 1950` — you MUST return `approved: false`, `severity: "CRITICAL"`, and list EVERY offending key with `rule_violated`, `detail`, and `required_fix`.
Return `approved: true`, `severity: "PASS"`, `errors: []` ONLY when 100% of items are historically and structurally error-free.

{JAGUAR_RULEBOOK}

Original input items ({len(compact_orig)}):
{json.dumps(compact_orig, ensure_ascii=False)}

Worker resolved_settlements ({len(compact_res)}):
{json.dumps(compact_res, ensure_ascii=False)}
"""


async def process_and_audit_batch (batch_path):
  with open(batch_path, "r", encoding="utf-8") as fh:
    raw = json.load(fh)

  items = raw.get("settlements", [])
  batch_idx = raw.get("batch_index", 1)
  out_dir = os.path.dirname(batch_path)
  out_path = os.path.join(out_dir, "resolved_" + os.path.basename(batch_path))

  prior_resolved = None
  if os.path.exists(out_path):
    try:
      prev = json.load(open(out_path, "r", encoding="utf-8"))
      if prev.get("approved_by_auditor") is True and len(prev.get("settlements", [])) == len(items):
        return {
          "approved": True,
          "batch_index": batch_idx,
          "batch_path": out_path,
          "count": len(prev["settlements"]),
          "errors_remaining": 0,
          "expected": len(items),
          "rounds": 0,
          "resumed": True,
        }
      elif len(prev.get("settlements", [])) == len(items):
        prior_resolved = prev.get("settlements", [])
    except Exception:
      pass

  if not items:
    return {"approved": True, "batch_index": batch_idx, "batch_path": out_path, "count": 0, "errors_remaining": 0, "expected": 0, "rounds": 0}

  primary_model = args.get("model", "flash")
  escalate_model = args.get("escalate_model", "pro")
  auditor_model = args.get("auditor_model", "inherit")
  max_rounds = int(args.get("max_audit_rounds", 4))

  prior_errors = None
  merged_settlements = list(prior_resolved) if prior_resolved else []
  approved = False
  last_errors = []
  round_num = 0

  # If resuming a previously unapproved draft, audit the draft first to collect exact line-item errors
  if prior_resolved:
    aud_prompt = build_auditor_prompt(batch_idx, items, prior_resolved)
    aud_res = await call_agent_with_retry(
      prompt=aud_prompt,
      schema=AUDITOR_SCHEMA,
      role=f"JAGUAR Toponymy Auditor b{batch_idx:03d} precheck",
      type_name="research",
      models=[auditor_model, auditor_model, "flash", "flash"],
    )
    last_errors = list(aud_res.get("errors") or [])
    approved = bool(aud_res.get("approved")) and len(last_errors) == 0
    if approved:
      with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({
          "approved_by_auditor": True,
          "batch_index": batch_idx,
          "count": len(merged_settlements),
          "errors_remaining": 0,
          "project": "JAGUAR",
          "rounds": 0,
          "settlements": merged_settlements,
        }, fh, ensure_ascii=False, indent=2)
      return {
        "approved": True,
        "batch_index": batch_idx,
        "batch_path": out_path,
        "count": len(merged_settlements),
        "errors_remaining": 0,
        "expected": len(items),
        "rounds": 0,
      }
    prior_errors = last_errors
    log(f"[resume-audit] Batch {batch_idx} has {len(last_errors)} error(s) to fix surgically.")

  for round_num in range(1, max_rounds + 1):
    # Escalate to pro/Hydrogen on Round 3+ (or Round 2+ when fixing a previously failed batch)
    use_pro = (round_num >= 3) or (bool(prior_resolved) and round_num >= 2)
    w_models = [escalate_model, "inherit", primary_model] if use_pro else [primary_model, primary_model, "inherit", escalate_model]
    w_prompt = build_worker_prompt(batch_idx, items, prior_errors, merged_settlements if merged_settlements else None)

    result = await call_agent_with_retry(
      prompt=w_prompt,
      schema=WORKER_SCHEMA,
      role=f"JAGUAR {'Pro' if use_pro else 'Flash'} Toponymy b{batch_idx:03d} r{round_num}",
      type_name="self",
      models=w_models,
    )

    by_key = {str(it.get("key")): it for it in (result.get("settlements") or []) if it.get("key")}
    merged_settlements = []
    missing_keys = []
    for orig in items:
      k = str(orig.get("key"))
      res = by_key.get(k)
      if not res:
        missing_keys.append(k)
        continue
      merged = dict(orig)
      merged["canonical_name"] = res.get("canonical_name", orig.get("name"))
      merged["historical_names"] = res.get("historical_names", [])
      merged["other_names"] = res.get("other_names", [])
      merged["verified_settlement"] = True
      merged_settlements.append(merged)

    if missing_keys:
      last_errors = [
        {
          "key": mk,
          "rule_violated": "MISSING_ITEM",
          "detail": f"Worker omitted required input settlement key {mk}.",
          "required_fix": f"Include complete historical_names entry for key {mk}.",
        }
        for mk in missing_keys
      ]
      log(f"[CRITICAL] Batch {batch_idx} r{round_num} missing {len(missing_keys)} key(s); sending back to worker.")
      prior_errors = last_errors
      continue

    aud_prompt = build_auditor_prompt(batch_idx, items, merged_settlements)
    aud_res = await call_agent_with_retry(
      prompt=aud_prompt,
      schema=AUDITOR_SCHEMA,
      role=f"JAGUAR Toponymy Auditor b{batch_idx:03d} r{round_num}",
      type_name="research",
      models=[auditor_model, auditor_model, "flash", "flash"],
    )
    last_errors = list(aud_res.get("errors") or [])
    approved = bool(aud_res.get("approved")) and len(last_errors) == 0
    if approved:
      break
    log(f"[CRITICAL AUDITOR FAILURE] Batch {batch_idx} r{round_num} rejected with {len(last_errors)} error(s); sending back to worker.")
    prior_errors = last_errors

  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump({
      "approved_by_auditor": approved,
      "batch_index": batch_idx,
      "count": len(merged_settlements),
      "errors_remaining": len(last_errors),
      "project": "JAGUAR",
      "rounds": round_num,
      "settlements": merged_settlements,
    }, fh, ensure_ascii=False, indent=2)

  return {
    "approved": approved,
    "batch_index": batch_idx,
    "batch_path": out_path,
    "count": len(merged_settlements),
    "errors_remaining": len(last_errors),
    "expected": len(items),
    "rounds": round_num,
  }


phase("Discover Tier 1 JAGUAR batches (resume-aware)")
svea_root = args.get("svea_root") or (WORKSPACES[0] if WORKSPACES else os.getcwd())
batch_dir = args.get("in_dir") or os.path.join(svea_root, "tests", "toponymy_batches", "jaguar_flash")
wave_size = int(args.get("wave_size", 4))

all_batch_files = sorted(
  os.path.join(batch_dir, f)
  for f in os.listdir(batch_dir)
  if re.match(r"^batch_\d+\.json$", f, re.IGNORECASE)
)

# Pre-filter already-approved batches so waves only run pending/unapproved batches
pending_files = []
already_approved = []
for bp in all_batch_files:
  out_p = os.path.join(batch_dir, "resolved_" + os.path.basename(bp))
  raw = json.load(open(bp, "r", encoding="utf-8"))
  bidx = raw.get("batch_index", 1)
  n_exp = len(raw.get("settlements", []))
  is_ok = False
  if os.path.exists(out_p):
    try:
      prev = json.load(open(out_p, "r", encoding="utf-8"))
      if prev.get("approved_by_auditor") is True and len(prev.get("settlements", [])) == n_exp:
        is_ok = True
        already_approved.append({
          "approved": True,
          "batch_index": bidx,
          "batch_path": out_p,
          "count": n_exp,
          "errors_remaining": 0,
          "expected": n_exp,
          "rounds": 0,
          "resumed": True,
        })
    except Exception:
      pass
  if not is_ok:
    pending_files.append(bp)

log(f"Resume scan: {len(already_approved)}/{len(all_batch_files)} already approved; running {len(pending_files)} pending batch(es) in waves of {wave_size}")

all_results = list(already_approved)
for w_start in range(0, len(pending_files), wave_size):
  wave = pending_files[w_start : w_start + wave_size]
  w_num = (w_start // wave_size) + 1
  w_tot = (len(pending_files) + wave_size - 1) // wave_size
  phase(f"Resume Wave {w_num}/{w_tot} ({len(wave)} Flash batches + zero-tolerance auditors)")
  w_res = await parallel(wave, process_and_audit_batch)
  all_results.extend(w_res)
  ok_cnt = sum(1 for r in w_res if r.get("approved"))
  err_cnt = sum(r.get("errors_remaining", 0) for r in w_res)
  log(f"Wave {w_num}/{w_tot} done: {ok_cnt}/{len(w_res)} approved, {err_cnt} unresolved error(s).")
  if w_start + wave_size < len(pending_files):
    await asyncio.sleep(5)

all_results.sort(key=lambda r: r.get("batch_index", 0))
total_resolved = sum(r.get("count", 0) for r in all_results)
total_errors = sum(r.get("errors_remaining", 0) for r in all_results)
all_approved = all(r.get("approved", False) for r in all_results) and total_errors == 0

signoff_path = os.path.join(batch_dir, "auditor_signoff.json")
with open(signoff_path, "w", encoding="utf-8") as fh:
  json.dump({
    "approved": all_approved,
    "batches_audited": len(all_results),
    "errors_remaining": total_errors,
    "project": "JAGUAR",
    "results": all_results,
    "total_resolved": total_resolved,
  }, fh, ensure_ascii=False, indent=2)

log(f"JAGUAR Flash swarm complete: {total_resolved} settlements across {len(all_results)} batches; approved={all_approved}, errors_remaining={total_errors}")
{
  "approved": all_approved,
  "batches_audited": len(all_results),
  "errors_remaining": total_errors,
  "total_resolved": total_resolved,
  "failed_batches": [r["batch_index"] for r in all_results if not r.get("approved")],
}
