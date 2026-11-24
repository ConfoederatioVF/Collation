import json
import re
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)

with open("tests/fetch_toponymy.py", "r", encoding="utf-8") as f:
    src = f.read()

# Extract SETTLEMENTS
m = re.search(r"SETTLEMENTS\s*=\s*(\[.*?\])\n\ndef ", src, re.S)
inp = json.loads(m.group(1))
inp_keys = [s["key"] for s in inp]
inp_map = {s["key"]: s for s in inp}

out_list = data["settlements"]
out_keys = [s["key"] for s in out_list]

assert len(out_list) == 90, f"Expected 90, got {len(out_list)}"
assert set(out_keys) == set(inp_keys), f"Key mismatch: missing={set(inp_keys)-set(out_keys)}, extra={set(out_keys)-set(inp_keys)}"

DATE_RE = re.compile(r"^(-?\d+)\.(\d+)\.(\d+)$")
BAD_SCRIPT_RE = re.compile(r"[\u0400-\u04FF\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")
PAREN_RE = re.compile(r"\([^)]*\)")

errors = []
for s in out_list:
    k = s["key"]
    cn = s["canonical_name"]
    hn = s["historical_names"]
    if not cn or PAREN_RE.search(cn) or BAD_SCRIPT_RE.search(cn):
        errors.append(f"{k}: bad canonical_name={cn!r}")
    if not hn:
        errors.append(f"{k}: empty historical_names")
        continue
    prev_tuple = None
    prev_name = None
    for idx, h in enumerate(hn):
        d = h["date"]
        nm = h["name"]
        note = h["date_source_note"]
        dm = DATE_RE.match(d)
        if not dm:
            errors.append(f"{k}[{idx}]: bad date format {d!r}")
            continue
        y, mo, da = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
        if y == 0 or y < -10000 or y > 2026 or not (1 <= mo <= 12) or not (1 <= da <= 31):
            errors.append(f"{k}[{idx}]: invalid calendar date {d!r}")
        cur_tuple = (y, mo, da)
        if prev_tuple is not None and cur_tuple <= prev_tuple:
            errors.append(f"{k}[{idx}]: non-ascending date {prev_tuple} -> {cur_tuple}")
        prev_tuple = cur_tuple
        if not nm or PAREN_RE.search(nm) or BAD_SCRIPT_RE.search(nm):
            errors.append(f"{k}[{idx}]: bad name {nm!r}")
        if prev_name is not None and nm.strip().lower() == prev_name.strip().lower():
            errors.append(f"{k}[{idx}]: repeated consecutive name {nm!r}")
        prev_name = nm
        wc = len(note.strip().split())
        if wc == 0 or wc > 8:
            errors.append(f"{k}[{idx}]: note word count {wc} ({note!r})")
    # Check earliest year <= ey (allowing ey==0 -> y<=-1)
    ey = inp_map[k]["ey"]
    y0 = int(DATE_RE.match(hn[0]["date"]).group(1))
    if y0 > ey:
        errors.append(f"{k}: earliest date {y0} > ey {ey}")

if errors:
    print("VALIDATION ERRORS:")
    for e in errors:
        print(" ", e)
    sys.exit(1)
else:
    print("ALL 90 SETTLEMENTS PASSED VALIDATION!")
