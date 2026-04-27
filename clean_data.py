"""
CSO Waste Data Cleaning Script
================================
Datasets: GWA01 (Waste Generation), GWA02 (Waste Treatment)
Source: Central Statistics Office Ireland - High Value Datasets
Transformations documented below.
"""

import pandas as pd
import json

# ── Load raw data ──────────────────────────────────────────────────────────────
df1 = pd.read_csv("GWA01.20260427T120427.csv", encoding='utf-8-sig')
df2 = pd.read_csv("GWA02.20260427T120416.csv", encoding='utf-8-sig')

print(f"GWA01 raw: {df1.shape[0]:,} rows")
print(f"GWA02 raw: {df2.shape[0]:,} rows")

# ──────────────────────────────────────────────────────────────────────────────
# GWA01: Waste Generation by Sector & Hazardousness
# Transformations:
#   1. Filter to "Total waste" category only (avoids double-counting subcategories)
#   2. Filter to top-level sectors only (exclude sub-manufacturing breakdowns)
#   3. Exclude "All NACE activities plus households" (aggregate row)
#   4. Separate Hazardous / Non-Hazardous rows (drop Total row)
#   5. Convert VALUE to numeric, fill missing as 0
#   6. Convert tonnes → thousand tonnes for readability
#   7. Rename and clean sector labels
# ──────────────────────────────────────────────────────────────────────────────

# Step 1: Filter to Total waste category
gwa01 = df1[df1['Waste Category'] == 'Total waste'].copy()

# Step 2+3: Keep only meaningful top-level sectors
keep_sectors = {
    'Agriculture, forestry and fishing (A)':                        'Agriculture & Fishing',
    'Mining and quarrying (B)':                                      'Mining & Quarrying',
    'Manufacturing (C)':                                             'Manufacturing',
    'Electricity, gas, steam and air conditioning supply  (D)':     'Electricity & Gas',
    'Water supply; sewerage, waste management and remediation activities (E)': 'Water & Waste Mgmt',
    'Construction (F)':                                              'Construction',
    'Services (except wholesale of waste and scrap)  (G-U_X_G4677)':'Services',
    'Households (EP_HH)':                                            'Households',
}

gwa01 = gwa01[gwa01['NACE Rev. 2 Activity'].isin(keep_sectors.keys())].copy()
gwa01['sector'] = gwa01['NACE Rev. 2 Activity'].map(keep_sectors)

# Step 4: Keep Hazardous and Non-Hazardous separately (not Total)
haz_map = {
    'Hazardous[HAZ]':     'Hazardous',
    'Non-hazardous[NHAZ]':'Non-Hazardous',
}
gwa01 = gwa01[gwa01['Hazardousness'].isin(haz_map.keys())].copy()
gwa01['hazardousness'] = gwa01['Hazardousness'].map(haz_map)

# Step 5: Convert to numeric
gwa01['VALUE'] = pd.to_numeric(gwa01['VALUE'], errors='coerce').fillna(0)

# Step 6: Tonnes → thousand tonnes
gwa01['waste_thousand_tonnes'] = (gwa01['VALUE'] / 1000).round(1)

# Step 7: Final columns
gwa01_clean = gwa01[['Year', 'sector', 'hazardousness', 'waste_thousand_tonnes']].copy()
gwa01_clean.columns = ['year', 'sector', 'hazardousness', 'waste_thousand_tonnes']
gwa01_clean = gwa01_clean.sort_values(['year', 'sector', 'hazardousness']).reset_index(drop=True)

print(f"\nGWA01 cleaned: {gwa01_clean.shape[0]} rows")
print(gwa01_clean.head(16).to_string())

# ──────────────────────────────────────────────────────────────────────────────
# GWA02: Waste Treatment Methods
# Transformations:
#   1. Filter to "Total waste" waste category
#   2. Filter to "Hazardous and non-hazardous - Total" (all waste combined)
#   3. Keep only the 4 meaningful treatment operations (no sub-totals/duplicates)
#   4. Convert VALUE to numeric, fill missing as 0
#   5. Convert tonnes → thousand tonnes
#   6. Clean operation labels
# ──────────────────────────────────────────────────────────────────────────────

gwa02 = df2[
    (df2['Waste Category'] == 'Total waste') &
    (df2['Hazardousness'] == 'Hazardous and non-hazardous - Total[HAZ_NHAZ]')
].copy()

keep_ops = {
    'Recovery - recycling and backfilling (R2-R11)[RCV_R_B]': 'Recycling & Recovery',
    'Recovery - energy recovery (R1)[RCV_E]':                  'Energy Recovery (Incineration)',
    'Disposal - landfill (D1, D5, D12)[DSP_L]':               'Landfill',
    'Disposal - incineration (D10)[DSP_I]':                    'Incineration (No Recovery)',
}
gwa02 = gwa02[gwa02['Waste Management Operation'].isin(keep_ops.keys())].copy()
gwa02['treatment'] = gwa02['Waste Management Operation'].map(keep_ops)

gwa02['VALUE'] = pd.to_numeric(gwa02['VALUE'], errors='coerce').fillna(0)
gwa02['waste_thousand_tonnes'] = (gwa02['VALUE'] / 1000).round(1)

gwa02_clean = gwa02[['Year', 'treatment', 'waste_thousand_tonnes']].copy()
gwa02_clean.columns = ['year', 'treatment', 'waste_thousand_tonnes']
gwa02_clean = gwa02_clean.sort_values(['year', 'treatment']).reset_index(drop=True)

print(f"\nGWA02 cleaned: {gwa02_clean.shape[0]} rows")
print(gwa02_clean.to_string())

# ──────────────────────────────────────────────────────────────────────────────
# Circular Economy Gap: per sector in most recent year (2020)
# Metric: total generated vs hazardous generated vs non-hazardous
# ──────────────────────────────────────────────────────────────────────────────
gap = gwa01_clean[gwa01_clean['year'] == 2020].copy()
gap_total = gap.groupby('sector')['waste_thousand_tonnes'].sum().reset_index()
gap_haz = gap[gap['hazardousness'] == 'Hazardous'].groupby('sector')['waste_thousand_tonnes'].sum().reset_index()
gap_total.columns = ['sector', 'total']
gap_haz.columns = ['sector', 'hazardous']
gap_df = gap_total.merge(gap_haz, on='sector')
gap_df['non_hazardous'] = gap_df['total'] - gap_df['hazardous']
gap_df['hazardous_pct'] = ((gap_df['hazardous'] / gap_df['total']) * 100).round(1)
gap_df = gap_df.sort_values('total', ascending=False).reset_index(drop=True)

print(f"\nCircular Economy Gap (2020):")
print(gap_df.to_string())

# ── Save cleaned CSVs ──────────────────────────────────────────────────────────
gwa01_clean.to_csv("/Users/dak/Information_Visualisation_Project/gwa01_clean.csv", index=False)
gwa02_clean.to_csv("/Users/dak/Information_Visualisation_Project/gwa02_clean.csv", index=False)
gap_df.to_csv("/Users/dak/Information_Visualisation_Project/gap_2020.csv", index=False)

# ── Export as JSON for Vega-Lite inline use ────────────────────────────────────
gen_json   = gwa01_clean.to_dict(orient='records')
treat_json = gwa02_clean.to_dict(orient='records')
gap_json   = gap_df.to_dict(orient='records')

with open("/Users/dak/Information_Visualisation_Project/data.json", "w") as f:
    json.dump({"generation": gen_json, "treatment": treat_json, "gap": gap_json}, f, indent=2)

print("\n✅ All files saved.")
print(f"   gwa01_clean.csv  → {len(gen_json)} rows")
print(f"   gwa02_clean.csv  → {len(treat_json)} rows")
print(f"   gap_2020.csv     → {len(gap_json)} rows")
