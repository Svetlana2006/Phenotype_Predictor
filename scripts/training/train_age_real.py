"""Train age regression models on the real GSE40279 methylation dataset."""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "src")

import pandas as pd

from phenotype_predictor.data_io import split_features_target
from phenotype_predictor.models.baselines import train_regressors
from phenotype_predictor.reporting import write_model_card
from pathlib import Path

print("=== STEP 2: Training Age Regression Models on Real GSE40279 Data ===")
df = pd.read_csv(r"outputs\gse40279_age_table.csv")

# Drop non-feature columns (metadata), keep only CpG columns + age
drop_cols = ["sample_id", "gender", "ethnicity", "tissue"]
feature_df = df.drop(columns=[c for c in drop_cols if c in df.columns])

x, y = split_features_target(feature_df, "age")
print(f"Features : {x.shape[1]} CpG methylation sites")
print(f"Samples  : {len(x)}")
print(f"Age range: {y.min():.0f} – {y.max():.0f} yrs  (mean={y.mean():.1f}, std={y.std():.1f})")
print()

t0 = time.time()
results = train_regressors(x, y, r"outputs\age_models")
elapsed = time.time() - t0

print(f"Training complete in {elapsed:.1f}s")
print()
print("=" * 55)
print("MODEL RESULTS  (test set = 20% held-out, ~33 samples)")
print("=" * 55)
best_mae = min(r.metrics["mae"] for r in results)
for r in results:
    star = " *BEST*" if r.metrics["mae"] == best_mae else ""
    print(
        f"  {r.model_name:<25}  MAE={r.metrics['mae']:5.2f} yrs   R2={r.metrics['r2']:.4f}{star}"
    )
print()
print("  MAE = mean absolute error in years (lower is better)")
print("  R2  = variance explained        (closer to 1.0 is better)")
print()

# Write model cards
for r in results:
    write_model_card(
        Path("outputs/age_models") / f"{r.model_name}_model_card.md",
        f"Age model: {r.model_name}",
        "data/raw/gse40279/GSE40279_average_beta_GSM989827-GSM989990.txt.gz",
        "age",
        r.metrics,
        [
            "Trained on whole-blood DNA methylation (Illumina 27k array, GSE40279).",
            "Cohort is ~65% Caucasian-European, ~35% Hispanic-Mexican (ages 19–101).",
            "Chronological age prediction is tissue-type dependent.",
            "External validation is required before any forensic interpretation.",
        ],
    )
print(f"Model cards saved to outputs/age_models/")
print(f"Saved model files: {[r.model_path.name for r in results]}")
