"""
Operation Viscount historical toponymy resolution workflow (`run_workflow`).

Fanns out fixed-size batches produced by `extract_missing_city_metadata.js`
across Gemini Flash agents (`model="flash"`) to reconstruct chronological Latin-script
`historical_names` trajectories and clean corrupted ASCII-hacek/mojibake names
before `merge_city_metadata.js` commits them to Dataview `city_metadata.json`.
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
- Do NOT do exhaustive per-city web searches when fixing obvious ASCII-hacek transliterations (`'Cerepovec -> Cherepovets`, `` `Cerkasy -> Cherkasy ``, `Ker`c -> Kerch`, `D`'zokar -> Dzhokhar`, `Rubi`zne -> Rubizhne`, etc.) or adding well-known major historical renames (e.g. Tsaritsyn/Stalingrad/Volgograd, Yekaterinburg/Sverdlovsk, Königsberg/Kaliningrad, Khlynov/Vyatka/Kirov).
- Use `search_web` AT MOST once or twice ONLY if an entry is `reason == "missing_entry"` and genuinely unfamiliar, then immediately call `finish` in ONE or TWO turns.

For EVERY settlement in the input array below, return an entry in `settlements` with:
- `key`: exact input `key` string (must match 1-to-1)
- `canonical_name`: cleanest standard modern English/Latin name (NO parenthetical notes, NO backticks `` ` ``, NO apostrophe-backtick artifacts like `` `' `` or `?` or mojibake)
- `historical_names`: chronological array of `{{"date": "Y.M.D", "name": "Name"}}`:
  - Date format MUST match regex `^-?\\d+\\.\\d+\\.\\d+$` (e.g. `"-1000.1.1"`, `"1147.1.1"`, `"1589.1.1"`, `"1925.4.10"`). Negative years denote BCE.
  - Preserve valid existing historical transitions if already accurate, fix any corrupted ASCII-hacek strings, and add documented pre-modern, imperial, Soviet, or modern official renames in clean standard Latin script.
  - If an item is an archaeological site or minor settlement with one attested name across its period, provide an initial date <= its `earliest_year` (e.g. `f"{{earliest_year}}.1.1"` or `"-1000.1.1"`) and `"name"`.
  - NEVER include parentheticals like `(Russia)` inside any name, NEVER include `?`, `'0'`, `'Unknown'`, `'Settlement'`, or backtick `` ` ``.
- `other_names`: optional clean alternate transliterations or native forms (clean Unicode/Latin, zero backticks or `?`).

Call `finish` immediately with valid schema output.

Input settlements ({len(compact_items)} items):
{items_json}
"""


async def process_batch(batch_path):
  """Runs one Flash agent over a single batch JSON and writes `resolved_<filename>`."""
  with open(batch_path, "r", encoding="utf-8") as fh:
    raw = json.load(fh)

  items = raw.get("settlements", [])
  batch_idx = raw.get("batch_index", 1)
  if not items:
    return {"batch_path": batch_path, "count": 0}

  result = await agent(
    prompt=build_prompt(batch_idx, items),
    schema=SCHEMA,
    role=f"Toponymy Flash batch {batch_idx} ({len(items)} cities)",
    type_name="self",
    model=args.get("model", "flash")
  )

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
