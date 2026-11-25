import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}

# 1. All LT & LV links on pop-stat.mashke.org index
h = urllib.request.urlopen(urllib.request.Request("http://pop-stat.mashke.org/", headers=UA), timeout=20).read().decode("utf-8", errors="replace")
for m in re.finditer(r'href=["\']([^"\']*(?:lithuania|latvia)[^"\']*)["\'][^>]*>(.*?)</a>', h, re.S | re.I):
  print("INDEX:", m.group(1), "|", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip())

# 2. Check bottom sources of lithuania-cities.htm & latvia-cities.htm + row count
for fn in ["lithuania-cities.htm", "latvia-cities.htm"]:
  p = urllib.request.urlopen(urllib.request.Request("http://pop-stat.mashke.org/" + fn, headers=UA), timeout=20).read().decode("utf-8", errors="replace")
  trs = re.findall(r"<tr[^>]*>(.*?)</tr>", p, re.S)
  print(f"\n=== {fn}: {len(trs)} trs ===")
  tail = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p[-4000:])).strip()
  print("TAIL:", tail[-1500:])

# 3. Check nasmesta_djvu.xml size & sample
req = urllib.request.Request("https://archive.org/download/nasmesta/nasmesta_djvu.xml", headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-3000"})
with urllib.request.urlopen(req, timeout=20) as r:
  print("\n=== nasmesta_djvu.xml head ===", r.headers.get("Content-Range"))
  print(r.read().decode("utf-8", errors="replace")[:1000])
