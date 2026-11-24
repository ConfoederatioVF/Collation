import json, urllib.request, urllib.parse, unicodedata, time

with open("tests/wd_results.json", "r", encoding="utf-8") as f:
  wd = json.load(f)

def norm(s):
  if not s: return ""
  s = unicodedata.normalize("NFKD", s)
  s = "".join(c for c in s if not unicodedata.combining(c))
  return s.lower().strip()

#Let's load items from wiki_lookup.py
with open("tests/wiki_lookup.py", "r", encoding="utf-8") as f:
  code = f.read()
ns = {}
exec(code.split("def sparql_batch")[0], ns)
items = ns["items"]

matched_titles_es = {}
for it in items:
  k = it["key"]
  n_norm = norm(it["n"])
  words = [w for w in n_norm.replace("(", " ").replace(")", " ").split() if len(w) > 2]
  al_norms = [norm(a) for a in it.get("al", [])]
  cands = wd.get(k, [])
  best = []
  for c in cands:
    lbl = norm(c.get("label", ""))
    es = c.get("eswiki")
    en = c.get("enwiki")
    score = 0
    if n_norm in lbl or lbl in n_norm:
      score += 10
    for w in words:
      if w in lbl:
        score += 2
    for a in al_norms:
      if a and (a in lbl or lbl in a):
        score += 5
    if score > 0 or c.get("inception"):
      best.append((score, c))
  best.sort(key=lambda x: -x[0])
  matched_titles_es[k] = best[:5]

#Collect unique eswiki titles for top matches
es_titles = []
for k, best in matched_titles_es.items():
  for sc, c in best[:2]:
    if c.get("eswiki") and sc >= 2:
      t = urllib.parse.unquote(c["eswiki"].split("/wiki/")[-1]).replace("_", " ")
      if t not in es_titles:
        es_titles.append(t)

print("Unique eswiki titles to fetch:", len(es_titles))

extracts = {}
for i in range(0, len(es_titles), 10):
  batch = es_titles[i:i+10]
  params = {
    "action": "query",
    "prop": "extracts",
    "exintro": "1",
    "explaintext": "1",
    "titles": "|".join(batch),
    "format": "json"
  }
  url = "https://es.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
  req = urllib.request.Request(url, headers={"User-Agent": "ViscountResearch/1.0 (https://confoederatio.org)"})
  with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read().decode("utf-8"))
  for pid, page in data.get("query", {}).get("pages", {}).items():
    if "extract" in page:
      extracts[page["title"]] = page["extract"]
  time.sleep(0.5)

summary = {}
for it in items:
  k = it["key"]
  rows = []
  for sc, c in matched_titles_es[k][:3]:
    t = urllib.parse.unquote(c["eswiki"].split("/wiki/")[-1]).replace("_", " ") if c.get("eswiki") else None
    rows.append({
      "score": sc,
      "label": c.get("label"),
      "inception": c.get("inception"),
      "es_title": t,
      "enwiki": c.get("enwiki"),
      "intro": extracts.get(t, "")[:600] if t else ""
    })
  summary[k] = rows

with open("tests/wiki_summary.json", "w", encoding="utf-8") as f:
  json.dump(summary, f, ensure_ascii=False, indent=2)
print("Saved wiki_summary.json")
