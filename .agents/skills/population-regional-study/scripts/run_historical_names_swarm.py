"""
Operation Viscount historical toponymy resolution & strict audit workflow (`run_workflow`).

Phase 1: Fans out 25-30-city chunks produced by `extract_missing_city_metadata.js`
across Gemini 3.8 Flash workers (`model="flash"`) armed with the full structural
encoding rulebook (endonymic transliteration, indigenous/pre-colonial endonyms,
municipal-limits non-decomposition, unified capitals, zero comma-inverted articles).

Phase 2: A strictly separate read-only `toponymy_auditor` reviews EVERY resolved
batch against the rulebook. Even a SINGLE historical, endonymic, chronological,
or structural error sends that batch back to the Flash worker with the exact
rejection list (up to `max_audit_rounds=3`) before writing `auditor_signoff.json`.
"""

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
                "name": {"type": "string"},
                "date_source_note": {"type": "string"}
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
  "required": ["approved", "errors"]
}

STRUCTURAL_RULEBOOK = """STRUCTURAL HISTORICAL TOPONYMY ENCODING RULEBOOK (ZERO TOLERANCE):
1. Endonymic Latin Transliteration:
   - Cyrillic/Slavic: national/BGN-PCGN endonymic Latin (`Kyiv`, `Chernihiv`, `Baranavichy`, `Cherepovets`, `Kerch`). ZERO ASCII backtick haceks (`` ` ``).
   - Arabic/Persian: ALA-LC / BGN-PCGN endonymic Latin (`Al-Iskandariyah`, `Al-Qahirah`, `Al-Jazair`). ZERO comma-inverted articles (`Mans, Le` -> `Le Mans`, `Iskandarîyah, Al` -> `Al-Iskandariyah`).
   - Turkic: official modern Latin endonym (`İstanbul`, `Bakı`, `Samarqand`, `Toshkent`/`Tashkent`). ZERO ASCII digraphs (`UE`/`AE`/`OE`).
   - Chinese: Hanyu Pinyin without tone numbers; Japanese: Modified Hepburn; Korean: Revised Romanization; Greek: ELOT 743; Indic: standard endonymic Latin.
2. Indigenous & Pre-Colonial Endonyms (MANDATORY for Americas, Oceania, Africa, Arctic, Greenland, Siberia, Ainu/Ryukyu, Sápmi):
   - Every settlement on pre-colonial/indigenous territory MUST record its attested indigenous endonym before colonial foundation/renaming (e.g. `Nuuk` / `Nûk` -> `Godthåb` `1728.1.1` -> `Nuuk` `1979.5.1`; `Tāmaki Makaurau` -> `Auckland` `1840.9.18`; `Warrane` -> `Sydney` `1788.1.26`; `Utqiaġvik` -> `Barrow` -> `Utqiaġvik` `2016.12.1`; `Qosqo` -> `Cuzco` `1533.11.15`; `Tenochtitlan` -> `Mexico City` `1521.8.13`).
   - NEVER back-project European colonial names into pre-contact centuries.
3. Municipal-Limits Non-Decomposition:
   - NEVER encode intra-municipal wards, arrondissements, boroughs, Stadtbezirke, urban raions, shiyakhas, or `-ku` divisions as standalone settlements; resolve to the parent municipal city. Independent extra-municipal suburbs remain distinct.
4. Capital-City Anchor Guarantee (`is_capital=true`):
   - Capitals MUST have complete, historically verified dynastic/colonial/modern timelines covering every era in which they served as capital, with zero placeholder dates.
5. Chronology & Clean Schema:
   - Dates MUST match `^-?\\d+\\.\\d+\\.\\d+$` (`-10000 <= Y <= 2026`, `Y != 0`, `1 <= M <= 12`, `1 <= D <= 31`).
   - Earliest entry year MUST be `<= earliest_year` (no modern fallback leak into earlier centuries).
   - Extant modern cities (`latest_year >= 1950`) MUST terminate with their documented modern name and true historical rename date (NEVER fabricate generic `1950.1.1` or `1900.1.1`).
   - Collapse spelling/romanisation variants into `other_names` — never create fake historical renames out of spelling variants.
   - ZERO parentheticals `(Russia)`, ZERO street addresses, ZERO `?`, `0`, `Unknown`, `Settlement`, ZERO temples/shrines/monuments or admin suffixes (`-shi`, `Prefecture`, `District`, `Kabupaten`).
"""


def resolve_batch_dir ():
  """Resolves the active `toponymy_batches` directory from `args` or workspace root."""
  svea_root = args.get("svea_root") or (WORKSPACES[0] if WORKSPACES else os.getcwd())
  in_dir = args.get("in_dir")
  if in_dir:
    return os.path.abspath(in_dir)
  slug = str(args.get("slug") or args.get("project") or "polaris").strip().lower()
  return os.path.join(svea_root, "tests", "toponymy_batches", slug)


def build_worker_prompt (batch_idx, batch_items, prior_errors=None):
  """Constructs a deterministic Flash worker prompt with the full rulebook and any auditor rejections."""
  compact_items = []
  for item in batch_items:
    compact_items.append({
      "key": item.get("key"),
      "name": item.get("name"),
      "country": item.get("country"),
      "region": item.get("region"),
      "coords_lat_lng": item.get("coords_lat_lng"),
      "earliest_year": item.get("earliest_year"),
      "latest_year": item.get("latest_year"),
      "max_pop": item.get("max_pop"),
      "is_capital": bool(item.get("is_capital")),
      "is_indigenous_region": bool(item.get("is_indigenous_region")),
      "known_aliases": item.get("known_aliases", [])[:10],
      "existing_meta_name": item.get("existing_meta_name"),
      "existing_historical_names": item.get("existing_historical_names", []),
      "reason": item.get("reason"),
    })

  correction_block = ""
  if prior_errors:
    correction_block = (
      "\nAUDITOR REJECTION — FIX EVERY SINGLE ERROR BELOW BEFORE RETURNING:\n"
      + json.dumps(prior_errors, ensure_ascii=False, indent=2)
      + "\n"
    )

  items_json = json.dumps(compact_items, ensure_ascii=False)
  return f"""Historical Toponymy Worker — Batch {batch_idx}

You are resolving historical settlement names into clean Dataview partitioned `city_metadata/` records.
Do NOT call `run_command`, `read_file`, or inspect local files. Use `search_web` ONLY when verifying uncertain historical rename dates or indigenous endonyms.

{STRUCTURAL_RULEBOOK}
{correction_block}
Return a 1-to-1 entry in `settlements` for EVERY input item and call `finish` with valid schema output.

Input settlements ({len(compact_items)} items):
{items_json}
"""


def build_auditor_prompt (batch_idx, orig_items, resolved_items):
  """Constructs the strictly separate read-only `toponymy_auditor` prompt (zero-tolerance single-error reject)."""
  return f"""Historical Toponymy Auditor (ZERO-TOLERANCE) — Batch {batch_idx}

You are a strictly independent historical toponymy auditor. Do NOT modify files or run commands; you may use `search_web` to spot-check uncertain historical rename dates or pre-colonial indigenous endonyms.

Audit EVERY settlement in `resolved_settlements` against EVERY rule in the rulebook below.
If you find EVEN A SINGLE historical error, anachronistic colonial name, missing pre-colonial indigenous endonym, wrong/fabricated rename date (`1950.1.1`/`1900.1.1`), non-endonymic transliteration, comma-inverted article, backtick hacek, parenthetical, intra-municipal district leak, or missing capital timeline, set `approved: false` and list EVERY offending key with `rule_violated`, `detail`, and `required_fix`.
Approve (`approved: true`, `errors: []`) ONLY when 100% of items are historically and structurally error-free.

{STRUCTURAL_RULEBOOK}

Original input items:
{json.dumps(orig_items, ensure_ascii=False)}

Worker resolved_settlements:
{json.dumps(resolved_items, ensure_ascii=False)}
"""


async def process_and_audit_batch (batch_path):
  """Runs Flash worker + separate read-only `toponymy_auditor` send-back loop on one batch."""
  with open(batch_path, "r", encoding="utf-8") as fh:
    raw = json.load(fh)

  items = raw.get("settlements", [])
  batch_idx = raw.get("batch_index", 1)
  if not items:
    return {"approved": True, "batch_path": batch_path, "count": 0, "errors_remaining": 0, "rounds": 0}

  primary_model = args.get("model", "flash")
  fallback_model = args.get("fallback_model", "inherit")
  auditor_model = args.get("auditor_model", "inherit")
  max_rounds = int(args.get("max_audit_rounds", 3))

  prior_errors = None
  merged_settlements = []
  approved = False
  last_errors = []

  for round_num in range(1, max_rounds + 1):
    w_prompt = build_worker_prompt(batch_idx, items, prior_errors)
    role_label = f"Toponymy Flash batch {batch_idx} r{round_num} ({len(items)} cities)"
    try:
      result = await agent(
        prompt=w_prompt,
        schema=WORKER_SCHEMA,
        role=role_label,
        type_name="self",
        model=primary_model,
      )
    except Exception as primary_err:
      if fallback_model and fallback_model != primary_model:
        log(f"[fallback] Batch {batch_idx} r{round_num} failed on {primary_model!r} ({primary_err}); retrying on {fallback_model!r}")
        result = await agent(
          prompt=w_prompt,
          schema=WORKER_SCHEMA,
          role=f"Toponymy Fallback batch {batch_idx} r{round_num}",
          type_name="self",
          model=fallback_model,
        )
      else:
        raise

    by_key = {str(it.get("key")): it for it in result.get("settlements", []) if it.get("key")}
    merged_settlements = []
    for orig in items:
      k = str(orig.get("key"))
      resolved = by_key.get(k)
      if not resolved:
        continue
      merged = dict(orig)
      merged["canonical_name"] = resolved.get("canonical_name", orig.get("name"))
      merged["historical_names"] = resolved.get("historical_names", [])
      merged["other_names"] = resolved.get("other_names", [])
      merged_settlements.append(merged)

    # Strictly separate read-only toponymy_auditor review
    aud_prompt = build_auditor_prompt(batch_idx, items, merged_settlements)
    aud_res = await agent(
      prompt=aud_prompt,
      schema=AUDITOR_SCHEMA,
      role=f"Toponymy Auditor batch {batch_idx} r{round_num}",
      type_name="research",
      model=auditor_model,
    )
    last_errors = list(aud_res.get("errors") or [])
    approved = bool(aud_res.get("approved")) and len(last_errors) == 0
    if approved:
      break
    log(f"[auditor] Batch {batch_idx} round {round_num} rejected with {len(last_errors)} error(s); sending back to worker.")
    prior_errors = last_errors

  out_dir = os.path.dirname(batch_path)
  out_name = "resolved_" + os.path.basename(batch_path)
  out_path = os.path.join(out_dir, out_name)
  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump({
      "approved_by_auditor": approved,
      "batch_index": batch_idx,
      "count": len(merged_settlements),
      "project": raw.get("project"),
      "settlements": merged_settlements,
    }, fh, ensure_ascii=False, indent=2)

  return {
    "approved": approved,
    "batch_path": out_path,
    "count": len(merged_settlements),
    "errors_remaining": len(last_errors),
    "expected": len(items),
    "rounds": round_num,
  }


phase("Discover batches")
batch_dir = resolve_batch_dir()
if not os.path.isdir(batch_dir):
  raise RuntimeError(f"Batch directory not found: {batch_dir}")

batch_files = sorted(
  os.path.join(batch_dir, f)
  for f in os.listdir(batch_dir)
  if re.match(r"^batch_\d+\.json$", f, re.IGNORECASE)
)
log(f"Found {len(batch_files)} toponymy batch file(s) in {batch_dir}")

phase("Resolve and audit historical names via Flash workers + separate auditor")
results = await parallel(batch_files, process_and_audit_batch)
total_resolved = sum(r.get("count", 0) for r in results)
total_errors = sum(r.get("errors_remaining", 0) for r in results)
all_approved = all(r.get("approved", False) for r in results) and total_errors == 0

signoff_path = os.path.join(batch_dir, "auditor_signoff.json")
with open(signoff_path, "w", encoding="utf-8") as fh:
  json.dump({
    "approved": all_approved,
    "batches_audited": len(results),
    "errors_remaining": total_errors,
    "results": results,
    "total_resolved": total_resolved,
  }, fh, ensure_ascii=False, indent=2)

log(f"Resolved {total_resolved} settlement(s) across {len(results)} batch(es); auditor approved={all_approved}, errors_remaining={total_errors}")
results
