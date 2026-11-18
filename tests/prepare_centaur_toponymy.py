"""Partition extracted CENTAUR Stage F toponymy batches into deterministic vs scholarly sets."""

import json
import os
import re

BATCH_SIZE = 30
CENTAUR_DIR = os.path.join("tests", "toponymy_batches", "centaur")
SCHOLARLY_DIR = os.path.join("tests", "toponymy_batches", "centaur_scholarly")

SUFFIX_RE = re.compile(
  r"\s+(city|town|village|cdp|borough|municipality|township|site|mound|mounds|pueblo|ruin|ruins|"
  r"parish|subdivision|unorganized|census\s+area|indian\s+reserve|reserve|band|settlement)$",
  re.IGNORECASE,
)
FOREIGN_SCRIPT_RE = re.compile(
  r"[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]"
)
SCHOLARLY_COUNTRIES = {
  "Greenland", "Alaska", "Hawaii", "American Samoa", "Bermuda", "Saint Pierre and Miquelon"
}


def strip_parenthetical(text):
  return re.sub(r"\s*\([^)]*\)", "", str(text or "")).strip()


def is_clean_name(text):
  s = str(text or "").strip()
  if not s or s in {"0", "Unknown", "Settlement"}:
    return False
  if re.fullmatch(r"[?\s\-_.,]+", s):
    return False
  if "?" in s or "\ufffd" in s or "`" in s:
    return False
  return True


def clean_aliases(raw_aliases, canonical_name):
  """Strip parentheticals, IATA codes, foreign-script noise and pure lowercase self-duplicates."""
  canon_low = canonical_name.lower()
  out = []
  seen_lower = {canon_low}
  for a in (raw_aliases or []):
    s = strip_parenthetical(a)
    if not is_clean_name(s):
      continue
    if FOREIGN_SCRIPT_RE.search(s) or re.match(r"^Ist\s+Pitc", s, re.IGNORECASE):
      continue
    # Filter 2-3 char lowercase IATA airport / stub codes unless exact match to name
    if len(s) <= 3 and s.islower():
      continue
    sl = s.lower()
    if sl in seen_lower:
      continue
    seen_lower.add(sl)
    out.append(s)
  return out


def has_distinct_alias(item, cleaned_aliases):
  canon_low = strip_parenthetical(item.get("name", "")).lower()
  canon_stem = SUFFIX_RE.sub("", canon_low).strip()
  for al in cleaned_aliases:
    al_stem = SUFFIX_RE.sub("", al.lower()).strip()
    if al_stem and al_stem != canon_stem and al_stem not in canon_stem and canon_stem not in al_stem:
      return True
  return False


def main():
  items = []
  for fname in sorted(os.listdir(CENTAUR_DIR)):
    if re.match(r"^batch_\d+\.json$", fname, re.IGNORECASE):
      with open(os.path.join(CENTAUR_DIR, fname), "r", encoding="utf-8") as fh:
        items.extend(json.load(fh).get("settlements", []))

  # Clear stale resolved/scholarly files first
  for fname in os.listdir(CENTAUR_DIR):
    if re.match(r"^resolved_batch_\d+\.json$", fname, re.IGNORECASE):
      os.remove(os.path.join(CENTAUR_DIR, fname))
  if os.path.isdir(SCHOLARLY_DIR):
    for fname in os.listdir(SCHOLARLY_DIR):
      if fname.endswith(".json"):
        os.remove(os.path.join(SCHOLARLY_DIR, fname))
  os.makedirs(SCHOLARLY_DIR, exist_ok=True)

  det_items = []
  sch_items = []
  for it in items:
    canon = strip_parenthetical(it.get("name", ""))
    cleaned = clean_aliases(it.get("known_aliases", []), canon)
    ey = it.get("earliest_year")
    is_sch = (
      it.get("reason") != "missing_entry"
      or str(it.get("country", "")) in SCHOLARLY_COUNTRIES
      or (ey is not None and int(ey) < 1750)
      or has_distinct_alias(it, cleaned)
    )
    if is_sch:
      sch_items.append(it)
    else:
      start_yr = int(ey) if ey is not None else -1000
      rec = dict(it)
      rec["canonical_name"] = canon
      rec["historical_names"] = [{"date": f"{start_yr}.1.1", "name": canon}]
      rec["other_names"] = cleaned
      rec["known_aliases"] = [canon] + cleaned
      det_items.append(rec)

  # Write deterministic batches as resolved_batch_0001..0NNN.json
  det_files = 0
  for i in range(0, len(det_items), BATCH_SIZE):
    idx = (i // BATCH_SIZE) + 1
    chunk = det_items[i:i + BATCH_SIZE]
    out_p = os.path.join(CENTAUR_DIR, f"resolved_batch_{idx:04d}.json")
    with open(out_p, "w", encoding="utf-8") as fh:
      json.dump({
        "batch_index": idx,
        "project": "CENTAUR",
        "count": len(chunk),
        "settlements": chunk,
      }, fh, ensure_ascii=False, indent=2)
    det_files += 1

  # Write scholarly batches as batch_0001..0NNN.json in SCHOLARLY_DIR
  sch_files = 0
  for i in range(0, len(sch_items), BATCH_SIZE):
    idx = (i // BATCH_SIZE) + 1
    chunk = sch_items[i:i + BATCH_SIZE]
    out_p = os.path.join(SCHOLARLY_DIR, f"batch_{idx:04d}.json")
    with open(out_p, "w", encoding="utf-8") as fh:
      json.dump({
        "batch_index": idx,
        "project": "CENTAUR",
        "count": len(chunk),
        "settlements": chunk,
      }, fh, ensure_ascii=False, indent=2)
    sch_files += 1

  print(
    f"Prepared {len(items)} total items -> "
    f"{len(det_items)} deterministic ({det_files} resolved files) + "
    f"{len(sch_items)} scholarly ({sch_files} batch files in {SCHOLARLY_DIR})."
  )


if __name__ == "__main__":
  main()
