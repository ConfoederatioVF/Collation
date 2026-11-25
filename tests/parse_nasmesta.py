import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path

XML_PATH = Path('tests/belarus_pale_cache/nasmesta_djvu.xml')
OUT_PATH = Path('tests/belarus_pale_cache/nasmesta_5gub_parsed.json')

# Exact page spans (1-based OBJECT index) — we will detect dynamically by governorate headers
TARGET_GUBS = {
    'Виленская': 'Vilna Governorate',
    'Витебская': 'Vitebsk Governorate',
    'Гродненская': 'Grodno Governorate',
    'Минская': 'Minsk Governorate',
    'Могилевская': 'Mogilev Governorate',
}

def extract_pages():
    pages = {}
    pidx = 0
    cur_gub = None
    # Collect lines per page with (x_min, y_min, text)
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
                '\n'.join(l[2] for l in left),
                '\n'.join(l[2] for l in right)
            )
            elem.clear()
    return pages

pages = extract_pages()
print(f'Extracted {len(pages)} pages', flush=True)

# Find which pages belong to each governorate (skip TOC pages < 15)
gub_ranges = []
for p in range(15, len(pages) + 1):
    for col_idx, col_txt in enumerate(pages[p]):
        for line in col_txt.splitlines():
            # e.g. "IV. Виленская губернія." or "ХХП. Минская губернія."
            for g in TARGET_GUBS:
                if g in line and ('губерн' in line or 'Сокращен' in col_txt):
                    if re.search(rf'(?:[IVXLCDM]+\.|^\s*){g}\s+губерн', line) or g + ' губерн' in line:
                        gub_ranges.append((p, col_idx, g, line))

print('Found governorate headers:', gub_ranges)

# Build ordered stream of (gub, text) by finding ALL governorate starts across pages 15..350
all_headers = []
for p in range(15, 338):
    for col_idx, col_txt in enumerate(pages[p]):
        for l_idx, line in enumerate(col_txt.splitlines()):
            if re.search(r'^[IVXLCDM0-9]+\.\s+\S+.*губерн', line) or ('губернія' in line and len(line) < 55 and 'ВСЕГО' not in line):
                all_headers.append((p, col_idx, l_idx, line))

print('Sample all headers:', [h for h in all_headers if any(g[:5] in h[3] for g in TARGET_GUBS)][:20])
