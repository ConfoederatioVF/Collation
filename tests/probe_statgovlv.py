import re
import ssl
import urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for u in [
  "https://stat.gov.lv/lv/statistikas-temas/iedzivotaji/iedzivotaju-skaits/publikacijas-un-infografikas/1302-ceturta-tautas",
  "https://stat.gov.lv/lv/statistikas-temas/iedzivotaji/iedzivotaju-skaits/publikacijas-un-infografikas",
]:
  try:
    h = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25, context=ctx).read().decode("utf-8", errors="replace")
    print("=== URL:", u, "len:", len(h), "===")
    links = re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', h, re.S)
    for href, txt in links:
      clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt)).strip()
      if any(k in (href + " " + clean).lower() for k in ["skait", "1920", "1925", "1930", "1935", "1959", "pdf", "media", "download"]):
        print(" ", href, "|", clean[:80])
  except Exception as e:
    print("ERR:", u, e)
