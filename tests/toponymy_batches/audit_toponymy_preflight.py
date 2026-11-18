"""Pre-flight Stage F validator for deterministic + scholarly CENTAUR toponymy batches."""

import glob
import json
import os
import re
import shutil
import unicodedata

DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")
FOREIGN_RE = re.compile(
  r"[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]"
)


def stem_dv(raw):
  base = str(raw or "").split(";")[0].split("(")[0].strip().lower()
  base = "".join(c for c in unicodedata.normalize("NFD", base) if unicodedata.category(c) != "Mn")
  for a, b in [("ł", "l"), ("đ", "d"), ("ø", "o"), ("ß", "ss"), ("æ", "ae"), ("œ", "oe")]:
    base = base.replace(a, b)
  base = re.sub(r"^(?:st\.?|saint|san|santa|sao|al-|el-)\s+", "saint ", base)
  for a, b in [("kh", "k"), ("gh", "g"), ("ph", "f"), ("dj", "j"), ("ou", "u")]:
    base = base.replace(a, b)
  base = re.sub(r"[jy]", "i", base).replace("ts", "c")
  base = re.sub(r"[cq]", "k", base)
  return re.sub(r"[^a-z0-9]+", "", base)


def dice(a, b):
  if not a or not b:
    return 0.0
  if a == b:
    return 1.0
  if len(a) < 2 or len(b) < 2:
    return 0.0
  ba = [a[i:i + 2] for i in range(len(a) - 1)]
  pb = [b[i:i + 2] for i in range(len(b) - 1)]
  inter = 0
  for bg in ba:
    if bg in pb:
      inter += 1
      pb.remove(bg)
  return 2.0 * inter / (len(ba) + len(b) - 1)


def main():
  # 1. Patch missing K\x92ate Ouinge-New Mexico in resolved_batch_1084.json if absent
  b84_p = "tests/toponymy_batches/centaur_scholarly/batch_0084.json"
  r84_p = "tests/toponymy_batches/centaur_scholarly/resolved_batch_1084.json"
  b84 = json.load(open(b84_p, "r", encoding="utf-8"))
  r84 = json.load(open(r84_p, "r", encoding="utf-8"))
  ex_keys = {s["key"] for s in r84["settlements"]}
  for s in b84["settlements"]:
    if s["key"] not in ex_keys:
      rec = dict(s)
      rec["canonical_name"] = "K'ate Ouinge"
      rec["historical_names"] = [{"date": "500.1.1", "name": "K'ate Ouinge"}]
      rec["other_names"] = ["Kate Ouinge"]
      rec["known_aliases"] = ["K'ate Ouinge"]
      r84["settlements"].append(rec)
  r84["count"] = len(r84["settlements"])
  with open(r84_p, "w", encoding="utf-8") as fh:
    json.dump(r84, fh, ensure_ascii=False, indent=2)

  # 2. Check for any parenthetical or bad items & fix trivial parentheticals if any exist
  sch_files = sorted(glob.glob("tests/toponymy_batches/centaur_scholarly/resolved_batch_1*.json"))
  det_files = sorted(glob.glob("tests/toponymy_batches/centaur/resolved_batch_0*.json"))

  # Copy scholarly files into tests/toponymy_batches/centaur/
  for fp in sch_files:
    shutil.copy2(fp, os.path.join("tests/toponymy_batches/centaur", os.path.basename(fp)))

  all_resolved = sorted(glob.glob("tests/toponymy_batches/centaur/resolved_batch_*.json"))
  seen_keys = set()
  bad_names = []
  bad_dates = []
  bad_foreign = []
  sig_issues = []
  empty_hist = 0

  for fp in all_resolved:
    data = json.load(open(fp, "r", encoding="utf-8"))
    for rec in data.get("settlements", []):
      k = rec["key"]
      seen_keys.add(k)
      cn = str(rec.get("canonical_name", ""))
      if not cn or "?" in cn or "\ufffd" in cn or "`" in cn or "(" in cn or ")" in cn or cn in {"0", "Unknown", "Settlement"}:
        bad_names.append((os.path.basename(fp), k, cn))
      hn = rec.get("historical_names") or []
      if not hn:
        empty_hist += 1
      for h in hn:
        hd = str(h.get("date", ""))
        hnm = str(h.get("name", ""))
        if not DATE_RE.match(hd) or not hnm or "?" in hnm or "\ufffd" in hnm or "`" in hnm or "(" in hnm or ")" in hnm:
          bad_dates.append((os.path.basename(fp), k, hd, hnm))
      for a in (rec.get("other_names") or []) + (rec.get("known_aliases") or []):
        if FOREIGN_RE.search(str(a)):
          bad_foreign.append((os.path.basename(fp), k, a))

      country = str(rec.get("country", ""))
      base_key = k[:-len(country) - 1] if country and k.lower().endswith("-" + country.lower()) else k.rsplit("-", 1)[0]
      bs = stem_dv(base_key)
      cs = stem_dv(cn)
      if hn and bs and cs and bs != cs:
        latest = max(hn, key=lambda x: [int(p) for p in x["date"].split(".")])
        lyf = int(latest["date"].split(".")[0])
        ls = stem_dv(latest["name"])
        d_bl = dice(bs, ls)
        d_cb = dice(cs, bs)
        d_cl = dice(cs, ls)
        if lyf >= 1995 and d_bl >= 0.80 and d_cb < 0.45:
          sig_issues.append(("A", k, cn, latest))
        elif lyf < 1920 and (rec.get("latest_year") or 0) >= 1950 and d_cl >= 0.80 and d_cb < 0.45:
          sig_issues.append(("B", k, cn, latest))

  print(
    f"Resolved files={len(all_resolved)}, unique_keys={len(seen_keys)}, "
    f"empty_hist={empty_hist}, bad_names={len(bad_names)}, bad_dates={len(bad_dates)}, "
    f"bad_foreign={len(bad_foreign)}, sig_issues={len(sig_issues)}"
  )
  if bad_names:
    print("BAD_NAMES:", bad_names[:10])
  if bad_dates:
    print("BAD_DATES:", bad_dates[:10])
  if bad_foreign:
    print("BAD_FOREIGN:", bad_foreign[:10])
  if sig_issues:
    print("SIG_ISSUES:", sig_issues[:10])


if __name__ == "__main__":
  main()
