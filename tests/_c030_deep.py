import glob
import json
import os
import time
import urllib.parse
import urllib.request

UA = "SVEA-Toponymy/1.0 (https://confoederatio.org)"

def fetch_json(url):
  for attempt in range(3):
    try:
      req = urllib.request.Request(url, headers={"User-Agent": UA})
      with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))
    except Exception as e:
      if "429" in str(e) or "503" in str(e):
        time.sleep(1.5 * (attempt + 1))
      else:
        return None
  return None

def load_local_records(items):
  root = "histmap/1.data_raw/population_regional/QUIPU"
  files = glob.glob(os.path.join(root, "**", "*_settlements.json"), recursive=True)
  by_key = {}
  by_name = {}
  for fp in files:
    try:
      data = json.load(open(fp, encoding="utf-8"))
    except Exception:
      continue
    rel = os.path.relpath(fp, root)
    if isinstance(data, dict):
      for k, v in data.items():
        if isinstance(v, dict):
          v_copy = dict(v)
          v_copy["_file"] = rel
          by_key.setdefault(k, []).append(v_copy)
          nm = str(v.get("name", "")).lower()
          if nm:
            by_name.setdefault(nm, []).append((k, v_copy))
  out = {}
  for it in items:
    k = it["key"]
    recs = by_key.get(k, [])
    if not recs:
      # try base key without _2 or (region)
      n_low = it["n"].lower()
      for cand_k, cand_v in by_name.get(n_low, []):
        c = cand_v.get("coords") or cand_v.get("ll")
        if c and len(c) == 2:
          # check distance
          d = abs(float(c[0]) - it["ll"][0]) + abs(float(c[1]) - it["ll"][1])
          if d < 0.15:
            recs.append(cand_v)
    # Compact local info
    compact = []
    for r in recs:
      compact.append({
        "file": r.get("_file"),
        "name": r.get("name"),
        "other_names": r.get("other_names"),
        "coords": r.get("coords") or r.get("ll"),
        "sources": r.get("sources"),
        "notes": r.get("notes"),
        "foundation_year": r.get("foundation_year"),
        "subregion": r.get("subregion"),
        "admin": r.get("admin") or r.get("department") or r.get("province") or r.get("municipality"),
        "years": sorted([kk for kk in r.keys() if kk.lstrip("-").isdigit()])[:8],
      })
    out[k] = compact
  return out

def query_wiki_for_item(it):
  lat, lng = it["ll"]
  name = it["n"]
  country = it["c"]
  res = {"es": [], "en": []}
  # Build candidate queries
  queries = [f"{name} {country}"]
  if country == "Peru":
    queries.insert(0, f"Distrito de {name}")
  elif country == "Ecuador":
    queries.insert(0, f"Parroquia {name}")
  elif country == "Colombia":
    queries.insert(0, f"{name} Colombia")
  elif country == "Bolivia":
    queries.insert(0, f"{name} Bolivia")
  elif country == "Venezuela":
    queries.insert(0, f"{name} Venezuela")

  for lang in ("es", "en"):
    titles = []
    seen = set()
    # Geosearch
    u_geo = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius=10000&gslimit=5&format=json"
    d_geo = fetch_json(u_geo)
    if d_geo:
      for g in d_geo.get("query", {}).get("geosearch", []):
        t = g["title"]
        if t not in seen:
          seen.add(t)
          titles.append((t, f"geo:{int(g.get('dist',0))}m"))
    # Text search (first query, or second if needed)
    for q_str in (queries[:2] if lang == "es" else [f"{name} {country}"]):
      u_sr = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q_str)}&srlimit=3&format=json"
      d_sr = fetch_json(u_sr)
      if d_sr:
        for s in d_sr.get("query", {}).get("search", []):
          t = s["title"]
          if t not in seen:
            seen.add(t)
            titles.append((t, "search"))
    if titles:
      top = [t[0] for t in titles[:4]]
      u_ext = f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote('|'.join(top))}&prop=extracts&explaintext=1&exchars=4500&format=json"
      d_ext = fetch_json(u_ext)
      if d_ext:
        pages = d_ext.get("query", {}).get("pages", {})
        by_t = {p.get("title"): p.get("extract", "") for p in pages.values()}
        for t, how in titles[:4]:
          ext = by_t.get(t, "")
          if ext:
            res[lang].append({"title": t, "how": how, "extract": ext[:3500]})
    time.sleep(0.05)
  return res

def main():
  inp = json.load(open("tests/_c030_input.json", encoding="utf-8"))
  local_map = load_local_records(inp)
  out = {}
  for idx, it in enumerate(inp):
    k = it["key"]
    w = query_wiki_for_item(it)
    out[k] = {"local": local_map.get(k, []), "es": w["es"], "en": w["en"]}
    if (idx + 1) % 15 == 0:
      print(f"Processed {idx+1}/90", flush=True)
  with open("tests/_c030_deep.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
  print("DONE 90/90")

if __name__ == "__main__":
  main()
