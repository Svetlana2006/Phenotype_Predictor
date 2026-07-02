"""
Parse the HIrisPlex-S webtool results CSV and combine with the
1000 Genomes genotype features to create a pigmentation training dataset.

Input:
  data/raw/igsr/hirisplex_genotypes/hirisplex_webtool_results.csv
    (downloaded from https://hirisplex.erasmusmc.nl/ after submission)
  data/raw/igsr/hirisplex_genotypes/hirisplex_1kg_phase3.vcf
    (our extracted genotype data)

Output:
  outputs/pigmentation_training_table.csv
    Columns: sample_id, eye_color, hair_color, skin_color,
             <41 HIrisPlex SNP dosage features>

This table is then used by train_pigmentation.py to train the models.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, "src")
from phenotype_predictor.markers.hirisplex import HIRISPLEX_S_MARKERS

RESULTS_PATH = Path("data/raw/igsr/hirisplex_genotypes/hirisplex_webtool_results.csv")
VCF_PATH     = Path("data/raw/igsr/hirisplex_genotypes/hirisplex_1kg_phase3.vcf")
OUT_PATH     = Path("outputs/pigmentation_training_table.csv")

MARKER_ORDER = [m.rsid for m in HIRISPLEX_S_MARKERS]

print("=" * 60)
print("Parse HIrisPlex-S Webtool Results -> Training Table")
print("=" * 60)

# ── Check inputs ──────────────────────────────────────────────────────────────
if not RESULTS_PATH.exists():
    print(f"ERROR: Webtool results not found at {RESULTS_PATH}")
    print()
    print("Steps to generate it:")
    print("  1. Run format_hirisplex_webtool.py")
    print("  2. Upload output to https://hirisplex.erasmusmc.nl/")
    print("  3. Download results CSV and save as:")
    print(f"     {RESULTS_PATH}")
    sys.exit(1)

if not VCF_PATH.exists():
    print(f"ERROR: Genotype VCF not found at {VCF_PATH}")
    print("Run download_hirisplex_1kg.py first.")
    sys.exit(1)

# ── Load webtool results ──────────────────────────────────────────────────────
print(f"Loading webtool results from {RESULTS_PATH}...")
results = pd.read_csv(RESULTS_PATH)
print(f"  Columns: {list(results.columns)}")
print(f"  Rows: {len(results)}")

# The webtool returns probability columns like:
#   blue_prob, intermediate_prob, brown_prob  (eye)
#   black_prob, dark_brown_prob, ...          (hair)
#   very_pale_prob, pale_prob, ...            (skin)
# We take the highest-probability class as the label.

def assign_label(row: pd.Series, prob_cols: list[str]) -> str:
    """Return the class name with the highest probability."""
    vals = {col.replace("_prob", ""): row[col] for col in prob_cols if col in row.index}
    return max(vals, key=vals.get) if vals else "unknown"

# Detect column groups automatically
all_cols = list(results.columns)
eye_cols  = [c for c in all_cols if "eye"  in c.lower() or c.lower().startswith("blue") or c.lower() in ("brown", "intermediate")]
hair_cols = [c for c in all_cols if "hair" in c.lower() or "black" in c.lower() or "blond" in c.lower() or "red" in c.lower()]
skin_cols = [c for c in all_cols if "skin" in c.lower() or "pale" in c.lower() or "dark" in c.lower()]

# Fallback: look for _prob suffix groups
if not eye_cols:
    eye_cols  = [c for c in all_cols if "eye" in c.lower()]
if not hair_cols:
    hair_cols = [c for c in all_cols if "hair" in c.lower()]
if not skin_cols:
    skin_cols = [c for c in all_cols if "skin" in c.lower()]

print(f"  Eye cols:  {eye_cols}")
print(f"  Hair cols: {hair_cols}")
print(f"  Skin cols: {skin_cols}")

# ── Assign labels from highest-probability class ──────────────────────────────
sample_col = results.columns[0]   # first column is sample ID
labels = results[[sample_col]].copy()
labels.columns = ["sample_id"]

if eye_cols:
    labels["eye_color"]  = results[eye_cols].idxmax(axis=1).str.replace("_prob","").str.lower()
if hair_cols:
    labels["hair_color"] = results[hair_cols].idxmax(axis=1).str.replace("_prob","").str.lower()
if skin_cols:
    labels["skin_color"] = results[skin_cols].idxmax(axis=1).str.replace("_prob","").str.lower()

print()
print("Label distributions:")
for col in ["eye_color", "hair_color", "skin_color"]:
    if col in labels.columns:
        print(f"  {col}:")
        print(labels[col].value_counts().to_string())
        print()

# ── Parse genotype VCF into dosage features ───────────────────────────────────
print(f"Parsing genotype dosages from {VCF_PATH}...")

sample_ids: list[str] = []
dosage_data: dict[str, list[int]] = {}

with open(VCF_PATH, encoding="utf-8") as f:
    for line in f:
        if line.startswith("##"):
            continue
        if line.startswith("#CHROM"):
            parts = line.strip().split("\t")
            sample_ids = parts[9:]
            continue

        parts = line.strip().split("\t")
        if len(parts) < 10:
            continue

        rsid   = parts[2]
        ref    = parts[3]
        alt    = parts[4].split(",")[0]
        alleles = [ref, alt]
        format_fields = parts[8].split(":")
        gt_idx = format_fields.index("GT") if "GT" in format_fields else 0

        # Find which allele is the effect allele for this marker
        marker_map = {m.rsid: m.allele for m in HIRISPLEX_S_MARKERS}
        effect_allele = marker_map.get(rsid, alt)

        dosages: list[int] = []
        for sample_field in parts[9:]:
            gt_str = sample_field.split(":")[gt_idx]
            sep = "|" if "|" in gt_str else "/"
            allele_indices = gt_str.split(sep)
            try:
                a1 = alleles[int(allele_indices[0])]
                a2 = alleles[int(allele_indices[1])]
                dosage = int(a1 == effect_allele) + int(a2 == effect_allele)
            except (ValueError, IndexError):
                dosage = -1  # missing
            dosages.append(dosage)

        feature_name = rsid + "_" + effect_allele
        dosage_data[feature_name] = dosages

print(f"  {len(dosage_data)} SNP features parsed for {len(sample_ids)} samples")

geno_df = pd.DataFrame(dosage_data)
geno_df.insert(0, "sample_id", sample_ids)
geno_df.replace(-1, np.nan, inplace=True)

# ── Merge labels with genotype features ──────────────────────────────────────
merged = labels.merge(geno_df, on="sample_id", how="inner")
print(f"\nMerged dataset: {merged.shape[0]} samples x {merged.shape[1]} columns")

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
merged.to_csv(OUT_PATH, index=False)
print(f"Saved: {OUT_PATH}")
print()
print("Next: run train_pigmentation.py to train eye/hair/skin color models")
