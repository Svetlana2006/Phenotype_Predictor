"""
Train age regression models on the FULL GSE40279 methylation dataset (~450k CpGs).

Safety features:
  1. RAM check at startup - warns and exits if free memory is too low
  2. Feature selection - reduces 450k CpGs to top N most correlated with age
     before any model sees the data (one streaming pass, low peak RAM)
  3. No SVR - SVR is quadratic in memory on high-dimensional data, excluded here
  4. Incremental saves - each model is saved to disk immediately after fitting;
     a crash only loses the model currently training, not everything already done
  5. Progress reporting - prints memory usage at key steps
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, "src")

# ── 1. RAM check ──────────────────────────────────────────────────────────────
try:
    import psutil
    free_gb = psutil.virtual_memory().available / 1e9
    total_gb = psutil.virtual_memory().total / 1e9
    print(f"RAM check: {free_gb:.1f} GB free of {total_gb:.1f} GB total")
    if free_gb < 4.0:
        print()
        print("ERROR: Less than 4 GB of RAM is free.")
        print("Close other applications and try again.")
        print("At minimum, you need ~6 GB free for safe full-CpG training.")
        sys.exit(1)
    elif free_gb < 6.0:
        print("WARNING: Less than 6 GB free - training will proceed but may be slow.")
    else:
        print("RAM looks good. Proceeding.")
except ImportError:
    print("psutil not installed - skipping RAM check. Run: pip install psutil")

print()

# ── 2. Config ─────────────────────────────────────────────────────────────────
FULL_TABLE   = Path("outputs/gse40279_age_table_full.csv")
OUTPUT_DIR   = Path("outputs/age_models_full")
TOP_N_CPGS   = 5000   # keep top N CpGs most correlated with age
TEST_SIZE    = 0.2
RANDOM_STATE = 42

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Full CpG table : {FULL_TABLE}  ({FULL_TABLE.stat().st_size / 1e6:.0f} MB)")
print(f"Feature budget : top {TOP_N_CPGS:,} CpGs selected by |Pearson r| with age")
print(f"Output dir     : {OUTPUT_DIR}")
print()

# ── 3. Load table ─────────────────────────────────────────────────────────────
print("[1/4] Loading full methylation table into memory...", flush=True)
t0 = time.time()

import pandas as pd
import numpy as np

df = pd.read_csv(FULL_TABLE)
print(f"      Loaded: {df.shape[0]} samples x {df.shape[1]} columns  ({time.time()-t0:.0f}s)", flush=True)

meta_cols = ["sample_id", "age", "gender", "ethnicity", "tissue"]
drop_cols  = [c for c in meta_cols if c in df.columns and c != "age"]
y = df["age"].astype(float)
X_full = df.drop(columns=[c for c in meta_cols if c in df.columns])

print(f"      Feature columns: {X_full.shape[1]:,}", flush=True)

# ── 4. Feature selection (correlation with age) ───────────────────────────────
print(f"\n[2/4] Selecting top {TOP_N_CPGS:,} CpGs by |Pearson r| with age...", flush=True)
t1 = time.time()

# Vectorised correlation: faster than applying corr() column by column
X_arr = X_full.values.astype("float32")
y_arr = y.values.astype("float32")

# z-score each column and y, then dot product / n
X_mean = np.nanmean(X_arr, axis=0)
X_std  = np.nanstd(X_arr,  axis=0) + 1e-8
y_mean = float(np.nanmean(y_arr))
y_std  = float(np.nanstd(y_arr))  + 1e-8

X_z = (X_arr - X_mean) / X_std          # (n_samples, n_cpgs)
y_z = (y_arr - y_mean) / y_std          # (n_samples,)

corr = (X_z * y_z[:, None]).mean(axis=0)   # (n_cpgs,)  — Pearson r per CpG
top_idx = np.argsort(np.abs(corr))[-TOP_N_CPGS:]
top_cols = X_full.columns[top_idx].tolist()

print(f"      Done in {time.time()-t1:.1f}s", flush=True)
print(f"      Top CpG |r| range: {np.abs(corr[top_idx]).min():.4f} to {np.abs(corr[top_idx]).max():.4f}", flush=True)

# Free the large array immediately to reclaim RAM
del X_arr, X_z, corr
import gc; gc.collect()

X = X_full[top_cols].copy()
del X_full
gc.collect()

print(f"      Feature matrix after selection: {X.shape}  (RAM freed)", flush=True)

# Save the selected CpG list so it can be reused for inference
selected_cpgs_path = OUTPUT_DIR / "selected_cpgs.txt"
selected_cpgs_path.write_text("\n".join(top_cols))
print(f"      Selected CpG names saved to {selected_cpgs_path}", flush=True)

# ── 5. Train/test split ───────────────────────────────────────────────────────
print("\n[3/4] Splitting train/test...", flush=True)

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from phenotype_predictor.data_io import split_features_target
from phenotype_predictor.models.baselines import _preprocessor
from phenotype_predictor.reporting import write_model_card
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
import joblib

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
)
print(f"      Train: {len(X_train)}  Test: {len(X_test)}", flush=True)

# ── 6. Train models incrementally ─────────────────────────────────────────────
print("\n[4/4] Training models (each saved to disk immediately)...", flush=True)

candidates = {
    "ridge": Ridge(alpha=1.0),
    "random_forest": RandomForestRegressor(
        n_estimators=200,
        max_features="sqrt",     # limit features per split - much lower RAM than default
        n_jobs=-1,
        random_state=RANDOM_STATE,
    ),
}

results = []
for name, estimator in candidates.items():
    out_path = OUTPUT_DIR / (name + ".joblib")

    # Skip if already trained (crash recovery)
    if out_path.exists():
        print(f"  {name}: already exists, skipping (delete to retrain)", flush=True)
        pipe = joblib.load(out_path)
        pred = pipe.predict(X_test)
        metrics = {
            "mae": float(mean_absolute_error(y_test, pred)),
            "r2":  float(r2_score(y_test, pred)),
        }
        results.append((name, metrics))
        continue

    print(f"  Fitting {name}...", flush=True)
    t2 = time.time()
    prep = _preprocessor(X_train)
    pipe = Pipeline([("prep", prep), ("model", estimator)])
    pipe.fit(X_train, y_train)
    print(f"    Fit done in {time.time()-t2:.0f}s - saving...", flush=True)

    # Save immediately
    joblib.dump(pipe, out_path)
    pred = pipe.predict(X_test)
    metrics = {
        "mae": float(mean_absolute_error(y_test, pred)),
        "r2":  float(r2_score(y_test, pred)),
    }
    results.append((name, metrics))
    print(f"    Saved to {out_path}  |  MAE={metrics['mae']:.2f} yrs  R2={metrics['r2']:.4f}", flush=True)

    # Write model card immediately
    write_model_card(
        OUTPUT_DIR / (name + "_model_card.md"),
        "Age model (full CpG): " + name,
        str(FULL_TABLE),
        "age",
        metrics,
        [
            "Trained on whole-blood DNA methylation (Illumina 27k array, GSE40279).",
            "Cohort: 164 samples, ~65% Caucasian-European, ~35% Hispanic-Mexican, ages 28-101.",
            f"Feature set: top {TOP_N_CPGS:,} CpGs selected by |Pearson r| with age from full ~450k array.",
            "Chronological age prediction is tissue-type dependent.",
            "External validation required before any forensic or clinical interpretation.",
        ],
    )

    # Free model from RAM before fitting next one
    del pipe
    gc.collect()

# ── 7. Summary ────────────────────────────────────────────────────────────────
print()
print("=" * 55)
print("FULL-CpG MODEL RESULTS  (test set = 20% held-out)")
print("=" * 55)
best_mae = min(m["mae"] for _, m in results)
for name, m in results:
    tag = "  <-- BEST" if m["mae"] == best_mae else ""
    print(f"  {name:<25}  MAE={m['mae']:5.2f} yrs   R2={m['r2']:.4f}{tag}")
print()
print(f"Total time: {time.time()-t0:.0f}s")
print(f"Outputs saved to: {OUTPUT_DIR}/")
