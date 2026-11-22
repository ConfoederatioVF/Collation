"""
Operation Viscount historical toponymy resolution workflow (`run_workflow`).

Fans out fixed-size batches produced by `extract_missing_city_metadata.js`
primarily across Gemini 3.8 Flash agents (`model="flash"`), with automatic
per-batch retry via `fallback_model` (and compatible with native `swarm`
workers pinned to `"gemini-3.8-flash-medium"` -> `"gemini-4-hydrogen-medium"` /
`"gemini-4-hydrogen-high"` fallback when Flash quota/capacity is exhausted),
before `merge_city_metadata.js` commits clean Latin chronological names to
Dataview `data/stadester/stadester_2.0/city_metadata.json`.
"""

import json
import os
import re

SCHEMA = {
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


def resolve_batch_dir():
  """Resolves the active `toponymy_batches` directory from `args` or workspace root."""
  svea_root = args.get("svea_root") or (WORKSPACES[0] if WORKSPACES else os.getcwd())
  in_dir = args.get("in_dir")
  if in_dir:
    return os.path.abspath(in_dir)
  slug = str(args.get("slug") or args.get("project") or "polaris").strip().lower()
  return os.path.join(svea_root, "tests", "toponymy_batches", slug)


def build_prompt(batch_idx, batch_items):
  """Constructs a concise, deterministic Flash prompt for a batch of settlements."""
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
      "known_aliases": item.get("known_aliases", [])[:10],
      "existing_meta_name": item.get("existing_meta_name"),
      "existing_historical_names": item.get("existing_historical_names", []),
      "reason": item.get("reason")
    })

  items_json = json.dumps(compact_items, ensure_ascii=False)
  return f"""Historical Toponymy Batch {batch_idx}

You are resolving historical city and archaeological site names into clean Dataview JSON records.

IMPORTANT WORKFLOW RULES:
- Do NOT call `run_command`, `read_file`, `search_marketplace`, or inspect any local filesystem/git files. Every field you need is already in the JSON array below.
- Verify uncertain historical rename dates via `search_web` rather than guessing or fabricating placeholder years (never invent generic `1950.1.1` or `1900.1.1` dates for documented colonial, dynastic, Soviet or post-independence renames).
- Do NOT waste turns searching obvious ASCII-hacek transliteration fixes (`'Cerepovec -> Cherepovets`, `Ker'c -> Kerch`).

For EVERY settlement in the input array below, return an entry in `settlements` with:
- `key`: exact input `key` string (must match 1-to-1)
- `canonical_name`: cleanest standard modern English/Latin settlement name (NO parenthetical notes, NO backticks `` ` ``, NO `?` or mojibake, NO administrative suffixes like `-shi`, `-gun`, `-ken`, `Prefecture`, `District`, `Kabupaten`, `Amphoe`, and NEVER a temple, shrine, pagoda, monastery, mosque or tomb name)
- `historical_names`: strictly chronological array of `{{"date": "Y.M.D", "name": "Name", "date_source_note": "brief factual basis"}}`:
  - Date format MUST match `^-?\\d+\\.\\d+\\.\\d+$` with valid calendar bounds (`-10000 <= Y <= 2026`, `Y != 0`, `1 <= M <= 12`, `1 <= D <= 31`). Negative years denote BCE.
  - The earliest entry's year MUST be `<= earliest_year` (respecting `foundation_year`) so Dataview never falls back to a later/modern name in earlier centuries.
  - Extant modern cities (`latest_year >= 1950`) MUST terminate with their documented modern restoration/rename date and `canonical_name`.
  - Do NOT create fake historical renames out of spelling/romanisation variants of the same name (e.g. `Samarqand -> Samarkand`, `Bokhara -> Bukhara`); place variant spellings in `other_names` instead.
  - NEVER include parentheticals like `(Russia)`, temple/shrine/monument names, `?`, `'0'`, `'Unknown'`, `'Settlement'`, or backtick `` ` ``.
- `other_names`: optional clean alternate transliterations or native forms (clean Unicode/Latin, zero backticks, zero foreign-script spam in Latin-only countries).

Call `finish` immediately with valid schema output.

Input settlements ({len(compact_items)} items):
{items_json}
"""


async def process_batch(batch_path):
  """Runs one agent (Gemini 3.8 Flash primary with fallback) over a single batch JSON and writes `resolved_<filename>`."""
  with open(batch_path, "r", encoding="utf-8") as fh:
    raw = json.load(fh)

  items = raw.get("settlements", [])
  batch_idx = raw.get("batch_index", 1)
  if not items:
    return {"batch_path": batch_path, "count": 0}

  primary_model = args.get("model", "flash")
  fallback_model = args.get("fallback_model", "inherit")
  prompt_text = build_prompt(batch_idx, items)
  role_label = f"Toponymy Flash batch {batch_idx} ({len(items)} cities)"

  try:
    result = await agent(
      prompt=prompt_text,
      schema=SCHEMA,
      role=role_label,
      type_name="self",
      model=primary_model
    )
  except Exception as primary_err:
    if fallback_model and fallback_model != primary_model:
      log(f"[fallback] Batch {batch_idx} failed on model={primary_model!r} ({primary_err}); retrying on fallback_model={fallback_model!r}")
      result = await agent(
        prompt=prompt_text,
        schema=SCHEMA,
        role=f"Toponymy Fallback batch {batch_idx} ({len(items)} cities)",
        type_name="self",
        model=fallback_model
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

  out_dir = os.path.dirname(batch_path)
  out_name = "resolved_" + os.path.basename(batch_path)
  out_path = os.path.join(out_dir, out_name)
  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump({
      "batch_index": batch_idx,
      "project": raw.get("project"),
      "count": len(merged_settlements),
      "settlements": merged_settlements
    }, fh, ensure_ascii=False, indent=2)

  return {"batch_path": out_path, "count": len(merged_settlements), "expected": len(items)}


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

phase("Resolve historical names via Flash swarm")
results = await parallel(batch_files, process_batch)
total_resolved = sum(r.get("count", 0) for r in results)
log(f"Resolved {total_resolved} settlement(s) across {len(results)} batch(es)")
results
