"""
Convert the Ensembl-fetched HIrisPlex-S dosage CSV
into a CSV that the HIrisPlex-S webtool accepts.

The webtool at https://hirisplex.erasmusmc.nl/ requires:
  - CSV format
  - First column: SampleID
  - Column headers in rsID_Allele format (e.g. rs312262906_A) — NOT plain rsID
  - Values: dosage counts 0 / 1 / 2  (NA for missing)

Input : data/raw/igsr/hirisplex_genotypes/hirisplex_1kg_genotypes.csv
Output: data/raw/igsr/hirisplex_genotypes/hirisplex_webtool_input.csv
"""
import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, "src")
from phenotype_predictor.markers.hirisplex import HIRISPLEX_S_MARKERS

IN_PATH  = Path("data/raw/igsr/hirisplex_genotypes/hirisplex_1kg_genotypes.csv")
OUT_PATH = Path("data/raw/igsr/hirisplex_genotypes/hirisplex_webtool_input.csv")

print("Reading genotype dosage CSV...")
df = pd.read_csv(IN_PATH)
print(f"  Shape: {df.shape}")

# Rename sample_id -> SampleID  (keep all other columns as-is: rs_A format)
df = df.rename(columns={"sample_id": "SampleID"})

# The Ensembl CSV already has rsID_Allele format (e.g. rs312262906_A)
# which is EXACTLY what the webtool requires. Just reorder to marker order.
marker_cols = [m.feature_name for m in HIRISPLEX_S_MARKERS]   # rs312262906_A, ...
available   = [c for c in marker_cols if c in df.columns]
missing     = [c for c in marker_cols if c not in df.columns]

if missing:
    print(f"  WARNING: {len(missing)} marker columns not in data: {missing}")

cols = ["SampleID"] + available
df = df[cols]

df.to_csv(OUT_PATH, index=False)
print(f"\nSaved: {OUT_PATH}")
print(f"  Samples : {len(df)}")
print(f"  SNP cols: {len(available)}")
print()
print("Column format (first 5):", list(df.columns[1:6]))
print()
print("Preview (first 3 rows, first 6 columns):")
print(df.iloc[:3, :6].to_string(index=False))
print()
print("=" * 55)
print("NEXT STEPS")
print("=" * 55)
print()
print("1. Open: https://hirisplex.erasmusmc.nl/")
print("2. Upload this file:", OUT_PATH.resolve())
print("3. Select: Eye color + Hair color + Skin color")
print("4. Download the results CSV")
print("5. Save it as:")
print("     data/raw/igsr/hirisplex_genotypes/hirisplex_webtool_results.csv")
print("6. Run: python parse_hirisplex_results.py")
