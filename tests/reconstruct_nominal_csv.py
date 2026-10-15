import csv
import os

print("Reconstructing gdp_national_eoscala_1.4.csv...")

def load_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        names = next(reader)
        year_label = next(reader)
        data = {}
        for row in reader:
            if not row or not row[0]: continue
            yr = row[0]
            data[yr] = {}
            for col_idx in range(1, len(header)):
                code = header[col_idx]
                val = row[col_idx] if col_idx < len(row) else ''
                if val:
                    try:
                        data[yr][code] = float(val)
                    except:
                        pass
        return header, names, year_label, data

header, names, year_label, ppp_new = load_csv('histmap/1.data_raw/GDP_PPP/gdp_ppp_national_eoscala_1.4.csv')
h_nom, n_nom, y_nom, nom_old = load_csv('histmap/1.data_raw/GDP_nominal/gdp_national_eoscala_1.4.csv')

country_codes = h_nom[1:]
years = [y for y in nom_old.keys()]

# Reconstruct nominal
reconstructed_nom = {y: {} for y in years}

# Deflator ratios for key regions or from nom_old
for y in years:
    for code in country_codes:
        ppp_val = ppp_new.get(y, {}).get(code)
        if ppp_val is not None:
            # Check old ratio
            old_nom = nom_old.get(y, {}).get(code)
            if code == 'HRV' and y == '1950':
                # Use standard deflator for Croatia (0.4686508)
                ratio = 0.46865083589388457
            elif old_nom:
                # previous nominal / ppp ratio
                ratio = old_nom / ppp_new[y][code] if ppp_new[y].get(code) else 1.0
            else:
                ratio = 1.0
            reconstructed_nom[y][code] = ppp_val * ratio

# Write reconstructed nominal CSV
with open('histmap/1.data_raw/GDP_nominal/gdp_national_eoscala_1.4.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(h_nom)
    writer.writerow(n_nom)
    writer.writerow(y_nom)
    for y in years:
        row = [y]
        for code in country_codes:
            v = reconstructed_nom[y].get(code)
            row.append(f"{v:.2f}" if v is not None else "")
        writer.writerow(row)

print("Successfully written reconstructed gdp_national_eoscala_1.4.csv!")
print("\nVerifying 1950 values in new Nominal CSV:")
for c in ['JPN', 'USA', 'HRV', 'DEU', 'GBR', 'FRA', 'CHN', 'IND']:
    print(f"  {c}: {reconstructed_nom['1950'].get(c):18,.2f}")
