import re
import urllib.request

H = {"User-Agent": "Mozilla/5.0"}
for cat in ("2112.01911", "2111.01921"):
  url = f"https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/{cat}?OpenDocument"
  html = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=20).read().decode("utf-8", "ignore")
  print(f"=== ABS {cat} ===")
  for tr in re.findall(r"<tr[^>]*>.*?</tr>", html, re.S):
    txt = re.sub(r"<[^>]+>", " ", tr)
    txt = re.sub(r"\s+", " ", txt).strip()
    hr = re.findall(r'href=["\']([^"\']*log\?openagent[^"\']*)["\']', tr, re.I)
    if hr and any(w in txt.lower() for w in ("localit", "town", "bulletin", "part i", "population", "summary", "appendix")):
      print(" ", txt[:95], "|", hr[0][:75])
