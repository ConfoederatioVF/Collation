import re
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

XML_PATH = Path('tests/belarus_pale_cache/nasmesta_djvu.xml')
OUT_PATH = Path('tests/belarus_pale_cache/nasmesta_5gub_parsed.json')

TARGET_PAGE_SET = set(range(22, 26)) | set(range(56, 61)) | set(range(116, 128))

pages_words = {}
pidx = 0
cur_words = []

for event, elem in ET.iterparse(str(XML_PATH), events=('start', 'end')):
    if event == 'start' and elem.tag == 'OBJECT':
        pidx += 1
        cur_words = []
    elif event == 'end' and elem.tag == 'WORD' and pidx in TARGET_PAGE_SET:
        coords = elem.attrib.get('coords', '').split(',')
        t = (elem.text or '').strip()
        if t and len(coords) >= 4:
            x1, y1, x2, y2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
            base_y = int(coords[4]) if len(coords) >= 5 else y1
            cur_words.append((x1, x2, base_y, t))
    elif event == 'end' and elem.tag == 'OBJECT':
        if pidx in TARGET_PAGE_SET:
            w = int(elem.attrib.get('width', 2500))
            pages_words[pidx] = (w, cur_words)
        elem.clear()

def cluster_rows(words, tol=16):
    if not words:
        return []
    words = sorted(words, key=lambda k: k[2])
    rows, cur, cur_y = [], [words[0]], words[0][2]
    for wd in words[1:]:
        if abs(wd[2] - cur_y) <= tol:
            cur.append(wd)
        else:
            rows.append(sorted(cur, key=lambda k: k[0]))
            cur, cur_y = [wd], wd[2]
    if cur:
        rows.append(sorted(cur, key=lambda k: k[0]))
    return rows

def clean_num(s):
    s = re.sub(r'[^\d]', '', s)
    return int(s) if s else None

GUB_MAP = {
    'Виленск': 'Vilna',
    'Витебск': 'Vitebsk',
    'Гродненск': 'Grodno',
    'Минск': 'Minsk',
    'Могилевск': 'Mogilev',
}

stream = []
for p in sorted(pages_words):
    w, words = pages_words[p]
    mid = w / 2.0
    full_rows = cluster_rows(words, tol=22)
    skip_words = set()
    header_events = []
    for rw in full_rows:
        line = ' '.join(wd[3] for wd in rw)
        y_avg = sum(wd[2] for wd in rw) / len(rw)
        is_hdr = (
            ('губерн' in line.lower() or 'область' in line.lower() or 'войска донск' in line.lower() or 'донского' in line.lower())
            and len(line) < 85
            and 'ВСЕГО' not in line
            and not re.search(r'\d\s+\d', line)
        )
        if is_hdr:
            header_events.append((y_avg, 'HEADER', line))
            for wd in rw: skip_words.add(id(wd))
        elif 'Сокращен' in line or (len(rw) > 2 and any('—' in wd[3] and wd[3].endswith('.') for wd in rw) and y_avg < 1200 and not any(wd[3].isdigit() for wd in rw)):
            for wd in rw: skip_words.add(id(wd))

    hdr_ys = sorted([h for h in header_events if h[1] == 'HEADER'], key=lambda k: k[0])
    y_bands = []
    prev_y = -1
    for hy, _, hline in hdr_ys:
        y_bands.append((prev_y, hy, None))
        y_bands.append((hy, hy, hline))
        prev_y = hy
    y_bands.append((prev_y, 999999, None))

    for y0, y1, hline in y_bands:
        if hline is not None:
            stream.append((p, -1, hline, []))
            continue
        band_words = [wd for wd in words if id(wd) not in skip_words and y0 < wd[2] < y1]
        for col_idx, col_words in [(0, [wd for wd in band_words if wd[0] < mid]), (1, [wd for wd in band_words if wd[0] >= mid])]:
            col_x_min = 0 if col_idx == 0 else mid
            num_start_x = col_x_min + 850
            m_xs = [wd[0] for wd in col_words if wd[3] in ('М.', 'м.') and wd[0] > col_x_min + 700]
            if m_xs:
                num_start_x = min(num_start_x, min(m_xs) - 25)
            for rw in cluster_rows(col_words, tol=16):
                txt_w = [wd[3] for wd in rw if wd[0] < num_start_x]
                num_w = [wd[3] for wd in rw if wd[0] >= num_start_x]
                stream.append((p, col_idx, ' '.join(txt_w), num_w))

cur_gub = None
in_target = False
entries = []
buf_txt = []

for p, c, txt, num_w in stream:
    if c == -1:
        matched = None
        for gk, gv in GUB_MAP.items():
            if gk in txt:
                matched = gv
                break
        if matched:
            cur_gub = matched
            in_target = True
            buf_txt = []
        else:
            cur_gub = None
            in_target = False
            buf_txt = []
        continue
    if not in_target:
        continue
    if txt in ('', 'М.', 'Ж.', 'ОБ. П.') or re.match(r'^[МЖ]\.\s*[МЖ]?\.?', txt) or 'ОБ. П.' in txt:
        continue
    if '—' in txt and ('скій' in txt or 'цкій' in txt or 'гкій' in txt) and not num_w:
        continue

    if txt:
        buf_txt.append(txt)
    nums = [clean_num(x) for x in num_w]
    nums = [n for n in nums if n is not None]
    if len(nums) >= 3:
        m, f, tot = nums[-3], nums[-2], nums[-1]
        full_text = ' '.join(buf_txt).strip()
        buf_txt = []
        if full_text:
            # Parse name, alt_name, type, jewish count
            m_jew = re.search(r'[ІI1][уy]д\.?\s*(\d[\d\.]*)', full_text)
            jew_str = m_jew.group(1).replace('.', '') if m_jew else ''
            jew_pop = int(jew_str) if jew_str.isdigit() else None
            # Name before first comma or before settlement type
            name_part = full_text.split(',')[0].strip()
            alt_name = None
            m_alt = re.search(r'\(([^)]+)\)', name_part)
            if m_alt:
                alt_name = m_alt.group(1).strip()
                name_part = re.sub(r'\s*\([^)]+\)', '', name_part).strip()
            entries.append({
                'gov': cur_gub,
                'page': p,
                'name': name_part,
                'alt_name': alt_name,
                'raw': full_text,
                'male': m,
                'female': f,
                'total': tot,
                'jewish': jew_pop,
                'checksum_ok': (m + f == tot)
            })

by_gov = Counter(e['gov'] for e in entries)
chk_ok = Counter(e['gov'] for e in entries if e['checksum_ok'])
has_jew = Counter(e['gov'] for e in entries if e['jewish'] is not None)
print('Extracted entries by governorate:', dict(by_gov))
print('Expected TOC counts: Vilna=149, Vitebsk=60, Grodno=565, Minsk=920, Mogilev=731')
print('Checksum (M+F==Total) OK:', dict(chk_ok))
print('With Jewish count:', dict(has_jew))
OUT_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
