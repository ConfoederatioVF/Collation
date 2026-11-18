"""
CENTAUR-II Stage F Scholarly Toponymy Resolution Workflow (`run_workflow`).

Executes batched Gemini 3.8 Flash agents in waves of 25 concurrent batches
(with per-batch exception isolation and in-workflow `fallback_model` retry)
over `tests/toponymy_batches/centaur_scholarly/batch_*.json`, writing
`resolved_batch_1XXX.json` outputs for `merge_city_metadata.js`.
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

FOREIGN_SCRIPT_RE = re.compile(
  r"[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]"
)
DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")


def strip_parenthetical(text):
  return re.sub(r"\s*\([^)]*\)", "", str(text or "")).strip()


def clean_aliases(raw_aliases, canonical_name):
  canon_low = canonical_name.lower()
  out = []
  seen_lower = {canon_low}
  for a in (raw_aliases or []):
    s = strip_parenthetical(a)
    if not s or s in {"0", "Unknown", "Settlement"} or "?" in s or "\ufffd" in s or "`" in s:
      continue
    if FOREIGN_SCRIPT_RE.search(s) or re.match(r"^Ist\s+Pitc", s, re.IGNORECASE):
      continue
    if len(s) <= 3 and s.islower():
      continue
    sl = s.lower()
    if sl in seen_lower:
      continue
    seen_lower.add(sl)
    out.append(s)
  return out


def build_prompt(batch_idx, batch_items):
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
      "known_aliases": [
        a for a in (item.get("known_aliases") or [])[:12]
        if not (len(str(a).strip()) <= 3 and str(a).strip().islower())
      ],
      "existing_meta_name": item.get("existing_meta_name"),
      "existing_historical_names": item.get("existing_historical_names", []),
      "reason": item.get("reason")
    })

  items_json = json.dumps(compact_items, ensure_ascii=False)
  return f"""CENTAUR-II Historical Toponymy Batch {batch_idx} (North America, Greenland, Bermuda, Hawaii & American Samoa)

You are resolving historical city, mission, fur-trade, Indigenous, and archaeological site names into clean Dataview JSON records.

IMPORTANT WORKFLOW RULES:
- Do NOT call `run_command`, `read_file`, `search_marketplace`, or inspect local filesystem/git files. Every field you need is already in the JSON array below.
- Call `finish` in ONE turn (use `search_web` at most once ONLY if truly ambiguous, otherwise use authoritative scholarly toponymy directly).

SCHEMA & CONTENT RULES FOR EVERY INPUT SETTLEMENT:
1. `key`: exact input `key` string (1-to-1 match; return ALL {len(compact_items)} items).
2. `canonical_name`: cleanest standard modern English/Latin/official Indigenous name (for `existing_meta_name`, preserve the primary settlement's clean modern name—do NOT rename a primary modern city after a merged minor suburb or annex). Strip ALL parenthetical notes like `(QC)` or `(AB)`, NO backticks `` ` ``, NO `?` or `\ufffd`.
3. `historical_names`: chronological array of `{{"date": "Y.M.D", "name": "Name"}}`:
   - `date` MUST match regex `^-?\\d+\\.\\d+\\.\\d+$` (e.g. `"-500.1.1"`, `"1749.6.21"`, `"1979.5.1"`). Negative years denote BCE.
   - Include documented Indigenous/pre-colonial, colonial (French, Spanish, British, Dutch, Russian-American, Danish), and modern name transitions from `known_aliases` or authoritative knowledge (e.g., `Kjipuktuk -> Halifax`, `Godthåb -> Nuuk (1979.5.1)`, `Jakobshavn -> Ilulissat`, `Pointe-Bleue -> Mashteuiatsh (1985.1.1)`, `Port Simpson -> Lax Kw'alaams (1986.1.1)`, `Friendly Cove -> Yuquot`, `Barrow -> Utqiaġvik (2016.12.1)`).
   - TERMINAL MODERN ANCHOR: Whenever `latest_year >= 1950`, the final entry MUST have a `>= 1950` date (or match the historical transition date) and its `name` MUST equal `canonical_name`. Do NOT end a modern city on a defunct pre-1920 annex or colonial name.
   - If a settlement or archaeological site has only one attested name across its period, output one entry with `date` `<= earliest_year` (e.g. `f"{{earliest_year or -1000}}.1.1"`) and `name` = `canonical_name`.
   - NEVER include parentheticals `(...)`, `?`, `'0'`, `'Unknown'`, `'Settlement'`, or backtick `` ` ``.
4. `other_names`: alternate spellings, native forms, or historical aliases in clean Latin/Indigenous script (strip parentheticals, drop 2-3 letter lowercase IATA codes, and zero Cyrillic/CJK/Arabic/Indic noise).

Call `finish` immediately with valid schema output containing all {len(compact_items)} settlements.

Input settlements ({len(compact_items)} items):
{items_json}
"""


async def process_batch(batch_path):
  with open(batch_path, "r", encoding="utf-8") as fh:
    raw = json.load(fh)

  items = raw.get("settlements", [])
  batch_idx = int(raw.get("batch_index", 1))
  if not items:
    return {"batch_path": batch_path, "count": 0, "expected": 0}

  out_dir = os.path.dirname(batch_path)
  out_name = f"resolved_batch_{1000 + batch_idx:04d}.json"
  out_path = os.path.join(out_dir, out_name)

  primary_model = args.get("model", "flash")
  fallback_model = args.get("fallback_model", "inherit")
  prompt_text = build_prompt(batch_idx, items)

  result = None
  try:
    try:
      result = await agent(
        prompt=prompt_text,
        schema=SCHEMA,
        role=f"CENTAUR Toponymy Flash {batch_idx} ({len(items)})",
        type_name="self",
        model=primary_model,
      )
    except Exception as primary_err:
      log(f"[fallback] Batch {batch_idx} failed on {primary_model!r}: {primary_err}")
      result = await agent(
        prompt=prompt_text,
        schema=SCHEMA,
        role=f"CENTAUR Toponymy Retry {batch_idx} ({len(items)})",
        type_name="self",
        model=fallback_model,
      )
  except Exception as fatal_err:
    log(f"[ERROR] Batch {batch_idx} failed both attempts: {fatal_err}")
    return {"batch_path": batch_path, "count": 0, "expected": len(items), "error": str(fatal_err)}

  by_key = {str(it.get("key")): it for it in result.get("settlements", []) if it.get("key")}
  merged_settlements = []
  for orig in items:
    k = str(orig.get("key"))
    resolved = by_key.get(k)
    if not resolved:
      continue
    canon = strip_parenthetical(resolved.get("canonical_name") or orig.get("name") or k)
    if not canon:
      canon = strip_parenthetical(orig.get("name") or k)
    hist_clean = []
    for h in (resolved.get("historical_names") or []):
      if not isinstance(h, dict):
        continue
      hd = str(h.get("date") or "").strip()
      hn = strip_parenthetical(h.get("name") or "")
      if DATE_RE.match(hd) and hn and "?" not in hn and "\ufffd" not in hn and "`" not in hn:
        hist_clean.append({"date": hd, "name": hn})
    if not hist_clean:
      ey = orig.get("earliest_year")
      sy = int(ey) if ey is not None else -1000
      hist_clean = [{"date": f"{sy}.1.1", "name": canon}]

    merged = dict(orig)
    merged["canonical_name"] = canon
    merged["historical_names"] = hist_clean
    cleaned_other = clean_aliases(resolved.get("other_names", []), canon)
    merged["other_names"] = cleaned_other
    merged["known_aliases"] = clean_aliases(orig.get("known_aliases", []), canon)
    merged_settlements.append(merged)

  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump({
      "batch_index": 1000 + batch_idx,
      "project": raw.get("project"),
      "count": len(merged_settlements),
      "settlements": merged_settlements,
    }, fh, ensure_ascii=False, indent=2)

  return {"batch_path": out_path, "count": len(merged_settlements), "expected": len(items)}


phase("Discover scholarly CENTAUR batches")
in_dir = os.path.abspath(args.get("in_dir") or os.path.join("tests", "toponymy_batches", "centaur_scholarly"))
batch_files = sorted(
  os.path.join(in_dir, f)
  for f in os.listdir(in_dir)
  if re.match(r"^batch_\d+\.json$", f, re.IGNORECASE)
)
log(f"Found {len(batch_files)} scholarly batch(es) in {in_dir}")

WAVE_SIZE = int(args.get("wave_size", 25))
all_results = []
for start in range(0, len(batch_files), WAVE_SIZE):
  wave_idx = (start // WAVE_SIZE) + 1
  wave_files = batch_files[start:start + WAVE_SIZE]
  phase(f"Resolve wave {wave_idx} ({len(wave_files)} batches)")
  wave_res = await parallel(wave_files, process_batch)
  all_results.extend(wave_res)
  log(f"Wave {wave_idx} complete: {sum(r.get('count', 0) for r in wave_res)}/{sum(r.get('expected', 0) for r in wave_res)} resolved.")

total_res = sum(r.get("count", 0) for r in all_results)
total_exp = sum(r.get("expected", 0) for r in all_results)
log(f"Total scholarly settlements resolved: {total_res}/{total_exp}")
{"resolved": total_res, "expected": total_exp, "results": all_results}
