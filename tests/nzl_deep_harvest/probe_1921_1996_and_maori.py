import re, requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

urls = [
  # Papers Past AJHR Maori Censuses (G-07, G-02, H-26A, H-26B etc.)
  "https://paperspast.natlib.govt.nz/parliamentary/appendix-to-the-journals-of-the-house-of-representatives/1874/I/1",
  "https://paperspast.natlib.govt.nz/parliamentary/AJHR1874-I.2.2.3.7",
  "https://paperspast.natlib.govt.nz/parliamentary/AJHR1878-I.2.2.3.2",
  "https://paperspast.natlib.govt.nz/parliamentary/AJHR1881-I.2.2.3.3",
  "https://paperspast.natlib.govt.nz/parliamentary/AJHR1886-I.2.2.4.12",
  "https://paperspast.natlib.govt.nz/parliamentary/AJHR1891-II.2.2.4.2",
  "https://paperspast.natlib.govt.nz/parliamentary/AJHR1896-I.2.3.2.15",
  "https://paperspast.natlib.govt.nz/parliamentary/AJHR1901-I.2.3.2.35",
  "https://paperspast.natlib.govt.nz/parliamentary/AJHR1906-II.2.3.2.34",
  # Stats NZ Store House / Archive / Historic census
  "https://statsnz.contentdm.oclc.org/",
  "https://www.stats.govt.nz/census/previous-censuses/",
  "https://www.stats.govt.nz/census/previous-censuses/historical-census-collection/",
  "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1951-52/",
  "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1961/",
  "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1971/",
  "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1981/",
  "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1992/",
  "https://www3.stats.govt.nz/New_Zealand_Official_Yearbooks/1997/",
]

for u in urls:
  try:
    r = requests.get(u, headers=H, timeout=12, allow_redirects=True)
    title = re.findall(r"<title>(.*?)</title>", r.text, re.I | re.S)
    t = title[0].strip()[:80] if title else ""
    print(f"{r.status_code} | {len(r.text):8d} | {t} | {u}")
  except Exception as e:
    print(f"ERR | {u} | {e}")
