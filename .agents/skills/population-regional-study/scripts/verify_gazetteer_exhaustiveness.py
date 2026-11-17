"""Gatekeeper A: Verifies exhaustive settlement inclusion (no artificial 120/200 caps)
and validates settlement gazetteer integrity (`_settlements.json` + `_source_ledger.json5`).
"""

import argparse
import json
import os
import re
import sys

try:
  import json5
except ImportError:
  json5 = None


CANONICAL_VISCOUNT_PROJECTS = {
  "CENTAUR",
  "POLARIS",
  "PRETA",
  "JADE",
  "INDUS",
  "CASTLE",
  "MANDALA",
  "SARAY",
  "HANDBOOK",
  "MAGNETIC",
  "QUIPU",
  "JAGUAR",
  "AUSTRAL",
  "NICETHI",
}

VALID_EXCLUDE_REASONS = {
  "outside_study_bounds",
  "subordinate_suburb_merged",
  "unlocated_historical_toponym",
  "duplicate_alias",
  "seasonal_encampment_unquantified",
  "superseded_by_higher_priority_tier",
}


def load_json_or_json5(arg0_path):
  """Loads JSON via stdlib first, falling back to json5 or comment-stripped JSON."""
  with open(arg0_path, "r", encoding="utf-8") as fh:
    text = fh.read()
  try:
    return json.loads(text)
  except (json.JSONDecodeError, ValueError):
    if json5 is not None:
      return json5.loads(text)
    stripped = re.sub(r"//.*?$|/\*.*?\*/", "", text, flags=re.MULTILINE | re.DOTALL)
    stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
    return json.loads(stripped)


def is_corrupt_name(arg0_name, arg1_allow_backtick=False):
  """Mirrors Dataview city name validation rules, optionally allowing legacy backtick carons."""
  if not isinstance(arg0_name, str):
    return True
  s = arg0_name.strip()
  if not s or s in {"0", "Unknown", "Settlement"}:
    return True
  if re.match(r"^[?\s\-_.,]+$", s):
    return True
  forbidden = ("?", "\ufffd", "\u00ef\u00bf\u00bd") if arg1_allow_backtick else ("?", "\ufffd", "\u00ef\u00bf\u00bd", "`")
  if any(ch in s for ch in forbidden):
    return True
  return False


def resolve_audit_mode(arg0_settlements_path, arg1_mode=None, arg2_require_sources=False):
  """Resolves whether validation enforces regional literature-review rules or compiled Stadestér rules."""
  if arg1_mode in ("regional", "compiled"):
    return arg1_mode
  norm_path = str(arg0_settlements_path or "").replace("\\", "/").lower()
  if "population_regional" in norm_path:
    return "regional"
  if arg2_require_sources:
    return "compiled"
  return "compiled"


def validate_city_sources(arg0_city, arg1_ckey, arg2_idx, arg3_mode, arg4_require_sources):
  """Validates `.sources` array schema and rejects legacy `.type` or disallowed source identifiers."""
  has_legacy_type = "type" in arg0_city
  missing_sources = False
  source_error = None

  if "sources" not in arg0_city:
    if arg4_require_sources:
      missing_sources = True
    return has_legacy_type, missing_sources, source_error

  sources = arg0_city.get("sources")
  if not isinstance(sources, list) or len(sources) == 0:
    source_error = f"Settlement {arg1_ckey!r} (index {arg2_idx}) has invalid 'sources': expected a non-empty list, got {sources!r}."
    return has_legacy_type, missing_sources, source_error

  seen = set()
  for item in sources:
    if not isinstance(item, str) or not item.strip():
      source_error = f"Settlement {arg1_ckey!r} (index {arg2_idx}) has invalid non-empty string entry in 'sources': {item!r}."
      break
    if item.strip().lower() == "viscount_regional":
      source_error = f"Settlement {arg1_ckey!r} (index {arg2_idx}) uses forbidden source tag 'viscount_regional'; cite canonical Viscount project name instead."
      break
    if item in seen:
      source_error = f"Settlement {arg1_ckey!r} (index {arg2_idx}) has duplicate entry {item!r} in 'sources'."
      break
    seen.add(item)
    if arg3_mode == "regional" and item not in CANONICAL_VISCOUNT_PROJECTS:
      source_error = (
        f"Regional settlement {arg1_ckey!r} (index {arg2_idx}) has non-project source {item!r}; "
        "regional _settlements.json .sources must cite only canonical Viscount project names."
      )
      break

  return has_legacy_type, missing_sources, source_error


def audit_settlements(arg0_settlements_path, arg1_ledger_path=None, arg2_require_sources=False, arg3_mode=None):
  """Validates a chapter's `_settlements.json` (or compiled Stadestér 2.0 shard) and optional `_source_ledger.json5`."""
  errors = []
  warnings = []
  resolved_mode = resolve_audit_mode(arg0_settlements_path, arg3_mode, arg2_require_sources)

  if not os.path.isfile(arg0_settlements_path):
    errors.append(f"Settlements file not found: {arg0_settlements_path}")
    return errors, warnings, {}

  data = load_json_or_json5(arg0_settlements_path)
  if isinstance(data, dict):
    entries = [{"key": k, **v} for k, v in data.items() if isinstance(v, dict)]
  elif isinstance(data, list):
    entries = [x for x in data if isinstance(x, dict)]
  else:
    errors.append(f"Unsupported top-level settlements structure in {arg0_settlements_path}")
    return errors, warnings, {}

  count = len(entries)
  if count == 0:
    errors.append("Settlement gazetteer is empty (0 settlements).")

  by_key = {}
  bad_coords = 0
  corrupt_names = 0
  zero_pop_cities = 0
  legacy_type_cities = 0
  missing_sources_cities = 0
  invalid_sources_cities = 0

  for idx, city in enumerate(entries):
    cname = city.get("name") or city.get("key") or f"entry_{idx}"
    ckey = str(city.get("key") or cname)
    by_key[ckey] = city

    if is_corrupt_name(str(cname), arg1_allow_backtick=(resolved_mode == "compiled")):
      corrupt_names += 1
      if corrupt_names <= 5:
        errors.append(f"Corrupted city name detected at index {idx}: {cname!r}")

    has_legacy_type, missing_sources, source_error = validate_city_sources(
      city, ckey, idx, resolved_mode, arg2_require_sources
    )
    if has_legacy_type:
      legacy_type_cities += 1
      if legacy_type_cities <= 5:
        errors.append(f"Legacy 'type' key detected on settlement {ckey!r} at index {idx}; replace with 'sources' list.")
    if missing_sources:
      missing_sources_cities += 1
      if missing_sources_cities <= 5:
        errors.append(f"Missing required 'sources' list on settlement {ckey!r} at index {idx}.")
    if source_error:
      invalid_sources_cities += 1
      if invalid_sources_cities <= 5:
        errors.append(source_error)

    coords = city.get("coords")
    if not isinstance(coords, list) or len(coords) < 2:
      bad_coords += 1
    else:
      try:
        lat = float(coords[0])
        lng = float(coords[1])
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
          bad_coords += 1
      except (TypeError, ValueError):
        bad_coords += 1

    pop = city.get("population")
    if not isinstance(pop, dict) or len(pop) == 0:
      zero_pop_cities += 1

  if bad_coords > 0:
    errors.append(f"{bad_coords} settlement(s) have missing or out-of-range coordinates.")
  if corrupt_names > 5:
    errors.append(f"Total corrupted city names: {corrupt_names}")
  if legacy_type_cities > 5:
    errors.append(f"Total settlements with legacy 'type' key: {legacy_type_cities}")
  if missing_sources_cities > 5:
    errors.append(f"Total settlements missing required 'sources' list: {missing_sources_cities}")
  if invalid_sources_cities > 5:
    errors.append(f"Total settlements with invalid 'sources' list: {invalid_sources_cities}")
  if zero_pop_cities > 0:
    if resolved_mode == "compiled":
      warnings.append(f"{zero_pop_cities} settlement(s) lack population year observations.")
    else:
      errors.append(f"{zero_pop_cities} settlement(s) lack population year observations.")

  ledger_stats = {"total_candidates": 0, "included": 0, "excluded": 0, "unaccounted": 0}
  if arg1_ledger_path:
    if not os.path.isfile(arg1_ledger_path):
      errors.append(f"Required source ledger missing: {arg1_ledger_path}")
    else:
      ledger = load_json_or_json5(arg1_ledger_path)
      candidates = ledger.get("candidates", []) if isinstance(ledger, dict) else ledger
      if not isinstance(candidates, list) or len(candidates) == 0:
        errors.append(f"Source ledger has no candidate entries: {arg1_ledger_path}")
      else:
        ledger_stats["total_candidates"] = len(candidates)
        for cand in candidates:
          status = str(cand.get("status", "")).strip().lower()
          ckey = str(cand.get("settlement_key") or cand.get("key") or cand.get("name") or "")
          if status == "included":
            ledger_stats["included"] += 1
            if ckey not in by_key and not any(
              str(e.get("name", "")).strip().lower() == str(cand.get("name", "")).strip().lower()
              for e in entries
            ):
              errors.append(f"Ledger marks {ckey!r} as included, but it is absent from {os.path.basename(arg0_settlements_path)}.")
          elif status == "excluded":
            ledger_stats["excluded"] += 1
            reason = str(cand.get("reason", "")).strip()
            justif = str(cand.get("justification", "")).strip()
            if reason not in VALID_EXCLUDE_REASONS or len(justif) < 8:
              errors.append(f"Excluded candidate {ckey!r} lacks a valid reason ({VALID_EXCLUDE_REASONS}) or justification.")
          else:
            ledger_stats["unaccounted"] += 1
            errors.append(f"Candidate {ckey!r} in ledger has invalid or pending status: {status!r}")
  elif count in {100, 120, 150, 200, 250} and resolved_mode != "compiled":
    errors.append(
      f"Settlement count ({count}) lands on a round quota cap without a verified _source_ledger.json5."
    )
  else:
    warnings.append("No --ledger supplied; verified structural validity only.")

  stats = {
    "settlements_count": count,
    "bad_coords": bad_coords,
    "corrupt_names": corrupt_names,
    "zero_pop_cities": zero_pop_cities,
    "legacy_type_cities": legacy_type_cities,
    "missing_sources_cities": missing_sources_cities,
    "invalid_sources_cities": invalid_sources_cities,
    "mode": resolved_mode,
    **ledger_stats,
  }
  return errors, warnings, stats


def main():
  parser = argparse.ArgumentParser(description="Verify exhaustive Viscount settlement gazetteer inclusion.")
  parser.add_argument("settlements", help="Path to *_settlements.json, POLARIS chapter JSON or compiled Stadestér 2.0 shard")
  parser.add_argument("--ledger", default=None, help="Path to *_source_ledger.json5")
  parser.add_argument(
    "--require-sources",
    action="store_true",
    help="Require a non-empty 'sources' array on every settlement (for compiled Stadestér 2.0 shards)."
  )
  parser.add_argument(
    "--mode",
    choices=["regional", "compiled"],
    default=None,
    help="Validation mode ('regional' restricts .sources to canonical Viscount project names; auto-detected if omitted)."
  )
  parsed = parser.parse_args()

  errors, warnings, stats = audit_settlements(
    parsed.settlements,
    parsed.ledger,
    parsed.require_sources,
    parsed.mode
  )
  for w in warnings:
    print(f"[WARN] {w}")
  for e in errors:
    print(f"[FAIL] {e}", file=sys.stderr)

  print(f"[verify_gazetteer_exhaustiveness] Summary: {json.dumps(stats)}")
  sys.exit(1 if errors else 0)


if __name__ == "__main__":
  main()
