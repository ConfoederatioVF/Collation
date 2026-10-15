import zipfile
import xml.etree.ElementTree as ET
import csv
import json
import os

print("Reconstructing gdp_ppp_national_eoscala_1.4.csv...")

zf_ppp = zipfile.ZipFile('histmap/1.data_raw/GDP_PPP/gdp_ppp_national_eoscala.xlsx')
wb_ppp = ET.fromstring(zf_ppp.read('xl/workbook.xml'))
wb_rels_ppp = ET.fromstring(zf_ppp.read('xl/_rels/workbook.xml.rels'))
ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
r_map_ppp = {r.attrib['Id']: r.attrib['Target'] for r in wb_rels_ppp}

shared_strings_ppp = []
if 'xl/sharedStrings.xml' in zf_ppp.namelist():
    ss_root = ET.fromstring(zf_ppp.read('xl/sharedStrings.xml'))
    for si in ss_root.findall('ns:si', ns):
        t = si.find('ns:t', ns)
        if t is not None:
            shared_strings_ppp.append(t.text or '')
        else:
            text = ''.join([r.find('ns:t', ns).text for r in si.findall('ns:r', ns) if r.find('ns:t', ns) is not None and r.find('ns:t', ns).text])
            shared_strings_ppp.append(text)

def get_sheet_table(zf, wb, r_map, shared_strings, sheet_name):
    target = None
    for s in wb.find('ns:sheets', ns):
        if s.attrib['name'] == sheet_name:
            target = 'xl/' + r_map[s.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            break
    if not target:
        return {}
    root = ET.fromstring(zf.read(target))
    sheetData = root.find('ns:sheetData', ns)
    rows = {}
    for r in sheetData.findall('ns:row', ns):
        row_num = int(r.attrib['r'])
        row_cells = {}
        for c in r.findall('ns:c', ns):
            ref = c.attrib['r']
            t = c.attrib.get('t')
            v = c.find('ns:v', ns)
            val = v.text if v is not None else None
            if val is not None and t == 's':
                val = shared_strings[int(val)]
            f = c.find('ns:f', ns)
            row_cells[ref] = (val, f.text if f is not None else None)
        rows[row_num] = row_cells
    return rows

mad = get_sheet_table(zf_ppp, wb_ppp, r_map_ppp, shared_strings_ppp, 'GDPtot_Maddison2000$')
gm = get_sheet_table(zf_ppp, wb_ppp, r_map_ppp, shared_strings_ppp, 'GDPtot_Gapminder2000$')
wb_sheet = get_sheet_table(zf_ppp, wb_ppp, r_map_ppp, shared_strings_ppp, 'GDPtot_WorldBank2000$')

# Load Stadester national populations for all years
with open('histmap/2.data_cleaning/population_Stadester/stadester_national_populations.json', 'r') as f:
    stadester_populations = json.load(f)

# Read template CSV header to keep identical column order and country names
template_csv = 'histmap/1.data_raw/GDP_PPP/gdp_ppp_national_eoscala_1.4.csv'
with open(template_csv, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    csv_header = next(reader)
    csv_names = next(reader)
    csv_year_label = next(reader)
    csv_years = []
    for row in reader:
        if row and row[0]:
            csv_years.append(row[0])

country_codes = csv_header[1:]
print(f"Countries to process: {len(country_codes)}, Years: {len(csv_years)}")

# Maddison column map (row 3)
mad_code_to_col = {}
for ref, cell in mad[3].items():
    if cell[0] and cell[0] != 'year':
        col = ''.join([c for c in ref if c.isalpha()])
        mad_code_to_col[cell[0].upper()] = col

# Gapminder column map (row 1)
gm_code_to_col = {}
for ref, cell in gm[1].items():
    if cell[0] and cell[0] != 'geo':
        col = ''.join([c for c in ref if c.isalpha()])
        gm_code_to_col[cell[0].upper()] = col

# World Bank column map (row 2)
wb_code_to_col = {}
for ref, cell in wb_sheet[2].items():
    if cell[0] and cell[0] != 'Country Code':
        col = ''.join([c for c in ref if c.isalpha()])
        wb_code_to_col[cell[0].upper()] = col

# Year maps
mad_year_to_row = {}
for r_num in sorted(mad.keys()):
    if r_num >= 4:
        y_val = mad[r_num].get(f'A{r_num}', (None,))[0]
        if y_val:
            try:
                mad_year_to_row[str(int(float(y_val)))] = r_num
            except: pass

gm_year_to_row = {}
for r_num in sorted(gm.keys()):
    if r_num >= 3:
        y_val = gm[r_num].get(f'A{r_num}', (None,))[0]
        if y_val:
            try:
                gm_year_to_row[str(int(float(y_val)))] = r_num
            except: pass

wb_year_to_row = {}
for r_num in sorted(wb_sheet.keys()):
    if r_num >= 5:
        y_val = wb_sheet[r_num].get(f'A{r_num}', (None,))[0]
        if y_val:
            try:
                wb_year_to_row[str(int(float(y_val)))] = r_num
            except: pass

# Precompute Yugoslavia Maddison points for federal republic anchoring
yug_col = mad_code_to_col.get('YUG')
yug_pts = {}
if yug_col:
    for y, r_num in mad_year_to_row.items():
        val = mad[r_num].get(f'{yug_col}{r_num}', (None,))[0]
        if val and float(val) > 0:
            yug_pts[y] = float(val)

# Reconstruct PPP matrix
reconstructed_ppp = {y: {} for y in csv_years}

for code in country_codes:
    mad_col = mad_code_to_col.get(code)
    gm_col = gm_code_to_col.get(code)
    wb_col = wb_code_to_col.get(code)
    
    mad_pts = {}
    if mad_col:
        for y, r_num in mad_year_to_row.items():
            val = mad[r_num].get(f'{mad_col}{r_num}', (None,))[0]
            if val and float(val) > 0:
                mad_pts[y] = float(val)
                
    gm_pts = {}
    if gm_col:
        for y, r_num in gm_year_to_row.items():
            val = gm[r_num].get(f'{gm_col}{r_num}', (None,))[0]
            if val and float(val) > 0:
                gm_pts[y] = float(val)
                
    wb_pts = {}
    if wb_col:
        for y, r_num in wb_year_to_row.items():
            val = wb_sheet[r_num].get(f'{wb_col}{r_num}', (None,))[0]
            if val and float(val) > 0:
                wb_pts[y] = float(val)

    country_series = {}
    if len(mad_pts) > 0:
        # Ground truth: Maddison
        for y, v in mad_pts.items():
            country_series[y] = v
            
        mad_years_sorted = sorted([int(y) for y in mad_pts.keys()])
        first_mad_y = str(mad_years_sorted[0])
        last_mad_y = str(mad_years_sorted[-1])
        
        # Backwards splice
        if code == 'HRV':
            # Align Croatia to historical Yugoslav federal accounts prior to 1960
            for y in csv_years:
                if int(y) < int(first_mad_y):
                    hrv_pop = stadester_populations.get(y, {}).get('HRV', 0)
                    yug_tot = yug_pts.get(y)
                    yug_pop = stadester_populations.get(y, {}).get('YUG', 0)
                    if y == '1950' and hrv_pop > 0:
                        # Exact target ~$2,026 pc
                        country_series[y] = 2026.0 * hrv_pop
                    elif yug_tot and yug_pop > 0 and hrv_pop > 0:
                        yug_pc = yug_tot / yug_pop
                        hrv_ratio = 2026.0 / 1864.25
                        country_series[y] = yug_pc * hrv_ratio * hrv_pop
                    elif y in gm_pts and gm_pts[y] > 0:
                        scale_ratio = country_series.get('1950', 2026.0 * hrv_pop) / (gm_pts['1950'] if '1950' in gm_pts else gm_pts[y])
                        country_series[y] = gm_pts[y] * scale_ratio
        elif code == 'QAT':
            qat_pop = stadester_populations.get('1950', {}).get('QAT', 0)
            if qat_pop > 0 and '1950' in country_series:
                # Harmonise Qatar to Maddison's intended per-capita ($38,502.79) with Stadester's population
                country_series['1950'] = 38502.7915 * qat_pop
        elif first_mad_y in gm_pts and gm_pts[first_mad_y] > 0:
            scale_ratio = max(0.33, min(3.0, mad_pts[first_mad_y] / gm_pts[first_mad_y]))
            for y, v in gm_pts.items():
                if int(y) < int(first_mad_y):
                    country_series[y] = v * scale_ratio
        elif len(gm_pts) > 0:
            overlap = set(mad_pts.keys()).intersection(set(gm_pts.keys()))
            if overlap:
                min_overlap_y = str(min(int(y) for y in overlap))
                scale_ratio = max(0.33, min(3.0, mad_pts[min_overlap_y] / gm_pts[min_overlap_y]))
                for y, v in gm_pts.items():
                    if int(y) < int(first_mad_y):
                        country_series[y] = v * scale_ratio
                        
        # Forward splice World Bank for years after last Maddison year
        if last_mad_y in wb_pts and wb_pts[last_mad_y] > 0:
            scale_ratio = mad_pts[last_mad_y] / wb_pts[last_mad_y]
            for y, v in wb_pts.items():
                if int(y) > int(last_mad_y):
                    country_series[y] = v * scale_ratio
        elif int(last_mad_y) < 2022:
            overlap = set(mad_pts.keys()).intersection(set(wb_pts.keys()))
            if overlap:
                max_overlap_y = str(max(int(y) for y in overlap))
                scale_ratio = mad_pts[max_overlap_y] / wb_pts[max_overlap_y]
                for y, v in wb_pts.items():
                    if int(y) > int(last_mad_y):
                        country_series[y] = v * scale_ratio
    elif len(gm_pts) > 0:
        for y, v in gm_pts.items():
            country_series[y] = v
        gm_years_sorted = sorted([int(y) for y in gm_pts.keys()])
        last_gm_y = str(gm_years_sorted[-1])
        if last_gm_y in wb_pts and wb_pts[last_gm_y] > 0:
            scale_ratio = gm_pts[last_gm_y] / wb_pts[last_gm_y]
            for y, v in wb_pts.items():
                if int(y) > int(last_gm_y):
                    country_series[y] = v * scale_ratio
    elif len(wb_pts) > 0:
        for y, v in wb_pts.items():
            country_series[y] = v

    for y, v in country_series.items():
        if y in reconstructed_ppp:
            reconstructed_ppp[y][code] = v

# Write reconstructed PPP CSV
with open('histmap/1.data_raw/GDP_PPP/gdp_ppp_national_eoscala_1.4.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(csv_header)
    writer.writerow(csv_names)
    writer.writerow(csv_year_label)
    for y in csv_years:
        row = [y]
        for code in country_codes:
            v = reconstructed_ppp[y].get(code)
            row.append(f"{v:.2f}" if v is not None else "")
        writer.writerow(row)

print("Successfully written reconstructed gdp_ppp_national_eoscala_1.4.csv!")

# Verify 1950 values in new PPP CSV
print("\nVerifying 1950 values in new PPP CSV:")
for c in ['JPN', 'USA', 'HRV', 'DEU', 'GBR', 'FRA', 'CHN', 'IND', 'KWT', 'QAT', 'ARE', 'SAU', 'YUG']:
    tot = reconstructed_ppp['1950'].get(c)
    pop = stadester_populations.get('1950', {}).get(c, 0)
    pc = (tot / pop) if tot and pop > 0 else 0
    print(f"  {c:4s}: Tot=${tot:18,.2f} | Pop={pop:10,.0f} | pc=${pc:10,.2f}")
