"""
Train eye color, hair color, and skin color classifiers
using HIrisPlex-S webtool predictions as labels on 1000 Genomes samples.

Data: 2,504 samples x 41 HIrisPlex SNP dosage features
Labels: highest-probability class from HIrisPlex-S webtool predictions
Models: Logistic Regression, Random Forest (per trait)
Output: outputs/pigmentation_models/
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import numpy as np
import joblib

sys.path.insert(0, "src")
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import balanced_accuracy_score, classification_report
from phenotype_predictor.reporting import write_model_card

# ── Config ────────────────────────────────────────────────────────────────────
OUT_DIR = Path("outputs/pigmentation_models")
OUT_DIR.mkdir(parents=True, exist_ok=True)
RANDOM_STATE = 42

# ── Load & clean training table ───────────────────────────────────────────────
print("=" * 60)
print("Pigmentation Model Training")
print("=" * 60)

results = pd.read_csv("data/raw/igsr/hirisplex_genotypes/Result.csv")
geno    = pd.read_csv("data/raw/igsr/hirisplex_genotypes/hirisplex_1kg_genotypes.csv")

# Assign hard labels cleanly
eye_cols  = ["PBlueEye", "PIntermediateEye", "PBrownEye"]
hair_cols = ["PBlondHair", "PBrownHair", "PRedHair", "PBlackHair"]
skin_cols = ["PVeryPaleSkin", "PPaleSkin", "PIntermediateSkin", "PDarkSkin", "PDarktoBlackSkin"]

label_map = {
    "PBlueEye":         "blue",
    "PIntermediateEye": "intermediate",
    "PBrownEye":        "brown",
    "PBlondHair":       "blond",
    "PBrownHair":       "brown",
    "PRedHair":         "red",
    "PBlackHair":       "black",
    "PVeryPaleSkin":    "very_pale",
    "PPaleSkin":        "pale",
    "PIntermediateSkin":"intermediate",
    "PDarkSkin":        "dark",
    "PDarktoBlackSkin": "dark_to_black",
}

results["eye_color"]  = results[eye_cols].idxmax(axis=1).map(label_map)
results["hair_color"] = results[hair_cols].idxmax(axis=1).map(label_map)
results["skin_color"] = results[skin_cols].idxmax(axis=1).map(label_map)

labels = results[["SampleID", "eye_color", "hair_color", "skin_color"]].rename(
    columns={"SampleID": "sample_id"}
)

# Merge with genotype features
df = labels.merge(geno, on="sample_id", how="inner")
feature_cols = [c for c in geno.columns if c != "sample_id"]
X = df[feature_cols].fillna(0)

print(f"Samples  : {len(df)}")
print(f"Features : {len(feature_cols)} HIrisPlex SNP dosages")
print()

# ── Per-trait training ─────────────────────────────────────────────────────────
TRAITS = {
    "eye_color":  ("Eye Color",  eye_cols),
    "hair_color": ("Hair Color", hair_cols),
    "skin_color": ("Skin Color", skin_cols),
}

MODELS = {
    "logistic_regression": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("clf",    LogisticRegression(max_iter=1000, random_state=RANDOM_STATE, C=1.0)),
    ]),
    "random_forest": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("clf", RandomForestClassifier(
            n_estimators=300,
            max_features="sqrt",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        )),
    ]),
}

all_results = []

for trait, (trait_name, _) in TRAITS.items():
    y = df[trait]

    # Merge very small classes to avoid stratify errors
    if trait == "skin_color":
        # Merge: very_pale + pale -> pale  |  dark + dark_to_black -> dark_or_black
        y = y.replace({"very_pale": "pale", "dark_to_black": "dark_or_black", "dark": "dark_or_black"})
    if trait == "hair_color":
        # Merge: red -> other (only 24 samples, keeps model honest)
        y = y.replace({"red": "other"})

    print(f"\n{'='*60}")
    print(f"Trait: {trait_name}")
    print(f"{'='*60}")
    print(f"  Class distribution:")
    print(y.value_counts().to_string())

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"  Train: {len(X_tr)}  Test: {len(X_te)}")

    trait_dir = OUT_DIR / trait
    trait_dir.mkdir(exist_ok=True)

    best_ba = -1
    for model_name, pipe in MODELS.items():
        out_path = trait_dir / f"{model_name}.joblib"

        print(f"  Fitting {model_name}...", flush=True)
        t0 = time.time()
        pipe.fit(X_tr, y_tr)
        print(f"    Done in {time.time()-t0:.1f}s")
        joblib.dump(pipe, out_path)

        preds = pipe.predict(X_te)
        ba = balanced_accuracy_score(y_te, preds)
        star = " <-- BEST" if ba > best_ba else ""
        if ba > best_ba:
            best_ba = ba
        print(f"  {model_name:<25}  balanced_acc={ba:.4f}{star}")

        metrics = {"balanced_accuracy": round(ba, 4)}
        all_results.append({
            "trait": trait, "model": model_name, "balanced_accuracy": ba
        })

        write_model_card(
            trait_dir / f"{model_name}_model_card.md",
            f"{trait_name} model: {model_name}",
            "data/raw/igsr/hirisplex_genotypes/hirisplex_1kg_genotypes.csv",
            trait,
            metrics,
            [
                "Labels derived from HIrisPlex-S webtool predictions (erasmusmc.nl).",
                "Genotypes: 1000 Genomes Phase 3, 2,504 samples from 5 super-populations.",
                "Features: 41 HIrisPlex-S SNP dosages (0/1/2 per effect allele).",
                "Labels represent model predictions, not self-reported phenotypes.",
                "Performance reflects how well the model replicates HIrisPlex-S.",
                "Skin color has strong population structure bias — interpret with caution.",
            ],
        )

    # Print detailed report for the best model
    best_model_name = max(
        MODELS.keys(),
        key=lambda m: balanced_accuracy_score(
            y_te, joblib.load(trait_dir / f"{m}.joblib").predict(X_te)
        )
    )
    best_pipe = joblib.load(trait_dir / f"{best_model_name}.joblib")
    print(f"\n  Classification report ({best_model_name}):")
    print(classification_report(y_te, best_pipe.predict(X_te), zero_division=0))

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)
summary_df = pd.DataFrame(all_results)
print(summary_df.to_string(index=False))
summary_df.to_csv(OUT_DIR / "pigmentation_results_summary.csv", index=False)
print(f"\nAll models saved to: {OUT_DIR}/")
print("Done.")
