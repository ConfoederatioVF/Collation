import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path

XML_PATH = Path('tests/belarus_pale_cache/nasmesta_djvu.xml')
OUT_PATH = Path('tests/belarus_pale_cache/nasmesta_5gub_parsed.json')

# Parse all pages into ordered column-separated text streams
pages = {}
pidx = 0
lines = []
cur_line_words = []
cur_line_x = 99999
cur_line_y = 99999
in_line = False

for event, elem in ET.iterparse(str(XML_PATH), events=('start', 'end')):
    if event == 'start' and elem.tag == 'OBJECT':
        pidx += 1
        lines = []
    elif event == 'start' and elem.tag == 'LINE':
        in_line = True
        cur_line_words = []
        cur_line_x = 99999
        cur_line_y = 99999
    elif event == 'end' and elem.tag == 'WORD' and in_line:
        coords = elem.attrib.get('coords', '').split(',')
        t = (elem.text or '').strip()
        if t and len(coords) >= 2:
            x1, y1 = int(coords[0]), int(coords[1])
            if x1 < cur_line_x: cur_line_x = x1
            if y1 < cur_line_y: cur_line_y = y1
            cur_line_words.append((x1, t))
    elif event == 'end' and elem.tag == 'LINE':
        in_line = False
        if cur_line_words:
            cur_line_words.sort(key=lambda k: k[0])
            lines.append((cur_line_x, cur_line_y, ' '.join(t for _, t in cur_line_words)))
    elif event == 'end' and elem.tag == 'OBJECT':
        w = int(elem.attrib.get('width', 2500))
        mid = w / 2.0
        left = sorted([l for l in lines if l[0] < mid], key=lambda k: k[1])
        right = sorted([l for l in lines if l[0] >= mid], key=lambda k: k[1])
        pages[pidx] = (
            [l[2] for l in left],
            [l[2] for l in right]
        )
        elem.clear()

# Flatten pages 15..140 into (page, col, line)
stream = []
for p in range(15, 140):
    if p in pages:
        for c in (0, 1):
            for ln in pages[p][c]:
                stream.append((p, c, ln))

# Find exact stream indices of governorate headers
gub_markers = []
for i, (p, c, ln) in enumerate(stream):
    if re.search(r'(?:^[IVXLCDM0-9ІУХ]+\.\s+|^)([А-ЯЁІѢѲ][а-яёіѣѳ\-]+\s+губерн)', ln) or ('губернія' in ln and len(ln) < 55 and 'ВСЕГО' not in ln):
        gub_markers.append((i, p, c, ln))

print('Detected governorate boundaries near targets:')
for idx, (si, p, c, ln) in enumerate(gub_markers):
    if any(k in ln for k in ['Вилен', 'Витеб', 'Владим', 'Гродн', 'Донск', 'Минск', 'Могил', 'Москов']):
        nxt = gub_markers[idx+1][0] if idx+1 < len(gub_markers) else len(stream)
        print(f'  [{si}..{nxt}] P.{p}C.{c}: {ln}')

# Print first 35 lines of each of the 5 target governorates
targets = ['Виленск', 'Витебск', 'Гродненск', 'Минск', 'Могилевск']
sections = {}
for idx, (si, p, c, ln) in enumerate(gub_markers):
    for t in targets:
        if t in ln and t not in sections:
            nxt = gub_markers[idx+1][0] if idx+1 < len(gub_markers) else len(stream)
            sections[t] = stream[si:nxt]

for t, rows in sections.items():
    print(f'=== {t} ({len(rows)} lines) ===')
    for _, _, ln in rows[:15]:
        print(' ', ln)
