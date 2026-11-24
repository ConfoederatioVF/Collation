import json
import sys

start = int(sys.argv[1])
end = int(sys.argv[2])
data = json.load(open('tests/chunk47_wiki.json', encoding='utf-8'))
for i, d in enumerate(data[start:end], start):
  print(f"=== [{i}] {d['key']} | {d['r']} | ey={d['ey']} ===")
  print("  geo:", d['geo'])
  print("  search:", d['search'])
  print("  chosen:", d['chosen'])
  ext = d['extract'].replace('\n', ' ')[:1200]
  print("  ext:", ext)
  if d['extra']:
    print("  extra:", d['extra'].replace('\n', ' ')[:600])
