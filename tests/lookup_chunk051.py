import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

with open("tests/chunk051_wiki.json", "r", encoding="utf-8") as f:
  INPUT = json.load(f)

HEADERS = {"User-Agent": "SVEAProjectToponymy/1.0 (https://confoederatio.org; admin@confoederatio.org)"}

def fetch_json(url):
  for attempt in range(4):
    time.sleep(0.18)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
      with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
      if e.code == 429:
        time.sleep(2.0 * (attempt + 1))
        continue
      return {}
    except Exception:
      return {}
  return {}

def clean_wiki_extract(text):
  text = re.sub(r"\s+", " ", text).strip()
  return text[:1200]

def search_wiki(lang, query):
  q = urllib.parse.quote(query)
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&srlimit=3&format=json"
  data = fetch_json(url)
  return [x["title"] for x in data.get("query", {}).get("search", [])]

def geosearch_wiki(lang, lat, lon):
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={lat}|{lon}&gsradius=8000&gslimit=4&format=json"
  data = fetch_json(url)
  return [(g["title"], int(g["dist"])) for g in data.get("query", {}).get("geosearch", [])]

def get_extracts_and_infobox(lang, titles):
  if not titles:
    return []
  t_str = urllib.parse.quote("|".join(titles[:2]))
  url = f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts|revisions&exchars=1600&explaintext=1&rvprop=content&rvslots=main&titles={t_str}&format=json"
  data = fetch_json(url)
  out = []
  for pid, p in data.get("query", {}).get("pages", {}).items():
    if int(pid) < 0:
      continue
    title = p.get("title", "")
    ext = clean_wiki_extract(p.get("extract") or "")
    rev_text = ""
    revs = p.get("revisions", [])
    if revs:
      raw = revs[0].get("slots", {}).get("main", {}).get("*", "")
      # grab fundacion/creacion/otros_nombres lines from infobox
      info_lines = []
      for line in raw.splitlines()[:120]:
        if re.search(r"fundaci|creaci|nombre|otros|fecha|erecci|inhabit|cultur|period|cronolog", line, re.I):
          info_lines.append(line.strip())
      if info_lines:
        rev_text = " | INFOBOX: " + " ; ".join(info_lines[:10])
    out.append(f"{lang.upper()}[{title}]: {ext}{rev_text}")
  return out

# Load original coordinates from input list? Wait: chunk051_wiki.json didn't save ll!
# Let's check if we should skip geosearch or re-embed ll. Wait, let's check search first, it's fast and accurate!
results = []
for idx, item in enumerate(INPUT):
  n = item["n"]
  c = item["c"]
  r = item["r"]
  hits = []
  titles_es = search_wiki("es", f'"{n}" {c}')
  if not titles_es:
    titles_es = search_wiki("es", f"{n} {c}")
  hits.extend(get_extracts_and_infobox("es", titles_es))
  if not hits:
    titles_en = search_wiki("en", f'"{n}" {c}')
    if not titles_en:
      titles_en = search_wiki("en", f"{n} {c}")
    hits.extend(get_extracts_and_infobox("en", titles_en))
  results.append({
    "key": item["key"],
    "n": n,
    "c": c,
    "r": r,
    "ey": item["ey"],
    "ly": item["ly"],
    "hits": hits
  })
  if (idx + 1) % 15 == 0:
    print(f"Processed {idx+1}/90", flush=True)

with open("tests/chunk051_wiki_full.json", "w", encoding="utf-8") as f:
  json.dump(results, f, ensure_ascii=False, indent=2)

print("Completed all 90!")
